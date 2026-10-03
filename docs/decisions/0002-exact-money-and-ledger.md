# ADR 0002: exact amounts and the posted journal

Date: 2026-09-25. Status: accepted for the foundation.

## Context

Double-entry equality must hold exactly. Currency, rounding policy, and reporting jurisdiction are
unspecified. Project plans and unconfirmed proposals must not change balances.

## Decision

Require an explicit organization currency label and fixed precision. Store nonnegative integer
minor units with exactly one positive side per line. Enforce balanced posted entries in application
validation and at the database posting transition. Cap lines and line amounts to keep per-entry
integer sums safe. Aggregate reports with Python integers. Derive all balances from posted journal
lines; do not maintain editable balances or infer postings from documents/project metadata.

## Consequences and alternatives

No floating-point tolerance or silent rounding exists. Single-currency reporting is simple and
deterministic, but FX and precision changes need separate approved designs. Arbitrary decimal SQL
storage and binary floating-point amounts are not used. Caches may be added later only as rebuildable
derived data. Basic report grouping uses user-selected account types and makes no statutory claim.
