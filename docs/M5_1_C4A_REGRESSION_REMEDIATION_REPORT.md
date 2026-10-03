# M5.1-C4A regression remediation report

**Date:** 2026-09-28  
**Scope:** Reconciliation failure-injection determinism only  
**Status:** **Remediated; release-candidate suite green; C4 remains NO-GO**

## Root cause

The `reconciliation_mismatch` failure injector updated the positive debit whose randomly generated
text ID sorted first and always added one minor unit. The C3 fixture intentionally contains a debit
at the supported maximum of 9,000,000,000,000 minor units. When that line's random ID sorted first,
SQLite correctly rejected the update through the existing line-limit `CHECK` constraint. The
migration therefore surfaced `IntegrityError` before reaching the intended financial-projection
comparison and its `migration_reconciliation` diagnostic.

The defect was in the rehearsal fault selection. It was not a ledger, migration, rollback, or
constraint defect.

## Exact remediation

`chatbook/canonical_migration.py` now routes this fault stage through a dedicated deterministic
helper. The helper:

1. considers only positive debit lines, which preserves the line-side constraint;
2. prioritizes debits below `MAX_AMOUNT`, ordered by amount, transaction, position, and ID;
3. increments the selected sub-maximum debit by exactly one minor unit;
4. if every positive debit is already at `MAX_AMOUNT`, selects deterministically and decrements by
   exactly one minor unit; and
5. fails with `migration_reconciliation` if no positive debit exists instead of producing an
   unrelated database diagnostic.

The injected line remains valid under the existing database constraints while differing from the
legacy projection. The normal reconciliation comparison then raises the intended
`migration_reconciliation` error. The surrounding transaction rolls the disposable target back to
schema v3, and the source file remains byte-for-byte unchanged.

## Financial and operational scope

The change is reachable only when the rehearsal-only `fail_after` option is explicitly set to
`reconciliation_mismatch`. It does not run during a normal migration and does not change:

- `MAX_AMOUNT` or any SQLite constraint;
- proposal, posting, balancing, confirmation, reversal, audit, period, or report behavior;
- canonical data copying or reconciliation rules;
- transaction or rollback boundaries;
- runtime schema selection or any production safety gate; or
- BUSINESS ownership, PERSONAL ownership, or public API behavior.

No production or shared database was discovered or accessed. Tests used temporary synthetic SQLite
fixtures. The workspace `chatbook.db` was not opened by the remediation tests and retained its
previous schema, size, and SHA-256 fingerprint.

## Verification

| Gate                                                                                               | Result                                              |
| -------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Focused failing test                                                                               | **PASS** — 1 test in 1.812 seconds                  |
| Determinism repetition                                                                             | **PASS** — 10 fresh runs in 18.224 seconds          |
| Complete C3/C4A suite                                                                              | **PASS** — 11 tests in 12.705 seconds               |
| Complete backend release-candidate suite                                                           | **PASS** — 88 tests in 31.257 seconds               |
| Strict mypy                                                                                        | **PASS** — 28 application source files              |
| Ruff lint                                                                                          | **PASS**                                            |
| Ruff formatting                                                                                    | **PASS** — 95 files                                 |
| Frontend Prettier formatting                                                                       | **PASS**                                            |
| Existing normal-schema, raw-book, PERSONAL-domain, source-boundary, and rehearsal-activation scans | **PASS** — 5 focused safety tests                   |
| Documentation formatting and local links                                                           | **PASS** — 203 local links across 58 Markdown files |

An initial sandbox-restricted focused invocation could not create its temporary SQLite file. It was
discarded as an environment failure and rerun with temporary-file permissions; all authoritative
test results are the passing runs above.

## Cutover status

This remediation closes only the nondeterministic release-candidate regression recorded in the C4
preflight blocker report. No maintenance announcement, writer shutdown, backup, restore, migration,
read-only cutover validation, canary, rollback, writer resumption, or M5.2 work occurred.

M5.1-C4 remains **NO-GO** until the separate deployment-specific source, topology, recovery,
protection, capacity, monitoring, canary, ownership, and approval blockers are resolved with real
evidence.
