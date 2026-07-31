# Factory Turnstile v1 — Sonnet package A

Work only in:
`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Read `reports/FACTORY_TURNSTILE_V1_WORK_ORDER_2026-07-23.md` for the governing contract, but
implement only this first package:

```text
factory_control/__init__.py
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Do not touch any other file. Do not spawn subagents, commit, or run anything beyond
`python3.14 -m unittest -v tests.test_factory_turnstile`, `py_compile` on the three files and
`git diff --check`.

Package A scope:

1. Stable canonical JSON, locked transitions, atomic `state.json`, append-only `events.jsonl`.
2. Exact Git candidate identity over HEAD plus every tracked/non-ignored-untracked path, content,
   mode/type and symlink target; reject escapes and special files.
3. `Turnstile` construction plus `init_stage()` and read-only `status()`.
4. Exclusive `run_worker()` using direct argv, a UUID lease, recorded actor/provider/role,
   child PID/start identity/process group/command/candidate-before, and real exit status.
5. On successful worker exit, seal candidate and add a weighted model-work ledger entry. On
   non-zero/interruption, seal and pause.
6. `recover()` refuses a live matching process and recovers only a dead/reused PID lease, sealing
   and pausing.
7. `pause()` refuses a live operation.
8. `stop()` sends SIGINT to the active process group, waits a bounded timeout, then SIGTERM,
   records the stop and leaves the stage paused.
9. Focused tests for stable/sensitive candidate identity, corrupt-state refusal, live-operation
   exclusion, real non-zero propagation, dead/live recovery, pause and stop.

Expose clean Python methods first; do not implement the CLI, review, tests, context packing,
allocation certification or documentation yet. Leave clear extension seams without placeholders
or fake success.

Finish with exact files, line counts and focused results. You are the sole writer for this turn.
