# Factory Turnstile v1 — Package C3 final independent review

Read only:

```text
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/scripts/factory_turnstile.py
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/tests/test_factory_turnstile_cli.py
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/FACTORY_TURNSTILE.md
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/factory_control/turnstile.py
```

Do not edit, run tests, spawn agents, commit, or inspect another worktree. Review the exact C3 files:

```text
a9f40e1a63300b1c35a42273cbaefba24ae2340abaa999d12b2ca66728a22342  scripts/factory_turnstile.py
3c7d84291a52a0a69eac362c9a471d5ae723012a265bccd87a08f4e95e2d1834  tests/test_factory_turnstile_cli.py
db634c0e6d91133e04ac0b168c136605f78b173fdb6fb23c994515921b232d42  FACTORY_TURNSTILE.md
```

Script mode: `0755`.  
Base commit: `3d49db36f565c8511645d3417d08fe3b839f48fe`.

Host evidence: 431 tests pass; compile/diff checks pass; production is 2,151 physical lines against
the final 2,200-line ceiling.

Verify the complete C3 contract and all repaired findings:

- executable mode and direct invocation;
- `main(argv=None) -> int`;
- no fictitious operator command;
- truthful failure/phase documentation;
- one-or-more suite wording;
- evidence-preserving new-stage guidance;
- canonical stdout/stderr JSON and exact exit codes;
- direct argv and no shell;
- no hidden scheduler/provider/model/retry policy or scope creep.

Return `PASS` only if C3 is certifiable. Otherwise return `CHANGES REQUIRED` with exact locations
and minimal regressions. State residuals separately.
