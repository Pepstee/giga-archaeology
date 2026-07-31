# Factory Turnstile v1 — Package A final repair

Work only in:
`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Read the governing work order, Package A repair order and scope-budget addendum. You are the sole
writer. Do not spawn subagents, commit, touch production, DFI-05, JAA, another worktree, or files
outside:

```text
factory_control/__init__.py
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Preserve all 54 currently passing tests. Make only these final Package A corrections:

1. **Never overwrite an existing lease.** `run_worker()` must refuse whenever `state["lease"]` is
   non-null, even when its PID is dead or reused. Only explicit `recover()` or `stop()` may clear
   it. Add a test proving a dead-PID lease blocks a new writer until `recover()` is called.

2. **Reject inconsistent state.** `_load_state()` must fail closed when phase is `running` without
   a lease, or when a non-running phase has a lease. Validate the required lease fields and basic
   types before any PID/PGID signalling. Add focused corrupt-state tests.

3. **Never clear a process that survived stop escalation.** After the final SIGKILL grace period,
   recheck the same process group. If it remains live, retain the matching lease and running phase,
   append `stop_failed`, and raise `LiveOperationError`. Do not announce `stopped` or permit a new
   writer. Add a deterministic mocked-boundary test for the surviving-group branch.

4. **Close stop races.** If the lease UUID changes while `stop()` is outside the lock, append a
   concurrency-violation event and fail closed without modifying the replacement lease. A stopped
   event is valid only when the exact original lease was cleared.

5. **Reject unsafe controller placement and invalid timeout.** Construction or initialisation must
   reject a control directory equal to or inside the governed worktree. `stop()` must reject
   non-finite or negative timeout values. Add focused tests.

Do not implement review, test receipts, contexts, allocation, CLI or documentation in this turn.
Keep the repair compact and report the resulting production line count.

Run only:

```text
python3.14 -m unittest -v tests.test_factory_turnstile
python3.14 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  tests/test_factory_turnstile.py
git diff --check
```

Finish with exact results and unresolved risks. Do not self-certify.
