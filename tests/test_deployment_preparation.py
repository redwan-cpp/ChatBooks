"""Controlled deployment-preparation tests."""

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from chatbook.deployment_preparation import (
    DeploymentPaths,
    prepare_deployment_environment,
    verify_deployment_environment,
)
from chatbook.domain import ChatbookError


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DeploymentPreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = Path(__file__).resolve().parents[1]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_preparation_builds_and_verifies_a_separate_schema_v3_environment(self) -> None:
        development_database = self.project / "chatbook.db"
        development_hash = _hash(development_database)
        deployment_root = self.root / "controlled-c4"

        evidence = prepare_deployment_environment(deployment_root, project_root=self.project)
        paths = DeploymentPaths.for_root(deployment_root)

        self.assertEqual(evidence["classification"], "CONTROLLED_DEPLOYMENT_STAGING_NOT_PRODUCTION")
        self.assertFalse(evidence["c4_executed"])
        self.assertFalse(evidence["personal_data_created"])
        self.assertTrue(paths.source.is_file())
        self.assertTrue(paths.backup.is_file())
        self.assertTrue(paths.restore_proof.is_file())
        self.assertFalse(paths.v4_target.exists())
        self.assertEqual(_hash(development_database), development_hash)

        connection = sqlite3.connect(paths.source)
        try:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertFalse(tuple(connection.execute("PRAGMA foreign_key_check")))
            self.assertEqual(
                connection.execute("SELECT count(*) FROM organizations").fetchone()[0], 2
            )
            self.assertEqual(
                {
                    str(row[0])
                    for row in connection.execute("SELECT DISTINCT role FROM memberships")
                },
                {"OWNER", "ADMIN", "ACCOUNTANT", "MEMBER", "VIEWER"},
            )
            proposal_count = connection.execute("SELECT count(*) FROM transactions").fetchone()[0]
            self.assertGreater(proposal_count, 0)
            self.assertGreater(
                connection.execute("SELECT count(*) FROM validations").fetchone()[0], 0
            )
            self.assertGreater(
                connection.execute("SELECT count(*) FROM confirmations").fetchone()[0], 0
            )
            self.assertGreater(
                connection.execute("SELECT count(*) FROM journal_entries").fetchone()[0], 0
            )
            self.assertGreater(
                proposal_count,
                connection.execute("SELECT count(*) FROM journal_entries").fetchone()[0],
            )
            self.assertGreater(
                connection.execute("SELECT count(*) FROM audit_events").fetchone()[0], 0
            )
            self.assertGreater(
                connection.execute("SELECT count(*) FROM command_idempotency").fetchone()[0], 0
            )
        finally:
            connection.close()

        serialized = json.dumps(evidence, sort_keys=True)
        secrets = json.loads(
            (paths.secrets / "staging-credentials.json").read_text(encoding="utf-8")
        )
        for item in secrets.values():
            self.assertNotIn(item["password"], serialized)

        verified = verify_deployment_environment(deployment_root)
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(verified["schema_version"], 3)
        self.assertTrue(verified["source_restore_content_equal"])
        self.assertTrue(verified["writer_gate"]["controlled_competing_writer_blocked"])
        self.assertFalse(verified["v4_target_exists"])

    def test_preparation_refuses_repository_or_existing_roots(self) -> None:
        with self.assertRaises(ChatbookError) as repository:
            prepare_deployment_environment(self.project, project_root=self.project)
        self.assertEqual(repository.exception.code, "deployment_root_invalid")

        existing = self.root / "existing"
        existing.mkdir()
        with self.assertRaises(ChatbookError) as occupied:
            prepare_deployment_environment(existing, project_root=self.project)
        self.assertEqual(occupied.exception.code, "deployment_root_exists")


if __name__ == "__main__":
    unittest.main()
