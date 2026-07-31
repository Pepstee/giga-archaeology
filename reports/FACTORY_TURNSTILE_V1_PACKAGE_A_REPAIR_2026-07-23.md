# Factory Turnstile v1 — Package A repair order

Work only in:
`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

This is a bounded repair of the Package A implementation after independent Codex review. You are
the sole writer. Do not spawn subagents, commit, touch production, DFI-05, JAA, another worktree,
or any file outside:

```text
factory_control/__init__.py
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Preserve the governing contract in
`reports/FACTORY_TURNSTILE_V1_WORK_ORDER_2026-07-23.md`. Correct the following without implementing
Package B features.

## Required repairs

1. **Run in the declared worktree.** `run_worker()` must launch direct argv with
   `cwd=self.worktree`. Add a test in which a child writes a relative file and prove it lands in
   the declared worktree, not the controller's current directory.

2. **Fail closed on launch/setup failure.** If `Popen`, process-group lookup or process-start
   identity setup fails after the pending lease is recorded, do not strand a permanently live
   `pid=None` lease. Under the state lock, seal the current candidate, clear only the matching
   lease, transition to `paused`, append a truthful `worker_launch_failed` event, then propagate
   the original exception. If a child was created before setup failed, terminate/reap it safely.
   Test at least a nonexistent executable.

3. **Make stop genuinely bounded.** The current loop has no exit once the post-SIGTERM deadline
   expires. Use the existing SIGINT grace period, then SIGTERM, then a short bounded final
   escalation to SIGKILL if the same process group is still alive. Never spin forever. Record
   which escalation was required. Add a child that ignores SIGINT and SIGTERM and prove `stop()`
   returns within a deterministic upper bound and leaves no live child.

4. **Never signal a stale/reused target.** Before the first signal, prove the lease PID is alive
   with the recorded process-start identity and that its current PGID equals the recorded PGID.
   If that proof fails, do not signal the group; recover the orphaned lease by sealing and pausing
   with a distinct event. Recheck that the lease UUID is still the same before finalising state.
   Add a stale-identity test proving an unrelated live process is not signalled.

5. **Use exact Git pathname transport.** Replace line-oriented `git ls-files` parsing with
   NUL-delimited output (`-z`) and filesystem-safe decoding. Add tracked and untracked filenames
   containing spaces, tabs and newlines; each must be represented and each content/path mutation
   must change candidate identity. Continue to reject escapes and unsupported special files.

6. **Expose the path binding and validate inputs.** The candidate record must explicitly contain
   the resolved worktree path that already participates in its identity. Validate `work_weight`
   as a finite positive number, command as a non-empty list of non-empty strings, and reject
   malformed state shapes (at minimum non-list ledger, non-string stage, invalid lease type)
   as `CorruptStateError` rather than failing later with unrelated exceptions.

7. **Do not overclaim process liveness.** Preserve Linux `/proc` start-time identity, but make
   unknown/unreadable identity fail closed for lease takeover: a controller must not start a
   second operation merely because process identity could not be read. Recovery may proceed only
   with positive proof of death (`ProcessLookupError`/missing `/proc`) or positive proof of PID
   reuse (different readable identity). Add focused tests for the decision logic.

## Verification ceiling

Run only:

```text
python3.14 -m unittest -v tests.test_factory_turnstile
python3.14 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  tests/test_factory_turnstile.py
git diff --check
```

Finish with exact changed files, production line count, test count/results, and any unresolved
risk. Do not self-certify.
