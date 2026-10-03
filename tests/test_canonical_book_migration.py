"""Canonical book-scoped migration and repository tests."""

import hashlib
import json
import sqlite3
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from threading import Barrier
from typing import Any, cast

from fastapi.testclient import TestClient

from chatbook.api.main import create_app
from chatbook.auth import AuthService
from chatbook.canonical_database import CanonicalDatabase
from chatbook.canonical_migration import FAILURE_STAGES, rehearse_canonical_migration
from chatbook.cli import _parser, _run
from chatbook.database import Database
from chatbook.domain import AccountType, ChatbookError, LineInput, ProjectStatus
from chatbook.engine import AccountingEngine
from chatbook.migration_evidence import table_evidence
from chatbook.storage.sqlite_book import SQLiteBookStorage


class CanonicalBookMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _fixture(self, name: str = "source.db") -> tuple[Path, dict[str, str]]:
        path = self.root / name
        auth = AuthService(path)
        registered = auth.register("Owner", "owner@example.test", "correct horse battery")
        auth.close()
        engine = AccountingEngine(path)
        owner = registered.id
        organization = engine.create_organization(owner, "Studio", "BDT", 2)
        cash = engine.create_account(owner, organization, "1000", "Cash", AccountType.ASSET)
        expense = engine.create_account(owner, organization, "5000", "Expense", AccountType.EXPENSE)
        inactive = engine.create_account(
            owner, organization, "5001", "Inactive", AccountType.EXPENSE
        )
        engine.set_account_active(owner, organization, inactive, False)
        period = engine.create_period(owner, organization, "2026", "2026-01-01", "2026-12-31")
        project = engine.create_project(
            owner,
            organization,
            "SolutionRed",
            description="Project fixture",
            client="Client",
            expected_revenue=500_000,
            budget=250_000,
            starts_on="2026-01-01",
            ends_on="2026-12-31",
            status=ProjectStatus.ACTIVE,
        )
        document = engine.register_document(
            owner,
            organization,
            "receipt.pdf",
            "application/pdf",
            "a" * 64,
            "fixtures/receipt.pdf",
        )
        pending = engine.create_transaction(
            owner,
            organization,
            "2026-01-02",
            "Pending",
            (LineInput(expense, 100, 0), LineInput(cash, 0, 100)),
        )
        validated = engine.create_transaction(
            owner,
            organization,
            "2026-01-03",
            "Validated",
            (LineInput(expense, 200, 0), LineInput(cash, 0, 200)),
        )
        validation_only = engine.validate_transaction(owner, organization, validated)
        confirmed = engine.create_transaction(
            owner,
            organization,
            "2026-01-04",
            "Confirmed",
            (LineInput(expense, 300, 0), LineInput(cash, 0, 300)),
        )
        confirmed_validation = engine.validate_transaction(owner, organization, confirmed)
        confirmation = engine.confirm_transaction(
            owner,
            organization,
            confirmed_validation.id,
            accepted=True,
            proposal_id=confirmed,
            proposal_version=1,
            confirmation_request_id="confirm-confirmed",
            idempotency_key="confirm-confirmed",
            request_fingerprint="b" * 64,
        )
        posted = engine.create_transaction(
            owner,
            organization,
            "2026-01-05",
            "Posted",
            (
                LineInput(expense, 9_000_000_000_000, 0, project),
                LineInput(cash, 0, 9_000_000_000_000, project),
            ),
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
            confirmation_request_id="confirm-posted-key",
            idempotency_key="confirm-posted-key",
            request_fingerprint="c" * 64,
        )
        entry = engine.post_transaction(
            owner,
            organization,
            posted_confirmation.id,
            idempotency_key="post-posted-key",
            request_fingerprint="d" * 64,
        )
        reversal = engine.propose_reversal(
            owner, organization, entry, "2026-01-06", "Correct posted fixture"
        )
        reversal_validation = engine.validate_transaction(owner, organization, reversal)
        reversal_confirmation = engine.confirm_transaction(
            owner,
            organization,
            reversal_validation.id,
            accepted=True,
            proposal_id=reversal,
            proposal_version=1,
            confirmation_request_id="confirm-reversal",
        )
        reversal_entry = engine.post_transaction(owner, organization, reversal_confirmation.id)
        chain = engine.propose_reversal(
            owner, organization, reversal_entry, "2026-01-07", "Restore fixture"
        )
        chain_validation = engine.validate_transaction(owner, organization, chain)
        chain_confirmation = engine.confirm_transaction(
            owner,
            organization,
            chain_validation.id,
            accepted=True,
            proposal_id=chain,
            proposal_version=1,
            confirmation_request_id="confirm-reversal-chain",
        )
        chain_entry = engine.post_transaction(owner, organization, chain_confirmation.id)
        second = engine.create_user("Second Owner")
        engine.add_member(owner, organization, second)
        second_org = engine.create_organization(second, "Other", "USD", 3)
        engine.create_account(second, second_org, "1000", "Cash", AccountType.ASSET)
        engine.create_period(second, second_org, "2026", "2026-01-01", "2026-12-31")
        second_period_id = next(iter(engine.list_periods(second, second_org)))["id"]
        engine.lock_period(second, second_org, str(second_period_id))
        snapshot = {
            "owner": owner,
            "organization": organization,
            "cash": cash,
            "expense": expense,
            "inactive": inactive,
            "period": period,
            "project": project,
            "document": document,
            "pending": pending,
            "validated": validated,
            "validation": validation_only.id,
            "confirmed": confirmed,
            "confirmation": confirmation.id,
            "posted": posted,
            "entry": entry,
            "reversal": reversal,
            "reversal_entry": reversal_entry,
            "chain": chain,
            "chain_entry": chain_entry,
            "second": second,
            "second_org": second_org,
        }
        engine.close()
        return path, snapshot

    def _migrate(self, source: Path) -> tuple[Path, dict[str, Any]]:
        target = self.root / f"{source.stem}-v4.db"
        evidence = rehearse_canonical_migration(
            source, target, self.root / f"{source.stem}.backup.db"
        )
        return target, evidence

    def test_migration_preserves_ids_history_reports_and_legacy_fingerprints(self) -> None:
        source, ids = self._fixture()
        before = AccountingEngine(source)
        reports_before = {
            "ledger": before.ledger(ids["owner"], ids["organization"]),
            "trial": asdict(before.trial_balance(ids["owner"], ids["organization"])),
            "income": before.income_statement(
                ids["owner"], ids["organization"], "2026-01-01", "2026-12-31"
            ),
            "balance": before.balance_sheet(ids["owner"], ids["organization"], "2026-12-31"),
            "cash_flow": before.cash_flow(
                ids["owner"],
                ids["organization"],
                "2026-01-01",
                "2026-12-31",
                [ids["cash"]],
            ),
            "account_balance": asdict(
                before.account_balance(ids["owner"], ids["organization"], ids["cash"])
            ),
            "project": asdict(
                before.trial_balance(ids["owner"], ids["organization"], project_id=ids["project"])
            ),
            "audit": before.audit_events(ids["owner"], ids["organization"]),
        }
        raw_before = table_evidence(before._db.connection, "audit_events")
        sequence_before = tuple(
            before._db.connection.execute("SELECT name, seq FROM sqlite_sequence ORDER BY name")
        )
        before.close()

        target, evidence = self._migrate(source)
        self.assertEqual(evidence["status"], "complete")
        self.assertTrue(evidence["source_unchanged"])
        with self.assertRaises(ChatbookError):
            Database(target)
        after = AccountingEngine.for_canonical_rehearsal(target)
        self.assertEqual(after.ledger(ids["owner"], ids["organization"]), reports_before["ledger"])
        self.assertEqual(
            asdict(after.trial_balance(ids["owner"], ids["organization"])),
            reports_before["trial"],
        )
        self.assertEqual(
            after.income_statement(ids["owner"], ids["organization"], "2026-01-01", "2026-12-31"),
            reports_before["income"],
        )
        self.assertEqual(
            after.balance_sheet(ids["owner"], ids["organization"], "2026-12-31"),
            reports_before["balance"],
        )
        self.assertEqual(
            after.cash_flow(
                ids["owner"],
                ids["organization"],
                "2026-01-01",
                "2026-12-31",
                [ids["cash"]],
            ),
            reports_before["cash_flow"],
        )
        self.assertEqual(
            asdict(after.account_balance(ids["owner"], ids["organization"], ids["cash"])),
            reports_before["account_balance"],
        )
        self.assertEqual(
            asdict(
                after.trial_balance(ids["owner"], ids["organization"], project_id=ids["project"])
            ),
            reports_before["project"],
        )
        self.assertEqual(
            after.audit_events(ids["owner"], ids["organization"]), reports_before["audit"]
        )
        self.assertEqual(table_evidence(after._db.connection, "audit_events"), raw_before)
        self.assertEqual(
            tuple(
                after._db.connection.execute("SELECT name, seq FROM sqlite_sequence ORDER BY name")
            ),
            sequence_before,
        )
        validation = after._db.connection.execute(
            "SELECT fingerprint_version FROM validations WHERE id = ?",
            (ids["validation"],),
        ).fetchone()
        self.assertEqual(validation[0], "organization-v1")
        after.confirm_transaction(
            ids["owner"],
            ids["organization"],
            ids["validation"],
            accepted=True,
            proposal_id=ids["validated"],
            proposal_version=1,
            confirmation_request_id="post-migration-confirmation",
        )
        after.close()

    def test_canonical_repository_posts_retries_reverses_and_scopes_new_audit(self) -> None:
        source, ids = self._fixture()
        target, _ = self._migrate(source)
        engine = AccountingEngine.for_canonical_rehearsal(target)
        proposal = engine.create_transaction(
            ids["owner"],
            ids["organization"],
            "2026-02-01",
            "Canonical write",
            (
                LineInput(ids["expense"], 500, 0, ids["project"]),
                LineInput(ids["cash"], 0, 500, ids["project"]),
            ),
            document_id=ids["document"],
        )
        validation = engine.validate_transaction(ids["owner"], ids["organization"], proposal)
        confirmation = engine.confirm_transaction(
            ids["owner"],
            ids["organization"],
            validation.id,
            accepted=True,
            proposal_id=proposal,
            proposal_version=1,
            confirmation_request_id="canonical-confirm-key",
            idempotency_key="canonical-confirm-key",
            request_fingerprint="e" * 64,
        )
        entry = engine.post_transaction(
            ids["owner"],
            ids["organization"],
            confirmation.id,
            idempotency_key="canonical-post-key",
            request_fingerprint="f" * 64,
        )
        self.assertEqual(
            engine.post_transaction(
                ids["owner"],
                ids["organization"],
                confirmation.id,
                idempotency_key="canonical-post-key",
                request_fingerprint="f" * 64,
            ),
            entry,
        )
        reversal = engine.propose_reversal(
            ids["owner"], ids["organization"], entry, "2026-02-02", "Canonical reversal"
        )
        reversal_validation = engine.validate_transaction(
            ids["owner"], ids["organization"], reversal
        )
        reversal_confirmation = engine.confirm_transaction(
            ids["owner"],
            ids["organization"],
            reversal_validation.id,
            accepted=True,
            proposal_id=reversal,
            proposal_version=1,
            confirmation_request_id="canonical-reversal-confirm",
        )
        reversal_entry = engine.post_transaction(
            ids["owner"], ids["organization"], reversal_confirmation.id
        )
        self.assertEqual(
            engine.get_journal_entry(ids["owner"], ids["organization"], entry)["id"], entry
        )
        self.assertEqual(
            engine.get_journal_entry(ids["owner"], ids["organization"], reversal_entry)[
                "reverses_entry_id"
            ],
            entry,
        )
        database = engine._db.connection
        applicable = database.execute(
            "SELECT count(*) FROM audit_events WHERE entity_type IN "
            "('charts_of_accounts','accounts','accounting_periods','transactions',"
            "'transaction_lines','validations','confirmations','journal_entries','journal_lines')"
        ).fetchone()[0]
        scopes = database.execute("SELECT count(*) FROM audit_event_book_scopes").fetchone()[0]
        self.assertEqual(scopes, applicable)
        self.assertEqual(
            database.execute(
                "SELECT count(*) FROM audit_event_book_scopes s JOIN audit_events a "
                "ON a.sequence = s.audit_sequence JOIN ledger_books b ON b.id = s.ledger_book_id "
                "WHERE a.organization_id IS NOT b.organization_id"
            ).fetchone()[0],
            0,
        )
        with self.assertRaises(sqlite3.DatabaseError):
            database.execute(
                "INSERT INTO audit_events (organization_id, actor_id, occurred_at, event_type, "
                "entity_type, entity_id, previous_state, new_state, metadata) "
                "VALUES (?, ?, '2026-01-01T00:00:00+00:00', 'forged', 'transactions', "
                "'forged', NULL, '{}', '{}')",
                (ids["organization"], ids["owner"]),
            )
        with self.assertRaises(sqlite3.DatabaseError):
            database.execute(
                "INSERT INTO audit_event_book_scopes VALUES (?, ?)",
                (999_999, f"book:business:{ids['organization']}"),
            )
        engine.close()

    def test_failure_injection_rolls_back_every_stage_and_never_changes_source(self) -> None:
        source, _ = self._fixture()
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        for index, stage in enumerate(FAILURE_STAGES):
            with self.subTest(stage=stage):
                target = self.root / f"failure-{index}.db"
                backup = self.root / f"failure-{index}.backup.db"
                with self.assertRaises(ChatbookError) as caught:
                    rehearse_canonical_migration(source, target, backup, fail_after=stage)
                expected_code = (
                    "migration_reconciliation"
                    if stage == "reconciliation_mismatch"
                    else "migration_failure_injected"
                )
                self.assertEqual(caught.exception.code, expected_code)
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), source_hash)
                connection = sqlite3.connect(target)
                try:
                    self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
                    self.assertEqual(
                        connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
                    )
                    self.assertFalse(
                        connection.execute(
                            "SELECT 1 FROM sqlite_master WHERE name LIKE 'v4_%' LIMIT 1"
                        ).fetchone()
                    )
                    self.assertIn(
                        "organization_id",
                        {
                            row[1]
                            for row in connection.execute("PRAGMA table_info(journal_entries)")
                        },
                    )
                finally:
                    connection.close()
                report = json.loads(Path(f"{target}.c3-report.json").read_text())
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["failure_stage"], stage)
                self.assertTrue(report["source_unchanged"])

    def test_cross_book_context_reference_and_history_attacks_fail_closed(self) -> None:
        source, ids = self._fixture()
        target, _ = self._migrate(source)
        engine = AccountingEngine.for_canonical_rehearsal(target)
        second_accounts = engine.list_accounts(ids["second"], ids["second_org"])
        second_cash = str(second_accounts[0]["id"])
        second_expense = engine.create_account(
            ids["second"], ids["second_org"], "5000", "Expense", AccountType.EXPENSE
        )
        second_period = engine.create_period(
            ids["second"], ids["second_org"], "2027", "2027-01-01", "2027-12-31"
        )
        second_proposal = engine.create_transaction(
            ids["second"],
            ids["second_org"],
            "2027-01-02",
            "Second book",
            (LineInput(second_expense, 10, 0), LineInput(second_cash, 0, 10)),
        )
        second_validation = engine.validate_transaction(
            ids["second"], ids["second_org"], second_proposal
        )
        second_confirmation = engine.confirm_transaction(
            ids["second"],
            ids["second_org"],
            second_validation.id,
            accepted=True,
            proposal_id=second_proposal,
            proposal_version=1,
            confirmation_request_id="second-book-confirmation",
        )
        context = engine._financial_context(ids["owner"], ids["organization"])
        engine.close()

        database = CanonicalDatabase(target)
        book_a = f"book:business:{ids['organization']}"
        book_b = f"book:business:{ids['second_org']}"
        chart_b = str(
            database.connection.execute(
                "SELECT id FROM charts_of_accounts WHERE ledger_book_id = ?", (book_b,)
            ).fetchone()[0]
        )

        with self.assertRaises(ChatbookError):
            with database.write(ids["second"], "attack.account", ledger_book_id=book_b) as db:
                db.execute(
                    "INSERT INTO business_proposal_documents VALUES (?, ?, ?, NULL)",
                    ("attack-transaction", book_b, ids["second_org"]),
                )
                db.execute(
                    "INSERT INTO transactions VALUES (?, ?, ?, ?, NULL, 1, 'assembling')",
                    ("attack-transaction", book_b, "2027-02-01", "Cross account"),
                )
                db.execute(
                    "INSERT INTO business_proposal_line_projects VALUES (?, ?, ?, NULL)",
                    ("attack-line", book_b, ids["second_org"]),
                )
                db.execute(
                    "INSERT INTO transaction_lines VALUES (?, ?, ?, 1, ?, 1, 0)",
                    ("attack-line", book_b, "attack-transaction", ids["expense"]),
                )

        with self.assertRaises(ChatbookError):
            with database.write(ids["second"], "attack.period", ledger_book_id=book_b) as db:
                db.execute(
                    "INSERT INTO journal_entries VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'assembling')",
                    (
                        "attack-entry-period",
                        book_b,
                        second_proposal,
                        second_confirmation.id,
                        ids["period"],
                        "2027-01-02",
                        "Cross period",
                    ),
                )

        with self.assertRaises(ChatbookError):
            with database.write(ids["second"], "attack.confirmation", ledger_book_id=book_b) as db:
                db.execute(
                    "INSERT INTO confirmations VALUES (?, ?, ?, ?)",
                    ("attack-confirmation", book_b, ids["validation"], ids["second"]),
                )

        with self.assertRaises(ChatbookError):
            with database.write(ids["second"], "attack.journal_line", ledger_book_id=book_b) as db:
                db.execute(
                    "INSERT INTO journal_entries VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'assembling')",
                    (
                        "attack-entry-line",
                        book_b,
                        second_proposal,
                        second_confirmation.id,
                        second_period,
                        "2027-01-02",
                        "Cross line",
                    ),
                )
                db.execute(
                    "INSERT INTO business_journal_line_projects VALUES (?, ?, ?, NULL)",
                    ("attack-journal-line", book_b, ids["second_org"]),
                )
                db.execute(
                    "INSERT INTO journal_lines VALUES (?, ?, ?, 1, ?, 1, 0)",
                    ("attack-journal-line", book_b, "attack-entry-line", ids["expense"]),
                )

        with self.assertRaises(ChatbookError):
            with database.write(ids["second"], "attack.idempotency", ledger_book_id=book_b) as db:
                db.execute(
                    "INSERT INTO command_idempotency VALUES "
                    "('attack-receipt', ?, ?, 'transaction.post', 'attack-key', ?, "
                    "'journal_entry', ?, '2027-01-01T00:00:00+00:00')",
                    (book_b, ids["second"], "1" * 64, ids["entry"]),
                )

        for extension, key, foreign_id in (
            ("business_proposal_line_projects", "line_id", ids["project"]),
            ("business_proposal_documents", "proposal_id", ids["document"]),
        ):
            with self.subTest(extension=extension):
                with self.assertRaises(ChatbookError):
                    with database.write(
                        ids["second"], "attack.extension", ledger_book_id=book_b
                    ) as db:
                        column = "project_id" if "line" in extension else "document_id"
                        db.execute(
                            f"INSERT INTO {extension} "
                            f"({key}, ledger_book_id, organization_id, {column}) "
                            "VALUES (?, ?, ?, ?)",
                            (f"attack-{key}", book_b, ids["second_org"], foreign_id),
                        )

        with self.assertRaises(ChatbookError):
            with database.write(ids["owner"], "attack.context", ledger_book_id=book_a) as db:
                db.execute(
                    "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, 'asset', 1)",
                    ("attack-account", book_b, chart_b, "9999", "Wrong context"),
                )

        with self.assertRaises(ChatbookError):
            with database.write(
                ids["owner"], "attack.missing_extension", ledger_book_id=book_a
            ) as db:
                db.execute(
                    "INSERT INTO transactions VALUES (?, ?, ?, ?, NULL, 1, 'assembling')",
                    ("attack-no-extension", book_a, "2026-04-01", "Missing extension"),
                )

        forged = replace(context, ledger_book_id=book_b)
        with self.assertRaises(ChatbookError):
            SQLiteBookStorage(database).bind(forged)

        with self.assertRaises(ChatbookError):
            with database.write(ids["owner"], "attack.history", ledger_book_id=book_a) as db:
                db.execute(
                    "UPDATE journal_entries SET description = 'forged' WHERE id = ?",
                    (ids["entry"],),
                )
        with self.assertRaises(sqlite3.DatabaseError):
            database.connection.execute(
                "UPDATE audit_events SET metadata = '{}' WHERE sequence = "
                "(SELECT min(sequence) FROM audit_events)"
            )
        with self.assertRaises(sqlite3.DatabaseError):
            database.connection.execute(
                "DELETE FROM audit_event_book_scopes WHERE audit_sequence = "
                "(SELECT min(audit_sequence) FROM audit_event_book_scopes)"
            )
        database.close()

    def test_business_api_and_cli_dispatcher_keep_their_public_behavior_on_v4(self) -> None:
        source, ids = self._fixture()
        target, _ = self._migrate(source)
        app = create_app(target, canonical_rehearsal=True)
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/token",
                json={
                    "username": "owner@example.test",
                    "password": "correct horse battery",
                },
            )
            self.assertEqual(login.status_code, 200, login.text)
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            organizations = client.get("/api/v1/organizations", headers=headers)
            self.assertEqual(organizations.status_code, 200, organizations.text)
            self.assertIn(ids["organization"], {row["id"] for row in organizations.json()})
            isolated = client.get(f"/api/v1/organizations/{ids['second_org']}", headers=headers)
            self.assertIn(isolated.status_code, {403, 404})
            proposal = client.post(
                f"/api/v1/organizations/{ids['organization']}/proposals",
                headers=headers,
                json={
                    "entry_date": "2026-03-01",
                    "description": "API on canonical persistence",
                    "document_id": ids["document"],
                    "lines": [
                        {
                            "account_id": ids["expense"],
                            "debit": 75,
                            "project_id": ids["project"],
                        },
                        {
                            "account_id": ids["cash"],
                            "credit": 75,
                            "project_id": ids["project"],
                        },
                    ],
                },
            )
            self.assertEqual(proposal.status_code, 201, proposal.text)
            proposal_body = proposal.json()
            validation = client.post(
                f"/api/v1/organizations/{ids['organization']}/proposals/"
                f"{proposal_body['id']}/validate",
                headers=headers,
            )
            self.assertEqual(validation.status_code, 200, validation.text)
            stale = client.post(
                f"/api/v1/organizations/{ids['organization']}/proposals/"
                f"{proposal_body['id']}/confirm",
                headers={**headers, "Idempotency-Key": "api-canonical-stale"},
                json={
                    "validation_id": validation.json()["id"],
                    "proposal_version": 2,
                    "accepted": True,
                },
            )
            self.assertEqual(stale.status_code, 409, stale.text)
            confirm_headers = {**headers, "Idempotency-Key": "api-canonical-confirm"}
            confirmation = client.post(
                f"/api/v1/organizations/{ids['organization']}/proposals/"
                f"{proposal_body['id']}/confirm",
                headers=confirm_headers,
                json={
                    "validation_id": validation.json()["id"],
                    "proposal_version": 1,
                    "accepted": True,
                },
            )
            self.assertEqual(confirmation.status_code, 200, confirmation.text)
            post_headers = {**headers, "Idempotency-Key": "api-canonical-post-key"}
            posted = client.post(
                f"/api/v1/organizations/{ids['organization']}/proposals/{proposal_body['id']}/post",
                headers=post_headers,
                json={"confirmation_id": confirmation.json()["id"]},
            )
            self.assertEqual(posted.status_code, 200, posted.text)
            retry = client.post(
                f"/api/v1/organizations/{ids['organization']}/proposals/{proposal_body['id']}/post",
                headers=post_headers,
                json={"confirmation_id": confirmation.json()["id"]},
            )
            self.assertEqual(retry.status_code, 200, retry.text)
            self.assertEqual(retry.json(), posted.json())
            trial = client.get(
                f"/api/v1/organizations/{ids['organization']}/reports/trial-balance",
                headers=headers,
            )
            self.assertEqual(trial.status_code, 200, trial.text)
            self.assertTrue(trial.json()["balanced"])
            audit = client.get(
                f"/api/v1/organizations/{ids['organization']}/audit-events",
                headers=headers,
            )
            self.assertEqual(audit.status_code, 200, audit.text)

            created_org = client.post(
                "/api/v1/organizations",
                headers=headers,
                json={"name": "Canonical New Org", "currency": "EUR", "minor_unit_digits": 2},
            )
            self.assertEqual(created_org.status_code, 201, created_org.text)
            new_org_id = created_org.json()["id"]
            account = client.post(
                f"/api/v1/organizations/{new_org_id}/accounts",
                headers=headers,
                json={"code": "1000", "name": "Cash", "account_type": "asset"},
            )
            self.assertEqual(account.status_code, 201, account.text)

        engine = AccountingEngine.for_canonical_rehearsal(target)
        arguments = _parser().parse_args(
            [
                "--actor",
                ids["owner"],
                "--org",
                ids["organization"],
                "catalog",
            ]
        )
        catalog = cast(dict[str, Any], _run(engine, arguments))
        self.assertEqual(catalog["organization"]["id"], ids["organization"])
        engine.close()

    def test_canonical_concurrency_serializes_retries_reversals_and_independent_books(self) -> None:
        source, ids = self._fixture()
        target, _ = self._migrate(source)

        def retry_post() -> str:
            worker = AccountingEngine.for_canonical_rehearsal(target)
            try:
                return worker.post_transaction(
                    ids["owner"],
                    ids["organization"],
                    ids["confirmation"],
                    idempotency_key="concurrent-canonical-post",
                    request_fingerprint="9" * 64,
                )
            finally:
                worker.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            retry_results = tuple(pool.map(lambda _: retry_post(), range(2)))
        self.assertEqual(len(set(retry_results)), 1)

        barrier = Barrier(2)

        def competing_reversal(index: int) -> tuple[str, str]:
            worker = AccountingEngine.for_canonical_rehearsal(target)
            try:
                proposal = worker.propose_reversal(
                    ids["owner"],
                    ids["organization"],
                    retry_results[0],
                    "2026-02-10",
                    f"Competing reversal {index}",
                )
                validation = worker.validate_transaction(
                    ids["owner"], ids["organization"], proposal
                )
                confirmation = worker.confirm_transaction(
                    ids["owner"],
                    ids["organization"],
                    validation.id,
                    accepted=True,
                    proposal_id=proposal,
                    proposal_version=1,
                    confirmation_request_id=f"competing-reversal-{index}",
                )
                barrier.wait(timeout=10)
                try:
                    entry = worker.post_transaction(
                        ids["owner"], ids["organization"], confirmation.id
                    )
                    return "posted", entry
                except ChatbookError as exc:
                    return "rejected", exc.code
            finally:
                worker.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            reversal_results = tuple(pool.map(competing_reversal, range(2)))
        self.assertEqual([result[0] for result in reversal_results].count("posted"), 1)
        self.assertEqual([result[0] for result in reversal_results].count("rejected"), 1)

        def create_account(actor: str, organization: str, code: str) -> str:
            worker = AccountingEngine.for_canonical_rehearsal(target)
            try:
                return worker.create_account(actor, organization, code, code, AccountType.ASSET)
            finally:
                worker.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            account_results = (
                pool.submit(create_account, ids["owner"], ids["organization"], "concurrent-a"),
                pool.submit(create_account, ids["second"], ids["second_org"], "concurrent-b"),
            )
            self.assertEqual(len({future.result() for future in account_results}), 2)

        connection = sqlite3.connect(target)
        try:
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM journal_entries WHERE transaction_id = ?",
                    (ids["confirmed"],),
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM journal_entries WHERE reverses_entry_id = ?",
                    (retry_results[0],),
                ).fetchone()[0],
                1,
            )
        finally:
            connection.close()

    def test_post_and_period_lock_remain_atomic_on_canonical_copy(self) -> None:
        source, ids = self._fixture()
        target, _ = self._migrate(source)
        barrier = Barrier(2)

        def post() -> str:
            worker = AccountingEngine.for_canonical_rehearsal(target)
            try:
                barrier.wait(timeout=10)
                try:
                    worker.post_transaction(ids["owner"], ids["organization"], ids["confirmation"])
                    return "posted"
                except ChatbookError as exc:
                    return exc.code
            finally:
                worker.close()

        def lock() -> str:
            worker = AccountingEngine.for_canonical_rehearsal(target)
            try:
                barrier.wait(timeout=10)
                worker.lock_period(ids["owner"], ids["organization"], ids["period"])
                return "locked"
            finally:
                worker.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            post_future = pool.submit(post)
            lock_future = pool.submit(lock)
            post_result = post_future.result()
            self.assertEqual(lock_future.result(), "locked")
        self.assertIn(post_result, {"posted", "period_locked"})
        connection = sqlite3.connect(target)
        try:
            rows = tuple(
                connection.execute(
                    "SELECT state FROM journal_entries WHERE transaction_id = ?",
                    (ids["confirmed"],),
                )
            )
            self.assertIn(len(rows), {0, 1})
            self.assertTrue(not rows or rows[0][0] == "posted")
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM journal_entries WHERE state = 'assembling'"
                ).fetchone()[0],
                0,
            )
        finally:
            connection.close()

    def test_version_paths_query_plans_and_repository_surface_fail_closed(self) -> None:
        fresh = self.root / "fresh.db"
        database = Database(fresh)
        self.assertEqual(database.connection.execute("PRAGMA user_version").fetchone()[0], 3)
        database.close()
        target, evidence = self._migrate(fresh)
        self.assertEqual(evidence["schema_version"], 4)
        self.assertGreater(evidence["timings_seconds"]["migration"], 0)
        self.assertGreater(evidence["target_bytes"], 0)
        plans = evidence["query_plans"]
        self.assertTrue(any("ledger_by_date" in step for step in plans["ledger_by_date"]))
        self.assertTrue(any("ledger_by_account" in step for step in plans["ledger_by_account"]))
        self.assertTrue(
            any(
                "command_idempotency" in step or "receipts_by_book" in step
                for step in plans["idempotency"]
            )
        )

        canonical = CanonicalDatabase(target)
        storage = SQLiteBookStorage(canonical)
        self.assertFalse(hasattr(storage, "connection"))
        self.assertFalse(hasattr(storage, "execute"))
        self.assertFalse(hasattr(storage, "cursor"))
        canonical.close()

        with self.assertRaises(ChatbookError):
            rehearse_canonical_migration(
                target, self.root / "v4-again.db", self.root / "v4-again.backup.db"
            )
        with self.assertRaises(ChatbookError):
            rehearse_canonical_migration(
                fresh, self.root / "existing.db", self.root / "existing.db"
            )
        unsupported = self.root / "unsupported.db"
        connection = sqlite3.connect(unsupported)
        connection.execute("PRAGMA user_version = 99")
        connection.close()
        with self.assertRaises(ChatbookError):
            rehearse_canonical_migration(
                unsupported,
                self.root / "unsupported-v4.db",
                self.root / "unsupported.backup.db",
            )

    def test_representative_volume_rehearsal_records_honest_performance_evidence(self) -> None:
        source = self.root / "volume.db"
        engine = AccountingEngine(source)
        owner = engine.create_user("Volume Owner")
        organization = engine.create_organization(owner, "Volume Studio", "BDT", 2)
        cash = engine.create_account(owner, organization, "1000", "Cash", AccountType.ASSET)
        revenue = engine.create_account(owner, organization, "4000", "Revenue", AccountType.REVENUE)
        engine.create_period(owner, organization, "2026", "2026-01-01", "2026-12-31")
        projects = tuple(
            engine.create_project(owner, organization, f"Project {index}") for index in range(5)
        )
        for index in range(100):
            value = 10_000 + index
            project = projects[index % len(projects)]
            proposal = engine.create_transaction(
                owner,
                organization,
                "2026-06-15",
                f"Volume transaction {index}",
                (
                    LineInput(cash, value, 0, project),
                    LineInput(revenue, 0, value, project),
                ),
            )
            validation = engine.validate_transaction(owner, organization, proposal)
            confirmation = engine.confirm_transaction(
                owner,
                organization,
                validation.id,
                accepted=True,
                proposal_id=proposal,
                proposal_version=1,
                confirmation_request_id=f"volume-confirmation-{index}",
            )
            engine.post_transaction(owner, organization, confirmation.id)
        engine.close()

        target, evidence = self._migrate(source)
        self.assertEqual(evidence["financial_projection"]["journal_entries"]["row_count"], 100)
        self.assertEqual(evidence["financial_projection"]["journal_lines"]["row_count"], 200)
        self.assertGreaterEqual(evidence["peak_temporary_bytes"], evidence["target_bytes"])
        self.assertGreater(evidence["timings_seconds"]["backup_and_verification"], 0)
        self.assertGreater(evidence["timings_seconds"]["restore_target"], 0)
        self.assertGreater(evidence["timings_seconds"]["index_and_trigger_installation"], 0)
        migrated = AccountingEngine.for_canonical_rehearsal(target)
        report_started = time.perf_counter()
        trial = migrated.trial_balance(owner, organization)
        report_seconds = time.perf_counter() - report_started
        migrated.close()
        self.assertTrue(trial.balanced)
        self.assertGreaterEqual(report_seconds, 0)
        performance_path = Path(f"{target}.performance.json")
        performance_path.write_text(
            json.dumps(
                {
                    "fixture": "synthetic-100-posted-transactions-200-lines",
                    "migration_seconds": evidence["timings_seconds"]["migration"],
                    "backup_and_verification_seconds": evidence["timings_seconds"][
                        "backup_and_verification"
                    ],
                    "restore_seconds": evidence["timings_seconds"]["restore_target"],
                    "index_and_trigger_seconds": evidence["timings_seconds"][
                        "index_and_trigger_installation"
                    ],
                    "report_seconds": report_seconds,
                    "source_bytes": evidence["source_bytes"],
                    "backup_bytes": evidence["backup_bytes"],
                    "target_bytes": evidence["target_bytes"],
                    "peak_temporary_bytes": evidence["peak_temporary_bytes"],
                },
                sort_keys=True,
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    unittest.main()
