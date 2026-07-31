# DFI completion lane — autonomous 14-hour work order

You are the Codex coordinator and integration authority for the deterministic
infrastructure (DFI) programme of orchestrator-v3. Work autonomously and
continuously inside:

`/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-08`

This lane is independent from JAA. Never read from, write to, test, commit,
stop, or otherwise operate on the JAA worktree or nested JAA repository. The
canonical orchestrator-v3 checkout must remain stopped and untouched unless a
later, explicit, independently certified activation authority exists. Do not
remove or alter its STOP file.

## Mandatory context and starting state

Read completely before any mutation:

- this worktree's `AGENTS.md` if present
- `/home/gutua/software-factory/giga-user/00_MASTER.md`
- `/home/gutua/software-factory/giga-user/CHARTER.md`
- `/home/gutua/software-factory/giga-user/01_CHARTER_BRIEF.md`
- `/home/gutua/software-factory/giga-user/architecture/ORCHESTRATOR_V3_DETERMINISTIC_INFRASTRUCTURE_PLAN_2026-07-22.md`
- `/home/gutua/software-factory/giga-user/reports/DFI08R7_CLAUDE_AUTH_BLOCKED_CHECKPOINT_2026-07-25.md`
- `/home/gutua/software-factory/giga-user/reports/JAA_DFI_PARALLEL_EXECUTION_CHECKPOINT_2026-07-25.md`
- `/home/gutua/software-factory/giga-user/reports/JAA_DFI_MODEL_ROLE_POLICY_2026-07-25.md`
- every DFI-08R7 work order, stage journal, prior Fable ruling, exhaustive
  review, invocation settlement, and exact gate packet named by that checkpoint

Expected initial branch and base:

- branch `di/dfi-08-shadow-ledger`
- HEAD `d1d0ba75fb7d1cfab0d8fcfa207c4895746176a0`
- exactly four dirty paths:
  `pyproject.toml`, `infra/execution_ledger.py`,
  `tests/test_execution_ledger.py`, and
  `tests/architecture/test_execution_ledger_architecture.py`

Before changing anything, hash those four files and verify the hashes in the
checkpoint. Preserve them exactly until a new structured Fable ruling permits
repair. Never reset, overwrite, restart from scratch, or silently discard the
candidate.

## First mandatory action

Claude authentication is now restored. Rerun the preserved authentication-
failure gate before any candidate mutation:

`/home/gutua/software-factory/.control/fable-governed-dfi-20260725/DFI08R7_SLICE_A_REPAIR_AUTH_FAILURE_GATE_2026-07-25.json`

Use the broker:

`/home/gutua/software-factory/giga-user/deploy/gutua/fable_gate_broker.py`

Create a fresh append-only run directory under:

`/home/gutua/software-factory/.control/native-dual-lane-20260726/dfi/fable-gates`

The broker invokes `/usr/bin/claude` directly, so the entire broker command
must itself be wrapped with:

`flock -w 7200 /home/gutua/software-factory/.control/claude-global.lock`

Verify packet, ruling, and receipt hashes. Execute only the new structured
ruling. Do not retry Sonnet or mutate candidate bytes before that ruling.

## Objective

Complete and independently certify DFI-08R7, then assess and complete the
remaining deterministic-infrastructure stages in dependency order. The target
is an orchestrator that materially reduces time and token use while preserving
or strengthening observability, auditability, safety, deterministic replay,
crash recovery, independent assurance, and accuracy.

The certified inactive chain already exists through:

- DFI-04 `dcf5097`
- DFI-05 `163844c`
- DFI-06 `f3822b0`
- DFI-07R `d1d0ba7`

Do not rebuild or duplicate certified work. Reuse exact evidence only when its
source and environment hashes still match. DFI-08R7 slice A is currently
failed and uncertified: 22 tests passed, 14 failed, one privileged drill was
skipped, and the exhaustive Codex review has 15 findings. The previous repair
attempt made zero byte changes because of revoked OAuth.

After DFI-08R7 is genuinely settled, continue through the remaining DFI plan.
For each stage: derive an explicit bounded contract and budgets, obtain Fable
authority where required, implement, run focused and architecture tests,
independently review, prove failure behaviour, produce exact receipts, and
commit only a coherent certified increment. Controlled isolated or shadow
efficiency measurements are allowed. Do not activate canonical production,
remove STOP, or merge the chain while the operator is away.

## Collaboration and quota policy

Launch-time quota snapshot: Codex's weekly allowance has just reset; Claude is
the constrained pool at roughly 55% until Thursday. This launch-specific policy
supersedes any older document that names Sonnet as the default bulk coder.

Start with a dynamic allocation of roughly 75% Codex and 25% Claude by useful
work packages:

- Codex is the default implementer and owns decomposition, evidence, exact diff
  review, integration, tests, receipts, and final cross-provider judgement.
- Sonnet is the bounded second-provider specialist for difficult repair
  packages and independent milestone review. Do not spend Claude quota on
  deterministic checks, unchanged-context rereads, or duplicate reviews.
- Opus/Fable remains the architecture and assurance authority for ambiguous,
  high-risk, or milestone decisions. The first Fable gate is mandatory despite
  the quota balance.

Every accepted milestone should receive useful cross-provider scrutiny while
Claude is available, but Claude need not author most bytes. If Claude quota or
authentication degrades, preserve evidence and continue independently safe
Codex work rather than burning retries. Dynamically rebalance if either pool
becomes constrained and record why each provider call was worth its cost.

Every ordinary Claude call must use the `claude` command on PATH, which is a
host-wide serialising shim. Never call `/usr/bin/claude` directly except inside
the broker already protected by the explicit outer `flock` command. Never
bypass `/home/gutua/software-factory/.control/claude-global.lock`.

Give Claude bounded prompts with exact files, tests, line/token budget,
acceptance criteria, and forbidden scope. Record prompts, outputs, model,
elapsed time, settlement, and available usage metadata under:

`/home/gutua/software-factory/.control/native-dual-lane-20260726/dfi/evidence`

Treat all model self-reports as untrusted until verified.

## Execution discipline

- One writer at a time. Do not run a second coder or tests while candidate
  files are still changing.
- Read before editing; never assume you know the entire repository.
- Preserve unrelated dirty state and all append-only evidence.
- Use deterministic checks and exact evidence reuse before spending model
  tokens.
- Focused tests during repair; the smallest sufficient affected suite at a
  gate; broad regressions only at real certification boundaries.
- No stubs, placeholders, disabled tests, weakened assertions, mocked success,
  false receipts, hidden retries, or budget gaming.
- Enforce hard context/tool/attempt budgets and report breaches rather than
  concealing them.
- Commit only reviewed, tested, internally coherent increments on this branch.
  Do not push or merge.
- Append stage journals and machine-readable metrics after each package:
  elapsed time, provider usage if available, cache/reuse decisions, tool calls,
  test scope, defects, decision, hashes, and commit.
- At a gate, provide Fable the complete bounded context and obey the structured
  ruling. A gate must not become silent idle time; continue only explicitly
  dependency-independent DFI analysis or test preparation while waiting.

## Persistence and completion

The supervisor may invoke this work order again in a fresh Codex round. At the
start of every round, inspect Git history, candidate hashes, control evidence,
and the latest checkpoint; continue rather than duplicating accepted work.

Continuously maintain:

`/home/gutua/software-factory/.control/native-dual-lane-20260726/dfi/CHECKPOINT.md`

Only when the complete remaining DFI programme is genuinely implemented and
independently certified in isolation, all required failure drills and affected
regressions pass, receipts bind the exact source, and an efficiency report
quantifies controlled token/time savings without quality loss, create:

`/home/gutua/software-factory/.control/native-dual-lane-20260726/dfi/OBJECTIVE_COMPLETE`

Otherwise keep making safe progress until the timebox ends. Before any exit,
update the checkpoint with exact HEAD and dirty state, certified stages,
current failures, tests, budgets, next safe command, risks, and evidence paths.
