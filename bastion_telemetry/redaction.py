"""Redaction helpers for public telemetry publication."""

from collections.abc import Mapping
from typing import Any


DEFAULT_REDACT_KEYS = {
    "ticket_id",
    "account_id",
    "broker_account",
    "entry_price",
    "exit_price",
    "stop_loss",
    "take_profit",
}


def redact_record(record: Mapping[str, Any], keys: set[str] | None = None) -> dict[str, Any]:
    """Return a shallow redacted copy of a telemetry record."""
    redacted_keys = keys or DEFAULT_REDACT_KEYS
    return {key: ("<redacted>" if key in redacted_keys else value) for key, value in record.items()}
