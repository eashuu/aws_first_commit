"""Control-plane Function URL handler: policy CRUD, the live feed, session
drill-down, and static UI serving. A flat route table, no framework.

The control plane owns the canonical policy bundle — stored as one
DynamoDB item (`pk="POLICY", sk="CURRENT"`) in the same table the data
plane already writes, rather than a second table for one row. `GET
/policy` falls back to the packaged `agent.cedar` when no item has ever
been written (a fresh deploy).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timezone

import cedarpy

import endpoint
import policy
from config import CFG

_WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _etag_for(text: str) -> str:
    return '"' + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] + '"'


def _response(status: int, body: dict | None = None, *, headers: dict | None = None) -> dict:
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    return {"statusCode": status, "headers": h, "body": json.dumps(body if body is not None else {})}


def _error(status: int, code: str, message: str) -> dict:
    return _response(status, {"error": {"code": code, "message": message, "trace_id": ""}})


def _header(event: dict, name: str) -> str | None:
    headers = event.get("headers") or {}
    lname = name.lower()
    for k, v in headers.items():
        if k.lower() == lname:
            return v
    return None


# ---------------------------------------------------------------------------
# Policy storage — one DynamoDB item, one ETag, one atomic swap (TD §3.4).
# ---------------------------------------------------------------------------

_ddb_cache: dict[str, object] = {}


def _ddb_client():
    client = _ddb_cache.get("client")
    if client is not None:
        return client
    import boto3

    client = boto3.client("dynamodb", region_name=CFG.aws_region)
    _ddb_cache["client"] = client
    return client


def _load_stored_bundle() -> dict | None:
    client = _ddb_client()
    resp = client.get_item(TableName=CFG.audit_table, Key={"pk": {"S": "POLICY"}, "sk": {"S": "CURRENT"}})
    item = resp.get("Item")
    if not item:
        return None
    return json.loads(item["body"]["S"])


def _store_bundle(body: dict) -> None:
    client = _ddb_client()
    client.put_item(
        TableName=CFG.audit_table,
        Item={"pk": {"S": "POLICY"}, "sk": {"S": "CURRENT"}, "body": {"S": json.dumps(body)}},
    )


def _fallback_bundle() -> dict:
    with open(CFG.fallback_policy_path, encoding="utf-8") as f:
        cedar_text = f.read()
    from config import (
        DEFAULT_BUDGET,
        DEFAULT_COMPREHEND_MIN_SCORE,
        DEFAULT_IDENTIFYING_TYPES,
        DEFAULT_SESSION_CEILING,
    )

    return {
        "version": "package-fallback",
        "cedar": cedar_text,
        "entities": [],
        "budget": {"default": DEFAULT_BUDGET, "per_role": {"compliance": 9999}},
        "session_ceiling": DEFAULT_SESSION_CEILING,
        "identifying_types": sorted(DEFAULT_IDENTIFYING_TYPES),
        "thresholds": {"comprehend_min_score": DEFAULT_COMPREHEND_MIN_SCORE},
    }


def _current_bundle() -> dict:
    try:
        stored = _load_stored_bundle()
    except Exception:  # noqa: BLE001
        stored = None
    return stored or _fallback_bundle()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _route_get_policy(event: dict) -> dict:
    bundle = _current_bundle()
    etag = _etag_for(bundle["cedar"])
    if _header(event, "If-None-Match") == etag:
        return {"statusCode": 304, "headers": {"ETag": etag}, "body": ""}
    return _response(200, bundle, headers={"ETag": etag})


def _route_put_policy(event: dict) -> dict:
    key = _header(event, "X-Naka-Key")
    if not CFG.naka_key or key != CFG.naka_key:
        return _error(401, "BAD_KEY", "missing or incorrect X-Naka-Key header")

    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw_body = base64.b64decode(raw_body).decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError) as exc:
        return _error(400, "BAD_REQUEST", f"invalid JSON body: {exc}")

    cedar_text = payload.get("cedar")
    if not cedar_text:
        return _error(400, "BAD_REQUEST", "'cedar' is required")

    try:
        cedarpy.PolicySet.from_str(cedar_text)
    except ValueError as exc:
        return _error(400, "CEDAR_PARSE_ERROR", str(exc))

    if not policy.floor_ok(cedar_text):
        return _error(400, "POLICY_FLOOR_VIOLATION", "bundle is missing a mandatory floor rule")

    current = _current_bundle()

    # Validate the shape of everything else before persisting anything —
    # the data plane's policy.py._bundle_from_json applies these same
    # types; a bad PUT that passed here would otherwise return 200, get
    # stored, and only fail later and silently on the data-plane side
    # (falling back to the previous/fallback bundle with no error ever
    # surfaced to whoever pushed it).
    budget = payload.get("budget", current.get("budget"))
    if not isinstance(budget, dict) or not isinstance(budget.get("default"), int):
        return _error(400, "BAD_REQUEST", "'budget' must be an object with an integer 'default'")
    if "per_role" in budget and not (
        isinstance(budget["per_role"], dict) and all(isinstance(v, int) for v in budget["per_role"].values())
    ):
        return _error(400, "BAD_REQUEST", "'budget.per_role' must be an object of integers")

    session_ceiling = payload.get("session_ceiling", current.get("session_ceiling"))
    if not isinstance(session_ceiling, int):
        return _error(400, "BAD_REQUEST", "'session_ceiling' must be an integer")

    identifying_types = payload.get("identifying_types", current.get("identifying_types"))
    if not isinstance(identifying_types, list) or not all(isinstance(t, str) for t in identifying_types):
        return _error(400, "BAD_REQUEST", "'identifying_types' must be an array of strings")

    thresholds = payload.get("thresholds", current.get("thresholds"))
    if not isinstance(thresholds, dict) or not isinstance(thresholds.get("comprehend_min_score"), (int, float)):
        return _error(400, "BAD_REQUEST", "'thresholds' must be an object with a numeric 'comprehend_min_score'")

    entities = payload.get("entities", current.get("entities", []))
    if not isinstance(entities, list):
        return _error(400, "BAD_REQUEST", "'entities' must be an array")

    current_etag = _etag_for(current["cedar"])
    if_match = _header(event, "If-Match")
    if if_match and if_match != current_etag:
        return _error(409, "ETAG_MISMATCH", "policy has changed since you last fetched it")

    new_bundle = {
        "version": payload.get("version") or _now_iso(),
        "cedar": cedar_text,
        "entities": entities,
        "budget": budget,
        "session_ceiling": session_ceiling,
        "identifying_types": identifying_types,
        "thresholds": thresholds,
    }
    _store_bundle(new_bundle)
    return _response(200, {"version": new_bundle["version"], "etag": _etag_for(cedar_text)})


def _encode_cursor(last_evaluated_key: dict) -> str:
    # DynamoDB's own LastEvaluatedKey is already the exact dict a follow-up
    # query needs as ExclusiveStartKey (all four key attributes: the base
    # table's pk/sk plus the GSI's gsi1pk/gsi1sk) — round-tripping it
    # opaquely, rather than hand-reconstructing a partial key from just
    # gsi1sk, is what makes pagination past page 1 actually resume correctly.
    return base64.urlsafe_b64encode(json.dumps(last_evaluated_key).encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8"))


def _route_feed(event: dict) -> dict:
    qs = event.get("queryStringParameters") or {}
    date = qs.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        limit = min(max(int(qs.get("limit", 50)), 1), 200)
    except (TypeError, ValueError):
        return _error(400, "BAD_REQUEST", f"invalid 'limit': {qs.get('limit')!r}")

    client = _ddb_client()
    kwargs = {
        "TableName": CFG.audit_table,
        "IndexName": "gsi1",
        "KeyConditionExpression": "gsi1pk = :pk",
        "ExpressionAttributeValues": {":pk": {"S": f"FEED#{date}"}},
        "ScanIndexForward": False,
        "Limit": limit,
    }

    after = qs.get("after")
    if after:
        try:
            kwargs["ExclusiveStartKey"] = _decode_cursor(after)
        except Exception:  # noqa: BLE001
            return _error(400, "BAD_CURSOR", "invalid or corrupted 'after' cursor")

    try:
        resp = client.query(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return _error(503, "STORE_UNAVAILABLE", type(exc).__name__)

    rows = [_item_to_row(item) for item in resp.get("Items", [])]
    last_key = resp.get("LastEvaluatedKey")
    cursor = _encode_cursor(last_key) if last_key else None
    return _response(200, {"rows": rows, "cursor": cursor})


def _route_session(session_id: str) -> dict:
    client = _ddb_client()
    try:
        resp = client.query(
            TableName=CFG.audit_table,
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": {"S": f"SESSION#{session_id}"}},
        )
    except Exception as exc:  # noqa: BLE001
        return _error(503, "STORE_UNAVAILABLE", type(exc).__name__)

    items = resp.get("Items", [])
    if not items:
        return _error(404, "NO_SUCH_SESSION", f"no rows for session '{session_id}'")

    calls, meters = [], {}
    for item in items:
        sk = item.get("sk", {}).get("S", "")
        if sk.startswith("METER#"):
            subject = sk[len("METER#") :]
            meters[subject] = {"seen": item.get("seen", {}).get("SS", []), "budget": 0}
        elif sk.startswith("CALL#"):
            calls.append(_item_to_row(item))

    # The budget is NOT on the meter row and must not be: ledger.spend()
    # writes only the grow-only `seen` set, and budget is a per-ROLE policy
    # value, so one number on a row that spans roles would be wrong for at
    # least one of them. Take it from the calls that actually touched this
    # subject (each audit row records the budget in force for its own
    # principal), newest last, and fall back to the current bundle's
    # default so the UI can still draw a meter for a subject whose calls
    # have aged out under TTL.
    default_budget = 0
    try:
        default_budget = int(_current_bundle().get("budget", {}).get("default", 0))
    except Exception:  # noqa: BLE001 — a missing bundle must not 500 the drill-down
        pass
    for subject, meter in meters.items():
        from_calls = [c["budget"] for c in calls if c["subject"] == subject and c["budget"]]
        meter["budget"] = from_calls[-1] if from_calls else default_budget

    return _response(200, {"calls": calls, "meters": meters})


def _item_to_row(item: dict) -> dict:
    def s(k, default=""):
        return item.get(k, {}).get("S", default)

    def session_id_from_pk() -> str:
        pk = item.get("pk", {}).get("S", "")
        return pk[len("SESSION#") :] if pk.startswith("SESSION#") else ""

    def n(k, default=0):
        v = item.get(k, {}).get("N")
        return int(v) if v is not None else default

    def ss(k):
        return item.get(k, {}).get("SS", [])

    def m(k):
        return {kk: (int(vv["N"]) if "N" in vv else vv.get("S")) for kk, vv in item.get(k, {}).get("M", {}).items()}

    return {
        "session_id": session_id_from_pk(),
        "seq": n("seq"),
        "ts": s("ts"),
        "principal": s("principal"),
        "role": s("role"),
        "subject": s("subject"),
        "tool": s("tool"),
        "call_decision": s("call_decision"),
        "deny_policy": item.get("deny_policy", {}).get("S"),
        "content_type": s("content_type"),
        "detector_tiers": ss("detector_tiers"),
        "entities_found": m("entities_found"),
        "entities_masked": m("entities_masked"),
        "entities_revealed": m("entities_revealed"),
        "mask_policies": m("mask_policies"),
        "ledger_after": ss("ledger_after"),
        "budget": n("budget"),
        "outcome": s("outcome"),
        "latency_ms": m("latency_ms"),
        "policy_version": s("policy_version"),
    }


# Detector-tier diagnostics. The point is to distinguish "this tier ran and
# found nothing" from "this tier never ran", which is the exact conflation
# the whole product exists to prevent (PRD §6.3: a blind spot wearing the
# clean state's clothes). Reporting a gated service as a neutral NOT_RUN is
# both honest and more useful than a red error or a silent skip.
_diag_cache: dict[str, object] = {}
_DIAG_TTL_S = 60

_ONE_PX_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _probe(fn) -> tuple[str, str]:
    """(status, detail). AccessDenied/SubscriptionRequired are reported as
    NOT_RUN rather than FAIL: the service is gated on this account, which is
    a provisioning state, not a defect in the detector."""
    try:
        fn()
        return "PASS", ""
    except Exception as exc:  # noqa: BLE001
        code = ""
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            code = response.get("Error", {}).get("Code", "")
        code = code or type(exc).__name__
        if code in (
            "SubscriptionRequiredException",
            "AccessDeniedException",
            "ValidationException",
            "UnrecognizedClientException",
        ):
            return "NOT_RUN", code
        return "FAIL", code


def _route_diag() -> dict:
    now = datetime.now(timezone.utc).timestamp()
    cached = _diag_cache.get("value")
    if cached and now - float(_diag_cache.get("at", 0)) < _DIAG_TTL_S:
        return _response(200, cached)  # type: ignore[arg-type]

    import boto3

    region = CFG.aws_region
    tiers = [
        {
            "tier": "Tier 1",
            "name": "Local checksum",
            "detail": "Verhoeff (Aadhaar), PAN/GSTIN/IFSC/Voter ID format",
            # Tier 1 is pure local arithmetic with no dependency to probe —
            # if this module imported, it runs.
            "status": "PASS",
            "note": "",
        }
    ]

    status, note = _probe(
        lambda: boto3.client("comprehend", region_name=region).detect_pii_entities(
            Text="probe", LanguageCode="en"
        )
    )
    tiers.append({"tier": "Tier 2", "name": "Amazon Comprehend", "detail": "DetectPiiEntities", "status": status, "note": note})

    status, note = _probe(
        lambda: boto3.client("textract", region_name=region).detect_document_text(
            Document={"Bytes": _ONE_PX_PNG}
        )
    )
    tiers.append({"tier": "Normalize", "name": "Amazon Textract", "detail": "DetectDocumentText (PDF/image OCR)", "status": status, "note": note})

    status, note = _probe(
        lambda: boto3.client("bedrock-runtime", region_name=region).converse(
            modelId=CFG.indic_model_id,
            messages=[{"role": "user", "content": [{"text": "probe"}]}],
            inferenceConfig={"maxTokens": 1},
        )
    )
    tiers.append({"tier": "Tier 3", "name": "Nova Pro multimodal", "detail": "Indic-script OCR, additive only", "status": status, "note": note})

    body = {"tiers": tiers, "checked_at": _now_iso(), "region": region}
    _diag_cache["value"] = body
    _diag_cache["at"] = now
    return _response(200, body)


def _serve_static(path: str) -> dict:
    rel = (path or "/").lstrip("/") or "index.html"
    web_root = os.path.normpath(_WEB_DIR)
    full = os.path.normpath(os.path.join(web_root, rel))

    # Extensionless pretty URLs: /pricing serves pricing.html. Resolved only
    # after the containment check below would have passed for the same base,
    # so this cannot be used to escape the web root — os.path.splitext on a
    # traversal attempt still leaves the "..", which the check rejects.
    if not os.path.isfile(full) and not os.path.splitext(rel)[1]:
        candidate = full + ".html"
        if os.path.isfile(candidate):
            full = candidate
    # A bare startswith(web_root) is satisfied by a *sibling* directory whose
    # name merely starts with the same characters (e.g. "web-internal") —
    # the trailing separator makes this an actual containment check, not a
    # string-prefix one.
    if not (full == web_root or full.startswith(web_root + os.sep)) or not os.path.isfile(full):
        return _error(404, "NOT_FOUND", f"no such file: {path}")

    ext = os.path.splitext(full)[1]
    ctype = _CONTENT_TYPES.get(ext, "application/octet-stream")
    with open(full, "rb") as f:
        raw = f.read()

    # A Function URL sends no caching headers at all, which leaves browsers
    # applying their own heuristic freshness — so a redeploy can leave a
    # visitor running last version's CSS against this version's markup,
    # with no way for them to know. (Observed: a stale app.css silently
    # disabled every reveal animation on an otherwise-correct deploy.)
    # `no-cache` still allows a cached copy, it just forces revalidation,
    # which is what a small console served straight from Lambda wants.
    headers = {"Content-Type": ctype, "Cache-Control": "no-cache"}

    if ctype.startswith("text/") or "javascript" in ctype or "json" in ctype:
        return {"statusCode": 200, "headers": headers, "body": raw.decode("utf-8")}
    return {
        "statusCode": 200,
        "headers": headers,
        "body": base64.b64encode(raw).decode("ascii"),
        "isBase64Encoded": True,
    }


def lambda_handler(event: dict, context) -> dict:
    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method", "GET")
    path = event.get("rawPath", "/")

    if path == "/health":
        # agent_url rides along so the UI this same Lambda serves can
        # prefill the data-plane endpoint. Without it a visitor who has
        # never used this browser before sees an empty field and "Set the
        # agent Function URL first" — the URL is remembered in
        # localStorage, which a fresh viewer by definition does not have.
        try:
            _ddb_client().describe_table(TableName=CFG.audit_table)
            return _response(200, {"ok": True, "table": CFG.audit_table, "agent_url": CFG.agent_url})
        except Exception as exc:  # noqa: BLE001
            return _response(503, {"ok": False, "error": type(exc).__name__, "agent_url": CFG.agent_url})

    if path == "/policy" and method == "GET":
        return _route_get_policy(event)
    if path == "/policy" and method == "PUT":
        return _route_put_policy(event)
    if path == "/diag" and method == "GET":
        return _route_diag()

    # ---- endpoint plane -------------------------------------------------
    # The agent itself runs on a laptop and cannot run on AWS (see
    # endpoint.py). These three routes are its control plane, and they are
    # what make the console's Endpoint view show a real fleet instead of the
    # honest empty state it showed while they did not exist.
    if path == "/endpoint/enroll" and method == "POST":
        key = _header(event, "X-Naka-Key")
        if not CFG.naka_key or key != CFG.naka_key:
            return _error(401, "BAD_KEY", "enrolling a device requires the operator X-Naka-Key header")
        try:
            payload = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _error(400, "BAD_JSON", "body must be JSON")
        status, body = endpoint.enroll(payload, table=CFG.audit_table, ddb=_ddb_client())
        return _response(status, body)

    if path == "/endpoint/event" and method == "POST":
        try:
            payload = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _error(400, "BAD_JSON", "body must be JSON")
        status, body = endpoint.ingest(
            payload,
            device_header=_header(event, "X-Naka-Device"),
            table=CFG.audit_table,
            ddb=_ddb_client(),
        )
        return _response(status, body)

    if path == "/endpoint/fleet" and method == "GET":
        try:
            status, body = endpoint.fleet(table=CFG.audit_table, ddb=_ddb_client())
            return _response(status, body)
        except Exception as exc:  # noqa: BLE001
            # Carry the real reason. A bare type name ("ClientError") sent me
            # hunting through CloudWatch for what turned out to be a missing
            # IAM action; the console renders this string, and an operator
            # deserves the same clue.
            return _error(503, "FLEET_UNAVAILABLE", f"{type(exc).__name__}: {exc}"[:400])
    if path == "/feed" and method == "GET":
        return _route_feed(event)
    if path.startswith("/session/") and method == "GET":
        return _route_session(path[len("/session/") :])

    if method == "GET":
        return _serve_static(path)

    return _error(404, "NOT_FOUND", f"no route for {method} {path}")
