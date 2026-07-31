# Factory Turnstile B2 repair R3 — truthful evidence lifecycle and cleanup

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
Preserve the current uncommitted 252-test candidate. You are the sole writer. Do not commit, spawn
subagents, or touch production, DFI-05, JAA, another worktree, or files outside:

```text
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Implement only the evidence lifecycle and post-launch cleanup corrections below.

## A. Stream reuse hashing

The new descriptor-bound helper reads the complete output log into RAM before hashing. Replace that
use with descriptor-bound streaming SHA-256 using fixed-size chunks. Keep bounded canonical receipt
reading, but refuse a receipt file larger than the exact expected canonical byte length instead of
allocating an unbounded file.

Preserve the regular-file, `O_NOFOLLOW` where available, `fstat`, device/inode, post-read `lstat`,
and always-close guarantees.

## B. Hash the fresh log through its original descriptor

Fresh test output is currently opened `wb`, closed, then reopened by pathname for hashing. A swap
can bind a different file. Open the log in a mode that permits reading. After the child exits:

1. flush and fsync;
2. hash from the same still-open descriptor using bounded chunks;
3. prove the evidence path still names that descriptor's regular device/inode;
4. only then close it.

The stored SHA must describe the exact bytes written by the test child. Do not reopen by pathname.

## C. No stranded matching tester lease after post-launch failure

After `Popen` succeeds, an exception while recording PID metadata, flushing/fsyncing/hashing output,
creating/fsyncing/replacing the canonical receipt, or writing final state can currently strand a
running child or a dead `running` lease.

Add one narrow cleanup path for test execution:

- preserve and re-raise the original exception;
- if the direct child may still be alive, terminate its exact process group with bounded escalation
  and reap it;
- under the lock, clear only the matching tester lease UUID, capture the current candidate when
  computable, and leave the stage `paused`;
- append a truthful `test_evidence_failed` or `test_finalize_failed` event;
- never clear or modify a replacement lease;
- if durable state itself remains unwritable, do not claim cleanup succeeded; preserve the original
  error and leave evidence for explicit recovery.

Do not change worker/reviewer semantics in this package.

## Tests

Add injected-failure regressions for:

- a large output log is hashed in bounded chunks and never read as one allocation;
- a fresh-log pathname swap before hashing is detected and fails closed;
- PID-record failure kills/reaps the launched child and clears only the matching lease;
- output flush/fsync/hash failure leaves no live child and no matching lease;
- receipt creation/replace/fsync failure leaves paused with no matching lease;
- one-shot final state-write failure is recovered to paused without losing the original exception;
- a replacement lease is never cleared by cleanup.

Preserve all 252 tests. Run:

```bash
python3 -m unittest tests.test_factory_turnstile
python3 -m py_compile factory_control/turnstile.py tests/test_factory_turnstile.py
git diff --check
```

Report exact count, production line count and residual risks. Do not self-certify or commit.
