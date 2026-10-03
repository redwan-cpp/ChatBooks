"""M5.1-C4P7 provider-neutral SaaS server deployment foundation tests."""

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from chatbook.api.main import create_app
from chatbook.domain import ChatbookError
from chatbook.maintenance import MaintenanceController, MaintenanceGate, MaintenancePaths
from chatbook.saas_deployment import (
    SaaSDeploymentConfiguration,
    create_backup_restore_evidence,
    inspect_server_candidate,
    probe_writer_gate,
    provision_schema_v3_candidate,
    validate_deployment_package,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class M51C4P7Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.temporary_root = Path(self.temporary.name).resolve()
        self.project = Path(__file__).resolve().parents[1]
        self.deployment_root = self.temporary_root / "server"
        self.config_path = self.temporary_root / "server-config.json"
        self.configuration_value = self._configuration_value()
        self._write_configuration(self.configuration_value)

    def _configuration_value(self) -> dict[str, object]:
        root = self.deployment_root
        return {
            "version": 1,
            "deployment_id": "disposable-c4p7-test-server",
            "release_id": "a" * 64,
            "runtime": {
                "storage_mode": "organization-v3",
                "schema_version": 3,
                "access_mode": "read-write",
                "backend_host": "127.0.0.1",
                "backend_port": 8000,
                "frontend_host": "127.0.0.1",
                "frontend_port": 3000,
                "authoritative_writer_processes": 1,
                "session_ttl_seconds": 28_800,
            },
            "paths": {
                "root": str(root),
                "v3_database": str(root / "database" / "business-v3.db"),
                "fresh_backup": str(root / "backup" / "business-v3.backup.db"),
                "restore_proof": str(root / "restore-proof" / "business-v3.restore.db"),
                "future_v4_target": str(root / "target" / "business-v4.db"),
                "evidence": str(root / "evidence"),
                "logs": str(root / "logs"),
                "recovery": str(root / "recovery"),
                "secrets": str(root / "secrets"),
                "runtime": str(root / "runtime"),
                "maintenance_control": str(root / "runtime" / "maintenance-control.json"),
                "maintenance_state": str(root / "runtime" / "maintenance-state.json"),
                "operational_events": str(root / "logs" / "operational-events.jsonl"),
                "monitoring_configuration": str(root / "config" / "monitoring.json"),
                "provisioning_credentials": str(root / "secrets" / "credentials.json"),
            },
        }

    def _write_configuration(self, value: object) -> None:
        self.config_path.write_text(json.dumps(value), encoding="utf-8")

    def _configuration(self) -> SaaSDeploymentConfiguration:
        return SaaSDeploymentConfiguration.from_file(self.config_path)

    def test_configuration_fails_closed_for_missing_path_schema_and_multiple_writers(self) -> None:
        valid = self._configuration()
        self.assertEqual(valid.schema_version, 3)
        self.assertEqual(valid.authoritative_writer_processes, 1)
        self.assertEqual(valid.backend_environment()["CHATBOOK_DB_PATH"], str(valid.database_path))
        self.assertNotIn("CHATBOOK_DB_PATH", valid.frontend_environment())

        missing_path = json.loads(json.dumps(self.configuration_value))
        del missing_path["paths"]["v3_database"]
        self._write_configuration(missing_path)
        with self.assertRaises(ChatbookError) as missing:
            self._configuration()
        self.assertEqual(missing.exception.code, "deployment_database_path")

        unsupported_schema = json.loads(json.dumps(self.configuration_value))
        unsupported_schema["runtime"]["schema_version"] = 5
        self._write_configuration(unsupported_schema)
        with self.assertRaises(ChatbookError) as schema:
            self._configuration()
        self.assertEqual(schema.exception.code, "runtime_schema_mismatch")

        multiple_writers = json.loads(json.dumps(self.configuration_value))
        multiple_writers["runtime"]["authoritative_writer_processes"] = 2
        self._write_configuration(multiple_writers)
        with self.assertRaises(ChatbookError) as writers:
            self._configuration()
        self.assertEqual(writers.exception.code, "deployment_single_writer")

        raw_book = json.loads(json.dumps(self.configuration_value))
        raw_book["ledger_book_id"] = "client-selected"
        self._write_configuration(raw_book)
        with self.assertRaises(ChatbookError) as book:
            self._configuration()
        self.assertEqual(book.exception.code, "deployment_forbidden_configuration")

    def test_package_contract_is_provider_neutral_private_and_single_writer(self) -> None:
        result = validate_deployment_package(self.project)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["authoritative_financial_writer_processes"], 1)
        self.assertFalse(result["backend_publicly_routable"])
        self.assertFalse(result["database_publicly_served"])

        package = self.project / "deploy" / "saas"
        files = [path for path in package.rglob("*") if path.is_file()]
        serialized = "\n".join(path.read_text(encoding="utf-8") for path in files).casefold()
        self.assertNotIn("ledger_book_id", serialized)
        self.assertNotIn("chatbook_book_id", serialized)
        self.assertNotIn("bearer ", serialized)
        self.assertNotIn("canonical_rehearsal", serialized)
        self.assertIn("requires_operator_decision", serialized)

    def test_provisioning_uses_business_boundaries_and_records_sanitized_evidence(self) -> None:
        configuration = self._configuration()
        development_database = self.project / "chatbook.db"
        development_hash = _hash(development_database)
        evidence = provision_schema_v3_candidate(configuration)

        self.assertEqual(evidence["status"], "PROVISIONED_NOT_APPROVED")
        self.assertEqual(evidence["schema_version"], 3)
        self.assertEqual(evidence["owner_scope"], "BUSINESS")
        self.assertFalse(evidence["personal_data_created"])
        self.assertFalse(evidence["v4_target_created"])
        self.assertFalse(evidence["c4_executed"])
        self.assertTrue(configuration.paths.v3_database.is_file())
        self.assertFalse(configuration.paths.future_v4_target.exists())
        self.assertEqual(_hash(development_database), development_hash)

        connection = sqlite3.connect(configuration.paths.v3_database)
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
            self.assertEqual(
                {
                    tuple(row)
                    for row in connection.execute(
                        "SELECT currency, minor_unit_digits FROM organizations"
                    )
                },
                {("BDT", 2), ("USD", 3)},
            )
            self.assertGreater(
                connection.execute("SELECT count(*) FROM journal_entries").fetchone()[0], 0
            )
            self.assertGreater(
                connection.execute("SELECT count(*) FROM audit_events").fetchone()[0], 0
            )
            self.assertGreater(
                connection.execute("SELECT count(*) FROM command_idempotency").fetchone()[0], 0
            )
            self.assertFalse(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name LIKE 'personal%'"
                ).fetchone()
            )
        finally:
            connection.close()

        credentials = json.loads(
            configuration.paths.provisioning_credentials.read_text(encoding="utf-8")
        )
        serialized_evidence = json.dumps(evidence, sort_keys=True)
        for credential in credentials.values():
            self.assertNotIn(credential["password"], serialized_evidence)
        self.assertNotIn("ledger_book_id", serialized_evidence)

        inspected = inspect_server_candidate(configuration)
        self.assertEqual(inspected["status"], "VERIFIED_NOT_APPROVED")
        self.assertEqual(inspected["database_sha256"], evidence["database_sha256"])
        with self.assertRaises(ChatbookError) as overwrite:
            provision_schema_v3_candidate(configuration)
        self.assertEqual(overwrite.exception.code, "deployment_artifact_exists")

    def test_startup_health_maintenance_shutdown_writer_gate_and_backup_restore(self) -> None:
        configuration = self._configuration()
        provision_schema_v3_candidate(configuration)
        credentials = json.loads(
            configuration.paths.provisioning_credentials.read_text(encoding="utf-8")
        )
        paths = MaintenancePaths.explicit(
            configuration.paths.maintenance_control, configuration.paths.maintenance_state
        )
        controller = MaintenanceController(paths)
        app = create_app(
            runtime_configuration=configuration.runtime_configuration,
            maintenance_gate=MaintenanceGate(paths),
            session_ttl_seconds=configuration.session_ttl_seconds,
        )
        with TestClient(app) as client:
            health = client.get("/api/v1/health")
            self.assertEqual(health.status_code, 200)
            login = client.post(
                "/api/v1/auth/token",
                json={
                    "username": credentials["bdt_owner"]["username"],
                    "password": credentials["bdt_owner"]["password"],
                },
            )
            self.assertEqual(login.status_code, 200, login.text)
            controller.enter_drain("c4p7-test-drain")
            self.assertEqual(controller.wait_for_drain(2)["in_flight"], 0)
            controller.seal("c4p7-test-maintenance")
            self.assertEqual(client.get("/api/v1/health").status_code, 503)
            controller.request_shutdown("c4p7-test-shutdown")

        self.assertEqual(controller.status()["runtime"]["backend_state"], "stopped")
        source_hash = _hash(configuration.paths.v3_database)
        self.assertTrue(probe_writer_gate(configuration.paths.v3_database)["writer_gate_acquired"])
        backup = create_backup_restore_evidence(configuration)
        self.assertEqual(backup["status"], "BACKUP_RESTORE_VERIFIED_NOT_APPROVED")
        self.assertTrue(configuration.paths.fresh_backup.is_file())
        self.assertTrue(configuration.paths.restore_proof.is_file())
        self.assertFalse(configuration.paths.future_v4_target.exists())
        self.assertEqual(_hash(configuration.paths.v3_database), source_hash)


if __name__ == "__main__":
    unittest.main()
