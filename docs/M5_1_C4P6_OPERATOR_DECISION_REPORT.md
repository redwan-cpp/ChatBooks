# M5.1-C4P6 operator decision intake report

**Date:** 2026-09-30  
**Project and product:** Chatbooks
**Scope:** Documentation and read-only consistency checks only  
**Current successor status:** **SERVER DEPLOYMENT FOUNDATION PREPARED — C4 NOT EXECUTED**

## Current C4 state

The migration, reconciliation, rollback, BUSINESS parity, regression, source-boundary, normal
schema-v4 runtime selection, local traffic gate, graceful drain, controlled shutdown, and read-only
monitoring collector have engineering evidence. Schema v4 remains disabled. The controlled source
remains schema v3 and the reserved schema-v4 target is absent.

C4 is still `NO-GO`. D01=B excludes the Windows staging target. There is no selected server,
approved C4 source, named human role,
approved baseline threshold, approved protection/recovery policy, approved canary, completed
signature set, final preflight, or go/no-go authorization.

## Deployment-target decision

The operator selected **D01=B** in the M5.1-C4P7 instruction:

- `F:\ChatbookDeployment\m5-1-c4-controlled` is staging only; and
- a separate server deployment target must be selected and prepared.

The decision is recorded as `APPROVED` for D01 only. No operator name or signature was invented.
Every Windows source/release/recovery path and identity remains staging evidence and is excluded from
future server approval. The C4P7 package prepares the technical foundation; no replacement server
or server-side source exists yet.

## What Codex completed

- Consolidated every remaining C4 decision into one intake packet using only the required status
  vocabulary.
- Preserved the exact current source, release, recovery, traffic, monitoring, and canary evidence.
- Added blank role, decision, evidence-reference, signature, and timestamp fields without inventing
  people or decisions.
- Supplied exact read-only elevated Windows inspection commands for the current controlled target,
  with restricted evidence and sanitization requirements.
- Separated fixed accounting/data invariants from empirical deployment thresholds.
- Preserved the canary unchanged and unexecuted.
- Reconciled the release checklist, readiness history, and approval matrix without deleting older
  evidence.

## Remaining blockers and intake requirements

| Gate                                 | Current status                   | What requires operator action                                     | Exact evidence required                                                | Exact approval required                                       |
| ------------------------------------ | -------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------- |
| Deployment target class              | `APPROVED`                       | D01=B is recorded; Windows staging is excluded                    | M5.1-C4P7 operator instruction                                         | No further D01 choice; select the actual server               |
| Exact C4 source                      | `BLOCKED`                        | Select server, then provision and review its schema-v3 candidate  | Path, schema, SHA-256, fingerprints, counts/reports, recovery record   | Release Owner + Accounting/Data Reviewer                      |
| Release/recovery identity            | `BLOCKED`                        | Build exact server releases and immutable artifacts               | Release manifest, release/migration hashes, compatible v3 archive/hash | Release Owner + Migration Operator                            |
| Five named roles                     | `PENDING_OPERATOR_DECISION`      | Assign people and availability                                    | Completed role intake rows                                             | Authorized sponsor/Release Owner                              |
| Writer/service/task/file handles     | `REQUIRES_ELEVATED_VERIFICATION` | Run and reconcile elevated inventory                              | Restricted transcript hash plus sanitized writer/handle summary        | Application Operator                                          |
| External traffic rejection           | `PENDING_OPERATOR_DECISION`      | Accept direct-local topology or identify external ingress         | Elevated process/listener/topology evidence and gate test              | Application Operator + Release Owner                          |
| Graceful drain timeout               | `BASELINE_REQUIRED`              | Establish intended-host value                                     | Repeated drain timings, zero in-flight proof, timeout failure result   | Application Operator + Release Owner                          |
| Backup/recovery storage              | `PENDING_OPERATOR_DECISION`      | Approve paths, principals, capacity, fresh backup/restore plan    | ACL/path/capacity evidence and procedure                               | Application Operator + Release Owner                          |
| Encryption at rest                   | `PENDING_OPERATOR_DECISION`      | Select and verify control                                         | Approved platform/storage verification                                 | Application Operator + Release Owner                          |
| Off-host recovery                    | `BLOCKED`                        | Implement protected off-host copy and restore drill               | Destination, encryption, custodian, hashes, successful restore         | Application Operator + Release Owner                          |
| Retention/destruction                | `PENDING_OPERATOR_DECISION`      | Set duration, owner, method, authority                            | Signed policy/change record                                            | Release Owner + Incident Recorder                             |
| Access auditing                      | `BLOCKED`                        | Implement protected-artifact audit collection                     | Collection/query evidence, redaction, delivery test                    | Application Operator + Incident Recorder                      |
| Separation of duties                 | `PENDING_OPERATOR_DECISION`      | Map named roles to approved principals                            | Role/principal matrix and conflict review                              | Release Owner                                                 |
| Maintenance window                   | `BASELINE_REQUIRED`              | Approve maximum window and abort time                             | Intended-host component timings and staffing                           | Release Owner + Application Operator                          |
| Disk/capacity margin                 | `BASELINE_REQUIRED`              | Approve required margin                                           | Candidate-specific peak and intended-filesystem measurements           | Application Operator + Release Owner                          |
| Monitoring owners                    | `PENDING_OPERATOR_DECISION`      | Assign monitoring/escalation/decision owners                      | Named acceptance and coverage                                          | Release Owner                                                 |
| Alert destination                    | `PENDING_OPERATOR_DECISION`      | Select protected destination and test delivery                    | Delivery/redaction/access evidence                                     | Monitoring owner + Incident Recorder                          |
| Empirical thresholds                 | `BASELINE_REQUIRED`              | Approve latency, drain, duration, error, and resource thresholds  | Intended-host baseline observations                                    | Monitoring owner + Application Operator                       |
| Observation duration                 | `BASELINE_REQUIRED`              | Approve staffed duration                                          | Baseline and escalation coverage                                       | Release Owner + Monitoring owner                              |
| BUSINESS canary                      | `READY_FOR_APPROVAL`             | Review unchanged accounting intent; wait for read-only acceptance | Packet section 8 and accepted v4 read-only evidence                    | Accounting/Data Reviewer + Release Owner                      |
| Rollback boundary                    | `READY_FOR_APPROVAL`             | Acknowledge branches A/B/C                                        | Signed packet section 9                                                | Release Owner + Migration Operator + Accounting/Data Reviewer |
| Fresh backup/restore/final preflight | `BLOCKED`                        | Perform only in separately authorized maintenance                 | Matching source/backup/restore manifests under writer gate             | Migration Operator + Accounting/Data Reviewer + Release Owner |
| Final go/no-go                       | `BLOCKED`                        | Close every prerequisite and sign                                 | Complete packet/checklist and final evidence set                       | All five roles; explicit Release Owner authorization          |

## Monitoring boundary

The following are deterministic stop conditions: wrong schema version, failed integrity check,
foreign-key violations, retry-resource disagreement, applicable audit-sidecar inconsistency,
unbalanced or mismatched ledger projections, report fingerprint mismatch, and applicable migration
failure. These checks do not need empirical thresholds.

Request latency, graceful drain duration, migration duration, SQLite lock/write-error frequency,
financial-command-error frequency, and resource limits remain `BASELINE_REQUIRED`. C4P5 staging and
C4A synthetic observations are evidence inputs, not approved deployment thresholds.

## Exact commands and evidence

The packet’s elevated Windows commands are now historical staging instructions. They are not valid
for the future server. The C4P7 foundation defines provider-neutral application commands and the
evidence contract. Exact privileged host/process/service/handle/firewall/TLS/storage commands remain
blocked until the operator selects the server and OS.

## Canary state

**DEFINED — AWAITING ACCOUNTING/DATA APPROVAL + RELEASE OWNER APPROVAL**

The organization, actor, accounts, amount, date, project, document, description, keys, expected
journal/report effects, reversal reason, and expected final state are unchanged. The canary was not
executed.

## Safety and blocked work

The C4P6 task did not stop writers, enter maintenance, create a backup, modify runtime configuration,
migrate schema v3 to v4, create a schema-v4 target, run the canary, start or resume a schema-v4
writer, mutate either database, or create PERSONAL data. C4P7 later marked only D01=B as approved.

## Verification

| Check                         | Result                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------- |
| Markdown formatting           | PASS — all eight created or updated operational documents                                   |
| Local documentation links     | PASS — 243 links across 67 Markdown files; zero broken                                      |
| Deployment-target form        | SUPERSEDED — C4P7 records exactly option B                                                  |
| Decision register             | PASS — 26 rows; all statuses use the required vocabulary; all required topics present       |
| Human role intake             | PASS — five required roles; every name/signature remains blank                              |
| Approval state                | SUPERSEDED — D01 only is `APPROVED`; every source/C4 approval remains open                  |
| Canary preservation           | PASS — all 16 prepared fields exactly match C4P4                                            |
| Release checklist             | PASS — 50 valid items; all 50 unchecked                                                     |
| Read-only operational monitor | PASS — `COLLECTED`; schema 3; zero hard alerts; no financial mutation                       |
| Controlled source             | PASS — SHA-256 `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` unchanged |
| Compatible recovery archive   | PASS — SHA-256 `a0a06cf0c90974bbacc2ee2dcd3e28cca3d74087818372b9645a702f26f05751` unchanged |
| Development database          | PASS — SHA-256 `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884` unchanged |
| Runtime/cutover boundary      | PASS — backend/frontend PID files absent; schema-v4 target absent                           |

Only documentation formatting, local-link validation, form/checklist consistency, canary
comparison, hashes/path checks, and the existing read-only monitor were run. No elevated inventory
result is claimed.

The exact current successor state is:

**SERVER DEPLOYMENT FOUNDATION PREPARED — C4 NOT EXECUTED**
