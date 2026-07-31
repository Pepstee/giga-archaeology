# Factory Turnstile v1 — Package C3 functional certification

Date: 2026-07-23  
Worktree: `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`  
Branch: `factory/turnstile-v1`  
Base commit: `3d49db36f565c8511645d3417d08fe3b839f48fe`

## Verdict

**C3 is functionally certified for thin deterministic CLI exposure and truthful operator
documentation.**

This completes package implementation. Authoritative installation and the end-to-end adversarial
gate still remain before operational use.

## Certified candidate

```text
a9f40e1a63300b1c35a42273cbaefba24ae2340abaa999d12b2ca66728a22342  scripts/factory_turnstile.py
3c7d84291a52a0a69eac362c9a471d5ae723012a265bccd87a08f4e95e2d1834  tests/test_factory_turnstile_cli.py
db634c0e6d91133e04ac0b168c136605f78b173fdb6fb23c994515921b232d42  FACTORY_TURNSTILE.md
```

Script mode: `0755`.

Complete production physical lines before commit:

```text
17    factory_control/__init__.py
1983  factory_control/turnstile.py
151   scripts/factory_turnstile.py
2151  total
```

The ratified complete-controller ceiling is 2,200 production physical lines. The candidate is 49
lines below it.

## Evidence

- Independent host suite: **431 tests passed**, zero failures/errors.
- `python3 -m py_compile` over core, CLI and both test modules: passed.
- `git diff --check`: passed.
- Direct executable invocation and repository-root Python invocation both passed in subprocess
  regressions.
- Initial read-only Sonnet review returned **CHANGES REQUIRED** for missing execute mode, absent
  return annotation and four documentation inaccuracies.
- Bounded Sonnet repair corrected all six findings and added four real invocation regressions.
- Final read-only Sonnet review verified the exact hashes and mode and returned **PASS**.
- No writer and reviewer ran concurrently.
- Production orchestrator remained stopped, STOP remained armed, and DFI-05/JAA were untouched.

## Certified behaviour

- Exactly eleven explicit subcommands expose the certified core API.
- Worker, reviewer and tester child commands remain direct argv; no shell evaluates command text.
- Actor, verdict, suite kind and required options are constrained by argparse and the core remains
  authoritative.
- Full-suite authorization is forwarded as a literal boolean.
- Successful output and expected controller errors are canonical compact sorted-key JSON on
  separate stdout/stderr channels.
- Child process exit codes propagate; argparse remains exit 2; expected controller errors are
  exit 1.
- CLI help states the immutable non-goal boundary.
- Documentation accurately describes phases, recovery, allocation semantics, evidence, reuse,
  certification, STOP/isolation preconditions and non-goals.
- The manual contains no invented reviewer binary and gives evidence-preserving new-stage guidance.

## Honest residuals

- The CLI is still a candidate-worktree artifact and is not authoritative or active until the
  installation gate succeeds.
- No controlled DFI workload has yet measured real token/time savings; documentation makes no such
  claim.
- The existing failure-injection suite emits one Python mocked-file `ResourceWarning` while all 431
  tests complete successfully.

## Efficiency relevance

C3 makes the certified collaboration primitives operable without embedding another planner,
scheduler or model router. It provides the narrow control surface required to resume DFI work while
preserving single-flight execution, exact evidence reuse and 30/70 allocation accountability.
