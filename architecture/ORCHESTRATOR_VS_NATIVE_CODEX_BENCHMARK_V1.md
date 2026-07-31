# Orchestrator versus native Codex benchmark contract v1

Date: 25 July 2026  
Status: proposed measurement contract; no contender has yet run it  
Purpose: determine whether the orchestrator matches or outperforms native Codex autonomous work
without losing correctness, observability, auditability, recovery or safety

## Decision this benchmark must support

Promote an orchestrator profile only if it:

1. reaches quality parity with the native baseline;
2. reaches at least 90% of native median certified throughput in the architecture-isolated track;
3. has no worse p90 time-to-certified-result after the continuity capsule is enabled;
4. uses no more uncached model input + output + reasoning per accepted work point;
5. records every required audit event and passes all recovery/authority drills;
6. requires no more operator interventions per completed workload;
7. keeps native/full-review fallback available and tested.

“Outperform” means at least 110% of native median certified throughput or at least 20% lower
uncached model consumption at quality parity, with no regression in the other mandatory
dimensions. These are engineering promotion thresholds, not statistical claims about all
software work.

## Contenders

### N — native Codex

One Codex task with the frozen repository, bounded prompt, permitted tools and the ordinary
app/CLI execution loop. Built-in compaction and subagents are allowed only when declared before
the run. No v3 task planner, ledger or semantic judge is available to the contender.

### T — thin persistent stack

The current `systemd`/Codex coordinator with sequential Sonnet author and Fable/Codex review.
This measures the operational incumbent, not pure Codex.

### V3-E — current efficient v3 baseline

Frozen E1–E6 v3 with active exact deterministic reuse, host assurance, context/tool ceilings and
the current role workflow. No DFI candidate authority.

### V3-C — continuity-capsule candidate

The proposed target: deterministic admission/identity/ledger/checkpoints outside a persistent
model-owned implementation loop; deterministic host gates at material boundaries; independent
delta review at component closure; full independent review at release.

DFI code may enter V3-C only after its own certification. The benchmark must never silently
compare an uncommitted worktree with a certified incumbent.

## Two mandatory tracks

### Track A — architecture-isolated

Purpose: isolate orchestration overhead.

- Use the same primary model, reasoning effort, tool set, maximum model calls, wall-time ceiling
  and repository context for N and V3-C.
- If role independence requires a second model call, use the same fixed independent-review model
  for both after implementation.
- Disable optional plugins, personal memory and unrelated skills.
- Use the same machine, runtime, dependency cache and network policy.
- Run contenders in randomised order.

### Track B — production policy

Purpose: compare the systems as they would actually be operated.

- N may use its recommended native model/subagent policy.
- T uses its certified Sonnet-author/Codex-review/Fable-authority policy.
- V3 uses its evidence-gated role/model cascade.
- Apply the same GBP-equivalent or subscription-limit budget ceiling per workload.
- Report every model separately; do not flatten unlike token accounting into one invented total.

Track A answers “is the architecture efficient?” Track B answers “is the deployed factory
economical?” Neither may substitute for the other.

## Frozen work unit

The unit of comparison is an **accepted work package**, not a task, turn, model call, commit or
line of code.

Every package contains:

- exact source commit and tree hash;
- natural-language goal;
- explicit acceptance criteria;
- allowed file/ownership scope;
- visible tests;
- hidden tests held outside contender context;
- risk class;
- deterministic runtime and dependency identity;
- tool/network/side-effect policy;
- maximum wall time, model calls and tool calls;
- mutation operators or seeded defects;
- external evaluation command;
- immutable package hash.

An accepted package is one exact resulting tree that passes all external gates. A system cannot
inflate throughput by splitting one package into many internal tasks or certificates.

## Workload set

Use at least five package classes and five independent instances of each. Three instances are an
exploratory minimum; five permits a useful median/p90 distribution without pretending the sample
is large.

### W1 — deterministic surgical repair

- One local defect.
- Existing failing regression.
- No API/schema redesign.
- Tests under five minutes.

Measures unnecessary planning, context and assurance overhead.

### W2 — bounded feature

- Two to four production modules.
- New independent tests required.
- Clear interfaces and no external service.

Measures ordinary implementation throughput and whether persistent cognition avoids handoff tax.

### W3 — semantic persistence defect

- SQLite/event/replay or migration invariant.
- Visible tests are incomplete.
- Hidden adversarial cases exercise crash, replay, malformed identity and partial settlement.

Measures reasoning quality and whether faster execution escapes material defects.

### W4 — multi-stage component

- Three dependent increments against one stable contract.
- Later increments depend on artefacts from earlier increments.
- One controlled requirement amendment arrives after increment one.

Measures continuity, amendment handling, invalidation precision and repeated-context economics.

### W5 — recovery and duplicate work

Run the same package under injected failures:

1. kill after provider response but before settlement;
2. kill after file write but before test receipt;
3. restart with an exact completed deterministic operation;
4. restart with one effective input changed;
5. start a competing controller/worker;
6. interrupt the transport without killing the worker.

Measures exact result recovery, duplicate billing, stale-worker rejection and autonomous
continuation.

### W6 — integration/release closure

Optional but required before commercial promotion:

- combine three previously accepted components;
- include one cross-component interface defect;
- require complete release review and clean-host restore.

Measures whether incremental assurance composes without weakening terminal review.

## External quality authority

No contender judges itself.

The external evaluator runs after the contender has stopped and receives only:

- frozen work-package contract;
- exact base and candidate trees;
- hidden tests and mutation controls;
- contender’s declared receipts/evidence;
- no contender reasoning transcript unless evaluating audit completeness.

Quality gates:

1. all visible and hidden deterministic tests pass;
2. mutation score meets the package floor;
3. no P0/P1 seeded or discovered defect remains;
4. blind semantic reviewers independently classify correctness and material findings;
5. persistence/recovery packages pass replay and integrity drills;
6. no tests, acceptance criteria or safeguards were weakened;
7. exact candidate tree remains unchanged during evaluation.

Disagreements are adjudicated against executable evidence first and a third blind reviewer
second. The evaluator records disagreement instead of averaging it away.

## Measurements

### Quality

- package acceptance: binary;
- weighted escaped defects: `10×P0 + 5×P1 + 2×P2 + 1×P3`;
- hidden-test pass rate;
- mutation score;
- material-finding recall;
- false-positive material findings;
- pass consistency: accepted runs / repeated runs for the same package;
- release full-review outcome.

Any extra escaped P0/P1 is an automatic quality regression regardless of speed.

### Throughput

Define a package’s work points before running it:

```text
work_points =
    1
  + changed_interface_weight
  + persistence_or_migration_weight
  + independent_test_weight
  + recovery_drill_weight
```

Each weight is fixed in the package manifest and cannot depend on contender output or line count.

Report:

- accepted work points / unattended wall hour;
- accepted work points / active model hour;
- time to first passing visible test;
- time to external acceptance;
- median, p90 and worst case;
- throughput including failed runs, never only accepted runs.

### Model economics

Per provider and model, report separately:

- input tokens;
- cached input;
- cache-created input;
- uncached input;
- output;
- reasoning output;
- model calls;
- tool calls;
- provider-reported/list-equivalent cost;
- subscription weekly-limit percentage before and after;
- missing telemetry as `null`, never zero.

Primary token-efficiency measures:

```text
uncached_generation_load =
    uncached_input + output + reasoning_output

uncached_load_per_accepted_work_point =
    sum(uncached_generation_load across all attempts)
    / accepted_work_points
```

Cached input is reported separately because it has real latency/quota economics but is not
equivalent to uncached input.

### Coordination tax

- planner/model calls whose output schedules already-declared work;
- role handoffs;
- context packages rebuilt;
- unchanged bytes sent to semantic review;
- repeat result events;
- requeues with unchanged causal fingerprint;
- deterministic commands re-executed despite an eligible current receipt;
- completed provider outputs lost/repeated after interruption;
- model tokens spent on rejected work;
- model tokens spent before deterministic rejection was available.

### Autonomy

- longest productive interval without operator input;
- operator decisions required / accepted package;
- status-only operator messages, recorded separately;
- time blocked while an eligible automatic/Fable decision path existed;
- restart-to-productive-work latency;
- productive service availability / unattended availability.

New goals and requirement amendments are not counted as interventions. Permission clicks,
repeated “continue” prompts, manual restarts and gate decisions are.

### Auditability and safety

Required durable event classes:

- admission/refusal;
- package and effective-input identity;
- model invocation start/settlement/unknown outcome;
- tool/side-effect intent and result;
- checkpoint;
- deterministic execution/reuse/invalidation;
- test and negative-control receipt;
- finding creation/resolution;
- model route and budget reservation;
- state transition;
- stale-worker/controller refusal;
- semantic review;
- certificate;
- rollback/recovery;
- operator intervention.

Report event coverage as a vector, not one percentage. A missing mandatory event fails promotion.

## Run protocol

1. Freeze contender commits, configuration, prompts, agent definitions and runtime images.
2. Prove clean trees and store their hashes.
3. Pin the workload package and external evaluator hashes.
4. Warm dependency/model caches with a non-benchmark package, then record cache state.
5. Randomise contender order within every workload instance.
6. Run one contender at a time unless the package is explicitly a concurrency test.
7. Apply the exact same kill/failure schedule from a precommitted seed.
8. Stop at the declared budget; do not grant a favourite contender extensions.
9. Run the external evaluator.
10. Seal raw JSONL, git trees, test output, provider usage and operator-touch log.
11. Compute the scorecard from sealed evidence.
12. Repeat until every package has the declared run count.

## Statistical reporting

For every metric publish:

- all individual runs;
- sample count;
- median;
- p90;
- minimum/maximum;
- bootstrap 95% interval when sample size supports it;
- failure rate;
- missing-data count.

Do not publish only the best run or only accepted runs. Do not claim statistical superiority if
intervals are too wide; report “inconclusive”.

## Promotion matrix

| Gate | V3-C requirement |
|---|---|
| Quality | No additional P0/P1; hidden tests and mutation floor at parity or better |
| Finding recall | 100% of seeded material findings; no loss against full-review baseline |
| Throughput | ≥90% of N median in Track A; p90 no worse after continuity activation |
| Token efficiency | No higher uncached load / accepted work point in Track A |
| Autonomy | No more operator decisions / package; recovery resumes automatically |
| Audit | Every mandatory event class present and hash-bound |
| Recovery | No duplicate durable settlement; no stale authority accepted |
| Release | Full-closure independent review passes exact release tree |
| Rollback | Legacy/full mode restored by tested configuration change |

If V3-C passes quality/audit but misses throughput, keep it shadow-only and optimise. If it passes
throughput but misses quality/audit, reject it. Safety is a constraint, not a weighted score that
speed can offset.

## First economical experiment

Before the complete matrix, run a three-package pilot:

1. one W1 deterministic repair;
2. one W3 persistence defect;
3. one W5 provider-return crash drill.

Use Track A only, two repeats per contender, N versus current V3-E. This will quantify the current
coordination tax and validate the telemetry pipeline before spending on V3-C.

The pilot does not authorise production promotion. Its purpose is to discover broken measurement
and establish the true baseline cheaply.

## Required output artefacts

```text
benchmark/
  contract.json
  workloads/<package-id>/
  contenders/<contender-id>.json
  runs/<run-id>/
    admission.json
    trajectory.jsonl
    provider-usage.json
    operator-touches.jsonl
    base-tree.txt
    candidate-tree.txt
    receipts/
    evaluator/
  scorecard.json
  scorecard.md
  SHA256SUMS
```

The scorecard is a projection. Sealed raw evidence remains authoritative.

