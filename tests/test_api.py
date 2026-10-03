import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from chatbook import AccountingEngine
from chatbook.api import create_app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db_path = Path(self.folder.name) / "api.db"
        self.client = TestClient(create_app(self.db_path))
        self.addCleanup(self.client.close)
        self.owner = self.register("Owner", "owner@example.test")
        self.owner_headers = self.login("owner@example.test")
        organization = self.client.post(
            "/api/v1/organizations",
            json={"name": "API Studio", "currency": "BDT", "minor_unit_digits": 2},
            headers=self.owner_headers,
        )
        self.assertEqual(organization.status_code, 201, organization.text)
        self.org = organization.json()["id"]
        self.bank = self.create_account("1000", "Bank", "asset")
        self.revenue = self.create_account("4000", "Revenue", "revenue")
        self.expense = self.create_account("5000", "Expense", "expense")
        period = self.client.post(
            f"/api/v1/organizations/{self.org}/periods",
            json={"name": "September", "starts_on": "2026-09-01", "ends_on": "2026-09-30"},
            headers=self.owner_headers,
        )
        self.assertEqual(period.status_code, 201, period.text)
        self.period = period.json()["id"]

    def register(self, name: str, username: str) -> dict[str, object]:
        response = self.client.post(
            "/api/v1/auth/register",
            json={"name": name, "username": username, "password": "correct horse battery"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def login(self, username: str) -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/token",
            json={"username": username, "password": "correct horse battery"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def create_account(self, code: str, name: str, account_type: str) -> str:
        response = self.client.post(
            f"/api/v1/organizations/{self.org}/accounts",
            json={"code": code, "name": name, "account_type": account_type},
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    def proposal(self, *, value: int = 1_250, entry_date: str = "2026-09-15") -> dict[str, object]:
        response = self.client.post(
            f"/api/v1/organizations/{self.org}/proposals",
            json={
                "entry_date": entry_date,
                "description": "Client payment",
                "lines": [
                    {"account_id": self.bank, "debit": value},
                    {"account_id": self.revenue, "credit": value},
                ],
            },
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def validate(self, proposal_id: str) -> dict[str, object]:
        response = self.client.post(
            f"/api/v1/organizations/{self.org}/proposals/{proposal_id}/validate",
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def confirm(
        self, proposal: dict[str, object], validation: dict[str, object], key: str
    ) -> dict[str, object]:
        response = self.client.post(
            f"/api/v1/organizations/{self.org}/proposals/{proposal['id']}/confirm",
            json={
                "validation_id": validation["id"],
                "proposal_version": proposal["version"],
                "accepted": True,
            },
            headers={**self.owner_headers, "Idempotency-Key": key},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def post(
        self, proposal: dict[str, object], confirmation: dict[str, object], key: str
    ) -> dict[str, object]:
        response = self.client.post(
            f"/api/v1/organizations/{self.org}/proposals/{proposal['id']}/post",
            json={"confirmation_id": confirmation["id"]},
            headers={**self.owner_headers, "Idempotency-Key": key},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def add_user(self, role: str, suffix: str) -> tuple[dict[str, object], dict[str, str]]:
        username = f"{suffix}@example.test"
        user = self.register(suffix, username)
        response = self.client.post(
            f"/api/v1/organizations/{self.org}/members",
            json={"user_id": user["id"], "role": role},
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return user, self.login(username)

    def test_authentication_rejects_anonymous_and_accepts_session(self) -> None:
        anonymous = self.client.get("/api/v1/organizations")
        self.assertEqual(anonymous.status_code, 401)
        authenticated = self.client.get("/api/v1/auth/me", headers=self.owner_headers)
        self.assertEqual(authenticated.status_code, 200)
        self.assertEqual(authenticated.json()["id"], self.owner["id"])

    def test_role_authorization_and_cross_organization_isolation(self) -> None:
        _, viewer_headers = self.add_user("VIEWER", "viewer")
        allowed = self.client.get(
            f"/api/v1/organizations/{self.org}/projects", headers=viewer_headers
        )
        self.assertEqual(allowed.status_code, 200)
        denied = self.client.post(
            f"/api/v1/organizations/{self.org}/accounts",
            json={"code": "1010", "name": "Other", "account_type": "asset"},
            headers=viewer_headers,
        )
        self.assertEqual(denied.status_code, 403)

        outsider = self.register("Outsider", "outsider@example.test")
        outsider_headers = self.login("outsider@example.test")
        other_org = self.client.post(
            "/api/v1/organizations",
            json={"name": "Other", "currency": "USD", "minor_unit_digits": 2},
            headers=outsider_headers,
        )
        self.assertEqual(other_org.status_code, 201)
        isolated = self.client.get(
            f"/api/v1/organizations/{self.org}/accounts", headers=outsider_headers
        )
        self.assertIn(isolated.status_code, {403, 404})
        self.assertNotEqual(outsider["id"], self.owner["id"])

    def test_projects_create_read_update_and_isolation(self) -> None:
        created = self.client.post(
            f"/api/v1/organizations/{self.org}/projects",
            json={
                "name": "Website",
                "description": "Initial",
                "budget": 9_000,
                "expected_revenue": 15_000,
                "status": "active",
            },
            headers=self.owner_headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        project_id = created.json()["id"]
        read = self.client.get(
            f"/api/v1/organizations/{self.org}/projects/{project_id}",
            headers=self.owner_headers,
        )
        self.assertEqual(read.status_code, 200)
        updated = self.client.patch(
            f"/api/v1/organizations/{self.org}/projects/{project_id}",
            json={"description": "Updated", "budget": 10_000},
            headers=self.owner_headers,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["description"], "Updated")
        self.assertEqual(updated.json()["budget"], 10_000)

        _, outsider_headers = self.add_user("VIEWER", "project-viewer")
        different = self.register("Different", "different@example.test")
        different_headers = self.login("different@example.test")
        other = self.client.post(
            "/api/v1/organizations",
            json={"name": "Different", "currency": "EUR", "minor_unit_digits": 2},
            headers=different_headers,
        ).json()["id"]
        denied = self.client.get(
            f"/api/v1/organizations/{other}/projects/{project_id}", headers=outsider_headers
        )
        self.assertIn(denied.status_code, {403, 404})
        self.assertTrue(different["id"])

    def test_proposal_stale_version_confirmation_and_idempotency(self) -> None:
        proposal = self.proposal()
        validation = self.validate(str(proposal["id"]))
        stale = self.client.post(
            f"/api/v1/organizations/{self.org}/proposals/{proposal['id']}/confirm",
            json={
                "validation_id": validation["id"],
                "proposal_version": 2,
                "accepted": True,
            },
            headers={**self.owner_headers, "Idempotency-Key": "confirm-stale-0001"},
        )
        self.assertEqual(stale.status_code, 409)
        first = self.confirm(proposal, validation, "confirm-retry-0001")
        second = self.confirm(proposal, validation, "confirm-retry-0001")
        self.assertEqual(second, first)
        self.assertEqual(first["proposal_id"], proposal["id"])
        self.assertEqual(first["proposal_version"], 1)
        self.assertEqual(first["actor_id"], self.owner["id"])
        self.assertEqual(first["confirmation_request_id"], "confirm-retry-0001")

        other = self.proposal(value=2_000)
        other_validation = self.validate(str(other["id"]))
        conflict = self.client.post(
            f"/api/v1/organizations/{self.org}/proposals/{other['id']}/confirm",
            json={
                "validation_id": other_validation["id"],
                "proposal_version": 1,
                "accepted": True,
            },
            headers={**self.owner_headers, "Idempotency-Key": "confirm-retry-0001"},
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["error"], "idempotency_conflict")

    def test_post_retry_has_one_accounting_effect(self) -> None:
        proposal = self.proposal()
        confirmation = self.confirm(
            proposal, self.validate(str(proposal["id"])), "confirm-post-0001"
        )
        first = self.post(proposal, confirmation, "post-retry-0001")
        second = self.post(proposal, confirmation, "post-retry-0001")
        self.assertEqual(first, second)
        ledger = self.client.get(
            f"/api/v1/organizations/{self.org}/reports/general-ledger",
            headers=self.owner_headers,
        )
        self.assertEqual(ledger.status_code, 200, ledger.text)
        self.assertEqual(ledger.json()["total"], 2)
        entries = self.client.get(
            f"/api/v1/organizations/{self.org}/journal-entries",
            headers=self.owner_headers,
        )
        self.assertEqual(entries.status_code, 200, entries.text)
        self.assertEqual(entries.json()["total"], 1)
        summary = entries.json()["items"][0]
        self.assertEqual((summary["debit_total"], summary["credit_total"]), (1_250, 1_250))
        self.assertEqual(summary["line_count"], 2)
        detail = self.client.get(
            f"/api/v1/organizations/{self.org}/journal-entries/{summary['id']}",
            headers=self.owner_headers,
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["debit_total"], 1_250)

    def test_reversal_authorization_and_original_history(self) -> None:
        proposal = self.proposal()
        confirmation = self.confirm(
            proposal, self.validate(str(proposal["id"])), "confirm-reversal-0001"
        )
        entry = self.post(proposal, confirmation, "post-reversal-0001")["entry_id"]
        _, viewer_headers = self.add_user("VIEWER", "reversal-viewer")
        denied = self.client.post(
            f"/api/v1/organizations/{self.org}/journal-entries/{entry}/reversals",
            json={"entry_date": "2026-09-16", "reason": "Correction"},
            headers=viewer_headers,
        )
        self.assertEqual(denied.status_code, 403)
        reversal = self.client.post(
            f"/api/v1/organizations/{self.org}/journal-entries/{entry}/reversals",
            json={"entry_date": "2026-09-16", "reason": "Correction"},
            headers=self.owner_headers,
        )
        self.assertEqual(reversal.status_code, 201, reversal.text)
        reversal_proposal = reversal.json()
        reversal_validation = self.validate(reversal_proposal["id"])
        reversal_confirmation = self.confirm(
            reversal_proposal, reversal_validation, "confirm-reversal-0002"
        )
        reversal_entry = self.post(reversal_proposal, reversal_confirmation, "post-reversal-0002")[
            "entry_id"
        ]
        original = self.client.get(
            f"/api/v1/organizations/{self.org}/journal-entries/{entry}",
            headers=self.owner_headers,
        )
        self.assertEqual(original.status_code, 200)
        self.assertEqual(original.json()["id"], entry)
        reversed_entry = self.client.get(
            f"/api/v1/organizations/{self.org}/journal-entries/{reversal_entry}",
            headers=self.owner_headers,
        )
        self.assertEqual(reversed_entry.json()["reverses_entry_id"], entry)
        trial = self.client.get(
            f"/api/v1/organizations/{self.org}/reports/trial-balance",
            headers=self.owner_headers,
        )
        self.assertEqual(trial.json()["total_debits"], 0)

    def test_locked_period_rejects_post_through_api(self) -> None:
        proposal = self.proposal()
        confirmation = self.confirm(
            proposal, self.validate(str(proposal["id"])), "confirm-lock-0001"
        )
        locked = self.client.post(
            f"/api/v1/organizations/{self.org}/periods/{self.period}/lock",
            headers=self.owner_headers,
        )
        self.assertEqual(locked.status_code, 200)
        posting = self.client.post(
            f"/api/v1/organizations/{self.org}/proposals/{proposal['id']}/post",
            json={"confirmation_id": confirmation["id"]},
            headers={**self.owner_headers, "Idempotency-Key": "post-lock-0001"},
        )
        self.assertEqual(posting.status_code, 409)
        self.assertEqual(posting.json()["error"], "period_locked")

    def test_reports_reconcile_with_engine_and_cash_is_explicit(self) -> None:
        proposal = self.proposal(value=3_400)
        confirmation = self.confirm(
            proposal, self.validate(str(proposal["id"])), "confirm-report-0001"
        )
        self.post(proposal, confirmation, "post-report-0001")
        api_trial = self.client.get(
            f"/api/v1/organizations/{self.org}/reports/trial-balance",
            headers=self.owner_headers,
        ).json()
        engine = AccountingEngine(self.db_path)
        self.addCleanup(engine.close)
        direct = engine.trial_balance(str(self.owner["id"]), self.org)
        self.assertEqual(api_trial["total_debits"], direct.total_debits)
        self.assertEqual(api_trial["total_credits"], direct.total_credits)
        cash = self.client.get(
            f"/api/v1/organizations/{self.org}/reports/cash-flow",
            params={
                "starts_on": "2026-09-01",
                "ends_on": "2026-09-30",
                "cash_account_id": self.bank,
            },
            headers=self.owner_headers,
        )
        self.assertEqual(cash.status_code, 200, cash.text)
        self.assertEqual(cash.json()["net_change"], 3_400)
        self.assertEqual(cash.json()["classification"], "unclassified_cash_movements")

    def test_audit_is_complete_read_only_and_database_is_not_exposed(self) -> None:
        proposal = self.proposal()
        confirmation = self.confirm(
            proposal, self.validate(str(proposal["id"])), "confirm-audit-0001"
        )
        entry = self.post(proposal, confirmation, "post-audit-0001")["entry_id"]
        events = self.client.get(
            f"/api/v1/organizations/{self.org}/audit-events",
            headers=self.owner_headers,
        )
        self.assertEqual(events.status_code, 200, events.text)
        post_events = [
            event
            for event in events.json()["items"]
            if event["metadata"]["operation"] == "transaction.post"
        ]
        self.assertEqual(len(post_events), 4)
        self.assertTrue(all(event["actor_id"] == self.owner["id"] for event in post_events))
        self.assertTrue(all(event["occurred_at"] for event in post_events))
        self.assertTrue(all(event["new_state"] is not None for event in post_events))
        self.assertTrue(
            all(event["metadata"]["request_id"] == "post-audit-0001" for event in post_events)
        )
        mutate = self.client.post(
            f"/api/v1/organizations/{self.org}/audit-events",
            json={"entity_id": entry},
            headers=self.owner_headers,
        )
        self.assertEqual(mutate.status_code, 405)
        private = self.client.get("/api/v1/debug/database", headers=self.owner_headers)
        self.assertEqual(private.status_code, 404)
        schema = self.client.get("/openapi.json").json()
        self.assertFalse(any("sqlite" in path or "connection" in path for path in schema["paths"]))


if __name__ == "__main__":
    unittest.main()
