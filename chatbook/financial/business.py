"""BUSINESS authorization and internal financial-context construction."""

import sqlite3
from typing import Protocol
from uuid import uuid4

from ..ledger_books import BusinessLedgerBook, resolve_business_ledger_book
from .context import (
    BUSINESS_COMPATIBILITY_CAPABILITIES,
    AuthoritySource,
    AuthorizedFinancialContext,
    FinancialSpaceKind,
    FinancialSpaceRef,
)


class _DatabaseConnection(Protocol):
    connection: sqlite3.Connection


class BusinessFinancialContextResolver:
    """Authorize membership before exposing an internal organization-backed context."""

    def __init__(self, database: _DatabaseConnection) -> None:
        self._database = database

    def resolve_book(self, actor_id: str, organization_id: str) -> BusinessLedgerBook:
        return resolve_business_ledger_book(self._database.connection, actor_id, organization_id)

    def resolve(
        self,
        actor_id: str,
        organization_id: str,
        *,
        request_id: str | None = None,
        project_scope: frozenset[str] | None = None,
        authority_source: AuthoritySource = AuthoritySource.TRUSTED_LOCAL_COMPATIBILITY,
    ) -> AuthorizedFinancialContext:
        book = self.resolve_book(actor_id, organization_id)
        return AuthorizedFinancialContext(
            actor_id=actor_id,
            financial_space=FinancialSpaceRef(FinancialSpaceKind.BUSINESS, organization_id),
            ledger_book_id=book.id,
            currency=book.currency,
            minor_unit_digits=book.minor_unit_digits,
            capabilities=BUSINESS_COMPATIBILITY_CAPABILITIES,
            request_id=request_id or str(uuid4()),
            authority_source=authority_source,
            organization_id=organization_id,
            project_scope=project_scope,
        )
