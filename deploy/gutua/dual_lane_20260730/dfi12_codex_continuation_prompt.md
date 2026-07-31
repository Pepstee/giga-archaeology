# DFI-12 governed continuation — 2026-07-30

Act as the sole Codex coordinator and integration writer for DFI-12 in:

`/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-12`

JAA is priority one and may run concurrently in its independent worktree.
Never read, write, test, stop or otherwise operate on JAA source or control
directories. DFI is priority two. Every Claude/Fable invocation across the
factory must remain serialized through:

`/home/gutua/software-factory/giga-user/deploy/gutua/run_claude_serialized.sh`

and the host-wide Claude lock. JAA has first claim on contested specialised
model capacity.

## Exact authority

Read repository instructions and hash-verify all of:

- `/home/gutua/software-factory/giga-user/reports/FACTORY_WORK_PRIORITY_POLICY_2026-07-29.md`
  - SHA-256:
    `2dbc95ea748507f3b2a50c1f188ab89c98ce0d991112f88840738ebc8dc3daf5`
- `/home/gutua/software-factory/.control/dfi11-codex-20260729/DFI12_ADMISSION_GATE_DRAFT_20260730.json`
  - SHA-256:
    `8adbaa1b9acd02c4df89473598be9940bd6c2f1f9fdfe54bd352ad00b9e96197`
- `/home/gutua/software-factory/.control/dfi11-codex-20260729/DFI12_ADMISSION_FABLE_RULING_20260730.json`
  - SHA-256:
    `a02ecf55964c8d503f84826fd66e6ea19ad4fa127f1c9731534facd280c6c142`
- `/home/gutua/software-factory/giga-user/reports/DFI12_OPERATOR_PEAK_RATIFICATION_2026-07-30.md`
  - SHA-256:
    `02343880d3de9a558106678ed0b86ffd1372e8460699e97ec34d55a2b0a7a7cc`
- `/home/gutua/software-factory/giga-user/reports/DFI12_ACTIVATION_RECEIPT_2026-07-30.json`
  - SHA-256:
    `5b9d6d2a14b1b8ca05c65fdb89b641abfe05f41f7f83e8f36284f59e47d22f1b`
- `/home/gutua/software-factory/.control/dfi11-codex-20260729/DFI11_POST_COMMIT_CERTIFICATION_RECEIPT_20260730.json`
  - SHA-256:
    `80d84517981e4797dc222586741e4e3ecf7378485d39ace950a3a3d833b9ebd3`

Expected clean initial state:

- branch `di/dfi-12-delta-active`;
- HEAD `17d1b23bb617a2b775ba54a37747ed6dabee0b76`;
- tree `7a06cbd74e246e5fa51987bf7c8ccde179a88b19`;
- no DFI-12 product mutation.

If a prior round advanced the branch, reconcile and preserve it. Never reset,
erase, overwrite or silently abandon work.

## Admitted architecture and scope

Implement active incremental certificates using a separate closed
delta-certificate schema and compact current projection. Do not extend or
reinterpret `AssuranceCertificate`.

New paths:

- `validation/certificate_algebra.py`, net at most `320`;
- `tests/test_certificate_algebra.py`.

Admitted modified paths:

- `infra/schema_registry.py`, closed schema additions only, net at most `180`;
- `control/scoped_completion.py`, one narrow active seam, net at most `60`;
- `validation/delta_review.py`, the admitted FIN-10 refusal-label repair only,
  net at most `2`.

Conditional paths require a written necessity proof before first edit and are
each capped at net `30`:

- `validation/assurance.py`;
- `validation/findings.py`;
- `validation/host_assurance.py`.

Frozen for DFI-12:

- `agents/judge.py`;
- `control/workflow_compiler.py`.

Touching either frozen path voids admission and requires a fresh Fable gate.

## Behavioural contract

- Delta composition is eligible only with one current trusted full ancestor.
- First component certificates, typed scope expansions, integration policy
  boundaries and every release route to authoritative full review before any
  delta-eligibility check.
- Missing, forged, stale or revoked ancestors, open material findings, changed
  dependencies or changed host evidence refuse composition.
- Overlap, order sensitivity, interaction, chain-depth ceiling-plus-one or
  change-surface ceiling-plus-one force a full rebase deterministically.
- Revocation and finding reopening propagate durably through complete lineage.
- The compact projection must equal full append-only lineage replay and cannot
  hide a missing edge, revocation, stale ancestor or reopened finding.
- Rollback routes all semantic review to full mode without product source
  changes and cannot create a second co-authoritative certificate.

All thirteen test names in the Fable ruling are binding. The chain-depth and
change-surface tests must cover both at-ceiling acceptance and
ceiling-plus-one full rebase. The rollback test must prove active failure
followed by rollback yields exactly one current authoritative certificate.

## Numeric, quality and provider bounds

- gross additions at most `700`;
- net additions at most `650`;
- net line `651` is a hard stop for fresh adjudication;
- temporary programme peak at most `5,299`;
- peak expires at DFI-12 post-commit certification and gives no later stage
  headroom;
- reserved `>=1,979`-line cutover retirement tranche remains unclaimed;
- measured judge-token reduction at least `25%` on the delta-eligible subset;
- telemetry must be complete; missing telemetry fails the gate;
- active/full material-verdict parity exactly `100%`;
- material-finding loss exactly `0`.

Provider budget after admission:

- at most one pre-final Sonnet review;
- at most one final exact-source Fable certification;
- failed or interrupted calls count as consumed.

Do deterministic implementation and tests with Codex. Use Sonnet only after
the deterministic candidate is green, as independent coder/reviewer. Fable is
the final authority. Treat all model output as untrusted until exact bytes,
tests and receipts verify.

Reconcile the consumed-but-empty prior DFI-12 admission attempt into the
append-only spend ledger with telemetry recorded as unknown. Never default
unknown usage to zero.

## Completion and safety

- One integration writer in this worktree. Parallel subagents are permitted
  only for genuinely disjoint, read-only or separately isolated work.
- Do not mutate canonical orchestrator-v3 production, STOP, services, daemons,
  epochs or JAA.
- Do not push, merge or deploy.
- No delta-only integration or release certificate.
- No stubs, placeholders, skipped controls, weakened assertions, fabricated
  receipts, line-budget gaming or self-certification.
- Use focused tests while iterating, then the admitted focused and affected
  suites, Ruff, compileall, diff checks and exact line accounting.
- Preserve rollback and all DFI-11 evidence.

Continuously maintain:

`/home/gutua/software-factory/.control/dfi12-codex-20260730/CHECKPOINT.md`

Create `OBJECTIVE_COMPLETE` only after the exact committed DFI-12 tree has
received final Fable certification, all post-commit checks and the immutable
post-commit receipt pass, the spend ledger is reconciled and the temporary
peak is explicitly expired. Create `BLOCKED` only if no safe admitted work
remains.
