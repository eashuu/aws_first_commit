"""The Vault (plaintext, process-local, invocation-scoped) and the
Rehydrator intervention.

PRD §11.2, promoted to Must #5: as specced without this fix, any authorized
tool call carrying a placeholder in its arguments gets the real value
substituted before execution — so a compromised or injected agent could
emit a placeholder into a call to an attacker-controlled destination and the
guardrail would "helpfully" restore the plaintext. The fix: rehydration is
itself a Cedar question (`Action::"rehydrate_<TYPE>"` against the
destination as resource), not a blanket substitution. See cedar_q2.py.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

from strands.hooks.events import BeforeToolCallEvent
from strands.interventions import Deny, InterventionHandler, OnError, Proceed

import cedar_q2

TOKEN_RE = re.compile(r"\[(?P<type>[A-Z_]+)_(?P<n>\d+)_(?P<nonce>[0-9a-f]{4})\]")

_DEST_KEYS = ("to", "destination", "dest")


@dataclass(frozen=True, slots=True)
class Placeholder:
    token: str
    type: str
    ordinal: int


class Vault:
    """Process-local, invocation-scoped, plaintext. Never serialized, never
    persisted, never logged, never in agent.state, never in an audit row.
    Cleared in a `finally:` at the end of the handler that owns it."""

    def __init__(self, nonce: str | None = None) -> None:
        # The nonce is not decoration: without it, a token minted in one HTTP
        # request for subject A collides with the same-shaped token minted in
        # another request for subject B, and a stale token surviving in
        # restored conversation history rehydrates to the wrong person's
        # value. Scoped per Lambda invocation, it kills the whole class.
        self.nonce = nonce or secrets.token_hex(2)
        self._map: dict[str, str] = {}
        self._rev: dict[str, str] = {}
        self._next_ordinal = 1

    def mint(self, entity_type: str, value: str) -> Placeholder:
        existing = self._rev.get(value)
        if existing is not None:
            m = TOKEN_RE.match(existing)
            return Placeholder(existing, entity_type, int(m.group("n")) if m else 0)
        ordinal = self._next_ordinal
        self._next_ordinal += 1
        token = f"[{entity_type}_{ordinal}_{self.nonce}]"
        self._map[token] = value
        self._rev[value] = token
        return Placeholder(token, entity_type, ordinal)

    def resolve(self, token: str) -> str | None:
        return self._map.get(token)

    def tokens(self) -> list[str]:
        return list(self._map.keys())

    def clear(self) -> None:
        self._map.clear()
        self._rev.clear()


def _destination_for_call(tool_input: dict) -> str:
    for key in _DEST_KEYS:
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
    return "unknown"  # no destination named -> Cedar default-deny handles it


class Rehydrator(InterventionHandler):
    name = "rehydrator"

    def __init__(self, *, vault: Vault, principal: str, role: str, policy) -> None:
        self._vault = vault
        self._principal = principal
        self._role = role
        self._policy = policy
        # toolUseId -> the tokens actually restored into that call's
        # arguments. Token strings only, never values (TD §3.5) — AuditHook
        # reads this to populate AuditRow.rehydrated, which is how a Q3
        # ALLOW becomes visible in the audit trail at all.
        self.resolved_by_call: dict[str, list[str]] = {}

    @property
    def on_error(self) -> OnError:
        return "deny"  # a handler that crashes must not let a placeholder through

    def before_tool_call(self, event: BeforeToolCallEvent) -> Proceed | Deny:
        tool_input = event.tool_use.get("input")
        if not isinstance(tool_input, dict):
            return Proceed()

        tokens_by_key: dict[str, list[re.Match]] = {}
        types_needed: set[str] = set()
        for key, value in tool_input.items():
            if not isinstance(value, str):
                continue
            matches = list(TOKEN_RE.finditer(value))
            if matches:
                tokens_by_key[key] = matches
                types_needed.update(m.group("type") for m in matches)

        if not types_needed:
            return Proceed()

        dest = _destination_for_call(tool_input)
        allowed = cedar_q2.authorize_rehydration(
            list(types_needed), principal=self._principal, role=self._role, dest=dest, policy=self._policy
        )

        new_input = dict(tool_input)
        restored: list[str] = []
        for key, matches in tokens_by_key.items():
            new_value = tool_input[key]
            for m in matches:
                token, etype = m.group(0), m.group("type")
                if not allowed.get(etype, False):
                    return Deny(
                        reason=(
                            f"Restoring a {etype} value into this destination is not authorized. "
                            f"Choose an authorized destination or omit the field."
                        )
                    )
                resolved = self._vault.resolve(token)
                if resolved is None:
                    # The vault is invocation-scoped; a token from a previous
                    # HTTP request is genuinely unresolvable. That is a
                    # design property, not a bug (TD §5.3) — deny with a
                    # reason the model can act on, never pass the literal
                    # token through, never guess.
                    return Deny(
                        reason=(
                            f"Placeholder {token} cannot be resolved in this session window. "
                            f"Re-fetch the record if the value is required."
                        )
                    )
                # str.replace, never re.sub — a value containing regex
                # metacharacters is a routine bug and a plausible injection.
                new_value = new_value.replace(token, resolved)
                restored.append(token)
            new_input[key] = new_value

        event.tool_use["input"] = new_input
        tool_use_id = event.tool_use.get("toolUseId")
        if tool_use_id and restored:
            self.resolved_by_call[tool_use_id] = restored
        return Proceed()
