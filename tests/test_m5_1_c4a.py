"""M5.1-C4A synthetic cutover-readiness and recovery evidence."""

import json
import tempfile
import unittest
from pathlib import Path

from chatbook.cutover_readiness import run_synthetic_cutover_rehearsal
from chatbook.database import SCHEMA_VERSION
from chatbook.domain import ChatbookError
from chatbook.engine import AccountingEngine


class M51C4AReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_synthetic_operational_rehearsal_is_complete_sanitized_and_fail_closed(self) -> None:
        output = self.root / "synthetic-c4a"
        evidence = run_synthetic_cutover_rehearsal(
            output,
            posted_transactions_per_organization=4,
            reversal_chain_length=3,
        )

        self.assertEqual(SCHEMA_VERSION, 3)
        self.assertTrue(evidence["fixture"]["synthetic"])
        self.assertFalse(evidence["fixture"]["production_scale_claim"])
        self.assertEqual(evidence["fixture"]["organization_count"], 3)
        self.assertTrue(evidence["source_unchanged"])
        self.assertFalse(evidence["real_or_shared_database_touched"])
        self.assertFalse(evidence["normal_v4_writers_resumed"])
        self.assertTrue(evidence["backup_restore"]["competing_writer_blocked_before_backup"])
        self.assertTrue(evidence["backup_restore"]["competing_writer_blocked_after_backup"])
        self.assertTrue(evidence["backup_restore"]["backup_restore_verified"])
        self.assertEqual(
            evidence["parity"]["exact_equality"],
            {"engine": True, "api": True, "cli": True},
        )
        self.assertTrue(evidence["canary"]["idempotent_retry_same_entry"])
        self.assertTrue(evidence["canary"]["trial_balance_balanced"])
        self.assertTrue(evidence["canary"]["net_account_balances_restored"])
        self.assertGreater(evidence["resources"]["minimum_free_bytes_beyond_existing_source"], 0)
        self.assertEqual(
            set(evidence["recovery_drills"]),
            {
                "preflight_failure",
                "backup_failure",
                "restore_failure",
                "migration_failure",
                "reconciliation_mismatch",
                "trigger_installation_failure",
                "read_only_acceptance_failure",
                "canary_financial_operation_failure",
            },
        )
        self.assertFalse(
            evidence["recovery_drills"]["canary_financial_operation_failure"][
                "old_backup_restore_performed"
            ]
        )
        self.assertFalse(
            evidence["recovery_drills"]["canary_financial_operation_failure"][
                "partial_journal_effect"
            ]
        )

        serialized = (output / "c4a-sanitized-evidence.json").read_text(encoding="utf-8")
        self.assertNotIn("session_token", serialized)
        self.assertNotIn("synthetic rehearsal password", serialized.lower())
        self.assertNotIn("Synthetic transaction", serialized)
        loaded = json.loads(serialized)
        self.assertTrue(loaded["security"]["sensitive_payload_scan_passed"])
        self.assertFalse(loaded["security"]["deployment_backup_access_control_verified"])
        self.assertTrue(loaded["security"]["deployment_access_control_is_c4_approval_gate"])

        with self.assertRaises(ChatbookError):
            AccountingEngine(output / "synthetic-representative-v4.db")
        with self.assertRaises(ChatbookError):
            run_synthetic_cutover_rehearsal(output)

    def test_normal_application_modules_do_not_activate_the_rehearsal_path(self) -> None:
        root = Path(__file__).parents[1]
        for relative in (
            "chatbook/api/main.py",
            "chatbook/cli.py",
            "chatbook/database.py",
            "chatbook/engine.py",
        ):
            source = (root / relative).read_text(encoding="utf-8")
            self.assertNotIn("cutover_readiness", source, relative)
        openapi_source = (root / "chatbook/api/schemas.py").read_text(encoding="utf-8")
        self.assertNotIn("ledger_book_id", openapi_source)


if __name__ == "__main__":
    unittest.main()
