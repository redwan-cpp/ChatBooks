"""Provider-neutral server deployment controls for the C4P7 foundation.

The module prepares and inspects a future BUSINESS schema-v3 source through the
existing authentication and accounting services. It never migrates a database,
selects schema v4 implicitly, or creates PERSONAL ownership.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from secrets import token_urlsafe
from typing import cast

from .api.main import OPERATIONAL_EVENT_LOG_ENV
from .auth import AuthService
from .domain import AccountType, ChatbookError, LineInput, OrganizationRole, ProjectStatus
from .engine import AccountingEngine
from .maintenance import (
    CONTROL_PATH_ENV,
    STATE_PATH_ENV,
    MaintenanceMode,
    MaintenancePaths,
    initialize_maintenance_control,
    read_maintenance_control,
)
from .migration_evidence import (
    build_preflight_manifest,
    create_verified_backup,
    restore_verified_backup,
)
from .operational_monitoring import BASELINE_REQUIRED, REQUIRES_OPERATOR_DECISION
from .runtime import (
    ACCESS_MODE_ENV,
    DATABASE_PATH_ENV,
    DEVELOPMENT_DATABASE_PATH,
    RELEASE_ID_ENV,
    SCHEMA_VERSION_ENV,
    STORAGE_MODE_ENV,
    RuntimeAccessMode,
    RuntimeConfiguration,
    RuntimeStorageMode,
    inspect_runtime_database,
)

FOUNDATION_VERSION = "m5.1-c4p7-v1"
FOUNDATION_CLASSIFICATION = "SERVER_CANDIDATE_NOT_APPROVED"
_RELEASE_PATTERN = re.compile(r"[0-9a-f]{64}")
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})
_FORBIDDEN_CONFIG_KEYS = frozenset(
    {
        "book_id",
        "chatbook_book_id",
        "chatbook_ledger_book_id",
        "financial_space",
        "ledger_book_id",
        "owner_id",
        "owner_kind",
        "personal",
        "personal_enabled",
        "password",
        "token",
        "credential",
    }
)


def _deployment_error(code: str, message: str) -> ChatbookError:
    return ChatbookError(code, message)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _write_sensitive_json_exclusive(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _deployment_error("deployment_configuration", f"{field} must be an object.")
    return cast(dict[str, object], value)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _deployment_error("deployment_configuration", f"{field} must be non-empty text.")
    return value.strip()


def _integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise _deployment_error("deployment_configuration", f"{field} must be an integer.")
    return value


def _reject_forbidden_keys(value: object, *, prefix: str = "configuration") -> None:
    if isinstance(value, dict):
        for raw_key, nested in value.items():
            key = str(raw_key).casefold()
            if key in _FORBIDDEN_CONFIG_KEYS:
                raise _deployment_error(
                    "deployment_forbidden_configuration",
                    f"{prefix}.{raw_key} is not permitted in deployment configuration.",
                )
            _reject_forbidden_keys(nested, prefix=f"{prefix}.{raw_key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_forbidden_keys(nested, prefix=f"{prefix}[{index}]")


def _require_exact_keys(value: Mapping[str, object], expected: frozenset[str], field: str) -> None:
    actual = frozenset(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        raise _deployment_error(
            "deployment_configuration",
            f"{field} has invalid fields: " + "; ".join(details),
        )


@dataclass(frozen=True, slots=True)
class SaaSDeploymentPaths:
    root: Path
    v3_database: Path
    fresh_backup: Path
    restore_proof: Path
    future_v4_target: Path
    evidence: Path
    logs: Path
    recovery: Path
    secrets: Path
    runtime: Path
    maintenance_control: Path
    maintenance_state: Path
    operational_events: Path
    monitoring_configuration: Path
    provisioning_credentials: Path

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> SaaSDeploymentPaths:
        required = frozenset(
            {
                "root",
                "v3_database",
                "fresh_backup",
                "restore_proof",
                "future_v4_target",
                "evidence",
                "logs",
                "recovery",
                "secrets",
                "runtime",
                "maintenance_control",
                "maintenance_state",
                "operational_events",
                "monitoring_configuration",
                "provisioning_credentials",
            }
        )
        missing = sorted(key for key in required if key not in value)
        if missing:
            raise _deployment_error(
                "deployment_database_path",
                "Deployment path configuration is incomplete: " + ", ".join(missing),
            )
        _require_exact_keys(value, required, "paths")
        paths = {key: Path(_text(value[key], f"paths.{key}")) for key in required}
        if any(not path.is_absolute() for path in paths.values()):
            raise _deployment_error(
                "deployment_database_path", "Every server deployment path must be absolute."
            )
        resolved = {key: path.resolve() for key, path in paths.items()}
        root = resolved["root"]
        for key, path in resolved.items():
            if key != "root" and not path.is_relative_to(root):
                raise _deployment_error(
                    "deployment_path_boundary", f"paths.{key} must stay inside paths.root."
                )
        unique_artifacts = (
            resolved["v3_database"],
            resolved["fresh_backup"],
            resolved["restore_proof"],
            resolved["future_v4_target"],
            resolved["maintenance_control"],
            resolved["maintenance_state"],
            resolved["operational_events"],
            resolved["monitoring_configuration"],
            resolved["provisioning_credentials"],
        )
        if len(set(unique_artifacts)) != len(unique_artifacts):
            raise _deployment_error(
                "deployment_path_conflict", "Server deployment artifact paths must be distinct."
            )
        if resolved["v3_database"] == DEVELOPMENT_DATABASE_PATH:
            raise _deployment_error(
                "deployment_development_database",
                "The repository development chatbook.db cannot be a server deployment source.",
            )
        return cls(**resolved)


@dataclass(frozen=True, slots=True)
class SaaSDeploymentConfiguration:
    source_path: Path
    deployment_id: str
    release_id: str
    storage_mode: RuntimeStorageMode
    schema_version: int
    access_mode: RuntimeAccessMode
    backend_host: str
    backend_port: int
    frontend_host: str
    frontend_port: int
    authoritative_writer_processes: int
    session_ttl_seconds: int
    paths: SaaSDeploymentPaths

    @classmethod
    def from_file(cls, path: str | Path) -> SaaSDeploymentConfiguration:
        source_path = Path(path).resolve()
        try:
            raw: object = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise _deployment_error(
                "deployment_configuration", "Server deployment configuration is unavailable."
            ) from exc
        root = _object(raw, "configuration")
        _reject_forbidden_keys(root)
        _require_exact_keys(
            root,
            frozenset({"version", "deployment_id", "release_id", "runtime", "paths"}),
            "configuration",
        )
        if _integer(root.get("version"), "version") != 1:
            raise _deployment_error(
                "deployment_configuration", "Unsupported server deployment configuration version."
            )
        deployment_id = _text(root.get("deployment_id"), "deployment_id")
        release_id = _text(root.get("release_id"), "release_id").casefold()
        if _RELEASE_PATTERN.fullmatch(release_id) is None:
            raise _deployment_error(
                "deployment_release_id", "release_id must be an immutable SHA-256 identity."
            )
        runtime = _object(root.get("runtime"), "runtime")
        _require_exact_keys(
            runtime,
            frozenset(
                {
                    "storage_mode",
                    "schema_version",
                    "access_mode",
                    "backend_host",
                    "backend_port",
                    "frontend_host",
                    "frontend_port",
                    "authoritative_writer_processes",
                    "session_ttl_seconds",
                }
            ),
            "runtime",
        )
        paths = SaaSDeploymentPaths.from_mapping(_object(root.get("paths"), "paths"))
        try:
            storage_mode = RuntimeStorageMode(_text(runtime.get("storage_mode"), "storage_mode"))
            access_mode = RuntimeAccessMode(_text(runtime.get("access_mode"), "access_mode"))
        except ValueError as exc:
            raise _deployment_error(
                "deployment_storage_mode", "The configured storage or access mode is unsupported."
            ) from exc
        schema_version = _integer(runtime.get("schema_version"), "runtime.schema_version")
        backend_host = _text(runtime.get("backend_host"), "runtime.backend_host")
        frontend_host = _text(runtime.get("frontend_host"), "runtime.frontend_host")
        if backend_host not in _LOOPBACK_HOSTS or frontend_host not in _LOOPBACK_HOSTS:
            raise _deployment_error(
                "deployment_network_boundary",
                "Backend and frontend processes must bind to explicit loopback addresses.",
            )
        backend_port = _integer(runtime.get("backend_port"), "runtime.backend_port")
        frontend_port = _integer(runtime.get("frontend_port"), "runtime.frontend_port")
        if not 1 <= backend_port <= 65535 or not 1 <= frontend_port <= 65535:
            raise _deployment_error("deployment_network_boundary", "Runtime ports are invalid.")
        if backend_port == frontend_port:
            raise _deployment_error(
                "deployment_network_boundary", "Backend and frontend ports must differ."
            )
        writer_processes = _integer(
            runtime.get("authoritative_writer_processes"),
            "runtime.authoritative_writer_processes",
        )
        if writer_processes != 1:
            raise _deployment_error(
                "deployment_single_writer",
                "SQLite deployment requires exactly one authoritative backend writer process.",
            )
        session_ttl = _integer(runtime.get("session_ttl_seconds"), "runtime.session_ttl_seconds")
        if session_ttl <= 0:
            raise _deployment_error(
                "deployment_configuration", "Session lifetime must be positive."
            )
        database_path = (
            paths.v3_database
            if storage_mode is RuntimeStorageMode.ORGANIZATION_V3
            else paths.future_v4_target
        )
        RuntimeConfiguration.explicit(
            database_path,
            storage_mode=storage_mode,
            expected_schema_version=schema_version,
            access_mode=access_mode,
            release_id=release_id,
            source="c4p7-server-configuration",
        )
        return cls(
            source_path,
            deployment_id,
            release_id,
            storage_mode,
            schema_version,
            access_mode,
            backend_host,
            backend_port,
            frontend_host,
            frontend_port,
            writer_processes,
            session_ttl,
            paths,
        )

    @property
    def database_path(self) -> Path:
        if self.storage_mode is RuntimeStorageMode.ORGANIZATION_V3:
            return self.paths.v3_database
        return self.paths.future_v4_target

    @property
    def runtime_configuration(self) -> RuntimeConfiguration:
        return RuntimeConfiguration.explicit(
            self.database_path,
            storage_mode=self.storage_mode,
            expected_schema_version=self.schema_version,
            access_mode=self.access_mode,
            release_id=self.release_id,
            source="c4p7-server-configuration",
        )

    def backend_environment(self) -> dict[str, str]:
        return {
            STORAGE_MODE_ENV: self.storage_mode.value,
            SCHEMA_VERSION_ENV: str(self.schema_version),
            DATABASE_PATH_ENV: str(self.database_path),
            ACCESS_MODE_ENV: self.access_mode.value,
            RELEASE_ID_ENV: self.release_id,
            "CHATBOOK_HOST": self.backend_host,
            "CHATBOOK_PORT": str(self.backend_port),
            CONTROL_PATH_ENV: str(self.paths.maintenance_control),
            STATE_PATH_ENV: str(self.paths.maintenance_state),
            OPERATIONAL_EVENT_LOG_ENV: str(self.paths.operational_events),
        }

    def frontend_environment(self) -> dict[str, str]:
        return {
            "NODE_ENV": "production",
            "HOSTNAME": self.frontend_host,
            "PORT": str(self.frontend_port),
            "CHATBOOK_API_URL": f"http://{self.backend_host}:{self.backend_port}/api/v1",
        }


def _post(
    engine: AccountingEngine,
    actor_id: str,
    organization_id: str,
    proposal_id: str,
    *,
    key: str,
) -> str:
    validation = engine.validate_transaction(actor_id, organization_id, proposal_id)
    confirmation = engine.confirm_transaction(
        actor_id,
        organization_id,
        validation.id,
        accepted=True,
        proposal_id=proposal_id,
        proposal_version=1,
        confirmation_request_id=f"confirmation-{key}",
        idempotency_key=f"confirmation-{key}",
        request_fingerprint=hashlib.sha256(f"confirmation:{key}".encode()).hexdigest(),
    )
    fingerprint = hashlib.sha256(f"posting:{key}".encode()).hexdigest()
    entry_id = engine.post_transaction(
        actor_id,
        organization_id,
        confirmation.id,
        idempotency_key=f"posting-{key}",
        request_fingerprint=fingerprint,
    )
    retry = engine.post_transaction(
        actor_id,
        organization_id,
        confirmation.id,
        idempotency_key=f"posting-{key}",
        request_fingerprint=fingerprint,
    )
    if retry != entry_id:
        raise RuntimeError("Idempotent provisioning retry returned a different journal entry.")
    return entry_id


def _populate_business_source(
    configuration: SaaSDeploymentConfiguration,
) -> dict[str, dict[str, str]]:
    database = configuration.paths.v3_database
    credentials: dict[str, dict[str, str]] = {}
    users: dict[str, str] = {}
    user_specs = (
        ("bdt_owner", "Server BDT Owner", "server-bdt-owner@example.test"),
        ("usd_owner", "Server USD Owner", "server-usd-owner@example.test"),
        ("admin", "Server Administrator", "server-admin@example.test"),
        ("accountant", "Server Accountant", "server-accountant@example.test"),
        ("member", "Server Member", "server-member@example.test"),
        ("viewer", "Server Viewer", "server-viewer@example.test"),
    )
    auth = AuthService(database)
    try:
        for key, name, username in user_specs:
            password = token_urlsafe(32)
            registered = auth.register(name, username, password)
            users[key] = registered.id
            credentials[key] = {"username": username, "password": password}
    finally:
        auth.close()

    organizations = (
        ("bdt_owner", "Server BDT Services", "BDT", 2),
        ("usd_owner", "Server USD Studio", "USD", 3),
    )
    engine = AccountingEngine(database)
    try:
        for index, (owner_key, name, currency, precision) in enumerate(organizations):
            actor = users[owner_key]
            organization = engine.create_organization(actor, name, currency, precision)
            for member_key, role in (
                ("admin", OrganizationRole.ADMIN),
                ("accountant", OrganizationRole.ACCOUNTANT),
                ("member", OrganizationRole.MEMBER),
                ("viewer", OrganizationRole.VIEWER),
            ):
                engine.add_member(actor, organization, users[member_key], role=role)
            cash = engine.create_account(
                actor, organization, "1000", "Operating Cash", AccountType.ASSET
            )
            revenue = engine.create_account(
                actor, organization, "4000", "Service Revenue", AccountType.REVENUE
            )
            expense = engine.create_account(
                actor, organization, "5000", "Operating Expense", AccountType.EXPENSE
            )
            inactive = engine.create_account(
                actor, organization, "5099", "Inactive Expense", AccountType.EXPENSE
            )
            engine.set_account_active(actor, organization, inactive, False)
            historical_period = engine.create_period(
                actor, organization, "Historical 2025", "2025-01-01", "2025-12-31"
            )
            engine.create_period(actor, organization, "Open 2026", "2026-01-01", "2026-12-31")
            project = engine.create_project(
                actor,
                organization,
                f"Server Candidate Project {index + 1}",
                description="Future C4 server candidate project",
                client=f"Server Candidate Client {index + 1}",
                expected_revenue=1_500_000 + index,
                budget=800_000 + index,
                starts_on="2025-01-01",
                ends_on="2026-12-31",
                status=ProjectStatus.ACTIVE,
            )
            document = engine.register_document(
                actor,
                organization,
                f"server-candidate-{index + 1}.pdf",
                "application/pdf",
                hashlib.sha256(f"server-candidate-document-{index}".encode()).hexdigest(),
                f"server-candidate://documents/{index + 1}",
            )
            historical = engine.create_transaction(
                actor,
                organization,
                "2025-06-15",
                "Historical service receipt",
                (
                    LineInput(cash, 250_000 + index, 0, project),
                    LineInput(revenue, 0, 250_000 + index, project),
                ),
                document_id=document,
            )
            _post(
                engine,
                actor,
                organization,
                historical,
                key=f"server-historical-{index}",
            )
            engine.lock_period(actor, organization, historical_period)
            expense_proposal = engine.create_transaction(
                actor,
                organization,
                "2026-02-10",
                "Project operating purchase",
                (
                    LineInput(expense, 40_000 + index, 0, project),
                    LineInput(cash, 0, 40_000 + index, project),
                ),
                document_id=document,
            )
            expense_entry = _post(
                engine,
                actor,
                organization,
                expense_proposal,
                key=f"server-expense-{index}",
            )
            revenue_proposal = engine.create_transaction(
                actor,
                organization,
                "2026-02-20",
                "Current service receipt",
                (
                    LineInput(cash, 90_000 + index, 0, project),
                    LineInput(revenue, 0, 90_000 + index, project),
                ),
            )
            _post(
                engine,
                actor,
                organization,
                revenue_proposal,
                key=f"server-revenue-{index}",
            )
            reversal = engine.propose_reversal(
                actor,
                organization,
                expense_entry,
                "2026-03-01",
                "Correct server candidate purchase",
            )
            _post(
                engine,
                actor,
                organization,
                reversal,
                key=f"server-reversal-{index}",
            )
            engine.create_transaction(
                actor,
                organization,
                "2026-04-01",
                "Pending server candidate proposal",
                (LineInput(expense, 1_001, 0), LineInput(cash, 0, 1_001)),
            )
            validated = engine.create_transaction(
                actor,
                organization,
                "2026-04-02",
                "Validated server candidate proposal",
                (LineInput(expense, 1_002, 0), LineInput(cash, 0, 1_002)),
            )
            engine.validate_transaction(actor, organization, validated)
            confirmed = engine.create_transaction(
                actor,
                organization,
                "2026-04-03",
                "Confirmed server candidate proposal",
                (LineInput(expense, 1_003, 0), LineInput(cash, 0, 1_003)),
            )
            validation = engine.validate_transaction(actor, organization, confirmed)
            engine.confirm_transaction(
                actor,
                organization,
                validation.id,
                accepted=True,
                proposal_id=confirmed,
                proposal_version=1,
                confirmation_request_id=f"server-confirmed-{index}",
            )
            if not engine.trial_balance(actor, organization).balanced:
                raise RuntimeError("Provisioned server candidate trial balance is not balanced.")
            engine.ledger(actor, organization)
            engine.income_statement(actor, organization, "2025-01-01", "2026-12-31")
            engine.balance_sheet(actor, organization, "2026-12-31")
            engine.cash_flow(actor, organization, "2025-01-01", "2026-12-31", (cash,))
            engine.ledger(actor, organization, project_id=project)
    finally:
        engine.close()
    return credentials


def _monitoring_payload(
    configuration: SaaSDeploymentConfiguration, manifest_path: Path
) -> dict[str, object]:
    return {
        "version": 1,
        "phase": "PRE_CUTOVER_V3",
        "database_path": str(configuration.paths.v3_database),
        "expected_schema_version": 3,
        "expected_manifest_path": str(manifest_path),
        "application_log_path": str(configuration.paths.operational_events),
        "migration_report_path": None,
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


def provision_schema_v3_candidate(
    configuration: SaaSDeploymentConfiguration,
) -> dict[str, object]:
    """Provision one new BUSINESS schema-v3 candidate through existing service boundaries."""
    if configuration.storage_mode is not RuntimeStorageMode.ORGANIZATION_V3:
        raise _deployment_error(
            "deployment_provisioning_mode", "Provisioning requires organization-v3 selection."
        )
    if (
        configuration.schema_version != 3
        or configuration.access_mode is not RuntimeAccessMode.READ_WRITE
    ):
        raise _deployment_error(
            "deployment_provisioning_mode", "Provisioning requires schema 3 read-write selection."
        )
    paths = configuration.paths
    for forbidden in (
        paths.v3_database,
        paths.fresh_backup,
        paths.restore_proof,
        paths.future_v4_target,
        paths.provisioning_credentials,
    ):
        if forbidden.exists():
            raise _deployment_error(
                "deployment_artifact_exists",
                "Provisioning refuses to overwrite an existing database, backup, target, "
                "or secret.",
            )
    for directory in (
        paths.v3_database.parent,
        paths.fresh_backup.parent,
        paths.restore_proof.parent,
        paths.future_v4_target.parent,
        paths.evidence,
        paths.logs,
        paths.recovery,
        paths.secrets,
        paths.runtime,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    credentials = _populate_business_source(configuration)
    _write_sensitive_json_exclusive(paths.provisioning_credentials, credentials)
    initialize_maintenance_control(
        MaintenancePaths.explicit(paths.maintenance_control, paths.maintenance_state)
    )
    manifest = build_preflight_manifest(paths.v3_database)
    manifest_path = paths.evidence / "schema-v3-preflight-manifest.json"
    _write_json(manifest_path, manifest)
    _write_json(paths.monitoring_configuration, _monitoring_payload(configuration, manifest_path))
    _write_json(paths.runtime / "backend-environment.json", configuration.backend_environment())
    _write_json(paths.runtime / "frontend-environment.json", configuration.frontend_environment())
    runtime_evidence = inspect_runtime_database(configuration.runtime_configuration)
    metrics = cast(dict[str, object], manifest["metrics"])
    evidence: dict[str, object] = {
        "version": FOUNDATION_VERSION,
        "status": "PROVISIONED_NOT_APPROVED",
        "classification": FOUNDATION_CLASSIFICATION,
        "deployment_id": configuration.deployment_id,
        "source_path": str(paths.v3_database),
        "schema_version": manifest["schema_version"],
        "database_sha256": manifest["database_sha256"],
        "schema_sha256": manifest["schema_sha256"],
        "content_fingerprint": manifest["content_fingerprint"],
        "legacy_content_fingerprint": manifest["legacy_content_fingerprint"],
        "row_counts": {
            "organizations": metrics["organization_count"],
            "transactions": metrics["proposal_count"],
            "validations": metrics["validation_count"],
            "confirmations": metrics["confirmation_count"],
            "idempotency_receipts": metrics["idempotency_receipt_count"],
            "journal_entries": metrics["journal_entry_count"],
            "journal_lines": metrics["journal_line_count"],
            "projects": metrics["project_count"],
            "documents": metrics["document_count"],
            "audit_events": metrics["audit_count"],
        },
        "release_id": configuration.release_id,
        "runtime_configuration_fingerprint": runtime_evidence["configuration_fingerprint"],
        "owner_scope": "BUSINESS",
        "authoritative_writer_processes": configuration.authoritative_writer_processes,
        "provisioned_through_existing_services": True,
        "credentials_emitted": False,
        "raw_book_ids_emitted": False,
        "personal_data_created": False,
        "v4_target_created": False,
        "c4_executed": False,
        "approval": "REQUIRES_OPERATOR_DECISION",
    }
    _write_json(paths.evidence / "schema-v3-provisioning-evidence.json", evidence)
    return evidence


def inspect_server_candidate(
    configuration: SaaSDeploymentConfiguration,
) -> dict[str, object]:
    runtime = inspect_runtime_database(configuration.runtime_configuration)
    manifest = build_preflight_manifest(configuration.database_path)
    if (
        configuration.storage_mode is RuntimeStorageMode.ORGANIZATION_V3
        and configuration.paths.future_v4_target.exists()
    ):
        raise _deployment_error(
            "deployment_unexpected_v4_target",
            "The schema-v3 foundation must not contain a schema-v4 target.",
        )
    return {
        "version": FOUNDATION_VERSION,
        "status": "VERIFIED_NOT_APPROVED",
        "classification": FOUNDATION_CLASSIFICATION,
        "deployment_id": configuration.deployment_id,
        "source_path": str(configuration.database_path),
        "database_sha256": manifest["database_sha256"],
        "schema_sha256": manifest["schema_sha256"],
        "content_fingerprint": manifest["content_fingerprint"],
        "legacy_content_fingerprint": manifest["legacy_content_fingerprint"],
        "schema_version": runtime["actual_schema_version"],
        "release_id": configuration.release_id,
        "runtime_configuration_fingerprint": runtime["configuration_fingerprint"],
        "owner_scope": runtime["owner_scope"],
        "integrity_check": runtime["integrity_check"],
        "foreign_key_violation_count": runtime["foreign_key_violation_count"],
        "authoritative_writer_processes": configuration.authoritative_writer_processes,
        "credentials_emitted": False,
        "raw_book_ids_emitted": False,
        "personal_data_created": False,
        "c4_executed": False,
        "approval": "REQUIRES_OPERATOR_DECISION",
    }


def probe_writer_gate(database_path: Path) -> dict[str, object]:
    """Prove a held SQLite writer gate blocks one controlled competing writer."""
    guard = sqlite3.connect(str(database_path), isolation_level=None, timeout=1)
    contender = sqlite3.connect(str(database_path), isolation_level=None, timeout=0)
    contender.execute("PRAGMA busy_timeout = 0")
    try:
        guard.execute("BEGIN IMMEDIATE")
        blocked = False
        try:
            contender.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            blocked = "locked" in str(exc).casefold()
        finally:
            if contender.in_transaction:
                contender.rollback()
        if not blocked:
            raise _deployment_error(
                "deployment_writer_gate", "The controlled competing writer was not blocked."
            )
        return {
            "writer_gate_acquired": True,
            "controlled_competing_writer_blocked": True,
            "data_mutation": False,
        }
    finally:
        if guard.in_transaction:
            guard.rollback()
        contender.close()
        guard.close()


def _require_stopped_maintenance(paths: SaaSDeploymentPaths) -> None:
    maintenance_paths = MaintenancePaths.explicit(
        paths.maintenance_control, paths.maintenance_state
    )
    control = read_maintenance_control(maintenance_paths)
    try:
        state: object = json.loads(paths.maintenance_state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _deployment_error(
            "deployment_maintenance_state", "Maintenance runtime state is unavailable."
        ) from exc
    state_object = _object(state, "maintenance_state")
    if (
        control["mode"] != MaintenanceMode.MAINTENANCE.value
        or control["shutdown_requested"] is not True
        or state_object.get("backend_state") != "stopped"
        or state_object.get("in_flight") != 0
    ):
        raise _deployment_error(
            "deployment_maintenance_required",
            "Backup requires sealed maintenance, stopped backend, and zero in-flight requests.",
        )


def create_backup_restore_evidence(
    configuration: SaaSDeploymentConfiguration,
) -> dict[str, object]:
    """Create a fresh verified backup and separate restore proof while maintenance is sealed."""
    if configuration.storage_mode is not RuntimeStorageMode.ORGANIZATION_V3:
        raise _deployment_error(
            "deployment_backup_mode", "C4 preflight backup preparation requires schema v3."
        )
    paths = configuration.paths
    _require_stopped_maintenance(paths)
    if paths.fresh_backup.exists() or paths.restore_proof.exists():
        raise _deployment_error(
            "deployment_artifact_exists", "Backup and restore proof targets must be new."
        )
    source_hash = _hash_file(paths.v3_database)
    gate = probe_writer_gate(paths.v3_database)
    backup = create_verified_backup(paths.v3_database, paths.fresh_backup)
    restored = restore_verified_backup(
        paths.fresh_backup,
        paths.restore_proof,
        expected_manifest=cast(Mapping[str, object], backup["manifest"]),
    )
    if _hash_file(paths.v3_database) != source_hash:
        raise _deployment_error(
            "deployment_source_changed", "Backup preparation changed the schema-v3 source."
        )
    evidence: dict[str, object] = {
        "version": FOUNDATION_VERSION,
        "status": "BACKUP_RESTORE_VERIFIED_NOT_APPROVED",
        "classification": FOUNDATION_CLASSIFICATION,
        "source_sha256": source_hash,
        "backup_sha256": backup["backup_sha256"],
        "restore_sha256": restored["restore_sha256"],
        "content_fingerprint": restored["content_fingerprint"],
        "writer_gate": gate,
        "source_changed": False,
        "c4_executed": False,
        "approval": "REQUIRES_OPERATOR_DECISION",
    }
    _write_json(paths.evidence / "backup-restore-evidence.json", evidence)
    return evidence


def validate_deployment_package(project_root: str | Path) -> dict[str, object]:
    package_root = Path(project_root).resolve() / "deploy" / "saas"
    required = (
        "README.md",
        "config/server.example.json",
        "env/backend.env.example",
        "env/frontend.env.example",
        "contracts/ingress.json",
        "contracts/processes.json",
        "contracts/storage.json",
        "monitoring/operational-monitoring.example.json",
    )
    missing = [name for name in required if not (package_root / name).is_file()]
    if missing:
        raise _deployment_error(
            "deployment_package_missing", "Missing deployment package files: " + ", ".join(missing)
        )
    ingress = json.loads((package_root / "contracts/ingress.json").read_text(encoding="utf-8"))
    processes = json.loads((package_root / "contracts/processes.json").read_text(encoding="utf-8"))
    storage = json.loads((package_root / "contracts/storage.json").read_text(encoding="utf-8"))
    if ingress.get("backend_publicly_routable") is not False:
        raise _deployment_error(
            "deployment_ingress_contract", "The backend must not be publicly routable."
        )
    process_definitions = _object(processes.get("processes"), "processes")
    backend = _object(process_definitions.get("backend"), "processes.backend")
    if backend.get("instances") != 1 or backend.get("authoritative_financial_writer") is not True:
        raise _deployment_error(
            "deployment_single_writer", "The process contract must define exactly one writer."
        )
    if storage.get("database_publicly_served") is not False:
        raise _deployment_error(
            "deployment_storage_contract", "Database files must not be publicly served."
        )
    serialized = json.dumps(
        {"ingress": ingress, "processes": processes, "storage": storage}, sort_keys=True
    ).casefold()
    if "ledger_book_id" in serialized or '"personal"' in serialized:
        raise _deployment_error(
            "deployment_source_boundary", "Deployment contracts expose a forbidden owner selector."
        )
    return {
        "status": "verified",
        "package_root": str(package_root),
        "required_files": len(required),
        "backend_publicly_routable": False,
        "authoritative_financial_writer_processes": 1,
        "database_publicly_served": False,
        "credentials_in_contracts": False,
        "raw_book_ids_in_contracts": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatbook-saas-deployment",
        description="Validate or prepare a provider-neutral Chatbooks server deployment.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate-config", "provision-v3", "inspect", "backup-restore", "environment"):
        command = commands.add_parser(name)
        command.add_argument("--config", required=True, type=Path)
    package = commands.add_parser("package-check")
    package.add_argument("--project-root", default=Path.cwd(), type=Path)
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "package-check":
            result = validate_deployment_package(cast(Path, arguments.project_root))
        else:
            configuration = SaaSDeploymentConfiguration.from_file(cast(Path, arguments.config))
            if arguments.command == "validate-config":
                result = {
                    "status": "valid",
                    "classification": FOUNDATION_CLASSIFICATION,
                    "deployment_id": configuration.deployment_id,
                    "storage_mode": configuration.storage_mode.value,
                    "schema_version": configuration.schema_version,
                    "database_path": str(configuration.database_path),
                    "authoritative_financial_writer_processes": 1,
                    "c4_executed": False,
                }
            elif arguments.command == "provision-v3":
                result = provision_schema_v3_candidate(configuration)
            elif arguments.command == "inspect":
                result = inspect_server_candidate(configuration)
            elif arguments.command == "backup-restore":
                result = create_backup_restore_evidence(configuration)
            else:
                result = {
                    "status": "rendered",
                    "backend": configuration.backend_environment(),
                    "frontend": configuration.frontend_environment(),
                    "credentials_included": False,
                }
    except (ChatbookError, OSError, sqlite3.Error, ValueError) as exc:
        code = exc.code if isinstance(exc, ChatbookError) else type(exc).__name__
        print(json.dumps({"status": "failed", "error": code, "message": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
