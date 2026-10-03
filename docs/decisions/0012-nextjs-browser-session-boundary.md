# ADR 0012: Next.js frontend and browser session boundary

**Status:** Accepted for M4  
**Date:** 2026-09-26

## Context

M4 requires a real browser application over the M3 FastAPI boundary. FastAPI issues opaque bearer
tokens, but placing those tokens in browser-accessible storage would unnecessarily expose them to
client JavaScript. The frontend must remain a presentation and workflow layer and must not acquire
accounting or authorization authority.

## Decision

Use a Next.js App Router application with strict TypeScript, React, and Tailwind CSS. Browser code
calls a same-origin `/api/chatbook` route. That route proxies requests to FastAPI, stores the opaque
session token in an HTTP-only, SameSite=Lax cookie, adds Secure in production, and removes the token
from the browser-visible login response.

FastAPI remains the authentication and organization-authorization authority. The frontend may hide
or explain controls using the current role, but it cannot grant access. All accounting mutations
continue through proposal, deterministic validation, exact-version confirmation, idempotent posting,
and reversal endpoints. The frontend contains no database client and no ledger calculations.

Financial context is a tagged UI value. A business context contains an existing organization ID.
Personal is visible but intentionally deferred and has no fake organization or persisted data.

## Consequences

- Bearer tokens are unavailable to ordinary browser JavaScript.
- The web and API processes can be developed and deployed separately while the browser uses one
  origin.
- The proxy is a security boundary that requires TLS, proxy-header review, CSRF review for future
  cross-site requirements, and operational hardening before Internet deployment.
- API authorization and accounting tests remain decisive; frontend role checks are experience tests.
- Personal persistence, conversations, attachments, budgets, reminders, and AI remain future domain
  work rather than simulated M4 data.
