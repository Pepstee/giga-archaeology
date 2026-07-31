# Factory Turnstile v1 B2 — final read-only Sonnet review

Review only. Worktree:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Base commit:

`c95dd91f69c20e2acfea0c2de351e28be710bccc`

Expected exact hashes:

```text
c9e0e41e99b8943c63c684446bd272064e8b6b141d01e345d4c84364ccfad375  factory_control/turnstile.py
a790ea9d0b842d30118b508d5e972f3fa7769701b2801922e5e490bf49ea3577  tests/test_factory_turnstile.py
```

Independent host evidence: 271 tests passed; py_compile and `git diff --check` passed.

Do not edit, commit, run the complete suite, spawn subagents, or touch production, DFI-05, JAA or
another worktree.

Review the complete uncommitted B2 delta from `c95dd91`, not merely its self-reports. Required B2
contract:

- reviewed unchanged candidate and exact pass review preconditions;
- one exclusive host tester lease;
- canonical key binds candidate/suite/kind/argv/runtime;
- only exact exit-zero valid receipts with descriptor-bound canonical receipt and complete output
  evidence may be reused;
- fresh output hash binds the original descriptor;
- failures and mutations are never reused;
- full suites require literal boolean `True`;
- malformed receipt state fails closed;
- post-launch failures cannot hide a live child or strand a matching dead lease when persistence is
  available;
- explicit successful stop always ends paused;
- replacement leases are never changed;
- host tests never enter the model-work ledger.

Inspect especially:

- state/receipt canonical binding and evidence identity;
- open/fsync/hash/receipt/state crash windows;
- PID/start-identity/PGID reuse;
- cleanup and stop races;
- exact exception/exit-code truthfulness;
- test gaps that could permit a false pass or unsafe reuse;
- unintended scheduler/queue/retry/orchestration scope.

Return `PASS` or `CHANGES REQUIRED`, with precise file/line evidence and severity. Do not propose
style-only expansion. This is independent review, not certification.
