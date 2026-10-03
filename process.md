# Chatbooks Development Process

## Mandatory start

Before inspecting, planning, running commands, or editing this repository:

1. Read [`rules.md`](rules.md) in full.
2. Read [`memory.md`](memory.md) for the current state and unresolved boundaries.
3. Inspect the affected implementation, tests, documentation, and ADRs.
4. Identify which modules and invariants the proposed work can affect.

Do not continue with a financial behavior change when its accounting rule is ambiguous. Record the
ambiguity and obtain an explicit product/accounting decision first.

## Change classification

Classify work before implementation because the required evidence differs:

| Change                                | Minimum review surface                                                                        |
| ------------------------------------- | --------------------------------------------------------------------------------------------- |
| Documentation only                    | Rulebook, affected documentation, link and consistency check                                  |
| Domain value or validation            | Domain model, engine callers, database constraints, invariant tests                           |
| Posting or reversal                   | Domain, engine, schema/triggers, audit, concurrency, full lifecycle tests, ADR review         |
| Schema or persistence                 | Schema version/migration, constraints, audit triggers, rollback, integrity checks, ADR        |
| Reports                               | Ledger query scope, exact arithmetic, date behavior, sign conventions, report tests           |
| Project or document metadata          | Organization ownership, audit event, financial non-effect tests                               |
| Authentication, API, or AI            | Security boundary, explicit human confirmation, tool permissions, threat model, new ADR       |
| Financial Space or personal model     | Typed ownership, isolation, migration impact, ledger reuse decision, security review, new ADR |
| Budget, reminder, recurrence, or goal | Ledger non-effect, actual derivation, state semantics, authorization, ambiguity record        |

## Implementation sequence

1. State the intended behavior and the existing invariant it preserves.
2. Name unresolved assumptions. Do not hide them in code defaults.
3. Define or update explicit domain values and stable errors.
4. Add database constraints for rules that persistence can enforce.
5. Implement the application workflow using atomic writes.
6. Keep presentation code free of accounting calculations.
7. Add meaningful tests for the success path, invalid path, and relevant rollback/concurrency path.
8. Update requirements, architecture, design, ADRs, and security notes as needed.
9. Run the complete relevant verification gate.
10. Update project memory as the final bookkeeping step.

Financial calculations must be reproducible from stored, verified values. Never copy a model's
calculation into a posting or report without deterministic engine validation.

## Database change process

Normal application startup remains on schema version 3. Schema version 4 exists only as the
M5.1-C3 disposable rehearsal target until C4 is separately approved. A schema change must:

- preserve existing posted entries and audit history;
- use an explicit migration path and increment the schema version;
- keep foreign keys and organization ownership intact;
- retain or strengthen posting and immutability constraints;
- run atomically and fail closed on unknown versions;
- include migration, rollback-on-failure, foreign-key, and integrity checks; and
- add an ADR when it changes a major data or consistency decision.

Never delete, rewrite, or rebuild posted history as a shortcut. If the required migration semantics
are unclear, stop and document the decision that is needed.

For C3 v3→v4 rehearsal, use `rehearse_canonical_migration` with three distinct file paths: the
closed schema-v3 source, verified backup, and new disposable target. The tool performs preflight,
backup/restore verification, uncommitted reconstruction and reconciliation, transactional table
swap, trigger/index installation, final integrity checks, and schema-version commit. Its sanitized
evidence file is `<target>.c3-report.json`. Never point the target at the source or open a v4 copy
through normal `Database`, CLI, or API startup. C4 owns writer shutdown, deployment approval,
post-commit acceptance, canary, and writer resumption.

For C4A operational evidence, `chatbook-c4a-rehearsal NEW_OUTPUT_DIRECTORY` is synthetic-only. It
refuses an existing directory and constructs its own v3 source, so it cannot migrate a deployment
database. Keep its generated database files outside version control. The future C4 process is
controlled by [`docs/M5_1_C4_CUTOVER_RUNBOOK.md`](docs/M5_1_C4_CUTOVER_RUNBOOK.md) and
[`docs/M5_1_C4_RELEASE_CHECKLIST.md`](docs/M5_1_C4_RELEASE_CHECKLIST.md); neither authorizes C4.

## Verification gate

Install the locked development tools once:

```powershell
uv sync --locked --extra dev
```

Run all checks before completing a financial or architectural change:

```powershell
uv run --locked --extra dev mypy
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev python -m unittest discover -v
```

At minimum, verify these accounting properties when affected:

- every posted entry and the organization-wide ledger balance exactly;
- invalid proposals never reach the ledger;
- confirmation and current-state validation are both required;
- posting is atomic and retry-safe;
- locked periods reject posting;
- posted and audit records are immutable;
- reversals preserve the original and exactly offset it;
- cross-organization references and reads fail;
- reports use posted entries only and respect accounting dates; and
- failed writes leave no partial ledger or success audit records.

Documentation-only changes do not require rerunning accounting tests unless they modify executable
examples or claim changed behavior. Check links, commands, names, and consistency with code.

## Completion and handoff

A change is complete when the requested behavior is implemented, constraints and tests provide
appropriate evidence, relevant documentation is current, and unresolved assumptions are visible.
Report what changed, what was verified, and any remaining limits.

Update [`memory.md`](memory.md) at the end of every task, including read-only and documentation-only
tasks. Add a concise dated activity entry stating what was done and how it was verified. Also update
the durable state sections when scope, architecture, milestone status, verification status, or
unresolved decisions change. Keep memory factual and concise; do not store credentials, personal
data, transient debugging notes, or speculative accounting policy. The memory update is the final
bookkeeping step and does not recursively require another memory entry.
