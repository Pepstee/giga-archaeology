# Factory Turnstile v1 — B1 lifecycle deduplication only

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
You are the sole writer. Preserve all 180 passing tests and all behaviour. Edit only:

```text
factory_control/turnstile.py
```

Do not add tests, validation, features or later-package work.

`run_worker()` and `run_review()` duplicate child launch, PID/PGID/start-identity recording,
launch-failure cleanup, and interrupted waiting. Extract small private helpers used by both.
Role-specific preconditions and final state transitions must remain in the public methods.

Requirements:

- direct argv, `cwd=self.worktree`, `start_new_session=True`;
- matching-UUID lease updates only;
- identical fail-closed launch cleanup and event types (`worker_launch_failed` versus
  `review_launch_failed`);
- identical KeyboardInterrupt SIGTERM→SIGKILL handling;
- exact child exit code unchanged;
- stop/recover compatibility unchanged;
- no shell invocation;
- target `factory_control/turnstile.py` at 1,050 lines or fewer without dense/cryptic code.

Run only the existing focused unittest module, py_compile and `git diff --check`. Report exact
line count and results; do not self-certify.
