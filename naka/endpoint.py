"""Endpoint plane control surface — enrolment and decision telemetry.

WHY THIS FILE EXISTS, and what it deliberately does not do.

The endpoint DLP agent runs on a laptop. It cannot run on AWS and it is not
supposed to: its entire value is that it sees a paste into a consumer AI
tool from a machine at home, on the employee's own connection, where no
corporate network exists to intercept. Hosting it on Fargate would make it
see nothing. (The overlay is WPF and would not start in a Linux container
either, and the proxy's root-CA interception would capture only its own
loopback.)

What belongs on AWS is the agent's CONTROL PLANE — the part that knows
which devices exist and what they decided. That is this module. It closes
the gap the console previously reported honestly as "no endpoints are
reporting to this control plane": that message was true, and it was true
because this file did not exist.

Item shapes, in the same `naka_audit` table as the other two planes, which
is what makes the one-platform claim real rather than a diagram:

    device  pk = ENDPOINT#DEVICES       sk = DEVICE#<device_id>
    event   pk = ENDPOINT#<device_id>   sk = EVENT#<iso-ts>#<seq>

Every device sits in ONE partition on purpose. The first cut keyed devices
by `ENDPOINT#<device_id>` and read the fleet with a Scan, which was wrong
twice over: a Scan against a table that also holds every audit row gets
more expensive with traffic that has nothing to do with endpoints, and the
Lambda role does not grant `dynamodb:Scan` anyway — correctly, because
nothing in this system should need it. Devices in a shared partition make
the fleet read a single Query, and each device's events are a Query on that
device's own partition, newest-first with a limit.

THE INVARIANT THAT CARRIES OVER FROM THE OTHER PLANES:
an event row records entity TYPES and COUNTS, never a value. A device
reports "2 IN_AADHAAR found, 2 withheld" and nothing that could reconstruct
the number. There is no field on the ingest schema that could carry one, and
`_clean_counts` drops anything that is not a non-negative integer count — so
an agent that tried to send a plaintext value would have it discarded rather
than persisted. That check is not paranoia about our own agent; it is what
makes the table safe to keep when a third party writes to it.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone

# Entity types a device is allowed to report counts for. An unknown type is
# dropped rather than stored: the console renders these verbatim, and an
# endpoint is the least trusted writer in the system.
_ALLOWED_TYPES = frozenset(
    {
        "IN_AADHAAR", "IN_PERMANENT_ACCOUNT_NUMBER", "IN_GSTIN", "IN_IFSC",
        "IN_VOTER_NUMBER", "IN_NREGA", "NAME", "EMAIL", "PHONE", "ADDRESS",
        "DATE_TIME", "AGE", "CREDIT_DEBIT_NUMBER", "BANK_ACCOUNT_NUMBER",
        "PASSPORT_NUMBER", "DRIVER_ID", "OTHER",
    }
)

_ALLOWED_ACTIONS = frozenset({"paste", "upload", "prompt", "download", "screenshot"})
_ALLOWED_DECISIONS = frozenset({"allow", "block", "warn"})

# The single partition every enrolled device lives in, so listing the fleet
# is one Query rather than a Scan. See the module docstring.
_DEVICE_PK = "ENDPOINT#DEVICES"


def _device_key(device_id: str) -> dict:
    return {"pk": {"S": _DEVICE_PK}, "sk": {"S": f"DEVICE#{device_id}"}}

# A device that has not checked in for this long is shown as stale rather
# than live. Nothing expires it; an operator needs to see that a machine
# went quiet, which is exactly the signal an auto-removing fleet list hides.
STALE_AFTER_S = 300


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _clean_counts(raw) -> dict[str, int]:
    """Types and counts only. Anything else is dropped, not stored."""
    out: dict[str, int] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if k not in _ALLOWED_TYPES:
            continue
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n < 0:
            continue
        out[k] = n
    return out


def _s(v, limit=200) -> str:
    return str(v)[:limit] if v is not None else ""


# ---------------------------------------------------------------------------
# Enrolment
# ---------------------------------------------------------------------------


def enroll(payload: dict, *, table: str, ddb) -> tuple[int, dict]:
    """Register a device and mint its reporting credential.

    Called with the operator's X-Naka-Key (checked by the caller). Returns a
    device_id and a one-time token; only the token's SHA-256 is stored, so a
    dump of the table does not yield working device credentials.
    """
    device_id = "dev_" + secrets.token_hex(6)
    token = secrets.token_urlsafe(32)

    ddb.put_item(
        TableName=table,
        Item={
            **_device_key(device_id),
            "device_id": {"S": device_id},
            "token_hash": {"S": _token_hash(token)},
            "hostname": {"S": _s(payload.get("hostname"), 120)},
            "os": {"S": _s(payload.get("os"), 60)},
            "principal": {"S": _s(payload.get("user"), 200)},
            "agent_version": {"S": _s(payload.get("agent_version"), 40)},
            "enrolled_at": {"S": _now_iso()},
            "last_seen": {"S": _now_iso()},
            "events": {"N": "0"},
        },
    )
    # The token is returned exactly once, here. There is no route that can
    # read it back, because a credential an API will re-issue on request is
    # not a credential.
    return 200, {"device_id": device_id, "device_token": token, "enrolled_at": _now_iso()}


def _authenticate(device_header: str | None, *, table: str, ddb):
    """`X-Naka-Device: <device_id>:<token>` -> the device item, or None."""
    if not device_header or ":" not in device_header:
        return None
    device_id, _, token = device_header.partition(":")
    if not device_id.startswith("dev_"):
        return None
    resp = ddb.get_item(TableName=table, Key=_device_key(device_id))
    item = resp.get("Item")
    if not item:
        return None
    stored = item.get("token_hash", {}).get("S", "")
    # compare_digest, not ==, so a wrong token cannot be recovered one
    # character at a time from response timing.
    if not stored or not hmac.compare_digest(stored, _token_hash(token)):
        return None
    return item


# ---------------------------------------------------------------------------
# Event ingest
# ---------------------------------------------------------------------------


def ingest(payload: dict, *, device_header: str | None, table: str, ddb) -> tuple[int, dict]:
    device = _authenticate(device_header, table=table, ddb=ddb)
    if device is None:
        # Deliberately does not distinguish "no such device" from "wrong
        # token": both are 401 with one message, so the route cannot be used
        # to enumerate which device ids exist.
        return 401, {"error": {"code": "BAD_DEVICE", "message": "unknown device or token", "trace_id": ""}}

    device_id = device["device_id"]["S"]

    action = _s(payload.get("action"), 32)
    if action not in _ALLOWED_ACTIONS:
        return 400, {"error": {"code": "BAD_ACTION", "message": f"action must be one of {sorted(_ALLOWED_ACTIONS)}", "trace_id": ""}}

    decision = _s(payload.get("decision"), 16)
    if decision not in _ALLOWED_DECISIONS:
        return 400, {"error": {"code": "BAD_DECISION", "message": f"decision must be one of {sorted(_ALLOWED_DECISIONS)}", "trace_id": ""}}

    found = _clean_counts(payload.get("entities_found"))
    masked = _clean_counts(payload.get("entities_masked"))
    tiers = [t for t in (payload.get("detector_tiers") or []) if isinstance(t, str)][:8]

    ts = _now_iso()
    # The counter is incremented first and its post-write value used as the
    # event's sequence number, so two events arriving in the same ISO
    # millisecond still get distinct sort keys instead of overwriting each
    # other. Same reasoning as the disclosure ledger's atomic ADD.
    bump = ddb.update_item(
        TableName=table,
        Key=_device_key(device_id),
        UpdateExpression="SET last_seen = :ts ADD events :one",
        ExpressionAttributeValues={":ts": {"S": ts}, ":one": {"N": "1"}},
        ReturnValues="UPDATED_NEW",
    )
    seq = int(bump.get("Attributes", {}).get("events", {}).get("N", "0"))

    item = {
        "pk": {"S": f"ENDPOINT#{device_id}"},
        "sk": {"S": f"EVENT#{ts}#{seq:06d}"},
        "device_id": {"S": device_id},
        "ts": {"S": ts},
        "seq": {"N": str(seq)},
        "action": {"S": action},
        "decision": {"S": decision},
        "destination": {"S": _s(payload.get("destination"), 200)},
        "principal": {"S": device.get("principal", {}).get("S", "")},
        "hostname": {"S": device.get("hostname", {}).get("S", "")},
    }
    if found:
        item["entities_found"] = {"M": {k: {"N": str(v)} for k, v in found.items()}}
    if masked:
        item["entities_masked"] = {"M": {k: {"N": str(v)} for k, v in masked.items()}}
    if tiers:
        item["detector_tiers"] = {"SS": tiers}

    ddb.put_item(TableName=table, Item=item)
    return 200, {"ok": True, "device_id": device_id, "seq": seq, "ts": ts}


# ---------------------------------------------------------------------------
# Fleet read
# ---------------------------------------------------------------------------


def _event_row(item: dict) -> dict:
    return {
        "device_id": item.get("device_id", {}).get("S", ""),
        "hostname": item.get("hostname", {}).get("S", ""),
        "ts": item.get("ts", {}).get("S", ""),
        "seq": int(item.get("seq", {}).get("N", "0")),
        "action": item.get("action", {}).get("S", ""),
        "decision": item.get("decision", {}).get("S", ""),
        "destination": item.get("destination", {}).get("S", ""),
        "principal": item.get("principal", {}).get("S", ""),
        "detector_tiers": item.get("detector_tiers", {}).get("SS", []),
        "entities_found": {
            k: int(v["N"]) for k, v in item.get("entities_found", {}).get("M", {}).items()
        },
        "entities_masked": {
            k: int(v["N"]) for k, v in item.get("entities_masked", {}).get("M", {}).items()
        },
    }


def fleet(*, table: str, ddb, limit: int = 40, per_device: int = 20) -> tuple[int, dict]:
    """Enrolled devices and their recent decisions.

    One Query for the device list (they share a partition), then one Query
    per device for its newest events. No Scan anywhere — the Lambda role
    does not grant it, and a Scan here would get slower as the audit table
    fills with rows from the other two planes, which have nothing to do
    with the endpoint fleet.
    """
    devices: list[dict] = []
    events: list[dict] = []
    now = datetime.now(timezone.utc)

    resp = ddb.query(
        TableName=table,
        KeyConditionExpression="pk = :p AND begins_with(sk, :s)",
        ExpressionAttributeValues={":p": {"S": _DEVICE_PK}, ":s": {"S": "DEVICE#"}},
        Limit=200,
    )

    for item in resp.get("Items", []):
        last = item.get("last_seen", {}).get("S", "")
        stale = True
        try:
            stale = (now - datetime.fromisoformat(last)).total_seconds() > STALE_AFTER_S
        except (ValueError, TypeError):
            pass
        devices.append(
            {
                "device_id": item.get("device_id", {}).get("S", ""),
                "hostname": item.get("hostname", {}).get("S", ""),
                "os": item.get("os", {}).get("S", ""),
                "principal": item.get("principal", {}).get("S", ""),
                "agent_version": item.get("agent_version", {}).get("S", ""),
                "enrolled_at": item.get("enrolled_at", {}).get("S", ""),
                "last_seen": last,
                "events": int(item.get("events", {}).get("N", "0")),
                "status": "stale" if stale else "live",
            }
        )

    for d in devices:
        if not d["device_id"]:
            continue
        try:
            ev = ddb.query(
                TableName=table,
                KeyConditionExpression="pk = :p AND begins_with(sk, :s)",
                ExpressionAttributeValues={
                    ":p": {"S": f"ENDPOINT#{d['device_id']}"},
                    ":s": {"S": "EVENT#"},
                },
                # Newest first — the sort key starts with an ISO timestamp,
                # so descending order is chronological without a sort here.
                ScanIndexForward=False,
                Limit=per_device,
            )
            events.extend(_event_row(i) for i in ev.get("Items", []))
        except Exception:  # noqa: BLE001
            # One unreadable device must not blank the whole fleet view.
            continue

    events.sort(key=lambda e: (e["ts"], e["seq"]), reverse=True)
    devices.sort(key=lambda d: d["last_seen"], reverse=True)
    return 200, {"devices": devices, "events": events[:limit], "checked_at": _now_iso()}
