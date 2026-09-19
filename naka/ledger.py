"""The disclosure ledger: a grow-only set (G-Set) per (session_id, subject_id).

It only ever gains entity *types* — never removes, never counts values,
never stores offsets. That single property removes locking, ordering and
conflict resolution from the whole system (TD §6): merge is set union,
which is commutative, associative and idempotent, so the worst possible
error from a lost or duplicated update is over-counting — a subject reading
as more disclosed than it is, which fails in the safe direction.

DynamoDB is authoritative. `agent.state` (via S3SessionManager) is a cache
only — the session managers take no distributed lock (verified against the
Strands session docs) and can silently lose a concurrent write. A DynamoDB
`ADD` on a String Set is a server-side atomic union and cannot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from config import Config

SubjectId = str
EntityType = str


class LedgerUnavailable(Exception):
    """The ledger could not be read or written. The caller MUST fail closed:
    a ledger defaulting to empty on read failure IS the bypass — every
    session would start with a full budget."""


@dataclass
class Ledger:
    session_id: str
    subjects: dict[SubjectId, set[EntityType]] = field(default_factory=dict)
    budget: int = 3
    session_ceiling: int = 25

    def seen(self, subject: SubjectId) -> list[str]:
        return sorted(self.subjects.get(subject, set()))

    def count(self, subject: SubjectId) -> int:
        return len(self.subjects.get(subject, set()))

    def total(self) -> int:
        return sum(len(types) for types in self.subjects.values())

    def merge(self, other: "Ledger") -> None:
        """Union; monotone, commutative, idempotent."""
        for subject, types in other.subjects.items():
            self.subjects.setdefault(subject, set()).update(types)

    def add(self, subject: SubjectId, types: Iterable[EntityType]) -> None:
        types = set(types)
        if not types:
            return
        self.subjects.setdefault(subject, set()).update(types)

    def to_state(self) -> dict:
        return {
            "v": 1,
            "session_id": self.session_id,
            "budget": self.budget,
            "session_ceiling": self.session_ceiling,
            "subjects": {s: sorted(t) for s, t in self.subjects.items()},
        }

    @classmethod
    def from_state(
        cls, d: dict | None, *, session_id: str, budget: int, session_ceiling: int
    ) -> "Ledger":
        if not d:
            return cls(session_id=session_id, subjects={}, budget=budget, session_ceiling=session_ceiling)
        subjects = {s: set(v) for s, v in d.get("subjects", {}).items()}
        return cls(
            session_id=session_id,
            subjects=subjects,
            budget=d.get("budget", budget),
            session_ceiling=d.get("session_ceiling", session_ceiling),
        )


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
        config=BotoConfig(
            connect_timeout=1,
            read_timeout=cfg.timeout_ddb_s,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )
    _ddb_client_cache["client"] = client
    return client


def load(session_id: str, *, cfg: Config, budget: int, session_ceiling: int, client=None) -> Ledger:
    """Query pk=SESSION#<id>, sk begins_with 'METER#', ConsistentRead=True.
    Raises LedgerUnavailable on any failure — the caller MUST fail closed.
    An empty (but successful) query is a new session, not an error."""
    client = client or _ddb_client(cfg)
    try:
        resp = client.query(
            TableName=cfg.audit_table,
            KeyConditionExpression="pk = :pk AND begins_with(sk, :pfx)",
            ExpressionAttributeValues={
                ":pk": {"S": f"SESSION#{session_id}"},
                ":pfx": {"S": "METER#"},
            },
            ConsistentRead=True,
        )
    except Exception as exc:  # noqa: BLE001
        raise LedgerUnavailable(type(exc).__name__) from exc

    subjects: dict[SubjectId, set[EntityType]] = {}
    for item in resp.get("Items", []):
        sk = item.get("sk", {}).get("S", "")
        if not sk.startswith("METER#"):
            continue
        subject = sk[len("METER#") :]
        seen = item.get("seen", {}).get("SS")
        if seen is None:
            raise LedgerUnavailable(f"meter item {sk} missing 'seen' string set")
        subjects[subject] = set(seen)

    return Ledger(session_id=session_id, subjects=subjects, budget=budget, session_ceiling=session_ceiling)


def spend(
    session_id: str, subject: SubjectId, types: set[EntityType], *, cfg: Config, client=None
) -> tuple[list[str], list[str]]:
    """Atomic set-union on the meter row. Returns (before, after) as sorted
    lists. One round trip, no read-modify-write, no lost update.

    Never call with an empty `types` — DynamoDB rejects empty sets, and this
    is a no-op by definition: nothing was revealed, so nothing is spent."""
    if not types:
        return [], []

    client = client or _ddb_client(cfg)
    now = datetime.now(timezone.utc)
    ts = now.isoformat()
    expires_at = int((now + timedelta(days=cfg.audit_ttl_days)).timestamp())

    try:
        resp = client.update_item(
            TableName=cfg.audit_table,
            Key={"pk": {"S": f"SESSION#{session_id}"}, "sk": {"S": f"METER#{subject}"}},
            UpdateExpression="SET last_ts = :ts, expires_at = :e, first_ts = if_not_exists(first_ts, :ts) ADD seen :t",
            ExpressionAttributeValues={
                ":t": {"SS": sorted(types)},
                ":ts": {"S": ts},
                ":e": {"N": str(expires_at)},
            },
            ReturnValues="ALL_OLD",
        )
    except Exception as exc:  # noqa: BLE001
        raise LedgerUnavailable(type(exc).__name__) from exc

    old_seen: set[str] = set()
    attrs = resp.get("Attributes")
    if attrs and "seen" in attrs:
        old_seen = set(attrs["seen"].get("SS", []))

    before = sorted(old_seen)
    after = sorted(old_seen | set(types))
    return before, after
