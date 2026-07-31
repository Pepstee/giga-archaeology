# Factory Turnstile v1 — Package C3 independent Sonnet review

Read only:

```text
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/scripts/factory_turnstile.py
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/tests/test_factory_turnstile_cli.py
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/FACTORY_TURNSTILE.md
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/factory_control/turnstile.py
```

Do not edit, run tests, spawn agents, commit, or inspect another worktree. Review the exact C3 files:

```text
ad6eb153b88f3b0bd49bea901ebc59fced246a28f12b7b7c6a2e0d81b79055a0  scripts/factory_turnstile.py
3d098ba3d239f949465085aa8c3d10c650f7f22df27a8e849e250aa246203be5  tests/test_factory_turnstile_cli.py
aed5382f2422eba581824ed1e8f6d73f22642e0849a9c91ed0bcea235158f4a2  FACTORY_TURNSTILE.md
```

Base commit: `3d49db36f565c8511645d3417d08fe3b839f48fe`.

Host evidence: 427 tests pass; compile/diff checks pass; production is 2,151 physical lines against
the final 2,200-line ceiling.

Assess the complete C3 contract:

`/mnt/c/Users/gutua/FACTORY_TURNSTILE_V1_PACKAGE_C3_CLI_DOCS_2026-07-23.md`

Inspect all CLI dispatch, argument, stdout/stderr and exit-code paths. Verify direct argv is
preserved without shell interpretation and no policy beyond the certified core is duplicated.
Inspect the tests for mocked-away integration failures.

Explicitly resolve these Codex hypotheses:

1. `scripts/factory_turnstile.py` is mode `0644`, despite the contract requiring an executable;
2. `main(argv=None)` lacks the promised `-> int` annotation;
3. docs name a likely nonexistent `openai-codex-review` command, which would be deceptive operator
   guidance;
4. docs claim every failure leaves `paused`, though context/certification validation failures do not
   transition the stage;
5. docs say multiple suite IDs are required when the API requires one or more;
6. docs suggest reinitializing/resetting a control directory even though `init_stage()` refuses an
   existing stage and evidence must not be discarded;
7. child exit code propagation and expected controller error exit 1 are distinguishable and
   truthful;
8. direct executable invocation, repository-root Python invocation, help and importable `main`
   actually work outside mocks;
9. any missing command separator, argument-order, canonical JSON or unsupported-option edge case;
10. any scope creep or undocumented operational assumption.

Return `PASS` only if C3 is certifiable; otherwise `CHANGES REQUIRED`, with exact locations and
minimal regressions. Separate documentation corrections from executable defects.
