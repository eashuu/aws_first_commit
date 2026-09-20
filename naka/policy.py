"""The control-plane client. Fetches the policy bundle, caches it with a TTL,
and enforces the policy floor: a bundle whose Cedar text does not contain
every mandatory rule is rejected and the previous bundle stays in force.

Unreachable must fail closed to a KNOWN policy, not to no policy (PRD §5) —
that known policy is `agent.cedar`, baked into the deployment package.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal

import cedarpy

from config import (
    DEFAULT_BUDGET,
    DEFAULT_COMPREHEND_MIN_SCORE,
    DEFAULT_IDENTIFYING_TYPES,
    DEFAULT_SESSION_CEILING,
    Config,
)

# The mandatory rules a served bundle must contain verbatim. A rewrite that
# keeps the substring but changes semantics defeats this — it is a substring
# check, not a semantic one, and that limitation is stated, not hidden
# (TD §1.8). Kept in sync with the corrected policy in agent.cedar; if you
# change the ceiling rule's head or condition text, update both.
FLOOR_RULES: tuple[str, ...] = (
    'forbid(principal, action == Action::"reveal_IN_AADHAAR", resource)',
    "context.session.seen_count >= context.session.budget",
)

PolicySource = Literal["control-plane", "cache", "package-fallback"]


@dataclass(frozen=True)
class PolicyBundle:
    version: str
    etag: str
    cedar: str
    policy_set: object  # cedarpy.PolicySet — parsed once, reused across calls
    entities: list[dict]
    budget_default: int
    budget_per_role: dict[str, int]
    session_ceiling: int
    identifying_types: frozenset[str]
    comprehend_min_score: float
    source: PolicySource

    def budget_for(self, role: str) -> int:
        return self.budget_per_role.get(role, self.budget_default)


def floor_ok(cedar_text: str) -> bool:
    return all(rule in cedar_text for rule in FLOOR_RULES)


def _bundle_from_fallback(cfg: Config) -> PolicyBundle:
    with open(cfg.fallback_policy_path, encoding="utf-8") as f:
        cedar_text = f.read()
    if not floor_ok(cedar_text):
        # The packaged fallback is supposed to be strictly more restrictive
        # than anything served — if IT fails its own floor, refuse to run
        # rather than serve a policy nobody validated.
        raise RuntimeError("packaged fallback policy fails its own floor check")
    return PolicyBundle(
        version="package-fallback",
        etag="",
        cedar=cedar_text,
        policy_set=cedarpy.PolicySet.from_str(cedar_text),
        entities=[],
        budget_default=DEFAULT_BUDGET,
        budget_per_role={"compliance": 9999},
        session_ceiling=DEFAULT_SESSION_CEILING,
        identifying_types=DEFAULT_IDENTIFYING_TYPES,
        comprehend_min_score=DEFAULT_COMPREHEND_MIN_SCORE,
        source="package-fallback",
    )


def _bundle_from_json(body: dict, *, etag: str) -> PolicyBundle | None:
    cedar_text = body.get("cedar")
    if not cedar_text or not floor_ok(cedar_text):
        return None
    try:
        policy_set = cedarpy.PolicySet.from_str(cedar_text)
    except ValueError:
        return None  # malformed Cedar — caller keeps the previous bundle

    budget = body.get("budget", {})
    return PolicyBundle(
        version=str(body.get("version", "")),
        etag=etag,
        cedar=cedar_text,
        policy_set=policy_set,
        entities=body.get("entities", []),
        budget_default=int(budget.get("default", DEFAULT_BUDGET)),
        budget_per_role={k: int(v) for k, v in budget.get("per_role", {}).items()},
        session_ceiling=int(body.get("session_ceiling", DEFAULT_SESSION_CEILING)),
        identifying_types=frozenset(body.get("identifying_types", list(DEFAULT_IDENTIFYING_TYPES))),
        comprehend_min_score=float(body.get("thresholds", {}).get("comprehend_min_score", DEFAULT_COMPREHEND_MIN_SCORE)),
        source="control-plane",
    )


class _State:
    bundle: PolicyBundle | None = None
    fetched_at: float = 0.0


_state = _State()


def current(cfg: Config) -> PolicyBundle:
    """No I/O if a bundle is already cached — use refresh() to check the TTL."""
    if _state.bundle is None:
        return refresh(cfg=cfg, force=True)
    return _state.bundle


def refresh(*, cfg: Config, force: bool = False) -> PolicyBundle:
    """Checked at the top of each HTTP request, never mid-turn — a policy
    that changed between hop 2 and hop 3 of one turn would make the audit
    trail unexplainable."""
    now = time.time()
    if not force and _state.bundle is not None and (now - _state.fetched_at) < cfg.policy_ttl_s:
        return _state.bundle

    if not cfg.control_plane_url:
        bundle = _state.bundle or _bundle_from_fallback(cfg)
        _state.bundle, _state.fetched_at = bundle, now
        return bundle

    try:
        fetched = _fetch(cfg)
    except Exception:
        fetched = None

    bundle = fetched or _state.bundle or _bundle_from_fallback(cfg)
    _state.bundle, _state.fetched_at = bundle, now
    return bundle


def _fetch(cfg: Config) -> PolicyBundle | None:
    """Returns None to mean "keep whatever we had" — a 304, a transient
    failure, or a bundle that fails validation are all the same instruction
    to the caller: do not replace a known-good policy with an unknown one."""
    headers = {}
    if _state.bundle is not None and _state.bundle.source == "control-plane" and _state.bundle.etag:
        headers["If-None-Match"] = _state.bundle.etag

    # rstrip is load-bearing. deploy.ps1 writes CONTROL_PLANE_URL with the
    # trailing slash the Function URL reports, so this produced "//policy",
    # which app_control's router does not match ("/policy" != "//policy") and
    # which therefore fell through to _serve_static and 404'd. The 404 raised,
    # refresh() swallowed it, and the agent silently fell back to the policy
    # baked into the package — for every request, forever.
    #
    # The effect was that the console's policy editor did not work at all:
    # PUT /policy stored the new bundle, the control plane served it, and the
    # data plane never read it. Nothing surfaced the failure because falling
    # back to a known-good policy is exactly what refresh() is supposed to do
    # when a fetch fails; it just had no way to say the fetch was failing
    # every single time. The `policy_version` on every audit row read
    # "package-fallback", which is the tell.
    base = (cfg.control_plane_url or "").rstrip("/")
    req = urllib.request.Request(f"{base}/policy", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_policy_s) as resp:
            if resp.status == 304:
                return None
            body = json.loads(resp.read().decode("utf-8"))
            etag = resp.headers.get("ETag", "")
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return None
        raise

    return _bundle_from_json(body, etag=etag)
