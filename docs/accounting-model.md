# Chatbooks accounting model

## Source of truth and amounts

Only posted journal entries and lines affect financial results. Proposals, project estimates,
documents, validations, and confirmations have no balance effect.

Each current organization explicitly selects one uppercase currency code and a precision of 0–6
decimal digits. The future universal model places those values on its internal ledger book. The code
is a label, not a validated currency registry entry. Amounts are integer minor
units throughout storage and the application interface. No binary floats, implicit rounding,
exchange conversion, tax inference, or automatic recognition rules are used. The decimal text
parser rejects excess precision and scientific notation.

The operational limit is 9,000,000,000,000 minor units per side per line, with at most 1,000 lines
per entry. Thus a per-entry SQLite sum stays below signed 64-bit overflow. Report accumulation uses
unbounded Python integers. These are technical limits, not accounting materiality policies.

## Posting invariants

1. A posted entry contains 2–1,000 lines.
2. Each line has one strictly positive side; the other side is zero. Negative or zero-only lines fail.
3. `SUM(debit) == SUM(credit)` exactly for every entry and the full ledger.
4. All referenced accounts, projects, documents, periods, and reversal targets belong to the organization.
5. Posting accounts are active, and the accounting date falls in exactly one open period.
6. The stored proposal has passed deterministic validation and has an explicit confirmation.
7. Confirmation identifies a validation of the exact immutable proposal. Its actor must match the poster.
8. The posted header and ordered lines exactly match the confirmed proposal.
9. A proposal posts at most once. Repeating the same confirmation is idempotent.
10. Posted headers, lines, confirmations, validations, and audit history cannot be updated or deleted.

Proposals may be unbalanced or incomplete to allow manual review, but invalid line values and
cross-organization references are rejected immediately. An invalid proposal cannot validate or post.
To correct a proposal, create a new one; draft editing and cancellation are not yet implemented.

## Manual lifecycle

`create proposal → validate → inspect and explicitly confirm → post → ledger → reports`

Validation records a SHA-256 fingerprint of the immutable proposal and its ordered lines.
Confirmation revalidates current conditions. Posting revalidates again inside the same write
transaction that commits the journal. Validation is not a reservation of an open period or active
account. Failed posting leaves the proposal/confirmation available for inspection without any
partial journal or successful posting audit event.

Posting the same confirmation again is idempotent and returns the original journal entry. Creating a
second proposal with identical content is treated as a distinct candidate business event because
content equality cannot distinguish a retry from two legitimate equal transactions. The API requires
stable request idempotency keys for confirmation and posting; proposal creation remains a distinct
operation even when its financial content matches another proposal.

## Reversals

`propose reversal → validate → explicitly confirm → post reversal`

A reversal references an existing posted entry and copies each line with debit and credit swapped,
preserving account, position, and project. It requires a reason and an explicit date. The original
entry is untouched, including when its original period is locked. The reversal must be dated in an
open period and no earlier than the original entry. Reports before the reversal date continue to
show the original effect. Each entry may have one direct posted reversal; a reversal may itself be
reversed with the same confirmed workflow, preserving the entire chain.

Full reversals are supported. Partial reversals and automatic replacement entries are deferred.
An inactive account must be reactivated explicitly before it can participate in a reversal. This
uniform posting constraint and the reversal-date restrictions are visible foundation policies,
recorded in ADR 0004, pending broader accounting workflow review.

The explicit correction operation is reversal. The kernel also permits ordinary balanced manual
journals and cannot infer whether the operator intended one as a correction. The API exposes the
reversal workflow for corrections; future clients must use it for undo instead of silently posting
offsets.

## Periods

Period dates are canonical calendar dates with inclusive endpoints. Periods in one organization
cannot overlap; gaps are permitted, but posting in a gap fails. Locks block all new postings,
including reversals, in that period. Locking is idempotent and audited once. Unlocking, fiscal-year
closing, adjustment periods, and privileged overrides are not implemented. Locking does not create
closing entries, certify completeness, or assert regulatory compliance.

## Balances and reports

For an account, `net_debit = total posted debits - total posted credits`. A positive result is a
debit balance; a negative result is a credit balance. The trial balance presents positive net
debits and credits separately and includes zero-balance and inactive accounts. The overall trial
balance must balance; unusual normal-side balances are not silently rejected or reclassified.
Account hierarchy, roll-up accounts, and parent/child posting restrictions are not supported.

The income statement sums revenue credits less debits and expense debits less credits over an
inclusive date range. Net income equals revenue minus expenses. The balance sheet uses asset
debit balances and liability/equity credit balances. It separately includes the cumulative net
revenue/expense balance as **unclosed earnings**, so manually posted closing entries are not counted
twice. These are basic ledger-derived summaries, not jurisdiction-specific statutory statements. The
M3 cash-flow endpoint reports unclassified movements for asset accounts explicitly selected by the
caller; cash-account designation and operating/investing/financing classification remain undefined.
No comparative statement, tax calculation, or automated closing is provided.

Project filters select tagged lines. A project-filtered view **may not balance**, because one side
may be unassigned or assigned to a different project. The organization-wide invariant remains
mandatory. Budgets and expected revenue are planning metadata and never create ledger entries.
Project status and budget limits do not gate postings without an approved business rule.

## M5.1 universal financial model and implemented service boundary

M5.1-A classifies the balance, line, proposal, confirmation, posting, reversal, and audit rules above
as jurisdiction-neutral financial-core behavior. It selects a future persisted `LedgerBook` as the
canonical scope for those records. BUSINESS resolves Organization to a book; PERSONAL resolves
PersonalSpace to a book. An authorized application context is required before the deterministic
service can operate on that book.

The future book-scoped invariants are the current posting invariants with “belongs to the
organization” generalized to “belongs to the same ledger book.” Business-only projects and document
references remain separately constrained extensions tied to the organization and its mapped book.
M5.1-C1 adds the tested one-to-one BUSINESS book mapping. M5.1-C2 makes the universal service the
single application-level financial write and calculation boundary while retaining schema-v3
organization storage. Every service operation requires the resolved BUSINESS book context and an
explicit capability. The repository and storage adapter preserve current database constraints,
atomic writes, immutable audit triggers, and organization isolation. All financial ownership columns
remain organization-scoped in the normal C3 application path.

M5.1-C3 implements the canonical schema-v4 representation on disposable copies. Charts, accounts,
periods, proposals and lines, validations, confirmations and provenance, receipts, journal entries,
and journal lines use `ledger_book_id` as their ownership key. Composite foreign keys carry that key
through every financial relationship, including reversal targets. Proposal-document,
proposal-line-project, and journal-line-project relationships remain BUSINESS extensions constrained
to the book's organization; they do not become universal financial-core concepts.

The accounting rules and exact integer amounts do not change in v4. Existing validation hashes are
not recalculated: each migrated row retains its bytes and records `organization-v1`, and the service
reconstructs the legacy organization-shaped proposal payload for confirmation and posting. Audit
events are not rewritten. A sidecar adds the book scope, and future v4 financial mutations append
both the legacy-shaped event and sidecar atomically. Normal v3 operation remains authoritative until
the separately authorized C4 cutover.

User-facing Financial Activity is not a new financial record. Money in, money out, transfers,
liability events, opening balances, and corrections are typed application commands that compile to
explicit proposals; posted activity is a read model over journal lines and immutable provenance.
Direction alone never determines income, expense, contribution, loan, reimbursement, principal,
interest, tax, or another classification.

Same-book transfers remain one balanced entry. Cross-space movements remain two independently
authorized and posted effects plus a non-financial correlation. Core periods remain an enforcement
capability scoped by book; the personal period policy is not selected. Budgets, goals, reminders,
recurrence, and project plans remain outside posted actuals.

The core exposes exact ledger lines, balances, trial-balance arithmetic, neutral account/date
aggregates, and lifecycle evidence. Business and personal application layers compose those values
for their audiences. Tax, VAT/GST, payroll compliance, statutory statements, filing, and
country-specific recognition rules are external versioned policy layers and cannot write the ledger
directly.

These architecture decisions are detailed in
[`universal-financial-core.md`](universal-financial-core.md) and ADRs 0018–0020. They do not approve
personal postings or any unresolved accounting policy.

## M5.0 personal finance model

The current implementation provides an organization-scoped business ledger through the universal
service. No personal financial records, personal
accounts, categories, budgets, reminders, recurring transactions, goals, or net-worth reports exist
in the current schema or API.

M5.0 decides that personal income, expenses, money-account balances, liabilities, opening balances,
and transfers between accounts in one personal context use the double-entry proposal and posting
lifecycle because they change actual financial position. The current accounting rules are reusable,
but the current engine and schema cannot accept a personal owner unchanged: they assume organization
membership, organization foreign keys, explicit periods, organization receipts, and
organization-scoped audit.

A future `PersonalAccountingAdapter` would resolve an owned `PersonalSpace`, translate personal
accounts/categories into explicit ledger lines, and call an ownership-neutral deterministic ledger
service through an internal owner-bound ledger book. The existing business engine remains a
compatibility facade. The BUSINESS book mapping and universal service now exist; no PersonalSpace,
personal adapter, personal storage, or personal API exists.

Personal planning and scheduling concepts do not belong in the journal:

| Future concept                 | Financial effect                                                         |
| ------------------------------ | ------------------------------------------------------------------------ |
| Budget or budget line          | Planned limit/target; actual comes from mapped posted activity           |
| Financial reminder             | No ledger effect; completion is not evidence of payment                  |
| Recurring transaction template | May create a proposal; cannot confirm or post it                         |
| Savings goal                   | Planned target; progress calculation requires an approved source mapping |
| User-facing category           | Classification/mapping; must not create a second mutable actual          |
| Insight                        | Explanation over verified data; cannot replace engine arithmetic         |

A transfer within one personal space creates one balanced accounting event and is excluded from
income and expense categories. A personal/business movement cannot be a single journal spanning two
reporting boundaries. It creates separately reviewed and posted effects in each space plus a
non-financial correlation. Contribution, drawing, distribution, reimbursement, salary, and loan
account mappings remain accountant decisions; architecture alone does not select them.

Personal accounts are user-facing profiles mapped to owned asset or liability ledger accounts. Their
balances are always ledger-derived. Personal categories are separate stable labels with versioned
income/expense account mappings captured by proposals. Category changes cannot rewrite posted
history. Opening balances are reviewable proposals with source/evidence provenance and corrections
through reversal and replacement; the offset account and personal period treatment remain blocked
on accountant approval.

The minimum liability model covers credit cards, personal loans, and installment debt as liability
accounts. Payments are transfer-style proposals. Interest, principal, fees, penalties, amortization,
and tax splits are never calculated or inferred without approved rules and reviewed source values.

Personal net worth is deferred. Supporting it later requires explicit account inclusion, liability
presentation, ownership, opening balance, valuation date, and non-cash asset valuation policy. The
system must not infer market values or combine personal and business interests without an approved
rule.

Personal user-facing reports are account balances, money activity, spending, income, category
spending, and an approved liquid-account cash position. They derive from posted personal lines.
Business statement names and presentation are not the default personal experience. Full design and
decision gates are in [`personal-finance-model.md`](personal-finance-model.md) and
[`M5_PERSONAL_FINANCE_DECISIONS.md`](M5_PERSONAL_FINANCE_DECISIONS.md).

## M5.2-A simplified personal MVP policy

M5.2-A narrows the future personal product to five understandable account kinds—Checking, Savings,
Cash, Credit Card, and Personal Loan—and six ledger-derived read models: Balances, Activity, Income,
Spending, Category Spending, and Cash Position. This is a policy boundary only. No PersonalSpace,
personal table, endpoint, UI, or posting path exists in the current application.

For the MVP, income and expense are explicit user classifications through an approved category
mapping; money direction alone never decides them. A same-space transfer between asset accounts is
one balanced debit-to-destination/credit-to-source proposal with no income or expense category.
Credit-card purchases increase an approved expense and the card liability; card payments reduce the
liability and the paying bank asset without creating new spending. A loan payment can reduce
principal only when the principal amount is explicit. These shapes are not enabled templates until
their default chart and mappings receive accounting approval.

Opening balances remain blocked from proposal generation and posting until an approved balancing
account, date/period, grouping, evidence, and prior-history treatment exists. The system may later
collect the asserted account, amount, direction, date, and source for review, but it may not guess
the other side. Personal periods remain an enforced core capability hidden from normal navigation;
no month, year, rolling, or perpetual-open policy is selected. Personal posting stays disabled until
period creation and late-entry behavior are approved.

Starter category labels and user-created categories are presentation concepts. Versioned same-book
mappings and captured proposal provenance prevent a rename or remap from changing posted history.
Historical financial reclassification uses an approved correction workflow, never a silent rewrite.
Budgets and reminders remain non-ledger future records; their state cannot change actuals.

The authoritative operation-by-operation policy, decision classification, exclusions, and gates are
in [`M5_2_PERSONAL_FINANCE_MVP_POLICY.md`](M5_2_PERSONAL_FINANCE_MVP_POLICY.md). This policy does not
approve tax, compliance, investment valuation, multi-currency, automated interest/amortization,
personal/business classifications, or automatic posting.

Budgets are always distinguishable from actuals. The current `projects.budget` value remains project
planning metadata and is neither historical budget-line data nor a posting limit. A future general
budget aggregate needs explicit periods, scope, currency, account/category/project mapping, rollover,
and enforcement semantics before implementation.

Recurring transactions require rules for time zones, occurrence generation, edits, missed dates,
duplicate prevention, and confirmation. Recurrence alone never grants posting authority.

## Unresolved business rules

| Ambiguity                                                     | Current boundary / decision still needed                                                                                                                                                                         |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Jurisdiction, reporting framework, tax regime                 | Not selected; no inferred tax or statutory rules                                                                                                                                                                 |
| Cash versus accrual treatment and revenue recognition         | Operator chooses entries; no automatic policy                                                                                                                                                                    |
| Fiscal calendar, closing, opening balances, retained earnings | Periods and balanced opening/closing entries are manual; templates and automation deferred                                                                                                                       |
| Who can post, confirm, invite users, or lock periods          | M3 role permissions are defined in ADR 0006; role changes/removal, ownership transfer, dual approval, and confirmation expiry remain unresolved                                                                  |
| Period reopening and late adjustments                         | No reopening API; approve a policy before adding one                                                                                                                                                             |
| FX, multi-currency, rounding, precision changes               | Single fixed organization currency/precision; conversion and changes unsupported                                                                                                                                 |
| Reversal of inactive accounts, partial reversals, date policy | Uniform active-account rule and full reversal with same/later date; broader workflow requires review                                                                                                             |
| Project allocations and project-level balancing               | Optional line dimensions; no allocations or per-project balancing requirement inferred                                                                                                                           |
| Required document evidence, deduplication, retention          | Optional metadata link; no source hash uniqueness or document approval policy                                                                                                                                    |
| Confirmation expiry and dual approval                         | No time-based expiry or dual approval; current conditions always rechecked                                                                                                                                       |
| Master-data edits and proposal amendments                     | Mostly immutable; define audited amendment/supersession semantics before extending                                                                                                                               |
| Account hierarchy and roll-ups                                | Unsupported; define posting and aggregation rules before adding parent/child accounts                                                                                                                            |
| API command idempotency                                       | Confirmation/posting caller keys are implemented; proposal/reversal creation keys and receipt retention remain unresolved                                                                                        |
| Cash-flow classification                                      | Caller selects asset accounts for unclassified cash movements; formal cash designation and operating/investing/financing rules require approval                                                                  |
| Universal ledger ownership                                    | BUSINESS mapping, service seam, and disposable schema-v4 parity evidence exist; ordinary v4 cutover remains blocked on C4 deployment evidence, authorization, and sign-off                                       |
| Personal ledger reuse                                         | Architecture uses a typed personal adapter over the universal service; M5.2-A narrows the generic MVP, while posting remains blocked on C4, personal period, chart/mapping, opening-balance, and isolation proof |
| Personal transfers and cross-space movements                  | Same-space transfer architecture is one balanced non-income/expense entry; define account treatment for contributions, drawings, reimbursements, distributions, salaries, and loans                              |
| Personal opening balances                                     | Define balancing account, date/period, batch grouping, evidence, and prior-income/equity treatment before enabling posts                                                                                         |
| Personal categories                                           | Define default taxonomy and mappings for splits, refunds, fees, tax, cashback, transfers, and historical recategorization                                                                                        |
| Personal liabilities and net worth                            | Define interest/principal/fee behavior, inclusion, ownership, valuation, and presentation; no inferred calculations or market values                                                                             |
| Budget behavior                                               | Define period, scope, mapping, rollovers, overspend meaning, enforcement, amendment history, and project-budget migration                                                                                        |
| Financial reminders and recurrence                            | Define time zones, missed occurrences, edits, notifications, completion, proposal generation, and duplicate handling                                                                                             |
| Household and delegated access                                | Define sharing, consent, roles, revocation, and whether joint ownership is supported                                                                                                                             |
