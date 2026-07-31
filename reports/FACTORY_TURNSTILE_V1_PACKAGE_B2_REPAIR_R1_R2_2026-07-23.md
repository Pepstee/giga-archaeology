# Factory Turnstile B2 repair R1/R2 — receipt authentication and exact authorisation

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
The current uncommitted B2 candidate on base `c95dd91f69c20e2acfea0c2de351e28be710bccc`
passes 233 tests. Preserve it.

You are the sole writer. Do not spawn subagents, commit, touch production, DFI-05, JAA, another
worktree, or any file except:

```text
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Implement only these two corrections:

1. `run_test(..., suite_kind="full")` must require `authorize_full is True`. Reject `1`, strings,
   objects and every other value.
2. Exact reuse must authenticate the canonical receipt evidence, not merely `lstat` its path.
   Read the receipt file only after proving it is a regular non-symlink file. Require its bytes to
   equal the stable canonical JSON bytes of the exact persisted receipt record. Missing, malformed,
   non-canonical, tampered or symlinked receipt evidence must never be reused; rerun the test.

Strengthen persisted receipt validation only as needed to make that binding trustworthy:

- `key` and `output_sha256` are lowercase 64-character hexadecimal digests;
- recompute `_test_canonical_key(candidate, suite_id, suite_kind, argv, runtime)` and require exact
  equality with `key`;
- require `ts_end >= ts_start`;
- tester leases require actor/provider `host`;
- reject duplicate receipt paths or output paths in persisted state.

Add direct regressions for:

- `authorize_full=1` refusal;
- tampered receipt bytes with intact log force rerun;
- malformed/non-canonical receipt bytes force rerun;
- missing and symlinked receipt file force rerun;
- non-hex digest, canonical-key mismatch, reversed timestamps, non-host tester lease and duplicate
  evidence paths fail closed as corrupt state.

Run:

```bash
python3 -m unittest tests.test_factory_turnstile
python3 -m py_compile factory_control/turnstile.py tests/test_factory_turnstile.py
git diff --check
```

Report exact count and residual risks. Do not self-certify or commit.
