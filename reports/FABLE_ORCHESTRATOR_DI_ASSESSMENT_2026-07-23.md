# Fable assessment: orchestrator deterministic infrastructure

**Date:** 2026-07-23  
**Reviewer:** Claude Code Fable 5, maximum-effort read-only review  
**Subject:** Codex's DFI-00–DFI-04 deterministic-efficiency work and the proposed DFI-05–DFI-16 roadmap  
**Status:** Assessment complete; implementation remains paused  

## Executive verdict

Resume from DFI-04 only after correcting the named gaps below. Do not certify DFI-04 yet. Do not begin DFI-05 as currently written.

The checkpoint is coherent and worth preserving. The five correctness hazards Codex said it had addressed are genuinely addressed, and the focused suite passes. However, DFI-04 still lacks crash-safe reconciliation, durable shadow/fallback telemetry, an enforced production profile-switch path, deterministic validation of claimed existing tests, and behavioural daemon-seam tests.

The wider programme has also crossed its own entropy warning threshold. Five of seventeen proposed slices have added 6,717 production lines. A straight-line projection is approximately 22,900 production lines; even halving the current rate would produce approximately 14,800. The problem is not primarily the number of slices. It is their order, implementation mass, repeated prose/schema work and the continued deferral of the largest token-saving mechanism: judge delta review.

## Frozen checkpoint

### Gigabyte: authoritative software factory

- Production repository: `/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3`
- Production branch: `efficiency/e2-shadow-cache`
- Production commit: `35efb19b07867bb58e1288479513078cf9ab65e4`
- Production state: unchanged, STOP armed, zero orchestrator processes
- DFI-04 worktree: `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-04`
- DFI-04 branch: `di/dfi-04-task-adapter`
- DFI-04 checkpoint commit: `274c6d0d68209084aa8ee3bf3265672f67c0bb02`
- DFI-04 tree: `3ce0646f0254b45726860345e470c037a0e869fa`
- DFI-04 state: clean, STOP armed, zero orchestrator processes, explicitly uncertified

### Mac: exact verification mirror

- Mirror: `/tmp/orchestrator-v3-dfi02.Jh3sKl/repo`
- Branch: `local/dfi-04-task-adapter`
- Commit: `e879ff20e241c1b2c6bc5b7b75428194be68159d`
- Tree: `3ce0646f0254b45726860345e470c037a0e869fa`
- State: clean

The commit IDs differ because the commits have different parents. Their tree hashes are identical, proving exact source equality at the checkpoint.

### Verification already completed

- 85 focused tests passed on the Mac mirror.
- The same 85 focused tests passed on Gigabyte.
- Ruff passed on both machines.
- Fable independently re-ran the focused tests and inspected the implementation without modifying files.

## What the machines and repositories mean

### `giga-user`

`giga-user` is Artiom's model-agnostic operator and governance layer. It is not the orchestrator product repository. It contains the laws, charters, deterministic-assurance doctrine, programme records, memory architecture, skills, reports, handoffs and operating context intended to remain portable across Claude, GPT, Kimi and future systems.

The primary personal copy is on the Mac:

`/Users/admin/Documents/giga-user`

The software-factory governance copy is on Gigabyte:

`/home/gutua/software-factory/giga-user`

The Mac remains the home of private corpora, Jarvis/digital-twin work and market-aligner. Those personal data exports are deliberately not part of the software-factory migration.

### `agentic-orchestrator`

The authoritative orchestrator development repository is on Gigabyte:

`/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3`

Gigabyte is the dedicated software-factory machine. New orchestrator development and eventual JAA development belong there. The Mac mirror exists only for exact verification and review; it is not the production authority.

### JAA

JAA remains paused and was not touched during this assessment. Its development must not resume until the deterministic-infrastructure work is settled and deliberately activated.

## DFI lineage at this checkpoint

| Slice | Commit | State |
|---|---|---|
| DFI-00 | `83003f69e5b01c20afed895941d8d8b42a2f5092` | Certified, inactive |
| DFI-01 | `7d36de9bb8e72501fecacb736a50be0e574e3633` | Certified, inactive |
| DFI-02 | `7282534df05341eee5742a183cb5b7f0cab47780` | Certified, inactive |
| DFI-03 | `8eb97cee14f628b1f2337be69f14d69043be5435` | Certified for shadow operation only |
| DFI-04 | `274c6d0d68209084aa8ee3bf3265672f67c0bb02` | Preserved checkpoint; uncertified |
| DFI-05–DFI-16 | — | Unimplemented |

## Confirmed strengths in DFI-04

Fable verified that all five hazards Codex explicitly claimed to fix are genuinely fixed:

1. Factory epoch is bound into workflow lineage.
2. Assurance bytes are included in the deterministic manifest and scope certificate.
3. Supplied-task semantics no longer silently collapse into planner-authored semantics.
4. Historical task identity is retained before schema upcasting.
5. Top-level `assurance.slice_id` is carried and validated.

These fixes are substantive. They are not stubs, placeholders or test-only disguises.

## Correctness findings

### F-1 — High: crash after task spawning can re-run the legacy planner

There is a crash window between emitting `tasks_spawned` and recording completion. On restart, the parent can be requeued. The adapter then detects previously admitted deterministic tasks and returns early, but the surrounding repository path can proceed to purchase another legacy planner result and emit misleading lineage.

Relevant areas include the adapter's existing-task early-return path and the repository settlement/requeue path.

**Required correction:** make the path idempotently re-settle or reconcile the parent from durable child state. Existing deterministic children must prove completion of admission, not merely cause an early return.

### F-2 — Medium-high: profile switching is not enforced by a production caller

`validate_profile_switch` exists but has no production caller, and there is no durable active-profile record. The intended switch and rollback gate is therefore a library capability, not an enforced operational control.

**Required correction:** persist profile adoption as an append-only event or record and require the production activation path to call the validator before mutation.

### F-3 — Medium: shadow and fallback records are ephemeral

Shadow-batch and fallback evidence currently lives on a transient scheduling action. The daemon logs and discards it. This makes activation evidence, fallback rates and ceiling enforcement impossible to reconstruct reliably.

**Required correction:** persist append-only shadow and fallback records with deterministic identities. This is the smallest and safest first implementation action.

### F-4 — Medium: model-authored `existing:` coverage can suppress test creation

A generated plan can claim coverage through an `existing:` marker without deterministic proof that the claimed test exists. This lets a model-authored assertion suppress a test-author task.

**Required correction:** resolve every claimed existing test against the repository and reject the plan when the test cannot be found or cannot be tied to the declared contract.

### F-5 — Medium: settlement refusal can fail the parent before safe fallback

The settlement gate can durably fail a parent before the adapter returns a fallback decision. A later legacy fallback cannot cleanly restore the intended queued state.

**Required correction:** precheck compiled task identities and settlement preconditions before mutating the parent. Collision or refusal must leave the parent safely eligible for the defined fallback path.

### F-6 — Low-medium: batch validation does not recompute task identities

The validator accepts task IDs without independently recomputing them from deterministic inputs.

**Required correction:** recompute IDs during validation and reject any mismatch.

### F-7 — Low: fallback-ceiling arithmetic is incoherent

The current pass condition requires a refusal count of zero, so a non-zero fallback ceiling never meaningfully binds. The validator also does not independently recompute the rate.

**Required correction:** ratify the intended semantics, then recompute numerator, denominator and rate from durable events. This policy decision belongs to Artiom.

### F-8 — Low: STOP is not rechecked between admissions in one batch

STOP is checked around the scheduling cycle but not between individual parent admissions within the same cycle.

**Required correction:** recheck STOP before each mutating admission.

### F-9 — Low: workflow schema still describes shadow-only authority

The schema says the authority mode is shadow-only even though the active profile is capable of admitting tasks. This is transitional but misleading.

**Required correction:** make the authority state explicit and versioned before any activation.

## Missing certification evidence

### T-1 — High: daemon integration is tested by source inspection, not behaviour

The daemon seam is currently covered mainly by source-text assertions. There is no behavioural test proving actual `run_daemon` control flow, persistence, STOP handling, fallback and reconciliation.

### T-2 — High: no tests cover the critical crash and persistence windows

Tests are missing for:

- crash after child admission but before parent completion;
- deterministic identity collisions;
- persistent fallback and shadow records;
- restart reconciliation;
- writer failure during event persistence.

### T-3 — Medium-high: no real factory-epoch bundle integration test

The test suite needs to run against a real `build_factory_epoch` bundle and prove that the compiled result, scope certificate and admitted tasks remain linked.

### T-4 — Medium: activation tests are synthetic

There is no production caller, durable adoption event, mutation-count check or rollback-history test for profile activation.

## Architecture and efficiency findings

### P-1 — High: the current Wave A activation gate is unsatisfiable

The roadmap requires deterministic recall against pinned JAA replay. Yet all 19 pre-scope JAA episodes correctly refuse because they predate the required deterministic scope evidence. This is a valid safety result, but it means the proposed recall gate cannot pass.

**Roadmap correction:** replace that gate with a scope-certified canary/property corpus plus a forward shadow soak over newly eligible work.

### P-2 — High: the entropy budget has fired

Fable measured 6,717 production insertions across five of seventeen planned slices, against a stop-and-review threshold of about 8,000. At the present rate, the programme would reach approximately 22,900 production lines. Even a 50% reduction from this point would still produce approximately 14,800.

This does not prove the work is wrong. It proves the programme must be re-cut before more infrastructure is added.

### P-3 — Medium-high: the programme front-loads a relatively small saving

Planner removal is estimated to save only 5–15% of total token use. Full-closure judge rereads cost approximately 48,000–70,000 tokens per revision. Delta review is estimated to save 10–30% overall and 50–80% of judge tokens, yet it is scheduled much later.

**Roadmap correction:** pull a shadow-only DFI-11-lite measurement forward, using the already-existing `legacy_evidence_ref`. This should measure delta-review economics without granting it certification authority.

### P-4 — Medium: the strict fallback contract has no owner

The architecture specifies a constrained `PlanProposal` fallback, but no future slice clearly owns its implementation. The current fallback restores full legacy-planner authority.

**Roadmap correction:** assign the strict fallback contract to an explicit slice and gate.

### P-5 — Medium: `schema_registry.py` is becoming a monolith

The file is approximately 1,824 lines and combines schema definitions, registration and validation concerns.

**Roadmap correction:** split or generate it while preserving byte-identical/golden schema output. Treat this as a behaviour-neutral refactor with a strict identity test.

### P-6 — Low: deterministic work is repeated every daemon cycle

Shadow compilation and validation can run every five seconds and then discard the same result. Persisting shadow records enables unchanged inputs to be recognised and skipped.

### P-7 — Low-medium: development cadence is itself expensive

The plan called for full-suite certification per wave, but DFI-01 through DFI-03 each received full-suite treatment. More importantly, model context repeatedly reloads a large registry and duplicated prose reports.

**Roadmap correction:** generate compact deterministic evidence bundles for routine review; reserve full-suite runs for named wave gates unless the changed surface demands otherwise.

## Principal token and time bleeding points

1. **Full-closure judge rereads:** approximately 48,000–70,000 tokens per revision.
2. **Rejected work:** historical evidence records approximately 19.7 million rejected tokens out of 43.2 million.
3. **Provider/harness overhead:** one measured builder/tester pair consumed approximately 110,317 tokens against an explicit prompt envelope of roughly 635 tokens. The unexplained amplification needs separate instrumentation.
4. **Planner calls:** approximately 5–15% of total token use.
5. **Inactive deterministic reuse:** 101 of 101 exact shadow matches were still executed; observed return-path wall time was about 15.4 times slower than reuse would have been.
6. **Per-cycle recompilation/replay:** mainly host time rather than model tokens, but it adds latency and noise.
7. **Development-review overhead:** repeated model reading of monolithic schemas and duplicated narrative evidence.

The career claim that the factory was measured at approximately 1,054,831 tokens per accepted task is defensible. The claim that it has already been redesigned successfully is not yet proven; the next phase must demonstrate a measured before/after improvement.

## Safe changes ranked by return and risk

1. Persist shadow and fallback records.
2. Add idempotent re-settlement and collision prechecks.
3. Persist profile-adoption events and enforce validated profile switching.
4. Verify every `existing:` coverage claim against repository evidence.
5. Add behavioural daemon integration tests.
6. Split or generate the schema registry under golden-output tests.
7. Pull delta-review measurement forward in shadow-only mode.
8. Activate the already-built E2/E3 pass-only reuse path only through its existing gates.

Items 1–6 are deterministic and should not reduce output quality. Item 7 is safe only while it remains observational. Item 8 is a separate activation event and must not be bundled into DFI-04 certification.

## Speculative or later changes

- Model cascade work in DFI-14.
- Parallel-lane work in DFI-13.

These may produce large returns, but they carry more policy and behavioural risk than the deterministic corrections above.

## Actions that must not happen yet

- No DFI-04 authority cutover.
- No active delta-review certification.
- No JAA development.
- No factory-epoch activation.
- No production merge merely because focused tests pass.

## Revised sequence

### Phase 1 — DFI-04 completion slice

Implement only:

1. durable shadow/fallback records;
2. idempotent restart reconciliation;
3. collision and settlement prechecks;
4. enforced, durable profile adoption;
5. deterministic verification of claimed existing tests;
6. behavioural daemon and crash-window tests.

If this completion slice exceeds 500 additional production lines, stop and review the design before proceeding.

### Phase 2 — Ratify the corrected programme contract

Amend the plan to:

- replace historical JAA replay recall with scope-certified canaries and a forward shadow soak;
- assign ownership of the strict `PlanProposal` fallback;
- define fallback-ceiling semantics;
- preserve STOP, audit and rollback requirements.

### Phase 3 — Measure the largest saving earlier

Run a shadow-only DFI-11-lite experiment for judge delta review. It must compare output, evidence coverage, disagreement and token use without granting certification authority.

### Phase 4 — Reduce infrastructure entropy

Refactor or generate the schema registry with golden identity tests and create compact deterministic evidence bundles.

### Phase 5 — Rescope the remaining slices

- Reconcile DFI-07 with the existing E2/E3 reuse implementation so only one mechanism survives.
- Consider merging DFI-09 into DFI-08.
- Defer DFI-13 until after Wave C.
- Re-evaluate DFI-05 and DFI-06 after DFI-04's persistence and reconciliation contract is complete.

## Go/no-go decision

- **DFI-04 development:** GO, but only for the bounded completion slice above.
- **DFI-04 certification:** NO-GO until F-1 through F-5 and T-1 through T-3 are closed.
- **DFI-05 as the next action:** NO-GO.
- **Production activation:** NO-GO.
- **JAA:** remains paused.

The safest first change is F-3: append-only persistence of shadow and fallback records.

## Mandatory stop conditions

Stop immediately if:

- shadow mode creates two live authorities;
- fallback exceeds the ratified ceiling;
- DFI-04 completion adds more than 500 production lines;
- production state changes before certification;
- STOP becomes disarmed without an explicit activation event.

## Open decisions

1. Fable recommends fixing the restart/re-settlement window now, rather than postponing it to DFI-06.
2. Provider/harness amplification remains unexplained and requires dedicated instrumentation.
3. Artiom must ratify fallback-ceiling semantics.
4. DFI-02 received less line-by-line scrutiny than DFI-03 and DFI-04 and should be revisited before wave-level certification.
5. Gigabyte operational facts were checked against durable handoffs; source-tree facts were independently verified through the exact Mac mirror.

## Confidence

- Implementation findings: high.
- Test-gap findings: high.
- Programme economics and projected savings: medium-high.
- Speculative future-slice returns: medium.

## Assessment integrity

Fable operated read-only. It did not edit source, activate the factory, disarm STOP or resume JAA. The first attached review process was interrupted while its viewer was being detached; the same durable Claude session was resumed and completed. The final review corresponds to the clean, tree-identical DFI-04 checkpoint recorded above.
