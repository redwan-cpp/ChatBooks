"""Typed commands and queries accepted by the universal financial service."""

from dataclasses import dataclass

from ..domain import AccountType, LineInput


@dataclass(frozen=True, slots=True)
class CreateAccountCommand:
    code: str
    name: str
    account_type: AccountType


@dataclass(frozen=True, slots=True)
class SetAccountActiveCommand:
    account_id: str
    active: bool


@dataclass(frozen=True, slots=True)
class CreatePeriodCommand:
    name: str
    starts_on: str
    ends_on: str


@dataclass(frozen=True, slots=True)
class CreateProposalCommand:
    entry_date: str
    description: str
    lines: tuple[LineInput, ...]
    document_id: str | None = None
    reverses_entry_id: str | None = None


@dataclass(frozen=True, slots=True)
class ConfirmProposalCommand:
    validation_id: str
    accepted: bool
    proposal_id: str | None = None
    proposal_version: int | None = None
    confirmation_request_id: str | None = None
    idempotency_key: str | None = None
    request_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class PostProposalCommand:
    confirmation_id: str
    idempotency_key: str | None = None
    request_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class ProposeReversalCommand:
    entry_id: str
    entry_date: str
    reason: str


@dataclass(frozen=True, slots=True)
class LedgerQuery:
    as_of: str | None = None
    project_id: str | None = None
    starts_on: str | None = None


@dataclass(frozen=True, slots=True)
class CashMovementQuery:
    starts_on: str
    ends_on: str
    cash_account_ids: tuple[str, ...]
