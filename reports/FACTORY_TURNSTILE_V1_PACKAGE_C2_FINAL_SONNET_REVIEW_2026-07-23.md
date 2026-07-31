# Factory Turnstile v1 — Package C2 final independent review

Read only:

```text
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/factory_control/turnstile.py
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/tests/test_factory_turnstile.py
```

Do not edit, run tests, spawn agents, commit, or inspect another worktree. Review the exact candidate:

```text
c85cd5b1b479a7babc35cefd0281e20ca14fab121e56f9d706e3de1deb3711b4  factory_control/turnstile.py
5050de4057baee3c36005f8844aa032c17f4734e2bf86c163610b1b299dee069  tests/test_factory_turnstile.py
```

Base commit: `5f57e59ce08691d2fb42426c9846fe39572e0870`.

Host evidence: 388 tests pass; compile and diff checks pass; production is exactly 2,000 physical
lines, matching the hard C2 ceiling.

Read and assess the complete C2 contract:

`/mnt/c/Users/gutua/FACTORY_TURNSTILE_V1_PACKAGE_C2_ALLOCATION_CERTIFICATION_2026-07-23.md`

Also verify the repaired findings:

- stable sorted return;
- strict actor/provider mapping;
- each review linked to matching reviewer and writer ledger evidence;
- cumulative overflow fails closed;
- second candidate check before persistence;
- real two-receipt deterministic selection;
- explicit recoverable event-write residual.

Inspect for any new regression or bypass introduced by the review/ledger cross-validation,
especially valid historical candidate reviews and all normal `run_review()` paths. Check that the
second candidate computation really detects a mutation after evidence verification, that
certificate bytes and reuse remain deterministic, and that no scope or line-accounting evasion
exists.

Return `PASS` only if C2 is certifiable. Otherwise return `CHANGES REQUIRED` with exact locations
and minimal regressions. State honest residuals separately from defects.
