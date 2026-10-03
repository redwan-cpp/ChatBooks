# ADR 0015: Personal actuals use a typed adapter over the deterministic ledger

**Date:** 2026-09-26  
**Status:** Accepted for M5.0 architecture; implementation and migration deferred

## Context

Personal balances, income, expenses, liabilities, transfers, corrections, and reports need exact,
auditable accounting. The current accounting invariants are suitable, but `AccountingEngine` and
the SQLite schema bind authorization, periods, foreign keys, receipts, audit, and reports to
`organization_id`. Using them unchanged would require a fake organization.

## Decision

Actual personal money movements use the existing proposal, deterministic validation, exact-version
confirmation, atomic posting, compensating reversal, immutable audit, and ledger-derived reporting
rules.

A future `PersonalAccountingAdapter` authorizes a `PersonalSpace`, maps personal accounts and
categories to explicit ledger lines, resolves an internal owner-bound `LedgerBook`, and calls an
ownership-neutral ledger application service. The business `AccountingEngine` remains a
compatibility facade over the same service. Ownership plumbing may be refactored, but debit/credit,
balance, confirmation, posting, reversal, and audit rules are not redesigned.

Plans, reminders, goals, account presentation metadata, categories, and cross-space correlations
remain outside the ledger. No independently mutable personal balance is stored.

## Alternatives considered

### Use the current engine with a hidden organization

Rejected because it violates personal ownership and exposes business semantics.

### Build a simpler personal transaction table with mutable balances

Rejected because it creates a second, weaker source of financial truth and loses reversal and audit
guarantees.

### Copy the accounting engine into a personal module

Rejected because duplicated posting logic and database constraints can diverge.

## Consequences

- Personal actuals can inherit proven accounting guarantees and tests.
- The current engine cannot be used through only a UI/API adapter; a future internal scope seam and
  migration are concrete prerequisites.
- Existing organization routes and results remain stable through a compatibility facade.
- Personal posting remains blocked until period, opening-balance, and default mapping policies are
  approved and equivalent database constraints are tested.
