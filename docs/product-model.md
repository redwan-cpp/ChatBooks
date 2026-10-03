# Chatbooks Product Model

Status: M3.5 product definition, M4 implementation notes, and M5.0 personal-domain architecture.
This document keeps implemented capability and planned product direction separate. M4 provides a
chat-first shell. M5.0 specifies personal ownership, isolation, ledger integration, accounts,
categories, transfers, opening balances, and reporting, but implements none of those capabilities.
Conversation persistence, natural-language understanding, personal finance, budgets, reminders,
and AI remain unavailable.

**Chatbooks** is the single canonical written name for the engineering project, repository,
codebase, and customer-facing product. Use lowercase `chatbook` only for stable technical
identifiers such as the Python package, CLI commands, internal modules, environment-variable prefix,
and database/internal functions. Those identifiers do not define a separate product name.

## Product purpose

Chatbooks is a conversational financial operating system for individuals and project-based
businesses. Its starting question is: **What do you want to do with your money?**

The product should make everyday financial work understandable without requiring accounting
knowledge. Accounting remains rigorous underneath the experience and appears progressively when a
user asks for detail, has an advanced role, or needs to review evidence.

Chatbooks is not a generic ERP, a chart dashboard with a chat box, or a general task manager. The
conversation is the front door. Money context, important actions, and evidence support that
conversation.

## Capability status

| Capability                                                    | Current status                                                                                                                                           |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Business organizations and roles                              | Implemented in M3                                                                                                                                        |
| Business projects and project-tagged ledger lines             | Implemented in M1–M3                                                                                                                                     |
| Manual transaction proposals, confirmation, posting, reversal | Implemented in M1–M3                                                                                                                                     |
| Ledger-derived business reports and audit history             | Implemented in M1–M3                                                                                                                                     |
| Personal financial spaces                                     | Specified in M5.0; no schema, domain service, API, or UI exists                                                                                          |
| Universal personal/business financial core                    | BUSINESS LedgerBook mapping and universal service seam implemented in M5.1-C1/C2; canonical book-scoped storage and PERSONAL adapter are not implemented |
| General personal or business budgets                          | Planned; project budget is metadata only                                                                                                                 |
| Financial reminders and recurring schedules                   | Planned; no domain or API exists                                                                                                                         |
| Chat-first web shell and business financial UX                | Implemented in M4                                                                                                                                        |
| Conversation storage or conversational intelligence           | Planned; no domain exists                                                                                                                                |
| AI interpretation, tools, or document extraction              | Planned for later milestones; not implemented                                                                                                            |

## Personal finance

A personal context is a private `PersonalSpace` boundary owned by one authenticated user in the
initial model. One personal space per user is the initial engineering constraint. Whether that limit
is permanent is a product decision. Shared households, delegated access, dependants, guardians, and
joint ownership are separate future decisions. A personal context must never be represented as an
organization or inherit business membership or project behavior.

Candidate personal capabilities are money accounts, income and expense activity, categories,
budgets, reminders, recurring-payment templates, savings goals, financial insights, and later net
worth. These concepts need a plain-language presentation even when verified actual money movements
use the double-entry engine underneath.

The personal model should distinguish records by their financial effect:

| Personal record                                     | Recommended future treatment                                                                                    |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Income, expense, account balance, liability payment | Posted through a deterministic ledger proposal                                                                  |
| Transfer between accounts in one personal space     | One balanced proposal; no income or expense effect                                                              |
| Budget                                              | Plan outside the ledger; actual use derived from posted activity                                                |
| Reminder                                            | Schedule outside the ledger; completion never implies payment                                                   |
| Recurring transaction                               | Template or schedule that creates a reviewable proposal; no automatic posting by default                        |
| Savings goal                                        | Target and progress definition; actual progress derived from selected ledger accounts or explicit contributions |
| Category                                            | User-facing classification mapped deterministically to ledger accounts or line dimensions                       |
| Insight                                             | Derived explanation from verified records; never an independent financial total                                 |
| Net worth                                           | Later ledger-derived assets minus liabilities, with valuation policy documented separately                      |

M5.0 approves reuse of the deterministic accounting rules and guarded lifecycle, but the current
`AccountingEngine` cannot safely serve personal data unchanged because ownership, authorization,
periods, foreign keys, idempotency, and audit are organization-scoped. Future implementation uses a
personal application adapter that resolves `PersonalSpace` to an internal ledger book and calls an
ownership-neutral ledger service. The existing business engine remains its compatibility facade.
Fake organizations and a parallel, weaker personal accounting engine are prohibited.

Personal accounts are user-facing records mapped to owned ledger accounts; balances are always
derived from posted lines. Personal categories are separate owner-scoped labels with versioned,
auditable mappings to income or expense accounts. Same-space transfers are one balanced entry with
no income or expense effect. Personal/business movements require two independently authorized
effects linked by a non-financial correlation record. Opening balances use ordinary proposals and
reversal/replacement correction. The exact period, opening-balance offset, default mapping,
liability, and cross-space accounting policies require human or accountant decisions before M5.1
posting is enabled.

The complete domain specification and decision gates are in
[`personal-finance-model.md`](personal-finance-model.md).

## Business finance

The existing organization is the implemented business ownership and ledger boundary. It owns the
chart, accounts, accounting periods, projects, documents, transaction proposals, journal, reports,
and audit history. Membership roles govern access. This model remains unchanged through M5.0.

Business-only concepts include organization membership and role administration, clients, projects,
business accounting-period administration, business financial statements, and the accountant audit
workspace. A future business experience may hide these concepts from ordinary members while keeping
them available to accountants and authorized operators.

## Projects

Projects remain children of business organizations. Existing project planning metadata includes
name, context, client, expected revenue, budget, dates, and status. Posted journal lines may carry a
project dimension, so project actuals are derived from the ledger.

Projects do not belong in a personal space in the initial model. A personal goal or event should use
a personal concept rather than weakening project semantics. Project expected revenue and budget are
plans and must never be reported as collected revenue or actual spend.

## Budgets

Budgets are planned financial limits or targets for a defined period and scope. They have no direct
ledger effect. Actual activity must be derived from posted ledger lines through an explicit mapping
to accounts, categories, projects, or another approved dimension.

A future budget aggregate will need at least a financial-space reference, name, period, currency,
status, one or more budget lines, and an explicit actual-activity mapping. Personal budgets may cover
food, transport, shopping, entertainment, or savings. Business budgets may cover a project,
department, or operating scope. Department modeling is not currently approved and must not be
created merely to support a label.

The current `projects.budget` field remains project planning metadata. It is not a general budget,
does not maintain actual spend, and does not enforce a posting limit. A later migration may link or
supersede this field only after compatibility semantics are decided.

## Reminders

Financial reminders are planned records for time-sensitive money work. They are not general tasks and
have no ledger effect. A reminder may refer to a due date, recurrence rule, financial space, account,
project, future invoice, proposal, document, or posted transaction where that reference is valid.

Completing a reminder must not mark a bill as paid or create a transaction. It may lead to a
reviewable proposal, which still follows validation, authenticated confirmation, deterministic
posting, and audit. Recurrence time zones, missed occurrences, edit history, notification delivery,
invoice semantics, and automatic proposal generation remain future decisions.

## Financial spaces

### Recommendation

Use **Financial Space** as the product and application context, but do not add it as a cross-cutting
persistent parent. M5.0 retains it as a tagged resolver over separate ownership domains.

For navigation and future API design, use a typed reference:

```text
FinancialSpaceRef
├── kind: PERSONAL | BUSINESS
└── id: identifier in that kind's ownership domain

BUSINESS → existing Organization → Project
PERSONAL → future PersonalSpace domain
```

This is a tagged reference, not an untyped identifier. Every request, cached view, conversation,
budget, reminder, and future AI tool call must carry exactly one space kind and ID. A resource from
one kind cannot be resolved in another. Combined personal-and-business totals are not a default view.

For business spaces, the existing organization ID remains the authorization, persistence, ledger,
and audit boundary. Existing ledger tables keep `organization_id`; adding `space_id` to every table
would create migration risk without solving a current problem. A future `/financial-spaces` endpoint
can provide a union read model over organizations and the future personal domain while preserving
the existing organization routes.

Personal data must not be implemented as an ordinary organization merely to reuse current APIs. That
would expose business roles, projects, periods, and reporting semantics in the wrong context and make
isolation depend on presentation code. ADR 0015 selects a typed personal adapter and internal
ledger-book boundary over an ownership-neutral deterministic ledger service. The physical SQLite
migration remains subject to implementation evidence and compatibility tests.

### Ownership and isolation

| Context  | Owner and access                     | Financial boundary                            |
| -------- | ------------------------------------ | --------------------------------------------- |
| Personal | One user initially; sharing deferred | Separate personal records and ledger scope    |
| Business | Organization membership and M3 roles | Existing organization-scoped ledger           |
| Project  | Inherits organization access         | Optional dimension within one business ledger |

No journal entry may span two financial spaces. A personal-to-business movement, owner contribution,
draw, reimbursement, or loan crosses two reporting boundaries and cannot be modeled as a single
cross-space journal. A future workflow should create separately reviewable effects in each space and
link them with a non-financial correlation record. The exact accounting treatment requires human and
accountant approval.

### Migration implications

- Existing organizations and all their records remain business data without reinterpretation.
- If a persistent space registry is later added, each organization can receive one additive BUSINESS
  mapping while preserving its ID, routes, foreign keys, audit history, and ledger.
- Existing business records must never be inferred as personal from their name, owner count, or chart.
- Personal spaces begin empty unless an explicit import or opening-balance workflow is approved.
- No current ledger row is changed by M5.0; the future M5.1 ledger-book migration must preserve all
  existing business identifiers, constraints, history, and results.
- The canonical Chatbooks package, commands, modules, environment-variable prefix, and
  database/internal identifiers remain unchanged; no naming migration is required.

## Chat-first interaction

The primary canvas is conversational. Users describe what happened, ask a question, request an
action, or review what needs attention. The experience should answer in plain language and reveal the
current financial context, relevant source records, and next safe action.

M4 builds a deterministic conversational shell over existing API actions without claiming natural
language understanding. AI arrives later. Guided prompts and structured forms connect the shell to
current workflows, and accounting writes still require the existing proposal and confirmation
sequence.

Every money-changing flow should make these facts visible before confirmation:

- Personal or business context and, for business, organization/project;
- amount and currency;
- date and description;
- money account and category or accounting mapping;
- validation result and any unresolved question; and
- the consequence of confirming, including whether a ledger posting will occur.

## Progressive disclosure

The same verified event can be presented at increasing depth:

| Level      | Example                                                                     |
| ---------- | --------------------------------------------------------------------------- |
| Everyday   | Money activity → ৳1,500 groceries                                           |
| Detailed   | Category → Food; payment account → Card                                     |
| Accounting | Debit → Food Expense; credit → Card Payable                                 |
| Audit      | Proposal → validation → confirmation → posting → actor → timestamp → source |

Everyday language is the default. Accounting terms remain available through detail panels,
permission-aware views, reports, and an eventual accountant workspace. Progressive disclosure must
never hide the amount, context, pending-versus-posted status, or confirmation consequence.

# UX Principles

1. **Conversation is the front door.** The first prompt asks what the user wants to do with their
   money. Tables and charts support an answer; they do not define the starting experience.
2. **Context is always visible.** Personal or business context appears in the conversation header,
   action cards, confirmation, reports, and activity. Context switches are explicit.
3. **Plain language first.** Use Money, Activity, Budget, Reminder, Project, and Report in ordinary
   navigation. Reveal journal, ledger, debit, credit, and chart terms when requested or appropriate.
4. **Actions are structured and reviewable.** A conversational request becomes a typed action or
   proposal with a stable state. The interface distinguishes suggestions, validated proposals,
   confirmations, posted entries, and reminders.
5. **Details unfold progressively.** Start with the decision-relevant amount and meaning, then offer
   account, category, accounting, and audit detail without sending users to unrelated modules.
6. **Actuals come from verified records.** Budgets, goals, and expected revenue are labeled as plans.
   Actual spend, income, balances, and reports come from posted ledger data.
7. **Attention beats dashboards.** Show what changed, what needs review, and what is due. Avoid a
   default wall of charts, metrics, and empty widgets.
8. **Confirmation is meaningful.** The user sees the exact proposal version and context before a
   money-changing action. Conversational ease cannot weaken authentication, validation, or audit.
9. **Advanced users keep full fidelity.** Accountants can reach ledger, statements, audit provenance,
   and correction workflows without forcing that vocabulary on everyone.
10. **Accessibility and calm are product behavior.** Amounts, statuses, errors, keyboard flows, focus,
    and contrast must be clear. Financial urgency should be communicated without alarmist styling.

## Familiar without copying ChatGPT

Chatbooks may use broadly familiar conversational patterns: a chronological message stream, a
clear composer, keyboard submission, suggested prompts, visible processing states, concise assistant
responses, and resumable conversation history. These are interaction conventions rather than another
product's identity.

Chatbooks establishes its own identity through persistent financial context, money-specific action
cards, proposal states, evidence trails, accessible amount formatting, and a focused financial
navigation model. It must not copy ChatGPT's logo, brand colors, typography, exact sidebar, composer,
spacing, icon treatment, message layout, microcopy, or assistant persona. Visual design should be
developed from Chatbooks' own brand and usability requirements.

## Recommended information architecture

For M4, use a compact context-aware structure:

| Surface  | Purpose                                                                               |
| -------- | ------------------------------------------------------------------------------------- |
| Chat     | Default entry and primary action surface                                              |
| Money    | Accounts, categories, balances, budgets later, and detailed activity                  |
| Projects | Business spaces only; project context and ledger-derived actuals                      |
| Reports  | Plain-language summaries with advanced accounting disclosure                          |
| Activity | Chronological proposals, postings, reversals, reminders later, and audit-aware status |

The Personal/Business space switcher sits above these surfaces and is never buried in settings.
Projects disappears in personal context rather than showing irrelevant empty UI. Accountant views
live under Money, Reports, or Activity based on the task and permission, not as a parallel ERP menu.

A separate Home destination is deferred for M4 because it would initially duplicate Chat. Once
budgets, reminders, and attention signals exist, Home can become a concise “Today” view while Chat
remains the main action surface. Budgets and reminders should not become top-level modules unless
usage proves that they need independent navigation.

# Domain Expansion Assessment

## What M3 already supports

- authenticated users and opaque sessions;
- business organizations, memberships, and explicit roles;
- organization isolation across accounts, projects, proposals, journal, reports, documents, and audit;
- project planning metadata and optional project dimensions on ledger lines;
- deterministic proposals, validation, exact-version confirmation, idempotent posting, reversal,
  immutable history, and correlated audit;
- ledger, account, trial-balance, statement, project-filtered, and selected-asset cash views; and
- a typed FastAPI boundary suitable for a business-context client.

## New domain concepts required later

- persistent PersonalSpace ownership and an authenticated typed space discovery/read model;
- an internal LedgerBook ownership seam and personal accounting adapter;
- personal financial account profiles and owned ledger mappings;
- user-facing category or classification mapping;
- Budget and BudgetLine with period/scope and actual-derivation rules;
- Reminder with financial purpose, due/recurrence state, and typed related-entity references;
- RecurringTransactionTemplate that can create reviewable proposals without silently posting;
- savings Goal with an approved progress calculation;
- conversation, message, source, and tool-invocation records when AI work begins; and
- optional cross-space correlation for separately posted personal/business effects.

## What remains unchanged

- the posted ledger is the source of actual financial truth;
- the accounting engine is the exclusive accounting write boundary;
- exact integer money, balance validation, atomic posting, period enforcement, reversal, and audit;
- existing organization data and role authorization;
- project actuals derived from tagged posted lines;
- proposal/validation/confirmation/posting separation; and
- AI exclusion from confirmation, posting, reversal, and direct database mutation.

## What is deferred

M5.0 makes no executable or ledger-schema change. Personal persistence, ownership-neutral ledger
plumbing, adapters, endpoints, UI, budgets, reminders, recurrence, goals, conversation storage,
document processing, AI, banking, automation, and production infrastructure remain future milestone
work. Implemented UI must not display planned capabilities as available.
