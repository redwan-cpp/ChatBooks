# M5.0 personal finance specification report

**Date:** 2026-09-26  
**Milestone:** M5.0 — domain and architecture decisions only  
**Result:** Complete. No personal-finance code, schema, endpoint, or UI was implemented.

## What was inspected

The review covered the repository rulebook, requirements, architecture, design, accounting model,
security model, AI boundary, roadmap, README, M3/M3.5/M4 reports, all prior ADRs, the SQLite schema
and migration, domain values, permissions, authentication, application/API schemas and routes, the
accounting engine, reports, tests, and the M4 frontend context and API boundaries.

The implemented system remains an organization-owned business ledger. `organization_id` currently
binds authorization, accounts, periods, projects, proposals, journal entries, idempotency receipts,
audit events, and reports. That coupling is safe for current business behavior but cannot represent
private personal ownership without a deliberate internal ownership seam.

## Architectural findings

- The deterministic debit/credit, proposal, validation, confirmation, posting, reversal, audit, and
  reporting rules are suitable for personal actual money movements.
- The current `AccountingEngine` and database layout cannot safely serve personal data unchanged.
  They require organization membership and organization-owned foreign keys, periods, receipts, and
  audit records. A surface-only adapter would require a fake organization and is rejected.
- The least invasive future design introduces `PersonalSpace` as a separate ownership aggregate,
  retains `FinancialSpaceRef(kind, id)` as the application resolver, and places an internal
  `LedgerBook` ownership seam behind the existing business facade.
- A future `PersonalAccountingAdapter` resolves and authorizes the personal owner, maps plain-language
  accounts/categories to explicit ledger lines, and calls the same ownership-neutral deterministic
  ledger service used by the business facade.
- Projects remain business-only. Plans, schedules, goals, categories, account presentation, and
  cross-space correlation records remain outside immutable posted actuals.

The detailed model is in [`personal-finance-model.md`](personal-finance-model.md). The separated
engineering and human/accountant decision gates are in
[`M5_PERSONAL_FINANCE_DECISIONS.md`](M5_PERSONAL_FINANCE_DECISIONS.md).

## Recommended personal domain model

The initial model has one private `PersonalSpace` per authenticated user. `owner_user_id` is unique,
and organization membership grants no personal access. Whether multiple spaces, households,
dependants, joint owners, or advisors should be supported is explicitly deferred for product,
privacy, and legal decisions.

`FinancialSpaceRef(PERSONAL, id)` resolves only to `PersonalSpace.id`.
`FinancialSpaceRef(BUSINESS, id)` continues to resolve only to `Organization.id`. The kind is part of
authorization, lookup, caching, export, notification, conversation, and future AI context keys. A
project may be present only inside a business space.

Personal assets, income, expenses, liabilities, balances, transfers, opening balances, and
corrections use the guarded ledger lifecycle. Personal accounts are presentation records mapped to
owned ledger accounts; their balances are derived. Personal categories are separate labels with
versioned mappings to income or expense accounts, and posted history retains mapping provenance.

Same-space transfers use one balanced entry and do not create income or expense. A personal/business
movement creates two independently authorized effects, one in each ledger, linked by a non-financial
correlation record. The accounting classification of contributions, drawings, reimbursements,
salaries, distributions, and loans remains an accountant decision.

Opening balances use a batch with date, actor, source, evidence references, system timestamp, and
generated proposal/entry references. They pass through the ordinary proposal and confirmation
lifecycle; corrections use reversal and replacement. Offset-account and period policies remain
unapproved.

The personal MVP liability boundary covers credit cards, personal loans, and installment debt as
ledger-derived liabilities. It does not calculate interest, amortization, fees, penalties, or
principal allocation. Initial personal read models are account balances, activity, spending, income,
category spending, and cash position. Net worth and valuation policy are deferred.

## Future API impact

Existing `/organizations/{organization_id}` routes remain business-only and unchanged. Future
personal routes use `/personal-spaces/{personal_space_id}` and apply authenticated owner checks at
the application boundary. A future `/financial-spaces` discovery route may return a typed union of
accessible spaces without exposing financial records or weakening either ownership model.

Future personal proposal, confirmation, posting, reversal, report, activity, and audit routes must
call the approved personal adapter and deterministic service. They must preserve exact-version
confirmation, caller idempotency, immutable posting, compensating reversal, and audit provenance.
No existing route needs context polymorphism.

## Future database and migration impact

M5.0 creates no table or migration. M5.1 is expected to need personal ownership, internal ledger-book
mapping, personal presentation accounts, categories and versioned mappings, opening-balance batches,
cross-space correlations, and personal audit/access evidence. Ownership-prefixed indexes, composite
foreign keys, exact-one-owner constraints, uniqueness, idempotency, and immutability protections are
required.

A safe migration must add and backfill one business ledger-book mapping per organization, introduce
the ownership-neutral service behind the current facade, and prove that all existing business IDs,
routes, foreign keys, posted history, reports, constraints, and test results remain unchanged. The
choice between adding `ledger_book_id` to current tables and using another constrained persistence
layout must be tested against SQLite migration behavior before approval.

## Security and isolation

The backend, rather than the frontend context switcher, remains the authority. Every personal request
must authenticate the actor, resolve the exact typed space, verify ownership, and constrain child
lookups by that owner. Personal identifiers must fail through organization routes and organization
identifiers must fail through personal routes.

The boundary applies to data, counts, errors, caches, logs, exports, documents, search, analytics,
notifications, conversations, and future AI retrieval. A business owner, administrator, or
accountant receives no personal visibility from organization membership. Future household or advisor
access requires explicit consent, grants, revocation, least privilege, and access audit.

## ADRs created

- [ADR 0013](decisions/0013-personal-ownership-isolation.md): separate private personal ownership.
- [ADR 0014](decisions/0014-personal-financial-space-resolution.md): PERSONAL resolves to
  `PersonalSpace`; BUSINESS continues to resolve to `Organization`.
- [ADR 0015](decisions/0015-personal-ledger-adapter.md): typed personal adapter over an
  ownership-neutral deterministic ledger service.
- [ADR 0016](decisions/0016-cross-space-transfer-coordination.md): two independently authorized
  ledger effects with non-financial correlation.
- [ADR 0017](decisions/0017-personal-category-mapping.md): personal labels with versioned ledger
  mappings and historical provenance.

## Decisions requiring human or accountant input

The decision register identifies product/privacy questions about multiple spaces, household and
advisor access, retention/export/recovery, locale/time zone, category taxonomy, opening-balance
evidence, and advanced personal detail.

It separately identifies accounting decisions about personal periods, opening-balance offsets and
dates, the default chart and mappings, contributions/drawings/reimbursements/loans, credit-card and
loan behavior, investment valuation, net worth, cash position, negative balances, corrections, and
currency. These decisions have no implied default. Personal posting must not be enabled until its
period, opening-balance, default mapping, liability, and applicable cross-space policies are
approved.

## Existing business behavior

No Python, TypeScript, API, database schema, migration, package, command, or frontend behavior was
changed. Existing organizations remain the business ownership and ledger boundary. Current IDs,
memberships, roles, projects, accounts, periods, proposals, journal entries, audit events,
idempotency receipts, and reports retain their existing meaning.

## Intentionally deferred

Personal persistence, API endpoints, UI, budgets, reminders, recurring activity, financial goals,
AI, LLM integration, document extraction, bank integration, investments, multi-currency, household
sharing, advisor access, billing, and production infrastructure were not built.

## Verification

| Check                     | Result                                                        |
| ------------------------- | ------------------------------------------------------------- |
| Python tests              | 56 passed                                                     |
| mypy                      | Passed; 11 source files checked                               |
| Ruff lint                 | Passed                                                        |
| Ruff formatting           | Passed; 55 files already formatted                            |
| Frontend TypeScript       | Passed                                                        |
| Frontend ESLint           | Passed                                                        |
| Frontend Prettier         | Passed                                                        |
| Frontend Vitest           | 10 passed in 1 test file                                      |
| Frontend production build | Passed; all routes built                                      |
| Documentation links       | 107 local links checked across 39 Markdown files; none broken |

The restricted execution environment initially blocked Windows temporary SQLite files and frontend
worker processes. The same commands passed when rerun with the required process and temporary-file
permissions. No product defect was found.

## Readiness

M5.0 is complete. The repository has a coherent foundation for M5.1 implementation planning and M4
business frontend work. It is not yet ready to claim or enable personal-finance functionality.
M5.1 personal posting remains gated by the identified human/accountant policies, a proven SQLite
migration design, equivalent database constraints, cross-scope security tests, and full business
compatibility evidence.

Work stops at the specification boundary; M5 implementation has not begun.
