"""Explicit context-bound persistence port for deterministic financial operations."""

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from ..domain import AccountType, LineInput
from .context import AuthorizedFinancialContext


@dataclass(frozen=True, slots=True)
class ChartRecord:
    id: str
    organization_id: str
    name: str

    def as_dict(self) -> dict[str, object]:
        return {"id": self.id, "organization_id": self.organization_id, "name": self.name}


@dataclass(frozen=True, slots=True)
class AccountRecord:
    id: str
    organization_id: str
    code: str
    name: str
    account_type: AccountType
    active: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "code": self.code,
            "name": self.name,
            "account_type": self.account_type.value,
            "active": int(self.active),
        }


@dataclass(frozen=True, slots=True)
class PeriodRecord:
    id: str
    organization_id: str
    name: str
    starts_on: str
    ends_on: str
    locked: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "starts_on": self.starts_on,
            "ends_on": self.ends_on,
            "locked": int(self.locked),
        }


@dataclass(frozen=True, slots=True)
class ProposalRecord:
    id: str
    organization_id: str
    entry_date: str
    description: str
    document_id: str | None
    reverses_entry_id: str | None
    version: int
    state: str

    def fingerprint_mapping(self) -> dict[str, object]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "entry_date": self.entry_date,
            "description": self.description,
            "document_id": self.document_id,
            "reverses_entry_id": self.reverses_entry_id,
            "version": self.version,
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class ValidationRecord:
    id: str
    organization_id: str
    transaction_id: str
    fingerprint: str
    actor_id: str
    fingerprint_version: str = "organization-v1"


@dataclass(frozen=True, slots=True)
class ConfirmationRecord:
    id: str
    organization_id: str
    validation_id: str
    actor_id: str
    transaction_id: str
    fingerprint: str
    fingerprint_version: str = "organization-v1"


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    request_fingerprint: str
    resource_type: str
    resource_id: str


@dataclass(frozen=True, slots=True)
class JournalEntryRecord:
    id: str
    organization_id: str
    transaction_id: str
    confirmation_id: str
    period_id: str
    entry_date: str
    description: str
    reverses_entry_id: str | None
    state: str


@dataclass(frozen=True, slots=True)
class JournalLineRecord:
    id: str
    organization_id: str
    entry_id: str
    position: int
    account_id: str
    debit: int
    credit: int
    project_id: str | None

    def as_input(self) -> LineInput:
        return LineInput(self.account_id, self.debit, self.credit, self.project_id)


class FinancialRepository(Protocol):
    """A repository already bound to one verified AuthorizedFinancialContext."""

    @property
    def context(self) -> AuthorizedFinancialContext: ...

    def write(
        self, operation: str, *, request_id: str | None = None
    ) -> AbstractContextManager[None]: ...

    def chart_id(self) -> str: ...
    def charts(self) -> tuple[ChartRecord, ...]: ...
    def create_account(
        self, account_id: str, code: str, name: str, account_type: AccountType
    ) -> None: ...
    def account(self, account_id: str) -> AccountRecord: ...
    def accounts(self, *, catalog_order: bool = False) -> tuple[AccountRecord, ...]: ...
    def set_account_active(self, account_id: str, active: bool) -> None: ...
    def overlapping_period_exists(self, starts_on: str, ends_on: str) -> bool: ...
    def create_period(self, period_id: str, name: str, starts_on: str, ends_on: str) -> None: ...
    def period(self, period_id: str) -> PeriodRecord: ...
    def periods(self, *, catalog_order: bool = False) -> tuple[PeriodRecord, ...]: ...
    def lock_period(self, period_id: str) -> None: ...
    def covering_period(self, entry_date: str) -> PeriodRecord | None: ...
    def create_proposal_header(self, proposal: ProposalRecord) -> None: ...
    def create_proposal_line(
        self, transaction_id: str, line_id: str, position: int, line: LineInput
    ) -> None: ...
    def seal_proposal(self, transaction_id: str) -> None: ...
    def proposal(self, transaction_id: str) -> ProposalRecord: ...
    def proposal_lines(self, transaction_id: str) -> tuple[LineInput, ...]: ...
    def posted_entry_for_transaction(self, transaction_id: str) -> JournalEntryRecord | None: ...
    def create_validation(self, validation: ValidationRecord) -> None: ...
    def validation(self, validation_id: str) -> ValidationRecord: ...
    def idempotency(self, actor_id: str, operation: str, key: str) -> IdempotencyRecord | None: ...
    def create_confirmation(
        self, confirmation_id: str, validation_id: str, actor_id: str
    ) -> None: ...
    def create_confirmation_provenance(
        self,
        confirmation_id: str,
        proposal_id: str,
        proposal_version: int,
        confirmed_at: str,
        request_id: str,
    ) -> None: ...
    def confirmation(self, confirmation_id: str) -> ConfirmationRecord: ...
    def confirmation_view(self, confirmation_id: str) -> dict[str, object]: ...
    def record_idempotency(
        self,
        receipt_id: str,
        actor_id: str,
        operation: str,
        key: str,
        request_fingerprint: str,
        resource_type: str,
        resource_id: str,
        created_at: str,
    ) -> None: ...
    def journal_entry(self, entry_id: str) -> JournalEntryRecord: ...
    def journal_lines(self, entry_id: str) -> tuple[JournalLineRecord, ...]: ...
    def posted_reversal_exists(self, entry_id: str) -> bool: ...
    def create_journal_header(self, entry: JournalEntryRecord) -> None: ...
    def create_journal_line(self, line: JournalLineRecord) -> None: ...
    def seal_journal_entry(self, entry_id: str) -> None: ...
    def transaction_view(self, transaction_id: str) -> dict[str, object]: ...
    def validation_transaction_id(self, validation_id: str) -> str: ...
    def ledger_rows(
        self, *, as_of: str | None, starts_on: str | None, project_id: str | None
    ) -> tuple[dict[str, object], ...]: ...
    def journal_entry_view(self, entry_id: str) -> dict[str, object]: ...
    def journal_entry_views(self) -> tuple[dict[str, object], ...]: ...
    def audit_events(self, *, entity_id: str | None) -> tuple[dict[str, object], ...]: ...


class FinancialStorage(Protocol):
    def bind(self, context: AuthorizedFinancialContext) -> FinancialRepository: ...
