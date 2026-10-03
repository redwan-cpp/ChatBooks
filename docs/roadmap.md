# Chatbooks roadmap

The roadmap separates implemented capability from planned product work. A milestone description is
not a claim that its capability exists. **Chatbooks** is the single project and product name.
Lowercase `chatbook` remains a stable technical identifier for compatibility.

## Completed foundations

### M0 — Product Constitution

**Status: complete.** Established the ledger as the source of financial truth, the deterministic
accounting write boundary, explicit confirmation, reversals instead of deletion, auditability, and
the prohibition on direct AI ledger mutation.

### M1 — Accounting Kernel

**Status: complete.** Added exact integer money, organizations, projects, accounts, periods,
proposals, balanced journal posting, ledger-derived balances and reports, full reversals, immutable
history, and append-only audit through the local engine and CLI.

### M2 — Kernel Hardening

**Status: complete.** Strengthened database constraints, atomicity, concurrency handling,
idempotency, period enforcement, immutability, reversal safety, reference integrity, reconciliation,
and adversarial tests. The current limits remain documented in the accounting model and hardening
report.

### M3 — API, Authentication, and RBAC

**Status: complete.** Added the FastAPI boundary, authenticated sessions, organization membership
and roles, tenant isolation, version-bound confirmation provenance, caller-key idempotency, safe
reversal, report and audit endpoints, and schema migration support.

The implemented acceptance flow is **register/login → access organization → create proposal →
validate → confirm the displayed version → post idempotently → view ledger/reports → propose and
post reversal → preserve original and audit history**. See
[`API_LAYER_IMPLEMENTATION_REPORT.md`](../API_LAYER_IMPLEMENTATION_REPORT.md).

### M3.5 — Product Model Revision

**Status: complete as documentation and architecture.** Defined the personal/business product
direction, Financial Space context, chat-first experience, progressive disclosure, budget and
reminder boundaries, information architecture, and future personal-finance assessment. No personal,
budget, reminder, frontend, conversation, or AI feature was implemented. See
[`product-model.md`](product-model.md) and
[`M3_5_PRODUCT_MODEL_REPORT.md`](../M3_5_PRODUCT_MODEL_REPORT.md).

### M4 — Financial UX Foundation

**Status: complete.** Added the Next.js/TypeScript/Tailwind frontend, HTTP-only browser session
boundary, visible Personal/Business context, chat-first shell, real Money, Projects, Reports, and
Activity views, progressive accounting detail, guarded proposal and reversal workflows, responsive
navigation, accessibility states, and focused frontend tests. Personal remains an explicit deferred
state with no fabricated data. See [`M4_IMPLEMENTATION_REPORT.md`](M4_IMPLEMENTATION_REPORT.md).

### M5.0 — Personal Finance Domain Specification

**Status: complete as documentation and architecture.** Defined separate private personal ownership,
PERSONAL Financial Space resolution, personal account/category semantics, deterministic ledger reuse
through a future typed adapter and internal ledger-book scope, same-space and cross-space transfers,
opening-balance provenance, liability MVP limits, personal reports, privacy enforcement, proposed API
and database impact, and explicit human/accountant decision gates. No personal table, endpoint, UI,
ledger migration, budget, reminder, recurrence, goal, or AI feature was implemented. See
[`personal-finance-model.md`](personal-finance-model.md),
[`M5_PERSONAL_FINANCE_DECISIONS.md`](M5_PERSONAL_FINANCE_DECISIONS.md), and
[`M5_0_PERSONAL_FINANCE_SPEC_REPORT.md`](M5_0_PERSONAL_FINANCE_SPEC_REPORT.md).

### M5.1-A — Universal Financial Core Architecture

**Status: complete as documentation and architecture.** Compared separate, one-step generic, and
phased-convergence designs; selected a persistent internal LedgerBook, authenticated Financial Space
resolver, business compatibility facade, personal adapter, one deterministic service, staged
business-preserving migration, Financial Activity command/read model, universal money-flow
boundaries, and external jurisdiction/compliance layers. No schema, migration, service, personal
feature, tax rule, or executable behavior was implemented. See
[`universal-financial-core.md`](universal-financial-core.md) and
[`M5_1A_UNIVERSAL_CORE_ARCHITECTURE_REPORT.md`](M5_1A_UNIVERSAL_CORE_ARCHITECTURE_REPORT.md).

### M5.1-B — Universal Financial Core Implementation Plan

**Status: complete as documentation and implementation design.** Defined the incremental
business-first sequence, universal service and repository boundaries, BUSINESS LedgerBook mapping,
canonical book-scoped target model, legacy fingerprint and audit compatibility, preflight and
reconciliation evidence, maintenance-window cutover, rollback boundary, personal prerequisites,
security controls, tests, operational gates, and exact policy approvals. No executable code, schema,
migration, PersonalSpace, API, UI, or runtime behavior was changed. See
[`M5_1B_IMPLEMENTATION_PLAN.md`](M5_1B_IMPLEMENTATION_PLAN.md) and
[`M5_1B_MIGRATION_PLAN.md`](M5_1B_MIGRATION_PLAN.md).

### M5.1-C1 — Preflight Evidence and Additive Business LedgerBook Mapping

**Status: complete.** Added deterministic read-only integrity/report manifests, sanitized
representative and corrupted migration fixtures, SQLite-consistent backup plus restore proof, and
atomic schema-v2-to-v3 migration. Schema v3 maps every organization to exactly one immutable
BUSINESS LedgerBook with a deterministic ID and matching currency/precision. New organizations
create the mapping atomically. Financial tables, API/CLI contracts, reports, audit rows, receipts,
and current ownership remain organization-scoped. No universal service, canonical book-scoped
financial table, PersonalSpace, or personal behavior was added. See
[`M5_1_C1_IMPLEMENTATION_REPORT.md`](M5_1_C1_IMPLEMENTATION_REPORT.md).

### M5.1-C2 — Universal Service Extraction over Organization Storage

**Status: complete.** Added immutable authorized financial context and capabilities, typed financial
commands, an explicit repository/unit-of-work boundary, and a schema-v3 organization storage
adapter. `AccountingEngine` is now the compatible BUSINESS facade over the single deterministic
service implementation. API, CLI, frontend, audit, receipts, errors, IDs, fingerprints, reports, and
schema-v3 ownership remain compatible. No canonical book-scoped financial table, PersonalSpace, or
personal behavior was added. See
[`M5_1_C2_IMPLEMENTATION_REPORT.md`](M5_1_C2_IMPLEMENTATION_REPORT.md).

### M5.1-C3 — Canonical Book-Scoped Persistence Rehearsal

**Status: complete.** Implemented schema-v4 table reconstruction, a book-scoped repository, exact
legacy projections and fingerprint verification, constrained business extensions, immutable audit
book sidecars, transactional table swap, eleven failure-injection gates, security/concurrency
attacks, business API/CLI parity, and representative-volume measurements on disposable copies.
Normal startup remains schema v3 and no shared database was migrated. See
[`M5_1_C3_IMPLEMENTATION_REPORT.md`](M5_1_C3_IMPLEMENTATION_REPORT.md).

### M5.1-C4A — Business Cutover Readiness and Deployment Rehearsal

**Status: complete on synthetic disposable copies; no live cutover.** Added a new-directory-only
synthetic rehearsal harness, writer-exclusion proof, retained verified restore, migration timing and
capacity evidence, exact engine/API/CLI parity, disposable success/failure canaries, eight recovery
drills, the controlled-cutover runbook, and the three-party release checklist. Normal startup remains
schema v3. Deployment-copy evidence, protected artifacts, actual process controls, monitoring, and
signatures remain blockers for C4. See
[`M5_1_C4A_READINESS_REPORT.md`](M5_1_C4A_READINESS_REPORT.md).

### M5.1-C4 — Controlled BUSINESS cutover

**Status: not started; requires separate authorization.** M5.1-C4A has completed the synthetic
operational rehearsal, recovery drills, measured resource method, cutover runbook, release checklist,
and readiness report. C4 remains blocked on an approved intended-deployment copy, actual process and
writer controls, deployment-host measurements, protected artifacts, monitoring ownership, canary
inputs, and all release signatures. Once separately authorized, stop writers, run the approved
v3→v4 orchestrator, complete post-commit read-only reconciliation, execute the approved canary, and
resume writers only after sign-off. Do not enable PERSONAL ownership in this phase. See
[`M5_1_C4A_READINESS_REPORT.md`](M5_1_C4A_READINESS_REPORT.md).

### M5.2-A — Simplified Personal Finance MVP Policy

**Status: complete as policy and implementation constraints; no personal feature implemented.**
Defines the smallest understandable personal-finance scope, presentation accounts, starter category
taxonomy, deterministic income/expense/transfer/card/loan/correction boundaries, the gated
opening-balance and period behavior, personal reports, budget/reminder/AI compatibility, tax and
compliance exclusion, and explicit ENGINEERING/PRODUCT/ACCOUNTING POLICY classification. It does
not add PersonalSpace, change schema, enable personal posting, or satisfy the outstanding C4
cutover gates. See
[`M5_2_PERSONAL_FINANCE_MVP_POLICY.md`](M5_2_PERSONAL_FINANCE_MVP_POLICY.md) and
[`M5_2_PERSONAL_FINANCE_POLICY_REPORT.md`](M5_2_PERSONAL_FINANCE_POLICY_REPORT.md).

## Planned milestones

### M5.2 — Personal Finance MVP implementation

**Status: not started; requires separate planning and authorization.** Implement only the generic
personal ownership, presentation-account, category-mapping, proposal lifecycle, same-space transfer,
explicit principal-only liability, and ledger-derived read-model capabilities permitted by the
M5.2-A policy. Personal posting remains blocked until the canonical BUSINESS cutover is complete and
the applicable personal period, chart/mapping, opening-balance, liability, report, and cross-space
accounting policies are approved. Do not include investments, valuation, household/advisor sharing,
multi-currency/FX, automatic financial posting, tax, or compliance in this MVP.

### M6 — Business and Project UX

Build organization and project experiences over the current API, including ledger-derived project
actuals, accessible business activity, permissions, and advanced accounting detail for authorized
users.

### M7 — Budgets and Financial Reminders

Add separate Budget/BudgetLine and financially scoped Reminder domains. Derive actuals from the
ledger, keep reminder completion separate from payment, and approve recurrence, time-zone, rollover,
mapping, and enforcement behavior before implementation.

### M8 — Documents

Add secure document upload, storage, provenance, retention, and evidence workflows. Extraction
remains untrusted input and cannot post financial records.

### M9 — AI Transaction Understanding

Introduce scoped structured tools for intent interpretation, clarification, and proposal creation.
AI remains unable to authenticate as the user, confirm, post, reverse, unlock periods, or write the
ledger.

### M10 — Conversational Financial Assistant

Add natural-language retrieval and guided financial workflows across authorized spaces, using
verified sources and structured actions within the M3/M5 boundaries.

### M11 — AI Reports and Financial Analysis

Add explanations and analysis over engine-generated reports with disclosed scope, dates, currency,
precision, and provenance. Model-generated arithmetic cannot replace ledger calculations.

### M12 — Accountant Workspace

Add advanced chart, journal, ledger, statement, audit, correction, review, and period workflows for
authorized accountants without forcing this terminology into the default experience.

### M13 — Integrations

Add explicitly approved bank, payment, import/export, and external system connections with
provenance, deduplication, review, and reconciliation controls.

### M14 — Automation

Add approved scheduling and automation only after authority, per-operation confirmation,
idempotency, failure recovery, and audit policies are defined. Recurrence does not imply permission
to post.

### M15 — Compliance and Production

Define intended jurisdictions and reporting policies in an external versioned compliance layer,
then add production database deployment,
security hardening, MFA/recovery, protected secrets and backups, monitoring, retention, operational
audit, disaster recovery, and compliance evidence.

## Cross-milestone decision gates

The following require product-owner and, where accounting treatment is involved, qualified
accountant approval before implementation:

- personal opening balances, periods, account/category mapping, transfers, liabilities, and
  net-worth valuation;
- personal-to-business contributions, drawings, reimbursements, and loans;
- budget periods, rollovers, actual mappings, overspend meaning, and enforcement;
- reminder recurrence, time zones, missed occurrences, notifications, and completion semantics;
- recurring proposal creation and any future automated posting authority;
- household sharing, business delegation, ownership transfer, dual approval, and period reopening;
- jurisdiction, tax, cash/accrual, revenue recognition, fiscal close, and statutory reports; and
- document retention, extraction evidence, integrations, and reconciliation policy.
