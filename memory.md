# Chatbooks Project Memory

Last updated: 2026-10-03

## Identity and non-negotiable rule

**Chatbooks** is the single canonical written name for the engineering project, repository,
codebase, and customer-facing product. Use lowercase `chatbook` only for stable technical
identifiers such as the Python package, CLI commands, internal modules, environment-variable prefix,
and database/internal functions. Those compatibility identifiers do not define a separate name.

Read [`rules.md`](rules.md) before every task. The posted ledger is the financial source of truth.
Never invent accounting policy, bypass validation, let an LLM mutate the ledger, delete or rewrite
posted history, mix LLM arithmetic with accounting calculations, or expand scope without instruction.

Update this file at the end of every task, including read-only and documentation-only tasks. Record
the date, a concise result, and the verification performed. The memory update is the final bookkeeping
step and does not recursively require another entry.

## Current state

M0–M4, including the local accounting foundation, hardening, FastAPI application/API layer, and
Financial UX Foundation, are implemented. M3.5 remains the product-model revision that defined the
direction implemented by M4. M5.0 is complete as a domain and architecture specification only; no
personal-finance behavior, schema, API, or UI is implemented. M5.1-A defines the universal
financial-core architecture, and M5.1-B defines its staged implementation and migration plan.
M5.1-C1 through C4A now implement and rehearse Phases 1–6: fail-closed migration evidence, the
additive BUSINESS LedgerBook mapping, the universal financial service over organization storage,
canonical schema-v4 persistence on disposable copies, and synthetic operational cutover readiness.
Normal application/API/CLI startup remains schema v3. No shared database was migrated, no ordinary
v4 writer was enabled, and C4 remains separately authorized.
The accounting-core hardening report is in
[`HARDENING_REPORT.md`](HARDENING_REPORT.md), and the M3 implementation record is in
[`API_LAYER_IMPLEMENTATION_REPORT.md`](API_LAYER_IMPLEMENTATION_REPORT.md). The expanded product
model and assessment are in [`docs/product-model.md`](docs/product-model.md) and
[`M3_5_PRODUCT_MODEL_REPORT.md`](M3_5_PRODUCT_MODEL_REPORT.md). The M4 implementation record is in
[`docs/M4_IMPLEMENTATION_REPORT.md`](docs/M4_IMPLEMENTATION_REPORT.md). The M5.0 model, decision
gates, and completion report are in
[`docs/personal-finance-model.md`](docs/personal-finance-model.md),
[`docs/M5_PERSONAL_FINANCE_DECISIONS.md`](docs/M5_PERSONAL_FINANCE_DECISIONS.md), and
[`docs/M5_0_PERSONAL_FINANCE_SPEC_REPORT.md`](docs/M5_0_PERSONAL_FINANCE_SPEC_REPORT.md). The selected
universal-core architecture and its completion report are in
[`docs/universal-financial-core.md`](docs/universal-financial-core.md) and
[`docs/M5_1A_UNIVERSAL_CORE_ARCHITECTURE_REPORT.md`](docs/M5_1A_UNIVERSAL_CORE_ARCHITECTURE_REPORT.md).
The approved M5.1-B coding sequence, target model, evidence gates, migration runbook, and recovery
boundary are in
[`docs/M5_1B_IMPLEMENTATION_PLAN.md`](docs/M5_1B_IMPLEMENTATION_PLAN.md) and
[`docs/M5_1B_MIGRATION_PLAN.md`](docs/M5_1B_MIGRATION_PLAN.md). The implemented M5.1-C1 behavior,
evidence, limits, and verification are recorded in
[`docs/M5_1_C1_IMPLEMENTATION_REPORT.md`](docs/M5_1_C1_IMPLEMENTATION_REPORT.md).
The subsequent implementation records are `docs/M5_1_C2_IMPLEMENTATION_REPORT.md`,
`docs/M5_1_C3_IMPLEMENTATION_REPORT.md`, and `docs/M5_1_C4A_READINESS_REPORT.md`. The future cutover
procedure and approvals are in `docs/M5_1_C4_CUTOVER_RUNBOOK.md` and
`docs/M5_1_C4_RELEASE_CHECKLIST.md`.

- Python 3.12+ package, local CLI, and FastAPI/Uvicorn application; SQLite schema version 3.
- Explicit tested migrations from schema version 1 through version 2 to version 3 that preserve
  every legacy financial table, posted history, audit record, receipt, fingerprint, and report.
- One immutable internal BUSINESS LedgerBook mapping per organization, with deterministic ID,
  matching currency/precision, database constraints, and membership-first internal resolution.
- Read-only/query-only migration preflight, deterministic evidence manifests, SQLite-consistent
  backup, reusable verified restore, and atomic fail-closed v2-to-v3 migration.
- One ownership-neutral deterministic financial service behind the compatible BUSINESS facade, with
  immutable server-issued context, typed commands, and explicit repository/unit-of-work boundaries.
- Canonical schema-v4 book-scoped persistence, constrained business extensions, audit sidecars,
  exact legacy fingerprint compatibility, and transactional reconstruction on disposable copies.
- Synthetic-only C4A fixture/rehearsal tooling that refuses existing input databases, proves writer
  exclusion, backup/restore, exact engine/API/CLI parity, canary behavior, capacity, and all eight
  required recovery drills without changing normal runtime selection.
- Organizations, users, role memberships, charts/accounts, periods, projects, document metadata,
  immutable transaction proposals/lines, validations, confirmations, journal entries/lines, and audit.
- Exact integer-minor-unit amounts and deterministic double-entry validation.
- Explicit proposal review and version-bound confirmation before atomic posting.
- Caller-key idempotency for API confirmation and posting, with conflict detection and atomic receipts.
- Posted ledger, account balances, trial balance, general ledger, basic income statement, basic balance
  sheet, and unclassified cash movements for caller-selected asset accounts.
- Full compensating reversals with immutable original history.
- One-way period locking, cross-organization constraints, immutable history, and automatic audit.
- Scrypt password hashes, opaque hashed bearer sessions, authenticated actor derivation, and logout.
- Explicit `OWNER`, `ADMIN`, `ACCOUNTANT`, `MEMBER`, and `VIEWER` permissions.
- Organization-scoped API routes for members, projects, accounts, periods, proposals, posting,
  journals/reversals, reports, and read-only audit history.
- Next.js 16, React 19, strict TypeScript, and Tailwind web application in `frontend/`, with an
  HTTP-only same-origin session proxy and no direct database or bearer-token access in browser code.
- Responsive chat-first shell with authenticated business context, explicit deferred Personal
  context, Money, Projects, Reports, Activity, and progressive accounting/audit disclosure.
- Complete API-driven proposal validation, exact-version confirmation, idempotent posting, ledger
  inspection, reporting, and audited compensating reversal workflows in the browser experience.
- Engine-derived journal-entry summaries for transaction activity; no financial totals are rebuilt
  in the frontend.
- M5.0 specifies a separate private `PersonalSpace`, tagged PERSONAL resolution, an internal
  ledger-book seam, a future typed personal adapter, personal account/category mappings, transfer and
  opening-balance workflows, personal reports, and strict owner isolation. These are specifications,
  not implemented capability.
- M5.1-A selects `LedgerBook` as the target canonical financial ownership scope, one
  ownership-neutral deterministic service behind business/personal facades, server-issued authorized
  financial contexts, a staged parity-gated business migration, and an external jurisdiction-policy
  layer. BUSINESS mapping, service, and disposable v4 persistence are implemented; PERSONAL remains
  deferred.
- M5.1-B defines eight separately gated implementation phases, canonical book-scoped schema-v4
  reconstruction, exact legacy fingerprint and audit compatibility, cutover/recovery limits, and
  M5.2 prerequisites. Phases 1–6 have implementation/rehearsal evidence. Phase 7 live BUSINESS
  cutover and Phase 8 PERSONAL prerequisites remain deferred.

No personal-finance domain or persistence, Financial Space discovery, general budget, financial
reminder, recurrence, category, goal, persisted conversation or AI behavior, document extraction,
marketing UI, billing, bank integration, tax filing, or cloud deployment has been implemented. The
M4 chat surface is an honest deterministic navigation/composer shell and does not simulate AI.

## Verification baseline

On 2026-09-28, the following M5.1-C4A acceptance gates passed on Windows with the locked Python and
frontend toolchains:

- 88 accounting, adversarial, concurrency, CLI, migration, API, C1/C2/C3, and C4A tests;
- 10 focused frontend component/workflow tests;
- strict mypy checking for all 28 application source files;
- Ruff lint checking;
- Ruff formatting verification for all 90 checked files;
- strict TypeScript, ESLint, Prettier, and optimized Next.js production build checks;
- synthetic-only `chatbook-c4a-rehearsal` module help execution;
- local-link validation for 182 local links across all 52 Markdown documents; and
- source/API boundary scans proving no PersonalSpace implementation, public LedgerBook authority,
  normal v4 activation, or alternate financial write path was introduced.

The production-shaped synthetic run contained three organizations across BDT/2, USD/3, and JPY/0;
525 proposals, 516 journal entries, 1,032 journal lines and receipts, 5,262 audit events, locked
periods, inactive accounts, projects, documents, and three 12-entry reversal chains. Source hash,
backup/restore manifests, exact v3/v4 engine/API/CLI outputs, database constraints, canary
post/retry/reversal, and all eight recovery drills passed. Local measured source/backup size was
6,922,240 bytes, final v4 size 10,604,544 bytes, migration-target peak 11,451,392 bytes, and proposed
free space with the clearly non-approved 25% rehearsal margin 31,619,840 bytes. These are synthetic
local measurements, not deployment performance claims.

The suite covers the complete forward and reversal lifecycle, balance invariants, invalid proposals,
explicit confirmation, stale proposal versions, caller-key retries/conflicts, locked periods,
inactive accounts, invalid/cross-organization references, role enforcement, persistence, concurrent
retries, competing reversals, post/lock races, rollback after storage failures, immutable posted/audit
history, audit correlation and anti-forgery, report reconciliation, exact money limits/parsing,
project-derived views, schema migration, and SQLite integrity checks.

The configured strict type gate covers the application package. An exploratory strict check of the
test modules reports 194 annotation/type errors; the runtime suite passes, but test typing remains
maintenance work. CI targets Python 3.12 and 3.14 on Linux, but no remote CI execution has been
recorded in this repository context.

## Architecture snapshot

- `chatbook/domain.py`: explicit immutable values, enums, and deterministic validation.
- `chatbook/engine.py`: authorized application workflows, posting, reversals, and reports.
- `chatbook/database.py`: SQLite connection policy, versioned migration, atomic writes, and audit setup.
- `chatbook/canonical_database.py`: explicit schema-v4 disposable-copy connection and audit boundary.
- `chatbook/canonical_migration.py`: verified v3-to-v4 reconstruction, reconciliation, timing, and
  rollback injection.
- `chatbook/cutover_readiness.py`: new-directory-only synthetic fixture, operational rehearsal,
  exact parity, capacity, canary, and recovery evidence.
- `chatbook/schema.sql`: strict schema, ownership constraints, posting guards, and immutability.
- `chatbook/migrations/`: explicit forward schema migrations.
- `chatbook/auth.py`: password credentials and opaque session lifecycle.
- `chatbook/permissions.py`: centralized role-to-permission mapping.
- `chatbook/api/`: typed HTTP contracts, authentication dependencies, authorization, and routing.
- `chatbook/cli.py`: trusted local manual interaction and explicit confirmation.
- `frontend/src/app/`: Next.js routes, responsive application shell, and same-origin API proxy.
- `frontend/src/features/`: context-aware, API-driven product workflows and progressive disclosure.
- `frontend/src/lib/api/`: typed browser client and response contracts without accounting logic.
- `tests/`: accounting, hardening, CLI, migration, and HTTP integration evidence.
- `frontend/src/test/`: focused M4 interface and workflow evidence.
- `docs/decisions/`: twenty accepted foundation, M3, M3.5, M4, M5.0, and M5.1-A ADRs.

Root documents have distinct purposes:

- [`requirement.md`](requirement.md): required behavior and acceptance criteria.
- [`architecture.md`](architecture.md): system boundaries and consistency model.
- [`process.md`](process.md): required workflow for repository changes.
- [`design.md`](design.md): concrete state, data, posting, report, and interface design.
- [`docs/product-model.md`](docs/product-model.md): Chatbooks product model, UX principles,
  information architecture, and domain-expansion assessment.
- [`docs/personal-finance-model.md`](docs/personal-finance-model.md): M5.0 personal ownership,
  ledger relationship, accounts, categories, transfers, opening balances, liabilities, reports,
  security, and future API/database specification.
- [`docs/M5_PERSONAL_FINANCE_DECISIONS.md`](docs/M5_PERSONAL_FINANCE_DECISIONS.md): separated
  engineering decisions and human/accountant policy gates.
- [`docs/universal-financial-core.md`](docs/universal-financial-core.md): selected persistent
  ledger-book ownership seam, authorized context, adapter/service boundary, staged compatibility
  migration, universal flow/read models, planning separation, security, AI, and compliance boundary.
- [`docs/M5_1B_IMPLEMENTATION_PLAN.md`](docs/M5_1B_IMPLEMENTATION_PLAN.md): eight-phase universal-core
  coding sequence, module boundaries, target data model, compatibility matrix, security/testing
  gates, personal prerequisites, risks, and policy decisions.
- [`docs/M5_1B_MIGRATION_PLAN.md`](docs/M5_1B_MIGRATION_PLAN.md): v2-to-v3 mapping, future v3-to-v4
  reconstruction, preflight and reconciliation manifests, backup/restore, cutover, rollback, and
  recovery rules.
- [`memory.md`](memory.md): current-state handoff and dated activity log; update after every task.

## Accepted decisions

1. Typed Python and transactional SQLite for the local foundation.
2. Integer minor units and posted journal lines as the financial source of truth.
3. Immutable proposals, deterministic validations, explicit confirmations, and automatic audit.
4. Nonoverlapping periods, one-way locks, full compensating reversals, and optional line-level
   project dimensions.
5. FastAPI as a thin network boundary around the accounting engine.
6. Salted scrypt credentials, opaque hashed sessions, and explicit organization role permissions.
7. Immutable proposal-version and authenticated-actor provenance for API confirmation.
8. Caller-supplied idempotency keys with atomic immutable receipts for confirmation and posting.
9. Financial Space is a typed application/product context: BUSINESS maps to the existing
   organization; PERSONAL will use a future personal ownership domain. No cross-cutting space schema
   or current ledger migration is introduced in M3.5.
10. Budgets, reminders, recurring templates, goals, and project estimates remain separate from
    posted actuals. Actual financial values derive from ledger data; schedules cannot post.
11. Conversation is the product front door with visible financial context, typed reviewable actions,
    progressive accounting/audit disclosure, and an independent Chatbooks visual identity.
12. The M4 browser application uses Next.js with a same-origin proxy that stores the opaque FastAPI
    access token in an HTTP-only cookie; FastAPI remains the authentication, authorization, and
    accounting authority.
13. Personal finance uses a separate private `PersonalSpace` ownership aggregate; organization
    membership never grants personal access.
14. `FinancialSpaceRef(PERSONAL, id)` resolves to `PersonalSpace`, while BUSINESS continues to
    resolve to `Organization`; existing organization routes remain business-only.
15. Personal actuals will use a typed personal adapter and internal ledger-book scope over the same
    ownership-neutral deterministic ledger service as the business compatibility facade.
16. Cross-space movements create two independently authorized ledger effects linked only by a
    non-financial correlation; no journal spans personal and business spaces.
17. Personal categories are stable owner-scoped labels with versioned mappings to ledger accounts;
    posted history retains mapping provenance and actual totals remain ledger-derived.
18. The future universal core uses a persistent internal `LedgerBook`, exactly one typed business or
    personal owner per book, canonical book-scoped financial persistence, and a staged parity-gated
    migration that enables personal writes only after business compatibility is proven.
19. The backend resolves a typed Financial Space into a server-issued `AuthorizedFinancialContext`;
    the business compatibility facade and future personal adapter call one deterministic service,
    and client-supplied book identifiers never confer authority.
20. Tax, VAT/GST, statutory reporting, payroll compliance, filing, and jurisdiction-specific rules
    remain outside the universal core; any future versioned policy layer consumes authorized data and
    can create proposals but cannot bypass confirmation or posting controls.
21. Schema v3 adds only an immutable one-to-one BUSINESS organization-to-LedgerBook mapping. A v2
    migration must pass read-only preflight, consistent backup, separate restore verification, legacy
    table hashing, and mapping checks before the version change commits.

These are implementation decisions, not invented jurisdictional accounting policies.

## Unresolved decisions

Do not implement assumptions for these topics:

- jurisdiction, tax, statutory statements, cash/accrual basis, and revenue recognition;
- formal cash-account designation and operating/investing/financing cash-flow classification;
- fiscal closing, retained earnings, opening balances, adjustment periods, and period reopening;
- role changes/removal, ownership transfer, dual approval, and confirmation expiry;
- credential provisioning for migrated CLI users, password recovery, MFA, login throttling, and
  session administration;
- proposal/reversal creation idempotency and idempotency-receipt retention;
- multi-currency, FX conversion, rounding policy, and precision changes;
- partial reversals and broader treatment of inactive accounts during corrections;
- project allocation or per-project balancing rules;
- document evidence, checksum verification, extraction, deduplication, and retention;
- proposal editing, cancellation, supersession, and master-data amendment semantics; and
- whether one personal space remains permanent, plus household ownership, sharing, advisor access,
  consent, revocation, export, deletion, retention, and recovery policy;
- personal period behavior, opening-balance offset/date/evidence, default chart/category mappings,
  category recategorization, credit-card semantics, liability splits, negative balances, and
  correction policy;
- personal-to-business contributions, drawings, distributions, salary, reimbursements, and loans,
  including the separate account mapping and confirmation policy for each side;
- investment valuation, net-worth inclusion, cash-position inclusion, multi-currency, FX, and
  revaluation policy;
- budget period/scope, actual mapping, rollover, overspend, enforcement, amendment history, and
  migration of existing project budget metadata;
- reminder recurrence, time zones, missed occurrences, notification delivery, completion semantics,
  and recurring proposal generation;
- conversation retention/privacy, source provenance, tool permissions, and future AI isolation; and
- cross-space coordinated-confirmation UX, personal period visibility, universal activity terms,
  household/advisor capabilities, and future jurisdiction-package product claims; and
- Internet/multi-host deployment, production database concurrency, TLS/proxy trust, secrets,
  encryption, backup/restore, security monitoring, and external audit anchoring.

The full ambiguity register is in [`docs/accounting-model.md`](docs/accounting-model.md). Obtain an
explicit decision and add or update an ADR before changing a major architectural boundary.

## Activity log

- 2026-09-25 — Created the root requirements, architecture, process, design, and memory documents
  from the implemented foundation and existing ADRs. Verified that all local documentation links
  resolve and that no obsolete product name appears in the new files. No accounting code changed.
- 2026-09-25 — Made memory updates mandatory at the end of every task by updating `rules.md`,
  `AGENTS.md`, `process.md`, and this memory protocol. Read back the amended rulebook and checked the
  affected documents for consistent task-final, non-recursive wording. No accounting code changed.
- 2026-09-25 — Completed the accounting-core hardening and audit pass after reading all documentation,
  ADRs, source, schema, and tests. Fixed direct forged audit insertion through the supported database
  connection, added 11 adversarial tests, and documented API idempotency, concurrency portability,
  correction, account-hierarchy, and production trust boundaries. All 46 tests passed; strict mypy,
  Ruff lint, and Ruff format checks passed; all local Markdown links resolved. The kernel is ready for
  application/API development with the conditions recorded in `HARDENING_REPORT.md`.
- 2026-09-25 — Ran the Chatbooks command-line application and completed a temporary in-memory startup
  and write check. The command catalog loaded, the database schema initialized, and local user creation
  succeeded. No persistent database or accounting data was created, and no application code changed.
- 2026-09-26 — Completed M3 after reading the rulebook, memory, repository documentation, ADRs, source,
  schema, and tests. Added the FastAPI application boundary, credential/session authentication,
  organization roles, scoped projects/accounts/periods/proposals/journals/reports/audit routes,
  version-bound confirmation provenance, caller-key confirmation/posting idempotency, schema v2 with
  tested v1 migration, API/reconciliation tests, four ADRs, and the implementation report. All 56
  tests passed; strict application mypy, Ruff lint, Ruff formatting, Markdown-link, dependency-lock,
  and OpenAPI checks passed. Remaining security, deployment, workflow, and accounting-policy decisions
  are recorded in `API_LAYER_IMPLEMENTATION_REPORT.md` and the ambiguity register.
- 2026-09-26 — Completed the M3.5 product-model and architecture revision after reviewing the full
  repository, documentation, ADRs, source, schema, and tests. Defined the Chatbooks personal and
  business direction, typed Financial Space context, chat-first UX, progressive disclosure, compact
  information architecture, personal-ledger assessment, budget/reminder boundaries, migration
  posture, M0–M15 roadmap, and ADRs 0009–0011. Updated requirements, architecture, design,
  accounting, AI, security, roadmap, README, and the M3.5 report. No executable code or schema
  changed. All 56 tests passed; strict mypy for 11 source files, Ruff lint, Ruff formatting for 46
  files, and all 58 local links across 29 Markdown files passed. The repository is ready for an M4
  business-capability frontend foundation, while personal finance, budgets, reminders, and AI remain
  deferred to their documented milestones.
- 2026-09-26 — Normalized the project/product naming convention across the M3.5 documentation and
  ADRs. Chatbooks is now explicit as the canonical engineering project, repository, package, CLI,
  module, environment, and internal identifier; Chatbooks is reserved for the customer-facing
  product and UX. Removed language that treated `chatbook` identifiers as temporary compatibility
  names. No executable code, schema, package, command, migration, or database identifier changed.
  Verified engineering and product headings, confirmed all three M3.5 ADRs state the distinction,
  found no Chatbooks references in source/tests/package metadata/CI, and validated all 61 local
  links across 29 Markdown files. No inconsistent naming references remain in the audited scope.
- 2026-09-26 — Completed M4 Financial UX Foundation. Added the Next.js/React/TypeScript/Tailwind
  frontend, HTTP-only same-origin session proxy, authenticated responsive shell, tagged
  Personal/Business context experience, Money and proposal workflows, project planning and
  ledger-derived detail, five reports, read-only audit activity, safe reversal flow, and one
  organization-scoped engine-derived journal-entry summary endpoint. Preserved FastAPI and the
  deterministic engine as the exclusive accounting write/calculation boundaries; no schema or
  ledger redesign was required. Added ADR 0012 and updated requirements, architecture, security,
  product, design, roadmap, README, and the M4 implementation report. All 56 Python tests and 10
  frontend tests passed, together with strict mypy, Ruff lint/format, TypeScript, ESLint, Prettier,
  the optimized Next.js build, OpenAPI generation, local end-to-end integration, desktop/mobile
  browser checks, source-boundary scans, and Markdown-link validation. Personal persistence,
  budgets, reminders, documents, AI, integrations, and production infrastructure remain deferred.
- 2026-09-26 — Started the M4 application for local use. The Chatbooks Next.js development
  server is running at `http://127.0.0.1:3001` because port 3000 is occupied by another project, and
  the Chatbooks FastAPI service is running at `http://127.0.0.1:8000`. Verified HTTP 200 responses
  from the frontend login page and API documentation, and queued the login page in the Codex browser.
  No source code, accounting records, schema, or product behavior changed.
- 2026-09-26 — Investigated the browser's stuck `Checking your session` state. The previously attached
  development processes had exited, leaving a stale browser page. Restarted the Chatbooks frontend
  on port 3001 and Chatbooks API on port 8000 as hidden background processes. Verified HTTP 200 for
  `/chat` and the API documentation, plus the expected HTTP 401 session response without a valid
  cookie. Confirmed the implemented page inventory and that M4's chat page is a deterministic shell;
  conversational AI remains deferred. No source code, accounting records, or schema changed.
- 2026-09-26 — Completed M5.0 Personal Finance Domain Specification after reviewing the rulebook,
  full documentation and ADR set, accounting/API/database source, tests, and M4 frontend boundaries.
  Defined separate private `PersonalSpace` ownership, typed Financial Space resolution, future
  ledger-book and personal-adapter integration, account/category mappings, same-space and cross-space
  transfers, opening-balance provenance, liability limits, personal reports, privacy, and proposed
  API/database impact. Added ADRs 0013–0017 and a decision register that separates engineering choices
  from human/accountant policy. Updated requirements, architecture, design, product, accounting, AI,
  security, roadmap, README, and the M5.0 report. No executable code, schema, endpoint, or UI changed.
  All 56 Python and 10 frontend tests passed, together with mypy, Ruff lint/format, TypeScript, ESLint,
  Prettier, the optimized Next.js build, stale-wording scans, executable-source boundary scans, and
  107 local links across 39 Markdown files. The repository is ready for M5.1 planning, while personal
  posting remains blocked on the documented policy decisions and migration/constraint evidence.
- 2026-09-26 — Completed M5.1-A Universal Financial Core Architecture after reviewing the complete
  repository, documentation, ADRs, source, schema/migration code, tests, and frontend financial-space
  boundary. Compared separate ledgers, a one-step generic replacement, and phased convergence;
  selected a persistent typed-owner `LedgerBook`, one deterministic service, authorized financial
  context, business compatibility facade, future personal adapter, staged parity-gated migration,
  planning/actual separation, and an external jurisdiction-policy layer. Added ADRs 0018–0020 and
  updated requirements, architecture, design, accounting, security, AI, product, roadmap, README,
  and the M5.1-A report. No executable code, schema, migration, endpoint, or UI changed. All 56 Python
  tests and 10 frontend tests passed, together with mypy, Ruff lint/format, TypeScript, ESLint,
  Prettier, the optimized Next.js build, executable-boundary scans, and all 138 local links across 44
  Markdown files. Work stopped before M5.1-B as required.
- 2026-09-27 — Completed M5.1-B Universal Financial Core Implementation Plan after reviewing the
  complete repository, documentation, twenty ADRs, schema and migration machinery, accounting/API
  source, tests, and frontend boundaries. Added the eight-phase implementation plan and detailed
  migration/recovery runbook; selected a BUSINESS-only additive v3 mapping before service extraction
  and canonical v4 reconstruction; preserved IDs, legacy fingerprints, audit rows/sequences,
  receipts, reports, and business compatibility in the plan; and identified M5.1-C1 as the exact
  next coding milestone. Updated the README and roadmap. No Python, TypeScript, SQL, migration, API,
  frontend, test, or database behavior changed, and no new ADR was needed. All 56 Python tests and 10
  frontend tests passed, together with mypy, Ruff lint/format, TypeScript, ESLint, Prettier, the
  optimized Next.js build, implementation-boundary scans, required-section checks, and all 153 local
  links across 46 Markdown files.
- 2026-09-27 — Completed M5.1-C1 Preflight Evidence and Additive Business LedgerBook Mapping. Added
  deterministic read-only migration inspection, sanitized representative/corrupt fixtures,
  SQLite-consistent backup and separate restore proof, atomic fail-closed schema-v2-to-v3 migration,
  an immutable one-to-one BUSINESS book mapping, membership-first internal resolution, and atomic
  book creation with new organizations. Preserved every legacy financial table and existing API,
  CLI, frontend, report, audit, receipt, and idempotency behavior; no personal domain, service
  extraction, canonical schema v4, or new accounting policy was introduced. Added 14 focused tests,
  updated the controlling plans, architecture/accounting/security/roadmap documents and ADR status,
  and created the M5.1-C1 implementation report. All 70 Python and 10 frontend tests passed, together
  with mypy for 15 source files, Ruff lint/format for 69 files, TypeScript, ESLint, Prettier, the
  optimized Next.js build, the installed migration-evidence command, scope-boundary scans, and all
  161 local links across 47 Markdown files.
- 2026-09-27 — Completed M5.1-C2 Universal Service Extraction over Organization Storage. Added the
  immutable `AuthorizedFinancialContext` and capabilities, typed financial commands, explicit
  repository/unit-of-work protocols, the schema-v3 organization storage adapter, and one
  `UniversalFinancialService` implementation for accounts, periods, proposal validation,
  exact-version confirmation, idempotent posting, compensating reversal, ledger/report calculations,
  and financial audit reads. Converted `AccountingEngine` into the stable BUSINESS compatibility
  facade while retaining business-only organization, membership, project, and document behavior.
  Preserved schema v3, organization-scoped financial tables, legacy fingerprint bytes, API/CLI/
  frontend contracts, audit and receipt data, concurrency, and report results; no PersonalSpace,
  canonical storage, AI, planning domain, document extraction, tax/compliance, or accounting policy
  was added. Added 7 focused context, isolation, parity, identical-copy differential, fingerprint,
  public-boundary, and source-boundary tests plus the C2 implementation report and documentation/ADR
  status updates. All 77 Python tests and 10 frontend tests passed, together with strict mypy for 23
  source files, Ruff lint/format for 79 files, TypeScript, ESLint, Prettier, the optimized Next.js
  build, 165 local Markdown links, package import/manifest checks, and an OpenAPI check covering 28
  paths and 35 operations with no public book/context/PersonalSpace authority. A 1,000-iteration
  in-memory account-list check observed four indexed reads per call and a 0.022 ms mean. Temporary
  sandbox test artifacts were removed.
- 2026-09-27 — Completed M5.1-C3 Canonical Book-Scoped Persistence Rehearsal on disposable database
  copies. Added schema-v4 temporary reconstruction and transactional swap, the explicit
  `CanonicalDatabase`, book-scoped `SQLiteBookStorage`, composite cross-book constraints, constrained
  BUSINESS project/document extensions, immutable audit-book sidecars, legacy
  `organization-v1` fingerprint verification, a verified-backup migration command, sanitized
  evidence, eleven rollback injection gates, critical query-plan evidence, and explicit rehearsal
  engine/API paths while normal application/CLI startup remains schema v3. Preserved stable IDs,
  proposal/journal state, receipts, reversal chains, audit rows/sequences/JSON, reports, API/CLI
  behavior, and the universal service as the sole financial authority. Added 9 C3 tests covering
  exact migration/report reconciliation, pending/validated/confirmed/posted fingerprints, new
  posting/reversal/audit behavior, cross-book and tampering attacks, failure rollback, API/CLI
  parity, concurrent retry/reversal/period-lock behavior, versions, query plans, and a synthetic
  100-posted-transaction/200-line rehearsal. The measured local volume run took 0.290 s for backup
  plus verification, 0.014 s for target restore, 0.112 s for migration, 0.0066 s for index/trigger
  installation, and 0.0019 s for trial balance, with a 2,306,048-byte measured target footprint;
  these are local synthetic measurements, not production claims. Updated architecture, accounting,
  security, migration/process, roadmap, README, ADR status, and the 21-section C3 report. All 86
  Python tests and 10 frontend tests passed, together with strict mypy, Ruff lint/format, TypeScript,
  ESLint, Prettier, the optimized Next.js build, migration/CLI help checks, source-boundary checks,
  and all local Markdown links. No shared database was migrated; no C4 cutover, PersonalSpace,
  personal behavior, frontend feature, AI, document extraction, planning domain, tax/compliance, or
  production infrastructure was added.
- 2026-09-28 — Completed M5.1-C4A Business Cutover Readiness and Deployment Rehearsal without a live
  cutover. Added a synthetic-only, new-directory rehearsal command; reusable verified restore;
  migration reconciliation/timing instrumentation; a three-organization production-shaped fixture;
  exact v3/v4 engine, authenticated API/OpenAPI, and CLI parity; writer-lock proof; measured backup,
  restore, maintenance, and capacity evidence; a disposable proposal/post/retry/reversal canary; and
  eight fail-closed recovery drills including the post-v4-write forward-recovery boundary. Created
  the C4 cutover runbook, three-party release checklist, and 13-section readiness report, and updated
  architecture, process, security, roadmap, plans, ADR status, and README. All 88 Python and 10
  frontend tests passed with mypy, Ruff lint/format, TypeScript, ESLint, Prettier, optimized Next.js
  build, help/source-boundary checks, exactly 13 report sections, and 182 local links across 52
  Markdown files. Disposable database artifacts were removed. Normal startup remains schema v3;
  no shared database, deployment configuration, production behavior, PERSONAL owner, personal
  feature, budget/reminder, AI, extraction, tax/compliance, or infrastructure was changed.
- 2026-09-28 — Completed M5.2-A Simplified Personal Finance MVP Policy as documentation and
  implementation constraints only. Created `docs/M5_2_PERSONAL_FINANCE_MVP_POLICY.md` with the
  product promise, personal/account/category models, deterministic income/expense/transfer/card/
  principal-only-loan/correction semantics, gated opening-balance and period boundaries, six
  ledger-derived personal reports, budget/reminder/AI compatibility, explicit tax/compliance
  exclusion, deferred scope, and classified ENGINEERING/PRODUCT/ACCOUNTING POLICY decisions.
  Created `docs/M5_2_PERSONAL_FINANCE_POLICY_REPORT.md` and updated root/detailed architecture,
  accounting model, design, roadmap, personal model, and decision register. The policy selects five
  presentation account kinds and curated-plus-user-created categories while leaving ledger mappings,
  personal periods, opening-balance offsets, ambiguous liability/cross-space treatment, cash-position
  inclusion, and all jurisdictional rules behind accountant gates. No ADR was needed because ADRs
  0013–0020 already govern the architecture. No executable, schema, API, UI, PersonalSpace, budget,
  reminder, AI, tax, or compliance behavior changed. Documentation verification passed: all 19
  required policy sections and all three decision classes were present, 191 local links across 54
  Markdown files had no breakage, all 9 changed documents passed Prettier, and the scope scan found
  zero executable or schema changes. Code, database, API, frontend, type, and lint tests were not run
  because the authorized milestone required documentation checks only.
- 2026-09-28 — Completed M5.2-B Personal Finance Foundation & Persistence Implementation Plan as a
  planning-only milestone. Created `docs/M5_2_PERSONAL_FINANCE_IMPLEMENTATION_PLAN.md` and
  `docs/M5_2_PERSONAL_FINANCE_IMPLEMENTATION_REPORT.md` after inspecting the M5.0/M5.1 architecture,
  ADRs 0013–0020, C1–C4A evidence, schema-v3 and rehearsed schema-v4 storage, universal service,
  BUSINESS facade, authentication/authorization, and test boundaries. The plan defines the
  PersonalSpace ACTIVE-only MVP lifecycle, owner-authorized PERSONAL context resolution, one-to-one
  PERSONAL LedgerBook mapping, balance-free FinancialAccount presentation records, PersonalCategory
  and immutable versioned mappings, reuse of book-scoped periods and UniversalFinancialService,
  owner-kind repository/storage separation, personal provenance, audit/idempotency behavior,
  cross-space isolation, exact M5.2-A feature gates, v4-to-v5 migration discipline, BUSINESS
  compatibility, adversarial tests, and staged M5.2-C0 through C7 implementation gates. It records
  successful M5.1-C4 cutover and observation as a hard prerequisite and keeps all personal postings
  closed until their period/mapping/accounting policies are separately approved. No code, schema,
  migration, endpoint, UI, or executable behavior changed. Both new documents passed Prettier and
  all 213 local Markdown links passed; runtime, type, lint, schema, API, and frontend tests were not
  run because the task explicitly limited verification to documentation/link/format checks.
- 2026-09-28 — Performed the authorized M5.1-C4 actual-environment preflight and issued a fail-closed
  NO-GO without starting cutover. Created `docs/M5_1_C4_PREFLIGHT_BLOCKER_REPORT.md` and linked the
  measured result from the C4A readiness report, release checklist, and runbook. Read-only inspection
  found only `F:\Projects\chatbook\chatbook.db`: an empty 323,584-byte schema-v2 development file
  with SHA-256 `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`,
  `integrity_check=ok`, zero foreign-key violations, and no BUSINESS records. No approved schema-v3
  source or deployment definition, complete writer inventory/control, protected backup/restore/
  target paths, normal v4 runtime selection, immutable v3 recovery release, monitoring thresholds/
  owners, approved canary inputs, maintenance window, or named signoffs existed; all 50 checklist
  items remain unchecked. The local F: drive reported 506,913,583,104 free bytes, but this is not
  deployment capacity evidence. The candidate database inherited broad modify access and was not an
  approved protected artifact. The permission-enabled backend/API/CLI/migration unittest suite ran
  88 tests in 31.044 seconds with one C3 `reconciliation_mismatch` failure-injection error: the
  injected increment selected a maximum debit and hit the line-limit CHECK before the intended
  reconciliation error. This regression gate remains a blocker. Four C4 documents pass Prettier,
  201 local links across 57 Markdown files pass, and the candidate database hash/version remained
  unchanged. No writer was stopped, no backup/restore/target was created, no migration/canary/
  rollback/resumption occurred, and no code, schema, API, runtime configuration, or PERSONAL work
  changed.
- 2026-09-28 — Repeated the M5.1-C4 actual-environment preflight after the execution request was
  reissued and confirmed the same fail-closed NO-GO. Re-read the C4A runbook, checklist, readiness
  report, blocker report, and C1/C2/C3 evidence, then repeated read-only database, runtime, capacity,
  environment, deployment-artifact, access-control, and checklist inspection. `chatbook.db` remains
  the only application database: unchanged at 323,584 bytes, schema version 2, SHA-256
  `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`, with integrity OK, zero
  foreign-key violations, and zero rows in every application table. No relevant process or listener
  was active; Windows service and scheduled-task inventory remained access-denied; no deployment,
  protected artifact, runtime environment, owner/signoff, monitoring, canary, recovery-release, or
  approved schema-v3 source evidence appeared. All 50 checklist items remain unchecked, inherited
  database ACLs remain broad, and the known C3 release-gate test failure remains unresolved. Updated
  the blocker and readiness reports with the repeated measurements. Both changed documents pass
  Prettier, and 201 local links across 57 Markdown files pass. No backup, migration, canary,
  writer-control, rollback, schema, code, runtime, or PERSONAL operation was performed.
- 2026-09-28 — Completed the authorized M5.1-C4A regression-only remediation. The
  `reconciliation_mismatch` fault injector in `chatbook/canonical_migration.py` no longer selects a
  positive debit by random UUID order and blindly increments it. It now deterministically prefers
  the smallest sub-maximum positive debit and increments it by one; if all positive debits are at
  `MAX_AMOUNT`, it deterministically decrements one by one. The injected line therefore remains
  constraint-valid, reaches the intended financial-projection mismatch, raises
  `migration_reconciliation`, rolls the disposable target back to schema v3, and leaves the source
  byte-identical. No line limit, accounting rule, migration validation, transaction boundary,
  rollback behavior, runtime selection, or safety gate changed. Created
  `docs/M5_1_C4A_REGRESSION_REMEDIATION_REPORT.md` and updated the preflight blocker and C4A
  readiness reports to mark only the code-regression blocker resolved. Verification passed: the
  focused test once, 10 additional fresh repetitions, all 11 C3/C4A tests, all 88 backend tests,
  strict mypy for 28 source files, Ruff lint, Ruff formatting for 95 files, frontend Prettier, five
  focused schema/authority/source-boundary/activation safety tests, Prettier for the changed C4
  documents, and 203 local links across 58 Markdown files. The development `chatbook.db` retained
  schema version 2, size 323,584 bytes, integrity OK, zero foreign-key violations, and SHA-256
  `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`. No production/shared
  database, backup, migration, canary, writer shutdown, rollback, resumption, or M5.2 work occurred.
- 2026-09-28 — Completed M5.1-C4P controlled deployment preparation without executing C4. Added
  `chatbook/deployment_preparation.py`, the `chatbook-c4p` command, and two focused tests. Created the
  persistent, non-production BUSINESS staging environment at
  `F:\ChatbookDeployment\m5-1-c4-controlled` through the normal schema-v3 initialization and
  deterministic application/engine paths. The source remains schema v3 at
  `source\chatbook-business-v3.db`, 475,136 bytes, SHA-256
  `7532962f3d3e752655946b1ec629b219e11d4f63de618dee0baa0c6e1e03e936`, with two organizations,
  BDT/USD precision, representative roles/accounts/periods/proposals/postings/retries/reversals,
  projects/documents, 150 audit events, integrity OK, zero foreign-key violations, and reconciled
  reports. Established restricted local ACL evidence, separate source/backup/restore/target/config/
  secrets/log/evidence/recovery paths, live-rehearsed backend/frontend start and full process-tree
  stop controls, five repeatable host-level writer-gate checks, deterministic release identity
  `576e88c8a47dd305fc40984242a923c15252eca89d375e0af43f1a9659988791`, a compatible v3 recovery
  archive, a verified backup/restore with content fingerprint
  `bb2574b83dcd0855ef5b52150905e256f90208075e1c5e3a6623e2fc7cfe12c2`, monitoring definitions,
  and a valid but unexecuted BUSINESS canary. Created
  `docs/M5_1_C4P_DEPLOYMENT_PREPARATION_REPORT.md` and integrated C4P evidence into the runbook,
  release checklist, readiness report, and preflight blocker report while leaving all 50 checklist
  items unchecked. Verification passed: 90 backend tests, five focused safety/source-boundary tests,
  mypy for 29 source files, Ruff lint/format for 99 files, 10 frontend tests plus TypeScript/ESLint/
  Prettier/build, live schema-v3 health/auth/API/CLI/report checks, backup/restore parity, runtime
  shutdown, five host-level writer-gate repetitions, Prettier for all changed C4 documents, and 205
  local links across 59 Markdown files. A sandbox-only lock probe did not preserve native SQLite
  contention; the actual host verifier consistently returned `database is locked`. The reserved v4
  target is absent, all controlled runtimes are stopped, and the development `chatbook.db` retained
  SHA-256 `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`. No controlled/development
  v4 migration, canary, v4 writer, PERSONAL data, production claim, or M5.2 work occurred; existing
  migration tests used only disposable temporary copies.

- 2026-09-28 — Completed M5.1-C4P2 normal schema-v4 runtime selection and C4P hardening without
  executing C4. Added `chatbook/runtime.py` and the `chatbook-runtime` entry point; normal API,
  authentication, engine, and trusted CLI startup now share an explicit server-owned storage/schema/
  path/access/release configuration. Schema-v4 startup requires an existing absolute target, schema
  4, explicit `read-only` or `read-write` access, and an immutable release SHA; it rejects rehearsal,
  PERSONAL, raw-book, development-database, missing-target, mismatched-schema, and fallback paths.
  Canonical read-only mode opens SQLite read-only/query-only and rejects writes before a transaction.
  Hardened C4P controls accept only the fixed schema-v3 source with read-write access or the fixed
  future v4 target with read-only access, never migrate/create a database, record sanitized runtime
  identity, preserve the writer gate, and use final release
  `672e551c8617a1e5371d4a5b31350fce700189f02c75457fafb9519241e43bde`. Added five focused C4P2
  tests and `docs/M5_1_C4P_RUNTIME_SELECTION_REPORT.md`; updated the C4P report, C4A readiness,
  release checklist, cutover runbook, and README without checking any approval box. Verification
  passed: exact final 95-test backend suite in 39.766 seconds; focused C4P2 5/5; focused C3/C4A
  11/11; mypy for 30 source files; Ruff and formatting for 102 files; frontend 10/10 tests,
  TypeScript, ESLint, Prettier, and production build; 210 local links across 60 Markdown files; live
  fixed-path schema-v3 backend/frontend startup, process-tree stop, quiescence, sanitized evidence,
  and rollback-only writer-gate checks. Normal API/CLI rehearsal activation, public raw-book
  authority, startup migration calls, evidence secret matches, and raw audit export scans all found
  zero. The development `chatbook.db` stayed at SHA-256
  `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`; no v4 target or PERSONAL
  data exists. During live verification, authentication was found to create an ephemeral session;
  the verifier stopped on the mismatch, the changed copy was retained, and the controlled source was
  restored from its verified schema-v3 backup. Its current SHA-256 is
  `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71`, its deterministic financial
  content fingerprint remains `bb2574b83dcd0855ef5b52150905e256f90208075e1c5e3a6623e2fc7cfe12c2`,
  all financial counts remained unchanged, and the recovery is explicitly recorded as requiring
  source reapproval. No migration, canary, v4 writer, financial mutation, or M5.2 work occurred.

- 2026-09-28 — Completed the documentation-only M5.1-C4P3 final readiness reconciliation. Created
  `docs/M5_1_C4P3_FINAL_READINESS_REPORT.md` and aligned the C4A readiness report, historical
  preflight blocker report, release checklist, cutover runbook, C4P deployment-preparation report,
  C4P2 runtime-selection report, and README. Preserved synthetic C4A, disposable C3 rehearsal,
  controlled C4P staging, C4P2 engineering, and future real-C4 evidence as separate classes. The
  canonical migration/reconciliation implementation, complete regression/source-boundary gate, and
  normal server-controlled schema-v4 selection are `CLOSED`; remaining technical preparation,
  deployment controls, human approvals, signatures, and final go/no-go retain their exact
  `PARTIALLY PREPARED` or `BLOCKED` status, while non-C4 product work is `DEFERRED`. Final state:
  **NOT READY FOR FINAL PREFLIGHT**; C4 remains `NO-GO` and unauthorized. Verification passed:
  Prettier on all eight reconciled Markdown files; 219 local links across 61 project Markdown files;
  three current tables with 16 rows each and only the four allowed statuses; all 12 required blocker
  areas present; 50 release-checklist items unchecked and zero checked; stale current-state wording
  scan clean. No runtime, database, migration, target, canary, writer, financial test, PERSONAL data,
  or C4 execution action occurred.

- 2026-09-29 — Completed the documentation-only M5.1-C4P4 final operational readiness package
  without executing C4. Created `docs/M5_1_C4_APPROVAL_MATRIX.md` with five blank named-role records,
  explicit approval gates, and elevated host-inventory commands; created
  `docs/M5_1_C4P4_OPERATIONAL_READINESS_REPORT.md` with the exact candidate source, release/recovery
  identities, writer and traffic assessment, protection/capacity/monitoring/canary packages,
  remaining blockers, and operator actions. Reclassified all 50 release-checklist items using only
  `CLOSED`, `READY FOR APPROVAL`, `REQUIRES OPERATOR ACTION`, and `BLOCKED`, leaving every checkbox
  unchecked. Updated the runbook to use phased preflight/post-migration gates and made C4P4 the
  current readiness authority in README. Final state: **NOT READY FOR FINAL PREFLIGHT**. Traffic
  rejection/graceful drain and monitoring collection/alerting remain genuine implementation gaps;
  elevated inventory, protection/recovery controls, candidate-specific capacity/window evidence,
  named approvals, and final go/no-go remain open. Verification passed: Prettier for all five
  changed documents; 230 local links across 63 Markdown files with zero broken; all 14 report
  sections present; 50 unique checklist items, all unchecked, with zero invalid statuses. Read-only
  boundary checks reconfirmed source/backup/restore at 475,136 bytes and SHA-256
  `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71`, no v4 target, no staging
  PID files or relevant listeners, and unchanged development `chatbook.db` SHA-256
  `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`. No backend, migration,
  canary, writer, financial, PERSONAL, or database mutation was performed.

## 2026-09-29 — M5.1-C4P5 traffic drain and monitoring preparation

- Inspected the controlled deployment topology and found direct local FastAPI/Next.js HTTP only:
  **NO EXTERNAL TRAFFIC TERMINATION PRESENT**. Implemented a server-owned, fail-closed maintenance
  gate with in-flight request accounting, explicit drain/seal states, operator-supplied timeouts,
  graceful Uvicorn shutdown, and no HTTP/frontend toggle. Hardened the staging controls for ordered
  drain, shutdown, quiescence, reset, and monitoring collection.
- Added a deterministic read-only twelve-signal C4 monitor. Hard schema, integrity, foreign-key,
  idempotency, audit-sidecar, ledger, report, and migration invariants fail closed. Rates, latency,
  drain, and duration values remain `BASELINE_REQUIRED`; owners, escalation, alert destination,
  observation period, decision authority, and protected-artifact auditing remain
  `REQUIRES_OPERATOR_DECISION`. No repair, rollback, or financial mutation path was added.
- Added six adversarial C4P5 tests and reconciled the C4P4 report, C4A readiness report, blocker
  report, 50-item release checklist, cutover runbook, approval matrix, README, and new root
  `OPERATIONS.md`. Created `docs/M5_1_C4P5_TRAFFIC_MONITORING_REPORT.md` with the required readiness
  table and exact staging/configuration evidence.
- Verification passed: traffic drain 5 consecutive runs; focused C4P5 6/6; combined C4P5/C4P/C4P2
  13/13; C3/C4A 11/11; complete backend 101 tests; five safety/source-boundary tests; mypy on 32
  source files; Ruff lint and formatting on 110 files; frontend 10 tests, typecheck, ESLint,
  Prettier, and production build; documentation formatting; 237 local links across 65 Markdown
  files with zero broken. All 50 checklist items remain unchecked with valid status labels.
- Controlled staging proved HTTP 200 before drain, HTTP 503 after drain, zero final in-flight
  requests, clean backend stop, successful rolled-back writer-gate/quiescence proof, and zero hard
  monitor alerts. The controlled schema-v3 source remained SHA-256
  `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71`; development `chatbook.db`
  remained `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`; no v4 target exists.
  No migration, canary, v4 writer, financial mutation, or PERSONAL work occurred.

## 2026-09-30 — M5.1-C4P6 operator decision and approval intake

- Created `docs/M5_1_C4P6_OPERATOR_DECISION_PACKET.md` and
  `docs/M5_1_C4P6_OPERATOR_DECISION_REPORT.md`. The packet requires exactly one unsigned A/B target
  choice, keeps the source/release identities blocked until that choice, covers all remaining
  operator decisions, uses only the required status vocabulary, and provides blank name/role/
  decision/evidence/signature/timestamp fields. No decision was marked approved.
- Added exact future elevated Windows read-only inventory commands for host/environment identity,
  paths/hashes/ACLs/capacity, runtime/configuration, processes, services, scheduled tasks, listeners,
  PID state, handles, environment-variable names, and the read-only monitor. Preserved the unchanged
  16-field BUSINESS canary as **DEFINED — AWAITING ACCOUNTING/DATA APPROVAL + RELEASE OWNER
  APPROVAL**. No elevated result was claimed.
- Updated the approval matrix, 50-item release checklist, C4A readiness report, C4P4 successor
  record, cutover runbook, and `OPERATIONS.md` without removing historical evidence. Corrected the
  documented monitoring invocation to match the fixed no-argument staging control script.
- Verification passed: Prettier on all eight created/updated operational documents; 243 local links
  across 67 Markdown files with zero broken; two target choices with zero selected; 26 decision
  rows with valid statuses and zero approved; five blank required-role rows; all 16 canary fields
  unchanged; 50 valid release-checklist items, all unchecked. The read-only monitor returned
  `COLLECTED`, schema 3, zero hard alerts, and no financial mutation.
- Read-only boundaries remained unchanged: controlled schema-v3 source SHA-256
  `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71`; compatible recovery
  archive SHA-256 `a0a06cf0c90974bbacc2ee2dcd3e28cca3d74087818372b9645a702f26f05751`;
  development `chatbook.db` SHA-256
  `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`; no backend/frontend PID
  files and no schema-v4 target. No C4 execution, migration, canary, v4 writer, database mutation, or
  PERSONAL work occurred.

## Next authorized work

M5.1-C4 remains **NO-GO** and **NOT READY FOR FINAL PREFLIGHT**. A responsible human must first
record exactly one deployment-target choice in the C4P6 packet. If A is selected, the candidate
source/release/recovery evidence can move to human review; if B is selected, prepare a new target and
regenerate all target-specific evidence. Named operators must then run the elevated inventory,
implement/approve protection and recovery controls, establish baseline-derived values, assign
monitoring ownership/delivery/observation, approve the unchanged canary and rollback boundary, and
sign every applicable gate. C4 work remains separately authorized and cannot begin from this packet
alone.

## 2026-09-30 — M5.1-C4P7 SaaS server deployment foundation

- Recorded the operator's explicit D01=B decision: `F:\ChatbookDeployment\m5-1-c4-controlled` is
  controlled staging only and is ineligible as the future C4 server/source. Preserved all staging
  evidence as historical engineering evidence and left every C4 approval, signature, canary, and
  go/no-go gate open.
- Added the provider-neutral `deploy/saas` package, strict deployment configuration and validation,
  single-authoritative-writer topology, backend/frontend startup contracts, maintenance/drain and
  shutdown controls, storage/backup/restore contracts, sanitized monitoring/evidence templates,
  and the `chatbook-saas-deployment` CLI. Added safe disposable schema-v3 BUSINESS provisioning
  through `AuthService` and `AccountingEngine`; no alternate transaction store or accounting write
  path was introduced.
- Created `docs/M5_1_C4P7_SAAS_DEPLOYMENT_FOUNDATION.md` and
  `docs/M5_1_C4P7_SAAS_DEPLOYMENT_REPORT.md`; reconciled the C4P6 packet/report, approval matrix,
  release checklist, cutover runbook, readiness/blocker reports, README, and operations guide.
  Provider, server, TLS, supervisor, storage, secrets, off-host recovery, monitoring baselines,
  named owners, approvals, and final authorization remain operator/server decisions.
- Verification passed: focused C4P7 4/4; combined C3/C4A/C4P2/C4P5/C4P7 26/26; complete backend
  105 tests; mypy on 33 source files; Ruff lint and format on 117 files; frontend 10 tests plus
  typecheck, ESLint, Prettier, and production build; deployment-package/single-writer/security
  checks; environment-template hygiene; and 253 local links across 70 Markdown files with zero
  broken. Disposable tests covered startup, health, authentication, maintenance 503, shutdown,
  writer exclusion, verified backup/restore, source preservation, no v4 target, and no PERSONAL
  data.
- Development `chatbook.db` remained SHA-256
  `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`; controlled staging source
  remained `de4d4b32a8456543a066536f3a9be8f97f368cd00d778d026d1afaf9d025be71`; compatible recovery
  archive remained `a0a06cf0c90974bbacc2ee2dcd3e28cca3d74087818372b9645a702f26f05751`; staging v4 target remains
  absent. No real server was selected or provisioned, and no C4 migration, canary, v4 writer,
  persistent financial mutation, or PERSONAL work occurred. Final state: **SERVER DEPLOYMENT
  FOUNDATION PREPARED — C4 NOT EXECUTED**.

## 2026-09-30 — M5.2-UI0 Chatbooks product shell and UX foundation

- Implemented the chat-first responsive product shell with the canonical Chat, Money, Activity,
  Reports, Projects, and Settings navigation; added an accessible mobile More sheet, keyboard tabs,
  stronger modal focus/Escape behavior, and progressive BUSINESS accounting setup.
- Added the non-executing Chat workspace and proposal-review architecture, ledger-backed BUSINESS
  Money/Activity presentation, Settings, and explicit PERSONAL fail-closed states. Projects remains
  BUSINESS-only; no personal persistence/API/ledger, AI call, attachment upload, migration, C4 work,
  invented financial value, or alternate financial write path was added.
- Created `docs/M5_2_UI0_CHATBOOKS_PRODUCT_SHELL_REPORT.md` and seven focused UI0 tests. Final
  verification passed: frontend 17/17, TypeScript, ESLint, Prettier, Next.js production build,
  existing backend API 9/9, source-boundary and fabricated-value scans, 71 Markdown files with 253
  local links and zero broken, and rendered desktop/mobile inspection at 390 × 844 without horizontal
  overflow. Development `chatbook.db` remained SHA-256
  `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`.
- Manual inspection used an isolated disposable schema-v3 database and recorded a pre-existing
  Python 3.14/FastAPI SQLite worker-thread risk; no backend code was changed. Final state:
  **Chatbooks product shell implemented; financial/personal capabilities remain behind their
  existing milestones.**

## 2026-09-30 — M5.2-UI0.1 Python 3.14 SQLite runtime hardening

- Traced the runtime defect to FastAPI/AnyIO scheduling the enter, use, and exit stages of one
  synchronous request dependency on different worker threads. Added an internal, default-off
  sequential thread-handoff option and enabled it only for fresh request-owned engine/auth
  connections; direct, CLI, migration, backup, monitoring, rehearsal, and cutover connections keep
  SQLite's creator-thread guard.
- Fixed both `chatbook-api` startup paths at one Uvicorn worker and documented the supported
  single-process SQLite topology. Accounting services, `BEGIN IMMEDIATE`, idempotency, audit,
  authorization, schema, and public BUSINESS API behavior remain unchanged.
- Added seven deterministic connection/concurrency tests covering three-thread lifecycle handoff,
  strict non-API ownership, distinct request connections and cleanup, concurrent reads/posting,
  idempotent retry, organization isolation, and runtime worker policy. Verification passed: focused
  module 7/7 across five consecutive runs; complete backend 112/112; C3/C4A/C4P2/C4P5/C4P7 26/26;
  mypy; Ruff lint/format; frontend 17/17, TypeScript, ESLint, Prettier, and production build.
- Normal Python 3.14 runtime inspection passed for Chat, Money, Activity, Reports, Settings,
  BUSINESS context, and PERSONAL deferred context; four concurrent pages and 120 authenticated API
  reads completed without SQLite thread errors or console errors. Documentation checks covered 72
  Markdown files and 254 local links with zero broken.
- The isolated verification database remained schema v3 with integrity `ok`, zero foreign-key
  violations, zero journal entries, and no personal tables. Development `chatbook.db` remained
  SHA-256 `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`.
  No PERSONAL data, AI, schema migration, v4 target, C4 execution, or accounting-rule change
  occurred. Final state: **SQLite runtime concurrency issue remediated; Chatbooks UI0 remains
  intact.**

## 2026-10-02 — M5.2-UI1 Chatbooks Business Money experience

- Implemented the API-backed BUSINESS Money workspace with Overview, Accounts, Income, Spending,
  and truthful deferred Transfers views; added reusable report date controls, loaded-page account
  filters, API pagination, loading/error/empty states, and responsive mobile layouts.
- Added account detail routing with trial-balance amounts and progressive accounting disclosure;
  clarified the existing proposal lifecycle as Draft → Validate → Review → Confirm → Post without
  changing confirmation, posting, role, idempotency, or accounting boundaries.
- Added eight focused UI1 tests and `docs/M5_2_UI1_BUSINESS_MONEY_EXPERIENCE_REPORT.md`. Verification
  passed: frontend 25/25, TypeScript, ESLint, Prettier, Next.js production build, complete backend
  112/112, 73 Markdown files with 254 local links and zero broken, and source-boundary scans with no
  frontend storage authority, PERSONAL API, raw book identifier, financial aggregation, or
  hard-coded runtime money values.
- Rendered verification passed on desktop and at 390 × 844 mobile with no document-level horizontal
  overflow. A disposable schema-v3 BUSINESS database supplied validated API values; 48 concurrent
  reads returned HTTP 200 with no browser or SQLite runtime errors. Temporary artifacts and servers
  were removed. Development `chatbook.db` remained SHA-256
  `d28f7434df6f6954d42c8c0a607b9be41bb4a7d61dc20d5b8fa7dabf8071c884`.
- No PERSONAL persistence/data, AI, budget, reminder, accounting-rule change, C4 execution,
  migration, v4 database, or deployment was introduced. Final state: **Chatbooks Business Money
  experience implemented using existing BUSINESS financial APIs; PERSONAL, AI, C4, and deferred
  capabilities remain untouched.**

## 2026-10-03 — Development runtime started

- Started the normal local `chatbook-api` process against the existing development database on
  `127.0.0.1:8000` and the Next.js development frontend on `127.0.0.1:3001`.
- Verified `/api/v1/health` returned `status: ok` and `/login` returned HTTP 200 with the Chatbooks
  shell. Both processes were left running for local development; no code, schema, accounting data,
  migration, PERSONAL capability, C4 control, or deployment configuration was changed.

## 2026-10-03 — Frontend blank-page runtime check

- Confirmed the FastAPI service on port 8000 and the Next.js frontend on port 3001 were healthy.
- Traced the blank `/chat` view to opening the development server through `127.0.0.1`, which Next.js reported as a blocked development origin; the unauthenticated route was also waiting on its session check.
- Opened and visibly verified the supported frontend URL at `http://localhost:3001/login`; the Chatbooks sign-in screen rendered successfully.
- No source code, database, schema, financial data, accounting behavior, or C4 state was changed.

## 2026-10-03 — Illustrated Chatbooks UI direction

- Added an original Chatbooks money companion and companion mark, with a playful illustrated visual system inspired by friendly learning products without copying another product's character, branding, or layout.
- Redesigned registration/login, the application shell, navigation, shared controls, and the chat landing experience with brighter color, tactile states, progressive disclosure, and responsive artwork.
- Added the `127.0.0.1` development origin so the supported local frontend no longer blanks when opened through that host.
- Preserved existing BUSINESS APIs, authorization, proposal review, accounting boundaries, and financial data behavior; introduced no storage access, financial arithmetic, API contract, schema, or database change.
- Verification: 25/25 frontend tests passed; TypeScript, ESLint, Prettier, and the Next.js production build passed; desktop and 375 px rendered checks passed with no horizontal overflow or browser warnings/errors; source-boundary scan passed.

## 2026-10-03 — Development runtime verification

- Investigated the report that Chatbooks was not running.
- Confirmed the FastAPI health endpoint and Next.js `/chat` route both returned HTTP 200, and both development processes remained active.
- Refreshed the visible in-app browser tab and verified the redesigned Chatbooks chat screen rendered successfully.
- Clarified that the chat assistant remains an intentionally non-executing UI shell with AI actions unavailable; no code, financial data, accounting behavior, or database state was changed.

## 2026-10-03 — Unified Chatbooks naming

- Made **Chatbooks** the single written name for the project, repository, product, application UI,
  API, documentation, ADRs, reports, tests, and package metadata. Removed all `ChatAccount`,
  `ChatAccounts`, and singular written `Chatbook` brand references from maintained source files.
- Renamed `docs/M5_2_UI0_CHATACCOUNTS_PRODUCT_SHELL_REPORT.md` to
  `docs/M5_2_UI0_CHATBOOKS_PRODUCT_SHELL_REPORT.md` and updated every local reference.
- Retained lowercase `chatbook`, `CHATBOOK_*`, package imports, CLI commands, routes, database
  filenames, and internal compatibility identifiers so the naming change does not break runtime,
  migration, or stored-data contracts.
- Verification passed: repository naming scan across 79 branded files; 112 backend tests; strict
  Mypy; Ruff lint and formatting; 25 frontend tests; TypeScript; ESLint; Prettier; Next.js production
  build; 254 local links across 73 Markdown files; rendered login-page inspection; and live API
  health/OpenAPI title checks. The local development API was restarted and reports `Chatbooks API`.
- No accounting rules, schema, financial records, migration state, PERSONAL capability, AI behavior,
  or C4 controls changed.

## 2026-10-03 — Development services started

- Started the FastAPI backend on `http://127.0.0.1:8000` and the Next.js development frontend on
  `http://localhost:3001` and left both processes running.
- Verified the API health endpoint returned `status: ok`, OpenAPI identified the service as
  `Chatbooks API`, and the frontend login route returned HTTP 200 with Chatbooks branding.
- No source code, schema, accounting data, migration state, or product behavior changed.
