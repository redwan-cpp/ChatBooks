# M5.2-UI0.1 — SQLite Runtime Hardening Report

**Date:** 2026-09-30  
**Scope:** Python 3.14 FastAPI/SQLite connection lifecycle and concurrency only

## Outcome

The Python 3.14 SQLite request-lifecycle defect is remediated without changing the BUSINESS API,
accounting policy, schema, ledger behavior, or UI0 product behavior. The supported runtime now uses
one Uvicorn worker and distinct request-owned database connections that may move sequentially across
FastAPI worker threads.

No PERSONAL domain, personal row, AI behavior, budget, reminder, schema migration, schema-v4 target,
or C4 operation was introduced. The repository development database was not used by tests or
rendered verification.

## 1. Exact root cause

`get_engine` and `get_auth_service` are synchronous generator dependencies. For each request they:

1. create an `AccountingEngine` or `AuthService` and its SQLite connection;
2. yield it to nested dependencies and the synchronous endpoint; and
3. close it in the generator's `finally` block.

FastAPI delegates synchronous work through Starlette/AnyIO's worker pool. Entering a synchronous
generator dependency, running the next dependency or endpoint, and exiting the generator are
separate thread-pool operations. Python 3.14 can schedule those sequential operations on different
workers. The original connection used SQLite's default `check_same_thread=True`, so an otherwise
valid request could fail when its next lifecycle stage touched or closed the connection on another
thread.

A deterministic regression test reproduced the failure before remediation by creating, using, and
closing one request dependency on three known distinct worker threads. The use stage raised
`sqlite3.ProgrammingError` before the fix. The defect was connection ownership across sequential
request stages, not concurrent use of one connection and not frontend behavior.

## 2. Exact remediation

- `Database` and `CanonicalDatabase` accept an internal `allow_thread_handoff` option. Its default is
  `False`, preserving SQLite's creator-thread guard.
- `open_runtime_database`, `AccountingEngine.for_runtime`,
  `AccountingEngine.for_canonical_rehearsal`, and `AuthService` propagate the option without changing
  their default behavior.
- Only the FastAPI request dependencies opt into thread handoff. Each invocation still creates new
  engine and authentication objects with separate connections and closes them on dependency exit.
- CLI, direct engine, migration, backup, monitoring, cutover, rehearsal, and startup-validation
  connections retain strict creator-thread enforcement.
- Both normal and maintenance-aware `chatbook-api` startup paths explicitly configure
  `workers=1`.

The remediation does not catch or suppress `sqlite3.ProgrammingError`, pool connections, introduce a
second data layer, or change storage technology.

## 3. Accounting-semantics preservation

The handoff is sequential within one request. A connection is not shared by simultaneous request
handlers, and tests prove that concurrent requests receive distinct connection objects that all
close exactly once. The repository abstractions and universal financial service are unchanged.

Financial mutations still enter the same authoritative engine and acquire `BEGIN IMMEDIATE` before
reading posting conditions or changing state. Journal, proposal, confirmation, idempotency,
reversal, period, and audit writes retain their existing transaction boundaries and constraints.
The public OpenAPI and BUSINESS route contracts are unchanged.

## 4. Concurrency test evidence

`tests/test_sqlite_runtime.py` adds deterministic coverage for:

- create/use/close of one request dependency on three distinct worker threads;
- strict creator-thread enforcement for non-API connections;
- the one-Uvicorn-worker runtime policy;
- 12 simultaneous authenticated reads with unique request connections and exact close tracking;
- simultaneous report reads and posting, where readers observe only complete pre- or post-commit
  balances;
- six simultaneous retries of one idempotent post, producing one journal entry and one accounting
  effect;
- simultaneous owner and outsider reads with no cross-organization disclosure.

The module passed five consecutive runs. The complete backend suite passed **112 tests**. The named
C3, C4A, C4P2, C4P5, and C4P7 compatibility selection passed **26 tests**.

## 5. BUSINESS compatibility evidence

The complete suite covers the accounting kernel, FastAPI, authentication, authorization, C1/C2/C3,
C4A/C4P controls, CLI behavior, migrations, posting, idempotency, reversal, reports, projects,
documents, and immutable audit behavior. All 112 tests passed on Python 3.14.3.

The remediation changes only connection construction and server process configuration. It does not
change request or response models, route paths, roles, permissions, transaction data, report
arithmetic, audit payloads, or schema definitions.

## 6. Frontend verification

Frontend verification passed:

- 17 Vitest tests in two files;
- TypeScript with no errors;
- ESLint;
- Prettier check;
- Next.js production build with 13 generated static pages.

Rendered verification used the normal built frontend and normal `chatbook-api` runtime on Python
3.14.3. It used an isolated schema-v3 database with one synthetic user and an empty BUSINESS
organization. Chat, Money, Activity, Reports, and Settings loaded correctly. Four authenticated
financial pages loaded concurrently, and a separate 120-request authenticated read run returned
only HTTP 200 responses. Browser consoles and backend output contained no SQLite thread errors.

The Personal shell remained deferred: Projects was absent, Personal Money/Activity/Reports/Settings
showed no business context or financial values, and no PERSONAL API or database data was created.
The run used no thread-pool limiter and no one-thread workaround.

## 7. Deployment and runtime implications

The supported SQLite topology is:

- one host;
- one `chatbook-api` backend process;
- one Uvicorn worker in that process;
- multiple request worker threads as needed;
- distinct request-owned connections; and
- SQLite's existing `BEGIN IMMEDIATE` single-writer gate.

The entry point now enforces one Uvicorn worker. Deployment supervision must independently enforce
one backend instance and prevent replacement overlap. `WEB_CONCURRENCY` or a multiprocess wrapper
must not be used to create additional SQLite writers.

## 8. Remaining SQLite limitations

This milestone does not make SQLite horizontally scalable or safe for multiple backend processes,
multiple hosts, rolling writer overlap, or shared-network storage. SQLite still serializes writers,
so write throughput and lock contention require measurement on the selected deployment host.
Backups, restore, monitoring, capacity, and C4 approvals remain governed by the existing C4P
controls. A future database redesign must re-prove all financial invariants and concurrency
properties.

## 9. Files changed

- `chatbook/database.py`
- `chatbook/canonical_database.py`
- `chatbook/runtime.py`
- `chatbook/engine.py`
- `chatbook/auth.py`
- `chatbook/api/main.py`
- `tests/test_sqlite_runtime.py` (new)
- `docs/M5_2_UI0_1_SQLITE_RUNTIME_HARDENING_REPORT.md` (new)
- `docs/M5_2_UI0_CHATBOOKS_PRODUCT_SHELL_REPORT.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/M5_1_C4P7_SAAS_DEPLOYMENT_FOUNDATION.md`
- `deploy/saas/README.md`
- `README.md`
- `memory.md` (task bookkeeping only)

## Verification summary

| Check                           | Result                                                                                     |
| ------------------------------- | ------------------------------------------------------------------------------------------ |
| Concurrency-sensitive module    | PASS — 7 tests, repeated 5 times                                                           |
| Complete backend suite          | PASS — 112 tests                                                                           |
| C3/C4A/C4P2/C4P5/C4P7 selection | PASS — 26 tests                                                                            |
| mypy                            | PASS — strict check of 33 application source files                                         |
| Ruff lint                       | PASS                                                                                       |
| Ruff formatting                 | PASS — 48 files                                                                            |
| Frontend tests                  | PASS — 17 tests in 2 files                                                                 |
| TypeScript, ESLint, Prettier    | PASS                                                                                       |
| Next.js production build        | PASS — 13 static pages generated                                                           |
| Live normal-runtime concurrency | PASS — 4 concurrent page loads and 120 authenticated API reads                             |
| Documentation links             | PASS — 72 Markdown files, 254 local links, 0 broken                                        |
| Source-boundary scan            | PASS — no unconditional thread-check disable, personal schema, or personal API route       |
| Isolated runtime database       | PASS — schema v3, integrity `ok`, 0 FK violations, 0 journal entries, 0 personal tables    |
| Development database            | PASS — SHA-256 remained `D28F7434DF6F6954D42C8C0A607B9BE41BB4A7D61DC20D5B8FA7DABF8071C884` |

## Final state

`SQLite runtime concurrency issue remediated; Chatbooks UI0 remains intact.`
