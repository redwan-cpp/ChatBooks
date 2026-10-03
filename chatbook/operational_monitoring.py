"""Deterministic read-only operational signal collection for controlled C4 staging."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from .canonical_schema import CANONICAL_SCHEMA_VERSION, verify_canonical_mapping
from .domain import ChatbookError
from .migration_evidence import PreflightFailure, build_preflight_manifest

MONITOR_VERSION = 1
REQUIRES_OPERATOR_DECISION = "REQUIRES_OPERATOR_DECISION"
BASELINE_REQUIRED = "BASELINE_REQUIRED"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class MonitoringPhase(StrEnum):
    PRE_CUTOVER_V3 = "PRE_CUTOVER_V3"
    POST_MIGRATION_READ_ONLY_V4 = "POST_MIGRATION_READ_ONLY_V4"
    POST_RESUMPTION_V4 = "POST_RESUMPTION_V4"


class SignalState(StrEnum):
    PASS = "PASS"
    ALERT = "ALERT"
    BASELINE_REQUIRED = BASELINE_REQUIRED
    REQUIRES_OPERATOR_DECISION = REQUIRES_OPERATOR_DECISION
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class MonitoringConfiguration:
    database_path: Path
    expected_schema_version: int
    phase: MonitoringPhase
    expected_manifest_path: Path | None
    application_log_path: Path | None
    migration_report_path: Path | None
    monitoring_owner: str
    escalation_owner: str
    observation_period: str
    alert_destination: str
    stop_or_rollback_authority: str

    @classmethod
    def from_file(cls, path: str | Path) -> MonitoringConfiguration:
        config_path = Path(path).resolve()
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ChatbookError(
                "monitoring_configuration", "Monitoring configuration is unavailable or invalid."
            ) from exc
        if not isinstance(raw, dict) or raw.get("version") != MONITOR_VERSION:
            raise ChatbookError(
                "monitoring_configuration", "Monitoring configuration version is invalid."
            )
        try:
            database_path = Path(str(raw["database_path"])).resolve()
            expected_schema = int(raw["expected_schema_version"])
            phase = MonitoringPhase(str(raw["phase"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ChatbookError(
                "monitoring_configuration", "Required monitoring configuration is invalid."
            ) from exc
        expected_for_phase = 3 if phase is MonitoringPhase.PRE_CUTOVER_V3 else 4
        if expected_schema != expected_for_phase:
            raise ChatbookError(
                "monitoring_configuration",
                "Monitoring phase and expected schema version do not match.",
            )

        def optional_path(key: str) -> Path | None:
            value = raw.get(key)
            return None if value is None else Path(str(value)).resolve()

        decisions = raw.get("operator_decisions")
        if not isinstance(decisions, dict):
            raise ChatbookError(
                "monitoring_configuration", "Operator-decision placeholders are required."
            )
        decision_values = {
            name: str(decisions.get(name, ""))
            for name in (
                "monitoring_owner",
                "escalation_owner",
                "observation_period",
                "alert_destination",
                "stop_or_rollback_authority",
            )
        }
        if any(value != REQUIRES_OPERATOR_DECISION for value in decision_values.values()):
            raise ChatbookError(
                "monitoring_configuration",
                "Unapproved monitoring ownership values must remain REQUIRES_OPERATOR_DECISION.",
            )
        baselines = raw.get("baselines")
        if not isinstance(baselines, dict) or any(
            value != BASELINE_REQUIRED for value in baselines.values()
        ):
            raise ChatbookError(
                "monitoring_configuration",
                "Unapproved monitoring thresholds must remain BASELINE_REQUIRED.",
            )
        return cls(
            database_path=database_path,
            expected_schema_version=expected_schema,
            phase=phase,
            expected_manifest_path=optional_path("expected_manifest_path"),
            application_log_path=optional_path("application_log_path"),
            migration_report_path=optional_path("migration_report_path"),
            monitoring_owner=decision_values["monitoring_owner"],
            escalation_owner=decision_values["escalation_owner"],
            observation_period=decision_values["observation_period"],
            alert_destination=decision_values["alert_destination"],
            stop_or_rollback_authority=decision_values["stop_or_rollback_authority"],
        )

    @property
    def fingerprint(self) -> str:
        return _json_hash(
            {
                "database_path": str(self.database_path),
                "expected_schema_version": self.expected_schema_version,
                "phase": self.phase.value,
                "expected_manifest_path": (
                    None
                    if self.expected_manifest_path is None
                    else str(self.expected_manifest_path)
                ),
                "application_log_path": (
                    None if self.application_log_path is None else str(self.application_log_path)
                ),
                "migration_report_path": (
                    None if self.migration_report_path is None else str(self.migration_report_path)
                ),
                "version": MONITOR_VERSION,
            }
        )


def _signal(
    name: str,
    classification: str,
    state: SignalState,
    diagnostic: str,
    *,
    metrics: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        "signal": name,
        "classification": classification,
        "state": state.value,
        "diagnostic": diagnostic,
        "metrics": dict(metrics or {}),
    }


def _read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ChatbookError("monitor_database_missing", "Monitored database does not exist.")
    connection = sqlite3.connect(
        f"{path.as_uri()}?mode=ro", uri=True, isolation_level=None, timeout=10
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _idempotency_disagreements(
    connection: sqlite3.Connection, schema_version: int
) -> tuple[int, int]:
    scope = "organization_id" if schema_version == 3 else "ledger_book_id"
    receipts = tuple(connection.execute("SELECT * FROM command_idempotency ORDER BY id"))
    disagreements = 0
    contracts = {
        "transaction.confirm": ("confirmation", "confirmations"),
        "transaction.post": ("journal_entry", "journal_entries"),
    }
    for receipt in receipts:
        contract = contracts.get(str(receipt["operation"]))
        if contract is None or receipt["resource_type"] != contract[0]:
            disagreements += 1
            continue
        table = contract[1]
        found = connection.execute(
            f"SELECT 1 FROM {table} WHERE id = ? AND {scope} = ?",  # noqa: S608
            (receipt["resource_id"], receipt[scope]),
        ).fetchone()
        if found is None:
            disagreements += 1
    return len(receipts), disagreements


def _ledger_mismatches(connection: sqlite3.Connection) -> dict[str, int]:
    result = connection.execute(
        "SELECT count(*) AS entries, "
        "sum(CASE WHEN state != 'posted' OR line_count < 2 OR debits != credits "
        "THEN 1 ELSE 0 END) AS mismatches FROM ("
        "SELECT e.id, e.state, count(l.id) AS line_count, "
        "coalesce(sum(l.debit), 0) AS debits, coalesce(sum(l.credit), 0) AS credits "
        "FROM journal_entries e LEFT JOIN journal_lines l ON l.entry_id = e.id GROUP BY e.id"
        ")"
    ).fetchone()
    return {
        "journal_entries": int(result["entries"]),
        "mismatches": int(result["mismatches"] or 0),
    }


def _audit_sidecar_mismatches(
    connection: sqlite3.Connection, schema_version: int
) -> dict[str, int] | None:
    if schema_version != CANONICAL_SCHEMA_VERSION:
        return None
    missing = int(
        connection.execute(
            "SELECT count(*) FROM audit_events a LEFT JOIN audit_event_book_scopes s "
            "ON s.audit_sequence = a.sequence WHERE a.entity_type IN "
            "('charts_of_accounts','accounts','accounting_periods','transactions',"
            "'transaction_lines','validations','confirmations','journal_entries','journal_lines') "
            "AND s.audit_sequence IS NULL"
        ).fetchone()[0]
    )
    wrong = int(
        connection.execute(
            "SELECT count(*) FROM audit_event_book_scopes s JOIN audit_events a "
            "ON a.sequence = s.audit_sequence JOIN ledger_books b ON b.id = s.ledger_book_id "
            "WHERE a.organization_id IS NOT b.organization_id"
        ).fetchone()[0]
    )
    return {"missing": missing, "wrong_scope": wrong}


def _safe_log_metrics(path: Path | None) -> dict[str, object]:
    metrics: dict[str, object] = {
        "available": False,
        "http_requests": 0,
        "chatbook_errors": 0,
        "database_errors": 0,
        "financial_command_errors": 0,
        "latency_samples": 0,
        "maximum_duration_ms": None,
    }
    if path is None or not path.is_file():
        return metrics
    durations: list[float] = []
    chatbook_errors = 0
    database_errors = 0
    financial_errors = 0
    requests = 0
    financial_fragments = ("/proposals", "/journal-entries", "/periods/")
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        candidate = raw_line[raw_line.find("{") :] if "{" in raw_line else ""
        try:
            event = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("event") == "http_request":
            requests += 1
            duration = event.get("duration_ms")
            if isinstance(duration, int | float):
                durations.append(float(duration))
        elif event.get("event") == "chatbook_error":
            chatbook_errors += 1
            code = str(event.get("error", ""))
            route = str(event.get("path", ""))
            if code in {"database_error", "sqlite_error"}:
                database_errors += 1
            if any(fragment in route for fragment in financial_fragments):
                financial_errors += 1
    metrics.update(
        {
            "available": True,
            "http_requests": requests,
            "chatbook_errors": chatbook_errors,
            "database_errors": database_errors,
            "financial_command_errors": financial_errors,
            "latency_samples": len(durations),
            "maximum_duration_ms": None if not durations else max(durations),
        }
    )
    return metrics


def collect_monitoring(configuration: MonitoringConfiguration) -> dict[str, object]:
    generated_at = _now()
    signals: list[dict[str, object]] = []
    diagnostics: tuple[str, ...] = ()
    connection = _read_only(configuration.database_path)
    try:
        schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        schema_ok = schema_version == configuration.expected_schema_version
        signals.append(
            _signal(
                "schema_version",
                "HARD_INVARIANT",
                SignalState.PASS if schema_ok else SignalState.ALERT,
                "actual schema matches the configured phase"
                if schema_ok
                else "actual schema differs from the configured phase",
                metrics={
                    "expected": configuration.expected_schema_version,
                    "actual": schema_version,
                },
            )
        )
        integrity = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
        signals.append(
            _signal(
                "database_integrity",
                "HARD_INVARIANT",
                SignalState.PASS if integrity == ["ok"] else SignalState.ALERT,
                "integrity_check returned ok"
                if integrity == ["ok"]
                else "integrity_check returned a non-ok result",
                metrics={"ok": integrity == ["ok"], "result_count": len(integrity)},
            )
        )
        foreign_keys = len(tuple(connection.execute("PRAGMA foreign_key_check")))
        signals.append(
            _signal(
                "foreign_key_violations",
                "HARD_INVARIANT",
                SignalState.PASS if foreign_keys == 0 else SignalState.ALERT,
                "no foreign-key violations" if foreign_keys == 0 else "violations detected",
                metrics={"violation_count": foreign_keys},
            )
        )
        if schema_version in {3, 4}:
            receipts, disagreements = _idempotency_disagreements(connection, schema_version)
        else:
            receipts, disagreements = 0, 1
        signals.append(
            _signal(
                "idempotency_disagreement",
                "HARD_INVARIANT",
                SignalState.PASS if disagreements == 0 else SignalState.ALERT,
                "all receipts resolve to the contracted resource"
                if disagreements == 0
                else "receipt/resource disagreement detected",
                metrics={"receipt_count": receipts, "disagreement_count": disagreements},
            )
        )
        ledger = _ledger_mismatches(connection)
        signals.append(
            _signal(
                "ledger_reconciliation",
                "HARD_INVARIANT",
                SignalState.PASS if ledger["mismatches"] == 0 else SignalState.ALERT,
                "all posted entries contain at least two balanced lines"
                if ledger["mismatches"] == 0
                else "unbalanced or structurally invalid journal entry detected",
                metrics=ledger,
            )
        )
        sidecars = _audit_sidecar_mismatches(connection, schema_version)
        if sidecars is None:
            signals.append(
                _signal(
                    "audit_sidecar_coverage",
                    "HARD_INVARIANT",
                    SignalState.NOT_APPLICABLE,
                    "audit sidecars begin with canonical schema v4",
                )
            )
        else:
            try:
                verify_canonical_mapping(connection)
                canonical_invalid = False
            except sqlite3.DatabaseError:
                canonical_invalid = True
            sidecar_invalid = canonical_invalid or any(sidecars.values())
            signals.append(
                _signal(
                    "audit_sidecar_coverage",
                    "HARD_INVARIANT",
                    SignalState.ALERT if sidecar_invalid else SignalState.PASS,
                    "canonical audit sidecar coverage is exact"
                    if not sidecar_invalid
                    else "canonical audit sidecar coverage mismatch detected",
                    metrics=sidecars,
                )
            )
    finally:
        connection.close()

    report_classification = "HARD_INVARIANT"
    if configuration.expected_manifest_path is not None and schema_version == 3:
        try:
            expected = json.loads(configuration.expected_manifest_path.read_text(encoding="utf-8"))
            if not isinstance(expected, dict):
                raise ValueError("manifest must be an object")
            build_preflight_manifest(
                configuration.database_path,
                database_identity="operational-monitor-read-only",
                expected_manifest=expected,
            )
            report_state = SignalState.PASS
            report_diagnostic = "approved v3 report fingerprints and content fingerprint match"
        except PreflightFailure as exc:
            diagnostics = exc.diagnostics
            report_state = SignalState.ALERT
            report_diagnostic = "preflight or report reconciliation diagnostic detected"
        except (OSError, json.JSONDecodeError, ValueError):
            diagnostics = ("monitor.expected_manifest_unavailable",)
            report_state = SignalState.ALERT
            report_diagnostic = "expected report baseline is unavailable or invalid"
    elif configuration.phase is MonitoringPhase.PRE_CUTOVER_V3:
        diagnostics = ("monitor.expected_manifest_missing",)
        report_state = SignalState.ALERT
        report_diagnostic = "pre-cutover report baseline is required"
    elif (
        configuration.phase is MonitoringPhase.POST_MIGRATION_READ_ONLY_V4
        and configuration.migration_report_path is not None
        and configuration.migration_report_path.is_file()
    ):
        try:
            migration_baseline = json.loads(
                configuration.migration_report_path.read_text(encoding="utf-8")
            )
            report_matches = (
                isinstance(migration_baseline, dict)
                and migration_baseline.get("status") == "complete"
                and migration_baseline.get("schema_version") == 4
                and migration_baseline.get("target_sha256")
                == _hash_file(configuration.database_path)
            )
        except (OSError, json.JSONDecodeError):
            report_matches = False
        report_state = SignalState.PASS if report_matches else SignalState.ALERT
        report_diagnostic = (
            "read-only v4 database matches the accepted migration artifact"
            if report_matches
            else "read-only v4 database differs from the accepted migration artifact"
        )
    else:
        report_classification = "BASELINE_DEPENDENT"
        report_state = SignalState.BASELINE_REQUIRED
        report_diagnostic = (
            "post-resumption report comparison requires an approved rolling baseline"
        )
    signals.append(
        _signal(
            "report_reconciliation",
            report_classification,
            report_state,
            report_diagnostic,
            metrics={"diagnostic_codes": list(diagnostics)},
        )
    )

    log_metrics = _safe_log_metrics(configuration.application_log_path)
    signals.extend(
        (
            _signal(
                "sqlite_lock_or_write_failures",
                "BASELINE_DEPENDENT",
                SignalState.BASELINE_REQUIRED,
                "events are collected; an operator-approved frequency threshold is required",
                metrics={
                    "log_available": log_metrics["available"],
                    "database_errors": log_metrics["database_errors"],
                },
            ),
            _signal(
                "financial_command_errors",
                "BASELINE_DEPENDENT",
                SignalState.BASELINE_REQUIRED,
                "stable error codes are collected; an operator-approved threshold is required",
                metrics={
                    "log_available": log_metrics["available"],
                    "error_count": log_metrics["financial_command_errors"],
                },
            ),
            _signal(
                "latency",
                "BASELINE_DEPENDENT",
                SignalState.BASELINE_REQUIRED,
                "request durations are collected; an operator-approved threshold is required",
                metrics={
                    "log_available": log_metrics["available"],
                    "samples": log_metrics["latency_samples"],
                    "maximum_duration_ms": log_metrics["maximum_duration_ms"],
                },
            ),
        )
    )

    if configuration.phase is MonitoringPhase.PRE_CUTOVER_V3:
        migration_state = SignalState.NOT_APPLICABLE
        migration_diagnostic = "no migration is permitted in the pre-cutover v3 phase"
        migration_metrics: dict[str, object] = {}
    elif (
        configuration.migration_report_path is None
        or not configuration.migration_report_path.is_file()
    ):
        migration_state = SignalState.ALERT
        migration_diagnostic = "required sanitized migration report is unavailable"
        migration_metrics = {}
    else:
        try:
            migration_report = json.loads(
                configuration.migration_report_path.read_text(encoding="utf-8")
            )
            migration_ok = (
                isinstance(migration_report, dict) and migration_report.get("status") == "complete"
            )
        except (OSError, json.JSONDecodeError):
            migration_ok = False
        migration_state = SignalState.PASS if migration_ok else SignalState.ALERT
        migration_diagnostic = (
            "sanitized migration report records completion"
            if migration_ok
            else "migration report records failure or is invalid"
        )
        migration_metrics = {"report_present": True}
    signals.append(
        _signal(
            "migration_failures",
            "HARD_INVARIANT",
            migration_state,
            migration_diagnostic,
            metrics=migration_metrics,
        )
    )
    signals.append(
        _signal(
            "protected_artifact_access",
            "OPERATOR_CONTROL",
            SignalState.REQUIRES_OPERATOR_DECISION,
            "Windows object-access audit source and alert destination are not configured",
        )
    )

    hard_alerts = [
        str(signal["signal"])
        for signal in signals
        if signal["classification"] == "HARD_INVARIANT"
        and signal["state"]
        in {SignalState.ALERT.value, SignalState.REQUIRES_OPERATOR_DECISION.value}
    ]
    return {
        "tool_version": "m5.1-c4p5-v1",
        "generated_at": generated_at,
        "status": "FAILED_CLOSED" if hard_alerts else "COLLECTED",
        "phase": configuration.phase.value,
        "configuration_fingerprint": configuration.fingerprint,
        "database": {
            "path_sha256": hashlib.sha256(
                str(configuration.database_path).encode("utf-8")
            ).hexdigest(),
            "bytes": configuration.database_path.stat().st_size,
            "sha256": _hash_file(configuration.database_path),
        },
        "signals": signals,
        "hard_alerts": hard_alerts,
        "operator_decisions": {
            "monitoring_owner": configuration.monitoring_owner,
            "escalation_owner": configuration.escalation_owner,
            "observation_period": configuration.observation_period,
            "alert_destination": configuration.alert_destination,
            "stop_or_rollback_authority": configuration.stop_or_rollback_authority,
        },
        "automatic_repair": False,
        "automatic_rollback": False,
        "financial_mutation": False,
        "sensitive_values_included": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatbook-c4-monitor",
        description="Collect sanitized read-only C4 operational signals.",
    )
    parser.add_argument("configuration", type=Path)
    parser.add_argument("--evidence", type=Path)
    arguments = parser.parse_args(argv)
    try:
        configuration = MonitoringConfiguration.from_file(arguments.configuration)
        evidence = collect_monitoring(configuration)
        if arguments.evidence is not None:
            _write_json(arguments.evidence, evidence)
    except (ChatbookError, OSError, sqlite3.Error) as exc:
        code = exc.code if isinstance(exc, ChatbookError) else type(exc).__name__
        print(json.dumps({"status": "FAILED_CLOSED", "error": code, "message": str(exc)}))
        return 2
    print(json.dumps(evidence, sort_keys=True))
    return 2 if evidence["status"] == "FAILED_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
