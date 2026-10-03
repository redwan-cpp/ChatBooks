"""Strict opener for an existing, verified schema-v4 canonical database."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .canonical_schema import CANONICAL_AUDIT_TRIGGER_NAMES, verify_canonical_mapping
from .database import AUDIT_TRIGGER_NAMES
from .domain import ChatbookError


class CanonicalDatabase:
    """Open an already-migrated v4 database; never initializes or migrates a database."""

    def __init__(
        self,
        path: str | Path,
        *,
        read_only: bool = False,
        allow_thread_handoff: bool = False,
    ) -> None:
        if str(path) == ":memory:":
            raise ChatbookError(
                "canonical_copy_required",
                "Canonical storage requires a file-backed migrated database.",
            )
        self._path = Path(path).resolve()
        self._read_only = read_only
        if not self._path.is_file():
            raise ChatbookError(
                "canonical_database_missing",
                "Canonical storage requires an existing migrated schema-v4 database.",
            )
        self.connection = sqlite3.connect(
            f"{self._path.as_uri()}?mode={'ro' if read_only else 'rw'}",
            uri=True,
            isolation_level=None,
            timeout=10,
            check_same_thread=not allow_thread_handoff,
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA recursive_triggers = ON")
        self.connection.execute("PRAGMA busy_timeout = 10000")
        self.connection.execute("PRAGMA synchronous = FULL")
        if read_only:
            self.connection.execute("PRAGMA query_only = ON")
        self._actor: str | None = None
        self._ledger_book_id: str | None = None
        self._metadata = "{}"
        self.connection.create_function("chatbook_actor", 0, self._current_actor)
        self.connection.create_function("chatbook_book", 0, self._current_book)
        self.connection.create_function("chatbook_metadata", 0, lambda: self._metadata)
        self.connection.create_function("chatbook_now", 0, lambda: datetime.now(UTC).isoformat())
        try:
            verify_canonical_mapping(self.connection)
            self.connection.set_authorizer(self._authorize_sql)
        except Exception as exc:
            self.connection.close()
            if isinstance(exc, ChatbookError):
                raise
            raise ChatbookError(
                "schema_version", "A verified schema-v4 database is required."
            ) from exc

    def _authorize_sql(
        self,
        action_code: int,
        arg1: str | None,
        arg2: str | None,
        database_name: str | None,
        trigger_or_view: str | None,
    ) -> int:
        del arg2, database_name
        if action_code == sqlite3.SQLITE_INSERT and arg1 == "audit_events":
            if trigger_or_view not in AUDIT_TRIGGER_NAMES | CANONICAL_AUDIT_TRIGGER_NAMES:
                return sqlite3.SQLITE_DENY
        if action_code == sqlite3.SQLITE_INSERT and arg1 == "audit_event_book_scopes":
            if trigger_or_view not in CANONICAL_AUDIT_TRIGGER_NAMES:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def _current_actor(self) -> str:
        if self._actor is None:
            raise ChatbookError("actor_required", "Writes require an authenticated actor.")
        return self._actor

    def _current_book(self) -> str:
        if self._ledger_book_id is None:
            raise ChatbookError(
                "financial_context_required", "Financial writes require a bound LedgerBook."
            )
        return self._ledger_book_id

    @contextmanager
    def write(
        self,
        actor_id: str,
        operation: str,
        *,
        request_id: str | None = None,
        ledger_book_id: str | None = None,
    ) -> Iterator[sqlite3.Connection]:
        if self._read_only:
            raise ChatbookError(
                "runtime_read_only",
                "Financial and authentication writes are disabled in read-only runtime mode.",
            )
        if self._actor is not None:
            raise RuntimeError("Nested financial operations are not supported.")
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self._actor = actor_id
            self._ledger_book_id = ledger_book_id
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
            self._ledger_book_id = None
            self._metadata = "{}"

    def close(self) -> None:
        self.connection.close()
