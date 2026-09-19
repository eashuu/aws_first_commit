"""Naka — every tunable, one place.

Values here need a redeploy to change. Values that should change live from the
control plane (budget, session_ceiling, identifying_types, comprehend_min_score)
live in the policy bundle instead — see policy.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"missing required env var {name}")
    return val or ""


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    normalized = val.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    # An unrecognized value (a typo, e.g. INDIC_ENABLED=maybe) used to
    # silently become False regardless of `default` — for a kill-switch
    # variable, "silently becomes off" and "silently stays on" are both
    # the wrong failure mode. Fail loudly instead.
    raise RuntimeError(f"env var {name}={val!r} is not a recognized boolean (use true/false, 1/0, yes/no, on/off)")


def _env_int(name: str, default: int) -> int:
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError as exc:
        raise RuntimeError(f"env var {name}={val!r} is not a valid integer") from exc


def _env_float(name: str, default: float) -> float:
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError as exc:
        raise RuntimeError(f"env var {name}={val!r} is not a valid number") from exc


@dataclass(frozen=True, slots=True)
class Config:
    # Region / identity
    aws_region: str
    model_id: str
    indic_model_id: str
    control_plane_url: str
    # The data plane's own Function URL, set on the CONTROL plane so the UI
    # it serves can prefill the agent endpoint. Both URLs only exist after
    # deploy, so this is written back by deploy.* once both are created.
    agent_url: str
    naka_key: str

    # Storage
    audit_table: str
    session_bucket: str
    session_prefix: str

    # Policy plumbing
    policy_ttl_s: int
    policy_path: str
    fallback_policy_path: str

    # Detection
    comprehend_language: str
    comprehend_chunk_bytes: int
    comprehend_chunk_overlap: int
    max_chunks_per_hop: int
    indic_enabled: bool

    # Ceilings
    max_attachment_bytes: int
    max_normalized_chars: int
    max_tool_calls_per_turn: int
    max_request_bytes: int

    # Timeouts (seconds) — each is "connect/read" budget before the retry
    # policy in normalize.py / detect.py gives up and fails closed.
    timeout_comprehend_s: float
    timeout_textract_s: float
    timeout_bedrock_s: float
    timeout_indic_s: float
    timeout_ddb_s: float
    timeout_policy_s: float

    # Audit
    audit_ttl_days: int

    @classmethod
    def load(cls) -> "Config":
        return cls(
            aws_region=_env("AWS_REGION", "ap-south-1"),
            model_id=_env("MODEL_ID", "apac.amazon.nova-lite-v1:0"),
            indic_model_id=_env("INDIC_MODEL_ID", "apac.amazon.nova-pro-v1:0"),
            control_plane_url=_env("CONTROL_PLANE_URL", ""),
            agent_url=_env("AGENT_URL", ""),
            naka_key=_env("NAKA_KEY", ""),
            audit_table=_env("AUDIT_TABLE", "naka_audit"),
            session_bucket=_env("SESSION_BUCKET", ""),
            session_prefix=_env("SESSION_PREFIX", "sessions/"),
            policy_ttl_s=_env_int("POLICY_TTL_S", 20),
            policy_path=_env("POLICY_PATH", "/tmp/agent.cedar"),
            fallback_policy_path=_env(
                "FALLBACK_POLICY_PATH",
                os.path.join(os.path.dirname(__file__), "agent.cedar"),
            ),
            comprehend_language=_env("COMPREHEND_LANGUAGE", "en"),
            comprehend_chunk_bytes=_env_int("COMPREHEND_CHUNK_BYTES", 90_000),
            comprehend_chunk_overlap=_env_int("COMPREHEND_CHUNK_OVERLAP", 200),
            max_chunks_per_hop=_env_int("MAX_CHUNKS_PER_HOP", 8),
            indic_enabled=_env_bool("INDIC_ENABLED", True),
            max_attachment_bytes=_env_int("MAX_ATTACHMENT_BYTES", 4_000_000),
            max_normalized_chars=_env_int("MAX_NORMALIZED_CHARS", 400_000),
            max_tool_calls_per_turn=_env_int("MAX_TOOL_CALLS_PER_TURN", 12),
            max_request_bytes=_env_int("MAX_REQUEST_BYTES", 6_000_000),
            timeout_comprehend_s=_env_float("TIMEOUT_COMPREHEND_S", 3.0),
            timeout_textract_s=_env_float("TIMEOUT_TEXTRACT_S", 8.0),
            timeout_bedrock_s=_env_float("TIMEOUT_BEDROCK_S", 30.0),
            timeout_indic_s=_env_float("TIMEOUT_INDIC_S", 10.0),
            timeout_ddb_s=_env_float("TIMEOUT_DDB_S", 2.0),
            timeout_policy_s=_env_float("TIMEOUT_POLICY_S", 2.0),
            audit_ttl_days=_env_int("AUDIT_TTL_DAYS", 30),
        )


# Module-scope singleton — loaded once per cold start, matching the rest of
# the package's cold-start amortisation (boto3 clients, PolicySet handle).
CFG = Config.load()

SUBJECT_KEYS: tuple[str, ...] = ("customer_id", "subject_id", "ticket_id", "account_id")

# Grounded on HIPAA Safe Harbor's list of identifiers (PRD §6.3) — cited for
# *which fields count as identifying*, never for the budget number itself.
DEFAULT_IDENTIFYING_TYPES: frozenset[str] = frozenset(
    {
        "NAME",
        "PHONE",
        "EMAIL",
        "ADDRESS",
        "DATE_TIME",
        "IN_AADHAAR",
        "IN_PERMANENT_ACCOUNT_NUMBER",
        "IN_VOTER_NUMBER",
        "IN_NREGA",
        "IN_GSTIN",
        "IN_IFSC",
        "CREDIT_DEBIT_NUMBER",
        "AGE",
    }
)

DEFAULT_BUDGET = 3
DEFAULT_SESSION_CEILING = 25
DEFAULT_COMPREHEND_MIN_SCORE = 0.5
