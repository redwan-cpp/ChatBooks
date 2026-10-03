# ADR 0017: Personal categories are separate, version-mapped classifications

**Date:** 2026-09-26  
**Status:** Accepted for M5.0 architecture; taxonomy and implementation deferred

## Context

Personal users need labels such as Groceries, Transport, and Entertainment, while deterministic
posting requires explicit ledger accounts. Treating a category as the account itself couples UX
changes to accounting identity. Storing category totals separately would create mutable actuals.

## Decision

Model `PersonalCategory` as a stable personal-space-owned label with income or expense direction.
Use a versioned `CategoryAccountMapping` to resolve the category to an owned ledger account at
proposal creation. The proposal and posted line retain the selected category and mapping provenance
alongside the resolved ledger account.

Renaming or changing a mapping affects future proposals only. It does not rewrite posted lines or
historical totals. Category actuals are derived from posted categorized lines. Transfers do not use
income or expense categories.

## Alternatives considered

### Make every category an accounting account

Rejected because user taxonomy changes would mutate or proliferate accounting identities and make
progressive disclosure harder.

### Store categories only as free-text tags

Rejected because reports and proposal mappings would be nondeterministic.

### Maintain a mutable category spending total

Rejected because it can drift from the ledger.

## Consequences

- Plain-language taxonomy can evolve without rewriting ledger history.
- Mapping versions provide reproducible posting and reporting provenance.
- Split lines, refunds, fees, tax, cashback, and historical recategorization need explicit policy.
- Default category taxonomy and ledger mapping require product/accountant approval.
