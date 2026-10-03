# M5.2-UI1 — Chatbooks Business Money Experience Report

**Date:** 2026-10-02  
**Scope:** Frontend product work over existing BUSINESS APIs

## Outcome

The Chatbooks Money area now presents a calm, customer-facing BUSINESS money experience over the
existing deterministic accounting and reporting APIs. The frontend displays API-returned account
balances, recognized revenue, recognized expenses, report dates, and posted activity. It does not
derive authoritative totals, infer categories, fabricate transfers, or expose internal book
authority.

No backend accounting behavior, schema, BUSINESS API contract, PERSONAL persistence, AI behavior,
budget, reminder, C4 control, migration, database target, deployment configuration, or development
database content changed.

## 1. Screens and components created

### Money overview

- Added a single Money workspace with Overview, Accounts, Income, Spending, and Transfers tabs.
- The overview displays the income-statement revenue and expense values for the selected financial
  dates.
- Account balances come directly from the trial-balance response and retain their API-provided
  debit/credit orientation.
- The report's returned `as_of` value labels account balances. The requested date is never presented
  as the report date when the response differs.
- Recent activity uses posted journal-entry summaries and links to the existing immutable entry
  detail.

### Accounts

- Replaced the setup-only view with a paginated account experience that shows account name, code,
  type, active status, and the matching trial-balance amount.
- Added search, type, and status controls over the currently loaded API page. The interface states
  that these presentation filters do not change balances or report totals.
- Preserved role-gated account creation and activation controls through the existing account APIs.
- Added `/money/accounts/[accountId]` with API-backed metadata, current balance, active state, and a
  progressive accounting disclosure for total debits, total credits, and net debit.
- The detail view links to full Activity and states that account-specific activity filtering is not
  available in the current BUSINESS API.

### Income and spending

- Added period context and report-returned revenue or expense totals.
- Added links to posted Activity and the full income statement.
- The views explicitly state that the current API does not supply product categories, so no category
  breakdown or category filter is inferred.
- The Spending view does not classify a transfer as spending in frontend code.

### Transfers

- Added a truthful deferred state because the current BUSINESS API has no dedicated transfer
  workflow.
- The interface does not offer a fake transfer action or translate a transfer into an expense.

### Proposal workflow

- Clarified the existing workflow as **Draft → Validate → Review → Confirm → Post**.
- Kept validation, authenticated exact-version confirmation, and posting as separate actions through
  the existing APIs.
- Preserved the confirmation modal, version review, required acknowledgement, role checks, and the
  separate posting action. No automatic confirmation or posting was introduced.

## 2. BUSINESS APIs reused

| Experience                   | Existing API capability                    |
| ---------------------------- | ------------------------------------------ |
| Overview account balances    | Trial balance                              |
| Overview income and spending | Income statement                           |
| Recent activity              | Journal-entry list                         |
| Project labels in activity   | Project list                               |
| Account list and pagination  | Account list                               |
| Account detail               | Account read plus trial balance            |
| Account creation/status      | Existing account create/update             |
| Proposal workflow            | Proposal read, validate, confirm, and post |

The browser continues to call the typed frontend API client through the existing authenticated
same-origin proxy. No frontend component accesses SQLite, a database path, repository object, raw
connection, or ledger-book identifier.

## 3. Interaction flows

- The Money tabs reuse one report request pair, one recent-activity request group, and one paginated
  account request rather than fetching the same report again for each tab.
- Applying a valid financial date range refreshes the trial balance and income statement through the
  API. Invalid start/end ordering is rejected before a request.
- Account filters affect only the loaded page; Previous and Next request the corresponding API page.
- Account rows open a focused detail view. Accounting totals remain behind an explicit disclosure.
- Empty, loading, and error states are present for reports, account lists, balances, and activity.
- Account mutations remain available only when the current BUSINESS role has `manage_account`.
- Proposal review keeps the authenticated confirmation and posting boundaries intact.

## 4. Responsive and accessibility work

- Desktop uses restrained report summaries, list rows, and whitespace rather than a card grid or
  decorative chart.
- Tablet layouts reflow date controls, account setup, filters, and account metadata.
- At a 390 × 844 mobile viewport, the page and account list reported equal document/client widths;
  no page-level horizontal overflow was present. Money tabs use the existing intentional horizontal
  tab scroller, financial values wrap safely, filters stack, and mobile navigation remains visible.
- Tabs retain arrow-key, Home, and End navigation from the shared accessible tab primitive.
- Forms have associated labels, loading uses status semantics, failures use alert semantics,
  pagination has a navigation label, the proposal stepper exposes the current step, and links/buttons
  retain visible focus behavior.
- Motion remains limited to exact, short property transitions and respects reduced-motion settings.

## 5. Financial-boundary verification

- Every displayed nonzero financial value in Money is passed through from the trial-balance,
  income-statement, or journal-entry API response.
- The frontend performs no sum, aggregation, category allocation, transfer classification, net-income
  calculation, account-balance calculation, or reconciliation.
- Choosing the API-provided debit-balance or credit-balance field controls presentation only; it does
  not derive a new balance.
- Source scans found no SQLite, database-path, raw book-ID, PERSONAL API, or hard-coded nonzero money
  reference in the runtime Money implementation.
- The only `Math` findings in the new Money implementation are account-page display bounds and
  pagination offset clamping.
- BUSINESS organization context remains supplied by the existing authenticated financial-space
  provider. No PERSONAL row, endpoint, or value was created.
- The development database SHA-256 remained
  `D28F7434DF6F6954D42C8C0A607B9BE41BB4A7D61DC20D5B8FA7DABF8071C884`.

## 6. Files changed

- `frontend/src/app/(app)/money/page.tsx`
- `frontend/src/app/(app)/money/accounts/[accountId]/page.tsx` (new)
- `frontend/src/app/globals.css`
- `frontend/src/features/money/account-detail.tsx` (new)
- `frontend/src/features/money/account-setup.tsx`
- `frontend/src/features/money/money-views.tsx`
- `frontend/src/features/money/proposal-workflow.tsx`
- `frontend/src/lib/api/client.ts`
- `frontend/src/test/m5-2-ui1.test.tsx` (new)
- `docs/M5_2_UI1_BUSINESS_MONEY_EXPERIENCE_REPORT.md` (new)
- `memory.md` (task bookkeeping only)

No Python application, accounting, schema, migration, C4, or deployment file changed.

## 7. Test and build results

| Check                                | Result                                                                                         |
| ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| Focused UI1 tests                    | PASS — 8 tests                                                                                 |
| Complete frontend tests              | PASS — 25 tests in 3 files                                                                     |
| TypeScript                           | PASS                                                                                           |
| ESLint                               | PASS after removing one unused test import                                                     |
| Prettier                             | PASS                                                                                           |
| Next.js production build             | PASS — account detail included as a dynamic route                                              |
| Complete backend compatibility suite | PASS — 112 tests in 44.419 seconds                                                             |
| Source-boundary scans                | PASS — no frontend storage authority, PERSONAL API, raw book ID, or financial aggregation      |
| Documentation format/links           | PASS — 73 Markdown files, 254 local links, 0 broken                                            |
| Rendered desktop verification        | PASS — overview, accounts, detail, income, spending, transfers, and proposal validation/review |
| Rendered mobile verification         | PASS — 390 × 844, no document-level horizontal overflow                                        |
| Concurrent isolated API reads        | PASS — 48/48 HTTP 200 responses across accounts, trial balance, income statement, and activity |
| Browser/backend runtime errors       | PASS — no browser warning/error and no SQLite runtime error                                    |
| Development database boundary        | PASS — SHA-256 unchanged                                                                       |

Rendered verification used the normal built frontend and normal one-worker `chatbook-api` runtime
against a disposable schema-v3 database under `.test-tmp`. Its financial values were created by the
real proposal validation, confirmation, and posting APIs. The rendered proposal was validated and
the exact-version confirmation review was inspected; no automatic browser confirmation or posting
was performed. The disposable database is not a deployment or C4 target.

## 8. Known limitations

- The income-statement API exposes authoritative aggregate revenue and expenses but no category
  model or category breakdown. Income/Spending category presentation remains unavailable.
- The BUSINESS API has no guided transfer operation, so Transfers remains deferred.
- The current general-ledger API has no account filter, so account detail links to full Activity
  rather than presenting a misleading account-only list.
- Account list filters apply to one API page because the current list contract exposes offset/limit
  but no server-side search, type, or status filter.
- The current report contract supports financial date ranges but no named relative-period presets.
- PERSONAL persistence, PERSONAL APIs, budgets, reminders, AI, document extraction, bank
  integrations, C4 execution, and deployment remain outside this milestone.

## Final state

`Chatbooks Business Money experience implemented using existing BUSINESS financial APIs;
PERSONAL, AI, C4, and deferred capabilities remain untouched.`
