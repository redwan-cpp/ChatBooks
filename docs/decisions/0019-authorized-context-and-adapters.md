# ADR 0019: Authorized context feeds business and personal adapters

**Date:** 2026-09-26  
**Status:** Accepted; BUSINESS context/service and both v3/v4 adapters implemented; PERSONAL adapter deferred

## Context

ADR 0009 and ADR 0014 define typed Financial Space resolution. ADR 0015 chooses a personal adapter
over shared deterministic rules. M5.1-A must define where authorization ends and universal financial
logic begins while preserving the current API.

## Decision

An application `FinancialSpaceResolver` derives the actor from authentication, resolves exactly one
typed BUSINESS or PERSONAL space, authorizes membership/role or personal ownership/grant, and issues
an internal `AuthorizedFinancialContext`. The context contains the actor, space, resolved LedgerBook,
currency/precision, capabilities, request provenance, and an optional business project.

The existing `AccountingEngine` and organization API become the business compatibility facade. A
future `PersonalAccountingAdapter` maps approved user-facing accounts/categories to explicit lines.
Both call one ownership-neutral deterministic financial service. The service owns proposal
validation, confirmation checks, posting, reversal, balances, audit, and receipt atomicity. Adapters
cannot write journal rows or calculate authoritative totals.

No API accepts a client-supplied ledger-book ID as authority. Organization routes resolve only
organizations; personal routes resolve only personal spaces.

## Alternatives considered

### Put ownership branching inside every core method

Rejected because it mixes membership/product policy with ledger invariants and makes every operation
responsible for two authorization models.

### Let routes call storage after authorization

Rejected because route-specific writes could bypass the universal lifecycle and atomic audit.

### Use one polymorphic route family for both kinds

Rejected because it increases ID-substitution risk and weakens compatibility of existing business
routes.

## Consequences

- The business API can retain paths, payloads, roles, and results.
- Personal ownership stays independent of organization membership.
- Future AI receives only a server-issued context and proposal tools.
- Resolver, adapter, service, and database each receive focused isolation tests.
- M5.1-C1 implements membership-first BUSINESS organization-to-book resolution.
- M5.1-C2 implements immutable `AuthorizedFinancialContext`, explicit capabilities, the universal
  deterministic service, typed repository/unit-of-work protocols, the schema-v3 organization
  adapter, and the `AccountingEngine` BUSINESS compatibility facade.
- M5.1-C3 implements the schema-v4 `SQLiteBookStorage` adapter behind the same service and context.
  The business facade and API contracts remain stable; only explicit rehearsal factories select the
  v4 adapter, so normal startup cannot accidentally perform the C4 cutover.
- M5.1-C4A exercises both adapters against the same synthetic business fixture and proves exact
  engine/API/CLI read parity. It does not expose canonical selection or book authority to clients.
- Personal ownership resolution and `PersonalAccountingAdapter` remain deferred. Public clients do
  not receive or construct the internal context.

**Classification:** ENGINEERING DECISION.
