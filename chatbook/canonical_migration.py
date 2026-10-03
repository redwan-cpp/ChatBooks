"""Controlled v3-to-v4 migration rehearsal for disposable SQLite copies only."""

import argparse
import hashlib
import json
import os
import sqlite3
import time
from collections.abc import Iterable, Sequence
from importlib.resources import files
from pathlib import Path
from typing import Any
from uuid import uuid4

from .canonical_schema import (
    CANONICAL_SCHEMA_VERSION,
    install_canonical_schema_protections,
    verify_canonical_mapping,
)
from .domain import MAX_AMOUNT, ChatbookError
from .migration_evidence import build_preflight_manifest, create_verified_backup, table_evidence

C3_MIGRATION_VERSION = "m5.1-c3-v1"
FAILURE_STAGES = (
    "books",
    "charts_accounts",
    "periods",
    "proposals",
    "validations_confirmations",
    "journals",
    "extensions",
    "audit_sidecar",
    "reconciliation_mismatch",
    "before_swap",
    "triggers_indexes",
    "before_version_commit",
)

FINANCIAL_TABLES = (
    "charts_of_accounts",
    "accounts",
    "accounting_periods",
    "transactions",
    "transaction_lines",
    "validations",
    "confirmations",
    "confirmation_provenance",
    "command_idempotency",
    "journal_entries",
    "journal_lines",
)

EXTENSION_TABLES = (
    "business_proposal_documents",
    "business_proposal_line_projects",
    "business_journal_line_projects",
    "audit_event_book_scopes",
)

AUDITED_FINANCIAL_ENTITY_TYPES = (
    "charts_of_accounts",
    "accounts",
    "accounting_periods",
    "transactions",
    "transaction_lines",
    "validations",
    "confirmations",
    "journal_entries",
    "journal_lines",
)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sqlite_footprint(path: Path) -> int:
    return sum(
        candidate.stat().st_size
        for candidate in (path, Path(f"{path}-journal"), Path(f"{path}-wal"), Path(f"{path}-shm"))
        if candidate.exists()
    )


def _canonical_hash(rows: Iterable[Sequence[object]]) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    for row in rows:
        digest.update(
            json.dumps(
                list(row), sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        )
        digest.update(b"\n")
        count += 1
    return count, digest.hexdigest()


def _projection_sql(table: str, *, prefix: str = "") -> str:
    name = f"{prefix}{table}"
    projections = {
        "charts_of_accounts": (
            f"SELECT t.id, b.organization_id, t.name FROM {name} t "
            "JOIN ledger_books b ON b.id = t.ledger_book_id ORDER BY t.id"
        ),
        "accounts": (
            f"SELECT t.id, b.organization_id, t.chart_id, t.code, t.name, t.account_type, "
            f"t.active FROM {name} t JOIN ledger_books b ON b.id = t.ledger_book_id ORDER BY t.id"
        ),
        "accounting_periods": (
            f"SELECT t.id, b.organization_id, t.name, t.starts_on, t.ends_on, t.locked "
            f"FROM {name} t JOIN ledger_books b ON b.id = t.ledger_book_id ORDER BY t.id"
        ),
        "transactions": (
            f"SELECT t.id, b.organization_id, t.entry_date, t.description, x.document_id, "
            f"t.reverses_entry_id, t.version, t.state FROM {name} t "
            f"JOIN ledger_books b ON b.id = t.ledger_book_id "
            f"JOIN {prefix}business_proposal_documents x ON x.proposal_id = t.id "
            "AND x.ledger_book_id = t.ledger_book_id ORDER BY t.id"
        ),
        "transaction_lines": (
            f"SELECT t.id, b.organization_id, t.transaction_id, t.position, t.account_id, "
            f"t.debit, t.credit, x.project_id FROM {name} t "
            f"JOIN ledger_books b ON b.id = t.ledger_book_id "
            f"JOIN {prefix}business_proposal_line_projects x ON x.line_id = t.id "
            "AND x.ledger_book_id = t.ledger_book_id ORDER BY t.id"
        ),
        "validations": (
            f"SELECT t.id, b.organization_id, t.transaction_id, t.fingerprint, t.actor_id "
            f"FROM {name} t JOIN ledger_books b ON b.id = t.ledger_book_id ORDER BY t.id"
        ),
        "confirmations": (
            f"SELECT t.id, b.organization_id, t.validation_id, t.actor_id "
            f"FROM {name} t JOIN ledger_books b ON b.id = t.ledger_book_id ORDER BY t.id"
        ),
        "confirmation_provenance": (
            f"SELECT t.confirmation_id, b.organization_id, t.proposal_id, t.proposal_version, "
            f"t.confirmed_at, t.confirmation_request_id FROM {name} t "
            "JOIN ledger_books b ON b.id = t.ledger_book_id ORDER BY t.confirmation_id"
        ),
        "command_idempotency": (
            f"SELECT t.id, b.organization_id, t.actor_id, t.operation, t.idempotency_key, "
            f"t.request_fingerprint, t.resource_type, t.resource_id, t.created_at FROM {name} t "
            "JOIN ledger_books b ON b.id = t.ledger_book_id ORDER BY t.id"
        ),
        "journal_entries": (
            f"SELECT t.id, b.organization_id, t.transaction_id, t.confirmation_id, t.period_id, "
            f"t.entry_date, t.description, t.reverses_entry_id, t.state FROM {name} t "
            "JOIN ledger_books b ON b.id = t.ledger_book_id ORDER BY t.id"
        ),
        "journal_lines": (
            f"SELECT t.id, b.organization_id, t.entry_id, t.position, t.account_id, t.debit, "
            f"t.credit, x.project_id FROM {name} t "
            f"JOIN ledger_books b ON b.id = t.ledger_book_id "
            f"JOIN {prefix}business_journal_line_projects x ON x.line_id = t.id "
            "AND x.ledger_book_id = t.ledger_book_id ORDER BY t.id"
        ),
    }
    return projections[table]


def _legacy_sql(table: str) -> str:
    primary = "confirmation_id" if table == "confirmation_provenance" else "id"
    return f"SELECT * FROM {table} ORDER BY {primary}"


def _financial_projection_evidence(
    connection: sqlite3.Connection, *, prefix: str | None
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for table in FINANCIAL_TABLES:
        sql = _legacy_sql(table) if prefix is None else _projection_sql(table, prefix=prefix)
        count, sha256 = _canonical_hash(connection.execute(sql))
        result[table] = {"row_count": count, "sha256": sha256}
    return result


def _execute_resource(connection: sqlite3.Connection, resource: str) -> None:
    script = files("chatbook").joinpath(*resource.split("/")).read_text(encoding="utf-8")
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ""
    if statement.strip():
        raise sqlite3.DatabaseError("Incomplete migration resource")


def _copy_database(source: Path, target: Path) -> None:
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


def _maybe_fail(stage: str, fail_after: str | None) -> None:
    if fail_after == stage:
        raise ChatbookError("migration_failure_injected", f"Injected failure after {stage}.")


def _inject_reconciliation_mismatch(connection: sqlite3.Connection) -> None:
    cursor = connection.execute(
        "UPDATE v4_transaction_lines "
        "SET debit = CASE WHEN debit < ? THEN debit + 1 ELSE debit - 1 END "
        "WHERE id = (SELECT id FROM v4_transaction_lines WHERE debit > 0 "
        "ORDER BY CASE WHEN debit < ? THEN 0 ELSE 1 END, debit, transaction_id, position, id "
        "LIMIT 1)",
        (MAX_AMOUNT, MAX_AMOUNT),
    )
    if cursor.rowcount != 1:
        raise ChatbookError(
            "migration_reconciliation",
            "Reconciliation failure injection requires a positive debit line.",
        )


def _drop_v3_financial_triggers(connection: sqlite3.Connection) -> None:
    placeholders = ",".join("?" for _ in FINANCIAL_TABLES)
    names = tuple(
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' "
            f"AND tbl_name IN ({placeholders})",
            FINANCIAL_TABLES,
        )
    )
    for name in names:
        if not name.replace("_", "").isalnum():
            raise sqlite3.DatabaseError("Unsafe trigger name")
        connection.execute(f'DROP TRIGGER "{name}"')


def _copy_rows(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO v4_charts_of_accounts "
        "SELECT c.id, b.id, c.name FROM charts_of_accounts c "
        "JOIN ledger_books b ON b.organization_id = c.organization_id"
    )
    connection.execute(
        "INSERT INTO v4_accounts "
        "SELECT a.id, b.id, a.chart_id, a.code, a.name, a.account_type, a.active "
        "FROM accounts a JOIN ledger_books b ON b.organization_id = a.organization_id"
    )


def _swap_tables(connection: sqlite3.Connection) -> None:
    for table in FINANCIAL_TABLES:
        connection.execute(f"ALTER TABLE {table} RENAME TO v3_{table}")
    for table in FINANCIAL_TABLES + EXTENSION_TABLES:
        connection.execute(f"ALTER TABLE v4_{table} RENAME TO {table}")
    for table in reversed(FINANCIAL_TABLES):
        connection.execute(f"DROP TABLE v3_{table}")


def _query_plan_evidence(connection: sqlite3.Connection) -> dict[str, list[str]]:
    samples = {
        "ledger_by_date": (
            "SELECT id FROM journal_entries WHERE ledger_book_id = ? AND state = 'posted' "
            "AND entry_date <= ? ORDER BY entry_date",
            ("book:query-plan", "9999-12-31"),
        ),
        "ledger_by_account": (
            "SELECT id FROM journal_lines WHERE ledger_book_id = ? AND account_id = ?",
            ("book:query-plan", "account:query-plan"),
        ),
        "idempotency": (
            "SELECT resource_id FROM command_idempotency WHERE ledger_book_id = ? "
            "AND actor_id = ? AND operation = ? AND idempotency_key = ?",
            ("book:query-plan", "actor:query-plan", "transaction.post", "query-plan-key"),
        ),
    }
    return {
        name: [str(row[3]) for row in connection.execute(f"EXPLAIN QUERY PLAN {sql}", params)]
        for name, (sql, params) in samples.items()
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def rehearse_canonical_migration(
    source_path: str | Path,
    target_path: str | Path,
    backup_path: str | Path,
    *,
    fail_after: str | None = None,
) -> dict[str, Any]:
    """Migrate a verified v3 snapshot into a separate v4 rehearsal database."""
    source = Path(source_path).resolve()
    target = Path(target_path).resolve()
    backup = Path(backup_path).resolve()
    report_path = Path(f"{target}.c3-report.json")
    if fail_after is not None and fail_after not in FAILURE_STAGES:
        raise ValueError(f"Unknown failure stage: {fail_after}")
    if len({source, target, backup}) != 3:
        raise ChatbookError(
            "migration_path_invalid", "Source, backup, and rehearsal target must be distinct."
        )
    if target.exists():
        raise ChatbookError(
            "migration_target_exists", "The disposable rehearsal target must not already exist."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}
    started = time.perf_counter()
    report: dict[str, Any] = {
        "tool_version": C3_MIGRATION_VERSION,
        "source_identity": hashlib.sha256(str(source).encode()).hexdigest(),
        "target_identity": hashlib.sha256(str(target).encode()).hexdigest(),
        "status": "failed",
        "failure_stage": None,
        "schema_from": None,
        "schema_to": CANONICAL_SCHEMA_VERSION,
        "timings_seconds": timings,
    }
    source_hash_before = _hash_file(source) if source.is_file() else None
    peak_temporary_bytes = 0
    connection: sqlite3.Connection | None = None
    current_stage = "preflight"
    try:
        before = time.perf_counter()
        preflight = build_preflight_manifest(source)
        timings["preflight"] = time.perf_counter() - before
        if preflight.get("schema_version") != 3:
            raise ChatbookError("schema_version", "C3 rehearsal requires a schema-v3 source.")
        report["schema_from"] = 3
        report["preflight_content_fingerprint"] = preflight["content_fingerprint"]
        report["preflight_report_fingerprints"] = preflight["report_fingerprints"]

        before = time.perf_counter()
        backup_evidence = create_verified_backup(source, backup)
        timings["backup_and_verification"] = time.perf_counter() - before
        if not backup_evidence.get("backup_restore_verified"):
            raise ChatbookError(
                "migration_backup_unverified", "Verified backup evidence is required."
            )
        report["backup_restore_verified"] = True
        report["backup_sha256"] = backup_evidence["backup_sha256"]

        before = time.perf_counter()
        _copy_database(backup, target)
        peak_temporary_bytes = max(peak_temporary_bytes, _sqlite_footprint(target))
        timings["restore_target"] = time.perf_counter() - before
        restored = build_preflight_manifest(
            target,
            expected_manifest=backup_evidence["manifest"],  # type: ignore[arg-type]
        )
        report["restored_content_fingerprint"] = restored["content_fingerprint"]

        connection = sqlite3.connect(str(target), isolation_level=None, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = OFF")
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version != 3:
            raise ChatbookError("schema_version", "Restored rehearsal target is not schema v3.")
        legacy_projection = _financial_projection_evidence(connection, prefix=None)

        migration_started = time.perf_counter()
        connection.execute("BEGIN IMMEDIATE")
        _drop_v3_financial_triggers(connection)
        _execute_resource(connection, "migrations/0004_canonical_book_tables.sql")

        current_stage = "books"
        mismatch = int(
            connection.execute(
                "SELECT count(*) FROM organizations o LEFT JOIN ledger_books b "
                "ON b.organization_id = o.id WHERE b.id IS NULL OR b.owner_kind != 'BUSINESS' "
                "OR b.currency != o.currency OR b.minor_unit_digits != o.minor_unit_digits"
            ).fetchone()[0]
        )
        if mismatch:
            raise ChatbookError("migration_reconciliation", "LedgerBook ownership is invalid.")
        _maybe_fail(current_stage, fail_after)

        current_stage = "charts_accounts"
        _copy_rows(connection)
        _maybe_fail(current_stage, fail_after)

        current_stage = "periods"
        connection.execute(
            "INSERT INTO v4_accounting_periods "
            "SELECT p.id, b.id, p.name, p.starts_on, p.ends_on, p.locked "
            "FROM accounting_periods p JOIN ledger_books b "
            "ON b.organization_id = p.organization_id"
        )
        _maybe_fail(current_stage, fail_after)

        current_stage = "proposals"
        connection.execute(
            "INSERT INTO v4_transactions "
            "SELECT t.id, b.id, t.entry_date, t.description, t.reverses_entry_id, "
            "t.version, t.state FROM transactions t JOIN ledger_books b "
            "ON b.organization_id = t.organization_id"
        )
        connection.execute(
            "INSERT INTO v4_transaction_lines "
            "SELECT l.id, b.id, l.transaction_id, l.position, l.account_id, l.debit, l.credit "
            "FROM transaction_lines l JOIN ledger_books b ON b.organization_id = l.organization_id"
        )
        _maybe_fail(current_stage, fail_after)

        current_stage = "validations_confirmations"
        connection.execute(
            "INSERT INTO v4_validations "
            "SELECT v.id, b.id, v.transaction_id, v.fingerprint, 'organization-v1', v.actor_id "
            "FROM validations v JOIN ledger_books b ON b.organization_id = v.organization_id"
        )
        connection.execute(
            "INSERT INTO v4_confirmations "
            "SELECT c.id, b.id, c.validation_id, c.actor_id FROM confirmations c "
            "JOIN ledger_books b ON b.organization_id = c.organization_id"
        )
        connection.execute(
            "INSERT INTO v4_confirmation_provenance "
            "SELECT p.confirmation_id, b.id, p.proposal_id, p.proposal_version, "
            "p.confirmed_at, p.confirmation_request_id FROM confirmation_provenance p "
            "JOIN ledger_books b ON b.organization_id = p.organization_id"
        )
        connection.execute(
            "INSERT INTO v4_command_idempotency "
            "SELECT r.id, b.id, r.actor_id, r.operation, r.idempotency_key, "
            "r.request_fingerprint, r.resource_type, r.resource_id, r.created_at "
            "FROM command_idempotency r JOIN ledger_books b "
            "ON b.organization_id = r.organization_id"
        )
        _maybe_fail(current_stage, fail_after)

        current_stage = "journals"
        connection.execute(
            "INSERT INTO v4_journal_entries "
            "SELECT e.id, b.id, e.transaction_id, e.confirmation_id, e.period_id, "
            "e.entry_date, e.description, e.reverses_entry_id, e.state "
            "FROM journal_entries e JOIN ledger_books b ON b.organization_id = e.organization_id"
        )
        connection.execute(
            "INSERT INTO v4_journal_lines "
            "SELECT l.id, b.id, l.entry_id, l.position, l.account_id, l.debit, l.credit "
            "FROM journal_lines l JOIN ledger_books b ON b.organization_id = l.organization_id"
        )
        _maybe_fail(current_stage, fail_after)

        current_stage = "extensions"
        connection.execute(
            "INSERT INTO v4_business_proposal_documents "
            "SELECT t.id, b.id, t.organization_id, t.document_id FROM transactions t "
            "JOIN ledger_books b ON b.organization_id = t.organization_id"
        )
        connection.execute(
            "INSERT INTO v4_business_proposal_line_projects "
            "SELECT l.id, b.id, l.organization_id, l.project_id FROM transaction_lines l "
            "JOIN ledger_books b ON b.organization_id = l.organization_id"
        )
        connection.execute(
            "INSERT INTO v4_business_journal_line_projects "
            "SELECT l.id, b.id, l.organization_id, l.project_id FROM journal_lines l "
            "JOIN ledger_books b ON b.organization_id = l.organization_id"
        )
        _maybe_fail(current_stage, fail_after)

        current_stage = "audit_sidecar"
        placeholders = ",".join("?" for _ in AUDITED_FINANCIAL_ENTITY_TYPES)
        connection.execute(
            "INSERT INTO v4_audit_event_book_scopes (audit_sequence, ledger_book_id) "
            "SELECT a.sequence, b.id FROM audit_events a JOIN ledger_books b "
            "ON b.organization_id = a.organization_id "
            f"WHERE a.entity_type IN ({placeholders})",
            AUDITED_FINANCIAL_ENTITY_TYPES,
        )
        _maybe_fail(current_stage, fail_after)

        current_stage = "reconciliation_mismatch"
        if fail_after == current_stage:
            _inject_reconciliation_mismatch(connection)
        reconciliation_started = time.perf_counter()
        reconstructed = _financial_projection_evidence(connection, prefix="v4_")
        if reconstructed != legacy_projection:
            raise ChatbookError(
                "migration_reconciliation", "Canonical financial projection differs from v3."
            )
        report["financial_projection"] = reconstructed
        peak_temporary_bytes = max(peak_temporary_bytes, _sqlite_footprint(target))
        report["audit_events"] = table_evidence(connection, "audit_events")
        report["audit_sequence"] = [
            list(row)
            for row in connection.execute("SELECT name, seq FROM sqlite_sequence ORDER BY name")
        ]
        timings["in_transaction_reconciliation"] = time.perf_counter() - reconciliation_started

        current_stage = "before_swap"
        _maybe_fail(current_stage, fail_after)
        swap_started = time.perf_counter()
        _swap_tables(connection)
        timings["table_swap"] = time.perf_counter() - swap_started

        current_stage = "triggers_indexes"
        index_started = time.perf_counter()
        install_canonical_schema_protections(connection)
        peak_temporary_bytes = max(peak_temporary_bytes, _sqlite_footprint(target))
        timings["index_and_trigger_installation"] = time.perf_counter() - index_started
        _maybe_fail(current_stage, fail_after)

        post_install_started = time.perf_counter()
        violations = tuple(connection.execute("PRAGMA foreign_key_check"))
        if violations:
            raise ChatbookError(
                "migration_reconciliation", "Canonical foreign-key validation failed."
            )
        integrity = tuple(str(row[0]) for row in connection.execute("PRAGMA integrity_check"))
        if integrity != ("ok",):
            raise ChatbookError("migration_reconciliation", "SQLite integrity validation failed.")
        final_projection = _financial_projection_evidence(connection, prefix="")
        if final_projection != legacy_projection:
            raise ChatbookError(
                "migration_reconciliation", "Final canonical projection differs from v3."
            )
        timings["post_install_validation"] = time.perf_counter() - post_install_started

        current_stage = "before_version_commit"
        _maybe_fail(current_stage, fail_after)
        connection.execute(f"PRAGMA user_version = {CANONICAL_SCHEMA_VERSION}")
        connection.commit()
        connection.execute("PRAGMA foreign_keys = ON")
        verify_canonical_mapping(connection)
        timings["migration"] = time.perf_counter() - migration_started
        report["query_plans"] = _query_plan_evidence(connection)
        report["foreign_key_violation_count"] = len(
            tuple(connection.execute("PRAGMA foreign_key_check"))
        )
        report["integrity_check"] = [
            str(row[0]) for row in connection.execute("PRAGMA integrity_check")
        ]
        report["status"] = "complete"
        report["schema_version"] = int(connection.execute("PRAGMA user_version").fetchone()[0])
        report["target_sha256"] = _hash_file(target)
        report["target_bytes"] = target.stat().st_size
        report["backup_bytes"] = backup.stat().st_size
        report["source_bytes"] = source.stat().st_size
        report["peak_temporary_bytes"] = max(peak_temporary_bytes, _sqlite_footprint(target))
        report["source_unchanged"] = _hash_file(source) == source_hash_before
        return report
    except Exception as exc:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        report["failure_stage"] = current_stage
        report["error_code"] = exc.code if isinstance(exc, ChatbookError) else type(exc).__name__
        report["source_unchanged"] = (
            source.is_file()
            and source_hash_before is not None
            and _hash_file(source) == source_hash_before
        )
        if target.is_file():
            check = sqlite3.connect(str(target), isolation_level=None)
            try:
                report["rolled_back_schema_version"] = int(
                    check.execute("PRAGMA user_version").fetchone()[0]
                )
                report["rollback_integrity_check"] = [
                    str(row[0]) for row in check.execute("PRAGMA integrity_check")
                ]
            finally:
                check.close()
        raise
    finally:
        if connection is not None:
            connection.close()
        timings["total"] = time.perf_counter() - started
        try:
            _write_report(report_path, report)
        except OSError:
            pass


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatbook-canonical-rehearsal",
        description="Reconstruct schema v4 on a new disposable copy; never performs cutover.",
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--fail-after", choices=FAILURE_STAGES, help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    try:
        evidence = rehearse_canonical_migration(
            arguments.source,
            arguments.target,
            arguments.backup,
            fail_after=arguments.fail_after,
        )
    except ChatbookError as exc:
        print(json.dumps({"error": exc.code, "message": str(exc)}, sort_keys=True))
        return 2
    except (OSError, sqlite3.Error) as exc:
        print(json.dumps({"error": "migration_failed", "message": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(evidence, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
