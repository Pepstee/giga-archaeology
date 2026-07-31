# Factory Turnstile v1 — Package C2 functional certification

Date: 2026-07-23  
Worktree: `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`  
Branch: `factory/turnstile-v1`  
Base commit: `5f57e59ce08691d2fb42426c9846fe39572e0870`

## Verdict

**C2 is functionally certified for weighted inter-model allocation reporting and fail-closed
candidate certification.**

This is not certification of the complete Factory Turnstile. The thin CLI/documentation,
authoritative installation and end-to-end adversarial gate remain.

## Certified candidate

```text
c85cd5b1b479a7babc35cefd0281e20ca14fab121e56f9d706e3de1deb3711b4  factory_control/turnstile.py
5050de4057baee3c36005f8844aa032c17f4734e2bf86c163610b1b299dee069  tests/test_factory_turnstile.py
```

Production physical lines before commit:

```text
17    factory_control/__init__.py
1983  factory_control/turnstile.py
2000  total
```

The ratified C2 ceiling is 2,000 production physical lines. The candidate meets it exactly.

## Evidence

- Independent host suite: **388 tests passed**, zero failures/errors.
- `python3 -m py_compile factory_control/__init__.py factory_control/turnstile.py
  tests/test_factory_turnstile.py`: passed.
- `git diff --check`: passed.
- The first read-only Sonnet review returned **CHANGES REQUIRED** and identified unstable return
  ordering and missing actor/provider binding, plus lower-level integrity and coverage gaps.
- A bounded Sonnet repair added exact regressions and stayed within the fixed line ceiling.
- Codex host verification caught one malformed full-suite test call; a one-line Sonnet correction
  restored the mandatory literal authorization instead of weakening production.
- Final read-only Sonnet review verified both hashes and returned **PASS**.
- No writer and reviewer ran concurrently.
- Production orchestrator remained stopped, STOP remained armed, and DFI-05/JAA were untouched.

## Certified behaviour

- Allocation uses only successful persisted Sonnet/Claude and Codex writer/reviewer ledger entries.
  Host test work is excluded.
- Declared positive finite work weights are accumulated across the complete stage history.
- Actor/provider bindings are strict and every accepted review is linked to matching reviewer and
  writer ledger evidence.
- Allocation reports deterministic integer basis points summing to 10,000 and enforce the inclusive
  6,000–8,000 Claude policy.
- Cumulative numeric overflow fails closed.
- Certification requires an unchanged reviewed candidate, at least one independent pass review,
  every named suite's exact current-candidate passing receipt, authenticated canonical receipt
  bytes and descriptor-bound output evidence, plus compliant allocation.
- Receipt choice and all returned lists are deterministically sorted.
- The candidate is recomputed after evidence/allocation verification and immediately before
  certificate construction.
- Canonical certificate bytes contain only stage, candidate, sorted suites, selected receipt keys,
  accepted review UUIDs, allocation and schema version.
- Certificate identity is SHA-256 over exact canonical bytes and installation is fsynced,
  content-addressed and no-clobber.
- Exact idempotent replay verifies and reuses the certificate without rewriting it.
- Certified state cannot carry a lease and deep state corruption fails closed.

## Honest residuals

- State, certificate and event log are separate durable files, not one transaction. If event append
  fails after certificate and certified-state persistence, the operation raises loudly; exact retry
  verifies/reuses the certificate and emits `certification_reused`. This recovery path is tested.
- A state-write failure after certificate installation can leave an unreferenced exact
  content-addressed certificate. It is inert and may be verified/reused later.
- Test execution emits a Python `ResourceWarning` for an unclosed mocked file descriptor in one
  failure-injection path. The 388 tests still complete successfully; this is test-harness hygiene,
  not evidence of a production lease or descriptor leak.
- Allocation weights are declared work units recorded by successful controller operations. They are
  not measured tokens, elapsed time or cognitive effort and must not be presented as such.

## Efficiency relevance

C2 turns the requested 30/70 Sonnet/Codex collaboration into a measurable acceptance policy and
prevents candidate certification unless independent review and exact reusable host evidence bind to
the same unchanged worktree. It therefore makes sequential inter-model collaboration enforceable
without adding a scheduler or duplicating the orchestrator.
