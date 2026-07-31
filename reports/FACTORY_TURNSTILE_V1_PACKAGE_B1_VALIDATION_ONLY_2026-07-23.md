# Factory Turnstile v1 — B1 persisted-state validation only

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
You are the sole writer. Preserve all 141 passing tests. Edit only:

```text
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Do not refactor process lifecycle and do not implement later packages. Implement only:

1. Candidate must be null or a dict with non-empty hash/head/worktree strings and a list of file
   records; `sealed`, `reviewed` and `changes_requested` require a non-null candidate.
2. Every ledger item must be a dict with non-empty actor/provider/role/candidate/UUID strings,
   finite positive weight and numeric finite timestamp. Role must be `writer` or `reviewer`.
3. Every accepted review must deeply validate: exact verdict, reviewer/writer actors, reviewer
   different from writer, non-empty direct argv, exit code exactly zero, positive finite weight,
   finite timestamp and non-empty candidate/lease UUID.
4. Malformed persisted state must raise `CorruptStateError`, never incidental Python exceptions.

Add representative adversarial tests. Run only the focused unittest module, py_compile and
`git diff --check`. Report exact results and production line count; do not self-certify.
