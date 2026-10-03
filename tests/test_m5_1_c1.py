import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chatbook import AccountingEngine, AccountType, ChatbookError, LineInput, OrganizationRole
from chatbook.api.main import create_app
from chatbook.database import Database
from chatbook.domain import MAX_AMOUNT
from chatbook.migration_evidence import (
    MIGRATION_TOOL_VERSION,
    PreflightFailure,
    build_preflight_manifest,
    create_verified_backup,
    legacy_table_evidence,
)
from chatbook.schema_contract import V2_TABLES, business_book_id


def _sqlite_backup(source: Path, destination: Path) -> None:
    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def _remove_v3_mapping(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript("""
            PRAGMA foreign_keys = OFF;
            DROP TRIGGER organization_creates_business_book;
            DROP TRIGGER ledger_book_matches_organization;
            DROP TRIGGER ledger_book_no_replace;
            DROP TRIGGER ledger_book_no_update;
            DROP TRIGGER ledger_book_no_delete;
            DROP TABLE ledger_books;
            PRAGMA user_version = 2;
        """)
    finally:
        connection.close()


def _drop_generated_update_guards(connection: sqlite3.Connection, table: str) -> None:
    connection.execute(f"DROP TRIGGER IF EXISTS no_update_{table}")
    connection.execute(f"DROP TRIGGER IF EXISTS audit_{table}_update")


class M51C1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def _empty_v2(self, name: str = "empty-v2.db") -> Path:
        path = self.root / name
        engine = AccountingEngine(path)
        engine.close()
        _remove_v3_mapping(path)
        return path

    def _populated_v2(self, name: str = "populated-v2.db") -> tuple[Path, dict[str, object]]:
        path = self.root / name
        engine = AccountingEngine(path)
        owner = engine.create_user("Sanitized owner")
        member = engine.create_user("Sanitized member")
        second_owner = engine.create_user("Second owner")

        organization = engine.create_organization(owner, "Sanitized studio", "BDT", 2)
        engine.add_member(owner, organization, member, OrganizationRole.ACCOUNTANT)
        bank = engine.create_account(owner, organization, "1000", "Bank", AccountType.ASSET)
        revenue = engine.create_account(owner, organization, "4000", "Revenue", AccountType.REVENUE)
        expense = engine.create_account(owner, organization, "5000", "Expense", AccountType.EXPENSE)
        inactive = engine.create_account(owner, organization, "1999", "Inactive", AccountType.ASSET)
        engine.set_account_active(owner, organization, inactive, False)
        september = engine.create_period(
            owner, organization, "September", "2026-09-01", "2026-09-30"
        )
        engine.create_period(owner, organization, "October", "2026-10-01", "2026-10-31")
        project = engine.create_project(
            owner,
            organization,
            "Sanitized project",
            description="Non-sensitive migration fixture",
            client="Fixture client",
            expected_revenue=50_000,
            budget=25_000,
            starts_on="2026-09-01",
            ends_on="2026-10-31",
        )
        document = engine.register_document(
            owner,
            organization,
            "fixture.pdf",
            "application/pdf",
            "a" * 64,
            "fixture://document",
        )

        pending = engine.create_transaction(
            owner,
            organization,
            "2026-10-10",
            "Maximum-value pending fixture",
            [LineInput(bank, debit=MAX_AMOUNT), LineInput(revenue, credit=MAX_AMOUNT)],
        )
        validated = engine.create_transaction(
            owner,
            organization,
            "2026-10-11",
            "Validated fixture",
            [LineInput(expense, debit=300), LineInput(bank, credit=300)],
        )
        validation_only = engine.validate_transaction(owner, organization, validated)
        confirmed = engine.create_transaction(
            owner,
            organization,
            "2026-10-12",
            "Confirmed fixture",
            [LineInput(expense, debit=400), LineInput(bank, credit=400)],
        )
        confirmed_validation = engine.validate_transaction(owner, organization, confirmed)
        confirmed_record = engine.confirm_transaction(
            owner,
            organization,
            confirmed_validation.id,
            accepted=True,
            proposal_id=confirmed,
            proposal_version=1,
            confirmation_request_id="fixture-confirmed-request",
            idempotency_key="fixture-confirmed-key",
            request_fingerprint="b" * 64,
        )

        posted = engine.create_transaction(
            owner,
            organization,
            "2026-09-15",
            "Posted fixture",
            [
                LineInput(bank, debit=1_200, project_id=project),
                LineInput(expense, debit=300, project_id=project),
                LineInput(revenue, credit=1_500, project_id=project),
            ],
            document_id=document,
        )
        posted_validation = engine.validate_transaction(owner, organization, posted)
        posted_confirmation = engine.confirm_transaction(
            owner,
            organization,
            posted_validation.id,
            accepted=True,
            proposal_id=posted,
            proposal_version=1,
            confirmation_request_id="fixture-post-request",
            idempotency_key="fixture-post-confirm-key",
            request_fingerprint="c" * 64,
        )
        entry = engine.post_transaction(
            owner,
            organization,
            posted_confirmation.id,
            idempotency_key="fixture-post-key",
            request_fingerprint="d" * 64,
        )
        engine.lock_period(owner, organization, september)
        reversal = engine.propose_reversal(
            owner, organization, entry, "2026-10-15", "Fixture reversal"
        )
        reversal_validation = engine.validate_transaction(owner, organization, reversal)
        reversal_confirmation = engine.confirm_transaction(
            owner,
            organization,
            reversal_validation.id,
            accepted=True,
        )
        reversal_entry = engine.post_transaction(owner, organization, reversal_confirmation.id)
        second_reversal = engine.propose_reversal(
            owner,
            organization,
            reversal_entry,
            "2026-10-16",
            "Fixture reversal chain",
        )
        second_reversal_validation = engine.validate_transaction(
            owner, organization, second_reversal
        )
        second_reversal_confirmation = engine.confirm_transaction(
            owner,
            organization,
            second_reversal_validation.id,
            accepted=True,
        )
        engine.post_transaction(owner, organization, second_reversal_confirmation.id)

        second_organization = engine.create_organization(
            second_owner, "Second sanitized business", "USD", 2
        )
        second_bank = engine.create_account(
            second_owner, second_organization, "1000", "Bank", AccountType.ASSET
        )
        second_revenue = engine.create_account(
            second_owner, second_organization, "4000", "Revenue", AccountType.REVENUE
        )
        engine.create_period(
            second_owner,
            second_organization,
            "September",
            "2026-09-01",
            "2026-09-30",
        )
        second_proposal = engine.create_transaction(
            second_owner,
            second_organization,
            "2026-09-20",
            "Second organization posting",
            [LineInput(second_bank, debit=700), LineInput(second_revenue, credit=700)],
        )
        second_validation = engine.validate_transaction(
            second_owner, second_organization, second_proposal
        )
        second_confirmation = engine.confirm_transaction(
            second_owner,
            second_organization,
            second_validation.id,
            accepted=True,
        )
        engine.post_transaction(second_owner, second_organization, second_confirmation.id)

        empty_organization = engine.create_organization(owner, "Empty sanitized business", "EUR", 2)
        before = {
            "legacy_tables": legacy_table_evidence(engine._db.connection),
            "ledger": engine.ledger(owner, organization),
            "trial": engine.trial_balance(owner, organization),
            "income": engine.income_statement(owner, organization, "2026-09-01", "2026-10-31"),
            "balance_sheet": engine.balance_sheet(owner, organization, "2026-10-31"),
            "cash_flow": engine.cash_flow(owner, organization, "2026-09-01", "2026-10-31", [bank]),
            "audit": tuple(
                tuple(row)
                for row in engine._db.connection.execute(
                    "SELECT * FROM audit_events ORDER BY sequence"
                )
            ),
            "receipts": tuple(
                tuple(row)
                for row in engine._db.connection.execute(
                    "SELECT * FROM command_idempotency ORDER BY id"
                )
            ),
        }
        identifiers: dict[str, object] = {
            "owner": owner,
            "member": member,
            "second_owner": second_owner,
            "organization": organization,
            "second_organization": second_organization,
            "empty_organization": empty_organization,
            "pending": pending,
            "validated": validated,
            "validation_only": validation_only.id,
            "confirmed": confirmed,
            "confirmed_record": confirmed_record.id,
            "entry": entry,
            "project": project,
            "document": document,
            "bank": bank,
            "post_confirmation": posted_confirmation.id,
            "before": before,
        }
        engine.close()
        _remove_v3_mapping(path)
        return path, identifiers

    def test_empty_v2_migrates_to_empty_v3_with_verified_backup(self) -> None:
        path = self._empty_v2()
        engine = AccountingEngine(path)
        self.addCleanup(engine.close)
        self.assertEqual(engine._db.connection.execute("PRAGMA user_version").fetchone()[0], 3)
        self.assertEqual(
            engine._db.connection.execute("SELECT count(*) FROM ledger_books").fetchone()[0], 0
        )
        backup = Path(f"{path.resolve()}.pre-v3.backup")
        self.assertTrue(backup.is_file())
        evidence = json.loads(Path(f"{backup}.manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(evidence["backup_restore_verified"])
        self.assertEqual(evidence["manifest"]["schema_version"], 2)

    def test_populated_v2_migration_preserves_business_state_and_reports(self) -> None:
        path, fixture = self._populated_v2()
        engine = AccountingEngine(path)
        self.addCleanup(engine.close)
        owner = str(fixture["owner"])
        organization = str(fixture["organization"])
        before = fixture["before"]
        assert isinstance(before, dict)
        self.assertEqual(engine._db.connection.execute("PRAGMA user_version").fetchone()[0], 3)
        books = tuple(
            engine._db.connection.execute("SELECT * FROM ledger_books ORDER BY organization_id")
        )
        self.assertEqual(len(books), 3)
        for book in books:
            self.assertEqual(book["id"], business_book_id(str(book["organization_id"])))
            self.assertEqual(book["owner_kind"], "BUSINESS")
            self.assertEqual(book["creation_source"], "schema_v3_migration")
            self.assertEqual(book["creation_version"], MIGRATION_TOOL_VERSION)
        self.assertEqual(legacy_table_evidence(engine._db.connection), before["legacy_tables"])
        self.assertEqual(engine.ledger(owner, organization), before["ledger"])
        self.assertEqual(engine.trial_balance(owner, organization), before["trial"])
        self.assertEqual(
            engine.income_statement(owner, organization, "2026-09-01", "2026-10-31"),
            before["income"],
        )
        self.assertEqual(
            engine.balance_sheet(owner, organization, "2026-10-31"),
            before["balance_sheet"],
        )
        self.assertEqual(
            engine.cash_flow(
                owner, organization, "2026-09-01", "2026-10-31", [str(fixture["bank"])]
            ),
            before["cash_flow"],
        )
        self.assertEqual(
            tuple(
                tuple(row)
                for row in engine._db.connection.execute(
                    "SELECT * FROM audit_events ORDER BY sequence"
                )
            ),
            before["audit"],
        )
        self.assertEqual(
            tuple(
                tuple(row)
                for row in engine._db.connection.execute(
                    "SELECT * FROM command_idempotency ORDER BY id"
                )
            ),
            before["receipts"],
        )
        retry = engine.post_transaction(
            owner,
            organization,
            str(fixture["post_confirmation"]),
            idempotency_key="fixture-post-key",
            request_fingerprint="d" * 64,
        )
        self.assertEqual(retry, fixture["entry"])

    def test_repeated_initialization_keeps_exactly_one_book_per_organization(self) -> None:
        path, _ = self._populated_v2()
        first = AccountingEngine(path)
        first.close()
        first_connection = sqlite3.connect(path)
        try:
            first_rows = first_connection.execute(
                "SELECT id, organization_id, currency, minor_unit_digits "
                "FROM ledger_books ORDER BY id"
            ).fetchall()
        finally:
            first_connection.close()
        second = AccountingEngine(path)
        second.close()
        connection = sqlite3.connect(path)
        try:
            second_rows = connection.execute(
                "SELECT id, organization_id, currency, minor_unit_digits "
                "FROM ledger_books ORDER BY id"
            ).fetchall()
            organization_count = connection.execute(
                "SELECT count(*) FROM organizations"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(first_rows, second_rows)
        self.assertEqual(len(second_rows), organization_count)

    def test_new_organization_atomically_creates_one_book_without_audit_event(self) -> None:
        path = self.root / "new-organization.db"
        engine = AccountingEngine(path)
        self.addCleanup(engine.close)
        actor = engine.create_user("Owner")
        before_audit = engine._db.connection.execute(
            "SELECT count(*) FROM audit_events"
        ).fetchone()[0]
        organization = engine.create_organization(actor, "New business", "BDT", 2)
        book = engine._resolve_business_ledger_book(actor, organization)
        self.assertEqual(book.id, business_book_id(organization))
        self.assertEqual(book.currency, "BDT")
        self.assertEqual(book.minor_unit_digits, 2)
        self.assertEqual(
            engine._db.connection.execute(
                "SELECT count(*) FROM audit_events WHERE entity_type = 'ledger_books'"
            ).fetchone()[0],
            0,
        )
        self.assertGreater(
            engine._db.connection.execute("SELECT count(*) FROM audit_events").fetchone()[0],
            before_audit,
        )

    def test_business_resolver_authorizes_before_mapping_and_rejects_raw_book_id(self) -> None:
        path = self.root / "resolver.db"
        engine = AccountingEngine(path)
        self.addCleanup(engine.close)
        owner_a = engine.create_user("Owner A")
        owner_b = engine.create_user("Owner B")
        organization_a = engine.create_organization(owner_a, "A", "BDT", 2)
        organization_b = engine.create_organization(owner_b, "B", "USD", 2)
        self.assertEqual(
            engine._resolve_business_ledger_book(owner_a, organization_a).organization_id,
            organization_a,
        )
        with self.assertRaisesRegex(ChatbookError, "not a member") as forbidden:
            engine._resolve_business_ledger_book(owner_a, organization_b)
        self.assertEqual(forbidden.exception.code, "forbidden")
        with self.assertRaises(ChatbookError) as raw_id:
            engine._resolve_business_ledger_book(owner_a, business_book_id(organization_a))
        self.assertEqual(raw_id.exception.code, "forbidden")

    def test_financial_tables_remain_organization_scoped_and_no_personal_domain_exists(
        self,
    ) -> None:
        path = self.root / "scope.db"
        engine = AccountingEngine(path)
        self.addCleanup(engine.close)
        financial_tables = (
            "charts_of_accounts",
            "accounts",
            "accounting_periods",
            "transactions",
            "transaction_lines",
            "validations",
            "confirmations",
            "command_idempotency",
            "journal_entries",
            "journal_lines",
        )
        for table in financial_tables:
            columns = {
                str(row["name"])
                for row in engine._db.connection.execute(f"PRAGMA table_info({table})")
            }
            self.assertIn("organization_id", columns)
            self.assertNotIn("ledger_book_id", columns)
        tables = {
            str(row[0])
            for row in engine._db.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertNotIn("personal_spaces", tables)
        openapi = json.dumps(create_app(path).openapi(), sort_keys=True)
        self.assertNotIn("ledger_book_id", openapi)
        self.assertNotIn("/personal-spaces", openapi)

    def test_verified_backup_restore_and_manifest_are_deterministic(self) -> None:
        path, _ = self._populated_v2()
        backup = self.root / "evidence.backup"
        evidence = create_verified_backup(path, backup, generated_at="2026-09-27T00:00:00+00:00")
        self.assertTrue(evidence["backup_restore_verified"])
        self.assertTrue(backup.is_file())
        self.assertTrue(Path(f"{backup}.manifest.json").is_file())
        connection = sqlite3.connect(path)
        try:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertIsNone(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ledger_books'"
                ).fetchone()
            )
        finally:
            connection.close()
        options = {
            "generated_at": "2026-09-27T00:00:00+00:00",
            "database_identity": "fixture-database",
            "database_sha256": "1" * 64,
            "backup_sha256": "2" * 64,
        }
        first = build_preflight_manifest(backup, **options)
        second = build_preflight_manifest(backup, **options)
        self.assertEqual(first, second)
        self.assertEqual(first["diagnostics"], [])
        self.assertEqual(first["schema_version"], 2)

    def test_unknown_schema_version_fails_without_migration(self) -> None:
        path = self._empty_v2("unknown.db")
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA user_version = 99")
        connection.close()
        with self.assertRaises(ChatbookError) as raised:
            AccountingEngine(path)
        self.assertEqual(raised.exception.code, "schema_version")
        self.assertFalse(Path(f"{path.resolve()}.pre-v3.backup").exists())

    def test_failed_v3_migration_rolls_back_all_schema_changes(self) -> None:
        path, _ = self._populated_v2("rollback.db")
        original = Database._execute_resource_script

        def fail_after_partial(database: Database, resource: str) -> None:
            if resource == "migrations/0003_business_ledger_books.sql":
                database.connection.execute("CREATE TABLE migration_partial (id TEXT)")
                raise RuntimeError("injected migration failure")
            original(database, resource)

        with patch.object(Database, "_execute_resource_script", fail_after_partial):
            with self.assertRaisesRegex(RuntimeError, "injected migration failure"):
                AccountingEngine(path)
        connection = sqlite3.connect(path)
        try:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            names = {
                str(row[0])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            self.assertNotIn("ledger_books", names)
            self.assertNotIn("migration_partial", names)
        finally:
            connection.close()
        self.assertTrue(Path(f"{path.resolve()}.pre-v3.backup").is_file())

    def test_failed_preflight_blocks_migration_and_preserves_schema_v2(self) -> None:
        path, _ = self._populated_v2("preflight-block.db")
        connection = sqlite3.connect(path)
        _drop_generated_update_guards(connection, "journal_lines")
        connection.execute(
            "UPDATE journal_lines SET debit = debit + 1 "
            "WHERE debit > 0 AND id = (SELECT id FROM journal_lines WHERE debit > 0 LIMIT 1)"
        )
        connection.commit()
        connection.close()
        with self.assertRaises(PreflightFailure) as raised:
            AccountingEngine(path)
        self.assertIn("journal.unbalanced", raised.exception.diagnostics)
        connection = sqlite3.connect(path)
        try:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertIsNone(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ledger_books'"
                ).fetchone()
            )
        finally:
            connection.close()

    def test_v3_startup_rejects_currency_mismatch_missing_mapping_and_orphan(self) -> None:
        cases = ("currency", "missing", "orphan")
        for case in cases:
            with self.subTest(case=case):
                path = self.root / f"mapping-{case}.db"
                engine = AccountingEngine(path)
                actor = engine.create_user("Owner")
                organization = engine.create_organization(actor, "Business", "BDT", 2)
                engine.close()
                connection = sqlite3.connect(path)
                connection.execute("PRAGMA foreign_keys = OFF")
                if case == "currency":
                    connection.execute("DROP TRIGGER ledger_book_no_update")
                    connection.execute(
                        "UPDATE ledger_books SET currency = 'USD' WHERE organization_id = ?",
                        (organization,),
                    )
                elif case == "missing":
                    connection.execute("DROP TRIGGER ledger_book_no_delete")
                    connection.execute(
                        "DELETE FROM ledger_books WHERE organization_id = ?", (organization,)
                    )
                else:
                    connection.execute("DROP TRIGGER ledger_book_matches_organization")
                    connection.execute(
                        "INSERT INTO ledger_books VALUES (?, 'BUSINESS', ?, 'BDT', 2, ?, ?, ?)",
                        (
                            business_book_id("missing"),
                            "missing",
                            "2026-09-27T00:00:00+00:00",
                            "schema_v3_migration",
                            MIGRATION_TOOL_VERSION,
                        ),
                    )
                connection.commit()
                connection.close()
                with self.assertRaises(ChatbookError) as raised:
                    AccountingEngine(path)
                self.assertEqual(raised.exception.code, "ledger_book_mapping_invalid")

    def test_preflight_rejects_each_corruption_with_specific_diagnostic(self) -> None:
        source, _ = self._populated_v2("corruption-source.db")
        baseline_copy = self.root / "corruption-baseline.db"
        _sqlite_backup(source, baseline_copy)
        baseline = build_preflight_manifest(baseline_copy, generated_at="2026-09-27T00:00:00+00:00")

        def corrupt_foreign_key(connection: sqlite3.Connection) -> None:
            connection.execute("PRAGMA foreign_keys = OFF")
            _drop_generated_update_guards(connection, "journal_lines")
            connection.execute(
                "UPDATE journal_lines SET account_id = 'missing-account' "
                "WHERE id = (SELECT id FROM journal_lines ORDER BY id LIMIT 1)"
            )

        def corrupt_unbalanced(connection: sqlite3.Connection) -> None:
            _drop_generated_update_guards(connection, "journal_lines")
            connection.execute(
                "UPDATE journal_lines SET debit = debit + 1 "
                "WHERE debit > 0 AND id = (SELECT id FROM journal_lines WHERE debit > 0 LIMIT 1)"
            )

        def corrupt_reversal(connection: sqlite3.Connection) -> None:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute("DROP TRIGGER journal_freeze")
            connection.execute("DROP TRIGGER audit_journal_entries_update")
            connection.execute(
                "UPDATE journal_entries SET reverses_entry_id = 'missing-entry' "
                "WHERE reverses_entry_id IS NOT NULL AND id = ("
                "SELECT id FROM journal_entries WHERE reverses_entry_id IS NOT NULL LIMIT 1)"
            )

        def corrupt_proposal_match(connection: sqlite3.Connection) -> None:
            connection.execute("DROP TRIGGER journal_freeze")
            connection.execute("DROP TRIGGER audit_journal_entries_update")
            connection.execute(
                "UPDATE journal_entries SET description = description || ' changed' "
                "WHERE id = (SELECT id FROM journal_entries ORDER BY id LIMIT 1)"
            )

        def corrupt_audit(connection: sqlite3.Connection) -> None:
            connection.execute("DROP TRIGGER audit_no_update")
            connection.execute(
                "UPDATE audit_events SET entity_id = 'missing-entity' "
                "WHERE sequence = (SELECT min(sequence) FROM audit_events)"
            )

        def corrupt_report(connection: sqlite3.Connection) -> None:
            connection.execute("DROP TRIGGER account_active_only")
            connection.execute("DROP TRIGGER audit_accounts_update")
            connection.execute(
                "UPDATE accounts SET name = name || ' changed' "
                "WHERE id = (SELECT id FROM accounts ORDER BY id LIMIT 1)"
            )

        def corrupt_idempotency(connection: sqlite3.Connection) -> None:
            connection.execute("DROP TRIGGER command_idempotency_no_update")
            connection.execute(
                "UPDATE command_idempotency SET resource_id = 'missing-resource' "
                "WHERE id = (SELECT id FROM command_idempotency ORDER BY id LIMIT 1)"
            )

        def corrupt_period(connection: sqlite3.Connection) -> None:
            connection.execute("DROP TRIGGER journal_freeze")
            connection.execute("DROP TRIGGER audit_journal_entries_update")
            connection.execute(
                "UPDATE journal_entries SET entry_date = '2099-01-01' "
                "WHERE id = (SELECT id FROM journal_entries ORDER BY id LIMIT 1)"
            )

        def corrupt_project(connection: sqlite3.Connection) -> None:
            connection.execute("PRAGMA foreign_keys = OFF")
            _drop_generated_update_guards(connection, "transaction_lines")
            connection.execute(
                "UPDATE transaction_lines SET project_id = 'missing-project' "
                "WHERE project_id IS NOT NULL AND id = ("
                "SELECT id FROM transaction_lines WHERE project_id IS NOT NULL LIMIT 1)"
            )

        def corrupt_validation(connection: sqlite3.Connection) -> None:
            _drop_generated_update_guards(connection, "validations")
            connection.execute(
                "UPDATE validations SET fingerprint = ? "
                "WHERE id = (SELECT id FROM validations ORDER BY id LIMIT 1)",
                ("0" * 64,),
            )

        cases = (
            ("foreign-key", corrupt_foreign_key, "database.foreign_key_integrity", None),
            ("unbalanced", corrupt_unbalanced, "journal.unbalanced", None),
            ("reversal", corrupt_reversal, "reversal.target_invalid", None),
            ("proposal", corrupt_proposal_match, "journal.proposal_mismatch", None),
            ("audit", corrupt_audit, "audit.entity_reference", None),
            ("report", corrupt_report, "report.fingerprint_mismatch", baseline),
            ("idempotency", corrupt_idempotency, "idempotency.resource_reference", None),
            ("period", corrupt_period, "journal.period_inconsistent", None),
            ("project", corrupt_project, "proposal.project_reference", None),
            ("validation", corrupt_validation, "validation.fingerprint_mismatch", None),
        )
        for name, corrupt, expected, comparison in cases:
            with self.subTest(case=name):
                path = self.root / f"corrupt-{name}.db"
                shutil.copy2(baseline_copy, path)
                connection = sqlite3.connect(path)
                try:
                    corrupt(connection)
                    connection.commit()
                finally:
                    connection.close()
                with self.assertRaises(PreflightFailure) as raised:
                    build_preflight_manifest(
                        path,
                        generated_at="2026-09-27T00:00:00+00:00",
                        expected_manifest=comparison,
                    )
                self.assertIn(expected, raised.exception.diagnostics)

    def test_v3_constraints_reject_duplicate_mismatch_and_mutation(self) -> None:
        path = self.root / "constraints.db"
        engine = AccountingEngine(path)
        self.addCleanup(engine.close)
        actor = engine.create_user("Owner")
        organization = engine.create_organization(actor, "Business", "BDT", 2)
        connection = engine._db.connection
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO ledger_books VALUES (?, 'BUSINESS', ?, 'BDT', 2, ?, ?, ?)",
                (
                    business_book_id(organization),
                    organization,
                    "2026-09-27T00:00:00+00:00",
                    "organization_creation",
                    MIGRATION_TOOL_VERSION,
                ),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO ledger_books VALUES (?, 'BUSINESS', ?, 'USD', 2, ?, ?, ?)",
                (
                    business_book_id("missing"),
                    "missing",
                    "2026-09-27T00:00:00+00:00",
                    "schema_v3_migration",
                    MIGRATION_TOOL_VERSION,
                ),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE ledger_books SET currency = 'USD' WHERE organization_id = ?",
                (organization,),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM ledger_books WHERE organization_id = ?", (organization,)
            )

    def test_manifest_includes_required_non_sensitive_evidence(self) -> None:
        path, _ = self._populated_v2("manifest.db")
        backup = self.root / "manifest.backup"
        evidence = create_verified_backup(path, backup)
        manifest = evidence["manifest"]
        assert isinstance(manifest, dict)
        self.assertEqual(manifest["tool_version"], MIGRATION_TOOL_VERSION)
        self.assertEqual(manifest["integrity_check"], ["ok"])
        self.assertEqual(manifest["foreign_key_violation_count"], 0)
        self.assertEqual(set(manifest["tables"]), set(V2_TABLES))
        metrics = manifest["metrics"]
        assert isinstance(metrics, dict)
        self.assertEqual(metrics["organization_count"], 3)
        self.assertGreater(metrics["proposal_count"], 0)
        self.assertGreater(metrics["audit_count"], 0)
        self.assertEqual(len(manifest["report_fingerprints"]), 3)
        serialized = json.dumps(manifest)
        self.assertNotIn("Maximum-value pending fixture", serialized)
        self.assertNotIn("Fixture client", serialized)


if __name__ == "__main__":
    unittest.main()
