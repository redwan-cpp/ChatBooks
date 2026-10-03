"""Controlled schema-v3 deployment preparation; never performs the C4 migration."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import socket
import sqlite3
import sys
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, cast

from .api.main import OPERATIONAL_EVENT_LOG_ENV, create_app
from .auth import AuthService
from .cli import _parser as cli_parser
from .cli import _run as run_cli
from .database import SCHEMA_VERSION
from .domain import AccountType, ChatbookError, LineInput, OrganizationRole, ProjectStatus
from .engine import AccountingEngine
from .maintenance import (
    CONTROL_PATH_ENV,
    STATE_PATH_ENV,
    MaintenancePaths,
    initialize_maintenance_control,
)
from .migration_evidence import (
    build_preflight_manifest,
    create_verified_backup,
    restore_verified_backup,
)
from .operational_monitoring import (
    BASELINE_REQUIRED,
    MONITOR_VERSION,
    REQUIRES_OPERATOR_DECISION,
    MonitoringConfiguration,
)
from .runtime import (
    ACCESS_MODE_ENV,
    DATABASE_PATH_ENV,
    RELEASE_ID_ENV,
    SCHEMA_VERSION_ENV,
    STORAGE_MODE_ENV,
    RuntimeAccessMode,
    RuntimeConfiguration,
    RuntimeStorageMode,
    inspect_runtime_database,
)

C4P_TOOL_VERSION = "m5.1-c4p5-v1"
DEPLOYMENT_LABEL = "controlled-c4-business-staging-v1"
REQUIRED_SCHEMA_VERSION = 3


@dataclass(frozen=True, slots=True)
class DeploymentPaths:
    root: Path
    source: Path
    backup: Path
    restore_proof: Path
    v4_target: Path
    evidence: Path
    logs: Path
    config: Path
    runtime: Path
    recovery: Path
    secrets: Path

    @classmethod
    def for_root(cls, root: str | Path) -> "DeploymentPaths":
        resolved = Path(root).resolve()
        return cls(
            root=resolved,
            source=resolved / "source" / "chatbook-business-v3.db",
            backup=resolved / "backup" / "chatbook-business-v3.backup.db",
            restore_proof=resolved / "restore-proof" / "chatbook-business-v3.restore.db",
            v4_target=resolved / "target" / "chatbook-business-v4.db",
            evidence=resolved / "evidence",
            logs=resolved / "logs",
            config=resolved / "config",
            runtime=resolved / "runtime",
            recovery=resolved / "recovery",
            secrets=resolved / "secrets",
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _post(
    engine: AccountingEngine,
    actor_id: str,
    organization_id: str,
    proposal_id: str,
    *,
    key: str,
) -> tuple[str, str]:
    validation = engine.validate_transaction(actor_id, organization_id, proposal_id)
    request_fingerprint = hashlib.sha256(f"confirmation:{key}".encode()).hexdigest()
    confirmation = engine.confirm_transaction(
        actor_id,
        organization_id,
        validation.id,
        accepted=True,
        proposal_id=proposal_id,
        proposal_version=1,
        confirmation_request_id=f"confirmation-{key}",
        idempotency_key=f"confirmation-{key}",
        request_fingerprint=request_fingerprint,
    )
    posting_fingerprint = hashlib.sha256(f"posting:{key}".encode()).hexdigest()
    entry_id = engine.post_transaction(
        actor_id,
        organization_id,
        confirmation.id,
        idempotency_key=f"posting-{key}",
        request_fingerprint=posting_fingerprint,
    )
    retry = engine.post_transaction(
        actor_id,
        organization_id,
        confirmation.id,
        idempotency_key=f"posting-{key}",
        request_fingerprint=posting_fingerprint,
    )
    if retry != entry_id:
        raise RuntimeError("Idempotent staging retry returned a different journal entry.")
    return confirmation.id, entry_id


def _create_staging_source(paths: DeploymentPaths) -> tuple[dict[str, object], dict[str, object]]:
    if paths.source.exists():
        raise ChatbookError("deployment_source_exists", "The deployment source already exists.")
    paths.source.parent.mkdir(parents=True, exist_ok=True)

    user_specs = (
        ("dhaka_owner", "C4P Dhaka Owner", "c4p-dhaka-owner@example.test"),
        ("precision_owner", "C4P Precision Owner", "c4p-precision-owner@example.test"),
        ("admin", "C4P Administrator", "c4p-admin@example.test"),
        ("accountant", "C4P Accountant", "c4p-accountant@example.test"),
        ("member", "C4P Member", "c4p-member@example.test"),
        ("viewer", "C4P Viewer", "c4p-viewer@example.test"),
    )
    users: dict[str, dict[str, str]] = {}
    credentials: dict[str, dict[str, str]] = {}
    auth = AuthService(paths.source)
    try:
        for key, name, username in user_specs:
            password = token_urlsafe(32)
            registered = auth.register(name, username, password)
            users[key] = {"id": registered.id, "name": name, "username": username}
            credentials[key] = {"username": username, "password": password}
    finally:
        auth.close()

    organization_specs = (
        ("dhaka_owner", "C4P Dhaka Services", "BDT", 2),
        ("precision_owner", "C4P Precision Studio", "USD", 3),
    )
    organizations: list[dict[str, object]] = []
    engine = AccountingEngine(paths.source)
    try:
        for org_index, (owner_key, name, currency, precision) in enumerate(organization_specs):
            actor_id = users[owner_key]["id"]
            organization_id = engine.create_organization(actor_id, name, currency, precision)
            for member_key, role in (
                ("admin", OrganizationRole.ADMIN),
                ("accountant", OrganizationRole.ACCOUNTANT),
                ("member", OrganizationRole.MEMBER),
                ("viewer", OrganizationRole.VIEWER),
            ):
                engine.add_member(actor_id, organization_id, users[member_key]["id"], role=role)

            cash = engine.create_account(
                actor_id, organization_id, "1000", "Operating Cash", AccountType.ASSET
            )
            revenue = engine.create_account(
                actor_id, organization_id, "4000", "Service Revenue", AccountType.REVENUE
            )
            expense = engine.create_account(
                actor_id, organization_id, "5000", "Operating Expense", AccountType.EXPENSE
            )
            inactive = engine.create_account(
                actor_id, organization_id, "5099", "Inactive Expense", AccountType.EXPENSE
            )
            engine.set_account_active(actor_id, organization_id, inactive, False)
            locked_period = engine.create_period(
                actor_id, organization_id, "Historical 2025", "2025-01-01", "2025-12-31"
            )
            open_period = engine.create_period(
                actor_id, organization_id, "Open 2026", "2026-01-01", "2026-12-31"
            )
            project = engine.create_project(
                actor_id,
                organization_id,
                f"C4P Project {org_index + 1}",
                description="Controlled deployment staging project",
                client=f"C4P Client {org_index + 1}",
                expected_revenue=1_500_000 + org_index,
                budget=800_000 + org_index,
                starts_on="2025-01-01",
                ends_on="2026-12-31",
                status=ProjectStatus.ACTIVE,
            )
            document = engine.register_document(
                actor_id,
                organization_id,
                f"c4p-source-{org_index + 1}.pdf",
                "application/pdf",
                hashlib.sha256(f"c4p-document-{org_index}".encode()).hexdigest(),
                f"staging://c4p/documents/{org_index + 1}",
            )

            historical = engine.create_transaction(
                actor_id,
                organization_id,
                "2025-06-15",
                "Historical service receipt",
                (
                    LineInput(cash, 250_000 + org_index, 0, project),
                    LineInput(revenue, 0, 250_000 + org_index, project),
                ),
                document_id=document,
            )
            _, historical_entry = _post(
                engine,
                actor_id,
                organization_id,
                historical,
                key=f"c4p-historical-{org_index}",
            )
            engine.lock_period(actor_id, organization_id, locked_period)

            expense_proposal = engine.create_transaction(
                actor_id,
                organization_id,
                "2026-02-10",
                "Project operating purchase",
                (
                    LineInput(expense, 40_000 + org_index, 0, project),
                    LineInput(cash, 0, 40_000 + org_index, project),
                ),
                document_id=document,
            )
            _, expense_entry = _post(
                engine,
                actor_id,
                organization_id,
                expense_proposal,
                key=f"c4p-expense-{org_index}",
            )
            revenue_proposal = engine.create_transaction(
                actor_id,
                organization_id,
                "2026-02-20",
                "Current service receipt",
                (
                    LineInput(cash, 90_000 + org_index, 0, project),
                    LineInput(revenue, 0, 90_000 + org_index, project),
                ),
            )
            _, revenue_entry = _post(
                engine,
                actor_id,
                organization_id,
                revenue_proposal,
                key=f"c4p-revenue-{org_index}",
            )

            reversal = engine.propose_reversal(
                actor_id,
                organization_id,
                expense_entry,
                "2026-03-01",
                "Correct controlled staging purchase",
            )
            _, reversal_entry = _post(
                engine,
                actor_id,
                organization_id,
                reversal,
                key=f"c4p-reversal-{org_index}",
            )

            pending = engine.create_transaction(
                actor_id,
                organization_id,
                "2026-04-01",
                "Pending controlled proposal",
                (LineInput(expense, 1_001, 0), LineInput(cash, 0, 1_001)),
            )
            validated = engine.create_transaction(
                actor_id,
                organization_id,
                "2026-04-02",
                "Validated controlled proposal",
                (LineInput(expense, 1_002, 0), LineInput(cash, 0, 1_002)),
            )
            engine.validate_transaction(actor_id, organization_id, validated)
            confirmed = engine.create_transaction(
                actor_id,
                organization_id,
                "2026-04-03",
                "Confirmed controlled proposal",
                (LineInput(expense, 1_003, 0), LineInput(cash, 0, 1_003)),
            )
            confirmation_validation = engine.validate_transaction(
                actor_id, organization_id, confirmed
            )
            confirmation = engine.confirm_transaction(
                actor_id,
                organization_id,
                confirmation_validation.id,
                accepted=True,
                proposal_id=confirmed,
                proposal_version=1,
                confirmation_request_id=f"c4p-confirmed-{org_index}",
            )

            trial = engine.trial_balance(actor_id, organization_id)
            if not trial.balanced:
                raise RuntimeError("Controlled staging trial balance is not balanced.")
            report_evidence = {
                "ledger": engine.ledger(actor_id, organization_id),
                "trial_balance": asdict(trial),
                "income_statement": engine.income_statement(
                    actor_id, organization_id, "2025-01-01", "2026-12-31"
                ),
                "balance_sheet": engine.balance_sheet(actor_id, organization_id, "2026-12-31"),
                "cash_flow": engine.cash_flow(
                    actor_id, organization_id, "2025-01-01", "2026-12-31", (cash,)
                ),
                "project_ledger": engine.ledger(actor_id, organization_id, project_id=project),
            }
            organizations.append(
                {
                    "organization_id": organization_id,
                    "owner_actor_id": actor_id,
                    "currency": currency,
                    "minor_unit_digits": precision,
                    "accounts": {
                        "cash": cash,
                        "revenue": revenue,
                        "expense": expense,
                        "inactive": inactive,
                    },
                    "periods": {"locked": locked_period, "open": open_period},
                    "project_id": project,
                    "document_id": document,
                    "proposal_states": {
                        "pending": pending,
                        "validated": validated,
                        "confirmed_unposted": confirmed,
                    },
                    "confirmation_id": confirmation.id,
                    "posted_entries": {
                        "historical": historical_entry,
                        "expense": expense_entry,
                        "revenue": revenue_entry,
                        "reversal": reversal_entry,
                    },
                    "report_evidence_sha256": _json_hash(report_evidence),
                }
            )
    finally:
        engine.close()

    paths.secrets.mkdir(parents=True, exist_ok=True)
    credential_path = paths.secrets / "staging-credentials.json"
    _write_json(credential_path, credentials)

    from fastapi.testclient import TestClient

    primary = organizations[0]
    primary_owner = credentials["dhaka_owner"]
    with TestClient(create_app(paths.source)) as client:
        health = client.get("/api/v1/health")
        token_response = client.post(
            "/api/v1/auth/token",
            json={
                "username": primary_owner["username"],
                "password": primary_owner["password"],
            },
        )
        if health.status_code != 200 or token_response.status_code != 200:
            raise RuntimeError("Controlled staging API startup/authentication verification failed.")
        token = str(token_response.json()["access_token"])
        headers = {"Authorization": f"Bearer {token}"}
        organization_id = str(primary["organization_id"])
        organizations_response = client.get("/api/v1/organizations", headers=headers)
        accounts_response = client.get(
            f"/api/v1/organizations/{organization_id}/accounts", headers=headers
        )
        report_response = client.get(
            f"/api/v1/organizations/{organization_id}/reports/trial-balance", headers=headers
        )
        if any(
            response.status_code != 200
            for response in (organizations_response, accounts_response, report_response)
        ):
            raise RuntimeError("Controlled staging BUSINESS API verification failed.")
        api_verification = {
            "health_status": health.status_code,
            "authentication_status": token_response.status_code,
            "organizations_status": organizations_response.status_code,
            "accounts_status": accounts_response.status_code,
            "trial_balance_status": report_response.status_code,
            "trial_balance_balanced": bool(report_response.json()["balanced"]),
        }

    cli_engine = AccountingEngine(paths.source)
    try:
        cli_arguments = cli_parser().parse_args(
            [
                "--db",
                str(paths.source),
                "--actor",
                str(primary["owner_actor_id"]),
                "--org",
                str(primary["organization_id"]),
                "trial-balance",
            ]
        )
        cli_result = cast(dict[str, object], run_cli(cli_engine, cli_arguments))
        if not bool(cli_result["balanced"]):
            raise RuntimeError("Controlled staging CLI trial balance is not balanced.")
    finally:
        cli_engine.close()

    canary = {
        "status": "DEFINED_NOT_EXECUTED",
        "scenario_source": "existing deterministic BUSINESS expense-and-cash scenario",
        "organization_id": primary["organization_id"],
        "actor_id": primary["owner_actor_id"],
        "accounts": {
            "debit": cast(dict[str, str], primary["accounts"])["expense"],
            "credit": cast(dict[str, str], primary["accounts"])["cash"],
        },
        "amount_minor_units": 12_345,
        "financial_date": "2026-09-30",
        "project_id": primary["project_id"],
        "document_id": primary["document_id"],
        "proposal_description": "Controlled C4 canary operating purchase",
        "confirmation_request_id": "c4-canary-confirm-v1",
        "confirmation_idempotency_key": "c4-canary-confirm-v1",
        "posting_idempotency_key": "c4-canary-post-v1",
        "reversal_reason": "Reverse controlled C4 canary after verification",
        "expected_journal_effect": {
            "debit_expense": 12_345,
            "credit_cash": 12_345,
            "balanced": True,
        },
        "expected_report_effect": {
            "expense_net_debit_change": 12_345,
            "cash_net_debit_change": -12_345,
        },
        "expected_reversal_result": (
            "original and reversal remain visible; net changes return to zero"
        ),
        "accounting_data_approval": "REQUIRES_OPERATOR_DECISION",
    }
    seed: dict[str, object] = {
        "label": DEPLOYMENT_LABEL,
        "source_generation": "normal AuthService and AccountingEngine schema-v3 pathways",
        "users": users,
        "organizations": organizations,
        "canary": canary,
    }
    verification: dict[str, object] = {
        "api": api_verification,
        "cli_trial_balance_balanced": bool(cli_result["balanced"]),
        "credentials_path": str(credential_path),
        "credentials_excluded_from_evidence": True,
    }
    return seed, verification


def _release_inputs(project_root: Path) -> tuple[Path, ...]:
    files: set[Path] = set()
    for relative in ("pyproject.toml", "uv.lock", "frontend/package.json"):
        candidate = project_root / relative
        if candidate.is_file():
            files.add(candidate)
    frontend_lock = project_root / "frontend" / "package-lock.json"
    if frontend_lock.is_file():
        files.add(frontend_lock)
    for base in (
        project_root / "chatbook",
        project_root / "tests",
        project_root / "frontend" / "src",
    ):
        if not base.is_dir():
            continue
        for candidate in base.rglob("*"):
            if candidate.is_file() and candidate.suffix in {
                ".py",
                ".sql",
                ".ts",
                ".tsx",
                ".css",
                ".json",
            }:
                files.add(candidate)
    return tuple(sorted(files, key=lambda path: path.relative_to(project_root).as_posix()))


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def _create_release_manifest(project_root: Path, paths: DeploymentPaths) -> dict[str, object]:
    inputs = _release_inputs(project_root)
    file_records = [
        {
            "path": path.relative_to(project_root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _hash_file(path),
        }
        for path in inputs
    ]
    release_id = _json_hash(file_records)
    archive = paths.recovery / f"chatbook-v3-release-{release_id[:16]}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for source in inputs:
            relative = source.relative_to(project_root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, source.read_bytes())

    build_id_path = project_root / "frontend" / ".next" / "BUILD_ID"
    frontend_build = (
        {
            "status": "CAPTURED",
            "build_id": build_id_path.read_text(encoding="utf-8").strip(),
            "build_id_sha256": _hash_file(build_id_path),
        }
        if build_id_path.is_file()
        else {
            "status": "REQUIRES_OPERATOR_DECISION",
            "reason": "No frontend .next/BUILD_ID was present when the manifest was generated.",
        }
    )
    v4_files = tuple(
        project_root / relative
        for relative in (
            "chatbook/canonical_database.py",
            "chatbook/canonical_migration.py",
            "chatbook/canonical_schema.py",
            "chatbook/migrations/0004_canonical_book_tables.sql",
            "chatbook/storage/sqlite_book.py",
        )
    )
    v4_artifact = [
        {
            "path": path.relative_to(project_root).as_posix(),
            "sha256": _hash_file(path),
        }
        for path in v4_files
    ]
    manifest: dict[str, object] = {
        "tool_version": C4P_TOOL_VERSION,
        "identity_method": "SHA-256 over sorted repository-relative release file records",
        "source_release_id": release_id,
        "git_revision": "UNAVAILABLE_NO_GIT_METADATA",
        "schema_v3_release": {
            "schema_version": SCHEMA_VERSION,
            "normal_runtime": "chatbook.database.Database",
            "release_id": release_id,
        },
        "schema_v4_migration_artifact": {
            "status": "IDENTIFIED_FOR_SEPARATELY_AUTHORIZED_C4",
            "artifact_sha256": _json_hash(v4_artifact),
            "files": v4_artifact,
            "normal_runtime_selection": "EXPLICIT_SERVER_CONFIGURATION_IMPLEMENTED",
            "normal_runtime_mode": RuntimeStorageMode.CANONICAL_V4.value,
            "expected_schema_version": 4,
        },
        "compatible_v3_recovery_release": {
            "archive": str(archive),
            "archive_sha256": _hash_file(archive),
            "archive_bytes": archive.stat().st_size,
            "release_id": release_id,
        },
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "sqlite_version": sqlite3.sqlite_version,
        },
        "python_packages": {
            name: _package_version(name)
            for name in ("chatbook", "fastapi", "uvicorn", "pydantic", "httpx2", "mypy", "ruff")
        },
        "frontend_build": frontend_build,
        "release_files": file_records,
    }
    return manifest


def _probe_writer_gate(source: Path) -> dict[str, object]:
    guard = sqlite3.connect(str(source), isolation_level=None, timeout=1)
    contender = sqlite3.connect(str(source), isolation_level=None, timeout=0)
    contender.execute("PRAGMA busy_timeout = 0")
    try:
        guard.execute("BEGIN IMMEDIATE")
        blocked = False
        diagnostic = ""
        try:
            contender.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            diagnostic = str(exc)
            blocked = "locked" in diagnostic.lower()
        finally:
            if contender.in_transaction:
                contender.rollback()
        if not blocked:
            raise RuntimeError("The controlled writer probe was not blocked by the SQLite gate.")
        return {
            "writer_gate_acquired": True,
            "controlled_competing_writer_blocked": True,
            "diagnostic": diagnostic,
            "data_mutation": False,
        }
    finally:
        if guard.in_transaction:
            guard.rollback()
        contender.close()
        guard.close()


def _monitoring_plan() -> dict[str, object]:
    required = "REQUIRES_OPERATOR_DECISION"
    return {
        "status": "COLLECTION_IMPLEMENTED_AWAITING_OPERATOR_ASSIGNMENT",
        "collector": "chatbook-c4-monitor",
        "collector_behavior": (
            "read-only sanitized evidence; nonzero exit for required invariant alerts"
        ),
        "external_alert_delivery": required,
        "automatic_repair": False,
        "automatic_rollback": False,
        "signals": [
            {
                "signal": "schema_version",
                "source": "PRAGMA user_version and application startup logs",
                "threshold": "3 before C4; 4 only after accepted C4 commit",
                "owner": required,
                "alert": "observed version differs from the approved phase",
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "database_integrity",
                "source": "PRAGMA integrity_check",
                "threshold": "exactly ok",
                "owner": required,
                "alert": "any result other than ok",
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "foreign_key_violations",
                "source": "PRAGMA foreign_key_check",
                "threshold": "zero rows",
                "owner": required,
                "alert": "one or more rows",
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "sqlite_lock_or_write_failures",
                "source": "structured API/CLI/migration error logs",
                "threshold": required,
                "owner": required,
                "alert": "busy/locked/write error exceeds approved threshold",
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "financial_command_errors",
                "source": "FastAPI structured request/error logs by stable error code",
                "threshold": required,
                "owner": required,
                "alert": (
                    "proposal/validation/confirmation/post/reversal/period-lock errors "
                    "exceed approved threshold"
                ),
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "idempotency_failures",
                "source": "command_idempotency reconciliation plus application errors",
                "threshold": (
                    "zero retry-resource disagreements; conflict-rate threshold requires approval"
                ),
                "owner": required,
                "alert": (
                    "retry returns a different resource or approved conflict threshold is exceeded"
                ),
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "audit_sidecar_integrity",
                "source": "C4 read-only audit_event_book_scopes coverage query",
                "threshold": "zero missing, duplicate, or mismatched sidecars",
                "owner": required,
                "alert": "any coverage mismatch",
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "ledger_or_reconciliation_mismatch",
                "source": "migration manifest, balance checks, proposal/journal projection hashes",
                "threshold": "zero unbalanced entries and exact approved fingerprints",
                "owner": required,
                "alert": "any mismatch",
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "report_mismatch",
                "source": (
                    "trial balance, ledger, statements, cash movement, and project report "
                    "fingerprints"
                ),
                "threshold": "exact equality with approved pre-cutover evidence",
                "owner": required,
                "alert": "any fingerprint or structured-result mismatch",
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "migration_errors",
                "source": "sanitized C4 migration report and operator command log",
                "threshold": "zero errors",
                "owner": required,
                "alert": "any migration, trigger, index, authorizer, or version error",
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "latency",
                "source": "FastAPI http_request duration_ms and migration phase timings",
                "threshold": required,
                "owner": required,
                "alert": "approved latency threshold exceeded",
                "escalation": required,
                "observation_duration": required,
            },
            {
                "signal": "protected_artifact_access_failures",
                "source": "Windows filesystem/security audit evidence",
                "threshold": (
                    "zero unauthorized access; audit enablement requires operator verification"
                ),
                "owner": required,
                "alert": "unauthorized or failed approved access",
                "escalation": required,
                "observation_duration": required,
            },
        ],
    }


def _write_monitoring_configuration(paths: DeploymentPaths) -> dict[str, object]:
    configuration: dict[str, object] = {
        "version": MONITOR_VERSION,
        "phase": "PRE_CUTOVER_V3",
        "database_path": str(paths.source),
        "expected_schema_version": 3,
        "expected_manifest_path": str(paths.evidence / "source-preflight-manifest.json"),
        "application_log_path": str(paths.logs / "operational-events.jsonl"),
        "migration_report_path": None,
        "baselines": {
            "latency_threshold": BASELINE_REQUIRED,
            "migration_duration": BASELINE_REQUIRED,
            "request_drain_duration": BASELINE_REQUIRED,
            "sqlite_lock_frequency": BASELINE_REQUIRED,
            "resource_usage": BASELINE_REQUIRED,
        },
        "operator_decisions": {
            "monitoring_owner": REQUIRES_OPERATOR_DECISION,
            "escalation_owner": REQUIRES_OPERATOR_DECISION,
            "observation_period": REQUIRES_OPERATOR_DECISION,
            "alert_destination": REQUIRES_OPERATOR_DECISION,
            "stop_or_rollback_authority": REQUIRES_OPERATOR_DECISION,
        },
        "automatic_repair": False,
        "automatic_rollback": False,
        "financial_mutation": False,
    }
    configuration_path = paths.config / "operational-monitoring.json"
    _write_json(configuration_path, configuration)
    parsed = MonitoringConfiguration.from_file(configuration_path)
    return {
        **configuration,
        "configuration_fingerprint": parsed.fingerprint,
    }


def _powershell_literal(value: Path) -> str:
    return str(value).replace("'", "''")


def _write_runtime_configuration(paths: DeploymentPaths, release_id: str) -> dict[str, object]:
    maintenance = MaintenancePaths.explicit(
        paths.config / "maintenance-control.json",
        paths.runtime / "maintenance-state.json",
    )
    initialize_maintenance_control(maintenance)
    configuration = {
        "database_path": str(paths.source),
        "storage_mode": RuntimeStorageMode.ORGANIZATION_V3.value,
        "expected_schema_version": 3,
        "access_mode": RuntimeAccessMode.READ_WRITE.value,
        "release_id": release_id,
        "owner_scope": "BUSINESS",
    }
    _write_json(paths.config / "runtime-selection.json", configuration)
    (paths.config / "backend.env").write_text(
        "\n".join(
            (
                f"{DATABASE_PATH_ENV}={paths.source}",
                f"{STORAGE_MODE_ENV}={RuntimeStorageMode.ORGANIZATION_V3.value}",
                f"{SCHEMA_VERSION_ENV}=3",
                f"{ACCESS_MODE_ENV}={RuntimeAccessMode.READ_WRITE.value}",
                f"{RELEASE_ID_ENV}={release_id}",
                f"{CONTROL_PATH_ENV}={maintenance.control}",
                f"{STATE_PATH_ENV}={maintenance.state}",
                f"{OPERATIONAL_EVENT_LOG_ENV}={paths.logs / 'operational-events.jsonl'}",
                "CHATBOOK_HOST=127.0.0.1",
                "CHATBOOK_PORT=8100",
                "",
            )
        ),
        encoding="utf-8",
    )
    (paths.config / "frontend.env").write_text(
        "CHATBOOK_API_URL=http://127.0.0.1:8100/api/v1\n", encoding="utf-8"
    )
    configuration["maintenance_configuration_fingerprint"] = maintenance.fingerprint
    configuration["maintenance_control_path"] = str(maintenance.control)
    configuration["maintenance_state_path"] = str(maintenance.state)
    return configuration


def _write_runtime_controls(
    paths: DeploymentPaths, project_root: Path, *, release_id: str
) -> dict[str, object]:
    backend = project_root / ".venv" / "Scripts" / "chatbook-api.exe"
    python = project_root / ".venv" / "Scripts" / "python.exe"
    npm = "npm.cmd"
    paths.runtime.mkdir(parents=True, exist_ok=True)
    controls = paths.root / "controls"
    controls.mkdir(parents=True, exist_ok=True)

    backend_text = _powershell_literal(backend)
    project_text = _powershell_literal(project_root)
    source_text = _powershell_literal(paths.source)
    backend_pid = _powershell_literal(paths.runtime / "backend.pid")
    frontend_pid = _powershell_literal(paths.runtime / "frontend.pid")
    backend_stdout = _powershell_literal(paths.logs / "backend.stdout.log")
    backend_stderr = _powershell_literal(paths.logs / "backend.stderr.log")
    operational_events = _powershell_literal(paths.logs / "operational-events.jsonl")
    frontend_stdout = _powershell_literal(paths.logs / "frontend.stdout.log")
    frontend_stderr = _powershell_literal(paths.logs / "frontend.stderr.log")
    frontend_root = _powershell_literal(project_root / "frontend")
    python_text = _powershell_literal(python)
    root_text = _powershell_literal(paths.root)
    runtime_selection = _powershell_literal(paths.config / "runtime-selection.json")
    release_manifest = _powershell_literal(paths.evidence / "release-manifest.json")
    startup_evidence = _powershell_literal(paths.evidence / "runtime-startup-evidence.json")
    maintenance_control = _powershell_literal(paths.config / "maintenance-control.json")
    maintenance_state = _powershell_literal(paths.runtime / "maintenance-state.json")
    monitoring_configuration = _powershell_literal(paths.config / "operational-monitoring.json")
    monitoring_evidence = _powershell_literal(
        paths.evidence / "operational-monitoring-evidence.json"
    )
    v4_target = _powershell_literal(paths.v4_target)
    release_text = release_id.replace("'", "''")

    start_backend = f"""$ErrorActionPreference = 'Stop'
$pidFile = '{backend_pid}'
if (Test-Path -LiteralPath $pidFile) {{ throw 'Backend PID file already exists.' }}
foreach ($requiredPath in @(
    '{backend_text}',
    '{python_text}',
    '{runtime_selection}',
    '{release_manifest}',
    '{maintenance_control}',
    '{maintenance_state}',
    '{monitoring_configuration}'
)) {{
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {{
        throw "Required C4P runtime artifact is missing: $requiredPath"
    }}
}}
$selection = Get-Content -Raw -LiteralPath '{runtime_selection}' | ConvertFrom-Json
$manifest = Get-Content -Raw -LiteralPath '{release_manifest}' | ConvertFrom-Json
if ($selection.owner_scope -ne 'BUSINESS') {{ throw 'C4P runtime owner scope must be BUSINESS.' }}
if ($selection.release_id -ne '{release_text}' -or
    $manifest.source_release_id -ne '{release_text}') {{
    throw 'Runtime selection and release manifest identity do not match this C4P release.'
}}
if ($selection.storage_mode -eq 'organization-v3') {{
    if ($selection.expected_schema_version -ne 3) {{ throw 'organization-v3 requires schema 3.' }}
    if ($selection.access_mode -ne 'read-write') {{
        throw 'organization-v3 C4P startup requires read-write access.'
    }}
    if ([System.IO.Path]::GetFullPath($selection.database_path) -ne '{source_text}') {{
        throw 'C4P schema-v3 runtime may target only the controlled source database.'
    }}
    if (Test-Path -LiteralPath '{v4_target}') {{
        throw 'The reserved v4 target exists; schema-v3 restart is blocked.'
    }}
}} elseif ($selection.storage_mode -eq 'canonical-v4') {{
    if ($selection.expected_schema_version -ne 4) {{ throw 'canonical-v4 requires schema 4.' }}
    if ($selection.access_mode -ne 'read-only') {{
        throw 'C4P permits canonical-v4 only for post-migration read-only acceptance.'
    }}
    if ([System.IO.Path]::GetFullPath($selection.database_path) -ne '{v4_target}') {{
        throw 'C4P schema-v4 runtime may target only the reserved controlled v4 database.'
    }}
    if (-not (Test-Path -LiteralPath '{v4_target}' -PathType Leaf)) {{
        throw 'The reviewed schema-v4 target does not exist; startup will not create it.'
    }}
}} else {{
    throw 'Unsupported C4P storage mode.'
}}
$env:CHATBOOK_DB_PATH = [string]$selection.database_path
$env:CHATBOOK_STORAGE_MODE = [string]$selection.storage_mode
$env:CHATBOOK_SCHEMA_VERSION = [string]$selection.expected_schema_version
$env:CHATBOOK_RUNTIME_ACCESS = [string]$selection.access_mode
$env:CHATBOOK_RUNTIME_RELEASE_ID = [string]$selection.release_id
$env:CHATBOOK_MAINTENANCE_CONTROL_PATH = '{maintenance_control}'
$env:CHATBOOK_MAINTENANCE_STATE_PATH = '{maintenance_state}'
$env:CHATBOOK_OPERATIONAL_EVENT_LOG_PATH = '{operational_events}'
$env:CHATBOOK_HOST = '127.0.0.1'
$env:CHATBOOK_PORT = '8100'
$trafficStatus = & '{python_text}' -m chatbook.maintenance `
    --control '{maintenance_control}' --state '{maintenance_state}' status | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $trafficStatus.control.mode -ne 'accepting' -or
    $trafficStatus.control.shutdown_requested) {{
    throw 'Backend startup requires the operator control in accepting mode.'
}}
$inspectionCode = @'
from chatbook.runtime import main
raise SystemExit(main(['inspect', '--evidence', r'{startup_evidence}']))
'@
& '{python_text}' -c $inspectionCode
if ($LASTEXITCODE -ne 0) {{ throw 'Runtime database inspection failed; backend was not started.' }}
$inspection = Get-Content -Raw -LiteralPath '{startup_evidence}' | ConvertFrom-Json
Write-Host "Chatbooks database: $($inspection.database_path)"
Write-Host "Storage/schema: $($inspection.storage_mode) / $($inspection.actual_schema_version)"
Write-Host "Access: $($inspection.access_mode)"
Write-Host "Release: $($inspection.release_id)"
$process = Start-Process `
    -FilePath '{backend_text}' `
    -WorkingDirectory '{project_text}' `
    -WindowStyle Hidden `
    -RedirectStandardOutput '{backend_stdout}' `
    -RedirectStandardError '{backend_stderr}' `
    -PassThru
Set-Content -LiteralPath $pidFile -Value $process.Id -NoNewline
"""
    start_frontend = f"""$ErrorActionPreference = 'Stop'
$pidFile = '{frontend_pid}'
if (Test-Path -LiteralPath $pidFile) {{ throw 'Frontend PID file already exists.' }}
if (-not (Test-Path -LiteralPath '{backend_pid}' -PathType Leaf)) {{
    throw 'Start the verified C4P backend before the frontend.'
}}
$backendProcessId = [int](Get-Content -Raw -LiteralPath '{backend_pid}')
if ($null -eq (Get-Process -Id $backendProcessId -ErrorAction SilentlyContinue)) {{
    throw 'The recorded C4P backend process is not running.'
}}
$env:CHATBOOK_API_URL = 'http://127.0.0.1:8100/api/v1'
$process = Start-Process `
    -FilePath '{npm}' `
    -ArgumentList 'run','start','--','--port','3100' `
    -WorkingDirectory '{frontend_root}' `
    -WindowStyle Hidden `
    -RedirectStandardOutput '{frontend_stdout}' `
    -RedirectStandardError '{frontend_stderr}' `
    -PassThru
Set-Content -LiteralPath $pidFile -Value $process.Id -NoNewline
"""
    enter_maintenance = f"""param(
    [Parameter(Mandatory=$true)]
    [ValidateRange(1,86400)]
    [int]$DrainTimeoutSeconds
)
$ErrorActionPreference = 'Stop'
& '{python_text}' -m chatbook.maintenance --control '{maintenance_control}' `
    --state '{maintenance_state}' enter --reason 'operator-started-c4-drain'
if ($LASTEXITCODE -ne 0) {{ throw 'Failed to enter the request-draining state.' }}
& '{python_text}' -m chatbook.maintenance --control '{maintenance_control}' `
    --state '{maintenance_state}' wait --timeout-seconds $DrainTimeoutSeconds
if ($LASTEXITCODE -ne 0) {{ throw 'In-flight requests did not drain to zero.' }}
& '{python_text}' -m chatbook.maintenance --control '{maintenance_control}' `
    --state '{maintenance_state}' seal --reason 'operator-sealed-c4-maintenance'
if ($LASTEXITCODE -ne 0) {{ throw 'Failed to seal the maintenance gate.' }}
"""
    stop_processes = f"""param(
    [Parameter(Mandatory=$true)]
    [ValidateRange(1,86400)]
    [int]$ShutdownTimeoutSeconds
)
$ErrorActionPreference = 'Stop'
$trafficStatus = & '{python_text}' -m chatbook.maintenance `
    --control '{maintenance_control}' --state '{maintenance_state}' status | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $trafficStatus.control.mode -ne 'maintenance' -or
    [int]$trafficStatus.runtime.in_flight -ne 0) {{
    throw 'Application stop requires sealed maintenance with zero in-flight requests.'
}}
if (Test-Path -LiteralPath '{frontend_pid}') {{
    $frontendProcessId = [int](Get-Content -Raw -LiteralPath '{frontend_pid}')
    if ($null -ne (Get-Process -Id $frontendProcessId -ErrorAction SilentlyContinue)) {{
        & taskkill.exe /PID $frontendProcessId /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) {{ throw 'Failed to stop the frontend process tree.' }}
    }}
    Remove-Item -LiteralPath '{frontend_pid}' -Force
}}
if (Test-Path -LiteralPath '{backend_pid}') {{
    $backendProcessId = [int](Get-Content -Raw -LiteralPath '{backend_pid}')
    $backendProcess = Get-Process -Id $backendProcessId -ErrorAction SilentlyContinue
    if ($null -ne $backendProcess) {{
        & '{python_text}' -m chatbook.maintenance --control '{maintenance_control}' `
            --state '{maintenance_state}' request-shutdown `
            --reason 'operator-requested-graceful-backend-stop'
        if ($LASTEXITCODE -ne 0) {{ throw 'Failed to request graceful backend shutdown.' }}
        if (-not $backendProcess.WaitForExit($ShutdownTimeoutSeconds * 1000)) {{
            throw 'Backend exceeded the supplied timeout; no force-stop was used.'
        }}
    }}
    Remove-Item -LiteralPath '{backend_pid}' -Force
}}
"""
    reset_maintenance = f"""param(
    [Parameter(Mandatory=$true)]
    [string]$Acknowledgement
)
$ErrorActionPreference = 'Stop'
if ($Acknowledgement -ne 'RESET STOPPED C4P STAGING TO ACCEPTING') {{
    throw 'Exact reset acknowledgement was not supplied.'
}}
& '{python_text}' -m chatbook.maintenance --control '{maintenance_control}' `
    --state '{maintenance_state}' reset-stopped --reason 'operator-reset-stopped-staging'
if ($LASTEXITCODE -ne 0) {{ throw 'Stopped staging runtime could not return to accepting mode.' }}
"""
    verify = f"""$ErrorActionPreference = 'Stop'
foreach ($pidFile in @('{frontend_pid}','{backend_pid}')) {{
    if (Test-Path -LiteralPath $pidFile) {{ throw "Runtime PID file remains: $pidFile" }}
}}
$trafficStatus = & '{python_text}' -m chatbook.maintenance `
    --control '{maintenance_control}' --state '{maintenance_state}' status | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $trafficStatus.control.mode -ne 'maintenance' -or
    $trafficStatus.runtime.backend_state -ne 'stopped' -or
    [int]$trafficStatus.runtime.in_flight -ne 0) {{
    throw 'Quiescence requires stopped backend, sealed maintenance, and zero in-flight requests.'
}}
& '{python_text}' -m chatbook.deployment_preparation verify '{root_text}' --record-evidence
if ($LASTEXITCODE -ne 0) {{ throw 'C4P quiescence/evidence verification failed.' }}
"""
    collect_monitoring = f"""$ErrorActionPreference = 'Stop'
& '{python_text}' -m chatbook.operational_monitoring '{monitoring_configuration}' `
    --evidence '{monitoring_evidence}'
if ($LASTEXITCODE -ne 0) {{ throw 'A required operational invariant failed closed.' }}
"""
    (controls / "Start-Backend.ps1").write_text(start_backend, encoding="utf-8")
    (controls / "Start-Frontend.ps1").write_text(start_frontend, encoding="utf-8")
    (controls / "Enter-Maintenance.ps1").write_text(enter_maintenance, encoding="utf-8")
    (controls / "Stop-Application.ps1").write_text(stop_processes, encoding="utf-8")
    (controls / "Reset-Maintenance.ps1").write_text(reset_maintenance, encoding="utf-8")
    (controls / "Verify-Quiescence.ps1").write_text(verify, encoding="utf-8")
    (controls / "Collect-Monitoring.ps1").write_text(collect_monitoring, encoding="utf-8")
    operator_notes = f"""# Controlled C4P runtime operations

Deployment root: `{paths.root}`

**Traffic topology:** `NO EXTERNAL TRAFFIC TERMINATION PRESENT`. The controlled backend is bound to
loopback and the local frontend calls it directly. The server-owned maintenance file is the
deployment-specific rejection boundary; no HTTP request can change it.

1. Start the backend with `controls\\Start-Backend.ps1`.
2. Start the already-built frontend with `controls\\Start-Frontend.ps1`.
3. Before a future separately authorized C4, run `controls\\Enter-Maintenance.ps1` with an
   operator-approved drain timeout. It rejects every newly arriving HTTP request, allows accepted
   requests to finish, waits for the measured in-flight count to reach zero, and seals the gate.
4. Run `controls\\Stop-Application.ps1` with an operator-approved shutdown timeout. It stops the
   frontend, requests graceful Uvicorn shutdown through the local control file, and does not use a
   force-stop fallback for the backend.
5. Confirm both PID files are absent, perform the elevated Windows service/scheduled-task/
   file-handle inventory, and prohibit trusted CLI and raw database access under the change record.
   Then run `controls\\Verify-Quiescence.ps1`.
6. The verification command requires sealed/stopped/zero-in-flight state, acquires
   `BEGIN IMMEDIATE`, proves a controlled second writer is
   blocked, and rolls back without data mutation. C4 must reacquire its own gate while creating the
   backup.
7. Run `controls\\Collect-Monitoring.ps1` to collect sanitized read-only invariant evidence. A hard
   invariant returns a nonzero status. Numerical baselines, owners, escalation, alert destination,
   observation duration, and stop/rollback authority remain operator decisions.

`config\runtime-selection.json` is the server-owned selector. It currently names the controlled
schema-v3 source with `read-write` access. The backend control accepts exactly that source for
`organization-v3`, or the reserved target for `canonical-v4` with `read-only` access; it rejects
every other path, owner scope, schema/mode/access combination, and release identity. It validates
the selected database read-only and records
`evidence\runtime-startup-evidence.json` before starting a process. It never migrates or creates a
database. Do not select `canonical-v4` until C4 has created and accepted the target and the release
owner has approved the exact release manifest.

The repository has no background worker or scheduler. The frontend is an HTTP client and has no
database access. External ingress, Windows service/task inventory, raw administrator exclusion,
monitoring ownership, empirical thresholds, alert delivery, and the observation period remain
`REQUIRES_OPERATOR_DECISION`.
"""
    (controls / "OPERATIONS.md").write_text(operator_notes, encoding="utf-8")
    return {
        "backend_entrypoint": "chatbook.api.main:run via chatbook-api",
        "frontend_entrypoint": "Next.js npm run start",
        "database_initialization": "explicit RuntimeConfiguration selects v3 or existing v4",
        "authentication_startup": "AuthService uses the same RuntimeConfiguration and adapter",
        "supported_financial_writers": [
            "FastAPI routes through AccountingEngine and UniversalFinancialService",
            "trusted local chatbook CLI through AccountingEngine and UniversalFinancialService",
        ],
        "background_or_scheduled_workers": "NONE_DEFINED_IN_REPOSITORY",
        "raw_administrator_tools": (
            "OUTSIDE_SUPPORTED_APPLICATION_BOUNDARY_REQUIRES_OPERATOR_CONTROL"
        ),
        "schema_v4_normal_runtime": "IMPLEMENTED_EXPLICIT_SERVER_CONFIGURATION_ONLY",
        "runtime_release_id": release_id,
        "runtime_selection": str(paths.config / "runtime-selection.json"),
        "external_traffic_termination": "NO EXTERNAL TRAFFIC TERMINATION PRESENT",
        "start_backend": str(controls / "Start-Backend.ps1"),
        "start_frontend": str(controls / "Start-Frontend.ps1"),
        "enter_maintenance": str(controls / "Enter-Maintenance.ps1"),
        "stop_application": str(controls / "Stop-Application.ps1"),
        "reset_maintenance": str(controls / "Reset-Maintenance.ps1"),
        "verify_quiescence": str(controls / "Verify-Quiescence.ps1"),
        "collect_monitoring": str(controls / "Collect-Monitoring.ps1"),
        "request_drain": "IMPLEMENTED_LOCAL_SERVER_OWNED_GATE",
        "external_ingress_control": "REQUIRES_OPERATOR_DECISION_IF_TOPOLOGY_CHANGES",
        "windows_service_task_handle_inventory": "REQUIRES_OPERATOR_DECISION",
    }


def prepare_deployment_environment(
    root: str | Path, *, project_root: str | Path
) -> dict[str, object]:
    paths = DeploymentPaths.for_root(root)
    project = Path(project_root).resolve()
    development_database = project / "chatbook.db"
    if paths.root == project or project in paths.root.parents:
        raise ChatbookError(
            "deployment_root_invalid",
            "The controlled deployment root must be outside the repository.",
        )
    if paths.source == development_database.resolve():
        raise ChatbookError(
            "deployment_source_invalid", "The development chatbook.db cannot be the C4P source."
        )
    if paths.root.exists():
        raise ChatbookError(
            "deployment_root_exists", "Preparation requires a new deployment directory."
        )
    if SCHEMA_VERSION != REQUIRED_SCHEMA_VERSION:
        raise ChatbookError(
            "schema_version", "C4P preparation requires the normal schema-v3 application release."
        )

    for directory in (
        paths.evidence,
        paths.logs,
        paths.config,
        paths.runtime,
        paths.recovery,
        paths.secrets,
        paths.v4_target.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    seed, application_verification = _create_staging_source(paths)
    release_manifest = _create_release_manifest(project, paths)
    _write_json(paths.evidence / "release-manifest.json", release_manifest)
    release_id = str(release_manifest["source_release_id"])
    monitoring = _monitoring_plan()
    _write_json(paths.config / "monitoring-plan.json", monitoring)
    runtime_configuration = _write_runtime_configuration(paths, release_id)
    topology = _write_runtime_controls(paths, project, release_id=release_id)

    preflight = build_preflight_manifest(
        paths.source,
        database_identity=hashlib.sha256(DEPLOYMENT_LABEL.encode()).hexdigest(),
    )
    _write_json(paths.evidence / "source-preflight-manifest.json", preflight)
    monitoring_configuration = _write_monitoring_configuration(paths)
    backup_evidence = create_verified_backup(paths.source, paths.backup)
    expected = cast(Mapping[str, object], backup_evidence["manifest"])
    restore_evidence = restore_verified_backup(
        paths.backup, paths.restore_proof, expected_manifest=expected
    )
    writer_gate = _probe_writer_gate(paths.source)

    source_hash = _hash_file(paths.source)
    source_size = paths.source.stat().st_size
    source_connection = sqlite3.connect(
        f"{paths.source.as_uri()}?mode=ro", uri=True, isolation_level=None
    )
    try:
        source_version = int(source_connection.execute("PRAGMA user_version").fetchone()[0])
        integrity = [str(row[0]) for row in source_connection.execute("PRAGMA integrity_check")]
        foreign_keys = len(tuple(source_connection.execute("PRAGMA foreign_key_check")))
    finally:
        source_connection.close()
    if source_version != REQUIRED_SCHEMA_VERSION or integrity != ["ok"] or foreign_keys:
        raise RuntimeError("Prepared deployment source failed its final schema/integrity gate.")
    if paths.v4_target.exists():
        raise RuntimeError("C4P must not create the schema-v4 target.")

    evidence: dict[str, object] = {
        "tool_version": C4P_TOOL_VERSION,
        "generated_at": _now(),
        "label": DEPLOYMENT_LABEL,
        "classification": "CONTROLLED_DEPLOYMENT_STAGING_NOT_PRODUCTION",
        "c4_executed": False,
        "personal_data_created": False,
        "paths": {
            "deployment_root": str(paths.root),
            "source_database": str(paths.source),
            "backup_database": str(paths.backup),
            "restore_proof_database": str(paths.restore_proof),
            "reserved_v4_target": str(paths.v4_target),
            "evidence": str(paths.evidence),
            "logs": str(paths.logs),
            "config": str(paths.config),
            "recovery": str(paths.recovery),
            "secrets": str(paths.secrets),
        },
        "source": {
            "schema_version": source_version,
            "bytes": source_size,
            "sha256": source_hash,
            "integrity_check": integrity,
            "foreign_key_violation_count": foreign_keys,
            "preflight_content_fingerprint": preflight["content_fingerprint"],
            "preflight_legacy_content_fingerprint": preflight["legacy_content_fingerprint"],
            "metrics": preflight["metrics"],
        },
        "seed": seed,
        "application_verification": application_verification,
        "runtime_topology": topology,
        "runtime_configuration": runtime_configuration,
        "writer_gate": writer_gate,
        "release": release_manifest,
        "backup": {
            "verified": backup_evidence["backup_restore_verified"],
            "sha256": backup_evidence["backup_sha256"],
            "bytes": paths.backup.stat().st_size,
            "restore_proof": restore_evidence,
        },
        "artifact_protection": {
            "acl": "PENDING_EXTERNAL_WINDOWS_ACL_VERIFICATION",
            "encryption": "REQUIRES_OPERATOR_DECISION",
            "off_host_recovery": "REQUIRES_OPERATOR_DECISION",
            "retention_owner": "REQUIRES_OPERATOR_DECISION",
            "destruction_owner": "REQUIRES_OPERATOR_DECISION",
        },
        "monitoring": monitoring,
        "monitoring_configuration": monitoring_configuration,
        "canary": seed["canary"],
        "unresolved_operator_decisions": [
            (
                "release owner, migration operator, application operator, accounting/data "
                "reviewer, and incident recorder"
            ),
            "approved maintenance window and graceful request-drain interval",
            (
                "elevated Windows service, scheduled-task, process, listener, and open-handle "
                "inventory"
            ),
            "artifact encryption, off-host recovery, retention, and destruction ownership",
            (
                "monitoring owners, numerical thresholds where needed, escalation routes, and "
                "observation duration"
            ),
            "canary accounting/data approval and final idempotency keys",
            "operator-approved disk safety margin and downtime budget",
        ],
    }
    _write_json(paths.evidence / "deployment-preparation-evidence.json", evidence)
    _write_json(
        paths.evidence / "source-identity.json",
        {
            "label": DEPLOYMENT_LABEL,
            "intended_use": "future separately authorized M5.1-C4 controlled staging source",
            "schema_version": source_version,
            "bytes": source_size,
            "sha256": source_hash,
            "content_fingerprint": preflight["content_fingerprint"],
            "c4_executed": False,
        },
    )
    return evidence


def _verify_source_artifacts(
    paths: DeploymentPaths,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    evidence_path = paths.evidence / "deployment-preparation-evidence.json"
    if not evidence_path.is_file():
        raise ChatbookError("deployment_evidence_missing", "C4P evidence is missing.")
    evidence = cast(dict[str, Any], json.loads(evidence_path.read_text(encoding="utf-8")))
    if (
        evidence.get("classification") != "CONTROLLED_DEPLOYMENT_STAGING_NOT_PRODUCTION"
        or evidence.get("label") != DEPLOYMENT_LABEL
        or evidence.get("c4_executed") is not False
        or evidence.get("personal_data_created") is not False
    ):
        raise ChatbookError(
            "deployment_evidence_mismatch", "C4P environment identity or scope evidence changed."
        )
    expected_source = cast(dict[str, Any], evidence["source"])
    if (
        not paths.source.is_file()
        or not paths.backup.is_file()
        or not paths.restore_proof.is_file()
    ):
        raise ChatbookError("deployment_artifact_missing", "A required C4P artifact is missing.")
    if paths.v4_target.exists():
        raise ChatbookError("c4p_scope_violation", "The schema-v4 target must not exist in C4P.")
    manifest = build_preflight_manifest(paths.source)
    restore_manifest = build_preflight_manifest(paths.restore_proof, expected_manifest=manifest)
    source_hash = _hash_file(paths.source)
    source_version = int(cast(int, manifest["schema_version"]))
    valid = (
        source_version == REQUIRED_SCHEMA_VERSION
        and source_hash == expected_source["sha256"]
        and manifest["content_fingerprint"] == expected_source["preflight_content_fingerprint"]
        and restore_manifest["content_fingerprint"] == manifest["content_fingerprint"]
    )
    if not valid:
        raise ChatbookError("deployment_evidence_mismatch", "C4P source evidence changed.")
    return evidence, manifest, restore_manifest, source_hash


def _read_backend_environment(paths: DeploymentPaths) -> dict[str, str]:
    allowed = {
        DATABASE_PATH_ENV,
        STORAGE_MODE_ENV,
        SCHEMA_VERSION_ENV,
        RELEASE_ID_ENV,
        ACCESS_MODE_ENV,
        CONTROL_PATH_ENV,
        STATE_PATH_ENV,
        OPERATIONAL_EVENT_LOG_ENV,
        "CHATBOOK_HOST",
        "CHATBOOK_PORT",
    }
    environment_path = paths.config / "backend.env"
    if not environment_path.is_file():
        raise ChatbookError("runtime_configuration_missing", "C4P backend.env is missing.")
    values: dict[str, str] = {}
    for line in environment_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator or key not in allowed or key in values:
            raise ChatbookError(
                "runtime_configuration_invalid", "C4P backend.env contains an invalid setting."
            )
        values[key] = value
    required = {
        DATABASE_PATH_ENV,
        STORAGE_MODE_ENV,
        SCHEMA_VERSION_ENV,
        ACCESS_MODE_ENV,
        RELEASE_ID_ENV,
    }
    if not required.issubset(values):
        raise ChatbookError(
            "runtime_configuration_missing", "C4P backend.env is missing required settings."
        )
    return values


def _load_c4p_runtime_configuration(
    paths: DeploymentPaths,
) -> tuple[RuntimeConfiguration, dict[str, object]]:
    selection_path = paths.config / "runtime-selection.json"
    manifest_path = paths.evidence / "release-manifest.json"
    if not selection_path.is_file() or not manifest_path.is_file():
        raise ChatbookError(
            "runtime_configuration_missing", "C4P runtime selection or release manifest is missing."
        )
    selection = cast(dict[str, object], json.loads(selection_path.read_text(encoding="utf-8")))
    if set(selection) != {
        "database_path",
        "storage_mode",
        "expected_schema_version",
        "release_id",
        "access_mode",
        "owner_scope",
    }:
        raise ChatbookError(
            "runtime_configuration_invalid", "C4P runtime selection has unexpected fields."
        )
    if selection["owner_scope"] != "BUSINESS":
        raise ChatbookError("runtime_owner_scope", "C4P runtime owner scope must be BUSINESS.")
    configuration = RuntimeConfiguration.explicit(
        str(selection["database_path"]),
        storage_mode=str(selection["storage_mode"]),
        expected_schema_version=int(cast(int, selection["expected_schema_version"])),
        access_mode=str(selection["access_mode"]),
        release_id=str(selection["release_id"]),
        source="c4p-runtime-selection",
    )
    if (
        configuration.storage_mode is not RuntimeStorageMode.ORGANIZATION_V3
        or configuration.resolved_database_path != paths.source
        or configuration.expected_schema_version != REQUIRED_SCHEMA_VERSION
        or configuration.access_mode is not RuntimeAccessMode.READ_WRITE
    ):
        raise ChatbookError(
            "c4p_scope_violation",
            "Before C4, the controlled runtime selection must remain on the schema-v3 source.",
        )
    manifest = cast(dict[str, object], json.loads(manifest_path.read_text(encoding="utf-8")))
    if manifest.get("source_release_id") != configuration.release_id:
        raise ChatbookError(
            "runtime_release_id", "Runtime selection and release manifest identities differ."
        )
    environment = _read_backend_environment(paths)
    environment_configuration = RuntimeConfiguration.from_environment(environment)
    if environment_configuration.fingerprint != configuration.fingerprint:
        raise ChatbookError(
            "runtime_configuration_invalid",
            "backend.env and runtime-selection.json do not describe the same runtime.",
        )
    return configuration, selection


def _listener_active(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.1):
            return True
    except OSError:
        return False


def verify_deployment_environment(
    root: str | Path, *, record_evidence: bool = False
) -> dict[str, object]:
    paths = DeploymentPaths.for_root(root)
    _, manifest, _, source_hash = _verify_source_artifacts(paths)
    configuration, selection = _load_c4p_runtime_configuration(paths)
    runtime_evidence = inspect_runtime_database(configuration)
    pid_files = tuple(
        str(path)
        for path in (paths.runtime / "backend.pid", paths.runtime / "frontend.pid")
        if path.exists()
    )
    listeners = {
        "backend_8100": _listener_active("127.0.0.1", 8100),
        "frontend_3100": _listener_active("127.0.0.1", 3100),
    }
    if pid_files or any(listeners.values()):
        raise ChatbookError(
            "runtime_not_quiescent", "C4P verification requires stopped application runtimes."
        )
    source_version = int(cast(int, manifest["schema_version"]))
    result: dict[str, object] = {
        "status": "verified",
        "schema_version": source_version,
        "source_sha256": source_hash,
        "source_bytes": paths.source.stat().st_size,
        "integrity_check": manifest["integrity_check"],
        "foreign_key_violation_count": manifest["foreign_key_violation_count"],
        "source_restore_content_equal": True,
        "writer_gate": _probe_writer_gate(paths.source),
        "writer_control_state": {
            "pid_files": list(pid_files),
            "active_listeners": listeners,
            "quiescent": True,
        },
        "runtime": runtime_evidence,
        "deployment_configuration": {
            "selected_storage_mode": selection["storage_mode"],
            "selected_schema_version": selection["expected_schema_version"],
            "selected_access_mode": selection["access_mode"],
            "database_path": selection["database_path"],
            "release_id": selection["release_id"],
            "owner_scope": selection["owner_scope"],
            "fingerprint": configuration.fingerprint,
            "sensitive_values_included": False,
        },
        "row_counts": manifest["metrics"],
        "v4_target_exists": False,
        "c4_executed": False,
        "personal_data_created": False,
    }
    if record_evidence:
        _write_json(paths.evidence / "runtime-verification-evidence.json", result)
    return result


def harden_deployment_environment(
    root: str | Path, *, project_root: str | Path
) -> dict[str, object]:
    paths = DeploymentPaths.for_root(root)
    project = Path(project_root).resolve()
    evidence, _, _, source_hash_before = _verify_source_artifacts(paths)
    release_manifest = _create_release_manifest(project, paths)
    _write_json(paths.evidence / "release-manifest.json", release_manifest)
    release_id = str(release_manifest["source_release_id"])
    runtime_configuration = _write_runtime_configuration(paths, release_id)
    monitoring = _monitoring_plan()
    _write_json(paths.config / "monitoring-plan.json", monitoring)
    monitoring_configuration = _write_monitoring_configuration(paths)
    topology = _write_runtime_controls(paths, project, release_id=release_id)
    verification = verify_deployment_environment(paths.root, record_evidence=True)
    if verification["source_sha256"] != source_hash_before:
        raise RuntimeError("C4P hardening changed the controlled schema-v3 source.")
    evidence["tool_version"] = C4P_TOOL_VERSION
    evidence["c4p2_hardened_at"] = _now()
    evidence["release"] = release_manifest
    evidence["runtime_configuration"] = runtime_configuration
    evidence["runtime_topology"] = topology
    evidence["monitoring"] = monitoring
    evidence["monitoring_configuration"] = monitoring_configuration
    evidence["runtime_verification"] = verification
    evidence["engineering_preparation"] = {
        "normal_v4_runtime_selection": "COMPLETE_NOT_ACTIVATED",
        "startup_safety_checks": "COMPLETE",
        "deployment_control_hardening": "COMPLETE",
        "sanitized_evidence_generation": "COMPLETE",
        "local_traffic_rejection_and_drain": "COMPLETE_NOT_OPERATOR_APPROVED",
        "read_only_monitoring_collection": "COMPLETE_NOT_OPERATOR_APPROVED",
    }
    unresolved = cast(list[object], evidence.get("unresolved_operator_decisions", []))
    evidence["unresolved_operator_decisions"] = [
        decision for decision in unresolved if "normal schema-v4" not in str(decision).casefold()
    ]
    _write_json(paths.evidence / "deployment-preparation-evidence.json", evidence)
    return {
        "status": "hardened",
        "deployment_root": str(paths.root),
        "schema_version": verification["schema_version"],
        "source_sha256": verification["source_sha256"],
        "release_id": release_id,
        "storage_mode": RuntimeStorageMode.ORGANIZATION_V3.value,
        "v4_target_exists": False,
        "c4_executed": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatbook-c4p",
        description="Prepare or verify a controlled schema-v3 C4 staging environment.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("root", type=Path)
    prepare.add_argument("--project-root", type=Path, default=Path.cwd())
    verify = commands.add_parser("verify")
    verify.add_argument("root", type=Path)
    verify.add_argument("--record-evidence", action="store_true")
    harden = commands.add_parser("harden")
    harden.add_argument("root", type=Path)
    harden.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "prepare":
            result = prepare_deployment_environment(
                arguments.root, project_root=arguments.project_root
            )
            result_paths = cast(Mapping[str, object], result["paths"])
            result_source = cast(Mapping[str, object], result["source"])
            summary = {
                "status": "prepared",
                "deployment_root": result_paths["deployment_root"],
                "source_database": result_paths["source_database"],
                "schema_version": result_source["schema_version"],
                "source_sha256": result_source["sha256"],
                "c4_executed": False,
            }
        elif arguments.command == "harden":
            summary = harden_deployment_environment(
                arguments.root, project_root=arguments.project_root
            )
        else:
            summary = verify_deployment_environment(
                arguments.root, record_evidence=cast(bool, arguments.record_evidence)
            )
    except (ChatbookError, OSError, RuntimeError, sqlite3.Error) as exc:
        code = exc.code if isinstance(exc, ChatbookError) else type(exc).__name__
        print(json.dumps({"status": "failed", "error": code, "message": str(exc)}))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
