"""SQLite persistence, atomic writes, schema initialization, and automatic audit capture."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

from .domain import ChatbookError
from .migration_evidence import create_verified_backup, legacy_table_evidence
from .schema_contract import AUDITED_TABLES, MUTABLE_TABLES

SCHEMA_VERSION = 3
AUDIT_TRIGGER_NAMES = frozenset(
    f"audit_{table}_{operation}" for table in AUDITED_TABLES for operation in ("insert", "update")
)


class Database:
    def __init__(self, path: str | Path, *, allow_thread_handoff: bool = False) -> None:
        self._path = None if str(path) == ":memory:" else Path(path).resolve()
        # FastAPI may execute a synchronous dependency's enter, endpoint, and exit stages on
        # different worker threads. API callers opt into sequential thread handoff for their
        # request-scoped connection; all other callers retain SQLite's strict creator-thread guard.
        self.connection = sqlite3.connect(
            str(path),
            isolation_level=None,
            timeout=10,
            check_same_thread=not allow_thread_handoff,
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA recursive_triggers = ON")
        self.connection.execute("PRAGMA busy_timeout = 10000")
        self.connection.execute("PRAGMA synchronous = FULL")
        self._actor: str | None = None
        self._metadata = "{}"
        self.connection.create_function("chatbook_actor", 0, self._current_actor)
        self.connection.create_function("chatbook_metadata", 0, lambda: self._metadata)
        self.connection.create_function("chatbook_now", 0, lambda: datetime.now(UTC).isoformat())
        try:
            self._initialize()
            self.connection.set_authorizer(self._authorize_sql)
        except Exception:
            self.connection.close()
            raise

    def _authorize_sql(
        self,
        action_code: int,
        arg1: str | None,
        arg2: str | None,
        database_name: str | None,
        trigger_or_view: str | None,
    ) -> int:
        """Reject forged audit inserts through the supported application connection."""
        del arg2, database_name
        if action_code == sqlite3.SQLITE_INSERT and arg1 == "audit_events":
            if trigger_or_view not in AUDIT_TRIGGER_NAMES:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def _current_actor(self) -> str:
        if self._actor is None:
            raise ChatbookError(
                "actor_required", "Writes require an actor and an atomic operation."
            )
        return self._actor

    def _initialize(self) -> None:
        version = int(self.connection.execute("PRAGMA user_version").fetchone()[0])
        has_application_tables = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()
        if version == SCHEMA_VERSION:
            self._verify_v3_mapping()
            return
        if version not in {0, 1, 2} or (version == 0 and has_application_tables):
            raise ChatbookError(
                "schema_version", "Unsupported database schema; migration required."
            )
        if version == 0:
            self._initialize_fresh_database()
            return
        if version == 1:
            self._migrate_v1_to_v2()
        self._migrate_v2_to_v3()

    def _initialize_fresh_database(self) -> None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self._execute_resource_script("schema.sql")
            self._install_audit_triggers()
            self.connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._verify_v3_mapping()
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def _migrate_v1_to_v2(self) -> None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self._execute_resource_script("migrations/0002_api_layer.sql")
            self._reinstall_audit_triggers("memberships")
            self._reinstall_audit_triggers("transactions")
            self.connection.execute("PRAGMA user_version = 2")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def _migrate_v2_to_v3(self) -> None:
        if self._path is None:
            raise ChatbookError(
                "migration_backup_required",
                "Schema v2 requires a file-backed database for verified backup migration.",
            )
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            backup_path = Path(f"{self._path}.pre-v3.backup")
            evidence = create_verified_backup(
                self._path, backup_path, lock_connection=self.connection
            )
            manifest = evidence["manifest"]
            if not isinstance(manifest, dict) or manifest.get("schema_version") != 2:
                raise ChatbookError(
                    "migration_preflight", "The verified migration evidence is not schema v2."
                )
            expected_tables = manifest.get("tables")
            if not isinstance(expected_tables, dict):
                raise ChatbookError(
                    "migration_preflight", "The verified migration evidence is incomplete."
                )
            self._execute_resource_script("migrations/0003_business_ledger_books.sql")
            self._verify_v3_mapping()
            after = legacy_table_evidence(self.connection)
            expected = {table: expected_tables.get(table) for table in after}
            if after != expected:
                raise ChatbookError(
                    "migration_reconciliation",
                    "The additive migration changed existing business records.",
                )
            self.connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def _verify_v3_mapping(self) -> None:
        try:
            organization_count = int(
                self.connection.execute("SELECT count(*) FROM organizations").fetchone()[0]
            )
            book_count = int(
                self.connection.execute("SELECT count(*) FROM ledger_books").fetchone()[0]
            )
            mismatch_count = int(
                self.connection.execute(
                    "SELECT count(*) FROM organizations o LEFT JOIN ledger_books b "
                    "ON b.organization_id = o.id WHERE b.id IS NULL "
                    "OR b.owner_kind != 'BUSINESS' OR b.id != 'book:business:' || o.id "
                    "OR b.currency != o.currency "
                    "OR b.minor_unit_digits != o.minor_unit_digits"
                ).fetchone()[0]
            )
            orphan_count = int(
                self.connection.execute(
                    "SELECT count(*) FROM ledger_books b LEFT JOIN organizations o "
                    "ON o.id = b.organization_id WHERE o.id IS NULL"
                ).fetchone()[0]
            )
        except sqlite3.DatabaseError as exc:
            raise ChatbookError(
                "ledger_book_mapping_invalid", "Schema v3 LedgerBook mapping is incomplete."
            ) from exc
        if organization_count != book_count or mismatch_count or orphan_count:
            raise ChatbookError(
                "ledger_book_mapping_invalid",
                "Every organization must have exactly one matching BUSINESS LedgerBook.",
            )

    def _execute_resource_script(self, resource: str) -> None:
        script = files("chatbook").joinpath(*resource.split("/")).read_text(encoding="utf-8")
        # Execute complete statements without implicitly committing the migration lock.
        statement = ""
        for line in script.splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                self.connection.execute(statement)
                statement = ""

    def _reinstall_audit_triggers(self, table: str) -> None:
        for suffix in ("insert", "update"):
            self.connection.execute(f"DROP TRIGGER IF EXISTS audit_{table}_{suffix}")
        for prefix in ("no_replace", "no_delete", "no_update"):
            self.connection.execute(f"DROP TRIGGER IF EXISTS {prefix}_{table}")
        self._install_audit_triggers_for(table)

    def _install_audit_triggers(self) -> None:
        for table in AUDITED_TABLES:
            self._install_audit_triggers_for(table)

    def _install_audit_triggers_for(self, table: str) -> None:
        # Identifiers come only from the constant table allowlist and schema metadata.
        if table not in AUDITED_TABLES:
            raise ValueError(f"Unsupported audited table: {table}")
        self.connection.execute(f"""
            CREATE TRIGGER no_replace_{table} BEFORE INSERT ON {table}
            WHEN EXISTS (SELECT 1 FROM {table} WHERE id = NEW.id)
            BEGIN SELECT RAISE(ABORT, 'immutable_identity'); END
        """)
        columns = [row[1] for row in self.connection.execute(f"PRAGMA table_info({table})")]
        new_json = "json_object(" + ",".join(f"'{c}', NEW.{c}" for c in columns) + ")"
        old_json = "json_object(" + ",".join(f"'{c}', OLD.{c}" for c in columns) + ")"
        org = (
            "NEW.id"
            if table == "organizations"
            else ("NEW.organization_id" if "organization_id" in columns else "NULL")
        )
        for operation in ("INSERT", "UPDATE"):
            previous = "NULL" if operation == "INSERT" else old_json
            self.connection.execute(f"""
                CREATE TRIGGER audit_{table}_{operation.lower()} AFTER {operation} ON {table}
                BEGIN
                    INSERT INTO audit_events (
                        organization_id, actor_id, occurred_at, event_type, entity_type,
                        entity_id, previous_state, new_state, metadata
                    ) VALUES (
                        {org}, chatbook_actor(), chatbook_now(), '{table}.{operation.lower()}',
                        '{table}', NEW.id, {previous}, {new_json}, chatbook_metadata()
                    );
                END
            """)
        self.connection.execute(f"""
            CREATE TRIGGER no_delete_{table} BEFORE DELETE ON {table}
            BEGIN SELECT RAISE(ABORT, 'immutable_history'); END
        """)
        if table not in MUTABLE_TABLES:
            self.connection.execute(f"""
                CREATE TRIGGER no_update_{table} BEFORE UPDATE ON {table}
                BEGIN SELECT RAISE(ABORT, 'immutable_history'); END
            """)

    @contextmanager
    def write(
        self, actor_id: str, operation: str, *, request_id: str | None = None
    ) -> Iterator[sqlite3.Connection]:
        if self._actor is not None:
            raise RuntimeError("Nested financial operations are not supported.")
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self._actor = actor_id
            self._metadata = json.dumps(
                {"operation": operation, "request_id": request_id or str(uuid4())}
            )
            yield self.connection
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ChatbookError("constraint_violation", str(exc)) from exc
        except sqlite3.OperationalError as exc:
            self.connection.rollback()
            raise ChatbookError("database_error", str(exc)) from exc
        except Exception:
            self.connection.rollback()
            raise
        finally:
            self._actor = None
            self._metadata = "{}"

    def close(self) -> None:
        self.connection.close()
