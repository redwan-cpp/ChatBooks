"""Immutable, server-issued financial authority passed to the universal service."""

from dataclasses import dataclass
from enum import StrEnum


class FinancialSpaceKind(StrEnum):
    BUSINESS = "BUSINESS"
    PERSONAL = "PERSONAL"


class AuthoritySource(StrEnum):
    API_ROLE = "API_ROLE"
    TRUSTED_LOCAL_COMPATIBILITY = "TRUSTED_LOCAL_COMPATIBILITY"


class FinancialCapability(StrEnum):
    MANAGE_ACCOUNTS = "manage_accounts"
    MANAGE_PERIODS = "manage_periods"
    CREATE_PROPOSAL = "create_proposal"
    VALIDATE_PROPOSAL = "validate_proposal"
    CONFIRM_PROPOSAL = "confirm_proposal"
    POST_PROPOSAL = "post_proposal"
    REVERSE_ENTRY = "reverse_entry"
    VIEW_FINANCIALS = "view_financials"
    VIEW_REPORTS = "view_reports"
    VIEW_AUDIT = "view_audit"


BUSINESS_COMPATIBILITY_CAPABILITIES = frozenset(FinancialCapability)


@dataclass(frozen=True, slots=True)
class FinancialSpaceRef:
    kind: FinancialSpaceKind
    owner_id: str


@dataclass(frozen=True, slots=True)
class AuthorizedFinancialContext:
    actor_id: str
    financial_space: FinancialSpaceRef
    ledger_book_id: str
    currency: str
    minor_unit_digits: int
    capabilities: frozenset[FinancialCapability]
    request_id: str
    authority_source: AuthoritySource
    organization_id: str | None = None
    project_scope: frozenset[str] | None = None
