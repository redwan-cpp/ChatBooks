"""Schema-v4 guards, indexes, and legacy-compatible audit triggers."""

import sqlite3

CANONICAL_SCHEMA_VERSION = 4
LEGACY_FINGERPRINT_VERSION = "organization-v1"

CANONICAL_CORE_TABLES = (
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

CANONICAL_EXTENSION_TABLES = (
    "business_proposal_documents",
    "business_proposal_line_projects",
    "business_journal_line_projects",
)

CANONICAL_BOOK_TABLES = (
    CANONICAL_CORE_TABLES + CANONICAL_EXTENSION_TABLES + ("audit_event_book_scopes",)
)

AUDITED_CANONICAL_TABLES = (
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

CANONICAL_AUDIT_TRIGGER_NAMES = frozenset(
    f"audit_{table}_{operation}"
    for table in AUDITED_CANONICAL_TABLES
    for operation in ("insert", "update")
)


def _execute_script(connection: sqlite3.Connection, script: str) -> None:
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ""
    if statement.strip():
        raise sqlite3.DatabaseError("Incomplete canonical schema statement")


def _json_object(columns: tuple[tuple[str, str], ...]) -> str:
    return (
        "json_object(" + ",".join(f"'{name}', {expression}" for name, expression in columns) + ")"
    )


def _legacy_columns(table: str, row: str) -> tuple[tuple[str, str], ...]:
    org = f"(SELECT organization_id FROM ledger_books WHERE id = {row}.ledger_book_id)"
    definitions: dict[str, tuple[tuple[str, str], ...]] = {
        "charts_of_accounts": (
            ("id", f"{row}.id"),
            ("organization_id", org),
            ("name", f"{row}.name"),
        ),
        "accounts": (
            ("id", f"{row}.id"),
            ("organization_id", org),
            ("chart_id", f"{row}.chart_id"),
            ("code", f"{row}.code"),
            ("name", f"{row}.name"),
            ("account_type", f"{row}.account_type"),
            ("active", f"{row}.active"),
        ),
        "accounting_periods": (
            ("id", f"{row}.id"),
            ("organization_id", org),
            ("name", f"{row}.name"),
            ("starts_on", f"{row}.starts_on"),
            ("ends_on", f"{row}.ends_on"),
            ("locked", f"{row}.locked"),
        ),
        "transactions": (
            ("id", f"{row}.id"),
            ("organization_id", org),
            ("entry_date", f"{row}.entry_date"),
            ("description", f"{row}.description"),
            (
                "document_id",
                "(SELECT document_id FROM business_proposal_documents "
                f"WHERE proposal_id = {row}.id AND ledger_book_id = {row}.ledger_book_id)",
            ),
            ("reverses_entry_id", f"{row}.reverses_entry_id"),
            ("version", f"{row}.version"),
            ("state", f"{row}.state"),
        ),
        "transaction_lines": (
            ("id", f"{row}.id"),
            ("organization_id", org),
            ("transaction_id", f"{row}.transaction_id"),
            ("position", f"{row}.position"),
            ("account_id", f"{row}.account_id"),
            ("debit", f"{row}.debit"),
            ("credit", f"{row}.credit"),
            (
                "project_id",
                "(SELECT project_id FROM business_proposal_line_projects "
                f"WHERE line_id = {row}.id AND ledger_book_id = {row}.ledger_book_id)",
            ),
        ),
        "validations": (
            ("id", f"{row}.id"),
            ("organization_id", org),
            ("transaction_id", f"{row}.transaction_id"),
            ("fingerprint", f"{row}.fingerprint"),
            ("actor_id", f"{row}.actor_id"),
        ),
        "confirmations": (
            ("id", f"{row}.id"),
            ("organization_id", org),
            ("validation_id", f"{row}.validation_id"),
            ("actor_id", f"{row}.actor_id"),
        ),
        "journal_entries": (
            ("id", f"{row}.id"),
            ("organization_id", org),
            ("transaction_id", f"{row}.transaction_id"),
            ("confirmation_id", f"{row}.confirmation_id"),
            ("period_id", f"{row}.period_id"),
            ("entry_date", f"{row}.entry_date"),
            ("description", f"{row}.description"),
            ("reverses_entry_id", f"{row}.reverses_entry_id"),
            ("state", f"{row}.state"),
        ),
        "journal_lines": (
            ("id", f"{row}.id"),
            ("organization_id", org),
            ("entry_id", f"{row}.entry_id"),
            ("position", f"{row}.position"),
            ("account_id", f"{row}.account_id"),
            ("debit", f"{row}.debit"),
            ("credit", f"{row}.credit"),
            (
                "project_id",
                "(SELECT project_id FROM business_journal_line_projects "
                f"WHERE line_id = {row}.id AND ledger_book_id = {row}.ledger_book_id)",
            ),
        ),
    }
    return definitions[table]


def _install_audit_trigger(connection: sqlite3.Connection, table: str, operation: str) -> None:
    new_json = _json_object(_legacy_columns(table, "NEW"))
    previous = "NULL" if operation == "insert" else _json_object(_legacy_columns(table, "OLD"))
    extension_check = ""
    extension_by_table = {
        "transactions": ("business_proposal_documents", "proposal_id"),
        "transaction_lines": ("business_proposal_line_projects", "line_id"),
        "journal_lines": ("business_journal_line_projects", "line_id"),
    }
    if operation == "insert" and table in extension_by_table:
        extension, key = extension_by_table[table]
        extension_check = (
            f"SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM {extension} "
            f"WHERE {key} = NEW.id AND ledger_book_id = NEW.ledger_book_id) "
            "THEN RAISE(ABORT, 'business_extension_required') END;"
        )
    connection.execute(
        f"""
        CREATE TRIGGER audit_{table}_{operation} AFTER {operation.upper()} ON {table}
        BEGIN
            {extension_check}
            INSERT INTO audit_events (
                organization_id, actor_id, occurred_at, event_type, entity_type,
                entity_id, previous_state, new_state, metadata
            ) VALUES (
                (SELECT organization_id FROM ledger_books WHERE id = NEW.ledger_book_id),
                chatbook_actor(), chatbook_now(), '{table}.{operation}', '{table}',
                NEW.id, {previous}, {new_json}, chatbook_metadata()
            );
            INSERT INTO audit_event_book_scopes (audit_sequence, ledger_book_id)
            VALUES (last_insert_rowid(), NEW.ledger_book_id);
        END
        """
    )


def install_canonical_schema_protections(connection: sqlite3.Connection) -> None:
    """Install v4 indexes and fail-closed write/audit rules after table reconstruction."""
    _execute_script(
        connection,
        """
        DROP TRIGGER organization_creates_business_book;
        CREATE TRIGGER organization_creates_business_book AFTER INSERT ON organizations
        BEGIN
            INSERT INTO ledger_books (
                id, owner_kind, organization_id, currency, minor_unit_digits,
                created_at, creation_source, creation_version
            ) VALUES (
                'book:business:' || NEW.id, 'BUSINESS', NEW.id, NEW.currency,
                NEW.minor_unit_digits, chatbook_now(), 'organization_creation', 'm5.1-c1-v1'
            );
            INSERT INTO charts_of_accounts (id, ledger_book_id, name)
            VALUES ('chart:business:' || NEW.id, 'book:business:' || NEW.id, 'Chart of Accounts');
        END;

        CREATE INDEX ledger_by_date ON journal_entries(ledger_book_id, state, entry_date);
        CREATE INDEX ledger_by_account
            ON journal_lines(ledger_book_id, account_id, entry_id);
        CREATE INDEX ledger_by_project
            ON business_journal_line_projects(ledger_book_id, project_id, line_id);
        CREATE INDEX proposal_lines_by_book
            ON transaction_lines(ledger_book_id, transaction_id, position);
        CREATE INDEX journal_lines_by_book
            ON journal_lines(ledger_book_id, entry_id, position);
        CREATE INDEX receipts_by_book
            ON command_idempotency(ledger_book_id, actor_id, operation, idempotency_key);
        CREATE UNIQUE INDEX one_posted_reversal
            ON journal_entries(ledger_book_id, reverses_entry_id)
            WHERE state = 'posted' AND reverses_entry_id IS NOT NULL;

        CREATE TRIGGER period_no_overlap BEFORE INSERT ON accounting_periods BEGIN
            SELECT CASE WHEN EXISTS (
                SELECT 1 FROM accounting_periods
                WHERE ledger_book_id = NEW.ledger_book_id
                  AND starts_on <= NEW.ends_on AND ends_on >= NEW.starts_on
            ) THEN RAISE(ABORT, 'period_overlap') END;
        END;

        CREATE TRIGGER transaction_starts_assembling BEFORE INSERT ON transactions
        WHEN NEW.state != 'assembling'
        BEGIN SELECT RAISE(ABORT, 'invalid_initial_state'); END;

        CREATE TRIGGER transaction_freeze BEFORE UPDATE ON transactions
        WHEN OLD.state != 'assembling' OR NEW.state != 'proposed'
          OR NEW.id IS NOT OLD.id OR NEW.ledger_book_id IS NOT OLD.ledger_book_id
          OR NEW.entry_date IS NOT OLD.entry_date OR NEW.description IS NOT OLD.description
          OR NEW.reverses_entry_id IS NOT OLD.reverses_entry_id
          OR NEW.version IS NOT OLD.version
        BEGIN SELECT RAISE(ABORT, 'immutable_proposal'); END;

        CREATE TRIGGER transaction_line_insert BEFORE INSERT ON transaction_lines
        WHEN NOT EXISTS (
            SELECT 1 FROM transactions WHERE id = NEW.transaction_id
              AND ledger_book_id = NEW.ledger_book_id AND state = 'assembling'
        )
        BEGIN SELECT RAISE(ABORT, 'immutable_proposal'); END;

        CREATE TRIGGER journal_starts_assembling BEFORE INSERT ON journal_entries
        WHEN NEW.state != 'assembling'
        BEGIN SELECT RAISE(ABORT, 'invalid_initial_state'); END;

        CREATE TRIGGER journal_line_insert BEFORE INSERT ON journal_lines
        WHEN NOT EXISTS (
            SELECT 1 FROM journal_entries WHERE id = NEW.entry_id
              AND ledger_book_id = NEW.ledger_book_id AND state = 'assembling'
        )
        BEGIN SELECT RAISE(ABORT, 'immutable_posted_history'); END;

        CREATE TRIGGER journal_freeze BEFORE UPDATE ON journal_entries
        WHEN OLD.state != 'assembling' OR NEW.state != 'posted'
          OR NEW.id IS NOT OLD.id OR NEW.ledger_book_id IS NOT OLD.ledger_book_id
          OR NEW.transaction_id IS NOT OLD.transaction_id
          OR NEW.confirmation_id IS NOT OLD.confirmation_id
          OR NEW.period_id IS NOT OLD.period_id OR NEW.entry_date IS NOT OLD.entry_date
          OR NEW.description IS NOT OLD.description
          OR NEW.reverses_entry_id IS NOT OLD.reverses_entry_id
        BEGIN SELECT RAISE(ABORT, 'immutable_posted_history'); END;

        CREATE TRIGGER period_lock_only BEFORE UPDATE ON accounting_periods
        WHEN OLD.locked != 0 OR NEW.locked != 1
          OR NEW.id IS NOT OLD.id OR NEW.ledger_book_id IS NOT OLD.ledger_book_id
          OR NEW.name IS NOT OLD.name OR NEW.starts_on IS NOT OLD.starts_on
          OR NEW.ends_on IS NOT OLD.ends_on
        BEGIN SELECT RAISE(ABORT, 'period_immutable_or_locked'); END;

        CREATE TRIGGER account_active_only BEFORE UPDATE ON accounts
        WHEN NEW.id IS NOT OLD.id OR NEW.ledger_book_id IS NOT OLD.ledger_book_id
          OR NEW.chart_id IS NOT OLD.chart_id OR NEW.code IS NOT OLD.code
          OR NEW.name IS NOT OLD.name OR NEW.account_type IS NOT OLD.account_type
        BEGIN SELECT RAISE(ABORT, 'immutable_account_identity'); END;

        CREATE TRIGGER validation_actor_membership BEFORE INSERT ON validations
        WHEN NOT EXISTS (
            SELECT 1 FROM ledger_books b JOIN memberships m
              ON m.organization_id = b.organization_id
            WHERE b.id = NEW.ledger_book_id AND b.owner_kind = 'BUSINESS'
              AND m.user_id = NEW.actor_id
        )
        BEGIN SELECT RAISE(ABORT, 'actor_not_authorized_for_book'); END;

        CREATE TRIGGER confirmation_actor_membership BEFORE INSERT ON confirmations
        WHEN NOT EXISTS (
            SELECT 1 FROM ledger_books b JOIN memberships m
              ON m.organization_id = b.organization_id
            WHERE b.id = NEW.ledger_book_id AND b.owner_kind = 'BUSINESS'
              AND m.user_id = NEW.actor_id
        )
        BEGIN SELECT RAISE(ABORT, 'actor_not_authorized_for_book'); END;

        CREATE TRIGGER idempotency_actor_membership BEFORE INSERT ON command_idempotency
        WHEN NOT EXISTS (
            SELECT 1 FROM ledger_books b JOIN memberships m
              ON m.organization_id = b.organization_id
            WHERE b.id = NEW.ledger_book_id AND b.owner_kind = 'BUSINESS'
              AND m.user_id = NEW.actor_id
        )
        BEGIN SELECT RAISE(ABORT, 'actor_not_authorized_for_book'); END;

        CREATE TRIGGER confirmation_provenance_validate
        BEFORE INSERT ON confirmation_provenance
        WHEN NOT EXISTS (
            SELECT 1 FROM confirmations c
            JOIN validations v ON v.id = c.validation_id
              AND v.ledger_book_id = c.ledger_book_id
            JOIN transactions t ON t.id = v.transaction_id
              AND t.ledger_book_id = v.ledger_book_id
            WHERE c.id = NEW.confirmation_id
              AND c.ledger_book_id = NEW.ledger_book_id
              AND t.id = NEW.proposal_id AND t.version = NEW.proposal_version
        )
        BEGIN SELECT RAISE(ABORT, 'confirmation_provenance_mismatch'); END;

        CREATE TRIGGER command_idempotency_validate
        BEFORE INSERT ON command_idempotency
        WHEN NOT (
            (NEW.operation = 'transaction.confirm' AND NEW.resource_type = 'confirmation'
             AND EXISTS (SELECT 1 FROM confirmations
                         WHERE ledger_book_id = NEW.ledger_book_id AND id = NEW.resource_id))
            OR
            (NEW.operation = 'transaction.post' AND NEW.resource_type = 'journal_entry'
             AND EXISTS (SELECT 1 FROM journal_entries
                         WHERE ledger_book_id = NEW.ledger_book_id AND id = NEW.resource_id
                           AND state = 'posted'))
        )
        BEGIN SELECT RAISE(ABORT, 'idempotency_resource_mismatch'); END;

        CREATE TRIGGER journal_validate BEFORE UPDATE OF state ON journal_entries
        WHEN NEW.state = 'posted' BEGIN
            SELECT CASE WHEN NOT EXISTS (
                SELECT 1 FROM accounting_periods
                WHERE id = NEW.period_id AND ledger_book_id = NEW.ledger_book_id
                  AND locked = 0 AND NEW.entry_date BETWEEN starts_on AND ends_on
            ) THEN RAISE(ABORT, 'period_closed_or_missing') END;
            SELECT CASE WHEN NOT EXISTS (
                SELECT 1 FROM transactions t
                JOIN validations v ON v.transaction_id = t.id
                  AND v.ledger_book_id = t.ledger_book_id
                JOIN confirmations c ON c.validation_id = v.id
                  AND c.ledger_book_id = v.ledger_book_id
                WHERE t.id = NEW.transaction_id
                  AND t.ledger_book_id = NEW.ledger_book_id AND t.state = 'proposed'
                  AND c.id = NEW.confirmation_id AND c.actor_id = chatbook_actor()
                  AND t.entry_date = NEW.entry_date AND t.description = NEW.description
                  AND t.reverses_entry_id IS NEW.reverses_entry_id
            ) THEN RAISE(ABORT, 'confirmation_mismatch') END;
            SELECT CASE WHEN (
                SELECT count(*) FROM journal_lines
                WHERE entry_id = NEW.id AND ledger_book_id = NEW.ledger_book_id
            ) < 2 THEN RAISE(ABORT, 'invalid_line_count') END;
            SELECT CASE WHEN (
                SELECT sum(debit) != sum(credit) FROM journal_lines
                WHERE entry_id = NEW.id AND ledger_book_id = NEW.ledger_book_id
            ) THEN RAISE(ABORT, 'unbalanced_entry') END;
            SELECT CASE WHEN EXISTS (
                SELECT 1 FROM journal_lines l JOIN accounts a
                  ON a.id = l.account_id AND a.ledger_book_id = l.ledger_book_id
                WHERE l.entry_id = NEW.id AND l.ledger_book_id = NEW.ledger_book_id
                  AND a.active = 0
            ) THEN RAISE(ABORT, 'inactive_account') END;
            SELECT CASE WHEN EXISTS (
                SELECT l.position, l.account_id, l.debit, l.credit, p.project_id
                FROM journal_lines l JOIN business_journal_line_projects p
                  ON p.line_id = l.id AND p.ledger_book_id = l.ledger_book_id
                WHERE l.entry_id = NEW.id AND l.ledger_book_id = NEW.ledger_book_id
                EXCEPT
                SELECT l.position, l.account_id, l.debit, l.credit, p.project_id
                FROM transaction_lines l JOIN business_proposal_line_projects p
                  ON p.line_id = l.id AND p.ledger_book_id = l.ledger_book_id
                WHERE l.transaction_id = NEW.transaction_id
                  AND l.ledger_book_id = NEW.ledger_book_id
            ) OR EXISTS (
                SELECT l.position, l.account_id, l.debit, l.credit, p.project_id
                FROM transaction_lines l JOIN business_proposal_line_projects p
                  ON p.line_id = l.id AND p.ledger_book_id = l.ledger_book_id
                WHERE l.transaction_id = NEW.transaction_id
                  AND l.ledger_book_id = NEW.ledger_book_id
                EXCEPT
                SELECT l.position, l.account_id, l.debit, l.credit, p.project_id
                FROM journal_lines l JOIN business_journal_line_projects p
                  ON p.line_id = l.id AND p.ledger_book_id = l.ledger_book_id
                WHERE l.entry_id = NEW.id AND l.ledger_book_id = NEW.ledger_book_id
            ) THEN RAISE(ABORT, 'proposal_mismatch') END;
            SELECT CASE WHEN NEW.reverses_entry_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM journal_entries
                WHERE id = NEW.reverses_entry_id AND ledger_book_id = NEW.ledger_book_id
                  AND state = 'posted' AND entry_date <= NEW.entry_date
            ) THEN RAISE(ABORT, 'invalid_reversal_target') END;
            SELECT CASE WHEN NEW.reverses_entry_id IS NOT NULL AND (EXISTS (
                SELECT l.position, l.account_id, l.debit, l.credit, p.project_id
                FROM journal_lines l JOIN business_journal_line_projects p
                  ON p.line_id = l.id AND p.ledger_book_id = l.ledger_book_id
                WHERE l.entry_id = NEW.id AND l.ledger_book_id = NEW.ledger_book_id
                EXCEPT
                SELECT l.position, l.account_id, l.credit, l.debit, p.project_id
                FROM journal_lines l JOIN business_journal_line_projects p
                  ON p.line_id = l.id AND p.ledger_book_id = l.ledger_book_id
                WHERE l.entry_id = NEW.reverses_entry_id
                  AND l.ledger_book_id = NEW.ledger_book_id
            ) OR EXISTS (
                SELECT l.position, l.account_id, l.credit, l.debit, p.project_id
                FROM journal_lines l JOIN business_journal_line_projects p
                  ON p.line_id = l.id AND p.ledger_book_id = l.ledger_book_id
                WHERE l.entry_id = NEW.reverses_entry_id
                  AND l.ledger_book_id = NEW.ledger_book_id
                EXCEPT
                SELECT l.position, l.account_id, l.debit, l.credit, p.project_id
                FROM journal_lines l JOIN business_journal_line_projects p
                  ON p.line_id = l.id AND p.ledger_book_id = l.ledger_book_id
                WHERE l.entry_id = NEW.id AND l.ledger_book_id = NEW.ledger_book_id
            )) THEN RAISE(ABORT, 'invalid_reversal_lines') END;
        END;

        CREATE TRIGGER audit_scope_no_update BEFORE UPDATE ON audit_event_book_scopes
        BEGIN SELECT RAISE(ABORT, 'immutable_audit_history'); END;
        CREATE TRIGGER audit_scope_no_delete BEFORE DELETE ON audit_event_book_scopes
        BEGIN SELECT RAISE(ABORT, 'immutable_audit_history'); END;
        CREATE TRIGGER audit_scope_no_replace BEFORE INSERT ON audit_event_book_scopes
        WHEN EXISTS (
            SELECT 1 FROM audit_event_book_scopes WHERE audit_sequence = NEW.audit_sequence
        )
        BEGIN SELECT RAISE(ABORT, 'immutable_audit_history'); END;
        """,
    )

    key_columns = {
        "confirmation_provenance": "confirmation_id",
        "business_proposal_documents": "proposal_id",
        "business_proposal_line_projects": "line_id",
        "business_journal_line_projects": "line_id",
        "audit_event_book_scopes": "audit_sequence",
    }
    for table in CANONICAL_BOOK_TABLES:
        key = key_columns.get(table, "id")
        connection.execute(
            f"""
            CREATE TRIGGER no_replace_{table} BEFORE INSERT ON {table}
            WHEN EXISTS (SELECT 1 FROM {table} WHERE {key} = NEW.{key})
            BEGIN SELECT RAISE(ABORT, 'immutable_identity'); END
            """
        )
        connection.execute(
            f"""
            CREATE TRIGGER no_delete_{table} BEFORE DELETE ON {table}
            BEGIN SELECT RAISE(ABORT, 'immutable_history'); END
            """
        )
        if table not in {"accounts", "accounting_periods", "transactions", "journal_entries"}:
            connection.execute(
                f"""
                CREATE TRIGGER no_update_{table} BEFORE UPDATE ON {table}
                BEGIN SELECT RAISE(ABORT, 'immutable_history'); END
                """
            )
        if table != "audit_event_book_scopes":
            for operation in ("INSERT", "UPDATE"):
                connection.execute(
                    f"""
                    CREATE TRIGGER book_context_{table}_{operation.lower()}
                    BEFORE {operation} ON {table}
                    WHEN NEW.ledger_book_id != chatbook_book()
                    BEGIN SELECT RAISE(ABORT, 'wrong_ledger_book_context'); END
                    """
                )

    for table in AUDITED_CANONICAL_TABLES:
        _install_audit_trigger(connection, table, "insert")
        if table in {"accounts", "accounting_periods", "transactions", "journal_entries"}:
            _install_audit_trigger(connection, table, "update")


def verify_canonical_mapping(connection: sqlite3.Connection) -> None:
    """Fail if the v4 BUSINESS book mapping or sidecar contract is incomplete."""
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version != CANONICAL_SCHEMA_VERSION:
        raise sqlite3.DatabaseError("canonical_schema_version")
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
    missing_scope = int(
        connection.execute(
            "SELECT count(*) FROM audit_events a LEFT JOIN audit_event_book_scopes s "
            "ON s.audit_sequence = a.sequence WHERE a.entity_type IN "
            "('charts_of_accounts','accounts','accounting_periods','transactions',"
            "'transaction_lines','validations','confirmations','journal_entries','journal_lines') "
            "AND s.audit_sequence IS NULL"
        ).fetchone()[0]
    )
    duplicate_or_wrong_scope = int(
        connection.execute(
            "SELECT count(*) FROM audit_event_book_scopes s JOIN audit_events a "
            "ON a.sequence = s.audit_sequence JOIN ledger_books b ON b.id = s.ledger_book_id "
            "WHERE a.organization_id IS NOT b.organization_id"
        ).fetchone()[0]
    )
    if mismatch or orphan or missing_scope or duplicate_or_wrong_scope:
        raise sqlite3.DatabaseError("canonical_mapping_invalid")
