# M5.1-A universal financial core architecture report

**Date:** 2026-09-26  
**Milestone:** Architecture and domain design only  
**Result:** Complete; no executable code, database schema, migration, endpoint, or UI was changed

## Repository review

The review covered the project rulebook, README, requirements, architecture, design, process,
security, accounting model, AI boundary, roadmap, all ADRs, M3/M3.5/M4/M5.0 reports, the M5 personal
decision register, Python package and CLI configuration, domain values, authentication, permissions,
FastAPI contracts/routes, accounting engine, SQLite connection/audit setup, schema and v1→v2
migration, all Python tests, and the M4 frontend Financial Space/API/test boundaries.

The current system remains a hardened business accounting implementation. `organization_id` is
embedded in membership authorization, core foreign keys, period enforcement, proposal and
confirmation provenance, posting triggers, audit, receipts, reports, projects, and documents. The
accounting rules are reusable; that ownership plumbing is not safely reusable for personal finance
without a persisted neutral seam.

## Architecture options and selection

Three approaches were compared:

1. **Separate personal and business ledgers** avoids immediate business migration but duplicates
   accounting logic, constraints, adversarial tests, and future AI tools. It was rejected.
2. **One-step replacement with generic tables** gives a clean final model but combines every schema,
   trigger, service, migration, and API compatibility risk in one cutover. It was rejected as a
   migration strategy.
3. **Phased convergence on a persistent LedgerBook and one deterministic service** introduces a
   mapping and service seam first, then migrates canonical financial tables behind parity gates, and
   enables personal writes last. It was selected.

An internal-only book identifier with permanent separate storage adapters was considered as a fourth
variant. It can help extract the service temporarily, but was rejected as the target because database
invariants would remain duplicated.

**Classification:** ENGINEERING DECISION.

## Selected universal core

Financial Space remains the typed product/application context:

```text
BUSINESS + Organization.id → authorized Organization → LedgerBook
PERSONAL + PersonalSpace.id → authorized PersonalSpace → LedgerBook
```

`LedgerBook` is a persisted internal entity and domain identifier with exactly one typed owner,
currency, precision, and creation provenance. It is the future canonical scope for charts/accounts,
periods, proposals/lines, validations, confirmations/provenance, journal entries/lines, financial
audit, and idempotency receipts.

The backend authenticates first, resolves the typed space, checks membership/role or personal
ownership/grant, and issues an internal `AuthorizedFinancialContext`. Clients never supply a raw
book ID as authority. Composite book-scoped keys and posting triggers prevent cross-book references.

**Classification:** ENGINEERING DECISION.

## Facade and adapter boundary

The existing `AccountingEngine` and organization FastAPI routes remain the business compatibility
facade. A future personal adapter translates approved personal account/category input to explicit
ledger lines. Both call one ownership-neutral deterministic service.

The deterministic service owns proposal validation, exact-version confirmation checks, atomic
posting, compensating reversal, balances, report primitives, immutable audit, and idempotent command
results. Facades/adapters own authorization, product terminology, and approved mappings only. They
cannot write journal rows or calculate authoritative totals.

**Classification:** ENGINEERING DECISION.

## Business compatibility and migration

The future migration must preserve organization IDs, routes, memberships, roles, project IDs,
account/period/proposal/validation/confirmation/journal/line IDs, posted history, reversals, audit
sequences and payloads, idempotency keys/results, report values, and database integrity.

The recommended sequence is:

1. run preflight foreign-key, balance, fingerprint, proposal-match, audit, receipt, and report checks;
2. add one BUSINESS ledger-book mapping per organization without changing organization IDs;
3. extract an internal core service while the compatibility repository still uses current tables;
4. construct book-scoped canonical tables and equivalent triggers in a later schema step;
5. copy records without changing IDs/state and preserve audit timestamps/payloads/sequences;
6. move project/document associations into constrained business extensions;
7. reconcile every row, balance, report, reversal, receipt, and audit event before atomic cutover;
8. fail and roll back rather than partially convert; and
9. enable personal writes only after compatibility and cross-scope security evidence passes.

An additive mapping version followed by a separate canonical-table version is safer than one large
v2→v3 rewrite. Exact schema-version numbers and DDL belong to M5.1-B planning.

**Classification:** ENGINEERING DECISION.

## Personal integration

PersonalSpace remains a private owner independent of organizations. The initial design maps one user
to one PersonalSpace and one book. Personal accounts are presentation records mapped one-to-one to
same-book asset/liability accounts for the initial model. Categories remain separate labels with
versioned income/expense-account mappings and immutable proposal/posting provenance.

Business membership never grants personal access. Personal routes cannot resolve organizations;
organization routes cannot resolve personal spaces. Audit and idempotency follow the same book scope
as the financial operation.

The ownership, sharing, household, advisor, export, deletion, retention, and recovery model beyond
the private initial space remains a **PRODUCT DECISION**.

The default personal chart, category/account mappings, negative-balance presentation, and correction
semantics remain **ACCOUNTING POLICY**.

## Financial Activity and money flows

Financial Activity is not a persisted financial aggregate. It is typed application command
vocabulary and a posted read model. Commands such as money in, money out, same-space transfer,
liability event, opening balance, and correction compile to explicit proposals. Posted amounts and
balances remain journal-derived.

The core does not infer income or expense from cash direction. Money in may be income, liability,
equity/contribution, refund, or transfer; money out may be expense, asset acquisition, repayment,
reimbursement, or transfer. Liability principal, interest, fees, penalties, tax, and due-date
behavior require explicit inputs and approved policy.

Same-space transfer remains one balanced effect. Cross-space transfer remains two independently
authorized and confirmed effects plus a non-financial correlation. Partial completion recovers by
retry or explicit reversal, never deletion.

The command/read-model choice and two-effect coordination are **ENGINEERING DECISIONS**. Customer
terminology and coordinated confirmation UX are **PRODUCT DECISIONS**. Contributions, drawings,
salary, distributions, reimbursements, loans, opening-balance offsets, and liability splits are
**ACCOUNTING POLICY**.

## Proposal, periods, plans, and reporting

Both ownership domains use proposal → deterministic validation → authenticated exact-version
confirmation → current-state revalidation → atomic post/audit/receipt. AI and external policy layers
remain proposal-only.

The core retains explicit, non-overlapping, book-scoped periods and open/lock enforcement. Current
business behavior remains unchanged. A personal calendar-month, continuous-open, auto-created, or
other period model was not selected. Period capability is an **ENGINEERING DECISION**; personal
period UX is a **PRODUCT DECISION**; closing, late-entry, adjustment, and reopening rules are
**ACCOUNTING POLICY**.

Budgets, goals, reminders, recurring schedules, expected revenue, and project budgets remain mutable
planning records outside posted actuals. Their actuals derive from core data. Schedules may create
idempotently identified proposals but cannot confirm or post.

Core reporting owns exact ledger lines, journal summaries, account balances, trial-balance
arithmetic, neutral account/date aggregates, selected-account cash movements, and lifecycle evidence.
Business and personal read-model layers own terminology and composition. Statutory/tax presentation
is external. This split is an **ENGINEERING DECISION**; cash inclusion, formal recognition,
valuation, and statutory mapping are **ACCOUNTING POLICY**.

## Jurisdiction and compliance boundary

Tax, VAT/GST, withholding, payroll compliance, statutory charts/statements, filing, regulator
integration, and country-specific recognition or depreciation do not belong in the universal core.
A future jurisdiction package may consume authorized versioned read models and must record rule-set,
effective date, source, and calculation provenance. Any adjustment is an ordinary proposal.

Layer separation is an **ENGINEERING DECISION**. Whether Chatbooks offers such a package and what
it claims are **PRODUCT/LEGAL DECISIONS**. Every tax, statutory, filing, and recognition rule is
**ACCOUNTING/DOMAIN POLICY**.

## Security findings

The architecture requires three independent controls: typed route/space resolution, authorized
service context, and book-scoped database constraints. Frontend context remains presentation only.

The threat model covers cross-kind ID substitution, raw book IDs, cross-book child references,
cross-space transfer disclosure, audit visibility, caches, searches, exports, logs, notifications,
background jobs, documents, and future AI retrieval. Each key or job includes space kind, owner ID,
and book scope; missing scope fails closed. Cross-space correlation reveals only the authorized local
side and minimal status.

Migration preserves immutable audit evidence and cannot dual-write posted history. A balanced book
does not establish tax or statutory compliance.

**Classification:** ENGINEERING DECISION for controls; PRODUCT/PRIVACY DECISION for sharing,
retention, export, recovery, and combined views.

## Future AI context

The future AI receives a server-issued Financial Context with typed Financial Space, display name,
currency/precision, authenticated capabilities, optional business organization/project, date scope,
allowed sources, and request/retrieval provenance. An internal book capability may be attached by the
server but is not chosen or treated as authority by the model.

AI may retrieve authorized results, explain them, ask questions, and create proposals. It cannot
select another space from conversation text, combine spaces implicitly, calculate authoritative
totals outside the core, confirm, post, reverse, lock, edit audit, or access storage.

**Classification:** ENGINEERING DECISION for the authority boundary; PRODUCT/PRIVACY DECISION for
conversation retention, explanations, and combined-space experience.

## ADRs

- [ADR 0018](decisions/0018-persistent-ledger-book-seam.md) selects the persistent book and phased
  migration.
- [ADR 0019](decisions/0019-authorized-context-and-adapters.md) selects the resolver,
  compatibility-facade, personal-adapter, and universal-service boundary.
- [ADR 0020](decisions/0020-jurisdiction-compliance-outside-core.md) keeps jurisdiction and
  compliance outside the core.

ADRs 0009 and 0014 already decide typed Financial Space resolution, so no duplicate ADR was created.
ADR 0015 already establishes the personal adapter; ADR 0019 refines the shared call boundary.

## Decisions still required

### Product decisions

- permanent one-space limit, household/joint/dependant ownership, advisor access, consent, revocation,
  export, deletion, retention, and recovery;
- personal account/category taxonomy and Financial Activity terminology;
- cross-space confirmation and partial-completion experience;
- personal period visibility and automatic creation;
- budgets, goals, reminders, recurrence, and automation behavior;
- future compliance product claims and professional-review requirements; and
- combined-space views, AI retention, and conversation privacy.

### Accounting policies

- personal period/close/late-entry/reopening model;
- opening-balance offset, date, grouping, evidence, and prior-period treatment;
- default chart and category/account mappings;
- contributions, drawings, distributions, salary, reimbursements, and loans on both sides;
- credit-card, liability principal/interest/fee/penalty, and negative-balance treatment;
- correction versus display recategorization;
- cash-position inclusion, income/expense recognition, valuation, and net worth;
- multi-currency, FX, rates, rounding, precision change, and revaluation; and
- every tax, statutory, payroll, filing, and jurisdiction rule.

## Verification

| Check                    | Result                                                     |
| ------------------------ | ---------------------------------------------------------- |
| Python tests             | Passed: 56                                                 |
| mypy                     | Passed: 11 application source files                        |
| Ruff lint                | Passed                                                     |
| Ruff formatting          | Passed: 60 files already formatted                         |
| Frontend Vitest          | Passed: 10 tests in 1 file                                 |
| Frontend TypeScript      | Passed                                                     |
| Frontend ESLint          | Passed                                                     |
| Frontend Prettier        | Passed                                                     |
| Next.js production build | Passed: all routes generated                               |
| Documentation links      | Passed: 138 local links across 44 Markdown files; 0 broken |

## Readiness and stop point

M5.1-A is complete as architecture. The repository is ready for a separately authorized M5.1-B
implementation plan, not for immediate personal posting. M5.1-B must define exact migration DDL,
rollback/recovery, service extraction order, compatibility tests, and policy gates before changing
the proven business system.

PersonalSpace tables, LedgerBook migration, personal API/UI, plans, schedules, documents, AI, bank
integration, tax, and compliance were intentionally not built. Work stops at the architecture
boundary.
