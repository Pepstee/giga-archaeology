# Factory Turnstile v1 — Package B2 functional certification

Date: 2026-07-23  
Worktree: `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`  
Branch: `factory/turnstile-v1`  
Base commit: `c95dd91f69c20e2acfea0c2de351e28be710bccc`

## Verdict

**B2 is functionally certified for truthful single-flight test execution and reuse.**

This is not certification of the complete Factory Turnstile. Bounded contexts, work-allocation
certification, CLI/documentation, installation and an end-to-end adversarial gate remain.

## Certified candidate

```text
c9e0e41e99b8943c63c684446bd272064e8b6b141d01e345d4c84364ccfad375  factory_control/turnstile.py
a790ea9d0b842d30118b508d5e972f3fa7769701b2801922e5e490bf49ea3577  tests/test_factory_turnstile.py
```

Production physical lines before commit:

```text
17    factory_control/__init__.py
1689  factory_control/turnstile.py
1706  total
```

## Evidence

- Independent host suite: **271 tests passed**, zero failures/errors.
- `python3 -m py_compile factory_control/turnstile.py tests/test_factory_turnstile.py`: passed.
- `git diff --check`: passed.
- Final read-only Sonnet review verified both hashes and returned **PASS**.
- The Codex-authored PID/PGID cleanup correction passed **267 tests** before R4 and received a
  separate read-only Sonnet **PASS**.
- No model or host test ran concurrently with a mutable writer.
- Production orchestrator remained stopped, STOP remained armed, and DFI-05/JAA were untouched.

## Certified behaviour

- Exact reuse identity binds candidate, suite ID, suite kind, direct argv and runtime identity.
- Reuse requires an exit-zero valid receipt, canonical receipt bytes and descriptor-bound complete
  output evidence.
- Missing, malformed, non-canonical, tampered, symlinked, identity-swapped or hash-mismatched
  evidence is never reused.
- Fresh output is flushed, fsynced and hashed through its original descriptor.
- Full suites require the literal boolean `True`.
- Failed, interrupted and mutation-invalidated receipts are never reused.
- Tester execution uses one exclusive host lease and never enters the model-work ledger.
- Persisted receipts and tester leases are deeply validated; corruption fails closed.
- Post-launch failures terminate/reap the exact child when safe. Live, mismatched, unkillable or
  unprovably reaped children preserve `running`; only proved-reaped children permit lease clearing.
- Replacement leases are never mutated.
- A successful explicit `stop()` always seals the current candidate and ends durably `paused`,
  regardless of final-lock ordering.

## Independent-review repairs

The initial 233-test candidate missed:

1. authentication of canonical receipt-file contents;
2. literal-boolean full-suite authorisation;
3. post-launch evidence/state failure cleanup;
4. deterministic paused state after a stop/finalisation race;
5. descriptor/path swap resistance;
6. bounded streaming of large output logs;
7. PID/start-identity/PGID reuse and unkillable-child handling.

Each defect received a direct regression before this certificate.

## Honest residuals

- If durable state is persistently unwritable, the controller cannot truthfully clear a lease.
  It preserves the original exception and may require explicit recovery/manual intervention.
- Receipt and state files are separately atomic, not transactionally coupled. A crash can leave an
  unreferenced receipt file; it is inert because reuse is driven only by validated state records.
- Process identity relies on Linux `/proc`, matching the Gigabyte WSL2 deployment.
- The complete-controller 1,500-line ceiling is no longer credible: B2 alone is 1,706 production
  lines after required correctness repairs. This certificate does **not** waive that gate. Before
  Package C, perform an evidence-backed budget revision and deletion/refactor pass; do not code-golf
  away safety checks or hide production logic in tests.

## Efficiency observation

Two broad Sonnet repair prompts ran for 20 and 25 minutes respectively and produced no edits; both
were stopped. Splitting the same work into bounded R1/R2, R1b, R3a, R3b, R3b1 and R4 packages
produced reviewable changes. This is direct evidence for fresh bounded context packs and against
monolithic model sessions.
