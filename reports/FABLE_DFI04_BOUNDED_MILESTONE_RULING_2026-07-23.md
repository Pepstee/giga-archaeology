# Fable bounded milestone ruling: DFI-04

Date: 2026-07-23

Scope: ruling from five exact facts supplied by Codex. Fable used no tools, browsing or
subagents. STOP remained armed, DFI-04 inactive and JAA paused.

## Verdict

DFI-04 remains **NO-GO for certification**. Every item below blocks certification.

## A. Admission and scheduler-decision ordering

The current active path mutates and completes work before appending its scheduler decision. A
crash can therefore leave durable children and a DONE parent with no reconstructable governing
decision.

Required design:

1. Compile the deterministic batch without durable mutation.
2. Recheck STOP immediately before appending the decision.
3. Durably append the sealed scheduler decision as a write-ahead commit point.
4. Execute admission idempotently, keyed by the decision identity.
5. Persist admission completion; the parent reaches DONE only at this point.

Replay must identify committed decisions lacking completion and redo admission rather than
reschedule the parent. A crash before the decision append leaves no durable effects. Once a
decision is committed, STOP prevents further batches but does not roll back that committed
decision; replay must finish it.

A single atomic multi-event transaction would also be valid, but write-ahead intent is preferred
because it reuses the current append-ledger model.

## B. Per-entry knowledge identity

Hashing and conflict comparison must use one shared semantic representation. It must include
`task_id` and stable ordinal as well as all other hashed semantic fields. Wall time remains
excluded.

Do not sort order-preserving lists. Preserve tags and links as-is unless their governing
contract explicitly declares set semantics. If set semantics are later ratified, sort by stable
canonical serialized bytes rather than raw mixed JSON values.

## C. Static existing-test verifier

Without executing or importing project code, certification must be restricted to tests that
static structure can prove pytest will collect:

- traverse module and class bodies structurally, never with `ast.walk`;
- collect module-level `test_*` functions;
- collect `test_*` methods only under default-convention `Test*` classes without `__init__`;
- emit and require fully qualified selectors such as
  `path::test_function` and `path::TestClass::test_method`;
- prohibit bare-name selectors;
- detect duplicate definitions rather than hiding them in a set;
- fail closed on ambiguity;
- retain strict confinement beneath `root/projects/<project>`.

## D. Corrupt scheduler decisions

Silent skip is prohibited. A schema-invalid scheduler decision must make replay/boot fail closed,
consistent with corrupt scheduler-profile adoption. A durable health record may supplement that
behaviour but cannot replace fail-closed boot.

## E. Required evidence

The explicit matrix is not waivable through adjacent general tests. Add distinct named tests for:

- reconstruction after CLAIM;
- reconstruction after `tasks_spawned`;
- reconstruction after a KB write;
- reconstruction after `task_result`;
- retry after COMPLETE;
- durable shadow, compiled and fallback decisions;
- fallback decisions with and without typed records;
- matching and mismatching daemon adoption+bundle states;
- real factory-epoch bundle integration.

## Budget

All production repairs remain inside the existing **500 net production-line** completion budget.
No extension is granted. Tests are outside this production-line budget, but must remain
matrix-scoped.
