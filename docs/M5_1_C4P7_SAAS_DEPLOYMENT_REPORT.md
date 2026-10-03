# M5.1-C4P7 SaaS server deployment report

**Date:** 2026-09-30  
**Project and product:** Chatbooks
**Scope:** Deployment foundation only  
**Final state:** **SERVER DEPLOYMENT FOUNDATION PREPARED — C4 NOT EXECUTED**

## Result

C4P7 records **D01 = B**. The existing Windows environment at
`F:\ChatbookDeployment\m5-1-c4-controlled` is permanently classified as controlled staging for
this decision. Its C3/C4A/C4P/C4P2/C4P5 evidence remains historical engineering evidence and does
not approve a future server or source.

The repository now contains one provider-neutral deployment foundation for a public SaaS server
with HTTPS ingress, one internal Next.js frontend, one internal FastAPI backend, exactly one
authoritative SQLite writer, private persistent storage, separated backup/restore/evidence paths,
maintenance controls, and read-only monitoring hooks.

No actual server was selected or inspected. No real server database was provisioned. No production
capacity, security control, threshold, or readiness claim is made.

## What changed

| Area               | Implementation                                                                                                                                                                                           |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Deployment package | Added `deploy/saas` with provider-neutral configuration, environment, ingress, process, storage, and monitoring contracts.                                                                               |
| Config boundary    | Added strict server config parsing with absolute contained paths, immutable release identity, loopback binding, schema/mode pairing, and exactly one writer.                                             |
| Provisioning       | Added an explicit schema-v3 command that uses existing `AuthService` and `AccountingEngine` boundaries and refuses existing artifacts.                                                                   |
| Evidence           | Added sanitized hash, schema/content fingerprints, row counts, release/config identity, and BUSINESS-only source inspection.                                                                             |
| Backup/restore     | Added maintenance-gated wrapper over the existing verified SQLite backup and restore-proof operations.                                                                                                   |
| Writer gate        | Added a rollback-only controlled competing-writer proof with no data mutation.                                                                                                                           |
| Runtime            | Preserved normal C4P2 mode/schema/path/access/release selection. No automatic migration or v4 activation was added.                                                                                      |
| Tests              | Added adversarial config, package boundary, provisioning, startup/health/authentication, maintenance, graceful shutdown, writer-gate, backup/restore, source preservation, and no-PERSONAL/no-v4 checks. |
| C4 documents       | Recorded D01=B and separated Windows staging identity from the absent future server identity.                                                                                                            |

The deterministic accounting engine, schema, journals, reports, public BUSINESS API, authorization,
idempotency, audit, migration logic, and rollback policy were not changed.

## Repository requirements found

- Backend: `chatbook-api`, Python `>=3.12`, locked FastAPI/Uvicorn dependencies, loopback host/port
  variables, startup database validation, `/api/v1/health`, server-owned maintenance, and sanitized
  operational events.
- Frontend: `npm ci`, `npm run build`, and `npm run start`; Next 16.3.6 requires Node `>=20.9.0`;
  full locked verification with Vitest requires `^22.12.0`, `^24.0.0`, or `>=26.0.0`; server-only
  `CHATBOOK_API_URL` connects the Next proxy to FastAPI.
- Authentication: scrypt password hashes, opaque bearer sessions, stored token hashes, and an
  HTTP-only secure production cookie at the Next boundary.
- Storage: schema v3 is initialized by the existing `Database`/`schema.sql` path. Schema v4 is an
  explicit existing-target choice only. Neither startup nor C4P7 migrates automatically.
- Operations: existing maintenance, backup/restore, migration evidence, canonical migration, and
  twelve-signal monitoring commands are reused.

The exact file and command inventory is in
[`M5_1_C4P7_SAAS_DEPLOYMENT_FOUNDATION.md`](M5_1_C4P7_SAAS_DEPLOYMENT_FOUNDATION.md).

## Disposable deployment-package evidence

Tests created only temporary server roots. Each disposable run:

- provisioned schema 3 through the existing service/accounting boundary;
- created two BUSINESS organizations with BDT/2 and USD/3 precision;
- covered all five roles, active/inactive accounts, open/locked periods, projects/documents,
  proposal lifecycle states, posting retry/idempotency, reversal, audit, ledger, and reports;
- returned a balanced trial balance for each organization;
- started the FastAPI application and returned health 200;
- authenticated through the normal session boundary;
- rejected requests with 503 after drain/seal;
- closed the backend lifecycle cleanly;
- acquired the SQLite writer gate and blocked a controlled competing writer;
- created and reconciled a verified backup and separate restore proof;
- preserved the source during writer-gate and backup/restore operations;
- left the schema-v4 target absent;
- emitted no credentials or raw book IDs in sanitized evidence; and
- created no PERSONAL table, owner, or data.

These are engineering tests, not deployment evidence and not an approved source.

## Server readiness boundary

### KNOWN FROM REPOSITORY

- single local SQLite file with exactly one backend writer;
- Python and Node compatibility constraints recorded from manifests/lock metadata;
- backend/frontend commands and environment variables;
- private backend, public frontend, and same-origin proxy topology;
- schema-v3 creation and explicit v4 runtime selection behavior;
- maintenance/drain/shutdown, backup/restore, writer-gate, monitoring, and evidence code;
- fail-closed schema/integrity/foreign-key/owner-scope checks;
- no client authority over database paths, schema mode, maintenance, or book ownership.

### NEEDS SERVER MEASUREMENT OR OPERATOR EVIDENCE

- provider, server, OS, region, DNS, TLS, ingress, firewall, supervisor, and service identities;
- CPU, memory, persistent disk, IOPS, network, database growth, and safety margin;
- filesystem/SQLite lock behavior and atomicity on the selected volume;
- ingress/frontend/backend drain and shutdown behavior;
- latency, lock/error rates, backup/restore/migration duration, thresholds, and observation period;
- encryption, off-host recovery, retention/destruction, and protected-artifact access audit;
- complete privileged process/service/task/container/CLI/raw-SQLite/file-handle inventory;
- named owners, source/release/recovery/canary approvals, rollback acknowledgement, signatures, and
  final go/no-go.

## Verification

| Check                                                         | Result                                                                                     |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Focused C4P7 deployment tests                                 | PASS — 4/4                                                                                 |
| C3/C4A migration and failure-injection suite                  | PASS — included in combined 26/26 suite                                                    |
| C4P2 runtime-selection suite                                  | PASS — included in combined 26/26 suite                                                    |
| C4P5 traffic/monitoring suite                                 | PASS — included in combined 26/26 suite                                                    |
| Complete backend suite                                        | PASS — 105 tests in 41.478 seconds                                                         |
| Startup, health, maintenance, shutdown, writer-gate, security | PASS — covered by focused C4P7 tests                                                       |
| Mypy                                                          | PASS — 33 source files                                                                     |
| Ruff lint and format                                          | PASS — lint clean; 117 files already formatted                                             |
| Frontend tests/type/lint/format/build                         | PASS — 10 tests plus typecheck, ESLint, Prettier, and Next build                           |
| Documentation links/format                                    | PASS — 70 Markdown files, 253 local links, 0 broken; changed files formatted               |
| Development database                                          | PASS — SHA-256 remained `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884` |
| Windows staging source/recovery and v4-target boundary        | PASS — source/recovery hashes unchanged; v4 target remains absent                          |

The focused C4P7 tests use disposable roots only. The first sandboxed frontend test launch was
blocked by the local process sandbox (`spawn EPERM`); the permitted rerun passed all 10 tests. This
was a test-runner environment restriction, not an application failure.

## Final blocker table

| BLOCKER                   | STATUS               | EVIDENCE                                                                                                             | EXACT NEXT ACTION                                                                                                                         |
| ------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Server selected           | `BLOCKED`            | D01=B excludes the Windows staging host; no replacement server is named or inspected.                                | Operator selects provider/server/OS/region and records immutable host identity.                                                           |
| Deployment source         | `BLOCKED`            | Provisioning procedure and disposable tests exist; no server-side schema-v3 source exists.                           | On the selected server, provision through the reviewed command, inspect, and obtain Release Owner plus Accounting/Data Reviewer approval. |
| Server topology           | `PARTIALLY PREPARED` | One provider-neutral single-server topology and machine-readable contract exist.                                     | Bind the contract to the selected server, identities, ports, supervisor, and storage; inspect it.                                         |
| Public ingress            | `PARTIALLY PREPARED` | Provider-neutral frontend-only ingress contract exists; no public ingress is deployed.                               | Select and configure ingress; prove FastAPI/storage are not public and test maintenance behavior.                                         |
| HTTPS                     | `BLOCKED`            | HTTPS/TLS is required; no domain, certificate, termination, renewal, or redirect evidence exists.                    | Select domain/TLS mechanism, deploy it, and record certificate/renewal and plaintext rejection evidence.                                  |
| Single-writer enforcement | `PARTIALLY PREPARED` | Config/process contracts enforce one backend; disposable writer-gate and shutdown tests pass.                        | Configure the actual supervisor/ACLs and complete elevated process/service/task/handle verification.                                      |
| Database persistence      | `PARTIALLY PREPARED` | Absolute private local path and SQLite filesystem contract exist; disposable schema-v3 startup passes.               | Provision selected persistent volume; verify durability, locking, ownership, atomic replace, capacity, and restart persistence.           |
| Backups                   | `PARTIALLY PREPARED` | Maintenance-gated backup/restore implementation and disposable parity test exist.                                    | Select protected storage, ACLs, retention, then create and restore-test a fresh server backup under the writer gate.                      |
| Off-host recovery         | `BLOCKED`            | Contract explicitly leaves it absent.                                                                                | Implement encrypted off-host copy, custodian/audit/retention, hash verification, and successful restore drill.                            |
| Secrets                   | `PARTIALLY PREPARED` | Config separates secrets and emits no credentials; credentials file is exclusive and unlogged.                       | Select platform secret store/injection, principals, rotation, audit, and removal of provisioning credentials.                             |
| Monitoring                | `PARTIALLY PREPARED` | Deterministic collector and config template exist; hard invariants are separated from baselines.                     | Deploy collector/destination, name owners, test redacted alerts, measure and approve empirical thresholds/observation period.             |
| Maintenance/drain         | `PARTIALLY PREPARED` | Server-owned gate, drain, shutdown, package contract, and disposable tests exist.                                    | Bind to ingress/supervisor; measure all layers; approve timeouts; verify restart suppression and zero handles.                            |
| Recovery release          | `BLOCKED`            | Windows recovery release is staging-specific; no exact future server v3/v4 release pair exists.                      | Build, hash, compatibility-test, protect, and approve exact server recovery/C4 releases.                                                  |
| Canary                    | `READY_FOR_APPROVAL` | Existing BUSINESS canary remains defined and unexecuted.                                                             | Accounting/Data Reviewer and Release Owner approve it only after server v4 read-only acceptance.                                          |
| Human approvals           | `BLOCKED`            | D01=B is recorded; all named roles, security/threshold/source signatures, and rollback acknowledgement remain blank. | Assign named people and complete evidence-bound approvals without reusing Windows source approval.                                        |
| Final C4 preflight        | `BLOCKED`            | No real server/source, fresh final evidence, signatures, or C4 authorization exists.                                 | Close every prerequisite, run final preflight under writer gate, reconcile manifests, and obtain explicit go/no-go.                       |

## Safety confirmation

C4P7 did not access or alter a production server because none was identified. It did not alter the
Windows staging source, create its v4 target, execute its canary, or treat its evidence as server
approval. It did not modify the development database, migrate any persistent database, resume a v4
writer, or create PERSONAL data.

**SERVER DEPLOYMENT FOUNDATION PREPARED — C4 NOT EXECUTED**
