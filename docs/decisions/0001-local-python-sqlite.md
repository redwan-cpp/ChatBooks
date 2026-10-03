# ADR 0001: typed Python and transactional SQLite

Date: 2026-09-25. Status: accepted for the foundation.

## Context

The repository is empty. The first milestone needs a real persistent ledger, explicit domain
boundaries, deterministic behavior, type checks, automated tests, and a manual transaction path.
No web UI, AI provider, or hosting stack has been specified.

## Decision

Use Python 3.12+, immutable dataclasses/enums for domain values, strict mypy checks, and standard
library SQLite for persistence. Provide a library and a CLI. Runtime dependencies are zero.
SQLite STRICT tables require version 3.37+; JSON functions support structured audit snapshots.
Use short `BEGIN IMMEDIATE` write transactions and relational constraints plus posting triggers.
Initialize schema v1 atomically and reject unknown versions until a migration exists.

## Consequences and alternatives

This is easy to run and test on a single machine and does not commit the product to a frontend
framework or external service. SQLite serializes writes; high-concurrency/multi-host operation may
require a future database ADR and migration. Python type annotations are checked rather than
runtime-enforced, so external data also receives runtime validation. A PostgreSQL service or
TypeScript web stack would add deployment/dependency work before the ledger milestone and is deferred.
