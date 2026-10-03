-- v3: additive BUSINESS LedgerBook mapping; financial tables remain organization-scoped.
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
) STRICT;

CREATE TABLE user_credentials (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    username TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (
        length(trim(username)) BETWEEN 3 AND 254
    ),
    password_hash TEXT NOT NULL CHECK (length(password_hash) > 0),
    created_at TEXT NOT NULL
) STRICT;

CREATE TABLE auth_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL UNIQUE CHECK (
        length(token_hash) = 64 AND token_hash NOT GLOB '*[^0-9a-f]*'
    ),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    CHECK (expires_at > created_at)
) STRICT;

CREATE INDEX auth_sessions_by_user ON auth_sessions(user_id, expires_at);

CREATE TABLE organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    currency TEXT NOT NULL CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
    minor_unit_digits INTEGER NOT NULL CHECK (minor_unit_digits BETWEEN 0 AND 6)
) STRICT;

CREATE TABLE ledger_books (
    id TEXT PRIMARY KEY,
    owner_kind TEXT NOT NULL CHECK (owner_kind = 'BUSINESS'),
    organization_id TEXT NOT NULL UNIQUE REFERENCES organizations(id),
    currency TEXT NOT NULL CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
    minor_unit_digits INTEGER NOT NULL CHECK (minor_unit_digits BETWEEN 0 AND 6),
    created_at TEXT NOT NULL,
    creation_source TEXT NOT NULL CHECK (
        creation_source IN ('schema_v3_migration', 'organization_creation')
    ),
    creation_version TEXT NOT NULL CHECK (creation_version = 'm5.1-c1-v1'),
    CHECK (id = 'book:business:' || organization_id),
    UNIQUE (owner_kind, organization_id)
) STRICT;

CREATE TRIGGER ledger_book_matches_organization BEFORE INSERT ON ledger_books
WHEN NOT EXISTS (
    SELECT 1 FROM organizations o WHERE o.id = NEW.organization_id
      AND o.currency = NEW.currency
      AND o.minor_unit_digits = NEW.minor_unit_digits
)
BEGIN SELECT RAISE(ABORT, 'ledger_book_organization_mismatch'); END;

CREATE TRIGGER ledger_book_no_replace BEFORE INSERT ON ledger_books
WHEN EXISTS (
    SELECT 1 FROM ledger_books WHERE id = NEW.id OR organization_id = NEW.organization_id
)
BEGIN SELECT RAISE(ABORT, 'immutable_ledger_book'); END;

CREATE TRIGGER ledger_book_no_update BEFORE UPDATE ON ledger_books
BEGIN SELECT RAISE(ABORT, 'immutable_ledger_book'); END;

CREATE TRIGGER ledger_book_no_delete BEFORE DELETE ON ledger_books
BEGIN SELECT RAISE(ABORT, 'immutable_ledger_book'); END;

CREATE TRIGGER organization_creates_business_book AFTER INSERT ON organizations
BEGIN
    INSERT INTO ledger_books (
        id, owner_kind, organization_id, currency, minor_unit_digits,
        created_at, creation_source, creation_version
    ) VALUES (
        'book:business:' || NEW.id, 'BUSINESS', NEW.id, NEW.currency,
        NEW.minor_unit_digits, chatbook_now(), 'organization_creation', 'm5.1-c1-v1'
    );
END;

CREATE TABLE memberships (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    user_id TEXT NOT NULL REFERENCES users(id),
    role TEXT NOT NULL CHECK (role IN ('OWNER', 'ADMIN', 'ACCOUNTANT', 'MEMBER', 'VIEWER')),
    UNIQUE (organization_id, user_id)
) STRICT;

CREATE TABLE charts_of_accounts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL UNIQUE REFERENCES organizations(id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    UNIQUE (organization_id, id)
) STRICT;

CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    chart_id TEXT NOT NULL,
    code TEXT NOT NULL CHECK (length(trim(code)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    account_type TEXT NOT NULL CHECK (
        account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')
    ),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    FOREIGN KEY (organization_id, chart_id) REFERENCES charts_of_accounts(organization_id, id),
    UNIQUE (organization_id, code),
    UNIQUE (organization_id, id)
) STRICT;

CREATE TABLE accounting_periods (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    starts_on TEXT NOT NULL CHECK (
        length(starts_on) = 10 AND date(starts_on, '+0 days') IS NOT NULL
        AND date(starts_on, '+0 days') = starts_on
    ),
    ends_on TEXT NOT NULL CHECK (
        length(ends_on) = 10 AND date(ends_on, '+0 days') IS NOT NULL
        AND date(ends_on, '+0 days') = ends_on AND ends_on >= starts_on
    ),
    locked INTEGER NOT NULL DEFAULT 0 CHECK (locked IN (0, 1)),
    UNIQUE (organization_id, id)
) STRICT;

CREATE TRIGGER period_no_overlap BEFORE INSERT ON accounting_periods BEGIN
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM accounting_periods WHERE organization_id = NEW.organization_id
        AND starts_on <= NEW.ends_on AND ends_on >= NEW.starts_on
    ) THEN RAISE(ABORT, 'period_overlap') END;
END;

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    description TEXT NOT NULL,
    client TEXT,
    expected_revenue INTEGER CHECK (expected_revenue BETWEEN 0 AND 9000000000000),
    budget INTEGER CHECK (budget BETWEEN 0 AND 9000000000000),
    starts_on TEXT CHECK (starts_on IS NULL OR (
        length(starts_on) = 10 AND date(starts_on, '+0 days') IS NOT NULL
        AND date(starts_on, '+0 days') = starts_on
    )),
    ends_on TEXT CHECK (ends_on IS NULL OR (
        length(ends_on) = 10 AND date(ends_on, '+0 days') IS NOT NULL
        AND date(ends_on, '+0 days') = ends_on
    )),
    status TEXT NOT NULL CHECK (status IN ('planned', 'active', 'completed', 'cancelled')),
    CHECK (starts_on IS NULL OR ends_on IS NULL OR ends_on >= starts_on),
    UNIQUE (organization_id, id)
) STRICT;

CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    filename TEXT NOT NULL CHECK (length(trim(filename)) > 0),
    media_type TEXT NOT NULL CHECK (length(trim(media_type)) > 0),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
    storage_reference TEXT NOT NULL CHECK (length(trim(storage_reference)) > 0),
    UNIQUE (organization_id, id)
) STRICT;

CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    entry_date TEXT NOT NULL CHECK (
        length(entry_date) = 10 AND date(entry_date, '+0 days') IS NOT NULL
        AND date(entry_date, '+0 days') = entry_date
    ),
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    document_id TEXT,
    reverses_entry_id TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version = 1),
    state TEXT NOT NULL DEFAULT 'assembling' CHECK (state IN ('assembling', 'proposed')),
    FOREIGN KEY (organization_id, document_id) REFERENCES documents(organization_id, id),
    FOREIGN KEY (organization_id, reverses_entry_id) REFERENCES journal_entries(organization_id, id),
    UNIQUE (organization_id, id)
) STRICT;

CREATE TABLE transaction_lines (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 1000),
    account_id TEXT NOT NULL,
    debit INTEGER NOT NULL CHECK (debit BETWEEN 0 AND 9000000000000),
    credit INTEGER NOT NULL CHECK (credit BETWEEN 0 AND 9000000000000),
    project_id TEXT,
    CHECK ((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)),
    FOREIGN KEY (organization_id, transaction_id) REFERENCES transactions(organization_id, id),
    FOREIGN KEY (organization_id, account_id) REFERENCES accounts(organization_id, id),
    FOREIGN KEY (organization_id, project_id) REFERENCES projects(organization_id, id),
    UNIQUE (transaction_id, position)
) STRICT;

CREATE TABLE validations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL CHECK (length(fingerprint) = 64),
    actor_id TEXT NOT NULL,
    FOREIGN KEY (organization_id, transaction_id) REFERENCES transactions(organization_id, id),
    FOREIGN KEY (organization_id, actor_id) REFERENCES memberships(organization_id, user_id),
    UNIQUE (organization_id, id)
) STRICT;

CREATE TABLE confirmations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    validation_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    FOREIGN KEY (organization_id, validation_id) REFERENCES validations(organization_id, id),
    FOREIGN KEY (organization_id, actor_id) REFERENCES memberships(organization_id, user_id),
    UNIQUE (organization_id, id)
) STRICT;

CREATE TABLE confirmation_provenance (
    confirmation_id TEXT PRIMARY KEY REFERENCES confirmations(id),
    organization_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    proposal_version INTEGER NOT NULL CHECK (proposal_version = 1),
    confirmed_at TEXT NOT NULL,
    confirmation_request_id TEXT NOT NULL CHECK (length(trim(confirmation_request_id)) > 0),
    FOREIGN KEY (organization_id, confirmation_id)
        REFERENCES confirmations(organization_id, id),
    FOREIGN KEY (organization_id, proposal_id)
        REFERENCES transactions(organization_id, id)
) STRICT;

CREATE TABLE command_idempotency (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (length(trim(operation)) > 0),
    idempotency_key TEXT NOT NULL CHECK (length(trim(idempotency_key)) BETWEEN 8 AND 200),
    request_fingerprint TEXT NOT NULL CHECK (
        length(request_fingerprint) = 64
        AND request_fingerprint NOT GLOB '*[^0-9a-f]*'
    ),
    resource_type TEXT NOT NULL CHECK (length(trim(resource_type)) > 0),
    resource_id TEXT NOT NULL CHECK (length(trim(resource_id)) > 0),
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id, actor_id) REFERENCES memberships(organization_id, user_id),
    UNIQUE (organization_id, actor_id, operation, idempotency_key)
) STRICT;

CREATE TABLE journal_entries (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL UNIQUE,
    confirmation_id TEXT NOT NULL UNIQUE,
    period_id TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    description TEXT NOT NULL,
    reverses_entry_id TEXT,
    state TEXT NOT NULL DEFAULT 'assembling' CHECK (state IN ('assembling', 'posted')),
    FOREIGN KEY (organization_id, transaction_id) REFERENCES transactions(organization_id, id),
    FOREIGN KEY (organization_id, confirmation_id) REFERENCES confirmations(organization_id, id),
    FOREIGN KEY (organization_id, period_id) REFERENCES accounting_periods(organization_id, id),
    FOREIGN KEY (organization_id, reverses_entry_id) REFERENCES journal_entries(organization_id, id),
    UNIQUE (organization_id, id)
) STRICT;

CREATE UNIQUE INDEX one_posted_reversal ON journal_entries(reverses_entry_id)
    WHERE state = 'posted' AND reverses_entry_id IS NOT NULL;

CREATE TABLE journal_lines (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    entry_id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 1000),
    account_id TEXT NOT NULL,
    debit INTEGER NOT NULL CHECK (debit BETWEEN 0 AND 9000000000000),
    credit INTEGER NOT NULL CHECK (credit BETWEEN 0 AND 9000000000000),
    project_id TEXT,
    CHECK ((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)),
    FOREIGN KEY (organization_id, entry_id) REFERENCES journal_entries(organization_id, id),
    FOREIGN KEY (organization_id, account_id) REFERENCES accounts(organization_id, id),
    FOREIGN KEY (organization_id, project_id) REFERENCES projects(organization_id, id),
    UNIQUE (entry_id, position)
) STRICT;

CREATE INDEX ledger_by_date ON journal_entries(organization_id, state, entry_date);
CREATE INDEX ledger_by_account ON journal_lines(organization_id, account_id, entry_id);
CREATE INDEX ledger_by_project ON journal_lines(organization_id, project_id, entry_id);

CREATE TABLE audit_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id TEXT REFERENCES organizations(id),
    actor_id TEXT NOT NULL REFERENCES users(id),
    occurred_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    previous_state TEXT CHECK (previous_state IS NULL OR json_valid(previous_state)),
    new_state TEXT CHECK (new_state IS NULL OR json_valid(new_state)),
    metadata TEXT NOT NULL CHECK (json_valid(metadata))
) STRICT;

CREATE INDEX audit_by_entity ON audit_events(organization_id, entity_type, entity_id, sequence);

CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events BEGIN
    SELECT RAISE(ABORT, 'immutable_audit_history');
END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events BEGIN
    SELECT RAISE(ABORT, 'immutable_audit_history');
END;
CREATE TRIGGER audit_no_replace BEFORE INSERT ON audit_events
WHEN EXISTS (SELECT 1 FROM audit_events WHERE sequence = NEW.sequence)
BEGIN SELECT RAISE(ABORT, 'immutable_audit_history'); END;

CREATE TRIGGER transaction_starts_assembling BEFORE INSERT ON transactions
WHEN NEW.state != 'assembling' BEGIN SELECT RAISE(ABORT, 'invalid_initial_state'); END;

CREATE TRIGGER transaction_freeze BEFORE UPDATE ON transactions
WHEN OLD.state != 'assembling' OR NEW.state != 'proposed'
    OR NEW.id IS NOT OLD.id OR NEW.organization_id IS NOT OLD.organization_id
    OR NEW.entry_date IS NOT OLD.entry_date OR NEW.description IS NOT OLD.description
    OR NEW.document_id IS NOT OLD.document_id OR NEW.reverses_entry_id IS NOT OLD.reverses_entry_id
    OR NEW.version IS NOT OLD.version
BEGIN SELECT RAISE(ABORT, 'immutable_proposal'); END;

CREATE TRIGGER transaction_line_insert BEFORE INSERT ON transaction_lines
WHEN NOT EXISTS (SELECT 1 FROM transactions WHERE id = NEW.transaction_id AND state = 'assembling')
BEGIN SELECT RAISE(ABORT, 'immutable_proposal'); END;

CREATE TRIGGER journal_starts_assembling BEFORE INSERT ON journal_entries
WHEN NEW.state != 'assembling' BEGIN SELECT RAISE(ABORT, 'invalid_initial_state'); END;

CREATE TRIGGER journal_line_insert BEFORE INSERT ON journal_lines
WHEN NOT EXISTS (SELECT 1 FROM journal_entries WHERE id = NEW.entry_id AND state = 'assembling')
BEGIN SELECT RAISE(ABORT, 'immutable_posted_history'); END;

CREATE TRIGGER journal_freeze BEFORE UPDATE ON journal_entries
WHEN OLD.state != 'assembling' OR NEW.state != 'posted'
    OR NEW.id IS NOT OLD.id OR NEW.organization_id IS NOT OLD.organization_id
    OR NEW.transaction_id IS NOT OLD.transaction_id OR NEW.confirmation_id IS NOT OLD.confirmation_id
    OR NEW.period_id IS NOT OLD.period_id OR NEW.entry_date IS NOT OLD.entry_date
    OR NEW.description IS NOT OLD.description OR NEW.reverses_entry_id IS NOT OLD.reverses_entry_id
BEGIN SELECT RAISE(ABORT, 'immutable_posted_history'); END;

CREATE TRIGGER journal_validate BEFORE UPDATE OF state ON journal_entries
WHEN NEW.state = 'posted' BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM accounting_periods WHERE id = NEW.period_id
        AND organization_id = NEW.organization_id AND locked = 0
        AND NEW.entry_date BETWEEN starts_on AND ends_on
    ) THEN RAISE(ABORT, 'period_closed_or_missing') END;
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM transactions t
        JOIN validations v ON v.transaction_id = t.id
        JOIN confirmations c ON c.validation_id = v.id
        WHERE t.id = NEW.transaction_id AND t.state = 'proposed'
        AND t.organization_id = NEW.organization_id AND c.id = NEW.confirmation_id
        AND c.actor_id = chatbook_actor() AND t.entry_date = NEW.entry_date
        AND t.description = NEW.description AND t.reverses_entry_id IS NEW.reverses_entry_id
    ) THEN RAISE(ABORT, 'confirmation_mismatch') END;
    SELECT CASE WHEN (SELECT count(*) FROM journal_lines WHERE entry_id = NEW.id) < 2
        THEN RAISE(ABORT, 'invalid_line_count') END;
    SELECT CASE WHEN (
        SELECT sum(debit) != sum(credit) FROM journal_lines WHERE entry_id = NEW.id
    ) THEN RAISE(ABORT, 'unbalanced_entry') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM journal_lines l JOIN accounts a ON a.id = l.account_id
        WHERE l.entry_id = NEW.id AND a.active = 0
    ) THEN RAISE(ABORT, 'inactive_account') END;
    SELECT CASE WHEN EXISTS (
        SELECT position, account_id, debit, credit, project_id
        FROM journal_lines WHERE entry_id = NEW.id
        EXCEPT SELECT position, account_id, debit, credit, project_id
        FROM transaction_lines WHERE transaction_id = NEW.transaction_id
    ) OR EXISTS (
        SELECT position, account_id, debit, credit, project_id
        FROM transaction_lines WHERE transaction_id = NEW.transaction_id
        EXCEPT SELECT position, account_id, debit, credit, project_id
        FROM journal_lines WHERE entry_id = NEW.id
    ) THEN RAISE(ABORT, 'proposal_mismatch') END;
    SELECT CASE WHEN NEW.reverses_entry_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM journal_entries WHERE id = NEW.reverses_entry_id AND state = 'posted'
        AND entry_date <= NEW.entry_date
    ) THEN RAISE(ABORT, 'invalid_reversal_target') END;
    SELECT CASE WHEN NEW.reverses_entry_id IS NOT NULL AND (EXISTS (
        SELECT position, account_id, debit, credit, project_id
        FROM journal_lines WHERE entry_id = NEW.id
        EXCEPT SELECT position, account_id, credit, debit, project_id
        FROM journal_lines WHERE entry_id = NEW.reverses_entry_id
    ) OR EXISTS (
        SELECT position, account_id, credit, debit, project_id
        FROM journal_lines WHERE entry_id = NEW.reverses_entry_id
        EXCEPT SELECT position, account_id, debit, credit, project_id
        FROM journal_lines WHERE entry_id = NEW.id
    )) THEN RAISE(ABORT, 'invalid_reversal_lines') END;
END;

CREATE TRIGGER period_lock_only BEFORE UPDATE ON accounting_periods
WHEN OLD.locked != 0 OR NEW.locked != 1
    OR NEW.id IS NOT OLD.id OR NEW.organization_id IS NOT OLD.organization_id
    OR NEW.name IS NOT OLD.name OR NEW.starts_on IS NOT OLD.starts_on OR NEW.ends_on IS NOT OLD.ends_on
BEGIN SELECT RAISE(ABORT, 'period_immutable_or_locked'); END;

CREATE TRIGGER account_active_only BEFORE UPDATE ON accounts
WHEN NEW.id IS NOT OLD.id OR NEW.organization_id IS NOT OLD.organization_id
    OR NEW.chart_id IS NOT OLD.chart_id OR NEW.code IS NOT OLD.code
    OR NEW.name IS NOT OLD.name OR NEW.account_type IS NOT OLD.account_type
BEGIN SELECT RAISE(ABORT, 'immutable_account_identity'); END;

CREATE TRIGGER project_fields_only BEFORE UPDATE ON projects
WHEN NEW.id IS NOT OLD.id OR NEW.organization_id IS NOT OLD.organization_id
BEGIN SELECT RAISE(ABORT, 'immutable_project_identity'); END;

CREATE TRIGGER credential_no_update BEFORE UPDATE ON user_credentials
BEGIN SELECT RAISE(ABORT, 'immutable_credentials'); END;
CREATE TRIGGER credential_no_delete BEFORE DELETE ON user_credentials
BEGIN SELECT RAISE(ABORT, 'immutable_credentials'); END;

CREATE TRIGGER auth_session_revoke_only BEFORE UPDATE ON auth_sessions
WHEN NEW.id IS NOT OLD.id OR NEW.user_id IS NOT OLD.user_id
    OR NEW.token_hash IS NOT OLD.token_hash OR NEW.created_at IS NOT OLD.created_at
    OR NEW.expires_at IS NOT OLD.expires_at OR OLD.revoked_at IS NOT NULL
    OR NEW.revoked_at IS NULL
BEGIN SELECT RAISE(ABORT, 'invalid_session_update'); END;
CREATE TRIGGER auth_session_no_delete BEFORE DELETE ON auth_sessions
BEGIN SELECT RAISE(ABORT, 'immutable_session_history'); END;

CREATE TRIGGER confirmation_provenance_validate BEFORE INSERT ON confirmation_provenance
WHEN NOT EXISTS (
    SELECT 1 FROM confirmations c
    JOIN validations v ON v.id = c.validation_id AND v.organization_id = c.organization_id
    JOIN transactions t ON t.id = v.transaction_id AND t.organization_id = v.organization_id
    WHERE c.id = NEW.confirmation_id AND c.organization_id = NEW.organization_id
      AND t.id = NEW.proposal_id AND t.version = NEW.proposal_version
)
BEGIN SELECT RAISE(ABORT, 'confirmation_provenance_mismatch'); END;
CREATE TRIGGER confirmation_provenance_no_update BEFORE UPDATE ON confirmation_provenance
BEGIN SELECT RAISE(ABORT, 'immutable_confirmation_provenance'); END;
CREATE TRIGGER confirmation_provenance_no_delete BEFORE DELETE ON confirmation_provenance
BEGIN SELECT RAISE(ABORT, 'immutable_confirmation_provenance'); END;

CREATE TRIGGER command_idempotency_no_update BEFORE UPDATE ON command_idempotency
BEGIN SELECT RAISE(ABORT, 'immutable_idempotency_history'); END;
CREATE TRIGGER command_idempotency_no_delete BEFORE DELETE ON command_idempotency
BEGIN SELECT RAISE(ABORT, 'immutable_idempotency_history'); END;
