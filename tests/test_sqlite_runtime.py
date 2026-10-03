"""Python 3.14 SQLite request-lifecycle and concurrent API regression tests."""

import sqlite3
import tempfile
import threading
import unittest
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request

from chatbook import AccountingEngine
from chatbook.api.main import create_app, get_auth_service, get_engine, run
from chatbook.auth import AuthService
from chatbook.database import Database


def _next_with_thread[T](generator: Generator[T]) -> tuple[T, int]:
    return next(generator), threading.get_ident()


def _call_with_thread[T](operation: Callable[[], T]) -> tuple[T, int]:
    return operation(), threading.get_ident()


def _finish_with_thread(generator: Generator[object]) -> int:
    try:
        next(generator)
    except StopIteration:
        return threading.get_ident()
    raise AssertionError("Request dependency yielded more than once.")


class SQLiteRuntimeThreadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database = Path(self.temporary.name) / "runtime.db"

        auth = AuthService(self.database)
        try:
            user = auth.register(
                "Runtime Owner", "runtime-owner@example.test", "correct horse battery"
            )
            session = auth.login("runtime-owner@example.test", "correct horse battery")
        finally:
            auth.close()
        self.actor = user.id
        self.token = session.access_token
        engine = AccountingEngine(self.database)
        try:
            self.organization = engine.create_organization(self.actor, "Runtime Test", "BDT", 2)
        finally:
            engine.close()
        self.application = create_app(self.database)

    def _request(self) -> Request:
        return Request(
            {
                "type": "http",
                "app": self.application,
                "method": "GET",
                "path": "/",
                "headers": [],
            }
        )

    def test_request_dependencies_allow_sequential_worker_handoff_and_close(self) -> None:
        engine_dependency = get_engine(self._request())
        auth_dependency = get_auth_service(self._request())

        with (
            ThreadPoolExecutor(max_workers=1) as creator,
            ThreadPoolExecutor(max_workers=1) as user,
            ThreadPoolExecutor(max_workers=1) as closer,
        ):
            engine_finished = False
            auth_finished = False
            try:
                engine, engine_created_thread = creator.submit(
                    _next_with_thread, engine_dependency
                ).result(timeout=5)
                service, auth_created_thread = creator.submit(
                    _next_with_thread, auth_dependency
                ).result(timeout=5)

                projects, engine_used_thread = user.submit(
                    _call_with_thread,
                    lambda: engine.list_projects(self.actor, self.organization),
                ).result(timeout=5)
                authenticated, auth_used_thread = user.submit(
                    _call_with_thread, lambda: service.authenticate(self.token)
                ).result(timeout=5)

                engine_closed_thread = closer.submit(_finish_with_thread, engine_dependency).result(
                    timeout=5
                )
                engine_finished = True
                auth_closed_thread = closer.submit(_finish_with_thread, auth_dependency).result(
                    timeout=5
                )
                auth_finished = True
            finally:
                if not engine_finished:
                    creator.submit(_finish_with_thread, engine_dependency).result(timeout=5)
                if not auth_finished:
                    creator.submit(_finish_with_thread, auth_dependency).result(timeout=5)

        self.assertEqual(projects, ())
        self.assertEqual(authenticated.id, self.actor)
        self.assertEqual(
            len(
                {
                    engine_created_thread,
                    engine_used_thread,
                    engine_closed_thread,
                }
            ),
            3,
        )
        self.assertEqual(
            len({auth_created_thread, auth_used_thread, auth_closed_thread}),
            3,
        )

    def test_non_api_connections_retain_creator_thread_enforcement(self) -> None:
        engine = AccountingEngine(self.database)
        try:
            with ThreadPoolExecutor(max_workers=1) as worker:
                future = worker.submit(engine.list_projects, self.actor, self.organization)
                with self.assertRaisesRegex(sqlite3.ProgrammingError, "created in a thread"):
                    future.result(timeout=5)
        finally:
            engine.close()

    def test_normal_sqlite_runtime_enforces_one_uvicorn_worker(self) -> None:
        with (
            patch(
                "chatbook.api.main.MaintenancePaths.from_environment",
                return_value=None,
            ),
            patch("chatbook.api.main.uvicorn.run") as uvicorn_run,
        ):
            run()

        self.assertEqual(uvicorn_run.call_args.kwargs["workers"], 1)


class SQLiteRuntimeApiConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database = Path(self.temporary.name) / "concurrent-api.db"
        self.application = create_app(self.database)
        self.client = TestClient(self.application)
        self.addCleanup(self.client.close)

        owner = self._register("Owner", "owner@example.test")
        self.actor = str(owner["id"])
        self.headers = self._login("owner@example.test")
        organization = self.client.post(
            "/api/v1/organizations",
            json={"name": "Concurrent Studio", "currency": "BDT", "minor_unit_digits": 2},
            headers=self.headers,
        )
        self.assertEqual(organization.status_code, 201, organization.text)
        self.organization = str(organization.json()["id"])
        self.bank = self._create_account("1000", "Bank", "asset")
        self.revenue = self._create_account("4000", "Revenue", "revenue")
        period = self.client.post(
            f"/api/v1/organizations/{self.organization}/periods",
            json={
                "name": "September",
                "starts_on": "2026-09-01",
                "ends_on": "2026-09-30",
            },
            headers=self.headers,
        )
        self.assertEqual(period.status_code, 201, period.text)

    def _register(self, name: str, username: str) -> dict[str, object]:
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "name": name,
                "username": username,
                "password": "correct horse battery",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return cast(dict[str, object], response.json())

    def _login(self, username: str) -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/token",
            json={"username": username, "password": "correct horse battery"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def _create_account(self, code: str, name: str, account_type: str) -> str:
        response = self.client.post(
            f"/api/v1/organizations/{self.organization}/accounts",
            json={"code": code, "name": name, "account_type": account_type},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return str(response.json()["id"])

    def _confirmed_proposal(self, suffix: str, value: int = 1_250) -> tuple[str, str]:
        proposal = self.client.post(
            f"/api/v1/organizations/{self.organization}/proposals",
            json={
                "entry_date": "2026-09-15",
                "description": f"Concurrent posting {suffix}",
                "lines": [
                    {"account_id": self.bank, "debit": value},
                    {"account_id": self.revenue, "credit": value},
                ],
            },
            headers=self.headers,
        )
        self.assertEqual(proposal.status_code, 201, proposal.text)
        proposal_value = proposal.json()
        proposal_id = str(proposal_value["id"])
        validation = self.client.post(
            f"/api/v1/organizations/{self.organization}/proposals/{proposal_id}/validate",
            headers=self.headers,
        )
        self.assertEqual(validation.status_code, 200, validation.text)
        confirmation = self.client.post(
            f"/api/v1/organizations/{self.organization}/proposals/{proposal_id}/confirm",
            json={
                "validation_id": validation.json()["id"],
                "proposal_version": proposal_value["version"],
                "accepted": True,
            },
            headers={**self.headers, "Idempotency-Key": f"confirm-{suffix}"},
        )
        self.assertEqual(confirmation.status_code, 200, confirmation.text)
        return proposal_id, str(confirmation.json()["id"])

    def test_concurrent_authenticated_reads_use_distinct_closed_connections(self) -> None:
        opened: list[Database] = []
        closed: list[Database] = []
        tracking_lock = threading.Lock()
        original_init = Database.__init__
        original_close = Database.close

        def tracked_init(database: Database, *args: object, **kwargs: object) -> None:
            original_init(database, *args, **kwargs)  # type: ignore[arg-type]
            with tracking_lock:
                opened.append(database)

        def tracked_close(database: Database) -> None:
            with tracking_lock:
                closed.append(database)
            original_close(database)

        request_count = 12
        barrier = threading.Barrier(request_count)

        def read(index: int) -> tuple[int, str]:
            barrier.wait(timeout=10)
            paths = (
                "/api/v1/auth/me",
                f"/api/v1/organizations/{self.organization}/accounts",
                f"/api/v1/organizations/{self.organization}/projects",
                f"/api/v1/organizations/{self.organization}/reports/trial-balance",
            )
            response = self.client.get(paths[index % len(paths)], headers=self.headers)
            return response.status_code, response.text

        with (
            patch.object(Database, "__init__", tracked_init),
            patch.object(Database, "close", tracked_close),
            ThreadPoolExecutor(max_workers=request_count) as pool,
        ):
            results = list(pool.map(read, range(request_count)))

        self.assertTrue(all(status == 200 for status, _body in results), results)
        self.assertGreaterEqual(len(opened), request_count)
        self.assertEqual(len({id(database) for database in opened}), len(opened))
        self.assertEqual(
            {id(database) for database in closed}, {id(database) for database in opened}
        )
        self.assertEqual(len(closed), len(opened))

    def test_concurrent_reads_never_observe_partial_posting(self) -> None:
        proposal_id, confirmation_id = self._confirmed_proposal("read-write")
        reader_count = 10
        barrier = threading.Barrier(reader_count + 1)

        def read_trial_balance() -> tuple[int, int, bool]:
            barrier.wait(timeout=10)
            response = self.client.get(
                f"/api/v1/organizations/{self.organization}/reports/trial-balance",
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 200, response.text)
            value = response.json()
            return int(value["total_debits"]), int(value["total_credits"]), bool(value["balanced"])

        def post() -> tuple[int, dict[str, object]]:
            barrier.wait(timeout=10)
            response = self.client.post(
                f"/api/v1/organizations/{self.organization}/proposals/{proposal_id}/post",
                json={"confirmation_id": confirmation_id},
                headers={**self.headers, "Idempotency-Key": "post-read-write"},
            )
            return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=reader_count + 1) as pool:
            readers = [pool.submit(read_trial_balance) for _ in range(reader_count)]
            writer = pool.submit(post)
            read_results = [future.result(timeout=20) for future in readers]
            write_status, write_value = writer.result(timeout=20)

        self.assertEqual(write_status, 200, write_value)
        self.assertTrue(all(balanced for _debits, _credits, balanced in read_results))
        self.assertTrue(
            all(
                (debits, credits) in {(0, 0), (1_250, 1_250)}
                for debits, credits, _balanced in read_results
            )
        )
        entries = self.client.get(
            f"/api/v1/organizations/{self.organization}/journal-entries",
            headers=self.headers,
        ).json()
        ledger = self.client.get(
            f"/api/v1/organizations/{self.organization}/reports/general-ledger",
            headers=self.headers,
        ).json()
        self.assertEqual(entries["total"], 1)
        self.assertEqual(ledger["total"], 2)
        self.assertEqual(
            (
                sum(line["debit"] for line in ledger["items"]),
                sum(line["credit"] for line in ledger["items"]),
            ),
            (1_250, 1_250),
        )

    def test_concurrent_duplicate_posting_serializes_to_one_effect(self) -> None:
        proposal_id, confirmation_id = self._confirmed_proposal("writer-gate", value=725)
        request_count = 6
        barrier = threading.Barrier(request_count)

        def post_once() -> tuple[int, dict[str, object]]:
            barrier.wait(timeout=10)
            response = self.client.post(
                f"/api/v1/organizations/{self.organization}/proposals/{proposal_id}/post",
                json={"confirmation_id": confirmation_id},
                headers={**self.headers, "Idempotency-Key": "post-writer-gate"},
            )
            return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=request_count) as pool:
            results = list(pool.map(lambda _index: post_once(), range(request_count)))

        self.assertTrue(all(status == 200 for status, _value in results), results)
        entry_ids = {str(value["entry_id"]) for _status, value in results}
        self.assertEqual(len(entry_ids), 1)
        entries = self.client.get(
            f"/api/v1/organizations/{self.organization}/journal-entries",
            headers=self.headers,
        ).json()
        self.assertEqual(entries["total"], 1)
        events = self.client.get(
            f"/api/v1/organizations/{self.organization}/audit-events",
            headers=self.headers,
        ).json()["items"]
        posting_events = [
            event for event in events if event["metadata"].get("request_id") == "post-writer-gate"
        ]
        self.assertEqual(len(posting_events), 4)

    def test_concurrent_cross_organization_reads_never_leak_data(self) -> None:
        outsider = self._register("Outsider", "outsider@example.test")
        outsider_headers = self._login("outsider@example.test")
        other = self.client.post(
            "/api/v1/organizations",
            json={"name": "Other Space", "currency": "USD", "minor_unit_digits": 2},
            headers=outsider_headers,
        )
        self.assertEqual(other.status_code, 201, other.text)
        self.assertNotEqual(str(outsider["id"]), self.actor)

        request_count = 10
        barrier = threading.Barrier(request_count)

        def read(index: int) -> tuple[str, int, str]:
            barrier.wait(timeout=10)
            if index % 2:
                response = self.client.get(
                    f"/api/v1/organizations/{self.organization}/accounts",
                    headers=outsider_headers,
                )
                return "outsider", response.status_code, response.text
            response = self.client.get(
                f"/api/v1/organizations/{self.organization}/accounts",
                headers=self.headers,
            )
            return "owner", response.status_code, response.text

        with ThreadPoolExecutor(max_workers=request_count) as pool:
            results = list(pool.map(read, range(request_count)))

        for actor, status, body in results:
            if actor == "owner":
                self.assertEqual(status, 200, body)
                self.assertIn("Bank", body)
            else:
                self.assertIn(status, {403, 404}, body)
                self.assertNotIn("Bank", body)


if __name__ == "__main__":
    unittest.main()
