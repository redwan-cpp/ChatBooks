# M5.1-C4P6 operator decision packet

**Date prepared:** 2026-09-30  
**Project and product:** Chatbooks
**Scope:** Operator decision intake only; no C4 execution  
**Current state:** **SERVER DEPLOYMENT FOUNDATION PREPARED — C4 NOT EXECUTED**  
**C4 authorization:** **NOT GRANTED**

This packet records the human, deployment, security, monitoring, and accounting decisions that are
still required before the final C4 preflight. Preparing or completing an individual row does not
authorize migration. No name, approval, threshold, infrastructure, or policy is inferred.

Use only these statuses:

- `PENDING_OPERATOR_DECISION`
- `REQUIRES_ELEVATED_VERIFICATION`
- `BASELINE_REQUIRED`
- `READY_FOR_APPROVAL`
- `APPROVED`
- `BLOCKED`

`APPROVED` requires an explicit operator decision. D01 is recorded from the direct C4P7 operator
instruction; no personal name or signature was inferred. Every source, release, security,
accounting, canary, rollback, and C4 approval still requires its named responsible human and
reviewed evidence. Blank fields and technical readiness never mean approval.

## 1. Deployment-target decision — select exactly one

The operator recorded this decision in the M5.1-C4P7 instruction. It selects the deployment class
only; it does not assign a named Release Owner or approve any source, release, recovery artifact,
security control, threshold, canary, or C4 execution.

- [ ] **A.** The controlled environment
      `F:\ChatbookDeployment\m5-1-c4-controlled` is the intended C4 deployment target.
- [x] **B.** This environment is staging only and a separate deployment target must be prepared.

| Field                        | Operator entry                 |
| ---------------------------- | ------------------------------ |
| Selected option (`A` or `B`) | `B`                            |
| Decision status              | `APPROVED`                     |
| Decision maker name          | ____________________           |
| Role                         | Operator                       |
| Evidence reference           | M5.1-C4P7 operator instruction |
| Signature                    | ____________________           |
| Timestamp                    | 2026-09-30                     |

Option **B** is selected. Do not reuse source-specific approvals: select and inspect the new server,
provision its schema-v3 BUSINESS source, regenerate every path/hash/fingerprint/recovery artifact,
and update this packet. The provider-neutral foundation is documented in
[`M5_1_C4P7_SAAS_DEPLOYMENT_FOUNDATION.md`](M5_1_C4P7_SAAS_DEPLOYMENT_FOUNDATION.md).

## 2. Current candidate identity — evidence, not approval

| Item                       | Current controlled-staging evidence                                | Status                                          |
| -------------------------- | ------------------------------------------------------------------ | ----------------------------------------------- |
| Environment                | `F:\ChatbookDeployment\m5-1-c4-controlled`                         | `STAGING ONLY — EXCLUDED FROM C4 TARGET`        |
| Host observed              | `DESKTOP-0D25D0C`                                                  | `STAGING ONLY — EXCLUDED FROM C4 TARGET`        |
| Source                     | `source\chatbook-business-v3.db`; schema 3; 475,136 bytes          | `STAGING EVIDENCE ONLY`                         |
| Source SHA-256             | `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` | `BLOCKED`                                       |
| Content fingerprint        | `bb2574b83dcd0855ef5b52150905e256f90208075e1c5e3a6623e2fc7cfe12c2` | `BLOCKED`                                       |
| Release ID                 | `6ef3b02b4e78783a2fbeddd2fe244b55c790b91b6eb5c3ccf7dac3bfe45f70a8` | `BLOCKED`                                       |
| Release manifest SHA-256   | `f51833e07e60b1b021f23eac0e65488cd0ff2c2645bb9a56010e532c4c0f204f` | `BLOCKED`                                       |
| Migration artifact SHA-256 | `6c80eaebb419b6affe7df837c9391cc64ee6146d1a6a92306985b398275f68e9` | `BLOCKED`                                       |
| Compatible v3 recovery     | `recovery\chatbook-v3-release-6ef3b02b4e78783a.zip`; 313,186 bytes | `BLOCKED`                                       |
| Recovery SHA-256           | `a0a06cf0c90974bbacc2ee2dcd3e28cca3d74087818372b9645a702f26f05751` | `BLOCKED`                                       |
| Schema-v4 target           | Absent by design                                                   | `BLOCKED` until separately authorized migration |

These source-specific rows remain preserved as staging evidence. They cannot move to approval for
the future server. Its path, hashes, fingerprints, counts/reports, recovery release, and runtime
identity must be generated again and reviewed by the named Release Owner and Accounting/Data
Reviewer.

## 3. Required role intake

All names remain blank. Assignment is a prerequisite, not evidence that the assignee approves C4.

| Name                 | Role                     | Decision                    | Evidence reference   | Signature            | Timestamp            |
| -------------------- | ------------------------ | --------------------------- | -------------------- | -------------------- | -------------------- |
| ____________________ | Release Owner            | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |
| ____________________ | Migration Operator       | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |
| ____________________ | Application Operator     | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |
| ____________________ | Accounting/Data Reviewer | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |
| ____________________ | Incident Recorder        | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |

## 4. Decision register

| ID   | Decision or gate                               | Current status                   | Evidence required before decision                                                                       | Required decision/approver                                                 |
| ---- | ---------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| D01  | Deployment target A or B                       | `APPROVED`                       | Option B selected in the M5.1-C4P7 operator instruction                                                 | Decision recorded; no source or C4 approval implied                        |
| D02  | Exact C4 source approval                       | `BLOCKED`                        | New server identity plus exact path, schema/hash/fingerprints, row/report evidence, recovery disclosure | Release Owner + Accounting/Data Reviewer approve or reject                 |
| D02R | C4 release and compatible v3 recovery identity | `BLOCKED`                        | New server release manifest, release/migration hashes, recovery archive/hash, compatibility evidence    | Release Owner + Migration Operator approve or reject                       |
| D03  | Release Owner                                  | `PENDING_OPERATOR_DECISION`      | Named assignment and availability                                                                       | Authorized sponsor assigns person                                          |
| D04  | Migration Operator                             | `PENDING_OPERATOR_DECISION`      | Named assignment and command/runbook acceptance                                                         | Release Owner assigns person                                               |
| D05  | Application Operator                           | `PENDING_OPERATOR_DECISION`      | Named assignment and traffic/writer responsibility acceptance                                           | Release Owner assigns person                                               |
| D06  | Accounting/Data Reviewer                       | `PENDING_OPERATOR_DECISION`      | Named assignment and independence/competence confirmation                                               | Release Owner assigns person                                               |
| D07  | Incident Recorder                              | `PENDING_OPERATOR_DECISION`      | Named assignment, restricted record path, retention, escalation route                                   | Release Owner assigns person                                               |
| D08  | Writer/service/task/file-handle verification   | `REQUIRES_ELEVATED_VERIFICATION` | Complete elevated output from section 6, reconciled to every writer and handle                          | Application Operator signs zero-uncontrolled-writer result                 |
| D09  | External traffic rejection                     | `PENDING_OPERATOR_DECISION`      | C4P7 provider-neutral public ingress contract plus actual server listener/process/drain evidence        | Application Operator + Release Owner approve the implemented external gate |
| D10  | Graceful drain timeout                         | `BASELINE_REQUIRED`              | Intended-host repeated drain observations and failure behavior                                          | Application Operator + Release Owner approve value                         |
| D11  | Backup/recovery storage                        | `PENDING_OPERATOR_DECISION`      | Exact paths, principals, fresh-backup plan, restore destination, capacity                               | Application Operator + Release Owner approve                               |
| D12  | Encryption at rest                             | `PENDING_OPERATOR_DECISION`      | Approved storage-encryption control and verification output                                             | Application Operator + Release Owner approve                               |
| D13  | Off-host recovery                              | `BLOCKED`                        | Approved encrypted destination, transfer procedure, custodian, hash verification, restore drill         | Application Operator + Release Owner approve implemented control           |
| D14  | Retention and destruction                      | `PENDING_OPERATOR_DECISION`      | Durations, legal/policy basis, destruction authority, method, evidence                                  | Release Owner + Incident Recorder approve                                  |
| D15  | Access auditing                                | `BLOCKED`                        | Approved object-access audit source, collection proof, redaction, alert routing                         | Application Operator + Incident Recorder approve implemented control       |
| D16  | Separation of duties                           | `PENDING_OPERATOR_DECISION`      | Named role/principal mapping and conflict review                                                        | Release Owner approves                                                     |
| D17  | Maintenance window                             | `BASELINE_REQUIRED`              | Intended-host drain, backup, restore, migration, validation, canary, and decision-time evidence         | Release Owner + Application Operator approve window                        |
| D18  | Disk/capacity safety margin                    | `BASELINE_REQUIRED`              | Intended-filesystem free bytes, candidate-specific peak, WAL/journal and retained-artifact allowance    | Application Operator + Release Owner approve margin                        |
| D19  | Monitoring owners                              | `PENDING_OPERATOR_DECISION`      | Named monitoring, escalation, and stop/rollback decision owners                                         | Release Owner assigns; assignees accept                                    |
| D20  | Monitoring alert destination                   | `PENDING_OPERATOR_DECISION`      | Approved destination, access controls, delivery test, redaction proof                                   | Monitoring owner + Incident Recorder approve                               |
| D21  | Baseline-derived thresholds                    | `BASELINE_REQUIRED`              | Intended-host observations for latency, drain, migration duration, lock/error frequency, resource use   | Monitoring owner + Application Operator approve values                     |
| D22  | Observation duration                           | `BASELINE_REQUIRED`              | Staffing/escalation coverage and intended-host operating baseline                                       | Release Owner + Monitoring owner approve duration                          |
| D23  | BUSINESS canary                                | `READY_FOR_APPROVAL`             | Unchanged section 8 canary and post-migration read-only acceptance                                      | Accounting/Data Reviewer + Release Owner approve                           |
| D24  | Rollback boundary                              | `READY_FOR_APPROVAL`             | Signed acknowledgement of runbook branches A/B/C                                                        | Release Owner + Migration Operator + Accounting/Data Reviewer approve      |
| D25  | Final go/no-go                                 | `BLOCKED`                        | All applicable gates approved; fresh writer-gated backup/restore and final preflight match              | All five roles sign; Release Owner explicitly authorizes C4                |

### Decision-entry form

Copy one row per decision ID. Do not use a blank as approval.

| ID   | Name                 | Role                 | Decision             | Status               | Evidence reference   | Signature            | Timestamp            |
| ---- | -------------------- | -------------------- | -------------------- | -------------------- | -------------------- | -------------------- | -------------------- |
| ____ | ____________________ | ____________________ | ____________________ | ____________________ | ____________________ | ____________________ | ____________________ |

Allowed decision values are `APPROVE`, `REJECT`, or `DEFER`. `APPROVE` changes the status to
`APPROVED` only when the required evidence and signature are present.

## 5. Monitoring decisions

### Deterministic invariant checks

These have fixed pass conditions and must not be weakened by an empirical threshold:

| Signal                | Required invariant                                                                         | Current status       |
| --------------------- | ------------------------------------------------------------------------------------------ | -------------------- |
| Schema version        | Exactly 3 before migration; exactly 4 only after committed migration in its approved phase | `READY_FOR_APPROVAL` |
| Database integrity    | `PRAGMA integrity_check` returns exactly `ok`                                              | `READY_FOR_APPROVAL` |
| Foreign keys          | `PRAGMA foreign_key_check` returns zero rows                                               | `READY_FOR_APPROVAL` |
| Idempotency           | Zero retry-resource disagreements                                                          | `READY_FOR_APPROVAL` |
| Audit sidecars        | Zero missing, duplicate, or mismatched applicable schema-v4 sidecars                       | `READY_FOR_APPROVAL` |
| Ledger reconciliation | Every journal remains balanced; approved projection fingerprints match                     | `READY_FOR_APPROVAL` |
| Report reconciliation | Approved ledger/report fingerprints match exactly                                          | `READY_FOR_APPROVAL` |
| Migration failures    | Zero errors in the applicable post-migration phase                                         | `READY_FOR_APPROVAL` |

Any failed invariant is a stop condition. The monitor may reject traffic and alert humans; it must
never repair, delete, reclassify, or roll back ledger data automatically.

### Empirical thresholds

| Signal                            | Status              | Operator-approved value | Evidence reference   | Approver/signature/time |
| --------------------------------- | ------------------- | ----------------------- | -------------------- | ----------------------- |
| Request latency                   | `BASELINE_REQUIRED` | ____________________    | ____________________ | ____________________    |
| Graceful drain duration           | `BASELINE_REQUIRED` | ____________________    | ____________________ | ____________________    |
| Migration duration                | `BASELINE_REQUIRED` | ____________________    | ____________________ | ____________________    |
| SQLite lock/write-error frequency | `BASELINE_REQUIRED` | ____________________    | ____________________ | ____________________    |
| Financial-command-error frequency | `BASELINE_REQUIRED` | ____________________    | ____________________ | ____________________    |
| CPU/memory/disk resource limits   | `BASELINE_REQUIRED` | ____________________    | ____________________ | ____________________    |

No value in controlled staging or synthetic rehearsal is promoted to an approved threshold here.

## 6. Elevated Windows verification commands

**C4P7 successor note:** option B is selected. The commands and fixed paths below are retained only
for the Windows staging evidence record. They must not be run or reused as final-server evidence.
After a server/OS is selected, the Application Operator must create and review equivalent commands
for that platform and the new paths.

Run this block only from an elevated PowerShell session on the selected intended host. It is
read-only except for writing a new restricted transcript chosen by the operator. It does not stop a
process, change a service/task, open the database for writing, create a backup, or run C4.

For target option A, use the fixed paths below. For option B, stop and regenerate this block for the
new approved environment.

```powershell
$deploymentRoot = 'F:\ChatbookDeployment\m5-1-c4-controlled'
$candidateDb = Join-Path $deploymentRoot 'source\chatbook-business-v3.db'
$runtimeRoot = Join-Path $deploymentRoot 'runtime'
$configRoot = Join-Path $deploymentRoot 'config'
$evidenceRoot = '<approved restricted operator-evidence directory>'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$evidenceFile = Join-Path $evidenceRoot "c4p6-elevated-$stamp.txt"

if (-not (Test-Path -LiteralPath $evidenceRoot -PathType Container)) {
    throw 'The approved evidence directory does not exist.'
}
if (Test-Path -LiteralPath $evidenceFile) {
    throw 'Refusing to overwrite existing operator evidence.'
}

Start-Transcript -LiteralPath $evidenceFile -NoClobber

whoami.exe /all
hostname.exe
[Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Get-CimInstance Win32_OperatingSystem |
    Select-Object CSName, Caption, Version, BuildNumber, OSArchitecture, LastBootUpTime
Get-CimInstance Win32_ComputerSystem |
    Select-Object Name, Domain, Manufacturer, Model, TotalPhysicalMemory

Get-Item -LiteralPath $deploymentRoot, $candidateDb |
    Select-Object FullName, Length, CreationTimeUtc, LastWriteTimeUtc, Attributes
Get-FileHash -Algorithm SHA256 -LiteralPath $candidateDb
Get-Acl -LiteralPath $deploymentRoot | Format-List
Get-Acl -LiteralPath $candidateDb | Format-List
Get-Volume | Select-Object DriveLetter, FileSystem, HealthStatus, Size, SizeRemaining
Get-PSDrive -PSProvider FileSystem | Select-Object Name, Root, Used, Free

Get-ChildItem -LiteralPath $configRoot -File -Force |
    Select-Object FullName, Length, LastWriteTimeUtc
$configFiles = @(
    (Join-Path $configRoot 'runtime-selection.json')
    (Join-Path $configRoot 'maintenance-control.json')
    (Join-Path $configRoot 'operational-monitoring.json')
)
Get-FileHash -Algorithm SHA256 -LiteralPath $configFiles
Get-ChildItem -LiteralPath $runtimeRoot -Force |
    Select-Object FullName, Length, LastWriteTimeUtc
$pidFiles = @(
    (Join-Path $runtimeRoot 'backend.pid')
    (Join-Path $runtimeRoot 'frontend.pid')
)
foreach ($pidFile in $pidFiles) {
    if (Test-Path -LiteralPath $pidFile) {
        $processIdText = Get-Content -Raw -LiteralPath $pidFile
        $processId = [int]$processIdText
        Get-Process -Id $processId |
            Select-Object Id, ProcessName, Path, StartTime
    }
}

Get-CimInstance Win32_Process |
    Select-Object ProcessId, ParentProcessId, Name, ExecutablePath, CommandLine |
    Sort-Object Name, ProcessId
Get-CimInstance Win32_Service |
    Select-Object Name, DisplayName, State, StartMode, StartName, PathName |
    Sort-Object Name
Get-ScheduledTask |
    Select-Object TaskPath, TaskName, State,
        @{Name='Actions';Expression={($_.Actions | ForEach-Object {
            "$($_.Execute) $($_.Arguments) [$($_.WorkingDirectory)]"
        }) -join '; '}} |
    Sort-Object TaskPath, TaskName

Get-NetTCPConnection -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess |
    Sort-Object LocalPort, LocalAddress
netstat.exe -ano -p tcp

Get-Process |
    Select-Object Id, ProcessName, Path, StartTime |
    Sort-Object ProcessName, Id
openfiles.exe /query /fo csv /v

Get-ChildItem Env: |
    Where-Object Name -Match '^(CHATBOOK|DATABASE|SQLITE|UVICORN)_' |
    Select-Object Name

& 'F:\Projects\chatbook\.venv\Scripts\python.exe' `
    -m chatbook.operational_monitoring `
    (Join-Path $configRoot 'operational-monitoring.json')
if ($LASTEXITCODE -ne 0) {
    throw 'The read-only operational monitor reported a hard invariant failure.'
}

Stop-Transcript
Get-FileHash -Algorithm SHA256 -LiteralPath $evidenceFile
```

Process command lines and the raw transcript can contain sensitive operational information. Keep
the transcript in restricted evidence storage and attach only a reviewed, sanitized summary to the
decision packet. Environment-variable values are deliberately excluded.

`openfiles.exe /query` is acceptable only if the intended host is configured to report the required
local handles. Do not enable system-wide tracking or reboot during a C4 window without a separately
approved procedure. If it is insufficient and a pre-approved Sysinternals Handle binary exists,
record its binary identity before use:

```powershell
$handleExe = '<approved absolute path to handle.exe>'
Get-FileHash -Algorithm SHA256 -LiteralPath $handleExe
& $handleExe -nobanner -a $candidateDb
```

Do not download or introduce a handle tool during the change window. The Application Operator must
reconcile every process, service, task, listener, PID file, CLI/admin path, and database handle to a
named stop/exclusion control. Missing or incomplete evidence leaves D08
`REQUIRES_ELEVATED_VERIFICATION`.

### Required sanitized evidence record

| Evidence                 | Required result                                                                                              | Recorded reference   |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ | -------------------- |
| Elevated identity        | Administrator status and intended operator identity recorded                                                 | ____________________ |
| Deployment root/database | Exact approved paths exist and match selected target                                                         | ____________________ |
| Database identity        | Expected schema-v3 source SHA-256 matches                                                                    | ____________________ |
| Read-only invariants     | Monitor reports expected schema, integrity, foreign keys, ledger/report reconciliation, and zero hard alerts | ____________________ |
| Runtime configuration    | Expected configuration hashes and schema-v3 selection match                                                  | ____________________ |
| Processes/services/tasks | Every writer-capable path classified with stop/exclusion owner                                               | ____________________ |
| Open handles             | No unexplained write-capable database handle                                                                 | ____________________ |
| Listeners/ingress        | Ports/PIDs reconciled; proxy/IIS/tunnel/forwarder presence decided                                           | ____________________ |
| Capacity                 | Intended filesystem measurements captured for baseline analysis                                              | ____________________ |
| ACLs                     | Approved principals and inherited/explicit permissions reviewed                                              | ____________________ |
| Transcript               | Restricted path, SHA-256, reviewer, and retention decision recorded                                          | ____________________ |

## 7. Traffic and drain approval

Current engineering evidence is direct local HTTP: FastAPI loopback `127.0.0.1:8100`, local Next.js
on `3100`, and **NO EXTERNAL TRAFFIC TERMINATION PRESENT** in the inspected repository/package.

| Decision                                                         | Entry                                      |
| ---------------------------------------------------------------- | ------------------------------------------ |
| Direct-local topology accepted, or external mechanism identified | ____________________                       |
| External traffic rejection mechanism, if present                 | ____________________                       |
| Local server-owned gate retained                                 | ____________________                       |
| Drain timeout                                                    | `BASELINE_REQUIRED` — ____________________ |
| Repeated intended-host evidence                                  | ____________________                       |
| Failure/abort behavior                                           | ____________________                       |
| Application Operator signature/time                              | ____________________                       |
| Release Owner signature/time                                     | ____________________                       |

## 8. Unchanged BUSINESS canary

**DEFINED — AWAITING ACCOUNTING/DATA APPROVAL + RELEASE OWNER APPROVAL**

The canary is not authorized and must not run before accepted post-migration read-only validation.
Its prepared values remain unchanged:

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

| Name                 | Role                     | Decision                    | Evidence reference   | Signature            | Timestamp            |
| -------------------- | ------------------------ | --------------------------- | -------------------- | -------------------- | -------------------- |
| ____________________ | Accounting/Data Reviewer | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |
| ____________________ | Release Owner            | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |

## 9. Rollback-boundary acknowledgement

- Before schema-v4 commit, transaction rollback is permitted.
- After schema-v4 commit and before any schema-v4 financial write, restore of the verified
  schema-v3 backup is permitted only under runbook branch B and only with complete no-write proof.
- After any schema-v4 financial write, ordinary schema-v3 restore is forbidden. Writers stay
  stopped and forward recovery must preserve all new history.

| Name                 | Role                     | Decision                    | Evidence reference   | Signature            | Timestamp            |
| -------------------- | ------------------------ | --------------------------- | -------------------- | -------------------- | -------------------- |
| ____________________ | Release Owner            | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |
| ____________________ | Migration Operator       | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |
| ____________________ | Accounting/Data Reviewer | `PENDING_OPERATOR_DECISION` | ____________________ | ____________________ | ____________________ |

## 10. Final authorization

This section must stay blank until every applicable decision is `APPROVED`, elevated verification
is complete, baseline-derived values are approved, and the fresh writer-gated backup/restore plus
final preflight match.

| Name                 | Role                     | Decision  | Evidence reference   | Signature            | Timestamp            |
| -------------------- | ------------------------ | --------- | -------------------- | -------------------- | -------------------- |
| ____________________ | Release Owner            | `BLOCKED` | ____________________ | ____________________ | ____________________ |
| ____________________ | Migration Operator       | `BLOCKED` | ____________________ | ____________________ | ____________________ |
| ____________________ | Application Operator     | `BLOCKED` | ____________________ | ____________________ | ____________________ |
| ____________________ | Accounting/Data Reviewer | `BLOCKED` | ____________________ | ____________________ | ____________________ |
| ____________________ | Incident Recorder        | `BLOCKED` | ____________________ | ____________________ | ____________________ |

**Final C4 state: SERVER DEPLOYMENT FOUNDATION PREPARED — C4 NOT EXECUTED**
