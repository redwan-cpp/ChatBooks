"""Canonical hashes reused by validation and read-only migration inspection."""

import hashlib
import json
from collections.abc import Mapping, Sequence

from .domain import LineInput

LEGACY_ORGANIZATION_FINGERPRINT_VERSION = "organization-v1"


def transaction_fingerprint(transaction: Mapping[str, object], lines: Sequence[LineInput]) -> str:
    """Reproduce the organization-v1 proposal fingerprint exactly."""
    payload = {
        "transaction": dict(transaction),
        "lines": [[line.account_id, line.debit, line.credit, line.project_id] for line in lines],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def transaction_fingerprint_for_version(
    version: str, transaction: Mapping[str, object], lines: Sequence[LineInput]
) -> str:
    """Verify persisted fingerprints without silently changing their historical algorithm."""
    if version != LEGACY_ORGANIZATION_FINGERPRINT_VERSION:
        raise ValueError(f"Unsupported transaction fingerprint version: {version}")
    return transaction_fingerprint(transaction, lines)
