"""Everything becomes markdown before detection (PRD §9). Text, PDF, scan and
spreadsheet all arrive at detect.py as one type, so detect.py needs no
per-format branching.

Three rules that are load-bearing, all stated in the module they protect:
  1. A multi-page PDF is withheld whole — sync Textract only ever reads
     page 1, and releasing it would scan page 1 while claiming the row clean.
  2. Every PDF goes to Textract, even one with an extractable text layer —
     a text-layer-only extractor misses a scanned image embedded in a page.
  3. Truncation is a detected condition, not a silent cut.
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from typing import Literal

from config import Config


@dataclass(frozen=True, slots=True)
class Word:
    text: str
    bbox: tuple[float, float, float, float]  # Left, Top, Width, Height — 0..1
    begin: int  # offset of this word in the assembled markdown


@dataclass(frozen=True, slots=True)
class Normalized:
    markdown: str
    source_media_type: str
    pages: int
    words: list[Word] | None
    truncated: bool
    ocr_sourced: bool


NormalizeReason = Literal[
    "unsupported_media", "too_large", "multipage", "ocr_failed", "ocr_unavailable", "embedded_unreadable"
]


class NormalizeError(Exception):
    def __init__(self, reason: NormalizeReason, message: str = ""):
        super().__init__(message or reason)
        self.reason = reason


_textract_client_cache: dict[str, object] = {}


def _textract_client(cfg: Config):
    client = _textract_client_cache.get("client")
    if client is not None:
        return client
    import boto3
    from botocore.config import Config as BotoConfig

    client = boto3.client(
        "textract",
        region_name=cfg.aws_region,
        config=BotoConfig(
            connect_timeout=1,
            read_timeout=cfg.timeout_textract_s,
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )
    _textract_client_cache["client"] = client
    return client


def _textract_extract(
    raw: bytes, *, source_media_type: str, cfg: Config, strict_lines: bool, client=None
) -> Normalized:
    client = client or _textract_client(cfg)
    try:
        resp = client.detect_document_text(Document={"Bytes": raw})
    except Exception as exc:  # noqa: BLE001
        code = ""
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            code = response.get("Error", {}).get("Code", "")
        if code in ("UnsupportedDocumentException", "BadDocumentException", "DocumentTooLargeException"):
            raise NormalizeError("unsupported_media", code) from exc
        raise NormalizeError("ocr_failed", type(exc).__name__) from exc

    pages = resp.get("DocumentMetadata", {}).get("Pages", 1) or 1
    if pages > 1:
        # Sync Textract returns page 1 only. Releasing it means pages 2..n
        # were never scanned while the audit row would read "clean" — the
        # exact silent fail-open this rule exists to prevent.
        raise NormalizeError("multipage", f"{pages} pages")

    blocks = resp.get("Blocks")
    if blocks is None:
        raise NormalizeError("ocr_failed", "malformed response: no Blocks")

    lines = [b["Text"] for b in blocks if b.get("BlockType") == "LINE" and b.get("Text")]
    if strict_lines and not lines:
        raise NormalizeError("ocr_failed", "no LINE blocks on a non-blank page")

    markdown_full = "\n".join(lines)

    words: list[Word] = []
    cursor = 0
    for b in blocks:
        if b.get("BlockType") != "WORD":
            continue
        text = b.get("Text", "")
        if not text:
            continue
        pos = markdown_full.find(text, cursor)
        if pos == -1:
            continue
        bbox = b.get("Geometry", {}).get("BoundingBox", {})
        words.append(
            Word(
                text=text,
                bbox=(bbox.get("Left", 0.0), bbox.get("Top", 0.0), bbox.get("Width", 0.0), bbox.get("Height", 0.0)),
                begin=pos,
            )
        )
        cursor = pos + len(text)

    truncated = False
    markdown = markdown_full
    if len(markdown) > cfg.max_normalized_chars:
        markdown = markdown[: cfg.max_normalized_chars]
        truncated = True

    return Normalized(
        markdown=markdown,
        source_media_type=source_media_type,
        pages=1,
        words=words or None,
        truncated=truncated,
        ocr_sourced=True,
    )


def _json_to_markdown(obj) -> str:
    """Flat `key: value` lines, in source order — a JSON tool result becomes
    readable, offset-stable text instead of a raw `{...}` blob, and key
    order is preserved from the source dict (Python 3.7+ dicts, and
    `json.loads` on the source text) so a field like `aadhaar` printed first
    in a fixture reliably becomes placeholder ordinal 1 (TD §3.1)."""
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{k}: {_json.dumps(v, ensure_ascii=False)}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)
    return _json.dumps(obj, ensure_ascii=False)


def _truncate(text: str, cfg: Config) -> tuple[str, bool]:
    if len(text) <= cfg.max_normalized_chars:
        return text, False
    return text[: cfg.max_normalized_chars], True


def _csv_to_markdown(text: str) -> str:
    import csv
    import io

    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return ""
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join("---" for _ in rows[0]) + " |"]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _xlsx_to_markdown(raw: bytes) -> str:
    import io

    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    lines: list[str] = []
    header_done = False
    for row in ws.iter_rows(values_only=True):
        cells = ["" if c is None else str(c) for c in row]
        lines.append("| " + " | ".join(cells) + " |")
        if not header_done:
            lines.append("| " + " | ".join("---" for _ in cells) + " |")
            header_done = True
    return "\n".join(lines)


def _payload_size(payload: bytes | str) -> int:
    return len(payload) if isinstance(payload, (bytes, bytearray)) else len(payload.encode("utf-8"))


def normalize(payload: bytes | str, media_type: str, *, cfg: Config) -> Normalized:
    mt = (media_type or "").split(";", 1)[0].strip().lower()

    # Every branch is bounded before it does any parsing work — a spreadsheet
    # or JSON blob is otherwise fully loaded into memory (openpyxl building a
    # workbook, json.loads building a tree) before the _truncate() call that
    # used to be the only ceiling ever ran.
    if _payload_size(payload) > cfg.max_attachment_bytes:
        raise NormalizeError("too_large", f"{_payload_size(payload)} bytes")

    if mt == "text/plain":
        text = payload.decode("utf-8", errors="replace") if isinstance(payload, (bytes, bytearray)) else payload
        text, truncated = _truncate(text, cfg)
        return Normalized(text, mt, 1, None, truncated, False)

    if mt == "application/json":
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8", errors="replace")
        try:
            obj = _json.loads(payload) if isinstance(payload, str) else payload
        except _json.JSONDecodeError as exc:
            raise NormalizeError("unsupported_media", f"invalid JSON: {exc}") from exc
        text, truncated = _truncate(_json_to_markdown(obj), cfg)
        return Normalized(text, mt, 1, None, truncated, False)

    if mt == "application/pdf":
        if not isinstance(payload, (bytes, bytearray)):
            raise NormalizeError("unsupported_media", "pdf payload must be bytes")
        return _textract_extract(bytes(payload), source_media_type=mt, cfg=cfg, strict_lines=True)

    if mt in ("image/png", "image/jpeg", "image/jpg"):
        if not isinstance(payload, (bytes, bytearray)):
            raise NormalizeError("unsupported_media", "image payload must be bytes")
        # strict_lines=False: a purely Indic-script image may legitimately
        # have zero Latin LINE blocks. Tier 3 (on the raw image bytes,
        # wired up by guard.py) is what reads it, not Textract.
        return _textract_extract(bytes(payload), source_media_type=mt, cfg=cfg, strict_lines=False)

    if mt == "text/csv":
        text = payload.decode("utf-8", errors="replace") if isinstance(payload, (bytes, bytearray)) else payload
        md, truncated = _truncate(_csv_to_markdown(text), cfg)
        return Normalized(md, mt, 1, None, truncated, False)

    if mt in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ):
        if not isinstance(payload, (bytes, bytearray)):
            raise NormalizeError("unsupported_media", "xlsx payload must be bytes")
        try:
            md, truncated = _truncate(_xlsx_to_markdown(bytes(payload)), cfg)
        except NormalizeError:
            raise
        except Exception as exc:  # noqa: BLE001 — openpyxl raises its own zoo of exceptions
            raise NormalizeError("unsupported_media", f"unreadable xlsx: {type(exc).__name__}") from exc
        return Normalized(md, mt, 1, None, truncated, False)

    raise NormalizeError("unsupported_media", mt)
