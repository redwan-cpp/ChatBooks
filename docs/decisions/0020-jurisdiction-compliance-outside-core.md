# ADR 0020: Jurisdiction and compliance rules stay outside the universal core

**Date:** 2026-09-26  
**Status:** Accepted for M5.1-A architecture; implementation deferred

## Context

Chatbooks needs trustworthy financial state for individuals and project-based businesses. Tax,
VAT/GST, payroll, statutory statements, filing, and recognition requirements vary by jurisdiction,
entity, date, and facts. Encoding one assumed policy in the shared core would misrepresent financial
or legal compliance as universal.

## Decision

The universal core contains exact financial state, proposals, postings, balances, reversals, audit,
and neutral report primitives. It contains no country-specific tax calculation, payroll compliance,
filing, statutory format, or regulatory determination.

A future jurisdiction package is an external, versioned capability layer. It consumes authorized
core read models and records jurisdiction, rule-set version, effective dates, source, and calculation
provenance. It cannot directly mutate ledger or audit data. Any adjustment enters as a structured
proposal and follows deterministic validation and explicit confirmation.

Chatbooks must not claim statutory or tax compliance merely because the ledger balances.

## Alternatives considered

### Put tax fields and rules into core accounts and postings

Rejected because rules vary and would contaminate otherwise reusable financial invariants.

### Let clients or AI calculate authoritative compliance values

Rejected because results would be nondeterministic, unaudited, and outside the accounting boundary.

### Exclude all future compliance integration

Rejected as an architectural restriction; an external versioned layer can be added later without
changing core ownership or posting.

## Consequences

- Core behavior stays jurisdiction-neutral and testable.
- Every compliance feature needs product/legal scope and qualified domain-expert approval.
- Compliance-derived entries retain the same proposal, confirmation, posting, and audit guarantees.
- No compliance feature is implemented in M5.1-A.

**Classification:** ENGINEERING DECISION for separation; PRODUCT DECISION for product scope;
ACCOUNTING POLICY for every jurisdiction rule and mapping.
