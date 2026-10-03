"""Fail-closed server configuration for selecting the persisted financial storage schema."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

from .canonical_database import CanonicalDatabase
from .canonical_schema import verify_canonical_mapping
from .database import SCHEMA_VERSION, Database
from .domain import ChatbookError

STORAGE_MODE_ENV = "CHATBOOK_STORAGE_MODE"
SCHEMA_VERSION_ENV = "CHATBOOK_SCHEMA_VERSION"
DATABASE_PATH_ENV = "CHATBOOK_DB_PATH"
RELEASE_ID_ENV = "CHATBOOK_RUNTIME_RELEASE_ID"
ACCESS_MODE_ENV = "CHATBOOK_RUNTIME_ACCESS"

FORBIDDEN_RUNTIME_ENVIRONMENT_KEYS = frozenset(
    {
        "CHATBOOK_CANONICAL_REHEARSAL",
        "CHATBOOK_REHEARSAL_MODE",
        "CHATBOOK_LEDGER_BOOK_ID",
        "CHATBOOK_BOOK_ID",
        "CHATBOOK_PERSONAL_ENABLED",
        "CHATBOOK_FINANCIAL_SPACE",
        "CHATBOOK_OWNER_KIND",
    }
)
DEVELOPMENT_DATABASE_PATH = (Path(__file__).resolve().parents[1] / "chatbook.db").resolve()


class RuntimeStorageMode(StrEnum):
    ORGANIZATION_V3 = "organization-v3"
    CANONICAL_V4 = "canonical-v4"

    @property
    def schema_version(self) -> int:
        return 3 if self is RuntimeStorageMode.ORGANIZATION_V3 else 4


class RuntimeAccessMode(StrEnum):
    READ_ONLY = "read-only"
    READ_WRITE = "read-write"


def _package_release_identity() -> str:
    try:
        version = importlib.metadata.version("chatbook")
    except importlib.metadata.PackageNotFoundError:
        version = "uninstalled"
    return f"local-package:{version}"


def _runtime_error(code: str, message: str) -> ChatbookError:
    return ChatbookError(code, message)


def _normalize_mode(value: RuntimeStorageMode | str) -> RuntimeStorageMode:
    try:
        return value if isinstance(value, RuntimeStorageMode) else RuntimeStorageMode(value)
    except ValueError as exc:
        raise _runtime_error(
            "runtime_storage_mode",
            "CHATBOOK_STORAGE_MODE must be organization-v3 or canonical-v4.",
        ) from exc


def _normalize_access(value: RuntimeAccessMode | str) -> RuntimeAccessMode:
    try:
        return value if isinstance(value, RuntimeAccessMode) else RuntimeAccessMode(value)
    except ValueError as exc:
        raise _runtime_error(
            "runtime_access_mode",
            "CHATBOOK_RUNTIME_ACCESS must be read-only or read-write.",
        ) from exc


@dataclass(frozen=True, slots=True)
class RuntimeConfiguration:
    database_path: str
    storage_mode: RuntimeStorageMode
    expected_schema_version: int
    access_mode: RuntimeAccessMode
    release_id: str
    source: str

    @classmethod
    def explicit(
        cls,
        database_path: str | Path,
        *,
        storage_mode: RuntimeStorageMode | str,
        expected_schema_version: int,
        access_mode: RuntimeAccessMode | str,
        release_id: str,
        source: str = "explicit-server-configuration",
    ) -> "RuntimeConfiguration":
        mode = _normalize_mode(storage_mode)
        access = _normalize_access(access_mode)
        if type(expected_schema_version) is not int:
            raise _runtime_error("runtime_schema_version", "Schema version must be an integer.")
        if expected_schema_version != mode.schema_version:
            raise _runtime_error(
                "runtime_schema_mismatch",
                "Selected storage mode and configured schema version do not match.",
            )
        if (
            mode is RuntimeStorageMode.ORGANIZATION_V3
            and access is not RuntimeAccessMode.READ_WRITE
        ):
            raise _runtime_error(
                "runtime_access_mode",
                "organization-v3 supports the existing read-write runtime only.",
            )
        raw_path = str(database_path)
        if not raw_path.strip():
            raise _runtime_error("runtime_database_path", "Database path must not be empty.")
        normalized_release = release_id.strip() if isinstance(release_id, str) else ""
        if not normalized_release:
            raise _runtime_error("runtime_release_id", "Runtime release identity is required.")
        if mode is RuntimeStorageMode.CANONICAL_V4:
            if raw_path == ":memory:" or not Path(raw_path).is_absolute():
                raise _runtime_error(
                    "runtime_database_path",
                    "Canonical schema-v4 startup requires an explicit absolute database path.",
                )
            if Path(raw_path).resolve() == DEVELOPMENT_DATABASE_PATH:
                raise _runtime_error(
                    "runtime_development_database",
                    "The repository development chatbook.db cannot be selected for schema v4.",
                )
            if re.fullmatch(r"[0-9a-fA-F]{64}", normalized_release) is None:
                raise _runtime_error(
                    "runtime_release_id",
                    "Canonical schema-v4 startup requires a 64-character release SHA-256.",
                )
        return cls(raw_path, mode, expected_schema_version, access, normalized_release, source)

    @classmethod
    def organization_v3(cls, database_path: str | Path) -> "RuntimeConfiguration":
        return cls.explicit(
            database_path,
            storage_mode=RuntimeStorageMode.ORGANIZATION_V3,
            expected_schema_version=SCHEMA_VERSION,
            access_mode=RuntimeAccessMode.READ_WRITE,
            release_id=_package_release_identity(),
            source="legacy-v3-compatible",
        )

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        database_override: str | Path | None = None,
    ) -> "RuntimeConfiguration":
        values = os.environ if environment is None else environment
        forbidden = sorted(key for key in FORBIDDEN_RUNTIME_ENVIRONMENT_KEYS if key in values)
        if forbidden:
            raise _runtime_error(
                "runtime_forbidden_configuration",
                "Normal runtime configuration rejects rehearsal, PERSONAL, and raw-book settings: "
                + ", ".join(forbidden),
            )

        raw_mode = values.get(STORAGE_MODE_ENV, RuntimeStorageMode.ORGANIZATION_V3.value)
        mode = _normalize_mode(raw_mode)
        raw_access = values.get(ACCESS_MODE_ENV)
        if raw_access is None:
            if mode is RuntimeStorageMode.CANONICAL_V4:
                raise _runtime_error(
                    "runtime_access_mode",
                    "Canonical schema-v4 startup requires CHATBOOK_RUNTIME_ACCESS.",
                )
            access = RuntimeAccessMode.READ_WRITE
        else:
            access = _normalize_access(raw_access)
        raw_schema = values.get(SCHEMA_VERSION_ENV)
        if raw_schema is None:
            if mode is RuntimeStorageMode.CANONICAL_V4:
                raise _runtime_error(
                    "runtime_schema_version",
                    "Canonical schema-v4 startup requires CHATBOOK_SCHEMA_VERSION=4.",
                )
            expected_schema = SCHEMA_VERSION
        else:
            try:
                expected_schema = int(raw_schema)
            except ValueError as exc:
                raise _runtime_error(
                    "runtime_schema_version", "CHATBOOK_SCHEMA_VERSION must be an integer."
                ) from exc

        configured_path = values.get(DATABASE_PATH_ENV)
        if database_override is not None:
            if mode is RuntimeStorageMode.CANONICAL_V4:
                if (
                    configured_path is None
                    or Path(configured_path).resolve() != Path(database_override).resolve()
                ):
                    raise _runtime_error(
                        "runtime_database_path",
                        "Schema-v4 CLI database overrides must exactly match CHATBOOK_DB_PATH.",
                    )
            database_path = str(database_override)
        else:
            if mode is RuntimeStorageMode.CANONICAL_V4 and configured_path is None:
                raise _runtime_error(
                    "runtime_database_path",
                    "Canonical schema-v4 startup requires CHATBOOK_DB_PATH.",
                )
            database_path = configured_path or "chatbook.db"

        configured_release = values.get(RELEASE_ID_ENV)
        if mode is RuntimeStorageMode.CANONICAL_V4 and configured_release is None:
            raise _runtime_error(
                "runtime_release_id",
                "Canonical schema-v4 startup requires CHATBOOK_RUNTIME_RELEASE_ID.",
            )
        return cls.explicit(
            database_path,
            storage_mode=mode,
            expected_schema_version=expected_schema,
            access_mode=access,
            release_id=configured_release or _package_release_identity(),
            source="deployment-environment",
        )

    @property
    def resolved_database_path(self) -> Path:
        if self.database_path == ":memory:":
            raise _runtime_error(
                "runtime_database_path", "An in-memory database has no deployment file identity."
            )
        return Path(self.database_path).resolve()

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            {
                "database_path": str(self.resolved_database_path),
                "expected_schema_version": self.expected_schema_version,
                "access_mode": self.access_mode.value,
                "release_id": self.release_id,
                "storage_mode": self.storage_mode.value,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_runtime_database(configuration: RuntimeConfiguration) -> dict[str, object]:
    """Return sanitized read-only startup evidence and fail on incompatible storage."""
    path = configuration.resolved_database_path
    if not path.is_file():
        raise _runtime_error(
            "runtime_database_missing", "The selected runtime database does not exist."
        )
    connection = sqlite3.connect(
        f"{path.as_uri()}?mode=ro", uri=True, isolation_level=None, timeout=10
    )
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA foreign_keys = ON")
        actual_schema = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if actual_schema != configuration.expected_schema_version:
            raise _runtime_error(
                "runtime_schema_mismatch",
                "Selected database schema does not match the configured storage mode.",
            )
        integrity = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
        foreign_key_violations = len(tuple(connection.execute("PRAGMA foreign_key_check")))
        if integrity != ["ok"] or foreign_key_violations:
            raise _runtime_error(
                "runtime_database_integrity",
                "Selected database failed integrity or foreign-key validation.",
            )
        owner_kinds: list[str] = []
        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ledger_books'"
        ).fetchone():
            owner_kinds = [
                str(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT owner_kind FROM ledger_books ORDER BY owner_kind"
                )
            ]
        if any(owner_kind != "BUSINESS" for owner_kind in owner_kinds):
            raise _runtime_error(
                "runtime_owner_scope", "Normal M5.1 runtime supports BUSINESS books only."
            )
        if configuration.storage_mode is RuntimeStorageMode.CANONICAL_V4:
            verify_canonical_mapping(connection)
        return {
            "database_path": str(path),
            "database_bytes": path.stat().st_size,
            "database_sha256": _hash_file(path),
            "storage_mode": configuration.storage_mode.value,
            "expected_schema_version": configuration.expected_schema_version,
            "actual_schema_version": actual_schema,
            "access_mode": configuration.access_mode.value,
            "release_id": configuration.release_id,
            "configuration_source": configuration.source,
            "configuration_fingerprint": configuration.fingerprint,
            "owner_scope": "BUSINESS",
            "owner_kinds": owner_kinds,
            "integrity_check": integrity,
            "foreign_key_violation_count": foreign_key_violations,
            "sensitive_values_included": False,
        }
    finally:
        connection.close()


def open_runtime_database(
    configuration: RuntimeConfiguration, *, allow_thread_handoff: bool = False
) -> Database | CanonicalDatabase:
    """Open exactly the configured adapter; never migrate, downgrade, or fall back across modes."""
    if configuration.storage_mode is RuntimeStorageMode.CANONICAL_V4:
        inspect_runtime_database(configuration)
        database: Database | CanonicalDatabase = CanonicalDatabase(
            configuration.resolved_database_path,
            read_only=configuration.access_mode is RuntimeAccessMode.READ_ONLY,
            allow_thread_handoff=allow_thread_handoff,
        )
    else:
        database = Database(configuration.database_path, allow_thread_handoff=allow_thread_handoff)
    actual = int(database.connection.execute("PRAGMA user_version").fetchone()[0])
    if actual != configuration.expected_schema_version:
        database.close()
        raise _runtime_error(
            "runtime_schema_mismatch",
            "Opened database schema does not match the configured storage mode.",
        )
    return database


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatbook-runtime",
        description="Validate configured Chatbooks storage and emit sanitized read-only evidence.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--evidence", type=Path)
    arguments = parser.parse_args(argv)
    try:
        configuration = RuntimeConfiguration.from_environment()
        evidence = inspect_runtime_database(configuration)
        if cast(Path | None, arguments.evidence) is not None:
            _write_json(cast(Path, arguments.evidence), evidence)
    except (ChatbookError, OSError, sqlite3.Error) as exc:
        code = exc.code if isinstance(exc, ChatbookError) else type(exc).__name__
        print(json.dumps({"status": "failed", "error": code, "message": str(exc)}))
        return 2
    print(json.dumps({"status": "verified", **evidence}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
