import json
import random
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from chatbook import AccountingEngine, AccountType, ChatbookError, LineInput, ProjectStatus
from chatbook.domain import MAX_AMOUNT, canonical_date, parse_amount


class AccountingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "ledger.db"
        self.engine = AccountingEngine(self.path)
        self.addCleanup(self.engine.close)
        self.actor = self.engine.create_user("Owner")
        self.org = self.engine.create_organization(self.actor, "Design Studio", "BDT", 2)
        self.bank = self.engine.create_account(
            self.actor, self.org, "1000", "Bank", AccountType.ASSET
        )
        self.revenue = self.engine.create_account(
            self.actor, self.org, "4000", "Services", AccountType.REVENUE
        )
        self.expense = self.engine.create_account(
            self.actor, self.org, "5000", "Materials", AccountType.EXPENSE
        )
        self.period = self.engine.create_period(
            self.actor, self.org, "September", "2026-09-01", "2026-09-30"
        )

    def assert_error(self, code, callable_, *args, **kwargs):
        with self.assertRaises(ChatbookError) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def proposal(self, value=12345, *, date="2026-09-25", project=None):
        return self.engine.create_transaction(
            self.actor,
            self.org,
            date,
            "Client payment",
            [
                LineInput(self.bank, debit=value, project_id=project),
                LineInput(self.revenue, credit=value, project_id=project),
            ],
        )

    def confirm(self, transaction):
        validation = self.engine.validate_transaction(self.actor, self.org, transaction)
        return self.engine.confirm_transaction(self.actor, self.org, validation.id, accepted=True)

    def post(self, transaction):
        return self.engine.post_transaction(self.actor, self.org, self.confirm(transaction).id)

    def test_full_manual_lifecycle_and_audit(self):
        project = self.engine.create_project(
            self.actor,
            self.org,
            "Website",
            description="Client relaunch",
            client="Example Ltd",
            expected_revenue=500000,
            budget=150000,
            starts_on="2026-09-01",
            ends_on="2026-09-30",
            status=ProjectStatus.ACTIVE,
        )
        transaction = self.proposal(project=project)
        self.assertEqual(self.engine.ledger(self.actor, self.org), ())
        validation = self.engine.validate_transaction(self.actor, self.org, transaction)
        self.assertEqual(validation.debit_total, 12345)
        self.assertEqual(validation.credit_total, 12345)
        self.assertEqual(self.engine.ledger(self.actor, self.org), ())
        confirmation = self.engine.confirm_transaction(
            self.actor, self.org, validation.id, accepted=True
        )
        self.assertEqual(self.engine.ledger(self.actor, self.org), ())
        entry = self.engine.post_transaction(self.actor, self.org, confirmation.id)
        self.assertEqual(len(self.engine.ledger(self.actor, self.org)), 2)
        self.assertEqual(
            self.engine.account_balance(self.actor, self.org, self.bank).net_debit, 12345
        )
        report = self.engine.trial_balance(self.actor, self.org)
        self.assertTrue(report.balanced)
        self.assertEqual(report.total_debits, 12345)
        self.assertEqual(report.total_credits, 12345)
        income = self.engine.income_statement(self.actor, self.org, "2026-09-01", "2026-09-30")
        self.assertEqual(income["net_income"], 12345)
        sheet = self.engine.balance_sheet(self.actor, self.org, "2026-09-30")
        self.assertEqual(sheet["assets"], 12345)
        self.assertEqual(sheet["unclosed_earnings"], 12345)
        self.assertTrue(sheet["balanced"])
        original = self.engine.ledger(self.actor, self.org)
        reversal = self.engine.propose_reversal(
            self.actor, self.org, entry, "2026-09-26", "Duplicate"
        )
        self.assertEqual(self.engine.ledger(self.actor, self.org), original)
        reversal_entry = self.post(reversal)
        ledger = self.engine.ledger(self.actor, self.org)
        self.assertEqual(len(ledger), 4)
        self.assertEqual(tuple(row for row in ledger if row["entry_id"] == entry), original)
        reversed_lines = [row for row in ledger if row["entry_id"] == reversal_entry]
        self.assertTrue(all(row["reverses_entry_id"] == entry for row in reversed_lines))
        self.assertTrue(all(row["project_id"] == project for row in reversed_lines))
        self.assertEqual(self.engine.account_balance(self.actor, self.org, self.bank).net_debit, 0)
        self.assertEqual(self.engine.trial_balance(self.actor, self.org).total_debits, 0)
        self.assertEqual(
            self.engine.account_balance(
                self.actor, self.org, self.bank, as_of="2026-09-25"
            ).net_debit,
            12345,
        )
        events = self.engine.audit_events(self.actor, self.org)
        posted = [event for event in events if event["event_type"] == "journal_entries.update"]
        self.assertEqual(len(posted), 2)
        for event in posted:
            self.assertEqual(event["actor_id"], self.actor)
            self.assertTrue(event["occurred_at"].endswith("+00:00"))
            self.assertEqual(event["previous_state"]["state"], "assembling")
            self.assertEqual(event["new_state"]["state"], "posted")
            self.assertEqual(event["metadata"]["operation"], "transaction.post")
            self.assertTrue(event["metadata"]["request_id"])

    def test_unbalanced_proposal_never_posts(self):
        transaction = self.engine.create_transaction(
            self.actor,
            self.org,
            "2026-09-25",
            "Incorrect",
            [LineInput(self.bank, debit=100), LineInput(self.revenue, credit=99)],
        )
        self.assert_error(
            "unbalanced_entry", self.engine.validate_transaction, self.actor, self.org, transaction
        )
        self.assertEqual(self.engine.ledger(self.actor, self.org), ())

    def test_incomplete_proposals_cannot_validate(self):
        for lines in ([], [LineInput(self.bank, debit=1)]):
            transaction = self.engine.create_transaction(
                self.actor, self.org, "2026-09-25", "Draft", lines
            )
            self.assert_error(
                "invalid_line_count",
                self.engine.validate_transaction,
                self.actor,
                self.org,
                transaction,
            )

    def test_invalid_amounts_and_sides_are_rejected_atomically(self):
        before = len(self.engine.audit_events(self.actor, self.org))
        for debit, credit in (
            (-1, 0),
            (0, -1),
            (1.5, 0),
            (True, 0),
            ("1", 0),
            (MAX_AMOUNT + 1, 0),
            (0, 0),
            (1, 1),
        ):
            with self.subTest(debit=debit, credit=credit), self.assertRaises(ChatbookError):
                self.engine.create_transaction(
                    self.actor,
                    self.org,
                    "2026-09-25",
                    "Bad",
                    [LineInput(self.bank, debit=debit, credit=credit)],
                )
        self.assertEqual(len(self.engine.audit_events(self.actor, self.org)), before)

    def test_confirmation_is_explicit_and_required(self):
        transaction = self.proposal()
        validation = self.engine.validate_transaction(self.actor, self.org, transaction)
        for invalid in (False, 1, "yes", None):
            self.assert_error(
                "confirmation_required",
                self.engine.confirm_transaction,
                self.actor,
                self.org,
                validation.id,
                accepted=invalid,
            )
        self.assert_error(
            "not_found", self.engine.post_transaction, self.actor, self.org, validation.id
        )
        self.assert_error(
            "not_found", self.engine.post_transaction, self.actor, self.org, transaction
        )
        self.assertEqual(self.engine.ledger(self.actor, self.org), ())

    def test_confirmation_cannot_be_used_by_another_member(self):
        other = self.engine.create_user("Colleague")
        self.engine.add_member(self.actor, self.org, other)
        confirmation = self.confirm(self.proposal())
        self.assert_error(
            "confirmation_actor", self.engine.post_transaction, other, self.org, confirmation.id
        )

    def test_period_must_exist_and_be_open(self):
        self.assert_error(
            "period_missing",
            self.engine.validate_transaction,
            self.actor,
            self.org,
            self.proposal(date="2026-10-01"),
        )
        transaction = self.proposal()
        self.engine.lock_period(self.actor, self.org, self.period)
        self.assert_error(
            "period_locked", self.engine.validate_transaction, self.actor, self.org, transaction
        )

    def test_lock_after_confirmation_blocks_post_without_partial_changes(self):
        confirmation = self.confirm(self.proposal())
        self.engine.lock_period(self.actor, self.org, self.period)
        before = self.engine.audit_events(self.actor, self.org)
        self.assert_error(
            "period_locked", self.engine.post_transaction, self.actor, self.org, confirmation.id
        )
        self.assertEqual(self.engine.ledger(self.actor, self.org), ())
        self.assertEqual(self.engine.audit_events(self.actor, self.org), before)

    def test_lock_after_validation_blocks_confirmation(self):
        validation = self.engine.validate_transaction(self.actor, self.org, self.proposal())
        self.engine.lock_period(self.actor, self.org, self.period)
        self.assert_error(
            "period_locked",
            self.engine.confirm_transaction,
            self.actor,
            self.org,
            validation.id,
            accepted=True,
        )

    def test_inactive_account_rechecked_at_post(self):
        confirmation = self.confirm(self.proposal())
        self.engine.set_account_active(self.actor, self.org, self.bank, False)
        self.assert_error(
            "inactive_account", self.engine.post_transaction, self.actor, self.org, confirmation.id
        )
        self.engine.set_account_active(self.actor, self.org, self.bank, True)
        self.engine.post_transaction(self.actor, self.org, confirmation.id)

    def test_period_overlap_and_date_validation(self):
        for start, end in (
            ("2026-09-30", "2026-10-31"),
            ("2026-08-01", "2026-09-01"),
            ("2026-09-10", "2026-09-11"),
        ):
            self.assert_error(
                "period_overlap",
                self.engine.create_period,
                self.actor,
                self.org,
                "Overlap",
                start,
                end,
            )
        for invalid in ("2026-02-30", "20260925", "2026-9-25", "nonsense"):
            self.assert_error("invalid_date", self.proposal, date=invalid)
        self.assert_error(
            "invalid_date_range",
            self.engine.create_period,
            self.actor,
            self.org,
            "Invalid",
            "2026-12-31",
            "2026-01-01",
        )

    def test_period_boundaries_are_inclusive(self):
        self.post(self.proposal(date="2026-09-01"))
        self.post(self.proposal(date="2026-09-30"))
        self.assertEqual(self.engine.trial_balance(self.actor, self.org).total_debits, 24690)

    def test_reverse_locked_original_in_later_open_period(self):
        entry = self.post(self.proposal())
        self.engine.lock_period(self.actor, self.org, self.period)
        self.engine.create_period(self.actor, self.org, "October", "2026-10-01", "2026-10-31")
        self.assert_error(
            "period_locked",
            self.engine.propose_reversal,
            self.actor,
            self.org,
            entry,
            "2026-09-26",
            "Correction",
        )
        reversal = self.engine.propose_reversal(
            self.actor, self.org, entry, "2026-10-01", "Correction"
        )
        self.post(reversal)
        self.assertEqual(
            self.engine.account_balance(
                self.actor, self.org, self.bank, as_of="2026-09-30"
            ).net_debit,
            12345,
        )
        self.assertEqual(self.engine.account_balance(self.actor, self.org, self.bank).net_debit, 0)

    def test_reversal_date_and_duplicate_reversal(self):
        entry = self.post(self.proposal())
        self.assert_error(
            "invalid_reversal_date",
            self.engine.propose_reversal,
            self.actor,
            self.org,
            entry,
            "2026-09-24",
            "Too early",
        )
        first = self.engine.propose_reversal(self.actor, self.org, entry, "2026-09-26", "First")
        second = self.engine.propose_reversal(self.actor, self.org, entry, "2026-09-26", "Second")
        confirmation = self.confirm(second)
        self.post(first)
        self.assert_error(
            "already_reversed", self.engine.post_transaction, self.actor, self.org, confirmation.id
        )

    def test_repeat_post_is_idempotent_even_after_period_lock(self):
        confirmation = self.confirm(self.proposal())
        entry = self.engine.post_transaction(self.actor, self.org, confirmation.id)
        self.engine.lock_period(self.actor, self.org, self.period)
        before = self.engine.audit_events(self.actor, self.org)
        self.assertEqual(self.engine.post_transaction(self.actor, self.org, confirmation.id), entry)
        self.assertEqual(self.engine.audit_events(self.actor, self.org), before)

    def test_another_confirmation_cannot_duplicate_post(self):
        transaction = self.proposal()
        first, second = self.confirm(transaction), self.confirm(transaction)
        self.engine.post_transaction(self.actor, self.org, first.id)
        self.assert_error(
            "already_posted", self.engine.post_transaction, self.actor, self.org, second.id
        )

    def test_posted_proposal_cannot_be_validated_or_confirmed_again(self):
        transaction = self.proposal()
        validation = self.engine.validate_transaction(self.actor, self.org, transaction)
        self.post(transaction)
        self.assert_error(
            "already_posted", self.engine.validate_transaction, self.actor, self.org, transaction
        )
        self.assert_error(
            "already_posted",
            self.engine.confirm_transaction,
            self.actor,
            self.org,
            validation.id,
            accepted=True,
        )

    def test_cross_organization_membership_and_references(self):
        outsider = self.engine.create_user("Other owner")
        other_org = self.engine.create_organization(outsider, "Other", "USD", 2)
        other_account = self.engine.create_account(
            outsider, other_org, "1", "Cash", AccountType.ASSET
        )
        other_project = self.engine.create_project(outsider, other_org, "Other project")
        other_document = self.engine.register_document(
            outsider, other_org, "file.pdf", "application/pdf", "a" * 64, "private/reference"
        )
        transaction = self.proposal()
        for read, args in (
            (self.engine.ledger, (outsider, self.org)),
            (self.engine.audit_events, (outsider, self.org)),
            (self.engine.get_transaction, (outsider, self.org, transaction)),
            (self.engine.catalog, (outsider, self.org)),
        ):
            self.assert_error("forbidden", read, *args)
        for lines, document in (
            ([LineInput(other_account, debit=10), LineInput(self.revenue, credit=10)], None),
            (
                [
                    LineInput(self.bank, debit=10, project_id=other_project),
                    LineInput(self.revenue, credit=10),
                ],
                None,
            ),
            ([LineInput(self.bank, debit=10), LineInput(self.revenue, credit=10)], other_document),
        ):
            self.assert_error(
                "constraint_violation",
                self.engine.create_transaction,
                self.actor,
                self.org,
                "2026-09-25",
                "Cross-org",
                lines,
                document_id=document,
            )

    def test_document_metadata_link_and_no_extraction(self):
        document = self.engine.register_document(
            self.actor, self.org, "receipt.pdf", "application/pdf", "b" * 64, "opaque/storage/key"
        )
        transaction = self.engine.create_transaction(
            self.actor,
            self.org,
            "2026-09-25",
            "Receipt",
            [LineInput(self.expense, debit=100), LineInput(self.bank, credit=100)],
            document_id=document,
        )
        self.post(transaction)
        self.assertEqual(
            self.engine.get_transaction(self.actor, self.org, transaction)["document_id"], document
        )

    def test_project_dimension_does_not_require_each_project_to_balance(self):
        project = self.engine.create_project(self.actor, self.org, "Project")
        transaction = self.engine.create_transaction(
            self.actor,
            self.org,
            "2026-09-25",
            "Expense",
            [
                LineInput(self.expense, debit=200, project_id=project),
                LineInput(self.bank, credit=200),
            ],
        )
        self.post(transaction)
        self.assertTrue(self.engine.trial_balance(self.actor, self.org).balanced)
        project_report = self.engine.trial_balance(self.actor, self.org, project_id=project)
        self.assertFalse(project_report.balanced)
        self.assertEqual(project_report.total_debits, 200)

    def test_reports_signs_and_equation_with_expenses_liabilities_equity(self):
        liability = self.engine.create_account(
            self.actor, self.org, "2000", "Payable", AccountType.LIABILITY
        )
        equity = self.engine.create_account(
            self.actor, self.org, "3000", "Capital", AccountType.EQUITY
        )
        self.post(
            self.engine.create_transaction(
                self.actor,
                self.org,
                "2026-09-01",
                "Capital",
                [LineInput(self.bank, debit=1000), LineInput(equity, credit=1000)],
            )
        )
        self.post(
            self.engine.create_transaction(
                self.actor,
                self.org,
                "2026-09-02",
                "Expense",
                [LineInput(self.expense, debit=200), LineInput(liability, credit=200)],
            )
        )
        self.post(self.proposal(500))
        income = self.engine.income_statement(self.actor, self.org, "2026-09-01", "2026-09-30")
        self.assertEqual(
            (income["revenue"], income["expenses"], income["net_income"]), (500, 200, 300)
        )
        sheet = self.engine.balance_sheet(self.actor, self.org, "2026-09-30")
        self.assertEqual(
            (sheet["assets"], sheet["liabilities"], sheet["total_equity"]), (1500, 200, 1300)
        )
        self.assertTrue(sheet["balanced"])

    def test_posted_records_proposals_and_audit_are_immutable_in_sql(self):
        transaction = self.proposal()
        entry = self.post(transaction)
        db = self.engine._db.connection
        line = db.execute("SELECT id FROM journal_lines WHERE entry_id = ?", (entry,)).fetchone()[0]
        statements = [
            ("UPDATE journal_entries SET description='changed' WHERE id=?", (entry,)),
            ("DELETE FROM journal_entries WHERE id=?", (entry,)),
            ("UPDATE journal_lines SET debit=debit+1 WHERE id=?", (line,)),
            ("DELETE FROM journal_lines WHERE id=?", (line,)),
            ("UPDATE transactions SET description='changed' WHERE id=?", (transaction,)),
            ("DELETE FROM transaction_lines WHERE transaction_id=?", (transaction,)),
            ("UPDATE audit_events SET actor_id=?", (self.actor,)),
            ("DELETE FROM audit_events", ()),
            (
                "INSERT OR REPLACE INTO journal_lines SELECT * FROM journal_lines WHERE id=?",
                (line,),
            ),
        ]
        before = self.engine.audit_events(self.actor, self.org)
        for sql, params in statements:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                db.execute(sql, params)
        with self.assertRaisesRegex(sqlite3.DatabaseError, "not authorized"):
            db.execute("INSERT OR REPLACE INTO audit_events SELECT * FROM audit_events LIMIT 1")
        self.assertEqual(self.engine.audit_events(self.actor, self.org), before)

    def test_cannot_append_lines_to_sealed_proposal_or_posted_entry(self):
        transaction = self.proposal()
        entry = self.post(transaction)
        db = self.engine._db.connection
        for table, parent, parent_id in (
            ("transaction_lines", "transaction_id", transaction),
            ("journal_lines", "entry_id", entry),
        ):
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    f"INSERT INTO {table} SELECT 'new-id', organization_id, {parent}, "
                    f"99, account_id, debit, credit, project_id FROM {table} "
                    f"WHERE {parent}=? LIMIT 1",
                    (parent_id,),
                )

    def test_sql_constraints_reject_unbalanced_and_mismatched_journals(self):
        transaction = self.proposal(100)
        confirmation = self.confirm(transaction)
        for bank_debit, revenue_credit, message in (
            (100, 99, "unbalanced_entry"),
            (200, 200, "proposal_mismatch"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ChatbookError, message):
                with self.engine._db.write(self.actor, "test.invalid_sql") as db:
                    db.execute(
                        "INSERT INTO journal_entries VALUES ('bad',?,?,?,?,?,?,NULL,'assembling')",
                        (
                            self.org,
                            transaction,
                            confirmation.id,
                            self.period,
                            "2026-09-25",
                            "Client payment",
                        ),
                    )
                    db.execute(
                        "INSERT INTO journal_lines VALUES ('bad-1',?,'bad',1,?,?,0,NULL)",
                        (self.org, self.bank, bank_debit),
                    )
                    db.execute(
                        "INSERT INTO journal_lines VALUES ('bad-2',?,'bad',2,?,0,?,NULL)",
                        (self.org, self.revenue, revenue_credit),
                    )
                    db.execute("UPDATE journal_entries SET state='posted' WHERE id='bad'")
        self.assertEqual(self.engine.ledger(self.actor, self.org), ())

    def test_database_rejects_direct_posted_insert_and_period_unlock(self):
        transaction = self.proposal()
        confirmation = self.confirm(transaction)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "invalid_initial_state"):
            self.engine._db.connection.execute(
                "INSERT INTO journal_entries VALUES ('bad',?,?,?,?,?,?,NULL,'posted')",
                (
                    self.org,
                    transaction,
                    confirmation.id,
                    self.period,
                    "2026-09-25",
                    "Client payment",
                ),
            )
        self.engine.lock_period(self.actor, self.org, self.period)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "period_immutable_or_locked"):
            self.engine._db.connection.execute(
                "UPDATE accounting_periods SET locked=0 WHERE id=?", (self.period,)
            )

    def test_storage_failure_rolls_back_journal_and_audit(self):
        confirmation = self.confirm(self.proposal())
        before = self.engine.audit_events(self.actor, self.org)
        self.engine._db.connection.execute(
            "CREATE TRIGGER simulated_failure BEFORE UPDATE ON journal_entries "
            "BEGIN SELECT RAISE(ABORT, 'simulated_failure'); END"
        )
        self.assert_error(
            "constraint_violation",
            self.engine.post_transaction,
            self.actor,
            self.org,
            confirmation.id,
        )
        self.assertEqual(self.engine.audit_events(self.actor, self.org), before)
        self.assertEqual(
            self.engine._db.connection.execute("SELECT count(*) FROM journal_entries").fetchone()[
                0
            ],
            0,
        )

    def test_simultaneous_retries_create_one_entry_and_one_audit_transition(self):
        confirmation = self.confirm(self.proposal())

        def post_on_connection(_):
            engine = AccountingEngine(self.path)
            try:
                return engine.post_transaction(self.actor, self.org, confirmation.id)
            finally:
                engine.close()

        with ThreadPoolExecutor(max_workers=6) as pool:
            entries = list(pool.map(post_on_connection, range(6)))
        self.assertEqual(len(set(entries)), 1)
        self.assertEqual(len(self.engine.ledger(self.actor, self.org)), 2)
        self.assertEqual(
            sum(
                event["event_type"] == "journal_entries.update"
                for event in self.engine.audit_events(self.actor, self.org)
            ),
            1,
        )

    def test_ledger_persists_across_connections(self):
        self.post(self.proposal())
        other = AccountingEngine(self.path)
        try:
            self.assertEqual(
                other.ledger(self.actor, self.org), self.engine.ledger(self.actor, self.org)
            )
            self.assertEqual(
                other.audit_events(self.actor, self.org),
                self.engine.audit_events(self.actor, self.org),
            )
        finally:
            other.close()

    def test_deterministic_generated_entries_preserve_invariants(self):
        rng = random.Random(20260925)
        for _ in range(40):
            value = rng.randint(2, MAX_AMOUNT)
            split = rng.randint(1, value - 1)
            transaction = self.engine.create_transaction(
                self.actor,
                self.org,
                "2026-09-25",
                "Generated",
                [
                    LineInput(self.bank, debit=split),
                    LineInput(self.bank, debit=value - split),
                    LineInput(self.revenue, credit=value),
                ],
            )
            entry = self.post(transaction)
            if rng.choice([True, False]):
                self.post(
                    self.engine.propose_reversal(
                        self.actor, self.org, entry, "2026-09-26", "Generated"
                    )
                )
        ledger = self.engine.ledger(self.actor, self.org)
        self.assertEqual(sum(row["debit"] for row in ledger), sum(row["credit"] for row in ledger))
        for entry_id in {row["entry_id"] for row in ledger}:
            lines = [row for row in ledger if row["entry_id"] == entry_id]
            self.assertEqual(
                sum(row["debit"] for row in lines), sum(row["credit"] for row in lines)
            )
        self.assertTrue(self.engine.trial_balance(self.actor, self.org).balanced)
        self.assertTrue(self.engine.balance_sheet(self.actor, self.org, "2026-09-30")["balanced"])

    def test_precision_parser_never_rounds(self):
        self.assertEqual(parse_amount("123.45", 2), 12345)
        self.assertEqual(parse_amount("0.01", 2), 1)
        self.assertEqual(parse_amount("1.2", 3), 1200)
        self.assertEqual(parse_amount("123", 0), 123)
        for bad in ("0.001", "1e2", "NaN", "-1", "+1", "1,000", " 1", "1."):
            self.assert_error("invalid_amount", parse_amount, bad, 2)
        self.assertEqual(canonical_date("2024-02-29"), "2024-02-29")

    def test_audit_records_all_entities_and_previous_state(self):
        self.engine.create_project(self.actor, self.org, "Project")
        self.engine.register_document(
            self.actor, self.org, "a.pdf", "application/pdf", "a" * 64, "key"
        )
        self.post(self.proposal())
        self.engine.set_account_active(self.actor, self.org, self.bank, False)
        self.engine.lock_period(self.actor, self.org, self.period)
        events = self.engine.audit_events(self.actor, self.org)
        self.assertEqual(
            {event["entity_type"] for event in events},
            {
                "organizations",
                "memberships",
                "charts_of_accounts",
                "accounts",
                "projects",
                "documents",
                "accounting_periods",
                "transactions",
                "transaction_lines",
                "validations",
                "confirmations",
                "journal_entries",
                "journal_lines",
            },
        )
        account_event = [e for e in events if e["event_type"] == "accounts.update"][-1]
        self.assertEqual(account_event["previous_state"]["active"], 1)
        self.assertEqual(account_event["new_state"]["active"], 0)
        json.dumps(events)

    def test_database_integrity_and_foreign_keys(self):
        self.post(self.proposal())
        self.assertEqual(
            self.engine._db.connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
        )
        self.assertEqual(
            self.engine._db.connection.execute("PRAGMA foreign_key_check").fetchall(), []
        )


if __name__ == "__main__":
    unittest.main()
