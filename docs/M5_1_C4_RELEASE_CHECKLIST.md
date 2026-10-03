# M5.1-C4 release checklist

**Status:** C4P7: **SERVER DEPLOYMENT FOUNDATION PREPARED — C4 NOT EXECUTED**; completing this
checklist does not itself authorize C4  
**Rule:** Every checkbox needs a named owner, timestamp, evidence reference, and explicit result

**C4P5 status vocabulary:**

- `CLOSED` — engineering evidence exists and no additional implementation is needed for the item;
- `READY FOR APPROVAL` — the technical package exists and the named human decision remains;
- `REQUIRES OPERATOR ACTION` — deployment-specific evidence or control must be performed; or
- `BLOCKED` — an upstream prerequisite or executable implementation is missing.

All checkboxes remain unchecked. The status labels describe readiness; they are not approvals. This
is a phased checklist: preflight-entry items must be signed before maintenance/preflight, while
post-migration acceptance, canary, and writer-resumption items can be signed only at their named
runbook phase.

**Deployment-preparation update, 2026-09-28:** C4P created a separate controlled schema-v3 staging
source, restricted artifact paths, a verified backup/restore proof, runtime controls, deterministic
release/recovery identities, a monitoring plan, and an unexecuted canary definition. C4P2 added
server-only normal schema-v4 selection, explicit read-only acceptance mode, fail-closed startup
checks, hardened fixed-path controls, and sanitized runtime evidence. See the
[C4P deployment preparation report](M5_1_C4P_DEPLOYMENT_PREPARATION_REPORT.md) and
[C4P2 runtime selection report](M5_1_C4P_RUNTIME_SELECTION_REPORT.md). This is controlled staging
evidence, not production or C4 execution evidence. All 50 items below remain unchecked until named
owners review the exact evidence during a separately authorized window. The engineering selection
mechanism is complete but disabled; deployment-specific decisions and human approvals remain open.
The current blocker classification and exact remaining actions are in the
[C4P3 final readiness report](M5_1_C4P3_FINAL_READINESS_REPORT.md). Normal schema-v4 runtime
selection is **CLOSED** as an engineering item; no operator approval, signature, final preflight, or
go/no-go is implied.
The C4P4 evidence and operator actions are in the
[operational readiness report](M5_1_C4P4_OPERATIONAL_READINESS_REPORT.md), and blank names,
signatures, and explicit decisions are in the
[approval matrix](M5_1_C4_APPROVAL_MATRIX.md).

**Traffic/monitoring update, 2026-09-29:** C4P5 implemented and tested the server-owned local
traffic-rejection gate, graceful in-flight drain, Uvicorn shutdown, and deterministic read-only
twelve-signal collector. **NO EXTERNAL TRAFFIC TERMINATION PRESENT.** These results are controlled
schema-v3 staging evidence. External-ingress discovery, elevated host inventory, timeouts,
thresholds, monitoring owners/delivery/observation, protected-artifact auditing, signatures, and
authorization remain operator work. See the
[C4P5 traffic/monitoring report](M5_1_C4P5_TRAFFIC_MONITORING_REPORT.md).

**Operator-decision update, 2026-09-30:** The
[C4P6 decision packet](M5_1_C4P6_OPERATOR_DECISION_PACKET.md) requires exactly one deployment-target
choice: the controlled environment is the intended C4 target, or it remains staging and a new
target must be prepared. C4P7 records option B. The Windows environment and all of its identities are
staging only. No replacement server/source, role, threshold, policy, canary, signature, or go/no-go
is approved. All 50 checklist items remain unchecked.

**SaaS foundation update, 2026-09-30:** The
[C4P7 foundation](M5_1_C4P7_SAAS_DEPLOYMENT_FOUNDATION.md) defines a provider-neutral,
single-server topology and deployable config/provisioning/backup contracts with exactly one FastAPI
writer. No actual server was selected or provisioned, so every host/source-specific checklist item
must be regenerated and approved on the new server.

Historical staging evidence root: `F:\ChatbookDeployment\m5-1-c4-controlled`. The source remains schema v3,
the reserved v4 target remains absent, and the final fresh backup must be recreated under the actual
maintenance writer gate. A C4P2 authentication check changed one ephemeral session; the verifier
stopped, the source was restored from the verified backup without a financial-data change, and the
recorded source rebaseline requires explicit approval.

## ENGINEERING SIGN-OFF

- [ ] **E01 — READY FOR APPROVAL.** The intended deployment database identity, schema version,
      SQLite version, application
      release, migration tool version, host, filesystem, and available bytes are recorded.
- [ ] **E02 — REQUIRES OPERATOR ACTION.** Every API, CLI, background, scheduler, administrative,
      and ad hoc writer is inventoried; elevated host evidence remains required.
- [ ] **E03 — REQUIRES OPERATOR ACTION.** The local maintenance response, graceful drain, Uvicorn
      shutdown, and competing-writer lock probe are implemented and rehearsed. The operator must
      approve the topology/timeouts and complete elevated connection/file-handle evidence.
- [ ] **E04 — REQUIRES OPERATOR ACTION.** A fresh representative backup was created with SQLite's
      backup API while writers were blocked.
- [ ] **E05 — REQUIRES OPERATOR ACTION.** Backup SHA-256, file size, restricted path, access owner,
      retention, and destruction plan are
      recorded.
- [ ] **E06 — READY FOR APPROVAL.** A separate preparation restore was completed and verified; the
      compatible v3 application can read it. Final C4 still requires a fresh restore proof.
- [ ] **E07 — REQUIRES OPERATOR ACTION.** Final preflight passed on the approved deployment copy and
      fresh restored backup.
- [ ] **E08 — CLOSED.** The v3-to-v4 reconstruction rehearsal passed with exact count/hash
      reconciliation.
- [ ] **E09 — CLOSED.** Database integrity, foreign keys, lifecycle constraints, immutable-history
      guards, write
      context, audit triggers, audit-sidecar triggers, indexes, and critical query plans passed.
- [ ] **E10 — CLOSED.** API, CLI, OpenAPI, pagination, error, idempotency, and source-boundary parity
      passed.
- [ ] **E11 — CLOSED.** The unchanged frontend suite passed against the exact v3/v4-compatible API
      contract.
- [ ] **E12 — CLOSED.** Recovery drills passed for preflight, backup, restore, migration,
      reconciliation, trigger
      installation, read-only acceptance, and canary failure.
- [ ] **E13 — READY FOR APPROVAL.** The exact v3 recovery release and the reviewed v4
      read-only/release-selection mechanism are
      available. The C4P control permits only `canonical-v4` plus `read-only`; normal v4 selection
      remains disabled until C4, and writable v4 requires the later writer-resumption gate.
- [ ] **E14 — REQUIRES OPERATOR ACTION.** Maintenance duration components and the observed total
      were measured on the intended hardware using the approved candidate.
- [ ] **E15 — REQUIRES OPERATOR ACTION.** Source, backup, restore, target, migration peak, minimum
      free space, and approved safety margin
      were measured on the intended filesystem.
- [ ] **E16 — READY FOR APPROVAL.** The canary proposal/post/retry/reversal/audit procedure is
      technically defined and ready for accounting/data approval; the prepared data remains
      unapproved.
- [ ] **E17 — REQUIRES OPERATOR ACTION.** Read-only collection and hard-invariant alert semantics are
      implemented. Baseline-dependent thresholds, owners, alert destination, escalation, protected
      artifact audit source, and observation duration remain unapproved.
- [ ] **E18 — CLOSED.** Normal schema-v3 startup remains the active behavior before the window; no
      PERSONAL owner,
      personal feature, AI, planning domain, tax/compliance, or unrelated release change is present.

**Engineering signer:** ____________________ **Time:** ____________________  
**Evidence reference:** ____________________

## PRODUCT/OPERATOR SIGN-OFF

- [ ] **P01 — READY FOR APPROVAL.** The maintenance announcement, start time, user impact, support
      response, and abort message are
      approved.
- [ ] **P02 — BLOCKED.** The operator accepts the candidate-specific measured maintenance duration
      and separately approves the window;
      C4A did not invent an acceptable downtime target.
- [ ] **P03 — BLOCKED.** The operator accepts the candidate-specific measured minimum free space and
      an environment-specific safety margin.
- [ ] **P04 — REQUIRES OPERATOR ACTION.** The source, backup, restore, target, manifest, and
      command-output locations have approved access,
      encryption where required, retention, off-host handling, and destruction controls.
- [ ] **P05 — REQUIRES OPERATOR ACTION.** Release owner, migration operator, application operator,
      accounting/data reviewer, incident recorder, and escalation contacts must be named and confirm
      availability; every name and signature remains blank.
- [ ] **P06 — READY FOR APPROVAL.** The v3 restore decision can be made before writers resume, and
      everyone understands that the
      ordinary v3 rollback window closes after the first v4 financial mutation.
- [ ] **P07 — REQUIRES OPERATOR ACTION.** Writer shutdown and request drain are proven for the
      controlled direct-local topology. The operator must approve it and complete elevated local
      CLI, administrative, service/task, listener, and file-handle inventory.
- [ ] **P08 — READY FOR APPROVAL.** The unchanged controlled canary organization, actor, timing,
      amount, accounts, project/document context, and reversal intent are **DEFINED — AWAITING
      ACCOUNTING/DATA APPROVAL + RELEASE OWNER APPROVAL**.
- [ ] **P09 — REQUIRES OPERATOR ACTION.** Post-cutover monitoring collection and deterministic hard
      alerts are implemented. Ownership, baseline-dependent thresholds, alert delivery, escalation,
      protected-artifact access collection, observation duration, and approval remain open.
- [ ] **P10 — READY FOR APPROVAL.** No cutover begins until this checklist and the readiness report
      are reviewed under a separately
      authorized M5.1-C4 change.

**Product/operator signer:** ____________________ **Time:** ____________________  
**Approved maintenance window:** ____________________

## ACCOUNTING/DATA SIGN-OFF

- [ ] **A01 — READY FOR APPROVAL.** Organization-to-book ownership, currency, and minor-unit precision
      are exact for every business.
- [ ] **A02 — READY FOR APPROVAL.** Every proposal, line, lifecycle state, validation
      fingerprint/version, confirmation provenance,
      receipt, journal entry/line, project/document link, reversal relationship, and stable ID reconciles.
- [ ] **A03 — READY FOR APPROVAL.** Every journal entry balances exactly with integer minor units;
      foreign-key and integrity checks
      pass.
- [ ] **A04 — READY FOR APPROVAL.** Existing audit rows, sequences, actors, timestamps, entity links,
      JSON hashes, and metadata are
      unchanged; every applicable financial event has exactly one immutable book sidecar.
- [ ] **A05 — READY FOR APPROVAL.** Account balances, trial balance, general ledger, income statement,
      balance sheet, caller-defined
      cash movements, and project views match exactly for approved date boundaries.
- [ ] **A06 — READY FOR APPROVAL.** Locked periods, inactive accounts,
      pending/validated/confirmed/posted proposals, retries, and
      long reversal chains are represented in the accepted evidence.
- [ ] **A07 — BLOCKED.** This post-migration canary-phase item requires the canary and compensating
      reversal to use approved accounting inputs, appear exactly once, leave
      the expected balances, and remain fully visible and auditable.
- [ ] **A08 — CLOSED.** Any source discrepancy is a stop condition. The migration will not repair,
      normalize, classify,
      delete, or reinterpret financial history.
- [ ] **A09 — READY FOR APPROVAL.** No unresolved accounting-policy question is treated as part of
      this technical cutover.

**Accounting/data signer:** ____________________ **Time:** ____________________  
**Evidence reference:** ____________________

## Final release-owner gate

- [ ] **F01 — BLOCKED.** All three sign-off sections are complete.
- [ ] **F02 — REQUIRES OPERATOR ACTION.** Fresh representative backup verified under the maintenance
      writer gate.
- [ ] **F03 — REQUIRES OPERATOR ACTION.** Fresh restore proof verified.
- [ ] **F04 — REQUIRES OPERATOR ACTION.** Final deployment-specific preflight passed.
- [ ] **F05 — CLOSED.** Migration rehearsal passed.
- [ ] **F06 — CLOSED.** Business parity passed.
- [ ] **F07 — CLOSED.** Rollback and recovery rehearsal passed.
- [ ] **F08 — BLOCKED.** Candidate-specific maintenance duration measured and accepted.
- [ ] **F09 — BLOCKED.** Candidate-specific disk-space requirement and margin measured and accepted.
- [ ] **F10 — READY FOR APPROVAL.** Canary procedure verified and approved for later execution after
      read-only acceptance.
- [ ] **F11 — REQUIRES OPERATOR ACTION.** Writer shutdown and graceful request drain are verified in
      controlled staging; intended-host elevated inventory, timeout approval, and maintenance-window
      repetition remain required.
- [ ] **F12 — REQUIRES OPERATOR ACTION.** Monitoring collection and hard-invariant alert semantics
      are implemented; owners, baseline thresholds, destination, escalation, protected-artifact
      auditing, and observation duration remain required.
- [ ] **F13 — BLOCKED.** The release owner has explicitly authorized M5.1-C4 execution.

**Release owner:** ____________________ **Decision/time:** ____________________
