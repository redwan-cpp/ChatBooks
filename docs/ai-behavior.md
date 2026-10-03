# Chatbooks AI behavior boundary

No AI, model provider, agent tool, conversation pipeline, natural-language transaction
understanding, or extraction code is implemented. The chat-first product direction and a future UI
do not change that status. Until M9, conversational surfaces must use deterministic structured flows
and must not imply that natural-language requests are understood by AI.

## Permitted future capabilities

AI may eventually:

- interpret intent and ask clarification questions;
- retrieve authorized financial context and history;
- inspect user-provided documents as untrusted source material;
- prepare structured transaction proposals;
- explain verified financial activity and engine-generated reports; and
- suggest next actions that the user can review.

Every future tool invocation must carry a typed Financial Space reference. The server must resolve
the authenticated user's authority for that exact personal or business context. Text that mentions a
different person, organization, project, or space is not authorization. Personal and business data
must never be merged into model context, retrieval, memory, or reports unless an explicitly
authorized product operation defines that view.

## M5.1-A universal context boundary

M5.0 defines the personal context and M5.1-A defines its universal-core resolution without
implementing any AI. A future tool call
must receive a server-issued `FinancialContext` containing a typed `FinancialSpaceRef`, display
currency and precision, the authenticated actor's resolved capabilities, a financial date or as-of
range, and request/source provenance. `project_id` is permitted only when the space kind is
`BUSINESS` and the project belongs to that organization.

For `PERSONAL`, the server must resolve the space to the authenticated user's `PersonalSpace` and
must enforce owner access before assembling retrieval context. For `BUSINESS`, it must continue to
resolve organization membership and permissions through the existing M3 boundary. The model cannot
choose a context, convert a personal identifier into a business identifier, request a combined
personal/business view, or expand its authority by mentioning a resource in conversation. Context
switching and any future combined view require an explicit, authorized application operation.

The server may attach an internal, narrowly scoped ledger-book capability after authorization. The
model never chooses, sees as authority, persists, or substitutes a raw `ledger_book_id`. Every tool
reauthorizes the space/resource relationship and returns deterministic core results. Business tools
call the compatibility facade; future personal tools call the personal adapter; both remain above
the same proposal and ledger service.

Personal accounts, categories, budgets, reminders, recurrence, goals, and conversations must remain
separate from posted ledger actuals. A future model may suggest a category or prepare a structured
proposal, but deterministic mapping, validation, human confirmation, posting, reports, and audit
remain outside the model boundary.

Future jurisdiction or compliance tools are also external proposal clients. They must carry rule-set
version, jurisdiction, effective date, source, and calculation provenance and cannot claim universal
tax/statutory correctness. AI cannot select a tax policy, perform an authoritative compliance
calculation, or turn a compliance result directly into a posting.

## Prohibited capabilities

AI must never receive direct database access, the private accounting connection, confirmation or
posting credentials, or a tool that can mutate the ledger. It must not:

- choose or impersonate an authenticated actor;
- manufacture confirmation or evidence of human review;
- confirm, post, reverse, delete, edit, or replace accounting records;
- unlock periods or bypass organization/space permissions;
- calculate authoritative balances separately from the engine;
- infer accounting, tax, currency, transfer, or recognition policy; or
- treat conversation memory, extracted values, reminders, budgets, or recurring templates as posted
  financial truth.

## Proposal and confirmation boundary

The M3 API separates proposal creation, deterministic validation, authenticated exact-version
confirmation, and posting. A future AI tool may create or inspect a proposal through an authorized
application service. It may not call confirmation, posting, reversal-posting, period-locking, or raw
database operations.

A tool-generated `accepted=True`, a bearer token accessible to a model, or conversational text such
as “yes” is not independent evidence of the required authenticated human confirmation. The
application must show the exact proposal version, context, amount, currency, date, and consequence,
then bind a separate user action to that version and actor. Requests to undo a posting may create a
reviewable reversal proposal only; the ordinary confirmation and posting boundary remains.

## Verified retrieval and explanation

Reports exposed to AI must be generated by the deterministic engine and include space scope,
currency and precision, financial date range or as-of date, and source provenance. Model narrative
may explain those results but cannot replace their arithmetic. The interface must distinguish an
estimate, plan, suggestion, proposal, and posted actual.

Conversation, message, source, retrieval, and tool-invocation records will require explicit
retention, deletion, privacy, and audit rules before implementation. AI memory must not become a
financial system of record.

## Readiness gate

M9 must not begin until tool permissions, space scoping, prompt/document injection defenses, source
provenance, privacy and retention, confirmation separation, and operational security are reviewed.
Passing the kernel, API, or frontend milestones does not authorize a model to confirm, post,
reverse, lock a period, or access the database.
