# ADR 0004: periods, compensating reversals, and project dimensions

Date: 2026-09-25. Status: foundation constraints implemented; broader workflow policies need review.

## Context

Period locking and auditable undo are required. Reopening rights, partial reversals, project
allocation rules, accounting basis, and fiscal closing policies are unspecified.

## Decision

Use explicit nonoverlapping periods with inclusive calendar dates. Locking is one-way in this
milestone. Reject posting if the date lacks an open period. A full reversal is a new proposal with
every original line swapped, preserving project dimensions, and a required reason and explicit
same-or-later date. It follows the normal validate/confirm/post workflow. A locked original period
does not prevent reversal in a later open period. Permit one direct posted reversal per target;
reversing a reversal creates a visible chain. Active accounts are required for every posting.

Project tags are optional on individual lines and do not themselves need to balance. Budget,
expected revenue, client, status, and dates are descriptive planning information only.

## Consequences and unresolved rules

Undo preserves all history and historical date reports. Some corrections will require account
reactivation or a new open period; the engine will report that requirement rather than bypass it.
Partial reversals, backdating before the original, period reopening, privileged overrides,
automatic close/open entries, and per-project allocation/balancing remain unresolved or deferred.
These restrictions are conservative product boundaries, not assertions of universal accounting law.
