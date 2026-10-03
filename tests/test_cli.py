import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.db = self.path / "cli.db"
        self.actor = self.call("user-create", "--name", "Manual owner")["user_id"]
        self.org = self.call(
            "org-create", "--name", "Studio", "--currency", "BDT", "--minor-unit-digits", "2"
        )["organization_id"]
        self.bank = self.call(
            "account-create", "--code", "1000", "--name", "Bank", "--type", "asset"
        )["account_id"]
        self.revenue = self.call(
            "account-create", "--code", "4000", "--name", "Sales", "--type", "revenue"
        )["account_id"]
        self.call(
            "period-create", "--name", "September", "--start", "2026-09-01", "--end", "2026-09-30"
        )

    def command(self, *args, input_text="", expected=0):
        command = [sys.executable, "-m", "chatbook", "--db", str(self.db)]
        if hasattr(self, "actor"):
            command += ["--actor", self.actor]
        if hasattr(self, "org"):
            command += ["--org", self.org]
        result = subprocess.run(
            [*command, *args],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def call(self, *args, **kwargs):
        return json.loads(self.command(*args, **kwargs).stdout)

    def proposal(self, **changes):
        payload = {
            "entry_date": "2026-09-25",
            "description": "Manual receipt",
            "lines": [
                {"account_id": self.bank, "debit": 5000},
                {"account_id": self.revenue, "credit": 5000},
            ],
        }
        payload.update(changes)
        path = self.path / "proposal.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_complete_cli_workflow_and_interactive_confirmation(self):
        transaction = self.call("create", "--file", str(self.proposal()))["transaction_id"]
        show = self.call("show", "--transaction", transaction)
        self.assertEqual(show["currency"], "BDT")
        self.assertEqual(show["minor_unit_digits"], 2)
        validation = self.call("validate", "--transaction", transaction)["id"]
        self.command("confirm", "--validation", validation, input_text="no\n", expected=2)
        confirmation = self.call(
            "confirm", "--validation", validation, input_text=f"CONFIRM {transaction}\n"
        )["id"]
        entry = self.call("post", "--confirmation", confirmation)["entry_id"]
        self.assertEqual(len(self.call("ledger")), 2)
        self.assertEqual(self.call("balance", "--account", self.bank)["net_debit"], 5000)
        self.assertEqual(self.call("trial-balance")["total_debits"], 5000)
        self.assertEqual(
            self.call("income-statement", "--start", "2026-09-01", "--end", "2026-09-30")[
                "net_income"
            ],
            5000,
        )
        self.assertTrue(self.call("balance-sheet", "--as-of", "2026-09-30")["balanced"])
        reversal = self.call(
            "reverse", "--entry", entry, "--date", "2026-09-26", "--reason", "Correction"
        )["transaction_id"]
        validation = self.call("validate", "--transaction", reversal)["id"]
        confirmation = self.call("confirm", "--validation", validation, "--accept")["id"]
        self.call("post", "--confirmation", confirmation)
        self.assertEqual(len(self.call("ledger")), 4)
        self.assertEqual(self.call("trial-balance")["total_debits"], 0)
        events = self.call("audit")
        self.assertEqual(
            sum(event["event_type"] == "journal_entries.update" for event in events), 2
        )

    def test_malformed_input_is_clear_error_with_no_traceback(self):
        path = self.proposal(unexpected="not silently accepted")
        result = self.command("create", "--file", str(path), expected=2)
        self.assertEqual(json.loads(result.stderr)["error"], "invalid_input")
        path.write_text("{", encoding="utf-8")
        result = self.command("create", "--file", str(path), expected=2)
        self.assertEqual(json.loads(result.stderr)["error"], "input_or_storage_error")

    def test_float_amounts_are_rejected(self):
        path = self.proposal(
            lines=[
                {"account_id": self.bank, "debit": 0.1},
                {"account_id": self.revenue, "credit": 0.1},
            ]
        )
        result = self.command("create", "--file", str(path), expected=2)
        self.assertEqual(json.loads(result.stderr)["error"], "invalid_amount")


if __name__ == "__main__":
    unittest.main()
