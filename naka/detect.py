"""Three detection tiers, cheapest first. Run all of them and merge — never
short-circuit. A tier may only ever *add* findings; no tier can clear
another's (PRD §8).

Tier 1 — local Verhoeff/PAN checksum. Zero latency, zero cost, written fresh
during this session from the published D5 dihedral-group tables (Verhoeff's
own construction, not anyone's implementation of it).

Tier 2 — Amazon Comprehend DetectPiiEntities. Everything else.

Tier 3 — Nova Pro multimodal, additive-only, for Indic-script content
Textract cannot OCR. Never trusted as authoritative: every returned
substring is verified with str.find() against the source text before it
becomes a finding.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal

from config import Config

TierName = Literal["checksum", "comprehend", "indic"]


@dataclass(frozen=True, slots=True)
class Entity:
    type: str
    begin: int
    end: int
    score: float
    tier: TierName
    ocr_derived: bool = False


@dataclass(frozen=True, slots=True)
class DetectResult:
    entities: list[Entity]
    tiers: list[str]  # tiers that actually contributed or ran, for the audit row
    tier3_attempted: bool = False
    tier3_ok: bool = True  # False = tier3 was attempted and failed (§5.1 row)
    covered_chars: int | None = None  # None = fully covered; else the offset Comprehend reached
    # Tiers that could not run at all. Non-empty means this result describes
    # a NARROWER scan than the full pipeline, and every consumer — audit row,
    # UI, operator — must be able to tell that apart from "scanned clean".
    tiers_unavailable: list[str] = field(default_factory=list)


class DetectorUnavailable(Exception):
    def __init__(self, tier: str, message: str = ""):
        super().__init__(message or f"detector unavailable: {tier}")
        self.tier = tier


# ---------------------------------------------------------------------------
# Tier 1 — Verhoeff (Aadhaar) and PAN
# ---------------------------------------------------------------------------

# The published D5 (dihedral group of order 10) multiplication table.
# D[j][k] = j * k in the group used by the Verhoeff algorithm.
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# The permutation table, period 8. P[i % 8][digit].
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# The multiplicative inverse in D5.
_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def only_digits(s: str) -> str:
    """Strip everything but digits. Callers do this before verhoeff_valid —
    the validator itself never strips, so a caller that forgets to call this
    fails loudly (a non-digit string is simply invalid) rather than silently
    validating something that was never a clean digit string."""
    return "".join(ch for ch in s if ch.isdigit())


def verhoeff_valid(digits: str) -> bool:
    """True iff `digits` (a string of ASCII digits only, in the order they
    are printed — the check digit is the last one) satisfies the Verhoeff
    checksum. Empty or non-digit input is False, not an error: a checksum
    validator's job is to answer the question, not to clean the input."""
    if not digits or not digits.isdigit():
        return False
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def _verhoeff_check_digit(base: str) -> str:
    """Given the payload digits (without a check digit), return the check
    digit that makes the full number valid. Used only by selfcheck.py to
    build fixtures — never in the detection path, which only ever validates."""
    if not base or not base.isdigit():
        raise ValueError("base must be a non-empty digit string")
    c = 0
    for i, ch in enumerate(reversed(base)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][int(ch)]]
    return str(_VERHOEFF_INV[c])


# 4-4-4 grouped or bare 12-digit runs. Negative lookaround on both sides so a
# 13+ digit run never contributes a false 12-digit substring.
_AADHAAR_CANDIDATE_RE = re.compile(
    r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)"
)

_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
# 4th character encodes holder type: P Individual, C Company, H HUF, F Firm,
# A AOP, T Trust, B BOI, L Local authority, J Artificial juridical, G Govt.
_PAN_HOLDER_TYPES = frozenset("PCHFATBLJG")


def pan_valid(s: str) -> bool:
    if not _PAN_RE.fullmatch(s):
        return False
    return s[3] in _PAN_HOLDER_TYPES


# GSTIN: 2-digit state code + 10-char PAN + 1 entity code + fixed 'Z' + 1
# check character. The check character has a published mod-36 (Luhn-style)
# algorithm, but — same honesty call this project already makes for PAN
# (TD/doc10 §1.2: "the check digit algorithm is deliberately unpublished") —
# it is not implemented here because it could not be verified against an
# authoritative primary source during this session. Format plus the
# state-code range (01-38, the current count of Indian states/UTs with a GST
# code) is the achievable guarantee, same tier as PAN's holder-type check:
# narrower than "any 15-char alphanumeric string", not a cryptographic proof.
_GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")


def gstin_valid(s: str) -> bool:
    if not _GSTIN_RE.fullmatch(s):
        return False
    state_code = int(s[:2])
    return 1 <= state_code <= 38 and pan_valid(s[2:12])


# IFSC: 4-letter bank code + fixed '0' (reserved for future use) + 6
# alphanumeric branch code. Format-only — IFSC has no public check digit.
_IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")


def ifsc_valid(s: str) -> bool:
    return bool(_IFSC_RE.fullmatch(s))


# Voter ID / EPIC, the older and still most common format: 3 letters + 7
# digits. (A newer 10-character all-alphanumeric format also circulates;
# out of scope here — format-only, no public check digit either way.)
_VOTER_ID_RE = re.compile(r"\b[A-Z]{3}[0-9]{7}\b")


def voter_id_valid(s: str) -> bool:
    return bool(_VOTER_ID_RE.fullmatch(s))


def tier1_checksum(text: str, *, ocr_sourced: bool = False) -> list[Entity]:
    out: list[Entity] = []

    for m in _AADHAAR_CANDIDATE_RE.finditer(text):
        digits = only_digits(m.group())
        if len(digits) != 12:
            continue
        if verhoeff_valid(digits):
            out.append(Entity("IN_AADHAAR", m.start(), m.end(), 1.0, "checksum"))
        elif ocr_sourced:
            # Checksum is a confidence signal, not a gate, on OCR text: a
            # real Aadhaar with one misread digit fails Verhoeff and would
            # otherwise vanish silently (PRD §8).
            out.append(
                Entity("IN_AADHAAR", m.start(), m.end(), 0.45, "checksum", ocr_derived=True)
            )
        # else: not ocr_sourced and fails Verhoeff -> not an Aadhaar, no entity.
        # This is the false-positive rejection the checksum tier exists for.

    for m in _PAN_RE.finditer(text):
        if pan_valid(m.group()):
            out.append(
                Entity("IN_PERMANENT_ACCOUNT_NUMBER", m.start(), m.end(), 1.0, "checksum")
            )

    for m in _GSTIN_RE.finditer(text):
        if gstin_valid(m.group()):
            out.append(Entity("IN_GSTIN", m.start(), m.end(), 0.85, "checksum"))

    for m in _IFSC_RE.finditer(text):
        if ifsc_valid(m.group()):
            out.append(Entity("IN_IFSC", m.start(), m.end(), 0.7, "checksum"))

    for m in _VOTER_ID_RE.finditer(text):
        if voter_id_valid(m.group()):
            out.append(Entity("IN_VOTER_NUMBER", m.start(), m.end(), 0.7, "checksum"))

    return out


# ---------------------------------------------------------------------------
# Tier 2 — Comprehend
# ---------------------------------------------------------------------------

_comprehend_client_cache = {}


def _comprehend_client(cfg: Config):
    client = _comprehend_client_cache.get("client")
    if client is not None:
        return client
    import boto3
    from botocore.config import Config as BotoConfig

    client = boto3.client(
        "comprehend",
        region_name=cfg.aws_region,
        config=BotoConfig(
            connect_timeout=1,
            read_timeout=cfg.timeout_comprehend_s,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )
    _comprehend_client_cache["client"] = client
    return client


def _chunk_text(text: str, chunk_bytes: int, overlap_chars: int, max_chunks: int) -> tuple[list[tuple[int, str]], bool]:
    """Split `text` into (start_offset, chunk) pairs, each under
    `chunk_bytes` UTF-8 bytes, splitting on the last newline before the
    boundary when one exists, carrying `overlap_chars` forward so an entity
    straddling a chunk edge is still seen whole in the next chunk.

    Returns (chunks, covered_all). `max_chunks` is a cost bound
    (MAX_CHUNKS_PER_HOP): hitting it means the tail of the text was never
    chunked at all, and therefore never sent to Comprehend — the caller
    must treat `covered_all=False` as a truncation, not a clean finish,
    exactly like normalize.py's own `truncated` flag."""
    n = len(text)
    if n == 0:
        return [], True
    chunks: list[tuple[int, str]] = []
    start = 0
    while start < n and len(chunks) < max_chunks:
        end = min(n, start + chunk_bytes)
        while end > start and len(text[start:end].encode("utf-8")) > chunk_bytes:
            end -= 1
        if end < n:
            nl = text.rfind("\n", start, end)
            if nl > start:
                end = nl + 1
        if end <= start:
            end = min(n, start + 1)
        chunks.append((start, text[start:end]))
        if end >= n:
            break
        start = max(start + 1, end - overlap_chars)
    covered_all = bool(chunks) and chunks[-1][0] + len(chunks[-1][1]) >= n
    return chunks, covered_all


def tier2_comprehend(
    text: str, *, min_score: float, cfg: Config, client=None
) -> tuple[list[Entity], int]:
    """One DetectPiiEntities call per chunk. Raises DetectorUnavailable on
    any failure — the caller (guard.py) fails the whole hop closed rather
    than release content Comprehend never actually scanned.

    Returns (entities, covered_chars) — covered_chars is how much of `text`
    the chunking actually reached. `MAX_CHUNKS_PER_HOP` is a documented cost
    bound whose own contract (config.py) is "exceeding it withholds the
    remainder" — when covered_chars < len(text), the caller MUST NOT release
    anything past that offset, or unscanned text passes straight through as
    if Comprehend had cleared it."""
    if not text:
        return [], 0
    client = client or _comprehend_client(cfg)
    chunks, covered_all = _chunk_text(
        text, cfg.comprehend_chunk_bytes, cfg.comprehend_chunk_overlap, cfg.max_chunks_per_hop
    )
    covered_chars = (chunks[-1][0] + len(chunks[-1][1])) if chunks else 0
    if not covered_all:
        covered_chars = min(covered_chars, len(text))
    out: list[Entity] = []
    for chunk_start, chunk in chunks:
        try:
            resp = client.detect_pii_entities(Text=chunk, LanguageCode=cfg.comprehend_language)
        except Exception as exc:  # noqa: BLE001 — anything here means "withhold"
            raise DetectorUnavailable("comprehend", str(type(exc).__name__)) from exc

        entities = resp.get("Entities")
        if entities is None:
            raise DetectorUnavailable("comprehend", "malformed response: no Entities")

        for e in entities:
            begin, end = e.get("BeginOffset"), e.get("EndOffset")
            score, etype = e.get("Score"), e.get("Type")
            if begin is None or end is None or end <= begin or score is None or not etype:
                continue  # malformed single entity: discard it, not the whole response
            if score < min_score:
                continue
            out.append(Entity(etype, begin + chunk_start, end + chunk_start, float(score), "comprehend"))
    return out, covered_chars


# ---------------------------------------------------------------------------
# Tier 3 — Indic, multimodal, additive-only
# ---------------------------------------------------------------------------

_INDIC_PROMPT = (
    "This image is a scanned identity or KYC document. Some text on it is "
    "printed in an Indian regional script (e.g. Devanagari, Tamil) alongside "
    "English. Return a JSON array only, no prose, of every name, address or "
    "other personal-data substring you can read, in this exact shape: "
    '[{"type": "NAME", "text": "<exact substring as it appears>"}]. '
    "Copy substrings exactly as printed. Do not translate, summarise, or "
    "invent text that is not visibly present."
)

_bedrock_client_cache = {}


def _bedrock_client(cfg: Config):
    client = _bedrock_client_cache.get("client")
    if client is not None:
        return client
    import boto3
    from botocore.config import Config as BotoConfig

    client = boto3.client(
        "bedrock-runtime",
        region_name=cfg.aws_region,
        config=BotoConfig(
            connect_timeout=1,
            read_timeout=cfg.timeout_indic_s,
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )
    _bedrock_client_cache["client"] = client
    return client


def tier3_indic(image: bytes, fmt: str, text: str, *, cfg: Config, client=None) -> list[Entity]:
    """Additive only, never authoritative (§7 threat 5). The model's output
    schema carries substrings only — no confidence override, no "clean"
    signal. Every substring is verified with str.find() before it becomes a
    finding; anything the model claims that isn't literally in `text` is
    dropped, never trusted."""
    if fmt not in ("png", "jpeg", "gif", "webp"):
        raise ValueError(f"unsupported image format for Bedrock ImageBlock: {fmt}")

    client = client or _bedrock_client(cfg)
    resp = client.converse(
        modelId=cfg.indic_model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {"image": {"format": fmt, "source": {"bytes": image}}},
                    {"text": _INDIC_PROMPT},
                ],
            }
        ],
    )
    content_blocks = resp.get("output", {}).get("message", {}).get("content", [])
    raw = "".join(b.get("text", "") for b in content_blocks)

    try:
        start = raw.index("[")
        end = raw.rindex("]") + 1
        candidates = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return []

    out: list[Entity] = []
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        etype, substring = cand.get("type"), cand.get("text")
        if not etype or not substring:
            continue
        pos = text.find(substring)
        if pos == -1:
            continue  # never trust it — drop, never approximate (§8)
        out.append(Entity(etype, pos, pos + len(substring), 0.6, "indic"))
    return out


# ---------------------------------------------------------------------------
# Merge — overlap resolution
# ---------------------------------------------------------------------------

# Specificity rank, highest first (PRD/TD §1.3 merge rule). Anything not
# listed (DATE_TIME, AGE, OTHER, ...) ranks below ADDRESS.
_RANK_ORDER = [
    "OTHER",
    "ADDRESS",
    "NAME",
    "EMAIL",
    "PHONE",
    "CREDIT_DEBIT_NUMBER",
    "IN_IFSC",
    "IN_NREGA",
    "IN_VOTER_NUMBER",
    "IN_PERMANENT_ACCOUNT_NUMBER",
    "IN_GSTIN",  # contains a PAN (chars 3-12) — must outrank it for containment
    "IN_AADHAAR",
]


def rank_of(entity_type: str) -> int:
    try:
        return _RANK_ORDER.index(entity_type)
    except ValueError:
        return 0  # unranked types sit alongside OTHER — no special standing


def merge(*groups: list[Entity]) -> list[Entity]:
    all_entities: list[Entity] = [e for g in groups for e in g]
    if not all_entities:
        return []

    # Step 1: exact-span dedup. Multiple tiers (or overlapping Comprehend
    # chunks) can produce identical (begin, end) spans; keep one.
    by_span: dict[tuple[int, int], Entity] = {}
    for e in all_entities:
        key = (e.begin, e.end)
        existing = by_span.get(key)
        if existing is None:
            by_span[key] = e
            continue
        if rank_of(e.type) > rank_of(existing.type):
            by_span[key] = e
        elif rank_of(e.type) == rank_of(existing.type):
            # Tie: prefer the checksum-tier hit, take the higher score.
            winner_tier = "checksum" if "checksum" in (e.tier, existing.tier) else existing.tier
            winner = e if e.tier == "checksum" else existing
            by_span[key] = Entity(
                winner.type, winner.begin, winner.end, max(e.score, existing.score), winner_tier
            )

    deduped = list(by_span.values())

    # Step 2: containment. Drop an entity fully inside a strictly MORE
    # specific entity's span. A less-specific container (e.g. ADDRESS
    # containing NAME) does NOT absorb the more-specific inner entity —
    # both survive and redact() applies them right-to-left (TD §9.2).
    dropped: set[tuple[int, int]] = set()
    for outer in deduped:
        for inner in deduped:
            if outer is inner:
                continue
            if (outer.begin, outer.end) == (inner.begin, inner.end):
                continue
            contained = outer.begin <= inner.begin and inner.end <= outer.end
            # `inner.type in _RANK_ORDER` is load-bearing, not defensive.
            # rank_of() returns 0 for anything unlisted, which is the same
            # rank as OTHER — so without this guard EVERY unranked type
            # (BANK_ACCOUNT_NUMBER, SSN, PASSPORT_NUMBER, DRIVER_ID, PIN,
            # PASSWORD, CREDIT_DEBIT_CVV, and even DATE_TIME and AGE, which
            # ARE in DEFAULT_IDENTIFYING_TYPES) is outranked by a merely
            # containing ADDRESS and silently dropped.
            #
            # That is a subtraction, and it fails open. Measured:
            #   merge([ADDRESS 6..45], [BANK_ACCOUNT_NUMBER 33..45])
            # returned [ADDRESS] alone. BANK_ACCOUNT_NUMBER has no reveal
            # permit so Cedar default-denies it and it would have been
            # masked; once dropped, the surviving ADDRESS is permitted by
            # q2_reveal_baseline and the whole span — account number
            # included — goes out in plaintext.
            #
            # An unranked inner type therefore never loses a containment
            # contest. "Tiers union, never subtract" has to hold here or it
            # does not hold at all.
            if contained and inner.type in _RANK_ORDER and rank_of(outer.type) > rank_of(inner.type):
                dropped.add((inner.begin, inner.end, inner.type))

    result = [e for e in deduped if (e.begin, e.end, e.type) not in dropped]
    result.sort(key=lambda e: (e.begin, -e.end))
    return result


def detect(
    text: str,
    *,
    ocr_sourced: bool,
    cfg: Config,
    min_score: float,
    image: bytes | None = None,
    image_fmt: str | None = None,
    indic_enabled: bool = True,
    degraded_ok: bool = False,
) -> DetectResult:
    """Run tiers in order, merge, sort by begin. Raises DetectorUnavailable
    if tier 2 fails — the caller must fail the hop closed.

    `degraded_ok=True` is the ONE exception, and it is never the default.
    It says: this caller has accepted, explicitly and in writing on screen,
    that tier 2 is unreachable on this account, and wants the tiers that
    CAN run to run anyway. Tier 1 is pure local arithmetic (Verhoeff, PAN /
    GSTIN / IFSC / voter-ID formats) with no AWS dependency, so it still
    produces real findings from real validation.

    The difference from a silent fail-open is that the unavailable tier is
    named in `tiers_unavailable`, carried into the audit row, and rendered
    in the UI — the result is labelled "scanned by checksum only", never
    "scanned clean". Conflating those two is the exact bug this product
    exists to prevent (PRD §6.3), so the degraded result must stay
    self-describing all the way to the screen."""
    tier1 = tier1_checksum(text, ocr_sourced=ocr_sourced)
    tiers_unavailable: list[str] = []
    try:
        tier2, covered_chars = tier2_comprehend(text, min_score=min_score, cfg=cfg)
    except DetectorUnavailable:
        if not degraded_ok:
            raise
        tier2, covered_chars = [], len(text)
        tiers_unavailable.append("comprehend")

    text_truncated = covered_chars < len(text)
    groups = [tier1, tier2]
    tiers_used = ["checksum"] if tiers_unavailable else ["checksum", "comprehend"]

    tier3_attempted = False
    tier3_ok = True
    if image is not None and indic_enabled:
        tier3_attempted = True
        try:
            tier3 = tier3_indic(image, image_fmt or "png", text, cfg=cfg)
            groups.append(tier3)
            tiers_used.append("indic")
        except Exception:  # noqa: BLE001 — tier 3 failing never blocks 1/2
            tier3_ok = False
            tiers_unavailable.append("indic")

    entities = merge(*groups)
    if text_truncated:
        # MAX_CHUNKS_PER_HOP's documented contract is "exceeding it withholds
        # the remainder" (config.py) — an entity that only exists past the
        # covered boundary is about to be in text guard.py will never
        # release, so it is not a finding here either.
        entities = [e for e in entities if e.end <= covered_chars]

    return DetectResult(
        entities=entities,
        tiers=tiers_used,
        tier3_attempted=tier3_attempted,
        tier3_ok=tier3_ok,
        covered_chars=covered_chars if text_truncated else None,
        tiers_unavailable=tiers_unavailable,
    )
