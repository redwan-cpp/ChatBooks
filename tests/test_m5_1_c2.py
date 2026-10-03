import inspect
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from chatbook import AccountingEngine, AccountType, ChatbookError, LineInput
from chatbook.api.main import create_app
from chatbook.database import SCHEMA_VERSION
from chatbook.financial.commands import (
    CashMovementQuery,
    ConfirmProposalCommand,
    CreateProposalCommand,
    LedgerQuery,
    PostProposalCommand,
    ProposeReversalCommand,
)
from chatbook.financial.context import FinancialCapability
from chatbook.fingerprints import transaction_fingerprint


class M51C2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "c2.db"
        self.engine = AccountingEngine(self.path)
        self.addCleanup(self.engine.close)
        self.actor = self.engine.create_user("C2 owner")
        self.organization = self.engine.create_organization(self.actor, "C2 business", "BDT", 2)
        self.bank = self.engine.create_account(
            self.actor,
            self.organization,
            "1000",
            "Bank",
            AccountType.ASSET,
        )
        self.revenue = self.engine.create_account(
            self.actor,
            self.organization,
            "4000",
            "Revenue",
            AccountType.REVENUE,
        )
        self.period = self.engine.create_period(
            self.actor,
            self.organization,
            "September",
            "2026-09-01",
            "2026-09-30",
        )

    def assert_error(self, code: str, callable_, *args, **kwargs) -> None:
        with self.assertRaises(ChatbookError) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def proposal(self, value: int = 1_250) -> str:
        return self.engine.create_transaction(
            self.actor,
            self.organization,
            "2026-09-15",
            "Service extraction",
            [
                LineInput(self.bank, debit=value),
                LineInput(self.revenue, credit=value),
            ],
        )

    def test_universal_service_requires_valid_server_context_and_capability(self) -> None:
        service = self.engine._financial
        self.assert_error(
            "financial_context_required",
            service.list_accounts,
            None,
        )
        context = self.engine._financial_context(self.actor, self.organization)
        self.assertEqual(
            service.list_accounts(context),
            self.engine.list_accounts(self.actor, self.organization),
        )
        no_capability = replace(context, capabilities=frozenset())
        self.assert_error(
            "financial_capability_required",
            service.list_accounts,
            no_capability,
        )
        self.assertIn(FinancialCapability.VIEW_FINANCIALS, context.capabilities)

    def test_context_and_cross_organization_substitution_fail_closed(self) -> None:
        other = self.engine.create_organization(self.actor, "Other business", "BDT", 2)
        other_bank = self.engine.create_account(
            self.actor, other, "1000", "Other bank", AccountType.ASSET
        )
        other_revenue = self.engine.create_account(
            self.actor, other, "4000", "Other revenue", AccountType.REVENUE
        )
        self.engine.create_period(self.actor, other, "September", "2026-09-01", "2026-09-30")
        other_project = self.engine.create_project(self.actor, other, "Other project")
        other_proposal = self.engine.create_transaction(
            self.actor,
            other,
            "2026-09-15",
            "Other proposal",
            [
                LineInput(other_bank, debit=100),
                LineInput(other_revenue, credit=100),
            ],
        )

        own_context = self.engine._financial_context(self.actor, self.organization)
        other_book = self.engine._resolve_business_ledger_book(self.actor, other)
        forged = replace(own_context, ledger_book_id=other_book.id)
        self.assert_error(
            "invalid_financial_context",
            self.engine._financial.list_accounts,
            forged,
        )
        self.assert_error(
            "forbidden",
            self.engine.list_accounts,
            self.actor,
            other_book.id,
        )
        self.assert_error(
            "constraint_violation",
            self.engine.create_transaction,
            self.actor,
            self.organization,
            "2026-09-15",
            "Cross account",
            [
                LineInput(other_bank, debit=100),
                LineInput(self.revenue, credit=100),
            ],
        )
        self.assert_error(
            "constraint_violation",
            self.engine.create_transaction,
            self.actor,
            self.organization,
            "2026-09-15",
            "Cross project",
            [
                LineInput(self.bank, debit=100, project_id=other_project),
                LineInput(self.revenue, credit=100),
            ],
        )
        self.assert_error(
            "not_found",
            self.engine.validate_transaction,
            self.actor,
            self.organization,
            other_proposal,
        )

    def test_legacy_organization_v1_fingerprint_is_byte_compatible(self) -> None:
        proposal_id = self.proposal()
        validation = self.engine.validate_transaction(self.actor, self.organization, proposal_id)
        transaction = dict(
            self.engine._db.connection.execute(
                "SELECT * FROM transactions WHERE id = ?", (proposal_id,)
            ).fetchone()
        )
        lines = tuple(
            LineInput(row["account_id"], row["debit"], row["credit"], row["project_id"])
            for row in self.engine._db.connection.execute(
                "SELECT * FROM transaction_lines WHERE transaction_id = ? ORDER BY position",
                (proposal_id,),
            )
        )
        self.assertEqual(
            validation.fingerprint,
            transaction_fingerprint(transaction, lines),
        )

    def test_facade_and_service_reads_are_exactly_equal(self) -> None:
        project_id = self.engine.create_project(self.actor, self.organization, "Parity project")
        proposal_id = self.engine.create_transaction(
            self.actor,
            self.organization,
            "2026-09-15",
            "Service extraction",
            [
                LineInput(self.bank, debit=1_250, project_id=project_id),
                LineInput(self.revenue, credit=1_250, project_id=project_id),
            ],
        )
        validation = self.engine.validate_transaction(self.actor, self.organization, proposal_id)
        confirmation = self.engine.confirm_transaction(
            self.actor, self.organization, validation.id, accepted=True
        )
        entry_id = self.engine.post_transaction(self.actor, self.organization, confirmation.id)
        context = self.engine._financial_context(self.actor, self.organization)
        project_context = self.engine._financial_context(
            self.actor,
            self.organization,
            project_ids=frozenset({project_id}),
        )
        service = self.engine._financial

        self.assertEqual(
            service.get_transaction(context, proposal_id),
            self.engine.get_transaction(self.actor, self.organization, proposal_id),
        )
        self.assertEqual(
            service.get_journal_entry(context, entry_id),
            self.engine.get_journal_entry(self.actor, self.organization, entry_id),
        )
        self.assertEqual(
            service.list_journal_entries(context),
            self.engine.list_journal_entries(self.actor, self.organization),
        )
        self.assertEqual(
            service.trial_balance(context),
            self.engine.trial_balance(self.actor, self.organization),
        )
        self.assertEqual(
            service.account_balance(context, self.bank),
            self.engine.account_balance(self.actor, self.organization, self.bank),
        )
        self.assertEqual(
            service.ledger(project_context, LedgerQuery(project_id=project_id)),
            self.engine.ledger(self.actor, self.organization, project_id=project_id),
        )
        self.assertEqual(
            service.trial_balance(project_context, project_id=project_id),
            self.engine.trial_balance(self.actor, self.organization, project_id=project_id),
        )
        self.assertEqual(
            service.income_statement(context, "2026-09-01", "2026-09-30"),
            self.engine.income_statement(self.actor, self.organization, "2026-09-01", "2026-09-30"),
        )
        self.assertEqual(
            service.balance_sheet(context, "2026-09-30"),
            self.engine.balance_sheet(self.actor, self.organization, "2026-09-30"),
        )
        self.assertEqual(
            service.cash_flow(
                context,
                CashMovementQuery("2026-09-01", "2026-09-30", (self.bank,)),
            ),
            self.engine.cash_flow(
                self.actor,
                self.organization,
                "2026-09-01",
                "2026-09-30",
                (self.bank,),
            ),
        )
        self.assertEqual(
            service.audit_events(context),
            self.engine.audit_events(self.actor, self.organization),
        )

    def test_facade_and_direct_service_mutations_match_on_identical_copies(self) -> None:
        self.engine.close()
        facade_path = Path(self.folder.name) / "facade.db"
        service_path = Path(self.folder.name) / "service.db"
        shutil.copy2(self.path, facade_path)
        shutil.copy2(self.path, service_path)
        facade = AccountingEngine(facade_path)
        direct = AccountingEngine(service_path)
        self.addCleanup(facade.close)
        self.addCleanup(direct.close)
        fixed_time = "2026-09-27T00:00:00+00:00"
        for engine in (facade, direct):
            engine._db.connection.create_function("chatbook_now", 0, lambda: fixed_time)

        def identifiers() -> list[UUID]:
            return [UUID(int=value) for value in range(100, 180)]

        def facade_workflow() -> tuple[object, ...]:
            proposal = facade.create_transaction(
                self.actor,
                self.organization,
                "2026-09-15",
                "Differential",
                [
                    LineInput(self.bank, debit=321),
                    LineInput(self.revenue, credit=321),
                ],
            )
            validation = facade.validate_transaction(self.actor, self.organization, proposal)
            confirmation = facade.confirm_transaction(
                self.actor,
                self.organization,
                validation.id,
                accepted=True,
                proposal_id=proposal,
                proposal_version=1,
                confirmation_request_id="confirm-request",
                idempotency_key="confirm-key",
                request_fingerprint="a" * 64,
            )
            entry = facade.post_transaction(
                self.actor,
                self.organization,
                confirmation.id,
                idempotency_key="posting-key",
                request_fingerprint="b" * 64,
            )
            retry = facade.post_transaction(
                self.actor,
                self.organization,
                confirmation.id,
                idempotency_key="posting-key",
                request_fingerprint="b" * 64,
            )
            reversal = facade.propose_reversal(
                self.actor,
                self.organization,
                entry,
                "2026-09-16",
                "Differential reversal",
            )
            reversal_validation = facade.validate_transaction(
                self.actor, self.organization, reversal
            )
            reversal_confirmation = facade.confirm_transaction(
                self.actor,
                self.organization,
                reversal_validation.id,
                accepted=True,
                proposal_id=reversal,
                proposal_version=1,
                confirmation_request_id="reversal-confirm-request",
                idempotency_key="reversal-confirm-key",
                request_fingerprint="c" * 64,
            )
            reversal_entry = facade.post_transaction(
                self.actor,
                self.organization,
                reversal_confirmation.id,
                idempotency_key="reversal-posting-key",
                request_fingerprint="d" * 64,
            )
            return (
                proposal,
                validation,
                confirmation,
                entry,
                retry,
                reversal,
                reversal_validation,
                reversal_confirmation,
                reversal_entry,
            )

        def service_workflow() -> tuple[object, ...]:
            service = direct._financial
            context = direct._financial_context(self.actor, self.organization)
            proposal = service.create_transaction(
                context,
                CreateProposalCommand(
                    "2026-09-15",
                    "Differential",
                    (
                        LineInput(self.bank, debit=321),
                        LineInput(self.revenue, credit=321),
                    ),
                ),
            )
            context = direct._financial_context(self.actor, self.organization)
            validation = service.validate_transaction(context, proposal)
            context = direct._financial_context(
                self.actor, self.organization, request_id="confirm-request"
            )
            confirmation = service.confirm_transaction(
                context,
                ConfirmProposalCommand(
                    validation_id=validation.id,
                    accepted=True,
                    proposal_id=proposal,
                    proposal_version=1,
                    confirmation_request_id="confirm-request",
                    idempotency_key="confirm-key",
                    request_fingerprint="a" * 64,
                ),
            )
            context = direct._financial_context(
                self.actor, self.organization, request_id="posting-key"
            )
            entry = service.post_transaction(
                context,
                PostProposalCommand(confirmation.id, "posting-key", "b" * 64),
            )
            retry = service.post_transaction(
                context,
                PostProposalCommand(confirmation.id, "posting-key", "b" * 64),
            )
            context = direct._financial_context(self.actor, self.organization)
            reversal = service.propose_reversal(
                context,
                ProposeReversalCommand(entry, "2026-09-16", "Differential reversal"),
            )
            context = direct._financial_context(self.actor, self.organization)
            reversal_validation = service.validate_transaction(context, reversal)
            context = direct._financial_context(
                self.actor,
                self.organization,
                request_id="reversal-confirm-request",
            )
            reversal_confirmation = service.confirm_transaction(
                context,
                ConfirmProposalCommand(
                    validation_id=reversal_validation.id,
                    accepted=True,
                    proposal_id=reversal,
                    proposal_version=1,
                    confirmation_request_id="reversal-confirm-request",
                    idempotency_key="reversal-confirm-key",
                    request_fingerprint="c" * 64,
                ),
            )
            context = direct._financial_context(
                self.actor,
                self.organization,
                request_id="reversal-posting-key",
            )
            reversal_entry = service.post_transaction(
                context,
                PostProposalCommand(
                    reversal_confirmation.id,
                    "reversal-posting-key",
                    "d" * 64,
                ),
            )
            return (
                proposal,
                validation,
                confirmation,
                entry,
                retry,
                reversal,
                reversal_validation,
                reversal_confirmation,
                reversal_entry,
            )

        with (
            patch("chatbook.financial.business.uuid4", side_effect=identifiers()),
            patch("chatbook.financial.service.uuid4", side_effect=identifiers()),
            patch("chatbook.financial.service._now", return_value=fixed_time),
        ):
            facade_result = facade_workflow()
        with (
            patch("chatbook.financial.business.uuid4", side_effect=identifiers()),
            patch("chatbook.financial.service.uuid4", side_effect=identifiers()),
            patch("chatbook.financial.service._now", return_value=fixed_time),
        ):
            service_result = service_workflow()
        self.assertEqual(facade_result, service_result)

        with self.assertRaises(ChatbookError) as facade_conflict:
            facade.post_transaction(
                self.actor,
                self.organization,
                facade_result[2].id,
                idempotency_key="posting-key",
                request_fingerprint="e" * 64,
            )
        direct_context = direct._financial_context(
            self.actor, self.organization, request_id="posting-key"
        )
        with self.assertRaises(ChatbookError) as service_conflict:
            direct._financial.post_transaction(
                direct_context,
                PostProposalCommand(service_result[2].id, "posting-key", "e" * 64),
            )
        self.assertEqual(facade_conflict.exception.code, service_conflict.exception.code)
        self.assertEqual(str(facade_conflict.exception), str(service_conflict.exception))

        tables = (
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
        for table in tables:
            with self.subTest(table=table):
                left = [
                    tuple(row)
                    for row in facade._db.connection.execute(
                        f"SELECT * FROM {table} ORDER BY rowid"
                    )
                ]
                right = [
                    tuple(row)
                    for row in direct._db.connection.execute(
                        f"SELECT * FROM {table} ORDER BY rowid"
                    )
                ]
                self.assertEqual(left, right)
        self.assertEqual(
            facade.trial_balance(self.actor, self.organization),
            direct.trial_balance(self.actor, self.organization),
        )
        self.assertEqual(
            facade.income_statement(self.actor, self.organization, "2026-09-01", "2026-09-30"),
            direct.income_statement(self.actor, self.organization, "2026-09-01", "2026-09-30"),
        )

    def test_source_boundary_has_one_financial_implementation(self) -> None:
        root = Path(__file__).resolve().parents[1]
        api = (root / "chatbook" / "api" / "main.py").read_text(encoding="utf-8")
        cli = (root / "chatbook" / "cli.py").read_text(encoding="utf-8")
        engine = (root / "chatbook" / "engine.py").read_text(encoding="utf-8")
        service = (root / "chatbook" / "financial" / "service.py").read_text(encoding="utf-8")
        repository = (root / "chatbook" / "financial" / "repository.py").read_text(encoding="utf-8")
        storage = (root / "chatbook" / "storage" / "sqlite_organization.py").read_text(
            encoding="utf-8"
        )

        for boundary in (api, cli):
            self.assertNotIn(".execute(", boundary)
            self.assertNotIn("INSERT INTO journal_", boundary)
        for forbidden in (
            "INSERT INTO journal_entries",
            "INSERT INTO journal_lines",
            "FROM journal_entries",
            "FROM journal_lines",
            "validate_lines(",
            "net_income =",
        ):
            self.assertNotIn(forbidden, engine)
        for forbidden in (".execute(", ".connection", "import sqlite3"):
            self.assertNotIn(forbidden, service)
            self.assertNotIn(forbidden, repository)
        self.assertIn("INSERT INTO journal_entries", storage)
        self.assertIn("INSERT INTO journal_lines", storage)

        financial_methods = (
            "create_account",
            "create_period",
            "create_transaction",
            "validate_transaction",
            "confirm_transaction",
            "post_transaction",
            "propose_reversal",
            "trial_balance",
            "income_statement",
            "balance_sheet",
            "cash_flow",
        )
        for method_name in financial_methods:
            body = inspect.getsource(getattr(AccountingEngine, method_name))
            self.assertIn("self._financial.", body)

    def test_schema_and_public_api_remain_v3_without_book_authority(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 3)
        schema = create_app(self.path).openapi()
        serialized = str(schema)
        self.assertNotIn("ledger_book_id", serialized)
        self.assertNotIn("AuthorizedFinancialContext", serialized)
        self.assertNotIn("personal_space", serialized.lower())
        financial_tables = (
            "accounts",
            "accounting_periods",
            "transactions",
            "transaction_lines",
            "validations",
            "confirmations",
            "command_idempotency",
            "journal_entries",
            "journal_lines",
            "audit_events",
        )
        for table in financial_tables:
            columns = {
                str(row["name"])
                for row in self.engine._db.connection.execute(f"PRAGMA table_info({table})")
            }
            self.assertIn("organization_id", columns)
            self.assertNotIn("ledger_book_id", columns)


if __name__ == "__main__":
    unittest.main()
