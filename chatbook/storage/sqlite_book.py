"""Schema-v4 book-scoped adapter for the universal financial service."""

import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import cast

from ..canonical_database import CanonicalDatabase
from ..domain import AccountType, ChatbookError, LineInput
from ..financial.context import AuthorizedFinancialContext, FinancialSpaceKind
from ..financial.repository import (
    AccountRecord,
    ChartRecord,
    ConfirmationRecord,
    FinancialRepository,
    IdempotencyRecord,
    JournalEntryRecord,
    JournalLineRecord,
    PeriodRecord,
    ProposalRecord,
    ValidationRecord,
)


class SQLiteBookStorage:
    """Bind a verified internal context to canonical book-scoped tables."""

    def __init__(self, database: CanonicalDatabase) -> None:
        self._database = database

    def bind(self, context: AuthorizedFinancialContext) -> FinancialRepository:
        if not isinstance(context, AuthorizedFinancialContext):
            raise ChatbookError(
                "financial_context_required",
                "A server-issued authorized financial context is required.",
            )
        organization_id = context.organization_id
        if (
            context.financial_space.kind is not FinancialSpaceKind.BUSINESS
            or organization_id is None
            or context.financial_space.owner_id != organization_id
        ):
            raise ChatbookError(
                "invalid_financial_context",
                "The financial context does not identify a BUSINESS organization.",
            )
        row = self._database.connection.execute(
            "SELECT id, organization_id, currency, minor_unit_digits FROM ledger_books "
            "WHERE owner_kind = 'BUSINESS' AND id = ? AND organization_id = ?",
            (context.ledger_book_id, organization_id),
        ).fetchone()
        if (
            row is None
            or str(row["currency"]) != context.currency
            or int(row["minor_unit_digits"]) != context.minor_unit_digits
        ):
            raise ChatbookError(
                "invalid_financial_context",
                "The financial context does not match the persisted BUSINESS LedgerBook.",
            )
        return SQLiteBookRepository(
            self._database, context, organization_id, context.ledger_book_id
        )


class SQLiteBookRepository:
    """Named financial operations bound to one canonical LedgerBook."""

    def __init__(
        self,
        database: CanonicalDatabase,
        context: AuthorizedFinancialContext,
        organization_id: str,
        ledger_book_id: str,
    ) -> None:
        self._database = database
        self._context = context
        self._organization_id = organization_id
        self._ledger_book_id = ledger_book_id

    @property
    def context(self) -> AuthorizedFinancialContext:
        return self._context

    @property
    def _db(self) -> sqlite3.Connection:
        return self._database.connection

    def _required(self, sql: str, parameters: tuple[object, ...]) -> sqlite3.Row:
        row = self._db.execute(sql, parameters).fetchone()
        if row is None:
            raise ChatbookError(
                "not_found", "The requested record was not found in this organization."
            )
        return cast(sqlite3.Row, row)

    @contextmanager
    def write(self, operation: str, *, request_id: str | None = None) -> Iterator[None]:
        with self._database.write(
            self._context.actor_id,
            operation,
            request_id=request_id or self._context.request_id,
            ledger_book_id=self._ledger_book_id,
        ):
            yield

    def _account_record(self, row: sqlite3.Row) -> AccountRecord:
        return AccountRecord(
            id=str(row["id"]),
            organization_id=self._organization_id,
            code=str(row["code"]),
            name=str(row["name"]),
            account_type=AccountType(str(row["account_type"])),
            active=bool(row["active"]),
        )

    def _period_record(self, row: sqlite3.Row) -> PeriodRecord:
        return PeriodRecord(
            id=str(row["id"]),
            organization_id=self._organization_id,
            name=str(row["name"]),
            starts_on=str(row["starts_on"]),
            ends_on=str(row["ends_on"]),
            locked=bool(row["locked"]),
        )

    def _proposal_record(self, row: sqlite3.Row) -> ProposalRecord:
        return ProposalRecord(
            id=str(row["id"]),
            organization_id=self._organization_id,
            entry_date=str(row["entry_date"]),
            description=str(row["description"]),
            document_id=str(row["document_id"]) if row["document_id"] is not None else None,
            reverses_entry_id=(
                str(row["reverses_entry_id"]) if row["reverses_entry_id"] is not None else None
            ),
            version=int(row["version"]),
            state=str(row["state"]),
        )

    def _journal_entry_record(self, row: sqlite3.Row) -> JournalEntryRecord:
        return JournalEntryRecord(
            id=str(row["id"]),
            organization_id=self._organization_id,
            transaction_id=str(row["transaction_id"]),
            confirmation_id=str(row["confirmation_id"]),
            period_id=str(row["period_id"]),
            entry_date=str(row["entry_date"]),
            description=str(row["description"]),
            reverses_entry_id=(
                str(row["reverses_entry_id"]) if row["reverses_entry_id"] is not None else None
            ),
            state=str(row["state"]),
        )

    def _journal_line_record(self, row: sqlite3.Row) -> JournalLineRecord:
        return JournalLineRecord(
            id=str(row["id"]),
            organization_id=self._organization_id,
            entry_id=str(row["entry_id"]),
            position=int(row["position"]),
            account_id=str(row["account_id"]),
            debit=int(row["debit"]),
            credit=int(row["credit"]),
            project_id=str(row["project_id"]) if row["project_id"] is not None else None,
        )

    def chart_id(self) -> str:
        row = self._required(
            "SELECT id FROM charts_of_accounts WHERE ledger_book_id = ?",
            (self._ledger_book_id,),
        )
        return str(row["id"])

    def charts(self) -> tuple[ChartRecord, ...]:
        return tuple(
            ChartRecord(str(row["id"]), self._organization_id, str(row["name"]))
            for row in self._db.execute(
                "SELECT id, name FROM charts_of_accounts WHERE ledger_book_id = ? ORDER BY id",
                (self._ledger_book_id,),
            )
        )

    def create_account(
        self, account_id: str, code: str, name: str, account_type: AccountType
    ) -> None:
        self._db.execute(
            "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, 1)",
            (
                account_id,
                self._ledger_book_id,
                self.chart_id(),
                code,
                name,
                account_type.value,
            ),
        )

    def account(self, account_id: str) -> AccountRecord:
        return self._account_record(
            self._required(
                "SELECT id, code, name, account_type, active "
                "FROM accounts WHERE id = ? AND ledger_book_id = ?",
                (account_id, self._ledger_book_id),
            )
        )

    def accounts(self, *, catalog_order: bool = False) -> tuple[AccountRecord, ...]:
        order = "id" if catalog_order else "code, id"
        return tuple(
            self._account_record(row)
            for row in self._db.execute(
                "SELECT id, code, name, account_type, active "
                f"FROM accounts WHERE ledger_book_id = ? ORDER BY {order}",
                (self._ledger_book_id,),
            )
        )

    def set_account_active(self, account_id: str, active: bool) -> None:
        self._db.execute(
            "UPDATE accounts SET active = ? WHERE id = ? AND ledger_book_id = ?",
            (int(active), account_id, self._ledger_book_id),
        )

    def overlapping_period_exists(self, starts_on: str, ends_on: str) -> bool:
        return (
            self._db.execute(
                "SELECT 1 FROM accounting_periods WHERE ledger_book_id = ? "
                "AND starts_on <= ? AND ends_on >= ?",
                (self._ledger_book_id, ends_on, starts_on),
            ).fetchone()
            is not None
        )

    def create_period(self, period_id: str, name: str, starts_on: str, ends_on: str) -> None:
        self._db.execute(
            "INSERT INTO accounting_periods VALUES (?, ?, ?, ?, ?, 0)",
            (period_id, self._ledger_book_id, name, starts_on, ends_on),
        )

    def period(self, period_id: str) -> PeriodRecord:
        return self._period_record(
            self._required(
                "SELECT * FROM accounting_periods WHERE id = ? AND ledger_book_id = ?",
                (period_id, self._ledger_book_id),
            )
        )

    def periods(self, *, catalog_order: bool = False) -> tuple[PeriodRecord, ...]:
        order = "id" if catalog_order else "starts_on, id"
        return tuple(
            self._period_record(row)
            for row in self._db.execute(
                f"SELECT * FROM accounting_periods WHERE ledger_book_id = ? ORDER BY {order}",
                (self._ledger_book_id,),
            )
        )

    def lock_period(self, period_id: str) -> None:
        self._db.execute(
            "UPDATE accounting_periods SET locked = 1 WHERE id = ? AND ledger_book_id = ?",
            (period_id, self._ledger_book_id),
        )

    def covering_period(self, entry_date: str) -> PeriodRecord | None:
        row = self._db.execute(
            "SELECT * FROM accounting_periods WHERE ledger_book_id = ? "
            "AND ? BETWEEN starts_on AND ends_on",
            (self._ledger_book_id, entry_date),
        ).fetchone()
        return self._period_record(row) if row is not None else None

    def create_proposal_header(self, proposal: ProposalRecord) -> None:
        self._db.execute(
            "INSERT INTO business_proposal_documents "
            "(proposal_id, ledger_book_id, organization_id, document_id) "
            "VALUES (?, ?, ?, ?)",
            (
                proposal.id,
                self._ledger_book_id,
                self._organization_id,
                proposal.document_id,
            ),
        )
        self._db.execute(
            "INSERT INTO transactions ("
            "id, ledger_book_id, entry_date, description, reverses_entry_id, "
            "version, state) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                proposal.id,
                self._ledger_book_id,
                proposal.entry_date,
                proposal.description,
                proposal.reverses_entry_id,
                proposal.version,
                proposal.state,
            ),
        )

    def create_proposal_line(
        self, transaction_id: str, line_id: str, position: int, line: LineInput
    ) -> None:
        self._db.execute(
            "INSERT INTO business_proposal_line_projects "
            "(line_id, ledger_book_id, organization_id, project_id) VALUES (?, ?, ?, ?)",
            (line_id, self._ledger_book_id, self._organization_id, line.project_id),
        )
        self._db.execute(
            "INSERT INTO transaction_lines VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                line_id,
                self._ledger_book_id,
                transaction_id,
                position,
                line.account_id,
                line.debit,
                line.credit,
            ),
        )

    def seal_proposal(self, transaction_id: str) -> None:
        self._db.execute(
            "UPDATE transactions SET state = 'proposed' WHERE id = ? AND ledger_book_id = ?",
            (transaction_id, self._ledger_book_id),
        )

    def proposal(self, transaction_id: str) -> ProposalRecord:
        return self._proposal_record(
            self._required(
                "SELECT t.*, x.document_id FROM transactions t "
                "JOIN business_proposal_documents x ON x.proposal_id = t.id "
                "AND x.ledger_book_id = t.ledger_book_id "
                "WHERE t.ledger_book_id = ? AND t.id = ? AND t.state = 'proposed'",
                (self._ledger_book_id, transaction_id),
            )
        )

    def proposal_lines(self, transaction_id: str) -> tuple[LineInput, ...]:
        return tuple(
            LineInput(
                str(row["account_id"]),
                int(row["debit"]),
                int(row["credit"]),
                str(row["project_id"]) if row["project_id"] is not None else None,
            )
            for row in self._db.execute(
                "SELECT l.*, x.project_id FROM transaction_lines l "
                "JOIN business_proposal_line_projects x ON x.line_id = l.id "
                "AND x.ledger_book_id = l.ledger_book_id "
                "WHERE l.ledger_book_id = ? AND l.transaction_id = ? ORDER BY l.position",
                (self._ledger_book_id, transaction_id),
            )
        )

    def posted_entry_for_transaction(self, transaction_id: str) -> JournalEntryRecord | None:
        row = self._db.execute(
            "SELECT * FROM journal_entries WHERE ledger_book_id = ? "
            "AND transaction_id = ? AND state = 'posted'",
            (self._ledger_book_id, transaction_id),
        ).fetchone()
        return self._journal_entry_record(row) if row is not None else None

    def create_validation(self, validation: ValidationRecord) -> None:
        self._db.execute(
            "INSERT INTO validations (id, ledger_book_id, transaction_id, fingerprint, "
            "fingerprint_version, actor_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                validation.id,
                self._ledger_book_id,
                validation.transaction_id,
                validation.fingerprint,
                validation.fingerprint_version,
                validation.actor_id,
            ),
        )

    def validation(self, validation_id: str) -> ValidationRecord:
        row = self._required(
            "SELECT * FROM validations WHERE id = ? AND ledger_book_id = ?",
            (validation_id, self._ledger_book_id),
        )
        return ValidationRecord(
            str(row["id"]),
            self._organization_id,
            str(row["transaction_id"]),
            str(row["fingerprint"]),
            str(row["actor_id"]),
            str(row["fingerprint_version"]),
        )

    def idempotency(self, actor_id: str, operation: str, key: str) -> IdempotencyRecord | None:
        row = self._db.execute(
            "SELECT request_fingerprint, resource_type, resource_id FROM command_idempotency "
            "WHERE ledger_book_id = ? AND actor_id = ? AND operation = ? "
            "AND idempotency_key = ?",
            (self._ledger_book_id, actor_id, operation, key),
        ).fetchone()
        if row is None:
            return None
        return IdempotencyRecord(
            str(row["request_fingerprint"]),
            str(row["resource_type"]),
            str(row["resource_id"]),
        )

    def create_confirmation(self, confirmation_id: str, validation_id: str, actor_id: str) -> None:
        self._db.execute(
            "INSERT INTO confirmations VALUES (?, ?, ?, ?)",
            (confirmation_id, self._ledger_book_id, validation_id, actor_id),
        )

    def create_confirmation_provenance(
        self,
        confirmation_id: str,
        proposal_id: str,
        proposal_version: int,
        confirmed_at: str,
        request_id: str,
    ) -> None:
        self._db.execute(
            "INSERT INTO confirmation_provenance ("
            "confirmation_id, ledger_book_id, proposal_id, proposal_version, confirmed_at, "
            "confirmation_request_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                confirmation_id,
                self._ledger_book_id,
                proposal_id,
                proposal_version,
                confirmed_at,
                request_id,
            ),
        )

    def confirmation(self, confirmation_id: str) -> ConfirmationRecord:
        row = self._required(
            "SELECT c.*, v.transaction_id, v.fingerprint, v.fingerprint_version "
            "FROM confirmations c JOIN validations v ON v.id = c.validation_id "
            "AND v.ledger_book_id = c.ledger_book_id "
            "WHERE c.id = ? AND c.ledger_book_id = ?",
            (confirmation_id, self._ledger_book_id),
        )
        return ConfirmationRecord(
            str(row["id"]),
            self._organization_id,
            str(row["validation_id"]),
            str(row["actor_id"]),
            str(row["transaction_id"]),
            str(row["fingerprint"]),
            str(row["fingerprint_version"]),
        )

    def confirmation_view(self, confirmation_id: str) -> dict[str, object]:
        return dict(
            self._required(
                "SELECT c.id, c.validation_id, c.actor_id, p.proposal_id, "
                "p.proposal_version, p.confirmed_at, p.confirmation_request_id "
                "FROM confirmations c JOIN confirmation_provenance p "
                "ON p.confirmation_id = c.id "
                "WHERE c.id = ? AND c.ledger_book_id = ?",
                (confirmation_id, self._ledger_book_id),
            )
        )

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
    ) -> None:
        self._db.execute(
            "INSERT INTO command_idempotency ("
            "id, ledger_book_id, actor_id, operation, idempotency_key, request_fingerprint, "
            "resource_type, resource_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                receipt_id,
                self._ledger_book_id,
                actor_id,
                operation,
                key,
                request_fingerprint,
                resource_type,
                resource_id,
                created_at,
            ),
        )

    def journal_entry(self, entry_id: str) -> JournalEntryRecord:
        return self._journal_entry_record(
            self._required(
                "SELECT * FROM journal_entries WHERE id = ? "
                "AND ledger_book_id = ? AND state = 'posted'",
                (entry_id, self._ledger_book_id),
            )
        )

    def journal_lines(self, entry_id: str) -> tuple[JournalLineRecord, ...]:
        return tuple(
            self._journal_line_record(row)
            for row in self._db.execute(
                "SELECT l.*, x.project_id FROM journal_lines l "
                "JOIN business_journal_line_projects x ON x.line_id = l.id "
                "AND x.ledger_book_id = l.ledger_book_id "
                "WHERE l.ledger_book_id = ? AND l.entry_id = ? ORDER BY l.position",
                (self._ledger_book_id, entry_id),
            )
        )

    def posted_reversal_exists(self, entry_id: str) -> bool:
        return (
            self._db.execute(
                "SELECT 1 FROM journal_entries WHERE ledger_book_id = ? "
                "AND reverses_entry_id = ? AND state = 'posted'",
                (self._ledger_book_id, entry_id),
            ).fetchone()
            is not None
        )

    def create_journal_header(self, entry: JournalEntryRecord) -> None:
        self._db.execute(
            "INSERT INTO journal_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.id,
                self._ledger_book_id,
                entry.transaction_id,
                entry.confirmation_id,
                entry.period_id,
                entry.entry_date,
                entry.description,
                entry.reverses_entry_id,
                entry.state,
            ),
        )

    def create_journal_line(self, line: JournalLineRecord) -> None:
        self._db.execute(
            "INSERT INTO business_journal_line_projects "
            "(line_id, ledger_book_id, organization_id, project_id) VALUES (?, ?, ?, ?)",
            (line.id, self._ledger_book_id, self._organization_id, line.project_id),
        )
        self._db.execute(
            "INSERT INTO journal_lines VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                line.id,
                self._ledger_book_id,
                line.entry_id,
                line.position,
                line.account_id,
                line.debit,
                line.credit,
            ),
        )

    def seal_journal_entry(self, entry_id: str) -> None:
        self._db.execute(
            "UPDATE journal_entries SET state = 'posted' WHERE id = ? AND ledger_book_id = ?",
            (entry_id, self._ledger_book_id),
        )

    def transaction_view(self, transaction_id: str) -> dict[str, object]:
        result: dict[str, object] = self.proposal(transaction_id).fingerprint_mapping()
        result["lines"] = [
            dict(row)
            for row in self._db.execute(
                "SELECT l.position, l.account_id, a.code, a.name, l.debit, l.credit, "
                "x.project_id FROM transaction_lines l JOIN accounts a ON a.id = l.account_id "
                "AND a.ledger_book_id = l.ledger_book_id "
                "JOIN business_proposal_line_projects x ON x.line_id = l.id "
                "AND x.ledger_book_id = l.ledger_book_id "
                "WHERE l.ledger_book_id = ? AND l.transaction_id = ? ORDER BY l.position",
                (self._ledger_book_id, transaction_id),
            )
        ]
        posted = self.posted_entry_for_transaction(transaction_id)
        result["posted_entry_id"] = posted.id if posted else None
        result["status"] = "posted" if posted else "proposed"
        if posted:
            lifecycle_state = "POSTED"
        elif self._db.execute(
            "SELECT 1 FROM confirmations c JOIN validations v ON v.id = c.validation_id "
            "AND v.ledger_book_id = c.ledger_book_id "
            "WHERE v.ledger_book_id = ? AND v.transaction_id = ? LIMIT 1",
            (self._ledger_book_id, transaction_id),
        ).fetchone():
            lifecycle_state = "CONFIRMED"
        elif self._db.execute(
            "SELECT 1 FROM validations WHERE ledger_book_id = ? AND transaction_id = ? LIMIT 1",
            (self._ledger_book_id, transaction_id),
        ).fetchone():
            lifecycle_state = "VALIDATED"
        else:
            lifecycle_state = "PROPOSED"
        result["lifecycle_state"] = lifecycle_state
        return result

    def validation_transaction_id(self, validation_id: str) -> str:
        return self.validation(validation_id).transaction_id

    def ledger_rows(
        self, *, as_of: str | None, starts_on: str | None, project_id: str | None
    ) -> tuple[dict[str, object], ...]:
        return tuple(
            dict(row)
            for row in self._db.execute(
                "SELECT e.id AS entry_id, e.transaction_id, e.entry_date, e.description, "
                "e.reverses_entry_id, l.id AS line_id, l.position, l.account_id, a.code, "
                "a.name AS account_name, a.account_type, l.debit, l.credit, x.project_id "
                "FROM journal_entries e JOIN journal_lines l ON l.entry_id = e.id "
                "AND l.ledger_book_id = e.ledger_book_id "
                "JOIN accounts a ON a.id = l.account_id "
                "AND a.ledger_book_id = l.ledger_book_id "
                "JOIN business_journal_line_projects x ON x.line_id = l.id "
                "AND x.ledger_book_id = l.ledger_book_id "
                "WHERE e.ledger_book_id = ? AND e.state = 'posted' "
                "AND (? IS NULL OR e.entry_date <= ?) AND (? IS NULL OR e.entry_date >= ?) "
                "AND (? IS NULL OR x.project_id = ?) ORDER BY e.entry_date, e.id, l.position",
                (
                    self._ledger_book_id,
                    as_of,
                    as_of,
                    starts_on,
                    starts_on,
                    project_id,
                    project_id,
                ),
            )
        )

    def _journal_view(self, row: Mapping[str, object]) -> dict[str, object]:
        result: dict[str, object] = dict(row)
        result["lines"] = [
            dict(line)
            for line in self._db.execute(
                "SELECT l.position, l.account_id, a.code, a.name AS account_name, "
                "a.account_type, l.debit, l.credit, x.project_id "
                "FROM journal_lines l JOIN accounts a ON a.id = l.account_id "
                "AND a.ledger_book_id = l.ledger_book_id "
                "JOIN business_journal_line_projects x ON x.line_id = l.id "
                "AND x.ledger_book_id = l.ledger_book_id "
                "WHERE l.ledger_book_id = ? AND l.entry_id = ? ORDER BY l.position",
                (self._ledger_book_id, row["id"]),
            )
        ]
        return result

    def journal_entry_view(self, entry_id: str) -> dict[str, object]:
        row = self._required(
            "SELECT id, transaction_id, confirmation_id, period_id, entry_date, description, "
            "reverses_entry_id, state FROM journal_entries "
            "WHERE id = ? AND ledger_book_id = ? AND state = 'posted'",
            (entry_id, self._ledger_book_id),
        )
        result = dict(row)
        result["organization_id"] = self._organization_id
        return self._journal_view(result)

    def journal_entry_views(self) -> tuple[dict[str, object], ...]:
        return tuple(
            self._journal_view({**dict(row), "organization_id": self._organization_id})
            for row in self._db.execute(
                "SELECT id, transaction_id, confirmation_id, period_id, entry_date, "
                "description, reverses_entry_id, state FROM journal_entries "
                "WHERE ledger_book_id = ? AND state = 'posted' "
                "ORDER BY entry_date DESC, id DESC",
                (self._ledger_book_id,),
            )
        )

    def audit_events(self, *, entity_id: str | None) -> tuple[dict[str, object], ...]:
        return tuple(
            dict(row)
            for row in self._db.execute(
                "SELECT * FROM audit_events WHERE organization_id = ? "
                "AND (? IS NULL OR entity_id = ?) ORDER BY sequence",
                (self._organization_id, entity_id, entity_id),
            )
        )
