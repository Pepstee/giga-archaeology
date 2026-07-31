# Fable assessment brief — orchestrator v3 deterministic infrastructure

Date: 23 July 2026  
Requested reviewer: Claude Fable 5  
Review mode: read-only, adversarial, evidence-first  
Code changes authorised: none  
Factory activation authorised: none  
JAA work authorised: none

## Verdict and checkpoint

Codex stopped implementation at the end of an **uncertified DFI-04 checkpoint**. The exact
checkpoint is preserved on both machines. It is not production, not activated, and not represented
as a completed slice.

The authoritative Gigabyte checkpoint is:

- Host: Gigabyte, Windows host with WSL/Linux factory runtime.
- Worktree:
  `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-04`
- Branch: `di/dfi-04-task-adapter`
- Commit: `274c6d0d68209084aa8ee3bf3265672f67c0bb02`
- Tree: `3ce0646f0254b45726860345e470c037a0e869fa`
- Git state at handoff: clean.
- STOP: armed.
- Factory/orchestrator processes: zero.

The exact Mac verification mirror is:

- Directory: `/tmp/orchestrator-v3-dfi02.Jh3sKl/repo`
- Branch: `local/dfi-04-task-adapter`
- Commit: `e879ff20e241c1b2c6bc5b7b75428194be68159d`
- Tree: `3ce0646f0254b45726860345e470c037a0e869fa`
- Git state at handoff: clean.

The different commit IDs are expected: the commits have different parents, but the tree IDs and
all ten transferred file SHA-256 values are identical.

Checkpoint verification on both Mac and Gigabyte:

- Focused tests: **85 passed**.
- Targeted Ruff: passed.
- `git diff --check`: passed.
- This is focused checkpoint evidence only. No DFI-04 full-suite, wave-promotion, activation,
  production, or JAA certification claim is made.

Production remains untouched:

- Authoritative checkout:
  `/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3`
- Branch: `efficiency/e2-shadow-cache`
- Commit: `35efb19b07867bb58e1288479513078cf9ab65e4`
- STOP: armed.
- No DFI branch has been merged into production.

## What `giga-user` is

`giga-user` is not the orchestrator product repository and is not merely a memory folder. It is
Artiom's model-agnostic operator/governance layer and personal AI infrastructure workspace. It
contains:

- the standing operator charter and context protocols;
- laws, gates, deterministic-assurance doctrine and machine-facing contracts;
- architecture plans, audit reports, migration receipts and session logs;
- skills and SkillTree implementation records;
- personal-memory/Jarvis and digital-twin systems;
- corpus preparation and fine-tuning machinery;
- career, Korean, travel and other operator-specific systems;
- project-side support material for the orchestrator, JAA and market-aligner.

The governing entry points on the Mac are:

- `/Users/admin/Documents/giga-user/00_MASTER.md`
- `/Users/admin/Documents/giga-user/01_CHARTER_BRIEF.md`
- `/Users/admin/Documents/giga-user/CHARTER.md`
- `/Users/admin/Documents/giga-user/CONTEXT.md`
- `/Users/admin/Documents/giga-user/AGENTS.md`

The complete deterministic-infrastructure design under review is:

- `/Users/admin/Documents/giga-user/architecture/ORCHESTRATOR_V3_DETERMINISTIC_INFRASTRUCTURE_PLAN_2026-07-22.md`
- `/Users/admin/Documents/giga-user/architecture/ORCHESTRATOR_V3_DISPROPORTIONATE_SPEED_RETURNS_2026-07-22.md`

Machine responsibility is intentionally split:

- **Mac:** primary home for `giga-user` personal context, private corpora/exports, Jarvis/digital
  twin and market-aligner. The Mac retains a usable but non-authoritative orchestrator copy.
- **Gigabyte:** dedicated software-factory host. It owns authoritative orchestrator development,
  isolated DFI worktrees and eventual JAA development/execution.
- **Gigabyte's migrated `giga-user`:**
  `/home/gutua/software-factory/giga-user`. This is the factory-side governance/harness copy. It
  exists so the factory carries Artiom's laws, gates, reports, skills and deterministic-assurance
  infrastructure. Private exports/corpora are not supposed to be factory inputs.

Do not confuse these repositories:

- Orchestrator engine: `agentic-orchestrator/projects/orchestrator-v3`.
- JAA product checkout nested under the production engine:
  `agentic-orchestrator/projects/orchestrator-v3/projects/job-application-automation`.
- Additional project/support material may exist under `giga-user/job-application-automation`;
  it is not automatically the authoritative JAA product tree.
- The DFI worktrees contain ignored read-only JAA fixtures needed by inherited tests. Their presence
  does not authorise JAA work.

## Certified implementation lineage before the checkpoint

All certified DFI work exists only in isolated Gigabyte branches/worktrees:

| Slice | Branch/worktree | Commit | Status |
|---|---|---|---|
| DFI-00 | `orchestrator-v3-dfi-00` / `di/dfi-00-baseline-epoch` | `83003f69e5b01c20afed895941d8d8b42a2f5092` | Component-certified, inactive |
| DFI-01 | `orchestrator-v3-dfi-01` / `di/dfi-01-canonical-schema` | `7d36de9bb8e72501fecacb736a50be0e574e3633` | Component-certified, inactive |
| DFI-02 | `orchestrator-v3-dfi-02` / `di/dfi-02-structured-findings` | `7282534df05341eee5742a183cb5b7f0cab47780` | Component-certified, inactive |
| DFI-03 | `orchestrator-v3-dfi-03` / `di/dfi-03-workflow-compiler-shadow` | `8eb97cee14f628b1f2337be69f14d69043be5435` | Component-certified shadow only |
| DFI-04 | `orchestrator-v3-dfi-04` / `di/dfi-04-task-adapter` | `274c6d0d68209084aa8ee3bf3265672f67c0bb02` | **Uncertified checkpoint** |

Implementation reports for DFI-00 through DFI-03 are in the DFI-04 tree:

- `docs/efficiency/DFI_00_IMPLEMENTATION_2026-07-22.md`
- `docs/efficiency/DFI_01_IMPLEMENTATION_2026-07-23.md`
- `docs/efficiency/DFI_02_IMPLEMENTATION_2026-07-23.md`
- `docs/efficiency/DFI_03_IMPLEMENTATION_2026-07-23.md`

Do not accept those reports as proof by themselves. Reconcile every material claim with code,
tests, commit history and host state.

## What Codex implemented in the DFI-04 checkpoint

The checkpoint changes ten files:

### Production files

- `control/daemon.py`
  - Adds a default-off scheduler-profile seam before ordinary task-manager dispatch.
  - No profile path means legacy behaviour.
  - A configured profile must bind the current factory epoch.

- `control/deterministic_scheduling.py` — new, 182 lines
  - Strict scheduler bundle loading.
  - Closed deterministic-scope package parsing.
  - Shadow compilation without repository mutation.
  - Active compilation/admission before the legacy task manager.
  - Typed refusal leaves the parent queued for the exact legacy fallback.

- `control/workflow_adapter.py` — new, 688 lines
  - Activation evidence and scheduler-profile creation.
  - STOP/reconciliation gate for profile switching.
  - Workflow model-node to existing `Task` conversion.
  - Deterministic task IDs and dependency projection.
  - Sealed task-batch records.
  - Existing `TaskRepository` settlement with zero planner calls.
  - Typed, scope-preserving fallback records.
  - Assurance-contract and supplied-task semantic validation.

- `control/scope_freeze.py`
  - Manifest schema v2 support binds an exact assurance-contract hash per component.
  - Historical/no-contract manifests carry `null`, not fabricated assurance authority.
  - Adds domain-separated assurance-contract identity.

- `control/workflow_compiler.py`
  - Workflow lineage now binds the factory epoch.
  - Current workflow schema becomes v3.
  - Repair tester omission is allowed only when all current findings bind `existing:` coverage.

- `infra/schema_registry.py`
  - Adds/upgrades workflow v3 and manifest-candidate v2 with explicit upcasters.
  - Adds `compiler_activation`, `scheduler_profile`, `workflow_task_batch` and
    `planner_fallback`.
  - Extends the sealed task batch to bind task semantics, scope lineage, assurance identity,
    parent retry/priority policy and runnable authority.

### Test files

- `tests/test_workflow_adapter.py` — new, 419 lines.
- `tests/test_deterministic_scheduling.py` — new, 172 lines.
- `tests/test_workflow_compiler.py` — extended.
- `tests/test_canonical_schema_registry.py` — registry golden updated.

DFI-04 checkpoint delta:

- 1,985 insertions and 54 deletions.
- Approximately 1,293 production insertions and 692 test insertions.
- Current large-file warning signs:
  - `infra/schema_registry.py`: 1,824 lines.
  - `control/workflow_compiler.py`: 897 lines.
  - `control/workflow_adapter.py`: 688 lines.
  - `control/scope_freeze.py`: 661 lines.

The architecture plan explicitly says new production infrastructure should remain in the low
thousands of lines, should favour small single-responsibility modules, and must stop for architecture
review if the projection exceeds roughly 8,000 new production lines before retirement. Assess
whether the implementation is already violating the spirit of that entropy budget.

## Important DFI-04 residual state

The checkpoint is intentionally incomplete:

1. No DFI-04 implementation/certification report exists.
2. No complete v3 suite has run for DFI-04.
3. No Wave-A promotion suite or independent review has run.
4. No scheduler bundle/profile is installed in production.
5. No production epoch or compiler-active authority is selected.
6. Historical JAA planner episodes correctly refuse because they predate DFI-03 scope
   certificates. They cannot authorise DFI-04.
7. The current evidence is a synthetic, genuinely scope-certified canary plus focused tests. Assess
   whether that is enough even to continue implementation, and what additional replay/parity
   evidence is minimally necessary before activation.
8. DFI-05 through DFI-16 are not implemented.
9. No DFI work is merged into the production branch.
10. JAA remains paused and untouched.

Codex found and corrected several hazards during the checkpoint, but Fable must independently
verify the corrections rather than inherit their intended meaning:

- Workflow identities originally did not bind the factory epoch.
- Manifest/scope certification originally did not bind the executable `_assurance` bytes.
- A supplied `Task` could originally reuse a valid deterministic task ID while altering executable
  semantics not present in the sealed batch.
- The existing judge expects top-level `_assurance.slice_id`; an early checkpoint form omitted it.
- Historical schema upcasts require validation of the historical identity before issuing the
  current identity.

## Fable's assessment mandate

Perform an extremely thorough, read-only review. Do not edit code, do not activate the factory,
do not remove STOP, do not run JAA, and do not treat a green test as proof that the tested contract
is the right contract.

Append findings as they are discovered rather than relying on end-of-session memory. For each
finding record:

- stable ID;
- severity and confidence;
- exact file/line or architecture section;
- observed evidence;
- violated invariant or efficiency objective;
- credible failure mechanism;
- smallest safe correction;
- expected correctness, token and wall-time impact;
- test or measurement needed to falsify the finding.

Review these six dimensions.

### A. Correctness and safety of Codex's DFI-00 to DFI-04 work

1. Audit every certified DFI-00–03 claim against implementation and tests.
2. Audit DFI-04 line by line, especially:
   - schema revision/upcast/self-identity rules;
   - assurance-contract shape, ownership and hash binding;
   - workflow, epoch, scope, manifest and programme-position lineage;
   - activation evidence and fallback-ceiling arithmetic;
   - dual-authority prevention;
   - task-ID collision and task-payload tampering;
   - `TaskRepository.settle()` crash windows and idempotency assumptions;
   - fallback scope/authority preservation;
   - daemon ordering around STOP, leadership, replay, scheduling and dispatch;
   - whether builder, tester and judge independence is real or merely labelled;
   - whether any untrusted data can become policy, scope, commands or `_assurance`;
   - whether default-off truly preserves production behaviour.
3. Find missing negative, mutation, crash/replay, concurrency and actual-host controls.
4. Identify false certification claims, tests that merely mirror implementation, and gaps between
   the architecture plan and executable enforcement.

### B. Runtime token/time bleeding

Trace where the present and proposed factory can spend or repeat tokens unnecessarily:

- routine LLM task-manager calls;
- duplicate builder/tester/judge calls;
- model-call repurchase after controller/process failure;
- repeated same-revision semantic review;
- overly broad prompts/context packages;
- planner fallback becoming normal;
- repeated repair loops from prose findings;
- redundant independent review that does not add independence;
- unnecessary frontier routing;
- full-suite/full-closure work when exact scoped evidence is available;
- model work performed before deterministic gates;
- cache identity that binds irrelevant dimensions and therefore always misses;
- runtime scans, hashing, replay or schema validation repeated per task/node;
- telemetry/reporting that blocks authority or performs full-log rescans.

Distinguish token cost, model latency, host CPU/I/O and developer iteration time. Do not optimise one
by silently moving cost into another.

### C. Development-process token/time bleeding

The infrastructure itself must not take more model work to build than it can credibly save. Assess:

- whether seventeen DFI slices and sixty-one failure modes are the right granularity;
- whether reports, schema prose, tests and validation duplicate the same contract;
- whether full context/plan rereading causes avoidable prompt bloat;
- whether per-slice branch/worktree/transfer/reverification is proportionate;
- whether tests are run at the plan's intended cadence (focused per slice, full per wave) or
  redundantly;
- whether giant central files (`schema_registry`, compiler, adapter, scope freeze) increase review
  and model-context cost;
- whether compatibility layers are accumulating instead of replacing entropy;
- whether repeated hash/schema projections can be generated from one source;
- whether remote Mac→Gigabyte staging is creating unnecessary manual verification work;
- whether assessment/certification can use deterministic evidence bundles instead of repeatedly
  asking models to reread the repository.

Quantify the largest bleeding points where evidence permits. Mark estimates as estimates.

### D. Architecture simplification without quality loss

Challenge the plan itself. Identify which mechanisms should be:

- preserved unchanged;
- consolidated;
- generated rather than handwritten;
- deferred until a real use case appears;
- removed because an existing v3/E1–E6 mechanism already provides the invariant;
- replaced by a smaller standard component or public orchestrator pattern.

The desired factory is safe, fast, accurate, observable, auditable and defensible—not
maximally elaborate. Prefer the minimum mechanism that proves an invariant. Do not propose
weakening isolation, independent evaluation, STOP, release review, evidence lineage or
fail-closed authority merely to save tokens.

### E. Revised implementation economics

Produce a ranked set of changes with:

- implementation effort;
- expected token saving;
- expected wall-time improvement;
- correctness/safety risk;
- observability/auditability effect;
- prerequisite and rollback;
- confidence and measurement plan.

Separate:

1. safe no-quality-loss changes;
2. changes safe only after shadow/parity evidence;
3. speculative changes;
4. mechanisms that must not be implemented yet.

Explicitly assess whether continuing DFI-05→16 as currently written is economically rational, or
whether the slices should be consolidated/reordered before more code is written.

### F. Resume recommendation

End with one of:

- resume from DFI-04 after named corrections;
- certify DFI-04 after named missing gates;
- redesign/consolidate before more implementation;
- abandon/revert part of the deterministic programme.

Give an exact next sequence, including the smallest first action, stop conditions and measurements.
Do not say merely “run more tests”.

## Required output

The final assessment must contain:

1. verdict first;
2. ranked findings;
3. correctness/security boundary findings separated from efficiency findings;
4. runtime and development-process token/time bleed maps;
5. safe disproportionate-return changes;
6. revised DFI roadmap;
7. explicit go/no-go on DFI-04 and DFI-05;
8. unresolved questions and confidence;
9. exact evidence paths and commit IDs.

The career claim to preserve is:

> “I measured a self-built autonomous software factory, discovered it was spending over one
> million tokens per accepted task, identified the architectural causes, and redesigned its
> assurance economics without weakening correctness.”

The review should strengthen or falsify that claim with measurements. It must not protect it from
unfavourable evidence.
