# Factory Turnstile C1 — independent-review repair

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
Preserve the current uncommitted 310-test C1 candidate on base
`895c2a8318de6d98cdccb03a58e0284d6433d37f`.

Sole writer. No subagents, commits, production, DFI-05, JAA, other worktrees, allocation,
certification, CLI or documentation. Edit only:

```text
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Fix only four independently identified C1 gaps:

1. **Lease race:** the method checks `state["lease"]` under the lock and then releases the lock for
   the entire multi-file read/write. Hold the controller lock continuously from state/lease
   validation through all reads, pack verification/installation and event append. A worker/reviewer/
   tester that arrives after context construction begins must not start until the pack has reached
   a terminal success/failure. An already-recorded lease is still rejected.
2. **Normalized duplicates/type safety:** validate every item is a string before any set operation.
   Normalize paths first and reject duplicates after normalization, including aliases such as
   `a/../b` and `b`. All bad inputs raise `TurnstileError`, not raw `TypeError`.
3. **Early byte ceiling:** pass the remaining byte allowance to descriptor-bound reading so an
   oversized file is refused without allocating the whole file. Convert the bounded-read failure to
   a truthful `TurnstileError`.
4. **No-clobber install:** the missing-collision check followed by `os.replace` can overwrite a file
   created in between. Install the fsynced same-directory tempfile atomically without replacement
   (standard library only; a hard-link/no-clobber pattern is acceptable), remove the temporary name,
   then fsync the directory. A concurrent collision must fail closed and must never be overwritten.

Add deterministic regressions for all four, including a barrier proving a model operation cannot
enter Lock-1 while context construction owns the lock, normalized alias refusal, a large-file
bounded-read check, and a collision injected at install time whose bytes remain unchanged.

Preserve all 310 tests. Complete production must remain at or below **1,840 physical lines**.
Run focused unittest, py_compile and `git diff --check`; report exact results and risks. Do not
self-certify or commit.
