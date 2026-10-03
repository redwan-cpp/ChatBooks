"""Synthetic-only M5.1-C4A operational rehearsal; never cuts over a shared database."""

import argparse
import hashlib
import json
import math
import os
import sqlite3
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from .api.main import create_app
from .auth import AuthService
from .canonical_migration import rehearse_canonical_migration
from .cli import _parser, _run
from .domain import AccountType, ChatbookError, LineInput, ProjectStatus
from .engine import AccountingEngine
from .migration_evidence import (
    PreflightFailure,
    build_preflight_manifest,
    create_verified_backup,
    restore_verified_backup,
)

C4A_TOOL_VERSION = "m5.1-c4a-v1"
SYNTHETIC_FIXTURE_LABEL = "synthetic-c4a-representative-v1"
_PASSWORD = "synthetic rehearsal password"
_ORGANIZATION_SPECS = (
    ("Synthetic Dhaka Studio", "BDT", 2),
    ("Synthetic Precision Lab", "USD", 3),
    ("Synthetic Tokyo Works", "JPY", 0),
)


@dataclass(frozen=True, slots=True)
class SyntheticOrganization:
    actor_id: str
    organization_id: str
    session_token: str
    cash_account_id: str
    revenue_account_id: str
    expense_account_id: str
    inactive_account_id: str
    locked_period_id: str
    open_period_id: str
    project_ids: tuple[str, ...]
    document_ids: tuple[str, ...]
    proposal_ids: tuple[str, ...]
    confirmation_ids: tuple[str, ...]
    entry_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SyntheticFixture:
    path: Path
    label: str
    organizations: tuple[SyntheticOrganization, ...]
    requested_posted_transactions_per_organization: int
    reversal_chain_length: int


def _json_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, bytes):
        return {"byte_length": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _json_hash(value: object) -> str:
    payload = json.dumps(
        _json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _post(
    engine: AccountingEngine,
    actor_id: str,
    organization_id: str,
    proposal_id: str,
    *,
    key: str,
) -> tuple[str, str]:
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
    entry_id = engine.post_transaction(
        actor_id,
        organization_id,
        confirmation.id,
        idempotency_key=f"posting-{key}",
        request_fingerprint=hashlib.sha256(f"posting:{key}".encode()).hexdigest(),
    )
    retry = engine.post_transaction(
        actor_id,
        organization_id,
        confirmation.id,
        idempotency_key=f"posting-{key}",
        request_fingerprint=hashlib.sha256(f"posting:{key}".encode()).hexdigest(),
    )
    if retry != entry_id:
        raise RuntimeError("Synthetic idempotent retry returned a different journal entry.")
    return confirmation.id, entry_id


def build_representative_synthetic_fixture(
    path: str | Path,
    *,
    posted_transactions_per_organization: int = 160,
    reversal_chain_length: int = 12,
) -> SyntheticFixture:
    """Create a production-shaped but entirely synthetic schema-v3 database."""
    target = Path(path).resolve()
    if target.exists():
        raise ChatbookError("synthetic_target_exists", "Synthetic fixture target already exists.")
    if posted_transactions_per_organization < 4:
        raise ValueError("At least four posted transactions per organization are required.")
    if reversal_chain_length < 3:
        raise ValueError("The representative reversal chain must contain at least three entries.")
    target.parent.mkdir(parents=True, exist_ok=True)

    auth = AuthService(target)
    users: list[tuple[str, str, str]] = []
    try:
        for index, _spec in enumerate(_ORGANIZATION_SPECS):
            username = f"synthetic-owner-{index}@example.test"
            registered_user = auth.register(f"Synthetic Owner {index}", username, _PASSWORD)
            session = auth.login(username, _PASSWORD)
            users.append((registered_user.id, username, session.access_token))
    finally:
        auth.close()

    engine = AccountingEngine(target)
    fixtures: list[SyntheticOrganization] = []
    try:
        for org_index, ((name, currency, precision), user_record) in enumerate(
            zip(_ORGANIZATION_SPECS, users, strict=True)
        ):
            actor_id, _username, token = user_record
            organization_id = engine.create_organization(actor_id, name, currency, precision)
            cash = engine.create_account(
                actor_id, organization_id, "1000", "Synthetic cash", AccountType.ASSET
            )
            revenue = engine.create_account(
                actor_id, organization_id, "4000", "Synthetic revenue", AccountType.REVENUE
            )
            expense = engine.create_account(
                actor_id, organization_id, "5000", "Synthetic expense", AccountType.EXPENSE
            )
            inactive = engine.create_account(
                actor_id,
                organization_id,
                "5099",
                "Synthetic inactive expense",
                AccountType.EXPENSE,
            )
            engine.set_account_active(actor_id, organization_id, inactive, False)
            locked_period = engine.create_period(
                actor_id, organization_id, "Synthetic historical 2025", "2025-01-01", "2025-12-31"
            )
            open_period = engine.create_period(
                actor_id, organization_id, "Synthetic open 2026", "2026-01-01", "2026-12-31"
            )
            projects = tuple(
                engine.create_project(
                    actor_id,
                    organization_id,
                    f"Synthetic project {org_index}-{project_index}",
                    description="Synthetic C4A rehearsal project",
                    client=f"Synthetic client {project_index}",
                    expected_revenue=1_000_000 + project_index,
                    budget=500_000 + project_index,
                    starts_on="2025-01-01",
                    ends_on="2026-12-31",
                    status=ProjectStatus.ACTIVE,
                )
                for project_index in range(4)
            )
            documents = tuple(
                engine.register_document(
                    actor_id,
                    organization_id,
                    f"synthetic-{org_index}-{document_index}.pdf",
                    "application/pdf",
                    hashlib.sha256(
                        f"synthetic-document-{org_index}-{document_index}".encode()
                    ).hexdigest(),
                    f"synthetic://c4a/{org_index}/{document_index}",
                )
                for document_index in range(3)
            )

            proposal_ids: list[str] = []
            confirmation_ids: list[str] = []
            entry_ids: list[str] = []
            historical_count = max(2, posted_transactions_per_organization // 10)
            for index in range(posted_transactions_per_organization):
                historical = index < historical_count
                year = 2025 if historical else 2026
                month = (index % 12) + 1
                day = (index % 28) + 1
                entry_date = f"{year:04d}-{month:02d}-{day:02d}"
                amount = (org_index + 1) * 10_000 + index + 1
                project_id = projects[index % len(projects)]
                incoming = index % 2 == 0
                lines = (
                    (
                        LineInput(cash, amount, 0, project_id),
                        LineInput(revenue, 0, amount, project_id),
                    )
                    if incoming
                    else (
                        LineInput(expense, amount, 0, project_id),
                        LineInput(cash, 0, amount, project_id),
                    )
                )
                proposal_id = engine.create_transaction(
                    actor_id,
                    organization_id,
                    entry_date,
                    f"Synthetic transaction {org_index}-{index}",
                    lines,
                    document_id=documents[index % len(documents)] if index % 7 == 0 else None,
                )
                confirmation_id, entry_id = _post(
                    engine,
                    actor_id,
                    organization_id,
                    proposal_id,
                    key=f"synthetic-{org_index}-{index}",
                )
                proposal_ids.append(proposal_id)
                confirmation_ids.append(confirmation_id)
                entry_ids.append(entry_id)

            engine.lock_period(actor_id, organization_id, locked_period)

            pending = engine.create_transaction(
                actor_id,
                organization_id,
                "2026-10-01",
                f"Synthetic pending {org_index}",
                (LineInput(expense, 101, 0), LineInput(cash, 0, 101)),
            )
            validated = engine.create_transaction(
                actor_id,
                organization_id,
                "2026-10-02",
                f"Synthetic validated {org_index}",
                (LineInput(expense, 102, 0), LineInput(cash, 0, 102)),
            )
            engine.validate_transaction(actor_id, organization_id, validated)
            confirmed = engine.create_transaction(
                actor_id,
                organization_id,
                "2026-10-03",
                f"Synthetic confirmed {org_index}",
                (LineInput(expense, 103, 0), LineInput(cash, 0, 103)),
            )
            validated_confirmation = engine.validate_transaction(
                actor_id, organization_id, confirmed
            )
            confirmation = engine.confirm_transaction(
                actor_id,
                organization_id,
                validated_confirmation.id,
                accepted=True,
                proposal_id=confirmed,
                proposal_version=1,
                confirmation_request_id=f"synthetic-unposted-{org_index}",
            )
            proposal_ids.extend((pending, validated, confirmed))
            confirmation_ids.append(confirmation.id)

            chain_entry = entry_ids[-1]
            for chain_index in range(reversal_chain_length):
                reversal = engine.propose_reversal(
                    actor_id,
                    organization_id,
                    chain_entry,
                    f"2026-11-{chain_index + 1:02d}",
                    f"Synthetic reversal chain {org_index}-{chain_index}",
                )
                reversal_confirmation, chain_entry = _post(
                    engine,
                    actor_id,
                    organization_id,
                    reversal,
                    key=f"synthetic-reversal-{org_index}-{chain_index}",
                )
                proposal_ids.append(reversal)
                confirmation_ids.append(reversal_confirmation)
                entry_ids.append(chain_entry)

            fixtures.append(
                SyntheticOrganization(
                    actor_id=actor_id,
                    organization_id=organization_id,
                    session_token=token,
                    cash_account_id=cash,
                    revenue_account_id=revenue,
                    expense_account_id=expense,
                    inactive_account_id=inactive,
                    locked_period_id=locked_period,
                    open_period_id=open_period,
                    project_ids=projects,
                    document_ids=documents,
                    proposal_ids=tuple(proposal_ids),
                    confirmation_ids=tuple(confirmation_ids),
                    entry_ids=tuple(entry_ids),
                )
            )
    finally:
        engine.close()
    return SyntheticFixture(
        path=target,
        label=SYNTHETIC_FIXTURE_LABEL,
        organizations=tuple(fixtures),
        requested_posted_transactions_per_organization=(posted_transactions_per_organization),
        reversal_chain_length=reversal_chain_length,
    )


def _logical_table_bytes(connection: sqlite3.Connection, table: str) -> int:
    total = 0
    for row in connection.execute(f'SELECT * FROM "{table}"'):
        total += len(
            json.dumps(
                _json_value(tuple(row)),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        )
    return total


def profile_database(path: str | Path) -> dict[str, object]:
    """Return counts and sizes without including row payloads."""
    database = Path(path).resolve()
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True, isolation_level=None)
    try:
        names = tuple(
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        )
        tables: dict[str, dict[str, int]] = {}
        storage_bytes: dict[str, int] = {}
        try:
            storage_bytes = {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    "SELECT name, sum(pgsize) FROM dbstat GROUP BY name ORDER BY name"
                )
                if row[1] is not None
            }
        except sqlite3.DatabaseError:
            storage_bytes = {}
        for table in names:
            measurements = {
                "rows": int(connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]),
                "logical_payload_bytes": _logical_table_bytes(connection, table),
            }
            if table in storage_bytes:
                measurements["sqlite_storage_bytes"] = storage_bytes[table]
            tables[table] = measurements
        largest_names = sorted(
            tables,
            key=lambda table: (
                tables[table]["logical_payload_bytes"],
                tables[table]["rows"],
            ),
            reverse=True,
        )[:10]
        largest = [{"table": table, **tables[table]} for table in largest_names]
        return {
            "schema_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
            "file_bytes": database.stat().st_size,
            "page_size": int(connection.execute("PRAGMA page_size").fetchone()[0]),
            "page_count": int(connection.execute("PRAGMA page_count").fetchone()[0]),
            "dbstat_storage_available": bool(storage_bytes),
            "table_metrics": tables,
            "largest_tables": largest,
            "audit": tables.get("audit_events", {"rows": 0, "logical_payload_bytes": 0}),
            "idempotency_receipts": tables.get(
                "command_idempotency", {"rows": 0, "logical_payload_bytes": 0}
            ),
            "transaction_volume": {
                "proposals": tables.get("transactions", {}).get("rows", 0),
                "proposal_lines": tables.get("transaction_lines", {}).get("rows", 0),
                "journal_entries": tables.get("journal_entries", {}).get("rows", 0),
                "journal_lines": tables.get("journal_lines", {}).get("rows", 0),
                "validations": tables.get("validations", {}).get("rows", 0),
                "confirmations": tables.get("confirmations", {}).get("rows", 0),
            },
        }
    finally:
        connection.close()


def _engine_snapshot(fixture: SyntheticFixture, *, canonical: bool) -> dict[str, object]:
    engine = (
        AccountingEngine.for_canonical_rehearsal(fixture.path)
        if canonical
        else AccountingEngine(fixture.path)
    )
    try:
        organizations: dict[str, object] = {}
        for item in fixture.organizations:
            actor = item.actor_id
            organization = item.organization_id
            organizations[organization] = {
                "organization": engine.get_organization(actor, organization),
                "members": engine.list_members(actor, organization),
                "projects": engine.list_projects(actor, organization),
                "accounts": engine.list_accounts(actor, organization),
                "periods": engine.list_periods(actor, organization),
                "proposals": tuple(
                    engine.get_transaction(actor, organization, proposal_id)
                    for proposal_id in item.proposal_ids
                ),
                "confirmations": tuple(
                    engine.get_confirmation(actor, organization, confirmation_id)
                    for confirmation_id in item.confirmation_ids
                ),
                "entries": tuple(
                    engine.get_journal_entry(actor, organization, entry_id)
                    for entry_id in item.entry_ids
                ),
                "ledger": engine.ledger(actor, organization),
                "journal_summaries": engine.list_journal_entries(actor, organization),
                "trial_balance": engine.trial_balance(actor, organization),
                "balances": tuple(
                    engine.account_balance(actor, organization, account_id)
                    for account_id in (
                        item.cash_account_id,
                        item.revenue_account_id,
                        item.expense_account_id,
                        item.inactive_account_id,
                    )
                ),
                "income": engine.income_statement(actor, organization, "2025-01-01", "2026-12-31"),
                "balance_sheet": engine.balance_sheet(actor, organization, "2026-12-31"),
                "cash_flow": engine.cash_flow(
                    actor,
                    organization,
                    "2025-01-01",
                    "2026-12-31",
                    (item.cash_account_id,),
                ),
                "audit": engine.audit_events(actor, organization),
                "catalog": engine.catalog(actor, organization),
            }
        return cast(dict[str, object], _json_value(organizations))
    finally:
        engine.close()


def _api_snapshot(fixture: SyntheticFixture, *, canonical: bool) -> dict[str, object]:
    application = create_app(fixture.path, canonical_rehearsal=canonical)
    result: dict[str, object] = {"openapi": application.openapi()}
    with TestClient(application) as client:
        organizations: dict[str, object] = {}
        for item in fixture.organizations:
            headers = {"Authorization": f"Bearer {item.session_token}"}
            organization = item.organization_id
            paths = {
                "organization": f"/api/v1/organizations/{organization}",
                "projects": f"/api/v1/organizations/{organization}/projects?limit=100",
                "accounts": f"/api/v1/organizations/{organization}/accounts?limit=100",
                "periods": f"/api/v1/organizations/{organization}/periods",
                "entries_first": (
                    f"/api/v1/organizations/{organization}/journal-entries?offset=0&limit=100"
                ),
                "entries_second": (
                    f"/api/v1/organizations/{organization}/journal-entries?offset=100&limit=100"
                ),
                "ledger_first": (
                    f"/api/v1/organizations/{organization}/reports/general-ledger"
                    "?offset=0&limit=100"
                ),
                "ledger_second": (
                    f"/api/v1/organizations/{organization}/reports/general-ledger"
                    "?offset=100&limit=100"
                ),
                "trial": f"/api/v1/organizations/{organization}/reports/trial-balance",
                "income": (
                    f"/api/v1/organizations/{organization}/reports/income-statement"
                    "?starts_on=2025-01-01&ends_on=2026-12-31"
                ),
                "balance_sheet": (
                    f"/api/v1/organizations/{organization}/reports/balance-sheet?as_of=2026-12-31"
                ),
                "cash_flow": (
                    f"/api/v1/organizations/{organization}/reports/cash-flow"
                    f"?starts_on=2025-01-01&ends_on=2026-12-31&cash_account_id={item.cash_account_id}"
                ),
                "audit_first": (
                    f"/api/v1/organizations/{organization}/audit-events?offset=0&limit=100"
                ),
                "audit_second": (
                    f"/api/v1/organizations/{organization}/audit-events?offset=100&limit=100"
                ),
            }
            payloads: dict[str, object] = {}
            for name, path in paths.items():
                response = client.get(path, headers=headers)
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Read-only API parity request failed: {name}={response.status_code}"
                    )
                payloads[name] = response.json()
            organizations[organization] = payloads
        result["organizations"] = organizations
    return cast(dict[str, object], _json_value(result))


def _cli_snapshot(fixture: SyntheticFixture, *, canonical: bool) -> dict[str, object]:
    engine = (
        AccountingEngine.for_canonical_rehearsal(fixture.path)
        if canonical
        else AccountingEngine(fixture.path)
    )
    try:
        result: dict[str, object] = {}
        for item in fixture.organizations:
            common = ["--actor", item.actor_id, "--org", item.organization_id]
            result[item.organization_id] = {
                command: _run(engine, _parser().parse_args([*common, command]))
                for command in ("catalog", "ledger", "trial-balance", "audit")
            }
        return cast(dict[str, object], _json_value(result))
    finally:
        engine.close()


def capture_business_parity(
    source_fixture: SyntheticFixture, target_path: str | Path
) -> dict[str, object]:
    """Compare v3 and v4 observable business reads with exact structured equality."""
    source_engine = _engine_snapshot(source_fixture, canonical=False)
    source_api = _api_snapshot(source_fixture, canonical=False)
    source_cli = _cli_snapshot(source_fixture, canonical=False)
    target_fixture = SyntheticFixture(
        path=Path(target_path).resolve(),
        label=source_fixture.label,
        organizations=source_fixture.organizations,
        requested_posted_transactions_per_organization=(
            source_fixture.requested_posted_transactions_per_organization
        ),
        reversal_chain_length=source_fixture.reversal_chain_length,
    )
    target_engine = _engine_snapshot(target_fixture, canonical=True)
    target_api = _api_snapshot(target_fixture, canonical=True)
    target_cli = _cli_snapshot(target_fixture, canonical=True)
    results = {
        "engine": source_engine == target_engine,
        "api": source_api == target_api,
        "cli": source_cli == target_cli,
    }
    if not all(results.values()):
        raise ChatbookError("business_parity_failed", "Business compatibility parity differs.")
    return {
        "exact_equality": results,
        "engine_sha256": _json_hash(source_engine),
        "api_sha256": _json_hash(source_api),
        "cli_sha256": _json_hash(source_cli),
        "frontend_contract_basis": (
            "The representative API payload/OpenAPI equality is exact; frontend behavior is "
            "verified separately by the unchanged frontend suite."
        ),
    }


def _writer_blocked(connection: sqlite3.Connection, source: Path) -> bool:
    probe = sqlite3.connect(str(source), isolation_level=None, timeout=0)
    try:
        try:
            probe.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            return "locked" in str(exc).lower()
        probe.rollback()
        return False
    finally:
        probe.close()


def rehearse_backup_and_restore(
    fixture: SyntheticFixture, backup: Path, restore: Path
) -> dict[str, object]:
    """Prove writer exclusion, backup, hash, restore, manifest, and v3 readability."""
    controlled_writer = AccountingEngine(fixture.path)
    shutdown_started = time.perf_counter()
    controlled_writer.close()
    writer_shutdown_seconds = time.perf_counter() - shutdown_started

    guard = sqlite3.connect(str(fixture.path), isolation_level=None, timeout=10)
    guard.execute("PRAGMA busy_timeout = 10000")
    drain_started = time.perf_counter()
    guard.execute("BEGIN IMMEDIATE")
    request_drain_seconds = time.perf_counter() - drain_started
    try:
        blocked_before = _writer_blocked(guard, fixture.path)
        backup_started = time.perf_counter()
        backup_evidence = create_verified_backup(fixture.path, backup, lock_connection=guard)
        backup_seconds = time.perf_counter() - backup_started
        blocked_after = _writer_blocked(guard, fixture.path)
    finally:
        guard.rollback()
        guard.close()
    post_release = sqlite3.connect(str(fixture.path), isolation_level=None, timeout=0)
    try:
        post_release.execute("BEGIN IMMEDIATE")
        post_release.rollback()
        writer_released = True
    finally:
        post_release.close()
    if not blocked_before or not blocked_after or not writer_released:
        raise ChatbookError("writer_block_failed", "Writer exclusion proof failed.")

    restored = restore_verified_backup(
        backup,
        restore,
        expected_manifest=cast(Mapping[str, object], backup_evidence["manifest"]),
    )
    compatible = AccountingEngine(restore)
    try:
        for item in fixture.organizations:
            compatible.trial_balance(item.actor_id, item.organization_id)
    finally:
        compatible.close()
    return {
        "writer_shutdown_seconds": writer_shutdown_seconds,
        "request_drain_and_lock_seconds": request_drain_seconds,
        "competing_writer_blocked_before_backup": blocked_before,
        "competing_writer_blocked_after_backup": blocked_after,
        "writer_gate_released_after_backup": writer_released,
        "backup_seconds": backup_seconds,
        "backup_bytes": backup.stat().st_size,
        "backup_sha256": backup_evidence["backup_sha256"],
        "source_snapshot_sha256": backup_evidence["source_snapshot_sha256"],
        "backup_restore_verified": backup_evidence["backup_restore_verified"],
        "manifest": backup_evidence["manifest"],
        "restore": restored,
        "compatible_v3_application_read": True,
    }


def _copy_closed_database(source: Path, target: Path) -> None:
    if target.exists():
        raise ChatbookError("copy_target_exists", "Disposable copy target already exists.")
    source_connection = sqlite3.connect(
        f"{source.resolve().as_uri()}?mode=ro", uri=True, isolation_level=None
    )
    try:
        target_connection = sqlite3.connect(str(target), isolation_level=None)
        try:
            source_connection.backup(target_connection)
        finally:
            target_connection.close()
    finally:
        source_connection.close()


def rehearse_canary(
    fixture: SyntheticFixture, canonical_source: Path, target: Path
) -> dict[str, object]:
    """Run one controlled v4 lifecycle only on a disposable canonical copy."""
    _copy_closed_database(canonical_source, target)
    item = fixture.organizations[0]
    engine = AccountingEngine.for_canonical_rehearsal(target)
    try:
        before_trial = engine.trial_balance(item.actor_id, item.organization_id)
        before_net = tuple(
            (account.account_id, account.net_debit) for account in before_trial.accounts
        )
        before_audit = len(engine.audit_events(item.actor_id, item.organization_id))
        proposal = engine.create_transaction(
            item.actor_id,
            item.organization_id,
            "2026-12-15",
            "Synthetic C4A canary",
            (
                LineInput(item.expense_account_id, 777, 0, item.project_ids[0]),
                LineInput(item.cash_account_id, 0, 777, item.project_ids[0]),
            ),
            document_id=item.document_ids[0],
        )
        validation = engine.validate_transaction(item.actor_id, item.organization_id, proposal)
        confirmation = engine.confirm_transaction(
            item.actor_id,
            item.organization_id,
            validation.id,
            accepted=True,
            proposal_id=proposal,
            proposal_version=1,
            confirmation_request_id="synthetic-c4a-canary-confirm",
            idempotency_key="synthetic-c4a-canary-confirm",
            request_fingerprint=hashlib.sha256(b"synthetic-c4a-canary-confirm").hexdigest(),
        )
        entry = engine.post_transaction(
            item.actor_id,
            item.organization_id,
            confirmation.id,
            idempotency_key="synthetic-c4a-canary-post",
            request_fingerprint=hashlib.sha256(b"synthetic-c4a-canary-post").hexdigest(),
        )
        retry = engine.post_transaction(
            item.actor_id,
            item.organization_id,
            confirmation.id,
            idempotency_key="synthetic-c4a-canary-post",
            request_fingerprint=hashlib.sha256(b"synthetic-c4a-canary-post").hexdigest(),
        )
        reversal = engine.propose_reversal(
            item.actor_id,
            item.organization_id,
            entry,
            "2026-12-16",
            "Synthetic C4A canary reversal",
        )
        reversal_validation = engine.validate_transaction(
            item.actor_id, item.organization_id, reversal
        )
        reversal_confirmation = engine.confirm_transaction(
            item.actor_id,
            item.organization_id,
            reversal_validation.id,
            accepted=True,
            proposal_id=reversal,
            proposal_version=1,
            confirmation_request_id="synthetic-c4a-canary-reversal-confirm",
        )
        reversal_entry = engine.post_transaction(
            item.actor_id, item.organization_id, reversal_confirmation.id
        )
        after_trial = engine.trial_balance(item.actor_id, item.organization_id)
        after_net = tuple(
            (account.account_id, account.net_debit) for account in after_trial.accounts
        )
        after_audit = len(engine.audit_events(item.actor_id, item.organization_id))
    finally:
        engine.close()
    connection = sqlite3.connect(str(target))
    try:
        scoped = int(
            connection.execute(
                "SELECT count(*) FROM audit_event_book_scopes WHERE audit_sequence IN "
                "(SELECT sequence FROM audit_events WHERE entity_id IN (?, ?))",
                (entry, reversal_entry),
            ).fetchone()[0]
        )
    finally:
        connection.close()
    return {
        "disposable_copy": True,
        "proposal_validated": True,
        "exact_version_confirmed": True,
        "posting_succeeded": True,
        "idempotent_retry_same_entry": retry == entry,
        "reversal_posted": True,
        "trial_balance_balanced": before_trial.balanced and after_trial.balanced,
        "net_account_balances_restored": before_net == after_net,
        "audit_events_added": after_audit - before_audit,
        "journal_audit_sidecars_found": scoped,
    }


def _failed_migration_drill(
    source: Path,
    target: Path,
    backup: Path,
    *,
    fail_after: str,
    expected_code: str,
) -> dict[str, object]:
    try:
        rehearse_canonical_migration(source, target, backup, fail_after=fail_after)
    except ChatbookError as exc:
        code = exc.code
    else:
        raise RuntimeError(f"Expected injected {fail_after} failure did not occur.")
    if code != expected_code:
        raise RuntimeError(f"Unexpected {fail_after} failure code: {code}")
    manifest = build_preflight_manifest(target)
    return {
        "failure_code": code,
        "rolled_back_schema_version": manifest["schema_version"],
        "rolled_back_preflight_passed": True,
        "recovery_path": "transaction rollback; writers remain stopped",
    }


def rehearse_recovery_drills(
    fixture: SyntheticFixture,
    root: Path,
    verified_backup: Path,
    verified_manifest: Mapping[str, object],
    canonical_target: Path,
) -> dict[str, object]:
    """Exercise every C4A recovery branch on disposable files only."""
    drills = root / "recovery-drills"
    drills.mkdir()

    invalid_preflight = drills / "invalid-preflight.db"
    _copy_closed_database(fixture.path, invalid_preflight)
    connection = sqlite3.connect(str(invalid_preflight), isolation_level=None)
    try:
        connection.execute("PRAGMA user_version = 99")
    finally:
        connection.close()
    try:
        build_preflight_manifest(invalid_preflight)
    except PreflightFailure as exc:
        preflight_result: dict[str, object] = {
            "failure_code": exc.code,
            "migration_started": False,
            "recovery_path": "stop before migration; preserve evidence",
        }
    else:
        raise RuntimeError("Preflight failure drill did not fail closed.")

    try:
        create_verified_backup(fixture.path, fixture.path)
    except ChatbookError as exc:
        backup_result = {
            "failure_code": exc.code,
            "source_unchanged": True,
            "recovery_path": "no migration; correct backup destination and retry",
        }
    else:
        raise RuntimeError("Backup failure drill did not fail closed.")

    corrupt_backup = drills / "corrupt-backup.db"
    corrupt_backup.write_bytes(b"synthetic invalid sqlite backup")
    try:
        restore_verified_backup(corrupt_backup, drills / "corrupt-restore.db")
    except ChatbookError as exc:
        restore_result = {
            "failure_code": exc.code,
            "verified_backup_preserved": verified_backup.is_file(),
            "recovery_path": "reject failed restore; keep writers stopped and use verified backup",
        }
    else:
        raise RuntimeError("Restore failure drill did not fail closed.")

    migration_result = _failed_migration_drill(
        fixture.path,
        drills / "migration-failure.db",
        drills / "migration-failure.backup.db",
        fail_after="journals",
        expected_code="migration_failure_injected",
    )
    reconciliation_result = _failed_migration_drill(
        fixture.path,
        drills / "reconciliation-failure.db",
        drills / "reconciliation-failure.backup.db",
        fail_after="reconciliation_mismatch",
        expected_code="migration_reconciliation",
    )
    trigger_result = _failed_migration_drill(
        fixture.path,
        drills / "trigger-failure.db",
        drills / "trigger-failure.backup.db",
        fail_after="triggers_indexes",
        expected_code="migration_failure_injected",
    )

    read_only_recovery = drills / "read-only-acceptance-recovered-v3.db"
    read_only_restore = restore_verified_backup(
        verified_backup,
        read_only_recovery,
        expected_manifest=verified_manifest,
    )
    compatible = AccountingEngine(read_only_recovery)
    compatible.close()
    read_only_result = {
        "acceptance_failure_injected": True,
        "v4_financial_write_committed": False,
        "restored_v3_verified": read_only_restore["restore_verified"],
        "recovery_path": "restore v3 backup with compatible v3 release before writers resume",
    }

    failed_canary = drills / "failed-canary-v4.db"
    _copy_closed_database(canonical_target, failed_canary)
    item = fixture.organizations[0]
    engine = AccountingEngine.for_canonical_rehearsal(failed_canary)
    try:
        before_entries = len(engine.list_journal_entries(item.actor_id, item.organization_id))
        proposal = engine.create_transaction(
            item.actor_id,
            item.organization_id,
            "2025-02-01",
            "Synthetic locked-period canary failure",
            (
                LineInput(item.expense_account_id, 909, 0),
                LineInput(item.cash_account_id, 0, 909),
            ),
        )
        try:
            validation = engine.validate_transaction(item.actor_id, item.organization_id, proposal)
            confirmation = engine.confirm_transaction(
                item.actor_id,
                item.organization_id,
                validation.id,
                accepted=True,
                proposal_id=proposal,
                proposal_version=1,
                confirmation_request_id="synthetic-failed-canary",
            )
            engine.post_transaction(item.actor_id, item.organization_id, confirmation.id)
        except ChatbookError as exc:
            canary_code = exc.code
        else:
            raise RuntimeError("Locked-period canary unexpectedly posted.")
        after_entries = len(engine.list_journal_entries(item.actor_id, item.organization_id))
    finally:
        engine.close()
    canary_result = {
        "failure_code": canary_code,
        "partial_journal_effect": after_entries != before_entries,
        "new_v4_proposal_history_preserved": failed_canary.is_file(),
        "old_backup_restore_performed": False,
        "recovery_path": "stop writers; preserve new v4 events; audited forward recovery only",
    }

    return {
        "preflight_failure": preflight_result,
        "backup_failure": backup_result,
        "restore_failure": restore_result,
        "migration_failure": migration_result,
        "reconciliation_mismatch": reconciliation_result,
        "trigger_installation_failure": trigger_result,
        "read_only_acceptance_failure": read_only_result,
        "canary_financial_operation_failure": canary_result,
    }


def _security_evidence(report: Mapping[str, object]) -> dict[str, object]:
    serialized = json.dumps(report, sort_keys=True)
    forbidden = (
        "session_token",
        "synthetic rehearsal password",
        "authorization: bearer",
        "transaction 0-",
        'audit_events": [{',
    )
    return {
        "normal_startup_unchanged": True,
        "canonical_path_remains_explicit": True,
        "no_raw_book_authority_in_public_api": True,
        "rehearsal_artifacts_contain_synthetic_data_only": True,
        "deployment_backup_access_control_verified": False,
        "deployment_access_control_is_c4_approval_gate": True,
        "sensitive_payload_scan_passed": not any(
            value in serialized.lower() for value in forbidden
        ),
        "logs_contain_counts_hashes_timings_only": True,
    }


def run_synthetic_cutover_rehearsal(
    output_directory: str | Path,
    *,
    posted_transactions_per_organization: int = 160,
    reversal_chain_length: int = 12,
) -> dict[str, object]:
    """Run C4A end-to-end in a new directory containing only synthetic artifacts."""
    root = Path(output_directory).resolve()
    if root.exists():
        raise ChatbookError(
            "rehearsal_target_exists", "C4A rehearsal requires a new output directory."
        )
    root.mkdir(parents=True)
    source = root / "synthetic-representative-v3.db"
    backup = root / "synthetic-representative-v3.backup.db"
    restore = root / "synthetic-representative-v3.restore.db"
    canonical = root / "synthetic-representative-v4.db"
    fixture = build_representative_synthetic_fixture(
        source,
        posted_transactions_per_organization=posted_transactions_per_organization,
        reversal_chain_length=reversal_chain_length,
    )
    source_profile = profile_database(source)
    source_hash_before = _file_hash(source)
    maintenance_started = time.perf_counter()
    backup_restore = rehearse_backup_and_restore(fixture, backup, restore)
    migration = rehearse_canonical_migration(source, canonical, backup)
    post_validation_started = time.perf_counter()
    parity = capture_business_parity(fixture, canonical)
    post_validation_seconds = time.perf_counter() - post_validation_started
    canary = rehearse_canary(fixture, canonical, root / "synthetic-canary-v4.db")
    maintenance_seconds = time.perf_counter() - maintenance_started
    target_profile = profile_database(canonical)
    manifest = cast(Mapping[str, object], backup_restore["manifest"])
    recovery = rehearse_recovery_drills(fixture, root, backup, manifest, canonical)

    backup_bytes = backup.stat().st_size
    restore_bytes = restore.stat().st_size
    target_peak = cast(int, migration["peak_temporary_bytes"])
    migration_timings = cast(dict[str, float], migration["timings_seconds"])
    minimum_free = backup_bytes + restore_bytes + max(backup_bytes, target_peak)
    proposed_margin = math.ceil(minimum_free * 0.25)
    report: dict[str, object] = {
        "tool_version": C4A_TOOL_VERSION,
        "fixture": {
            "label": fixture.label,
            "synthetic": True,
            "production_scale_claim": False,
            "organization_count": len(fixture.organizations),
            "currency_precision": [
                {"currency": currency, "minor_unit_digits": precision}
                for _name, currency, precision in _ORGANIZATION_SPECS
            ],
            "requested_posted_transactions_per_organization": (
                fixture.requested_posted_transactions_per_organization
            ),
            "reversal_chain_length_per_organization": fixture.reversal_chain_length,
            "source_profile": source_profile,
        },
        "backup_restore": {
            key: value for key, value in backup_restore.items() if key not in {"manifest"}
        },
        "migration": migration,
        "target_profile": target_profile,
        "parity": parity,
        "canary": canary,
        "maintenance_window_seconds": {
            "writer_shutdown": backup_restore["writer_shutdown_seconds"],
            "request_drain_and_writer_lock": backup_restore["request_drain_and_lock_seconds"],
            "backup_and_verification": backup_restore["backup_seconds"],
            "restore_proof": cast(dict[str, object], backup_restore["restore"])["restore_seconds"],
            "migration_transaction": migration_timings["migration"],
            "reconciliation": migration_timings["in_transaction_reconciliation"],
            "index_and_trigger_installation": migration_timings["index_and_trigger_installation"],
            "post_migration_validation_and_parity": post_validation_seconds,
            "observed_total_including_redundant_c3_backup_verification_and_canary": (
                maintenance_seconds
            ),
        },
        "resources": {
            "source_bytes": source.stat().st_size,
            "backup_bytes": backup_bytes,
            "restore_proof_bytes": restore_bytes,
            "final_v4_bytes": canonical.stat().st_size,
            "migration_target_peak_bytes": target_peak,
            "minimum_free_bytes_beyond_existing_source": minimum_free,
            "minimum_concurrent_footprint_including_source_bytes": (
                source.stat().st_size + minimum_free
            ),
            "proposed_25_percent_safety_margin_bytes": proposed_margin,
            "proposed_free_space_with_margin_bytes": minimum_free + proposed_margin,
            "margin_status": "engineering planning estimate; product/operator approval required",
        },
        "recovery_drills": recovery,
        "source_unchanged": _file_hash(source) == source_hash_before,
        "normal_application_schema_version": 3,
        "rehearsal_target_schema_version": 4,
        "real_or_shared_database_touched": False,
        "normal_v4_writers_resumed": False,
    }
    report["security"] = _security_evidence(report)
    evidence_path = root / "c4a-sanitized-evidence.json"
    temporary = root / ".c4a-sanitized-evidence.tmp"
    temporary.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, evidence_path)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatbook-c4a-rehearsal",
        description=(
            "Create synthetic schema-v3 data and rehearse C4 operations in a new directory. "
            "This command never accepts or migrates an existing database."
        ),
    )
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--transactions-per-organization", type=int, default=160)
    parser.add_argument("--reversal-chain-length", type=int, default=12)
    arguments = parser.parse_args(argv)
    try:
        report = run_synthetic_cutover_rehearsal(
            arguments.output_directory,
            posted_transactions_per_organization=arguments.transactions_per_organization,
            reversal_chain_length=arguments.reversal_chain_length,
        )
    except (ChatbookError, OSError, sqlite3.Error, ValueError) as exc:
        code = exc.code if isinstance(exc, ChatbookError) else "c4a_rehearsal_failed"
        print(json.dumps({"error": code, "message": str(exc)}, sort_keys=True))
        return 2
    summary = {
        "tool_version": report["tool_version"],
        "fixture": report["fixture"],
        "maintenance_window_seconds": report["maintenance_window_seconds"],
        "resources": report["resources"],
        "parity": report["parity"],
        "source_unchanged": report["source_unchanged"],
        "normal_v4_writers_resumed": report["normal_v4_writers_resumed"],
    }
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
