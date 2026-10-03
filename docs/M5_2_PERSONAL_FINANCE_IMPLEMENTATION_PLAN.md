# M5.2-B personal finance foundation and persistence implementation plan

**Date:** 2026-09-28  
**Milestone:** Planning only  
**Project and product:** Chatbooks
**Status:** Implementation-ready plan; no code, schema, API, or executable behavior implemented

## Purpose and stop boundary

This plan defines the changes needed to add private PERSONAL ownership and persistence on top of the
existing universal financial core. It does not authorize those changes. It stops before code, schema
migrations, endpoints, UI, or personal financial behavior.

The design follows the approved personal model in
[`personal-finance-model.md`](personal-finance-model.md), the M5.2-A policy in
[`M5_2_PERSONAL_FINANCE_MVP_POLICY.md`](M5_2_PERSONAL_FINANCE_MVP_POLICY.md), and ADRs
[0013](decisions/0013-personal-ownership-isolation.md) through
[0020](decisions/0020-jurisdiction-compliance-outside-core.md). The deterministic ledger remains the
only source of actual financial state. The implementation must reuse `UniversalFinancialService`;
it must not add a personal transaction store, mutable balance cache, second posting engine, or
direct ledger-write path.

## Hard prerequisite: complete M5.1-C4 first

Normal Chatbooks startup still uses schema v3. Schema v4 and `SQLiteBookStorage` exist only in the
explicit C3/C4A rehearsal path. M5.1-C4 has not been authorized or executed.

No M5.2 implementation may begin until all of the following are true:

1. the separately authorized M5.1-C4 BUSINESS cutover is complete;
2. the deployment database is schema v4 and normal runtime selects the canonical book repository;
3. the C4 release checklist, read-only parity, canary, reversal, audit-sidecar, recovery, and writer-
   resumption gates have passed;
4. the approved post-cutover observation period has completed without unexplained financial,
   idempotency, audit, integrity, or report discrepancies; and
5. the v4 source, backup, recovery release, manifests, and rollback boundary remain protected under
   the C4 runbook.

M5.2 must not be bundled into C4. Combining BUSINESS canonical cutover with a new owner kind would
remove the clean parity baseline and make rollback evidence ambiguous.

## Existing implementation baseline

The repository already provides:

- exact integer minor-unit money and deterministic double-entry validation;
- immutable proposals, validations, exact-version confirmations, postings, reversals, and audit;
- book-scoped schema-v4 core tables and composite foreign keys on rehearsed copies;
- atomic financial writes and receipts under SQLite `BEGIN IMMEDIATE`;
- `FinancialSpaceRef` and `AuthorizedFinancialContext` values, including the `PERSONAL` enum value;
- one `UniversalFinancialService` implementation for accounts, periods, proposal lifecycle,
  reversal, balances, reports, audit, and idempotency;
- a stable BUSINESS facade through `AccountingEngine`;
- organization role authorization in the API; and
- cross-book, migration, failure-injection, concurrency, compatibility, and source-boundary tests.

The repository does not yet provide:

- a `PersonalSpace` table or owner resolver;
- a PERSONAL ledger-book owner row;
- personal account/category persistence;
- personal proposal provenance or read models;
- a personal storage adapter/facade;
- personal routes or authorization dependencies;
- an approved personal period policy; or
- any enabled personal posting template.

Several schema-v4 implementation details remain BUSINESS-specific and must be removed from the
shared internal path without changing BUSINESS behavior:

- `ledger_books.owner_kind` currently permits only `BUSINESS` and requires `organization_id`;
- repository record types and proposal fingerprint inputs carry `organization_id`;
- `SQLiteBookStorage.bind` rejects non-BUSINESS contexts;
- repository reads and writes assume one BUSINESS extension row for each proposal and line;
- validation fingerprinting accepts only `organization-v1`;
- actor/owner triggers authorize organization membership only; and
- new canonical audit JSON is serialized in the legacy organization-facing shape.

## Target ownership model

### PersonalSpace

`PersonalSpace` is the stable product ownership and privacy boundary for personal data.

```text
User
└── owns one PersonalSpace
    ├── one internal LedgerBook
    ├── FinancialAccount presentation records
    ├── PersonalCategory records and mapping history
    ├── personal proposal provenance
    └── authorized personal reports and audit history
```

The initial lifecycle is deliberately small:

```text
ABSENT → ACTIVE
```

- Creation uses the authenticated user as `owner_user_id`; a client cannot nominate another owner.
- `owner_user_id` is unique, enforcing at most one personal space per user.
- The space ID is stable and is used in typed PERSONAL routes and references.
- Non-financial display-name changes are allowed only to the owner and are audited.
- Ownership transfer, sharing, household membership, delegation, merge, archive, deletion, recovery,
  export deletion, and reuse of a deleted owner ID are not implemented.
- The implementation must not expose a delete or owner-change operation until retention, recovery,
  consent, and legal requirements are approved.

The minimum persisted fields are:

| Field           | Rule                                                                   |
| --------------- | ---------------------------------------------------------------------- |
| `id`            | Stable opaque identifier; never inferred from `user_id`                |
| `owner_user_id` | Required unique foreign key to `users.id`                              |
| `display_name`  | Non-financial user-facing label with bounded validation                |
| `created_at`    | UTC system timestamp                                                   |
| `created_by`    | Authenticated owner; required and equal to `owner_user_id` at creation |

Currency and precision belong authoritatively to `LedgerBook`, not to a separately mutable
`PersonalSpace` copy. A personal-space read model may project them from its book.

### FinancialSpaceRef resolution

`FinancialSpaceRef(PERSONAL, id)` means `PersonalSpace.id`; `FinancialSpaceRef(BUSINESS, id)` remains
`Organization.id`. The pair is mandatory.

Resolution order for PERSONAL is:

1. derive `actor_id` from the authenticated session or an explicitly trusted local boundary;
2. select `PersonalSpace` by the supplied personal-space ID only;
3. require `personal_spaces.owner_user_id == actor_id`;
4. resolve the one PERSONAL `LedgerBook` owned by that space;
5. verify owner kind, owner ID, currency, precision, and lifecycle constraints;
6. intersect operation capabilities with server-owned M5.2 feature gates; and
7. issue an immutable `AuthorizedFinancialContext`.

Failure at any step returns the same non-disclosing not-found response used for inaccessible
personal resources. Organization membership and roles are never consulted as personal authority.
Raw book IDs are never accepted from clients or treated as authority.

### PersonalSpace to LedgerBook mapping

After C4 establishes schema v4, the first personal schema migration is planned as schema v5. The
implementation agent must confirm that v5 is still the next unused version before writing the
migration; a different intervening migration requires renumbering, not combining histories.

The v5 owner model is:

```text
LedgerBook
├── owner_kind: BUSINESS | PERSONAL
├── organization_id: present only for BUSINESS
├── personal_space_id: present only for PERSONAL
├── currency
└── minor_unit_digits
```

Database constraints must enforce:

- exactly one owner column is non-null;
- the non-null owner column agrees with `owner_kind`;
- `organization_id` is unique when present;
- `personal_space_id` is unique when present;
- both owner references use real foreign keys;
- existing BUSINESS book IDs, owner mappings, currency, precision, and provenance are unchanged;
- PERSONAL book currency and precision are immutable after creation in this milestone; and
- owner kind, owner reference, and book ID cannot be updated or deleted through supported storage.

Create the personal space and its ledger book in one private database transaction. A successful
commit creates both or neither. Startup verification must prove every active `PersonalSpace` has
exactly one PERSONAL book and every PERSONAL book has exactly one owner. The book is internal and is
never included in an authorization request.

The planned personal book identifier is a stable server-generated value in the existing internal
namespace. Freeze its exact format in migration tests before implementation. It must not encode a
user-chosen label, email address, or other mutable/private identifier.

## Persistence model

### FinancialAccount presentation model

`FinancialAccount` is the user-facing representation of where personal money is held or owed. It is
not a ledger account replacement and contains no balance or mutable actual total.

| Field               | Rule                                                                  |
| ------------------- | --------------------------------------------------------------------- |
| `id`                | Stable opaque ID                                                      |
| `personal_space_id` | Required owner FK                                                     |
| `ledger_book_id`    | Required internal scope, constrained to the space's book              |
| `ledger_account_id` | Required same-book account FK; unique for active presentation mapping |
| `name`              | User-facing label                                                     |
| `kind`              | `CHECKING`, `SAVINGS`, `CASH`, `CREDIT_CARD`, or `PERSONAL_LOAN`      |
| `institution_name`  | Optional presentation metadata                                        |
| `masked_reference`  | Optional masked presentation value; never a credential                |
| `state`             | `ACTIVE`; archive/deactivation is not exposed in this milestone       |
| provenance          | UTC creation/update timestamps and authenticated actors               |

Kind-to-ledger-type constraints are deterministic:

- Checking, Savings, and Cash link to an `ASSET` ledger account.
- Credit Card and Personal Loan link to a `LIABILITY` ledger account.
- The linked account must belong to the exact personal book.

The `FinancialAccount` row never stores balance, available funds, credit limit, principal schedule,
interest, valuation, or currency conversion. Balance reads call the universal service and join the
verified result to presentation metadata.

Account creation needs an atomic composition seam because the current universal account command
creates only the ledger account. Implement a narrow, private personal-account provisioning unit of
work that:

1. resolves and authorizes the personal context;
2. creates the ledger account through `UniversalFinancialService` using a server-supplied stable
   account ID;
3. inserts the same-space `FinancialAccount` mapping in the same storage transaction;
4. verifies the kind/account-type constraint; and
5. commits the active core account, presentation mapping, audit events, and scopes together or rolls
   all of them back.

The implementation may expose this as a new service composition port, but it must not give the
personal adapter a connection or direct account-table write. If the current unit-of-work API cannot
span core and personal metadata safely, extend that private interface first and prove rollback with
failure injection. Do not persist a partially provisioned or partially active account as a normal
recovery design.

Rename affects presentation only and is audited. Account deactivation/archive semantics, posting
to inactive accounts for corrections, and deletion/retention remain unresolved; no public archive
operation is enabled in the foundation phase.

### PersonalCategory

`PersonalCategory` is a stable user-facing income or expense label, separate from ledger account
identity.

| Field               | Rule                                                    |
| ------------------- | ------------------------------------------------------- |
| `id`                | Stable opaque ID                                        |
| `personal_space_id` | Required owner FK                                       |
| `name`              | Required owner-scoped label                             |
| `direction`         | `INCOME` or `EXPENSE`                                   |
| `origin`            | `STARTER` or `USER`                                     |
| `active`            | Presentation availability only                          |
| provenance          | UTC creation/update timestamps and authenticated actors |

Starter labels may be installed as unmapped presentation records. Their presence does not approve a
chart of accounts or permit posting. Category-name case, Unicode normalization, and uniqueness are
product decisions. Until approved, the persistence layer must not silently normalize or merge
labels; stable IDs remain the unambiguous references.

Rename and activation-state changes are audited and affect future selection only. They do not change
historical lines, proposal fingerprints, or report provenance. Deletion is not supported.

### Versioned CategoryAccountMapping

Each category-to-ledger relationship is an immutable version:

| Field                      | Rule                                            |
| -------------------------- | ----------------------------------------------- |
| `id`                       | Stable opaque ID                                |
| `personal_space_id`        | Required owner FK                               |
| `ledger_book_id`           | Required exact space book                       |
| `category_id`              | Required same-space category FK                 |
| `ledger_account_id`        | Required same-book ledger account FK            |
| `version`                  | Positive, monotonically increasing per category |
| `created_at`, `created_by` | Required provenance                             |
| `supersedes_mapping_id`    | Optional prior version in the same category     |

An INCOME category maps only to a `REVENUE` account. An EXPENSE category maps only to an `EXPENSE`
account. Mapping rows are append-only. A separately constrained current pointer may select the
latest approved mapping; changing it is audited and never updates earlier mappings.

Proposal creation captures the category ID, category label snapshot, mapping ID, mapping version,
and resolved ledger account. Validation fingerprints include this immutable provenance. Posted
category actuals are calculated from posted journal lines joined through captured provenance; no
category total is stored.

Default chart accounts and starter category mappings remain disabled until the M5.2-A accountant
gate is approved. The implementation must permit categories to exist without an active mapping and
return a stable `policy_not_configured` failure when a financial operation needs one.

### Personal proposal and posted provenance

Do not add a personal transaction/activity table. Core `transactions`, `transaction_lines`,
`validations`, `confirmations`, `journal_entries`, and `journal_lines` remain the only financial
lifecycle and posted actuals.

Add immutable PERSONAL extension records only for user-facing classification and reproducibility:

- proposal-level context: personal space, typed activity kind, source/request provenance;
- line-level context: presentation account role, `FinancialAccount` ID where applicable, category
  ID/mapping ID/version/label snapshot where applicable; and
- journal-line context copied from the exact confirmed proposal at posting and reversal.

These extensions contain no balance, independently editable amount, or second lifecycle state. A
PERSONAL core proposal must have the required personal extension family and no BUSINESS project or
document extension. A BUSINESS proposal keeps its current extension family and cannot receive a
personal extension. Database triggers and service checks enforce owner-kind exclusivity.

Reversal construction copies the original immutable personal provenance while swapping the exact
ledger debit/credit lines. The original and reversal remain separately visible and audited.

### Personal periods

Personal periods reuse the existing book-scoped `accounting_periods` table and universal service.
There is no personal period table and no alternative posting rule.

The foundation persists no automatically selected month, year, rolling period, or perpetual-open
period. It exposes no personal period creation, lock, reopen, or override API. All personal proposal
generation, validation, confirmation, posting, and reversal-posting capabilities stay disabled until
the M5.2-A period policy is approved and represented by explicit server-created periods.

When that policy is approved in a later milestone, the adapter will call the existing universal
period commands under an internal capability. Posting will continue to require exactly one open
period containing the financial date. Late entry, future period creation, lock authority, and
reopening remain policy questions, not implementation defaults.

## Repository and storage changes

### Ownership-neutral records

Refactor internal financial repository records to use `ledger_book_id` as canonical ownership.
Remove required `organization_id` from shared core record shapes. Business-only organization,
project, and document values move to typed BUSINESS extension records; personal presentation values
move to typed PERSONAL extensions.

This refactor must be completed against BUSINESS schema v4 first. Every existing BUSINESS command,
row, validation fingerprint, audit payload, error, API result, CLI result, and report must remain
identical before PERSONAL storage can bind.

### Storage interfaces

Retain named repository operations and a private unit-of-work. Do not add generic SQL, cursor, or
connection access. Split responsibilities as follows:

```text
CanonicalFinancialRepository
├── book-scoped core accounts, periods, proposals, confirmations, entries, reports
├── deterministic fingerprint material
├── audit/receipt operations
└── private atomic unit-of-work

BusinessExtensionRepository
└── organization/project/document extension projection

PersonalExtensionRepository
├── PersonalSpace ownership reads
├── FinancialAccount persistence
├── PersonalCategory and mapping history
└── personal proposal/journal provenance
```

`SQLiteBookStorage.bind(context)` becomes an owner-kind dispatcher after independent resolver
authorization. BUSINESS binding verifies the organization-to-book relation and uses the business
extension repository. PERSONAL binding verifies the personal-space-to-book relation and uses the
personal extension repository. The shared core repository never authorizes an owner from a book ID.

Every lookup includes the bound book or personal-space scope. Methods such as `get_account(id)` that
could resolve another owner's identifier must become context-bound queries that return no cross-
space distinction.

### Validation fingerprint versions

Preserve every existing BUSINESS `organization-v1` fingerprint and its exact serializer. Do not
recompute or relabel existing values.

Add a new explicit PERSONAL fingerprint version only after its canonical serialization is frozen by
golden tests. It must bind:

- book and personal-space scope;
- proposal ID/version, financial date, description/source, and ordered core lines;
- presentation-account roles;
- category ID, label snapshot, mapping ID/version, and resolved ledger account; and
- any other immutable personal provenance displayed for confirmation.

The universal service chooses and verifies the serializer by stored fingerprint version. Unknown
versions fail closed. Payload equality never replaces caller-supplied idempotency.

### Schema migration mechanics

The planned v5 migration is additive except for the small `ledger_books` owner-table
reconstruction. It must use the proven C3/C4 migration style:

1. stop writers and verify schema v4 plus post-C4 observation evidence;
2. create and restore-test a new protected backup;
3. run integrity, foreign-key, audit, receipt, ledger, reversal, and report manifests;
4. create `personal_spaces` and the replacement typed-owner book table;
5. copy existing BUSINESS book rows byte-for-byte in all existing values;
6. add personal presentation, mapping, provenance, audit-scope, and gate/configuration tables or
   constrained records;
7. install owner-kind, same-space, append-only, and audit triggers;
8. reconcile every BUSINESS row and observable result before schema-version advance;
9. run full foreign-key and integrity checks; and
10. set schema version only at the final transaction gate.

No personal space or personal book is backfilled for existing users. Provisioning is an explicit,
authenticated post-migration operation. This avoids assuming that every user wants personal finance
and avoids inventing opening balances, accounts, periods, or categories.

If SQLite cannot safely reconstruct `ledger_books` while retaining child foreign keys in one
verified transaction, stop and revise the migration design. Do not weaken foreign keys or leave a
permanent mapping table that cannot enforce exactly one owner merely to avoid reconstruction.

## Universal service reuse and personal adapter

### UniversalFinancialService remains exclusive

The following continue to belong only to `UniversalFinancialService` and its repository:

- exact amounts and balanced-line validation;
- account/period current-state checks;
- proposal creation and immutable lines;
- validation fingerprints;
- exact-version confirmation;
- idempotent posting and journal equality;
- reversal construction and double-reversal protection;
- ledger, balance, trial-balance, and neutral report arithmetic; and
- atomic financial audit and receipt behavior.

No personal route, adapter, presentation repository, future AI tool, or UI code may reimplement
these rules or write core financial tables.

### PersonalFinanceFacade responsibilities

Create a personal application facade/adapter above the universal service. It may:

- resolve an owner-authorized PERSONAL context;
- manage non-financial personal-space profile data;
- provision presentation accounts through the private atomic composition seam;
- manage categories and append-only mappings;
- accept only typed personal activity commands;
- require all referenced presentation records to belong to the same personal space;
- translate an approved command into complete explicit ledger lines and immutable provenance;
- call the universal service for every financial lifecycle operation;
- shape personal account, activity, category, and report read models from verified core results; and
- apply server-owned feature gates before compiling a command.

It may not accept arbitrary debit/credit lines through the normal personal MVP API, infer a
classification from money direction, choose a missing category mapping, create a period, confirm or
post on behalf of the user, calculate authoritative totals, expose a book ID, or write audit events.

## API and authorization boundary

The future API uses distinct typed route families:

```text
GET  /api/v1/financial-spaces
POST /api/v1/personal-spaces
GET  /api/v1/personal-spaces/{personal_space_id}
PATCH /api/v1/personal-spaces/{personal_space_id}
...  /api/v1/personal-spaces/{personal_space_id}/accounts
...  /api/v1/personal-spaces/{personal_space_id}/categories
...  /api/v1/personal-spaces/{personal_space_id}/proposals
...  /api/v1/personal-spaces/{personal_space_id}/entries
...  /api/v1/personal-spaces/{personal_space_id}/reports
...  /api/v1/personal-spaces/{personal_space_id}/audit
```

The existing `/api/v1/organizations/{organization_id}/...` contract remains unchanged.

API requirements:

- all routes require the existing authenticated session boundary;
- `actor_id` always comes from the session, never the body, query, or path;
- owner resolution occurs before a child resource query;
- personal routes use an owner-only dependency, not organization RBAC;
- organization permissions grant no personal capability;
- request and response models contain personal IDs, never internal book IDs;
- confirmation shows and binds the exact proposal version and PERSONAL fingerprint provenance;
- confirmation and posting require caller-supplied idempotency keys;
- list endpoints are owner-scoped and paginated with non-leaking cursors;
- inaccessible and absent cross-space IDs produce the same response; and
- clients cannot create, edit, delete, or replace audit events.

Foundation endpoints may expose space, account, and category persistence only after their individual
tests pass. Financial proposal/posting endpoints remain unavailable or return a stable feature-
gated response until every required policy gate for that operation is approved.

## Personal/business isolation guarantees

The implementation must enforce isolation at four layers:

1. **Route:** personal and business route families parse different owner types.
2. **Resolver:** personal owner equality and business membership/role checks are independent.
3. **Service/repository:** all records use the bound book plus the correct typed extension.
4. **Database:** owner XOR constraints, composite book foreign keys, same-space foreign keys,
   owner-kind extension triggers, and immutable audit scopes reject substitutions.

The following are forbidden:

- using a PersonalSpace ID on an organization route or an organization ID on a personal route;
- resolving a raw book ID supplied by a caller;
- linking a personal account/category to a BUSINESS book or vice versa;
- attaching a business project/document to a PERSONAL proposal;
- returning personal rows through organization audit/report/list endpoints;
- using an organization membership or role to authorize personal data;
- combining personal and business totals in one report; and
- creating a journal entry with lines from more than one book.

Cross-space transfers remain absent. No correlation record or coordinated workflow is added in this
milestone.

## Audit and idempotency

### Audit

Every PersonalSpace, presentation-account, category, mapping, and financial mutation must create an
immutable audit event in the same transaction as the mutation. Personal audit events record:

- authenticated actor;
- UTC system timestamp distinct from the financial date;
- event and entity type/ID;
- previous/new state where applicable;
- request/operation metadata;
- PERSONAL space scope; and
- ledger-book scope for financial entities.

Existing BUSINESS audit rows, sequence values, JSON bytes, metadata, and API presentation remain
unchanged. Personal financial events use `organization_id = NULL`, an immutable book-scope sidecar,
and an immutable personal-space-scope sidecar. Personal master-data events require the personal-
space sidecar even when they do not yet reference a book-scoped financial entity.

Only installed database triggers under the private transaction context may append audit data.
Direct insert, update, delete, or replacement remains rejected. Audit reads authorize the personal
space first and then query its scope; there is no global financial audit endpoint.

### Idempotency

Existing confirmation and posting receipt uniqueness remains:

```text
(ledger_book_id, actor_id, operation, idempotency_key)
```

A matching retry returns the original result. Reuse for a different request fingerprint fails. The
receipt, financial mutation, audit event, and scope sidecars commit atomically.

Proposal creation and reversal-proposal creation are not currently idempotent commands. Do not
pretend content equality solves this. Until a separately approved command-creation idempotency
design exists, clients must not automatically retry an indeterminate create response. Duplicate
proposals have no financial effect until separately validated, confirmed, and posted, but the UX and
operational risk must remain documented.

## Exact M5.2-A feature gates

Feature gates are server-owned, default-deny capabilities. They cannot be enabled by a request,
frontend state, AI output, database content alone, or the presence of a category label. Each gate
requires the named policy approval plus its implementation and tests.

| Capability                                                       | Foundation state                                        | Enablement requirement                                                                |
| ---------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Create/view personal space                                       | Planned after v5                                        | Ownership, lifecycle, privacy, audit, and migration tests pass                        |
| Create/view FinancialAccount                                     | Planned after v5                                        | Atomic provisioning and account-kind/type constraints pass                            |
| Create/view categories                                           | Planned after v5                                        | Presentation-only; no mapping or posting implied                                      |
| Create category mappings                                         | Disabled by default                                     | Approved default chart/mapping and correction policy                                  |
| Record income                                                    | Disabled                                                | Approved revenue mapping, category provenance, and personal period policy             |
| Record expense from Cash/Checking/Savings                        | Disabled                                                | Approved expense mapping, payment-account mapping, and personal period policy         |
| Record Credit Card purchase                                      | Disabled                                                | Approved expense/category and liability mappings plus personal period policy          |
| Pay Credit Card                                                  | Disabled                                                | Approved account mapping and personal period policy; no new expense at payment        |
| Transfer between owned asset accounts                            | Disabled                                                | Same-space ownership checks plus approved personal period policy                      |
| Principal-only Personal Loan payment                             | Disabled                                                | Principal explicitly supplied, approved mappings, and personal period policy          |
| Initial loan recognition or mixed principal/interest/fee payment | Disabled                                                | Accountant-approved liability recognition and component-allocation policy             |
| Opening balance                                                  | Disabled                                                | Approved offset account, date/period, grouping, evidence, and prior-history treatment |
| Reverse personal posting                                         | Disabled until posting exists                           | Open-period policy, exact original provenance, and ordinary reversal lifecycle        |
| Balances and Activity                                            | Available only after authorized personal postings exist | Derived from universal ledger; never cached as mutable actuals                        |
| Income, Spending, Category Spending                              | Disabled until mappings/postings approved               | Ledger-derived with captured mapping provenance                                       |
| Cash Position                                                    | Disabled                                                | Approved included account kinds and negative-balance presentation                     |
| Account archive/deactivate                                       | Disabled                                                | Approved correction, retention, and inactive-account behavior                         |
| Historical recategorization                                      | Disabled                                                | Approved correction versus display-only policy; no history rewrite                    |
| Personal/business transfer                                       | Deferred                                                | M5.2-A exclusion; separate later authorization/accounting policy                      |

Tax/compliance, investments/valuation, multi-currency, household sharing, budgets, reminders, AI
transaction execution, bank integrations, interest/amortization automation, net worth, and automatic
posting are outside this plan.

## Opening-balance and policy-gated operations

An opening balance is never a `FinancialAccount.balance` field. When all gates are approved, it will
be an ordinary typed proposal with asserted account/amount/direction/date/source/evidence metadata,
an approved explicit offset, deterministic validation, exact-version confirmation, atomic posting,
and reversal/replacement correction.

The foundation may persist no authoritative opening amount. It may later collect a draft assertion
for review only if that draft is clearly non-financial and cannot be compiled while any gate is
closed. This plan does not add such a draft table.

The adapter must return explicit gate failures rather than guessing:

- missing personal period policy or open period;
- absent/unsupported default chart;
- absent category mapping;
- unapproved opening-balance offset or evidence policy;
- ambiguous loan component split;
- unsupported cross-space movement; or
- unapproved cash-position inclusion.

## Backward compatibility requirements

The following BUSINESS behavior must remain untouched:

- `AccountingEngine` public constructor and methods;
- organization API paths, request/response models, HTTP codes, pagination, and OpenAPI;
- CLI commands and output contracts;
- organization roles and permission matrix;
- all existing IDs and deterministic BUSINESS book mappings;
- existing `organization-v1` validation fingerprints;
- existing confirmation, posting, and reversal idempotency results;
- organization/project/document extension semantics;
- BUSINESS audit rows, JSON presentation, sequence, and sidecar coverage;
- ledger, balance, trial-balance, statement, cash-movement, and project report results; and
- existing error behavior for invalid account, project, document, period, proposal, confirmation,
  receipt, reversal, and audit references.

Personal work must not rename current tables, routes, commands, package modules, or compatibility
identifiers merely for symmetry.

## Implementation milestone sequence

Each milestone requires separate authorization and stops at its acceptance gate. No later milestone
starts because earlier code happens to exist.

### M5.2-C0 — C4 dependency and baseline freeze

**WHAT:** Complete M5.1-C4, observe schema-v4 BUSINESS operation, and capture a new exact baseline.  
**WHERE:** Existing C4 runbook/checklist and deployment evidence; no personal modules.  
**WHY:** PERSONAL must build on the proven canonical store, not a rehearsal-only path.  
**UNTOUCHED:** All personal concepts.  
**VERIFY:** Schema v4 normal startup, complete BUSINESS suite/parity, canary/reversal, backup/restore,
audit sidecars, observation sign-off.

### M5.2-C1 — Ownership-neutral BUSINESS internals

**WHAT:** Generalize repository records, extension handling, and fingerprint dispatch while binding
only BUSINESS contexts.  
**WHERE:** `chatbook/financial/repository.py`, `chatbook/financial/service.py`,
`chatbook/storage/sqlite_book.py`, focused tests.  
**WHY:** Remove organization-only assumptions from the shared path before adding another owner.  
**UNTOUCHED:** Schema, public facade, routes, CLI, audit payloads, fingerprints, calculations.  
**VERIFY:** Row-for-row service/facade parity, golden `organization-v1` fingerprints, unchanged
OpenAPI/CLI/audit/report outputs, source-boundary scan, complete suite.

### M5.2-C2 — Schema-v5 ownership and persistence migration

**WHAT:** Add `PersonalSpace`, reconstruct typed `LedgerBook` ownership, add presentation/category/
mapping/provenance/audit-scope persistence, and install database guards. Do not provision a personal
space or expose a route.  
**WHERE:** New numbered migration, canonical database startup verification, storage records, migration
evidence tests.  
**WHY:** Establish durable database-enforced isolation before application behavior.  
**UNTOUCHED:** Every existing BUSINESS row and observable behavior.  
**VERIFY:** v4→v5 empty/populated/multi-organization migration; exact before/after hashes; owner XOR;
same-space FKs; append-only mappings; trigger inventory; failure rollback; backup/restore; all
BUSINESS parity checks.

### M5.2-C3 — Personal ownership resolver and private provisioning

**WHAT:** Add owner-only PERSONAL resolution, atomic PersonalSpace plus book provisioning, startup
coverage verification, and read-only discovery/profile behavior.  
**WHERE:** `chatbook/financial/context.py`, new personal application module, canonical storage,
authentication dependencies, focused tests.  
**WHY:** Establish backend authority before child records.  
**UNTOUCHED:** Financial capabilities and posting endpoints remain disabled.  
**VERIFY:** one-space-per-owner, atomic failure injection, raw-book rejection, wrong-kind and
cross-user substitution, no organization-role escalation, audit event/scopes, BUSINESS regression.

### M5.2-C4 — FinancialAccount and category foundation

**WHAT:** Add atomic account provisioning, PersonalCategory CRUD within the approved lifecycle, and
append-only mappings behind a disabled policy gate.  
**WHERE:** Personal facade, personal extension repository, universal-service composition seam,
typed API models/routes only when persistence tests pass.  
**WHY:** Build presentation concepts without creating financial actuals.  
**UNTOUCHED:** No proposal, posting, report, opening-balance, archive, budget, reminder, or AI feature.  
**VERIFY:** account kind/type and same-book constraints, no balance columns, category versioning,
mapping immutability, atomic provisioning failure, audit, authorization, pagination, cross-space
attacks, BUSINESS parity.

### M5.2-C5 — Typed personal proposal adapter behind gates

**WHAT:** Add typed command compilation and PERSONAL immutable provenance; add the PERSONAL
fingerprint version. Leave every financial operation gate closed unless its policy approvals are
recorded in a separately authorized milestone.  
**WHERE:** Personal facade/commands, universal service fingerprint dispatch, personal extensions,
tests.  
**WHY:** Prove the reusable path without inventing a chart, period, or opening-balance policy.  
**UNTOUCHED:** Arbitrary manual journals, cross-space transfers, automatic confirmation/posting.  
**VERIFY:** deterministic golden proposals/fingerprints, stale-version rejection, mapping snapshot,
wrong-space rejection, unapproved operations fail before any core mutation, BUSINESS fingerprints
unchanged.

### M5.2-C6 — Approved personal lifecycle and read API

**WHAT:** For only separately approved feature gates, expose proposal validation, confirmation,
posting, reversal, account/activity/report reads, and audit.  
**WHERE:** Personal FastAPI route family and personal facade; no accounting arithmetic in routes.  
**WHY:** Complete the ordinary guarded lifecycle through the existing core.  
**UNTOUCHED:** Every excluded or still-gated capability.  
**VERIFY:** authentication, owner authorization, exact-version confirmation, caller idempotency,
atomic post/reversal, locked-period rejection, report reconciliation, immutable audit, cross-space
attacks, private connection/source boundary.

### M5.2-C7 — Migration, security, recovery, and release verification

**WHAT:** Run representative-volume migration rehearsal, full isolation matrix, recovery drills,
performance/query-plan checks, and controlled enablement of approved gates.  
**WHERE:** Migration evidence tooling, integration/adversarial tests, runbook/report documentation.  
**WHY:** Personal financial data must not weaken existing ledger or privacy guarantees.  
**UNTOUCHED:** Closed gates stay absent or fail closed.  
**VERIFY:** complete backend/frontend compatibility suite, type/lint/format checks, documentation
links, schema/integrity/FK checks, BUSINESS parity, personal reconciliation, backup/restore, failure
injection, concurrency, audit/receipt coverage, no cross-space disclosure.

## Test strategy

### Migration and schema

- v4→v5 on empty, populated, multi-organization, high-volume, reversal-heavy, locked-period,
  confirmed-unposted, and receipt-rich fixtures;
- repeated startup and unsupported-version rejection;
- exact BUSINESS IDs, rows, fingerprints, audit bytes/sequences, receipts, balances, reports, and
  query ordering before/after;
- injected failure after each migration stage proves no partial schema or owner mapping;
- exact owner XOR, one book per owner, and missing/orphan/mismatched owner rejection;
- same-book/same-space foreign-key attacks across every new table;
- append-only category mapping and personal audit-sidecar constraints; and
- no mutable balance/category-total field in schema or models.

### Authorization and cross-space attacks

Build a matrix using two users, two personal spaces, two organizations, overlapping role holders,
and deliberately reused-looking resource IDs. For every personal endpoint and repository lookup,
substitute another user's:

- personal-space ID;
- book ID where an internal test can reach the resolver boundary;
- FinancialAccount and linked ledger-account IDs;
- category and mapping IDs;
- period, proposal, line, validation, confirmation, receipt, entry, reversal, and audit IDs; and
- pagination cursor, export/reference key, cache key, and request/idempotency key.

Also substitute organization, project, and document IDs into personal calls and personal IDs into
business calls. Prove equal non-disclosing failures, no count/timing-dependent detail in response
payloads, no mutation, no audit leakage, and no cache/list contamination.

### Financial lifecycle and invariants

- unbalanced, zero, negative, over-limit, excess-line, inactive-account, wrong-type, and wrong-book
  proposals fail deterministically;
- missing/open/locked/boundary-date period behavior uses the existing service;
- exact proposal version and fingerprint bind confirmation;
- idempotent retry returns one effect; conflicting key reuse fails;
- failed posting creates no partial entry, line, receipt, or success audit event;
- reversal preserves original history, copies provenance, balances exactly, and rejects a second
  direct reversal;
- concurrent post/retry, post/lock, reversal/reversal, mapping-change/proposal, and account-
  provisioning conflicts fail safely under SQLite's supported topology;
- balances and reports reconcile directly to posted journal lines; and
- a category rename/remap never changes an earlier posted result or fingerprint.

### Feature gates

- every gate defaults closed on fresh and migrated databases;
- a client cannot set or override a gate;
- categories without mappings remain usable as labels but cannot compile financial commands;
- no personal period means no personal validation/posting/reversal-posting;
- opening balance, initial loan recognition, mixed loan payment, cash position, archive,
  recategorization, cross-space movement, investments, tax, multi-currency, budgets, reminders, and
  AI execution remain unavailable; and
- enabling one approved gate grants no adjacent capability.

### BUSINESS compatibility

- run every existing accounting, hardening, API, CLI, C1/C2/C3/C4, auth, permission, project,
  document, audit, idempotency, and report test unchanged;
- compare v4/v5 BUSINESS database rows and deterministic manifests;
- compare OpenAPI and frontend-consumed responses;
- retain golden `organization-v1` validation and legacy-shaped audit fixtures; and
- prove PERSONAL code cannot be selected by an organization route or BUSINESS context.

## What must remain untouched

- Double-entry, line limits, exact money, balance, period, posting, reversal, and immutable-history
  rules.
- Existing BUSINESS public contracts and organization role semantics.
- Existing business data, validation hashes, audit payloads, receipts, project/document links, and
  report results.
- `UniversalFinancialService` as the exclusive financial write/calculation boundary.
- The prohibition on client, UI, AI, or adapter confirmation/posting authority.
- Planning domains such as budgets and reminders, which remain outside ledger actuals and outside
  this implementation.

## Risks, ambiguities, and missing prerequisites

| Item                                                                                  | Required response                                                              |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| M5.1-C4 is incomplete                                                                 | Do not implement M5.2 against rehearsal-only v4 storage                        |
| Repository records and fingerprints remain organization-shaped                        | Complete C1 ownership-neutral BUSINESS refactor with exact parity first        |
| v4 business extension rows are assumed for every proposal/line                        | Add typed owner extension exclusivity before PERSONAL proposals                |
| v4 actor/audit triggers are BUSINESS-specific                                         | Add owner-kind trigger dispatch while preserving BUSINESS bytes                |
| No atomic account/presentation composition seam exists                                | Design and test a private unit-of-work extension before account routes         |
| Personal period policy is unapproved                                                  | Keep all personal financial writes disabled                                    |
| Default chart/category mapping is unapproved                                          | Permit labels only; reject financial compilation                               |
| Opening-balance policy is unapproved                                                  | Store no authoritative opening amount and create no proposal                   |
| Cash Position and negative-balance presentation are unapproved                        | Do not expose the report                                                       |
| Account archive/inactive correction behavior is unresolved                            | Expose no archive/deactivate endpoint                                          |
| Personal retention, deletion, recovery, export, and ownership transfer are unresolved | Keep ACTIVE-only lifecycle and no delete/transfer                              |
| Proposal/reversal creation idempotency is absent                                      | No automatic retry; require separate design before claiming create idempotency |
| SQLite is a single-writer local database                                              | Retain `BEGIN IMMEDIATE`; do not claim distributed/production concurrency      |
| Category-name uniqueness and case/Unicode normalization are not approved              | Preserve exact labels and stable IDs; do not silently normalize or merge       |

These are fail-closed gates. An implementation agent must document a newly discovered ambiguity and
stop the affected feature rather than choose accounting or privacy policy.

## Implementation-agent checklist

Before each code milestone, the agent must state:

- the completed prerequisite and authorization for that milestone;
- exact modules/tables/contracts affected;
- exact BUSINESS compatibility evidence to preserve;
- which M5.2-A gates remain closed;
- migration backup/rollback boundary where applicable; and
- focused plus complete verification commands.

After each milestone, update the implementation report with actual changes and measured results.
Documentation describing a future capability must never be presented as implemented support.

## Explicitly deferred

Cross-space transfers, tax/compliance, investments/valuation, multi-currency, household/advisor
sharing, budgets, reminders, recurring transactions, goals, bank integrations, documents/OCR, AI
transaction understanding/execution, net worth, automatic interest/amortization, production database,
cloud deployment, and frontend UI are not part of M5.2-B or the foundation persistence sequence.
