# M5.1-C4P5 traffic drain and monitoring collection report

**Date:** 2026-09-29  
**Project and product:** Chatbooks
**Environment:** `F:\ChatbookDeployment\m5-1-c4-controlled`  
**Evidence class:** controlled schema-v3 staging preparation  
**C4 authorization:** **NOT GRANTED**

## Result

C4P5 implements and tests a server-owned maintenance gate, graceful request drain, controlled
backend shutdown, and deterministic read-only operational monitoring for the current direct-local
HTTP topology. These controls close the two documented implementation gaps for this topology.

They do not close operator approvals. Elevated writer/process/handle inventory, any future external
ingress, timeout values, monitoring thresholds, owners, alert delivery, observation time, protected
artifact audit collection, canary approval, signatures, and final go/no-go remain open.

**NO EXTERNAL TRAFFIC TERMINATION PRESENT**

**Final status: NOT READY FOR FINAL PREFLIGHT**

## Engineering status

### Traffic rejection and graceful drain

The FastAPI application now supports a server-owned maintenance control:

- new HTTP requests receive `503 Service Unavailable` once drain begins;
- requests accepted before the transition remain counted until their response completes;
- the operator control waits for zero in-flight requests within an explicitly supplied timeout;
- invalid or unavailable maintenance state fails closed;
- no API endpoint, frontend flag, or client actor can toggle maintenance;
- the backend observes a protected shutdown request and exits through Uvicorn's graceful path;
- quiescence remains a separate SQLite writer-lock and source-preservation proof.

The implementation lives in `chatbook/maintenance.py`; integration is in `chatbook/api/main.py`.
The controlled package supplies `Enter-Maintenance.ps1`, `Stop-Application.ps1`,
`Verify-Quiescence.ps1`, and `Reset-Maintenance.ps1`.

### Monitoring collection

`chatbook-c4-monitor` and `chatbook/operational_monitoring.py` implement a sanitized, deterministic,
read-only collector for all twelve requested signal groups:

1. schema version;
2. database integrity;
3. foreign-key violations;
4. SQLite lock/write errors;
5. financial command errors;
6. idempotency disagreement;
7. audit-sidecar coverage;
8. ledger reconciliation;
9. report reconciliation;
10. migration failures;
11. request latency;
12. protected artifact access.

The collector opens SQLite read-only/query-only. It compares schema-v3 results with retained
preflight fingerprints and supports schema-v4 post-migration checks against a reviewed migration
report without selecting or starting a schema-v4 runtime. Hard invariants emit `ALERT`, set the
overall result to `FAILED_CLOSED`, and return a failing exit status. It has no repair, correction,
rollback, or financial-write behavior.

The API writes a dedicated sanitized JSONL event stream when the server-owned path is configured.
Events contain request ID, method, route path, status, duration, and safe error code only. They omit
tokens, credentials, descriptions, line contents, financial values, and audit payloads. Requests
rejected by the outer maintenance boundary are counted in the maintenance state; latency samples
cover accepted requests.

## Operator status

The following fields remain deliberately unresolved:

| Field                             | Required value               |
| --------------------------------- | ---------------------------- |
| Monitoring owner                  | `REQUIRES_OPERATOR_DECISION` |
| Escalation owner                  | `REQUIRES_OPERATOR_DECISION` |
| Alert destination                 | `REQUIRES_OPERATOR_DECISION` |
| Observation period                | `REQUIRES_OPERATOR_DECISION` |
| Stop/rollback decision authority  | `REQUIRES_OPERATOR_DECISION` |
| Lock/write-error threshold        | `BASELINE_REQUIRED`          |
| Financial-command-error threshold | `BASELINE_REQUIRED`          |
| Latency threshold                 | `BASELINE_REQUIRED`          |
| Drain timeout                     | `BASELINE_REQUIRED`          |
| Migration-duration threshold      | `BASELINE_REQUIRED`          |

An operator must also approve the direct-local topology or identify external ingress. If external
traffic termination exists outside the inspected environment, its traffic gate and drain evidence
are additional requirements. The Application Operator must complete elevated process, service,
scheduled-task, administrative tool, listener, and file-handle inventory before C4.

## Controlled staging evidence

### Topology and configuration identity

| Evidence                        | Value                                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------- |
| Traffic topology                | FastAPI loopback `127.0.0.1:8100`; local Next.js on `3100`; no external traffic layer found |
| Candidate release ID            | `6ef3b02b4e78783a2fbeddd2fe244b55c790b91b6eb5c3ccf7dac3bfe45f70a8`                          |
| Release manifest SHA-256        | `f51833e07e60b1b021f23eac0e65488cd0ff2c2645bb9a56010e532c4c0f204f`                          |
| Migration artifact SHA-256      | `6c80eaebb419b6affe7df837c9391cc64ee6146d1a6a92306985b398275f68e9`                          |
| Runtime-selection fingerprint   | `2c7fc8c7001a44843bdc47bffb394b5e4b6fd4775d90c76f9bc2c078f46a9cad`                          |
| Maintenance-control fingerprint | `400f847d28b394264cff0ca1b65fa65b006fa121ea075e5752ac873f1888e804`                          |
| Monitoring-config fingerprint   | `5d30d1f3cd664fa4dd774f4e06bf514b1432072e4633536872381c67187e19d8`                          |
| Traffic implementation SHA-256  | `f6137a4628479f503e83c16a33628ce89a98d07c9c8d3cf67ded71487def5a36`                          |
| Monitor implementation SHA-256  | `0cda41f50a6aa2ecfcf48075cdfe93f92a57e18dd2c262bac4caceabc2c72b14`                          |

### Live schema-v3 control exercise

The exercise used the controlled schema-v3 source and only the health endpoint:

- health before drain: HTTP 200;
- health after drain/seal: HTTP 503;
- accepted requests: 1; rejected requests: 1; final in-flight requests: 0;
- accepted-request latency sample: 36.693 ms; state `BASELINE_REQUIRED`;
- monitor state: `COLLECTED`; hard alerts: 0;
- schema version 3; integrity `ok`; zero foreign-key violations;
- 16 idempotency receipts and zero retry-resource disagreements;
- 8 journal entries and zero balance/reconciliation mismatches;
- schema-v3 report and content fingerprints matched the retained evidence;
- audit-sidecar and migration-failure checks were `NOT_APPLICABLE` before cutover;
- protected-artifact access remained `REQUIRES_OPERATOR_DECISION`;
- Uvicorn exited gracefully; its PID and listener were absent afterward;
- quiescence acquired the writer gate, a competing writer received `database is locked`, and the
  probe rolled back without data mutation.

The observed timings are staging observations only. They are not thresholds and do not approve a
maintenance window.

### Source preservation

| Item                                | Before/after result                                                                                        |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Controlled schema-v3 source SHA-256 | `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71` unchanged                               |
| Repository development DB SHA-256   | `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884` unchanged                               |
| Source rows                         | organizations 2; transactions 14; journal entries 8; audit events 150; idempotency receipts 16 — unchanged |
| Schema-v4 target                    | absent before and after                                                                                    |

No financial endpoint was called. No posting, reversal, period change, audit mutation, migration,
canary, schema-v4 runtime, schema-v4 writer, or PERSONAL operation occurred.

## Verification record

The final verification results are recorded after all repository gates complete.

| Gate                         | Result                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------ |
| Focused C4P5 tests           | PASS — 6/6                                                                     |
| Focused C4P5/C4P/C4P2        | PASS — 13/13                                                                   |
| Repeated traffic-drain test  | PASS — 5 consecutive fresh runs                                                |
| C3/C4A suite                 | PASS — 11/11                                                                   |
| Complete backend suite       | PASS — 101 tests in 38.692 seconds                                             |
| Mypy                         | PASS — 32 source files                                                         |
| Ruff lint                    | PASS                                                                           |
| Ruff formatting              | PASS — 110 files                                                               |
| Frontend tests/build         | PASS — 10 tests; TypeScript, ESLint, Prettier, and production build passed     |
| Safety/source-boundary scans | PASS — 5 boundary tests; source/development hashes unchanged; v4 target absent |
| Documentation/link checks    | PASS — formatting clean; 237 local links across 65 Markdown files; 0 broken    |

## Readiness table

| ITEM                  | STATUS                                    | EVIDENCE                                                                                     | REMAINING OPERATOR ACTION                                                                                        |
| --------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Traffic rejection     | ENGINEERING IMPLEMENTED AND TESTED        | Server-owned fail-closed gate returned 503 after drain in controlled staging                 | Approve direct-local topology; identify and separately gate any external ingress                                 |
| Graceful drain        | ENGINEERING IMPLEMENTED AND TESTED        | Accepted work completed; new work rejected; in-flight count reached zero                     | Approve drain timeout and repeat on the intended host during authorized maintenance                              |
| Writer shutdown       | PARTIALLY PREPARED                        | Uvicorn exited cleanly; PID/listener absent; writer-gate probe passed                        | Complete elevated writer/process/service/task/admin-tool/file-handle inventory and approve stop/resume procedure |
| Monitoring collection | ENGINEERING IMPLEMENTED AND TESTED        | Read-only 12-signal collector returned `COLLECTED` with zero hard alerts on schema v3        | Approve evidence destination and Windows protected-artifact audit source                                         |
| Monitoring thresholds | `BASELINE_REQUIRED`                       | Hard invariants are deterministic; rate, latency, drain, and duration metrics are unapproved | Establish baselines and approve thresholds without weakening invariants                                          |
| Monitoring owners     | `REQUIRES_OPERATOR_DECISION`              | Placeholders are enforced by configuration validation                                        | Name monitoring/escalation/decision owners and alert destination                                                 |
| Observation period    | `REQUIRES_OPERATOR_DECISION`              | No duration was inferred from staging                                                        | Approve a staffed post-resumption observation period                                                             |
| Canary                | BLOCKED — DEFINED, UNAPPROVED, UNEXECUTED | Existing C4P4 canary form remains unchanged                                                  | Accounting/Data Reviewer and Release Owner approve only after read-only acceptance                               |
| Signatures            | BLOCKED                                   | All checklist boxes and approval-matrix signatures remain open                               | Assign named people and record every required approval                                                           |
| Final C4 preflight    | BLOCKED                                   | No C4 migration, target, canary, or signed go/no-go exists                                   | Close all operator gates, run fresh deployment-specific preflight, and obtain explicit authorization             |

**NOT READY FOR FINAL PREFLIGHT**
