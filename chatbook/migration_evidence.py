"""Read-only SQLite preflight, deterministic manifests, and verified local backups."""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from .domain import AccountType, ChatbookError, LineInput
from .fingerprints import transaction_fingerprint
from .schema_contract import AUDITED_TABLES, V2_TABLES

MIGRATION_TOOL_VERSION = "m5.1-c1-v1"
SUPPORTED_PREFLIGHT_VERSIONS = frozenset({2, 3})


class PreflightFailure(ChatbookError):
    """A fail-closed preflight result with stable, non-sensitive diagnostic codes."""

    def __init__(self, diagnostics: Sequence[str]) -> None:
        self.diagnostics = tuple(sorted(set(diagnostics)))
        detail = ", ".join(self.diagnostics)
        super().__init__("preflight_failed", f"Migration preflight failed: {detail}")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _json_hash(value: object) -> str:
    return _hash_bytes(_json_bytes(value))


def _normalize(value: object) -> object:
    if isinstance(value, bytes):
        return {"bytes_sha256": _hash_bytes(value), "length": len(value)}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe SQLite identifier: {value}")
    return f'"{value}"'


def _readonly_connection(path: Path) -> sqlite3.Connection:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _table_names(connection: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
    )


def table_evidence(connection: sqlite3.Connection, table: str) -> dict[str, object]:
    """Hash a table in deterministic primary-key order without returning row contents."""
    quoted_table = _identifier(table)
    columns = tuple(connection.execute(f"PRAGMA table_info({quoted_table})"))
    if not columns:
        raise sqlite3.DatabaseError(f"missing table: {table}")
    names = [str(column[1]) for column in columns]
    primary = [
        str(column[1])
        for column in sorted(columns, key=lambda column: int(column[5]) or 1_000_000)
        if int(column[5]) > 0
    ]
    order = primary or names
    select_columns = ", ".join(_identifier(name) for name in names)
    order_columns = ", ".join(_identifier(name) for name in order)
    digest = hashlib.sha256()
    count = 0
    for row in connection.execute(
        f"SELECT {select_columns} FROM {quoted_table} ORDER BY {order_columns}"
    ):
        digest.update(_json_bytes([_normalize(row[name]) for name in names]))
        digest.update(b"\n")
        count += 1
    return {"row_count": count, "sha256": digest.hexdigest()}


def legacy_table_evidence(connection: sqlite3.Connection) -> dict[str, dict[str, object]]:
    """Return hashes for every v2 table; used to prove v3 changed no legacy row."""
    return {table: table_evidence(connection, table) for table in V2_TABLES}


def _rows(
    connection: sqlite3.Connection,
    sql: str,
    parameters: Sequence[object] = (),
) -> list[dict[str, object]]:
    return [dict(row) for row in connection.execute(sql, parameters)]


def _legacy_fingerprint_diagnostics(connection: sqlite3.Connection) -> set[str]:
    diagnostics: set[str] = set()
    for validation in connection.execute("SELECT * FROM validations ORDER BY id"):
        transaction = connection.execute(
            "SELECT * FROM transactions WHERE id = ? AND organization_id = ?",
            (validation["transaction_id"], validation["organization_id"]),
        ).fetchone()
        if transaction is None:
            diagnostics.add("validation.transaction_reference")
            continue
        lines = tuple(
            LineInput(
                str(row["account_id"]),
                int(row["debit"]),
                int(row["credit"]),
                cast(str | None, row["project_id"]),
            )
            for row in connection.execute(
                "SELECT * FROM transaction_lines WHERE transaction_id = ? ORDER BY position",
                (transaction["id"],),
            )
        )
        if transaction_fingerprint(dict(transaction), lines) != validation["fingerprint"]:
            diagnostics.add("validation.fingerprint_mismatch")
    return diagnostics


def _proposal_diagnostics(connection: sqlite3.Connection) -> set[str]:
    diagnostics: set[str] = set()
    for transaction in connection.execute("SELECT * FROM transactions ORDER BY id"):
        transaction_id = str(transaction["id"])
        organization_id = str(transaction["organization_id"])
        lines = tuple(
            connection.execute(
                "SELECT * FROM transaction_lines WHERE transaction_id = ? ORDER BY position",
                (transaction_id,),
            )
        )
        if transaction["state"] != "proposed":
            diagnostics.add("proposal.transient_state")
        positions = [int(row["position"]) for row in lines]
        if positions != list(range(1, len(lines) + 1)):
            diagnostics.add("proposal.line_order")
        if not 2 <= len(lines) <= 1_000:
            diagnostics.add("proposal.line_count")
        if sum(int(row["debit"]) for row in lines) != sum(int(row["credit"]) for row in lines):
            diagnostics.add("proposal.unbalanced")
        period_count = connection.execute(
            "SELECT count(*) FROM accounting_periods WHERE organization_id = ? "
            "AND ? BETWEEN starts_on AND ends_on",
            (organization_id, transaction["entry_date"]),
        ).fetchone()[0]
        if period_count != 1:
            diagnostics.add("proposal.period_inconsistent")
        if (
            transaction["document_id"] is not None
            and connection.execute(
                "SELECT 1 FROM documents WHERE id = ? AND organization_id = ?",
                (transaction["document_id"], organization_id),
            ).fetchone()
            is None
        ):
            diagnostics.add("proposal.document_reference")
        for line in lines:
            if (
                connection.execute(
                    "SELECT 1 FROM accounts WHERE id = ? AND organization_id = ?",
                    (line["account_id"], organization_id),
                ).fetchone()
                is None
            ):
                diagnostics.add("proposal.account_reference")
            if (
                line["project_id"] is not None
                and connection.execute(
                    "SELECT 1 FROM projects WHERE id = ? AND organization_id = ?",
                    (line["project_id"], organization_id),
                ).fetchone()
                is None
            ):
                diagnostics.add("proposal.project_reference")
    return diagnostics


def _confirmation_diagnostics(connection: sqlite3.Connection) -> set[str]:
    diagnostics: set[str] = set()
    for confirmation in connection.execute("SELECT * FROM confirmations ORDER BY id"):
        joined = connection.execute(
            "SELECT v.transaction_id, v.organization_id, t.version FROM validations v "
            "JOIN transactions t ON t.id = v.transaction_id "
            "AND t.organization_id = v.organization_id "
            "WHERE v.id = ? AND v.organization_id = ?",
            (confirmation["validation_id"], confirmation["organization_id"]),
        ).fetchone()
        provenance = connection.execute(
            "SELECT * FROM confirmation_provenance WHERE confirmation_id = ?",
            (confirmation["id"],),
        ).fetchone()
        if joined is None:
            diagnostics.add("confirmation.validation_reference")
        if provenance is None:
            diagnostics.add("confirmation.provenance_missing")
        elif joined is None or (
            provenance["organization_id"] != confirmation["organization_id"]
            or provenance["proposal_id"] != joined["transaction_id"]
            or provenance["proposal_version"] != joined["version"]
            or not str(provenance["confirmation_request_id"]).strip()
        ):
            diagnostics.add("confirmation.provenance_mismatch")
    return diagnostics


def _idempotency_diagnostics(connection: sqlite3.Connection) -> set[str]:
    diagnostics: set[str] = set()
    expected = {
        "transaction.confirm": ("confirmation", "confirmations"),
        "transaction.post": ("journal_entry", "journal_entries"),
    }
    for receipt in connection.execute("SELECT * FROM command_idempotency ORDER BY id"):
        contract = expected.get(str(receipt["operation"]))
        if contract is None or receipt["resource_type"] != contract[0]:
            diagnostics.add("idempotency.operation_resource_mismatch")
            continue
        table = _identifier(contract[1])
        if (
            connection.execute(
                f"SELECT 1 FROM {table} WHERE id = ? AND organization_id = ?",
                (receipt["resource_id"], receipt["organization_id"]),
            ).fetchone()
            is None
        ):
            diagnostics.add("idempotency.resource_reference")
    return diagnostics


def _journal_diagnostics(connection: sqlite3.Connection) -> set[str]:
    diagnostics: set[str] = set()
    entries = tuple(connection.execute("SELECT * FROM journal_entries ORDER BY id"))
    for entry in entries:
        entry_id = str(entry["id"])
        organization_id = str(entry["organization_id"])
        lines = tuple(
            connection.execute(
                "SELECT * FROM journal_lines WHERE entry_id = ? ORDER BY position", (entry_id,)
            )
        )
        if entry["state"] != "posted":
            diagnostics.add("journal.transient_state")
        positions = [int(row["position"]) for row in lines]
        if positions != list(range(1, len(lines) + 1)):
            diagnostics.add("journal.line_order")
        if not 2 <= len(lines) <= 1_000:
            diagnostics.add("journal.line_count")
        if sum(int(row["debit"]) for row in lines) != sum(int(row["credit"]) for row in lines):
            diagnostics.add("journal.unbalanced")
        if (
            connection.execute(
                "SELECT 1 FROM accounting_periods WHERE id = ? AND organization_id = ? "
                "AND ? BETWEEN starts_on AND ends_on",
                (entry["period_id"], organization_id, entry["entry_date"]),
            ).fetchone()
            is None
        ):
            diagnostics.add("journal.period_inconsistent")
        transaction = connection.execute(
            "SELECT * FROM transactions WHERE id = ? AND organization_id = ?",
            (entry["transaction_id"], organization_id),
        ).fetchone()
        confirmation = connection.execute(
            "SELECT c.id FROM confirmations c JOIN validations v ON v.id = c.validation_id "
            "WHERE c.id = ? AND c.organization_id = ? AND v.transaction_id = ?",
            (entry["confirmation_id"], organization_id, entry["transaction_id"]),
        ).fetchone()
        if transaction is None or confirmation is None:
            diagnostics.add("journal.proposal_confirmation_reference")
        elif (
            transaction["entry_date"] != entry["entry_date"]
            or transaction["description"] != entry["description"]
            or transaction["reverses_entry_id"] != entry["reverses_entry_id"]
        ):
            diagnostics.add("journal.proposal_mismatch")
        proposal_lines = tuple(
            (
                int(row["position"]),
                row["account_id"],
                int(row["debit"]),
                int(row["credit"]),
                row["project_id"],
            )
            for row in connection.execute(
                "SELECT position, account_id, debit, credit, project_id FROM transaction_lines "
                "WHERE transaction_id = ? ORDER BY position",
                (entry["transaction_id"],),
            )
        )
        journal_lines = tuple(
            (
                int(row["position"]),
                row["account_id"],
                int(row["debit"]),
                int(row["credit"]),
                row["project_id"],
            )
            for row in lines
        )
        if journal_lines != proposal_lines:
            diagnostics.add("journal.proposal_lines_mismatch")
        for line in lines:
            if (
                connection.execute(
                    "SELECT 1 FROM accounts WHERE id = ? AND organization_id = ?",
                    (line["account_id"], organization_id),
                ).fetchone()
                is None
            ):
                diagnostics.add("journal.account_reference")
            if (
                line["project_id"] is not None
                and connection.execute(
                    "SELECT 1 FROM projects WHERE id = ? AND organization_id = ?",
                    (line["project_id"], organization_id),
                ).fetchone()
                is None
            ):
                diagnostics.add("journal.project_reference")
        target_id = entry["reverses_entry_id"]
        if target_id is not None:
            target = connection.execute(
                "SELECT * FROM journal_entries WHERE id = ? AND organization_id = ? "
                "AND state = 'posted'",
                (target_id, organization_id),
            ).fetchone()
            if (
                target is None
                or target_id == entry_id
                or (target is not None and entry["entry_date"] < target["entry_date"])
            ):
                diagnostics.add("reversal.target_invalid")
            else:
                expected = tuple(
                    (
                        int(row["position"]),
                        row["account_id"],
                        int(row["credit"]),
                        int(row["debit"]),
                        row["project_id"],
                    )
                    for row in connection.execute(
                        "SELECT position, account_id, debit, credit, project_id FROM journal_lines "
                        "WHERE entry_id = ? ORDER BY position",
                        (target_id,),
                    )
                )
                if journal_lines != expected:
                    diagnostics.add("reversal.lines_mismatch")
    for entry in entries:
        seen: set[str] = set()
        cursor = cast(str | None, entry["reverses_entry_id"])
        while cursor is not None:
            if cursor in seen or cursor == entry["id"]:
                diagnostics.add("reversal.cycle")
                break
            seen.add(cursor)
            row = connection.execute(
                "SELECT reverses_entry_id FROM journal_entries WHERE id = ?", (cursor,)
            ).fetchone()
            if row is None:
                break
            cursor = cast(str | None, row["reverses_entry_id"])
    return diagnostics


def _audit_diagnostics(connection: sqlite3.Connection) -> set[str]:
    diagnostics: set[str] = set()
    allowed = set(AUDITED_TABLES)
    for event in connection.execute("SELECT * FROM audit_events ORDER BY sequence"):
        entity_type = str(event["entity_type"])
        operation = str(event["event_type"])
        if entity_type not in allowed or operation not in {
            f"{entity_type}.insert",
            f"{entity_type}.update",
        }:
            diagnostics.add("audit.event_contract")
            continue
        table = _identifier(entity_type)
        entity = connection.execute(
            f"SELECT * FROM {table} WHERE id = ?", (event["entity_id"],)
        ).fetchone()
        if entity is None:
            diagnostics.add("audit.entity_reference")
            continue
        columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
        expected_organization: object = None
        if entity_type == "organizations":
            expected_organization = entity["id"]
        elif "organization_id" in columns:
            expected_organization = entity["organization_id"]
        if event["organization_id"] != expected_organization:
            diagnostics.add("audit.organization_scope")
        try:
            new_state = json.loads(str(event["new_state"]))
            metadata = json.loads(str(event["metadata"]))
            previous_state = (
                None
                if event["previous_state"] is None
                else json.loads(str(event["previous_state"]))
            )
        except (json.JSONDecodeError, TypeError):
            diagnostics.add("audit.json_invalid")
            continue
        if not isinstance(new_state, dict) or new_state.get("id") != event["entity_id"]:
            diagnostics.add("audit.payload_entity")
        if not isinstance(metadata, dict):
            diagnostics.add("audit.metadata_invalid")
        if operation.endswith(".insert") and previous_state is not None:
            diagnostics.add("audit.previous_state")
        if operation.endswith(".update") and not isinstance(previous_state, dict):
            diagnostics.add("audit.previous_state")
    sequence_row = connection.execute(
        "SELECT seq FROM sqlite_sequence WHERE name = 'audit_events'"
    ).fetchone()
    maximum = int(
        connection.execute("SELECT COALESCE(max(sequence), 0) FROM audit_events").fetchone()[0]
    )
    sequence = 0 if sequence_row is None else int(sequence_row[0])
    if sequence < maximum:
        diagnostics.add("audit.sequence_state")
    return diagnostics


def _book_diagnostics(connection: sqlite3.Connection, version: int) -> set[str]:
    if version < 3:
        return set()
    diagnostics: set[str] = set()
    organizations = int(connection.execute("SELECT count(*) FROM organizations").fetchone()[0])
    books = int(connection.execute("SELECT count(*) FROM ledger_books").fetchone()[0])
    mismatch = int(
        connection.execute(
            "SELECT count(*) FROM organizations o LEFT JOIN ledger_books b "
            "ON b.organization_id = o.id WHERE b.id IS NULL OR b.owner_kind != 'BUSINESS' "
            "OR b.id != 'book:business:' || o.id OR b.currency != o.currency "
            "OR b.minor_unit_digits != o.minor_unit_digits"
        ).fetchone()[0]
    )
    orphan = int(
        connection.execute(
            "SELECT count(*) FROM ledger_books b LEFT JOIN organizations o "
            "ON o.id = b.organization_id WHERE o.id IS NULL"
        ).fetchone()[0]
    )
    if organizations != books or mismatch:
        diagnostics.add("ledger_book.organization_mapping")
    if orphan:
        diagnostics.add("ledger_book.orphan")
    return diagnostics


def _trial_payload(
    connection: sqlite3.Connection,
    organization: sqlite3.Row,
    ledger: Sequence[dict[str, object]],
    *,
    as_of: str | None = None,
    project_id: str | None = None,
) -> dict[str, object]:
    organization_id = str(organization["id"])
    selected = [
        row
        for row in ledger
        if (as_of is None or str(row["entry_date"]) <= as_of)
        and (project_id is None or row["project_id"] == project_id)
    ]
    totals: dict[str, tuple[int, int]] = {}
    for row in selected:
        account_id = str(row["account_id"])
        debit, credit = totals.get(account_id, (0, 0))
        totals[account_id] = debit + int(str(row["debit"])), credit + int(str(row["credit"]))
    accounts: list[dict[str, object]] = []
    for account in connection.execute(
        "SELECT id, code, name, account_type FROM accounts "
        "WHERE organization_id = ? ORDER BY code, id",
        (organization_id,),
    ):
        debit, credit = totals.get(str(account["id"]), (0, 0))
        net = debit - credit
        accounts.append(
            {
                "id": account["id"],
                "code": account["code"],
                "name": account["name"],
                "type": account["account_type"],
                "debits": debit,
                "credits": credit,
                "debit_balance": max(net, 0),
                "credit_balance": max(-net, 0),
            }
        )
    return {
        "currency": organization["currency"],
        "minor_unit_digits": organization["minor_unit_digits"],
        "as_of": as_of,
        "project_id": project_id,
        "accounts": accounts,
    }


def _report_fingerprints(connection: sqlite3.Connection) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for organization in connection.execute(
        "SELECT id, currency, minor_unit_digits FROM organizations ORDER BY id"
    ):
        organization_id = str(organization["id"])
        ledger = _rows(
            connection,
            "SELECT e.id AS entry_id, e.transaction_id, e.entry_date, e.description, "
            "e.reverses_entry_id, l.id AS line_id, l.position, l.account_id, a.code, "
            "a.name AS account_name, a.account_type, l.debit, l.credit, l.project_id "
            "FROM journal_entries e JOIN journal_lines l ON l.entry_id = e.id "
            "JOIN accounts a ON a.id = l.account_id "
            "WHERE e.organization_id = ? AND e.state = 'posted' "
            "ORDER BY e.entry_date, e.id, l.position",
            (organization_id,),
        )

        period_reports: list[dict[str, object]] = []
        for period in connection.execute(
            "SELECT id, starts_on, ends_on FROM accounting_periods "
            "WHERE organization_id = ? ORDER BY starts_on, id",
            (organization_id,),
        ):
            period_ledger = [
                row
                for row in ledger
                if str(period["starts_on"]) <= str(row["entry_date"]) <= str(period["ends_on"])
            ]
            revenue = expenses = 0
            for row in period_ledger:
                net = int(str(row["debit"])) - int(str(row["credit"]))
                if row["account_type"] == AccountType.REVENUE.value:
                    revenue -= net
                elif row["account_type"] == AccountType.EXPENSE.value:
                    expenses += net
            period_trial = _trial_payload(
                connection, organization, ledger, as_of=str(period["ends_on"])
            )
            net_by_type = {kind.value: 0 for kind in AccountType}
            for account in cast(list[dict[str, object]], period_trial["accounts"]):
                net_by_type[str(account["type"])] += int(str(account["debits"])) - int(
                    str(account["credits"])
                )
            period_reports.append(
                {
                    "period_id": period["id"],
                    "starts_on": period["starts_on"],
                    "ends_on": period["ends_on"],
                    "income": {
                        "revenue": revenue,
                        "expenses": expenses,
                        "net_income": revenue - expenses,
                    },
                    "balance_sheet": net_by_type,
                    "trial": period_trial,
                    "asset_movements": [
                        row
                        for row in period_ledger
                        if row["account_type"] == AccountType.ASSET.value
                    ],
                }
            )
        project_reports = [
            _trial_payload(
                connection,
                organization,
                ledger,
                project_id=str(project["id"]),
            )
            for project in connection.execute(
                "SELECT id FROM projects WHERE organization_id = ? ORDER BY id",
                (organization_id,),
            )
        ]
        result[organization_id] = {
            "general_ledger_sha256": _json_hash(ledger),
            "trial_balance_sha256": _json_hash(_trial_payload(connection, organization, ledger)),
            "period_reports_sha256": _json_hash(period_reports),
            "project_reports_sha256": _json_hash(project_reports),
        }
    return result


def build_preflight_manifest(
    database_copy: str | Path,
    *,
    generated_at: str | None = None,
    database_identity: str | None = None,
    database_sha256: str | None = None,
    backup_sha256: str | None = None,
    expected_manifest: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Inspect a consistent SQLite copy without writing to it or logging financial payloads."""
    path = Path(database_copy)
    if not path.is_file():
        raise ChatbookError("backup_missing", "The SQLite database copy does not exist.")
    diagnostics: set[str] = set()
    connection = _readonly_connection(path)
    try:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version not in SUPPORTED_PREFLIGHT_VERSIONS:
            diagnostics.add("schema.version_unsupported")
        integrity_rows = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
        if integrity_rows != ["ok"]:
            diagnostics.add("database.integrity_check")
        foreign_key_rows = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
        if foreign_key_rows:
            diagnostics.add("database.foreign_key_integrity")
        names = _table_names(connection)
        required = set(V2_TABLES) | ({"ledger_books"} if version == 3 else set())
        missing = required - set(names)
        if missing:
            diagnostics.add("schema.table_missing")
        if diagnostics & {"schema.version_unsupported", "schema.table_missing"}:
            raise PreflightFailure(tuple(diagnostics))
        table_manifest: dict[str, dict[str, object]] = {}
        for table in names:
            table_manifest[table] = table_evidence(connection, table)
        organizations = (
            _rows(
                connection,
                "SELECT id, currency, minor_unit_digits FROM organizations ORDER BY id",
            )
            if "organizations" in names
            else []
        )
        metrics: dict[str, object] = {
            "organization_count": len(organizations),
            "organization_currency_precision": organizations,
            "proposal_count": int(
                connection.execute("SELECT count(*) FROM transactions").fetchone()[0]
            ),
            "proposal_line_count": int(
                connection.execute("SELECT count(*) FROM transaction_lines").fetchone()[0]
            ),
            "proposal_states": _rows(
                connection,
                "SELECT state, count(*) AS count FROM transactions GROUP BY state ORDER BY state",
            ),
            "validation_count": int(
                connection.execute("SELECT count(*) FROM validations").fetchone()[0]
            ),
            "confirmation_count": int(
                connection.execute("SELECT count(*) FROM confirmations").fetchone()[0]
            ),
            "confirmation_provenance_count": int(
                connection.execute("SELECT count(*) FROM confirmation_provenance").fetchone()[0]
            ),
            "idempotency_receipt_count": int(
                connection.execute("SELECT count(*) FROM command_idempotency").fetchone()[0]
            ),
            "journal_entry_count": int(
                connection.execute("SELECT count(*) FROM journal_entries").fetchone()[0]
            ),
            "journal_line_count": int(
                connection.execute("SELECT count(*) FROM journal_lines").fetchone()[0]
            ),
            "project_count": int(connection.execute("SELECT count(*) FROM projects").fetchone()[0]),
            "document_count": int(
                connection.execute("SELECT count(*) FROM documents").fetchone()[0]
            ),
            "audit_count": int(
                connection.execute("SELECT count(*) FROM audit_events").fetchone()[0]
            ),
            "audit_max_sequence": int(
                connection.execute(
                    "SELECT COALESCE(max(sequence), 0) FROM audit_events"
                ).fetchone()[0]
            ),
            "sqlite_sequence": _rows(
                connection, "SELECT name, seq FROM sqlite_sequence ORDER BY name"
            ),
        }
        diagnostics.update(_proposal_diagnostics(connection))
        diagnostics.update(_legacy_fingerprint_diagnostics(connection))
        diagnostics.update(_confirmation_diagnostics(connection))
        diagnostics.update(_idempotency_diagnostics(connection))
        diagnostics.update(_journal_diagnostics(connection))
        diagnostics.update(_audit_diagnostics(connection))
        diagnostics.update(_book_diagnostics(connection, version))
        report_fingerprints = _report_fingerprints(connection)
        legacy_manifest = {
            table: table_manifest[table] for table in V2_TABLES if table in table_manifest
        }
        schema_rows = _rows(
            connection,
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name",
        )
        manifest: dict[str, object] = {
            "tool_version": MIGRATION_TOOL_VERSION,
            "generated_at": generated_at or _now(),
            "database_identity": database_identity or _hash_bytes(str(path.resolve()).encode()),
            "database_sha256": database_sha256 or _hash_file(path),
            "backup_sha256": backup_sha256 or _hash_file(path),
            "schema_version": version,
            "sqlite_version": sqlite3.sqlite_version,
            "schema_sha256": _json_hash(schema_rows),
            "integrity_check": integrity_rows,
            "foreign_key_violation_count": len(foreign_key_rows),
            "tables": table_manifest,
            "legacy_content_fingerprint": _json_hash(legacy_manifest),
            "content_fingerprint": _json_hash(table_manifest),
            "metrics": metrics,
            "report_fingerprints": report_fingerprints,
            "diagnostics": sorted(diagnostics),
        }
        if expected_manifest is not None:
            if (
                expected_manifest.get("legacy_content_fingerprint")
                != manifest["legacy_content_fingerprint"]
            ):
                diagnostics.add("evidence.content_mismatch")
            if expected_manifest.get("report_fingerprints") != report_fingerprints:
                diagnostics.add("report.fingerprint_mismatch")
            manifest["diagnostics"] = sorted(diagnostics)
        if diagnostics:
            raise PreflightFailure(tuple(diagnostics))
        return manifest
    except sqlite3.DatabaseError as exc:
        raise PreflightFailure(("database.read_error",)) from exc
    finally:
        connection.close()


def _backup_database(source: Path, destination: Path) -> None:
    source_connection = _readonly_connection(source)
    try:
        destination_connection = sqlite3.connect(str(destination), isolation_level=None)
        try:
            source_connection.backup(destination_connection)
        finally:
            destination_connection.close()
    finally:
        source_connection.close()


def create_verified_backup(
    source_path: str | Path,
    backup_path: str | Path,
    *,
    lock_connection: sqlite3.Connection | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    """Create, restore, and inspect a SQLite-consistent backup while writers are blocked."""
    source = Path(source_path).resolve()
    backup = Path(backup_path).resolve()
    if source == backup:
        raise ChatbookError("backup_path_invalid", "Backup must use a separate path.")
    if not source.is_file():
        raise ChatbookError("backup_source_missing", "The source database does not exist.")
    backup.parent.mkdir(parents=True, exist_ok=True)
    owns_lock = lock_connection is None
    guard = lock_connection or sqlite3.connect(str(source), isolation_level=None, timeout=10)
    if owns_lock:
        guard.execute("PRAGMA busy_timeout = 10000")
        guard.execute("BEGIN IMMEDIATE")
    elif not guard.in_transaction:
        raise RuntimeError("A migration backup requires an active writer-blocking transaction.")
    timestamp = generated_at or _now()
    temporary_backup = backup.with_name(f".{backup.name}.{uuid4().hex}.tmp")
    restore = backup.with_name(f".{backup.name}.{uuid4().hex}.restore")
    try:
        _backup_database(source, temporary_backup)
        snapshot_hash = _hash_file(temporary_backup)
        source_identity = _hash_bytes(str(source).encode())
        snapshot_manifest = build_preflight_manifest(
            temporary_backup,
            generated_at=timestamp,
            database_identity=source_identity,
            database_sha256=snapshot_hash,
            backup_sha256=snapshot_hash,
        )
        if backup.exists():
            existing_hash = _hash_file(backup)
            existing_manifest = build_preflight_manifest(
                backup,
                generated_at=timestamp,
                database_identity=source_identity,
                database_sha256=existing_hash,
                backup_sha256=existing_hash,
            )
            if (
                existing_manifest["legacy_content_fingerprint"]
                != snapshot_manifest["legacy_content_fingerprint"]
            ):
                raise ChatbookError(
                    "backup_conflict",
                    "The existing migration backup does not match the locked source database.",
                )
            temporary_backup.unlink()
        else:
            os.replace(temporary_backup, backup)
        backup_hash = _hash_file(backup)
        backup_manifest = build_preflight_manifest(
            backup,
            generated_at=timestamp,
            database_identity=source_identity,
            database_sha256=snapshot_hash,
            backup_sha256=backup_hash,
        )
        _backup_database(backup, restore)
        restore_hash = _hash_file(restore)
        restored_manifest = build_preflight_manifest(
            restore,
            generated_at=timestamp,
            database_identity=source_identity,
            database_sha256=restore_hash,
            backup_sha256=backup_hash,
            expected_manifest=backup_manifest,
        )
        evidence: dict[str, object] = {
            "tool_version": MIGRATION_TOOL_VERSION,
            "generated_at": timestamp,
            "source_database_identity": source_identity,
            "source_file_sha256": _hash_file(source),
            "source_snapshot_sha256": snapshot_hash,
            "backup_sha256": backup_hash,
            "restored_sha256": restore_hash,
            "backup_restore_verified": True,
            "manifest": backup_manifest,
            "restored_content_fingerprint": restored_manifest["content_fingerprint"],
        }
        manifest_path = Path(f"{backup}.manifest.json")
        manifest_temporary = manifest_path.with_name(f".{manifest_path.name}.{uuid4().hex}.tmp")
        manifest_temporary.write_text(
            json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(manifest_temporary, manifest_path)
        return evidence
    finally:
        if temporary_backup.exists():
            temporary_backup.unlink()
        if restore.exists():
            restore.unlink()
        if owns_lock:
            guard.rollback()
            guard.close()


def restore_verified_backup(
    backup_path: str | Path,
    restore_path: str | Path,
    *,
    expected_manifest: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Restore a protected SQLite backup to a new path and reconcile the restored copy."""
    backup = Path(backup_path).resolve()
    restore = Path(restore_path).resolve()
    if backup == restore:
        raise ChatbookError("restore_path_invalid", "Restore must use a separate path.")
    if not backup.is_file():
        raise ChatbookError("restore_source_missing", "The backup database does not exist.")
    if restore.exists():
        raise ChatbookError("restore_target_exists", "The restore target must not already exist.")
    restore.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    manifest = expected_manifest or build_preflight_manifest(backup)
    try:
        _backup_database(backup, restore)
        restored = build_preflight_manifest(restore, expected_manifest=manifest)
        return {
            "backup_sha256": _hash_file(backup),
            "restore_sha256": _hash_file(restore),
            "backup_bytes": backup.stat().st_size,
            "restore_bytes": restore.stat().st_size,
            "restore_seconds": time.perf_counter() - started,
            "content_fingerprint": restored["content_fingerprint"],
            "legacy_content_fingerprint": restored["legacy_content_fingerprint"],
            "report_fingerprints": restored["report_fingerprints"],
            "restore_verified": True,
        }
    except Exception:
        if restore.exists():
            restore.unlink()
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatbook-migration-evidence",
        description="Create and restore-verify a read-only Chatbooks SQLite migration backup.",
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("backup", type=Path)
    arguments = parser.parse_args(argv)
    try:
        evidence = create_verified_backup(arguments.source, arguments.backup)
    except ChatbookError as exc:
        print(json.dumps({"error": exc.code, "message": str(exc)}))
        return 2
    summary = {
        "tool_version": evidence["tool_version"],
        "generated_at": evidence["generated_at"],
        "source_database_identity": evidence["source_database_identity"],
        "source_snapshot_sha256": evidence["source_snapshot_sha256"],
        "backup_sha256": evidence["backup_sha256"],
        "restored_sha256": evidence["restored_sha256"],
        "backup_restore_verified": evidence["backup_restore_verified"],
        "manifest": evidence["manifest"],
    }
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
