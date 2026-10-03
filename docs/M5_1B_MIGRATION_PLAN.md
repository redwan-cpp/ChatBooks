# M5.1-B universal financial core migration plan

**Date:** 2026-09-27  
**Milestone:** Migration design and recovery plan only  
**Project and product:** Chatbooks
**Status:** Complete plan; additive mapping, service extraction, canonical and operational rehearsals implemented

## Purpose and non-negotiable outcome

This runbook defines how the existing organization-scoped business ledger can become the first
BUSINESS-owned `LedgerBook` without losing or changing any financial evidence. It supplements the
[implementation plan](M5_1B_IMPLEMENTATION_PLAN.md) and the accepted
[M5.1-A architecture](universal-financial-core.md). It is deliberately more conservative than a
normal schema migration because posted history, validation fingerprints, confirmation provenance,
idempotency receipts, audit rows, and reports must remain reconcilable.

The migration succeeds only if every existing identifier, proposal state, posted line, reversal
relationship, report result, receipt, audit sequence, and stored timestamp remains attributable to
the same business organization through its deterministic book. The migration must fail closed on
any mismatch. It must not reinterpret account types, projects, dates, periods, transaction purpose,
or accounting policy.

This document remains the controlling plan for later phases. M5.1-C1 separately authorized and
implemented the v2/v3 preflight, backup proof, and additive mapping. M5.1-C2 separately authorized
and implemented the service transition over unchanged schema-v3 organization storage. M5.1-C3
separately authorized and implemented canonical persistence only on disposable restored copies.
M5.1-C4A completed a synthetic operational rehearsal, recovery drills, capacity method, cutover
runbook, and release checklist. Production/business cutover remains unauthorized and unimplemented.

## M5.1-C1 implemented state

- `chatbook/migration_evidence.py` creates deterministic read-only manifests from a consistent
  SQLite copy, emits stable diagnostic codes, creates a SQLite backup while writers are blocked,
  restores it to a separate temporary database, and verifies content/report equivalence.
- `chatbook-migration-evidence SOURCE BACKUP` exposes the evidence workflow without migrating the
  source. Normal v2 startup uses the same workflow automatically and stores
  `<database>.pre-v3.backup` plus its protected manifest.
- `chatbook/migrations/0003_business_ledger_books.sql` adds the schema-v3 mapping in the same
  transaction that reconciles every legacy table and advances `user_version`.
- `ledger_books` contains `id`, BUSINESS-only `owner_kind`, unique required `organization_id`, copied
  `currency` and `minor_unit_digits`, `created_at`, `creation_source`, and `creation_version`.
- The implemented deterministic ID is exactly `book:business:<organization_id>`. Mapping rows reject
  replacement, update, deletion, invalid ownership, and currency/precision mismatch.
- An organization-insert trigger creates the book atomically. The existing engine then resolves it
  through a membership-first internal resolver. No public route accepts a book ID.
- The preflight covers SQLite integrity/foreign keys, table counts and ordered hashes, sequence
  state, proposals, fingerprints, confirmations/provenance, receipts, journals, periods, reversals,
  audit relationships, project/document references, and per-organization report fingerprints.
- Every original v2 table is hash-compared before the migration commits. LedgerBook creation emits
  no audit event and rewrites no financial row, audit payload, timestamp, state, receipt, or ID.

Normal application financial tables remain keyed by `organization_id`. M5.1-C2 adds the universal
financial service, authorized BUSINESS context, compatibility facade, and organization storage
adapter without a schema migration. M5.1-C3 adds separate v4 rehearsal copies with book-scoped
tables and an audit-book sidecar. PersonalSpace and personal behavior remain unimplemented.

## Current schema dependency map

Normal application storage is version 3 and uses `organization_id` as the financial ownership key.
Disposable C3 rehearsal targets are version 4 and use `ledger_book_id`.

| Area                | Current records and dependencies                                                                                       | Migration treatment                                                                                                      |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Identity and access | `users`, credentials, sessions, organizations, memberships                                                             | Remain unchanged. Authentication and role authority stay outside the ledger book.                                        |
| Business planning   | projects and documents belong to an organization                                                                       | Remain business-owned. They receive explicit, constrained links to book-owned proposals or journal lines where required. |
| Master data         | charts, accounts, and accounting periods belong to an organization                                                     | Gain book ownership in the canonical schema while preserving every ID and value.                                         |
| Proposal lifecycle  | transactions, lines, validations, confirmation provenance, confirmations, and command receipts are organization-scoped | Become book-scoped together. Existing versions, fingerprints, request IDs, states, and resource results remain exact.    |
| Posted ledger       | journal entries and lines are organization-scoped and link back to proposals                                           | Become book-scoped. IDs, dates, line order, amounts, reversal links, and immutability remain exact.                      |
| Audit               | append-only events retain actor, organization, entity, before/after JSON, metadata, and sequence                       | Existing rows remain byte-for-byte unchanged. A new immutable sidecar associates financial events with their book.       |
| Reports             | queries derive balances and statements from posted journal lines                                                       | Move behind the universal repository only after report parity is proved for every business book.                         |

The current `AccountingEngine` and `Database` are part of this dependency graph. The engine combines
authorization assumptions, workflow, SQL, reporting, audit reads, and receipt handling. `Database`
owns connection privacy, `BEGIN IMMEDIATE`, schema migration, transaction audit context, audit
triggers, and the audit-insert authorizer. Extracting those responsibilities is a service transition,
not a reason to alter accounting behavior.

## Target schema evolution

The migration uses two durable schema stages rather than one replacement.

### Schema v3: additive BUSINESS book mapping

Version 3 adds one `ledger_books` record for every organization and does not move financial rows.
Each book has:

- an internal stable ID derived deterministically for the migration, such as
  `book:business:<organization_id>`;
- owner kind `BUSINESS`;
- one required and unique `organization_id` reference;
- currency and minor-unit precision copied exactly from the organization;
- creation timestamp and migration provenance; and
- optional creator metadata only when it can be sourced without inventing history.

Version 3 supports BUSINESS owners only. It enforces one book per organization, prevents a book from
referring to an organization more than once, and prevents silent currency or precision divergence.
The existing financial tables, keys, APIs, queries, reports, audit triggers, and receipts continue to
use `organization_id`. This seam permits authorization and service extraction while keeping rollback
small.

### Schema v4: canonical book-scoped persistence

Version 4 keeps current public entity and table identities where practical but changes the canonical
financial ownership key to `ledger_book_id`.

| Target concern                  | Conceptual columns and constraints                                                                                                                                                                                                                                              |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ledger_books`                  | Stable ID; owner kind; exactly one supported owner reference; immutable currency and precision; lifecycle metadata; unique owner. M5.1 contains BUSINESS books only.                                                                                                            |
| Charts                          | Stable chart ID; required book ID; existing name and lifecycle fields; unique chart identity within a book.                                                                                                                                                                     |
| Accounts                        | Stable account ID; required book ID and constrained chart reference; existing code, name, type, active state, and hierarchy fields; uniqueness and parent integrity within the same book.                                                                                       |
| Accounting periods              | Stable period ID; required book ID; existing name, inclusive start/end dates, status, and lock evidence; non-overlap and state constraints remain deterministic.                                                                                                                |
| Transactions/proposals          | Stable transaction ID; required book ID; existing version, entry date, description, lifecycle state, reversal intent, source, and timestamps. Organization identity is available through the book owner and may remain as a guarded compatibility projection during transition. |
| Transaction lines               | Stable line ID; required book ID and same-book proposal/account references; existing order, debit, credit, memo, and exact integer amount constraints. Business project allocation moves to a business extension relation.                                                      |
| Validations                     | Stable validation ID; required book ID and same-book proposal reference; version, exact fingerprint, explicit fingerprint algorithm version, validation result, and timestamp.                                                                                                  |
| Confirmation provenance         | Stable provenance ID; required book ID; same-book proposal and validation; proposal version, displayed fingerprint, authenticated actor, confirmation timestamp, and request identifier.                                                                                        |
| Confirmations                   | Stable confirmation ID; required book ID; same-book proposal, validation, and provenance references; existing actor, timestamp, and state.                                                                                                                                      |
| Command idempotency             | Required book ID, authenticated actor, operation, caller-supplied key, immutable request fingerprint, stored response/resource, and timestamps; unique composite scope remains book + actor + operation + key.                                                                  |
| Journal entries                 | Stable entry ID; required book ID; same-book proposal; date, description, posted actor/time, immutable status, and direct reversal references.                                                                                                                                  |
| Journal lines                   | Stable line ID; required book ID and same-book entry/account references; existing line order, debit, credit, memo, and exact integer constraints. Business project allocation moves to a business extension relation.                                                           |
| Audit events                    | Existing table and rows remain unchanged, including `organization_id`, JSON, sequence, actor, timestamp, metadata, and hashes/fingerprints where present.                                                                                                                       |
| Audit book scope                | Immutable one-to-one relation from financial audit event sequence to book ID, populated during migration and atomically for new events.                                                                                                                                         |
| Business proposal documents     | Same-business-owner relation from proposal to business document, preserving every existing document association without making documents universal-core entities.                                                                                                               |
| Business proposal line projects | Same-business-owner relation from proposal line to project, preserving optional allocation.                                                                                                                                                                                     |
| Business journal line projects  | Same-business-owner relation from journal line to project, preserving posted project attribution and report results.                                                                                                                                                            |

Identity, credential, session, organization, membership, project, and document tables remain outside
the universal core. Projects and documents remain business-only. A future `PersonalSpace` owner is
not added in this migration.

### Ownership representation

For M5.1, the `ledger_books` record carries owner kind `BUSINESS` and a required organization
reference. The database can therefore enforce exactly one supported owner and one book for that
owner directly. Empty owner references, unsupported owner kinds, and cross-owner references are
rejected.

When M5.2 introduces `PersonalSpace`, the small owner table may be reconstructed to add a personal
owner reference and an exclusive-owner constraint. That reconstruction is intentionally deferred
until the personal owner exists. Permanent parallel owner-map tables are rejected because SQLite
cannot declaratively prove exactly one owner across separate maps.

### Required indexes

The implementation must measure query plans and add indexes for these access paths without changing
logical results:

- unique book owner and unique BUSINESS organization;
- book plus account code and book plus account hierarchy traversal;
- book plus period date range/status;
- book plus transaction state/date/version;
- book plus journal date/entry and book plus account/date/line;
- book plus validation/confirmation/provenance lookup;
- book plus actor/operation/idempotency key;
- audit sidecar by book and sequence;
- business project extension by project and by line; and
- document extension by document and proposal.

Index creation belongs in the same reviewed migration definition, but performance evidence is a
separate acceptance check from accounting reconciliation.

## Compatibility that must remain exact

### Identifiers and lifecycle

All user, organization, membership, project, document, chart, account, period, proposal, proposal
line, validation, provenance, confirmation, receipt, journal entry, journal line, and audit event
identifiers remain unchanged. All proposal states and versions remain unchanged. Reversal source and
target IDs remain unchanged, including the guarantee that one posted entry has at most one direct
reversal.

### Validation fingerprints

The existing fingerprint serializes the current organization-scoped transaction representation and
ordered financial lines. Canonical storage must add an explicit fingerprint algorithm version.
Migrated validation rows are labeled `organization-v1` and verified by reconstructing the legacy
payload exactly, even after the physical owner column changes. New book-native validations use a
separately named version. A confirmed but unposted legacy proposal must still post only if its stored
version and legacy fingerprint remain valid.

The migration must not recompute and overwrite historical fingerprints. It may compute comparison
values during preflight and reconciliation.

### Audit evidence

Existing audit rows are never rewritten or regenerated. Their sequence, actor, timestamp,
organization, entity, before/after JSON, and metadata remain exact. The audit-book relation is an
immutable sidecar populated from the pre-existing organization/entity relationship. New financial
mutations insert both the audit event and its book-scope row in the same database transaction.

The database audit authorizer and trigger allowlist must protect the sidecar as strictly as the audit
table. API, CLI, adapters, and repositories cannot directly create, edit, or delete either form of
audit evidence.

### Organization compatibility projection

During transition, existing business callers may continue to receive organization ID, currency, and
minor-unit precision. The book becomes the canonical financial scope, while a database guard ensures
that the BUSINESS book and its organization cannot diverge. The compatibility facade resolves the
organization to the book and renders existing response shapes without duplicating accounting logic.

## Preflight integrity and reconciliation manifest

Preflight runs read-only against a consistent copy before any migration and again inside the cutover
window. A representative populated database, not the repository's empty tracked database, is
required for release evidence.

The signed or otherwise integrity-protected manifest records database identity, file size, schema
version, SQLite version, migration tool version, generation timestamp, operator, and cryptographic
hashes of the source database and backup. Sensitive financial contents must not be written to normal
application logs; detailed manifests require restricted operational storage.

The manifest contains:

1. `integrity_check` result, foreign-key check, and the complete declared schema version.
2. Row counts and deterministic ordered content hashes for every table, including SQLite sequence
   state where relevant.
3. Organizations' currency and minor-unit precision, with a check that all copied book values match.
4. Every proposal and line count, state, version, debit/credit total, account reference, optional
   project/document reference, validation, provenance, confirmation, and idempotency receipt.
5. No persistent transaction left in a transient assembly state that the migration cannot interpret.
6. Every journal entry's equal debit and credit totals, line order, proposal link, actor, posting
   timestamp, financial date, project attribution, and reversal relationship.
7. Aggregate ledger balance of zero debits minus credits per entry and for the complete ledger.
8. Proposal-to-journal equivalence for posted proposals using the current engine's existing rules.
9. Stored fingerprint verification under the legacy algorithm for all applicable validations and
   confirmation provenance.
10. At most one direct reversal for an original entry, valid back-references, no missing original,
    and correct compensating line amounts without inferring an unrecorded business reason.
11. Period boundaries and entry-date membership. Historical data in a now-locked period is valid;
    lock state is not retroactively reinterpreted. Any existing violation is a stop condition.
12. Audit event count, maximum sequence, SQLite sequence state, immutable JSON payload hashes,
    actor/entity/organization references where required, and metadata. Sequence gaps are recorded
    and preserved rather than treated as corruption.
13. Receipt scope, request fingerprint, stored resource/result, and correspondence to the referenced
    confirmation, posting, or reversal outcome.
14. Current report snapshots per organization: account balances, trial balance, general ledger,
    income statement, balance sheet, cash-flow output, and project views for representative date
    boundaries. Cash-flow comparison preserves current engine output; it does not designate accounts
    or invent a new cash policy.

Any failed check blocks migration. Operators must classify the source discrepancy and obtain a
separate, audited repair decision. The migration itself cannot normalize, delete, or silently repair
financial history.

## Backup and recovery preparation

Before v3 or v4 migration:

1. Stop or block all API, CLI, background, and administrative writers.
2. Verify no process retains a write-capable connection.
3. Create a SQLite-consistent backup using the supported backup mechanism rather than copying a live
   file blindly.
4. Hash the source and backup, record paths and access controls, and restore the backup to a separate
   location.
5. Run schema, integrity, foreign-key, count, hash, invariant, and report checks on the restored copy.
6. Keep the source database and verified backup immutable for the agreed retention window.
7. Record the schema version and exact application release that can read the backup.

Backup success alone is insufficient; restore plus reconciliation is the acceptance condition.
Recovery artifacts contain financial and identity data and must receive the same confidentiality and
access protection as the source database.

## Migration sequence

### Step 1: v2 to v3 additive mapping

**Prerequisites:** Phase 1 preflight passes, backup restoration passes, the deterministic book-ID
algorithm is frozen, and no writer is active.

**Order:**

1. Begin one immediate migration transaction through the private database layer.
2. Add the BUSINESS-only book table and its ownership/currency constraints.
3. Insert exactly one book for every organization using the deterministic ID and exact currency and
   precision.
4. Verify organization count equals book count, every organization has one book, no book is orphaned,
   and all copied values match.
5. Run current accounting invariants, hashes, report snapshots, and full automated tests.
6. Advance schema version only after every check passes, then commit.

No existing financial row or audit event is updated. On any failure before commit, roll back the
transaction. After commit, v2 readers remain compatible because their tables and columns are
unchanged. A verified v2 backup is the recovery point until v3 has operated successfully for the
defined observation period.

### Step 2: service transition on v3

**Implementation status:** Complete in M5.1-C2.

The universal command/read service is introduced over the organization-backed storage adapter. The
business facade resolves `organization_id` to `ledger_book_id` and keeps all API, CLI, permission,
error, serialization, and report behavior stable. This step has no schema migration.

Release gates require old-engine versus new-service differential tests on identical copies,
including proposals, stale confirmation, posting retries, reversals, locked periods, project
attribution, audit, and all reports. During this phase the old implementation remains the rollback
release; there are no simultaneous implementations writing the same database.

### Step 3: v3 to v4 canonical reconstruction rehearsal

**Implementation status:** Complete in M5.1-C3 on disposable copies only.

The table reconstruction must first run repeatedly against disposable copies of representative
databases. It must include empty, small, high-volume, old-validation, pending-confirmation,
reversal-heavy, locked-period, inactive-account, project-rich, and receipt-retry fixtures.

Rehearsal produces the same before/after reconciliation manifest required in production, measures
copy and index time, records peak disk use, and exercises a failure injection after each major copy
stage. A release is not approved from the empty repository database alone.

The implemented `chatbook-canonical-rehearsal SOURCE TARGET BACKUP` tool requires three distinct
paths, passing v3 preflight evidence, and verified backup/restore evidence. It reconstructs under
`v4_` names, preserves legacy projections and audit rows, swaps within one transaction, installs
final guards, checks integrity/foreign keys, and sets version 4 at the final gate. It writes
sanitized `<TARGET>.c3-report.json` evidence. The explicit rehearsal engine and API factory prove
business parity; normal startup intentionally rejects the target.

### Step 4: v3 to v4 production cutover

Use a planned maintenance window. Zero downtime and dual writes are explicitly out of scope.

1. Stop all writers and reject new financial commands with a stable maintenance response.
2. Drain active requests, close application connections, and verify the database is quiescent.
3. Create and restore-test a fresh v3 backup, then run the complete preflight manifest.
4. Open the private migration connection, begin one exclusive/immediate migration transaction, and
   defer foreign-key checking only within that controlled transaction where reconstruction requires
   it.
5. Create new canonical tables under temporary names with final constraints but without normal audit
   triggers. Migration copy operations must not manufacture audit events.
6. Copy parent data in dependency order: books, charts, accounts and hierarchy, periods, proposals,
   validations/provenance/confirmations, entries, then children and receipts. Populate book IDs by
   the unique organization-to-book map while preserving every existing ID and value.
7. Copy proposal lines and journal lines with exact order and amounts. Copy business project and
   document relationships to the constrained extension tables.
8. Resolve circular reversal references using the database's deferred-reference mechanism or a
   staged nullable copy followed by validation before final constraints. Do not renumber or rebuild
   entries.
9. Leave audit events untouched. Populate the immutable audit-book sidecar by deterministic
   organization/entity scope and reject any event whose financial book cannot be resolved uniquely.
10. Label migrated validation fingerprints with the legacy algorithm version without changing the
    stored fingerprint. Verify all legacy payloads through the compatibility serializer.
11. Run row-count, ordered-hash, relationship, balance, proposal/journal, reversal, receipt, audit,
    and report reconciliation while the transaction is still uncommitted.
12. Swap the reconstructed tables into their canonical names in dependency-safe order. Remove old
    temporary tables only inside the still-uncommitted transaction after all data is proven present.
13. Add final indexes, book-aware immutability/audit triggers, authorizer expectations, and database
    context requirements against the canonical names. Verify query plans for critical reads.
14. Run full foreign-key checking, integrity checking, trigger inventory checking, schema inspection,
    and migration-version checks.
15. Advance schema version and commit only if every gate passes.
16. Keep writers stopped. Reopen read-only through the new release and run post-commit reconciliation,
    report parity, API/CLI smoke reads, and audit reads.
17. Resume writes only after the release owner signs the manifest. Execute one controlled canary
    proposal lifecycle using approved test data in the intended environment, then verify ledger,
    receipt, audit event, and audit-book sidecar atomically.

The implementation must use the migration connection's own transaction controls. It must not expose
the connection or allow a repository/service to bypass the migration orchestrator.

## Table-by-table reconciliation

| Data set                          | Required before/after proof                                                                                                                                                                   |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Users, organizations, memberships | IDs, fields, role values, counts, and hashes unchanged.                                                                                                                                       |
| Books                             | Exactly one BUSINESS book per organization; deterministic ID; currency and precision equal the organization; no extra owner.                                                                  |
| Projects and documents            | Rows unchanged; all extension references resolve to the same business owner and preserve optionality.                                                                                         |
| Charts and accounts               | IDs and attributes unchanged; chart/account/parent references remain within one book; active flags retained.                                                                                  |
| Periods                           | IDs, dates, states, and lock evidence unchanged; every posting remains mapped to the same period outcome.                                                                                     |
| Proposals and lines               | IDs, state, version, text, dates, source, line order, accounts, amounts, and extensions match. Every line has exactly one book through its proposal.                                          |
| Validations and confirmations     | IDs, actors, timestamps, request IDs, versions, and fingerprints unchanged; legacy verification succeeds.                                                                                     |
| Receipts                          | Same key scope after organization-to-book resolution, same request fingerprint, resource ID, serialized result, and timestamps; retry returns the same effect.                                |
| Journal entries and lines         | IDs, proposal links, entry dates, posting actors/times, line order, accounts, debits, credits, descriptions, and project extensions match. Every entry balances.                              |
| Reversals                         | Original/reversal IDs and direction match; one direct reversal limit holds; original remains visible; net balances match.                                                                     |
| Audit events                      | Count, sequence, SQLite sequence, actor, timestamp, entity, organization, before/after JSON, metadata, and content hash unchanged. Each financial event gets exactly one correct sidecar row. |
| Reports                           | Account balances, trial balance, ledger, income statement, balance sheet, cash-flow output, and project totals match for the same inputs and dates.                                           |

Reconciliation uses exact integer comparisons and deterministic ordered serialization. It does not
use floating point, rounded display strings, or payload equality as an idempotency substitute.

## Rollback and forward recovery

| Failure point                                               | Required response                                                                                                                                                                                                                                                   |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Preflight or restore test fails                             | Do not start migration. Preserve evidence and obtain a separate repair decision.                                                                                                                                                                                    |
| v3 or v4 transaction fails before commit                    | Roll back the database transaction, verify the original schema and manifests, and keep writers stopped until integrity is confirmed.                                                                                                                                |
| Process or host fails during uncommitted reconstruction     | Reopen only after SQLite recovery, run integrity and schema checks, and restore the verified pre-cutover backup if the source cannot be proven exact.                                                                                                               |
| Post-commit read-only acceptance fails before writes resume | Keep writers stopped and restore the verified pre-cutover backup together with its compatible application release. Verify the restoration before reopening.                                                                                                         |
| Any v4 financial write has committed                        | Do not restore the old backup as an ordinary rollback because that would destroy new history. Stop writers and perform an audited forward repair, or use a separately approved recovery procedure that preserves and replays every new committed event and receipt. |
| Audit sidecar or trigger fails on a canary write            | The financial mutation must roll back atomically. Keep writers stopped and repair forward before retrying.                                                                                                                                                          |
| Report parity fails but ledger invariants pass              | Keep writers stopped. Diagnose query/repository mapping; do not alter ledger data to make the report match.                                                                                                                                                         |

The rollback window therefore ends when v4 writes resume. This boundary must be visible in the
operator checklist and release approval.

## Write handling and concurrency

No write is accepted during v4 cutover. The API returns a stable maintenance response; the CLI and
administrative paths fail closed. There is no queue that silently replays financial commands, no
dual-write bridge, and no replication-based migration in this SQLite milestone.

After cutover, current SQLite single-writer serialization and `BEGIN IMMEDIATE` remain part of the
correctness model. The universal service must preserve atomic proposal/posting/reversal/audit/receipt
transactions. Multi-process and production-database locking, advisory locks, online migration, and
distributed idempotency are deferred to the production deployment milestone and require new
evidence.

## Migration and compatibility tests

The eventual implementation requires:

- v2-to-v3 and v3-to-v4 migration tests from realistic golden fixtures;
- empty database, already-current database, repeated initialization, and unsupported-version tests;
- deterministic book-ID and unique-owner tests;
- exact ID, row-count, ordered-hash, timestamp, JSON, and sequence preservation tests;
- legacy validation fingerprint verification, including confirmed but unposted proposals;
- proposal/posting/reversal/idempotency/audit atomic failure injection at every migration stage;
- business API, CLI, error-code, permission, response-shape, pagination, and report parity tests;
- unbalanced entry, invalid account/project, locked period, stale confirmation, duplicate posting,
  conflicting receipt, reversal, and double-reversal regression tests;
- concurrent or conflicting command tests within SQLite's supported topology;
- extension-table cross-owner rejection tests;
- audit-event and sidecar immutability/direct-write rejection tests;
- backup restoration and both permitted rollback paths; and
- representative-volume timing, disk-space, index, and query-plan tests.

All existing Python and frontend tests must remain green. The migration suite must compare current
and target implementations against the same immutable fixtures rather than merely checking that v4
queries return internally consistent results.

## Operational and performance limits

Before approval, rehearsal must establish maintenance-window duration, backup and restore time, peak
temporary disk space, table-copy throughput, index-build time, and post-migration critical-query
plans. The operator must reserve enough disk for the source, verified backup, restored proof copy,
and temporary reconstructed tables with a safety margin.

Structured logs may record migration phase, duration, schema version, counts, manifest identifiers,
and pass/fail status. They must not contain passwords, session tokens, proposal descriptions,
financial line contents, full audit JSON, or unredacted personal/business financial data.

Monitoring after cutover covers migration/version mismatch, command failures, lock contention,
idempotency conflicts, audit/sidecar insertion failures, report latency, and invariant alarms. It
does not auto-correct ledger data.

## Personal, AI, and jurisdiction boundaries

The migration creates a universal ownership seam but enables no personal behavior. A future personal
release still needs a `PersonalSpace` domain, authenticated owner resolution, privacy/consent policy,
personal adapter, approved default mappings, opening-balance and period decisions, transfer policy,
and separate API/UI acceptance.

AI receives no database or ledger mutation capability from this work. Future AI can use authorized
read tools and proposal commands through the same service; confirmation, posting, reversal, period
locking, and audit authority remain deterministic and authenticated.

Tax, statutory reporting, filing, jurisdiction-specific classification, exchange rates, and
compliance policy remain versioned layers outside the universal core. The migration must not encode
them in owner mapping, canonical accounts, or report arithmetic.

## Release acceptance criteria

M5.1 canonical migration is acceptable only when:

- preflight and restored-backup manifests pass on representative data;
- every organization maps to exactly one BUSINESS book with exact currency and precision;
- every existing ID, lifecycle state, line, receipt, reversal, timestamp, audit row, and relationship
  is preserved;
- all entries balance and all database constraints and foreign keys pass;
- legacy fingerprints, stale-version protection, and idempotent retry behavior remain valid;
- old and new business services produce identical observable commands, errors, and reports;
- audit rows remain unchanged and each financial event has one immutable book-scope relation;
- failure injection proves transaction rollback and no partial canonical state;
- post-commit read-only acceptance passes before writes resume;
- backup recovery is demonstrated and the end of the rollback window is explicitly approved;
- performance fits the measured maintenance window and resource budget; and
- no PersonalSpace, personal posting, AI, tax, or compliance behavior is enabled.

## Approval gates and unresolved risks

Engineering approval is required for deterministic ID format, canonical table reconstruction,
fingerprint-version format, audit-sidecar trigger design, service/repository cutover, migration
orchestrator, maintenance response, operational manifests, and rollback tooling.

Product approval is required before any personal owner, sharing, advisor access, privacy lifecycle,
combined view, or cross-space confirmation experience. Qualified accounting/domain approval is
required before personal periods, opening balances, default mappings, liability splits,
personal/business movements, cash-position policy, valuation, multi-currency, tax, or statutory
behavior.

The largest residual risks are an incomplete legacy fingerprint reconstruction, audit-trigger or
authorizer drift during table reconstruction, accidental loss of project/document attribution,
receipt-scope changes, report query drift, insufficient representative migration fixtures, SQLite
maintenance duration, and attempted backup rollback after new writes. Each is a fail-closed release
gate, not an accepted silent difference.

## Implemented milestone and next stop

**M5.1-C1: Preflight Evidence and Additive Business LedgerBook Mapping**, **M5.1-C2: Universal
Service Extraction over Organization Storage**, and **M5.1-C3: Canonical Book-Scoped Persistence
Rehearsal** are complete. **M5.1-C4A: Business Cutover Readiness and Deployment Rehearsal** is also
complete on synthetic disposable copies. The next possible milestone is **M5.1-C4: Controlled
BUSINESS Cutover**, which requires separate authorization and release-owner approval. C4A evidence
does not authorize writer shutdown, migration of the shared database, a deployment canary, or writer
resumption.

## DO NOT IMPLEMENT YET

Do not start the C4 cutover or any later phase without separate authorization.

Do not add PersonalSpace, personal accounts/activity/transfers/reports, budgets, reminders,
recurrence, goals, documents/extraction, AI, tax/compliance, bank integrations, production database,
or cloud infrastructure as part of this migration.
