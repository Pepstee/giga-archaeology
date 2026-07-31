# Factory Turnstile Package A — Sonnet counter-review

Operate read-only in:
`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Do not edit, write, run tests, spawn subagents, commit, or touch another worktree. Read:

```text
factory_control/__init__.py
factory_control/turnstile.py
tests/test_factory_turnstile.py
reports/FACTORY_TURNSTILE_V1_WORK_ORDER_2026-07-23.md
reports/FACTORY_TURNSTILE_V1_SCOPE_BUDGET_ADDENDUM_2026-07-23.md
```

The sealed candidate identity before review is:
`d58dc0b60453df6318a056a8a25825c6ba6d06276c92097d34baed3dc6b313c2`.

Independent host evidence already obtained:

- `python3.14 -m py_compile`: pass
- focused suite: 94/94 pass
- pre/post source hashes unchanged
- Package A production: 845 physical lines including exports

Review Package A line by line for correctness against its current scope only: durable state,
candidate identity, exclusive worker lease, launch failure, recovery, pause and bounded stop.
Pay particular attention to fail-closed behaviour, process identity/PGID reuse, state/lease
consistency, stop races, event truthfulness, and whether tests merely mirror implementation.

Return:

1. `PASS` or `CHANGES_REQUESTED`;
2. each material finding with severity, exact file/line and a reproducible failure scenario;
3. any non-blocking limitation that belongs to later packages;
4. whether Package A may freeze and Package B begin.

Do not treat line count, formatting preference or hypothetical hostile tampering as a blocker.
Do not self-report test success because you are not authorised to run tests.
