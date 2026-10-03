# ADR 0005: FastAPI application boundary

Date: 2026-09-25. Status: accepted for M3.

## Context

The hardened accounting kernel is ready for an application layer. Network clients need typed HTTP
contracts, authentication, authorization, organization isolation, stable errors, pagination, and
request logging without duplicating accounting rules or gaining database access.

## Decision

Use FastAPI with Pydantic v2 models and synchronous route functions. Each request opens its own
`AccountingEngine`; FastAPI runs synchronous work outside the event loop. Routes authenticate an
opaque bearer session, resolve the actor from that session, enforce an explicit organization role
permission, and call a public engine method. API code does not write ledger, proposal, confirmation,
journal, period, account, project, or audit tables directly.

SQLite remains the M3 store. Schema version 2 has an explicit v1 migration. The API does not expose
the engine's private database wrapper, raw SQL, SQLite paths, or connection objects. List endpoints
use deterministic ordering and bounded offset/limit responses.

## Consequences

Accounting validation, posting, reversal, audit creation, and report arithmetic remain in the
kernel. The API can be replaced without changing ledger semantics. Synchronous SQLite calls are
appropriate for the current single-host milestone; multi-host scale, deployment topology, database
pooling, and a production database remain separate decisions.
