# ADR 0011: Chat-first experience with progressive financial disclosure

## Status

Accepted for M3.5 product and UX architecture; frontend and AI implementation are deferred.

## Naming

Chatbooks is the single canonical written name for the project, codebase, product, and visual
identity discussed in this ADR. Existing lowercase `chatbook` technical identifiers remain stable
compatibility surfaces.

## Context

Chatbooks is intended for people with varied accounting knowledge. A traditional dashboard that
leads with charts, tables, modules, debits, and credits would expose the storage model instead of
helping users answer what they want to do with their money. The experience should feel familiar to
users of modern conversational software without copying another product's visual identity.

## Decision

Conversation is the default entry and primary action surface. The top-level experience uses a
visible Personal/Business context switcher and the compact concepts Chat, Money, Projects, Reports,
and Activity. Projects appears only in business context. A separate Home surface is deferred until
budgets, reminders, and attention signals give it a distinct purpose.

Financial detail is progressively disclosed:

1. everyday meaning and amount;
2. category, account, date, and context;
3. debit, credit, and ledger detail; and
4. proposal, validation, confirmation, posting, actor, timestamp, and source provenance.

Conversation never replaces typed actions. Any money-changing request becomes a structured proposal
whose exact context, amount, date, status, and consequence are reviewable before confirmation.

Chatbooks may use established conversation conventions such as a chronological message stream,
composer, suggested prompts, keyboard submission, processing states, and conversation history. Its
visual identity must be designed independently and must not copy ChatGPT branding, exact layout,
sidebar, composer, typography, color system, spacing, icons, microcopy, or persona.

## Consequences

- M4 may implement a deterministic conversational shell over existing API actions without claiming
  natural-language understanding.
- The UI must distinguish planned, proposed, validated, confirmed, posted, and reversed states.
- Accounting and audit fidelity stays reachable for authorized advanced users.
- Plain language cannot hide financial context, status, amount, currency, or confirmation effects.
- AI remains deferred and, when introduced, can only operate through scoped structured tools and
  proposal boundaries.

## Alternatives considered

### Lead with a conventional accounting dashboard

Rejected because it makes accounting structure the primary user journey and conflicts with the
product's conversational purpose.

### Hide accounting detail completely

Rejected because accountants and users investigating a transaction need deterministic detail and
audit provenance.

### Reproduce an existing conversational product's interface

Rejected because familiarity should come from interaction conventions, while Chatbooks needs its
own financial context, action states, evidence patterns, and brand identity.
