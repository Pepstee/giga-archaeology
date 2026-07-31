# Factory Turnstile B2 repair R4 — deterministic explicit stop

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
Start from the current uncommitted B2 candidate after R3b. Sole writer; no subagents, commits,
production, DFI-05, JAA, other worktrees, or files outside `factory_control/turnstile.py` and
`tests/test_factory_turnstile.py`.

Fix only the final stop/finalisation race.

`stop()` promises that a successful explicit stop seals the current candidate and leaves the stage
`paused`. Today, if the child exits and `run_test()` clears its lease just before `stop()` takes its
final lock, `stop()` emits `stop_stale_lease` but leaves `reviewed`.

Required invariant after `stop()` returns successfully:

- no live operation or lease remains;
- the current candidate is sealed;
- durable phase is exactly `paused`.

At the final lock:

- if the original lease still exists, clear it and pause as today;
- if no lease exists because original finalisation won the race, and no replacement operation
  exists, seal current candidate and persist `paused`;
- if a different replacement lease exists, fail closed as a concurrency violation and never
  mutate it.

Do not add queues, stop-intent persistence, scheduling or retries unless a deterministic test proves
the simple final-lock rule is insufficient.

Add deterministic barriers/tests for both final-lock orderings, including a tester and at least one
model worker/reviewer path. Replace any test that currently accepts either `paused` or `reviewed`;
after successful stop it must require `paused`.

Preserve every existing test. Run focused unittest, py_compile and `git diff --check`. Report exact
count and risks. Do not self-certify or commit.
