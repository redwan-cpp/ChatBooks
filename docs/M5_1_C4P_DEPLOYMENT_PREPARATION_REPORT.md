# M5.1-C4P controlled deployment preparation report

**Date:** 2026-09-28  
**Project and product:** Chatbooks
**Environment classification:** `CONTROLLED_DEPLOYMENT_STAGING_NOT_PRODUCTION`  
**Status:** C4P2 engineering preparation complete; C4 still not executed and remains `NO-GO`

This report records the controlled schema-v3 BUSINESS environment prepared for a future,
separately authorized M5.1-C4 cutover. The data is deliberately seeded staging data. It is more
representative than the disposable C4A fixture, but it is neither production data nor evidence that
a production cutover occurred.

## 1. Exact environment established

The controlled target is on the inspected Windows host `DESKTOP-0D25D0C` under
`F:\ChatbookDeployment\m5-1-c4-controlled`. It is outside the repository and `.test-tmp`, and it
does not reuse `F:\Projects\chatbook\chatbook.db`.

| Artifact                 | Exact path or value                                 |
| ------------------------ | --------------------------------------------------- |
| Deployment root          | `F:\ChatbookDeployment\m5-1-c4-controlled`          |
| Schema-v3 source         | `source\chatbook-business-v3.db`                    |
| Verified backup          | `backup\chatbook-business-v3.backup.db`             |
| Retained restore proof   | `restore-proof\chatbook-business-v3.restore.db`     |
| Reserved v4 target       | `target\chatbook-business-v4.db` — absent by design |
| Evidence and manifests   | `evidence`                                          |
| Runtime logs             | `logs`                                              |
| Non-secret configuration | `config`                                            |
| Restricted credentials   | `secrets\staging-credentials.json`                  |
| Runtime controls         | `controls`                                          |
| Recovery release         | `recovery`                                          |

`chatbook/deployment_preparation.py` and the `chatbook-c4p` console command provide three operations:
`prepare` creates a new controlled environment only when the root does not already exist, and
`verify` performs read-only verification plus the rollback-only writer-gate probe of an existing
prepared environment. `harden` refreshes only the release manifest, server-owned runtime selector,
fixed-path controls, and sanitized evidence after verifying the existing source, backup, and restore
proof. All refuse a root inside the repository and refuse the development database path.
Preparation and hardening do not call the canonical migration or C4A rehearsal factory.

The source was initialized by the normal `chatbook.database.Database` schema-v3 path, with identity,
membership, and sessions created through `AuthService` and financial state created through
`AccountingEngine` and the existing BUSINESS service boundary. It contains only BUSINESS owners.

## 2. Exact database path

The future controlled C4 source is:

`F:\ChatbookDeployment\m5-1-c4-controlled\source\chatbook-business-v3.db`

The repository development database remained at `F:\Projects\chatbook\chatbook.db`. Its SHA-256
stayed
`d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`; it was not opened for
mutation or upgraded.

C4P2 initially verified the previously recorded source SHA-256
`7532962f3d3e752655946b1ec629b219e11d4f63de618dee0baa0c6e1e03e936`. A later live
authentication check created one ephemeral `auth_sessions` row. The verifier detected the changed
content and stopped. With every process stopped, the source was restored from its retained verified
schema-v3 backup. The current source and backup SHA-256 is
`de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71`; the deterministic content
fingerprint and every financial count remain unchanged. The changed copy is retained in the
restricted backup area, the recovery is recorded in `evidence\c4p2-source-recovery.json`, and source
approval remains `REQUIRES_OPERATOR_DECISION`.

## 3. Exact schema version

The source, final backup, and restore proof all have `PRAGMA user_version = 3`. The reserved v4
target does not exist. No schema-v4 database was created under the controlled deployment root or
selected by the normal runtime. Existing C3/C4A regression tests continued to use only their own
disposable temporary copies.

## 4. Database fingerprint and representative state

| Measure                            |                                                             Result |
| ---------------------------------- | -----------------------------------------------------------------: |
| Source bytes                       |                                                            475,136 |
| Current source/backup SHA-256      | `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` |
| Historical pre-C4P2 source SHA-256 | `7532962f3d3e752655946b1ec629b219e11d4f63de618dee0baa0c6e1e03e936` |
| Deterministic content fingerprint  | `bb2574b83dcd0855ef5b52150905e256f90208075e1c5e3a6623e2fc7cfe12c2` |
| Schema fingerprint                 | `dfcb38279bee54d4bfb249ed938b74bd538231c9acb610316a407a7e5ef1658a` |
| Integrity check                    |                                                               `ok` |
| Foreign-key violations             |                                                                  0 |
| Organizations / ledger books       |                                                              2 / 2 |
| Currencies and precision           |                                                   BDT / 2; USD / 3 |
| Users / memberships                |                                                             6 / 10 |
| Accounts / accounting periods      |                                                              8 / 4 |
| Proposals / lines                  |                                                            14 / 28 |
| Validations / confirmations        |                                                            12 / 10 |
| Idempotency receipts               |                                                                 16 |
| Journal entries / lines            |                                                             8 / 16 |
| Projects / documents               |                                                              2 / 2 |
| Audit events                       |                                          150, maximum sequence 150 |

The seeded source covers every initial role, active and inactive accounts, open and locked periods,
proposal lifecycle states, posting, idempotent retries, reversals, projects, document metadata,
audit history, and ledger-derived reports. Trial balance, ledger, period-report, and project-report
fingerprints are recorded per organization in `evidence\source-preflight-manifest.json`. The
generator used only already-supported deterministic BUSINESS scenarios; it introduced no new
accounting classification or policy.

## 5. Runtime topology

| Component           | Entrypoint and configuration                                                                                 | Database access                                                  |
| ------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| Backend             | `chatbook-api` / `chatbook.api.main:run`; server-owned path, mode, schema, release ID, host, and port        | Direct, through the existing API/application/accounting boundary |
| Frontend            | `npm run start` from `frontend`; `CHATBOOK_API_URL`                                                          | None; HTTP client only                                           |
| Trusted CLI         | `chatbook` / `chatbook.cli:main`; mode from deployment environment, optional exact-path `--db` compatibility | Direct, through `AccountingEngine`                               |
| Runtime inspection  | `chatbook-runtime` / `chatbook.runtime:main`                                                                 | Read-only validation and sanitized identity evidence             |
| Preparation control | `chatbook-c4p` / `chatbook.deployment_preparation:main`                                                      | Prepares, hardens, or verifies only the dedicated staging root   |

Normal startup resolves one explicit `RuntimeConfiguration`. `organization-v3` preserves the
existing `Database` behavior. `canonical-v4` requires schema 4, an explicit access mode, an existing
absolute target distinct from repository `chatbook.db`, and an immutable release SHA; it opens
`CanonicalDatabase` only after read-only integrity, foreign-key, owner-scope, and canonical-mapping
checks. `read-only` opens SQLite in read-only/query-only mode and rejects writes before a transaction.
`AuthService` and
`AccountingEngine` use the same selection. The repository contains no financial background worker
or scheduler. Normal v4 selection is implemented without using the rehearsal flag, but it is not
activated in this environment.

## 6. Writer inventory

Known financial writers are authenticated FastAPI requests and the trusted local CLI. Both converge
on the same deterministic accounting engine and existing transaction boundary. The frontend has no
SQLite access. The preparation command creates staging data through those application/domain
services and is not a second production write path.

Raw SQLite administration, unreviewed scripts, Windows services, scheduled tasks, and file handles
cannot be excluded from repository inspection alone. An elevated operator must inventory them at
the maintenance window and prohibit ad hoc CLI/raw-database access in the signed change record.

## 7. Stop, drain, quiescence, and restart controls

The environment contains `Start-Backend.ps1`, `Start-Frontend.ps1`, `Stop-Application.ps1`,
`Verify-Quiescence.ps1`, and `OPERATIONS.md`. The backend and frontend controls were live-rehearsed
on ports 8100 and 3100. Backend health and authenticated reads succeeded; the frontend login route
returned HTTP 200. The stop control terminates the full spawned process tree, and the final rehearsal
left no listener or PID file.

`Verify-Quiescence.ps1` checks configured listeners and PID files, opens the database, acquires
`BEGIN IMMEDIATE`, proves a controlled competing writer receives `database is locked`, and rolls
back without mutation. A graceful request drain, elevated service/task/file-handle inventory, and
enforcement against raw administrator writes remain `REQUIRES_OPERATOR_DECISION`. During actual C4,
traffic must first be rejected externally, the approved drain interval must elapse, all writers must
be stopped, and the gate must be reacquired before the fresh backup.

Restart order for the current schema-v3 rehearsal is backend health first, then frontend. The
controls validate and record the exact path, mode, schema, access mode, release identity, and configuration
fingerprint before starting. They allow only the fixed controlled v3 source or fixed reserved v4
target in read-only mode, never migrate or create a v4 database, and refuse the current v3 restart if the reserved v4
target exists. No v4 restart or writer resumption is permitted until the C4 migration, read-only
acceptance, and explicit release-owner gate have succeeded.

## 8. Release identity

The checkout has no usable Git metadata, so no commit hash is claimed. Release identity is a SHA-256
over sorted repository-relative release-file records, including source, migrations, dependency lock
files, tests, and frontend sources.

| Identity                       | Value                                                              |
| ------------------------------ | ------------------------------------------------------------------ |
| Schema-v3 source release ID    | `672e551c8617a1e5371d4a5b31350fce700189f02c75457fafb9519241e43bde` |
| Compatible v3 recovery archive | `recovery\chatbook-v3-release-672e551c8617a1e5.zip`                |
| Recovery archive SHA-256       | `46eae5724488a8e9ddcf08976320678967658f9ad6abd163c2b23896b539e40d` |
| Recovery archive bytes         | 295,734                                                            |
| Frontend build ID              | `oXmnRkL-VIVFLjLOfejJm`                                            |
| v4 migration artifact hash     | `6c80eaebb419b6affe7df837c9391cc64ee6146d1a6a92306985b398275f68e9` |
| Python / SQLite                | CPython 3.14.3 / SQLite 3.50.4                                     |
| Chatbooks / FastAPI / Uvicorn  | 0.1.0 / 0.141.1 / 0.54.0                                           |

The exact package versions and every hashed file are in `evidence\release-manifest.json`. Earlier
manifests and recovery archives created before the process-tree stop correction and C4P2 runtime
hardening are retained as historical evidence. The final identity above covers the hardened
controls and normal runtime selection.

## 9. Backup and recovery setup

The final backup was made with SQLite's backup API after runtime writers were stopped. It was copied
to a separate restore-proof path and opened for complete preflight and report-fingerprint
comparison.

| Measure                   | Result                                                             |
| ------------------------- | ------------------------------------------------------------------ |
| Backup SHA-256            | `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` |
| Restore SHA-256           | `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` |
| Backup / restore bytes    | 475,136 / 475,136                                                  |
| Content parity            | exact content fingerprint and report fingerprints                  |
| Backup verification time  | 0.2400739 seconds                                                  |
| Restore verification time | 0.028415900000254624 seconds                                       |
| Drive free / total bytes  | 506,828,025,856 / 544,432,189,440                                  |

The current backup is a preparation proof. Actual C4 still requires a new backup under the approved
writer gate, a new restore test, and manifest comparison immediately before migration. Before v4
commit, transaction rollback applies. After v4 commit but before any v4 financial write, only the
verified v3 backup and compatible v3 recovery release may be used. After any v4 financial write, an
ordinary v3 restore is forbidden; writers must stop and audited forward recovery must preserve new
history.

## 10. Artifact protection status

Windows ACL evidence records the owner as `DESKTOP-0D25D0C\User` and allows only that user,
`NT AUTHORITY\SYSTEM`, and `BUILTIN\Administrators`, each with full control. The deployment root,
source, backup, and credentials file have protected ACLs. Credentials are stored separately and are
excluded from evidence output.

This proves a restricted local ACL on the inspected host. It does not prove encryption at rest,
off-host recovery, a retention/destruction owner, Windows access auditing, or organizational
separation of duties. Those remain `REQUIRES_OPERATOR_DECISION`.

## 11. Monitoring status

`config\monitoring-plan.json` defines sources and invariant thresholds for schema version, integrity,
foreign keys, idempotency disagreement, audit-sidecar coverage, ledger/reconciliation equality,
report equality, and migration errors. It also identifies application-error, SQLite lock/write,
latency, and protected-artifact signals whose numerical thresholds require observed baselines and
operator approval.

Every signal still needs a named owner, escalation route, and observation duration. Windows security
auditing and the collection/alert mechanism are not configured. Monitoring is therefore
`DEFINED_AWAITING_OPERATOR_ASSIGNMENT`, not release-ready.

## 12. Canary definition

A controlled BUSINESS expense-and-cash scenario is defined but was not executed:

- organization `0ba470aa-e553-4303-b0b7-c4615852cc4d`;
- actor `f6d1dbd1-b80d-439e-ab24-c9afd59874e8`;
- debit expense account `e9e3427d-73d7-44c6-a23b-dd4b5bf8fec9`;
- credit cash account `7aa504b2-578b-417d-b64e-6f8409300211`;
- amount 12,345 BDT minor units on 2026-09-30;
- project `9992bf14-af4d-445f-aa3a-65894a38104f` and document
  `47b2af28-c66d-4402-aee9-c23ecadc0750`;
- distinct confirmation and posting keys `c4-canary-confirm-v1` and `c4-canary-post-v1`;
- expected journal effect: debit expense and credit cash by 12,345, balanced exactly once;
- expected report effect: expense net debit +12,345 and cash net debit -12,345; and
- reversal reason `Reverse controlled C4 canary after verification`, preserving both entries and
  returning their net effect to zero.

The input reuses an existing valid BUSINESS scenario and carries no new accounting classification.
Its status is `DEFINED_NOT_EXECUTED`. Accounting/data approval and release-owner authorization are
required before future execution.

## 13. Unresolved operator decisions

- Name the release owner, migration operator, application operator, accounting/data reviewer, and
  incident recorder; obtain all required signatures.
- Decide whether this staging source is the approved C4 source or replace it with an approved real
  deployment source without relabeling staging evidence as production.
- Review and approve the exact C4P2 runtime configuration and immutable release identity for the
  future C4 record; keep normal schema-v4 selection disabled until post-migration acceptance.
- Establish external traffic rejection, graceful request drain, elevated Windows
  service/task/file-handle inventory, and enforcement against ad hoc writer access.
- Approve encryption, off-host recovery, backup retention/destruction ownership, access auditing,
  and separation of duties.
- Measure migration peak space and representative migration duration on the approved source; approve
  the maintenance window and safety margin.
- Assign monitoring owners, thresholds that need a baseline, escalation paths, and observation
  durations; configure the actual collection and alerting mechanism.
- Approve the canary input and its accounting classification, then authorize it only after a future
  read-only v4 acceptance gate.

These are deployment and human approval decisions. No accounting rule was inferred to close them.

## 14. Verification results

| Verification                 | Result                                                                                                |
| ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| Original C4P unit tests      | 2 passed; separation, refusal, secret exclusion, and unchanged-development-DB checks                  |
| Focused C4P2 tests           | 5 passed; runtime matrix, adapter pairing, BUSINESS parity, evidence redaction, and control hardening |
| Live schema-v3 backend       | Hardened startup selected exact v3 source/release; health and read-only accounting checks passed      |
| Live frontend                | Hardened start required the live backend; `/login` returned HTTP 200                                  |
| Runtime shutdown             | Full backend/frontend process trees stopped; no listeners or PID files remained                       |
| Writer gate                  | Final verifier acquired the gate, blocked the controlled competitor, and rolled back without mutation |
| Database verification        | Schema 3, integrity `ok`, zero foreign-key violations, BUSINESS only                                  |
| Source recovery disclosure   | Auth-session-only change detected; verified backup restored; source reapproval remains required       |
| Backup/restore               | Exact deterministic content and report parity passed                                                  |
| v4 target                    | Absent                                                                                                |
| Backend suite                | 95 tests passed                                                                                       |
| Type checking                | mypy passed for 30 source files                                                                       |
| Python lint/format           | Ruff passed; 102 files formatted                                                                      |
| Frontend                     | 10 tests, TypeScript, ESLint, Prettier, and optimized build passed                                    |
| Safety/source-boundary scans | Passed                                                                                                |
| Documentation/link checks    | Passed after C4P2 documentation update                                                                |

The first sandboxed frontend test/build attempt encountered a Windows process-spawn permission
error; the same commands passed in the permitted host environment. No financial behavior changed to
obtain that result.

One earlier sandboxed C4P verifier call failed to observe native SQLite contention because the
sandbox filesystem broker did not preserve the host lock behavior. Host verification then proved
the expected `database is locked` result. C4P2 repeated the gate after the recorded source recovery:
the controlled competitor was blocked, the transaction rolled back, and the final restored source
hash remained stable. The writer gate must still be verified on the deployment host during C4; a
staging result is not production lock evidence.

## 15. C4 execution status

M5.1-C4 was **not executed**. No schema-v3 to schema-v4 migration ran against the controlled source
or repository database, no controlled v4 target was created, no canary ran, no v4 writer resumed, no
PERSONAL data was created, and `chatbook.db` was not modified. Existing regression tests exercised
only disposable temporary migration fixtures. All controlled runtime verification used schema v3
and ended with writers stopped.

Evidence remains separated as follows:

| Evidence class                   | Meaning                                                                                                                                                                  |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Synthetic C4A                    | Disposable representative fixture and recovery drills                                                                                                                    |
| C3 rehearsal                     | Disposable-copy canonical migration and parity evidence                                                                                                                  |
| C4P/C4P2 engineering preparation | Persistent controlled staging source, explicit normal runtime selection, hardened controls, release identity, backup/restore proof, and live schema-v3 runtime rehearsal |
| Future real C4                   | Absent; must be created only by the separately authorized runbook execution                                                                                              |

## Current C4 blocker table

| Blocker                                                       | Status             | Evidence                                                                                                | Remaining action                                                                                  |
| ------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Canonical migration/reconciliation and BUSINESS parity        | CLOSED             | C3/C4A disposable-copy migration, rollback, reconciliation, and parity evidence is green.               | Preserve it and rerun the release gate for the exact C4 release.                                  |
| Complete regression and source-boundary gate                  | CLOSED             | C4P2 reports the backend, typing, lint, format, frontend, and safety gates green.                       | Rerun against the exact authorized release.                                                       |
| Normal schema-v4 runtime selection                            | CLOSED             | C4P2 proves server-controlled mode/schema/path/access/release selection and read-only v4 acceptance.    | Keep disabled until a successful migration and read-only acceptance.                              |
| Approved exact C4 source                                      | PARTIALLY PREPARED | Exact staging identity, verified recovery, and unchanged financial content exist.                       | Named release and accounting/data owners must approve the rebaseline or nominate another source.  |
| Host and writer inventory                                     | PARTIALLY PREPARED | Repository and staging runtime/writer paths are documented.                                             | Complete elevated service/task/file-handle and ad hoc writer inventory on the intended host.      |
| External traffic rejection and graceful drain                 | BLOCKED            | The runbook defines the gate, but no deployment mechanism or live drain proof exists.                   | Implement, rehearse, measure, and approve rejection and drain.                                    |
| Writer shutdown/resumption                                    | PARTIALLY PREPARED | Process-tree stop, writer exclusion, read-only acceptance, and ordered resumption rules were rehearsed. | Bind them to approved host inventory and operators; repeat under maintenance.                     |
| Protected backup/restore paths                                | PARTIALLY PREPARED | Separate restricted staging paths and exact restore parity exist.                                       | Approve exact paths and repeat a fresh backup/restore under the actual writer gate.               |
| Encryption/off-host recovery/retention/access auditing/duties | BLOCKED            | Requirements and local ACL evidence exist; operational controls and ownership do not.                   | Implement and approve the complete protection and recovery policy.                                |
| Exact v3 recovery and v4 release identity                     | PARTIALLY PREPARED | Deterministic release, migration, frontend, recovery, and configuration identities exist.               | Human reviewers must approve and reverify the exact artifacts in the final change record.         |
| Intended-host capacity and maintenance window                 | PARTIALLY PREPARED | Synthetic and staging sizes, timings, and free space were measured.                                     | Measure on approved data/host and approve margin, downtime, and window.                           |
| Monitoring and observation                                    | PARTIALLY PREPARED | Signals, invariant thresholds, and stop decisions are defined.                                          | Configure collection/alerts and approve owners, thresholds, escalation, and observation duration. |
| Canary inputs and approval                                    | PARTIALLY PREPARED | The scenario and expected effects are defined as `DEFINED_NOT_EXECUTED`.                                | Obtain accounting/data and release-owner approval after read-only acceptance.                     |
| Named owners and signatures                                   | BLOCKED            | Roles exist; every checklist box and signer field remains open.                                         | Assign named people and complete every signature and evidence reference.                          |
| Final preflight and go/no-go                                  | BLOCKED            | No signed final evidence set or authorization exists.                                                   | Close prerequisites, run the fresh preflight, reconcile manifests, and obtain signed go/no-go.    |
| PERSONAL and other non-C4 work                                | DEFERRED           | C4 is BUSINESS-only; no PERSONAL data or behavior was created.                                          | Keep outside C4.                                                                                  |

See the
[`M5_1_C4P_RUNTIME_SELECTION_REPORT.md`](M5_1_C4P_RUNTIME_SELECTION_REPORT.md) for the C4P2 design,
startup matrix, complete verification, and controlled-source recovery disclosure.
The authoritative current reconciliation is
[`M5_1_C4P3_FINAL_READINESS_REPORT.md`](M5_1_C4P3_FINAL_READINESS_REPORT.md).

**NOT READY FOR FINAL PREFLIGHT**

M5.1-C4P/C4P2 engineering preparation is complete. C4 remains `NO-GO`, unexecuted, and unauthorized
while the deployment-specific and human gates above remain open.
