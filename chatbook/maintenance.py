"""Server-owned maintenance gate and graceful-drain controls."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .domain import ChatbookError

CONTROL_PATH_ENV = "CHATBOOK_MAINTENANCE_CONTROL_PATH"
STATE_PATH_ENV = "CHATBOOK_MAINTENANCE_STATE_PATH"
CONTROL_VERSION = 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _read_object(path: Path, *, code: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChatbookError(code, f"Required operator control is unavailable: {path}") from exc
    if not isinstance(value, dict):
        raise ChatbookError(code, f"Required operator control is invalid: {path}")
    return cast(dict[str, object], value)


class MaintenanceMode(StrEnum):
    ACCEPTING = "accepting"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True, slots=True)
class MaintenancePaths:
    control: Path
    state: Path

    @classmethod
    def explicit(cls, control: str | Path, state: str | Path) -> MaintenancePaths:
        control_path = Path(control).resolve()
        state_path = Path(state).resolve()
        if control_path == state_path:
            raise ChatbookError(
                "maintenance_configuration", "Control and runtime-state paths must differ."
            )
        return cls(control_path, state_path)

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> MaintenancePaths | None:
        values = os.environ if environment is None else environment
        control = values.get(CONTROL_PATH_ENV)
        state = values.get(STATE_PATH_ENV)
        if control is None and state is None:
            return None
        if not control or not state:
            raise ChatbookError(
                "maintenance_configuration",
                f"{CONTROL_PATH_ENV} and {STATE_PATH_ENV} must be configured together.",
            )
        return cls.explicit(control, state)

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps(
            {
                "control_path": str(self.control),
                "state_path": str(self.state),
                "version": CONTROL_VERSION,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _validate_control(value: Mapping[str, object]) -> dict[str, object]:
    try:
        version = int(cast(int, value["version"]))
        mode = MaintenanceMode(str(value["mode"]))
        generation = int(cast(int, value["generation"]))
        changed_at = str(value["changed_at"])
        shutdown_requested = value["shutdown_requested"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ChatbookError(
            "maintenance_control_invalid", "Maintenance control has an invalid schema."
        ) from exc
    if version != CONTROL_VERSION or generation < 1 or not changed_at.strip():
        raise ChatbookError(
            "maintenance_control_invalid", "Maintenance control has invalid values."
        )
    if type(shutdown_requested) is not bool:
        raise ChatbookError(
            "maintenance_control_invalid", "Maintenance shutdown state must be a boolean."
        )
    return {
        "version": version,
        "mode": mode.value,
        "generation": generation,
        "changed_at": changed_at,
        "shutdown_requested": shutdown_requested,
        "reason": str(value.get("reason", "")),
    }


def read_maintenance_control(paths: MaintenancePaths) -> dict[str, object]:
    return _validate_control(_read_object(paths.control, code="maintenance_control_unavailable"))


def _stopped_state(paths: MaintenancePaths) -> dict[str, object]:
    return {
        "version": CONTROL_VERSION,
        "backend_state": "stopped",
        "pid": None,
        "in_flight": 0,
        "accepted_total": 0,
        "rejected_total": 0,
        "control_generation": 1,
        "control_mode": MaintenanceMode.ACCEPTING.value,
        "configuration_fingerprint": paths.fingerprint,
        "started_at": None,
        "updated_at": _now(),
        "last_error": None,
    }


def initialize_maintenance_control(paths: MaintenancePaths) -> None:
    """Create the initial stopped/accepting state without overwriting operator state."""
    if paths.control.exists():
        read_maintenance_control(paths)
    else:
        _write_json(
            paths.control,
            {
                "version": CONTROL_VERSION,
                "mode": MaintenanceMode.ACCEPTING.value,
                "generation": 1,
                "changed_at": _now(),
                "shutdown_requested": False,
                "reason": "initialized-stopped-runtime",
            },
        )
    if paths.state.exists():
        state = _read_object(paths.state, code="maintenance_state_unavailable")
        if int(cast(int, state.get("version", 0))) != CONTROL_VERSION:
            raise ChatbookError(
                "maintenance_state_invalid", "Maintenance runtime state has an invalid version."
            )
    else:
        _write_json(paths.state, _stopped_state(paths))


class MaintenanceController:
    """Local operator control; it is intentionally not exposed over HTTP."""

    def __init__(self, paths: MaintenancePaths) -> None:
        self.paths = paths

    def status(self) -> dict[str, object]:
        control = read_maintenance_control(self.paths)
        state = _read_object(self.paths.state, code="maintenance_state_unavailable")
        return {
            "status": "verified",
            "configuration_fingerprint": self.paths.fingerprint,
            "control": control,
            "runtime": {
                "backend_state": state.get("backend_state"),
                "pid": state.get("pid"),
                "in_flight": state.get("in_flight"),
                "accepted_total": state.get("accepted_total"),
                "rejected_total": state.get("rejected_total"),
                "control_generation": state.get("control_generation"),
                "control_mode": state.get("control_mode"),
                "started_at": state.get("started_at"),
                "updated_at": state.get("updated_at"),
                "last_error": state.get("last_error"),
            },
            "sensitive_values_included": False,
        }

    def _transition(
        self,
        *,
        expected: MaintenanceMode,
        target: MaintenanceMode,
        reason: str,
        shutdown_requested: bool = False,
    ) -> dict[str, object]:
        current = read_maintenance_control(self.paths)
        if current["mode"] != expected.value:
            raise ChatbookError(
                "maintenance_transition",
                f"Maintenance transition requires {expected.value} mode.",
            )
        normalized_reason = reason.strip()
        if not normalized_reason or len(normalized_reason) > 200 or "\n" in normalized_reason:
            raise ChatbookError(
                "maintenance_reason", "Maintenance reason must be 1-200 single-line characters."
            )
        updated: dict[str, object] = {
            "version": CONTROL_VERSION,
            "mode": target.value,
            "generation": int(cast(int, current["generation"])) + 1,
            "changed_at": _now(),
            "shutdown_requested": shutdown_requested,
            "reason": normalized_reason,
        }
        _write_json(self.paths.control, updated)
        return updated

    def enter_drain(self, reason: str) -> dict[str, object]:
        return self._transition(
            expected=MaintenanceMode.ACCEPTING,
            target=MaintenanceMode.DRAINING,
            reason=reason,
        )

    def wait_for_drain(self, timeout_seconds: float) -> dict[str, object]:
        if timeout_seconds <= 0:
            raise ChatbookError("maintenance_timeout", "Drain timeout must be greater than zero.")
        started = time.monotonic()
        while True:
            control = read_maintenance_control(self.paths)
            if control["mode"] != MaintenanceMode.DRAINING.value:
                raise ChatbookError("maintenance_transition", "Drain wait requires draining mode.")
            state = _read_object(self.paths.state, code="maintenance_state_unavailable")
            try:
                in_flight = int(cast(int, state["in_flight"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ChatbookError(
                    "maintenance_state_invalid", "In-flight request state is invalid."
                ) from exc
            if in_flight == 0:
                return {
                    "status": "drained",
                    "in_flight": 0,
                    "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
                    "control_generation": control["generation"],
                }
            if time.monotonic() - started >= timeout_seconds:
                raise ChatbookError(
                    "maintenance_drain_timeout", "In-flight requests did not drain to zero."
                )
            time.sleep(min(0.05, timeout_seconds))

    def seal(self, reason: str) -> dict[str, object]:
        state = _read_object(self.paths.state, code="maintenance_state_unavailable")
        if int(cast(int, state.get("in_flight", -1))) != 0:
            raise ChatbookError(
                "maintenance_in_flight", "Maintenance cannot be sealed with active requests."
            )
        return self._transition(
            expected=MaintenanceMode.DRAINING,
            target=MaintenanceMode.MAINTENANCE,
            reason=reason,
        )

    def request_shutdown(self, reason: str) -> dict[str, object]:
        state = _read_object(self.paths.state, code="maintenance_state_unavailable")
        if int(cast(int, state.get("in_flight", -1))) != 0:
            raise ChatbookError(
                "maintenance_in_flight", "Backend shutdown requires zero in-flight requests."
            )
        return self._transition(
            expected=MaintenanceMode.MAINTENANCE,
            target=MaintenanceMode.MAINTENANCE,
            reason=reason,
            shutdown_requested=True,
        )

    def reset_stopped(self, reason: str) -> dict[str, object]:
        state = _read_object(self.paths.state, code="maintenance_state_unavailable")
        if (
            state.get("backend_state") != "stopped"
            or int(cast(int, state.get("in_flight", -1))) != 0
        ):
            raise ChatbookError(
                "maintenance_runtime_active",
                "Maintenance can return to accepting only while the backend is stopped.",
            )
        return self._transition(
            expected=MaintenanceMode.MAINTENANCE,
            target=MaintenanceMode.ACCEPTING,
            reason=reason,
        )


class MaintenanceGate:
    def __init__(self, paths: MaintenancePaths) -> None:
        self.paths = paths
        read_maintenance_control(paths)
        self._lock = asyncio.Lock()
        self._backend_state = "starting"
        self._in_flight = 0
        self._accepted_total = 0
        self._rejected_total = 0
        self._started_at: str | None = None
        self._last_error: str | None = None

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> MaintenanceGate | None:
        paths = MaintenancePaths.from_environment(environment)
        return None if paths is None else cls(paths)

    def _state(self, control: Mapping[str, object]) -> dict[str, object]:
        return {
            "version": CONTROL_VERSION,
            "backend_state": self._backend_state,
            "pid": os.getpid() if self._backend_state == "running" else None,
            "in_flight": self._in_flight,
            "accepted_total": self._accepted_total,
            "rejected_total": self._rejected_total,
            "control_generation": control.get("generation"),
            "control_mode": control.get("mode"),
            "configuration_fingerprint": self.paths.fingerprint,
            "started_at": self._started_at,
            "updated_at": _now(),
            "last_error": self._last_error,
        }

    async def start(self) -> None:
        async with self._lock:
            control = read_maintenance_control(self.paths)
            if control["mode"] != MaintenanceMode.ACCEPTING.value or control["shutdown_requested"]:
                raise ChatbookError(
                    "maintenance_startup_blocked",
                    "Backend startup requires accepting mode with no shutdown request.",
                )
            self._backend_state = "running"
            self._started_at = _now()
            self._last_error = None
            _write_json(self.paths.state, self._state(control))

    async def stop(self) -> None:
        async with self._lock:
            try:
                control = read_maintenance_control(self.paths)
            except ChatbookError:
                control = {
                    "generation": None,
                    "mode": "invalid",
                }
            self._backend_state = "stopped"
            _write_json(self.paths.state, self._state(control))

    async def accept(self) -> tuple[bool, str]:
        async with self._lock:
            try:
                control = read_maintenance_control(self.paths)
                mode = str(control["mode"])
                allowed = mode == MaintenanceMode.ACCEPTING.value and not bool(
                    control["shutdown_requested"]
                )
                self._last_error = None
            except ChatbookError as exc:
                control = {"generation": None, "mode": "invalid"}
                mode = "invalid"
                allowed = False
                self._last_error = exc.code
            if allowed:
                self._in_flight += 1
                self._accepted_total += 1
            else:
                self._rejected_total += 1
            _write_json(self.paths.state, self._state(control))
            return allowed, mode

    async def release(self) -> None:
        async with self._lock:
            if self._in_flight <= 0:
                raise RuntimeError("Maintenance in-flight request count underflow.")
            self._in_flight -= 1
            try:
                control = read_maintenance_control(self.paths)
            except ChatbookError as exc:
                control = {"generation": None, "mode": "invalid"}
                self._last_error = exc.code
            _write_json(self.paths.state, self._state(control))


class MaintenanceMiddleware:
    def __init__(self, app: ASGIApp, *, gate: MaintenanceGate) -> None:
        self.app = app
        self.gate = gate

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        accepted, mode = await self.gate.accept()
        if not accepted:
            response = JSONResponse(
                status_code=503,
                content={
                    "error": "maintenance_mode",
                    "message": "Chatbooks is temporarily unavailable for controlled maintenance.",
                    "request_id": "maintenance-gate",
                    "details": {"state": mode},
                },
                headers={"Cache-Control": "no-store"},
            )
            await response(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        finally:
            await self.gate.release()


def shutdown_requested(paths: MaintenancePaths) -> bool:
    """Return a fail-closed shutdown decision for the controlled server watcher."""
    try:
        control = read_maintenance_control(paths)
    except ChatbookError:
        return True
    return bool(control["shutdown_requested"])


def _paths_from_arguments(arguments: argparse.Namespace) -> MaintenancePaths:
    return MaintenancePaths.explicit(arguments.control, arguments.state)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatbook-traffic-control",
        description="Operate the local server-owned maintenance gate; never changes ledger data.",
    )
    parser.add_argument("--control", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("initialize")
    commands.add_parser("status")
    enter = commands.add_parser("enter")
    enter.add_argument("--reason", required=True)
    wait = commands.add_parser("wait")
    wait.add_argument("--timeout-seconds", required=True, type=float)
    seal = commands.add_parser("seal")
    seal.add_argument("--reason", required=True)
    shutdown = commands.add_parser("request-shutdown")
    shutdown.add_argument("--reason", required=True)
    reset = commands.add_parser("reset-stopped")
    reset.add_argument("--reason", required=True)
    arguments = parser.parse_args(argv)
    try:
        paths = _paths_from_arguments(arguments)
        controller = MaintenanceController(paths)
        if arguments.command == "initialize":
            initialize_maintenance_control(paths)
            result: dict[str, Any] = controller.status()
        elif arguments.command == "status":
            result = controller.status()
        elif arguments.command == "enter":
            result = {"status": "draining", **controller.enter_drain(arguments.reason)}
        elif arguments.command == "wait":
            result = controller.wait_for_drain(arguments.timeout_seconds)
        elif arguments.command == "seal":
            result = {"status": "maintenance", **controller.seal(arguments.reason)}
        elif arguments.command == "request-shutdown":
            result = {
                "status": "shutdown-requested",
                **controller.request_shutdown(arguments.reason),
            }
        else:
            result = {"status": "accepting", **controller.reset_stopped(arguments.reason)}
    except (ChatbookError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, ChatbookError) else type(exc).__name__
        print(json.dumps({"status": "failed", "error": code, "message": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
