"""The audit writer. One DynamoDB item per tool call, written from a hook
rather than an intervention so it never blocks the decision path.

Binds BOTH BeforeToolCallEvent and AfterToolCallEvent (PRD §10) — a call
denied at Q1 short-circuits and never reaches after_tool_call, so an
after-only hook silently omits every denial, which is exactly the evidence
the audit trail exists to produce.

The order matters and is not the default. Verified against the actual
InterventionRegistry source: interventions run `before_tool_call` at
`HookOrder.INTERVENTION_INPUT` (90) but `after_tool_call` at
`HookOrder.INTERVENTION_OUTPUT` (-90) — lower runs first. So a hook
registered at the default order (0) on BeforeToolCallEvent fires BEFORE
interventions decide anything (it would never see a denial), while the same
default order on AfterToolCallEvent fires AFTER them (correctly observing
the already-redacted result). The before-hook here is therefore registered
at `HookOrder.SDK_LAST` (100) so it always runs last and can read
`event.cancel_tool`, which the registry sets to `f"DENIED: {reason}"` when
an intervention returns `Deny`.
"""

from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from strands.hooks.events import AfterToolCallEvent, BeforeToolCallEvent
from strands.hooks.registry import HookOrder, HookProvider, HookRegistry

import attribute
from config import Config
from guard import DisclosureGuard


@dataclass(frozen=True, slots=True)
class AuditRow:
    session_id: str
    seq: int
    ts: str
    invocation_id: str
    principal: str
    role: str
    subject: str
    tool: str
    call_decision: str  # "ALLOW" | "DENY"
    deny_policy: str | None  # Q1 only — the determining policy id, or None
    content_type: str
    pages: int
    truncated: bool
    detector_tiers: list[str]
    entities_found: dict[str, int]
    entities_masked: dict[str, int]
    entities_revealed: dict[str, int]
    mask_policies: dict[str, str]  # entity type -> the Q2 policy id that masked it
    ledger_before: list[str]
    ledger_after: list[str]
    budget: int
    session_total: int
    rehydrated: list[str]  # token strings only, never values
    outcome: str
    latency_ms: dict[str, int]
    policy_version: str
    # Shadow mode. `enforce=False` means the row records a decision that was
    # made but not applied, and `would_mask` carries what the guard WOULD
    # have masked. Both default so every existing construction site stays
    # valid and an enforced row reads exactly as it did before.
    enforce: bool = True
    would_mask: dict[str, int] = field(default_factory=dict)
    # Detector tiers that could not run for this call. An empty list means
    # the full pipeline ran; a non-empty one means this row describes a
    # NARROWER scan, and no reader may treat its zero-findings as clean.
    tiers_unavailable: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_cancel_reason(cancel_tool) -> tuple[str, str | None, str]:
    """cancel_tool is `f"DENIED: {reason}"` (set by the intervention
    registry). Returns (outcome, deny_policy, human_reason)."""
    text = cancel_tool if isinstance(cancel_tool, str) else "DENIED"
    reason = text.split(":", 1)[1].strip() if ":" in text else text

    if "Access denied by Cedar policy" in reason:
        # CedarAuthorization's own Deny message lists cedarpy's raw
        # positional reasons (e.g. "policy0"), not the @id annotation —
        # verified against the SDK source, which never resolves annotations
        # for this message. Best available without a duplicate Q1 call.
        tail = reason.split(":", 1)[1].strip() if ":" in reason else None
        return "denied_call", tail, reason
    if "Placeholder" in reason or "Restoring a" in reason:
        return "denied_placeholder", None, reason
    return "denied_call", None, reason


class AuditHook(HookProvider):
    def __init__(
        self,
        *,
        session_id: str,
        principal: str,
        role: str,
        invocation_id: str,
        guard: DisclosureGuard,
        policy,  # policy.PolicyBundle
        cfg: Config,
        rehydrator=None,  # rehydrate.Rehydrator — for AuditRow.rehydrated
    ) -> None:
        self.session_id = session_id
        self.principal = principal
        self.role = role
        self.invocation_id = invocation_id
        self.guard = guard
        self.policy = policy
        self.cfg = cfg
        self.rehydrator = rehydrator
        self._seq = itertools.count(1)
        self.rows: list[AuditRow] = []  # kept for app_agent.py's response summary

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self._on_before_tool_call, order=HookOrder.SDK_LAST)
        registry.add_callback(AfterToolCallEvent, self._on_after_tool_call)

    def _on_before_tool_call(self, event: BeforeToolCallEvent) -> None:
        if not event.cancel_tool:
            return  # call proceeded — the after-hook logs it, not this one
        outcome, deny_policy, reason = _parse_cancel_reason(event.cancel_tool)
        tool_input = event.tool_use.get("input") or {}
        subject = attribute.canonical_subject(
            attribute.subject_key(tool_input) if isinstance(tool_input, dict) else None,
            session_id=self.session_id,
        )
        row = AuditRow(
            session_id=self.session_id,
            seq=next(self._seq),
            ts=_now_iso(),
            invocation_id=self.invocation_id,
            principal=self.principal,
            role=self.role,
            subject=subject,
            tool=event.tool_use.get("name", ""),
            call_decision="DENY",
            deny_policy=deny_policy,
            content_type="",
            pages=0,
            truncated=False,
            detector_tiers=[],
            entities_found={},
            entities_masked={},
            entities_revealed={},
            mask_policies={},
            ledger_before=[],
            ledger_after=[],
            budget=self.policy.budget_for(self.role),
            session_total=self.guard.ledger.total(),
            rehydrated=[],
            outcome=outcome,
            latency_ms={},
            policy_version=self.policy.version,
            enforce=self.guard.enforce,
        )
        self.rows.append(row)
        put_row(row, cfg=self.cfg)

    def _on_after_tool_call(self, event: AfterToolCallEvent) -> None:
        tool_use_id = event.tool_use.get("toolUseId") or ""
        hop = self.guard.hop_outcomes.pop(tool_use_id, None)
        if hop is None:
            return  # e.g. a tool error result — nothing was scanned
        rehydrated: list[str] = []
        if self.rehydrator is not None:
            rehydrated = self.rehydrator.resolved_by_call.pop(tool_use_id, [])
        row = AuditRow(
            session_id=self.session_id,
            seq=next(self._seq),
            ts=_now_iso(),
            invocation_id=self.invocation_id,
            principal=self.principal,
            role=self.role,
            subject=hop.subject,
            tool=event.tool_use.get("name", ""),
            call_decision="ALLOW",
            deny_policy=None,
            content_type=hop.content_type,
            pages=hop.pages,
            truncated=hop.truncated,
            detector_tiers=hop.detector_tiers,
            entities_found=hop.entities_found,
            entities_masked=hop.entities_masked,
            entities_revealed=hop.entities_revealed,
            mask_policies=hop.mask_policies,
            ledger_before=hop.ledger_before,
            ledger_after=hop.ledger_after,
            budget=hop.budget,
            session_total=hop.session_total,
            rehydrated=rehydrated,
            outcome=hop.outcome,
            latency_ms=hop.latency_ms,
            policy_version=self.policy.version,
            enforce=hop.enforce,
            would_mask=hop.would_mask,
            tiers_unavailable=hop.tiers_unavailable,
        )
        self.rows.append(row)
        put_row(row, cfg=self.cfg)


_ddb_client_cache: dict[str, object] = {}


def _ddb_client(cfg: Config):
    client = _ddb_client_cache.get("client")
    if client is not None:
        return client
    import boto3
    from botocore.config import Config as BotoConfig

    client = boto3.client(
        "dynamodb",
        region_name=cfg.aws_region,
        config=BotoConfig(connect_timeout=1, read_timeout=cfg.timeout_ddb_s, retries={"max_attempts": 1, "mode": "standard"}),
    )
    _ddb_client_cache["client"] = client
    return client


def _to_ddb_map(d: dict) -> dict:
    """A dict[str, int] or dict[str, str] -> a DynamoDB M of N/S. Only ever
    called on `AuditRow` fields, which are structurally counts and ids —
    never entity values (§3.5)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, bool):
            out[k] = {"BOOL": v}
        elif isinstance(v, (int, float)):
            out[k] = {"N": str(v)}
        else:
            out[k] = {"S": str(v)}
    return {"M": out}


def _row_to_item(row: AuditRow, *, cfg: Config) -> dict:
    ts_compact = row.ts.replace(":", "").replace("-", "").replace(".", "")
    date_part = row.ts[:10]
    expires_at = int((datetime.now(timezone.utc) + timedelta(days=cfg.audit_ttl_days)).timestamp())
    item = {
        "pk": {"S": f"SESSION#{row.session_id}"},
        "sk": {"S": f"CALL#{row.ts}#{row.seq:04d}"},
        "gsi1pk": {"S": f"FEED#{date_part}"},
        "gsi1sk": {"S": f"{row.ts}#{row.seq:04d}"},
        "ts": {"S": row.ts},
        "seq": {"N": str(row.seq)},
        "invocation_id": {"S": row.invocation_id},
        "principal": {"S": row.principal},
        "role": {"S": row.role},
        "subject": {"S": row.subject},
        "tool": {"S": row.tool},
        "call_decision": {"S": row.call_decision},
        "content_type": {"S": row.content_type},
        "pages": {"N": str(row.pages)},
        "truncated": {"BOOL": row.truncated},
        "detector_tiers": {"SS": row.detector_tiers} if row.detector_tiers else {"L": []},
        "entities_found": _to_ddb_map(row.entities_found),
        "entities_masked": _to_ddb_map(row.entities_masked),
        "entities_revealed": _to_ddb_map(row.entities_revealed),
        "mask_policies": _to_ddb_map(row.mask_policies),
        "ledger_before": {"SS": row.ledger_before} if row.ledger_before else {"L": []},
        "ledger_after": {"SS": row.ledger_after} if row.ledger_after else {"L": []},
        "budget": {"N": str(row.budget)},
        "session_total": {"N": str(row.session_total)},
        "rehydrated": {"SS": row.rehydrated} if row.rehydrated else {"L": []},
        "outcome": {"S": row.outcome},
        "latency_ms": _to_ddb_map(row.latency_ms),
        "policy_version": {"S": row.policy_version},
        # `enforce` is written on every row, not only shadow ones: a query
        # that filters for enforced rows must not have to treat "attribute
        # absent" as "enforced", which would silently include shadow rows
        # written by an older build.
        "enforce": {"BOOL": row.enforce},
        "would_mask": _to_ddb_map(row.would_mask),
        "tiers_unavailable": {"SS": row.tiers_unavailable} if row.tiers_unavailable else {"L": []},
        "expires_at": {"N": str(expires_at)},
    }
    if row.deny_policy:
        item["deny_policy"] = {"S": row.deny_policy}
    return item


def put_row(row: AuditRow, *, cfg: Config) -> None:
    """The only fail-open path in the system (TD §5.1) — a failed audit
    write must never withhold a result that policy already cleared."""
    try:
        client = _ddb_client(cfg)
        client.put_item(TableName=cfg.audit_table, Item=_row_to_item(row, cfg=cfg))
    except Exception:  # noqa: BLE001
        import json as _json
        import sys

        print(_json.dumps({"evt": "audit_write_fail", "session_id": row.session_id, "seq": row.seq}), file=sys.stderr)
