# M4 Financial UX Foundation implementation report

**Date:** 2026-09-26  
**Status:** Complete

## Outcome

M4 adds the first real Chatbooks web application over the existing Chatbooks API and accounting
kernel. A user can register or sign in, create a business context, navigate a chat-first product
shell, work with projects and accounting setup, create and review a transaction proposal, validate,
confirm, post, inspect, and reverse it, read ledger-derived reports, and inspect immutable audit
history.

The frontend never opens SQLite, receives the private database connection, posts directly to the
ledger, or calculates report totals. FastAPI authorization and the deterministic engine remain the
exclusive financial write and calculation boundaries. No database schema change was needed.

## Pages and routes

| Route                           | Implemented behavior                                                                                                             |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `/login`, `/register`           | Credentials, authenticated session establishment, validation, and designed failure/loading states                                |
| `/chat`                         | Default entry point, current financial context, supported action paths, and an honest no-AI composer shell                       |
| `/money`                        | Paginated posted activity, page-scoped filters, engine-returned account balances, account setup, and period setup/locking        |
| `/money/[entryId]`              | Plain-language entry detail with expandable journal lines, provenance, authorized audit evidence, and reversal-proposal creation |
| `/money/proposals/new`          | Structured proposal creation with exact minor-unit conversion and optional project context                                       |
| `/money/proposals/[proposalId]` | Deterministic validation, exact-version review, explicit confirmation, idempotent posting, and posted-entry link                 |
| `/projects`                     | Paginated business project list with plan values clearly labeled                                                                 |
| `/projects/new`                 | Authorized project creation                                                                                                      |
| `/projects/[projectId]`         | Project context, plan metadata, project-tagged ledger balances and activity, and unsupported-classification disclosure           |
| `/projects/[projectId]/edit`    | Authorized project planning-metadata updates                                                                                     |
| `/reports`                      | Income statement, balance sheet, explicitly scoped cash movements, trial balance, and paginated general ledger                   |
| `/activity`                     | Authorized read-only audit timeline with actor, timestamp, entity, metadata, and before/after evidence                           |

The shell uses a desktop sidebar, tablet/mobile header and bottom navigation, visible active states,
profile/logout access, and the compact Chat, Money, Projects, Reports, and Activity information
architecture. Projects is hidden in Personal context.

## Components and product features

- Strict typed API client and shared response contracts.
- Same-origin Next.js API proxy with structured upstream errors and request/idempotency header
  forwarding.
- Authentication provider, protected route, login/register experience, and logout.
- Tagged frontend financial context: `personal` or `business + organization ID`.
- Honest Personal deferred state with no organization substitution, balances, activity, or reports.
- Reusable loading, retryable error, empty, notice, field, badge, button, and accessible dialog
  components.
- Money activity, transaction detail, account setup, period setup, proposal form, and proposal
  lifecycle components.
- Project list, form, and plan-versus-ledger detail components.
- Report presentation and explicit cash-account selection.
- Plain-language audit activity with complete expandable raw evidence.
- Responsive visual system with visible focus, semantic controls, reduced-motion support, and
  mobile-specific layout rather than a scaled desktop view.

## API integration

The frontend integrates the M3 authentication, organization, project, account, period, proposal,
validation, confirmation, posting, reversal, report, and audit endpoints. It adds one API read model:

`GET /api/v1/organizations/{organization_id}/journal-entries`

The accounting engine returns posted-entry summaries with deterministic debit/credit totals, line
count, and project IDs. This supports plain-language transaction lists without reconstructing totals
in React. The route is organization scoped, membership protected, read-only, and covered by the API
posting/idempotency test. Entry detail uses the same engine-derived fields.

## Authentication and authorization

The browser calls only `/api/chatbook`. The Next.js proxy sends credentials to FastAPI, removes the
opaque bearer token from the browser-visible login response, and stores it in an HTTP-only,
SameSite=Lax cookie with Secure enabled in production. It clears the cookie on logout and rejected
sessions.

FastAPI still authenticates the actor and authorizes every organization operation. Frontend role
checks improve the experience by hiding or explaining unavailable controls; they cannot grant
permission. Proposal confirmation remains bound to the displayed proposal version and authenticated
actor. Confirmation and posting use distinct caller idempotency keys. Reversal creates a proposal and
follows the same validate/confirm/post path; it never edits or deletes the original entry.

## Financial context model

M4 implements the M3.5 tagged context decision in the UI without migrating the ledger. A business
context resolves to an existing organization. Personal is a distinct context kind with an explicit
future-capability state. It does not create a fake organization or issue personal financial API
requests. The selected UI context is retained locally as a non-sensitive preference; financial data
and authority remain server scoped.

## Tests added

Ten focused frontend tests cover:

- anonymous protected-route redirect and authenticated access;
- business context loading and Personal switching;
- the Personal deferred state;
- project list, project detail, and plan/actual separation;
- posted transaction rendering from engine-returned values;
- report and audit rendering;
- viewer permission controls;
- exact-version proposal review and confirmation;
- accessible loading, error/retry, and empty states.

The existing API integration test now also verifies that an idempotent posting produces one journal
summary and that summary/detail totals and line count come from the engine.

## Verification results

| Check                               | Result                                                                                                                                                                                 |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend unit/component tests       | Passed: 10 tests                                                                                                                                                                       |
| Strict TypeScript                   | Passed                                                                                                                                                                                 |
| ESLint / Next core web vitals       | Passed                                                                                                                                                                                 |
| Prettier formatting check           | Passed                                                                                                                                                                                 |
| Next.js production build            | Passed; all application and proxy routes generated                                                                                                                                     |
| Python mypy configured target       | Passed: 11 source files                                                                                                                                                                |
| Ruff lint                           | Passed                                                                                                                                                                                 |
| Ruff formatting check               | Passed: 47 files                                                                                                                                                                       |
| Complete Python suite               | Passed: 56 tests                                                                                                                                                                       |
| Local Next.js → FastAPI integration | Passed register, login, HTTP-only token handling, organization/project setup, proposal, validation, confirmation, idempotent post retry, journal summary, reports, reversal, and audit |
| Browser desktop verification        | Passed authenticated shell, Money, Projects, project detail, Reports, and Activity                                                                                                     |
| Browser mobile verification         | Passed 390 × 844 layout, bottom navigation, no horizontal overflow, readable Money activity, and non-overlapping composer/navigation                                                   |
| Personal-context verification       | Passed deferred state, no displayed financial amounts, and no Projects destination                                                                                                     |
| Direct database/frontend scan       | No SQLite client, database path, or direct database access in frontend source                                                                                                          |
| Fake financial data scan            | No shipped fake balances, transactions, reports, or AI responses; sample values exist only in tests and temporary local verification data                                              |

The local integration exercise also proved that the browser-visible token response contains no
`access_token`, an authenticated retry returns the original entry ID, the trial balance remains
balanced before and after reversal, the original and reversal are both retained, and financial
mutations produce audit events.

## Visual and interaction decisions

The visual direction uses an ivory canvas, deep mineral/navy navigation, restrained green and coral
signals, editorial typography, thin borders, limited shadow, and compact radii. It avoids gradients,
glass effects, decorative AI language, chart-heavy dashboard composition, and oversized card grids.
Familiarity comes from the message composer, prompt paths, chronological activity, and compact
navigation; the product mark, layout, palette, financial surfaces, and copy are original to
Chatbooks.

Plain language leads each surface. Account sides, journal lines, proposal provenance, actor IDs, and
audit snapshots appear progressively when requested. Planning values remain visibly separate from
ledger-derived values.

## Deferred capabilities and known limitations

- The chat composer has no model, message persistence, tool execution, or upload. It clearly reports
  that no action occurred.
- Personal finance has no persistence, accounts, transactions, reports, budgets, reminders, or fake
  data.
- Project budget and expected revenue are planning metadata. Actual spend, collected revenue, and
  remaining budget are not shown because approved account/category mappings do not yet exist.
- Cash movements require the user to select active asset accounts and remain unclassified; operating,
  investing, and financing policy is unresolved.
- Budgets, reminders, recurring transactions, documents/extraction, AI, bank/payment integration,
  billing, tax, and production infrastructure remain out of scope.
- Organization membership administration, account recovery, MFA, login throttling, and production
  session/CSRF/TLS hardening remain later security work.
- The current SQLite deployment remains single-host. The frontend/API boundary is production shaped,
  but this milestone is not a production deployment profile.

## Before M5

M5 must resolve the personal ownership, privacy/sharing, personal account/category, transfer,
opening-balance, period, liability, and personal/business cross-boundary policies documented in the
product and accounting models. Personal data must receive explicit server-side isolation and cannot
be implemented by treating a person as a business organization. M4 is ready as the frontend
foundation for that approved domain work; it does not itself claim personal financial capability.
