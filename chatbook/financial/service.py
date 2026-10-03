"""Single deterministic implementation of Chatbooks financial operations and reports."""

import json
import re
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from ..domain import (
    AccountType,
    Balance,
    ChatbookError,
    Confirmation,
    LineInput,
    TrialBalance,
    Validation,
    amount,
    canonical_date,
    validate_lines,
)
from ..fingerprints import (
    LEGACY_ORGANIZATION_FINGERPRINT_VERSION,
    transaction_fingerprint_for_version,
)
from .commands import (
    CashMovementQuery,
    ConfirmProposalCommand,
    CreateAccountCommand,
    CreatePeriodCommand,
    CreateProposalCommand,
    LedgerQuery,
    PostProposalCommand,
    ProposeReversalCommand,
    SetAccountActiveCommand,
)
from .context import AuthorizedFinancialContext, FinancialCapability
from .repository import (
    FinancialRepository,
    FinancialStorage,
    JournalEntryRecord,
    JournalLineRecord,
    ProposalRecord,
    ValidationRecord,
)


def _id() -> str:
    return str(uuid4())


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChatbookError("required_field", f"{field} must not be empty.")
    return value.strip()


class UniversalFinancialService:
    """Own all authoritative financial mutations and ledger-derived calculations."""

    def __init__(self, storage: FinancialStorage) -> None:
        self._storage = storage

    def _repository(
        self,
        context: AuthorizedFinancialContext,
        capability: FinancialCapability,
    ) -> FinancialRepository:
        if not isinstance(context, AuthorizedFinancialContext):
            raise ChatbookError(
                "financial_context_required",
                "A server-issued authorized financial context is required.",
            )
        if capability not in context.capabilities:
            raise ChatbookError(
                "financial_capability_required",
                "The financial context does not permit this operation.",
            )
        return self._storage.bind(context)

    @staticmethod
    def _require_project_scope(
        context: AuthorizedFinancialContext, project_ids: frozenset[str]
    ) -> None:
        if not project_ids:
            return
        if context.project_scope is None or not project_ids <= context.project_scope:
            raise ChatbookError(
                "invalid_financial_context",
                "The financial context does not contain the required business project scope.",
            )

    def create_account(
        self, context: AuthorizedFinancialContext, command: CreateAccountCommand
    ) -> str:
        if not isinstance(command.account_type, AccountType):
            raise ChatbookError("invalid_account_type", "Choose a defined account type.")
        repository = self._repository(context, FinancialCapability.MANAGE_ACCOUNTS)
        account_id = _id()
        with repository.write("account.create"):
            repository.create_account(
                account_id,
                _text(command.code, "code"),
                _text(command.name, "name"),
                command.account_type,
            )
        return account_id

    def set_account_active(
        self, context: AuthorizedFinancialContext, command: SetAccountActiveCommand
    ) -> None:
        if type(command.active) is not bool:
            raise ChatbookError("invalid_status", "active must be a boolean.")
        repository = self._repository(context, FinancialCapability.MANAGE_ACCOUNTS)
        with repository.write("account.set_active"):
            repository.account(command.account_id)
            repository.set_account_active(command.account_id, command.active)

    def get_account(
        self, context: AuthorizedFinancialContext, account_id: str
    ) -> dict[str, object]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        return repository.account(account_id).as_dict()

    def list_accounts(self, context: AuthorizedFinancialContext) -> tuple[dict[str, object], ...]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        return tuple(account.as_dict() for account in repository.accounts())

    def catalog_accounts(
        self, context: AuthorizedFinancialContext
    ) -> tuple[dict[str, object], ...]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        return tuple(account.as_dict() for account in repository.accounts(catalog_order=True))

    def catalog_charts(self, context: AuthorizedFinancialContext) -> tuple[dict[str, object], ...]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        return tuple(chart.as_dict() for chart in repository.charts())

    def create_period(
        self, context: AuthorizedFinancialContext, command: CreatePeriodCommand
    ) -> str:
        canonical_date(command.starts_on, "starts_on")
        canonical_date(command.ends_on, "ends_on")
        if command.ends_on < command.starts_on:
            raise ChatbookError("invalid_date_range", "Period end must be on or after its start.")
        repository = self._repository(context, FinancialCapability.MANAGE_PERIODS)
        period_id = _id()
        with repository.write("period.create"):
            if repository.overlapping_period_exists(command.starts_on, command.ends_on):
                raise ChatbookError("period_overlap", "Accounting periods must not overlap.")
            repository.create_period(
                period_id,
                _text(command.name, "name"),
                command.starts_on,
                command.ends_on,
            )
        return period_id

    def lock_period(self, context: AuthorizedFinancialContext, period_id: str) -> None:
        repository = self._repository(context, FinancialCapability.MANAGE_PERIODS)
        with repository.write("period.lock"):
            period = repository.period(period_id)
            if not period.locked:
                repository.lock_period(period_id)

    def list_periods(self, context: AuthorizedFinancialContext) -> tuple[dict[str, object], ...]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        return tuple(period.as_dict() for period in repository.periods())

    def catalog_periods(self, context: AuthorizedFinancialContext) -> tuple[dict[str, object], ...]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        return tuple(period.as_dict() for period in repository.periods(catalog_order=True))

    def create_transaction(
        self, context: AuthorizedFinancialContext, command: CreateProposalCommand
    ) -> str:
        projects = frozenset(
            line.project_id for line in command.lines if line.project_id is not None
        )
        self._require_project_scope(context, projects)
        repository = self._repository(context, FinancialCapability.CREATE_PROPOSAL)
        with repository.write("transaction.propose"):
            return self._create_proposal(repository, command)

    def _create_proposal(
        self, repository: FinancialRepository, command: CreateProposalCommand
    ) -> str:
        canonical_date(command.entry_date, "entry_date")
        if len(command.lines) > 1_000:
            raise ChatbookError("invalid_line_count", "A proposal supports at most 1000 lines.")
        transaction_id = _id()
        repository.create_proposal_header(
            ProposalRecord(
                id=transaction_id,
                organization_id=repository.context.organization_id or "",
                entry_date=command.entry_date,
                description=_text(command.description, "description"),
                document_id=command.document_id,
                reverses_entry_id=command.reverses_entry_id,
                version=1,
                state="assembling",
            )
        )
        for position, line in enumerate(command.lines, 1):
            amount(line.debit, "debit")
            amount(line.credit, "credit")
            if (line.debit > 0) == (line.credit > 0):
                raise ChatbookError(
                    "invalid_line", "Each line must have exactly one positive side."
                )
            repository.create_proposal_line(transaction_id, _id(), position, line)
        repository.seal_proposal(transaction_id)
        return transaction_id

    def _check(
        self,
        repository: FinancialRepository,
        proposal: ProposalRecord,
        fingerprint_version: str = LEGACY_ORGANIZATION_FINGERPRINT_VERSION,
    ) -> tuple[tuple[LineInput, ...], str, str]:
        lines = repository.proposal_lines(proposal.id)
        validate_lines(lines)
        period = repository.covering_period(proposal.entry_date)
        if period is None:
            raise ChatbookError(
                "period_missing", "Create an accounting period covering the entry date."
            )
        if period.locked:
            raise ChatbookError("period_locked", "The accounting period is locked.")
        for line in lines:
            if not repository.account(line.account_id).active:
                raise ChatbookError("inactive_account", "Every posting account must be active.")
        original_id = proposal.reverses_entry_id
        if original_id is not None:
            original = repository.journal_entry(original_id)
            if proposal.entry_date < original.entry_date:
                raise ChatbookError(
                    "invalid_reversal_date",
                    "Reversal date cannot precede the original.",
                )
            if repository.posted_reversal_exists(original_id):
                raise ChatbookError("already_reversed", "This entry already has a posted reversal.")
            expected = tuple(
                LineInput(
                    line.account_id,
                    line.credit,
                    line.debit,
                    line.project_id,
                )
                for line in repository.journal_lines(original_id)
            )
            if lines != expected:
                raise ChatbookError(
                    "invalid_reversal_lines",
                    "A reversal must exactly offset its target.",
                )
        try:
            fingerprint = transaction_fingerprint_for_version(
                fingerprint_version, proposal.fingerprint_mapping(), lines
            )
        except ValueError as exc:
            raise ChatbookError(
                "unsupported_fingerprint_version",
                "The validation fingerprint version is not supported.",
            ) from exc
        return lines, period.id, fingerprint

    def validate_transaction(
        self, context: AuthorizedFinancialContext, transaction_id: str
    ) -> Validation:
        repository = self._repository(context, FinancialCapability.VALIDATE_PROPOSAL)
        with repository.write("transaction.validate"):
            proposal = repository.proposal(transaction_id)
            if repository.posted_entry_for_transaction(transaction_id) is not None:
                raise ChatbookError("already_posted", "The transaction has already been posted.")
            lines, _, fingerprint = self._check(repository, proposal)
            validation_id = _id()
            repository.create_validation(
                ValidationRecord(
                    validation_id,
                    proposal.organization_id,
                    transaction_id,
                    fingerprint,
                    context.actor_id,
                )
            )
            debits, credits = validate_lines(lines)
            return Validation(validation_id, transaction_id, fingerprint, debits, credits)

    @staticmethod
    def _idempotent_resource(
        repository: FinancialRepository,
        operation: str,
        idempotency_key: str | None,
        request_fingerprint: str | None,
        resource_type: str,
    ) -> str | None:
        if idempotency_key is None and request_fingerprint is None:
            return None
        if idempotency_key is None or request_fingerprint is None:
            raise ChatbookError(
                "invalid_idempotency",
                "Idempotency key and request fingerprint must be supplied together.",
            )
        key = idempotency_key.strip()
        if not 8 <= len(key) <= 200:
            raise ChatbookError(
                "invalid_idempotency",
                "Idempotency key must be 8 to 200 characters.",
            )
        if not re.fullmatch(r"[0-9a-f]{64}", request_fingerprint):
            raise ChatbookError(
                "invalid_idempotency",
                "Request fingerprint must be a lowercase SHA-256 value.",
            )
        existing = repository.idempotency(repository.context.actor_id, operation, key)
        if existing is None:
            return None
        if (
            existing.request_fingerprint != request_fingerprint
            or existing.resource_type != resource_type
        ):
            raise ChatbookError(
                "idempotency_conflict",
                "This idempotency key was already used for a different request.",
            )
        return existing.resource_id

    @staticmethod
    def _record_idempotency(
        repository: FinancialRepository,
        operation: str,
        idempotency_key: str | None,
        request_fingerprint: str | None,
        resource_type: str,
        resource_id: str,
    ) -> None:
        if idempotency_key is None:
            return
        if request_fingerprint is None:
            raise RuntimeError("Validated idempotency data is incomplete.")
        repository.record_idempotency(
            _id(),
            repository.context.actor_id,
            operation,
            idempotency_key.strip(),
            request_fingerprint,
            resource_type,
            resource_id,
            _now(),
        )

    def confirm_transaction(
        self,
        context: AuthorizedFinancialContext,
        command: ConfirmProposalCommand,
    ) -> Confirmation:
        if command.accepted is not True:
            raise ChatbookError("confirmation_required", "Explicit user confirmation is required.")
        repository = self._repository(context, FinancialCapability.CONFIRM_PROPOSAL)
        with repository.write(
            "transaction.confirm",
            request_id=command.confirmation_request_id or command.idempotency_key,
        ):
            existing_id = self._idempotent_resource(
                repository,
                "transaction.confirm",
                command.idempotency_key,
                command.request_fingerprint,
                "confirmation",
            )
            if existing_id is not None:
                existing = repository.confirmation(existing_id)
                return Confirmation(existing.id, existing.transaction_id, existing.actor_id)
            validation = repository.validation(command.validation_id)
            proposal = repository.proposal(validation.transaction_id)
            if command.proposal_id is not None and command.proposal_id != proposal.id:
                raise ChatbookError(
                    "stale_proposal_version",
                    "Confirmation does not match the displayed proposal.",
                )
            if (
                command.proposal_version is not None
                and command.proposal_version != proposal.version
            ):
                raise ChatbookError(
                    "stale_proposal_version",
                    "Confirmation does not match the displayed version.",
                )
            if repository.posted_entry_for_transaction(proposal.id) is not None:
                raise ChatbookError("already_posted", "The transaction has already been posted.")
            _, _, fingerprint = self._check(repository, proposal, validation.fingerprint_version)
            if fingerprint != validation.fingerprint:
                raise ChatbookError(
                    "stale_validation",
                    "The proposal no longer matches its validation.",
                )
            confirmation_id = _id()
            repository.create_confirmation(confirmation_id, validation.id, context.actor_id)
            provenance_request_id = (
                command.confirmation_request_id or command.idempotency_key or _id()
            )
            repository.create_confirmation_provenance(
                confirmation_id,
                proposal.id,
                proposal.version,
                _now(),
                provenance_request_id,
            )
            self._record_idempotency(
                repository,
                "transaction.confirm",
                command.idempotency_key,
                command.request_fingerprint,
                "confirmation",
                confirmation_id,
            )
            return Confirmation(confirmation_id, proposal.id, context.actor_id)

    def post_transaction(
        self, context: AuthorizedFinancialContext, command: PostProposalCommand
    ) -> str:
        repository = self._repository(context, FinancialCapability.POST_PROPOSAL)
        with repository.write("transaction.post", request_id=command.idempotency_key):
            idempotent_entry = self._idempotent_resource(
                repository,
                "transaction.post",
                command.idempotency_key,
                command.request_fingerprint,
                "journal_entry",
            )
            if idempotent_entry is not None:
                return idempotent_entry
            confirmation = repository.confirmation(command.confirmation_id)
            if confirmation.actor_id != context.actor_id:
                raise ChatbookError(
                    "confirmation_actor",
                    "Only the confirming actor may post this entry.",
                )
            existing = repository.posted_entry_for_transaction(confirmation.transaction_id)
            if existing is not None:
                if existing.confirmation_id == command.confirmation_id:
                    self._record_idempotency(
                        repository,
                        "transaction.post",
                        command.idempotency_key,
                        command.request_fingerprint,
                        "journal_entry",
                        existing.id,
                    )
                    return existing.id
                raise ChatbookError(
                    "already_posted",
                    "The transaction was posted using another confirmation.",
                )
            proposal = repository.proposal(confirmation.transaction_id)
            lines, period_id, fingerprint = self._check(
                repository, proposal, confirmation.fingerprint_version
            )
            if fingerprint != confirmation.fingerprint:
                raise ChatbookError("stale_validation", "The confirmed proposal has changed.")
            entry_id = _id()
            repository.create_journal_header(
                JournalEntryRecord(
                    entry_id,
                    proposal.organization_id,
                    proposal.id,
                    command.confirmation_id,
                    period_id,
                    proposal.entry_date,
                    proposal.description,
                    proposal.reverses_entry_id,
                    "assembling",
                )
            )
            for position, line in enumerate(lines, 1):
                repository.create_journal_line(
                    JournalLineRecord(
                        _id(),
                        proposal.organization_id,
                        entry_id,
                        position,
                        line.account_id,
                        line.debit,
                        line.credit,
                        line.project_id,
                    )
                )
            repository.seal_journal_entry(entry_id)
            self._record_idempotency(
                repository,
                "transaction.post",
                command.idempotency_key,
                command.request_fingerprint,
                "journal_entry",
                entry_id,
            )
            return entry_id

    def propose_reversal(
        self,
        context: AuthorizedFinancialContext,
        command: ProposeReversalCommand,
    ) -> str:
        repository = self._repository(context, FinancialCapability.REVERSE_ENTRY)
        with repository.write("transaction.propose_reversal"):
            original = repository.journal_entry(command.entry_id)
            lines = tuple(
                LineInput(
                    line.account_id,
                    line.credit,
                    line.debit,
                    line.project_id,
                )
                for line in repository.journal_lines(command.entry_id)
            )
            transaction_id = self._create_proposal(
                repository,
                CreateProposalCommand(
                    command.entry_date,
                    f"Reversal: {_text(command.reason, 'reason')}",
                    lines,
                    reverses_entry_id=original.id,
                ),
            )
            self._check(repository, repository.proposal(transaction_id))
            return transaction_id

    def get_transaction(
        self, context: AuthorizedFinancialContext, transaction_id: str
    ) -> dict[str, object]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        result = repository.transaction_view(transaction_id)
        result["currency"] = context.currency
        result["minor_unit_digits"] = context.minor_unit_digits
        return result

    def get_confirmation(
        self, context: AuthorizedFinancialContext, confirmation_id: str
    ) -> dict[str, object]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        return repository.confirmation_view(confirmation_id)

    def proposal_for_validation(
        self, context: AuthorizedFinancialContext, validation_id: str
    ) -> dict[str, object]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        transaction_id = repository.validation_transaction_id(validation_id)
        result = repository.transaction_view(transaction_id)
        result["currency"] = context.currency
        result["minor_unit_digits"] = context.minor_unit_digits
        return result

    @staticmethod
    def _validate_ledger_query(query: LedgerQuery) -> None:
        for field, value in (("as_of", query.as_of), ("starts_on", query.starts_on)):
            if value is not None:
                canonical_date(value, field)
        if query.starts_on and query.as_of and query.starts_on > query.as_of:
            raise ChatbookError("invalid_date_range", "Report start must not exceed its end.")

    def _ledger(
        self, repository: FinancialRepository, query: LedgerQuery
    ) -> tuple[dict[str, object], ...]:
        self._validate_ledger_query(query)
        return repository.ledger_rows(
            as_of=query.as_of,
            starts_on=query.starts_on,
            project_id=query.project_id,
        )

    def ledger(
        self, context: AuthorizedFinancialContext, query: LedgerQuery
    ) -> tuple[dict[str, object], ...]:
        if query.project_id is not None:
            self._require_project_scope(context, frozenset({query.project_id}))
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        return self._ledger(repository, query)

    @staticmethod
    def _complete_journal_view(result: dict[str, object]) -> dict[str, object]:
        raw_lines = result.get("lines")
        if not isinstance(raw_lines, list):
            raise RuntimeError("Journal repository returned an invalid line collection.")
        lines = [dict(line) for line in raw_lines if isinstance(line, dict)]
        result["lines"] = lines
        result["debit_total"] = sum(int(line["debit"]) for line in lines)
        result["credit_total"] = sum(int(line["credit"]) for line in lines)
        result["line_count"] = len(lines)
        result["project_ids"] = list(
            dict.fromkeys(
                str(line["project_id"]) for line in lines if line["project_id"] is not None
            )
        )
        return result

    def get_journal_entry(
        self, context: AuthorizedFinancialContext, entry_id: str
    ) -> dict[str, object]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        return self._complete_journal_view(repository.journal_entry_view(entry_id))

    def list_journal_entries(
        self, context: AuthorizedFinancialContext
    ) -> tuple[dict[str, object], ...]:
        repository = self._repository(context, FinancialCapability.VIEW_FINANCIALS)
        summaries: list[dict[str, object]] = []
        for raw in repository.journal_entry_views():
            complete = self._complete_journal_view(raw)
            complete.pop("lines")
            summaries.append(complete)
        return tuple(summaries)

    def _trial_balance(
        self,
        context: AuthorizedFinancialContext,
        repository: FinancialRepository,
        *,
        as_of: str | None,
        project_id: str | None,
    ) -> TrialBalance:
        ledger = self._ledger(repository, LedgerQuery(as_of=as_of, project_id=project_id))
        totals: dict[str, tuple[int, int]] = {}
        for row in ledger:
            account_id = str(row["account_id"])
            debit, credit = totals.get(account_id, (0, 0))
            totals[account_id] = (
                debit + int(str(row["debit"])),
                credit + int(str(row["credit"])),
            )
        accounts = tuple(
            Balance(
                account.id,
                account.code,
                account.name,
                account.account_type,
                *totals.get(account.id, (0, 0)),
            )
            for account in repository.accounts()
        )
        return TrialBalance(
            context.currency,
            context.minor_unit_digits,
            as_of,
            project_id,
            accounts,
        )

    def trial_balance(
        self,
        context: AuthorizedFinancialContext,
        *,
        as_of: str | None = None,
        project_id: str | None = None,
    ) -> TrialBalance:
        if project_id is not None:
            self._require_project_scope(context, frozenset({project_id}))
        repository = self._repository(context, FinancialCapability.VIEW_REPORTS)
        return self._trial_balance(context, repository, as_of=as_of, project_id=project_id)

    def account_balance(
        self,
        context: AuthorizedFinancialContext,
        account_id: str,
        *,
        as_of: str | None = None,
    ) -> Balance:
        repository = self._repository(context, FinancialCapability.VIEW_REPORTS)
        report = self._trial_balance(context, repository, as_of=as_of, project_id=None)
        for account in report.accounts:
            if account.account_id == account_id:
                return account
        raise ChatbookError("not_found", "Account not found in this organization.")

    def income_statement(
        self,
        context: AuthorizedFinancialContext,
        starts_on: str,
        ends_on: str,
    ) -> dict[str, object]:
        canonical_date(starts_on, "starts_on")
        canonical_date(ends_on, "ends_on")
        repository = self._repository(context, FinancialCapability.VIEW_REPORTS)
        ledger = self._ledger(repository, LedgerQuery(as_of=ends_on, starts_on=starts_on))
        revenue = expenses = 0
        for row in ledger:
            net = int(str(row["debit"])) - int(str(row["credit"]))
            if row["account_type"] == AccountType.REVENUE:
                revenue -= net
            elif row["account_type"] == AccountType.EXPENSE:
                expenses += net
        return {
            "currency": context.currency,
            "minor_unit_digits": context.minor_unit_digits,
            "starts_on": starts_on,
            "ends_on": ends_on,
            "revenue": revenue,
            "expenses": expenses,
            "net_income": revenue - expenses,
        }

    def balance_sheet(self, context: AuthorizedFinancialContext, as_of: str) -> dict[str, object]:
        canonical_date(as_of, "as_of")
        repository = self._repository(context, FinancialCapability.VIEW_REPORTS)
        report = self._trial_balance(context, repository, as_of=as_of, project_id=None)
        net = {
            kind: sum(
                account.net_debit for account in report.accounts if account.account_type == kind
            )
            for kind in AccountType
        }
        assets = net[AccountType.ASSET]
        liabilities = -net[AccountType.LIABILITY]
        recorded_equity = -net[AccountType.EQUITY]
        unclosed_earnings = -net[AccountType.REVENUE] - net[AccountType.EXPENSE]
        return {
            "currency": report.currency,
            "minor_unit_digits": report.minor_unit_digits,
            "as_of": as_of,
            "assets": assets,
            "liabilities": liabilities,
            "recorded_equity": recorded_equity,
            "unclosed_earnings": unclosed_earnings,
            "total_equity": recorded_equity + unclosed_earnings,
            "balanced": assets == liabilities + recorded_equity + unclosed_earnings,
        }

    def cash_flow(
        self, context: AuthorizedFinancialContext, query: CashMovementQuery
    ) -> dict[str, object]:
        canonical_date(query.starts_on, "starts_on")
        canonical_date(query.ends_on, "ends_on")
        if query.starts_on > query.ends_on:
            raise ChatbookError("invalid_date_range", "Report start must not exceed its end.")
        if not query.cash_account_ids:
            raise ChatbookError(
                "cash_accounts_required",
                "Select at least one asset account for the cash movement report.",
            )
        repository = self._repository(context, FinancialCapability.VIEW_REPORTS)
        selected: list[dict[str, object]] = []
        seen: set[str] = set()
        for account_id in query.cash_account_ids:
            if account_id in seen:
                continue
            account = repository.account(account_id)
            if account.account_type is not AccountType.ASSET:
                raise ChatbookError(
                    "invalid_cash_account",
                    "Cash movement accounts must be asset accounts.",
                )
            seen.add(account_id)
            selected.append(account.as_dict())
        ledger = self._ledger(
            repository,
            LedgerQuery(as_of=query.ends_on, starts_on=query.starts_on),
        )
        movements = tuple(row for row in ledger if str(row["account_id"]) in seen)
        inflows = sum(int(str(row["debit"])) for row in movements)
        outflows = sum(int(str(row["credit"])) for row in movements)
        return {
            "currency": context.currency,
            "minor_unit_digits": context.minor_unit_digits,
            "starts_on": query.starts_on,
            "ends_on": query.ends_on,
            "cash_accounts": selected,
            "movements": movements,
            "total_inflows": inflows,
            "total_outflows": outflows,
            "net_change": inflows - outflows,
            "classification": "unclassified_cash_movements",
        }

    def audit_events(
        self,
        context: AuthorizedFinancialContext,
        *,
        entity_id: str | None = None,
    ) -> tuple[dict[str, object], ...]:
        repository = self._repository(context, FinancialCapability.VIEW_AUDIT)
        result: list[dict[str, object]] = []
        for raw in repository.audit_events(entity_id=entity_id):
            event = dict(raw)
            for key in ("previous_state", "new_state", "metadata"):
                value = event[key]
                event[key] = json.loads(cast(str, value)) if value is not None else None
            result.append(event)
        return tuple(result)
