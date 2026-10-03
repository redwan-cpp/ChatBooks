"""Stable BUSINESS compatibility facade over the universal financial service."""

import re
import sqlite3
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import cast
from uuid import uuid4

from .canonical_database import CanonicalDatabase
from .database import Database
from .domain import (
    AccountType,
    Balance,
    ChatbookError,
    Confirmation,
    LineInput,
    OrganizationRole,
    ProjectStatus,
    TrialBalance,
    Validation,
    amount,
    canonical_date,
)
from .financial.business import BusinessFinancialContextResolver
from .financial.commands import (
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
from .financial.context import AuthorizedFinancialContext
from .financial.repository import FinancialStorage
from .financial.service import UniversalFinancialService
from .ledger_books import BusinessLedgerBook
from .runtime import RuntimeConfiguration, RuntimeStorageMode, open_runtime_database
from .schema_contract import business_book_id
from .storage.sqlite_book import SQLiteBookStorage
from .storage.sqlite_organization import SQLiteOrganizationStorage


def _id() -> str:
    return str(uuid4())


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChatbookError("required_field", f"{field} must not be empty.")
    return value.strip()


class AccountingEngine:
    """BUSINESS authorization, extension resolution, and legacy response facade.

    Actor IDs must come from a trusted caller. FastAPI supplies authenticated actors; the local CLI
    is a trusted compatibility interface. All financial writes and calculations delegate to
    UniversalFinancialService.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._configure_database(Database(path), canonical_storage=False)

    def _configure_database(
        self, database: Database | CanonicalDatabase, *, canonical_storage: bool
    ) -> None:
        self._canonical_storage = canonical_storage
        self._db = database
        self._business_contexts = BusinessFinancialContextResolver(self._db)
        self._financial_storage: FinancialStorage = (
            SQLiteBookStorage(self._db)
            if canonical_storage and isinstance(self._db, CanonicalDatabase)
            else SQLiteOrganizationStorage(cast(Database, self._db))
        )
        self._financial = UniversalFinancialService(self._financial_storage)

    @classmethod
    def for_runtime(
        cls, configuration: RuntimeConfiguration, *, allow_thread_handoff: bool = False
    ) -> "AccountingEngine":
        """Open exactly the server-selected storage implementation."""
        instance = cls.__new__(cls)
        database = open_runtime_database(configuration, allow_thread_handoff=allow_thread_handoff)
        instance._configure_database(
            database,
            canonical_storage=(configuration.storage_mode is RuntimeStorageMode.CANONICAL_V4),
        )
        return instance

    @classmethod
    def for_canonical_rehearsal(
        cls, path: str | Path, *, allow_thread_handoff: bool = False
    ) -> "AccountingEngine":
        """Open an explicit migrated copy without changing normal schema-v3 startup."""
        instance = cls.__new__(cls)
        instance._configure_database(
            CanonicalDatabase(path, allow_thread_handoff=allow_thread_handoff),
            canonical_storage=True,
        )
        return instance

    def close(self) -> None:
        self._db.close()

    def _row(self, sql: str, parameters: Sequence[object] = ()) -> sqlite3.Row:
        row = self._db.connection.execute(sql, parameters).fetchone()
        if row is None:
            raise ChatbookError(
                "not_found", "The requested record was not found in this organization."
            )
        return cast(sqlite3.Row, row)

    def _authorize(self, actor_id: str, organization_id: str) -> None:
        if not self._db.connection.execute(
            "SELECT 1 FROM memberships WHERE organization_id = ? AND user_id = ?",
            (organization_id, actor_id),
        ).fetchone():
            raise ChatbookError("forbidden", "The actor is not a member of this organization.")

    def _resolve_business_ledger_book(
        self, actor_id: str, organization_id: str
    ) -> BusinessLedgerBook:
        return self._business_contexts.resolve_book(actor_id, organization_id)

    def _financial_context(
        self,
        actor_id: str,
        organization_id: str,
        *,
        request_id: str | None = None,
        project_ids: frozenset[str] | None = None,
    ) -> AuthorizedFinancialContext:
        context = self._business_contexts.resolve(actor_id, organization_id, request_id=request_id)
        if project_ids:
            for project_id in project_ids:
                self._row(
                    "SELECT id FROM projects WHERE id = ? AND organization_id = ?",
                    (project_id, organization_id),
                )
            context = replace(context, project_scope=project_ids)
        return context

    def _proposal_context(
        self,
        actor_id: str,
        organization_id: str,
        lines: Sequence[LineInput],
        document_id: str | None,
    ) -> AuthorizedFinancialContext:
        context = self._business_contexts.resolve(actor_id, organization_id)
        project_ids = frozenset(line.project_id for line in lines if line.project_id is not None)
        references = [("projects", project_id) for project_id in project_ids]
        if document_id is not None:
            references.append(("documents", document_id))
        for table, identifier in references:
            if (
                self._db.connection.execute(
                    f"SELECT 1 FROM {table} WHERE id = ? AND organization_id = ?",
                    (identifier, organization_id),
                ).fetchone()
                is None
            ):
                raise ChatbookError("constraint_violation", "FOREIGN KEY constraint failed")
        return replace(context, project_scope=project_ids or None)

    def create_user(self, name: str) -> str:
        user_id = _id()
        with self._db.write(user_id, "user.register") as db:
            db.execute("INSERT INTO users VALUES (?, ?)", (user_id, _text(name, "name")))
        return user_id

    def create_organization(
        self, actor_id: str, name: str, currency: str, minor_unit_digits: int
    ) -> str:
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ChatbookError(
                "invalid_currency", "Currency must be a three-letter uppercase code."
            )
        if type(minor_unit_digits) is not int or not 0 <= minor_unit_digits <= 6:
            raise ChatbookError("invalid_precision", "Minor unit digits must be between 0 and 6.")
        organization_id = _id()
        if isinstance(self._db, CanonicalDatabase):
            write_context = self._db.write(
                actor_id,
                "organization.create",
                ledger_book_id=business_book_id(organization_id),
            )
        else:
            write_context = self._db.write(actor_id, "organization.create")
        with write_context as db:
            self._row("SELECT id FROM users WHERE id = ?", (actor_id,))
            db.execute(
                "INSERT INTO organizations VALUES (?, ?, ?, ?)",
                (organization_id, _text(name, "name"), currency, minor_unit_digits),
            )
            db.execute(
                "INSERT INTO memberships (id, organization_id, user_id, role) VALUES (?, ?, ?, ?)",
                (_id(), organization_id, actor_id, OrganizationRole.OWNER.value),
            )
            if not self._canonical_storage:
                db.execute(
                    "INSERT INTO charts_of_accounts VALUES (?, ?, ?)",
                    (_id(), organization_id, "Chart of Accounts"),
                )
            book = self._resolve_business_ledger_book(actor_id, organization_id)
            if book.currency != currency or book.minor_unit_digits != minor_unit_digits:
                raise RuntimeError("Organization and BUSINESS LedgerBook configuration diverged.")
        return organization_id

    def add_member(
        self,
        actor_id: str,
        organization_id: str,
        user_id: str,
        role: OrganizationRole = OrganizationRole.MEMBER,
    ) -> None:
        if not isinstance(role, OrganizationRole):
            raise ChatbookError("invalid_role", "Choose a defined organization role.")
        with self._db.write(actor_id, "membership.create") as db:
            self._authorize(actor_id, organization_id)
            self._row("SELECT id FROM users WHERE id = ?", (user_id,))
            db.execute(
                "INSERT INTO memberships (id, organization_id, user_id, role) VALUES (?, ?, ?, ?)",
                (_id(), organization_id, user_id, role.value),
            )

    def organizations_for_actor(self, actor_id: str) -> tuple[dict[str, object], ...]:
        return tuple(
            dict(row)
            for row in self._db.connection.execute(
                "SELECT o.*, m.role FROM organizations o "
                "JOIN memberships m ON m.organization_id = o.id "
                "WHERE m.user_id = ? ORDER BY o.name, o.id",
                (actor_id,),
            )
        )

    def get_organization(self, actor_id: str, organization_id: str) -> dict[str, object]:
        self._authorize(actor_id, organization_id)
        return dict(
            self._row(
                "SELECT o.*, m.role FROM organizations o "
                "JOIN memberships m ON m.organization_id = o.id "
                "WHERE o.id = ? AND m.user_id = ?",
                (organization_id, actor_id),
            )
        )

    def membership_role(self, actor_id: str, organization_id: str) -> OrganizationRole:
        row = self._row(
            "SELECT role FROM memberships WHERE organization_id = ? AND user_id = ?",
            (organization_id, actor_id),
        )
        return OrganizationRole(str(row["role"]))

    def list_members(self, actor_id: str, organization_id: str) -> tuple[dict[str, object], ...]:
        self._authorize(actor_id, organization_id)
        return tuple(
            dict(row)
            for row in self._db.connection.execute(
                "SELECT m.user_id, u.name, m.role FROM memberships m "
                "JOIN users u ON u.id = m.user_id WHERE m.organization_id = ? "
                "ORDER BY u.name, m.user_id",
                (organization_id,),
            )
        )

    def create_account(
        self,
        actor_id: str,
        organization_id: str,
        code: str,
        name: str,
        account_type: AccountType,
    ) -> str:
        context = self._financial_context(actor_id, organization_id)
        return self._financial.create_account(
            context, CreateAccountCommand(code, name, account_type)
        )

    def set_account_active(
        self,
        actor_id: str,
        organization_id: str,
        account_id: str,
        active: bool,
    ) -> None:
        context = self._financial_context(actor_id, organization_id)
        self._financial.set_account_active(context, SetAccountActiveCommand(account_id, active))

    def get_account(
        self, actor_id: str, organization_id: str, account_id: str
    ) -> dict[str, object]:
        return self._financial.get_account(
            self._financial_context(actor_id, organization_id), account_id
        )

    def list_accounts(self, actor_id: str, organization_id: str) -> tuple[dict[str, object], ...]:
        return self._financial.list_accounts(self._financial_context(actor_id, organization_id))

    def create_period(
        self,
        actor_id: str,
        organization_id: str,
        name: str,
        starts_on: str,
        ends_on: str,
    ) -> str:
        return self._financial.create_period(
            self._financial_context(actor_id, organization_id),
            CreatePeriodCommand(name, starts_on, ends_on),
        )

    def lock_period(self, actor_id: str, organization_id: str, period_id: str) -> None:
        self._financial.lock_period(self._financial_context(actor_id, organization_id), period_id)

    def list_periods(self, actor_id: str, organization_id: str) -> tuple[dict[str, object], ...]:
        return self._financial.list_periods(self._financial_context(actor_id, organization_id))

    def create_project(
        self,
        actor_id: str,
        organization_id: str,
        name: str,
        *,
        description: str = "",
        client: str | None = None,
        expected_revenue: int | None = None,
        budget: int | None = None,
        starts_on: str | None = None,
        ends_on: str | None = None,
        status: ProjectStatus = ProjectStatus.PLANNED,
    ) -> str:
        for field, value in (("expected_revenue", expected_revenue), ("budget", budget)):
            if value is not None:
                amount(value, field)
        if starts_on is not None:
            canonical_date(starts_on, "starts_on")
        if ends_on is not None:
            canonical_date(ends_on, "ends_on")
        if starts_on is not None and ends_on is not None and ends_on < starts_on:
            raise ChatbookError("invalid_date_range", "Project end must be on or after its start.")
        if not isinstance(status, ProjectStatus):
            raise ChatbookError("invalid_status", "Choose a defined project status.")
        project_id = _id()
        with self._db.write(actor_id, "project.create") as db:
            self._authorize(actor_id, organization_id)
            db.execute(
                "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id,
                    organization_id,
                    _text(name, "name"),
                    description,
                    client,
                    expected_revenue,
                    budget,
                    starts_on,
                    ends_on,
                    status.value,
                ),
            )
        return project_id

    def get_project(
        self, actor_id: str, organization_id: str, project_id: str
    ) -> dict[str, object]:
        self._authorize(actor_id, organization_id)
        return dict(
            self._row(
                "SELECT * FROM projects WHERE id = ? AND organization_id = ?",
                (project_id, organization_id),
            )
        )

    def list_projects(self, actor_id: str, organization_id: str) -> tuple[dict[str, object], ...]:
        self._authorize(actor_id, organization_id)
        return tuple(
            dict(row)
            for row in self._db.connection.execute(
                "SELECT * FROM projects WHERE organization_id = ? ORDER BY name, id",
                (organization_id,),
            )
        )

    def update_project(
        self,
        actor_id: str,
        organization_id: str,
        project_id: str,
        *,
        name: str,
        description: str,
        client: str | None,
        expected_revenue: int | None,
        budget: int | None,
        starts_on: str | None,
        ends_on: str | None,
        status: ProjectStatus,
    ) -> dict[str, object]:
        for field, value in (("expected_revenue", expected_revenue), ("budget", budget)):
            if value is not None:
                amount(value, field)
        if starts_on is not None:
            canonical_date(starts_on, "starts_on")
        if ends_on is not None:
            canonical_date(ends_on, "ends_on")
        if starts_on is not None and ends_on is not None and ends_on < starts_on:
            raise ChatbookError("invalid_date_range", "Project end must be on or after its start.")
        if not isinstance(status, ProjectStatus):
            raise ChatbookError("invalid_status", "Choose a defined project status.")
        with self._db.write(actor_id, "project.update") as db:
            self._authorize(actor_id, organization_id)
            self._row(
                "SELECT id FROM projects WHERE id = ? AND organization_id = ?",
                (project_id, organization_id),
            )
            db.execute(
                "UPDATE projects SET name = ?, description = ?, client = ?, "
                "expected_revenue = ?, budget = ?, starts_on = ?, ends_on = ?, status = ? "
                "WHERE id = ? AND organization_id = ?",
                (
                    _text(name, "name"),
                    description,
                    client,
                    expected_revenue,
                    budget,
                    starts_on,
                    ends_on,
                    status.value,
                    project_id,
                    organization_id,
                ),
            )
        return self.get_project(actor_id, organization_id, project_id)

    def register_document(
        self,
        actor_id: str,
        organization_id: str,
        filename: str,
        media_type: str,
        sha256: str,
        storage_reference: str,
    ) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ChatbookError("invalid_checksum", "sha256 must contain 64 lowercase hex digits.")
        document_id = _id()
        with self._db.write(actor_id, "document.register") as db:
            self._authorize(actor_id, organization_id)
            db.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)",
                (
                    document_id,
                    organization_id,
                    _text(filename, "filename"),
                    _text(media_type, "media_type"),
                    sha256,
                    _text(storage_reference, "storage_reference"),
                ),
            )
        return document_id

    def create_transaction(
        self,
        actor_id: str,
        organization_id: str,
        entry_date: str,
        description: str,
        lines: Sequence[LineInput],
        *,
        document_id: str | None = None,
    ) -> str:
        line_values = tuple(lines)
        context = self._proposal_context(actor_id, organization_id, line_values, document_id)
        return self._financial.create_transaction(
            context,
            CreateProposalCommand(entry_date, description, line_values, document_id=document_id),
        )

    def validate_transaction(
        self, actor_id: str, organization_id: str, transaction_id: str
    ) -> Validation:
        return self._financial.validate_transaction(
            self._financial_context(actor_id, organization_id), transaction_id
        )

    def confirm_transaction(
        self,
        actor_id: str,
        organization_id: str,
        validation_id: str,
        *,
        accepted: bool,
        proposal_id: str | None = None,
        proposal_version: int | None = None,
        confirmation_request_id: str | None = None,
        idempotency_key: str | None = None,
        request_fingerprint: str | None = None,
    ) -> Confirmation:
        request_id = confirmation_request_id or idempotency_key
        context = self._financial_context(actor_id, organization_id, request_id=request_id)
        return self._financial.confirm_transaction(
            context,
            ConfirmProposalCommand(
                validation_id=validation_id,
                accepted=accepted,
                proposal_id=proposal_id,
                proposal_version=proposal_version,
                confirmation_request_id=confirmation_request_id,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            ),
        )

    def post_transaction(
        self,
        actor_id: str,
        organization_id: str,
        confirmation_id: str,
        *,
        idempotency_key: str | None = None,
        request_fingerprint: str | None = None,
    ) -> str:
        context = self._financial_context(actor_id, organization_id, request_id=idempotency_key)
        return self._financial.post_transaction(
            context,
            PostProposalCommand(confirmation_id, idempotency_key, request_fingerprint),
        )

    def propose_reversal(
        self,
        actor_id: str,
        organization_id: str,
        entry_id: str,
        entry_date: str,
        reason: str,
    ) -> str:
        return self._financial.propose_reversal(
            self._financial_context(actor_id, organization_id),
            ProposeReversalCommand(entry_id, entry_date, reason),
        )

    def get_transaction(
        self, actor_id: str, organization_id: str, transaction_id: str
    ) -> dict[str, object]:
        return self._financial.get_transaction(
            self._financial_context(actor_id, organization_id), transaction_id
        )

    def get_confirmation(
        self, actor_id: str, organization_id: str, confirmation_id: str
    ) -> dict[str, object]:
        return self._financial.get_confirmation(
            self._financial_context(actor_id, organization_id), confirmation_id
        )

    def proposal_for_validation(
        self, actor_id: str, organization_id: str, validation_id: str
    ) -> dict[str, object]:
        return self._financial.proposal_for_validation(
            self._financial_context(actor_id, organization_id), validation_id
        )

    def ledger(
        self,
        actor_id: str,
        organization_id: str,
        *,
        as_of: str | None = None,
        project_id: str | None = None,
        starts_on: str | None = None,
    ) -> tuple[dict[str, object], ...]:
        projects = frozenset({project_id}) if project_id is not None else None
        context = self._financial_context(actor_id, organization_id, project_ids=projects)
        return self._financial.ledger(context, LedgerQuery(as_of, project_id, starts_on))

    def get_journal_entry(
        self, actor_id: str, organization_id: str, entry_id: str
    ) -> dict[str, object]:
        return self._financial.get_journal_entry(
            self._financial_context(actor_id, organization_id), entry_id
        )

    def list_journal_entries(
        self, actor_id: str, organization_id: str
    ) -> tuple[dict[str, object], ...]:
        return self._financial.list_journal_entries(
            self._financial_context(actor_id, organization_id)
        )

    def trial_balance(
        self,
        actor_id: str,
        organization_id: str,
        *,
        as_of: str | None = None,
        project_id: str | None = None,
    ) -> TrialBalance:
        projects = frozenset({project_id}) if project_id is not None else None
        return self._financial.trial_balance(
            self._financial_context(actor_id, organization_id, project_ids=projects),
            as_of=as_of,
            project_id=project_id,
        )

    def account_balance(
        self,
        actor_id: str,
        organization_id: str,
        account_id: str,
        *,
        as_of: str | None = None,
    ) -> Balance:
        return self._financial.account_balance(
            self._financial_context(actor_id, organization_id),
            account_id,
            as_of=as_of,
        )

    def income_statement(
        self,
        actor_id: str,
        organization_id: str,
        starts_on: str,
        ends_on: str,
    ) -> dict[str, object]:
        return self._financial.income_statement(
            self._financial_context(actor_id, organization_id), starts_on, ends_on
        )

    def balance_sheet(self, actor_id: str, organization_id: str, as_of: str) -> dict[str, object]:
        return self._financial.balance_sheet(
            self._financial_context(actor_id, organization_id), as_of
        )

    def cash_flow(
        self,
        actor_id: str,
        organization_id: str,
        starts_on: str,
        ends_on: str,
        cash_account_ids: Sequence[str],
    ) -> dict[str, object]:
        return self._financial.cash_flow(
            self._financial_context(actor_id, organization_id),
            CashMovementQuery(starts_on, ends_on, tuple(cash_account_ids)),
        )

    def audit_events(
        self,
        actor_id: str,
        organization_id: str,
        *,
        entity_id: str | None = None,
    ) -> tuple[dict[str, object], ...]:
        return self._financial.audit_events(
            self._financial_context(actor_id, organization_id),
            entity_id=entity_id,
        )

    def catalog(self, actor_id: str, organization_id: str) -> dict[str, object]:
        context = self._financial_context(actor_id, organization_id)
        result: dict[str, object] = {
            "organization": dict(
                self._row("SELECT * FROM organizations WHERE id = ?", (organization_id,))
            ),
            "charts_of_accounts": list(self._financial.catalog_charts(context)),
            "accounts": list(self._financial.catalog_accounts(context)),
            "accounting_periods": list(self._financial.catalog_periods(context)),
        }
        for table in ("projects", "documents"):
            result[table] = [
                dict(row)
                for row in self._db.connection.execute(
                    f"SELECT * FROM {table} WHERE organization_id = ? ORDER BY id",
                    (organization_id,),
                )
            ]
        return result
