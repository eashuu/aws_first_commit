"""The three demo tools. Each returns an explicit `{"status", "content"}`
ToolResult shape (verified against the actual `strands` decorator: returning
a bare dict gets JSON-stringified into a `{"text": ...}` block, which is not
what guard.py's payload extraction expects — a `{"json": ...}` block is
what `normalize()` is built to read). Fixture data only; no network calls.
"""

from __future__ import annotations

import base64
import json
import os

from strands import tool

_HERE = os.path.dirname(__file__)
_FIXTURES = os.path.join(_HERE, "fixtures")

with open(os.path.join(_FIXTURES, "customers.json"), encoding="utf-8") as f:
    _CUSTOMERS = json.load(f)

with open(os.path.join(_FIXTURES, "tickets.json"), encoding="utf-8") as f:
    _TICKETS = json.load(f)

_CUSTOMER_FIELDS = ("name", "phone", "email", "address", "kyc")


def _error(message: str) -> dict:
    return {"status": "error", "content": [{"text": message}]}


def _json_result(obj: dict) -> dict:
    return {"status": "success", "content": [{"json": obj}]}


@tool
def fetch_customer(customer_id: str, field: str) -> dict:
    """Look up one field of a customer record.

    Args:
        customer_id: The customer's id, e.g. "cust_8814".
        field: Which field to return — one of name, phone, email, address, kyc.
            "kyc" returns the full KYC record (Aadhaar, name, phone, PAN).
    """
    if field not in _CUSTOMER_FIELDS:
        return _error(f"Unknown field '{field}'. Valid fields: {', '.join(_CUSTOMER_FIELDS)}")
    record = _CUSTOMERS.get(customer_id)
    if record is None:
        return _error(f"No such customer '{customer_id}'")

    if field == "kyc":
        payload = {"customer_id": customer_id, **record["kyc"]}
    else:
        payload = {"customer_id": customer_id, field: record.get(field)}
    return _json_result(payload)


@tool
def read_attachment(ticket_id: str) -> dict:
    """Read the attachment on a support ticket.

    Args:
        ticket_id: The ticket's id, e.g. "tkt_4471".
    """
    ticket = _TICKETS.get(ticket_id)
    if ticket is None:
        return _error(f"No such ticket '{ticket_id}'")

    attachment_path = os.path.join(_FIXTURES, ticket["attachment"])
    if not os.path.exists(attachment_path):
        return _error(
            f"Fixture attachment '{ticket['attachment']}' is missing. "
            f"Run fixtures/build_kyc_sheet.py to generate it."
        )

    with open(attachment_path, "rb") as f:
        raw = f.read()

    return _json_result(
        {
            "filename": ticket["attachment"],
            "media_type": ticket["media_type"],
            "b64": base64.b64encode(raw).decode("ascii"),
        }
    )


@tool
def send_summary(to: str, body: str) -> dict:
    """Send a short text summary to a destination.

    Args:
        to: The destination — a system or address such as "kyc-vault.internal".
        body: The summary text. May contain a redaction placeholder such as
            "[IN_AADHAAR_1_7f3a]", which is resolved on the trusted side
            before this tool runs, if and only if the destination is
            authorized to receive that value.
    """
    return _json_result({"to": to, "sent": True, "body_length": len(body)})


# Each is already an `@tool`-decorated DecoratedFunctionTool, ready to pass
# straight into Agent(tools=[...]). Calling one directly (e.g.
# `fetch_customer(customer_id=..., field=...)`) still works as a plain
# function call — verified against the decorator's own behaviour — so
# selfcheck.py can exercise these without spinning up an Agent.
TOOL_FUNCTIONS = (fetch_customer, read_attachment, send_summary)
