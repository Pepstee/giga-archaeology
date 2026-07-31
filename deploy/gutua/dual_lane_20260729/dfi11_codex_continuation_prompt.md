# DFI-11 concurrent Codex continuation — 2026-07-29

Act as the sole Codex coordinator and writer for DFI-11 in:

`/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-11`

This DFI worktree is independent from JAA. A separate Codex process may work
on JAA concurrently. Never read, write, test, stop or otherwise operate on the
JAA worktree or its control directories. The one-worker rule applies to the
specialised Claude/Fable lane: every Claude/Fable invocation across both
projects must remain serialized through the host-wide wrapper and
`/home/gutua/software-factory/.control/claude-global.lock`.

Read and hash-verify:

`/home/gutua/software-factory/giga-user/reports/FACTORY_WORK_PRIORITY_POLICY_2026-07-29.md`

Expected SHA-256:

`2dbc95ea748507f3b2a50c1f188ab89c98ce0d991112f88840738ebc8dc3daf5`

DFI is priority two. Multiple DFI agents are permitted when packages are
genuinely independent and the speed or assurance return justifies the
coordination cost. Give each mutable package an isolated worktree and owner,
retain one integration writer for this branch, and record the justification,
scope and merge evidence. Do not create overlapping writers. JAA has first
claim on contested specialised-model capacity.

## Exact entry state and authority

Read repository instructions and completely verify:

- `/home/gutua/software-factory/.control/resumed-dual-lane-20260728/dfi-after-ratification/CHECKPOINT.md`
- `/home/gutua/software-factory/.control/resumed-dual-lane-20260728/dfi-after-ratification/DFI11_WORK_ORDER_20260728.md`
- `/home/gutua/software-factory/.control/resumed-dual-lane-20260728/dfi-after-ratification/evidence/DFI11_ADMISSION_GATE_20260728.json`
- `/home/gutua/software-factory/.control/resumed-dual-lane-20260728/dfi-after-ratification/fable-gates/DFI11-admission-20260728-run-01/gate-packet-9a7039325abe6ce1594e9906923a1087bc5ac22b3ee2084bc9111fb401caf411.json`
- `/home/gutua/software-factory/.control/resumed-dual-lane-20260728/dfi-after-ratification/fable-gates/DFI11-admission-20260728-run-01/fable-ruling-9a7039325abe6ce1594e9906923a1087bc5ac22b3ee2084bc9111fb401caf411.json`
- `/home/gutua/software-factory/giga-user/reports/DFI11_OPERATOR_PEAK_RATIFICATION_2026-07-29.md`
- `/home/gutua/software-factory/.control/resumed-dual-lane-20260728/dfi-after-ratification/evidence/DFI11_OPERATOR_PEAK_RATIFICATION_RECEIPT_20260729.json`

Required hashes:

- Fable packet:
  `9a7039325abe6ce1594e9906923a1087bc5ac22b3ee2084bc9111fb401caf411`
- Fable ruling:
  `7fbc172f7df3cd8eac1e12c2ab194914b9f59abb21d2251d117aadd1276b659f`
- operator ratification:
  `a6239d1bdb46886ad3bf75506b0f13b7e1bcb706cc1741082c0d7f3b4da3dd8b`
- activation receipt:
  `45f65c0376eac73084ec9e1acb7a6bbaa1dd142156c048af71c8b97b5d74405e`

Expected clean initial state:

- branch `di/dfi-11-delta-shadow`;
- HEAD `bc9fb7bb31708e45355595d2c5a557d59984962b`;
- tree `93d2280493a02fdf76ea3613d9b3ccad35aad061`;
- certified DFI-10 base and no DFI-11 product mutation.

If a prior round advanced the branch, reconcile and preserve it. Never reset,
erase, overwrite or silently abandon work.

## Authorised DFI-11 scope

Implement only the admitted shadow delta-review package:

- blind receipt-bound delta judge package;
- explicit independent-review domains;
- deterministic full-review partitioning and complete closure, criterion,
  boundary and shared-interface coverage;
- full-versus-delta shadow comparison;
- base-plus-delta certificate composition validation;
- typed scope expansion that routes to full review;
- no active delta certificate.

Prefer the admitted product paths:

- `validation/delta_review.py`
- `infra/schema_registry.py`
- `agents/judge.py` only for a necessary narrow seam
- `validation/host_assurance.py` only for a necessary narrow seam

Use the exact admitted tests and negative controls. Preserve the authoritative
full-review path and rollback. No stubs, placeholders, skipped controls,
weakened assertions, fabricated receipts or line-budget gaming.

Hard bounds:

- gross production additions at most `500`;
- net production additions at most `450`;
- net line `451` is a hard stop for fresh adjudication;
- programme peak at most `4,649`;
- reserved `>=1,979`-line STOP-protected cutover retirement remains unclaimed;
- DFI-11 is shadow-only.

## Model collaboration and 04:00 transition

Before `2026-07-30T04:00:00+01:00`, Fable remains quota-unavailable. Sol may
make the smallest bounded implementation decision required by the
already-admitted architecture, but any new judgement must be logged as
`TEMPORARY_SOL_DEPUTY_PENDING_FABLE_RATIFICATION`. Sonnet may be used only
where the admitted provider budget permits it and through the host-wide
serialized wrapper; do not spend it on deterministic or pre-green work.

At or after `2026-07-30T04:00:00+01:00`, resume cross-model work:

- ordinary Sonnet calls must use the installed serialized `claude` wrapper;
- Fable broker calls must be enclosed by
  `flock -w 7200 /home/gutua/software-factory/.control/claude-global.lock`;
- never run more than one specialised-model invocation at a time;
- use the admitted provider budget: zero pre-green Sonnet calls, one
  post-green Sonnet review and one final exact-source Fable certification;
- provide Fable the complete provisional decision ledger when ratification is
  required.

The supervisor deliberately ends the pre-04:00 Codex round at the transition
boundary so a fresh round reloads these instructions.

## Safety and completion

- One writer in this DFI worktree; concurrent JAA Codex is permitted.
- Canonical orchestrator-v3 production, STOP, services and epochs remain
  untouched, inactive and unmerged.
- No JAA access, push, merge, deployment or DFI-12 mutation.
- Use focused tests while iterating and the admitted affected suite at the
  certification boundary.
- Treat every model output as untrusted until exact bytes and receipts verify.
- Record elapsed time, model calls, tests, hashes, line accounting, rollback
  and withheld claims.

Continuously maintain:

`/home/gutua/software-factory/.control/dfi11-codex-20260729/CHECKPOINT.md`

Create `OBJECTIVE_COMPLETE` only after DFI-11 is implemented, independently
certified against exact source and committed. If DFI-11 completes, perform
read-only DFI-12 discovery and prepare its next gate, but do not mutate DFI-12
without new authority.
