-- Additive v3 mapping only. Existing financial rows remain organization-scoped and untouched.
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

INSERT INTO ledger_books (
    id, owner_kind, organization_id, currency, minor_unit_digits,
    created_at, creation_source, creation_version
)
SELECT
    'book:business:' || id,
    'BUSINESS',
    id,
    currency,
    minor_unit_digits,
    chatbook_now(),
    'schema_v3_migration',
    'm5.1-c1-v1'
FROM organizations
ORDER BY id;

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
