# ADR 0010: Plans and schedules remain separate from posted actuals

## Status

Accepted for M3.5 product architecture; implementation is deferred.

## Naming

Chatbooks is the single canonical written name for the project, codebase, and product whose planning
and scheduling behavior this ADR defines. Existing lowercase `chatbook` technical identifiers
remain stable compatibility surfaces.

## Context

The expanded product includes personal and business budgets, financial reminders, recurring
payments, savings goals, and existing project planning values. These concepts describe intentions,
limits, targets, or future work. Treating them as accounting truth would permit mutable planning
records to disagree with the posted ledger.

## Decision

Budgets, budget lines, reminders, recurring transaction templates, goals, expected revenue, and
project budget metadata are non-ledger domain records. Creating, editing, completing, or cancelling
one has no direct accounting effect.

Actual income, expense, balance, revenue, and spend are derived from posted ledger lines using an
explicit approved mapping. No mutable `actual_spend` or equivalent field may become a second source
of financial truth.

A reminder completion does not mean a payment occurred. A recurring template or reminder may later
create a reviewable transaction proposal, but it cannot confirm or post it. The ordinary validation,
authenticated exact-version confirmation, deterministic posting, and audit path remains mandatory.

The existing `projects.budget` field remains planning metadata. It is not silently converted into a
general budget history or posting limit.

## Consequences

- Budget edits cannot rewrite historical actuals.
- Reminder and recurrence workflows remain safe even when schedules are wrong or delayed.
- Future reports can compare plan and actual while disclosing their distinct sources.
- Budget periods, category/account mapping, rollovers, enforcement, recurrence, time zones, and
  missed-occurrence behavior require explicit product and accounting decisions.
- Any future automated posting policy requires a separate decision and cannot be implied by this
  ADR.

## Alternatives considered

### Store actual amounts on budgets or projects

Rejected because independently mutable actuals can drift from the ledger.

### Post ledger entries when reminders complete

Rejected because task state is not evidence that money moved and does not satisfy confirmation.

### Let recurring templates post automatically

Rejected for the current architecture because it bypasses per-proposal validation and explicit
confirmation. Future automation needs a separately approved authorization model.
