# ADR 0013: Personal ownership is separate and private by default

**Date:** 2026-09-26  
**Status:** Accepted for M5.0 architecture; implementation deferred

## Context

The existing organization is a business owner with memberships and roles. Personal finance needs a
private owner and must not inherit business projects, role semantics, or accountant visibility. A
stable personal ID is also needed so ownership can evolve without using the user ID as every
resource's tenant key.

## Decision

Introduce a future `PersonalSpace` ownership aggregate. The initial model permits one personal space
per user and makes its authenticated owner the only principal with access. Every personal resource
is constrained to that space. Organization membership grants no personal access.

Household, dependant, guardian, joint-owner, and advisor access are deferred. They require explicit
personal grants or a distinct household ownership model with consent, revocation, and access audit;
they will not reuse organization memberships.

## Alternatives considered

### Represent a person as a one-member organization

Rejected because it exposes business roles, projects, periods, routes, and reporting semantics and
makes isolation depend on presentation behavior.

### Use `user_id` directly as every personal record's owner

Rejected because it makes future ownership evolution and sharing a cross-cutting primary-key change.

### Implement household sharing in the initial model

Rejected because joint ownership, consent, guardianship, and delegated access requirements are not
approved.

## Consequences

- Personal and business ownership remain independently enforceable.
- A unique owner constraint provides simple private-by-default MVP authorization.
- Multiple personal spaces or sharing will require an explicit migration and product decision.
- Personal deletion, retention, recovery, and export rules remain human decisions.
