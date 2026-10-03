# M5.2-B personal finance foundation planning report

**Date:** 2026-09-28  
**Project and product:** Chatbooks
**Milestone:** Personal Finance Foundation & Persistence Implementation Plan  
**Status:** Planning complete; no implementation performed

## Work completed

Created the implementation-ready plan in
[`M5_2_PERSONAL_FINANCE_IMPLEMENTATION_PLAN.md`](M5_2_PERSONAL_FINANCE_IMPLEMENTATION_PLAN.md).
This milestone changed documentation only. It added no code, table, migration, endpoint, UI,
feature flag, or executable personal behavior.

## Inspected baseline

The planning pass inspected:

- the M5.2-A policy and policy report;
- M5.0 personal ownership, accounts, categories, transfers, reporting, and unresolved decisions;
- the M5.1-A universal financial core and ADRs 0013–0020;
- M5.1-B implementation and migration plans;
- C1 BUSINESS book mapping, C2 universal-service extraction, C3 canonical persistence rehearsal,
  and C4A readiness/runbook/checklist evidence;
- the current accounting, architecture, security, and AI boundaries;
- schema-v3 normal startup and schema-v4 canonical rehearsal schema;
- `AuthorizedFinancialContext`, financial commands, repository protocols,
  `UniversalFinancialService`, BUSINESS facade, organization permissions, and authentication;
- canonical database transaction/audit controls and the schema-v4 book repository; and
- accounting, hardening, API, C1/C2/C3, authorization, migration, concurrency, and source-boundary
  test structures.

## Architectural findings

1. **The universal financial behavior is reusable.** Exact money, double-entry validation,
   confirmation, posting, reversal, reports, audit, and idempotency do not need a second personal
   implementation.
2. **The deployed persistence prerequisite is not complete.** Normal runtime remains schema v3;
   schema v4 is rehearsal-only until separately authorized M5.1-C4 succeeds.
3. **The canonical schema is book-scoped but its active adapter remains BUSINESS-shaped.** Internal
   records, extension joins, actor triggers, audit serialization, and validation fingerprints still
   assume an organization.
4. **Personal ownership requires real persistence.** A UI-only context or fake organization would
   violate the accepted isolation model and cannot provide database-enforced ownership.
5. **Presentation records must remain outside financial truth.** FinancialAccount and category
   records can improve vocabulary and classification, but all actual balances and totals must remain
   derived from posted ledger lines.
6. **Personal posting cannot be enabled from current policy.** Personal periods, default chart/
   mappings, opening balances, some liability behavior, and Cash Position still require explicit
   decisions.

## Recommended domain model

The plan recommends:

- one private `PersonalSpace` per authenticated user for the MVP;
- an ACTIVE-only lifecycle after explicit creation, with no sharing, transfer, archive, or delete;
- one PERSONAL `LedgerBook` per personal space under an exact owner-kind XOR constraint;
- `FinancialAccount` presentation records linked one-to-one to same-book asset/liability accounts,
  with no balance fields;
- stable `PersonalCategory` labels with append-only versioned account mappings;
- immutable personal proposal/journal provenance for account roles and category mapping versions;
- reuse of the existing book-scoped periods and universal proposal lifecycle; and
- a thin owner-authorized personal facade above `UniversalFinancialService`.

No second personal transaction store is recommended.

## Persistence and migration recommendation

M5.1-C4 must finish first. After the resulting schema-v4 BUSINESS baseline is observed and signed
off, the next available schema version should:

1. add `PersonalSpace` ownership;
2. reconstruct only the book owner representation to support BUSINESS or PERSONAL with exact XOR
   constraints;
3. preserve all existing BUSINESS book IDs and values;
4. add presentation account, category, immutable mapping, personal provenance, and audit-scope
   persistence;
5. retain the current book-scoped core financial tables; and
6. create no personal rows implicitly for existing users.

The migration must reuse C3/C4 backup, restore, preflight, single-transaction, reconciliation, and
failure-injection discipline. It must not dual-write financial history or migrate a shared database
at the same time as the C4 cutover.

## Recommended authorization and API boundary

`FinancialSpaceRef(PERSONAL, id)` resolves only to a `PersonalSpace`. The authenticated session actor
must equal its owner before the server resolves the internal book. Organization roles provide no
personal authority, and public clients never supply a book ID.

Future personal routes should live under `/api/v1/personal-spaces/{id}` and remain separate from
unchanged organization routes. The API may manage owner-scoped presentation data after its
persistence and isolation tests pass. Financial endpoints must remain gated until their required
M5.2-A policies are approved and implemented through the universal service.

## Feature-gate result

The plan carries the M5.2-A gates forward without treating them as solved:

- personal period model and late-entry behavior;
- default ledger chart and category mappings;
- income, expense, credit-card, and loan templates;
- opening-balance offset/date/grouping/evidence/history treatment;
- Cash Position inclusion and negative-balance presentation;
- account archive/inactive correction behavior; and
- historical recategorization behavior.

Cross-space transfers, tax/compliance, investments/valuation, multi-currency, household sharing,
budgets, reminders, AI transaction execution, bank integration, net worth, and automated interest or
amortization remain deferred.

## Exact implementation order

The plan defines these separately authorized stages:

1. **C0:** complete and observe M5.1-C4.
2. **C1:** make schema-v4 repository internals ownership-neutral while serving BUSINESS only.
3. **C2:** add schema-v5 personal ownership and constrained persistence with no public behavior.
4. **C3:** add owner-only resolver and atomic PersonalSpace/book provisioning.
5. **C4:** add FinancialAccount and category foundation without personal actuals.
6. **C5:** add typed personal proposal compilation and provenance behind closed gates.
7. **C6:** expose only separately approved personal lifecycle/read operations.
8. **C7:** complete migration, isolation, recovery, performance, and release verification.

Each stage preserves a stop point and an exact BUSINESS parity gate.

## Test and verification recommendation

The planned suite includes:

- v4→v5 migration parity, backup/restore, failure injection, and schema constraints;
- one-owner/one-book and owner-kind XOR enforcement;
- cross-user, cross-organization, wrong-route, wrong-book, wrong-account, wrong-category, wrong-
  proposal, wrong-entry, wrong-audit, cursor, cache, and idempotency substitution attacks;
- atomic account provisioning and no partially active mapping;
- versioned category mapping and immutable historical provenance;
- unbalanced/invalid/locked-period/stale-confirmation/duplicate/conflicting/reversal cases;
- direct ledger-to-report reconciliation and no mutable actual fields;
- default-deny and non-escalating feature gates; and
- complete unchanged BUSINESS API, CLI, fingerprint, audit, receipt, report, and frontend parity.

This planning milestone ran documentation/link/format checks only, as requested. Runtime, schema,
accounting, API, and frontend tests belong to the later authorized implementation milestones.

## Risks and missing prerequisites

- M5.1-C4 deployment execution and observation are not complete.
- The current shared repository contract still exposes organization-shaped records.
- Schema-v4 requires BUSINESS extension rows and BUSINESS actor/audit behavior.
- Atomic composition of a core ledger account and its presentation mapping needs a private service/
  unit-of-work seam; the personal adapter must not receive raw database access.
- Personal period and default chart/mapping policies block all personal postings.
- Opening balances block realistic historical onboarding until separately approved.
- Personal retention, deletion, recovery, ownership transfer, and account archive behavior are not
  approved.
- Proposal and reversal-proposal creation lack caller-key idempotency; payload equality is not an
  acceptable substitute.
- SQLite remains a local single-writer architecture, not a distributed production concurrency
  design.

## Decisions still requiring human or accountant input

Human product/privacy/legal decisions are still required for personal retention, deletion,
recovery, export, ownership transfer, sharing, category-name normalization, account archive, and
future combined-space experiences.

Qualified accounting decisions are still required for the personal period model, default chart and
category mappings, opening balances, initial loan recognition, principal/interest/fee allocation,
negative-balance presentation, Cash Position inclusion, historical reclassification, and every
personal/business movement classification.

This plan deliberately does not choose those policies.

## Readiness conclusion

The repository has an implementation-ready M5.2 foundation plan, but it is **not ready to implement
PERSONAL persistence until M5.1-C4 has completed and its observation gate has passed**. After that
prerequisite, the ownership-neutral refactor and schema-v5 foundation can proceed in the documented
order.

The repository does not currently support personal spaces, personal accounts, personal categories,
personal postings, or personal reports. This milestone does not claim otherwise.
