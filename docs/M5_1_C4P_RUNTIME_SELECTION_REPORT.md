# M5.1-C4P2 normal schema-v4 runtime selection report

**Date:** 2026-09-28  
**Project and product:** Chatbooks
**Status:** Engineering preparation complete; normal schema-v4 selection is implemented but not
activated; C4P3 records **NOT READY FOR FINAL PREFLIGHT**; M5.1-C4 remains `NO-GO`

This report records the production-shaped runtime-selection boundary and the C4P control hardening
completed without running the BUSINESS schema-v3 to schema-v4 cutover. The controlled staging
environment remains on schema v3. No schema-v4 database, canary transaction, PERSONAL owner, or v4
writer was created or started.
The current consolidated blocker classification is in
[`M5_1_C4P3_FINAL_READINESS_REPORT.md`](M5_1_C4P3_FINAL_READINESS_REPORT.md).

## 1. Previous blocker

C3 proved the canonical schema-v4 repository and migration only on disposable copies. C4P then
prepared a persistent schema-v3 staging environment, but the normal API, authentication service,
and CLI still opened the legacy `Database` path. The only way to exercise schema v4 was the
rehearsal-only `canonical_rehearsal=True` path. That was intentionally unsuitable for deployment:
normal startup could not name a reviewed v4 target, prove adapter/schema compatibility, or bind the
selection to an immutable release identity.

C4P2 closes that engineering blocker. It does not authorize selection of schema v4 in the
controlled environment. Source approval, the maintenance window, migration execution, read-only
acceptance, canary approval, and writer resumption remain separate operator gates.

## 2. Design chosen

`RuntimeConfiguration` is the single normal-runtime selection boundary. It maps one explicit
storage mode and access mode to one expected schema and adapter:

| Storage mode      | Schema | Adapter             | Current C4P state |
| ----------------- | -----: | ------------------- | ----------------- |
| `organization-v3` |      3 | `Database`          | selected          |
| `canonical-v4`    |      4 | `CanonicalDatabase` | implemented only  |

The API factory, authentication service, accounting engine, and trusted CLI all receive the same
resolved configuration. No route, request body, query parameter, actor, organization, or raw
`ledger_book_id` can choose a storage mode. `AccountingEngine.for_runtime()` changes only the
persistence adapter. BUSINESS authorization, server-side financial-context resolution, application
services, accounting validation, journal posting, reporting, idempotency, and audit logic remain
unchanged.

`CanonicalDatabase` now opens only an existing file in the configured SQLite `read-only` or
`read-write` mode. It does not create or migrate a target. Startup first performs a read-only
inspection of the exact configured path,
checks the schema, integrity, foreign keys, BUSINESS owner scope, and canonical mapping, and only
then opens the selected adapter. There is no fallback between adapters.

## 3. Exact files changed

| File                                             | Change                                                                                                                        |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `chatbook/runtime.py`                            | Added explicit server configuration, fail-closed inspection, sanitized evidence, and the `chatbook-runtime` command.          |
| `chatbook/canonical_database.py`                 | Restricted canonical startup to an existing verified schema-v4 file.                                                          |
| `chatbook/engine.py`                             | Added the normal configured adapter path while retaining the disposable rehearsal factory.                                    |
| `chatbook/auth.py`                               | Made authentication use the same normal runtime configuration and adapter.                                                    |
| `chatbook/api/main.py`                           | Wired normal server startup to deployment configuration; explicit test/local database injection remains schema-v3 compatible. |
| `chatbook/cli.py`                                | Made storage mode server-environment-only and required any v4 database override to match the configured path exactly.         |
| `chatbook/deployment_preparation.py`             | Hardened fixed C4P controls and added deterministic runtime verification/evidence and the `harden` operation.                 |
| `pyproject.toml`                                 | Registered the runtime inspection command.                                                                                    |
| `tests/test_m5_1_c4p2.py`                        | Added runtime matrix, adapter-pairing, BUSINESS parity, sanitized-evidence, and C4P hardening tests.                          |
| `docs/M5_1_C4P_RUNTIME_SELECTION_REPORT.md`      | Added this C4P2 implementation and evidence report.                                                                           |
| `docs/M5_1_C4P_DEPLOYMENT_PREPARATION_REPORT.md` | Preserved historical C4P evidence and added C4P2 runtime, recovery, release, and blocker status.                              |
| `docs/M5_1_C4A_READINESS_REPORT.md`              | Updated readiness with the closed engineering blocker and remaining gates.                                                    |
| `docs/M5_1_C4_RELEASE_CHECKLIST.md`              | Added C4P2 evidence while leaving every approval checkbox open.                                                               |
| `docs/M5_1_C4_CUTOVER_RUNBOOK.md`                | Replaced the stale missing-selector note with the reviewed read-only acceptance path.                                         |
| `README.md`                                      | Linked the C4P2 report.                                                                                                       |
| `memory.md`                                      | Receives the required final dated task and verification record.                                                               |

No accounting schema, journal rule, migration semantics, public API payload, user role, organization
boundary, or financial calculation was changed.

## 4. Configuration boundary

Normal server startup accepts these deployment-owned values:

| Value                         | Purpose                                                                |
| ----------------------------- | ---------------------------------------------------------------------- |
| `CHATBOOK_STORAGE_MODE`       | Exact mode: `organization-v3` or `canonical-v4`.                       |
| `CHATBOOK_SCHEMA_VERSION`     | Expected schema paired with the mode.                                  |
| `CHATBOOK_DB_PATH`            | Exact database path. Schema v4 requires an absolute path.              |
| `CHATBOOK_RUNTIME_ACCESS`     | Exact access: `read-only` or `read-write`; required for schema v4.     |
| `CHATBOOK_RUNTIME_RELEASE_ID` | Immutable release identity. Schema v4 requires a 64-character SHA-256. |

The absence of deployment configuration preserves the existing local schema-v3 default. Selecting
`canonical-v4` requires all five values and an existing compatible database. The controlled C4P
selector is a protected JSON file rendered into process environment by `Start-Backend.ps1`; it
currently names only the controlled schema-v3 source with `read-write` access. The control accepts
the fixed controlled source for v3, or the fixed reserved target with `read-only` access for a future
post-migration acceptance phase. It rejects every other path/access combination and never provides
a general arbitrary-database administration switch. Enabling writable v4 after acceptance requires
a separate deployment configuration change under the writer-resumption approval gate.

The following configuration is rejected at the boundary: rehearsal flags, raw book identifiers,
PERSONAL or financial-space selectors, unknown modes, unsupported/mismatched schema versions,
relative v4 paths, missing v4 access mode, read-only v3 mode, the repository development
`chatbook.db`, missing v4 targets, malformed release identities, and CLI overrides that differ from
the server-owned v4 path.

## 5. Startup safety behavior

Startup is fail closed:

- mode and expected schema must be an exact supported pair;
- read-only inspection must see the configured schema version, `integrity_check = ok`, zero foreign
  key violations, and only BUSINESS owner kinds;
- canonical mapping validation must pass before the v4 adapter opens;
- the old v3 `Database` rejects schema v4;
- the v4 adapter refuses an absent path and never creates a file;
- v4 read-only mode opens SQLite with `mode=ro`, enables query-only enforcement, and rejects writes
  before beginning a transaction;
- normal configuration rejects rehearsal-only activation and any client/raw-book authority;
- the repository development database cannot be selected as schema v4; and
- no mismatch causes fallback, migration, downgrade, mode switching, or PERSONAL enablement.

The inspection evidence contains only path and file identity, release/configuration identity,
mode/schema/access, owner-kind labels, integrity status, foreign-key count, and an explicit redaction
flag.
It contains no credentials, tokens, book identifiers, journal payloads, descriptions, or audit JSON.

## 6. Rollback and failure behavior

Configuration and inspection fail before API routes, authentication, CLI commands, or accounting
services can operate. They do not begin a migration and do not change the selected database.
`CanonicalDatabase` performs no initialization. A missing or mismatched v4 target therefore leaves
no partial target and no downgrade path.

Once an accepted database is open, all financial mutations continue through the existing
deterministic engine, database transaction, validation, authorization, idempotency, and audit
boundaries. C4P2 did not change C4 rollback rules: before v4 commit, the migration transaction may
roll back; after commit and before the first v4 financial write, only the verified v3 recovery path
is eligible; after any v4 financial write, ordinary v3 restore is forbidden and forward recovery
must preserve the new history.

## 7. BUSINESS compatibility evidence

Disposable-copy parity tests selected normal schema v4 through `RuntimeConfiguration`, then used the
unchanged public `AccountingEngine`, FastAPI organization/report routes, authenticated BUSINESS
identity, and trusted CLI. Organizations, general ledger, trial balance, and complete audit history
matched the schema-v3 source. OpenAPI exposed no `ledger_book_id`, and the source copy remained
unchanged.

The full backend suite covers organization RBAC/isolation, organization-v1 fingerprints, immutable
audit sequences and payload hashes, idempotent confirmation/posting, reports, projects/documents,
reversals, locked periods, concurrency, source-boundary enforcement, schema-v3 compatibility, and
C3 canonical behavior. No accounting logic was added to the runtime boundary.

The controlled environment uses release
`672e551c8617a1e5371d4a5b31350fce700189f02c75457fafb9519241e43bde` and configuration fingerprint
`12c64ab1b7513b3b482891531d98d4a8b603f48f4e47eed3afaf16b198213ded`.
The hardened backend and frontend controls were live-rehearsed on the existing schema-v3 source,
then stopped. Final evidence records no listeners or PID files and a successful rollback-only writer
gate.

### Controlled-source recovery disclosure

During the C4P2 live check, an authenticated read was attempted. Authentication creates an
`auth_sessions` row, so it changed the staging file even though no financial command ran. The
verifier correctly stopped on `evidence.content_mismatch`. The post-authentication file was retained
in the restricted backup area, and the source was restored from the existing verified schema-v3
backup while all processes were stopped.

The original source SHA-256 was
`7532962f3d3e752655946b1ec629b219e11d4f63de618dee0baa0c6e1e03e936`; the restored source and
verified backup now share SHA-256
`de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71`.
The deterministic content fingerprint remains
`bb2574b83dcd0855ef5b52150905e256f90208075e1c5e3a6623e2fc7cfe12c2`.
Only `auth_sessions` differed before recovery (three rows instead of two); all financial metrics,
eight journal entries, sixteen journal lines, sixteen idempotency receipts, and 150 audit events
were unchanged. Final verification records schema 3, integrity `ok`, zero foreign-key violations,
two restored sessions, no v4 target, and no PERSONAL data. This physical source rebaseline is not
silently treated as approval; source approval remains an operator decision.

## 8. Verification results

| Check                                      | Result                                                                                    |
| ------------------------------------------ | ----------------------------------------------------------------------------------------- |
| Focused C4P2 runtime/startup/control tests | 5 passed                                                                                  |
| Complete backend suite                     | 95 passed in 39.766 seconds                                                               |
| C3/C4A and failure-injection coverage      | Passed as part of the complete suite; focused suite also passed before final verification |
| Mypy                                       | Passed, 30 source files                                                                   |
| Ruff                                       | Passed                                                                                    |
| Ruff formatting                            | Passed, 102 files formatted                                                               |
| Frontend tests                             | 10 passed                                                                                 |
| Frontend type check                        | Passed                                                                                    |
| Frontend lint                              | Passed                                                                                    |
| Frontend formatting                        | Passed                                                                                    |
| Frontend production build                  | Passed, 12 static/dynamic route groups generated                                          |
| C4P runtime evidence                       | Schema 3, integrity `ok`, zero FK violations, BUSINESS only                               |
| Writer gate                                | Acquired; controlled competing writer blocked; rolled back without mutation               |
| Final listeners/PID files                  | None                                                                                      |
| Reserved v4 target                         | Absent                                                                                    |
| Development `chatbook.db`                  | SHA-256 unchanged: `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`     |
| Documentation/link checks                  | Passed after documentation update                                                         |

The first constrained backend and frontend-test invocations were blocked by operating-system sandbox
permissions for temporary directories and child processes. The identical commands were rerun with
the required local permissions and produced the passing results above.

## 9. Unresolved human and operator decisions

Engineering-closable C4P items are complete: normal v4 selection, startup safety checks, fixed-path
control hardening, and deterministic sanitized evidence generation.

The following remain unresolved and are not represented as complete:

- named release owner, migration operator, application operator, accounting/data reviewer, and
  incident recorder;
- approval of the exact source, including the recorded verified-backup rebaseline;
- encryption and off-host recovery controls;
- retention, destruction, and access-audit ownership;
- monitoring owners, numerical thresholds, escalation routes, and observation duration;
- approved maintenance window, request-drain interval, downtime budget, and disk safety margin;
- elevated inventory of services, scheduled tasks, processes, listeners, open handles, raw SQLite
  tools, and trusted CLI access;
- accounting/data approval of canary inputs and explicit release-owner authorization to run it; and
- final post-migration acceptance and writer-resumption approval.

Every box in the C4 release checklist remains unchecked.

## 10. Confirmation that C4 was not executed

The controlled source is schema v3. No schema-v3 to schema-v4 migration ran. The reserved v4 target
does not exist. No canary, reversal, or other financial mutation was executed. No v4 writer was
started or resumed. No PERSONAL owner, data, or behavior was introduced. The development database
was not modified.

**M5.1-C4P engineering preparation complete; C4 remains blocked only by deployment-specific and
human approval gates.**
