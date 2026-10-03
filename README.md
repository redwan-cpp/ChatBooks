# Chatbooks

Chatbooks is a conversational financial operating system for individuals and project-based
businesses. The current application provides a customer-facing Next.js experience backed by a
FastAPI service, a deterministic double-entry accounting engine, and SQLite persistence.

The product is designed to make financial work understandable without hiding correctness. Users
work with familiar concepts such as Money, Activity, Projects, and Reports, while the accounting
kernel enforces balanced entries, explicit confirmation, immutable posted history, audited
reversals, period locks, authorization, and organization isolation.

## Current capabilities

- Secure registration, login, opaque sessions, and role-based permissions.
- Organization-scoped projects, accounts, periods, proposals, and journal entries.
- Proposal review, deterministic validation, explicit confirmation, and idempotent posting.
- Reversals that create compensating entries without deleting financial history.
- Ledger-derived balances, trial balance, income statement, balance sheet, cash flow, and general
  ledger reports.
- Append-only financial audit history.
- Responsive Chat, Money, Activity, Projects, Reports, and Settings experiences.
- Controlled single-writer SQLite runtime, maintenance controls, monitoring, and deployment
  contracts.

Personal finance ownership, automated transaction understanding, document extraction, budgets,
reminders, bank integrations, and cloud deployment are not active capabilities in the current
runtime.

## Financial safety boundary

The posted ledger is the source of financial truth. Every financial write passes through the
deterministic application and accounting services. Clients cannot write journal rows, audit events,
or balances directly.

Posting requires:

1. an immutable proposal;
2. deterministic validation;
3. confirmation of the exact proposal version by an authenticated actor; and
4. an atomic database transaction.

All monetary amounts use integer minor units. Floating-point arithmetic is not used for financial
values. Posted entries cannot be edited or deleted, and corrections use audited reversal entries.

## Repository layout

```text
chatbook/       FastAPI service, domain model, accounting engine, persistence, and CLI
frontend/       Next.js customer application
tests/          Backend, API, accounting, migration, concurrency, and deployment tests
docs/           Product, architecture, accounting, security, design, and ADR documentation
deploy/saas/    Provider-neutral deployment contracts and examples
```

## Run the backend

Requirements: Python 3.12+, SQLite 3.37+ with JSON functions, and
[uv](https://docs.astral.sh/uv/).

```powershell
uv sync --locked --extra dev
uv run chatbook-api
```

The API listens on `http://127.0.0.1:8000` by default. OpenAPI documentation is available at
`http://127.0.0.1:8000/docs`.

Environment variables:

- `CHATBOOK_DB_PATH` selects the SQLite database.
- `CHATBOOK_HOST` selects the API bind address.
- `CHATBOOK_PORT` selects the API port.

While SQLite is authoritative, run exactly one backend process. Concurrent requests are supported
through request-owned connections, but multiprocess or multi-instance writers are not supported.

## Run the frontend

Requirements: Node.js and npm.

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

The browser application uses a same-origin Next.js proxy. Authentication tokens stay in HTTP-only
cookies and are not exposed to browser JavaScript. The proxy calls the FastAPI endpoint configured
by `CHATBOOK_API_URL`.

## Command-line interface

```powershell
uv run chatbook --help
```

The CLI supports manual organization, account, period, project, proposal, posting, reporting,
reversal, and audit workflows. Actor IDs accepted by the trusted local CLI are not API credentials.

## Verification

Backend checks:

```powershell
uv run --locked --extra dev python -m unittest discover -v
uv run --locked --extra dev mypy
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
```

Frontend checks:

```powershell
cd frontend
npm test
npm run typecheck
npm run lint
npm run format:check
npm run build
```

Tests use disposable databases. Local databases, backups, environment files, dependency folders,
build output, generated media, and internal development notes are excluded from version control.

## Documentation

- [Product model and UX principles](docs/product-model.md)
- [Product requirements](requirement.md)
- [Application design](design.md)
- [Architecture and module boundaries](docs/architecture.md)
- [Accounting model and invariants](docs/accounting-model.md)
- [Personal finance domain model](docs/personal-finance-model.md)
- [Universal financial core](docs/universal-financial-core.md)
- [Security model](docs/security.md)
- [AI boundary](docs/ai-behavior.md)
- [Architectural decisions](docs/decisions/README.md)
- [SaaS deployment package](deploy/saas/README.md)
