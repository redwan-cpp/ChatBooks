"""M5.1-C4P2 normal runtime selection and controlled-environment hardening."""

import contextlib
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from chatbook.api import create_app
from chatbook.auth import AuthService
from chatbook.canonical_database import CanonicalDatabase
from chatbook.canonical_migration import rehearse_canonical_migration
from chatbook.cli import main as cli_main
from chatbook.database import Database
from chatbook.deployment_preparation import (
    DeploymentPaths,
    harden_deployment_environment,
    prepare_deployment_environment,
    verify_deployment_environment,
)
from chatbook.domain import AccountType, ChatbookError, LineInput
from chatbook.engine import AccountingEngine
from chatbook.runtime import (
    FORBIDDEN_RUNTIME_ENVIRONMENT_KEYS,
    RuntimeAccessMode,
    RuntimeConfiguration,
    RuntimeStorageMode,
    inspect_runtime_database,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class M51C4P2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = Path(__file__).resolve().parents[1]

    def _business_fixture(self) -> tuple[Path, dict[str, str], dict[str, object]]:
        source = self.root / "business-v3.db"
        password = "correct horse battery"
        auth = AuthService(source)
        try:
            user = auth.register("Runtime Owner", "runtime@example.test", password)
        finally:
            auth.close()
        engine = AccountingEngine(source)
        try:
            organization = engine.create_organization(user.id, "Runtime Studio", "BDT", 2)
            cash = engine.create_account(user.id, organization, "1000", "Cash", AccountType.ASSET)
            revenue = engine.create_account(
                user.id, organization, "4000", "Revenue", AccountType.REVENUE
            )
            engine.create_period(user.id, organization, "2026", "2026-01-01", "2026-12-31")
            proposal = engine.create_transaction(
                user.id,
                organization,
                "2026-09-28",
                "Runtime parity receipt",
                (LineInput(cash, 2500, 0), LineInput(revenue, 0, 2500)),
            )
            validation = engine.validate_transaction(user.id, organization, proposal)
            confirmation = engine.confirm_transaction(
                user.id,
                organization,
                validation.id,
                accepted=True,
                proposal_id=proposal,
                proposal_version=1,
                confirmation_request_id="runtime-parity-confirm",
                idempotency_key="runtime-parity-confirm",
                request_fingerprint="a" * 64,
            )
            entry = engine.post_transaction(
                user.id,
                organization,
                confirmation.id,
                idempotency_key="runtime-parity-post",
                request_fingerprint="b" * 64,
            )
            before = {
                "organizations": engine.organizations_for_actor(user.id),
                "ledger": engine.ledger(user.id, organization),
                "trial": asdict(engine.trial_balance(user.id, organization)),
                "audit": engine.audit_events(user.id, organization),
            }
        finally:
            engine.close()
        return (
            source,
            {
                "actor": user.id,
                "organization": organization,
                "entry": entry,
                "password": password,
            },
            before,
        )

    def _canonical_fixture(self) -> tuple[Path, Path, dict[str, str], dict[str, object]]:
        source, ids, before = self._business_fixture()
        target = self.root / "business-v4.db"
        backup = self.root / "business-v3.backup.db"
        report = rehearse_canonical_migration(source, target, backup)
        self.assertEqual(report["status"], "complete")
        return source, target, ids, before

    @staticmethod
    def _v4_environment(target: Path) -> dict[str, str]:
        return {
            "CHATBOOK_DB_PATH": str(target.resolve()),
            "CHATBOOK_STORAGE_MODE": RuntimeStorageMode.CANONICAL_V4.value,
            "CHATBOOK_SCHEMA_VERSION": "4",
            "CHATBOOK_RUNTIME_ACCESS": RuntimeAccessMode.READ_WRITE.value,
            "CHATBOOK_RUNTIME_RELEASE_ID": "c" * 64,
        }

    def test_runtime_configuration_is_server_only_explicit_and_fail_closed(self) -> None:
        default = RuntimeConfiguration.from_environment({})
        self.assertEqual(default.storage_mode, RuntimeStorageMode.ORGANIZATION_V3)
        self.assertEqual(default.expected_schema_version, 3)
        self.assertEqual(default.access_mode, RuntimeAccessMode.READ_WRITE)

        invalid_environments = (
            {"CHATBOOK_STORAGE_MODE": "unknown"},
            {"CHATBOOK_STORAGE_MODE": "organization-v3", "CHATBOOK_SCHEMA_VERSION": "4"},
            {"CHATBOOK_STORAGE_MODE": "canonical-v4"},
            {
                "CHATBOOK_STORAGE_MODE": "canonical-v4",
                "CHATBOOK_SCHEMA_VERSION": "4",
                "CHATBOOK_DB_PATH": str(self.root / "missing.db"),
                "CHATBOOK_RUNTIME_RELEASE_ID": "c" * 64,
            },
            {
                "CHATBOOK_STORAGE_MODE": "canonical-v4",
                "CHATBOOK_SCHEMA_VERSION": "4",
                "CHATBOOK_DB_PATH": "relative.db",
                "CHATBOOK_RUNTIME_ACCESS": "read-only",
                "CHATBOOK_RUNTIME_RELEASE_ID": "c" * 64,
            },
            {
                "CHATBOOK_STORAGE_MODE": "canonical-v4",
                "CHATBOOK_SCHEMA_VERSION": "4",
                "CHATBOOK_DB_PATH": str(self.root / "missing.db"),
                "CHATBOOK_RUNTIME_ACCESS": "read-only",
                "CHATBOOK_RUNTIME_RELEASE_ID": "not-a-release-hash",
            },
            {
                "CHATBOOK_STORAGE_MODE": "organization-v3",
                "CHATBOOK_RUNTIME_ACCESS": "read-only",
            },
        )
        for environment in invalid_environments:
            with self.subTest(environment=environment), self.assertRaises(ChatbookError):
                RuntimeConfiguration.from_environment(environment)

        for forbidden in FORBIDDEN_RUNTIME_ENVIRONMENT_KEYS:
            with self.subTest(forbidden=forbidden), self.assertRaises(ChatbookError) as raised:
                RuntimeConfiguration.from_environment({forbidden: "anything"})
            self.assertEqual(raised.exception.code, "runtime_forbidden_configuration")

        with self.assertRaises(ChatbookError) as development:
            RuntimeConfiguration.explicit(
                self.project / "chatbook.db",
                storage_mode=RuntimeStorageMode.CANONICAL_V4,
                expected_schema_version=4,
                access_mode=RuntimeAccessMode.READ_ONLY,
                release_id="c" * 64,
            )
        self.assertEqual(development.exception.code, "runtime_development_database")

    def test_schema_adapter_pairing_never_creates_switches_or_downgrades(self) -> None:
        source, target, _, _ = self._canonical_fixture()
        missing = self.root / "never-created-v4.db"
        missing_configuration = RuntimeConfiguration.explicit(
            missing,
            storage_mode=RuntimeStorageMode.CANONICAL_V4,
            expected_schema_version=4,
            access_mode=RuntimeAccessMode.READ_ONLY,
            release_id="c" * 64,
        )
        with self.assertRaises(ChatbookError):
            AccountingEngine.for_runtime(missing_configuration)
        self.assertFalse(missing.exists())

        with self.assertRaises(ChatbookError):
            AccountingEngine.for_runtime(
                RuntimeConfiguration.explicit(
                    source,
                    storage_mode=RuntimeStorageMode.CANONICAL_V4,
                    expected_schema_version=4,
                    access_mode=RuntimeAccessMode.READ_ONLY,
                    release_id="c" * 64,
                )
            )
        with self.assertRaises(ChatbookError):
            AccountingEngine.for_runtime(RuntimeConfiguration.organization_v3(target))
        with self.assertRaises(ChatbookError):
            Database(target)
        missing_direct = self.root / "canonical-direct-missing.db"
        with self.assertRaises(ChatbookError):
            CanonicalDatabase(missing_direct)
        self.assertFalse(missing_direct.exists())

        read_only = RuntimeConfiguration.explicit(
            target,
            storage_mode=RuntimeStorageMode.CANONICAL_V4,
            expected_schema_version=4,
            access_mode=RuntimeAccessMode.READ_ONLY,
            release_id="c" * 64,
        )
        read_only_engine = AccountingEngine.for_runtime(read_only)
        try:
            with self.assertRaises(ChatbookError) as blocked:
                read_only_engine.create_user("Blocked write")
            self.assertEqual(blocked.exception.code, "runtime_read_only")
        finally:
            read_only_engine.close()

    def test_normal_v4_engine_api_auth_and_cli_preserve_business_behavior(self) -> None:
        source, target, ids, before = self._canonical_fixture()
        source_hash = _hash(source)
        environment = self._v4_environment(target)
        configuration = RuntimeConfiguration.from_environment(environment)

        engine = AccountingEngine.for_runtime(configuration)
        try:
            self.assertEqual(engine.organizations_for_actor(ids["actor"]), before["organizations"])
            self.assertEqual(engine.ledger(ids["actor"], ids["organization"]), before["ledger"])
            self.assertEqual(
                asdict(engine.trial_balance(ids["actor"], ids["organization"])), before["trial"]
            )
            self.assertEqual(
                engine.audit_events(ids["actor"], ids["organization"]), before["audit"]
            )
        finally:
            engine.close()

        app = create_app(runtime_configuration=configuration)
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/token",
                json={"username": "runtime@example.test", "password": ids["password"]},
            )
            self.assertEqual(login.status_code, 200, login.text)
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            organizations = client.get("/api/v1/organizations", headers=headers)
            self.assertEqual(organizations.status_code, 200, organizations.text)
            self.assertEqual(organizations.json()[0]["id"], ids["organization"])
            trial = client.get(
                f"/api/v1/organizations/{ids['organization']}/reports/trial-balance",
                headers=headers,
            )
            self.assertEqual(trial.status_code, 200, trial.text)
            self.assertTrue(trial.json()["balanced"])
            self.assertNotIn("ledger_book_id", json.dumps(app.openapi()))

        output = io.StringIO()
        with patch.dict(os.environ, environment, clear=True), contextlib.redirect_stdout(output):
            result = cli_main(
                [
                    "--actor",
                    ids["actor"],
                    "--org",
                    ids["organization"],
                    "trial-balance",
                ]
            )
        self.assertEqual(result, 0)
        self.assertTrue(json.loads(output.getvalue())["balanced"])
        self.assertEqual(_hash(source), source_hash)

    def test_runtime_evidence_is_sanitized_and_contains_no_book_authority(self) -> None:
        _, target, _, _ = self._canonical_fixture()
        configuration = RuntimeConfiguration.from_environment(self._v4_environment(target))
        evidence = inspect_runtime_database(configuration)
        self.assertEqual(evidence["storage_mode"], "canonical-v4")
        self.assertEqual(evidence["actual_schema_version"], 4)
        self.assertEqual(evidence["access_mode"], "read-write")
        self.assertEqual(evidence["owner_scope"], "BUSINESS")
        serialized = json.dumps(evidence, sort_keys=True)
        self.assertNotIn("ledger_book_id", serialized)
        self.assertNotIn("password", serialized.casefold())
        self.assertNotIn("token", serialized.casefold())
        self.assertNotIn("Runtime parity receipt", serialized)

    def test_c4p_controls_are_fixed_sanitized_and_preserve_the_source(self) -> None:
        development_database = self.project / "chatbook.db"
        development_hash = _hash(development_database)
        deployment_root = self.root / "controlled-c4"
        prepared = prepare_deployment_environment(deployment_root, project_root=self.project)
        paths = DeploymentPaths.for_root(deployment_root)
        source_hash = _hash(paths.source)
        connection = sqlite3.connect(paths.source)
        try:
            counts = {
                table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("organizations", "transactions", "journal_entries", "audit_events")
            }
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertFalse(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name LIKE 'personal%'"
                ).fetchone()
            )
        finally:
            connection.close()

        hardened = harden_deployment_environment(deployment_root, project_root=self.project)
        self.assertEqual(hardened["status"], "hardened")
        self.assertEqual(hardened["schema_version"], 3)
        self.assertFalse(hardened["v4_target_exists"])
        self.assertEqual(_hash(paths.source), source_hash)
        self.assertEqual(_hash(development_database), development_hash)
        self.assertFalse(paths.v4_target.exists())

        verified = verify_deployment_environment(deployment_root, record_evidence=True)
        self.assertEqual(verified["source_sha256"], source_hash)
        self.assertTrue(verified["writer_control_state"]["quiescent"])
        self.assertEqual(verified["runtime"]["storage_mode"], "organization-v3")
        self.assertFalse(verified["personal_data_created"])
        runtime_evidence = json.loads(
            (paths.evidence / "runtime-verification-evidence.json").read_text(encoding="utf-8")
        )
        self.assertFalse(runtime_evidence["deployment_configuration"]["sensitive_values_included"])

        selection = json.loads(
            (paths.config / "runtime-selection.json").read_text(encoding="utf-8")
        )
        self.assertEqual(selection["database_path"], str(paths.source))
        self.assertEqual(selection["storage_mode"], "organization-v3")
        self.assertEqual(selection["expected_schema_version"], 3)
        self.assertEqual(selection["access_mode"], "read-write")
        backend = (paths.root / "controls" / "Start-Backend.ps1").read_text(encoding="utf-8")
        self.assertIn(str(paths.source), backend)
        self.assertIn(str(paths.v4_target), backend)
        self.assertIn("from chatbook.runtime import main", backend)
        self.assertIn("canonical-v4 only for post-migration read-only acceptance", backend)
        self.assertNotIn("canonical_rehearsal", backend)
        self.assertNotIn("canonical_migration", backend)
        self.assertNotIn(str(development_database), backend)

        connection = sqlite3.connect(paths.source)
        try:
            self.assertEqual(
                {
                    table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    for table in counts
                },
                counts,
            )
        finally:
            connection.close()
        serialized = json.dumps(prepared, sort_keys=True)
        secrets = json.loads(
            (paths.secrets / "staging-credentials.json").read_text(encoding="utf-8")
        )
        for item in secrets.values():
            self.assertNotIn(item["password"], serialized)


if __name__ == "__main__":
    unittest.main()
