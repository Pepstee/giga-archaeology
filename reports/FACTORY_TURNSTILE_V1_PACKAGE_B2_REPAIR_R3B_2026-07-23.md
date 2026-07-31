# Factory Turnstile B2 repair R3b — post-launch tester cleanup

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
Start from the current uncommitted B2 candidate after R3a. Sole writer; no subagents, commits,
production, DFI-05, JAA, other worktrees, or files outside `factory_control/turnstile.py` and
`tests/test_factory_turnstile.py`.

Implement only fail-closed cleanup after the tester child has successfully launched.

Current failure points after `Popen` include PID-lease recording, output flush/fsync/hash/identity
verification, receipt create/write/fsync/replace/directory-fsync, and final state persistence.
An exception can leave a live child or a dead `running` tester lease.

Add one narrow test-operation cleanup path:

- preserve and re-raise the original exception;
- if the direct child may still be alive, terminate its exact process group with bounded
  SIGTERM→SIGKILL escalation and reap the direct child;
- acquire the controller lock and clear only the matching tester lease UUID;
- capture the current candidate when computable and persist `paused`;
- append a truthful failure event;
- if a replacement lease exists, do not clear or mutate it and record a concurrency violation;
- never claim durable cleanup if state remains unwritable.

Do not alter worker/reviewer semantics, stop-race semantics, scheduling, retries or queues.

Add injected one-shot failure tests for:

1. PID-recording failure after launch: child is reaped; matching lease cleared; paused.
2. output flush/fsync/hash/identity failure: no live child or matching lease; paused.
3. receipt tempfile/write/fsync/replace/directory-fsync failure: paused, matching lease cleared,
   original exception preserved.
4. one-shot final state-write failure: second cleanup write leaves paused while original exception
   is re-raised.
5. replacement lease: cleanup refuses to clear or mutate it.

Preserve every existing test. Run focused unittest, py_compile and `git diff --check`. Report exact
count, production line count and residual risks. Do not self-certify or commit.
