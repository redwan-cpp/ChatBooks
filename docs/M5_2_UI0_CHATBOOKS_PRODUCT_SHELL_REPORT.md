# M5.2-UI0 — Chatbooks Product Shell Report

**Date:** 2026-09-30  
**Scope:** Frontend product shell and UX foundation only

## Outcome

Chatbooks now has a responsive, chat-first product shell that presents existing BUSINESS
capabilities through accessible user-facing concepts while keeping PERSONAL financial operations,
AI execution, document intelligence, and later milestones explicitly unavailable.

The work did not add a personal ledger, personal persistence, personal API routes, accounting rules,
financial records, migrations, or AI behavior. The existing accounting engine and API remain the
only financial boundaries.

## Screens and navigation

The global navigation now follows this order:

1. Chat
2. Money
3. Activity
4. Reports
5. Projects
6. Settings

Desktop uses a compact sidebar. Mobile uses a bottom navigation for Chat, Money, Activity, and
Reports, plus a More sheet for context-appropriate destinations. Projects is visible only in a
BUSINESS context. Settings remains available in both contexts, with PERSONAL settings gated until
the personal foundation exists.

### Chat

- Establishes the primary conversational workspace with conversation history, a composer,
  attachment affordance, financial-context label, and proposal-review rail.
- Makes the future Proposal → Validation → Confirmation → Posting sequence visible without
  implementing AI or posting behavior.
- Keeps typed messages local to the current rendered component and labels them `You · not sent`.
- States that attachments, conversation storage, AI actions, and personal proposals are unavailable.
- Links BUSINESS users to the existing manual proposal workflow.

### Money

- Organizes existing capabilities as Balances, Accounts, Income, Spending, and Transfers.
- Reads balances and income/spending values from existing report endpoints and does not calculate
  independent financial truth in the frontend.
- Preserves the existing account-setup and manual proposal paths.
- Marks transfers as unavailable because no supported transfer operation exists in the current API.
- Shows no invented personal balances, accounts, or transactions.

### Activity

- Leads with chronological posted financial activity from existing journal-entry data.
- Preserves the authorized immutable audit-history view as a secondary tab.
- Applies search, project filtering, and pagination only to API-returned data.
- Leaves PERSONAL activity unavailable until ledger-backed personal APIs exist.

### Reports

- Retains the existing BUSINESS income statement, balance sheet, cash flow, trial balance, and
  general ledger integrations.
- Keeps all reported amounts sourced from the accounting/reporting engine.
- Leaves PERSONAL reports unavailable.

### Projects and Settings

- Existing BUSINESS project routes and workflows remain intact.
- Projects is omitted from PERSONAL navigation and has an explicit business-only fallback.
- Settings introduces a progressive-disclosure home for the current business context and the
  existing accounting-period setup. Account management remains under Money.

## Design-system changes

- Added reusable keyboard-operable tabs with Arrow, Home, and End navigation.
- Strengthened modal behavior with Escape handling, focus containment, and focus restoration.
- Added restrained context, status, review, empty-state, list, and responsive-shell patterns.
- Added settings, shield, and overflow icons in the existing line-icon language.
- Preserved the warm neutral palette, dark green navigation, salmon accent, readable type scale,
  visible focus states, and reduced-motion behavior.
- Kept the interface sparse and conversational instead of expanding it into an ERP dashboard or
  copying ChatGPT's visual treatment.

## Existing BUSINESS integrations reused

- Authentication and session handling
- Organization selection and role context
- Accounts and account creation
- Structured proposals, validation, confirmation, and posting
- Journal-entry reads and reversals
- Projects
- Trial balance, income statement, balance sheet, cash flow, and general ledger
- Audit history
- Accounting-period management

No frontend API contract changed.

## PERSONAL and AI boundaries

The shell permits users to select a Personal context so the future information architecture can be
evaluated. In that context:

- Chat remains visible as a non-executing shell.
- Money, Activity, Reports, and Settings fail closed with page-specific explanations.
- Projects is hidden and explicitly identified as BUSINESS-only if reached directly.
- No personal data is requested, persisted, fabricated, or mixed with BUSINESS data.

AI remains entirely deferred. The composer does not call an AI service, create a proposal, upload a
file, or mutate financial state. It previews local text only.

## Files changed

- `frontend/src/app/(app)/activity/page.tsx`
- `frontend/src/app/(app)/chat/page.tsx`
- `frontend/src/app/(app)/money/page.tsx`
- `frontend/src/app/(app)/settings/page.tsx` (new)
- `frontend/src/app/globals.css`
- `frontend/src/components/app-shell.tsx`
- `frontend/src/components/icons.tsx`
- `frontend/src/components/ui.tsx`
- `frontend/src/features/chat/chat-workspace.tsx` (new)
- `frontend/src/features/context/context-switcher.tsx`
- `frontend/src/features/context/personal-deferred.tsx`
- `frontend/src/features/money/money-views.tsx` (new)
- `frontend/src/test/m5-2-ui0.test.tsx` (new)
- `docs/M5_2_UI0_CHATBOOKS_PRODUCT_SHELL_REPORT.md` (new)
- `memory.md` (task bookkeeping only)

## Verification

| Check                            | Result                                                                                     |
| -------------------------------- | ------------------------------------------------------------------------------------------ |
| Frontend component tests         | PASS — 17 tests in 2 files                                                                 |
| TypeScript                       | PASS — `tsc --noEmit`                                                                      |
| ESLint                           | PASS                                                                                       |
| Prettier write/check             | PASS                                                                                       |
| Next.js production build         | PASS — 13 static pages generated; `/settings` included                                     |
| Existing backend API suite       | PASS — 9 tests                                                                             |
| Documentation format/link checks | PASS — 71 Markdown files, 253 local links, 0 broken                                        |
| Frontend financial-boundary scan | PASS — no database path, SQLite, ledger-book, or personal API access                       |
| Fabricated-value scan            | PASS — no hard-coded non-zero financial display values in product source                   |
| Development database integrity   | PASS — SHA-256 remained `D28F7434DF6F6954D42C8C0A607B9BE41BB4A7D61DC20D5B8FA7DABF8071C884` |
| Rendered desktop inspection      | PASS — Chat, Money, Activity, Reports, Settings, and context gating reviewed               |
| Rendered mobile inspection       | PASS — 390 × 844 viewport, no horizontal overflow, More sheet verified                     |
| PERSONAL isolation inspection    | PASS — Projects hidden; financial pages fail closed; Chat remains non-executing            |

Rendered verification used an isolated disposable schema-v3 SQLite database containing only a
synthetic verification user and empty BUSINESS organization. It did not access or change
`chatbook.db`, create PERSONAL data, create a schema-v4 target, execute C4, or add financial
activity.

## Known limitations and risks

- PERSONAL data, accounts, categories, transactions, reports, and proposals remain dependent on the
  M5.2 personal-finance foundation and are intentionally unavailable.
- The conversation composer is an interaction shell only. Drafts are ephemeral and disappear on
  navigation or refresh.
- Attachments and document intelligence remain unavailable.
- Transfers have no supported current API operation and remain gated.
- UI0 originally exposed a pre-existing Python 3.14 request-lifecycle defect: FastAPI could create,
  use, and close one request-owned SQLite connection on different worker threads. M5.2-UI0.1 now
  permits that sequential handoff only for API request connections, retains strict thread ownership
  elsewhere, and fixes the backend process count at one while SQLite remains the store. Normal
  multi-request rendered verification now passes without a thread-limiter workaround. See
  [`M5_2_UI0_1_SQLITE_RUNTIME_HARDENING_REPORT.md`](M5_2_UI0_1_SQLITE_RUNTIME_HARDENING_REPORT.md).

## Final state

`Chatbooks product shell implemented; financial/personal capabilities remain behind their existing milestones.`
