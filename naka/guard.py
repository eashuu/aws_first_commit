"""DisclosureGuard — the centre of the system. One instance per HTTP
request, holding the ledger, the vault and the policy bundle.

before_tool_call: derive the call-scoped subject, stash a context snapshot
for CedarAuthorization's context_enricher to read (registered second, so it
runs after this), and enforce the session_ceiling backstop.

after_tool_call: normalize -> detect -> attribute -> Q2 -> redact -> spend.
Mutates event.result in place via Transform.

The enricher's `ctx["invocation_state"]` is not read — the PRD warns it is
not documented as the same object this handler mutated, so the stash reads
the handler instance directly instead, keyed by (tool_name, canonical
tool_input) so concurrent tool calls within one model turn cannot read each
other's snapshot (TD §6.3).
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field

from strands.hooks.events import AfterToolCallEvent, BeforeToolCallEvent
from strands.interventions import Deny, InterventionHandler, OnError, Proceed, Transform

import attribute
import cedar_q2
import detect
import ledger as ledger_mod
import normalize
from config import Config
from rehydrate import Vault

WITHHELD = (
    "[CONTENT WITHHELD BY POLICY GUARD: {reason}. "
    "The data was not inspected, so it cannot be released. "
    "Do not retry this exact call.]"
)


def _canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, default=str)


@dataclass
class HopOutcome:
    """What after_tool_call decided, carried out to the caller so app_agent.py
    and audit.py don't have to re-derive it from the mutated event."""

    outcome: str  # "ok" | "withheld_detector" | "withheld_normalize" | "withheld_ledger"
    subject: str
    content_type: str
    pages: int
    truncated: bool
    detector_tiers: list[str]
    entities_found: dict[str, int]
    entities_masked: dict[str, int]
    entities_revealed: dict[str, int]
    mask_policies: dict[str, str]
    ledger_before: list[str]
    ledger_after: list[str]
    budget: int
    session_total: int
    latency_ms: dict[str, int]
    # Shadow mode (enforce=False): the identical decision path ran and
    # `would_mask` is what it decided, but nothing was substituted and the
    # payload reached the model intact. `entities_masked` stays empty in
    # that case precisely because nothing WAS masked -- the counterfactual
    # lives in its own field rather than overloading the enforced one, so a
    # dashboard summing `entities_masked` across rows can never silently
    # count a shadow row as a prevented disclosure.
    enforce: bool = True
    would_mask: dict[str, int] = field(default_factory=dict)


class DisclosureGuard(InterventionHandler):
    name = "disclosure-guard"

    def __init__(
        self,
        *,
        session_id: str,
        principal: str,
        role: str,
        vault: Vault,
        ledger: ledger_mod.Ledger,
        policy,  # policy.PolicyBundle
        cfg: Config,
        enforce: bool = True,
    ) -> None:
        # enforce=False is shadow mode: authorize exactly as usual, record
        # every decision, substitute nothing. It exists for the reason every
        # blocking control eventually needs it -- nobody turns one on in
        # front of live traffic without first measuring what it would have
        # blocked -- and it is what makes the demo's guarded/unguarded
        # comparison a real counterfactual rather than two different
        # codepaths photographed side by side.
        self.enforce = enforce
        self.session_id = session_id
        self.principal = principal
        self.role = role
        self.vault = vault
        self.ledger = ledger
        self.policy = policy
        self.cfg = cfg
        # Two views of the same stash object. The content-keyed one is for
        # `snapshot()` — the context_enricher is handed only
        # {tool_name, tool_input, invocation_state}, with no tool-use id, so
        # content is the only key available to it. The id-keyed one is for
        # `after_tool_call`, because the Rehydrator (registered third) can
        # legitimately MUTATE tool_input between the two, which would leave
        # the content key unmatchable on the after-path.
        self._pending: dict[tuple[str, str], dict] = {}
        self._pending_by_id: dict[str, dict] = {}
        self._lock = threading.Lock()
        # Keyed by toolUseId, not appended in call order: if Strands ever
        # dispatches multiple tool calls from one model turn concurrently
        # (undetermined by the docs — PRD open question 1), a FIFO list
        # would let AuditHook read call A's outcome for call B's audit row.
        self.hop_outcomes: dict[str, HopOutcome] = {}

    @property
    def on_error(self) -> OnError:
        return "deny"  # a handler that crashes must not let the call through

    def _withhold(self, reason: str) -> Proceed | Transform:
        """Blank the payload behind the WITHHELD notice — unless this is a
        shadow run, which must never alter traffic.

        Shadow mode is enabled on exactly one promise: that it cannot break
        anything. A detector outage that blanked a tool result in shadow
        mode would violate that promise, so the conservative default here is
        the wrong one — an operator who wanted blocking would have enabled
        it. The audit row is still written either way, so the hop shows up
        as unmeasured rather than as silently clean.
        """
        if not self.enforce:
            return Proceed()
        return Transform(apply=lambda ev: _replace_content(ev.result, WITHHELD.format(reason=reason)))

    # -- Q1 side: stash + ceiling -------------------------------------------------

    def before_tool_call(self, event: BeforeToolCallEvent) -> Proceed | Deny:
        tool_name = event.tool_use.get("name", "")
        tool_input = event.tool_use.get("input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}

        if self.ledger.total() >= self.ledger.session_ceiling and self.enforce:
            # Cross-subject backstop against subject-id churn (§7 threat 6).
            # This denies the CALL, not a field — there is nothing left to
            # redact once the whole session is over its ceiling.
            #
            # Shadow mode lets the call through instead. A ceiling that
            # short-circuits here would end the unguarded run early and the
            # comparison would understate the leak -- the whole point of the
            # shadow run is to see how far past the ceiling the session
            # actually goes when nothing stops it.
            return Deny(
                reason=(
                    f"Session disclosure ceiling ({self.ledger.session_ceiling}) reached "
                    f"across all subjects. Start a new session to continue."
                )
            )

        raw_subject = attribute.subject_key(tool_input)
        subject = attribute.canonical_subject(raw_subject, session_id=self.session_id)
        stash = {"subject": subject, "dest": _destination_hint(tool_input)}
        self._pending[(tool_name, _canonical_json(tool_input))] = stash
        tool_use_id = event.tool_use.get("toolUseId")
        if tool_use_id:
            self._pending_by_id[tool_use_id] = stash
        return Proceed()

    def snapshot(self, ctx: dict) -> dict:
        """The context_enricher passed to CedarAuthorization. ctx is
        {'tool_name', 'tool_input', 'invocation_state'}."""
        tool_name = ctx.get("tool_name", "")
        tool_input = ctx.get("tool_input") or {}
        key = (tool_name, _canonical_json(tool_input))
        pending = self._pending.get(key, {})
        subject = pending.get("subject")

        out: dict = {
            "role": self.role,
            "seen": [],
            "seen_count": 0,
            "budget": self.policy.budget_for(self.role),
            "session_total": self.ledger.total(),
            "session_ceiling": self.ledger.session_ceiling,
            "policy_version": self.policy.version,
        }
        if subject is not None:
            out["subject"] = subject
            out["seen"] = self.ledger.seen(subject)
            out["seen_count"] = len(out["seen"])
            out["budget"] = self.policy.budget_for(self.role)
        dest = pending.get("dest")
        if dest is not None:
            # Lets a Q1 policy condition on the call's destination (doc10
            # §0: "DisclosureGuard.snapshot() adds dest when tool_name ==
            # send_summary"). Q3 (rehydrate_<TYPE>) does its own
            # destination check independently via cedar_q2.authorize_
            # rehydration — this is additive, for Q1 policies that want it.
            out["dest"] = dest
        return out

    # -- Q2 side: normalize -> detect -> attribute -> Q2 -> redact -> spend -------

    def after_tool_call(self, event: AfterToolCallEvent) -> Proceed | Transform:
        t0 = time.monotonic()
        tool_name = event.tool_use.get("name", "")
        tool_input = event.tool_use.get("input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}
        # Prefer the id-keyed stash: tool_input may have been rewritten by
        # the Rehydrator since before_tool_call, which would make the
        # content key miss.
        tool_use_id = event.tool_use.get("toolUseId") or ""
        pending = self._pending_by_id.pop(tool_use_id, None)
        if pending is None:
            pending = self._pending.pop((tool_name, _canonical_json(tool_input)), {})
        subject = pending.get("subject") or attribute.canonical_subject(
            attribute.subject_key(tool_input), session_id=self.session_id
        )

        result = event.result
        if not isinstance(result, dict) or result.get("status") != "success":
            return Proceed()  # nothing to scan on an error result

        try:
            with self._lock:
                return self._guard_result(event, subject=subject, t0=t0, tool_use_id=tool_use_id)
        except Exception as exc:  # noqa: BLE001 — the safety net, not decoration
            # Verified against the actual intervention registry (strands
            # .interventions.registry._apply_after_tool_call): Deny has NO
            # effect on after_tool_call — only Transform/Proceed do anything,
            # so on_error="deny" is a silent no-op here and an unhandled
            # exception would release the tool's ORIGINAL, unredacted result
            # to the model. That is the one failure mode this whole design
            # exists to prevent, so it cannot be delegated to the framework's
            # error handling for this event — it must be caught here,
            # explicitly, every time.
            self._record_withheld(
                subject, "withheld_internal_error", "", {"total": int((time.monotonic() - t0) * 1000)}, tool_use_id=tool_use_id
            )
            reason = f"internal error ({type(exc).__name__})"
            return self._withhold(reason)

    def _guard_result(
        self, event: AfterToolCallEvent, *, subject: str, t0: float, tool_use_id: str
    ) -> Proceed | Transform:
        ms: dict[str, int] = {}
        result = event.result
        content = result.get("content") or []

        payload, media_type = _extract_payload(content)

        t_norm = time.monotonic()
        try:
            n = normalize.normalize(payload, media_type, cfg=self.cfg)
        except normalize.NormalizeError as exc:
            # Bind the reason to a plain local BEFORE building the lambda.
            # Python deletes an `except ... as exc` target at the end of the
            # block, so a lambda that closes over `exc` raises NameError
            # when the Transform is applied — which is strictly later than
            # this frame. The whole point of this path is to withhold
            # content; raising instead would defeat it.
            reason = exc.reason
            self._record_withheld(subject, "withheld_normalize", media_type, ms, tool_use_id=tool_use_id)
            return self._withhold(reason)
        ms["normalize"] = int((time.monotonic() - t_norm) * 1000)

        image_bytes = payload if isinstance(payload, (bytes, bytearray)) and media_type.startswith("image/") else None
        image_fmt = "png" if media_type == "image/png" else ("jpeg" if media_type in ("image/jpeg", "image/jpg") else None)

        t_det = time.monotonic()
        try:
            det = detect.detect(
                n.markdown,
                ocr_sourced=n.ocr_sourced,
                cfg=self.cfg,
                min_score=self.policy.comprehend_min_score,
                image=image_bytes,
                image_fmt=image_fmt,
                indic_enabled=self.cfg.indic_enabled,
            )
        except detect.DetectorUnavailable as exc:
            # Same `except ... as exc` lifetime trap as the normalize branch
            # above — bind the message before the lambda captures it.
            reason = f"detector unavailable ({exc.tier})"
            self._record_withheld(subject, "withheld_detector", media_type, ms, tool_use_id=tool_use_id)
            return self._withhold(reason)
        ms["detect"] = int((time.monotonic() - t_det) * 1000)

        # MAX_CHUNKS_PER_HOP's contract is "exceeding it withholds the
        # remainder" (config.py) — the markdown handed to _redact() must
        # already be cut at the boundary Comprehend actually reached, or the
        # uncovered tail passes through untouched (nothing replaces text
        # that has no entity in it). detect() already dropped any entity
        # past that boundary; this is the matching cut on the text itself.
        markdown = n.markdown
        truncated = n.truncated
        if det.covered_chars is not None:
            markdown = markdown[: det.covered_chars]
            truncated = True

        entities = det.entities
        entities_found: dict[str, int] = {}
        for e in entities:
            entities_found[e.type] = entities_found.get(e.type, 0) + 1

        if not entities:
            self._record_ok(
                subject, media_type, n, det, entities_found={}, entities_masked={}, entities_revealed={},
                mask_policies={}, ledger_before=self.ledger.seen(subject), ledger_after=self.ledger.seen(subject), ms=ms,
                truncated=truncated, tool_use_id=tool_use_id,
            )
            if truncated:
                return Transform(apply=lambda ev: _replace_content(ev.result, markdown))
            return Proceed()

        distinct_types = sorted({e.type for e in entities})
        reqs = [cedar_q2.FieldRequest(subject=subject, entity_type=t) for t in distinct_types]

        t_cedar = time.monotonic()
        decisions = cedar_q2.authorize_fields(reqs, principal=self.principal, role=self.role, ledger=self.ledger, policy=self.policy)
        ms["cedar_q2"] = int((time.monotonic() - t_cedar) * 1000)
        decisions_by_type = {d.entity_type: d for d in decisions}

        redacted_text, masked, revealed, mask_policies = _redact(markdown, entities, decisions_by_type, vault=self.vault)

        would_mask: dict[str, int] = {}
        if not self.enforce:
            # Everything above ran identically -- normalize, detect, Q2, and
            # the redaction itself. Only the outcome changes: what Q2 denied
            # becomes `would_mask`, nothing is masked, and every detected
            # entity counts as revealed because the original payload is what
            # reaches the model.
            would_mask, masked = masked, {}
            revealed = dict(entities_found)
            redacted_text = markdown

        revealed_identifying = {t for t in revealed if t in self.policy.identifying_types}
        t_spend = time.monotonic()
        if not self.enforce:
            # The ledger still accumulates in memory, so Q2 keeps deciding
            # against a truthful running total and the shadow run reports how
            # far over budget it went. It is deliberately NOT written to
            # DynamoDB: a measurement run must not spend a real session's
            # budget, and `spend()` is the only authoritative writer.
            before = self.ledger.seen(subject)
            if revealed_identifying:
                self.ledger.add(subject, revealed_identifying)
            after = self.ledger.seen(subject)
        elif revealed_identifying:
            try:
                before, after = ledger_mod.spend(self.session_id, subject, revealed_identifying, cfg=self.cfg)
            except ledger_mod.LedgerUnavailable:
                self._record_withheld(subject, "withheld_ledger", media_type, ms, tool_use_id=tool_use_id)
                return self._withhold("ledger unavailable")
            self.ledger.add(subject, revealed_identifying)
        else:
            # Nothing identifying was revealed this hop — a no-op by
            # definition (ledger.spend() rejects an empty set and would
            # otherwise misreport the ledger as [] -> [] even when the
            # subject already has real history from an earlier call).
            before = after = self.ledger.seen(subject)
        ms["spend"] = int((time.monotonic() - t_spend) * 1000)

        # Cache the ledger into agent.state now, not after agent(...) returns
        # in app_agent.py — S3SessionManager syncs on AfterInvocationEvent,
        # which fires before control returns to the caller, so a state.set()
        # after the call would silently miss this turn's sync entirely
        # (verified against the SDK: sync_agent is wired to
        # AfterInvocationEvent, not called again afterward).
        #
        # Not in shadow mode. The shadow run's ledger counts entities that
        # were never actually spent, and app_agent.py merges this cache ON
        # TOP of the DynamoDB ledger at the start of every turn. Writing it
        # would let a measurement run inflate the budget of a real session
        # that happened to reuse the same session id — the one remaining way
        # a non-enforcing mode could still change enforced behaviour.
        if self.enforce:
            try:
                event.agent.state.set("disclosure_ledger", self.ledger.to_state())
            except Exception:  # noqa: BLE001 — the cache is best-effort; DynamoDB is authoritative
                pass

        ms["total"] = int((time.monotonic() - t0) * 1000)
        self._record_ok(
            subject, media_type, n, det, entities_found=entities_found, entities_masked=masked,
            entities_revealed=revealed, mask_policies=mask_policies, ledger_before=before, ledger_after=after, ms=ms,
            truncated=truncated, tool_use_id=tool_use_id, would_mask=would_mask,
        )

        if not self.enforce:
            # The one branch that differs. Everything above -- normalize,
            # detect, Q2, redact, ledger -- already ran; the shadow run just
            # does not apply the result, so the model receives the tool's
            # original payload. That includes the case where detection was
            # truncated at MAX_CHUNKS_PER_HOP: the enforced path substitutes
            # the cut markdown there, but doing so here would alter traffic,
            # and `truncated` on the audit row already marks the hop as
            # only partially measured.
            return Proceed()

        def _apply(ev: AfterToolCallEvent) -> None:
            _replace_content(ev.result, redacted_text)

        return Transform(apply=_apply)

    def _record_ok(self, subject, media_type, n, det, *, entities_found, entities_masked, entities_revealed, mask_policies, ledger_before, ledger_after, ms, tool_use_id, truncated=None, would_mask=None):
        self.hop_outcomes[tool_use_id] = HopOutcome(
            outcome="ok",
            subject=subject,
            content_type=media_type,
            pages=n.pages,
            truncated=n.truncated if truncated is None else truncated,
            detector_tiers=det.tiers,
            entities_found=entities_found,
            entities_masked=entities_masked,
            entities_revealed=entities_revealed,
            mask_policies=mask_policies,
            ledger_before=ledger_before,
            ledger_after=ledger_after,
            budget=self.policy.budget_for(self.role),
            session_total=self.ledger.total(),
            latency_ms=ms,
            enforce=self.enforce,
            would_mask=dict(would_mask or {}),
        )

    def _record_withheld(self, subject, outcome, media_type, ms, *, tool_use_id):
        self.hop_outcomes[tool_use_id] = HopOutcome(
            outcome=outcome,
            subject=subject,
            content_type=media_type,
            pages=0,
            truncated=False,
            detector_tiers=[],
            entities_found={},
            entities_masked={},
            entities_revealed={},
            mask_policies={},
            ledger_before=self.ledger.seen(subject),
            ledger_after=self.ledger.seen(subject),
            budget=self.policy.budget_for(self.role),
            session_total=self.ledger.total(),
            latency_ms=ms,
            enforce=self.enforce,
        )


def _destination_hint(tool_input: dict) -> str | None:
    for key in ("to", "destination", "dest"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
    return None


def _extract_payload(content: list[dict]) -> tuple[bytes | str, str]:
    """A tool result's content list carries one of {text, json, image,
    document}. Pick the first meaningful block and normalize it to
    (payload, media_type).

    A JSON block shaped like {"filename", "media_type", "b64"} is this
    project's convention for a tool returning a binary attachment (a
    ToolResultContent has no dedicated "file" type) — decode it to raw
    bytes under its declared media type rather than treating the wrapper
    itself as the JSON payload to scan."""
    import base64

    for block in content:
        if "json" in block:
            obj = block["json"]
            if isinstance(obj, dict) and "b64" in obj and "media_type" in obj:
                return base64.b64decode(obj["b64"]), obj["media_type"]
            return json.dumps(obj), "application/json"
        if "text" in block:
            return block["text"], "text/plain"
        if "document" in block:
            doc = block["document"]
            fmt = (doc.get("format") or "pdf").lower()
            media = "application/pdf" if fmt == "pdf" else f"application/{fmt}"
            raw = doc.get("source", {}).get("bytes", b"")
            return raw, media
        if "image" in block:
            img = block["image"]
            fmt = (img.get("format") or "png").lower()
            raw = img.get("source", {}).get("bytes", b"")
            return raw, f"image/{fmt}"
    return "", "text/plain"


def _replace_content(result: dict, text: str) -> None:
    result["content"] = [{"text": text}]


def _redact(
    text: str, entities: list[detect.Entity], decisions_by_type: dict[str, "cedar_q2.FieldDecision"], *, vault: Vault
) -> tuple[str, dict[str, int], dict[str, int], dict[str, str]]:
    """Denied spans -> numbered placeholders, minted left-to-right so token
    ordinals match reading order, applied right-to-left by offset so earlier
    spans are never invalidated by a longer replacement (TD §9.2)."""
    masked: dict[str, int] = {}
    revealed: dict[str, int] = {}
    mask_policies: dict[str, str] = {}
    denied: list[detect.Entity] = []

    for e in sorted(entities, key=lambda x: x.begin):
        decision = decisions_by_type.get(e.type)
        if decision is not None and decision.allow:
            revealed[e.type] = revealed.get(e.type, 0) + 1
            continue
        denied.append(e)
        masked[e.type] = masked.get(e.type, 0) + 1
        if decision is not None and decision.policy_id:
            mask_policies[e.type] = decision.policy_id

    # Collapse overlapping denied spans before replacing anything.
    # merge() resolves exact duplicates and full containment, but leaves
    # genuine partial overlaps (e.g. 10-22 and 18-30) both standing, by
    # design. Those cannot be replaced independently: once the right-hand
    # span becomes a token, the left-hand span's [begin, end) no longer
    # addresses the original characters, and slicing it splices a fragment
    # of the token into the output. Merging each overlapping run into one
    # span — typed by its highest-rank member — makes every replacement
    # disjoint, which is the precondition the right-to-left pass assumes.
    clusters: list[tuple[int, int, str]] = []
    for e in sorted(denied, key=lambda x: (x.begin, x.end)):
        if clusters and e.begin < clusters[-1][1]:
            begin, end, etype = clusters[-1]
            best = etype if detect.rank_of(etype) >= detect.rank_of(e.type) else e.type
            clusters[-1] = (begin, max(end, e.end), best)
        else:
            clusters.append((e.begin, e.end, e.type))

    # Mint ascending (ordinals read left-to-right on screen), apply
    # descending (earlier offsets stay valid).
    to_replace = [(b, e, vault.mint(t, text[b:e]).token) for b, e, t in clusters]

    new_text = text
    for begin, end, token in sorted(to_replace, key=lambda t: t[0], reverse=True):
        new_text = new_text[:begin] + token + new_text[end:]

    return new_text, masked, revealed, mask_policies
