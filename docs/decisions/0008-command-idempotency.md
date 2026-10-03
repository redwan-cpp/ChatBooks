# ADR 0008: caller-supplied command idempotency

Date: 2026-09-25. Status: accepted for M3.

## Context

Network clients retry requests. The kernel safely retries one confirmation when posting, but a new
confirmation can otherwise be created more than once, and payload equality cannot distinguish a
retry from two legitimate transactions.

## Decision

Confirmation and posting require a caller-supplied `Idempotency-Key` of 8–200 characters. The engine
stores an immutable receipt scoped by organization, authenticated actor, operation, and key. The
receipt contains a canonical request fingerprint and the original resource ID. The receipt and the
confirmation or journal mutation commit in the same SQLite transaction.

A retry with the same key and request fingerprint returns the original confirmation or journal
entry. Reusing the key for a different request returns `idempotency_conflict`. Fingerprints only
detect conflicting reuse of an already supplied key; they never deduplicate requests by content.

## Consequences

Retries cannot duplicate accounting effects, including concurrent retries under SQLite's serialized
write model. Proposal creation and reversal-proposal creation do not yet accept idempotency keys.
Receipt retention and cleanup are intentionally undefined; deleting receipts could weaken retry
safety and therefore requires a later policy and migration.
