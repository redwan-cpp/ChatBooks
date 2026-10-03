# ADR 0018: Persistent LedgerBook is the universal ownership seam

**Date:** 2026-09-26  
**Status:** Accepted; BUSINESS mapping, service seam, canonical and operational rehearsals implemented; cutover deferred

## Context

The deterministic accounting rules can serve personal and business finance, but the current schema
and engine scope every financial record by `organization_id`. A personal user cannot safely reuse
that storage without a fake organization. A purely in-memory scope would not let database foreign
keys, triggers, audit, periods, or receipts enforce the same isolation.

## Decision

Introduce a future persisted internal `LedgerBook` with exactly one typed owner: an existing
Organization or a future PersonalSpace. It owns currency, precision, accounts, periods, proposals,
confirmations, journal, financial audit, and idempotency scope.

Canonical financial tables will ultimately use `ledger_book_id` in composite ownership keys and
foreign keys. Financial Space remains the customer/application context; LedgerBook is internal and
is resolved only after authorization. Existing organization IDs are preserved and mapped one-to-one
to books; they are not reinterpreted as book IDs.

Migration uses staged schema versions and parity gates: add owner mappings, extract the service seam,
construct book-scoped tables, copy existing IDs and immutable history, reconcile all reports and
audit, atomically switch, then enable personal writes. Personal posting is prohibited during a
partial migration.

## Alternatives considered

### Keep LedgerBook only as a domain value

Rejected as the target because business and personal database constraints would remain separate and
could diverge. It may be used temporarily while extracting the service seam.

### One-step replacement of all business tables

Rejected as a migration strategy because it combines service refactoring, ownership migration,
trigger replacement, and API compatibility in one cutover.

### Duplicate a personal ledger schema

Rejected because it creates two implementations of balance, posting, reversal, audit, and receipts.

## Consequences

- One durable scope can enforce cross-record ownership for both domains.
- Existing business behavior remains behind a compatibility facade.
- SQLite table reconstruction and extensive parity tests will be required later.
- Projects and organization documents remain business extensions rather than universal owners.
- M5.1-C1 implements the additive BUSINESS mapping only. Financial tables remain organization-scoped;
  canonical book-scoped persistence and personal ownership remain deferred.
- M5.1-C2 implements the universal service over a temporary organization-scoped storage adapter.
  It uses the mapped book as an authorized application seam while database ownership remains
  organization-scoped. This is an intentional migration stage, not the canonical target.
- M5.1-C3 implements the canonical schema-v4 book scope on disposable restored copies. Financial
  tables use composite book ownership; BUSINESS project/document links use constrained extensions;
  existing audit events remain unchanged and receive immutable book-scope sidecars. The normal v3
  application path stays authoritative until a separately approved C4 cutover.
- M5.1-C4A adds synthetic operational, backup/restore, capacity, parity, canary, and recovery evidence
  plus the future cutover runbook/checklist. It changes no owner, normal schema selection, or release
  authority.

**Classification:** ENGINEERING DECISION.
