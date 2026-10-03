# M5.2-A personal finance policy report

**Date:** 2026-09-28  
**Project and product:** Chatbooks
**Result:** Policy boundary complete; no executable behavior or schema changed

## What was inspected

The review covered the repository rulebook; root and detailed architecture; accounting model;
security and AI boundaries; design and roadmap; the M5.0 personal model, decision register, and
specification report; the M5.1-A architecture and report; the M5.1-B implementation and migration
plans; C1, C2, C3, and C4A implementation/readiness reports; and personal/universal-core ADRs
0013–0020.

The current runtime remains schema v3. The universal financial service and BUSINESS compatibility
facade are implemented; canonical schema-v4 persistence has been proven only on disposable copies.
No normal v4 cutover, PersonalSpace, personal owner, personal API, personal UI, budget, reminder, or
AI capability exists.

## Architectural findings

- The universal service already provides the correct lifecycle for personal actuals: exact money,
  deterministic validation, exact-version confirmation, atomic posting, idempotency, reversal,
  immutable audit, and ledger-derived calculations.
- The personal MVP does not need a second transaction store, mutable balances, or different
  double-entry rules.
- Presentation accounts, categories, and personal report composition belong above the universal
  core. They map to same-book ledger records and retain immutable mapping provenance.
- `FinancialSpaceRef(PERSONAL, id)` and private `PersonalSpace` ownership remain the correct
  isolation boundary. Personal and business journals never mix.
- M5.1-C4 remains a prerequisite for ordinary canonical book writes. M5.2-A policy does not satisfy
  its deployment-copy, maintenance, security, monitoring, canary, or sign-off blockers.
- No new ADR is necessary. ADRs 0013–0020 already decide ownership, typed resolution, shared-ledger
  reuse, transfer coordination, categories, the persistent book seam, authorized adapters, and the
  compliance boundary. M5.2-A narrows product scope within those accepted boundaries.

## Product decisions made

- The personal promise is limited to money held, money received, money spent, money owed, and money
  moved between accounts.
- MVP presentation accounts are Checking, Savings, Cash, Credit Card, and Personal Loan.
- Starter expense categories are Food, Transport, Housing, Utilities, Shopping, Entertainment,
  Education, Healthcare, Subscriptions, and Other Expense. Starter income categories are Salary,
  Freelance, and Other Income. User-created categories are allowed.
- Personal periods stay out of normal navigation. The product does not expose close, lock, reopen,
  or adjustment workflows in the simple MVP.
- Default personal views are Balances, Activity, Income, Spending, Category Spending, and Cash
  Position. Formal business statements are advanced evidence rather than default personal views.
- Investment, valuation, household sharing, multi-currency, automation, tax, and compliance scope is
  excluded from the personal MVP.

These product choices do not approve ledger mappings or financial classification policy.

## Deterministic flow assessment

| Flow                 | Safe generic boundary                                                                        | Remaining gate                                                               |
| -------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Income               | Explicit asset destination plus approved income category compiles to a balanced proposal     | Default mapping and classification of ambiguous receipts                     |
| Expense              | Explicit payment/card account plus approved expense category compiles to a balanced proposal | Default mapping, capitalization, reimbursement, and tax treatment            |
| Same-space transfer  | Debit destination asset, credit source asset; no category or income/expense effect           | Fees, FX, investments, and third-party ownership excluded                    |
| Credit-card purchase | Expense line plus card-liability line                                                        | Accountant approval of default chart/template; refunds/fees/rewards deferred |
| Credit-card payment  | Card-liability reduction plus bank-asset reduction; no new spending                          | Overpayment and other exceptional treatment deferred                         |
| Loan payment         | Explicit principal reduces loan liability and bank asset                                     | Initial loan recognition and every component allocation                      |
| Opening balance      | Collect assertion/date/source and use ordinary proposal/audit lifecycle                      | Offset account, date/period, grouping, evidence, and prior-history treatment |
| Correction           | Full compensating reversal and optional separately confirmed replacement                     | Partial correction and historical recategorization deferred                  |

## Documentation changes

- Added [`M5_2_PERSONAL_FINANCE_MVP_POLICY.md`](M5_2_PERSONAL_FINANCE_MVP_POLICY.md) as the complete
  operation, account, category, reporting, compatibility, exclusion, and policy-gate contract.
- Updated the accounting model to distinguish safe generic personal mechanics from unapproved
  accounting mappings.
- Updated root and detailed architecture to show M5.2-A as a policy layer with no runtime effect.
- Updated design guidance with the simple personal vocabulary and gated-flow rules.
- Updated the roadmap to record M5.2-A and keep personal implementation, C4, budgets, reminders, and
  AI unimplemented.

## What M5.2 can safely implement generically

After separate implementation authorization and the required canonical BUSINESS cutover gates,
M5.2 can add private PersonalSpace ownership; PERSONAL resolution; presentation accounts; category
and versioned-mapping infrastructure; reuse of the existing proposal/post/reversal/audit lifecycle;
same-space asset transfers; explicit principal-only liability reductions; ledger-derived balances
and Activity; and personal read-model infrastructure over posted core data.

The system can also collect the non-financial inputs for an opening-balance batch, but it cannot
generate or post its financial proposal without an approved offset and period policy.

## What remains gated

- Income, expense, and credit-card templates until the default chart and category mappings are
  approved.
- Any personal posting until a personal period creation/coverage policy is approved.
- Opening-balance posting until offset, date, grouping, evidence, and prior-period treatment are
  approved.
- Loan onboarding and any payment whose principal/interest/fee/penalty/tax split is not explicit.
- Category Income/Spending reports until their mappings and exceptional-item rules are approved.
- Cash Position until included account kinds and negative/overdrawn behavior are approved.
- Personal/business movement until each side's contribution, drawing, salary, distribution,
  reimbursement, or loan classification is approved.
- Executable personal work until M5.1-C4's deployment-specific blockers and separate authorization
  are resolved.

## What is permanently excluded from this MVP

Investments and valuation, net-worth valuation, household or advisor sharing, multiple personal
spaces, multi-currency and FX, automatic interest/amortization/fee allocation, bank automation,
automatic posting, tax, VAT/GST, withholding, payroll, statutory reporting, filing, and
country-specific compliance are outside the simplified personal MVP.

Budgets, reminders, recurrence, goals, documents/extraction, and AI remain later milestones. Their
future compatibility is documented, but they are not personal MVP functionality.

## Accountant input still required

A qualified accountant or domain owner must approve the personal default chart; starter-category
mappings; personal period behavior; opening-balance offset/date/grouping/evidence treatment;
classification of ambiguous receipts and payments; credit-card templates and exceptions; initial
loan recognition and component allocation; cross-space classifications on both sides; negative and
overdrawn presentation; cash-position inclusion; correction versus recategorization; and any future
valuation, currency, tax, statutory, or jurisdiction-specific rule.

No listed item has an implied default, and M5.2-A does not claim that approval has occurred.

## Verification and readiness

Only documentation checks were run for this policy milestone, as required:

| Check                     | Result                                                                                             |
| ------------------------- | -------------------------------------------------------------------------------------------------- |
| Required policy structure | Passed: all 19 required sections present                                                           |
| Decision classification   | Passed: ENGINEERING, PRODUCT, and ACCOUNTING POLICY are explicit                                   |
| Local Markdown links      | Passed: 191 links across 54 project Markdown files; 0 broken                                       |
| Markdown formatting       | Passed: all 9 changed policy/architecture/design/roadmap files match the repository Prettier style |
| Change-scope scan         | Passed: only Markdown documentation files changed; no executable or schema file changed            |

Python, API, frontend, type, lint, and database tests were not run because the milestone explicitly
requires documentation checks only and changes no executable behavior.

The repository is ready to use this policy as input to a separately authorized M5.2 implementation
plan. It is not ready to enable personal posting: schema-v4 business cutover, PersonalSpace design
and migration, isolation tests, and the accounting-policy gates above remain incomplete.
