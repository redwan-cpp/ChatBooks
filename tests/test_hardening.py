import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from threading import Barrier

from chatbook import AccountingEngine, AccountType, ChatbookError, LineInput
from chatbook.domain import MAX_AMOUNT


class HardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "hardening.db"
        self.engine = AccountingEngine(self.path)
        self.addCleanup(self.engine.close)
        self.actor = self.engine.create_user("Hardening owner")
        self.org = self.engine.create_organization(self.actor, "Hardening Studio", "BDT", 2)
        self.bank = self.account("1000", "Bank", AccountType.ASSET)
        self.receivable = self.account("1100", "Receivable", AccountType.ASSET)
        self.payable = self.account("2000", "Payable", AccountType.LIABILITY)
        self.equity = self.account("3000", "Capital", AccountType.EQUITY)
        self.revenue = self.account("4000", "Revenue", AccountType.REVENUE)
        self.expense = self.account("5000", "Expense", AccountType.EXPENSE)
        self.period = self.engine.create_period(
            self.actor, self.org, "September", "2026-09-01", "2026-09-30"
        )

    def account(self, code: str, name: str, account_type: AccountType) -> str:
        return self.engine.create_account(self.actor, self.org, code, name, account_type)

    def transaction(
        self,
        description: str,
        lines: list[LineInput],
        *,
        entry_date: str = "2026-09-15",
    ) -> str:
        return self.engine.create_transaction(self.actor, self.org, entry_date, description, lines)

    def confirm(self, transaction_id: str):
        validation = self.engine.validate_transaction(self.actor, self.org, transaction_id)
        return self.engine.confirm_transaction(self.actor, self.org, validation.id, accepted=True)

    def post(self, transaction_id: str) -> str:
        confirmation = self.confirm(transaction_id)
        return self.engine.post_transaction(self.actor, self.org, confirmation.id)

    def assert_error(self, code: str, callable_, *args, **kwargs) -> None:
        with self.assertRaises(ChatbookError) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_mid_line_failure_rolls_back_header_lines_and_audit(self):
        transaction = self.transaction(
            "Atomic failure",
            [LineInput(self.bank, debit=100), LineInput(self.revenue, credit=100)],
        )
        confirmation = self.confirm(transaction)
        before = self.engine.audit_events(self.actor, self.org)
        self.engine._db.connection.execute(
            "CREATE TRIGGER fail_second_line BEFORE INSERT ON journal_lines "
            "WHEN NEW.position = 2 BEGIN SELECT RAISE(ABORT, 'mid_copy_failure'); END"
        )

        self.assert_error(
            "constraint_violation",
            self.engine.post_transaction,
            self.actor,
            self.org,
            confirmation.id,
        )

        db = self.engine._db.connection
        self.assertEqual(db.execute("SELECT count(*) FROM journal_entries").fetchone()[0], 0)
        self.assertEqual(db.execute("SELECT count(*) FROM journal_lines").fetchone()[0], 0)
        self.assertEqual(self.engine.ledger(self.actor, self.org), ())
        self.assertEqual(self.engine.audit_events(self.actor, self.org), before)

    def test_database_rejects_zero_value_lines_and_direct_audit_inserts(self):
        transaction = self.transaction(
            "Zero defense",
            [LineInput(self.bank, debit=100), LineInput(self.revenue, credit=100)],
        )
        confirmation = self.confirm(transaction)
        before = self.engine.audit_events(self.actor, self.org)

        with self.assertRaises(ChatbookError) as caught:
            with self.engine._db.write(self.actor, "test.zero_line") as db:
                db.execute(
                    "INSERT INTO journal_entries VALUES "
                    "('zero-entry',?,?,?,?,?,?,NULL,'assembling')",
                    (
                        self.org,
                        transaction,
                        confirmation.id,
                        self.period,
                        "2026-09-15",
                        "Zero defense",
                    ),
                )
                db.execute(
                    "INSERT INTO journal_lines VALUES ('zero-line',?,'zero-entry',1,?,0,0,NULL)",
                    (self.org, self.bank),
                )
        self.assertEqual(caught.exception.code, "constraint_violation")
        self.assertEqual(
            self.engine._db.connection.execute("SELECT count(*) FROM journal_entries").fetchone()[
                0
            ],
            0,
        )
        self.assertEqual(self.engine.audit_events(self.actor, self.org), before)

        with self.assertRaisesRegex(sqlite3.DatabaseError, "not authorized"):
            self.engine._db.connection.execute(
                "INSERT INTO audit_events "
                "(organization_id, actor_id, occurred_at, event_type, entity_type, "
                "entity_id, previous_state, new_state, metadata) "
                "VALUES (?, ?, '2000-01-01T00:00:00+00:00', 'forged', 'forged', "
                "'forged', NULL, NULL, '{}')",
                (self.org, self.actor),
            )
        self.assertEqual(self.engine.audit_events(self.actor, self.org), before)

    def test_full_reversal_and_reversal_of_reversal_preserve_chain(self):
        original = self.post(
            self.transaction(
                "Original",
                [LineInput(self.bank, debit=500), LineInput(self.revenue, credit=500)],
                entry_date="2026-09-10",
            )
        )
        original_lines = tuple(
            row for row in self.engine.ledger(self.actor, self.org) if row["entry_id"] == original
        )

        reversal_transaction = self.engine.propose_reversal(
            self.actor, self.org, original, "2026-09-11", "Correct original"
        )
        reversal = self.post(reversal_transaction)
        self.assertEqual(self.engine.account_balance(self.actor, self.org, self.bank).net_debit, 0)
        self.assert_error(
            "already_reversed",
            self.engine.propose_reversal,
            self.actor,
            self.org,
            original,
            "2026-09-12",
            "Duplicate reversal",
        )

        restore_transaction = self.engine.propose_reversal(
            self.actor, self.org, reversal, "2026-09-12", "Reverse the reversal"
        )
        restore = self.post(restore_transaction)
        ledger = self.engine.ledger(self.actor, self.org)
        self.assertEqual(
            tuple(row for row in ledger if row["entry_id"] == original), original_lines
        )
        self.assertTrue(
            all(
                row["reverses_entry_id"] == original
                for row in ledger
                if row["entry_id"] == reversal
            )
        )
        self.assertTrue(
            all(
                row["reverses_entry_id"] == reversal for row in ledger if row["entry_id"] == restore
            )
        )
        self.assertEqual(
            self.engine.account_balance(self.actor, self.org, self.bank).net_debit, 500
        )
        self.assertTrue(self.engine.trial_balance(self.actor, self.org).balanced)

    def test_missing_account_and_project_are_rejected_without_residue(self):
        before = self.engine.audit_events(self.actor, self.org)
        cases = (
            [LineInput("missing-account", debit=50), LineInput(self.revenue, credit=50)],
            [
                LineInput(self.bank, debit=50, project_id="missing-project"),
                LineInput(self.revenue, credit=50),
            ],
        )
        for lines in cases:
            with self.subTest(lines=lines):
                self.assert_error(
                    "constraint_violation",
                    self.engine.create_transaction,
                    self.actor,
                    self.org,
                    "2026-09-15",
                    "Invalid reference",
                    lines,
                )
        self.assertEqual(self.engine.ledger(self.actor, self.org), ())
        self.assertEqual(self.engine.audit_events(self.actor, self.org), before)

    def test_zero_and_negative_account_balances_are_explicit_and_balanced(self):
        self.post(
            self.transaction(
                "Asset credit balance",
                [LineInput(self.expense, debit=200), LineInput(self.bank, credit=200)],
            )
        )
        bank = self.engine.account_balance(self.actor, self.org, self.bank)
        unused = self.engine.account_balance(self.actor, self.org, self.receivable)
        self.assertEqual((bank.net_debit, bank.debit_balance, bank.credit_balance), (-200, 0, 200))
        self.assertEqual((unused.net_debit, unused.debit_balance, unused.credit_balance), (0, 0, 0))
        report = self.engine.trial_balance(self.actor, self.org)
        self.assertIn(self.receivable, {account.account_id for account in report.accounts})
        self.assertTrue(report.balanced)

    def test_project_view_is_derived_only_from_tagged_ledger_lines(self):
        project = self.engine.create_project(
            self.actor,
            self.org,
            "Ledger-derived project",
            expected_revenue=888_888,
            budget=999_999,
        )
        self.post(
            self.transaction(
                "Tagged sale",
                [
                    LineInput(self.bank, debit=250, project_id=project),
                    LineInput(self.revenue, credit=250, project_id=project),
                ],
            )
        )
        self.post(
            self.transaction(
                "Untagged sale",
                [LineInput(self.bank, debit=400), LineInput(self.revenue, credit=400)],
            )
        )
        ledger = self.engine.ledger(self.actor, self.org, project_id=project)
        report = self.engine.trial_balance(self.actor, self.org, project_id=project)
        self.assertEqual(sum(int(row["debit"]) for row in ledger), 250)
        self.assertEqual(sum(int(row["credit"]) for row in ledger), 250)
        self.assertEqual((report.total_debits, report.total_credits), (250, 250))
        self.assertTrue(report.balanced)
        project_row = next(
            row
            for row in self.engine.catalog(self.actor, self.org)["projects"]
            if row["id"] == project
        )
        self.assertEqual(
            (project_row["expected_revenue"], project_row["budget"]), (888_888, 999_999)
        )

    def test_post_audit_is_complete_correlated_and_uses_system_time(self):
        transaction = self.transaction(
            "Timestamp separation",
            [LineInput(self.bank, debit=100), LineInput(self.revenue, credit=100)],
            entry_date="2026-09-01",
        )
        entry = self.post(transaction)
        events = [
            event
            for event in self.engine.audit_events(self.actor, self.org)
            if event["metadata"]["operation"] == "transaction.post"
        ]
        self.assertEqual(len(events), 4)
        self.assertEqual(
            {event["entity_type"] for event in events}, {"journal_entries", "journal_lines"}
        )
        self.assertEqual(len({event["metadata"]["request_id"] for event in events}), 1)
        for event in events:
            self.assertEqual(event["actor_id"], self.actor)
            timestamp = datetime.fromisoformat(str(event["occurred_at"]))
            self.assertEqual(timestamp.utcoffset(), timedelta(0))
            self.assertIsNotNone(event["new_state"])
        transition = next(
            event for event in events if event["event_type"] == "journal_entries.update"
        )
        self.assertEqual(transition["entity_id"], entry)
        self.assertEqual(transition["previous_state"]["state"], "assembling")
        self.assertEqual(transition["new_state"]["state"], "posted")
        self.assertTrue(
            all(
                row["entry_date"] == "2026-09-01"
                for row in self.engine.ledger(self.actor, self.org)
            )
        )

    def test_concurrent_reversal_posts_allow_exactly_one_winner(self):
        original = self.post(
            self.transaction(
                "Concurrent reversal target",
                [LineInput(self.bank, debit=300), LineInput(self.revenue, credit=300)],
            )
        )
        first = self.confirm(
            self.engine.propose_reversal(
                self.actor, self.org, original, "2026-09-16", "First candidate"
            )
        )
        second = self.confirm(
            self.engine.propose_reversal(
                self.actor, self.org, original, "2026-09-16", "Second candidate"
            )
        )
        barrier = Barrier(2)

        def post_reversal(confirmation_id: str) -> tuple[str, str]:
            engine = AccountingEngine(self.path)
            try:
                barrier.wait(timeout=10)
                try:
                    return "posted", engine.post_transaction(self.actor, self.org, confirmation_id)
                except ChatbookError as exc:
                    return "error", exc.code
            finally:
                engine.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(post_reversal, (first.id, second.id)))
        self.assertEqual([status for status, _ in results].count("posted"), 1)
        self.assertEqual(
            [value for status, value in results if status == "error"], ["already_reversed"]
        )
        ledger = self.engine.ledger(self.actor, self.org)
        reversal_entries = {
            row["entry_id"] for row in ledger if row["reverses_entry_id"] == original
        }
        self.assertEqual(len(reversal_entries), 1)
        self.assertEqual(self.engine.account_balance(self.actor, self.org, self.bank).net_debit, 0)

    def test_concurrent_post_and_period_lock_are_serializable(self):
        transaction = self.transaction(
            "Lock race",
            [LineInput(self.bank, debit=700), LineInput(self.revenue, credit=700)],
        )
        confirmation = self.confirm(transaction)
        barrier = Barrier(2)

        def post() -> tuple[str, str]:
            engine = AccountingEngine(self.path)
            try:
                barrier.wait(timeout=10)
                try:
                    return "post", engine.post_transaction(self.actor, self.org, confirmation.id)
                except ChatbookError as exc:
                    return "post_error", exc.code
            finally:
                engine.close()

        def lock() -> tuple[str, str]:
            engine = AccountingEngine(self.path)
            try:
                barrier.wait(timeout=10)
                engine.lock_period(self.actor, self.org, self.period)
                return "lock", "ok"
            finally:
                engine.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(post), pool.submit(lock)]
            outcomes = [future.result(timeout=20) for future in results]
        self.assertIn(("lock", "ok"), outcomes)
        post_outcome = next(result for result in outcomes if result[0] != "lock")
        self.assertIn(post_outcome[0], {"post", "post_error"})
        if post_outcome[0] == "post_error":
            self.assertEqual(post_outcome[1], "period_locked")
            self.assertEqual(self.engine.ledger(self.actor, self.org), ())
        else:
            self.assertEqual(len(self.engine.ledger(self.actor, self.org)), 2)
            self.assertTrue(self.engine.trial_balance(self.actor, self.org).balanced)
        period = self.engine._db.connection.execute(
            "SELECT locked FROM accounting_periods WHERE id = ?", (self.period,)
        ).fetchone()
        self.assertEqual(period["locked"], 1)

    def test_known_scenario_reconciles_ledger_balances_and_statements(self):
        entries = (
            (
                "Capital",
                [LineInput(self.bank, debit=10_000), LineInput(self.equity, credit=10_000)],
            ),
            (
                "Credit sale",
                [LineInput(self.receivable, debit=4_000), LineInput(self.revenue, credit=4_000)],
            ),
            (
                "Collection",
                [LineInput(self.bank, debit=3_000), LineInput(self.receivable, credit=3_000)],
            ),
            (
                "Cash expense",
                [LineInput(self.expense, debit=1_500), LineInput(self.bank, credit=1_500)],
            ),
            (
                "Credit expense",
                [LineInput(self.expense, debit=500), LineInput(self.payable, credit=500)],
            ),
        )
        for description, lines in entries:
            self.post(self.transaction(description, lines))

        ledger = self.engine.ledger(self.actor, self.org)
        report = self.engine.trial_balance(self.actor, self.org)
        for account in report.accounts:
            lines = [row for row in ledger if row["account_id"] == account.account_id]
            self.assertEqual(account.debits, sum(int(row["debit"]) for row in lines))
            self.assertEqual(account.credits, sum(int(row["credit"]) for row in lines))
        self.assertEqual((report.total_debits, report.total_credits), (14_500, 14_500))
        self.assertTrue(report.balanced)

        income = self.engine.income_statement(self.actor, self.org, "2026-09-01", "2026-09-30")
        self.assertEqual(
            (income["revenue"], income["expenses"], income["net_income"]),
            (4_000, 2_000, 2_000),
        )
        sheet = self.engine.balance_sheet(self.actor, self.org, "2026-09-30")
        self.assertEqual(
            (
                sheet["assets"],
                sheet["liabilities"],
                sheet["recorded_equity"],
                sheet["unclosed_earnings"],
                sheet["total_equity"],
            ),
            (12_500, 500, 10_000, 2_000, 12_000),
        )
        self.assertTrue(sheet["balanced"])

    def test_maximum_line_amount_uses_exact_integer_arithmetic(self):
        self.post(
            self.transaction(
                "Maximum exact amount",
                [
                    LineInput(self.bank, debit=MAX_AMOUNT),
                    LineInput(self.equity, credit=MAX_AMOUNT),
                ],
            )
        )
        report = self.engine.trial_balance(self.actor, self.org)
        self.assertEqual((report.total_debits, report.total_credits), (MAX_AMOUNT, MAX_AMOUNT))
        self.assertTrue(report.balanced)


if __name__ == "__main__":
    unittest.main()
