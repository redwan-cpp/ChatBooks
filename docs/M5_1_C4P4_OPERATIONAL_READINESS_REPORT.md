# M5.1-C4P4 final operational readiness package

**Date:** 2026-09-29  
**Project and product:** Chatbooks
**Scope:** Read-only inspection and operator-package documentation; no C4 execution  
**Candidate label:** **CANDIDATE — NOT YET OPERATOR-APPROVED**  
**Current successor status:** C4P5: **NOT READY FOR FINAL PREFLIGHT**

This report packages the current engineering evidence for human and operator decisions. It does not
approve the candidate, represent it as production, or authorize maintenance, migration, target
creation, canary execution, or writer resumption.

> **C4P5 successor note:** C4P5 subsequently implemented and tested the local server-owned traffic
> gate, graceful drain, controlled shutdown, and read-only monitoring collector for the inspected
> direct-local topology. See
> [`M5_1_C4P5_TRAFFIC_MONITORING_REPORT.md`](M5_1_C4P5_TRAFFIC_MONITORING_REPORT.md). The historical
> C4P4 observations below are preserved; the current classification is in section 15.

The inspection did not read credential values. It did not run the C4P verifier or writer-gate probe,
because those operations acquire a write lock and record evidence. The source was opened only through
SQLite read-only/query-only preflight inspection. No source, backup, restore proof, runtime
configuration, evidence file, process, listener, PID file, database row, or PERSONAL behavior was
changed.

## 1. Candidate C4 environment

| Item               | Current value                                                                                                | Readiness                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| Root               | `F:\ChatbookDeployment\m5-1-c4-controlled`                                                                   | Exists; protected ACL observed                                       |
| Classification     | Controlled BUSINESS deployment staging                                                                       | **CANDIDATE — NOT YET OPERATOR-APPROVED**                            |
| Host               | `DESKTOP-0D25D0C`                                                                                            | Candidate host only; production status is not claimed                |
| Source             | `source\chatbook-business-v3.db`                                                                             | Exists; schema 3                                                     |
| Backup             | `backup\chatbook-business-v3.backup.db`                                                                      | Existing preparation proof; not the required fresh C4 backup         |
| Restore proof      | `restore-proof\chatbook-business-v3.restore.db`                                                              | Existing preparation proof; not the required fresh C4 restore test   |
| Reserved v4 target | `target\chatbook-business-v4.db`                                                                             | Absent by design; no target was created                              |
| Evidence           | `evidence`                                                                                                   | Exists; contains historical C4P/C4P2 evidence                        |
| Runtime selection  | `config\runtime-selection.json`                                                                              | Selects schema-v3 BUSINESS source, `read-write`; v4 remains disabled |
| Credentials        | `secrets\staging-credentials.json`                                                                           | Exists behind protected ACL; contents were not inspected             |
| Runtime state      | Backend/frontend PID files absent; no relevant listener on `3000`, `3001`, `3100`, `8000`, `8001`, or `8100` | Prepared runtimes are stopped                                        |

The non-elevated session could not enumerate Windows processes, services, or scheduled tasks through
CIM (`Access denied`). That absence of evidence is not proof that no external writer exists.

## 2. Source identity and approval package

**Approval state:** **CANDIDATE — NOT YET OPERATOR-APPROVED**

| Property                   | Exact current read-only result                                                                                                                 |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Absolute source path       | `F:\ChatbookDeployment\m5-1-c4-controlled\source\chatbook-business-v3.db`                                                                      |
| Source label               | `controlled-c4-business-staging-v1`                                                                                                            |
| Intended use               | Future separately authorized M5.1-C4 controlled staging source                                                                                 |
| File size                  | 475,136 bytes                                                                                                                                  |
| Schema version             | 3                                                                                                                                              |
| SQLite version             | 3.50.4                                                                                                                                         |
| Current SHA-256            | `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71`                                                                             |
| Schema fingerprint         | `dfcb38279bee54d4bfb249ed938b74bd538231c9acb610316a407a7e5ef1658a`                                                                             |
| Content fingerprint        | `bb2574b83dcd0855ef5b52150905e256f90208075e1c5e3a6623e2fc7cfe12c2`                                                                             |
| Legacy content fingerprint | `f1a943fd14ee8ba27f7ffbb564681072280f0a05f7e630c08676dfcbded3c590`                                                                             |
| Integrity                  | `PRAGMA integrity_check = ok`                                                                                                                  |
| Foreign keys               | 0 violations                                                                                                                                   |
| Owner kind                 | BUSINESS only, per C4P2 runtime verification                                                                                                   |
| Release identity           | `672e551c8617a1e5371d4a5b31350fce700189f02c75457fafb9519241e43bde`                                                                             |
| Recovery release           | `recovery\chatbook-v3-release-672e551c8617a1e5.zip`; 295,734 bytes; SHA-256 `46eae5724488a8e9ddcf08976320678967658f9ad6abd163c2b23896b539e40d` |

### Current row counts

| Table                 | Rows | Table                     | Rows |
| --------------------- | ---: | ------------------------- | ---: |
| `organizations`       |    2 | `ledger_books`            |    2 |
| `charts_of_accounts`  |    2 | `accounts`                |    8 |
| `accounting_periods`  |    4 | `projects`                |    2 |
| `documents`           |    2 | `transactions`            |   14 |
| `transaction_lines`   |   28 | `validations`             |   12 |
| `confirmations`       |   10 | `confirmation_provenance` |   10 |
| `journal_entries`     |    8 | `journal_lines`           |   16 |
| `command_idempotency` |   16 | `audit_events`            |  150 |
| `users`               |    6 | `user_credentials`        |    6 |
| `memberships`         |   10 | `auth_sessions`           |    2 |

Audit sequence maximum is 150. The current read-only report fingerprints match the retained C4P
evidence for both organizations.

### Currencies and precision

| Organization ID                        | Currency | Minor-unit digits |
| -------------------------------------- | -------- | ----------------: |
| `0ba470aa-e553-4303-b0b7-c4615852cc4d` | BDT      |                 2 |
| `9636dbfb-79b1-4f61-ad83-9ac5a5c57a3f` | USD      |                 3 |

### Source-generation and recovery history

1. The candidate was generated through normal `AuthService` and `AccountingEngine` schema-v3
   BUSINESS pathways. No PERSONAL owner was introduced.
2. Its original physical SHA-256 was
   `7532962f3d3e752655946b1ec629b219e11d4f63de618dee0baa0c6e1e03e936`.
3. A C4P2 authenticated read created one ephemeral `auth_sessions` row. The verifier detected the
   physical mismatch and stopped.
4. With runtime processes stopped, the source was restored from the retained verified schema-v3
   backup. The changed file was preserved as
   `backup\chatbook-business-v3.post-c4p2-auth-rehearsal.db`.
5. The restored source has two sessions, unchanged financial metrics, current SHA-256
   `de4d4b32...be71`, and the same deterministic content fingerprint.

The retained `evidence\source-preflight-manifest.json` records the original physical SHA-256 and is
historical evidence. The C4P4 read-only inspection regenerated the logical manifest in memory and
confirmed the current SHA-256, schema fingerprint, content fingerprints, row counts, integrity,
foreign keys, currencies, and report fingerprints. Final preflight must write a fresh approved
manifest under the maintenance writer gate; this report is not a substitute.

### Backup and restore identities

| Artifact                  |   Bytes | Current SHA-256                                                    | Meaning                         |
| ------------------------- | ------: | ------------------------------------------------------------------ | ------------------------------- |
| Source                    | 475,136 | `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` | Candidate schema-v3 source      |
| Preparation backup        | 475,136 | `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` | Preparation proof only          |
| Preparation restore proof | 475,136 | `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` | Preparation proof only          |
| Backup manifest           |   6,518 | `618a5a4fe4a6269d2f08608b18f81da42a220cc0a8ad99c254d579fc294f42e8` | Historical preparation manifest |

Source approval requires the Release Owner and Accounting/Data Reviewer to accept the disclosed
recovery history and current identity, or nominate another source and regenerate every dependent
artifact.

## 3. Release identity

| Property                   | Value                                                                                                        | Current state                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| Source/C4 release ID       | `672e551c8617a1e5371d4a5b31350fce700189f02c75457fafb9519241e43bde`                                           | Technically identified; awaiting human approval         |
| Release identity method    | SHA-256 over sorted repository-relative release file records                                                 | Implemented                                             |
| Git revision               | `UNAVAILABLE_NO_GIT_METADATA`                                                                                | Disclosed; immutable content identity is the release ID |
| Release manifest           | `evidence\release-manifest.json`; SHA-256 `5e7c63336d3cfa5b66e33e8c2d8fea9b89a2212f8a61218da4ccb86154ac4edf` | Exists                                                  |
| Migration artifact SHA-256 | `6c80eaebb419b6affe7df837c9391cc64ee6146d1a6a92306985b398275f68e9`                                           | Identified for separately authorized C4                 |
| Frontend build ID          | `oXmnRkL-VIVFLjLOfejJm`                                                                                      | Captured                                                |
| Frontend build ID SHA-256  | `8588ce53b701f7ef8de4755b31364a91cb5537fc029a096441565b0a59c35193`                                           | Captured                                                |
| Normal v4 selector         | Server-controlled `canonical-v4`, exact path/schema/release, read-only acceptance                            | Implemented, disabled, and unactivated                  |

Documentation changes in C4P4 do not alter the release-file set recorded by the manifest. The exact
release and migration artifacts still require Release Owner and Migration Operator approval.

## 4. Recovery identity

The compatible schema-v3 recovery archive is:

```text
F:\ChatbookDeployment\m5-1-c4-controlled\recovery\chatbook-v3-release-672e551c8617a1e5.zip
```

It exists, is 295,734 bytes, has SHA-256
`46eae5724488a8e9ddcf08976320678967658f9ad6abd163c2b23896b539e40d`, and carries release ID
`672e551c8617a1e5371d4a5b31350fce700189f02c75457fafb9519241e43bde`.

The archive is technically prepared. Human approval, off-host protection, retention, access
auditing, and a deployment-specific restore decision remain open. Before any v4 financial write,
rollback may use the verified v3 backup only under runbook branch B. After any v4 financial write,
ordinary v3 restore is forbidden and forward recovery must preserve the new history.

## 5. Writer and host inventory

| Access path or component                  | Observed/prepared state                                                                                                                        | Write capability                                                                         | Current requirement                                                                       |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| FastAPI backend                           | `chatbook-api`; prepared host `127.0.0.1`, port `8100`; PID file `runtime\backend.pid`; currently no PID/listener                              | Financial and authentication writes through deterministic services                       | Application Operator must bind the process to the elevated inventory and maintenance gate |
| Authentication                            | Uses the same runtime configuration and adapter; login creates `auth_sessions`                                                                 | Non-financial database write                                                             | Must be included in drain/quiescence and post-read-only checks                            |
| Next.js frontend                          | `npm run start -- --port 3100`; PID file `runtime\frontend.pid`; currently no PID/listener; frontend host is not explicitly set in the control | No direct database access; forwards API traffic                                          | Operator must approve the bind/ingress mode and maintenance response                      |
| Trusted `chatbook` CLI                    | Repository entry point; no active process proven                                                                                               | Financial writer through `AccountingEngine`                                              | Prohibit use in the change record and verify no process/session remains                   |
| Raw SQLite/admin tools                    | Outside the supported boundary                                                                                                                 | Can bypass application process controls                                                  | Elevated operator inventory and access exclusion required                                 |
| `chatbook-migration-evidence`             | Backup/preflight tooling                                                                                                                       | Opens source writer gate; creates backup/evidence at operator paths                      | Run only under the approved maintenance gate                                              |
| `chatbook-canonical-rehearsal`            | Reviewed canonical reconstruction command                                                                                                      | Creates/migrates a new target; does not change source                                    | Use only under separately authorized C4 procedure                                         |
| `chatbook-c4a-rehearsal`                  | Synthetic-only rehearsal                                                                                                                       | Writes disposable synthetic files                                                        | Must not be used as deployment evidence                                                   |
| `chatbook-c4p`                            | Preparation/verification/hardening tool                                                                                                        | Preparation writes staging artifacts; verification acquires and rolls back a writer gate | Do not run during this package; future use requires the named operator procedure          |
| `chatbook-runtime`                        | Read-only startup inspection and selector evidence                                                                                             | Does not create or migrate a database                                                    | Use the fixed server-owned configuration only                                             |
| Background/scheduled writer in repository | None defined                                                                                                                                   | None known in repository                                                                 | Elevated host inventory must still prove no external task exists                          |
| Windows services/tasks/processes          | Non-elevated CIM queries returned `Access denied`                                                                                              | Unknown                                                                                  | **REQUIRES ELEVATED OPERATOR VERIFICATION**                                               |
| Local database handles                    | No approved handle tool installed; handle state not proven                                                                                     | Unknown                                                                                  | **REQUIRES ELEVATED OPERATOR VERIFICATION**                                               |
| Relevant listeners                        | `netstat` found none on `3000`, `3001`, `3100`, `8000`, `8001`, or `8100` during inspection                                                    | None observed                                                                            | Repeat immediately before maintenance and reconcile every PID                             |

The exact elevated commands are in
[`M5_1_C4_APPROVAL_MATRIX.md`](M5_1_C4_APPROVAL_MATRIX.md). Zero observed PID files/listeners is
stopped-staging evidence only and does not prove a complete writer inventory.

## 6. Maintenance and traffic sequence

### Current topology finding

The prepared backend is direct loopback HTTP on `127.0.0.1:8100`. The prepared frontend calls that
backend and starts on port `3100`, but its host bind is not explicit. No reverse-proxy, IIS, Nginx,
Apache, Caddy, container, service, or load-balancer configuration was found in the repository or
candidate package. Non-elevated checks did not find relevant listeners; service/task visibility was
denied.

**Ingress mode: REQUIRES OPERATOR DECISION.** The operator must choose and record whether traffic is
local-only, direct to Next.js, or controlled by an external ingress not represented here. If traffic
can reach the frontend/API directly, an engineering/deployment mechanism for a stable maintenance
response and measurable graceful drain is still missing.

### Exact future sequence — do not execute during C4P4

1. Record the five named roles, approved window, maximum drain duration, maintenance message,
   ingress mode, abort message, and escalation channel.
2. Activate the approved traffic-rejection mechanism. New financial and authentication requests
   must receive the approved maintenance response; do not queue or silently replay requests.
3. Start the approved in-flight-request measurement. Wait until the count is zero within the
   approved drain duration. If it cannot reach zero, abort before stopping processes.
4. Disable trusted CLI use, administrative scripts, raw SQLite access, scheduled tasks, and every
   external writer identified by the elevated inventory.
5. Run `controls\Stop-Application.ps1` only after drain reaches zero. Its forceful process-tree stop
   is a cleanup control, not a graceful-drain implementation.
6. Prove backend/frontend PID files are absent; reconcile all relevant listeners and process trees;
   run the elevated service/task/handle inventory; record zero outstanding requests and zero
   write-capable handles.
7. Run `controls\Verify-Quiescence.ps1` under the approved change record. It must acquire
   `BEGIN IMMEDIATE`, block the controlled competitor, roll back, and leave the source hash intact.
8. While the C4 writer gate remains held, create the fresh protected backup, restore it separately,
   run read-only preflight, and compare source/backup/restore manifests.
9. Stop if any identity, hash, count, fingerprint, integrity, foreign-key, permission, writer,
   listener, or handle evidence differs. Migration requires a separate signed go/no-go.

## 7. Backup and recovery protection package

Only `IMPLEMENTED`, `VERIFIED`, `REQUIRES OPERATOR DECISION`, and `BLOCKED` are used below.

| Control                | Status                     | Evidence                                                                                                                  | Exact remaining action                                                                                          |
| ---------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Backup path            | VERIFIED                   | `backup\chatbook-business-v3.backup.db` exists; 475,136 bytes; protected ACL; exact hash recorded                         | Approve the path and replace the preparation proof with a fresh writer-gated C4 backup                          |
| Restore-proof path     | VERIFIED                   | `restore-proof\chatbook-business-v3.restore.db` exists; exact source/backup hash and logical content                      | Approve the path and run the fresh C4 restore test                                                              |
| V4 target path         | IMPLEMENTED                | Separate protected `target` directory exists; target file is absent by design                                             | Approve the path; create the file only during authorized migration                                              |
| Evidence path          | VERIFIED                   | Protected `evidence` directory exists with manifests and sanitized runtime evidence                                       | Approve retention, access, and incident-record handling                                                         |
| Credential path        | VERIFIED                   | Separate protected `secrets` directory/file exists; credential contents were not read                                     | Approve credential custodian, rotation, and C4 access procedure                                                 |
| ACL principals         | VERIFIED                   | Inheritance is disabled; `SYSTEM`, `Administrators`, and `DESKTOP-0D25D0C\User` have explicit Full Control                | Decide whether these are the approved operator principals and remove/replace any unapproved principal before C4 |
| Encryption at rest     | REQUIRES OPERATOR DECISION | No approved BitLocker/EFS/storage-encryption evidence was available; file attributes alone do not prove volume encryption | Select the approved control and attach verification evidence                                                    |
| Off-host copy/recovery | BLOCKED                    | No approved off-host destination, transfer method, custodian, or restore drill exists                                     | Implement and test an encrypted off-host recovery path                                                          |
| Retention duration     | REQUIRES OPERATOR DECISION | No duration is approved                                                                                                   | Record duration for source, backup, restore, target, evidence, and logs                                         |
| Destruction authority  | REQUIRES OPERATOR DECISION | No person or policy is assigned                                                                                           | Assign authority, method, and evidence requirements                                                             |
| Access auditing        | BLOCKED                    | ACLs exist, but Windows object-access auditing/collection evidence is absent                                              | Enable and verify approved audit collection without leaking financial payloads                                  |
| Separation of duties   | BLOCKED                    | Technical ACLs grant full control to the same local user/admin boundary; organizational role separation is unproven       | Assign distinct operational/review roles and approve access principals                                          |

## 8. Capacity and maintenance-window package

### Measured evidence

| Measure                                       |                 Value | Evidence class                                |
| --------------------------------------------- | --------------------: | --------------------------------------------- |
| Current candidate source                      |         475,136 bytes | C4P4 read-only candidate measurement          |
| Current preparation backup                    |         475,136 bytes | C4P4 read-only candidate measurement          |
| Current preparation restore proof             |         475,136 bytes | C4P4 read-only candidate measurement          |
| Candidate-host free space                     | 506,884,919,296 bytes | C4P4 host measurement; not an approved margin |
| C4P backup plus verification                  |     0.2400739 seconds | Controlled staging measurement                |
| C4P restore proof                             |     0.0284159 seconds | Controlled staging measurement                |
| Synthetic C4A source/backup/restore           |  6,922,240 bytes each | Synthetic rehearsal only                      |
| Synthetic C4A final v4 size                   |      10,604,544 bytes | Synthetic rehearsal only                      |
| Synthetic C4A v4 target peak                  |      11,451,392 bytes | Synthetic rehearsal only                      |
| Synthetic C4A migration transaction           |      0.265734 seconds | Synthetic rehearsal only                      |
| Synthetic C4A full C3 invocation              |      2.790871 seconds | Synthetic rehearsal only                      |
| Synthetic C4A backup plus verification        |      1.216773 seconds | Synthetic rehearsal only                      |
| Synthetic C4A restore proof                   |      0.430719 seconds | Synthetic rehearsal only                      |
| Synthetic C4A total through disposable canary |      8.004117 seconds | Synthetic rehearsal only                      |

The three current candidate schema-v3 copies consume 1,425,408 bytes. Combining their measured size
with the unrelated synthetic v4 peak yields an illustrative mixed-evidence footprint of 12,876,800
bytes, or 12,401,664 bytes free beyond the existing source. This is not an approved capacity
requirement because the v4 peak was measured on a different synthetic database. Candidate-specific
migration peak and duration remain unmeasured.

### Operator approval form

| Decision                           | Operator-entered value | Evidence/conditions                                                                                                 | Approver             | Signature/time       |
| ---------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------- |
| Maximum maintenance duration       | ____________________   | Must include drain, backup, restore, preflight, migration, read-only acceptance, canary, and decision time          | ____________________ | ____________________ |
| Disk safety margin                 | ____________________   | Must be based on candidate-specific migration peak, WAL/journal behavior, evidence retention, and concurrent growth | ____________________ | ____________________ |
| Expected drain duration            | ____________________   | Must come from the approved ingress and in-flight measurement                                                       | ____________________ | ____________________ |
| Post-resumption observation period | ____________________   | Must match configured monitoring and staffed escalation coverage                                                    | ____________________ | ____________________ |

No acceptable downtime, safety margin, drain interval, or observation period is inferred here.

## 9. Monitoring package

All existing signal definitions are preserved. **Collection and alerting status: NOT CONFIGURED.**
Owner, escalation, and observation fields remain blank for operator assignment.

| Signal                     | Source                                                  | Current threshold                                                    | Threshold type    | Owner  | Alert                                                | Escalation | Observation duration | Stop condition                                                          | Configuration  |
| -------------------------- | ------------------------------------------------------- | -------------------------------------------------------------------- | ----------------- | ------ | ---------------------------------------------------- | ---------- | -------------------- | ----------------------------------------------------------------------- | -------------- |
| Schema version             | `PRAGMA user_version`; startup logs                     | 3 before C4; 4 only after accepted commit                            | INVARIANT         | ______ | Phase differs                                        | ______     | ______               | Any unexpected version                                                  | NOT CONFIGURED |
| Database integrity         | `PRAGMA integrity_check`                                | Exactly `ok`                                                         | INVARIANT         | ______ | Any other result                                     | ______     | ______               | Result differs                                                          | NOT CONFIGURED |
| Foreign-key violations     | `PRAGMA foreign_key_check`                              | Zero rows                                                            | INVARIANT         | ______ | One or more rows                                     | ______     | ______               | Any row                                                                 | NOT CONFIGURED |
| SQLite lock/write failures | Structured API/CLI/migration errors                     | Numeric threshold not approved                                       | BASELINE REQUIRED | ______ | Approved threshold exceeded                          | ______     | ______               | Migration writer conflict or approved stop threshold exceeded           | NOT CONFIGURED |
| Financial command errors   | FastAPI structured stable error codes                   | Numeric threshold not approved                                       | BASELINE REQUIRED | ______ | Approved threshold exceeded                          | ______     | ______               | Unexpected mutation/invariant error or approved stop threshold exceeded | NOT CONFIGURED |
| Idempotency                | Receipt reconciliation and application errors           | Zero retry-resource disagreement; conflict-rate threshold unapproved | OPERATOR APPROVAL | ______ | Different retry resource or rate exceeded            | ______     | ______               | Any retry-resource disagreement                                         | NOT CONFIGURED |
| Audit sidecar integrity    | C4 sidecar coverage query                               | Zero missing, duplicate, or mismatched sidecars                      | INVARIANT         | ______ | Any coverage mismatch                                | ______     | ______               | Any mismatch                                                            | NOT CONFIGURED |
| Ledger/reconciliation      | Migration manifests, balance checks, projection hashes  | Zero unbalanced entries; exact approved fingerprints                 | INVARIANT         | ______ | Any mismatch                                         | ______     | ______               | Any mismatch                                                            | NOT CONFIGURED |
| Reports                    | Ledger, statements, cash movement, project fingerprints | Exact equality to approved evidence                                  | INVARIANT         | ______ | Any mismatch                                         | ______     | ______               | Any mismatch                                                            | NOT CONFIGURED |
| Migration errors           | Sanitized migration report and operator log             | Zero errors                                                          | INVARIANT         | ______ | Any migration/trigger/index/authorizer/version error | ______     | ______               | Any error                                                               | NOT CONFIGURED |
| Latency                    | FastAPI `duration_ms`; migration timings                | Threshold not approved                                               | BASELINE REQUIRED | ______ | Approved threshold exceeded                          | ______     | ______               | Approved stop threshold exceeded                                        | NOT CONFIGURED |
| Protected artifact access  | Windows filesystem/security audit evidence              | Zero unauthorized access; audit enablement unverified                | OPERATOR APPROVAL | ______ | Unauthorized or failed approved access               | ______     | ______               | Any unauthorized access or missing required audit evidence              | NOT CONFIGURED |

Monitoring may reject traffic, stop the change, and alert humans. It must never repair, edit, or
auto-correct ledger data. Logs and alerts must exclude credentials, tokens, descriptions, journal
line payloads, complete audit JSON, and raw manifests.

## 10. Canary approval package

**DEFINED — NOT EXECUTED — AWAITING ACCOUNTING/DATA + RELEASE OWNER APPROVAL**

| Field                    | Exact prepared value                                                                                         |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Organization             | `0ba470aa-e553-4303-b0b7-c4615852cc4d` (BDT, 2 minor-unit digits)                                            |
| Actor                    | `f6d1dbd1-b80d-439e-ab24-c9afd59874e8`                                                                       |
| Debit account            | Expense `e9e3427d-73d7-44c6-a23b-dd4b5bf8fec9`                                                               |
| Credit account           | Cash `7aa504b2-578b-417d-b64e-6f8409300211`                                                                  |
| Amount                   | 12,345 minor units (BDT 123.45)                                                                              |
| Financial date           | 2026-09-30                                                                                                   |
| Project                  | `9992bf14-af4d-445f-aa3a-65894a38104f`                                                                       |
| Document                 | `47b2af28-c66d-4402-aee9-c23ecadc0750`                                                                       |
| Scenario source          | Existing deterministic BUSINESS expense-and-cash scenario                                                    |
| Description              | `Controlled C4 canary operating purchase`                                                                    |
| Confirmation request/key | `c4-canary-confirm-v1`                                                                                       |
| Posting idempotency key  | `c4-canary-post-v1`                                                                                          |
| Expected journal         | Debit expense 12,345; credit cash 12,345; balanced                                                           |
| Expected report effects  | Expense net debit +12,345; cash net debit −12,345                                                            |
| Reversal reason          | `Reverse controlled C4 canary after verification`                                                            |
| Expected final state     | Original and reversal remain visible; net changes return to zero; audit/idempotency history remains complete |

The keys are prepared values, not approvals. The Accounting/Data Reviewer must approve the business
purpose, classification, accounts, amount, date, project/document context, reversal, and expected
effects. The Release Owner may authorize execution only after accepted read-only v4 validation.

## 11. Human approval matrix

The blank role assignments, explicit decision register, elevated verification commands, and final
authorization fields are in
[`M5_1_C4_APPROVAL_MATRIX.md`](M5_1_C4_APPROVAL_MATRIX.md). No name, signature, timestamp, approval,
maintenance window, threshold, escalation, or go/no-go was filled during C4P4.

## 12. Exact remaining blockers

| Blocker                               | Classification                                           | Why it remains open                                                                                                          | Closure evidence required                                                                             |
| ------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Exact source approval                 | Technically prepared; awaiting named human decision      | Current identity and recovery history are packaged but unsigned                                                              | Release Owner and Accounting/Data Reviewer approval                                                   |
| Release and recovery approval         | Technically prepared; awaiting named human decision      | Immutable identities exist but are unsigned                                                                                  | Release Owner and Migration Operator signatures                                                       |
| Canary approval                       | Technically prepared; awaiting named human decision      | Complete input/effects form exists; accounting purpose is not approved                                                       | Accounting/Data Reviewer and Release Owner signatures                                                 |
| Rollback-boundary acceptance          | Technically prepared; awaiting named human decision      | Branches are documented; acknowledgement is blank                                                                            | Required role signatures                                                                              |
| Named roles and final authority       | Technically prepared; awaiting named human decision      | All names/signatures/timestamps are blank                                                                                    | Completed approval matrix                                                                             |
| Elevated host/writer/handle inventory | Requires explicit operator/deployment action             | Non-elevated CIM access was denied; handle evidence is absent                                                                | Elevated inventory, exclusions, PID/listener/handle reconciliation                                    |
| Final fresh backup/restore/preflight  | Requires explicit operator/deployment action             | Existing artifacts are preparation evidence only                                                                             | Fresh writer-gated backup, separate restore, and matching manifests                                   |
| Protection and recovery governance    | Requires explicit operator/deployment action             | Encryption, off-host recovery, retention, destruction, auditing, and duties are unapproved or absent                         | Implemented controls and signed policy/evidence                                                       |
| Candidate-specific capacity/window    | Requires explicit operator/deployment action             | Migration peak/duration, drain, margin, window, and observation period are unmeasured/unapproved                             | Intended-host measurements and signed form                                                            |
| Traffic rejection and graceful drain  | Genuinely requires engineering/deployment implementation | No configured ingress maintenance response or in-flight drain mechanism exists; the stop script force-kills only after drain | Implemented rejection/drain control, rehearsal, metrics, and operator approval                        |
| Monitoring collection and alerting    | Genuinely requires engineering/deployment implementation | Signals exist only as JSON/documentation; no collector, alert transport, dashboard, or stop automation is configured         | Implemented sanitized collection/alerts plus assigned owners, thresholds, escalation, and observation |
| Final go/no-go                        | Blocked by all preceding items                           | No final preflight evidence set or authorization exists                                                                      | Zero open prerequisites and signed final decision                                                     |

No accounting-kernel, migration-algorithm, runtime-selector, API, or PERSONAL implementation blocker
was found in this pass.

## 13. Exact actions required from the operator

1. Assign all five named roles and establish the restricted change/incident record.
2. Review and approve or reject the exact source, including the C4P2 session recovery/rebaseline.
3. Review and approve the release identity, migration artifact, and compatible v3 recovery archive.
4. Run the elevated process/service/task/listener/handle/access inventory from the approval matrix;
   identify every writer and record its stop/exclusion control.
5. Choose the ingress topology. Provide or commission the missing stable traffic-rejection and
   graceful-drain mechanism; rehearse it and record zero in-flight requests.
6. Approve exact source, backup, restore, target, evidence, log, and credential paths and principals.
7. Decide and implement encryption, off-host recovery, retention, destruction, access auditing, and
   separation of duties; test off-host restore.
8. Obtain candidate-specific migration peak/duration evidence in an approved rehearsal context;
   choose the disk margin, maximum window, drain duration, and observation period.
9. Configure sanitized monitoring collection and alerts; assign owners, thresholds, escalation
   routes, and stop behavior for every signal.
10. Have Accounting/Data and Release Owner review and sign the canary form without changing its
    accounting inputs silently.
11. Complete all applicable preflight-phase checklist statuses and signatures.
12. During a separately authorized maintenance window only: reject traffic, drain, stop writers,
    prove quiescence, create/restore-test the fresh backup, compare manifests, and obtain the final
    pre-migration go/no-go.

## 14. Explicit C4 status

The operational forms and technical evidence are now consolidated, but two required controls do not
exist as executable deployment behavior: traffic rejection/graceful drain and monitoring
collection/alerting. Elevated host evidence, security/recovery controls, candidate-specific
capacity/window evidence, named roles, approvals, and final preflight artifacts also remain absent.

### Verification record

| Check                                    | Result                                                                                                                                       |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Markdown formatting                      | Passed for `README.md` and all four C4P4-created or updated documents                                                                        |
| Local documentation links                | Passed: 230 links across 63 Markdown files; 0 broken                                                                                         |
| Release checklist structure              | Passed: 50 unique items, all 50 unchecked, 0 invalid status labels                                                                           |
| Required report structure                | Passed: all 14 required numbered sections present                                                                                            |
| Candidate source/backup/restore identity | Passed read-only check: all three files remain 475,136 bytes with SHA-256 `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` |
| Reserved v4 target                       | Confirmed absent                                                                                                                             |
| Staging runtime state                    | 0 runtime PID files and 0 relevant listeners observed after documentation work                                                               |
| Development database boundary            | `chatbook.db` remains SHA-256 `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`                                             |

No executable backend, migration, canary, writer, or database test was run. C4P4 changed
documentation only and required documentation plus lightweight read-only consistency checks. The
repository has no Git metadata, so verification used explicit file checks instead of Git status.

**NOT READY FOR FINAL PREFLIGHT**

The candidate cannot become `READY FOR FINAL PREFLIGHT` until both implementation gaps are closed,
all explicit operator actions above are completed, and all preflight-entry decisions are signed.
C4 remains `NO-GO`, unexecuted, and unauthorized.

## 15. C4P5 successor reconciliation

C4P5 inspected the actual prepared topology and found direct local HTTP only:

**NO EXTERNAL TRAFFIC TERMINATION PRESENT**

The local engineering gaps described in sections 6 and 9 are now implemented and exercised against
the controlled schema-v3 staging source. A server-owned, fail-closed FastAPI maintenance gate rejects
new requests, retains in-flight accounting until accepted responses complete, and supports an
operator-supplied drain timeout. Uvicorn then exits through its graceful shutdown path, after which
the existing writer-lock quiescence proof remains mandatory. No HTTP or frontend toggle exists.

A deterministic read-only collector now gathers all twelve monitoring signal groups. Schema,
integrity, foreign keys, idempotency disagreement, ledger/report reconciliation, and applicable
schema-v4 audit-sidecar/migration checks are hard invariants. Rate, latency, drain, and duration
values remain `BASELINE_REQUIRED`. Monitoring owner, escalation owner, alert destination,
observation period, and stop/rollback authority remain `REQUIRES_OPERATOR_DECISION`.

This closes the implementation gaps only for the current local topology. Writer shutdown remains
partially prepared until elevated host inventory and operator approval are complete. Any external
ingress discovered later requires its own gate. Monitoring is not operationally approved until
thresholds, owners, delivery, observation, and protected-artifact audit collection are assigned.
The canary, signatures, final preflight, and C4 authorization remain blocked.

The controlled exercise left the schema-v3 source and repository development database hashes and
row counts unchanged. It created no schema-v4 target, ran no migration or canary, started no
schema-v4 writer, and created no PERSONAL data.

**Current C4P5 status: NOT READY FOR FINAL PREFLIGHT**

## 16. C4P6 operator-decision successor note

C4P6 preserves this operational package and moves every remaining human/deployment choice into
[`M5_1_C4P6_OPERATOR_DECISION_PACKET.md`](M5_1_C4P6_OPERATOR_DECISION_PACKET.md). The first required
choice is whether `F:\ChatbookDeployment\m5-1-c4-controlled` is the intended C4 target or staging
only. Neither option is selected, so the source remains unapproved.

All human names, approvals, empirical thresholds, security/recovery policies, monitoring owners,
alert destinations, observation duration, canary signatures, rollback acknowledgement, and final
authorization remain blank or blocked. C4P6 ran no elevated operator commands and performed no C4
step.

**Current C4P6 status: NOT READY FOR FINAL PREFLIGHT**
