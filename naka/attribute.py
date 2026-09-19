"""Entity -> data subject. The subject comes from the call, not the content
(TD §1.4) — general-purpose attribution by clustering entity values is a
research problem, and PRD open question 5 says not to claim it. Everything
unattributed shares ONE subject bucket per session, which is deliberate and
conservative: content with no subject hint cannot dodge the budget by being
anonymous.
"""

from __future__ import annotations

import unicodedata

from config import SUBJECT_KEYS

SubjectId = str


def canonical_subject(raw: str | None, *, session_id: str) -> SubjectId:
    """NFKC, strip, casefold, collapse internal whitespace — kills the
    trivial subject-id-churn variants ("cust_8814 ", "CUST_8814"). The
    genuine version (a different real id per call) needs value-level
    identity resolution and is out of scope; `session_ceiling` backstops it."""
    if not raw:
        return f"unattributed:{session_id}"
    s = unicodedata.normalize("NFKC", raw).strip().casefold()
    s = " ".join(s.split())
    return s if s else f"unattributed:{session_id}"


def subject_key(tool_input: dict) -> str | None:
    for key in SUBJECT_KEYS:
        val = tool_input.get(key)
        if val:
            return str(val)
    return None


def attribute(
    entities: list, *, tool_name: str, tool_input: dict, session_id: str
) -> dict[int, SubjectId]:
    """index-in-entities -> subject id. Every entity from one tool result
    shares one subject: the call is the unit of attribution, not the field."""
    raw_subject = subject_key(tool_input) if isinstance(tool_input, dict) else None
    subject = canonical_subject(raw_subject, session_id=session_id)
    return {i: subject for i in range(len(entities))}
