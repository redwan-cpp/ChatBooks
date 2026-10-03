# Chatbooks controlled deployment operations

**Scope:** M5.1-C4P5 controlled BUSINESS staging preparation  
**Environment:** `F:\ChatbookDeployment\m5-1-c4-controlled`  
**C4 authority:** **NO-GO — NOT READY FOR FINAL PREFLIGHT**

**C4P7 successor decision:** D01=B. This document and every fixed Windows path below are controlled
staging evidence only. They are not the final server procedure. Use the provider-neutral
[SaaS deployment package](deploy/saas/README.md) to prepare a newly selected server, then regenerate
its exact commands and evidence.

This document describes the controls that are present in the controlled staging package. It does
not authorize M5.1-C4, a schema-v3 to schema-v4 migration, a canary, or schema-v4 writers.

## Current traffic topology

The prepared FastAPI process listens on loopback `127.0.0.1:8100`. The local Next.js process calls
that API and is prepared on port `3100`. Repository and candidate-package inspection found no reverse
proxy, IIS configuration, Windows service, load balancer, container ingress, tunnel, or other HTTP
server.

**NO EXTERNAL TRAFFIC TERMINATION PRESENT**

The deployment-specific equivalent is a server-owned maintenance control file read by the FastAPI
process. It rejects every newly arriving HTTP request after drain starts and tracks requests that
were already accepted. It has no HTTP toggle and cannot be controlled by the frontend. An invalid,
missing-after-start, unreadable, or fingerprint-mismatched control state fails closed.

If an external ingress is later introduced, the operator must inventory and gate it separately. The
local application gate must remain active as a second boundary.

## Fixed paths

| Purpose                        | Path                                   |
| ------------------------------ | -------------------------------------- |
| Runtime selection              | `config\runtime-selection.json`        |
| Maintenance control            | `config\maintenance-control.json`      |
| Maintenance state              | `runtime\maintenance-state.json`       |
| Monitoring configuration       | `config\operational-monitoring.json`   |
| Sanitized operational events   | `logs\operational-events.jsonl`        |
| Structured monitoring evidence | `evidence\operational-monitoring.json` |
| Backend PID                    | `runtime\backend.pid`                  |
| Frontend PID                   | `runtime\frontend.pid`                 |

Only the protected operator identity may modify the control/configuration files. The application
never accepts a request that toggles maintenance state.

## Prepared controls

Run these only from an approved PowerShell session on the intended host. C4 remains prohibited
until the release checklist and approval matrix are complete.

1. Start the schema-v3 staging processes with `controls\Start-Backend.ps1` and
   `controls\Start-Frontend.ps1`.
2. Collect a read-only baseline with `controls\Collect-Monitoring.ps1`. The fixed protected
   configuration currently selects the pre-cutover schema-v3 phase.
3. After maintenance authorization, reject new requests and drain accepted requests with
   `controls\Enter-Maintenance.ps1 -DrainTimeoutSeconds <approved-value>`.
4. Confirm the maintenance state reports `mode=maintenance` and `in_flight=0`.
5. Stop the application with
   `controls\Stop-Application.ps1 -ShutdownTimeoutSeconds <approved-value>`.
6. Reconcile listeners, PIDs, services, tasks, administrative tools, and file handles under the
   elevated operator inventory.
7. Run `controls\Verify-Quiescence.ps1`. It must acquire the SQLite writer gate, prove a competing
   writer is blocked, roll back the probe, and preserve the source hash.
8. Collect another read-only monitor result. Do not proceed if its overall state is
   `FAILED_CLOSED` or any hard invariant reports `ALERT`.

The timeout values are deliberately not defaulted. They are `BASELINE_REQUIRED` and need operator
approval. `Reset-Maintenance.ps1` is a preparation/recovery control for a stopped schema-v3 process;
it requires the exact acknowledgement embedded in the script. It is not writer-resumption
authorization.

## Monitoring semantics

`chatbook-c4-monitor` is read-only. It opens SQLite using read-only and query-only controls and
emits timestamps, safe counts, hashes, states, and diagnostic codes. It never repairs a ledger,
edits an entry, rolls back financial history, or exposes credentials, journal payloads, descriptions,
or complete audit JSON.

Hard invariants fail closed:

- exact expected schema version;
- `PRAGMA integrity_check = ok`;
- zero foreign-key violations;
- zero idempotency retry-resource disagreements;
- complete schema-v4 audit-sidecar coverage when schema v4 is the approved phase;
- balanced journal entries and exact reconciliation fingerprints;
- exact report fingerprints;
- zero migration failures in a post-migration phase.

Signals that require operating history remain `BASELINE_REQUIRED`: SQLite lock/write-error rate,
financial-command-error rate, latency, migration duration, and drain duration. Protected-artifact
access collection requires an approved Windows audit source. Monitoring owner, escalation owner,
alert destination, observation period, and stop/rollback decision authority remain
`REQUIRES_OPERATOR_DECISION`.

## Stop conditions

Stop before migration if traffic cannot be rejected, accepted requests do not drain within the
approved duration, any writer or write-capable handle remains, the source identity changes, or a
hard monitor invariant alerts. Preserve sanitized evidence and escalate. Monitoring must never
auto-correct financial state.

After any future schema-v4 financial write, ordinary schema-v3 restore is forbidden. Keep writers
stopped and use the audited forward-recovery branch in the C4 runbook.
