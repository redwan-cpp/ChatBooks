ALTER TABLE memberships ADD COLUMN role TEXT NOT NULL DEFAULT 'MEMBER'
    CHECK (role IN ('OWNER', 'ADMIN', 'ACCOUNTANT', 'MEMBER', 'VIEWER'));

DROP TRIGGER IF EXISTS no_update_memberships;
DROP TRIGGER IF EXISTS audit_memberships_update;

UPDATE memberships
SET role = CASE
    WHEN user_id = COALESCE(
        (
            SELECT actor_id
            FROM audit_events
            WHERE entity_type = 'organizations'
              AND entity_id = memberships.organization_id
              AND event_type = 'organizations.insert'
            ORDER BY sequence
            LIMIT 1
        ),
        (
            SELECT fallback.user_id
            FROM memberships AS fallback
            WHERE fallback.organization_id = memberships.organization_id
            ORDER BY fallback.rowid
            LIMIT 1
        )
    ) THEN 'OWNER'
    ELSE 'MEMBER'
END;

ALTER TABLE transactions ADD COLUMN version INTEGER NOT NULL DEFAULT 1 CHECK (version = 1);

DROP TRIGGER IF EXISTS transaction_freeze;
CREATE TRIGGER transaction_freeze BEFORE UPDATE ON transactions
WHEN OLD.state != 'assembling' OR NEW.state != 'proposed'
    OR NEW.id IS NOT OLD.id OR NEW.organization_id IS NOT OLD.organization_id
    OR NEW.entry_date IS NOT OLD.entry_date OR NEW.description IS NOT OLD.description
    OR NEW.document_id IS NOT OLD.document_id OR NEW.reverses_entry_id IS NOT OLD.reverses_entry_id
    OR NEW.version IS NOT OLD.version
BEGIN SELECT RAISE(ABORT, 'immutable_proposal'); END;

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

INSERT INTO confirmation_provenance (
    confirmation_id, organization_id, proposal_id, proposal_version,
    confirmed_at, confirmation_request_id
)
SELECT
    c.id,
    c.organization_id,
    v.transaction_id,
    1,
    COALESCE(
        (
            SELECT occurred_at
            FROM audit_events
            WHERE entity_type = 'confirmations' AND entity_id = c.id
            ORDER BY sequence
            LIMIT 1
        ),
        '1970-01-01T00:00:00+00:00'
    ),
    'migration:' || c.id
FROM confirmations AS c
JOIN validations AS v ON v.id = c.validation_id;

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

DROP TRIGGER IF EXISTS no_update_projects;

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
