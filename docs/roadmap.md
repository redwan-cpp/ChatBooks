# Chatbooks product roadmap

This roadmap separates shipped capability from planned work. Planned items are not claims about the
current product.

## Available foundation

### Accounting and audit

The deterministic accounting kernel supports exact integer money, balanced double-entry posting,
immutable journal history, audited reversals, period locking, ledger-derived balances and reports,
idempotency, and atomic SQLite transactions.

### API, identity, and organization access

FastAPI provides authenticated sessions, organization membership and roles, tenant isolation,
typed proposal workflows, exact-version confirmation, posting, reversal, reporting, and audit
access. Client-provided actor IDs are not trusted as authentication.

### Customer application

The Next.js application provides responsive Chat, Money, Activity, Projects, Reports, and Settings
areas. The current financial experience is backed by BUSINESS APIs. Personal context is visible but
does not claim unsupported persistence or financial operations.

### Universal financial service foundation

Business accounting operations use one deterministic financial service behind the compatible
business facade. The repository includes an additive business ledger-book mapping, canonical
book-scoped schema rehearsal, reconciliation evidence, and single-writer deployment controls.
Normal runtime remains on the approved business storage path until a separately authorized cutover.

## Planned product work

### Personal finance

Add private personal ownership, presentation accounts, category mappings, same-space transfers,
opening-balance provenance, approved liability behavior, and ledger-derived personal reports. Keep
personal and business ownership strictly isolated and reuse the deterministic ledger through a typed
adapter. Cross-space transfers, investments, valuation, household sharing, multi-currency, tax, and
compliance remain outside the initial scope.

### Business and project experience

Extend the organization and project experience with ledger-derived project actuals, clearer business
activity, permission-aware workflows, and progressively disclosed accounting detail.

### Budgets and financial reminders

Add separate budget and financially scoped reminder domains. Actuals remain ledger-derived.
Reminder completion must remain distinct from payment or posting. Recurrence, time-zone, rollover,
mapping, and enforcement policies require explicit decisions before implementation.

### Documents

Add secure upload, storage, provenance, retention, and evidence workflows. Extracted content remains
untrusted input and cannot post financial records directly.

### Conversational financial assistance

Introduce structured intent understanding, clarification, explanation, and proposal creation through
the existing authenticated application boundary. AI must never write the ledger, confirm a proposal
for the user, or mix generated values with authoritative financial calculations.

### Analysis and accountant workspace

Add source-linked financial explanations, accountant review workflows, advanced reports, approval
controls, and export capabilities while preserving organization isolation and audit history.

### Integrations and automation

Add bank and payment imports, notifications, and approved recurring workflows through idempotent,
audited connectors. Imported data creates reviewable proposals and does not bypass validation or
confirmation.

### Production readiness

Complete provider selection, deployment evidence, backup and restore operations, monitoring
baselines, incident ownership, retention controls, and human approvals. SQLite remains a
single-writer deployment until a separately reviewed storage redesign is authorized.

## Permanent product constraints

- The posted ledger remains the source of financial truth.
- Financial writes pass through deterministic validation and explicit confirmation.
- Posted entries are corrected through reversals, never deletion.
- Personal and business data remain separately owned and authorized.
- Reports and financial actuals are derived from posted ledger data.
- AI and document extraction cannot directly mutate financial state.
