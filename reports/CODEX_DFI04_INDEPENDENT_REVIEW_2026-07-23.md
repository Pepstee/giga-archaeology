# Codex independent review: DFI-04 completion candidate

Date: 2026-07-23

Status: **provisional NO-GO for certification**. This review is being appended while the
candidate is tested. Production remains unchanged, STOP remains armed and JAA remains paused.

## Evidence already observed

- Focused candidate suite: 143 passed.
- Broader affected suite: 333 passed, 4 skipped.
- Ruff: passed over every changed Python file.
- `git diff --check`: passed.
- Production-code budget: 531 insertions minus 31 deletions = exactly 500 net lines.
- Full suite: running when this checkpoint was written.

## Open findings

### C-1 — High: active mutation precedes its durable scheduler decision

`schedule_scope_certified_plans()` calls `admit_task_batch()` before `remember()` persists the
`compiled` scheduler decision. The admission can durably create children, write knowledge,
record a successful result and complete the parent. A crash immediately afterwards leaves real
mutations without the scheduler decision that is supposed to make the action auditable and
restart-reconstructable. Because the parent is then DONE, a subsequent scheduler cycle will not
recreate the missing record.

Required resolution: define and test a crash-safe ordering or transactional equivalent. A
durable decision may precede idempotent execution, provided STOP is rechecked before mutation and
restart deterministically resumes the recorded decision.

### C-2 — High: the required deterministic re-settlement matrix is incomplete

The new tests directly cover a crash after one of multiple KB entries and a crash after
`task_result` but before COMPLETE. The work order also requires reconstruction after CLAIM,
`tasks_spawned`, and COMPLETE, proving one child set, complete KB membership, one successful
result and a DONE parent at every window. Existing general repository and daemon tests are useful
but do not collectively prove this exact deterministic-adapter matrix.

### C-3 — Medium-high: existing-test verification can misidentify collected tests

The AST verifier walks every function recursively and then collapses names into a set per file.
Consequences:

- nested `test_*` functions that pytest would not collect can satisfy a claim;
- methods in non-test classes can satisfy a claim;
- duplicate definitions in one file collapse to one token rather than becoming ambiguous;
- class-qualified pytest node IDs are not represented.

The verifier therefore does not yet prove that a selector identifies exactly one current,
owned, collectable test.

### C-4 — Medium: knowledge conflict comparison is incomplete and can raise on legal JSON lists

The deterministic KB identity includes the task ID, but conflict comparison omits the durable
entry's `task_id`. It also sorts tags and links. Those fields are list-valued JSON in the
existing KB contract; mixed JSON values cannot necessarily be ordered and can raise during
settlement. Sorting also silently changes the existing exact-list semantics.

Required resolution: compare every semantic identity field, including `task_id`, using the same
canonical representation used to derive the ID, excluding only deliberately non-semantic
wall-time fields.

### C-5 — Medium: corrupt scheduler decisions disappear without a durable corruption state

Replay validation errors for `scheduler_decision` fall through the repository's generic
corrupt-record skip. The added test explicitly expects the decision to disappear while boot
continues. For authority telemetry, silent omission weakens auditability: the reconstructed
decision set can look complete when a durable decision record was malformed.

Fable should rule whether scheduler-decision corruption must fail boot, mark the decision ledger
incomplete, or be surfaced through a durable health state. Silent clean-looking omission should
not be accepted without an explicit policy.

### C-6 — Medium: scheduler-decision and daemon evidence is narrower than the work order

The new durable-decision test exercises shadow persistence and dedupe. It does not yet prove
durable `compiled` and both typed/untyped `fallback` decisions, embedded-batch validation, or the
crash boundary between decision persistence and mutation. The daemon matrix lacks a matching
adoption+bundle success path and an explicit mismatched-adoption+bundle refusal path. The
factory-epoch bundle tests still substitute a synthetic epoch rather than exercising the real
bundle integration requested by Fable.

## Constraints for the correction

- Keep the candidate at or below 500 net added production lines.
- Do not weaken STOP, adoption, replay, isolation or assurance checks.
- Do not activate or merge DFI-04.
- Do not begin DFI-05.
- Do not resume JAA.
