# M5 personal finance decisions

**Date:** 2026-09-26  
**Status:** M5.0 specification decisions, refined by M5.2-A. No implementation is authorized by this
document.

This register separates software architecture that Chatbooks can decide from product and accounting
policy that requires an explicit human decision. The detailed proposed model is in
[`personal-finance-model.md`](personal-finance-model.md).

M5.2-A resolves one narrow product question for the simplified MVP: personal categories use both a
curated starter taxonomy and user-created income/expense categories. It also selects the five MVP
presentation account kinds and the default personal report set. It does not approve the ledger
accounts behind categories, personal period policy, opening-balance treatment, liability mappings,
cash-position inclusion, or cross-space classifications. See
[`M5_2_PERSONAL_FINANCE_MVP_POLICY.md`](M5_2_PERSONAL_FINANCE_MVP_POLICY.md).

# 1. ENGINEERING DECISIONS

## E1. Personal ownership is a separate aggregate

`PersonalSpace` is a stable, first-class ownership boundary. In the initial model, one authenticated
user owns exactly one private personal space. `owner_user_id` is unique. Personal data is not stored
as an organization and does not use organization memberships or roles.

Future household, dependant, guardian, or advisor access must use an explicit personal-sharing model
or a distinct household owner. It cannot be inferred from business access.

**ADR:** [0013](decisions/0013-personal-ownership-isolation.md)

## E2. Financial Space remains a tagged resolver

`FinancialSpaceRef(kind, id)` remains an application reference:

- `BUSINESS` + ID resolves to the existing organization domain.
- `PERSONAL` + ID resolves to `PersonalSpace`.
- A project is an optional child dimension of a business space.

No global Financial Space parent table is required for discovery. A future discovery endpoint returns
a typed union read model. Existing organization routes remain business-only.

**ADR:** [0014](decisions/0014-personal-financial-space-resolution.md)

## E3. Actual personal money uses the guarded ledger lifecycle

Personal income, expense, balances, liabilities, transfers, opening balances, and corrections use
proposal → deterministic validation → exact-version authenticated confirmation → atomic posting →
ledger/report/audit. Mutable personal records cannot maintain independent actual balances.

The accounting rules are reusable. The current engine is not directly reusable as-is because its
ownership, authorization, periods, foreign keys, receipts, and audit are organization-scoped. A
future `PersonalAccountingAdapter` will resolve a personal space to an internal ledger book and call
an ownership-neutral deterministic ledger service. The business engine remains a compatibility
facade. No fake organization or duplicate/weaker accounting engine is permitted.

M5.1-A refines this decision: `LedgerBook` is a persistent internal entity and the canonical future
financial ownership scope. Business and personal adapters authorize an owner, obtain a server-issued
financial context, and call one deterministic service. Migration is staged and must prove business
history, constraint, report, audit, and receipt parity before personal writes are enabled. See
[ADR 0018](decisions/0018-persistent-ledger-book-seam.md) and
[ADR 0019](decisions/0019-authorized-context-and-adapters.md).

**ADR:** [0015](decisions/0015-personal-ledger-adapter.md)

## E4. Personal accounts are presentation objects linked to ledger accounts

`PersonalAccount` holds user-facing account kind and metadata and maps to one owned ledger account.
Its balance is always derived from posted lines. Cash, checking, savings, credit-card liability,
personal-loan liability, and installment liability are the proposed MVP kinds. Investment valuation
is deferred.

## E5. Categories are separate records with versioned mappings

`PersonalCategory` is an owner-scoped user label. A versioned mapping resolves it to an owned income
or expense ledger account at proposal creation. The proposal/post retains the mapping provenance.
Renaming or remapping does not rewrite history. Transfers do not use income/expense categories.

**ADR:** [0017](decisions/0017-personal-category-mapping.md)

## E6. Same-space and cross-space transfers are different workflows

A transfer between accounts in one personal space is one balanced entry and is excluded from income
and expense. A personal/business movement produces two independently authorized, validated,
confirmed, and posted effects plus a non-financial correlation. It cannot be a cross-space journal or
a distributed transaction that deletes a committed side.

**ADR:** [0016](decisions/0016-cross-space-transfer-coordination.md)

## E7. Opening balances are proposals, not mutable fields

An opening-balance batch records date, source, evidence references, actor, system timestamp, and
generated proposal/entry IDs. Approved balances post through the ordinary lifecycle. Corrections use
reversal and replacement. The accounting lines remain blocked until the offset and period policy is
approved.

## E8. Personal liabilities remain ledger-derived

Credit cards, loans, and installment debt map to liability ledger accounts. Payments are explicit
transfer-style proposals. Chatbooks does not calculate interest, amortization, fees, penalties, or
principal splits in the initial model.

## E9. Personal reporting uses dedicated read models

The default personal reports are account balances, money activity, spending, income, category
spending, and cash position. They derive from posted personal lines. Formal business statements do
not become the default personal UI. Net worth remains a later report behind valuation decisions.

## E10. Privacy is enforced at the backend owner boundary

Every personal route authenticates the actor, resolves the exact personal space, checks owner access,
and loads all child records through that owner key. Frontend selection is never authority. Business
membership never grants personal visibility. The boundary applies to records, counts, caches, logs,
exports, documents, notifications, conversations, and future AI retrieval.

## E11. Existing business behavior remains unchanged

No current organization ID, route, role, foreign key, proposal, journal, audit row, or report is
reinterpreted. M5.0 adds documentation only. A future migration must preserve all business history,
constraints, and results and must run the complete business suite before enabling personal writes.

## E12. Plans and schedules remain outside actuals

Future personal budgets, reminders, recurring templates, and goals reference the personal space but
have no direct ledger effect. Actuals and goal progress derive from posted records through approved
mappings. A schedule may create a proposal occurrence; it cannot confirm or post.

## E13. Future AI receives a server-resolved context envelope

Future AI tools receive a typed space, currency/precision, authenticated capabilities, optional
business project, date scope, and provenance from the application. Conversation text cannot select
or authorize another space. AI remains proposal-only for financial writes.

# 2. HUMAN / ACCOUNTANT DECISIONS

No item below has an implied default. A decision must identify its owner, rationale, effective scope,
and required tests before implementation.

## Product, privacy, and authorization decisions

| ID  | Decision needed                                                                              | Why software must not assume it                                                                                 | Blocks                                  |
| --- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| H1  | Whether one personal space per user is permanent or only the MVP limit                       | Multiple spaces change onboarding, uniqueness, selection, export, and recovery                                  | Multiple-space support                  |
| H2  | Household ownership and sharing model                                                        | Joint ownership, household membership, dependants, guardians, and consent have different legal/privacy meanings | Household finance                       |
| H3  | Advisor/accountant access roles and revocation                                               | Business `ACCOUNTANT` authority cannot be reused; personal access needs explicit consent and least privilege    | Delegated personal access               |
| H4  | Export, deletion, retention, and account-recovery effects                                    | Financial/audit retention and privacy deletion duties can conflict and vary by jurisdiction                     | Production personal data                |
| H5  | Personal display name, locale, time zone, and date-boundary policy                           | Scheduling and reports depend on an approved user time basis                                                    | Reminders, recurrence, period UX        |
| H6  | Category lifecycle beyond the M5.2-A choice of curated starters plus user-created categories | Duplicate names, rename/archive UX, locale, and taxonomy evolution remain product choices                       | Category lifecycle after MVP onboarding |
| H7  | Whether historical display recategorization is allowed                                       | It affects comparability and audit expectations even when ledger lines stay unchanged                           | Recategorization UI                     |
| H8  | Whether personal confirmations can be coordinated with business confirmations                | One gesture may still need two legally and technically distinct acceptances                                     | Cross-space UX                          |
| H9  | Evidence requirements for opening balances and imports                                       | Requiring statements or allowing self-attestation is a product/risk decision                                    | Opening-balance posting                 |
| H10 | Who may see advanced journal and audit detail in personal spaces                             | Full fidelity helps support/accountants but may expose sensitive internal data                                  | Advanced personal views                 |

## Accounting and financial-policy decisions

| ID  | Decision needed                                                                       | Why accountant approval is required                                                                                                            | Blocks                            |
| --- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| A1  | Personal accounting basis and jurisdictional intent                                   | Tax, recognition, and report meaning vary; the platform cannot infer them                                                                      | Formal personal accounting claims |
| A2  | Personal period model                                                                 | The current kernel requires open periods; hidden continuous periods, calendar periods, locks, and late corrections have different consequences | Personal posting adapter          |
| A3  | Opening-balance offset treatment                                                      | Existing bank and liability balances need an approved balancing account and treatment of prior income/equity                                   | Opening-balance posting           |
| A4  | Opening date and batch grouping                                                       | One common date versus account-specific dates changes historical reports                                                                       | Opening-balance workflow          |
| A5  | Default personal chart/account mapping                                                | Income, expenses, assets, liabilities, equity, and category mappings must be reviewed before templates create lines                            | Personal onboarding and posting   |
| A6  | Personal contribution, gift, refund, reimbursement, and loan classification           | Similar cash movement can have materially different meaning                                                                                    | Proposal templates and reports    |
| A7  | Personal-to-business contribution treatment on both sides                             | Business capital, director/shareholder loan, or other treatment depends on legal/entity context                                                | Cross-space contribution          |
| A8  | Business-to-personal drawing, distribution, salary, reimbursement, and loan treatment | The correct accounts and possible tax/payroll treatment cannot be inferred from direction alone                                                | Cross-space withdrawal            |
| A9  | Credit-card purchase and payment presentation                                         | Liability, expense timing, refunds, statement cycles, and pending activity need explicit semantics                                             | Credit-card UX                    |
| A10 | Loan principal, interest, fee, tax, and penalty splits                                | Calculating or inferring a split would invent financial policy                                                                                 | Loan payments and summaries       |
| A11 | Investment cost, valuation, income, gains/losses, and transfer treatment              | Market value and realized/unrealized results require a valuation policy and source                                                             | Investment accounts and net worth |
| A12 | Net-worth inclusion and valuation policy                                              | Non-cash assets, business interests, joint property, and stale values cannot be safely combined by default                                     | Net-worth report                  |
| A13 | Cash-position account inclusion                                                       | Not every asset is liquid cash; overdrafts and restricted funds need treatment                                                                 | Cash-position report              |
| A14 | Category mapping rules for split, fee, tax, cashback, and transfer lines              | These affect spending/income summaries and cannot be derived from labels alone                                                                 | Category reports                  |
| A15 | Negative and overdrawn account presentation                                           | An asset with a credit balance may need liability presentation or an explicit warning                                                          | Personal balance UX               |
| A16 | Personal correction and recategorization policy                                       | Some changes require a reversal/repost; others may be non-financial classification amendments                                                  | Editing/correction workflow       |
| A17 | Currency, foreign account, exchange-rate, and revaluation policy                      | Exact conversion source, rate date, rounding, and gain/loss treatment are undefined                                                            | Multi-currency personal finance   |

## Later budget, reminder, and automation decisions

| ID  | Decision needed                                                                           | Blocks                                            |
| --- | ----------------------------------------------------------------------------------------- | ------------------------------------------------- |
| L1  | Budget period, scope, rollover, amendment history, overspend meaning, and enforcement     | M7 budgets                                        |
| L2  | Budget/category/account mapping and treatment of transfers/refunds                        | Budget actuals                                    |
| L3  | Reminder recurrence, time zone, missed occurrence, completion, and notification semantics | M7 reminders                                      |
| L4  | Recurring-proposal occurrence identity, edits, catch-up, and duplicate prevention         | Recurring templates                               |
| L5  | Whether any future automation may post without per-item confirmation                      | Automation; requires a separate authorization ADR |
| L6  | Goal contribution, withdrawal, progress, and account-selection rules                      | Financial goals                                   |

## Decision process

For every approved item:

1. record the decision and approver in this register or a dedicated policy document;
2. add or update an ADR when it changes an architectural boundary;
3. update the accounting model and API/domain requirements;
4. define deterministic examples and failure cases;
5. add database constraints and tests where the rule is enforceable; and
6. preserve reversal, audit, and historical visibility.
