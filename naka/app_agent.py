"""Data-plane Function URL handler + agent assembly.

Wiring order is the design (PRD §5): DisclosureGuard first (stashes the
call-scoped subject before anything else runs), CedarAuthorization second
(Q1 — a Deny here skips the Rehydrator entirely, so a denied call never gets
plaintext substituted into its arguments), Rehydrator third (Q3, and only
after Cedar has already allowed the call to happen).
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from strands import Agent
from strands.session import S3SessionManager
from strands.vended_interventions.cedar import CedarAuthorization

import audit
import ledger as ledger_mod
import policy
import tools
from config import CFG
from guard import DisclosureGuard
from rehydrate import Rehydrator, Vault

VALID_ROLES = {"analyst", "compliance"}


def build_agent(
    *,
    session_id: str,
    principal: str,
    role: str,
    vault: Vault,
    ledger: ledger_mod.Ledger,
    policy_bundle,
    invocation_id: str,
    enforce: bool = True,
) -> tuple[Agent, "audit.AuditHook"]:
    guard = DisclosureGuard(
        session_id=session_id,
        principal=principal,
        role=role,
        vault=vault,
        ledger=ledger,
        policy=policy_bundle,
        cfg=CFG,
        enforce=enforce,
    )

    with open(CFG.policy_path, "w", encoding="utf-8") as f:
        f.write(policy_bundle.cedar)

    cedar = CedarAuthorization(
        policies=CFG.policy_path,
        entities=policy_bundle.entities,
        principal_resolver=lambda st: {"type": "User", "id": st["user"]},
        context_enricher=guard.snapshot,  # the handler instance, not invocation_state
        on_error="deny",
        # schema deliberately omitted — PRD §2.1: a schema present can fail
        # validation on custom context.session attributes.
    )

    rehydrator = Rehydrator(vault=vault, principal=principal, role=role, policy=policy_bundle)

    audit_hook = audit.AuditHook(
        session_id=session_id,
        principal=principal,
        role=role,
        invocation_id=invocation_id,
        guard=guard,
        policy=policy_bundle,
        cfg=CFG,
        rehydrator=rehydrator,
    )

    agent = Agent(
        model=CFG.model_id,
        tools=list(tools.TOOL_FUNCTIONS),
        interventions=[guard, cedar, rehydrator],
        hooks=[audit_hook],
        session_manager=S3SessionManager(
            session_id=session_id, bucket=CFG.session_bucket, prefix=CFG.session_prefix
        ),
    )
    return agent, audit_hook


def _now_trace_id(context: Any) -> str:
    return getattr(context, "aws_request_id", None) or str(uuid.uuid4())


def _parse_body(event: dict) -> dict:
    raw = event.get("body")
    if raw is None:
        raise ValueError("empty request body")
    if event.get("isBase64Encoded"):
        import base64

        raw = base64.b64decode(raw).decode("utf-8")
    try:
        body = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"body is not valid JSON: {exc}") from exc
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")
    return body


def _header(event: dict, name: str) -> str | None:
    """Case-insensitive header lookup. Function URLs lower-case header names
    in the event, but nothing in the contract promises that, so match the way
    HTTP actually defines it rather than trusting the casing we happen to
    receive."""
    headers = event.get("headers") or {}
    lname = name.lower()
    for k, v in headers.items():
        if k.lower() == lname:
            return v
    return None


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _error(status: int, code: str, message: str, trace_id: str) -> dict:
    return _response(status, {"error": {"code": code, "message": message, "trace_id": trace_id}})


def _call_summary(row: "audit.AuditRow") -> dict:
    return {
        "seq": row.seq,
        "tool": row.tool,
        "decision": row.call_decision,
        "deny_policy": row.deny_policy,
        "subject": row.subject,
        "entities_found": row.entities_found,
        "entities_masked": row.entities_masked,
        "entities_revealed": row.entities_revealed,
        "ledger_after": row.ledger_after,
        "budget": row.budget,
        "outcome": row.outcome,
        "latency_ms": row.latency_ms,
        "enforce": row.enforce,
        "would_mask": row.would_mask,
    }


def _route_demo(body: dict, trace_id: str) -> dict:
    """Run a scripted scenario through the real guardrail. No model, so this
    works while Bedrock is gated — see demo.py for exactly what stays real.

    Unauthenticated on purpose: it runs a fixed sequence against fixture
    data and cannot be pointed at anything else, so there is nothing here an
    arbitrary caller could use that `POST /` would not already allow them.
    The scenario name is checked against a whitelist rather than used to
    look anything up."""
    import demo

    scenario = body.get("scenario")
    if scenario not in demo.SCENARIOS:
        return _error(
            400, "BAD_REQUEST", f"unknown scenario; expected one of {sorted(demo.SCENARIOS)}", trace_id
        )

    role = body.get("role", "analyst")
    if role not in VALID_ROLES:
        return _error(400, "BAD_REQUEST", f"unknown role '{role}'", trace_id)

    session_id = body.get("session_id") or str(uuid.uuid4())
    principal = body.get("user") or "anonymous@example.com"
    if not isinstance(principal, str) or '"' in principal:
        return _error(400, "BAD_REQUEST", "'user' must not contain a double-quote character", trace_id)

    try:
        policy_bundle = policy.refresh(cfg=CFG)
    except Exception as exc:  # noqa: BLE001
        return _error(503, "POLICY_UNAVAILABLE", type(exc).__name__, trace_id)

    try:
        ledger = ledger_mod.load(
            session_id,
            cfg=CFG,
            budget=policy_bundle.budget_for(role),
            session_ceiling=policy_bundle.session_ceiling,
        )
    except ledger_mod.LedgerUnavailable as exc:
        return _error(503, "LEDGER_UNAVAILABLE", str(exc), trace_id)

    try:
        out = demo.run_scenario(
            scenario,
            session_id=session_id,
            principal=principal,
            role=role,
            policy_bundle=policy_bundle,
            ledger=ledger,
            invocation_id=trace_id,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(500, "INTERNAL", f"{type(exc).__name__}: {exc}", trace_id)

    out.update({"session_id": session_id, "policy_version": policy_bundle.version, "trace_id": trace_id})
    return _response(200, out)


def lambda_handler(event: dict, context: Any) -> dict:
    trace_id = _now_trace_id(context)

    if event.get("requestContext", {}).get("http", {}).get("method") == "GET" and event.get("rawPath", "/") == "/health":
        try:
            bundle = policy.current(CFG)
            return _response(200, {"ok": True, "policy_version": bundle.version, "policy_source": bundle.source})
        except Exception as exc:  # noqa: BLE001
            return _response(503, {"ok": False, "error": type(exc).__name__})

    try:
        body = _parse_body(event)
    except ValueError as exc:
        return _error(400, "BAD_REQUEST", str(exc), trace_id)

    raw_body_len = len(event.get("body") or "")
    if raw_body_len > CFG.max_request_bytes:
        return _error(413, "PAYLOAD_TOO_LARGE", "request exceeds MAX_REQUEST_BYTES", trace_id)

    if event.get("rawPath", "/") == "/demo":
        return _route_demo(body, trace_id)

    prompt = body.get("prompt")
    if not prompt or not isinstance(prompt, str):
        return _error(400, "BAD_REQUEST", "'prompt' is required and must be a string", trace_id)

    role = body.get("role", "analyst")
    if role not in VALID_ROLES:
        return _error(400, "BAD_REQUEST", f"unknown role '{role}'; expected one of {sorted(VALID_ROLES)}", trace_id)

    # Shadow mode. Absent means enforce -- a client that forgets the field,
    # or an old client that has never heard of it, must get the protecting
    # behaviour. Only an explicit `false` turns enforcement off, and a
    # non-boolean is rejected rather than coerced, because `"false"` from a
    # hand-written curl is truthy in Python and would silently enforce when
    # the caller asked for a measurement run.
    enforce = body.get("enforce", True)
    if not isinstance(enforce, bool):
        return _error(400, "BAD_REQUEST", "'enforce' must be a boolean (true/false)", trace_id)

    # Turning enforcement OFF requires the operator key, because this
    # Function URL is AuthType=NONE -- public, unauthenticated, by design, so
    # judges can open it. Without this check, `{"enforce": false}` from any
    # caller on the internet is an off-switch for the entire guardrail, which
    # is the one thing this system exists to make impossible. Measuring what
    # a control would have blocked is an operator action, not a caller's
    # choice. Enforcing (the default) needs no key: the protective path must
    # never depend on a secret being present.
    if not enforce:
        if not CFG.naka_key:
            return _error(403, "SHADOW_MODE_UNAVAILABLE", "shadow mode requires NAKA_KEY to be configured", trace_id)
        if _header(event, "X-Naka-Key") != CFG.naka_key:
            return _error(401, "BAD_KEY", "'enforce: false' requires a valid X-Naka-Key header", trace_id)

    session_id = body.get("session_id") or str(uuid.uuid4())
    principal = body.get("user") or "anonymous@example.com"
    if not isinstance(principal, str) or '"' in principal:
        # cedar_q2.py escapes this before building a Cedar UID literal, but
        # rejecting it at the boundary is cheaper and clearer than trusting
        # every internal interpolation site to have done so correctly.
        return _error(400, "BAD_REQUEST", "'user' must not contain a double-quote character", trace_id)

    try:
        policy_bundle = policy.refresh(cfg=CFG)  # top-of-request only, never mid-turn
    except Exception as exc:  # noqa: BLE001
        return _error(503, "POLICY_UNAVAILABLE", type(exc).__name__, trace_id)

    try:
        ledger = ledger_mod.load(
            session_id,
            cfg=CFG,
            budget=policy_bundle.budget_for(role),
            session_ceiling=policy_bundle.session_ceiling,
        )
    except ledger_mod.LedgerUnavailable as exc:
        return _error(503, "LEDGER_UNAVAILABLE", str(exc), trace_id)

    vault = Vault()

    try:
        try:
            agent, audit_hook = build_agent(
                session_id=session_id,
                principal=principal,
                role=role,
                vault=vault,
                ledger=ledger,
                policy_bundle=policy_bundle,
                invocation_id=trace_id,
                enforce=enforce,
            )

            # Merge the cached ledger from a restored session on top of the
            # DynamoDB-authoritative one — union is safe (§6), and DynamoDB
            # wins on anything the cache dropped. A malformed cached state
            # must not crash the request — it is a cache, not the authority.
            cached = agent.state.get("disclosure_ledger")
            if cached:
                ledger.merge(
                    ledger_mod.Ledger.from_state(
                        cached, session_id=session_id, budget=ledger.budget, session_ceiling=ledger.session_ceiling
                    )
                )
        except Exception as exc:  # noqa: BLE001
            return _error(500, "INTERNAL", type(exc).__name__, trace_id)

        try:
            result = agent(prompt, user=principal, role=role)
        except Exception as exc:  # noqa: BLE001
            return _error(503, "MODEL_UNAVAILABLE", type(exc).__name__, trace_id)
    finally:
        vault.clear()  # never survives past this invocation, success or not

    calls = [_call_summary(r) for r in audit_hook.rows]

    return _response(
        200,
        {
            "session_id": session_id,
            "reply": str(result),
            "calls": calls,
            "enforce": enforce,
            # A shadow run deliberately never calls ledger.spend(), so the
            # accumulation it reports is in-memory only. Saying so in the
            # response stops a dashboard presenting a measurement run's
            # totals as though they were persisted session state.
            "ledger_persisted": enforce,
            "policy_version": policy_bundle.version,
            "trace_id": trace_id,
        },
    )
