# Factory Turnstile v1 — Package A final repair 2/2

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
You are the sole writer. Do not spawn subagents, commit, or touch any file except:

```text
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Preserve all 75 passing tests. Implement only:

1. `pause()` must refuse whenever any lease is recorded, including a dead or reused PID lease,
   and direct the operator to `recover()`. It must never write `phase=paused` while retaining a
   lease. Test live and dead lease cases.
2. `recover()` must fail closed when a pending lease has `pid=None`; that state does not prove a
   child was never launched. Raise `LiveOperationError` with a manual-inspection message and leave
   state unchanged. Test it.
3. `stop(timeout=0)` must still take one locked state snapshot and operate immediately when
   PID/PGID metadata is already present; it must not fail merely because a zero-length polling
   loop never ran. Test a real stoppable child with zero SIGINT grace.
4. After SIGKILL grace, if the original process group still appears live, retain the matching
   lease and `running` phase, append `stop_failed`, and raise `LiveOperationError`. Never append
   `stopped`. Cover this branch deterministically with mocked OS boundaries.
5. If the lease UUID changes while `stop()` is outside the lock, append
   `concurrency_violation`, do not alter the replacement lease, and raise `LiveOperationError`.
   Append `stopped` or `stop_stale_lease` only when the exact original lease is cleared. Add a
   focused race test.
6. Tighten lease validation without adding policy machinery: command must be a non-empty list of
   non-empty strings; PID/PGID must be null or positive non-boolean integers; UUID,
   candidate-before, actor, provider and role must be non-empty strings. Add representative tests.

Do not implement review, test receipts, contexts, allocation, CLI or documentation. Run only the
focused unittest module, py_compile and `git diff --check`. Report exact results and production
line count; do not self-certify.
