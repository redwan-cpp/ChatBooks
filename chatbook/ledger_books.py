"""Internal BUSINESS LedgerBook identity and authorized organization resolution."""

import sqlite3
from dataclasses import dataclass

from .domain import ChatbookError


@dataclass(frozen=True, slots=True)
class BusinessLedgerBook:
    id: str
    organization_id: str
    currency: str
    minor_unit_digits: int


def resolve_business_ledger_book(
    connection: sqlite3.Connection, actor_id: str, organization_id: str
) -> BusinessLedgerBook:
    """Authorize organization membership before resolving its internal book."""
    if (
        connection.execute(
            "SELECT 1 FROM memberships WHERE organization_id = ? AND user_id = ?",
            (organization_id, actor_id),
        ).fetchone()
        is None
    ):
        raise ChatbookError("forbidden", "The actor is not a member of this organization.")
    row = connection.execute(
        "SELECT id, organization_id, currency, minor_unit_digits FROM ledger_books "
        "WHERE owner_kind = 'BUSINESS' AND organization_id = ?",
        (organization_id,),
    ).fetchone()
    if row is None:
        raise ChatbookError(
            "ledger_book_mapping_missing",
            "The organization does not have its required financial book mapping.",
        )
    return BusinessLedgerBook(
        id=str(row["id"]),
        organization_id=str(row["organization_id"]),
        currency=str(row["currency"]),
        minor_unit_digits=int(row["minor_unit_digits"]),
    )
