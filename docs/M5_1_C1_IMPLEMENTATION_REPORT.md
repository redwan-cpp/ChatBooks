# M5.1-C1 implementation report

**Date:** 2026-09-27  
**Project and product:** Chatbooks
**Milestone:** Preflight Evidence and Additive Business LedgerBook Mapping  
**Status:** Implemented; stopped before M5.1-C2

## 1. What was implemented

M5.1-C1 implements only Phase 1 and Phase 2 of the approved M5.1-B plan:

1. read-only SQLite preflight and deterministic migration manifests;
2. SQLite-consistent backup and separate restore verification;
3. atomic schema-v2-to-v3 migration;
4. exactly one immutable BUSINESS LedgerBook mapping per organization;
5. atomic book creation for new organizations; and
6. a membership-first internal BUSINESS organization-to-book resolver.

The current `AccountingEngine`, FastAPI routes, CLI financial commands, frontend, reports, audit
presentation, idempotency behavior, and organization-scoped financial schema remain the business
compatibility baseline.

No new ADR was required. ADR 0018 defines the persistent book seam, ADR 0019 defines authorization
before resolution, and the M5.1-B implementation/migration plans already fix the staged v3 design.

## 2. Phase 1 preflight tooling

`chatbook/migration_evidence.py` inspects a consistent SQLite database copy through a read-only,
query-only connection. It returns a deterministic manifest when the generation time and database
identity inputs are fixed. The manifest contains:

- database identity, schema version, SQLite version, tool version, generation timestamp, and source,
  snapshot, backup, and restored-file hashes;
- `integrity_check`, foreign-key result, table counts, deterministic ordered table hashes, legacy
  content fingerprint, schema fingerprint, and SQLite sequence state;
- organization count plus currency/precision references;
- proposal and line counts/states, consecutive line order, balance, periods, account/project/document
  ownership, and stored legacy validation-fingerprint verification;
- validation, confirmation, and confirmation-provenance consistency;
- idempotency operation/resource consistency;
- journal balance, line order, proposal equality, period/date consistency, account/project ownership,
  and complete reversal-chain validation;
- audit count, maximum/allocator sequence, entity/organization relation, event contract, JSON shape,
  metadata, and payload-table hash;
- per-organization general-ledger, trial-balance, period-statement/asset-movement, and project-report
  fingerprints; and
- stable, non-sensitive diagnostic codes for every failed gate.

The inspector hashes row contents but does not place proposal descriptions, client names, financial
lines, credentials, session tokens, or audit JSON in the manifest or normal logs. It never repairs,
deletes, normalizes, or writes source data. The existing proposal fingerprint serializer moved to a
small shared deterministic helper so preflight verifies stored fingerprints with exactly the same
`organization-v1` algorithm used by the engine.

## 3. Fixture strategy

The migration suite builds sanitized temporary SQLite fixtures covering:

- empty database and empty organization;
- one and multiple organizations;
- multiple users and role memberships;
- active and inactive accounts;
- open and locked periods;
- pending, validated, and confirmed-but-unposted proposals;
- posted transactions with multiple lines;
- a posted reversal and reversal-of-reversal chain;
- project and document references;
- confirmation and posting idempotency receipts;
- complete audit history; and
- the maximum supported integer money value on a balanced pending proposal.

The same populated baseline is copied into isolated corruption cases for foreign-key failure,
unbalanced journal, invalid reversal target, proposal/journal mismatch, invalid audit entity,
report-fingerprint mismatch, invalid receipt resource, period/date mismatch, invalid project
reference, and stored validation-fingerprint mismatch. Every case fails closed and exposes the
expected diagnostic code.

## 4. Backup and restore verification

`create_verified_backup` acquires or requires an active `BEGIN IMMEDIATE` transaction before
capturing evidence. This blocks another SQLite writer while a separate read-only source connection
uses SQLite's backup API. It does not copy a live database file blindly.

The workflow:

1. creates a SQLite-consistent temporary snapshot;
2. runs preflight on that copy;
3. installs or reuses a matching protected backup without overwriting conflicting evidence;
4. restores the backup through SQLite's backup API to another temporary database;
5. runs the same preflight against the restore and compares legacy content and report fingerprints;
6. writes a JSON evidence manifest beside the backup; and
7. removes the temporary snapshot and restore copy.

The standalone command is:

```text
chatbook-migration-evidence SOURCE BACKUP
```

The source remains at its original schema version. Backup and manifest files contain sensitive
financial evidence and require the same access protection as the source database.

## 5. Schema v3 design actually implemented

Schema version 3 adds only `ledger_books`:

| Field               | Implemented rule                                                        |
| ------------------- | ----------------------------------------------------------------------- |
| `id`                | Text primary key and exact `book:business:<organization_id>` constraint |
| `owner_kind`        | Required and fixed to `BUSINESS`                                        |
| `organization_id`   | Required, unique foreign key to `organizations`                         |
| `currency`          | Required three-letter code copied exactly from the organization         |
| `minor_unit_digits` | Required integer from 0 through 6 copied exactly from the organization  |
| `created_at`        | Required creation/migration timestamp                                   |
| `creation_source`   | `schema_v3_migration` or `organization_creation`                        |
| `creation_version`  | Fixed to `m5.1-c1-v1`                                                   |

Database triggers reject currency/precision mismatch, replacement, update, and deletion. An
organization-insert trigger creates its BUSINESS book in the same transaction. Startup rejects a
missing mapping, orphan, owner-kind/ID mismatch, currency mismatch, or precision mismatch.

The table has no personal owner column. No financial table received `ledger_book_id`; charts,
accounts, periods, proposals, confirmations, receipts, journal entries/lines, audit, projects, and
documents continue to use `organization_id` exactly as before.

## 6. Migration behavior

Opening a file-backed schema-v2 database performs these gates:

1. acquire `BEGIN IMMEDIATE` before evidence capture;
2. create or verify `<database>.pre-v3.backup` and its manifest;
3. prove a separate restore and run all preflight checks against the consistent copy;
4. create and backfill `ledger_books` with deterministic IDs and exact organization currency and
   precision;
5. install immutable mapping and organization-creation triggers;
6. verify one-to-one ownership and absence of orphans;
7. recompute hashes for every v2 table and compare them with the verified preflight manifest;
8. set `PRAGMA user_version = 3` only after every gate passes; and
9. commit the mapping and version atomically.

Any exception rolls back all schema changes and leaves version 2. The verified recovery backup may
remain for diagnosis/retry. If an existing backup does not match the locked source, migration stops
with `backup_conflict`. Unknown schema versions and nonempty unversioned databases continue to fail
closed.

Version 1 still migrates explicitly to version 2 and then passes through the same verified v2→v3
gate. Fresh databases initialize directly at version 3.

No existing financial row, lifecycle state, amount, ID, timestamp, receipt, or audit row is updated.
The book backfill has no financial audit trigger and creates no audit event.

## 7. Resolver behavior

The internal BUSINESS resolver accepts only:

- actor ID from the trusted caller boundary; and
- organization ID from the existing business route/command context.

It first checks organization membership. Only after authorization succeeds does it select the
BUSINESS book by `organization_id`. It has no method that accepts a raw book ID as authority. Passing
a book ID in place of an organization ID fails the membership check. No API field, route, response,
or OpenAPI schema exposes `ledger_book_id` as an authorization mechanism.

Organization creation exercises the resolver before its transaction commits, proving that the new
organization, book, owner membership, and existing chart setup were created together with matching
currency and precision.

## 8. Tests added

Fourteen focused M5.1-C1 tests cover:

- empty and populated v2→v3 migration;
- multiple organizations and exact deterministic IDs;
- repeated initialization and one book per organization;
- verified backup/restore and deterministic manifest generation;
- unknown schema version;
- injected partial-migration rollback;
- preflight failure blocking migration;
- currency mismatch, missing mapping, and orphan rejection;
- atomic new-organization book creation without an audit event;
- duplicate, mismatch, update, and delete constraint attacks;
- membership-first resolution, cross-organization denial, and raw-ID rejection;
- unchanged organization ownership columns and absence of PersonalSpace;
- unchanged ledger, reports, audit rows, receipts, and idempotent retry; and
- every requested corruption diagnostic class.

The earlier version-1 migration test now continues through the verified version-3 mapping and proves
its posted ledger remains unchanged.

## 9. Verification results

| Check                                              | Result                                                                                                       |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Complete Python suite                              | Passed: 70 tests                                                                                             |
| M5.1-C1 focused suite                              | Passed: 14 tests                                                                                             |
| Existing API, CLI, hardening, and accounting tests | Passed                                                                                                       |
| mypy                                               | Passed: 15 application source files                                                                          |
| Ruff lint                                          | Passed                                                                                                       |
| Ruff formatting                                    | Passed                                                                                                       |
| Frontend Vitest                                    | Passed: 10 tests                                                                                             |
| Frontend TypeScript                                | Passed                                                                                                       |
| Frontend ESLint                                    | Passed                                                                                                       |
| Frontend Prettier                                  | Passed                                                                                                       |
| Next.js production build                           | Passed                                                                                                       |
| Documentation links                                | Passed: 161 local links across 47 Markdown documents                                                         |
| Source/API boundary scan                           | No personal domain, public book authority, service extraction, v4 table, or financial ownership change found |

## 10. Compatibility evidence

Migration tests compare deterministic ordered hashes for all twenty pre-existing v2 tables before
and after migration. This includes identity, memberships, projects, documents, accounts, periods,
proposals/lines, validations, confirmations/provenance, idempotency receipts, journal entries/lines,
and audit events.

The representative fixture additionally compares the existing engine's ledger, trial balance,
income statement, balance sheet, selected-asset cash movement report, raw audit row tuples, raw
receipt tuples, and a successful posting retry before and after migration. Existing API and CLI
integration suites pass unchanged. The frontend consumes the same API contract and was not modified.

## 11. Discrepancies and remaining risks

No financial or business-behavior discrepancy was found.

Remaining operational risks are bounded and documented:

- automatic v2 migration needs write access and enough local disk for the source, backup, evidence
  manifest, and temporary restore;
- backup/manifest permission, retention, encryption, and off-host disaster recovery remain operator
  responsibilities outside this local milestone;
- the sanitized fixture is broad but not production-volume performance evidence;
- report fingerprints are migration evidence, not a new financial source of truth;
- schema v3 intentionally contains an immutable currency/precision projection in both organization
  and book records; both sides reject mutation, and equality is checked at insert and startup; and
- SQLite's single-writer behavior remains part of the current safety model and is not a production
  multi-host concurrency design.

## 12. Explicitly not implemented

M5.1-C1 did not implement:

- universal service extraction or a new accounting engine;
- schema v4 or book-scoped financial tables;
- changes to financial ownership columns, report arithmetic, API behavior, CLI financial behavior,
  or frontend behavior;
- audit-book sidecars or rewritten audit payloads;
- PersonalSpace, personal accounts, personal finance, personal API/UI, or cross-space activity;
- budgets, reminders, recurring activity, goals, document upload/extraction, AI, LLM tools, bank
  integrations, tax, payroll, statutory compliance, production database, or cloud infrastructure.

## 13. Readiness for M5.1-C2

M5.1-C1 meets its evidence and compatibility gates. The repository is ready for a separately
authorized **M5.1-C2: Universal Service Extraction over Organization Storage** milestone.

M5.1-C2 must extract one deterministic operation at a time behind the existing `AccountingEngine`,
retain schema v3 and organization-scoped storage, and prove exact business parity. It must not begin
canonical v4 reconstruction or personal enablement. Work stops here until that milestone is
explicitly authorized.
