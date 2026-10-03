# M5.1-C4 BUSINESS cutover preflight blocker report

**Date:** 2026-09-28  
**Host inspected:** `DESKTOP-0D25D0C`  
**Workspace inspected:** `F:\Projects\chatbook`  
**Historical preflight status:** **NO-GO — blocked before backup or cutover**  
**Current C4P5 state:** **NOT READY FOR FINAL PREFLIGHT**  
**Scope:** Actual-environment preflight only; no schema migration, canary, or writer resumption

This report preserves the original actual-environment preflight evidence. Sections 1–9 describe the
state observed before C4P and C4P2. The current post-C4P2 classification is in section 10 and
[`M5_1_C4P3_FINAL_READINESS_REPORT.md`](M5_1_C4P3_FINAL_READINESS_REPORT.md).

## 1. Historical actual-preflight decision

M5.1-C4 was not executed. The inspected environment does not contain an approved schema-v3 BUSINESS
source database or the deployment, recovery, protection, monitoring, canary, and sign-off controls
required by the
[`M5_1_C4_CUTOVER_RUNBOOK.md`](M5_1_C4_CUTOVER_RUNBOOK.md) and
[`M5_1_C4_RELEASE_CHECKLIST.md`](M5_1_C4_RELEASE_CHECKLIST.md).

The preflight stopped before maintenance announcement, writer shutdown, backup creation, restore,
migration, schema-v4 commit, read-only acceptance, canary, or writer resumption. No rollback branch
was entered because no cutover action occurred.

## 2. Historical evidence classification

| Evidence class                  | What exists                                                                                                                 | What it proves                                                 |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Synthetic C4A evidence          | Three-organization disposable fixture and recovery drills documented in the C4A report                                      | The tooling and controls worked on generated local data        |
| C3 rehearsal evidence           | Disposable-copy schema-v3 to schema-v4 migrations and parity tests                                                          | Canonical reconstruction can work on controlled fixtures       |
| Actual local preflight evidence | Read-only inspection of this workspace, host metadata, process metadata, source controls, checklist, and candidate database | The current machine does not satisfy the real C4 prerequisites |
| Real deployment evidence        | **Absent**                                                                                                                  | No production/shared BUSINESS cutover claim can be made        |

Synthetic and rehearsal evidence was not treated as production evidence.

## 3. Candidate database inspection

The workspace contains one application-named SQLite file, `F:\Projects\chatbook\chatbook.db`. It was
opened read-only with SQLite query-only mode. The `.mypy_cache\3.12\cache.db` file was identified as
a tool cache and excluded.

| Property                                   | Measured result                                                    |
| ------------------------------------------ | ------------------------------------------------------------------ |
| File size                                  | 323,584 bytes                                                      |
| SHA-256                                    | `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884` |
| SQLite runtime                             | 3.50.4                                                             |
| `PRAGMA user_version`                      | **2**                                                              |
| Journal mode                               | `delete`                                                           |
| `PRAGMA integrity_check`                   | `ok`                                                               |
| Foreign-key violations                     | 0                                                                  |
| Users / organizations / accounts / periods | 0 / 0 / 0 / 0                                                      |
| Proposals / validations / confirmations    | 0 / 0 / 0                                                          |
| Journal entries / journal lines            | 0 / 0                                                              |
| Receipts / audit events                    | 0 / 0                                                              |

This is an empty schema-v2 development database. It is not schema v3, contains no BUSINESS data,
has no schema-v3 LedgerBook mapping, and has no approval record identifying it as the C4 source. It
therefore cannot be used for the schema-v3 to schema-v4 BUSINESS cutover.

No other application SQLite source, approved deployment-copy path, verified backup, restored proof,
schema-v4 target, C3 report, or protected C4 evidence artifact was found outside caches, build output,
and test-temporary directories in the workspace.

## 4. Runtime and writer topology

Observed at preflight time:

- no matching Python, Uvicorn, Node, npm, or pnpm application process was running;
- no listener was present on ports 3000, 3001, 8000, or 8001;
- no `CHATBOOK_*`, `DATABASE_*`, `SQLITE_*`, or `UVICORN_*` environment variable name was present;
- no Docker, Compose, systemd, Kubernetes, hosted-service, or other deployment definition was found;
  the only environment template found was `frontend/.env.example`; and
- Windows service and scheduled-task inventory was unavailable to this session with `CimException`.

Zero observed processes is not proof that all deployment writers are known or controllable. There is
no environment-specific inventory of API pools, local CLI users, administrative scripts,
background jobs, scheduled tasks, file handles, or ad hoc database clients. There are no approved
stop, drain, connection-close, competing-writer-probe, restart, or staged writer-resumption commands.

The repository source contains synthetic shutdown/drain measurements in `cutover_readiness.py`, but
no normal runtime maintenance response or deployment control plane. Those synthetic calls are not
evidence that a real application topology can be quiesced.

## 5. Release and schema-v4 selection at original preflight

At the original preflight, normal application construction used `Database` and schema v3. Schema v4 was selected
only through `canonical_rehearsal=True` or `AccountingEngine.for_canonical_rehearsal`, both explicitly
documented as rehearsal-only paths.

No reviewed normal-runtime schema-v4 release-selection mechanism existed then. The workspace had package
version `0.1.0`, but no `.git` metadata or immutable release artifact was present, so the exact
release identity and exact schema-v3 recovery release cannot be established from this checkout.

## 6. Backup, restore, and artifact protection

The repository contains generic SQLite backup/restore and migration-rehearsal code, but the actual
deployment values required by the runbook are absent:

- no approved source path;
- no restricted backup destination;
- no separately retained restore-proof destination;
- no new schema-v4 target path;
- no retention or destruction owner;
- no approved encryption or off-host recovery arrangement; and
- no environment-specific restore and release-selection commands.

The candidate `chatbook.db` inherits access rules rather than using a protected ACL. `Authenticated
Users` have modify access, and the file has the `Archive` attribute without the `Encrypted`
attribute. This is not acceptable evidence of the restricted artifact handling required by C4.

No backup was created because the source is not an approved schema-v3 deployment database. Creating
one would not close the source-identity or operational-control gates.

## 7. Capacity evidence

The local `F:` drive reported:

| Measure             |                      Result |
| ------------------- | --------------------------: |
| Free bytes          |             506,913,583,104 |
| Total bytes         |             544,432,189,440 |
| Workspace path type |   Local drive path, not UNC |
| Filesystem type     | Unavailable to this session |

This is host-level development information only. There is no approved deployment source size,
target path, filesystem, concurrent growth estimate, measured deployment migration peak, or
operator-approved safety margin. The capacity checklist therefore remains open even though the
development drive has substantial free space.

## 8. Monitoring, canary, and ownership

No monitoring configuration, signal source, threshold, alert, observation duration, owner, or
escalation path was found for schema mismatch, financial command errors, SQLite locks, idempotency,
audit sidecars, ledger invariants, report reconciliation, migration failures, latency, or artifact
access.

No canary organization, actor, accounts, date, amount, project/document context, business purpose,
reversal reason, confirmation key, or posting key has been selected or approved.

The release checklist has **50 unchecked items**. The engineering signer, product/operator signer,
accounting/data signer, release owner, evidence references, decision timestamps, and maintenance
window are blank. No change record with named release, migration, application, accounting/data, or
incident owners was found.

## 9. Repository regression evidence

The requested Python backend/API/CLI/migration suite was run against temporary test databases, not
against `chatbook.db`.

- `python -m pytest -q` could not run because pytest is not installed; the repository documents
  `unittest` as its test runner.
- Initial sandboxed unittest attempts could not create temporary SQLite files and were discarded as
  environment failures.
- The final permission-enabled `python -m unittest discover -q` run executed 88 tests in 31.044
  seconds and failed with **one error**.

The failing test was
`tests.test_m5_1_c3.M51C3Tests.test_failure_injection_rolls_back_every_stage_and_never_changes_source`
at failure stage `reconciliation_mismatch`. The injection selects the first positive debit by random
ID ordering and adds one. In this run it selected the maximum supported debit and SQLite raised the
line-limit `CHECK` constraint before the intended `migration_reconciliation` error. This means the
current complete regression gate is not green and the failure-injection evidence is nondeterministic.
It had to be corrected and the full suite rerun before C4 approval. This preflight did not modify
the migration or test code.

The earlier C4A report's 88-test pass remains historical synthetic evidence. It does not replace a
passing release-candidate run in the actual C4 change record.

The regression was subsequently remediated on 2026-09-28 without changing accounting constraints or
normal migration behavior. The focused test passed once and then passed ten additional fresh runs;
the complete C3/C4A suite passed 11 tests; and the complete backend release-candidate suite passed
all 88 tests. Static, formatting, safety-boundary, and documentation gates also passed. See
[`M5_1_C4A_REGRESSION_REMEDIATION_REPORT.md`](M5_1_C4A_REGRESSION_REMEDIATION_REPORT.md). This closes
the code-regression blocker only and does not supply any missing deployment evidence or approval.

### Historical checklist comparison

This table records the original preflight observation. It is not the current C4P3 classification.

| Required C4 item                             | Actual observation                                                                | Result      |
| -------------------------------------------- | --------------------------------------------------------------------------------- | ----------- |
| Approved schema-v3 source                    | Only an empty, unapproved schema-v2 `chatbook.db` exists                          | **BLOCKED** |
| Application/runtime topology                 | No deployment definition; service/task inventory unavailable                      | **BLOCKED** |
| Complete writer inventory and stop procedure | No approved inventory, maintenance response, drain, handle, or restart controls   | **BLOCKED** |
| Protected backup destination and restore     | Generic code only; no approved paths, retention, encryption, or off-host recovery | **BLOCKED** |
| Intended-host disk measurement               | Development drive measured; no approved source/target or margin                   | **BLOCKED** |
| Exact recovery release                       | No immutable release identity or reviewed v3 recovery artifact                    | **BLOCKED** |
| Artifact permissions                         | Candidate database inherits broad modify access; no protected evidence directory  | **BLOCKED** |
| Monitoring and thresholds                    | No implementation, values, owners, observation duration, or escalation            | **BLOCKED** |
| Approved canary inputs                       | None recorded                                                                     | **BLOCKED** |
| Named owners/signatures                      | All signer fields blank; 50 checklist items unchecked                             | **BLOCKED** |
| Normal schema-v4 runtime selection           | Rehearsal-only selection exists; normal v4 release path absent                    | **BLOCKED** |
| Complete regression suite                    | 88 tests passed after deterministic fault-injection remediation                   | **CLOSED**  |
| Deployment-specific preflight manifest       | Not run because no approved schema-v3 source exists                               | **BLOCKED** |

### Historical exact blocker list

1. Identify and approve the exact closed schema-v3 BUSINESS database, its owner, purpose, and
   immutable source hash. The current `chatbook.db` is schema v2 and empty.
2. Identify the deployment host and complete the process, service, scheduled-task, background-job,
   local CLI, administrative writer, and open-file-handle inventory.
3. Implement and approve the actual maintenance response, request drain, writer stop, connection
   close, competing-writer proof, restart, and staged writer-resumption commands.
4. Build and review normal-runtime schema-v4 selection that does not expose or reuse a rehearsal
   flag as a client capability. C4P2 later closed this engineering blocker.
5. Produce immutable release identifiers and verify both the C4 release and exact schema-v3 recovery
   release.
6. Approve distinct source, backup, restore-proof, and v4 target paths with restricted ACLs,
   encryption where required, retention, destruction, and off-host recovery controls.
7. Rehearse backup and restore on an approved protected copy of the actual schema-v3 source.
8. Measure source size, migration peak, backup/restore duration, drain time, migration time, read-only
   acceptance time, and total maintenance window on the intended host/filesystem; approve a safety
   margin and downtime window.
9. Define every required monitoring source, threshold, owner, alert, escalation route, and
   observation duration.
10. Select and approve complete canary and compensating-reversal inputs without inventing accounting
    classification.
11. Complete all engineering, product/operator, accounting/data, incident, and final release-owner
    fields and attach evidence references to every checklist item.
12. Only after blockers 1–11 close, run the deployment-specific source/backup/restore preflight and
    obtain the explicit go/no-go signatures required by the runbook.

### Actions deliberately not taken

- No maintenance announcement was issued for a nonexistent approved deployment window.
- No process or writer was stopped.
- No source database was opened for writing.
- No backup, restore, or schema-v4 target was created.
- No migration command was run.
- No schema version or application selection changed.
- No API/CLI canary or financial mutation was performed.
- No rollback or forward-recovery action was needed.
- No PERSONAL owner, row, feature, or M5.2 implementation was introduced.

### Historical documentation and preservation verification

- The blocker report, readiness report, release checklist, and runbook pass Prettier formatting.
- 201 local Markdown links across 57 repository Markdown files pass when test/build/dependency
  directories are excluded.
- The release checklist still contains exactly 50 unchecked items.
- The candidate database remains 323,584 bytes at schema version 2 with the same SHA-256 recorded
  above, `integrity_check = ok`, and zero foreign-key violations.
- No application code, schema, migration, endpoint, PERSONAL model, or runtime configuration changed.

### Historical exit state

M5.1-C4 remains **blocked and incomplete**. The existing schema-v3 to schema-v4 cutover procedure is
still valid as a future runbook, but it cannot be executed until the blocker list is closed with real
deployment evidence and signed approvals. The inspected `chatbook.db` remains schema v2 and was not
modified by this preflight.

### Repeated preflight confirmation

The repository and host were inspected again on 2026-09-28 after the C4 execution request was
reissued. The no-go evidence is unchanged:

- `chatbook.db` is still the only application database, remains 323,584 bytes at schema version 2,
  has SHA-256 `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`,
  reports `integrity_check = ok` and zero foreign-key violations, and contains zero rows in every
  application table;
- no Chatbooks, FastAPI, Uvicorn, Next.js, or npm process and no listener on ports 3000, 3001, 8000,
  or 8001 was found, while Windows service and scheduled-task inventory remained unavailable due to
  host access denial;
- no deployment or protected backup/restore artifact definition and no relevant runtime environment
  variable was found;
- the database ACL still inherits broad modify access, including for Authenticated Users;
- all 50 checklist items remain unchecked; and
- `F:` reported 506,913,550,336 free bytes, which remains development-host information rather than
  approved deployment capacity evidence.

No source, application, schema, or runtime condition changed that could close a deployment blocker.
At the time of this repeated preflight, the release-candidate regression remained open. It was later
remediated as recorded in the repository regression evidence above; that code-only remediation does
not change the C4 no-go decision. No backup, migration, canary, writer-control, rollback, or PERSONAL
operation was performed during the repeated preflight.

## 10. Subsequent C4P/C4P2 preparation and current C4P3 status

M5.1-C4P subsequently created a separate controlled staging environment at
`F:\ChatbookDeployment\m5-1-c4-controlled`. This new evidence does not overwrite the actual
preflight above and does not turn the repository development database into a deployment source.

C4P prepared a normal schema-v3 BUSINESS source, restricted local paths, start/stop/quiescence
controls, deterministic release and recovery identity, a verified backup/restore proof, monitoring
definitions, and an unexecuted canary. C4P2 then implemented and tested normal server-controlled
schema-v4 selection and explicit read-only acceptance. The dedicated source remains schema v3, the
selector remains disabled, and the reserved v4 target remains absent. Full details are in
[`M5_1_C4P_DEPLOYMENT_PREPARATION_REPORT.md`](M5_1_C4P_DEPLOYMENT_PREPARATION_REPORT.md).

The current classification below supersedes the original blocker labels without changing their
historical measurements:

| Blocker                                                               | Current status     | Current evidence                                                                                             | Exact remaining action                                                                                   |
| --------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| Canonical migration/reconciliation and BUSINESS parity                | CLOSED             | C3/C4A disposable-copy migration, reconciliation, rollback, parity, and failure-injection evidence is green. | Preserve the implementation and rerun the release gate for the exact C4 release.                         |
| Complete regression and source-boundary gate                          | CLOSED             | C4P2 reports 95 backend tests plus Mypy, Ruff, formatting, frontend, and safety scans green.                 | Rerun against the exact authorized release.                                                              |
| Normal server-controlled schema-v4 selection                          | CLOSED             | C4P2 proves exact server-owned mode/schema/path/access/release selection and read-only v4 acceptance.        | Keep disabled until post-migration read-only acceptance under C4.                                        |
| Approved exact C4 source                                              | PARTIALLY PREPARED | The staging source has exact hashes, integrity, recovery, and unchanged financial counts.                    | Named release and accounting/data owners must approve the rebaseline or nominate another source.         |
| Intended-host and writer inventory                                    | PARTIALLY PREPARED | Repository and staging paths are inventoried.                                                                | Complete and approve elevated service/task/file-handle and ad hoc writer inventory on the intended host. |
| External traffic rejection and graceful drain                         | BLOCKED            | Requirements are documented; no deployment mechanism or live drain evidence exists.                          | Implement, rehearse, measure, and approve traffic rejection and zero-request drain.                      |
| Writer shutdown/resumption                                            | PARTIALLY PREPARED | C4P process-tree controls, writer gate, and ordered resumption rules were rehearsed in staging.              | Bind them to the approved host and operators; repeat under the maintenance gate.                         |
| Protected backup/restore paths                                        | PARTIALLY PREPARED | Separate restricted staging paths and exact restore parity exist.                                            | Approve final paths and create/restore-test a fresh maintenance-window backup.                           |
| Encryption, off-host recovery, retention, access auditing, and duties | BLOCKED            | Requirements and local ACL evidence exist; the operational controls do not.                                  | Implement and approve all controls, owners, retention, auditing, and off-host recovery.                  |
| Exact v3 recovery and v4 release identity                             | PARTIALLY PREPARED | C4P2 records deterministic recovery/release artifacts and configuration identity.                            | Human reviewers must approve and reverify the exact artifacts in the C4 record.                          |
| Intended-host capacity and maintenance window                         | PARTIALLY PREPARED | Synthetic and staging measurements exist.                                                                    | Measure on approved data/host and approve disk margin, downtime, and window.                             |
| Monitoring and observation                                            | PARTIALLY PREPARED | Signals and stop thresholds are defined.                                                                     | Configure collection/alerts and approve owners, thresholds, escalation, and observation duration.        |
| Canary inputs and approval                                            | PARTIALLY PREPARED | A complete scenario is defined but not executed.                                                             | Obtain accounting/data and release-owner approval after read-only acceptance.                            |
| Named owners and signatures                                           | BLOCKED            | Roles exist; all 50 checklist boxes and signer fields remain open.                                           | Assign named people and complete every required signature and evidence reference.                        |
| Final deployment-specific preflight and go/no-go                      | BLOCKED            | No signed final evidence set or authorization exists.                                                        | Close every prerequisite, run the fresh preflight, reconcile manifests, and obtain signed go/no-go.      |
| PERSONAL and other non-C4 work                                        | DEFERRED           | C4 is BUSINESS-only and C4P2 rejects PERSONAL selection.                                                     | Keep outside C4.                                                                                         |

All 50 release-checklist items remain unchecked. The complete evidence and exact actions are in
[`M5_1_C4P3_FINAL_READINESS_REPORT.md`](M5_1_C4P3_FINAL_READINESS_REPORT.md).

**NOT READY FOR FINAL PREFLIGHT**

C4 remains `NO-GO`, was not executed, and is not authorized by this reconciliation.

## 11. C4P5 successor classification

C4P5 preserves the original preflight, C3 rehearsal, synthetic C4A, C4P staging, and C4P2
engineering records. It adds a separate controlled schema-v3 staging exercise. Current changes to
the blocker table are:

| Blocker                                          | Current status     | Current evidence                                                                                                                                                          | Exact remaining action                                                                                                   |
| ------------------------------------------------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| External traffic rejection and graceful drain    | PARTIALLY PREPARED | **NO EXTERNAL TRAFFIC TERMINATION PRESENT.** A server-owned fail-closed local gate rejected new requests, drained accepted work to zero, and has no HTTP/frontend toggle. | Operator approves the direct-local topology and timeout; any later external ingress needs a separate gate and evidence.  |
| Writer shutdown/resumption                       | PARTIALLY PREPARED | Uvicorn shut down gracefully; PID/listener were absent; SQLite writer-gate/quiescence proof passed without source mutation.                                               | Complete elevated host writer/process/service/task/admin-tool/file-handle inventory; approve stop and staged resumption. |
| Monitoring collection                            | PARTIALLY PREPARED | The read-only twelve-signal collector ran on controlled schema v3 with zero hard alerts and sanitized evidence.                                                           | Approve destination and protected-artifact audit source; repeat in the authorized maintenance record.                    |
| Monitoring thresholds and observation            | PARTIALLY PREPARED | Deterministic hard invariants fail closed; rate, latency, drain, and duration values remain `BASELINE_REQUIRED`.                                                          | Approve empirical thresholds, observation duration, owners, alert destination, escalation, and decision authority.       |
| Canary inputs and approval                       | PARTIALLY PREPARED | Scenario remains defined and unexecuted.                                                                                                                                  | Accounting/Data Reviewer and Release Owner approve after read-only acceptance.                                           |
| Named owners and signatures                      | BLOCKED            | No technical preparation assigned a human name or signature.                                                                                                              | Assign named roles and complete every required approval.                                                                 |
| Final deployment-specific preflight and go/no-go | BLOCKED            | No migration, schema-v4 target, canary, schema-v4 writer, or authorization exists.                                                                                        | Close all prerequisites, run fresh final preflight, and obtain signed go/no-go.                                          |

The controlled schema-v3 source, repository development database, and financial row counts remained
unchanged. No PERSONAL work occurred. See
[`M5_1_C4P5_TRAFFIC_MONITORING_REPORT.md`](M5_1_C4P5_TRAFFIC_MONITORING_REPORT.md).

**NOT READY FOR FINAL PREFLIGHT**

## 12. C4P7 deployment-target decision and SaaS foundation

The operator selected **D01=B**. The entire Windows controlled environment is now classified as
staging only. Its evidence is preserved, but its source, releases, recovery package, paths, hashes,
fingerprints, controls, timings, and monitoring results cannot approve the future server.

C4P7 closes the provider-neutral deployment-package implementation gap: strict server config,
single-writer process contract, frontend-only public ingress contract, separated private storage,
schema-v3 BUSINESS provisioning through existing service boundaries, maintenance-gated backup and
restore proof, writer-gate verification, and monitoring configuration are implemented and tested on
disposable roots.

The actual-server blockers remain: server/provider/OS selection, new source provisioning and
approval, privileged writer/handle inventory, deployed public ingress/TLS, filesystem and persistent
storage proof, encryption, off-host recovery, retention/access audit, exact recovery/C4 releases,
capacity/baselines/window, monitoring owners/delivery, canary approval, signatures, final preflight,
and go/no-go. The current table is in
[`M5_1_C4P7_SAAS_DEPLOYMENT_REPORT.md`](M5_1_C4P7_SAAS_DEPLOYMENT_REPORT.md).

**SERVER DEPLOYMENT FOUNDATION PREPARED — C4 NOT EXECUTED**
