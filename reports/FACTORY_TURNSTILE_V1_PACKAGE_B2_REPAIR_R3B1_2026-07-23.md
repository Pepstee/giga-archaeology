# Factory Turnstile B2 repair R3b1 — cleanup target identity and live-child refusal

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
Preserve the current uncommitted 260-test candidate. Sole writer; no subagents, commits, production,
DFI-05, JAA, other worktrees, or files outside `factory_control/turnstile.py` and
`tests/test_factory_turnstile.py`.

Fix only two independently found flaws in `_cleanup_tester_postlaunch`:

1. It calls `killpg` even when the direct child may already have exited, so a rapidly reused PGID
   could be signalled. Pass/use the child PID and captured process-start identity. Before every
   first signal, prove the direct child is still alive with that identity and still belongs to the
   captured PGID. If the child is already dead/reaped or identity/PGID no longer matches, never
   signal that group.
2. After bounded SIGTERM→SIGKILL, it swallows a failed `proc.wait()` and clears the lease anyway.
   Never clear the matching lease while the exact child/group remains live or cannot be proved
   dead. Record a cleanup-failed event where possible and leave durable `running` state for explicit
   `stop`/recovery/manual intervention. Only clear and pause after the child is proved dead/reaped.

Also do not silently swallow `out_f.close()` failure after an otherwise successful test evidence
finalisation; route it through the same matching-lease fail-closed cleanup.

Add deterministic tests for:

- already-exited direct child: no `killpg` call;
- mismatched start identity or PGID: no signal to the stale/reused group;
- simulated unkillable child/group: matching lease remains and controller does not claim paused;
- successful termination/reap still clears matching lease and pauses;
- output close failure invokes cleanup and re-raises.

Preserve all 260 tests. Run focused unittest, py_compile and `git diff --check`; report exact results
and risks. Do not self-certify or commit.
