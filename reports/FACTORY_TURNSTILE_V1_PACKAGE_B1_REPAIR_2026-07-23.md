# Factory Turnstile v1 — Package B1 repair

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
You are the sole writer. Preserve the Package A commit and all 141 currently passing tests. Do not
spawn subagents, commit, touch another worktree, or implement test receipts/contexts/CLI.

Edit only:

```text
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

## Required repair

1. **Remove lifecycle duplication.** `run_worker()` and `run_review()` currently duplicate process
   launch, PID/PGID/start-identity recording, launch-failure cleanup and interrupted wait. Extract
   small private helpers used by both without weakening Package A semantics. Keep role-specific
   finalisation in the public methods. Target the complete production module at **1,000 lines or
   fewer** after refactoring; do not compress readability or tests to hit it.
2. **Fail closed on candidate corruption.** Validate candidate as null or a dict with non-empty
   SHA-256-like hash/head/worktree strings and a list of file records before callers use `.get`.
   Require a non-null candidate in `sealed`, `reviewed` and `changes_requested` phases.
3. **Fail closed on ledger corruption.** Every ledger item must be a dict with non-empty actor,
   provider, role, candidate and UUID strings, finite positive weight and numeric timestamp.
   Validate writer/reviewer roles used by this package.
4. **Fail closed on review corruption.** Validate every review record deeply: exact verdict,
   reviewer/writer actors, direct non-empty argv, exit code exactly zero for accepted reviews,
   finite positive weight, numeric timestamp, non-empty candidate/lease UUID, and reviewer
   different from writer.
5. `status()` must not raise incidental `KeyError`, `AttributeError` or `TypeError` for persisted
   malformed state; malformed state must raise `CorruptStateError`.
6. Preserve exact behaviour already tested: independent reviewer, mutation violation, exact exit
   code, launch failure cleanup, stop/recover compatibility and historical-candidate isolation.

Add representative adversarial state tests for each validation boundary. Run only the focused
unittest module, py_compile and `git diff --check`. Report exact line count, test result and
unresolved risks; do not self-certify.
