# ADR 0007: authenticated confirmation provenance

Date: 2026-09-25. Status: accepted for M3.

## Context

The foundation binds confirmation to an immutable validation fingerprint and actor. The API must
also prove which proposal version was displayed, which authenticated person confirmed it, when the
confirmation occurred, and which client request caused it.

## Decision

Foundation proposals remain immutable and currently have explicit version `1`; proposal editing and
supersession remain deferred. An API confirmation supplies the validation ID, proposal ID, displayed
proposal version, explicit `accepted: true`, and an `Idempotency-Key`. The engine rechecks the
validation fingerprint and current posting conditions, then atomically writes the confirmation and
an immutable provenance row containing proposal ID/version, authenticated actor through the linked
confirmation, UTC confirmation time, and request identifier.

The caller's idempotency key is also the confirmation request identifier and the audit correlation
request ID. A version or proposal mismatch is rejected as stale. Posting still requires a separate
request and the existing engine rule that the posting actor matches the confirming actor.

## Consequences

The exact reviewed immutable version is reconstructable without trusting API logs. Version 1 is a
real stored version, not a payload hash approximation. Introducing editable drafts will require a
new version/supersession design and must invalidate stale validations and confirmations.
