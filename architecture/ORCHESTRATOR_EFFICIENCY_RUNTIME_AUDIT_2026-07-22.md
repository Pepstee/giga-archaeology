# Orchestrator efficiency runtime audit — 2026-07-22

Scope: the live `orchestrator-v3` runtime executing the JAA programme. This is an evidence
record, not a claim that all token waste is eliminated.

## Verified controls

- The active factory profile sets contained context, active deterministic cache, active host
  assurance, medium effort for all four roles, and tool ceilings of 0/16/12/18 for
  planner/builder/tester/judge.
- `99` focused control tests passed in `3.23s` across deterministic shadow caching, efficiency
  telemetry, context containment, host assurance, and provider routing.
- The latest 50 live work measurements contained 32 provider-cache reuses.
- Eleven durable assurance measurements exist with eight deterministic test-cache hits.
- Three recent JAA claims were rejected by host assurance before a semantic judge was invoked;
  their work measurements recorded zero model tokens.
- The active JAA validator is fenced by `STOP`, one project worker, one claim, and one cycle.
- Semantic judges now receive an explicit exhaustive-review contract: inspect every acceptance
  criterion and persistence/trust boundary, consolidate duplicates, and return all known material
  findings in one verdict. The focused judge/host/telemetry regression set passes `27` tests in
  `1.61s` at orchestrator revision `7f3dcf8`.
- The first live verdict under that contract returned two independent JAA-01 boundary defects in
  one call. This is direct runtime evidence that the change reduces serial find-one/fix-one judge
  cycles without weakening deterministic or semantic review.

## Remaining measured waste

- The latest 50 work measurements still total 8,087,309 tokens. This is historical-window
  consumption, not the cost of a single current claim.
- The largest recent semantic context was 234,927 bytes. It remains below the 256 KiB bounded
  bundle ceiling, but JAA-00's component closure is itself large.
- Recent successful semantic judge invocations consumed roughly 61k–65k tokens. They found real
  publication races, so the semantic pass is valuable; its input closure is still the main token
  target.
- The first exhaustive batched JAA-01 rejection consumed 70,015 tokens. Batching improves defects
  found per call, but does not reduce the large source bundle itself.
- No dedicated durable `duplicate_work_rejected` event was found in the live log. Exact duplicate
  command suppression is test-proven, but production telemetry should not be represented as
  proving a rejection that it does not explicitly record.

## Decision

The speed controls are active and materially working. The next safe optimization is semantic
delta review: preserve the complete component contract and assurance receipts, but give the judge
the changed closure plus dependency/interface summaries rather than every unchanged component
byte. That optimization requires its own completeness negative controls before activation.

## Later live measurement and transport correction

- JAA-01 host assurance completed twice in `5.93s` and `6.25s`. Both exact command receipts were
  cache hits, and all authenticity, closure, dependency, evidence and negative-control gates
  remained true. The deterministic layer is therefore not the current latency source.
- A complete-source Sol review reached the existing `1,200s` watchdog without a verdict. No false
  certificate was produced; the task requeued with `agent_process_timeout`.
- Orchestrator commit `fda7b5a` lowered automatic semantic source injection from 256 KiB to 128
  KiB. Larger components now retain their signed file index and bounded read-only tool budget;
  closure identity, post-review revision checks and the watchdog are unchanged. Forty-five
  focused judge, host-assurance, context and launcher tests passed in `2.85s`.
- A subsequent Terra indexed review was externally abandoned and correctly reclaimed. A Sol
  review launched through an interactive shell was likewise orphaned when that shell closed;
  this exposed supervision as a separate operational fault. A fresh operator STOP created at
  17:29 was respected, leaving JAA-01 queued rather than repeatedly consuming model calls.

These observations narrow the next work: use a durable detached supervisor for model workers,
then measure indexed semantic review. Do not spend additional tokens on deterministic reruns whose
content-addressed receipts remain current.
