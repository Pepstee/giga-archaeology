# DFI-05 inter-model concurrency stop checkpoint

**Stopped:** 2026-07-23 12:53 BST  
**Verdict:** Factory work paused. DFI-05 is dirty, preserved and **NOT CERTIFIED**.  
**Restart authority:** Artiom only, after the concurrency protocol below is implemented.

## Reason for stop

The unattended DFI-05 run violated the intended two-model collaboration contract:

- Codex and Claude Sonnet operated against the same mutable DFI-05 worktree concurrently.
- Their reads, edits and test runs were not separated by an exclusive writer hand-off.
- Sonnet launched repeated complete suites while the candidate continued changing.
- Test commands used pipelines such as `pytest ... | tail`; without `pipefail`, the shell
  reported success from `tail` while pytest had failed.
- The monolithic Codex task reported approximately 44.27 million cumulative tokens, including
  approximately 43.56 million cached-input tokens, demonstrating severe repeated-context churn.

The stop is preventative. No claim based on the concurrent DFI-05 run may be used as
certification evidence.

## Completed work that remains valid

DFI-04 was independently certified and committed before DFI-05 began:

- branch: `di/dfi-04-task-adapter`
- commit: `dcf509753845552a906a5a1a04fcdad754cb6471`
- tree: `ee193aac16910650c35c0b65588e1d2baa7bba50`
- production budget: 495 net added lines
- focused evidence: 118 passed
- affected regression evidence: 730 passed, 4 skipped
- authoritative complete suite: 3,830 passed, 9 skipped
- Ruff and diff checks: passed
- Fable ruling: GO

The durable receipt is:
`/home/gutua/software-factory/giga-user/reports/DFI04_CERTIFICATION_2026-07-23.md`.

## Preserved DFI-05 state

- worktree: `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-05`
- branch: `di/dfi-05-scope-admission`
- base commit: `dcf509753845552a906a5a1a04fcdad754cb6471`
- base tree: `ee193aac16910650c35c0b65588e1d2baa7bba50`
- commit status: no DFI-05 commit; dirty candidate preserved
- binary recovery patch:
  `/home/gutua/software-factory/.mobile-cutover-20260723/DFI05_GRACEFUL_STOP_2026-07-23.patch`
- patch SHA-256:
  `e7f7d438d33133c7deebd7894f70cba33df340bac3780603c2501a32a007b125`
- patch size: 62,065 bytes
- `git diff --check`: passed at the stop boundary

Changed paths:

```text
 M agents/task_manager.py
 M control/deterministic_scheduling.py
 A control/scope_admission.py
 M control/workflow_adapter.py
 M dispatch/repository.py
 A docs/efficiency/DFI_05_COHORT_SEAL_2026-07-23.json
 A docs/efficiency/DFI_05_WORK_ORDER_2026-07-23.md
 M infra/schema_registry.py
 A infra/scope_admission.py
 M tests/test_canonical_schema_registry.py
 M tests/test_deterministic_scheduling.py
 M tests/test_scheduler_decisions_and_boot_matrix.py
 A tests/test_scope_admission_and_fallback.py
 M tests/test_workflow_adapter.py
```

Production numstat:

```text
97  4  agents/task_manager.py
30  5  control/deterministic_scheduling.py
86  0  control/scope_admission.py
9   1  control/workflow_adapter.py
58  0  dispatch/repository.py
22  0  infra/schema_registry.py
56  0  infra/scope_admission.py
```

Production additions: 358. Production deletions: 10. Net: **348**, under the Fable-ratified
350-line ceiling by two lines. This is accounting only, not acceptance.

## Invalid or incomplete DFI-05 evidence

A 97-test focused run passed against an earlier candidate, but concurrent later edits invalidate
it as final evidence.

Repeated complete-suite outputs included:

```text
3 failed, 3,839 passed, 9 skipped
3 failed, 3,827 passed, 9 skipped
10 failed, 3,820 passed, 9 skipped
34 failed, 3,796 passed, 9 skipped
```

Some failures were environment-related because an external programme fixture was absent from the
new worktree. Others were genuine regressions involving scheduler-decision identity, fallback
persistence, STOP-before-write-ahead behaviour, profile adoption and workflow-adapter fallback.
The pipeline exit-code defect caused these runs to be described as successful. None is
certification evidence.

## Safety state after stop

- Windows Codex desktop process tree: stopped
- WSL Claude processes: stopped
- WSL pytest/Ruff processes: stopped
- production branch: `efficiency/e2-shadow-cache`
- production commit: `35efb19b07867bb58e1288479513078cf9ab65e4`
- production STOP: armed
- `orchestrator-v3.service`: inactive
- JAA: paused and untouched

## Required inter-model concurrency protocol before restart

1. **Exclusive writer lease:** one model may write a worktree at a time. The other model is
   read-only or idle.
2. **Explicit hand-off:** the writer exits before the reviewer begins. Bind every hand-off to a
   Git diff/tree hash and exact changed-path inventory.
3. **No overlapping correction:** if Codex writes a material correction, Sonnet must not still
   be running. Sonnet subsequently reviews that fixed snapshot read-only.
4. **Single-flight test controller:** only the coordinator launches certification suites.
   Workers may run named focused tests from their work order, never duplicate complete suites.
5. **Truthful exit capture:** use direct pytest invocation, `set -o pipefail`, or capture
   `PIPESTATUS[0]`. Output truncation must never replace the test process's exit status.
6. **Immutable evidence boundary:** a test result is valid only for the exact diff/tree hash that
   was tested. Any later edit invalidates it.
7. **Fresh bounded model sessions:** each work package receives only its work order and required
   evidence. Do not carry the monolithic 44-million-token coordinator transcript forward.
8. **Measured 30/70 split:** Sonnet receives approximately 70% of substantive implementation/test
   work packages; Codex receives approximately 30% for decomposition, integration, independent
   review and certification. The split does not permit simultaneous writers.

## Next safe sequence

1. Keep every process stopped.
2. Design and implement the exclusive writer/test single-flight mechanism outside the dirty
   DFI-05 candidate or as a coordinator harness change with its own tests.
3. Start a fresh Codex coordinator task from this checkpoint, not the prior transcript.
4. Inspect the preserved DFI-05 diff independently against `dcf5097`.
5. Decide which concurrent edits are coherent; do not trust either model's self-report.
6. Repair the candidate under one writer lease.
7. Recalculate the 350-line budget.
8. Run focused tests once, then affected regressions, then the complete suite only at the
   authorised gate with truthful exit capture.
9. Obtain independent model and Fable rulings before any commit.

Do not activate production, clear STOP, resume JAA or continue the unattended order until this
checkpoint's restart authority and gates are satisfied.
