# Factory Turnstile v1 — C2 one-test correction

Work only in:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Sole writer. Do not spawn agents, commit, touch production, DFI-05, JAA or another worktree.

The bounded C2 repair reached 388 tests and exactly 2,000 production lines. Host execution found
one test-construction error:

```text
ERROR: test_receipt_key_selection_is_deterministic
TurnstileError: suite_kind='full' requires authorize_full=True
```

Fix only that call in `tests/test_factory_turnstile.py` by supplying the existing public API's
literal full-suite authorization. Do not change production code or weaken `run_test()`. Then run:

```bash
python3 -m unittest tests.test_factory_turnstile
python3 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  tests/test_factory_turnstile.py
git diff --check
```

Report result and exit. Do not self-certify or commit.
