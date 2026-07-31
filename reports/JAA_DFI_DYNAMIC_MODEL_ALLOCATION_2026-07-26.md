# Dynamic model allocation for JAA + DFI — 2026-07-26

## Decision

Use Codex for the majority of current production work because its weekly
allowance has reset, while preserving Claude as a distinct second-provider
specialist rather than exhausting it on bulk or duplicate work.

Initial target: approximately 75% Codex and 25% Claude by useful work packages.
This is a control heuristic, not a quota to satisfy.

## Roles

- Codex: default coding, decomposition, integration, deterministic checks,
  focused and regression testing, evidence binding, receipts and final
  cross-provider judgement.
- Sonnet: difficult bounded coding packages and independent reviews where a
  different model is likely to expose different defects.
- Fable/Opus: architecture, scope exceptions and high-risk certification gates.

## Rebalancing law

Reassess after milestones or provider failures. Shift work toward the provider
with more available allowance, but never remove independent cross-provider
scrutiny from meaningful acceptance boundaries. Do not spend model quota on
checks that deterministic tools or valid hash-bound evidence can answer.

