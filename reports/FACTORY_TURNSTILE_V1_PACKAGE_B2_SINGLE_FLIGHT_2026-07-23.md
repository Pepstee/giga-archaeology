# Factory Turnstile v1 — Package B2: truthful single-flight tests

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
Base commit: `c95dd91f69c20e2acfea0c2de351e28be710bccc`.

You are the sole writer. Do not spawn subagents, commit, touch production, DFI-05, JAA or another
worktree. Edit only:

```text
factory_control/__init__.py
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Preserve all 183 tests. Implement truthful single-flight tests only; do not implement contexts,
allocation certification, CLI or documentation.

## Public contract

Add:

```python
run_test(
    suite_id: str,
    suite_kind: str,              # "focused" or "full"
    command: list[str],
    runtime_identity: str,
    authorize_full: bool = False,
) -> dict
```

Return:

```python
{"exit_code": int, "reused": bool, "receipt": dict}
```

## Preconditions and exclusivity

- Require phase `reviewed`, an unchanged sealed candidate, and an accepted `pass` review for that
  exact candidate.
- Reject any existing lease. A live writer/reviewer/test therefore blocks a test.
- Validate non-empty suite/runtime IDs and direct non-empty argv.
- `suite_kind` must be `focused` or `full`; `full` requires `authorize_full is True`.
- Host test execution is not model work and must not enter the model ledger.

## Exact reuse

- Build a canonical SHA-256 key from candidate hash, suite ID, suite kind, argv and runtime
  identity.
- Under the lock, search existing receipts for that exact key.
- Reuse only an exit-zero, valid receipt whose canonical receipt file and complete output log both
  still exist as regular non-symlink files inside `control_dir/evidence`, whose hashes/content
  exactly match the stored record.
- Never reuse failures, invalid receipts, a different candidate, suite, argv, kind or runtime.
- Reuse launches no child and appends a `test_reused` event.

## New execution

- Record a UUID lease with actor/provider `host`, role `tester`, command, suite metadata,
  candidate-before, PID/start identity/PGID.
- Reuse the shared direct child lifecycle; extend the helper safely to accept output redirection.
- Execute in the governed worktree with no shell or pipeline.
- Capture complete merged stdout+stderr to a uniquely named binary evidence log; flush and fsync.
- Preserve the exact child exit code regardless of output text.
- Hash the output log and write a canonical atomic receipt JSON binding:
  key, candidate, suite ID/kind, argv, runtime, timestamps, exit code, output SHA-256/path,
  receipt path, lease UUID and validity.
- Append the receipt to state. A normal pass or failure returns to `reviewed`; an interruption
  pauses. Failures remain recorded but are never reusable.
- Any candidate mutation during the test writes a `valid=false` receipt, updates the candidate,
  clears only the matching lease, pauses, appends a mutation event and raises `TurnstileError`.
- Launch/evidence failures fail closed without a stranded lease.

## Validation and status

- Deeply validate persisted receipt records; malformed receipt state raises `CorruptStateError`.
- Validate evidence paths as safe relative paths with no traversal.
- `status()` reports receipt count and passing-valid receipt count without mutation.
- `stop()` and `recover()` must remain role-agnostic and work for a real tester lease.

## Required tests

1. output claiming success with real non-zero exit remains failed;
2. stdout and stderr are both present in the complete evidence log;
3. exact pass rerun reuses the receipt and does not relaunch (use a counter file);
4. failed receipt reruns and increments the counter;
5. every key-field change prevents reuse;
6. full suite requires explicit authorisation;
7. concurrent/live operations block test;
8. test-time mutation invalidates evidence and pauses;
9. pre-test candidate change or missing pass review refuses;
10. tampered/missing/symlinked receipt or output evidence is never reused;
11. launch failure and stop/recover tester paths fail closed;
12. corrupt receipt records fail closed;
13. all 183 earlier tests remain green.

Use Python 3.14 standard library only. Keep code clear and within the ratified narrow scope; target
the complete production controller at 1,400 lines or fewer for B2. Run only the focused unittest
module, py_compile and `git diff --check`. Report exact results/line count/risks; do not
self-certify.
