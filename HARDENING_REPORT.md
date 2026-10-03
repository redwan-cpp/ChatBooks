# Chatbooks Accounting-Core Hardening Report

Date: 2026-09-25

## Outcome

The existing accounting architecture was retained. The audit found no defect in double-entry
posting, reversal arithmetic, period enforcement, ledger-derived reporting, or transaction rollback.
One audit-integrity gap was fixed, and adversarial evidence was expanded substantially.

The accounting kernel is ready to support development of an application/API layer. It is not ready
for production exposure until that layer supplies authenticated actors, authorization policy, human
confirmation provenance, request idempotency, protected storage, and equivalent database guarantees.

## What was inspected

- The repository rulebook, memory, requirements, architecture, process, design, README, roadmap,
  security model, AI boundary, accounting model, and all four ADRs.
- Every Python source file, the complete SQLite schema and trigger set, CI configuration, dependency
  manifest/lock, and all existing accounting and CLI tests.
- Domain values, proposal/validation/confirmation/posting states, reversal flow, ledger queries,
  report arithmetic, audit creation, organization ownership, exception handling, and schema startup.
- Application and database protections for balance, atomicity, immutability, periods, references,
  duplicate posts/reversals, exact money, dates, audit history, and concurrent writers.

## Issues found and fixes made

1. **Forged audit insertion through the supported connection.** Updates, deletes, and replacements
   were already blocked, but a caller with accidental access to the engine's private SQLite
   connection could append a fabricated audit row directly. The database wrapper now installs a
   connection authorizer that permits `audit_events` inserts only from the known automatic audit
   triggers. File/database administrators remain inside the documented trust boundary.
2. **Adversarial evidence gaps.** Several behaviors were implemented but lacked direct tests,
   including mid-line failure rollback, reversal-of-reversal, concurrent competing reversals,
   post-versus-period-lock races, unknown references, negative account balances, exact maximum
   amounts, complete post audit correlation, project-derived totals, and full statement
   reconciliation. These cases now have explicit tests.
3. **API idempotency boundary.** Retrying the same confirmation is safely idempotent. The kernel
   cannot determine whether two newly created, content-identical proposals are a retry or two real
   transactions. Content-based deduplication would reject legitimate events, so the future API must
   bind caller-supplied idempotency keys to original results.
4. **Portable concurrency boundary.** SQLite `BEGIN IMMEDIATE` correctly serializes current writers.
   A future production database must recreate the behavior with appropriate isolation/locking,
   constraints, and the same concurrency tests.

No schema version or ADR changed because the architecture and persisted data model were not redesigned.

## New tests

Eleven hardening tests were added:

- rollback of journal header, partial lines, and audit events after a mid-copy failure;
- database rejection of zero-value lines and direct forged audit inserts;
- full reversal, duplicate-reversal rejection, and reversal-of-reversal chain behavior;
- missing account and project rejection without audit or proposal residue;
- explicit zero and negative account-balance behavior;
- project views derived only from tagged posted ledger lines, independent of planning metadata;
- complete, request-correlated posting audit events with UTC system timestamps;
- simultaneous reversal posting with exactly one winner;
- simultaneous posting and period locking with a serializable result;
- a known multi-entry reconciliation across ledger, account balances, trial balance, income
  statement, and balance sheet; and
- maximum supported line amounts using exact integer arithmetic.

The pre-existing suite already covers unbalanced proposals, zero/invalid sides, explicit
confirmation, duplicate posting, final-transition failure rollback, ordinary reversal, duplicate
reversal, locked periods and boundaries, inactive accounts, cross-organization references,
immutability, generated invariants, persistence, concurrent retries, audit creation, and database
integrity.

## Verification results

| Check                              | Result                              |
| ---------------------------------- | ----------------------------------- |
| Complete unit and subprocess suite | 46 tests passed in 9.171 seconds    |
| Strict mypy check                  | Passed; no issues in 6 source files |
| Ruff lint                          | Passed                              |
| Ruff format check                  | Passed; 28 files already formatted  |

Environment: Windows, Python 3.14.3, SQLite through the Python standard library.

## Remaining architectural risks

- Actor IDs are trusted inputs; the local kernel does not authenticate people or define production
  roles, approval separation, or membership administration policy.
- The private database connection must never be exposed by an API. Filesystem/database owners can
  still replace the database, alter triggers, or use another SQLite client; audit is append-only at
  the supported application boundary, not cryptographically tamper-evident.
- SQLite is a single-host database. Production database isolation, migrations, backup/restore,
  encryption, operational failure logs, and recovery procedures are deferred.
- Proposal creation has no caller idempotency key. The API must implement one; payload equality is
  not a safe substitute.
- The engine can enforce reversal semantics when its correction operation is used, but it cannot
  infer that an arbitrary balanced manual journal was intended as a correction. UI/API correction
  paths must use `propose_reversal`.
- Account hierarchy is not supported. Project financial views are line dimensions derived from the
  ledger; there is no separately mutable project financial total.
- Reports are deterministic basic ledger summaries, not jurisdiction-specific statutory statements.

## Accounting-policy questions requiring human decisions

- Jurisdiction, tax regime, reporting framework, cash/accrual basis, and revenue recognition.
- Fiscal calendars, opening/closing entries, retained earnings, late adjustments, and period reopening.
- Partial reversals, reversal-date policy, and correction behavior for inactive accounts.
- Production roles, dual approval, confirmation expiry, and who may lock or reopen periods.
- Multi-currency, FX rates, rounding, and organization precision changes.
- Account hierarchy, roll-up and posting-account rules.
- Project allocation and whether any project-level balancing rules are required.
- Proposal amendment/cancellation/supersession and document-evidence requirements.

These remain documented ambiguities; no policy was invented during hardening.

## Readiness decision

**Ready for application/API-layer development, with conditions.** The API may call the deterministic
engine as the exclusive accounting write boundary. Before production use, it must authenticate the
actor, enforce approved roles, bind explicit human confirmation to the displayed proposal, add
request idempotency keys, keep the database connection private, and preserve all current constraints,
atomicity, audit, and concurrency behavior in its deployment database.
