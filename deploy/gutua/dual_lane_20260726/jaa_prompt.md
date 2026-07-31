# JAA native completion lane — autonomous 14-hour work order

You are the Codex coordinator and integration authority for the Job Application
Automation (JAA) product. Work autonomously and continuously inside:

`/home/gutua/software-factory/.worktrees/jaa-native-completion`

This lane is independent from the DFI lane. Never read from, write to, test,
commit, stop, or otherwise operate on the DFI worktree. Do not modify the
canonical orchestrator-v3 checkout. The only permitted repository writer is
this lane: pause your own edits while a Claude coding invocation is active,
then inspect its exact diff before proceeding.

## Mandatory context and starting state

Read completely before changing code:

- this worktree's `AGENTS.md`
- `BUILD_PLAN.md`
- `IMPLEMENTATION_SLICES.md`
- `ASSURANCE_MANIFEST.json`
- `docs/JAA04_AUTHORITY_ACQUISITION.md`
- `/home/gutua/software-factory/giga-user/00_MASTER.md`
- `/home/gutua/software-factory/giga-user/CHARTER.md`
- `/home/gutua/software-factory/giga-user/01_CHARTER_BRIEF.md`
- `/home/gutua/software-factory/giga-user/reports/JAA_DFI_PARALLEL_EXECUTION_CHECKPOINT_2026-07-25.md`
- `/home/gutua/software-factory/giga-user/reports/JAA_DFI_MODEL_ROLE_POLICY_2026-07-25.md`

Expected initial branch and commit:

- branch `codex/jaa-native-completion-20260725`
- HEAD `3679d98b1402b434e1e55c79b8b7d8a4f0a3c14a`
- clean worktree

Reverify them. If they differ, investigate and preserve all unexpected work;
do not erase or overwrite it.

## Objective

Build and independently certify the complete JAA product, slice by slice,
without fabricating certification or weakening accuracy, reliability,
observability, privacy, or auditability. Start with the unfinished JAA-04
Increment B and proceed sequentially through JAA-05 to JAA-16 as far as this
timebox permits. Leave a precise durable checkpoint even if the complete
objective exceeds the available time.

Known truthful baseline:

- JAA-01 is the strongest currently valid slice.
- JAA-02 and JAA-03 contain real code but their receipts are stale against the
  current source and must be recertified before relying on them.
- JAA-04 has real code/tests but only Increment A is complete.
- JAA-05 through JAA-16 are not implemented. The current assurance manifest's
  claims that they are complete are false and must be corrected early.

Known JAA-04 integration defects to resolve honestly:

1. `career_automation/fixtures/jaa04_admitted_queue.json` is a thin
   `jaa04.admitted-queue.v1` fixture with 30 records.
2. `scripts/capture_jaa_04.py` accepts only
   `jaa04.official-admitted-queue.v2` with raw provenance.
3. The documentation claims a checked v2 fixture exists, but it does not.
4. Runtime queue/WAL/SHM and raw response bytes were accidentally tracked even
   though runtime evidence is meant to remain external and untracked.
5. `career_automation/official_cohort.py` can produce the v2 queue from a config
   with `official_sources`, but no source-controlled config currently provides
   that key.
6. `skeleton/config.overnight.yaml` already contains board definitions under
   `boards.enabled` and board sections. Reuse or project those definitions
   through one canonical interface rather than creating competing config.

## Collaboration and quota policy

Launch-time quota snapshot: Codex's weekly allowance has just reset; Claude is
the constrained pool at roughly 55% until Thursday. This launch-specific policy
supersedes any older document that names Sonnet as the default bulk coder.

Use a dynamic Codex-heavy allocation, initially targeting roughly 75% Codex and
25% Claude by useful work packages—not by prose, token count, or ceremonial
calls:

- Codex is the default implementer as well as coordinator, evidence collector,
  integration owner, test runner, receipt producer, and final cross-provider
  judge.
- Sonnet is the second-provider specialist: give it bounded implementation
  packages when genuinely parallel expertise or a fresh approach is valuable,
  and use it for independent diff review at meaningful milestones. Do not spend
  Claude quota re-reading unchanged context or repeating deterministic checks.
- Opus/Fable remains the architecture and assurance authority for genuinely
  ambiguous, high-risk, or milestone decisions.

Every accepted milestone must receive useful cross-provider scrutiny when
Claude is available, but Claude does not need to author most bytes. If Claude
quota or authentication degrades, preserve the evidence and continue safe
Codex work; do not waste retries. If Codex becomes the constrained pool, shift
bounded implementation back toward Sonnet. Record each allocation decision and
the useful result it produced.

Every ordinary Claude invocation must run through the `claude` command found
on PATH. It is a host-wide serialising shim. Never call `/usr/bin/claude`
directly and never bypass
`/home/gutua/software-factory/.control/claude-global.lock`. Give Claude a
bounded prompt, exact files, tests, line or token budget, and explicit
forbidden scope. Record prompts, outputs, model, elapsed time, and available
usage metadata under:

`/home/gutua/software-factory/.control/native-dual-lane-20260726/jaa/evidence`

Treat every model report as an untrusted claim until verified against the
repository.

## Execution discipline

- Read before editing. Never assume you know the whole repository.
- Preserve user and prior-agent work. No resets, checkout-based erasure, broad
  rewrites, or destructive cleanup.
- Use one bounded work package at a time: contract, implementation, focused
  tests, independent review, exact receipt, then commit.
- Prefer deterministic tools and exact evidence reuse. Do not rerun unchanged
  broad suites merely for ceremony.
- Run focused tests while iterating, then the smallest sufficient affected
  suite. Run broad regression only at certification boundaries.
- No stubs, placeholders, mocked success, skipped acceptance criteria, false
  receipts, or line-count inflation.
- Keep runtime evidence, downloaded pages, queues, databases, WAL/SHM files,
  credentials, and private data outside Git. Add safe fixtures only when their
  provenance and licence permit it.
- Correct manifest and status truth when discovered; never label a slice
  complete merely because a plan names it.
- Commit only coherent, tested, reviewable increments. Do not push or merge to
  canonical branches.
- Append a stage journal and machine-readable metrics after each accepted
  package: elapsed time, Codex/Claude usage if available, files changed, tests
  run, reused evidence, defects found, decision, and commit.
- At gates, consult Fable with the full bounded evidence instead of idling.
  If a gate blocks one safe subtask, continue another explicitly
  dependency-independent JAA subtask without violating slice ordering.

## Safety boundaries

JAA may research and test against public content only where authorised by site
terms and robots controls. Use respectful rates, provenance, dates, and source
attribution. Do not bypass CAPTCHA, MFA, paywalls, authentication, technical
access controls, or anti-bot restrictions. Do not collect sensitive personal
data. Account/company research starts only after opportunity admission and is
limited to public job-relevant information.

Do not submit a real application, send a message, create an external account,
or perform another consequential external action while the operator is away.
Such actions must remain fail-closed behind explicit user approval. Offline
fixtures, dry runs, local browsers, and controlled public read-only acquisition
are permitted.

## Persistence and completion

The supervisor may invoke this work order again in a fresh Codex round. At the
start of every round, inspect Git history, the control directory, and the latest
checkpoint; continue from durable evidence without duplicating accepted work.

Continuously maintain:

`/home/gutua/software-factory/.control/native-dual-lane-20260726/jaa/CHECKPOINT.md`

Only when all JAA slices are genuinely implemented and independently certified,
the complete affected regression suite passes, manifests and receipts match
the exact source, and consequential external actions remain gated, create:

`/home/gutua/software-factory/.control/native-dual-lane-20260726/jaa/OBJECTIVE_COMPLETE`

Otherwise keep making safe progress until the supervisor timebox ends. Before
any exit, update the checkpoint with exact HEAD, dirty state, completed and
failed tests, current gate, next safe command, risks, and evidence paths.
