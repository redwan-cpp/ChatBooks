# M5.2-A simplified personal finance MVP policy

**Date:** 2026-09-28  
**Milestone:** Policy and implementation constraints only  
**Project and product:** Chatbooks
**Status:** Approved product boundary; no executable code, schema, PersonalSpace, API, or UI is
implemented by this milestone

## Decision classification

Every rule in this document uses one of three classifications:

- **ENGINEERING** defines deterministic representation, isolation, validation, persistence, audit,
  or calculation behavior.
- **PRODUCT** defines what the MVP presents, asks from the user, includes, or defers.
- **ACCOUNTING POLICY** defines a financial classification or treatment that must be approved by a
  qualified accountant or domain owner before the related template or posting is enabled.

An engineering mechanism does not approve an accounting policy. A product label does not determine
ledger treatment. Where a rule needs policy that has not been approved, the operation remains
feature-gated and fails closed.

## 1. Product promise

Chatbooks personal finance helps an ordinary user answer five questions:

1. What money do I have?
2. Where did it come from?
3. Where did it go?
4. What do I owe?
5. What moved between my accounts?

The MVP uses the smallest deterministic model that can answer those questions from posted financial
activity. It is not a miniature ERP, tax product, statutory accounting system, investment tracker,
or automated financial adviser. Normal screens use Accounts, Income, Spending, Transfers,
Categories, Balances, and Activity. Ledger accounts, debits, credits, proposals, and audit evidence
remain available through progressive disclosure.

**PRODUCT:** Simplicity and the six MVP reports in section 13 define the customer promise.

**ENGINEERING:** Posted journal lines remain the only source of actual balances and totals. Exact
integer money, one currency per book, deterministic validation, explicit confirmation, atomic
posting, compensating reversal, and immutable audit remain mandatory.

## 2. Personal domain model

The implementation target remains the model selected by M5.0 and M5.1:

```text
User
└── owns PersonalSpace
    ├── LedgerBook                    financial truth
    ├── FinancialAccount             presentation for an asset or liability account
    ├── PersonalCategory             user-facing income or expense label
    ├── CategoryAccountMapping       versioned deterministic mapping
    ├── FinancialActivity command    creates an explicit proposal
    └── FinancialActivity read model derives from posted entries
```

`FinancialSpaceRef(PERSONAL, personal_space_id)` is the required application context. The server
authenticates the user, verifies personal ownership, resolves the book, and issues the internal
authorized context. Organization roles grant no personal access. Projects remain business-only.

**ENGINEERING:** Personal and business records, authorization, reports, caches, conversations,
audit, and future AI context remain isolated. No journal spans books or spaces.

**PRODUCT:** The first personal MVP is one private personal space per user. Household sharing,
advisor access, dependants, and multiple personal spaces remain deferred.

## 3. Account model

The user sees a `FinancialAccount`, not a chart-of-accounts row. MVP kinds are:

| User-facing kind | Core classification | MVP meaning                                           |
| ---------------- | ------------------- | ----------------------------------------------------- |
| Checking         | Asset               | Spendable money held at a bank or similar institution |
| Savings          | Asset               | Money held separately for saving                      |
| Cash             | Asset               | Physical cash controlled by the user                  |
| Credit card      | Liability           | Amount owed for card activity                         |
| Personal loan    | Liability           | Explicit outstanding principal tracked by the user    |

Minimum presentation metadata is a stable ID, personal-space ID, display name, kind, active/archived
state, linked same-book ledger account ID, and immutable creation provenance. Institution name and a
masked account reference are optional display metadata. Full account numbers, credentials, credit
limits, statements, interest rates, due dates, and schedules are outside the MVP account record.

The account never stores an authoritative mutable balance. Its balance is calculated from posted
lines for the linked ledger account. Archiving hides it from new entry selection but retains all
history. A new posting cannot use an inactive underlying account.

**PRODUCT:** Onboarding asks for account name and one of the five kinds. Accounting terms are hidden
by default.

**ENGINEERING:** Each presentation account maps to one same-book asset or liability account. The
mapping is ownership-constrained and auditable.

**ACCOUNTING POLICY:** The exact default chart, account codes, normal-balance warnings, overdraft
presentation, and any use of equity or contra accounts require approval before templates are
enabled.

## 4. Category model

Categories describe why money came in or went out. They do not represent where money is held and do
not store totals.

The MVP starter taxonomy is a **PRODUCT** choice:

| Direction | Starter categories                                                                                                |
| --------- | ----------------------------------------------------------------------------------------------------------------- |
| Expense   | Food, Transport, Housing, Utilities, Shopping, Entertainment, Education, Healthcare, Subscriptions, Other Expense |
| Income    | Salary, Freelance, Other Income                                                                                   |

Users may create additional income or expense categories, rename categories, and archive categories.
A category has a stable ID, personal-space ID, name, direction, origin (`SYSTEM` or `USER`), and
active state. Names are unique within direction for one personal space. A transfer has no income or
expense category.

Each category resolves through a versioned `CategoryAccountMapping` to a same-book income or expense
ledger account. Proposal provenance captures category ID, mapping version, and the display label used
for review. Renaming a category changes future selection and may show the current label in catalog
views; it does not change the captured label, mapping version, ledger account, or financial meaning
of posted history. Remapping affects future proposals only. Historical financial reclassification
requires an approved correction process and never edits a posted line.

**ENGINEERING:** Stable IDs, direction, versioned same-book mappings, immutable proposal provenance,
and ledger-derived category totals are mandatory.

**PRODUCT:** The starter labels and user-created-category capability are part of the MVP.

**ACCOUNTING POLICY:** The ledger accounts behind starter or user-created categories, and treatment
of refunds, cashback, split purchases, fees, and reclassification, require approved mappings.

## 5. Income semantics

**User-facing meaning:** Money received into a personal asset account that the user explicitly
classifies as income. A transfer, loan proceeds, refund, reimbursement, gift, contribution, or other
ambiguous receipt must not be labeled income merely because money arrived.

**Required input:** Personal space, destination Checking/Savings/Cash account, amount, currency
context, financial date, income category, description, and authenticated confirmation. Optional
source text is provenance, not classification authority.

**Underlying proposal shape:** One debit to the destination asset account and one credit to the
approved income account mapped from the selected category. Additional lines are outside the simple
MVP template.

**Ledger effect:** The asset balance increases and the mapped income balance increases by the exact
same minor-unit amount.

**Reporting effect:** The event appears in Activity and Income and contributes to the selected
income category. It does not appear as a transfer.

**Audit:** Retain space, account, category and mapping version, amount, date, description, proposal
and version, validation fingerprint, authenticated confirmation, request/idempotency IDs, posted
entry, actor, timestamps, and source provenance.

**Classification:** Proposal lifecycle and arithmetic are **ENGINEERING**. The plain-language flow
and required fields are **PRODUCT**. Default category-to-income-account mappings and whether a
specific receipt is income are **ACCOUNTING POLICY**. The template remains disabled until its
mapping is approved.

## 6. Expense semantics

**User-facing meaning:** Money spent for a selected personal expense category, paid from an asset
account or charged to a credit card.

**Required input:** Personal space, payment account, amount, currency context, financial date,
expense category, description, and authenticated confirmation.

**Underlying proposal shape:** Debit the approved expense account mapped from the category. Credit
the selected asset account for a cash/bank payment or the selected credit-card liability for a card
purchase.

**Ledger effect:** The selected asset decreases or the selected card liability increases, while the
mapped expense increases by the same amount.

**Reporting effect:** The event appears in Activity, Spending, and Category Spending. It is excluded
from transfer totals.

**Audit:** Retain the same lifecycle, mapping, actor, request, date, amount, source, and posting
evidence required for income.

**Classification:** Deterministic proposal and reporting mechanics are **ENGINEERING**. The simple
expense entry is **PRODUCT**. Default expense mappings, capitalization, reimbursement, tax, and
other non-expense treatment are **ACCOUNTING POLICY**. If the user cannot select an approved expense
classification, the system asks for clarification or declines to create the proposal.

## 7. Transfer semantics

### Same-space asset transfer

**User-facing meaning:** Move money between two asset accounts owned by the same personal space,
such as Checking to Savings.

**Required input:** Source account, destination account, exact amount, financial date, description,
and authenticated confirmation. The accounts must be different, active, same-book, and in the same
currency.

**Underlying proposal shape:** Debit the destination asset and credit the source asset. No income or
expense category is allowed.

**Ledger and reporting effect:** One balanced entry changes the two account balances and has zero
income and expense effect. Activity presents it once as a transfer with both accounts.

**Audit:** Retain both accounts, proposal lifecycle, actor, exact amount/date, request/idempotency
provenance, and posted entry.

This is safe generic **ENGINEERING** behavior for the approved asset kinds and a simple **PRODUCT**
flow. Transfer fees, FX, investment disposals, and third-party ownership are excluded.

### Personal and business movement

A personal/business movement remains two independent proposals in two books plus a non-financial
correlation. Each side has separate authorization, exact-version confirmation, idempotency, posting,
and audit. The correlation has no financial effect and cannot expose the inaccessible side.

Contribution, drawing, salary, reimbursement, distribution, and loan classifications are
**ACCOUNTING POLICY** gates. The cross-space feature remains disabled for the personal MVP until
both sides have approved mappings and recovery behavior.

## 8. Credit-card semantics

### Purchase

**User-facing meaning:** Record a purchase made on a personal credit card.

**Required input:** Credit-card account, amount, date, expense category, description, and explicit
confirmation.

**Proposal and ledger:** Debit the approved mapped expense account; credit the card liability.

**Reporting:** Increase category Spending and the amount owed on the card. Do not reduce bank cash
until a payment is posted.

### Payment

**User-facing meaning:** Pay down a card from a personal bank account.

**Required input:** Source Checking/Savings account, destination card, amount, date, description,
and explicit confirmation.

**Proposal and ledger:** Debit the card liability; credit the bank asset. The payment is a
liability transfer, not new spending or negative income.

**Reporting:** Reduce the bank balance and card amount owed; show one transfer-style activity; do
not count it again in Spending.

Both flows carry the complete proposal, confirmation, posting, request/idempotency, and audit
evidence. Their basic double-entry shapes are candidate **ACCOUNTING POLICY** templates that require
accountant approval with the default chart before enablement. Interest, fees, penalties, rewards,
cash advances, refunds, statement cycles, pending authorizations, credit limits, and card overpayment
are deferred rather than inferred.

## 9. Loan MVP semantics

The MVP can safely present a loan as a liability balance and record a payment only when the amount
applied to principal is explicit.

**User-facing meaning:** Show an established outstanding personal-loan principal and reduce it with
an explicitly identified principal payment.

**Required input for payment:** Source Checking/Savings account, loan account, exact principal
amount, date, description, and explicit confirmation. If a statement or user supplies a total
payment containing unknown interest, fees, penalties, tax, or insurance, the system must not guess a
principal amount.

**Proposal and ledger:** Debit the loan liability for the explicit principal amount; credit the bank
asset. A loan balance first enters the system only through an approved opening balance or explicit
borrowing proposal; neither is inferred from a typed number.

**Reporting:** Reduce the loan amount owed and the source-bank balance. Principal reduction is not
Spending or Income. Activity shows a loan payment.

**Audit:** Retain the user's explicit principal assertion or trusted source reference in proposal
provenance together with the ordinary lifecycle evidence.

**ENGINEERING:** Exact principal-only posting and liability balance derivation are deterministic.
**PRODUCT:** MVP shows outstanding balance and principal payments. **ACCOUNTING POLICY:** Initial
loan recognition and any component allocation require approval. Interest calculation, amortization,
fees, penalties, payoff forecasts, schedules, and automated allocation are deferred.

## 10. Opening-balance boundary

An opening balance is a financial event, never an editable account field.

The system can safely generalize the collection of:

- account and asserted balance;
- whether the balance is money held or money owed, consistent with account kind;
- opening date;
- user assertion or evidence reference;
- authenticated actor and system timestamp; and
- batch, proposal, confirmation, posting, and later correction provenance.

The eventual proposal must contain the account-side line and a separately approved balancing line.
For `Bank = ৳200,000`, the bank asset side is explicit. For `Credit Card = ৳35,000 owed`, the
liability side is explicit. The offset account, prior-income/equity treatment, batch grouping,
opening date policy, period coverage, and evidence requirement cannot be generalized safely.

**ENGINEERING:** Opening balances use ordinary validated proposals, exact confirmation, posting,
audit, and reversal/replacement correction.

**PRODUCT:** The MVP may collect and preview an opening-balance batch only after it can clearly show
that no balance exists until posting succeeds.

**ACCOUNTING POLICY:** No opening-balance proposal may be generated or posted until the balancing
treatment, date/period rules, and default chart are approved. Automated history reconstruction,
unverified imports, FX conversion, and mutable starting-balance fields are deferred.

## 11. Correction and reversal boundary

**User-facing meaning:** Correct a posted personal transaction without erasing what happened.

**Required input:** Target posted entry, reason, correction date, authenticated actor, and explicit
confirmation. A replacement requires a separate fully specified proposal.

**Underlying proposal shape:** Copy every original line with debit and credit swapped, preserving
line order, account, and immutable classification provenance. Post the full reversal through the
ordinary lifecycle. Create and confirm a replacement separately when needed.

**Ledger and reporting effect:** The original and reversal both remain visible. Totals reverse on
the reversal date. Historical reports before that date retain the original effect.

**Audit:** Preserve target/reversal linkage, reason, actor, financial date, event timestamps,
proposal/validation/confirmation/posting evidence, and any replacement chain.

The full compensating-reversal mechanism is **ENGINEERING** and already established by the core.
The plain-language correction flow is **PRODUCT**. Partial reversal, historical recategorization,
backdating, inactive-account exceptions, and alternative correction-date rules remain
**ACCOUNTING POLICY** or later product decisions.

## 12. Period boundary

| Classification        | M5.2-A decision                                                                                                                                                                                                                                                                                                                        |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ENGINEERING**       | The universal service retains non-overlapping periods and rejects posting unless the financial date belongs to exactly one open period. Locks and date checks remain deterministic.                                                                                                                                                    |
| **PRODUCT**           | Personal periods are hidden from normal MVP navigation. Users choose transaction dates; they do not close, lock, reopen, or manage periods in the simple personal experience. If posting is unavailable because coverage is not approved or available, the product explains that setup is incomplete rather than fabricating a period. |
| **ACCOUNTING POLICY** | The duration and creation of personal periods, late-entry behavior, opening-balance coverage, lock/close authority, adjustments, and reopening need explicit approval. No calendar-month, annual, rolling, or perpetual-open default is selected here.                                                                                 |

Personal posting remains feature-gated until an approved period policy can be represented by the
existing engineering capability. Hiding periods in the UI does not disable period enforcement.

## 13. Reporting model

The MVP contains only these personal read models:

| Report            | Deterministic source                                                 | MVP presentation                                                         | Gate                                        |
| ----------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------- |
| Balances          | Posted lines grouped by owned presentation account                   | Money held and amount owed, by account                                   | Negative/overdrawn presentation policy      |
| Activity          | Posted entries plus immutable category/account provenance            | Chronological income, expense, transfer, card, loan, and reversal events | None beyond approved templates              |
| Income            | Posted lines mapped to approved income accounts/categories           | Total and category detail for a date range                               | Approved mappings and recognition           |
| Spending          | Posted lines mapped to approved expense accounts/categories          | Total spending for a date range; transfers excluded                      | Refund/split behavior if present            |
| Category spending | Posted expense activity grouped by captured category/mapping version | Category totals and drill-down                                           | Approved category mappings                  |
| Cash position     | Posted balances for an approved set of liquid asset accounts         | Available personal cash by account and total                             | Cash-account inclusion and overdraft policy |

The universal service owns posted-line retrieval, exact account balances, date-range aggregation,
transfer provenance, and neutral account-type totals. The authorized personal read-model layer owns
plain-language names, category grouping through captured mappings, filtering, and progressive
disclosure. It may compose core values but may not recalculate or persist authoritative totals.

Formal business statements are not default personal views. Trial balance and ledger detail remain
advanced evidence. Net worth, investments, valuation, forecast, and jurisdictional reports are
deferred.

## 14. Budget compatibility

Budgets are not implemented in M5.2-A. The future model can add a non-ledger `Budget` and
`BudgetLine` owned by a typed Financial Space and associated with category IDs, account IDs, and a
date range under an approved mapping policy. Actual spending must be queried from posted categorized
activity. Editing a budget changes a plan, never the journal or an authoritative actual total.

Refund treatment, transfers, rollover, amendment history, enforcement, and category remapping are
future product/accounting decisions.

## 15. Reminder compatibility

Reminders are not implemented in M5.2-A. A future financial reminder may reference the personal
space, a financial account, a proposal/posted entry, a payment purpose, and a due date. It remains a
schedule record outside the ledger. Marking it complete, overdue, or dismissed never creates income,
spending, a balance change, or evidence of payment. Any later proposal generation requires unique
occurrence identity and explicit confirmation.

## 16. AI compatibility

A future interpretation of “I spent 3200 on groceries” may create a draft PERSONAL expense proposal
only after the server has fixed and authorized the personal Financial Space. The model may suggest
Food and ask which payment account was used. The deterministic adapter resolves only an approved
category mapping, and the application shows the exact amount, currency, date, account, category,
space, and proposal version before a separate human confirmation.

AI cannot choose or switch the Financial Space, choose an unapproved accounting mapping, calculate
an authoritative balance, confirm, post, reverse, lock a period, edit audit history, or access
storage. Conversation text is untrusted input and never evidence that a financial event occurred.

## 17. Tax and compliance exclusion

The personal MVP excludes tax, VAT/GST, withholding, payroll, statutory statements, filing,
country-specific compliance, and jurisdiction-specific recognition. No extension hook, country
field, tax rate, or speculative calculation is added by this milestone.

A future external versioned policy layer may consume authorized core results and create a reviewable
proposal. It remains outside the universal core and cannot write the ledger or audit directly.

## 18. Deferred functionality

The MVP defers:

- investments, securities, market valuation, gains/losses, and investment transfers;
- net-worth valuation and non-cash assets;
- household/joint/dependant ownership, advisor access, and multiple personal spaces;
- multi-currency, foreign accounts, FX, revaluation, and precision changes;
- interest, amortization, fees, penalties, payoff forecasts, and automatic allocation;
- tax, payroll, statutory reporting, filing, and all country-specific compliance;
- bank feeds, reconciliation automation, document extraction, OCR, and automatic posting;
- budgets, reminders, recurrence, goals, and automated proposal generation;
- personal/business transfer execution;
- partial reversals, historical recategorization, and mutable opening balances; and
- AI transaction understanding and conversational financial actions.

## 19. Accounting-policy gates

The following require qualified accountant or domain-owner approval before the related operation or
report is enabled:

1. the default personal ledger chart and every starter category mapping;
2. personal period duration/creation, late entries, opening coverage, locking, adjustment, and
   reopening;
3. opening-balance offset, date, grouping, evidence, and prior-income/equity treatment;
4. whether specific receipts are income, refunds, gifts, reimbursements, contributions, or loans;
5. capitalization or other non-expense treatment for outgoing money;
6. credit-card purchase/payment templates, refunds, overpayment, interest, fee, and reward treatment;
7. initial loan recognition and any principal/interest/fee/penalty/tax allocation;
8. personal/business contribution, drawing, salary, distribution, reimbursement, and loan treatment
   on both sides;
9. negative/overdrawn account presentation and cash-position account inclusion;
10. correction versus non-financial display recategorization and any alternative reversal-date
    behavior; and
11. any valuation, multi-currency, tax, statutory, or jurisdiction-specific behavior.

No item has an implied default.

## Simplification test

| Capability                        | Understandable without accounting knowledge? | Deterministic without jurisdiction rules?         | Result                                |
| --------------------------------- | -------------------------------------------- | ------------------------------------------------- | ------------------------------------- |
| Checking, Savings, Cash balances  | Yes                                          | Yes, after same-book account mapping              | Include                               |
| Explicit income and expense       | Yes                                          | Yes, after approved category mappings             | Include behind mapping gate           |
| Checking ↔ Savings transfer       | Yes                                          | Yes                                               | Include                               |
| Credit-card purchase/payment      | Yes                                          | Yes, after approved template/chart                | Include behind policy gate            |
| Principal-only loan payment       | Yes                                          | Yes when principal is explicit                    | Include behind initial-balance gate   |
| Opening balance                   | Yes at product level                         | No safe generic balancing treatment               | Collect/preview only; posting gated   |
| Personal periods                  | No need to expose                            | Engineering can enforce, policy cannot be assumed | Hide UI; posting gated until approved |
| Personal ↔ Business transfer      | Usually not without classification           | No                                                | Defer                                 |
| Investment valuation or net worth | Not reliably                                 | No without valuation policy                       | Defer                                 |
| Tax/compliance                    | No universal meaning                         | No                                                | Exclude from MVP                      |

## Implementation constraint summary

M5.2 can safely implement generically, after separate implementation authorization and completion of
the required canonical-business cutover prerequisites:

- private PersonalSpace ownership and typed PERSONAL resolution;
- presentation accounts for Checking, Savings, Cash, Credit Card, and Personal Loan;
- stable personal categories and versioned same-book mapping infrastructure;
- exact proposal, validation, confirmation, posting, reversal, audit, and idempotency reuse;
- same-space asset transfers;
- principal-only liability reductions when the principal amount is explicit;
- ledger-derived balances and Activity; and
- read-model infrastructure that uses only posted core data.

Income, expense, credit-card templates, opening-balance posting, full loan onboarding, category
financial reports, cash position, and all cross-space movements remain gated by the policies listed
above. Investments, valuation, household sharing, multi-currency/FX, automated interest or
amortization, tax/compliance, automatic posting, and the broader deferred list remain outside the
personal MVP.
