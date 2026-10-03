# Chatbooks universal financial core

**Milestone:** M5.1-A architecture and domain design  
**Status:** Accepted architecture direction; no implementation or schema change  
**Project and product:** Chatbooks

## Scope and promise

The universal financial core is Chatbooks' jurisdiction-neutral system for exact financial state.
It serves business and personal financial spaces through one deterministic lifecycle without making
either ownership model pretend to be the other.

The core owns exact money, accounts, periods as a posting-control capability, proposals,
validations, confirmations, postings, journal lines, balances, reversals, audit evidence, and
idempotent command results. It does not own tax, VAT/GST, payroll compliance, filing, statutory
presentation, or country-specific calculations.

This document makes architecture decisions only. It creates no `PersonalSpace`, `LedgerBook`, API,
table, migration, budget, reminder, recurring transaction, goal, document workflow, AI tool, bank
integration, tax rule, or compliance feature.

## Current-system findings

The current business engine is correct and hardened, but its ownership model is not neutral:

- every account, period, proposal, validation, confirmation, journal entry, journal line, receipt,
  and financial audit query is scoped by `organization_id`;
- confirmation and idempotency actors are constrained through organization membership;
- posting triggers compare organization-owned periods, accounts, proposals, confirmations, and
  journal lines;
- reports authorize membership and select organization-owned lines; and
- projects and documents are business-owned references embedded in proposal and journal records.

The debit/credit rules, exact integer arithmetic, lifecycle, atomicity, reversal, and report
arithmetic can be shared. The current ownership columns, membership assumptions, and foreign keys
cannot serve personal finance unchanged. A fake organization would preserve storage convenience at
the cost of incorrect ownership and privacy semantics.

## Architecture options

| Option                                                                         | Correctness                                                                            | Migration and compatibility                                                                                      | Personal fit                                                    | Security and testability                                                        | Decision                       |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------ |
| A. Separate personal and business ledger implementations                       | Two implementations can each be correct initially, but rules and constraints can drift | Low immediate business migration; permanent duplicate maintenance                                                | Good surface fit but creates a second financial truth mechanism | Every invariant, adversarial test, and future AI tool must be duplicated        | Rejected                       |
| B. One-step replacement with generic LedgerBook tables and service             | Clean final ownership model                                                            | Highest cutover risk because all proven business tables, triggers, queries, and reports change together          | Strong                                                          | One canonical path after migration, but rollback and parity proof are difficult | Rejected as migration strategy |
| C. Phased convergence on a persistent LedgerBook and one deterministic service | One final set of accounting rules and database constraints                             | Add mapping first, introduce service/facades, migrate core tables with parity gates, then enable personal writes | Strong without fake organizations                               | Explicit scope, one test matrix, and staged substitution tests                  | Selected                       |

An internal-only `LedgerBookId` with unchanged business tables and separate personal tables was also
considered. It lowers initial migration cost but leaves database invariants implemented twice. It is
acceptable as a temporary refactoring seam during transition, not as the target architecture.

**ENGINEERING DECISION U1:** Select Option C. The target is one persistent ledger-book scope and one
deterministic service, reached through reversible, test-gated stages rather than a big-bang rewrite.

## Target architecture

```text
Client
  → FastAPI authentication
  → FinancialSpaceResolver
      BUSINESS + organization ID → membership/capability check → LedgerBook
      PERSONAL + personal-space ID → owner/grant check → LedgerBook
  → AuthorizedFinancialContext
  → BusinessAccountingFacade | PersonalAccountingAdapter
  → UniversalFinancialService
  → constrained ledger-book persistence
  → immutable audit and deterministic read models
```

`FinancialSpaceRef` is a product/application reference. `LedgerBook` is an internal persisted
financial boundary. They are related but not interchangeable: the resolver proves that an actor may
act in a product space before revealing the corresponding book to the core.

### Core modules after implementation

```text
chatbook/application/financial_context.py   resolve and authorize typed spaces
chatbook/application/business_facade.py     preserve organization API behavior
chatbook/application/personal_adapter.py    translate approved personal commands
chatbook/core/domain.py                     exact money and deterministic invariants
chatbook/core/service.py                    proposal-to-post and reversal lifecycle
chatbook/core/reports.py                    ledger-derived primitive read models
chatbook/core/repository.py                 typed persistence port
chatbook/storage/sqlite_core.py             SQLite transactions and constraints
```

These names are directional rather than an implementation instruction. M5.1-B must first identify a
small extraction sequence from the current modules and preserve public `AccountingEngine` behavior.

## Ledger ownership seam

### Persistent entity

`LedgerBook` should be a persisted internal entity and a typed domain identifier.

Conceptually it contains:

```text
LedgerBook
├── id
├── owner_kind: BUSINESS | PERSONAL
├── organization_id XOR personal_space_id
├── currency
├── minor_unit_digits
└── immutable creation provenance
```

The owner-kind relationship requires real foreign keys plus an exact-one-owner `CHECK`; an untyped
`owner_id` is insufficient. Each organization and each personal space owns exactly one ledger book
in the initial architecture. The ledger book is internal and is never accepted from an untrusted
client as authorization.

**ENGINEERING DECISION U2:** Persist `LedgerBook`. A memory-only concept or mapping with duplicated
personal tables cannot enforce ownership across accounts, periods, proposals, journal, audit, and
idempotency.

### Canonical scope on financial tables

The target canonical financial tables use `ledger_book_id` for:

- chart/account records;
- periods;
- proposals and proposal lines;
- validations and confirmations;
- confirmation provenance;
- journal entries and lines;
- idempotency receipts; and
- financial audit events.

Composite unique keys and foreign keys include the book wherever a child can otherwise reference a
record in another book. Posting triggers compare records inside one book and never infer ownership
from an account, project, or identifier alone. Indexes begin with `ledger_book_id` for scoped reads.

Projects and organization document metadata remain business aggregates. Their optional proposal and
line associations should move to constrained business extension links keyed by both organization and
ledger book, rather than making personal core rows carry fake business ownership. Exact extension
DDL is an M5.1-B migration-design task.

**ENGINEERING DECISION U3:** `ledger_book_id` becomes the canonical future scope for financial-core
records. `organization_id` remains the public business context and migration source; it does not
remain a second mutable owner of canonical core rows.

### Currency and precision

A ledger book has one three-letter uppercase currency label and fixed minor-unit precision. Amounts
remain bounded nonnegative integers on one debit or credit side. Arithmetic uses integers and never
implicit rounding or binary floating point.

Current organization currency and precision are copied and reconciled during migration. There must
not be two independently mutable currency configurations. The business facade may continue returning
the existing response fields by joining the organization to its book.

**ENGINEERING DECISION U4:** Keep one currency and precision per book. Multi-currency, FX, rate
sources, revaluation, and precision changes remain deferred accounting/product work.

## Financial Space resolution and authorization

The existing tagged resolver remains:

```text
FinancialSpaceRef(kind, id)
BUSINESS → Organization → LedgerBook
PERSONAL → PersonalSpace → LedgerBook
```

The backend derives the actor from authentication, resolves the typed space, authorizes that actor
in the ownership domain, loads the mapped book, and issues an internal context:

```text
AuthorizedFinancialContext
├── actor_id
├── financial_space_ref
├── ledger_book_id
├── currency and minor_unit_digits
├── resolved capabilities
├── request/correlation ID
└── optional BUSINESS project_id
```

The universal service accepts this internal context or a narrower capability token created from it.
It does not accept a raw client actor ID, organization ID, personal-space ID, or ledger-book ID as
proof of authority. A project is valid only in a business context and must belong to the resolved
organization/book pair.

**ENGINEERING DECISION U5:** Keep Financial Space resolution in the application/security boundary;
keep ledger rules in the universal service. Existing organization routes stay business-only and
future personal routes stay personal-only.

## Adapter and facade boundary

The business facade preserves the current `AccountingEngine` and FastAPI contracts. It authorizes
membership and roles, resolves the organization's book, translates existing organization commands
to universal commands, and translates results back to existing response shapes. It adds no new
accounting arithmetic.

The personal adapter authorizes the personal owner or a future explicit grant, resolves the personal
book, maps user-facing accounts and approved category mappings to explicit ledger lines, and calls
the same universal service. It cannot weaken periods, confirmation, idempotency, posting, reversal,
or audit.

Adapters may select approved templates and presentation mappings. The universal service validates
the final explicit proposal and owns all posted state transitions.

**ENGINEERING DECISION U6:** One universal service owns financial writes and calculations. Business
and personal boundaries adapt ownership, permissions, terminology, and approved mappings only.

## Business compatibility and migration

Existing organization IDs, routes, memberships, roles, projects, account IDs, period IDs, proposal
IDs, journal IDs, line IDs, confirmation records, receipt keys, audit sequences, and report results
must survive. The private schema may evolve, but current business behavior and historical evidence
must not be reinterpreted.

### Recommended staged migration

1. **Preflight:** validate foreign keys, proposal fingerprints, journal balance, posted/proposal
   equality, period ownership, idempotency uniqueness, audit immutability, row counts, and report
   reconciliation on a copy of a v2 database.
2. **Add owner mapping:** create `ledger_books` and one BUSINESS book for every organization in one
   transaction. Keep organization IDs unchanged. Record schema migration provenance.
3. **Extract the service seam:** make the existing business facade resolve the mapped book while a
   compatibility repository still uses the proven organization-scoped tables. All existing tests
   must remain byte-for-byte or value-for-value equivalent.
4. **Build canonical core tables:** in a later schema step, create book-scoped tables and constraints,
   copy rows without changing their IDs or state, preserve audit sequence/timestamp/payload, and copy
   business project/document links to constrained extensions.
5. **Reconcile before switch:** compare row counts, immutable fingerprints, confirmation provenance,
   ledger lines, balances, reports, reversals, receipts, and audit history for every organization.
6. **Atomic cutover:** switch the repository only after parity succeeds; retain a tested backup and
   fail the migration rather than partially converting.
7. **Enable personal writes last:** add personal ownership and adapter paths only after business
   compatibility, cross-scope substitution, concurrency, rollback, and database-trigger tests pass.

SQLite table reconstruction may be required to replace organization-scoped foreign keys. That work
must happen inside an explicit migration transaction with foreign-key verification after the copy.
An additive mapping-only v3 followed by a canonical-table v4 is safer than combining both risks in
one release; the final version numbers belong to M5.1-B planning.

**ENGINEERING DECISION U7:** Use staged schema versions and parity gates. Never dual-write financial
history during migration, silently rewrite audit payloads, or enable personal posting against a
partially migrated store.

## Personal integration

`PersonalSpace` remains the private product owner defined by M5.0. It is independent of organizations
and memberships. The initial model has one personal space and one ledger book per user. The personal
adapter checks owner access before resolving its book.

Core records belong to the book. Personal account profiles, categories, and future plans belong to
the personal space and reference only records from its mapped book. Audit and idempotency are scoped
to the same book. An organization route can never resolve a personal book, even if a supplied ID has
the same text value.

**PRODUCT DECISION P1:** Whether one personal space per user remains permanent, and how households,
dependants, joint owners, advisors, export, deletion, retention, and recovery work, require product,
privacy, and legal approval.

## User-facing accounts and ledger accounts

The core account is an exact ledger classification with stable identity, account type, active state,
and book ownership. It is not required to use customer-facing terminology.

A personal `FinancialAccount` is presentation metadata for Checking, Savings, Cash, Visa, or a loan.
The initial design maps one active presentation account to one ledger asset or liability account in
the same book. Its balance is always derived from posted lines. Closing or hiding the presentation
record cannot edit the ledger account or history.

Income and expense categories are separate stable labels with versioned mappings to owned ledger
income/expense accounts. Proposals retain category and mapping-version provenance. Renames and new
mappings affect future proposals only.

**ENGINEERING DECISION U8:** Keep presentation accounts and categories outside the core ledger while
requiring same-book, versioned mappings. Do not store mutable balances or category totals.

**PRODUCT DECISION P2:** Default personal account kinds, category taxonomy, rename/archive behavior,
and whether historical display recategorization is allowed require product approval.

**ACCOUNTING POLICY A1:** Default ledger chart, category-to-account mapping, negative-balance
presentation, and correction versus non-financial recategorization require accountant approval.

## Financial Activity abstraction

`FinancialActivity` should not be a persisted source-of-truth aggregate. It has two safe forms:

1. a typed application command such as `RecordMoneyIn`, `RecordMoneyOut`, `Transfer`,
   `RecordLiabilityEvent`, `EstablishOpeningBalance`, or `CorrectPosting`; and
2. a read model derived from posted entries, explicit immutable provenance, and authorized
   presentation mappings.

The command compiles to a complete proposal with explicit ledger lines. Its kind may be retained as
non-authoritative proposal/audit provenance, but posting correctness comes from the lines and core
validation. The read model never stores its own balance or posted amount.

**ENGINEERING DECISION U9:** Financial Activity is application command vocabulary plus a derived
read model, not duplicate financial truth.

**PRODUCT DECISION P3:** The final customer-facing activity names, forms, and progressive-disclosure
language require product and usability approval.

## Universal money flows

All flows use one owned book, exact amount/date/currency context, an explicit proposal, deterministic
validation, exact-version authenticated confirmation, atomic posting, and immutable audit.

| Flow                | Concept and required input                                                                 | Proposal and ledger                                                                           | Deterministic report treatment                                                 | Policy boundary                                                                    |
| ------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| Money in / income   | A receipt into an owned asset account plus an explicitly selected source/classification    | Debit destination asset; credit the approved income, liability, equity, or transfer account   | Counts as income only when the approved ledger classification says so          | Gifts, refunds, loans, contributions, and revenue recognition must not be inferred |
| Money out / expense | A payment from an asset account or increase in a liability plus an explicit classification | Debit approved expense/asset/liability account; credit payment asset or liability             | Counts as expense only for approved expense lines                              | Tax, capitalization, reimbursement, and expense recognition remain policy          |
| Same-space transfer | Movement between two accounts in one book                                                  | One balanced proposal; normally balance-sheet accounts on both sides                          | Transfer view; excluded from income/expense when no income/expense line exists | Investment disposals, fees, and FX are not assumed to be simple transfers          |
| Liability event     | Borrowing, credit purchase, repayment, refund, fee, or adjustment with explicit components | Explicit asset/expense/liability lines; no inferred split                                     | Liability balances derive from lines; components follow their accounts         | Principal, interest, fee, penalty, due-date, and amortization rules need approval  |
| Opening balance     | Existing position, effective date, source/evidence, and approved offset mapping            | Batch of ordinary proposals or one bounded proposal; normal posting lifecycle                 | Appears from the opening date with disclosed provenance                        | Offset account, grouping, date, and prior-period treatment need approval           |
| Correction          | Target posted entry, reason, correction date, and replacement when required                | Full compensating reversal through the ordinary lifecycle, then optional replacement proposal | Original, reversal, and replacement remain visible                             | Partial correction and historical recategorization rules remain deferred           |

**ENGINEERING DECISION U10:** Universal commands never infer financial classification from direction
alone. They require an approved mapping and always compile to explicit ledger lines.

## Transfers

A same-space transfer remains one atomic balanced entry inside one book. It cannot cross the book
boundary.

A personal/business transfer remains two independently authorized effects and one non-financial
correlation record. Each side has its own proposal version, confirmation, idempotency key, post, and
audit. The correlation may reveal only the minimum status and typed references authorized to the
viewer. If one side posts and the other fails, recovery is retry or compensating reversal; committed
history is never deleted.

**ENGINEERING DECISION U11:** Retain the M5.0 transfer architecture. Do not implement distributed
rollback or a cross-book journal.

**PRODUCT DECISION P4:** Whether one user gesture can coordinate two confirmations and what status is
shown during partial completion require product and authorization approval.

**ACCOUNTING POLICY A2:** Contributions, drawings, salary, distributions, reimbursements, and loans
require explicit account mappings for both spaces.

## Proposal, confirmation, and posting

The universal service preserves this state transition for both ownership domains:

```text
proposal
→ deterministic validation and fingerprint
→ exact-version confirmation by authenticated actor
→ current-state revalidation
→ atomic journal post + audit + idempotency receipt
```

The proposal carries book scope, immutable lines, date, description, source provenance, mapping
versions, and optional approved extension references. Confirmation records the proposal/version,
validation, actor, UTC system timestamp, and request identifier. The service rechecks book scope,
active accounts, period, balance, line equality, reversal constraints, and confirmation actor inside
the write transaction.

Idempotency keys are scoped by book, actor, operation, and key. A matching retry returns the original
result; conflicting reuse fails. Validation and confirmation records cannot cross books.

**ENGINEERING DECISION U12:** The lifecycle is universal and mandatory. Adapters and future AI can
create proposals; they cannot bypass confirmation or call lower-level journal writes.

## Period capability and policy

The core retains non-overlapping dated periods, open/locked state, and the rule that posting requires
exactly one open period. Current business creation, inclusive boundaries, one-way locking, and report
behavior remain unchanged.

The core provides period capability; an owner adapter selects an approved policy. Personal
calendar-month periods, a long continuously open period, automatic future period creation, closing,
and late correction have different product and accounting consequences.

**ENGINEERING DECISION U13:** Scope periods by ledger book and retain deterministic enforcement.

**PRODUCT DECISION P5:** Personal period visibility, automatic creation, notifications, and lock UX
require product approval.

**ACCOUNTING POLICY A3:** The personal period model, closing/locking authority, late entries,
adjustment periods, and reopening require accountant approval. No default is selected in M5.1-A.

## Planning and management layer

Budgets, goals, reminders, recurring schedules, expected revenue, and project budgets are mutable
planning/management records outside the core ledger. They may reference a Financial Space and
approved accounts/categories/projects. Their actual values are deterministic queries over posted
lines.

A future schedule may create an idempotently identified proposal occurrence. It cannot validate,
confirm, post, reverse, or mark a financial event paid.

**ENGINEERING DECISION U14:** Planning may reference actuals but never mutates them or stores a second
authoritative actual total.

**PRODUCT DECISION P6:** Budget periods, rollover, goals, reminder recurrence, schedule occurrence,
and automation behavior require later product decisions.

## Tax and compliance boundary

The universal core records financial facts and management classifications. It makes no claim of
jurisdictional correctness or statutory compliance.

Outside the core:

- income, sales, VAT/GST, withholding, payroll, and other tax rules;
- statutory charts and statements;
- filing forms, deadlines, submissions, and regulator integrations;
- country-specific depreciation, capital allowance, or recognition logic; and
- compliance determinations and professional advice.

A future jurisdiction package may consume versioned, authorized core read models and retain its rule
set, jurisdiction, effective dates, source, and calculation provenance. If it proposes adjustments,
they enter through the ordinary proposal lifecycle. It receives no direct journal-write or audit-edit
capability.

**ENGINEERING DECISION U15:** Tax/compliance is an external capability layer with versioned
provenance and proposal-only write access.

**PRODUCT DECISION P7:** Whether Chatbooks offers any jurisdiction package, what it claims, and
which professional review is required need product/legal approval.

**ACCOUNTING POLICY A4:** Every jurisdiction rule, statutory mapping, tax calculation, filing, and
recognition policy requires a qualified domain expert; none is universal core behavior.

## Reporting boundary

The core owns deterministic primitives:

- posted general-ledger lines and journal summaries;
- account balances and trial-balance arithmetic;
- exact account-type and date-range aggregates;
- transfer candidates based on explicit immutable provenance/mappings;
- selected-account cash movement; and
- audit/proposal/posting lifecycle read models.

Application/presentation layers name, group, and disclose those primitives for a context:

- the business facade keeps the current general ledger, trial balance, non-statutory income
  statement, balance sheet, cash movement, and project views;
- the personal adapter presents activity, spending, income, account balances, category spending,
  and approved cash position; and
- statutory statements, tax reports, and regulated classifications remain outside the core.

All totals come from the core or an external versioned policy layer over core data. UI and AI do not
recalculate financial totals.

**ENGINEERING DECISION U16:** Put ledger arithmetic and neutral aggregates in the core; put audience
terminology, report composition, and policy-specific classification in authorized read-model layers.

**ACCOUNTING POLICY A5:** Cash-account inclusion, formal income/expense recognition, cash-flow
classification, net-worth valuation, and statutory presentation require approval.

## Audit and idempotency scope

Financial audit events carry `ledger_book_id`, actor, UTC event timestamp, event/entity identity,
before/after state, operation/request metadata, and ownership provenance. Global identity events may
remain outside a book. Migration preserves every existing audit sequence, timestamp, actor, payload,
and metadata; adding a book scope is migration metadata, not permission to rewrite history.

Receipt uniqueness is `(ledger_book_id, actor_id, operation, idempotency_key)`. The receipt and
financial mutation commit in the same transaction. Audit and receipts are append-only and queried
only after book authorization.

**ENGINEERING DECISION U17:** Audit and idempotency follow the ledger-book boundary and remain atomic
with the financial operation.

## Security and isolation model

| Threat                                                                         | Required control                                                                             |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Personal ID sent to an organization route                                      | Route resolves only Organization; lookup returns no personal data before any child query     |
| Organization ID sent to a personal route                                       | Route resolves only PersonalSpace and verifies owner/grant                                   |
| Raw ledger-book ID supplied by client                                          | Never accepted as authority; resolve it server-side from typed space                         |
| Cross-book account, period, proposal, confirmation, project, or line reference | Composite book-scoped foreign keys plus service validation                                   |
| Cross-space transfer leaks the other side                                      | Correlation returns only authorized local references and minimal redacted status             |
| Search, cache, export, analytics, or notification mixes spaces                 | Keys and jobs include space kind, owner ID, and book ID; authorize on read and delivery      |
| Audit endpoint reveals another book                                            | Resolve space authority first, then query by book; no global financial audit listing         |
| Logs expose sensitive payloads                                                 | Structured allowlist, redaction, no credentials or financial documents, controlled retention |
| Future document retrieval crosses owners                                       | Document owner and linked book/space validated independently; document text is untrusted     |
| Future AI mentions another space or identifier                                 | Conversation text never changes the server-issued authorized context                         |

Authorization must be fail-closed. A not-found response should be preferred when distinguishing
forbidden from absent would reveal another owner's resource. Background work repeats authorization
or uses a narrowly scoped, expiring server-issued capability; it never trusts queued client scope.

**ENGINEERING DECISION U18:** Isolation is enforced in resolver, service, and database constraints.
Frontend context is presentation state only.

## Future AI context

The future orchestrator receives a server-issued envelope:

```text
FinancialContext
├── FinancialSpaceRef(kind, id)
├── internal authorized ledger-book capability
├── display name, currency, precision
├── actor and resolved tool capabilities
├── optional BUSINESS organization and project
├── date/as-of scope
├── allowed source references
└── request/retrieval provenance
```

The internal book capability is not displayed to or chosen by the model. Tools reauthorize their
arguments and return core-generated numbers. AI may retrieve authorized data, ask clarification,
explain verified results, and create structured proposals. It cannot confirm, post, reverse, lock a
period, edit audit history, access raw storage, or combine spaces without a separately authorized
application operation.

**ENGINEERING DECISION U19:** AI remains a scoped proposal client above the resolver and adapters.

**PRODUCT DECISION P8:** Combined-space user experiences, AI retention, conversation deletion,
explanation wording, and human-review UX require product/privacy approval.

## Required implementation evidence

Before any personal financial write is enabled, M5.1-B and later work must prove:

- v2 migration preserves every business identifier, row, immutable payload, audit sequence, receipt,
  balance, reversal chain, and report result;
- old organization routes and response behavior remain compatible;
- personal and business identifiers fail when substituted across route families;
- every core foreign key and posting trigger is book-scoped;
- concurrent posting, period locking, retries, and reversals remain serializable;
- failures during migration or posting leave no partial state;
- personal owner checks and business role checks cannot select the other owner's book;
- same-space transfers do not create income/expense under the approved mapping;
- cross-space partial completion is recoverable without deletion;
- audit and idempotency remain append-only and atomic; and
- all current Python and frontend checks remain passing throughout the transition.

## Decision classification register

### Engineering decisions

U1 phased convergence; U2 persisted LedgerBook; U3 canonical book scope; U4 exact single-currency
book; U5 server-side Financial Space resolution; U6 facade/adapter boundary; U7 staged migration;
U8 presentation-account/category mappings; U9 Financial Activity as command/read model; U10 explicit
flow mappings; U11 two-effect cross-space coordination; U12 universal proposal lifecycle; U13
book-scoped period capability; U14 planning separation; U15 external compliance layer; U16 neutral
report primitives; U17 book-scoped audit/idempotency; U18 layered isolation; U19 proposal-only AI.

### Product decisions

P1 personal-space/sharing lifecycle; P2 personal account/category experience; P3 activity language;
P4 coordinated cross-space confirmation UX; P5 personal period UX; P6 budgets/goals/reminders and
automation; P7 compliance product scope and claims; P8 combined views and AI privacy/retention.

### Accounting policies

A1 personal chart/mappings and corrections; A2 cross-space classification; A3 personal period and
close policy; A4 every jurisdiction/compliance rule; A5 report classifications and valuation. The
larger policy register remains in
[`M5_PERSONAL_FINANCE_DECISIONS.md`](M5_PERSONAL_FINANCE_DECISIONS.md) and
[`accounting-model.md`](accounting-model.md).

## Intentionally deferred

Implementation, schema versions, personal persistence, personal API/UI, budgets, reminders,
recurrence, goals, documents, bank integration, AI, multi-currency, FX, tax, compliance, cloud
deployment, and production-database selection remain outside M5.1-A.
