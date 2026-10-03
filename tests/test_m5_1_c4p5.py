"""M5.1-C4P5 traffic-drain and monitoring preparation tests."""

import asyncio
import hashlib
import json
import shutil
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from chatbook.api.main import create_app
from chatbook.auth import AuthService
from chatbook.canonical_migration import rehearse_canonical_migration
from chatbook.deployment_preparation import DeploymentPaths, prepare_deployment_environment
from chatbook.domain import AccountType, LineInput
from chatbook.engine import AccountingEngine
from chatbook.maintenance import (
    MaintenanceController,
    MaintenanceGate,
    MaintenancePaths,
    initialize_maintenance_control,
)
from chatbook.migration_evidence import build_preflight_manifest
from chatbook.operational_monitoring import (
    BASELINE_REQUIRED,
    REQUIRES_OPERATOR_DECISION,
    MonitoringConfiguration,
    collect_monitoring,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class M51C4P5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "business-v3.db"
        self.project = Path(__file__).resolve().parents[1]
        self._create_business_fixture()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _create_business_fixture(self) -> None:
        auth = AuthService(self.database)
        try:
            user = auth.register("Drain Owner", "drain@example.test", "correct horse battery")
        finally:
            auth.close()
        engine = AccountingEngine(self.database)
        try:
            organization = engine.create_organization(user.id, "Drain Studio", "BDT", 2)
            cash = engine.create_account(user.id, organization, "1000", "Cash", AccountType.ASSET)
            revenue = engine.create_account(
                user.id, organization, "4000", "Revenue", AccountType.REVENUE
            )
            engine.create_period(user.id, organization, "September", "2026-09-01", "2026-09-30")
            proposal = engine.create_transaction(
                user.id,
                organization,
                "2026-09-29",
                "Fixture receipt that must never appear in monitor evidence",
                (LineInput(cash, 5000, 0), LineInput(revenue, 0, 5000)),
            )
            validation = engine.validate_transaction(user.id, organization, proposal)
            confirmation = engine.confirm_transaction(
                user.id,
                organization,
                validation.id,
                accepted=True,
                proposal_id=proposal,
                proposal_version=1,
                confirmation_request_id="fixture-confirmation",
                idempotency_key="fixture-confirmation",
                request_fingerprint="a" * 64,
            )
            engine.post_transaction(
                user.id,
                organization,
                confirmation.id,
                idempotency_key="fixture-posting",
                request_fingerprint="b" * 64,
            )
        finally:
            engine.close()

    def _maintenance(self) -> tuple[MaintenancePaths, MaintenanceController]:
        paths = MaintenancePaths.explicit(
            self.root / "maintenance-control.json", self.root / "maintenance-state.json"
        )
        initialize_maintenance_control(paths)
        return paths, MaintenanceController(paths)

    def _monitoring_configuration(
        self,
        database: Path,
        *,
        phase: str = "PRE_CUTOVER_V3",
        expected_schema_version: int = 3,
        baseline_database: Path | None = None,
        migration_report_path: Path | None = None,
    ) -> MonitoringConfiguration:
        manifest_path = self.root / f"{database.stem}-manifest.json"
        if expected_schema_version == 3:
            manifest = build_preflight_manifest(baseline_database or database)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            expected_manifest: str | None = str(manifest_path)
        else:
            expected_manifest = None
        log_path = self.root / "backend.log"
        log_path.write_text(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": "safe-request",
                    "method": "GET",
                    "path": "/api/v1/health",
                    "status": 200,
                    "duration_ms": 1.25,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        config_path = self.root / f"{database.stem}-monitoring.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "phase": phase,
                    "database_path": str(database),
                    "expected_schema_version": expected_schema_version,
                    "expected_manifest_path": expected_manifest,
                    "application_log_path": str(log_path),
                    "migration_report_path": (
                        None if migration_report_path is None else str(migration_report_path)
                    ),
                    "baselines": {
                        "latency": BASELINE_REQUIRED,
                        "migration_duration": BASELINE_REQUIRED,
                        "drain_duration": BASELINE_REQUIRED,
                        "lock_frequency": BASELINE_REQUIRED,
                    },
                    "operator_decisions": {
                        "monitoring_owner": REQUIRES_OPERATOR_DECISION,
                        "escalation_owner": REQUIRES_OPERATOR_DECISION,
                        "observation_period": REQUIRES_OPERATOR_DECISION,
                        "alert_destination": REQUIRES_OPERATOR_DECISION,
                        "stop_or_rollback_authority": REQUIRES_OPERATOR_DECISION,
                    },
                }
            ),
            encoding="utf-8",
        )
        return MonitoringConfiguration.from_file(config_path)

    def test_accepted_request_drains_while_new_requests_fail_closed(self) -> None:
        paths, controller = self._maintenance()
        gate = MaintenanceGate(paths)
        application = create_app(self.database, maintenance_gate=gate)
        started = threading.Event()
        release = threading.Event()

        @application.get("/controlled-slow-request")
        async def controlled_slow_request() -> dict[str, str]:
            started.set()
            await asyncio.to_thread(release.wait)
            return {"status": "finished"}

        response_holder: list[object] = []
        with TestClient(application) as client:
            worker = threading.Thread(
                target=lambda: response_holder.append(client.get("/controlled-slow-request"))
            )
            worker.start()
            self.assertTrue(started.wait(timeout=5))
            controller.enter_drain("test-controlled-drain")

            rejected = client.get("/api/v1/health")
            self.assertEqual(rejected.status_code, 503)
            self.assertEqual(rejected.json()["error"], "maintenance_mode")
            self.assertEqual(controller.status()["runtime"]["in_flight"], 1)

            release.set()
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(response_holder[0].status_code, 200)  # type: ignore[union-attr]
            drained = controller.wait_for_drain(1)
            self.assertEqual(drained["in_flight"], 0)
            controller.seal("test-sealed-maintenance")
            self.assertEqual(client.get("/api/v1/health").status_code, 503)

        status = controller.status()
        self.assertEqual(status["runtime"]["backend_state"], "stopped")
        self.assertEqual(status["runtime"]["in_flight"], 0)

    def test_invalid_control_rejects_requests_and_gate_blocks_database_writes(self) -> None:
        paths, controller = self._maintenance()
        source_hash = _hash(self.database)
        connection = sqlite3.connect(self.database)
        try:
            user_count = int(connection.execute("SELECT count(*) FROM users").fetchone()[0])
        finally:
            connection.close()

        application = create_app(self.database, maintenance_gate=MaintenanceGate(paths))
        with TestClient(application) as client:
            controller.enter_drain("block-new-writes")
            blocked = client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Blocked User",
                    "username": "blocked@example.test",
                    "password": "correct horse battery",
                },
            )
            self.assertEqual(blocked.status_code, 503)
            controller.wait_for_drain(1)
            controller.seal("seal-before-corruption")
            paths.control.write_text("not-json", encoding="utf-8")
            self.assertEqual(client.get("/api/v1/health").status_code, 503)

        connection = sqlite3.connect(self.database)
        try:
            self.assertEqual(
                int(connection.execute("SELECT count(*) FROM users").fetchone()[0]), user_count
            )
        finally:
            connection.close()
        self.assertEqual(_hash(self.database), source_hash)

    def test_monitor_collects_sanitized_read_only_invariants_and_baselines(self) -> None:
        source_hash = _hash(self.database)
        evidence = collect_monitoring(self._monitoring_configuration(self.database))
        self.assertEqual(evidence["status"], "COLLECTED")
        self.assertFalse(evidence["financial_mutation"])
        self.assertFalse(evidence["automatic_repair"])
        self.assertFalse(evidence["automatic_rollback"])
        signals = {item["signal"]: item for item in evidence["signals"]}
        self.assertEqual(len(signals), 12)
        for name in (
            "schema_version",
            "database_integrity",
            "foreign_key_violations",
            "idempotency_disagreement",
            "ledger_reconciliation",
            "report_reconciliation",
        ):
            self.assertEqual(signals[name]["state"], "PASS")
        for name in (
            "sqlite_lock_or_write_failures",
            "financial_command_errors",
            "latency",
        ):
            self.assertEqual(signals[name]["state"], BASELINE_REQUIRED)
        self.assertEqual(signals["protected_artifact_access"]["state"], REQUIRES_OPERATOR_DECISION)
        serialized = json.dumps(evidence, sort_keys=True)
        self.assertNotIn("Fixture receipt", serialized)
        self.assertNotIn("correct horse battery", serialized)
        self.assertNotIn("drain@example.test", serialized)
        self.assertEqual(_hash(self.database), source_hash)

    def test_monitor_fails_closed_on_wrong_phase_and_idempotency_disagreement(self) -> None:
        wrong_phase = collect_monitoring(
            self._monitoring_configuration(
                self.database,
                phase="POST_MIGRATION_READ_ONLY_V4",
                expected_schema_version=4,
            )
        )
        self.assertEqual(wrong_phase["status"], "FAILED_CLOSED")
        self.assertIn("schema_version", wrong_phase["hard_alerts"])

        corrupt = self.root / "corrupt-v3.db"
        shutil.copy2(self.database, corrupt)
        connection = sqlite3.connect(corrupt)
        try:
            connection.execute("DROP TRIGGER command_idempotency_no_update")
            connection.execute(
                "UPDATE command_idempotency SET resource_id = 'missing-resource' "
                "WHERE id = (SELECT id FROM command_idempotency ORDER BY id LIMIT 1)"
            )
            connection.commit()
        finally:
            connection.close()
        corrupted = collect_monitoring(
            self._monitoring_configuration(corrupt, baseline_database=self.database)
        )
        self.assertEqual(corrupted["status"], "FAILED_CLOSED")
        self.assertIn("idempotency_disagreement", corrupted["hard_alerts"])

    def test_monitor_validates_canonical_sidecars_and_migration_artifact_read_only(self) -> None:
        target = self.root / "business-v4.db"
        backup = self.root / "business-v3.backup.db"
        migration = rehearse_canonical_migration(self.database, target, backup)
        self.assertEqual(migration["status"], "complete")
        migration_report = Path(f"{target}.c3-report.json")
        target_hash = _hash(target)

        evidence = collect_monitoring(
            self._monitoring_configuration(
                target,
                phase="POST_MIGRATION_READ_ONLY_V4",
                expected_schema_version=4,
                migration_report_path=migration_report,
            )
        )
        self.assertEqual(evidence["status"], "COLLECTED")
        signals = {item["signal"]: item for item in evidence["signals"]}
        self.assertEqual(signals["audit_sidecar_coverage"]["state"], "PASS")
        self.assertEqual(signals["report_reconciliation"]["state"], "PASS")
        self.assertEqual(signals["migration_failures"]["state"], "PASS")
        self.assertEqual(_hash(target), target_hash)

    def test_deployment_package_contains_only_local_operator_controls(self) -> None:
        deployment_root = self.root / "controlled-c4"
        evidence = prepare_deployment_environment(deployment_root, project_root=self.project)
        paths = DeploymentPaths.for_root(deployment_root)
        self.assertEqual(
            evidence["runtime_topology"]["external_traffic_termination"],
            "NO EXTERNAL TRAFFIC TERMINATION PRESENT",
        )
        self.assertEqual(
            evidence["runtime_topology"]["request_drain"],
            "IMPLEMENTED_LOCAL_SERVER_OWNED_GATE",
        )
        for name in (
            "Enter-Maintenance.ps1",
            "Stop-Application.ps1",
            "Reset-Maintenance.ps1",
            "Verify-Quiescence.ps1",
            "Collect-Monitoring.ps1",
        ):
            self.assertTrue((paths.root / "controls" / name).is_file())
        operations = (paths.root / "controls" / "OPERATIONS.md").read_text(encoding="utf-8")
        self.assertIn("NO EXTERNAL TRAFFIC TERMINATION PRESENT", operations)
        self.assertIn("no HTTP request can change it", operations)
        self.assertFalse(paths.v4_target.exists())


if __name__ == "__main__":
    unittest.main()
