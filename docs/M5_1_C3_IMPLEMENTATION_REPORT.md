# M5.1-C3 Canonical Book-Scoped Persistence Rehearsal

**Date:** 2026-09-27  
**Project and product:** Chatbooks
**Status:** Complete on disposable database copies; C4 cutover not started

## 1. Schema v4 implemented

Schema v4 is implemented as a separately opened rehearsal target. It is produced only by
`chatbook-canonical-rehearsal`/`rehearse_canonical_migration` from a closed schema-v3 source, a
restore-verified backup, and a new distinct target path. Normal `Database`, FastAPI startup, and the
`chatbook` CLI remain on schema v3 and reject v4. No shared or running database was migrated.

## 2. Target schema

`ledger_book_id` is the canonical key in `charts_of_accounts`, `accounts`,
`accounting_periods`, `transactions`, `transaction_lines`, `validations`, `confirmations`,
`confirmation_provenance`, `command_idempotency`, `journal_entries`, and `journal_lines`. Existing
table names and every business identifier remain stable.

Projects and documents remain organization-owned. The v4 business extensions are:

- `business_proposal_documents`;
- `business_proposal_line_projects`; and
- `business_journal_line_projects`.

`audit_event_book_scopes` maps applicable financial audit sequences to books. `ledger_books` remains
BUSINESS-only and requires exactly one deterministic book per organization with matching currency
and minor-unit precision. No balance cache, PERSONAL owner, currency conversion, or account
hierarchy was added.

## 3. Migration orchestration

The orchestrator runs v3 preflight, creates a SQLite-consistent backup while writers are blocked,
restores and verifies it, restores that backup to a new target, and reconstructs v4 tables under
`v4_` names. It copies data in dependency order, handles reversal references with deferred foreign
keys, reconciles exact legacy projections before swap, swaps inside the same transaction, installs
final protections, runs `foreign_key_check` and `integrity_check`, and sets `user_version = 4` only
at the last gate.

Source, backup, and target paths must differ and the target must not exist. Unknown versions fail
closed. The tool writes sanitized evidence to `<target>.c3-report.json`; it does not log financial
descriptions, line contents, audit JSON, passwords, or tokens.

## 4. Repository implementation

`SQLiteBookStorage` binds a server-issued `AuthorizedFinancialContext` to the persisted BUSINESS
book after rechecking organization, book, currency, and precision. `SQLiteBookRepository` implements
the existing named `FinancialRepository` operations with book-first queries. It exposes no public
connection, cursor, arbitrary query, or generic execute method. `UniversalFinancialService` remains
the only financial lifecycle and calculation implementation.

`AccountingEngine.for_canonical_rehearsal` and `create_app(..., canonical_rehearsal=True)` are
explicit test/rehearsal entry points. Existing constructors keep their v3 behavior. The business
facade, API routes, payloads, response shapes, errors, and CLI dispatcher remain compatible.

## 5. Constraint/trigger design

Composite foreign keys carry `ledger_book_id` through chart/account, proposal/line, validation,
confirmation/provenance, period/journal, account/line, receipt, and reversal relationships. Critical
unique constraints are book scoped. Business extensions additionally carry `organization_id` and
reference the exact `(book, organization)` owner before accepting a project or document.

Write-context triggers require each financial row's book to equal the internally bound book.
Lifecycle triggers preserve assembling→proposed and assembling→posted transitions, exact proposal
and journal equality, balanced lines, active accounts, open covering periods, confirming actor,
reversal date/line equality, one direct posted reversal, immutable receipts/provenance, period
lock-only changes, account-status-only changes, and immutable financial history.

Each proposal/document or line/project extension row is inserted first with a deferred core foreign
key. The following core insert requires that extension to exist. This lets the core audit trigger
capture the complete legacy-shaped row while a missing extension aborts the operation.

## 6. Audit sidecar behavior

Migration does not update or regenerate `audit_events`. Existing sequences, SQLite sequence state,
actors, timestamps, organization IDs, entity data, before/after JSON, and metadata remain exact.
Each existing applicable financial event receives one sidecar row for the book mapped from its
organization.

New v4 financial audit triggers serialize the established organization-shaped JSON, insert the
event, and insert its sidecar using the same transaction. The connection authorizer permits those
inserts only from the installed audit triggers. Both audit tables reject direct replacement,
update, and deletion. Non-financial organization/project/document events retain their existing
organization-scoped presentation.

## 7. Fingerprint compatibility

Migrated validation fingerprints retain their exact stored bytes and receive explicit version
`organization-v1`. The service dispatches verification by version and reconstructs the original
organization-shaped transaction payload plus ordered lines. Unknown versions fail closed. Tests
cover pending, validated, confirmed-but-unposted, posted, reversed, and reversal-chain proposals,
including confirmation and posting after migration.

## 8. Business extension migration

Every proposal, proposal line, and journal line receives one extension row, including a row with a
null optional association. Existing document/project IDs and optionality are preserved. Composite
foreign keys reject a project or document from a different organization/book. Reports continue to
derive project totals from tagged posted journal lines; extensions do not store mutable actuals.

## 9. Fixture strategy

The primary migration fixture contains two organizations with different currencies/precision,
multiple memberships, active and inactive accounts, open and locked periods, projects, document
metadata, pending/validated/confirmed/posted proposals, maximum supported integer amounts,
idempotency receipts, a reversal chain, complete audit history, and legacy fingerprints. Empty and
unsupported-version databases are also exercised.

A separate synthetic volume fixture contains 100 posted transactions, 200 journal lines, five
project dimensions, 100 validations/confirmations, and their complete audit trail. It is useful for
repeatable local evidence and is not claimed to represent production scale.

## 10. Reconciliation methodology

Before table swap, every v4 financial table is projected back to the exact v3 column order. Counts
and SHA-256 hashes over stable primary-key ordering must equal the source projection. This covers
IDs, proposal state/version, fingerprints, confirmations, provenance, receipts, entries, lines,
reversals, documents, and projects. Existing audit-table evidence and sequence state are captured
without rewriting rows.

After commit, the same projection is checked again. The v3 and v4 engines are then compared for
general ledger, account balances, trial balance, income statement, balance sheet, cash movement,
project-filtered views, and audit presentation using exact integers and structured values.

## 11. Failure-injection results

Injected failures pass after all eleven gates: books, charts/accounts, periods, proposals,
validations/confirmations, journals, extensions, audit sidecar, before swap, trigger/index
installation, and before schema-version commit. Every target remains a valid schema-v3 restored
snapshot with no `v4_` residue, and every source hash remains unchanged. Each failure leaves a
sanitized diagnostic report.

## 12. Security attack results

Tests reject cross-book account, period, validation/confirmation, journal-line, receipt, reversal,
project, and document references. They also reject wrong write context, forged book substitution,
missing business extensions, forged audit/sidecar inserts, audit/sidecar update or delete, and direct
posted-history modification. Public API organization isolation remains enforced on the v4 adapter,
and no API exposes the private database connection or book ID as authority.

## 13. Concurrency results

SQLite `BEGIN IMMEDIATE` still serializes writers. Two simultaneous retries with the same caller
idempotency key return one journal entry. Competing reversals produce one posted winner. Posting
against a competing period lock resolves in one serial order with no assembling residue. Writes to
two independent books both complete under SQLite's database-wide writer serialization. No
distributed or multi-primary concurrency claim is made.

## 14. Performance measurements

On the local synthetic 100-posted-transaction/200-line fixture, one measured run produced:

| Measure                                       |               Result |
| --------------------------------------------- | -------------------: |
| Backup plus restore verification              |              0.290 s |
| Restore to rehearsal target                   |              0.014 s |
| Canonical migration transaction               |              0.112 s |
| Index and trigger installation                |             0.0066 s |
| Trial-balance read                            |             0.0019 s |
| Source / backup size                          | 1,527,808 bytes each |
| Final target / measured peak target footprint | 2,306,048 bytes each |

Critical query-plan evidence uses book-leading indexes for ledger date, account lines, and receipt
lookups. These local synthetic measurements establish instrumentation and a baseline only; C4 must
measure the intended deployment copy and reserve source, backup, restore, reconstruction, and safety
margin space.

## 15. Backup/restore evidence

The migration requires the existing verified-backup workflow. It holds a writer-blocking lock,
uses SQLite's backup API, hashes the snapshot, restores it separately, reruns preflight and report
fingerprints, and records a protected manifest. The rehearsal target is restored from that verified
backup. Tests prove the source file hash is unchanged on success and at every injected failure.

## 16. Business parity evidence

The current authenticated API workflow runs on a migrated copy: login, organization access,
cross-organization rejection, proposal creation, validation, stale-version rejection, exact
confirmation, idempotent posting/retry, ledger/report reads, audit reads, and creation of a new
BUSINESS organization/account. The existing CLI dispatcher reads the same catalog through the
canonical rehearsal engine. Public OpenAPI contracts do not expose books or v4 internals.

## 17. Tests added

Nine C3 tests add migration/reconciliation, new-write/audit, all-stage rollback, cross-book and
tampering attacks, API/CLI parity, concurrent retry/reversal/independent-book writes,
post-versus-period-lock, version/query-plan/repository-boundary checks, and representative-volume
evidence. Existing 77 Python tests and 10 frontend tests remain part of the gate.

## 18. Full verification results

The completion gate passes 86 Python tests, strict mypy, Ruff lint, Ruff formatting, 10 frontend
Vitest tests, frontend TypeScript checking, ESLint, Prettier checking, production frontend build,
documentation-link checks, and source/API boundary checks. The normal schema-v3 suite remains green
alongside the v4 rehearsal suite.

## 19. Remaining risks

- C3 has not exercised the actual deployment database size, filesystem, maintenance window, or
  operational restore procedure.
- SQLite has one database-wide writer and does not prove distributed locking or production database
  behavior.
- A machine/database-file administrator remains inside the trust boundary; audit evidence is not a
  cryptographic external log.
- Backup, target, and evidence files contain or describe sensitive financial data and need approved
  access, encryption, retention, and destruction controls.
- Only the legacy `organization-v1` fingerprint exists. Adding another algorithm requires explicit
  version design and compatibility fixtures.
- Normal startup deliberately rejects v4; deployment selection, maintenance responses, and recovery
  after the first committed v4 write remain C4 work.

## 20. Explicitly deferred C4/personal work

C4 writer shutdown, production backup, shared-database migration, release-owner approval,
post-commit read-only acceptance, canary, writer resumption, rollback-window closure, and forward
recovery are not implemented. PersonalSpace, PERSONAL books, personal accounts/activity/transfers,
budgets, reminders, recurrence, documents/extraction, AI, tax/compliance, bank integrations,
billing, production database changes, and cloud infrastructure remain deferred.

No accounting policy was invented. Period reopening, personal periods/opening balances, default
personal mappings, personal/business movement treatment, partial corrections, multi-currency/FX,
tax, payroll, statutory reporting, and compliance still require human/accountant decisions before
related implementation.

## 21. Readiness for C4

The repository is ready to plan and separately authorize C4 because the disposable-copy v4 schema,
repository, exact reconstruction, audit/fingerprint compatibility, business parity, rollback,
attack, concurrency, and measurement gates pass. It is not cut over, production-ready, or authorized
to resume ordinary writers on v4. C4 must use the measured deployment database and complete every
operator and recovery approval before the first v4 financial write.
