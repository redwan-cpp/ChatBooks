# Chatbooks

**Chatbooks** is the single canonical name for the engineering project, repository, and
customer-facing conversational financial operating system for individuals and project-based businesses. The
repository currently implements the hardened organization-scoped accounting foundation, the M3
FastAPI application layer, and the M4 Chatbooks web experience. The M3.5 product model documents
the broader personal/business experience, and M5.0 specifies the future personal-finance ownership,
isolation, and ledger integration model. M5.1-A selects the universal financial-core architecture,
persistent ledger-book seam, compatibility strategy, and jurisdiction boundary. Those designs are
documentation only. M5.1-B adds the reviewed incremental implementation and migration runbooks.
M5.1-C1 implements their first two phases: read-only migration evidence and an additive schema-v3
BUSINESS LedgerBook mapping. M5.1-C2 extracts the ownership-neutral deterministic financial service
over that unchanged organization-scoped storage and turns `AccountingEngine` into the compatible
BUSINESS facade. M5.1-C3 implements canonical schema-v4 book-scoped persistence, audit sidecars,
business extensions, and exact v3→v4 reconciliation on disposable copies. M5.1-C4A adds
synthetic-only operational rehearsal, recovery drills, measured capacity evidence, and the future C4
operator/checklist package. M5.1-C4P2 adds normal server-controlled schema-v3/schema-v4 runtime
selection and read-only v4 acceptance while keeping v4 disabled. C4P4 packages the candidate
operational evidence and blank approval controls. C4P5 adds a server-owned local maintenance/drain
gate and deterministic read-only operational collector for the current direct-local topology. It
records that C4 remains **NOT READY FOR FINAL PREFLIGHT**. C4P7 records the operator’s D01=B
decision, makes that Windows environment staging only, and adds a provider-neutral SaaS server
deployment foundation with exactly one authoritative SQLite writer. No actual server or replacement
source has been selected or provisioned. The C4 cutover and personal capabilities do not exist yet.

The posted double-entry ledger is the source of actual financial truth. Accounting writes pass
through the deterministic engine, exact-version confirmation, and audit boundary. The Next.js
frontend uses the API exclusively and keeps accounting detail progressively available. There is no
personal-finance persistence, general budget or reminder domain, AI integration, extraction pipeline,
or cloud deployment in the current code.

Use **Chatbooks** in prose for both the project and the product. Lowercase `chatbook` remains the
stable technical identifier for the Python package, CLI command, internal modules,
environment-variable prefix, and database/internal identifiers where applicable. Those identifiers
do not represent a second product name.

## Product direction and current capability

The intended experience starts with conversation and an explicit Personal/Business context. Plain
language leads; accounting and audit detail appears progressively. The implemented API serves the
business context through organizations, projects, accounts, proposals, posting, reversal, reports,
and audit. It must not be presented as supporting personal finance, budgets, reminders, or natural
language until those milestones are built.

Read the [Chatbooks Product Model](docs/product-model.md),
[M3.5 product-model report](M3_5_PRODUCT_MODEL_REPORT.md), and
[M4 implementation report](docs/M4_IMPLEMENTATION_REPORT.md) for the product and UX boundaries. The
[M5.0 personal-finance model](docs/personal-finance-model.md),
[decision register](docs/M5_PERSONAL_FINANCE_DECISIONS.md), and
[M5.0 report](docs/M5_0_PERSONAL_FINANCE_SPEC_REPORT.md) define the next domain boundary without
claiming personal-finance support. The
[universal financial-core architecture](docs/universal-financial-core.md) and
[M5.1-A report](docs/M5_1A_UNIVERSAL_CORE_ARCHITECTURE_REPORT.md) define the shared future core and
staged migration without changing the running system. The
[M5.1-B implementation plan](docs/M5_1B_IMPLEMENTATION_PLAN.md) and
[migration runbook](docs/M5_1B_MIGRATION_PLAN.md) define the business-preserving coding sequence,
evidence gates, and recovery boundary. The
[M5.1-C1 implementation report](docs/M5_1_C1_IMPLEMENTATION_REPORT.md) records the implemented
preflight, backup/restore, v3 mapping, compatibility evidence, and remaining stop boundary. The
[M5.1-C2 implementation report](docs/M5_1_C2_IMPLEMENTATION_REPORT.md) records the authorized
context, service/repository extraction, and business-facade compatibility evidence. The
[M5.1-C3 implementation report](docs/M5_1_C3_IMPLEMENTATION_REPORT.md) records the disposable-copy
v4 reconstruction, migration/rollback evidence, book repository, audit sidecar, attacks,
concurrency, performance, and C4 stop boundary.
The [M5.1-C4A readiness report](docs/M5_1_C4A_READINESS_REPORT.md),
[cutover runbook](docs/M5_1_C4_CUTOVER_RUNBOOK.md), and
[release checklist](docs/M5_1_C4_RELEASE_CHECKLIST.md) record the synthetic operational rehearsal
and the blockers that must close before C4 authorization. The
[C4P2 runtime selection report](docs/M5_1_C4P_RUNTIME_SELECTION_REPORT.md) records the server-only
normal schema-v4 selector, read-only acceptance mode, hardened staging controls, and remaining
deployment and human gates without executing C4. The
[C4P4 operational readiness report](docs/M5_1_C4P4_OPERATIONAL_READINESS_REPORT.md) packages the
candidate and blank operator controls. The
[C4P5 traffic/monitoring report](docs/M5_1_C4P5_TRAFFIC_MONITORING_REPORT.md) records the current
engineering controls, staging evidence, and remaining operator actions. The
[C4P7 SaaS deployment foundation](docs/M5_1_C4P7_SAAS_DEPLOYMENT_FOUNDATION.md) and
[report](docs/M5_1_C4P7_SAAS_DEPLOYMENT_REPORT.md) define the future single-server deployment
contract without selecting a provider or executing C4. The
[approval matrix](docs/M5_1_C4_APPROVAL_MATRIX.md) keeps all human decisions blank until named
owners sign them.

## Run locally

Requires Python 3.12+ with SQLite 3.37+ and SQLite JSON functions. Install locked dependencies with
`uv sync --locked --extra dev`.

```powershell
python -m chatbook --help
chatbook-api
chatbook-migration-evidence --help
chatbook-canonical-rehearsal --help
chatbook-c4a-rehearsal --help
chatbook-saas-deployment --help
python -m unittest discover -v
```

The C3 migration command is for closed, disposable schema-v3 copies only:

```powershell
chatbook-canonical-rehearsal SOURCE.db TARGET-v4.db VERIFIED-BACKUP.db
```

All three paths must differ and the target must not exist. The tool writes sanitized evidence to
`TARGET-v4.db.c3-report.json`. Normal API and CLI startup use server-controlled runtime
configuration. Schema v4 requires an existing exact target, immutable release identity, and explicit
access mode; the reviewed C4P control permits read-only v4 acceptance only. V4 remains disabled and
no target exists before an authorized C4 migration.

The C4A command accepts only a new output directory. It constructs its own synthetic source and
cannot be pointed at an existing database:

```powershell
chatbook-c4a-rehearsal .test-tmp/c4a-rehearsal
```

It exercises writer exclusion, verified backup/restore, v4 reconstruction, exact business parity,
a disposable canary, and recovery drills. Its timings are local synthetic evidence, not production
performance or permission to run C4.

The API listens on `127.0.0.1:8000` by default. Set `CHATBOOK_DB_PATH`, `CHATBOOK_HOST`, and
`CHATBOOK_PORT` for local operation. OpenAPI is available at `/docs`. The CLI remains a trusted local
tool whose actor IDs are not credentials. Read [security.md](docs/security.md) before deployment or
using real financial data. While SQLite is authoritative, `chatbook-api` runs exactly one Uvicorn
worker and deployments must run exactly one non-overlapping backend process. Concurrent requests are
supported with separate request-owned connections; horizontal or multiprocess SQLite writers are
not.

Opening a file-backed schema-v2 database with the current application acquires SQLite's writer lock,
creates a consistent `.pre-v3.backup`, restores and verifies it, runs the fail-closed preflight, and
then atomically adds the BUSINESS book mapping. The standalone
`chatbook-migration-evidence SOURCE BACKUP` command creates the same protected local evidence without
migrating the source. Treat backup and manifest files as sensitive financial data.

Run the customer-facing web application in a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

The browser application listens on `127.0.0.1:3000` by default. Its same-origin Chatbooks proxy sends
requests to `CHATBOOK_API_URL` (default `http://127.0.0.1:8000/api/v1`) and retains the opaque API
token in an HTTP-only cookie. Browser JavaScript never receives the bearer token.

For development checks, install the locked tools with `uv sync --extra dev --locked`, then run:

```powershell
uv run --locked --extra dev mypy
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev python -m unittest discover -v
```

## Manual acceptance workflow

The following PowerShell session starts a local database, manually creates a proposal, reviews it,
validates it, explicitly confirms it, posts it, checks reports, and creates a separate reversal.
All amounts are **integer minor units**: with precision 2, `12500` means `125.00 BDT`.
Account classifications here are sample inputs chosen by the operator, not automatic classification.

```powershell
$chatbookDb = 'demo.db'
$actor = (python -m chatbook --db $chatbookDb user-create --name 'Owner' | ConvertFrom-Json).user_id
$org = (python -m chatbook --db $chatbookDb --actor $actor org-create --name 'My Studio' --currency BDT --minor-unit-digits 2 | ConvertFrom-Json).organization_id
$base = @('-m', 'chatbook', '--db', $chatbookDb, '--actor', $actor, '--org', $org)

$bank = (python @base account-create --code 1000 --name Bank --type asset | ConvertFrom-Json).account_id
$sales = (python @base account-create --code 4000 --name 'Service revenue' --type revenue | ConvertFrom-Json).account_id
python @base period-create --name September --start 2026-09-01 --end 2026-09-30
$project = (python @base project-create --name 'Client website' --client 'Example client' --budget 50000 --expected-revenue 100000 | ConvertFrom-Json).project_id

@{
    entry_date = '2026-09-25'
    description = 'Client payment for completed work'
    lines = @(
        @{ account_id = $bank; debit = 12500; project_id = $project }
        @{ account_id = $sales; credit = 12500; project_id = $project }
    )
} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 proposal.json

$transaction = (python @base create --file proposal.json | ConvertFrom-Json).transaction_id
python @base show --transaction $transaction
$validation = (python @base validate --transaction $transaction | ConvertFrom-Json).id

# Displays the proposal and requires typing CONFIRM followed by its transaction ID.
$confirmation = (python @base confirm --validation $validation | ConvertFrom-Json).id
$entry = (python @base post --confirmation $confirmation | ConvertFrom-Json).entry_id

python @base ledger
python @base balance --account $bank
python @base trial-balance
python @base income-statement --start 2026-09-01 --end 2026-09-30
python @base balance-sheet --as-of 2026-09-30

$reversal = (python @base reverse --entry $entry --date 2026-09-26 --reason 'Entered twice' | ConvertFrom-Json).transaction_id
$validation = (python @base validate --transaction $reversal | ConvertFrom-Json).id
$confirmation = (python @base confirm --validation $validation | ConvertFrom-Json).id
python @base post --confirmation $confirmation

python @base ledger
python @base trial-balance
python @base audit
```

Expected: the first posting creates two ledger lines and a bank debit balance of 12500. The
reversal adds two more lines and returns balances to zero. Both journal entries and their
proposal, validation, confirmation, posting, and reversal links remain inspectable. A report
with `--as-of 2026-09-25` still includes only the original entry.

`confirm --accept` is an explicit noninteractive confirmation for an operator who already
reviewed the proposal. `create`, `validate`, and `reverse` never post automatically. Repeating
`post` with the same confirmation returns the existing entry without duplicate ledger or audit rows.

Use `catalog` to retrieve account, period, project, and document IDs. Each command also has `--help`.
The Python application interface is `chatbook.AccountingEngine`; every organization operation
requires the trusted actor ID and organization ID. Expected errors have stable `ChatbookError.code`
values; the CLI returns JSON errors on stderr and exit code 2.

## Documentation

- [Chatbooks product model and UX principles](docs/product-model.md)
- [M3.5 domain-expansion and readiness report](M3_5_PRODUCT_MODEL_REPORT.md)
- [M4 financial UX implementation report](docs/M4_IMPLEMENTATION_REPORT.md)
- [M5.0 personal-finance domain specification](docs/personal-finance-model.md)
- [M5.0 engineering and human/accountant decisions](docs/M5_PERSONAL_FINANCE_DECISIONS.md)
- [M5.0 specification report](docs/M5_0_PERSONAL_FINANCE_SPEC_REPORT.md)
- [M5.1-A universal financial-core architecture](docs/universal-financial-core.md)
- [M5.1-A architecture report](docs/M5_1A_UNIVERSAL_CORE_ARCHITECTURE_REPORT.md)
- [M5.1-B universal-core implementation plan](docs/M5_1B_IMPLEMENTATION_PLAN.md)
- [M5.1-B migration and recovery plan](docs/M5_1B_MIGRATION_PLAN.md)
- [M5.1-C1 implementation report](docs/M5_1_C1_IMPLEMENTATION_REPORT.md)
- [M5.1-C2 implementation report](docs/M5_1_C2_IMPLEMENTATION_REPORT.md)
- [M5.1-C3 implementation report](docs/M5_1_C3_IMPLEMENTATION_REPORT.md)
- [M5.1-C4A readiness report](docs/M5_1_C4A_READINESS_REPORT.md)
- [M5.1-C4 controlled-cutover runbook](docs/M5_1_C4_CUTOVER_RUNBOOK.md)
- [M5.1-C4 release checklist](docs/M5_1_C4_RELEASE_CHECKLIST.md)
- [M5.1-C4P2 runtime selection report](docs/M5_1_C4P_RUNTIME_SELECTION_REPORT.md)
- [M5.1-C4P3 final readiness report](docs/M5_1_C4P3_FINAL_READINESS_REPORT.md)
- [M5.1-C4P4 operational readiness report](docs/M5_1_C4P4_OPERATIONAL_READINESS_REPORT.md)
- [M5.1-C4 approval matrix](docs/M5_1_C4_APPROVAL_MATRIX.md)
- [Architecture and module boundaries](docs/architecture.md)
- [Accounting model, invariants, and unresolved rules](docs/accounting-model.md)
- [Future AI boundary](docs/ai-behavior.md)
- [Security and trust limits](docs/security.md)
- [Roadmap and milestone acceptance](docs/roadmap.md)
- [Architectural decisions](docs/decisions/README.md)
- [Accounting-core hardening report](HARDENING_REPORT.md)
