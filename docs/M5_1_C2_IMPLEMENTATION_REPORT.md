# M5.1-C2 implementation report

**Date:** 2026-09-27  
**Project and product:** Chatbooks
**Milestone:** Universal Service Extraction over Organization Storage  
**Status:** Implemented; canonical storage and personal behavior remain deferred

## 1. Extraction sequence

The extraction followed the authorized schema-v3 migration boundary:

1. Added immutable Financial Space, authority-source, capability, and authorized-context values.
2. Added typed account, period, proposal, confirmation, posting, reversal, and report commands.
3. Defined explicit financial repository and storage protocols without a generic SQL escape hatch.
4. Implemented the temporary SQLite organization adapter over the existing schema-v3 tables.
5. Moved financial operations into one `UniversalFinancialService` implementation.
6. Converted `AccountingEngine` into the BUSINESS compatibility facade while retaining its public
   signatures and business-only project/document responsibilities.
7. Added context, substitution, differential, fingerprint, schema, public-boundary, and source-
   boundary tests.

The extraction did not change the schema, rewrite a financial row, regenerate audit history, or run
two active financial write implementations.

## 2. New module and service boundaries

| Module                                    | Implemented responsibility                                                            |
| ----------------------------------------- | ------------------------------------------------------------------------------------- |
| `chatbook/financial/context.py`           | Immutable `AuthorizedFinancialContext`, Financial Space, capabilities, and provenance |
| `chatbook/financial/commands.py`          | Typed financial command/query values                                                  |
| `chatbook/financial/repository.py`        | Context-bound repository/storage protocols and typed persistence records              |
| `chatbook/financial/business.py`          | Membership-first BUSINESS context resolution                                          |
| `chatbook/financial/service.py`           | Single deterministic financial lifecycle and reporting implementation                 |
| `chatbook/storage/sqlite_organization.py` | Temporary schema-v3 organization persistence adapter                                  |
| `chatbook/engine.py`                      | Stable BUSINESS facade plus organization/project/document behavior                    |

The FastAPI routes and CLI continue to call `AccountingEngine`. They received no duplicate financial
logic, SQL, or arithmetic.

## 3. Repository and storage boundary

`FinancialStorage.bind(context)` returns a repository bound to one authorized BUSINESS scope. The
repository exposes named operations for existing financial records and an atomic write context. It
does not expose `execute`, arbitrary query text, a generic cursor, or the SQLite connection.

The temporary adapter still queries schema-v3 tables by `organization_id`. On every bind it verifies
that the context's book exists and matches the organization, owner kind, currency, and minor-unit
precision. Current composite organization foreign keys, posting triggers, audit triggers, and
`BEGIN IMMEDIATE` transaction behavior remain authoritative. Canonical `ledger_book_id` columns and
book-scoped database constraints are deferred to C3.

## 4. AuthorizedFinancialContext

The immutable context contains:

- authenticated or trusted actor ID;
- `FinancialSpaceRef(kind=BUSINESS, owner_id=organization_id)`;
- resolved LedgerBook ID;
- currency and minor-unit precision;
- explicit financial capabilities;
- request provenance and authority source; and
- optional BUSINESS project scope.

Every service entry point requires the context and checks its operation capability before binding
storage. Project-filtered operations also require the matching project scope. Public API payloads do
not accept book IDs or authorized contexts as authority.

## 5. Business facade

`AccountingEngine` retains its public constructor, methods, arguments, results, and stable errors.
For financial operations it resolves a BUSINESS context and delegates to the universal service.
Organization membership remains the trusted local engine boundary; FastAPI role permissions remain
in the existing API permission layer. The facade continues to own organization, membership, project,
and document behavior and validates business extension identifiers before service calls.

The facade retains private database composition for existing identity, migration, authentication,
project, and document behavior. The universal service never receives or exposes that connection.

## 6. Operations extracted

The service now owns the active implementation of:

- account creation, activation state, reads, and catalog reads;
- period creation, locking, reads, and coverage enforcement;
- proposal creation, immutable lines, deterministic validation, and legacy fingerprints;
- exact-version confirmation and caller-key idempotency;
- atomic posting, posting retry, period/account/project checks, and journal sealing;
- compensating reversal proposal creation and double-reversal protection;
- transaction, confirmation, journal, ledger, and audit reads;
- account balance, trial balance, income statement, balance sheet, cash movement, and project-filtered
  financial views.

Project and document CRUD, identity, organizations, membership, authentication, and role assignment
remain outside the universal service.

## 7. Compatibility evidence

The existing backend suite, API/CLI tests, hardening tests, migration tests, and frontend checks remain
the compatibility baseline. C2 tests additionally verify:

- the exact legacy `organization-v1` validation fingerprint;
- facade and direct-service equality for transaction, confirmation, journal, ledger, balances,
  project views, statements, cash movement, and audit results;
- unchanged schema version 3 and organization-scoped financial tables;
- no book/context/PERSONAL field in public OpenAPI; and
- the unchanged API/CLI/frontend call path through `AccountingEngine`.

No API route, CLI command, public request/response field, role permission, error code, identifier
format, audit payload, receipt scope, or report convention was intentionally changed.

## 8. Differential results

A differential test creates identical schema-v3 database copies, runs the legacy facade path on one
and the direct authorized-service path on the other, and compares observable results plus ordered
rows. It covers proposal creation, validation, confirmation, posting, a repeated post using the same
idempotency key, reversal proposal, reversal validation/confirmation/posting, and final reports.

Exact comparisons cover transactions and lines, validations, confirmations and provenance, command
receipts, journal entries and lines, and audit events. IDs, timestamps, serialized audit state,
metadata, sequence, fingerprints, and balances match. The retry creates no duplicate financial
effect, and the posted reversal returns balances to the expected state while preserving both entries.

## 9. Security results

Tests reject missing context, missing capability, forged book/organization/currency/precision
context, use of a book ID as an organization ID, and cross-organization account, project, and
proposal substitution. Membership is checked before book resolution. The adapter independently
revalidates the mapping, so possession of a valid internal book ID is not authority.

Public OpenAPI exposes neither the private SQLite connection nor a raw storage, book, context, audit-
mutation, or PERSONAL interface. Existing API authentication, role authorization, and organization
isolation tests continue to pass.

## 10. Source-boundary results

The C2 source-boundary test scans the API, CLI, BUSINESS facade, and universal service boundaries.
It fails if API/CLI code introduces financial SQL or report arithmetic, if the facade writes journal
tables or calculates authoritative reports, or if the service uses SQL/connection primitives. The
only financial SQL implementation is the temporary organization storage adapter.

## 11. Performance observations

The service adds one indexed LedgerBook mapping verification when a context is bound. The BUSINESS
resolver already performs membership and book resolution. A 1,000-iteration in-memory
`list_accounts` measurement observed four indexed reads per call and a 0.022 ms mean call time in
this development environment. This is a narrow regression check, not a production benchmark. Writes
still use one SQLite
`BEGIN IMMEDIATE` transaction for the complete financial effect, receipt, and audit behavior; no
dual write, additional report scan, or network boundary was introduced. The test suite showed no
obvious runtime regression at current fixture sizes.

Representative-volume query-plan, latency, lock-contention, and disk measurements remain release
gates for canonical persistence and production deployment. Current tests are correctness evidence,
not a production performance benchmark.

## 12. Remaining risks

- Schema-v3 financial constraints are still organization-scoped while application context also
  carries a LedgerBook. The adapter validation closes the application boundary; canonical book-
  scoped database enforcement remains unfinished.
- `AccountingEngine` still composes the private `Database` for nonfinancial business behavior and
  compatibility tests. Future work must avoid turning that composition into an adapter bypass.
- SQLite single-writer behavior is retained. Multi-process/distributed locking and idempotency are
  production-database concerns.
- C3 must preserve legacy fingerprints, audit sequence/state JSON, idempotency receipts, business
  extensions, reversal chains, and report ordering during table reconstruction.
- Personal accounting, opening balances, periods, mappings, transfers, privacy, and sharing remain
  blocked on product and qualified accounting decisions.

## 13. Explicitly deferred work

This milestone did not add or enable:

- schema v4 or canonical book-scoped financial tables;
- audit-book sidecars or a production cutover;
- `PersonalSpace`, PERSONAL resolution, personal APIs, accounts, activity, transfers, or reports;
- budgets, reminders, recurrence, goals, or document extraction;
- AI, LLM tools, OCR, bank integrations, tax/compliance behavior, billing, cloud, or production
  infrastructure; or
- new accounting classifications, default charts, or policy.

## 14. Readiness for C3

C2 establishes the required service/facade seam and exact schema-v3 business baseline for the next
migration stage. The repository is ready to begin **M5.1-C3 canonical book-scoped persistence
rehearsal on disposable database copies after separate authorization**. It is not approved for a
canonical-storage cutover or personal feature development. C3 must use the current service tests,
differential fixtures, migration evidence, and recovery runbook as fail-closed release gates.

## Verification

Final verification results:

| Check                    | Result                                                                                      |
| ------------------------ | ------------------------------------------------------------------------------------------- |
| Complete Python suite    | 77 passed in 18.955 seconds                                                                 |
| Focused C2 suite         | 7 passed in 0.710 seconds                                                                   |
| mypy strict              | Passed; 23 source files                                                                     |
| Ruff lint                | Passed                                                                                      |
| Ruff format              | Passed; 79 files already formatted                                                          |
| Frontend Vitest          | 10 passed in 1 test file                                                                    |
| Frontend TypeScript      | Passed                                                                                      |
| Frontend ESLint          | Passed                                                                                      |
| Frontend Prettier        | Passed                                                                                      |
| Next.js production build | Passed; 12 static pages plus dynamic routes generated                                       |
| Markdown local links     | 165 checked; 0 broken                                                                       |
| OpenAPI boundary         | 28 paths, 35 operations, no `ledger_book_id`, authorized-context, or PersonalSpace exposure |
| Source boundary          | Passed as part of the C2 suite                                                              |

The first sandboxed backend/frontend test attempts were blocked by Windows temp/process permissions
before application logic ran. The same locked commands passed when granted the required local test
process and temporary-database permissions. No dependency or product-code workaround was added.
