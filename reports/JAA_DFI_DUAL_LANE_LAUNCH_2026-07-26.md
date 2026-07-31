# JAA + DFI dual-lane unattended launch — 2026-07-26

## Purpose

Run JAA product completion and orchestrator deterministic-infrastructure work
concurrently for up to 14 hours on the dedicated Gigabyte software factory.

## Isolation

- JAA worktree:
  `/home/gutua/software-factory/.worktrees/jaa-native-completion`
- DFI worktree:
  `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-08`
- Shared control root:
  `/home/gutua/software-factory/.control/native-dual-lane-20260726`
- User services: `giga-jaa-native.service` and `giga-dfi-native.service`

The lanes have separate repositories/worktrees, prompts, logs, evidence,
checkpoints, and supervisor locks. Claude calls share one host-wide `flock`
lock. JAA cannot mutate DFI; DFI cannot mutate JAA. Canonical orchestrator-v3
remains stopped with STOP armed.

## Model roles and launch allocation

At launch, Codex's weekly allowance had just reset while Claude remained the
constrained pool at roughly 55% until Thursday. The initial allocation is
therefore approximately 75% Codex and 25% Claude by useful work packages:

- Codex: default implementer, coordinator, decomposition, integration, tests,
  receipts, and final cross-provider review.
- Claude Sonnet: bounded second-provider implementation and independent
  milestone review where it adds distinct information.
- Fable/Opus: architecture and assurance decisions at high-risk gates.

This is dynamically quota- and competence-aware, not a fixed percentage. Every
Claude call must justify its cost through distinct implementation or review
coverage; deterministic checks and unchanged-context rereads remain local.

## Unattended boundaries

- No real job application submission or consequential external action.
- No bypass of CAPTCHA, MFA, authentication, paywalls, terms, or access
  controls.
- No canonical orchestrator activation, merge, or STOP removal.
- No stubs, false certification, weakened tests, or destruction of dirty work.
- Each lane must leave a durable checkpoint even when the timebox expires.
