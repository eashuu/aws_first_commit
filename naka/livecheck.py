"""Live-AWS integration check — the half of the system selfcheck.py cannot
reach.

`selfcheck.py` covers pure logic (checksums, offsets, merge, Cedar
decisions) with no network. This file covers the wiring: real DynamoDB
round-trips, real Comprehend/Textract/Bedrock calls, and the two Lambda
handlers driven in-process against them.

Run it against a deployed stack:

    AUDIT_TABLE=naka_audit SESSION_BUCKET=naka-sessions-<acct> python livecheck.py

Every AWS-dependent check reports SKIP (not FAIL) when its service is
unreachable, so this is still useful on a half-provisioned account — the
summary tells you which half. Anything it writes to DynamoDB is under a
`SESSION#livecheck-<uuid>` partition and is deleted on the way out.
"""

from __future__ import annotations

import json
import sys
import uuid

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
_results: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str = "") -> None:
    _results.append((status, name, detail))
    mark = {PASS: "ok  ", FAIL: "FAIL", SKIP: "skip"}[status]
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))


def check(name: str):
    """Decorator: run fn, record PASS, or FAIL with the exception type.
    A fn that raises `Skip` records SKIP instead."""

    def wrap(fn):
        try:
            detail = fn() or ""
            record(PASS, name, detail)
        except Skip as exc:
            record(SKIP, name, str(exc))
        except Exception as exc:  # noqa: BLE001
            record(FAIL, name, f"{type(exc).__name__}: {exc}")
        return fn

    return wrap


class Skip(Exception):
    pass


# ---------------------------------------------------------------------------
# Service reachability — everything below keys off this
# ---------------------------------------------------------------------------

import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

from config import CFG  # noqa: E402

REACHABLE: dict[str, bool] = {}


def _probe(service: str, fn) -> None:
    try:
        fn()
        REACHABLE[service] = True
        record(PASS, f"reachable: {service}")
    except Exception as exc:  # noqa: BLE001
        REACHABLE[service] = False
        code = ""
        if isinstance(exc, ClientError):
            code = exc.response.get("Error", {}).get("Code", "")
        record(SKIP, f"reachable: {service}", code or type(exc).__name__)


print("\n== service reachability ==")
_ddb = boto3.client("dynamodb", region_name=CFG.aws_region)
_probe("dynamodb", lambda: _ddb.describe_table(TableName=CFG.audit_table))
_probe(
    "s3",
    lambda: boto3.client("s3", region_name=CFG.aws_region).head_bucket(Bucket=CFG.session_bucket),
)
_probe(
    "comprehend",
    lambda: boto3.client("comprehend", region_name=CFG.aws_region).detect_pii_entities(
        Text="Call me at 9876543210.", LanguageCode="en"
    ),
)
_probe(
    "textract",
    lambda: boto3.client("textract", region_name=CFG.aws_region).detect_document_text(
        Document={"Bytes": _ONE_PX_PNG}
        if (_ONE_PX_PNG := __import__("base64").b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        ))
        else {}
    ),
)
_probe(
    "bedrock",
    lambda: boto3.client("bedrock-runtime", region_name=CFG.aws_region).converse(
        modelId=CFG.model_id,
        messages=[{"role": "user", "content": [{"text": "hi"}]}],
        inferenceConfig={"maxTokens": 5},
    ),
)


def need(service: str) -> None:
    if not REACHABLE.get(service):
        raise Skip(f"{service} unreachable")


# ---------------------------------------------------------------------------
# A stub Comprehend, so the pipeline checks still run on an account where
# the real one is gated. It is deliberately dumb: fixed offsets computed by
# str.find, no model. It proves the WIRING, and says so — it is never a
# substitute for the real-Comprehend check above.
# ---------------------------------------------------------------------------


class StubComprehend:
    """Finds a fixed set of demo strings. Same response shape as the real
    DetectPiiEntities: {"Entities": [{Type, Score, BeginOffset, EndOffset}]}.

    The strings below are copied verbatim out of fixtures/customers.json.
    That matters: a stub keyed on invented values finds nothing, every
    assertion about masking passes vacuously, and the checks look green
    while testing nothing."""

    KNOWN = [
        ("NAME", "Anil Kumar Rao"),
        ("PHONE", "+91 55501 84412"),
        ("EMAIL", "anil.rao@example.com"),
        ("ADDRESS", "Flat 4B, Nandini Residency, 12 Sarjapur Cross Road, Bengaluru, Karnataka 560102"),
        ("NAME", "Meera Nair"),
    ]

    def detect_pii_entities(self, *, Text: str, LanguageCode: str) -> dict:  # noqa: N803
        out = []
        for etype, needle in self.KNOWN:
            start = 0
            while (pos := Text.find(needle, start)) != -1:
                out.append(
                    {"Type": etype, "Score": 0.99, "BeginOffset": pos, "EndOffset": pos + len(needle)}
                )
                start = pos + len(needle)
        return {"Entities": out}


SESSION_ID = f"livecheck-{uuid.uuid4().hex[:8]}"
WROTE_KEYS: list[dict] = []


# ---------------------------------------------------------------------------
# 1. The ledger, against real DynamoDB
# ---------------------------------------------------------------------------

print("\n== ledger (real DynamoDB) ==")

import ledger as ledger_mod  # noqa: E402


@check("ledger.load on a fresh session is empty, not an error")
def _t():
    need("dynamodb")
    led = ledger_mod.load(SESSION_ID, cfg=CFG, budget=3, session_ceiling=25)
    assert led.subjects == {}, led.subjects
    assert led.total() == 0


@check("ledger.spend is an atomic union and reports (before, after)")
def _t():
    need("dynamodb")
    subject = "cust_8814"
    WROTE_KEYS.append({"pk": {"S": f"SESSION#{SESSION_ID}"}, "sk": {"S": f"METER#{subject}"}})

    before, after = ledger_mod.spend(SESSION_ID, subject, {"NAME", "PHONE"}, cfg=CFG)
    assert before == [], before
    assert after == ["NAME", "PHONE"], after

    # Second spend overlaps the first — union, not append, and `before` now
    # reflects what was already there.
    before2, after2 = ledger_mod.spend(SESSION_ID, subject, {"PHONE", "EMAIL"}, cfg=CFG)
    assert before2 == ["NAME", "PHONE"], before2
    assert after2 == ["EMAIL", "NAME", "PHONE"], after2

    # Idempotent: re-spending a type already seen must not grow the set.
    _, after3 = ledger_mod.spend(SESSION_ID, subject, {"NAME"}, cfg=CFG)
    assert after3 == ["EMAIL", "NAME", "PHONE"], after3
    return "NAME,PHONE -> +PHONE,EMAIL -> union of 3"


@check("ledger.load reads back exactly what spend wrote")
def _t():
    need("dynamodb")
    led = ledger_mod.load(SESSION_ID, cfg=CFG, budget=3, session_ceiling=25)
    assert led.seen("cust_8814") == ["EMAIL", "NAME", "PHONE"], led.seen("cust_8814")
    assert led.count("cust_8814") == 3
    assert led.total() == 3


@check("ledger.spend([]) is a no-op, not a DynamoDB error")
def _t():
    need("dynamodb")
    assert ledger_mod.spend(SESSION_ID, "cust_8814", set(), cfg=CFG) == ([], [])


# ---------------------------------------------------------------------------
# 2. The audit writer, against real DynamoDB
# ---------------------------------------------------------------------------

print("\n== audit rows (real DynamoDB) ==")

import audit  # noqa: E402


@check("audit.put_row writes an item the control plane can read back")
def _t():
    need("dynamodb")
    row = audit.AuditRow(
        session_id=SESSION_ID,
        seq=1,
        ts=audit._now_iso(),
        invocation_id="livecheck",
        principal="analyst@example.com",
        role="analyst",
        subject="cust_8814",
        tool="fetch_customer",
        call_decision="ALLOW",
        deny_policy=None,
        content_type="application/json",
        pages=1,
        truncated=False,
        detector_tiers=["checksum", "comprehend"],
        entities_found={"IN_AADHAAR": 1, "NAME": 1},
        entities_masked={"IN_AADHAAR": 1},
        entities_revealed={"NAME": 1},
        mask_policies={"IN_AADHAAR": "q2_forbid_aadhaar"},
        ledger_before=[],
        ledger_after=["NAME"],
        budget=3,
        session_total=1,
        rehydrated=[],
        outcome="ok",
        latency_ms={"total": 42},
        policy_version="livecheck",
    )
    item = audit._row_to_item(row, cfg=CFG)
    WROTE_KEYS.append({"pk": item["pk"], "sk": item["sk"]})
    audit.put_row(row, cfg=CFG)

    got = _ddb.get_item(TableName=CFG.audit_table, Key={"pk": item["pk"], "sk": item["sk"]})
    assert "Item" in got, "row did not land in DynamoDB"
    stored = got["Item"]
    assert stored["ts"]["S"] == row.ts
    assert stored["seq"]["N"] == "1"
    assert stored["gsi1pk"]["S"].startswith("FEED#")
    assert "expires_at" in stored, "TTL attribute missing"
    return f"sk={item['sk']['S']}"


@check("no audit attribute carries an entity VALUE (only types and counts)")
def _t():
    need("dynamodb")
    # The single most important invariant in the system: the audit trail
    # describes disclosure without reproducing it. Assert against the real
    # stored item, not the dataclass.
    key = WROTE_KEYS[-1]
    stored = _ddb.get_item(TableName=CFG.audit_table, Key=key)["Item"]
    blob = json.dumps(stored)
    for secret in ("234176349012", "Priya Sharma", "98765 43210", "ABCPS1234D"):
        assert secret not in blob, f"audit row leaked {secret!r}"
    return "checked 4 known plaintext values"


# ---------------------------------------------------------------------------
# 3. The full guard pipeline, end to end
# ---------------------------------------------------------------------------

print("\n== guard pipeline (tool -> normalize -> detect -> Q2 -> redact -> spend) ==")

import detect  # noqa: E402
import policy as policy_mod  # noqa: E402
import tools  # noqa: E402
from guard import DisclosureGuard  # noqa: E402
from rehydrate import Rehydrator, Vault  # noqa: E402


class FakeAgentState:
    def __init__(self):
        self._d = {}

    def set(self, k, v):
        self._d[k] = v

    def get(self, k):
        return self._d.get(k)


class FakeAgent:
    def __init__(self):
        self.state = FakeAgentState()


class FakeEvent:
    """Stands in for Before/AfterToolCallEvent — the guard only ever touches
    .tool_use, .result and .agent."""

    def __init__(self, tool_use: dict, result: dict | None = None):
        self.tool_use = tool_use
        self.result = result
        self.agent = FakeAgent()
        self.cancel_tool = None


def _guard_for(role: str, session_id: str, *, bundle=None, vault=None):
    bundle = bundle or policy_mod.current(CFG)
    led = ledger_mod.load(session_id, cfg=CFG, budget=bundle.budget_for(role), session_ceiling=bundle.session_ceiling)
    return (
        DisclosureGuard(
            session_id=session_id,
            principal=f"{role}@example.com",
            role=role,
            vault=vault or Vault(nonce="abcd"),
            ledger=led,
            policy=bundle,
            cfg=CFG,
        ),
        bundle,
        led,
    )


def _run_hop(guard, tool_name: str, tool_input: dict, result: dict, tool_use_id: str):
    ev_before = FakeEvent({"name": tool_name, "input": tool_input, "toolUseId": tool_use_id})
    guard.before_tool_call(ev_before)
    ev_after = FakeEvent({"name": tool_name, "input": tool_input, "toolUseId": tool_use_id}, result=result)
    outcome = guard.after_tool_call(ev_after)
    if hasattr(outcome, "apply") and outcome.apply is not None:
        outcome.apply(ev_after)
    return ev_after, guard.hop_outcomes.get(tool_use_id)


@check("analyst KYC hop: Aadhaar+PAN masked, NAME revealed, ledger spent")
def _t():
    need("dynamodb")
    detect._comprehend_client_cache["client"] = StubComprehend()
    session = f"{SESSION_ID}-a"
    WROTE_KEYS.append({"pk": {"S": f"SESSION#{session}"}, "sk": {"S": "METER#cust_8814"}})

    guard, bundle, _ = _guard_for("analyst", session)
    result = tools.fetch_customer(customer_id="cust_8814", field="kyc")
    assert result["status"] == "success", result

    ev, hop = _run_hop(guard, "fetch_customer", {"customer_id": "cust_8814", "field": "kyc"}, result, "tu-1")
    text = ev.result["content"][0]["text"]

    assert hop is not None and hop.outcome == "ok", hop
    assert "IN_AADHAAR" in hop.entities_found, hop.entities_found
    assert hop.entities_masked.get("IN_AADHAAR") == 1, hop.entities_masked
    assert "[IN_AADHAAR_1_abcd]" in text, text
    # The masked value must be gone from the released text entirely.
    assert "2341" not in text, text
    assert hop.ledger_before == [], hop.ledger_before
    assert hop.ledger_after, "nothing was spent"
    return f"found={hop.entities_found} masked={hop.entities_masked} ledger={hop.ledger_after}"


@check("budget exhaustion: a 4th distinct field for one subject is masked")
def _t():
    need("dynamodb")
    detect._comprehend_client_cache["client"] = StubComprehend()
    session = f"{SESSION_ID}-b"
    subject = "cust_8814"
    WROTE_KEYS.append({"pk": {"S": f"SESSION#{session}"}, "sk": {"S": f"METER#{subject}"}})

    guard, bundle, led = _guard_for("analyst", session)
    budget = bundle.budget_for("analyst")

    # Pre-spend the budget so the next hop is over it.
    ledger_mod.spend(session, subject, {"NAME", "PHONE", "EMAIL"}, cfg=CFG)
    led.add(subject, {"NAME", "PHONE", "EMAIL"})
    assert led.count(subject) >= budget, (led.count(subject), budget)

    result = tools.fetch_customer(customer_id=subject, field="address")
    ev, hop = _run_hop(guard, "fetch_customer", {"customer_id": subject, "field": "address"}, result, "tu-2")
    text = ev.result["content"][0]["text"]

    assert hop.entities_revealed == {} or "ADDRESS" not in hop.entities_revealed, hop.entities_revealed
    assert "ADDRESS" in hop.entities_masked, hop.entities_masked
    assert "MG Road" not in text, text
    return f"budget={budget} seen={led.count(subject)} masked={hop.entities_masked}"


@check("compliance role sees what analyst cannot")
def _t():
    need("dynamodb")
    detect._comprehend_client_cache["client"] = StubComprehend()
    session = f"{SESSION_ID}-c"
    WROTE_KEYS.append({"pk": {"S": f"SESSION#{session}"}, "sk": {"S": "METER#cust_8814"}})

    guard, _, _ = _guard_for("compliance", session)
    result = tools.fetch_customer(customer_id="cust_8814", field="kyc")
    ev, hop = _run_hop(guard, "fetch_customer", {"customer_id": "cust_8814", "field": "kyc"}, result, "tu-3")
    text = ev.result["content"][0]["text"]

    assert hop.entities_revealed.get("IN_AADHAAR") == 1, hop.entities_revealed
    assert "[IN_AADHAAR" not in text, text
    return f"revealed={hop.entities_revealed}"


@check("detector failure withholds the content instead of releasing it")
def _t():
    need("dynamodb")

    class BrokenComprehend:
        def detect_pii_entities(self, **kw):
            raise RuntimeError("simulated Comprehend outage")

    detect._comprehend_client_cache["client"] = BrokenComprehend()
    session = f"{SESSION_ID}-d"
    guard, _, _ = _guard_for("analyst", session)
    result = tools.fetch_customer(customer_id="cust_8814", field="kyc")
    ev, hop = _run_hop(guard, "fetch_customer", {"customer_id": "cust_8814", "field": "kyc"}, result, "tu-4")
    text = ev.result["content"][0]["text"]

    assert hop.outcome == "withheld_detector", hop.outcome
    assert "WITHHELD" in text, text
    assert "2341" not in text, "plaintext leaked on the failure path"
    detect._comprehend_client_cache.pop("client", None)
    return hop.outcome


@check("guard exception path still withholds (Deny is a no-op on after_tool_call)")
def _t():
    need("dynamodb")
    detect._comprehend_client_cache["client"] = StubComprehend()
    session = f"{SESSION_ID}-e"
    guard, _, _ = _guard_for("analyst", session)

    # Force an unexpected exception from deep inside _guard_result.
    orig = guard._guard_result
    guard._guard_result = lambda *a, **k: (_ for _ in ()).throw(KeyError("boom"))
    try:
        result = tools.fetch_customer(customer_id="cust_8814", field="kyc")
        ev, hop = _run_hop(guard, "fetch_customer", {"customer_id": "cust_8814", "field": "kyc"}, result, "tu-5")
    finally:
        guard._guard_result = orig
    text = ev.result["content"][0]["text"]

    assert hop.outcome == "withheld_internal_error", hop.outcome
    assert "WITHHELD" in text, text
    assert "2341" not in text, "plaintext leaked through the exception path"
    return hop.outcome


@check("rehydration into an unauthorized destination is denied")
def _t():
    need("dynamodb")
    vault = Vault(nonce="abcd")
    bundle = policy_mod.current(CFG)
    token = vault.mint("IN_AADHAAR", "2341 7634 9012").token

    rh = Rehydrator(vault=vault, principal="analyst@example.com", role="analyst", policy=bundle)
    ev = FakeEvent({"name": "send_summary", "input": {"to": "pastebin.example.com", "body": f"id {token}"}, "toolUseId": "tu-6"})
    outcome = rh.before_tool_call(ev)
    assert type(outcome).__name__ == "Deny", outcome
    assert token in ev.tool_use["input"]["body"], "token was substituted before the deny"
    return "denied, token left unresolved"


@check("rehydration into the authorized vault destination succeeds")
def _t():
    need("dynamodb")
    vault = Vault(nonce="abcd")
    bundle = policy_mod.current(CFG)
    token = vault.mint("IN_AADHAAR", "2341 7634 9012").token

    rh = Rehydrator(vault=vault, principal="analyst@example.com", role="analyst", policy=bundle)
    ev = FakeEvent({"name": "send_summary", "input": {"to": "kyc-vault.internal", "body": f"id {token}"}, "toolUseId": "tu-7"})
    outcome = rh.before_tool_call(ev)
    assert type(outcome).__name__ == "Proceed", outcome
    body = ev.tool_use["input"]["body"]
    assert "2341 7634 9012" in body, body
    assert rh.resolved_by_call.get("tu-7") == [token], rh.resolved_by_call
    return "resolved + recorded for the audit row"


# ---------------------------------------------------------------------------
# 4. Real Comprehend / Textract / Bedrock, when the account allows it
# ---------------------------------------------------------------------------

print("\n== real AI services ==")


@check("Comprehend finds the demo PII and detect() merges it with tier 1")
def _t():
    need("comprehend")
    detect._comprehend_client_cache.pop("client", None)
    text = (
        "customer_id: cust_8814\n"
        "name: Priya Sharma\n"
        "aadhaar: 2341 7634 9012\n"
        "phone: 98765 43210\n"
        "pan: ABCPS1234D\n"
    )
    res = detect.detect(text, ocr_sourced=False, cfg=CFG, min_score=0.5, indic_enabled=False)
    types = {e.type for e in res.entities}
    assert "IN_AADHAAR" in types, types
    assert "IN_PERMANENT_ACCOUNT_NUMBER" in types, types
    # Offsets must land on the real substrings, not approximately.
    for e in res.entities:
        if e.type == "IN_AADHAAR":
            assert text[e.begin : e.end].replace(" ", "") == "234176349012", text[e.begin : e.end]
    return f"types={sorted(types)}"


@check("Textract reads the generated KYC PDF fixture")
def _t():
    need("textract")
    import normalize as normalize_mod

    normalize_mod._textract_client_cache.pop("client", None)
    res = tools.read_attachment(ticket_id="tkt_4471")
    if res["status"] != "success":
        raise Skip("fixture missing — run fixtures/build_kyc_sheet.py")
    import base64 as _b64

    blob = res["content"][0]["json"]
    raw = _b64.b64decode(blob["b64"])
    n = normalize_mod.normalize(raw, blob["media_type"], cfg=CFG)
    assert n.ocr_sourced is True
    assert n.pages == 1, n.pages
    assert "Priya" in n.markdown or "PRIYA" in n.markdown.upper(), n.markdown[:200]
    return f"{len(n.markdown)} chars OCR'd"


@check("Bedrock Nova Lite answers a trivial prompt")
def _t():
    need("bedrock")
    client = boto3.client("bedrock-runtime", region_name=CFG.aws_region)
    resp = client.converse(
        modelId=CFG.model_id,
        messages=[{"role": "user", "content": [{"text": "Reply with the single word: ready"}]}],
        inferenceConfig={"maxTokens": 10},
    )
    out = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
    assert out.strip(), "empty model reply"
    return out.strip()[:40]


# ---------------------------------------------------------------------------
# 5. The control-plane handler, in-process against real DynamoDB
# ---------------------------------------------------------------------------

print("\n== control plane handler ==")

import app_control  # noqa: E402


def _evt(method: str, path: str, *, body=None, headers=None, qs=None) -> dict:
    return {
        "requestContext": {"http": {"method": method}},
        "rawPath": path,
        "body": json.dumps(body) if body is not None else None,
        "headers": headers or {},
        "queryStringParameters": qs or {},
    }


@check("GET /health reports the table")
def _t():
    need("dynamodb")
    resp = app_control.lambda_handler(_evt("GET", "/health"), None)
    assert resp["statusCode"] == 200, resp
    assert json.loads(resp["body"])["ok"] is True


@check("GET /policy serves a floor-valid bundle with an ETag")
def _t():
    need("dynamodb")
    resp = app_control.lambda_handler(_evt("GET", "/policy"), None)
    assert resp["statusCode"] == 200, resp
    bundle = json.loads(resp["body"])
    import policy as p

    assert p.floor_ok(bundle["cedar"]), "served bundle fails its own floor"
    etag = resp["headers"]["ETag"]
    again = app_control.lambda_handler(_evt("GET", "/policy", headers={"If-None-Match": etag}), None)
    assert again["statusCode"] == 304, again["statusCode"]
    return f"etag={etag}"


@check("PUT /policy rejects a bad key, bad Cedar, and a floor violation")
def _t():
    need("dynamodb")
    bad_key = app_control.lambda_handler(_evt("PUT", "/policy", body={"cedar": "permit(principal,action,resource);"}), None)
    assert bad_key["statusCode"] == 401, bad_key

    if not CFG.naka_key:
        return "no NAKA_KEY set locally — only the 401 path is exercised"

    h = {"X-Naka-Key": CFG.naka_key}
    bad_cedar = app_control.lambda_handler(_evt("PUT", "/policy", body={"cedar": "this is not cedar"}, headers=h), None)
    assert bad_cedar["statusCode"] == 400, bad_cedar

    floor = app_control.lambda_handler(
        _evt("PUT", "/policy", body={"cedar": "permit(principal, action, resource);"}, headers=h), None
    )
    assert floor["statusCode"] == 400, floor
    assert json.loads(floor["body"])["error"]["code"] == "POLICY_FLOOR_VIOLATION"
    return "401 / CEDAR_PARSE_ERROR / POLICY_FLOOR_VIOLATION all enforced"


@check("GET /feed returns today's rows with a session_id on each")
def _t():
    need("dynamodb")
    resp = app_control.lambda_handler(_evt("GET", "/feed", qs={"limit": "50"}), None)
    assert resp["statusCode"] == 200, resp
    rows = json.loads(resp["body"])["rows"]
    mine = [r for r in rows if r["session_id"] == SESSION_ID]
    assert mine, f"livecheck row not in feed ({len(rows)} rows today)"
    r = mine[0]
    assert r["tool"] == "fetch_customer", r
    assert r["entities_masked"] == {"IN_AADHAAR": 1}, r["entities_masked"]
    return f"{len(rows)} rows today, found ours"


@check("GET /feed rejects a malformed limit and a corrupt cursor")
def _t():
    need("dynamodb")
    bad_limit = app_control.lambda_handler(_evt("GET", "/feed", qs={"limit": "abc"}), None)
    assert bad_limit["statusCode"] == 400, bad_limit
    bad_cursor = app_control.lambda_handler(_evt("GET", "/feed", qs={"after": "!!!not-base64!!!"}), None)
    assert bad_cursor["statusCode"] == 400, bad_cursor


@check("GET /session/<id> returns calls AND a per-subject meter with a real budget")
def _t():
    need("dynamodb")
    resp = app_control.lambda_handler(_evt("GET", f"/session/{SESSION_ID}"), None)
    assert resp["statusCode"] == 200, resp
    body = json.loads(resp["body"])
    assert body["calls"], "no calls returned"
    assert "cust_8814" in body["meters"], body["meters"]
    meter = body["meters"]["cust_8814"]
    assert set(meter["seen"]) == {"EMAIL", "NAME", "PHONE"}, meter
    # The UI draws "seen of budget" — a budget of 0 renders an empty meter
    # and makes every subject look permanently over-disclosed.
    assert meter["budget"] > 0, f"meter budget is {meter['budget']} — the UI cannot draw this"
    return f"seen={meter['seen']} budget={meter['budget']}"


@check("shadow mode (enforce=false) is refused without the operator key")
def _t():
    import app_agent

    def agent_evt(body: dict, headers: dict | None = None) -> dict:
        return {
            "requestContext": {"http": {"method": "POST"}},
            "rawPath": "/",
            "body": json.dumps(body),
            "headers": headers or {},
        }

    base = {"prompt": "hi", "role": "analyst", "user": "a@example.com", "session_id": SESSION_ID}

    # The data plane's Function URL is AuthType=NONE. If `enforce: false`
    # were honoured from an unauthenticated body, any caller on the internet
    # could switch the guardrail off -- the single failure this system
    # exists to prevent.
    unauth = app_agent.lambda_handler(agent_evt({**base, "enforce": False}), None)
    assert unauth["statusCode"] in (401, 403), f"shadow mode accepted without a key: {unauth}"

    wrong = app_agent.lambda_handler(agent_evt({**base, "enforce": False}, {"X-Naka-Key": "nope"}), None)
    assert wrong["statusCode"] in (401, 403), f"shadow mode accepted a wrong key: {wrong}"

    bad_type = app_agent.lambda_handler(agent_evt({**base, "enforce": "false"}), None)
    assert bad_type["statusCode"] == 400, bad_type

    # Enforcing is the default and must never require a secret: getting past
    # this check means it reached the model call, which is allowed to fail.
    default = app_agent.lambda_handler(agent_evt(base), None)
    assert default["statusCode"] != 401, "the PROTECTING path must not require a key"
    return "401/403 without key, 400 on non-boolean, default path keyless"


@check("GET /session/<unknown> is a 404, not an empty 200")
def _t():
    need("dynamodb")
    resp = app_control.lambda_handler(_evt("GET", "/session/does-not-exist"), None)
    assert resp["statusCode"] == 404, resp


@check("static routes serve the UI and refuse traversal")
def _t():
    index = app_control.lambda_handler(_evt("GET", "/"), None)
    assert index["statusCode"] == 200, index
    assert "<html" in index["body"].lower(), index["body"][:200]
    for attack in ("/../config.py", "/../../etc/passwd", "/..%2fconfig.py"):
        resp = app_control.lambda_handler(_evt("GET", attack), None)
        assert resp["statusCode"] == 404, f"{attack} -> {resp['statusCode']}"
    return "index.html served, 3 traversal attempts refused"


# ---------------------------------------------------------------------------
# Cleanup + summary
# ---------------------------------------------------------------------------


def cleanup() -> None:
    if not REACHABLE.get("dynamodb"):
        return
    seen = set()
    for key in WROTE_KEYS:
        ident = (key["pk"]["S"], key["sk"]["S"])
        if ident in seen:
            continue
        seen.add(ident)
        try:
            _ddb.delete_item(TableName=CFG.audit_table, Key=key)
        except Exception:  # noqa: BLE001
            pass
    # The guard hops wrote their own audit rows under SESSION#<id>-a..e.
    for suffix in ("", "-a", "-b", "-c", "-d", "-e"):
        pk = f"SESSION#{SESSION_ID}{suffix}"
        try:
            resp = _ddb.query(
                TableName=CFG.audit_table,
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": {"S": pk}},
            )
        except Exception:  # noqa: BLE001
            continue
        for item in resp.get("Items", []):
            try:
                _ddb.delete_item(TableName=CFG.audit_table, Key={"pk": item["pk"], "sk": item["sk"]})
            except Exception:  # noqa: BLE001
                pass
    print(f"\n  cleaned up test rows under SESSION#{SESSION_ID}*")


if __name__ == "__main__":
    cleanup()
    passed = sum(1 for s, _, _ in _results if s == PASS)
    failed = [(n, d) for s, n, d in _results if s == FAIL]
    skipped = [(n, d) for s, n, d in _results if s == SKIP]

    print("\n" + "=" * 72)
    print(f"  {passed} passed, {len(failed)} failed, {len(skipped)} skipped")
    if skipped:
        print("\n  skipped (service unreachable — not a code failure):")
        for n, d in skipped:
            print(f"    - {n}" + (f" ({d})" if d else ""))
    if failed:
        print("\n  FAILED:")
        for n, d in failed:
            print(f"    - {n}: {d}")
    print("=" * 72)
    sys.exit(1 if failed else 0)
