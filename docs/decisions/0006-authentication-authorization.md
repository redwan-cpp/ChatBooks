# ADR 0006: authentication and organization authorization

Date: 2026-09-25. Status: accepted for M3.

## Context

The CLI trusts actor identifiers, which is not safe for a network boundary. The API needs a real
identity source and a small, explicit organization permission model without an enterprise IAM system.

## Decision

API registration stores a normalized unique username and a salted scrypt password hash. Login issues
a cryptographically random opaque bearer token; only its SHA-256 hash is stored. Sessions expire
after eight hours by default and can be revoked through logout. API actor IDs always come from a
valid session and never from request bodies or organization headers.

Memberships carry one of `OWNER`, `ADMIN`, `ACCOUNTANT`, `MEMBER`, or `VIEWER`. Permissions are
explicit in `chatbook/permissions.py`. Viewers can view organization data and reports. Members can
also create proposals and manage project metadata. Accountants can validate/confirm/post manual
journals, reverse entries, manage accounts and periods, and view audit history. Admins and owners
have all M3 permissions, including period locking and membership administration. Only an owner may
add another owner.

An organization creator becomes its owner. During v1 migration, the organization creation audit
actor becomes owner and other existing members become members. Membership removal, role changes,
ownership transfer, password reset, MFA, rate limiting, and account recovery are deferred.

## Consequences

Organization paths are always checked against the authenticated membership before data access.
Sessions are revocable without a signing-key rotation and token contents disclose no identity data.
The database stores credential hashes and session hashes, so protected storage, TLS, rate limiting,
and operational access controls are mandatory before Internet deployment.
