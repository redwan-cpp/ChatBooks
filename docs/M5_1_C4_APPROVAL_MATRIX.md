# M5.1-C4 approval matrix

**Date prepared:** 2026-09-29  
**C4P6 intake update:** 2026-09-30  
**Project and product:** Chatbooks
**Historical staging environment:** `F:\ChatbookDeployment\m5-1-c4-controlled`  
**Environment label:** **STAGING ONLY — EXCLUDED FROM FINAL C4 TARGET**  
**C4 authorization:** **NOT GRANTED**

This matrix is the human approval record for a future, separately authorized M5.1-C4 preflight and
cutover. Preparing this form does not approve its contents. Names, decisions, signatures, and
timestamps must be entered by the responsible people; none are inferred from technical evidence.

The current engineering evidence is
[`M5_1_C4P5_TRAFFIC_MONITORING_REPORT.md`](M5_1_C4P5_TRAFFIC_MONITORING_REPORT.md), with the approval
package in
[`M5_1_C4P4_OPERATIONAL_READINESS_REPORT.md`](M5_1_C4P4_OPERATIONAL_READINESS_REPORT.md). The
procedure remains
[`M5_1_C4_CUTOVER_RUNBOOK.md`](M5_1_C4_CUTOVER_RUNBOOK.md), and the phased gates remain
[`M5_1_C4_RELEASE_CHECKLIST.md`](M5_1_C4_RELEASE_CHECKLIST.md).

The C4P6 intake form and exact remaining evidence requirements are in
[`M5_1_C4P6_OPERATOR_DECISION_PACKET.md`](M5_1_C4P6_OPERATOR_DECISION_PACKET.md). C4P7 records only
D01=B; no source, human role, security control, threshold, canary, signature, or C4 execution is
approved.

## Deployment-target decision

Select exactly one. Until this row is completed and signed, the candidate source is not approved.

- [ ] **A.** `F:\ChatbookDeployment\m5-1-c4-controlled` is the intended C4 deployment target.
- [x] **B.** The controlled environment is staging only; a separate deployment target must be
      prepared.

| Name                 | Role     | Decision                | Evidence reference    | Signature            | Timestamp  |
| -------------------- | -------- | ----------------------- | --------------------- | -------------------- | ---------- |
| ____________________ | Operator | `APPROVED — D01=B ONLY` | M5.1-C4P7 instruction | ____________________ | 2026-09-30 |

Option B is selected. Regenerate the source-specific package and identities for the new server
before using the remaining approval rows. The Windows commands below are retained for staging
history and are not final-server evidence.

## Required roles

| Role                     | Name                 | Responsibility                                                                                                                                     | Approval required                                                                                                                                     | Evidence required                                                                                                                                                | Signature            | Timestamp            |
| ------------------------ | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------- |
| Release Owner            | ____________________ | Owns final preflight entry, go/no-go, rollback-window closure, canary authorization, and writer resumption.                                        | Every prerequisite approval is complete; final preflight evidence matches; post-migration read-only acceptance and canary pass before writers resume. | This matrix, release checklist, source package, release/recovery identities, preflight manifests, read-only acceptance, canary, monitoring, and incident record. | ____________________ | ____________________ |
| Migration Operator       | ____________________ | Runs only the approved backup, restore, preflight, migration, reconciliation, and recovery commands; records exact outputs and times.              | Exact commands, paths, release artifacts, maintenance gate, and rollback branch are approved.                                                         | Runbook, exact path record, release manifest, fresh backup/restore evidence, migration report, and command log.                                                  | ____________________ | ____________________ |
| Application Operator     | ____________________ | Rejects traffic, drains requests, stops every writer, proves quiescence, controls runtime configuration, and resumes writers only when authorized. | Ingress topology, maintenance response, drain method, complete writer inventory, stop/start controls, monitoring, and staged resumption are approved. | Elevated inventory, listener/PID/handle evidence, drain record, writer-gate proof, runtime configuration, monitoring dashboard/alerts, and resumption record.    | ____________________ | ____________________ |
| Accounting/Data Reviewer | ____________________ | Approves source identity, financial counts/fingerprints, currency/precision, ledger/report parity, canary accounting inputs, and reversal results. | Source package and exact accounting evidence are accepted without repair, reclassification, or reinterpretation.                                      | Source manifest, row counts/hashes, currencies/precision, audit/receipt/reversal evidence, report fingerprints, migration reconciliation, and canary form.       | ____________________ | ____________________ |
| Incident Recorder        | ____________________ | Maintains the immutable timeline of commands, decisions, failures, evidence references, rollback branch, and escalations.                          | Recording location, access control, escalation route, retention, and incident template are approved before maintenance.                               | Change record, restricted evidence path, timestamps, command results, alerts, decision log, and recovery record.                                                 | ____________________ | ____________________ |

### Signature intake

Use one row for each role decision. Every field is blank by design.

| Name                 | Role                     | Decision             | Evidence reference   | Signature            | Timestamp            |
| -------------------- | ------------------------ | -------------------- | -------------------- | -------------------- | -------------------- |
| ____________________ | Release Owner            | ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | Migration Operator       | ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | Application Operator     | ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | Accounting/Data Reviewer | ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | Incident Recorder        | ____________________ | ____________________ | ____________________ | ____________________ |

## Explicit approval register

Every decision below remains blank. D01=B above is a target-class decision and does not populate any
source or C4 approval. Use `APPROVE`, `REJECT`, or `DEFER`; do not treat a blank field as approval.

| Approval                       | Required approver(s)                                        | Evidence to review                                                                                                                                                                            | Decision             | Conditions or evidence reference | Signature            | Timestamp            |
| ------------------------------ | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------------------- | -------------------- | -------------------- |
| Exact C4 source                | Release Owner; Accounting/Data Reviewer                     | New server path; schema 3; fresh SHA-256; schema/content/report fingerprints; row counts; runtime identity; recovery disclosure. Windows staging identity is ineligible.                      | ____________________ | ____________________             | ____________________ | ____________________ |
| C4 release identity            | Release Owner; Migration Operator                           | New immutable server release ID, release manifest SHA-256, migration artifact SHA-256, dependency/build identity, and compatibility evidence. Windows staging release identity is ineligible. | ____________________ | ____________________             | ____________________ | ____________________ |
| Compatible v3 recovery release | Release Owner; Migration Operator                           | New protected server-compatible v3 recovery archive, exact SHA-256, dependency/build identity, startup/restore evidence, and custodian. Windows staging recovery archive is ineligible.       | ____________________ | ____________________             | ____________________ | ____________________ |
| Backup protection              | Application Operator; Release Owner                         | Exact paths, protected ACLs, encryption decision, access principals, credential separation, fresh-maintenance backup procedure, and restore test.                                             | ____________________ | ____________________             | ____________________ | ____________________ |
| Off-host recovery              | Release Owner; Application Operator                         | Approved off-host destination, transfer/encryption method, access principals, identity/hash verification, restore drill, and recovery owner.                                                  | ____________________ | ____________________             | ____________________ | ____________________ |
| Retention and destruction      | Release Owner; Incident Recorder                            | Retention duration for source/backup/restore/target/evidence/logs; legal or policy constraints; destruction authority; destruction evidence.                                                  | ____________________ | ____________________             | ____________________ | ____________________ |
| Maintenance window             | Release Owner; Application Operator                         | Approved maximum duration, drain duration, intended-host measurements, disk margin, user communication, abort time, and support/escalation coverage.                                          | ____________________ | ____________________             | ____________________ | ____________________ |
| Monitoring                     | Application Operator; Release Owner; Incident Recorder      | Configured collectors and alerts, thresholds, owners, escalation routes, observation duration, stop behavior, and redaction proof.                                                            | ____________________ | ____________________             | ____________________ | ____________________ |
| Canary                         | Accounting/Data Reviewer; Release Owner                     | Exact organization, actor, accounts, amount/date, project/document, keys, journal/report effects, reversal reason, and rollback-boundary acknowledgement.                                     | ____________________ | ____________________             | ____________________ | ____________________ |
| Rollback boundary              | Release Owner; Migration Operator; Accounting/Data Reviewer | Branch A/B/C decision tree and explicit acknowledgement that ordinary v3 restore is forbidden after any v4 financial write.                                                                   | ____________________ | ____________________             | ____________________ | ____________________ |
| Final go/no-go                 | All five roles                                              | Every applicable preflight gate is complete; unresolved items are zero; fresh source/backup/restore manifests match; maintenance and recovery controls are active.                            | ____________________ | ____________________             | ____________________ | ____________________ |

## Elevated operator verification

**C4P7 boundary:** D01=B. The Windows commands and observations in this section are retained as
staging history only. Generate platform-specific elevated commands and evidence after the future
server and OS are selected.

The 2026-09-29 inspection ran as `DESKTOP-0D25D0C\User` without elevation. Process, service, and
scheduled-task enumeration returned `Access denied`; no approved local open-handle tool was present.
The following commands are evidence-gathering commands for an elevated PowerShell session on the
intended host. They must be run and reviewed by the Application Operator. They do not stop writers,
change configuration, create a backup, or run C4.

### Identity and process inventory

```powershell
$candidateDb = 'F:\ChatbookDeployment\m5-1-c4-controlled\source\chatbook-business-v3.db'

[Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Get-CimInstance Win32_Process |
    Select-Object ProcessId, ParentProcessId, Name, ExecutablePath, CommandLine |
    Sort-Object Name, ProcessId
```

Record every process capable of reaching the candidate database, including Python, Uvicorn,
Chatbooks CLI, SQLite clients, editors, backup tools, administrative shells, and unrecognized
processes. A filtered list alone is not sufficient evidence.

### Services and scheduled tasks

```powershell
Get-CimInstance Win32_Service |
    Select-Object Name, DisplayName, State, StartMode, StartName, PathName |
    Sort-Object Name

Get-ScheduledTask |
    Select-Object TaskPath, TaskName, State,
        @{Name='Actions';Expression={($_.Actions | ForEach-Object {
            "$($_.Execute) $($_.Arguments) [$($_.WorkingDirectory)]"
        }) -join '; '}} |
    Sort-Object TaskPath, TaskName
```

The operator must identify every relevant service/task and explicitly record why every excluded
item cannot write the candidate database.

### Listeners and ingress

```powershell
Get-NetTCPConnection -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess |
    Sort-Object LocalPort, LocalAddress

netstat.exe -ano -p tcp
```

Reconcile listening PIDs to the process inventory. Specifically record ports `3100` and `8100` and
any proxy, IIS, HTTP server, VPN, tunnel, or port-forwarding process.

### PID files and database handles

```powershell
Get-ChildItem -LiteralPath 'F:\ChatbookDeployment\m5-1-c4-controlled\runtime' -Force

Get-Process |
    Select-Object Id, ProcessName, Path, StartTime |
    Sort-Object ProcessName, Id

openfiles.exe /query /fo csv /v
```

If the approved host uses Sysinternals Handle, record its trusted binary identity before using:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '<approved-path>\handle.exe'
& '<approved-path>\handle.exe' -nobanner -a $candidateDb
```

`handle.exe` is not currently installed or approved. Do not download or introduce it during the C4
window without a separate review. If neither `openfiles` nor an approved handle tool provides
complete local-handle evidence, this gate remains open.

### Access paths and ACLs

```powershell
Get-Acl -LiteralPath 'F:\ChatbookDeployment\m5-1-c4-controlled' | Format-List
Get-Acl -LiteralPath $candidateDb | Format-List
Get-ChildItem Env: |
    Where-Object Name -Match '^(CHATBOOK|DATABASE|SQLITE|UVICORN)_' |
    Select-Object Name
```

Do not print credential values into the change record. Record variable names and sanitized runtime
identity only.

## Final authorization

**Preflight-entry decision:** ____________________  
**C4 execution decision:** ____________________  
**Release Owner signature:** ____________________  
**Timestamp:** ____________________

Until every applicable field is completed with reviewed evidence, the candidate remains
**NOT YET OPERATOR-APPROVED** and C4 remains unauthorized.
