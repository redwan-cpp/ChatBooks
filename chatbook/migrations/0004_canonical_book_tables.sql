CREATE UNIQUE INDEX IF NOT EXISTS ledger_books_book_organization
    ON ledger_books(id, organization_id);

CREATE TABLE v4_charts_of_accounts (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL UNIQUE REFERENCES ledger_books(id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    UNIQUE (ledger_book_id, id)
) STRICT;

CREATE TABLE v4_accounts (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    chart_id TEXT NOT NULL,
    code TEXT NOT NULL CHECK (length(trim(code)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    account_type TEXT NOT NULL CHECK (
        account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')
    ),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    FOREIGN KEY (ledger_book_id, chart_id)
        REFERENCES v4_charts_of_accounts(ledger_book_id, id),
    UNIQUE (ledger_book_id, code),
    UNIQUE (ledger_book_id, id)
) STRICT;

CREATE TABLE v4_accounting_periods (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL REFERENCES ledger_books(id),
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
    UNIQUE (ledger_book_id, id)
) STRICT;

CREATE TABLE v4_transactions (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL REFERENCES ledger_books(id),
    entry_date TEXT NOT NULL CHECK (
        length(entry_date) = 10 AND date(entry_date, '+0 days') IS NOT NULL
        AND date(entry_date, '+0 days') = entry_date
    ),
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    reverses_entry_id TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version = 1),
    state TEXT NOT NULL DEFAULT 'assembling' CHECK (state IN ('assembling', 'proposed')),
    FOREIGN KEY (ledger_book_id, reverses_entry_id)
        REFERENCES v4_journal_entries(ledger_book_id, id) DEFERRABLE INITIALLY DEFERRED,
    UNIQUE (ledger_book_id, id)
) STRICT;

CREATE TABLE v4_transaction_lines (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 1000),
    account_id TEXT NOT NULL,
    debit INTEGER NOT NULL CHECK (debit BETWEEN 0 AND 9000000000000),
    credit INTEGER NOT NULL CHECK (credit BETWEEN 0 AND 9000000000000),
    CHECK ((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)),
    FOREIGN KEY (ledger_book_id, transaction_id)
        REFERENCES v4_transactions(ledger_book_id, id),
    FOREIGN KEY (ledger_book_id, account_id)
        REFERENCES v4_accounts(ledger_book_id, id),
    UNIQUE (ledger_book_id, id),
    UNIQUE (ledger_book_id, transaction_id, position)
) STRICT;

CREATE TABLE v4_validations (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL CHECK (
        length(fingerprint) = 64 AND fingerprint NOT GLOB '*[^0-9a-f]*'
    ),
    fingerprint_version TEXT NOT NULL DEFAULT 'organization-v1'
        CHECK (fingerprint_version = 'organization-v1'),
    actor_id TEXT NOT NULL REFERENCES users(id),
    FOREIGN KEY (ledger_book_id, transaction_id)
        REFERENCES v4_transactions(ledger_book_id, id),
    UNIQUE (ledger_book_id, id)
) STRICT;

CREATE TABLE v4_confirmations (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    validation_id TEXT NOT NULL,
    actor_id TEXT NOT NULL REFERENCES users(id),
    FOREIGN KEY (ledger_book_id, validation_id)
        REFERENCES v4_validations(ledger_book_id, id),
    UNIQUE (ledger_book_id, id)
) STRICT;

CREATE TABLE v4_confirmation_provenance (
    confirmation_id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    proposal_version INTEGER NOT NULL CHECK (proposal_version = 1),
    confirmed_at TEXT NOT NULL,
    confirmation_request_id TEXT NOT NULL CHECK (length(trim(confirmation_request_id)) > 0),
    FOREIGN KEY (ledger_book_id, confirmation_id)
        REFERENCES v4_confirmations(ledger_book_id, id),
    FOREIGN KEY (ledger_book_id, proposal_id)
        REFERENCES v4_transactions(ledger_book_id, id)
) STRICT;

CREATE TABLE v4_command_idempotency (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL REFERENCES ledger_books(id),
    actor_id TEXT NOT NULL REFERENCES users(id),
    operation TEXT NOT NULL CHECK (length(trim(operation)) > 0),
    idempotency_key TEXT NOT NULL CHECK (length(trim(idempotency_key)) BETWEEN 8 AND 200),
    request_fingerprint TEXT NOT NULL CHECK (
        length(request_fingerprint) = 64
        AND request_fingerprint NOT GLOB '*[^0-9a-f]*'
    ),
    resource_type TEXT NOT NULL CHECK (length(trim(resource_type)) > 0),
    resource_id TEXT NOT NULL CHECK (length(trim(resource_id)) > 0),
    created_at TEXT NOT NULL,
    UNIQUE (ledger_book_id, id),
    UNIQUE (ledger_book_id, actor_id, operation, idempotency_key)
) STRICT;

CREATE TABLE v4_journal_entries (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    confirmation_id TEXT NOT NULL,
    period_id TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    description TEXT NOT NULL,
    reverses_entry_id TEXT,
    state TEXT NOT NULL DEFAULT 'assembling' CHECK (state IN ('assembling', 'posted')),
    FOREIGN KEY (ledger_book_id, transaction_id)
        REFERENCES v4_transactions(ledger_book_id, id),
    FOREIGN KEY (ledger_book_id, confirmation_id)
        REFERENCES v4_confirmations(ledger_book_id, id),
    FOREIGN KEY (ledger_book_id, period_id)
        REFERENCES v4_accounting_periods(ledger_book_id, id),
    FOREIGN KEY (ledger_book_id, reverses_entry_id)
        REFERENCES v4_journal_entries(ledger_book_id, id) DEFERRABLE INITIALLY DEFERRED,
    UNIQUE (ledger_book_id, id),
    UNIQUE (ledger_book_id, transaction_id),
    UNIQUE (ledger_book_id, confirmation_id)
) STRICT;

CREATE TABLE v4_journal_lines (
    id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    entry_id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 1000),
    account_id TEXT NOT NULL,
    debit INTEGER NOT NULL CHECK (debit BETWEEN 0 AND 9000000000000),
    credit INTEGER NOT NULL CHECK (credit BETWEEN 0 AND 9000000000000),
    CHECK ((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)),
    FOREIGN KEY (ledger_book_id, entry_id)
        REFERENCES v4_journal_entries(ledger_book_id, id),
    FOREIGN KEY (ledger_book_id, account_id)
        REFERENCES v4_accounts(ledger_book_id, id),
    UNIQUE (ledger_book_id, id),
    UNIQUE (ledger_book_id, entry_id, position)
) STRICT;

CREATE TABLE v4_business_proposal_documents (
    proposal_id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    document_id TEXT,
    FOREIGN KEY (ledger_book_id, proposal_id)
        REFERENCES v4_transactions(ledger_book_id, id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (ledger_book_id, organization_id)
        REFERENCES ledger_books(id, organization_id),
    FOREIGN KEY (organization_id, document_id)
        REFERENCES documents(organization_id, id)
) STRICT;

CREATE TABLE v4_business_proposal_line_projects (
    line_id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    project_id TEXT,
    FOREIGN KEY (ledger_book_id, line_id)
        REFERENCES v4_transaction_lines(ledger_book_id, id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (ledger_book_id, organization_id)
        REFERENCES ledger_books(id, organization_id),
    FOREIGN KEY (organization_id, project_id)
        REFERENCES projects(organization_id, id)
) STRICT;

CREATE TABLE v4_business_journal_line_projects (
    line_id TEXT PRIMARY KEY,
    ledger_book_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    project_id TEXT,
    FOREIGN KEY (ledger_book_id, line_id)
        REFERENCES v4_journal_lines(ledger_book_id, id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (ledger_book_id, organization_id)
        REFERENCES ledger_books(id, organization_id),
    FOREIGN KEY (organization_id, project_id)
        REFERENCES projects(organization_id, id)
) STRICT;

CREATE TABLE v4_audit_event_book_scopes (
    audit_sequence INTEGER PRIMARY KEY REFERENCES audit_events(sequence),
    ledger_book_id TEXT NOT NULL REFERENCES ledger_books(id)
) STRICT;
