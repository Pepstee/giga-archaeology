# GIGA transition roadmap: evidence substrate → virtual twin

*P3 · dependency-ordered plan · 2026-07-20*

## Planning rule

The sequence is governed by promotion evidence, not feature excitement:

`protect evidence → make writes trustworthy → make memory accurate → model decisions → observe outcomes → train behaviour → grant agency`.

Every phase leaves a runnable artefact, tests and a machine-derived status receipt. A later
phase cannot compensate for an earlier failed gate.

Market Aligner and application automation continue as an independent commercial-product lane.
GIGA may later consume their job/application/outcome events through an adapter, but this plan
does not pause, rewrite or physically absorb their active implementation.

## Current-to-target gap matrix

| Target capability | Current state | Gap | First proof |
|---|---|---|---|
| Complete memory access | large owned corpus + 42 Markdown entries | no deterministic retrieval/temporal/sensitivity routing | locked memory questions with source packets |
| Accurate current truth | recency law in prompts | no typed validity/confidence/review fields | validator + contradiction/staleness suite |
| Reliable capture | Telegram and daily ingestion live | no durable queue/transaction/receipt | crash/retry/idempotency tests |
| Preference understanding | retrospective prose and decisions | no explicit/inferred preference ledger | held-out choice prediction |
| Decision support | ad hoc model advice + Market Aligner pattern | no generic goal/decision/outcome model | shadow decisions with scored outcomes |
| Planning | domain documents and reminders | no shared plan/task state machine | daily priorities derived from goals/dependencies |
| Speaking style | prepared casual data, training unauthorised | no mode map/baseline/promoted adapter | blind mode-specific evaluation |
| Thinking style | reasoning candidates + retrospectives | candidates do not prove independent reasoning | held-out constraint/decision suite |
| Self-scrutiny | deep manual analyses | no automated hypothesis/correction lifecycle | false-positive/valuable-catch measurement |
| Agency | external orchestrator and standalone scripts | no central authority/action/receipt interface | bounded reversible task with zero violations |
| Provider independence | Claude→GPT fallback in two scripts | commands and context packets differ; health is prose | provider-extinction drill |
| Durability | source archives and new hashes | no versioned control plane or restore drill | clean rebuild from canon + encrypted restore |

## Phase 0 — Evidence and scope protection

**Purpose:** ensure twin work cannot damage the thing it is trying to understand.

### Deliverables

- SHA-256 baseline for immutable exports.
- Read-only exclusion policy for active Market Aligner/application work.
- Complete light/medium/deep maps and inventory methodology.
- Derived-artefact registry seed: every future build names source hashes and build command.
- Owner-only permissions for local token/state files.

### Gate P0

- Every export hash verifies before and after a build.
- No code path writes under an export directory.
- Market Aligner working files have no GIGA-generated changes.

**Status:** discovery artefacts and hashes complete; permissions and automated enforcement enter
the first implementation slice.

## Phase 1 — Trust kernel

**Purpose:** establish machine-verifiable events, transitions and receipts before widening
automation.

### Deliverables

1. `twin_core` provider-neutral Python package.
2. Local SQLite operational store outside the repository with migrations for:
   - events;
   - processing attempts;
   - receipts;
   - derived-artefact dependencies;
   - goals, decisions and actions (initial schemas, not full engine).
3. Append-only identifiers and idempotency keys.
4. Deterministic Markdown-memory validator:
   - frontmatter/schema;
   - index coverage;
   - resolvable entry links;
   - supersession integrity;
   - provenance/review warnings;
   - sensitive-hot-index warnings.
5. Health command deriving runtime truth from files, processes, logs and databases.
6. Machine-readable maturity scorecard.

### Gate P1

- Replaying an event does not duplicate a transition.
- A receipt cannot reference a missing event/action.
- Corrupt/partial records are rejected without damaging previous state.
- The memory validator reports current known drift and exits non-zero on hard violations.
- Unit tests use temporary stores and require no provider.

## Phase 2 — Transactional capture and historical backfill

**Purpose:** stop losing, double-processing or falsely acknowledging evidence.

### Telegram path

- Persist every authorised Telegram update locally before model invocation.
- State machine: `received → claimed → staged → validated → committed` or `retry/dead-letter`.
- Commit the Telegram offset after durable receipt, not after model-shaped reply text.
- Use update ID as the idempotency key.
- Separate user acknowledgment from librarian completion.

### Daily path

- Separate fresh daily events from historical corpus backfill.
- Replace 120-record limit with token/character budget for fresh changes.
- Backfill by conversation/month shards so context is preserved.
- Model writes into a staging directory or emits structured proposals.
- Deterministic code validates the diff/provenance/index, then commits allowed files.
- Mark only receipted input hashes as processed.
- Preserve run-addressed delta and snapshot hashes.

### Gate P2

- Kill provider, process and network at every state boundary; every event is either committed
  once or remains retryable.
- Injection text cannot alter authority or write outside staging.
- A deliberately partial model response cannot acknowledge untouched records.
- Fresh events reach memory independently of a large historical backlog.

## Phase 3 — Memory Accuracy (maturation stage 2)

**Purpose:** make recall measurably trustworthy before personality or agency.

### Schema

Extend durable memory metadata with:

- stable ID, subject and scope;
- source event IDs/fingerprints;
- observed/valid-from/valid-until timestamps;
- epistemic class and confidence;
- review state;
- sensitivity class;
- typed supersession/contradiction links.

Historical files are migrated non-destructively with receipts. Uncertain fields remain unknown;
the migration cannot invent precision.

### Retrieval compiler

- deterministic candidate selection;
- lexical/metadata search first, optional embeddings as a replaceable index;
- time and sensitivity filters;
- one-hop linked-neighbour and contradiction prefetch;
- bounded provider-neutral packet;
- access telemetry and explicit retrieval trace.

### Evaluation

Build locked question sets across identity, career, relationships, travel, commitments,
preferences and negative/gap cases. Score citation correctness, important omissions, stale
answers, contradictions and abstention.

### Gate P3

- Thresholds ratified after a baseline run.
- Zero uncited high-impact factual answers in the locked suite.
- Known historical plans never surface as current facts.
- Retrieval packet is byte-identical across provider adapters for the same state/query.

## Phase 4 — Goal, preference and decision OS

**Purpose:** move from remembering Artiom to helping him choose well.

### Goal registry

- objectives, measures, deadlines and priority weights;
- hard constraints and standing decisions;
- projects, dependencies, resource budgets and abandoned alternatives;
- conflicts between short- and long-term outcomes.

### Preference ledger

- explicit preferences outrank inferred ones;
- every inference carries evidence, scope, confidence and counterexamples;
- choice observations update calibration, not biography directly.

### Decision engine

- detect/accept a decision trigger;
- generate options including inaction;
- retrieve relevant goals/memory/evidence;
- forecast outcomes and information value;
- run an independent critic;
- calculate deterministic eligibility, cost, reversibility and authority;
- record recommendation, actual choice and later outcome.

Run in shadow mode first: no external action, no pressure to agree.

### First pilot

Daily career/project prioritisation while Market Aligner runs independently:

- what should receive attention/compute today;
- what is blocked;
- what can run unattended;
- what most improves employment/product evidence before Korea;
- what genuinely requires Artiom.

### Gate P4

- meaningful held-out sample of predictions and decisions;
- calibration reported by domain and confidence bucket;
- operator corrections improve future recommendations;
- utility/outcome measure beats a simple deadline/priority baseline before autonomy expands.

## Phase 5 — External state and daily counsel

**Purpose:** remove blindness to real commitments.

### Deliverables

- Gmail and Calendar read-only adapters with explicit scopes.
- Untrusted-content isolation and injection canaries.
- Morning brief generated from the same goal/memory/decision packet.
- Commitments extracted as proposals, not auto-promoted facts.
- Response/receipt ingest from domain tools, beginning with career applications when their API
  boundary is stable.

### Gate P5

- two weeks of useful daily briefs with measured action rate;
- injection tests pass;
- no connector write scope;
- calendar/email claims cite source event IDs and timestamps.

## Phase 6 — Speaking-style model (maturation stage 3)

**Purpose:** make the twin sound appropriate only after it is factually reliable.

### Deliverables

- private operator-reviewed thread→mode map;
- Discord composition/function triage;
- separate current casual, intimate, work-directive and reasoning-critique datasets;
- base/prompted/fine-tuned blind evaluation;
- local adapter registry with immutable versions and rollback;
- explicit mode router and cross-mode leakage canaries.

### Gate P6

- adapter beats strongest prompted/retrieval baseline on blind decision/intent and register;
- no privacy/factual-restraint regression;
- no material intimate/work mode leakage;
- base+retrieval remains one-command rollback.

## Phase 7 — Thinking style and self-scrutiny (stages 4–5)

**Purpose:** model how Artiom reasons without merely reproducing his errors.

### Deliverables

- curated decision/critique episodes with outcome labels;
- explicit decomposition, challenge threshold and evidence-seeking features;
- held-out flawed-answer and real-decision suites;
- dual objective: predict Artiom's likely choice and recommend goal-improving choice;
- bias/habit hypotheses with confirm/refine/discard lifecycle;
- counterfactual postmortems and operator repair feedback.

### Gate P7

- catches decisive missing constraints on held-out cases;
- improves forecast/decision outcomes versus generic critic baseline;
- false-positive self-criticism stays below ratified annoyance threshold;
- never converts a behavioural pattern into a moral/clinical fact.

## Phase 8 — Bounded agency and domain unification

**Purpose:** allow the twin to act in Artiom's favour under proven authority.

### Deliverables

- central authority policy and capability registry;
- action plan/receipt/rollback contract;
- orchestrator adapter;
- domain adapters rather than merged codebases:
  - Market Aligner/application outcomes;
  - Korean progress;
  - travel intelligence;
  - client/project work;
  - approved communications;
- unattended monitor and recovery supervisor;
- provider-extinction/local-restore drills.

### Promotion sequence

1. A1 reminders and recommendations.
2. A2 fully prepared actions requiring approval.
3. A3 reversible local actions with strict budgets.
4. A4 multi-step delegated workflows only after measured low repair rate.

### Gate P8

- zero authority violations in adversarial tests and a substantial live sample;
- every claimed completion has an independently validated receipt;
- rollback succeeds for every action classified reversible;
- provider outage does not lose tasks or corrupt state;
- external outcome metrics—not task volume—show benefit.

## Parallel lanes

Some work can proceed while trust/accuracy mature, but promotion dependencies remain:

- Market Aligner commercial development and scraping/application work continue independently.
- Corpus retrospective and candidate labelling may continue as analysis.
- New exports may land immutably and be inventoried.
- No style adapter promotes before P3.
- No connector write scope or autonomous application submission promotes before P4/P5 and the
  relevant domain authority tests.

## First implementation slice authorised by this plan

P4 in the current session should implement the smallest useful portion of Phases 0–1:

1. `twin_core` local operational ledger with append-only events and receipts.
2. Goal/decision/action schema foundations.
3. Deterministic memory validator and health snapshot.
4. CLI and tests.
5. Maturity scorecard generated from machine evidence.
6. Owner-only permissions for `~/.jarvis` secret/state files.
7. Repair and test the read-only prediction-worker invocation without running a new memory
   ingestion batch.

Telegram transaction integration follows only after this kernel passes its focused failure
tests; changing the live daemon before a durable queue exists would increase risk.

