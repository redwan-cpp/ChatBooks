# ADR 0016: Cross-space transfers coordinate separate ledger effects

**Date:** 2026-09-26  
**Status:** Accepted for M5.0 architecture; accounting mappings and implementation deferred

## Context

Money may move between a personal space and a business organization. The movement crosses distinct
owners, authorizations, reports, and accounting meanings. Depending on facts, it may be a
contribution, drawing, reimbursement, salary, distribution, or loan.

## Decision

No journal spans financial spaces. A cross-space workflow creates one independently reviewable
proposal in each ledger and links them with a non-financial `CrossSpaceTransfer` correlation. Each
side requires authority in that space, deterministic validation, its own exact-version confirmation,
an idempotency key, posting, and audit.

The correlation records minimal typed references, amount/currency, proposal/entry IDs, request/audit
provenance, and recovery state. It does not affect balances or grant visibility into the other side.
If one side posts and another fails, recovery is a retry or explicit compensating reversal; committed
history is never deleted.

The ledger accounts and financial classification for contributions, drawings, reimbursements,
salaries, distributions, and loans require accountant approval.

## Alternatives considered

### One journal with personal and business lines

Rejected because it breaks ownership and reporting isolation and cannot be authorized as one ledger.

### Post one side and represent the other only as metadata

Rejected because one space's actual balance would not have a ledger source of truth.

### Distributed rollback by deleting the first post

Rejected because posted history is immutable and external failure cannot justify history deletion.

## Consequences

- Each ledger remains balanced and independently auditable.
- Coordinated review may appear as one UX step but produces two confirmation records.
- Partial completion is an explicit recoverable state.
- Cross-space accounting templates cannot be implemented until human/accountant decisions are made.
