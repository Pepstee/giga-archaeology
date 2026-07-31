# Factory Turnstile — Fable pre-activation repair

Work only in the worktree supplied as your current directory. You are the sole writer. Do not spawn
agents, commit, touch authoritative `giga-user`, orchestrator-v3, DFI-05, JAA or another worktree.

Starting head:

`938b42d392ff4ac4df39492ff28f5dc398192d45`

Read:

```text
reports/FABLE_FACTORY_TURNSTILE_V1_FINAL_AUTHORITY_RESULT_2026-07-23.md
factory_control/turnstile.py
scripts/factory_turnstile.py
tests/test_factory_turnstile.py
tests/test_factory_turnstile_cli.py
FACTORY_TURNSTILE.md
```

Implement only the two Fable pre-activation blockers.

## F1 — deterministic stop phase

In `stop()`'s pre-signal stale-lease race, when the original lease has already finalized and the
current lease is now `None`, seal the current candidate and force durable `phase="paused"` before
returning success. Preserve replacement leases untouched. Make this branch agree with the existing
final-lock branch.

Add a deterministic regression based on `TestStopStaleBranchConcurrency` where the liveness probe
simulates the original operation finalizing to `lease=None, phase="sealed"`. Assert:

- `stop()` returns normally;
- final phase is `paused`;
- lease remains `None`;
- current candidate is sealed;
- no replacement lease is changed;
- terminal event is truthful.

## F2 — truthful CLI operational errors and signal exits

- Treat `OSError` raised by the core (including nonexistent child executable) as an expected
  operational CLI failure: canonical compact sorted-key JSON on stderr, no success JSON on stdout,
  exit 1.
- Preserve the raw child return code in stdout JSON.
- Map a negative child return code `-N` to the CLI process status `128 + N`; leave ordinary 0–255
  child exits unchanged.
- Use one small shared helper for worker/review/test return mapping.
- Do not catch unexpected programming errors as normal success.
- Do not weaken core launch failure handling.

Add regressions for:

1. real Turnstile worker launch of a definitely nonexistent executable: stage fails closed,
   canonical stderr JSON, no stdout, CLI exit 1;
2. mocked worker/review/test raw return `-9`: stdout retains `exit_code=-9`, `main()` returns 137;
3. ordinary child exit 1 and 2 remain 1 and 2.

Update `FACTORY_TURNSTILE.md`:

- operational `TurnstileError`/`OSError` use stderr JSON and exit 1;
- negative signal return `-N` maps to process status `128+N` while JSON preserves raw `-N`;
- child exit 1/2 is distinguished from controller/argparse 1/2 by stdout result JSON versus stderr
  error/usage output;
- candidate immutability means git-visible content; ignored cache/build artifacts are outside the
  snapshot;
- keep the accepted process-group/runtime-identity/control-lock residuals concise.

## Boundary and gates

- No scheduler, retries, routing, prompt generation, model/provider choice, token policy or daemon.
- Complete production remains at most 2,200 physical lines.
- Preserve all 431 tests.

Run:

```bash
python3 -m unittest tests.test_factory_turnstile tests.test_factory_turnstile_cli
python3 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  scripts/factory_turnstile.py tests/test_factory_turnstile.py tests/test_factory_turnstile_cli.py
git diff --check
```

Report exact tests, production lines, hashes and residuals. Do not self-certify or commit.
