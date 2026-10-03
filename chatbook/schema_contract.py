"""Stable schema metadata shared by persistence and migration evidence tooling."""

AUDITED_TABLES = (
    "users",
    "organizations",
    "memberships",
    "charts_of_accounts",
    "accounts",
    "accounting_periods",
    "projects",
    "documents",
    "transactions",
    "transaction_lines",
    "validations",
    "confirmations",
    "journal_entries",
    "journal_lines",
)

MUTABLE_TABLES = {
    "accounts",
    "accounting_periods",
    "projects",
    "transactions",
    "journal_entries",
}

V2_TABLES = (
    "users",
    "user_credentials",
    "auth_sessions",
    "organizations",
    "memberships",
    "charts_of_accounts",
    "accounts",
    "accounting_periods",
    "projects",
    "documents",
    "transactions",
    "transaction_lines",
    "validations",
    "confirmations",
    "confirmation_provenance",
    "command_idempotency",
    "journal_entries",
    "journal_lines",
    "audit_events",
)


def business_book_id(organization_id: str) -> str:
    """Return the stable internal book ID for an existing business organization."""
    return f"book:business:{organization_id}"
