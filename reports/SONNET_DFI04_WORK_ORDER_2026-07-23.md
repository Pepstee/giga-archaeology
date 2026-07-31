# DFI-04 Sonnet implementation work order

Date: 2026-07-23

## Authority and roles

- Fable is the technical authority for architectural uncertainty and milestone assessment.
- Sonnet is the default implementation workforce.
- Codex coordinates scope, preserves checkpoints, reviews integration, runs independent gates, and maintains evidence.
- Do not spawn subagents. Work directly and keep the task bounded to this work order.

## Exact scope

Authoritative worktree:

`/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-04`

Baseline:

- branch: `di/dfi-04-task-adapter`
- HEAD: `274c6d0d68209084aa8ee3bf3265672f67c0bb02`
- tree: `3ce0646f0254b45726860345e470c037a0e869fa`

The uncommitted six-file WIP was transferred byte-for-byte from the reviewed Mac mirror. Preserve it and repair it in place.

Hard constraints:

- Work only in the DFI-04 worktree.
- Do not modify production.
- Do not touch JAA.
- Do not remove or weaken STOP.
- Do not activate, merge, push, or deploy.
- Do not commit; Codex will review and integrate.
- No stubs, placeholders, mocks standing in for required behaviour, source-text-only tests, or suppressed failures.
- Net added production lines against HEAD must be at most 500. Tests do not count.
- If the architecture becomes uncertain, stop with a precise question for Fable instead of improvising.

## Fable ruling

Development is GO on top of the WIP. Merge, certification, and production activation are NO-GO until all defects and evidence requirements below are resolved.

The architecture already judged sound includes:

- idempotent crash re-settlement;
- durable, schema-sealed scheduler-profile adoption;
- durable scheduler decisions;
- mutation-free prechecks before parent claim;
- deterministic task identity recomputation;
- STOP checks between admissions.

### Required repairs

1. Epoch-safe planner rollback

   A source commit rotates the factory epoch and currently wedges any adopted non-planner profile. Permit a replacement whose mode is `planner` to cross epochs because this reduces authority. Keep STOP, reconciliation, record/replacement epoch equality, and profile-chain continuity. Shadow or active adoption across epochs must still refuse.

2. Existing-test verification correctness

   - Deduplicate files matched by overlapping `test_resources` globs before tokenising.
   - Deduplicate verified coverage claims shared by multiple findings.
   - Remove the strip/raw asymmetry: operate on the exact raw claim.
   - Preserve path containment and unique-match rules.

3. Project-root confinement

   Never fall back to the factory root when `root/projects/<project>` is absent. Resolve beneath `root/projects`, refuse missing or escaping roots with `existing_coverage_unverified`, and leave the parent queued/fallback-eligible.

4. Adoption CLI authority discipline

   - Make `ProfileAdoptionRefusal` a real `RuntimeError` subclass.
   - Take `legacy_daemon_leadership(root)` during adoption.
   - Translate leadership unavailability into a bounded adoption refusal.
   - Re-check STOP immediately before the durable adoption append.

5. Corrupt-adoption replay must fail closed

   If replay cannot ingest a `scheduler_profile_adopted` event, mark adoption state corrupt. `active_scheduler_profile()` must refuse instead of silently exposing a stale adoption. Daemon boot must convert that into `BootRefusal`.

6. Robust trigger handling

   Guard raw finding elements before calling `.get(...)`; do not rely on an upstream validation side effect.

### Required trims

- Remove duplicate binding-id recomputation from `_validate_supplied_tasks`; schema validation already enforces it.
- Remove `record_type` from `scheduler_decision`; derive the embedded record schema from `kind` and whether `record` is absent.
- Keep required production changes within the 500-net-line budget.

### Contract changes to preserve and report for ratification

- `existing:` recognition is currently case-insensitive.
- Shadow bundles now require durable profile adoption rather than env-only activation.

## Required behavioural evidence

Add real behavioural tests, including:

1. Scheduler-profile adoption

   Chain continuity, dedupe, discontinuity refusal, replay reconstruction, first-adoption planner anchor, planner rollback across a rotated epoch, and cross-epoch shadow/active refusal.

2. Deterministic re-settlement

   Rebuild the repository after each durable crash window: after CLAIM, `tasks_spawned`, KB write, `task_result`, and COMPLETE. Assert one child set, one KB entry, one successful result, and a DONE parent.

3. Daemon boot/adoption

   Real bounded daemon boots where feasible: bundle without adoption refuses; non-planner adoption without bundle refuses; planner adoption boots; corrupt adoption refuses; STOP between admissions halts further mutation.

4. Scheduler decisions

   Persist every decision kind, dedupe across cycles and restarts, validate embedded batches, and cover fallback with and without a typed record.

5. Existing-test claims

   Overlapping globs, shared claims, padded claims, missing tests, ambiguous bare names, and symlink/path escape.

6. Adoption CLI

   Leadership contention refuses; STOP disappearance immediately before append refuses.

Update old tests to the new contract; do not weaken the new contract to preserve stale expectations.

## Verification

Run:

- the focused DFI-04 suites;
- repository, settlement, spawned-task, daemon, workflow adapter/compiler, schema, epoch, and deterministic scheduling suites affected by the diff;
- Ruff over every changed Python file;
- `git diff --check`;
- production-line accounting against HEAD.

Return:

- exact changed-file list;
- exact pass/fail/skip counts and commands;
- line-budget calculation;
- unresolved risks or Fable questions;
- confirmation that production, STOP, JAA, activation, merge, push, and commit were untouched.
