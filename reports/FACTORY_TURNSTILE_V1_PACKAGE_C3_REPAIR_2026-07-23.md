# Factory Turnstile v1 — Package C3 bounded repair

Work only in:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

You are the sole writer. Do not spawn agents, commit, touch production, DFI-05, JAA, another
worktree, or files outside:

```text
scripts/factory_turnstile.py
tests/test_factory_turnstile_cli.py
FACTORY_TURNSTILE.md
```

Preserve all 427 tests and the C3 scope. Do not modify `factory_control/`.

Apply only:

1. set `scripts/factory_turnstile.py` mode to executable (`0755`);
2. change the public signature to `main(argv=None) -> int`;
3. add regressions proving:
   - the tracked script has a user execute bit;
   - direct `./scripts/factory_turnstile.py --help` works from repository root;
   - `python3 scripts/factory_turnstile.py --help` works from repository root;
   - imported `main` has return annotation `int`;
4. remove the nonexistent `openai-codex-review` example. Do not replace it with another invented
   binary or placeholder. Keep the truthful generic `review ... -- COMMAND [ARG...]` example and
   explain that the operator supplies the real read-only reviewer argv installed on that host;
5. correct the purpose text and state diagram: only worker/review/test process failures pause.
   Preconditions and validation failures for init/context/certify/recover/pause/stop raise without
   claiming a phase transition;
6. change “Multiple suite IDs are required” to “One or more suite IDs are required”;
7. remove reset/re-initialize guidance. State that `init` refuses an existing stage; preserve/archive
   its control directory and use a new empty control directory for a new stage. Never recommend
   deleting evidence as a routine recovery step.

Production remains at most 2,200 physical lines. Run:

```bash
python3 -m unittest tests.test_factory_turnstile tests.test_factory_turnstile_cli
python3 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  scripts/factory_turnstile.py tests/test_factory_turnstile.py tests/test_factory_turnstile_cli.py
git diff --check
```

Report exact tests, production lines, hashes and file mode. Do not self-certify or commit.
