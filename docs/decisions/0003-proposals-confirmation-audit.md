# ADR 0003: immutable proposals, explicit confirmation, and automatic audit

Date: 2026-09-25. Status: accepted for the foundation.

## Context

Users must review a valid proposal before posting. Future AI must not directly mutate accounting
records. Financial history must survive correction and every mutation must be attributable.

## Decision

Keep proposals separate from journal entries. Seal proposals after creation, record deterministic
validation with a proposal fingerprint, then require a separate explicit confirmation bound to that
validation and actor. Revalidate during confirmation and within the atomic posting transaction.
Require the posting actor to match the confirming actor. A unique proposal reference prevents
duplicate posting; repeated use of the same confirmation returns the existing entry.

Use database triggers to capture insert/update audit snapshots in the same transaction. Prevent
updates/deletes/replacements of immutable records and appends to sealed proposals or posted journals.
The supported mutation boundary is the engine, not raw SQL. No AI interface is implemented.

## Consequences and alternatives

Correction requires a new proposal or posted reversal. Proposal editing would need explicit
versioning/supersession and invalidation of old confirmations; it is deferred. Automatic posting
upon validation is rejected because it conflates correctness with user authorization. The local
caller is trusted: confirmation records alone cannot prove human identity without future
authentication. Trigger audit is durable with financial writes but not tamper-proof against file owners.
