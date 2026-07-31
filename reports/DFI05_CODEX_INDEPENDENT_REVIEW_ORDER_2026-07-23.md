# DFI-05 Codex independent review order

Review only. Do not edit, commit, spawn agents, inspect another worktree, or
read recursively from any controller/control directory.

## Bound candidate

- base: `dcf509753845552a906a5a1a04fcdad754cb6471`
- sealed candidate:
  `420519090abe9ec9195bc90ae222156d2fd498dc559ba90d0093a18640446eb6`
- patch SHA-256:
  `e7f7d438d33133c7deebd7894f70cba33df340bac3780603c2501a32a007b125`
- deterministic context:
  `9f5aadf69dcfcf38b2940494aed36e2043e16f0fbb694f0466156f3ab0491955`
- production budget: 358 additions, 10 deletions, net 348; ceiling 350

Read:

- `docs/efficiency/DFI_05_WORK_ORDER_2026-07-23.md`
- the 14 changed files in `git status --short`
- relevant surrounding code from the same worktree only
- `/home/gutua/software-factory/giga-user/reports/DFI05_ARCHITECTURE_REVIEW_2026-07-23.md`
- `/home/gutua/software-factory/giga-user/reports/DFI05_INTERMODEL_CONCURRENCY_STOP_CHECKPOINT_2026-07-23.md`

Do not print or search controller `state.json`, context-pack JSON, JSONL, or
other large generated artifacts. The hashes above are supplied to prevent that
token-bleeding pattern.

## Review requirements

Independently determine whether the dirty implementation completely and safely
satisfies DFI-05:

1. host-only, replay-safe scope admission with closed bindings and no accepted
   pre-authored certificate;
2. authoritative JSONL persistence, idempotency, divergent-reuse refusal, and
   manifest/epoch freeze ordering before any planner claim;
3. exact fallback authorisation and claim gating for missing, malformed, stale,
   conflicting, cross-parent, cross-epoch, or over-broad state;
4. strict bounded `PlanProposal` validation before model invocation and before
   child creation, including correction limits and no parent completion;
5. compiler hard failures cannot become rate-eligible fallbacks;
6. cohort seal identity, denominator/minimum/ceiling semantics, and pre-seal
   rejection are implemented rather than merely documented;
7. default-off behavior, no side store/configuration/cache, and no authority
   duplication;
8. all base call sites and legacy schema consumers remain compatible;
9. production behavior is not hidden in tests/docs, and net production remains
   at most 350.

Run only these direct suites:

```text
pytest -q tests/test_scope_admission_and_fallback.py
pytest -q tests/test_deterministic_scheduling.py tests/test_workflow_adapter.py tests/test_scheduler_decisions_and_boot_matrix.py tests/test_canonical_schema_registry.py
```

Also run Ruff on changed Python files and `git diff --check`. Do not run the
complete suite and do not use pipelines.

Sonnet reports 14 focused plus 86 affected tests passing and no additional
edits. Treat that as an untrusted claim and verify independently.

Return schema-valid JSON only. Use `PASS` only if no required change remains.
Otherwise return `CHANGES_REQUIRED` with precise file/line, mechanism,
regression, and bounded repair.
