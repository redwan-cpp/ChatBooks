# Chatbooks M3.5 product-model report

Date: 2026-09-26

## Outcome

M3.5 revises the product and architecture direction without adding features or changing schema. The
existing M3 API remains an organization-scoped business accounting backend. Personal finance,
general budgets, reminders, chat, and AI remain unimplemented.

## Architectural findings

- The current `organization_id` is both business ownership boundary and ledger isolation key.
- The accounting kernel is safe to retain unchanged; adding personal product concepts does not
  require changing posting, reversal, audit, or report arithmetic now.
- Projects are business-only planning aggregates and optional journal-line dimensions.
- `projects.budget` is planning metadata. There is no general Budget aggregate or mutable actual.
- There is no Reminder, recurrence, personal ownership, category, goal, conversation, or AI domain.
- Current API routes are suitable for a business-context UI but cannot truthfully serve personal,
  budget, reminder, or conversational capabilities.

## Recommended domain model

Use a tagged `FinancialSpaceRef(kind, id)` as the application context. BUSINESS references an
existing organization. PERSONAL will reference a future personal ownership domain. Do not add a
cross-cutting `space_id` to current ledger tables, reinterpret existing organizations, or store a
personal space as an ordinary business organization merely to reuse APIs.

Keep actual money movements behind a deterministic ledger boundary. Personal income, expenses,
balances, liabilities, and same-space transfers are strong candidates for the same engine through a
future typed adapter. Budgets, reminders, recurring templates, goals, and conversations remain
separate non-ledger records; actual amounts are always derived from posted activity.

No journal may span personal and business spaces. Cross-space movements need separately confirmed
effects in each space plus an optional non-financial correlation record after accounting treatment is
approved.

The decisions are recorded in:

- [`ADR 0009`](docs/decisions/0009-financial-space-context.md) — typed Financial Space context;
- [`ADR 0010`](docs/decisions/0010-plans-schedules-ledger-separation.md) — separation of plans,
  schedules, and ledger actuals; and
- [`ADR 0011`](docs/decisions/0011-chat-first-progressive-disclosure.md) — chat-first experience and
  progressive disclosure.

## Recommended information architecture

Use a visible Personal/Business context switcher and a compact navigation model:

- **Chat** — default entry and action surface;
- **Money** — accounts, balances, activity details, and later budgets;
- **Projects** — visible only in business context;
- **Reports** — accessible summaries with progressive accounting detail; and
- **Activity** — chronological financial state and evidence.

Defer a separate Home destination until budgets, reminders, and attention signals can make it useful.
Keep accounting and audit depth available inside Money, Reports, and Activity based on role.

## Required future API and domain work

1. Add an additive financial-space discovery/read model without breaking organization routes.
2. Define personal ownership, privacy, account setup, periods, opening balances, categories, and
   transfer semantics before adding personal persistence.
3. Add Budget/BudgetLine and deterministic actual derivation; decide how project budget metadata
   relates to the new aggregate.
4. Add financially scoped Reminder and recurrence semantics without treating completion as payment.
5. Add recurring transaction templates that produce proposals rather than direct postings.
6. Add context-aware activity and plain-language report read models for M4/M5 UI use.
7. Add conversation and AI tool records only in their scheduled milestones, with proposal-only write
   authority for AI.

## Migration concerns

- Existing organizations and all related records must remain business data.
- A future persistent registry should map one BUSINESS space to each organization additively while
  preserving organization IDs, routes, foreign keys, and audit history.
- Never infer a personal space from an organization name, chart, member count, or owner.
- Personal imports and opening balances need explicit provenance and approved accounting treatment.
- `projects.budget` cannot be silently converted into budget-line history.
- Chatbooks is the single canonical written name for the engineering project, repository, and
  customer-facing product. Lowercase `chatbook` remains a stable compatibility identifier for the
  package, CLI commands, internal modules, environment-variable prefix, and database/internal names.

## Human and accountant decisions required

- personal opening balances, period behavior, account/category mapping, transfers, liabilities, and
  later net-worth valuation;
- personal-to-business contributions, drawings, reimbursements, and loans;
- budget periods, rollovers, overspend meaning, category mapping, and enforcement policy;
- reminder recurrence, time zones, missed occurrences, notifications, and completion semantics;
- recurring proposal generation and whether any class of automation may post without per-item
  confirmation;
- shared household access and business/personal delegation;
- jurisdiction, tax, cash/accrual, revenue recognition, fiscal close, and formal reporting rules; and
- role changes, dual approval, confirmation expiry, and period reopening.

## Intentionally deferred

Frontend and chat UI, personal storage, budgets, reminders, categories, goals, recurrence, document
processing, LLM integration, AI agents, bank integrations, billing, compliance automation, and cloud
infrastructure remain unimplemented.

## Verification

- Full accounting, hardening, migration, CLI, and API suite: **56 tests passed**.
- Strict mypy: **passed for 11 source files**.
- Ruff lint: **passed**.
- Ruff formatting check: **passed for 46 files**.
- Documentation links: **29 Markdown files and 55 local links checked; all targets exist**.
- Executable code and database schema: **unchanged in M3.5**.

## M4 readiness

The repository is ready for M4 Financial UX Foundation work against the implemented business API and
for a context-aware, chat-first frontend shell. M4 must label current capability accurately and must
not simulate personal finance, budgets, reminders, or AI. Real personal flows require the M5 domain
and API decisions above; general budgets and reminders require M7 work.
