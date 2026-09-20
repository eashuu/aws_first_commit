"""The only module that touches `cedarpy` directly. Q1 ("may this call
happen?") is Cedar-via-Strands' `CedarAuthorization`; Q2 ("may this
principal learn this field about this subject, given the ledger?") and Q3
("may this value be restored into an outbound argument?") are Cedar-direct,
both through `is_authorized_batch` against the same policy set.

Verified live against cedarpy 4.12.0 (not just the README):
  - `is_authorized_batch(requests, policies, entities, schema=None)` accepts
    a `PolicySet` handle in place of `policies` — parse once, reuse.
  - A `Subject::"<id>"` / `Destination::"<id>"` resource UID absent from the
    entity store authorizes fine with `entities=[]` and `schema` omitted.
  - `AuthzResult.diagnostics` exposes `.reasons` (positional Cedar ids like
    "policy0") and `.id_annotations_by_reason` (reason -> its `@id`
    annotation, when one exists). The determining policy id for the audit
    row is the annotation when present, else the positional id.
"""

from __future__ import annotations

from dataclasses import dataclass

import cedarpy


@dataclass(frozen=True, slots=True)
class FieldRequest:
    subject: str
    entity_type: str


@dataclass(frozen=True, slots=True)
class FieldDecision:
    subject: str
    entity_type: str
    allow: bool
    policy_id: str | None  # the determining policy, for the audit row


def _cedar_str(s: str) -> str:
    """Escape a Python string for embedding inside a Cedar string-literal
    UID (`Type::"<escaped>"`). `principal`/`subject`/`dest` all come from
    request-controlled input (the API's `user` field, a tool argument, a
    destination string) — without this, a value containing `"` breaks out
    of the literal and corrupts the Cedar request text."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _policy_id(diagnostics) -> str | None:
    if not diagnostics.reasons:
        return None
    reason = diagnostics.reasons[0]
    return diagnostics.id_annotations_by_reason.get(reason, reason)


def authorize_fields(
    reqs: list[FieldRequest],
    *,
    principal: str,
    role: str,
    ledger,  # ledger.Ledger
    policy,  # policy.PolicyBundle
) -> list[FieldDecision]:
    """One `is_authorized_batch` call, one request per (subject, field)."""
    if not reqs:
        return []

    cedar_requests = []
    for r in reqs:
        seen = ledger.seen(r.subject)
        cedar_requests.append(
            {
                "principal": f'User::"{_cedar_str(principal)}"',
                "action": f'Action::"reveal_{r.entity_type}"',
                "resource": f'Subject::"{_cedar_str(r.subject)}"',
                "context": {
                    "session": {
                        "role": role,
                        "subject": r.subject,
                        "seen": seen,  # Cedar Set — a Python list, per subject
                        "seen_count": len(seen),  # Cedar Long — no set-cardinality op
                        "budget": policy.budget_for(role),
                    }
                },
                "correlation_id": f"{r.subject}\x00{r.entity_type}",
            }
        )

    results = cedarpy.is_authorized_batch(cedar_requests, policy.policy_set, [])
    by_correlation = {res.correlation_id: res for res in results if res.correlation_id is not None}

    decisions: list[FieldDecision] = []
    for r in reqs:
        cid = f"{r.subject}\x00{r.entity_type}"
        result = by_correlation.get(cid)
        if result is None:
            # A field we could not decide on is a field we redact (TD §9.5) —
            # default deny, never trust result ordering over correlation_id.
            decisions.append(FieldDecision(r.subject, r.entity_type, False, None))
            continue
        allow = result.decision == cedarpy.Decision.Allow and result.allowed
        decisions.append(FieldDecision(r.subject, r.entity_type, allow, _policy_id(result.diagnostics)))
    return decisions


def authorize_call(tool_name: str, *, principal: str, role: str, resource: str, policy):
    """Q1: may this tool invocation happen at all?

    On the agent path this question is asked by Strands' `CedarAuthorization`
    intervention, which builds the request itself. The scripted demo driver
    has no Strands agent and therefore no intervention chain, so it asks the
    same question here against the same policy set.

    The request shape mirrors what `CedarAuthorization` produces, and it has
    to keep mirroring it: `Action::"<tool_name>"` with the session role in
    context is what every `q1_*` permit in agent.cedar matches on. If those
    two ever drift, the demo path and the agent path stop agreeing about
    what is allowed — which is a worse failure than either being wrong,
    because only one of them is the one anybody watches.

    Returns (allow, policy_id).
    """
    req = {
        "principal": f'User::"{_cedar_str(principal)}"',
        "action": f'Action::"{_cedar_str(tool_name)}"',
        "resource": f'Resource::"{_cedar_str(resource)}"',
        "context": {"session": {"role": role}},
        "correlation_id": tool_name,
    }
    results = cedarpy.is_authorized_batch([req], policy.policy_set, [])
    if not results:
        # No decision is not an allow. Cedar returning nothing here would be
        # a library-level surprise, and the fail-closed default is the whole
        # posture of the product.
        return False, None
    result = results[0]
    allow = result.decision == cedarpy.Decision.Allow and result.allowed
    return allow, _policy_id(result.diagnostics)


def authorize_rehydration(
    entity_types: list[str], *, principal: str, role: str, dest: str, policy
) -> dict[str, bool]:
    """PRD §11.2 Must #5: rehydration is itself a Cedar question against the
    destination as resource, not a blanket substitution — this is what stops
    an authorized-but-compromised call from using the guardrail as an
    exfiltration channel. One request per distinct entity type present among
    the placeholders this tool call is trying to resolve."""
    if not entity_types:
        return {}

    reqs = [
        {
            "principal": f'User::"{_cedar_str(principal)}"',
            "action": f'Action::"rehydrate_{et}"',
            "resource": f'Destination::"{_cedar_str(dest)}"',
            "context": {"session": {"role": role}},
            "correlation_id": et,
        }
        for et in sorted(set(entity_types))
    ]
    results = cedarpy.is_authorized_batch(reqs, policy.policy_set, [])
    return {
        res.correlation_id: (res.decision == cedarpy.Decision.Allow and res.allowed)
        for res in results
        if res.correlation_id is not None
    }
