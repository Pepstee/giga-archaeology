# DFI-05 deletion-refactor order

You are the sole writer in the fresh DFI-05 refactor worktree. Do not commit.

## Starting point

- base: `dcf509753845552a906a5a1a04fcdad754cb6471`
- exact restored patch:
  `e7f7d438d33133c7deebd7894f70cba33df340bac3780603c2501a32a007b125`
- starting production accounting: 358 additions, 10 deletions, net 348
- final ceiling: net at most 350 against the base

Read:

- `docs/efficiency/DFI_05_WORK_ORDER_2026-07-23.md`
- `/home/gutua/software-factory/giga-user/reports/DFI05_INTERMODEL_CONCURRENCY_STOP_CHECKPOINT_2026-07-23.md`
- `/home/gutua/software-factory/giga-user/reports/FABLE_DFI05_POST_CODEX_BUDGET_RULING_2026-07-23.md`
- `/home/gutua/software-factory/.control/dfi-05-deletion-refactor/DFI05_CODEX_FINDINGS_REPAIR_ORDER_2026-07-23.md`

The quarantined overflow patch is read-only:

`/home/gutua/software-factory/.quarantine/dfi-05-post-codex-20260723/DFI05_POST_CODEX_OVERFLOW.patch`

Consult only small relevant hunks as a correctness reference. Never apply it,
copy whole files from it, or use it as the editing base.

## Required sequence

1. Repair repository embedded fallback bindings: parent, project, and intent
   receipt.
2. Repair replay verification: bind task contract, recompute current-slice
   hash, and bind the closed scope including instruction registry, assurance
   contract, findings, and untrusted-data bytes.
3. Move complete fallback/admission/authority validation before model
   invocation. Delete/substitute the schema-only pre-check and any duplicated
   post-response validation; do not layer a second validator.
4. Replace the cohort hash-shape check with canonical seal validation and
   pre-seal/foreign-cohort rejection. Carry minima/ceiling/denominator fields
   for later soak evaluation, but do not implement rate evaluation in DFI-05.

## Gates

- Preserve every original DFI-05 requirement and Fable condition.
- Default off; no config, side store, cache, activation, production change,
  STOP clearing, daemon start, or JAA work.
- Production behavior may not move to tests/docs/scripts.
- Check net production after each finding. If final net is 351 or more, stop
  nonzero and report per-finding line cost—do not weaken or conceal.
- Add negative tests for every repaired mechanism.
- Run direct focused/affected tests only, Ruff, and `git diff --check`.
- No complete suite and no pipelines.
- Exit zero only with exact test counts and final numstat at or below 350.
