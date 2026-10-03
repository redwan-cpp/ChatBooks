# ADR 0009: Financial Space is a typed application context

## Status

Accepted for M3.5 product architecture; persistence and personal-finance implementation are
deferred.

## Naming

Chatbooks is the single canonical written name for the project, codebase, and product whose
Financial Space model this ADR defines. Existing lowercase `chatbook` technical identifiers remain
stable compatibility surfaces and are not candidates for a naming migration.

## Context

M3 uses `organization_id` as the business ownership, authorization, ledger, reporting, and audit
boundary. The revised product must eventually support personal and business finance without mixing
their data or forcing personal users through business concepts such as organization roles, projects,
and accounting-period administration.

Adding a new parent key to every current table would require a high-risk ledger migration before a
personal domain has been defined. Treating a personal context as an ordinary organization would
reuse storage but would expose the wrong authorization and product semantics.

## Decision

Financial Space is the explicit product and application context represented by a tagged reference:

```text
FinancialSpaceRef(kind: PERSONAL | BUSINESS, id)
```

A BUSINESS reference resolves to an existing organization. A PERSONAL reference will resolve to a
future personal ownership domain after its accounting and privacy rules are approved. The tag is
mandatory; an untyped identifier is insufficient.

Existing business tables retain `organization_id`. M3.5 adds no persistent space registry and no
ledger migration. A future discovery endpoint may present a union read model over organizations and
personal spaces without changing organization routes or IDs.

Every future request, cache entry, conversation, budget, reminder, and AI tool invocation must carry
one financial-space reference. A journal entry cannot span financial spaces. A personal-to-business
movement must eventually use separately reviewed effects in each space, with an optional
non-financial correlation record, after the accounting treatment is approved.

## Consequences

- Existing organizations and their history remain business data without reinterpretation.
- M4 can build a context-aware shell around the current business API without a schema change.
- Personal persistence cannot be implemented until personal ownership, accounts, periods, opening
  balances, transfers, and privacy are decided.
- A future common ledger-scope abstraction remains possible, but requires its own ADR and migration
  plan.
- Combined personal-and-business totals are not a default report and must not be inferred by the UI.

## Alternatives considered

### Represent each personal space as an organization

Rejected because it couples personal finance to business membership, role, project, period, and
reporting semantics and makes data separation depend on presentation code.

### Add `financial_space_id` to every existing record now

Rejected because no implemented personal aggregate needs it yet, and the migration would touch the
proven ledger without a complete target model.

### Build separate personal and business applications

Rejected because the product requires one context-switching experience. Persistence may still use
different typed ownership domains behind that experience.
