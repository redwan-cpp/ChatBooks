import sqlite3
import tempfile
import unittest
from pathlib import Path

from chatbook import AccountingEngine, AccountType, LineInput, OrganizationRole


class SchemaMigrationTests(unittest.TestCase):
    def test_v1_database_migrates_without_changing_posted_history(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "migration.db"
        engine = AccountingEngine(path)
        actor = engine.create_user("Legacy owner")
        organization = engine.create_organization(actor, "Legacy", "BDT", 2)
        bank = engine.create_account(actor, organization, "1000", "Bank", AccountType.ASSET)
        revenue = engine.create_account(actor, organization, "4000", "Revenue", AccountType.REVENUE)
        engine.create_period(actor, organization, "September", "2026-09-01", "2026-09-30")
        proposal = engine.create_transaction(
            actor,
            organization,
            "2026-09-15",
            "Legacy posting",
            [LineInput(bank, debit=500), LineInput(revenue, credit=500)],
        )
        validation = engine.validate_transaction(actor, organization, proposal)
        confirmation = engine.confirm_transaction(actor, organization, validation.id, accepted=True)
        entry = engine.post_transaction(actor, organization, confirmation.id)
        before = engine.ledger(actor, organization)
        engine.close()

        connection = sqlite3.connect(path)
        connection.executescript("""
            PRAGMA foreign_keys = OFF;
            DROP TRIGGER organization_creates_business_book;
            DROP TRIGGER ledger_book_matches_organization;
            DROP TRIGGER ledger_book_no_replace;
            DROP TRIGGER ledger_book_no_update;
            DROP TRIGGER ledger_book_no_delete;
            DROP TABLE ledger_books;
            DROP TABLE confirmation_provenance;
            DROP TABLE command_idempotency;
            DROP TABLE auth_sessions;
            DROP TABLE user_credentials;
            DROP TRIGGER audit_memberships_insert;
            DROP TRIGGER audit_memberships_update;
            ALTER TABLE memberships DROP COLUMN role;
            DROP TRIGGER audit_transactions_insert;
            DROP TRIGGER audit_transactions_update;
            DROP TRIGGER transaction_freeze;
            ALTER TABLE transactions DROP COLUMN version;
            DROP TRIGGER project_fields_only;
            CREATE TRIGGER no_update_projects BEFORE UPDATE ON projects
            BEGIN SELECT RAISE(ABORT, 'immutable_history'); END;
            PRAGMA user_version = 1;
        """)
        connection.close()

        migrated = AccountingEngine(path)
        self.addCleanup(migrated.close)
        self.assertEqual(migrated.ledger(actor, organization), before)
        self.assertEqual(migrated.membership_role(actor, organization), OrganizationRole.OWNER)
        self.assertEqual(migrated.get_journal_entry(actor, organization, entry)["id"], entry)
        provenance = migrated.get_confirmation(actor, organization, confirmation.id)
        self.assertEqual(provenance["proposal_id"], proposal)
        self.assertEqual(provenance["proposal_version"], 1)
        self.assertEqual(migrated._db.connection.execute("PRAGMA user_version").fetchone()[0], 3)
        self.assertEqual(
            migrated._db.connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
        )
        self.assertEqual(migrated._db.connection.execute("PRAGMA foreign_key_check").fetchall(), [])


if __name__ == "__main__":
    unittest.main()
