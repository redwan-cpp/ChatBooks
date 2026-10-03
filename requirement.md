# Chatbooks Requirements

## Purpose

Chatbooks is a conversational financial operating system for individuals and project-based
businesses. It must make financial management understandable to people with little or no accounting
knowledge while maintaining the correctness, determinism, and auditability of conventional
double-entry accounting software.

M0–M4 are implemented. M3.5 defines the revised product direction, M4 adds the authenticated
Chatbooks web application, M5.0 specifies the personal-finance domain, and M5.1-A specifies the
universal financial-core architecture. M5.1-C1 implements read-only migration evidence and the
additive schema-v3 BUSINESS LedgerBook mapping while leaving financial records and behavior
organization-scoped. M5.1-C2 implements the authorized universal service and BUSINESS compatibility
facade over that unchanged storage. Personal finance persistence and UI, canonical book-scoped
financial tables, general budgets, financial reminders, conversational AI, document extraction,
billing, integrations, tax/compliance, and cloud deployment are not implemented.

**Chatbooks** is the single canonical written name for the repository, codebase, engineering
project, and customer-facing product. Use lowercase `chatbook` only for stable technical identifiers
such as the Python package, CLI command, internal modules, environment-variable prefix, and
database/internal identifiers. Those identifiers do not define a separate name and do not require a
compatibility-breaking rename.

The mandatory repository rules are in [`rules.md`](rules.md). When a requirement appears to
conflict with that rulebook, preserve ledger integrity and document the conflict before proceeding.

## Source of truth

The posted accounting ledger is the sole source of financial truth.

- Proposals, validations, confirmations, project estimates, and document metadata do not affect
  balances.
- Only posted journal entries and journal lines appear in the ledger and financial reports.
- Posted history is immutable. Corrections use compensating entries.
- Financial calculations use deterministic engine logic and verified ledger data.
- No LLM may confirm, post, edit, or delete ledger data.

## Product contexts and experience

The product presents an explicit Personal or Business financial context. Data from the two contexts
must remain separated in authorization, persistence, retrieval, reporting, caching, conversation,
and future AI tool calls. Switching context is an explicit user action. No journal entry may span
personal and business financial boundaries.

The chat surface is the front door. In M4 it provides context, an honest no-AI empty state, and
links into typed, reviewable actions over current APIs; natural-language understanding remains
deferred. Familiarity may come from common
conversation patterns, but the interface must use Chatbooks' own visual system and must not copy
ChatGPT branding, exact layout, composer, navigation, typography, colors, icons, or microcopy.

User-facing navigation and language favor Chat, Money, Projects, Reports, and Activity. Accounting
concepts remain available progressively:

1. everyday activity and amount;
2. category, account, date, and context;
3. debit, credit, journal, and ledger; and
4. proposal, validation, confirmation, posting, actor, timestamp, and source.

The detailed model and information architecture are in
[`docs/product-model.md`](docs/product-model.md).

## Financial Space requirement

Financial Space is a typed product/application context, not a new persisted parent in M3.5. A
BUSINESS space maps to an existing organization. A PERSONAL space will map to a future personal
`PersonalSpace` ownership domain. The initial personal model is private, owned by one authenticated
user, and limited to one space per user. Existing ledger records keep their organization ownership
and are not migrated or reinterpreted.

Every future space-aware reference must carry both kind and ID. Personal data must not be stored as
an ordinary organization merely to reuse business APIs. A future additive space-discovery read model
may unify navigation while preserving typed ownership and current organization routes.

M5.0 requires personal actual money movements to use the deterministic proposal, validation,
exact-version confirmation, posting, reversal, report, and audit lifecycle. Personal account profiles
and categories map to owned ledger accounts and do not store actual balances. Same-space transfers
are balanced non-income/expense events. Personal/business movements produce separately authorized
ledger effects and a non-financial correlation; no journal spans spaces.

The current accounting rules are reusable, but the current engine/schema organization ownership is
not. Schema v3 now maps each organization to one internal BUSINESS LedgerBook without changing any
financial ownership column. Future implementation still requires an ownership-neutral service and a
typed personal adapter while the existing business engine and organization routes remain compatible.
Personal posting must remain disabled until period, opening-balance, default mapping, liability, and
cross-space accounting policies are approved. See
[`docs/personal-finance-model.md`](docs/personal-finance-model.md).

## Universal financial-core requirement

The future universal core must serve BUSINESS and PERSONAL books through one deterministic
proposal, validation, confirmation, posting, reversal, balance, report-primitive, audit, and
idempotency implementation. It must not duplicate the accounting engine or represent personal
ownership as an organization.

A persistent internal LedgerBook is the target canonical scope for financial records. M5.1-C1 adds
the BUSINESS mapping and membership-first internal resolver; financial rows are not book-scoped yet.
The backend resolves the mapping only after authenticating/trusting the actor and authorizing the
organization. Existing
organization routes, IDs, memberships, roles, projects, accounts, periods, proposals, journal
history, audit history, receipts, report results, and database guarantees must survive migration.

The migration must be staged and fail closed. It must preserve immutable record IDs and payloads,
use book-scoped foreign keys/triggers, reconcile every organization before cutover, and enable no
personal write until business parity and cross-scope isolation tests pass. The detailed architecture
and decision classifications are in
[`docs/universal-financial-core.md`](docs/universal-financial-core.md).

The universal core is jurisdiction-neutral. Tax, VAT/GST, payroll compliance, statutory reporting,
filing, and country-specific rules remain external versioned layers. Such a layer may produce a
reviewable proposal but may never write journal or audit records directly.

## Budgets and financial reminders

Budgets are first-class planned limits or targets for both contexts, but they are not ledger actuals.
Future budget actuals must be derived from posted ledger activity through an explicit approved
mapping. The existing project budget remains planning metadata and cannot become independently
mutable actual spend.

Financial reminders are future records for money-related work. Completing a reminder must not imply
that money moved. A reminder or recurring template may eventually create a reviewable proposal, but
it may never confirm or post it. Generic task-management scope is excluded.

## Implemented M3 domain

The foundation must explicitly model:

- Organization
- User identity, credentials/session boundary, and role-bearing organization membership
- Project
- Account and chart of accounts
- Accounting period
- Transaction proposal and proposal line
- Validation and explicit confirmation
- Journal entry and journal line
- Audit event
- Document metadata

Domain objects and persisted records must have stable identifiers and organization ownership where
applicable. Cross-organization financial references must fail.

Future milestones require separate, explicit concepts for personal ownership, typed Financial Space
references, categories, Budget/BudgetLine, financial Reminder, RecurringTransactionTemplate,
savings Goal, and conversation/tool provenance. Their mention here does not mean they exist in the
current API or schema.

## API identity and authorization requirements

- API actor IDs come only from authenticated sessions, never client-provided identity fields.
- Passwords use a salted memory-hard hash; bearer tokens are random, stored only as hashes, expire,
  and can be revoked.
- Roles are `OWNER`, `ADMIN`, `ACCOUNTANT`, `MEMBER`, and `VIEWER`, with explicit permissions for
  views, proposals, confirmation, manual journals, reversal, reports, audit, accounts, projects,
  periods, locks, and membership administration.
- Every organization resource is scoped through authenticated membership before access.
- Confirmation records proposal ID/version, authenticated actor, UTC time, and request identifier.
- Confirmation and posting require caller-supplied idempotency keys and atomically replay the original
  result for a matching retry while rejecting conflicting key reuse.
- API routes call the accounting engine for all accounting writes and financial calculations.

## Accounting requirements

All monetary amounts are exact nonnegative integer minor units in the organization's single
configured currency and precision. Binary floating-point values, implicit rounding, exchange-rate
inference, and LLM-generated arithmetic are prohibited.

Every posted journal entry must satisfy all of the following:

1. It contains at least two and at most 1,000 lines.
2. Every line has exactly one positive side: debit or credit.
3. `SUM(debit) == SUM(credit)` exactly.
4. Every referenced account is active and belongs to the organization.
5. Optional project and document references belong to the organization.
6. The accounting date belongs to exactly one open accounting period.
7. The entry exactly matches an immutable, deterministically validated proposal.
8. An explicit confirmation exists for that validation and actor.
9. One proposal produces at most one posted entry.
10. Posting and its audit records commit atomically or roll back together.

Invalid entries must be rejected before they affect the ledger. The database must independently
enforce structural, ownership, immutability, balance, period, proposal-match, and uniqueness
constraints wherever SQLite can express them.

## Manual transaction lifecycle

The required forward path is:

`create proposal → inspect → validate → explicitly confirm → post → ledger → balances → reports`

Validation proves accounting correctness but does not post. Confirmation proves explicit acceptance
but does not post. Posting re-runs all current-state checks inside the atomic database write.
Repeating a successful post with the same confirmation must return the existing entry without
duplicating ledger or audit records.

## Reversal lifecycle

Undo must never delete or modify the original entry. A reversal must:

- reference a posted entry;
- copy every original line with debit and credit exchanged;
- preserve line order, account, and project dimensions;
- include an explicit reason and date;
- pass the ordinary validation, confirmation, and posting flow;
- be posted into an open period on or after the original entry date; and
- remain linked to the original entry in the ledger and audit history.

Only full reversals are currently supported. Partial reversals and alternative reversal-date rules
require an explicit approved requirement before implementation.

## Period requirements

Accounting periods have inclusive, canonical calendar-date boundaries and cannot overlap within an
organization. Gaps are permitted, but entries dated in a gap cannot post. Locking a period is
one-way in the current milestone, is audited, and blocks all later postings dated in that period.
The system must not infer reopening, closing, or adjustment-period rules.

## Project requirements

A project records name, description/context, client, expected revenue, budget, dates, and status.
Journal lines may carry an optional project dimension. Project budgets and expected revenue are
planning metadata and never create financial entries. A project-filtered view may be unbalanced
because project assignment applies to individual lines; the organization-wide ledger must balance.
Projects remain business-only in the initial expanded model.

## Audit requirements

Every successful financial or financial-master-data mutation must produce an audit event in the same
atomic write. Each event must contain:

- actor identifier;
- UTC timestamp;
- event type;
- entity type and identifier;
- previous state when applicable;
- new state when applicable; and
- metadata including the operation and request identifier.

Audit events are append-only. Updates, deletes, or replacements must fail. Failed financial writes
must leave neither partial financial data nor a misleading success audit event.

## Reporting requirements

Reports must be derived from posted journal lines rather than mutable balance caches. The foundation
must provide:

- ledger detail;
- account balances;
- organization-wide trial balance;
- basic date-range income statement; and
- basic as-of balance sheet with unclosed earnings shown explicitly.

Reports must disclose organization currency and precision. These summaries do not claim compliance
with a jurisdiction-specific reporting framework.

## Engineering requirements

- Python 3.12 or later with strict static type checking for application code.
- SQLite strict tables, foreign keys, recursive triggers, and synchronous atomic writes.
- Explicit domain boundaries between values, application workflows, persistence, and presentation.
- Stable, user-actionable domain error codes.
- FastAPI/Pydantic and Uvicorn are the only M3 runtime framework dependencies; HTTPX is used for API
  integration tests. All versions are locked.
- Tests for happy paths, invalid entries, organization isolation, period locks, immutability,
  rollback, idempotency, concurrency, persistence, reports, reversals, and database integrity.
- Schema changes require explicit migration handling and an ADR when the architecture changes.

## Implemented milestone acceptance

The foundation is accepted only when a manually entered transaction can be created, inspected,
validated, explicitly confirmed, posted, observed in the ledger, reflected in balances and reports,
fully reversed through the same guarded workflow, and retained with complete audit history.

The automated suite must also prove that unbalanced entries, missing confirmation, locked periods,
cross-organization references, duplicate posts, and attempts to mutate posted history fail safely.

M3 additionally requires an authenticated client to access its organization, create and validate a
proposal, confirm the exact displayed version, post it safely with an idempotency key, observe ledger
and report effects, reverse it through the guarded workflow, and retain the original and audit history.

M3.5 is accepted when the revised personal/business model, Financial Space decision, UX principles,
information architecture, domain-expansion assessment, roadmap, migration concerns, and unresolved
policy decisions are documented without claiming future features or weakening M3. No code or schema
change is required unless a concrete blocker is found; this assessment found none.

M5.0 is accepted when personal ownership and isolation, typed Financial Space resolution, ledger
reuse, personal account/category mapping, transfer coordination, opening-balance workflow, liability
boundaries, personal reporting, future API/database impact, migration concerns, and security failure
cases are documented; engineering decisions and human/accountant decisions are separate; all current
business behavior remains unchanged; and all existing Python and frontend checks pass. M5.0 must not
create personal tables, endpoints, UI, budgets, reminders, recurrence, goals, or AI.

M5.1-A is accepted when architecture options are compared, a persisted ownership seam and adapter
boundary are selected, business compatibility and staged migration are defined, Financial Activity
is kept from becoming duplicate truth, planning and compliance boundaries are explicit, security and
AI context are documented, every decision is classified, no executable/schema behavior changes, and
all existing checks pass.

## Excluded and unresolved requirements

The following are not defined and must not be invented:

- jurisdiction, tax regime, and statutory reporting framework;
- cash-versus-accrual policy and revenue-recognition rules;
- fiscal closing, opening balances, and retained-earnings workflow;
- role changes/removal, ownership transfer, dual approval, confirmation expiry, and period-reopening authority;
- foreign exchange, multi-currency, and precision changes;
- partial reversals and project allocation rules;
- document retention, evidence, extraction, and deduplication policy;
- proposal amendment, cancellation, or supersession rules;
- password reset, account recovery, MFA, login throttling, and migrated-user credential provisioning;
- formal cash-account designation and cash-flow activity classification; and
- idempotency-key retention and proposal/reversal-creation idempotency;
- household sharing, advisor access, personal retention/export/recovery, and whether multiple
  personal spaces are needed beyond the one-owner/one-space MVP;
- personal opening-balance offset, period behavior, default account/category mapping, liability
  splits, historical recategorization, cash-position inclusion, and net-worth valuation;
- personal-to-business contributions, drawings, reimbursements, and loans;
- budget periods, scopes, mapping, rollover, amendment, enforcement, and project-budget migration;
  and
- reminder recurrence, time zones, notifications, missed occurrences, completion, and recurring
  proposal generation.

Record decisions for these topics before extending the implementation. The detailed ambiguity
register is maintained in [`docs/accounting-model.md`](docs/accounting-model.md).
