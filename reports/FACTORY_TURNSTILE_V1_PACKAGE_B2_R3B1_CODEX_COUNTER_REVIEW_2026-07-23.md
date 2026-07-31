# Read-only Sonnet counter-review — B2 R3b1 Codex correction

Review only. Worktree:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Expected exact hashes:

```text
400cbb86465c704a863f00fdcf85916719f4d7b060a16b7ef4234c68fa35c2cf  factory_control/turnstile.py
339a67c82155d11183c3ec543877f6af0fda7af4fb656c740e5393f2fb4c7c3a  tests/test_factory_turnstile.py
```

Independent host evidence: 267 tests passed; py_compile and `git diff --check` passed.

Do not edit, commit, run the complete suite, spawn subagents, or touch production, DFI-05, JAA or
another worktree.

Review the actual code around `_cleanup_tester_postlaunch` and the
`TestCleanupTesterIdentityGuard` tests. The Codex correction changed the invariant to:

- `proc is None` means the caller already reaped the child and may clear the matching lease;
- otherwise `proc.poll()` or `proc.wait()` must prove the direct child reaped;
- a live identity/PGID mismatch, failed wait, or any ambiguity preserves the matching lease and
  durable `running`;
- signalling occurs only after exact PID start-identity and PGID agreement;
- a replacement lease is never changed.

Check for false clearing, signalling a reused target, zombie leakage, swallowed live-child states,
replacement-lease mutation, and test gaps. You may run only targeted read-only inspections or
named individual tests; do not mutate files.

Return `PASS` or `CHANGES REQUIRED` with precise evidence. This is a supplied-evidence
counter-review, not certification.
