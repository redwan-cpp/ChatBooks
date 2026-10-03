# Chatbooks M3 API-layer implementation report

Date: 2026-09-26

## Outcome

M3 is implemented as a FastAPI application boundary around the existing deterministic accounting
engine. The API authenticates users, derives the actor from a server-side session, enforces explicit
organization permissions, and delegates accounting mutations and report calculations to the engine.
It does not expose SQLite connections or duplicate ledger arithmetic.

The complete supported path is covered by HTTP integration tests:

`register/login → organization → proposal → validate → confirm exact version → post idempotently →
ledger/reports → reversal proposal → confirm/post reversal → preserved history and audit`

## Repository and integration review

The review covered the rulebook, project memory, root requirements/design/process documents, all
architecture, accounting, AI-boundary, security, roadmap, and ADR documents, the schema and database
adapter, domain and accounting engine, CLI, packaging, and the complete test suite.

No defect requiring a redesign of the hardened accounting kernel was found. The application-layer
gaps were:

- no authenticated network actor boundary;
- organization memberships had no role;
- confirmation did not store an explicit proposal version or API request provenance;
- retries had no caller-supplied command key;
- schema version 1 had no migration path for API tables;
- projects were fully immutable, preventing audited planning-metadata updates required by the API;
- the kernel had no explicitly bounded cash-flow view; and
- FastAPI, server, and HTTP integration-test dependencies were absent.

## Changes made

### API, authentication, and authorization

- Added a FastAPI application factory, versioned routes, typed Pydantic contracts, bounded
  pagination, consistent errors, request IDs, and structured request logging.
- Added normalized usernames, per-password salted scrypt hashes, random opaque bearer sessions,
  SHA-256 token storage, expiry, and logout revocation. Client actor IDs are never trusted.
- Added `OWNER`, `ADMIN`, `ACCOUNTANT`, `MEMBER`, and `VIEWER` with a centralized permission map for
  views, proposals, confirmation/posting, manual journals, reversals, reports, audit, account/period
  management, membership administration, and period locking.
- Scoped every organization route through authenticated membership and permission checks.

### Accounting application boundary

- Added organization, membership, project, account, period, proposal, journal/reversal, report, and
  read-only audit endpoints. API routes call public engine operations and contain no SQL or ledger
  calculations.
- Kept proposal lifecycle state derived from immutable proposal, validation, confirmation, and
  journal records instead of storing a competing state machine.
- Bound confirmation to proposal ID, stored proposal version, validation, authenticated actor, UTC
  confirmation time, and caller request identifier. Stale or mismatched versions fail.
- Added caller-key idempotency receipts for confirmation and posting. Receipts commit atomically with
  results, replay identical retries, and reject conflicting key reuse.
- Carried the caller request identifier into posting and confirmation audit metadata.
- Exposed reversal only through the engine's compensating-entry workflow; originals remain visible.
- Added an engine cash-movement report for caller-selected asset accounts. It deliberately leaves
  operating/investing/financing classification undefined pending an approved accounting policy.

### Persistence and compatibility

- Advanced SQLite to schema version 2 with credential, session, confirmation-provenance, and command
  idempotency tables plus immutability and integrity triggers.
- Added a tested v1-to-v2 migration that preserves posted entries and audit history, assigns the
  organization-creation actor as owner, backfills version-1 confirmation provenance, and installs
  the new guards.
- Allowed audited updates to project planning metadata while keeping organization and project
  identity immutable. Financial project totals remain derived from tagged posted journal lines.
- Added FastAPI and Uvicorn as runtime dependencies and Starlette's supported `httpx2` test client as
  a development dependency; refreshed the lockfile.

### Architecture records and documentation

Updated the architecture, accounting model, AI boundary, security model, roadmap, requirements,
design, process, README, and ADR index. Added ADRs for the FastAPI boundary, authentication and role
authorization, confirmation provenance, and command idempotency. Accounting and workflow ambiguities
remain explicit rather than encoded as inferred policy.

## Tests added

Nine HTTP integration tests cover:

- anonymous rejection and authenticated access;
- allowed roles, denied roles, and cross-organization isolation;
- project create/read/update and tenant isolation;
- proposal creation and deterministic validation;
- stale-version rejection, confirmation success, same-key replay, and conflicting-key rejection;
- posting success and retry without a second accounting effect;
- authorized and unauthorized reversal with original history preserved;
- locked-period rejection through the API;
- trial balance, statements, general ledger, and selected-account cash movements reconciled to the
  engine; and
- complete correlated financial audit events, read-only audit routes, and no exposed database route.

One migration test reconstructs a version-1 database, migrates it, and verifies preserved ledger
history, ownership, confirmation provenance, foreign keys, and database integrity.

## Verification results

| Check                                                     | Result                                                |
| --------------------------------------------------------- | ----------------------------------------------------- |
| Locked environment synchronization                        | Passed; 23 packages resolved                          |
| Complete unit, concurrency, CLI, migration, and API suite | Passed; 56 tests in 13.562 seconds                    |
| Project-configured strict mypy gate                       | Passed; 11 application source files                   |
| Ruff lint                                                 | Passed                                                |
| Ruff formatting check                                     | Passed; 40 files already formatted                    |
| Local Markdown-link check                                 | Passed; 24 documents                                  |
| OpenAPI generation smoke check                            | Passed; 27 paths, 34 operations, unique operation IDs |

The configured strict type gate intentionally covers `chatbook`, not tests. An additional diagnostic
run against `chatbook tests` reported 194 annotation/type errors in the test modules; this does
not change the passing application-package gate or runtime suite, but typing the tests remains useful
maintenance work.

## Remaining architectural and security risks

- SQLite remains a single-host database. A production database must reproduce transaction isolation,
  unique constraints, immutable history, audit atomicity, and concurrency behavior.
- A filesystem/database administrator remains inside the trust boundary; audit rows are not
  cryptographically anchored outside the database.
- TLS/proxy trust, deployment secrets, rate limiting, MFA, password reset/recovery, protected
  backup/restore, security monitoring, and session administration are not implemented.
- Migrated CLI-only users need an approved credential-provisioning workflow.
- Role changes/removal and ownership transfer are not implemented.
- Idempotency does not yet cover proposal creation or reversal-proposal creation, and receipt
  retention has no deletion policy.
- Separate report requests do not share a multi-report snapshot/export transaction.
- The CLI remains a trusted local actor-ID interface and must not be exposed as a remote or AI tool.
- Tests are runtime-complete for this milestone, but strict typing does not yet cover test code.

## Accounting and workflow decisions still required

- jurisdiction, tax regime, reporting framework, cash/accrual basis, and revenue recognition;
- cash-account designation and operating/investing/financing cash-flow classification;
- fiscal closing, retained earnings, opening balances, adjustment periods, and period reopening;
- dual approval, confirmation expiry, and separation-of-duties policy;
- proposal amendment/cancellation/supersession and master-data amendment rules;
- partial reversals and broader correction policy, including inactive accounts;
- multi-currency, FX conversion, rounding, and precision changes;
- project allocation and per-project balancing policy; and
- document evidence, checksum verification, deduplication, extraction, and retention.

## Readiness assessment

The foundation is ready for a client or UI to use the M3 API in the current local, single-host
architecture. The deterministic accounting engine remains the exclusive accounting write boundary,
and all required accounting invariants pass through the API. Internet or multi-host production
deployment should wait for the security, operations, database, and accounting-policy decisions above.
