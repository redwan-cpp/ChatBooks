# ADR 0014: Personal Financial Space resolves to PersonalSpace

**Date:** 2026-09-26  
**Status:** Accepted for M5.0 architecture; implementation deferred

## Context

ADR 0009 defines `FinancialSpaceRef(kind, id)` without persistent personal ownership. M5.0 must say
what a PERSONAL reference means while preserving current organization IDs, routes, foreign keys, and
history.

## Decision

`FinancialSpaceRef(PERSONAL, id)` resolves to `PersonalSpace.id`.
`FinancialSpaceRef(BUSINESS, id)` continues to resolve to `Organization.id`. The pair of kind and ID
is mandatory. A project remains an optional business dimension.

A future authenticated discovery endpoint returns a typed union of accessible personal spaces and
organizations. No cross-cutting `financial_spaces` parent table is required. Personal routes use
`/personal-spaces/{id}` and existing `/organizations/{id}` routes remain business-only.

## Alternatives considered

### Add a global Financial Space parent to every current table

Rejected because it would force a proven-ledger migration without improving current business
authorization and would conflate product navigation identity with ledger ownership.

### Make organization routes accept either kind

Rejected because an ID substitution could select the wrong domain and every handler would carry two
sets of semantics.

### Use one untagged ID namespace

Rejected because ownership kind would be implicit and unsafe for caches, routes, tools, and future
AI context.

## Consequences

- Existing business API behavior and identifiers remain unchanged.
- Clients dispatch to an explicit route family using the typed reference.
- Cache, export, conversation, notification, and AI keys must include both kind and ID.
- Cross-context aggregate views need separately approved authorization and product semantics.
