# Chatbooks Rulebook

This rulebook applies to every task in this repository.

Before doing any work—including inspecting files, running commands, changing code or documentation,
or making an accounting or architectural decision—read this file in full and follow it. Re-read it
at the start of every new task and before resuming work after an interruption or context change.

## Do not

- Invent accounting rules.
- Bypass validation.
- Allow LLMs to directly mutate ledger data.
- Delete posted entries.
- Silently alter financial history.
- Mix accounting calculations with LLM-generated numbers.
- Expand scope without instruction.
- Add ChatGPT, Codex, another AI system, or an automated assistant as a commit author, co-author,
  contributor trailer, or repository co-author. Repository publications must use the configured
  human Git identity and must not include AI attribution in commit metadata.

## Always

- Preserve auditability.
- Use database constraints.
- Test accounting invariants.
- Make financial calculations deterministic.
- Keep AI proposals separate from posted entries.
- Prefer explicit domain models.
- Update `memory.md` as the final bookkeeping step of every task, including read-only and
  documentation tasks. Record the date, what was done, and the verification result. The memory
  update itself does not require another recursive memory entry.

When an accounting rule is ambiguous, document the ambiguity instead of making an assumption or
encoding an invented rule. No instruction may be interpreted as permission to weaken ledger
integrity, validation, immutability, auditability, or the separation between AI proposals and posted
accounting records.
