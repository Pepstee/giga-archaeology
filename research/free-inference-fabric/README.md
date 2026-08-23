# GIGA Free-Inference Fabric v0.3 — experimental laboratory

This is an executable, provider-neutral laboratory for turning cheap inference into useful,
measured project work. It treats models as replaceable workers and obtains quality from the whole
system: independent attempts, cross-model criticism, deterministic gates, bounded repair loops,
stagnation detection, experiment memory and evidence-rich escalation.

It is deliberately **not** a second Orchestrator, a new GIGA authority root or a production Jarvis
runtime. The active `(8) End result architecture (2)` task owns Ox Alpha and project-supervisor
coordination. This laboratory owns only inference experiments and their evidence. The boundary is
needed because the operator asked for the new mechanism without conflicting with that active task.

## What is implemented

```text
durable work queue
      │
      ▼
workload contract ──► model/privacy/cost policy ──► eligible local/free/explicit-paid pool
      │                                                   │
      │                                      independent candidates in concurrent slots
      │                                                   │
      │                                      cross-model, non-certifying critics
      │                                                   │
      └──────────────────────────────► objective evaluator/tests
                                                          │
                            pass ──► verified pattern memory + benchmark scorecard
                              │
                            fail ──► bounded repair round
                                          │
                             repeated output/no improvement?
                                      │ yes
                                      ▼
                              forced strategy change
                                      │
                         budget exhausted without proof
                                      ▼
                    frontier escalation packet containing attempts,
                    gate results and failures—not a restart from zero
```

The implementation includes:

- OpenRouter model discovery using its public models API, with free and preview classification;
- OpenAI-compatible adapters for OpenRouter and local servers such as Ollama;
- final-content-first parsing with explicitly labelled reasoning-only fallback for local reasoning
  servers; objective gates still decide whether fallback text is usable;
- a policy boundary for `local`, `free` and explicitly admitted `paid` tiers, including paid-call reservation;
- public/internal/personal/Vault privacy classes and ZDR eligibility;
- several independent candidates per round, enforced minimum model diversity and different approaches;
- independent critics using other models, with their findings fed into subsequent repairs;
- strict versioned text/command/composite evaluator contracts exposed by CLI and background queue;
- automatic repair rounds until a gate passes or the bounded round budget expires;
- repeated-output and no-score-improvement stagnation detection;
- a forced change of decomposition/approach after stagnation;
- a hard remote-call budget so a retry storm cannot consume an entire free allowance;
- a persistent cross-experiment daily remote-call ledger and limit, including critic calls;
- SQLite storage for attempts, outputs, model identity, telemetry, critiques and gate evidence;
- reusable successful solution patterns and accumulated failure/correction patterns;
- immutable, fixture-hash-bound real-project benchmarks and benchmark-filtered model scorecards;
- an idempotent, leased, retry-bounded background work queue;
- deterministic one-cell study progression that refuses before discovery when the remaining daily
  allowance cannot cover the declared worst case;
- preview-first `harvest-next` selection that benchmarks one still-unmeasured free model against an
  immutable objective gate and cannot claim or spend on the same model/contract twice;
- escalation packets that give a frontier model prior experiments and failures;
- 19 reusable workloads covering tests, bug finding, debt, refactoring, documentation,
  codebase research, architecture maps, code/security/dependency review, alternatives,
  re-audits, preview harvesting and controlled orchestration research.

## Capability-to-mechanism mapping

| Operator intent | Implemented mechanism |
|---|---|
| Exploit free OpenRouter and temporary previews | Public discovery snapshot, preview-first `harvest-next`, immutable benchmark and deterministic claim |
| Compensate for weak models | Multi-round engine with objective feedback, critics and approach rotation |
| Try independent solutions and models | `candidates_per_round`, model rotation and mandatory independent approaches |
| One model checks another / mutual criticism | Candidate model is excluded from its critic pool; several critics can be required |
| Trust tests, not self-evaluation | Evaluators run outside the model; provider failure and model prose can never produce PASS |
| Continue repairing until tests pass | Bounded repair loop with prior candidate and exact gate evidence |
| Detect loops and change approach | Output hashes, score windows, `STAGNATION DETECTED`, approach rotation and call ceilings |
| Generate tests, find bugs/debt, refactor, document, map, review | Versioned workload catalogue with an objective gate for every workload |
| Preserve useful experience and errors | `solution_patterns`, `failure_patterns`, attempts and critiques in SQLite |
| Build real project benchmarks | Immutable fixture/evaluator bindings plus benchmark-filtered scorecards |
| Compare free ensembles with frontier models | Locked `ensemble-vs-frontier`, `weak-model-orchestration-research` and `attempt-tradeoff` profiles |
| Combine local, free and paid models | Provider-neutral `ModelSpec`/adapter contract; paid use requires explicit CLI admission |
| Prepare context before expensive inference | `giga.frontier-escalation-packet.v1` includes all attempts and gate evidence |
| Parallel hypothesis exploration | Candidate calls execute concurrently; evidence commits and objective gates remain ordered |
| Turn idle inference into background work | Idempotent queue, leases, attempt ceiling and periodic `queue-next` consumption |
| Redesign later with a stronger model | `frontier-architecture-redesign` workload requires evidence and migration proof, not a prestige rewrite |

## Why this does not simply use `openrouter/free`

OpenRouter's `openrouter/free` router is useful for low-volume experimentation, but it selects a
compatible free model at random. That is appropriate for opportunistic work, not controlled
experiments where model identity, independence and reproducibility matter. The fabric therefore
discovers the current free catalogue and normally selects explicit model IDs; the actual served
model is still recorded from every response.

OpenRouter currently documents a shared allowance of 50 free-model requests per day without a
qualifying credit purchase, rising to 1,000 per day after at least $10 of purchased credits, with
availability and upstream limits still varying. Failed requests can consume allowance. The default
experiment ceiling is consequently 50 remote calls, including critics. Local calls do not consume
that budget. See the official [free-router documentation](https://openrouter.ai/docs/guides/routing/routers/free-router),
[rate-limit FAQ](https://openrouter.ai/docs/faq), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
and [ZDR controls](https://openrouter.ai/docs/guides/features/zdr).

The linked [Hermes Agent profile](https://openrouter.ai/apps/hermes-agent) is evidence that a
persistent agent can combine cross-session memory, tools, schedules and subagents across many model
backends. Hermes is a reference pattern here, not a dependency and not an authority source.

## Run it

No third-party Python library is required.

```bash
cd /Users/admin/Documents/giga-user/research/free-inference-fabric
export PYTHONPATH="$PWD/src"

# Snapshot current free/preview availability without sending project content.
python3 -m giga_inference_fabric.cli discover

# Produce one scheduler-friendly receipt. Exit 10 means a free/preview window changed.
python3 -m giga_inference_fabric.cli monitor-once

# Select the highest-priority unmeasured preview/free model without calling it. Add --execute and
# the existing OpenCode bridge only when the printed worst-case call count fits the daily budget.
python3 -m giga_inference_fabric.cli harvest-next \
  --benchmark-id fabric-json-test-plan-002 --daily-remote-limit 40
python3 -m giga_inference_fabric.cli harvest-next \
  --benchmark-id fabric-json-test-plan-002 --daily-remote-limit 40 \
  --execute --use-opencode-auth

# Discover models served by a local OpenAI-compatible endpoint.
python3 -m giga_inference_fabric.cli discover-local \
  --local-base-url http://127.0.0.1:11434/v1

# Inspect the reusable workload catalogue.
python3 -m giga_inference_fabric.cli profiles

# Run a bounded OpenRouter ensemble. The key is read only from the environment.
export OPENROUTER_API_KEY='...'
python3 -m giga_inference_fabric.cli run \
  --free-model nvidia/nemotron-3-super-120b-a12b:free \
  --free-model thinkingmachines/inkling-small:free \
  --objective 'Produce a test plan with a deterministic negative control' \
  --prompt 'Return a concrete plan for the bounded source packet.' \
  --require 'negative control' \
  --require 'expected failure' \
  --candidates 3 --critics 2 --min-distinct-models 2 \
  --rounds 4 --max-remote-calls 50 --max-output-tokens 4096

# Or reuse an existing OpenCode OpenRouter login without reading/copying its key. Paid access is
# denied by default. Every call runs with an isolated HOME/config/data/state/cache, all tool
# permissions denied, sharing/snapshots disabled, a one-invocation exact-model output-cap plugin
# and a credential-scrubbed process environment. Only a symlink to OpenCode's own auth file is
# exposed; its existing session database, user plugins and project instructions are not loaded.
# The canonical safety plugin is versioned at opencode/giga-output-budget.js because OpenCode
# rejects executable file-plugins generated inside the macOS temporary tree.
python3 -m giga_inference_fabric.cli run \
  --use-opencode-auth \
  --free-model nvidia/nemotron-3-super-120b-a12b:free \
  --objective '...' --prompt '...' --require '...'

# Add one or more local OpenAI-compatible models.
python3 -m giga_inference_fabric.cli run \
  --local-model qwen3-coder:latest \
  --local-base-url http://127.0.0.1:11434/v1 \
  --objective '...' --prompt '...' --require '...'
```

Paid models are excluded by default. Adding one requires all three explicit elements. Before every
paid call, the engine uses the highest published base/override prompt and completion prices, a
conservative UTF-8 prompt bound and the provider-side output-token ceiling to reserve the maximum
call cost atomically. Missing, invalid, stale-catalogue or over-budget admission fails before
provider execution.

```bash
python3 -m giga_inference_fabric.cli run \
  --use-opencode-auth \
  --include-paid --paid-model openai/gpt-5.6-sol --max-cost-usd 0.02 \
  --max-output-tokens 128 --max-remote-calls 1 \
  --objective 'Resolve only the failures in the supplied escalation packet' \
  --prompt "$(<state/last-result.json)" --require '...'
```

The laboratory emits the escalation packet automatically. Paid fallback is still operator-invoked;
autonomous production activation remains owned by GIGA-v2's JSR-086 authority boundary.

## Real-project benchmarks

The repository preserves `benchmarks/fabric-json-test-plan-001`, the runnable first structural
benchmark. A live three-model/six-critic study exposed a false-positive: v1 accepted contradictory
positive and negative controls with the same input. That result remains immutable evidence, but
future utility studies use `fabric-json-test-plan-002`, which also requires disjoint inputs and
deterministic non-modal outcomes. See
`evidence/benchmark-v1-cross-critic-supersession-2026-08-24.json`. Benchmark fixtures are separate
from unit tests because they measure models and must remain immutable across comparisons.

```bash
python3 -m giga_inference_fabric.cli benchmark-register \
  --benchmark-id orchestrator-retry-regression-001 \
  --project orchestrator-v3 \
  --workload implementation \
  --objective 'Fix the locked retry regression without changing public semantics' \
  --fixture-ref '/absolute/path/to/disposable-fixture' \
  --evaluator-ref 'python3 -m pytest tests/test_retry_regression.py'

# The run objective/workload must exactly match the immutable registration. Fixture and evaluator
# bindings are checked before any provider call.
python3 -m giga_inference_fabric.cli run \
  --benchmark-id orchestrator-retry-regression-001 \
  --workload implementation \
  --objective 'Fix the locked retry regression without changing public semantics' \
  --prompt 'Return the complete artifact consumed through GIGA_CANDIDATE_PATH.'

python3 -m giga_inference_fabric.cli scoreboard \
  --benchmark-id orchestrator-retry-regression-001
```

The relevant metrics are gate success, false-success rate, attempts to repair, wall-clock latency,
tokens and monetary cost. A model does not become “good” because another model likes its answer.
Benchmark binding and verification live in a separate `benchmarks.py` module because fixture
identity has a distinct lifecycle from provider discovery, workload profiles and experiment state.

## Controlled orchestration studies

The admitted future-study contracts use the strengthened disjoint-control benchmark:

- `weak-model-orchestration-v2`: single-shot, repair-only, repair-plus-memory and
  ensemble-plus-critics;
- `free-ensemble-vs-frontier-v2`: a repeated free ensemble against an explicitly admitted paid
  single shot;
- `cheap-attempt-pareto-v2`: clean one, four and twelve-free-attempt budgets against one paid
  attempt.

The original `config/studies.json` remains immutable historical evidence, but its v1 studies are
bound to the superseded false-positive benchmark and must not be used for future conclusions.
`config/studies-v2.json` preserves the already-started orchestration study; the comparative studies
live in `config/studies-comparative-v2.json` because modifying either admitted catalogue would
invalidate deterministic experiment identities.

```bash
# Inspect the current immutable arm definitions and expand the 12 orchestration cells. The plan
# reports cells that cannot fit the selected daily limit instead of leaving them permanently stuck.
python3 -m giga_inference_fabric.cli studies --study-catalogue config/studies-v2.json
python3 -m giga_inference_fabric.cli study-plan \
  --study-id weak-model-orchestration-v2 \
  --study-catalogue config/studies-v2.json --daily-remote-limit 40

# Run one declared cell. The study contract overrides candidates, critics, rounds, memory and tier.
# Reusing the same study/arm/repeat identity fails closed instead of duplicating a datapoint.
python3 -m giga_inference_fabric.cli run \
  --study-id weak-model-orchestration-v2 \
  --study-arm single-shot-no-memory --repeat-index 1 \
  --study-catalogue config/studies-v2.json \
  --use-opencode-auth \
  --free-model thinkingmachines/inkling-small:free \
  --workload model-benchmark \
  --objective 'Produce a deterministic JSON test plan with both positive and negative controls' \
  --prompt 'Return only a strict giga.test-plan.v1 JSON candidate.'

python3 -m giga_inference_fabric.cli study-scoreboard \
  --study-id weak-model-orchestration-v2
```

Memory-off arms bypass reusable experience in the engine rather than merely hiding it in reports.
Paid arms still require named models, explicit admission and pre-reserved cost authority. Study
Definitions live separately from background workload prompts and each catalogue has its own
SHA-256 identity file. Any unadmitted edit blocks listing, planning and execution.

The strengthened live study is `weak-model-orchestration-v2` in `config/studies-v2.json`. Its
external verifier rejects overlapping positive/negative inputs and vague expected outcomes. A
scheduler should use `study-next`, not invent repeat numbers. The command deterministically selects
exactly one unclaimed SHA-bound cell, preserves the explicitly declared model order and calculates
the cell's maximum candidate-plus-critic call count before model discovery. It emits `BUDGET_WAIT`
without a provider call if the entire cell cannot fit inside the remaining daily allowance.

```bash
# Read-only: show the next cell or the reason it cannot run today.
python3 -m giga_inference_fabric.cli study-next \
  --study-id weak-model-orchestration-v2 \
  --study-catalogue config/studies-v2.json \
  --daily-remote-limit 40 \
  --free-model thinkingmachines/inkling-small:free

# Execute at most that one cell. The deterministic experiment primary key prevents duplicate
# workers from spending inference on the same cell.
python3 -m giga_inference_fabric.cli study-next \
  --study-id weak-model-orchestration-v2 \
  --study-catalogue config/studies-v2.json \
  --daily-remote-limit 40 --execute --use-opencode-auth \
  --free-model thinkingmachines/inkling-small:free \
  --free-model nvidia/nemotron-3-super-120b-a12b:free \
  --free-model thinkingmachines/inkling:free
```

The current 40-call research ceiling fits the largest declared 36-call ensemble while retaining ten
requests of headroom below OpenRouter's documented 50-request daily allowance for accounts below
the $10 purchased-credit threshold. It is a local risk budget, not a claim about provider
entitlement; retries cannot silently raise it.

## Background work

Queue insertion is idempotent, so a periodic feeder cannot create the same job repeatedly:

```bash
python3 -m giga_inference_fabric.cli queue-add \
  --project orchestrator-v3 --workload bug-hunt \
  --objective 'Find one reproducible state-machine defect' \
  --prompt 'Inspect only the admitted source packet and provide a deterministic reproducer.' \
  --require 'reproducer' \
  --check-command 'python3 verify_candidate.py' \
  --evaluator-cwd /absolute/path/to/disposable-fixture \
  --max-attempts 3

python3 -m giga_inference_fabric.cli queue-next --lease-minutes 30

# A scheduler or supervisor can instead execute exactly one item and exit.
python3 -m giga_inference_fabric.cli worker-once \
  --lease-minutes 30 --candidates 3 --critics 2 --rounds 4
```

A supervisor can run the leased item in a disposable checkout itself and record `queue-finish`, or
invoke `worker-once`; the worker never becomes an unbounded daemon. Objective commands receive the
candidate only through `GIGA_CANDIDATE_PATH`, run without a shell and receive a minimal environment
that excludes provider credentials. They are execution gates, not an OS sandbox, so the working
directory must still be an admitted disposable fixture. This v0.3 intentionally does not install a
launchd job or mutate project trees:
the active architecture task already owns project supervision, and silently adding a second writer
would violate the operator's non-conflict requirement.

## Production integration seam

The laboratory maps to the existing GIGA-v2 plan instead of replacing it:

| Laboratory artifact | Canonical future seam |
|---|---|
| completion and gate telemetry | JSR-044 universal invocation envelope |
| model pool and role eligibility | JSR-047 / JSR-049 |
| independent critics | JSR-085 |
| call and monetary budgets | JSR-086 |
| provider health and fallback | JSR-087 / JSR-088 |
| real-work scorecards | JSR-075 and identity/evaluation lane |
| least-context packets | JSR-084 |
| objective tool execution | operation request → kernel decision → adapter receipt, never direct model authority |

No laboratory result is automatically a GIGA-v2 law, production policy, integration candidate or
completion receipt.

## Evidence status

- **Runtime-proven locally:** orchestration, enforced diversity, critique-to-repair feedback,
  stagnation reset, budgets, paid pre-reservation, external command gates, benchmark drift
  rejection, experience memory, queues and model-window events.
- **Live-proven without content disclosure:** OpenRouter public discovery and consecutive
  `monitor-once` checks.
- **Live-proven:** one authenticated, zero-cost OpenRouter completion through the isolated OpenCode
  bridge; see `evidence/live-free-transport-2026-08-24.json`.
- **Live benchmark-proven:** the bound `fabric-json-test-plan-001` external verifier rejected eight
  Nemotron candidates and accepted Inkling Small on its first attempt, all at provider-reported
  zero cost; see `evidence/live-benchmark-comparison-2026-08-24.json`.
- **One live mutual-criticism cell completed:** three candidate models, six independent critiques,
  nine zero-cost calls and one objective PASS. Critics then exposed a v1 verifier false-positive;
  the immutable result is retained and the strengthened v2 study contract supersedes it.
- **First strengthened v2 baseline completed:** Inkling Small passed the disjoint-control verifier
  in one no-memory/no-repair call at reported zero cost. See
  `evidence/live-study-v2-baseline-2026-08-24.json`.
- **Controlled v2 progression live-proven:** the second weak-model single shot and the first
  one-attempt Pareto cell passed at zero reported cost; a newly harvested preview model failed the
  same external verifier, and the 36-call ensemble was refused before execution with only 17 calls
  remaining. See `evidence/live-controlled-progress-2026-08-24-r2.json`.
- **Implemented but not yet executed as complete studies:** remaining orchestration, ensemble/frontier
  and Pareto cells with idempotent repeat identities and study scoreboards.
- **Local transport and minimal utility live-proven:** cached Qwen2.5-3B-Instruct produced the exact
  externally gated `READY` token in one attempt with `remote_calls=0` under Vault policy. The same
  model failed the stronger immutable strict-JSON benchmark twice, so general engineering utility
  remains unproven. See `evidence/live-local-qwen25-qualification-2026-08-24.json`; earlier negative
  models remain preserved in `evidence/live-local-negative-results-2026-08-24.json`. No local server
  was left running.
- **Deliberately not activated:** a recurring portfolio writer or production GIGA-v2 fallback.
  The non-conflict instruction leaves those actions with `(8) End result architecture (2)`.

## Operator requirements checklist

`[x]` means an executable laboratory mechanism or callable workload exists. It does not mean that a
production scheduler has been activated across the project portfolio.

- [x] Free OpenRouter inference: discovery plus explicit zero-cost model selection.
- [x] Weak-model compensation: bounded generate → evaluate → repair cycles.
- [x] Several independent solutions: configurable candidate fan-out and approach separation.
- [x] Different models solve the same task: fail-closed minimum diversity plus model rotation.
- [x] One model checks another: the producing model is excluded from its critic pool.
- [x] Several models criticise: retained disagreement is injected into the next repair round.
- [x] Objective checks outrank self-assessment: JSON/text/command/composite evaluators.
- [x] Automatic correction: failed gate evidence enters the next repair prompt.
- [x] Loop detection: output hashes and score-improvement windows.
- [x] Approach switching: stagnation injects a strategy-reset contract and rotates approaches.
- [x] Mass test generation: `test-generation` workload.
- [x] Bug search: `bug-hunt` workload with reproducer gate.
- [x] Technical-debt search: `technical-debt` workload with measured-impact gate.
- [x] Refactoring: behaviour-preserving `refactoring` workload.
- [x] Existing-code documentation: source-anchored `documentation` workload.
- [x] Large-codebase research: bounded `codebase-research` workload.
- [x] Architecture/dependency maps: extracted-versus-inferred `architecture-map` workload.
- [x] Code review: reproducibility-gated `code-review` workload.
- [x] Security review: authorised, non-live-exploitation `security-review` workload.
- [x] Dependency/config review: primary-source-backed `dependency-config-audit` workload.
- [x] Many alternative implementations: `alternative-implementation` plus candidate fan-out.
- [x] Successful-chain memory and reuse: `solution_patterns` are injected into later matching tasks.
- [x] Model-error/correction history: `failure_patterns`, attempts, critiques and gate outputs.
- [x] Real-project benchmarks: immutable registry with verified fixture and evaluator hashes.
- [x] Workflow-specific utility: scorecard records gate score, success, latency, tokens and cost.
- [x] Temporary free previews: preview-first `harvest-next` executes one immutable benchmark cell.
- [x] New/free-window monitoring: `monitor-once` records durable open/close events and receipts.
- [x] Local inference: OpenAI-compatible adapter plus local model discovery.
- [x] Local/free/paid composition: common adapter contract; paid tier requires explicit admission.
- [x] Cheap context preparation: `frontier-context-preparation` workload.
- [x] Frontier model receives prior work: versioned escalation packet includes every attempt and gate.
- [x] Parallel hypotheses: candidate calls execute concurrently, while evidence commits remain ordered.
- [x] Continuous test-coverage improvement: schedulable test-generation queue items.
- [x] Periodic legacy audit: `legacy-reaudit` workload.
- [x] Idle compute becomes useful background work: idempotent queue, lease, `worker-once`, attempt cap.
- [x] Models are replaceable resources: provider-neutral model and adapter contracts.
- [x] Weak-model orchestration research: immutable single-shot/repair/ensemble/memory study arms.
- [x] Free ensemble versus frontier: repeated tier-bound arms with paid admission retained.
- [x] Cheap-attempt versus expensive-attempt trade-off: fixed one/four/twelve/free-versus-paid cells.
- [x] Future strong-model architecture redesign: separate evidence-gated redesign workload.
