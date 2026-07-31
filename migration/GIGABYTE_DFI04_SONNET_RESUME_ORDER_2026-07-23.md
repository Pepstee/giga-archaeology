# Gigabyte DFI-04 Sonnet resume order — 2026-07-23

Work only in:

`/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-04`

Read first:

1. `/home/gutua/software-factory/giga-user/migration/MOBILE_CUTOVER_CHECKPOINT_2026-07-23_DFI04_NO_GO.md`
2. `/home/gutua/software-factory/giga-user/reports/FABLE_DFI04_BOUNDED_MILESTONE_RULING_2026-07-23.md`
3. `/home/gutua/software-factory/giga-user/reports/CODEX_DFI04_INDEPENDENT_REVIEW_2026-07-23.md`

Do not use subagents. Do not commit, transfer, activate, touch production, begin DFI-05 or touch
JAA. Do not clear STOP. Do not run the full suite; Codex will run authoritative certification
after independent review.

The current candidate is NO-GO. Its most important Fable ruling was not implemented:
compiler-active still calls `admit_task_batch` before persisting the scheduler decision, so the
decision is not a write-ahead commit and restart cannot re-drive it.

Implement this exact contract:

1. Compile and plan without mutation.
2. Immediately before durable decision append, check STOP. If armed, append nothing and mutate
   nothing.
3. Persist a sealed `scheduler_decision` containing the complete `workflow_task_batch` before any
   parent claim, child admission, KB write, `task_result` or COMPLETE mutation.
4. After decision commit, idempotently admit/settle the batch. If STOP appears after the commit,
   finish that committed parent; STOP only prevents starting the next parent.
5. If admission crashes after decision append, a fresh repository and later scheduler cycle must
   discover the committed incomplete decision, validate its embedded batch
   identity/profile/epoch/parent, re-drive it, dedupe the decision and child set, and return one
   successful local `SchedulingAction` only after admission completes.
6. Add distinct tests proving event order, crash after durable decision before admission, restart
   redrive, one decision, one child set, parent DONE, and STOP behavior before versus after commit.

Settle the remaining evidence gaps:

7. The existing-test verifier must recognize only `test_` functions/methods. A read, decode or
   syntax failure in any matched owned Python test resource must fail verification rather than be
   silently skipped. Prove version-stable recursive-glob behavior under Python 3.12 and 3.14.
8. Add exact daemon tests:
   - matching durable adoption plus matching bundle boots;
   - mismatched durable adoption plus bundle refuses;
   - one real `build_factory_epoch` bundle integration test with no synthetic epoch substitution.
9. Prove typed and untyped compiler fallback decisions, plus shadow and compiled decisions,
   persist/replay/dedupe and validate embedded batch identity.

The production code budget is 496 net added lines against HEAD, including untracked
`control/scheduler_profile.py`. All repairs must remain at or below 500 net production lines.
Refactor duplication; tests are outside the budget. Never weaken behavior to meet the budget.

Run focused tests under Python 3.12 and verifier tests under Python 3.14, Ruff on every changed
Python file, `git diff --check`, and the exact production numstat including the untracked file.
Return exact commands, counts, net lines and unresolved risks. If the contract cannot fit within
500 net lines, stop and report the conflict instead of concealing it.
