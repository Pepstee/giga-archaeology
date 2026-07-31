# Factory Turnstile v1 — Package A final repair 1/2

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
You are the sole writer. Do not spawn subagents, commit, or touch any file except:

```text
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Preserve the 54 passing tests. Implement only:

1. `run_worker()` must refuse whenever `state["lease"]` is non-null, even if the PID is dead or
   reused. The error must direct the operator to explicit `recover()`. Test that a dead-PID lease
   blocks a writer until recovery, then permits it after recovery.
2. `_load_state()` must reject `running` without a lease and every non-running phase with a lease.
   Validate required lease fields `actor`, `command`, `pgid`, `pid`, `provider`, `role`,
   `start_identity`, `uuid`, and `candidate_before` with safe basic types before signalling.
   Add focused corrupt-state tests.
3. Reject a control directory equal to or inside the governed worktree before creating anything.
   Add tests for equal, nested and valid sibling placement.
4. `stop()` must reject non-numeric, non-finite and negative timeout values. Zero is allowed.
   Add focused tests.

Do not alter stop escalation semantics in this package. Do not implement later features. Run only
the focused unittest module, py_compile and `git diff --check`. Report exact results and production
line count; do not self-certify.
