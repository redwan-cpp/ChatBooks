# Chatbooks personal finance model

**Milestone:** M5.0 domain specification, refined by M5.1-A and constrained by M5.2-A  
**Status:** Approved architecture direction; BUSINESS universal service exists, but no personal
feature, API, table, adapter, or personal ledger migration is implemented  
**Project and product:** Chatbooks

## Purpose and boundary

This document defines the future personal-finance domain without claiming that personal finance is
available. It preserves the existing organization-owned business ledger and the deterministic
proposal, validation, confirmation, posting, reversal, report, and audit invariants.

Personal and business finance are separate ownership and reporting domains. Personal data is never
stored as an organization, organization membership never grants personal access, and a journal entry
never spans the two domains. Frontend context selection is presentation state; the backend resolves
the authenticated actor's authority for every request.

The decisions are architectural. Accounting and product-policy questions that still need human or
qualified-accountant approval are listed in
[`M5_PERSONAL_FINANCE_DECISIONS.md`](M5_PERSONAL_FINANCE_DECISIONS.md).
The simplified MVP vocabulary, operation semantics, exclusions, and remaining policy gates are in
[`M5_2_PERSONAL_FINANCE_MVP_POLICY.md`](M5_2_PERSONAL_FINANCE_MVP_POLICY.md). That policy narrows
future scope but does not implement personal finance or approve the listed accountant gates.

## Architecture conclusions

1. `PersonalSpace` is a first-class ownership aggregate with a stable ID and one authenticated owner
   in the first implementation.
2. `FinancialSpaceRef` remains a tagged application reference. `BUSINESS` resolves to an existing
   organization ID; `PERSONAL` resolves to a `PersonalSpace` ID.
3. Existing organization IDs, tables, foreign keys, routes, ledger history, roles, and reports remain
   business-only and unchanged.
4. Actual personal money movements use the deterministic double-entry lifecycle. Categories,
   reminders, budgets, goals, recurring templates, and transfer correlations do not become ledger
   truth.
5. The current accounting rules are reusable, but the current engine and schema cannot be reused
   unchanged because authorization, periods, foreign keys, idempotency, audit, and ledger ownership
   are hard-wired to `organization_id`.
6. M5.1-A selects a persistent internal `LedgerBook` and one ownership-neutral deterministic
   financial service. A future typed personal adapter will resolve a personal owner to that book and
   call the shared service. This changes ownership plumbing, not debit/credit, balancing,
   confirmation, posting, reversal, or audit rules.
7. Cross-space movements create separately authorized and separately posted effects in each space.
   A non-financial correlation may link them without joining the ledgers.

## Personal ownership

### Initial model

The initial personal domain uses:

```text
User
└── owns exactly one PersonalSpace
    ├── personal accounts
    ├── personal categories and mappings
    ├── one internal ledger book
    ├── personal proposals and posted activity
    └── personal reports and audit scope
```

`PersonalSpace.id` is the stable resource and authorization boundary. `owner_user_id` references the
authenticated user and is unique for the first implementation. A separate ID is necessary so that
ownership can evolve without using a user ID as every resource's tenant key.

The space is private by default. Only its owner can discover, read, export, propose, confirm, post,
reverse, or inspect its audit history. An organization role, including `OWNER` or `ACCOUNTANT`, has
no personal authority.

The first implementation supports one personal space per user. Multiple personal spaces, joint
ownership, dependants, guardians, and household spaces require an explicit product decision and a
migration. Future sharing should use personal-space grants or a distinct household ownership model;
it must not reuse organization memberships.

### Ownership invariants

- Every personal record carries `personal_space_id` directly or through a database-enforced parent.
- The authenticated actor is derived from the session, then checked against personal ownership.
- Personal resource lookup uses both resource ID and personal-space ID.
- IDs from a business route cannot resolve personal records, and personal routes cannot resolve
  organization records.
- Removing frontend context, changing a URL, or substituting an ID cannot widen server authority.
- Personal exports, conversation retrieval, background work, cache keys, search indexes, documents,
  notifications, and future AI tools use the same typed scope.

## Financial Space resolution

The application reference is:

```text
FinancialSpaceRef
├── kind: PERSONAL | BUSINESS
└── id: PersonalSpace.id | Organization.id
```

The pair is the identity. The ID alone is never accepted as a space reference. A project is an
optional business dimension, not a third Financial Space kind:

```text
PERSONAL → PersonalSpace
BUSINESS → Organization
BUSINESS → Organization → optional Project
```

A future authenticated `GET /api/v1/financial-spaces` endpoint can return a union read model of the
owner's personal space and accessible organizations. It does not need a persistent cross-cutting
`financial_spaces` parent table. Business routes keep `/organizations/{organization_id}`. Personal
routes use `/personal-spaces/{personal_space_id}`.

The client may remember the last selected reference as a convenience. The server independently
checks the kind, ID, actor, route family, and resource ownership on every request.

## Relationship to the deterministic ledger

### What belongs in the ledger

Events that change actual personal financial position use the guarded ledger lifecycle:

- deposits and withdrawals;
- earned or received income;
- purchases and other expenses;
- payments and refunds;
- transfers between personal money accounts;
- liability advances and repayments;
- approved opening-balance entries; and
- corrections through compensating reversal and replacement.

They follow:

```text
personal intent
→ typed proposal
→ deterministic validation
→ exact-version authenticated confirmation
→ atomic post
→ personal ledger and audit
```

The ledger remains the sole source of actual balances, income, expense, liabilities, category
actuals, and personal financial reports.

### What stays outside the ledger

| Record                   | Treatment                                               |
| ------------------------ | ------------------------------------------------------- |
| Personal account profile | User-facing metadata linked to a ledger account         |
| Category                 | Classification with a versioned ledger mapping          |
| Budget and budget line   | Plan; actuals derive from posted categorized activity   |
| Reminder                 | Schedule; completion does not prove payment             |
| Recurring template       | May create a proposal; cannot confirm or post           |
| Goal                     | Target; progress needs an approved ledger mapping       |
| Cross-space correlation  | Links two independent operations; has no balance effect |
| Insight                  | Explanation over verified results; no independent total |

### Reuse assessment

The current pure rules in `chatbook/domain.py` and the accounting lifecycle are suitable for personal
actuals. The existing `AccountingEngine` and schema are not ownership-neutral: they require
organization membership, organization foreign keys, organization periods, organization idempotency
receipts, and organization-scoped audit.

Therefore a thin adapter alone is insufficient. The future implementation should introduce an
internal `LedgerBook` scope and an ownership-neutral ledger application service. A
`PersonalAccountingAdapter` will:

1. authenticate the actor through the current session boundary;
2. authorize ownership of the exact `PersonalSpace`;
3. resolve that space's internal ledger book, currency, precision, and approved period policy;
4. translate personal accounts/categories into explicit ledger lines;
5. call the shared deterministic validation/posting/reversal service; and
6. translate verified ledger results into personal read models.

The business `AccountingEngine` remains a compatibility facade that resolves organizations and calls
the same service. No accounting rule moves into the adapter. The implementation must retain the
current database protections and tests before any personal post is enabled.

M5.1-A selects a persistent internal ledger-book table as the canonical financial ownership seam:

```text
LedgerBook
├── id
├── owner_kind: BUSINESS | PERSONAL
├── organization_id XOR personal_space_id
├── currency
└── minor_unit_digits
```

Database constraints must enforce the owner-kind relationship and one ledger book per owner. This
internal object is not a new customer-facing Financial Space and does not authorize access by
itself.

## Personal accounts and money mapping

`PersonalAccount` is the plain-language representation of where money is held or owed. It has a
stable ID, `personal_space_id`, name, account kind, active state, optional institution and masked
reference, and one linked ledger account. It does not store an authoritative mutable balance.

Proposed MVP kinds are:

| Personal kind            | Ledger semantics | Notes                                                  |
| ------------------------ | ---------------- | ------------------------------------------------------ |
| Cash                     | Asset            | Physical cash balance                                  |
| Checking/current account | Asset            | Bank-held spendable funds                              |
| Savings                  | Asset            | Bank-held savings                                      |
| Credit card              | Liability        | Purchases increase the liability; payments reduce it   |
| Personal loan            | Liability        | Principal balance; interest behavior is not calculated |
| Installment debt         | Liability        | Principal balance; schedule automation is deferred     |
| Investment cash/value    | Asset candidate  | Market valuation and gains remain deferred             |

Every actual balance is calculated from posted ledger lines for the linked ledger account. An
inactive personal account remains visible historically but cannot be used for a new posting unless
the approved correction policy allows it.

Income and expense classifications use ledger revenue and expense accounts underneath. The
customer-facing experience uses categories rather than exposing those accounts first. Equity or
other balancing accounts remain advanced implementation detail and cannot be generated until the
relevant opening-balance and contribution policy is approved.

MVP remains single-currency per personal space with exact integer minor units. Foreign-currency
accounts, exchange rates, revaluation, and currency changes are deferred.

## Personal categories

Categories are separate user-facing records and are not aliases for account IDs. The proposed model
uses both a category and an explicit mapping:

```text
PersonalCategory
├── id
├── personal_space_id
├── name
├── direction: INCOME | EXPENSE
└── active

CategoryAccountMapping
├── category_id
├── ledger_account_id
├── version/effective boundary
└── active
```

At proposal creation, the personal adapter resolves the selected category to a ledger account and
records the category ID and mapping version with the proposal line. The posted line retains the
resolved ledger account and stable classification provenance. Renaming or remapping a category only
affects future proposals. It never rewrites posted journal lines or historical totals.

A transfer has no income or expense category. Fees, interest, tax, cashback, split purchases, and
historical recategorization need explicit product/accounting behavior before implementation. A
display-only category change must be audited and must not pretend that an accounting correction
occurred.

## Transfers

### Inside one personal space

A transfer between two accounts in one personal space is one balanced proposal and one posted entry.
The source and destination must both belong to the same space. It is excluded from income and expense
category totals.

Examples at an architectural level:

- checking to savings moves value between two asset accounts;
- bank to credit card reduces a bank asset and a liability;
- savings to investment moves value between owned asset accounts if the destination's valuation
  basis has been approved.

Transfer fees or interest are separate explicit lines using approved categories. The adapter must
not infer them.

### Personal and business

A personal-to-business or business-to-personal movement crosses ownership, authorization, and
reporting boundaries. It cannot be one journal entry.

The future workflow creates:

1. a non-financial `CrossSpaceTransfer` correlation with typed source and destination references;
2. one proposal in the personal ledger; and
3. one proposal in the business ledger.

Each proposal is validated and confirmed for its own exact version by an actor authorized in that
space. A single user gesture may present a coordinated review, but it must produce two independent
confirmation records and two idempotent posts. The correlation records state such as `DRAFT`,
`PARTIALLY_POSTED`, `POSTED`, or `REVERSED`; it does not change balances and cannot grant access from
one side to the other.

If one side posts and the other fails, the posted history remains. Recovery is retry or an explicitly
confirmed compensating reversal, never deletion or distributed rollback. Contribution, drawing,
reimbursement, dividend, salary, and loan treatment on either side requires accountant approval.

Cross-space metadata is minimal: correlation ID, typed spaces, amount/currency, proposal/entry IDs,
state, actor/timestamps, and audit/request IDs. A caller who can access only one side sees only that
side plus a restricted correlation status, not the other space's descriptions, accounts, or reports.

## Opening balances

Opening balances are financial events, not editable account fields. The proposed application flow is:

```text
choose opening date
→ enter account balances and source/provenance
→ review an opening-balance batch
→ generate one or more typed proposals
→ validate
→ explicitly confirm exact versions
→ atomically post each proposal
→ retain batch, entries, evidence, and audit history
```

The workflow records the asserted balance, account, opening date, source type, optional supporting
evidence reference, creating actor, system timestamp, generated proposal IDs, posted entry IDs, and
correction chain. Financial date and audit timestamp remain separate.

Changing an opening balance uses a reversal and replacement proposal. It never updates or deletes the
original entry. The balancing account, opening period behavior, evidence requirement, treatment of
prior income/equity, and whether multiple accounts form one batch are accountant/product decisions.
Until those decisions are approved, opening balances must not post.

## Personal liabilities

The minimum MVP represents credit cards, personal loans, and installment debt as personal accounts
mapped to liability ledger accounts. The authoritative outstanding amount is the ledger-derived
liability balance.

The liability profile may hold descriptive lender, masked reference, account status, and optional
statement or contractual metadata. Due dates and notifications belong to the later Reminder domain.
Amortization schedules, accrued interest, penalty calculations, payoff estimates, and credit limits
are not authoritative ledger calculations in M5.

A payment is an explicit transfer-style proposal from a personal asset account to the liability.
Principal, interest, fee, and tax splits must be supplied by a trusted source or user, displayed for
review, and mapped through approved categories. Chatbooks does not calculate or infer the split.

## Personal reporting

Personal reports are plain-language read models over posted personal ledger data:

| Report            | Source and boundary                                                |
| ----------------- | ------------------------------------------------------------------ |
| Account balances  | Posted lines for personal money/liability accounts                 |
| Spending summary  | Posted expense lines mapped to personal categories                 |
| Income summary    | Posted income lines mapped to personal categories                  |
| Category spending | Posted categorized expense lines; transfers excluded               |
| Cash position     | Approved set of liquid personal asset accounts                     |
| Money activity    | Posted entries with personal account/category presentation         |
| Net worth         | Later: approved included assets minus liabilities at an as-of date |

Business income statements, balance sheets, trial balances, and cash-flow terminology do not become
the default personal UI. Advanced ledger detail remains available for audit and support. Net worth is
deferred until inclusion, ownership, valuation, investment, non-cash asset, and business-interest
policies are approved. The system never invents market values.

## Privacy and sharing

The backend enforcement order is:

1. authenticate the user;
2. parse a typed space kind and ID from the route/application command;
3. resolve the named `PersonalSpace` or organization;
4. authorize personal ownership or organization membership independently;
5. load every referenced resource through the same owner key; and
6. run the owner-specific application service.

Personal data is private by default. Future household and advisor access requires explicit grants,
least-privilege permissions, consent, revocation, access audit, export rules, and recovery behavior.
No business accountant can see personal data merely because the same user belongs to that business.

Isolation must cover list counts, errors, cache entries, logs, exports, documents, reminders,
analytics, notifications, conversations, search, and AI retrieval. Prefer a consistent not-found
response when disclosing existence would cross a privacy boundary.

## Proposed future API

The following surface is a proposal, not an implemented contract.

### Discovery and profile

- `GET /api/v1/financial-spaces` — union of accessible typed spaces, without financial records.
- `POST /api/v1/personal-spaces` — create the authenticated user's one personal space.
- `GET /api/v1/personal-spaces/{personal_space_id}` — owner-scoped profile.
- `PATCH /api/v1/personal-spaces/{personal_space_id}` — permitted non-financial profile settings.

### Accounts and categories

- `GET|POST /personal-spaces/{id}/accounts`
- `GET|PATCH /personal-spaces/{id}/accounts/{account_id}`
- `GET|POST /personal-spaces/{id}/categories`
- `GET|PATCH /personal-spaces/{id}/categories/{category_id}`
- `GET|POST /personal-spaces/{id}/category-mappings`

### Financial lifecycle

- `GET|POST /personal-spaces/{id}/proposals`
- `GET /personal-spaces/{id}/proposals/{proposal_id}`
- `POST /personal-spaces/{id}/proposals/{proposal_id}/validate`
- `POST /personal-spaces/{id}/proposals/{proposal_id}/confirm`
- `POST /personal-spaces/{id}/proposals/{proposal_id}/post`
- `GET /personal-spaces/{id}/entries`
- `GET /personal-spaces/{id}/entries/{entry_id}`
- `POST /personal-spaces/{id}/entries/{entry_id}/reversals`
- `POST /personal-spaces/{id}/opening-balance-batches`
- `GET /personal-spaces/{id}/opening-balance-batches/{batch_id}`
- `POST /cross-space-transfers` — coordinated proposal creation after policy approval.

### Read models and evidence

- `GET /personal-spaces/{id}/reports/account-balances`
- `GET /personal-spaces/{id}/reports/spending`
- `GET /personal-spaces/{id}/reports/income`
- `GET /personal-spaces/{id}/reports/cash-position`
- `GET /personal-spaces/{id}/reports/net-worth` — deferred beyond initial MVP.
- `GET /personal-spaces/{id}/activity`
- `GET /personal-spaces/{id}/audit-events` — advanced owner/auditor evidence.

Current `/organizations/{organization_id}` routes remain business-only. They do not accept a space
kind or personal ID. The Next.js same-origin proxy can forward both route families without becoming
an authorization authority.

## Proposed future database impact

No table is created in M5.0. A future migration is expected to add:

| Entity                        | Purpose and key constraints                                                 |
| ----------------------------- | --------------------------------------------------------------------------- |
| `personal_spaces`             | Stable personal owner; unique initial `owner_user_id`; currency/precision   |
| `ledger_books`                | Internal typed owner mapping; exactly one organization or personal-space FK |
| `personal_accounts`           | Personal presentation mapped one-to-one to an owned ledger account          |
| `personal_categories`         | Stable owner-scoped label and income/expense direction                      |
| `category_account_mappings`   | Versioned category-to-ledger mapping within one space                       |
| `opening_balance_batches`     | Provenance and immutable references to generated proposals/entries          |
| `cross_space_transfers`       | Non-financial correlation and recovery state for two scoped effects         |
| personal audit/access records | Owner-scoped mutation and future access evidence                            |

Indexes begin with the ownership key for personal resource lookup. Composite foreign keys prevent
cross-space account, category, proposal, entry, mapping, and document references. Unique constraints
enforce one personal space per user in the initial model, one ledger book per owner, one presentation
account per ledger account, and existing posting/idempotency rules.

The selected ledger-book migration is phased:

1. preflight the current v2 schema, constraints, identifiers, and business reconciliation baseline;
2. add `ledger_books` and backfill one BUSINESS book per organization without changing organization
   IDs or enabling personal writes;
3. extract one ownership-neutral deterministic service behind the existing business engine facade
   while the current organization-scoped storage remains authoritative;
4. construct canonical book-scoped financial tables, copy the complete business history, and
   reconcile identifiers, journal lines, reports, audit evidence, and idempotency receipts;
5. cut business traffic over atomically only after rollback and parity checks pass;
6. add `PersonalSpace` and personal presentation records after the business cutover; and
7. enable personal writes last, after isolation, cross-scope, concurrency, reversal, and reporting
   tests prove equivalent protection.

The target financial persistence uses `ledger_book_id` as its canonical ownership key. The exact
DDL, migration versioning, and SQLite table-reconstruction sequence are M5.1-B implementation work
and require evidence from the current schema. Parallel accounting logic or weaker personal database
constraints are not acceptable. See
[`universal-financial-core.md`](universal-financial-core.md) for the authoritative architecture.

## Budgets, reminders, goals, and recurrence

The personal owner and typed space reference allow later `Budget`, `BudgetLine`, `Reminder`,
`Recurrence`, `RecurringTransactionTemplate`, and `FinancialGoal` records to belong to a personal
space. They remain non-ledger aggregates.

Actual budget or goal progress comes from posted ledger lines through explicit category/account
mappings. Reminder completion has no financial effect. A recurring template may generate a uniquely
identified proposal occurrence, but cannot validate, confirm, post, reverse, or mark an entry paid.

## Future AI context

A future AI orchestrator receives a server-issued context envelope, not a context inferred from
conversation text:

```text
FinancialContext
├── space: FinancialSpaceRef(kind, id)
├── display_name
├── currency and minor_unit_digits
├── authenticated actor and resolved capabilities
├── optional BUSINESS project_id
├── financial date/as-of range
└── source/request provenance
```

The backend resolves the envelope and authorized tools. A model cannot select another space, combine
personal and business data, or gain confirmation/posting authority by mentioning an ID or name. AI
may later inspect verified results or create a proposal; it cannot confirm, post, reverse, lock,
write audit history, or access the database.

## Required implementation evidence

Before any personal posting is enabled, tests must prove:

- owner access and anonymous/non-owner/business-member rejection;
- personal and organization ID substitution fails in both directions;
- every posted personal entry balances and posts atomically;
- exact-version confirmation, idempotency, reversal, and immutable audit match business guarantees;
- personal account/category references cannot cross spaces;
- same-space transfers do not appear as income or expense;
- cross-space correlation cannot expose the inaccessible side;
- opening-balance correction preserves original history;
- all personal reports reconcile to posted lines; and
- the complete existing business suite remains unchanged and passing.

## Intentionally deferred

This specification does not implement personal storage, endpoints, UI, budgets, reminders,
recurrence, goals, AI, documents, bank integration, multi-currency, market valuation, interest
calculation, tax, household sharing, advisor access, or production infrastructure.
