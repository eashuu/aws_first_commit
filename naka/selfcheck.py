"""Run as `python selfcheck.py`. Exits non-zero on the first round of
failures. No pytest, no fixtures directory, no mocking framework — this
file exercises the non-obvious logic directly (TD §9), not a general test
suite. AWS-backed paths (Comprehend, Textract, DynamoDB, Bedrock) are
exercised elsewhere via injectable `client=` params; this file covers what
needs zero network access to get right the first time.
"""

from __future__ import annotations

import random
import sys

import cedarpy
from strands.interventions import Proceed, Transform

import detect
import guard as guard_mod
import ledger as ledger_mod
import policy
import rehydrate
from cedar_q2 import FieldDecision

FAILURES = 0


def check(name: str, condition: bool) -> None:
    global FAILURES
    print(f"[{'ok' if condition else 'FAIL'}] {name}")
    if not condition:
        FAILURES += 1


# --- Verhoeff (TD §9.1) -----------------------------------------------------


def test_verhoeff() -> None:
    random.seed(1234)
    bases = [f"{random.randint(0, 10**11 - 1):011d}" for _ in range(20)]
    fulls = [base + detect._verhoeff_check_digit(base) for base in bases]
    check("20 random generate/validate round-trips all valid", all(detect.verhoeff_valid(f) for f in fulls))

    base_full = fulls[0]
    total = rejected = 0
    for pos in range(len(base_full)):
        for d in "0123456789":
            if d == base_full[pos]:
                continue
            mutated = base_full[:pos] + d + base_full[pos + 1 :]
            total += 1
            rejected += not detect.verhoeff_valid(mutated)
    check(f"every single-digit mutation rejected ({total} tried)", rejected == total)

    total = rejected = 0
    for pos in range(len(base_full) - 1):
        if base_full[pos] == base_full[pos + 1]:
            continue
        swapped = base_full[:pos] + base_full[pos + 1] + base_full[pos] + base_full[pos + 2 :]
        total += 1
        rejected += not detect.verhoeff_valid(swapped)
    check(
        f"every adjacent-pair transposition rejected ({total} tried) — the Luhn discriminator",
        rejected == total and total > 0,
    )

    check("empty string invalid", detect.verhoeff_valid("") is False)
    check("non-digit string invalid", detect.verhoeff_valid("abc") is False)
    check("caller must strip separators — raw string is invalid", detect.verhoeff_valid("1234-5678-9012") is False)
    check("leading zero survives (no int() anywhere)", detect.verhoeff_valid("048273915604"))

    ocr_hit = detect.tier1_checksum("aadhaar: 163940582714", ocr_sourced=True)
    check(
        "OCR path: a checksum-failing 12-digit run still emits, at score<0.5, ocr_derived",
        any(e.type == "IN_AADHAAR" and e.ocr_derived and e.score < 0.5 for e in ocr_hit),
    )
    non_ocr_hit = detect.tier1_checksum("aadhaar: 163940582714", ocr_sourced=False)
    check(
        "non-OCR path: the same failing run emits nothing (false-positive rejection)",
        not any(e.type == "IN_AADHAAR" for e in non_ocr_hit),
    )

    valid_fixtures = ["048273915604", "163940582713", "095713604829", "137460298151"]
    check("all four demo Aadhaar fixtures verify", all(detect.verhoeff_valid(n) for n in valid_fixtures))


def test_pan() -> None:
    check("valid PAN accepted", detect.pan_valid("AZKPR0000M"))
    check("bad holder-type char rejected", not detect.pan_valid("AZKXR0000M"))
    check("lowercase rejected (PAN is canonically uppercase)", not detect.pan_valid("azkpr0000m"))
    for pan in ("AZKPR0000M", "BQTPN0000K", "CLMPQ0000J", "DXVPD0000F"):
        check(f"demo PAN fixture {pan} valid", detect.pan_valid(pan))


# --- Offset-preserving redaction (TD §9.2) ----------------------------------


def _rehydrate_all(text: str, vault: rehydrate.Vault) -> str:
    for token in vault.tokens():
        text = text.replace(token, vault.resolve(token))
    return text


def test_redact_offsets() -> None:
    text = "aadhaar: 0482 7391 5604 and pan: AZKPR0000M end"
    ents = detect.tier1_checksum(text)
    check("two entities detected in one string", len(ents) == 2)

    decisions = {e.type: FieldDecision("s", e.type, False, "p") for e in ents}
    vault = rehydrate.Vault(nonce="aaaa")
    new_text, masked, revealed, mask_policies = guard_mod._redact(text, ents, decisions, vault=vault)
    check("both entities masked", masked == {"IN_AADHAAR": 1, "IN_PERMANENT_ACCOUNT_NUMBER": 1})
    check("nothing revealed", revealed == {})
    check(
        "neither original value appears in the redacted text",
        "0482 7391 5604" not in new_text and "AZKPR0000M" not in new_text,
    )
    check("rehydrate(redact(text)) == text", _rehydrate_all(new_text, vault) == text)

    # Entity at offset 0 and one at the very end of the string.
    text2 = "0482 7391 5604 tail AZKPR0000M"
    ents2 = detect.tier1_checksum(text2)
    vault2 = rehydrate.Vault(nonce="bbbb")
    decisions2 = {e.type: FieldDecision("s", e.type, False, None) for e in ents2}
    new_text2, *_ = guard_mod._redact(text2, ents2, decisions2, vault=vault2)
    check("offset-0 and end-of-string entities both round-trip", _rehydrate_all(new_text2, vault2) == text2)

    # Only revealed fields spend — masked ones must not appear in `revealed`.
    ents3 = detect.tier1_checksum("pan: AZKPR0000M")
    decisions3 = {e.type: FieldDecision("s", e.type, True, None) for e in ents3}
    vault3 = rehydrate.Vault()
    new_text3, masked3, revealed3, _ = guard_mod._redact("pan: AZKPR0000M", ents3, decisions3, vault=vault3)
    check("an allowed field is revealed, not masked", masked3 == {} and revealed3 == {"IN_PERMANENT_ACCOUNT_NUMBER": 1})
    check("revealed text is untouched", new_text3 == "pan: AZKPR0000M")


def test_vault() -> None:
    v = rehydrate.Vault(nonce="cccc")
    p1 = v.mint("PHONE", "+91 55501 84412")
    p2 = v.mint("PHONE", "+91 55501 84412")
    check("the same value mints one token, reused", p1.token == p2.token)
    check("an unminted token resolves to None", v.resolve("[PHONE_9_zzzz]") is None)

    v2 = rehydrate.Vault(nonce="dddd")
    v2.mint("PHONE", "+91 55501 84412")
    check("tokens from vault A do not resolve in vault B (nonce)", v2.resolve(p1.token) is None)


# --- Ledger accumulation (TD §9.4) ------------------------------------------


def test_ledger() -> None:
    l1 = ledger_mod.Ledger(session_id="s1", budget=3, session_ceiling=25)
    l1.add("cust_1", {"NAME"})
    l1.add("cust_1", {"NAME"})
    check("revealing NAME twice leaves count == 1 (a set, not a counter)", l1.count("cust_1") == 1)

    a = ledger_mod.Ledger(session_id="s1", budget=3, session_ceiling=25)
    a.add("cust_1", {"NAME"})
    other = ledger_mod.Ledger(session_id="s1", budget=3, session_ceiling=25)
    other.add("cust_1", {"PHONE"})
    a.merge(other)
    a.merge(other)
    check("merge is commutative/idempotent (A.merge(B) twice == union once)", a.subjects == {"cust_1": {"NAME", "PHONE"}})

    empty = ledger_mod.Ledger.from_state(None, session_id="s2", budget=3, session_ceiling=25)
    check("from_state(None) yields an empty ledger, not an error", empty.total() == 0)

    ceiling = ledger_mod.Ledger(session_id="s3", budget=3, session_ceiling=25)
    for i in range(26):
        ceiling.add(f"cust_{i}", {"NAME"})
    check("session_ceiling trips on 26 distinct subjects, 1 field each", ceiling.total() >= ceiling.session_ceiling)


# --- Cedar decisions with accumulated context (TD §9.5) ---------------------


def test_cedar_policy() -> None:
    with open("agent.cedar", encoding="utf-8") as f:
        cedar_text = f.read()
    check("agent.cedar passes its own policy floor", policy.floor_ok(cedar_text))
    ps = cedarpy.PolicySet.from_str(cedar_text)

    def q2(seen, seen_count, budget, action, role="analyst") -> bool:
        req = {
            "principal": 'User::"alice@example.com"',
            "action": f'Action::"{action}"',
            "resource": 'Subject::"cust_8814"',
            "context": {"session": {"role": role, "seen": seen, "seen_count": seen_count, "budget": budget}},
        }
        return cedarpy.is_authorized(req, ps, []).allowed

    check("reveal_PHONE, seen=[] -> Allow", q2([], 0, 3, "reveal_PHONE"))
    check(
        "reveal_PHONE, seen=[NAME] -> Allow — the proof the enricher reaches policy (the critical beat)",
        q2(["NAME"], 1, 3, "reveal_PHONE"),
    )
    check("reveal_IN_AADHAAR, analyst -> Deny regardless of seen", not q2([], 0, 3, "reveal_IN_AADHAAR"))
    check("seen_count == budget -> Deny (>= not >)", not q2(["A", "B", "C"], 3, 3, "reveal_NAME"))
    check("seen_count < budget -> Allow", q2(["A", "B"], 2, 3, "reveal_NAME"))
    check("role=compliance -> Allow everything, even Aadhaar", q2([], 0, 3, "reveal_IN_AADHAAR", role="compliance"))

    def q1(action, role="analyst") -> bool:
        req = {
            "principal": 'User::"alice@example.com"',
            "action": f'Action::"{action}"',
            "resource": 'Resource::"agent"',
            "context": {"session": {"role": role, "seen": ["A", "B", "C"], "seen_count": 3, "budget": 3}},
        }
        return cedarpy.is_authorized(req, ps, []).allowed

    check(
        "send_summary allowed even with budget exhausted — the ceiling must not gate the call itself",
        q1("send_summary"),
    )

    def q3(action, dest) -> bool:
        req = {
            "principal": 'User::"alice@example.com"',
            "action": f'Action::"{action}"',
            "resource": f'Destination::"{dest}"',
            "context": {"session": {"role": "analyst"}},
        }
        return cedarpy.is_authorized(req, ps, []).allowed

    check("rehydrate_IN_AADHAAR -> pastebin denied (default-deny)", not q3("rehydrate_IN_AADHAAR", "notes.pastebin.example"))
    check("rehydrate_IN_AADHAAR -> kyc-vault allowed", q3("rehydrate_IN_AADHAAR", "kyc-vault.internal"))


# --- Audit row never leaks a value (TD §9.6) --------------------------------


def test_audit_row_no_leak() -> None:
    import json as _json
    from dataclasses import asdict

    from audit import AuditRow

    SENTINEL_AADHAAR = "0482 7391 5604"
    row = AuditRow(
        session_id="s1",
        seq=1,
        ts="2026-01-01T00:00:00+00:00",
        invocation_id="i1",
        principal="alice@example.com",
        role="analyst",
        subject="cust_8814",
        tool="fetch_customer",
        call_decision="ALLOW",
        deny_policy=None,
        content_type="application/json",
        pages=1,
        truncated=False,
        detector_tiers=["checksum"],
        entities_found={"IN_AADHAAR": 1},
        entities_masked={"IN_AADHAAR": 1},
        entities_revealed={},
        mask_policies={"IN_AADHAAR": "q2_forbid_aadhaar_analyst"},
        ledger_before=[],
        ledger_after=[],
        budget=3,
        session_total=1,
        rehydrated=[],
        outcome="ok",
        latency_ms={"total": 10},
        policy_version="v1",
    )
    dumped = _json.dumps(asdict(row))
    check("the audit row's own JSON never contains the fixture's entity value", SENTINEL_AADHAAR not in dumped)


def test_multipage_withheld() -> None:
    import normalize

    class _FakeTextract:
        def detect_document_text(self, Document):
            return {"DocumentMetadata": {"Pages": 2}, "Blocks": [{"BlockType": "LINE", "Text": "page one"}]}

    try:
        normalize._textract_extract(b"%PDF-fake", source_media_type="application/pdf", cfg=None, strict_lines=True, client=_FakeTextract())
        check("a 2-page PDF raises NormalizeError('multipage')", False)
    except normalize.NormalizeError as exc:
        check("a 2-page PDF raises NormalizeError('multipage'), not a partial scan", exc.reason == "multipage")


# --- merge() containment and rank resolution (found untested in review) ----


def test_merge_containment() -> None:
    gstin = detect.Entity("IN_GSTIN", 0, 15, 0.85, "checksum")
    pan_inner = detect.Entity("IN_PERMANENT_ACCOUNT_NUMBER", 2, 12, 1.0, "checksum")
    merged = detect.merge([gstin, pan_inner])
    check(
        "a more-specific container (IN_GSTIN) absorbs a less-specific contained entity (PAN)",
        len(merged) == 1 and merged[0].type == "IN_GSTIN",
    )

    address = detect.Entity("ADDRESS", 0, 40, 0.9, "comprehend")
    name_inner = detect.Entity("NAME", 5, 12, 0.9, "comprehend")
    merged2 = detect.merge([address, name_inner])
    check(
        "a less-specific container (ADDRESS) must NOT absorb a more-specific contained entity (NAME)",
        len(merged2) == 2 and {e.type for e in merged2} == {"ADDRESS", "NAME"},
    )

    dup_checksum = detect.Entity("IN_AADHAAR", 10, 22, 1.0, "checksum")
    dup_comprehend = detect.Entity("OTHER", 10, 22, 0.5, "comprehend")
    merged3 = detect.merge([dup_comprehend], [dup_checksum])
    check(
        "identical span from two tiers: the checksum-tier type wins, score is max()",
        len(merged3) == 1 and merged3[0].type == "IN_AADHAAR" and merged3[0].tier == "checksum",
    )


# --- Comprehend chunk-offset math (pure Python, needs no AWS call) ---------


def test_chunk_offsets() -> None:
    chunk_bytes, overlap = 50, 10
    text = ("x" * 40 + "\n") * 5  # 205 chars, several chunks at this size

    chunks, covered_all = detect._chunk_text(text, chunk_bytes, overlap, max_chunks=100)
    check("a generous max_chunks covers the whole text", covered_all)
    check(
        "every (start, chunk) pair matches the source text at that offset",
        all(text[start : start + len(chunk)] == chunk for start, chunk in chunks),
    )

    marker = "MARKERVALUE"
    padded = ("a" * 45) + marker + ("b" * 45)
    chunks2, _ = detect._chunk_text(padded, chunk_bytes, overlap, max_chunks=100)
    found_at = [start + chunk.find(marker) for start, chunk in chunks2 if marker in chunk]
    check(
        "a marker near a chunk boundary maps back to its true absolute offset (chunk_start + local offset)",
        len(found_at) > 0 and all(padded[p : p + len(marker)] == marker for p in found_at),
    )

    chunks3, covered_all3 = detect._chunk_text(text, chunk_bytes, overlap, max_chunks=1)
    check("hitting max_chunks reports covered_all=False, not a silent clean finish", not covered_all3)
    covered_chars3 = chunks3[-1][0] + len(chunks3[-1][1]) if chunks3 else 0
    check("the reported coverage boundary is strictly short of the full text", covered_chars3 < len(text))


# --- canonical_subject (the anti-budget-bypass normalization) --------------


def test_canonical_subject() -> None:
    import attribute

    check(
        "case/whitespace variants of the same id collapse to one subject",
        attribute.canonical_subject("CUST_8814 ", session_id="s1")
        == attribute.canonical_subject("cust_8814", session_id="s1"),
    )
    check(
        "None falls back to a shared per-session unattributed bucket",
        attribute.canonical_subject(None, session_id="s1") == "unattributed:s1",
    )
    check(
        "empty string falls back the same way as None",
        attribute.canonical_subject("", session_id="s1") == "unattributed:s1",
    )
    check(
        "internal whitespace collapses too",
        attribute.canonical_subject("  cust   8814  ", session_id="s1") == "cust 8814",
    )


# --- Rehydrator: the Python glue, not just the Cedar policy text -----------


class _FakeEvent:
    def __init__(self, tool_use: dict):
        self.tool_use = tool_use


def test_rehydrator() -> None:
    from strands.interventions import Deny, Proceed

    with open("agent.cedar", encoding="utf-8") as f:
        ps = cedarpy.PolicySet.from_str(f.read())

    class _Bundle:
        policy_set = ps

    vault = rehydrate.Vault(nonce="9999")
    aadhaar_token = vault.mint("IN_AADHAAR", "0482 7391 5604")
    r = rehydrate.Rehydrator(vault=vault, principal="alice@example.com", role="analyst", policy=_Bundle())

    ev_ok = _FakeEvent(
        {
            "name": "send_summary",
            "toolUseId": "tu1",
            "input": {"to": "KYC-Vault.Internal", "body": f"Aadhaar: {aadhaar_token.token}"},
        }
    )
    action_ok = r.before_tool_call(ev_ok)
    check("allows and substitutes for an authorized destination, even mixed-case", isinstance(action_ok, Proceed))
    check(
        "the substituted body carries the real value, not the token",
        ev_ok.tool_use["input"]["body"] == "Aadhaar: 0482 7391 5604",
    )
    check(
        "the resolved token is tracked by toolUseId, for the audit row's `rehydrated` field",
        r.resolved_by_call.get("tu1") == [aadhaar_token.token],
    )

    other_token = vault.mint("IN_AADHAAR", "0957 1360 4829")
    ev_bad_dest = _FakeEvent(
        {
            "name": "send_summary",
            "toolUseId": "tu2",
            "input": {"to": "notes.pastebin.example", "body": f"Aadhaar: {other_token.token}"},
        }
    )
    action_bad_dest = r.before_tool_call(ev_bad_dest)
    check("denies rehydration into an unauthorized destination", isinstance(action_bad_dest, Deny))
    check("a denied call is not recorded as resolved", "tu2" not in r.resolved_by_call)

    # "abcd" is a well-formed nonce (TOKEN_RE requires 4 lowercase hex
    # digits) that was never actually minted by this vault — distinct from a
    # malformed lookalike, which TOKEN_RE wouldn't match as a token at all.
    ev_unminted = _FakeEvent(
        {"name": "send_summary", "toolUseId": "tu3", "input": {"to": "kyc-vault.internal", "body": "[IN_AADHAAR_99_abcd]"}}
    )
    check("an unminted/unknown token is denied, never passed through", isinstance(r.before_tool_call(ev_unminted), Deny))

    ev_none = _FakeEvent({"name": "fetch_customer", "toolUseId": "tu4", "input": {"customer_id": "cust_8814"}})
    check("a call with no placeholder proceeds untouched", isinstance(r.before_tool_call(ev_none), Proceed))


# --- redact(): genuinely overlapping (not nested) denied spans -------------


def test_redact_partial_overlap() -> None:
    text = "AAAAAAAAAABBBBBBBBBBCCCCCCCCCC"  # 30 chars: 3 blocks of 10
    e1 = detect.Entity("NAME", 5, 17, 0.9, "comprehend")  # tail of A + head of B
    e2 = detect.Entity("NAME", 13, 25, 0.9, "comprehend")  # tail of B + head of C — overlaps e1, neither contains the other
    decisions = {"NAME": FieldDecision("s", "NAME", False, None)}
    vault = rehydrate.Vault(nonce="eeee")
    new_text, masked, revealed, _ = guard_mod._redact(text, [e1, e2], decisions, vault=vault)
    check(
        "two genuinely overlapping denied spans collapse into exactly one placeholder",
        masked == {"NAME": 2} and new_text.count("[NAME_") == 1,
    )
    check(
        "the untouched prefix/suffix outside both spans survive intact",
        new_text.startswith(text[:5]) and new_text.endswith(text[25:]),
    )


# --- Shadow mode (enforce=False) --------------------------------------------
#
# The guarded/unguarded comparison is only worth showing if the unguarded run
# is the SAME code with enforcement switched off. These checks pin exactly
# that: one fixture, one policy, two runs, and the only differences permitted
# are the ones shadow mode is defined to have.

SHADOW_TEXT = "name: Priya Sharma, aadhaar: 0482 7391 5604, pan: AZKPR0000M"


def _shadow_harness(*, enforce: bool):
    """Drive DisclosureGuard._guard_result end to end with the normalizer,
    detector and DynamoDB writer stubbed, so this needs no network. Returns
    (result, hop, state, outcome)."""
    import types

    import normalize as normalize_mod

    cfg = types.SimpleNamespace(indic_enabled=False, fallback_policy_path="agent.cedar")
    bundle = policy._bundle_from_fallback(cfg)

    entities = detect.tier1_checksum(SHADOW_TEXT)
    assert len(entities) == 2, "fixture must carry exactly Aadhaar + PAN"

    led = ledger_mod.Ledger(session_id="s-shadow", subjects={}, budget=3, session_ceiling=10)

    def _fake_spend(session_id, subject, types_, *, cfg):
        before = led.seen(subject)
        led.add(subject, types_)
        return before, led.seen(subject)

    saved = (normalize_mod.normalize, detect.detect, ledger_mod.spend)
    normalize_mod.normalize = lambda payload, media_type, *, cfg: normalize_mod.Normalized(
        markdown=SHADOW_TEXT, source_media_type="text/plain", pages=1, words=None, truncated=False, ocr_sourced=False
    )
    detect.detect = lambda text, **kw: detect.DetectResult(entities=entities, tiers=["checksum"])
    ledger_mod.spend = _fake_spend

    try:
        guard = guard_mod.DisclosureGuard(
            session_id="s-shadow",
            principal="alice@example.com",
            role="analyst",
            vault=rehydrate.Vault(nonce="cccc"),
            ledger=led,
            policy=bundle,
            cfg=cfg,
            enforce=enforce,
        )

        result = {"status": "success", "content": [{"text": SHADOW_TEXT}]}

        class _State:
            def __init__(self):
                self.written = {}

            def set(self, k, v):
                self.written[k] = v

        state = _State()
        event = types.SimpleNamespace(
            tool_use={"name": "fetch_customer", "toolUseId": "tu-1", "input": {"customer_id": "cust_8814"}},
            result=result,
            agent=types.SimpleNamespace(state=state),
        )

        outcome = guard._guard_result(event, subject="cust_8814", t0=0.0, tool_use_id="tu-1")
        # A Transform carries a callable the framework applies later; a
        # Proceed does not. Apply it here so `result` holds what the model
        # would actually have received.
        if isinstance(outcome, Transform):
            outcome.apply(event)
        return result, guard.hop_outcomes["tu-1"], state, outcome
    finally:
        normalize_mod.normalize, detect.detect, ledger_mod.spend = saved


def test_shadow_mode() -> None:
    enforced_result, enforced_hop, enforced_state, _ = _shadow_harness(enforce=True)
    shadow_result, shadow_hop, shadow_state, shadow_outcome = _shadow_harness(enforce=False)

    enforced_text = enforced_result["content"][0]["text"]
    shadow_text = shadow_result["content"][0]["text"]

    check("enforced: the Aadhaar never reaches the model", "0482 7391 5604" not in enforced_text)
    check(
        "shadow: the payload arrives byte-identical - an altered 'unguarded' run would prove nothing",
        shadow_text == SHADOW_TEXT and isinstance(shadow_outcome, Proceed),
    )
    check(
        "shadow still DECIDED: would_mask holds exactly what the enforced run masked",
        shadow_hop.would_mask == enforced_hop.entities_masked and shadow_hop.would_mask.get("IN_AADHAAR") == 1,
    )
    check("shadow reports nothing masked, because nothing was", shadow_hop.entities_masked == {})
    check(
        "both runs detect identically - enforcement is the only variable",
        shadow_hop.entities_found == enforced_hop.entities_found,
    )
    check(
        "shadow counts the Aadhaar as revealed; the enforced run does not",
        "IN_AADHAAR" in shadow_hop.entities_revealed and "IN_AADHAAR" not in enforced_hop.entities_revealed,
    )
    check(
        "shadow's ledger therefore accumulates further than the enforced run's",
        len(shadow_hop.ledger_after) > len(enforced_hop.ledger_after),
    )
    check(
        "each hop is tagged with the mode that produced it",
        shadow_hop.enforce is False and enforced_hop.enforce is True,
    )
    check(
        "shadow never writes the ledger cache - a measurement run cannot inflate a real session's budget",
        "disclosure_ledger" not in shadow_state.written and "disclosure_ledger" in enforced_state.written,
    )


def test_shadow_never_alters_traffic() -> None:
    """_withhold is the only place the guard blanks a payload it could not
    inspect. Shadow mode must not, or "shadow cannot break anything" is a
    false promise."""
    import types

    cfg = types.SimpleNamespace(indic_enabled=False, fallback_policy_path="agent.cedar")
    bundle = policy._bundle_from_fallback(cfg)

    def _guard(enforce: bool):
        return guard_mod.DisclosureGuard(
            session_id="s", principal="a@b.c", role="analyst", vault=rehydrate.Vault(),
            ledger=ledger_mod.Ledger(session_id="s", subjects={}, budget=3, session_ceiling=10),
            policy=bundle, cfg=cfg, enforce=enforce,
        )

    res = {"status": "success", "content": [{"text": "sensitive"}]}
    enforced_out = _guard(True)._withhold("detector unavailable (comprehend)")
    enforced_out.apply(types.SimpleNamespace(result=res))
    check(
        "enforced: an uninspectable payload is blanked behind the WITHHELD notice",
        "sensitive" not in res["content"][0]["text"],
    )
    check(
        "shadow: an uninspectable payload passes through untouched",
        isinstance(_guard(False)._withhold("detector unavailable (comprehend)"), Proceed),
    )


def main() -> None:
    test_verhoeff()
    test_pan()
    test_redact_offsets()
    test_vault()
    test_ledger()
    test_cedar_policy()
    test_audit_row_no_leak()
    test_multipage_withheld()
    test_merge_containment()
    test_chunk_offsets()
    test_canonical_subject()
    test_rehydrator()
    test_redact_partial_overlap()
    test_shadow_mode()
    test_shadow_never_alters_traffic()

    print()
    if FAILURES:
        print(f"{FAILURES} check(s) FAILED")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
