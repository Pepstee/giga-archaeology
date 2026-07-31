# Gigabyte handoff — DFI-05 through JAA

Checkpoint time: 2026-07-24 01:07 BST

## Global goal

1. Finish and certify Claude–Codex collaboration.
2. Complete, validate, activate, and prove all remaining orchestrator-v3
   efficiency work without reducing safety, observability, auditability, or
   accuracy.
3. Use the efficient orchestrator to finish and independently certify JAA.
4. Freeze the certified JAA candidate and await Artiom's sign-off.
5. While waiting for sign-off, continue bounded orchestrator-efficiency
   hardening without mutating the frozen JAA candidate.

## Machine and repository authority

The authoritative software-factory state is on Gigabyte under WSL Ubuntu:

- giga-user control plane:
  `/home/gutua/software-factory/giga-user`
- production orchestrator:
  `/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3`
- isolated DFI-05 repair worktree:
  `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-05-refactor`
- preserved original dirty DFI-05 worktree:
  `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-05`
- active DFI-05 controller:
  `/home/gutua/software-factory/.control/dfi-05-deletion-refactor`
- quarantined overflow patch, read-only:
  `/home/gutua/software-factory/.quarantine/dfi-05-post-codex-20260723/DFI05_POST_CODEX_OVERFLOW.patch`

The Mac is no longer the execution authority for this work. Do not copy a Mac
repository over these Gigabyte paths.

## Safety state

- Production orchestrator STOP remains armed.
- `orchestrator-v3.service` remains inactive and disabled.
- Production remains on commit `35efb19...` on
  `efficiency/e2-shadow-cache`.
- JAA has not been resumed or mutated during this DFI-05 repair.
- No writer, reviewer, or test lease is live.
- The DFI-05 controller is deliberately `paused` because a Sonnet process was
  interrupted after exceeding the 20-minute transport bound.
- A paused controller may accept the next `worker` call directly. `recover`
  is only for a stale `running` lease and correctly refuses here.

Before any mutation, prove these facts again from the host.

## Collaboration controller — completed and certified

Authoritative giga-user commit:
`7e6311182554d8dadf2c0c0e78d5af5cb75a402b`

Certified controller evidence:

- exact allocation policy: Sonnet 70%, Codex 30%;
- only one mutable lease at a time;
- Codex review follows Sonnet writing, never concurrently;
- exact deterministic test receipts can be reused;
- 439 host tests passed;
- independent Fable review passed;
- certificate:
  `/home/gutua/software-factory/.control/factory-turnstile-activation-candidate/evidence/cert_20f91ab28e6d1750fcdfdab313edd819d57b76e850f99058fde488bfd5eb642c.json`

Operational rule: Sonnet is the majority coder; Codex is the independent
reviewer/coordinator; Fable is the authority at milestones. The 70/30 measure
is weighted substantive work, not call count. Never let two actors mutate or
test the same candidate concurrently.

## DFI-05 exact current state

Base commit:
`dcf509753845552a906a5a1a04fcdad754cb6471`

Current candidate hash:
`ba01fafaa86b6f996018efaefa78bc6c375cc2a3a7d52838f13ec0374f86a3c0`

Current production diff against the base:

- 356 added lines;
- 10 deleted lines;
- 346 net production lines;
- hard ceiling: 350 net production lines.

Current controller allocation ledger:

- Sonnet weight: 13.0;
- Codex weight: 0.0;
- failed/interrupted calls were correctly excluded;
- final independent Codex review weight must restore the required 70/30
  allocation. Query the ledger immediately before choosing its weight:
  Codex weight = successful Sonnet weight × 3 / 7.

Do not trust this checkpoint in place of re-running `status`, `allocation`,
`git status --short`, `git diff --numstat`, and process checks.

## DFI-05 findings and repairs

Independent Codex previously rejected the original 348-net-line candidate for
four substantive defects.

1. Cohort seal was only hash-shaped; canonical seal identity, declared cohort,
   and post-seal admission time were not enforced.
   - **Still open. This is the only mechanical repair remaining.**
2. Task manager did not verify exact fallback/admission/scope bindings before
   model invocation.
   - Mechanically repaired in the current candidate.
   - Negative matrix now covers parent, project, epoch, intent, manifest,
     certificate, programme position, slice, and maximum authority.
   - Every mismatch proves `llm_invoked=false`.
   - Focused result after the interrupted Sonnet lease:
     `34 passed in 2.90s`; Ruff clean; `git diff --check` clean.
   - This repair is not holistically certified until the final Codex/Fable
     review.
3. Repository claim did not bind fallback parent/project/intent.
   - Mechanically repaired with three negative regressions.
4. Replay verification did not bind the complete task/scope package.
   - Mechanically repaired.
   - The freeze marker now hashes the complete closed scope and factory epoch,
     including findings and untrusted-data contents.
   - Focused result at that checkpoint: 25 passed.

Fable's binding budget ruling:

- `GO_DELETION_REFRACTOR`;
- final DFI-05 ceiling remains 350;
- 351 is a hard stop;
- canonical cohort seal validation and pre-seal/foreign-cohort rejection
  belong in DFI-05;
- cohort rate denominator/minimum/ceiling evaluation is deferred to the later
  activation soak;
- do not copy the 521-line overflow patch wholesale;
- report:
  `/home/gutua/software-factory/giga-user/reports/FABLE_DFI05_POST_CODEX_BUDGET_RULING_2026-07-23.md`

## Next exact action — repair finding 1 only

Give Sonnet one small safe-mode package. It must:

1. Replace `cohort_seal_id` as a free hash-shaped admission argument with the
   actual closed cohort-seal record, or an equally strong host-owned
   representation.
2. Recompute and compare its canonical identity under one explicit domain.
   The `cohort_seal_id` field must not hash itself; compute identity from the
   closed unsigned record.
3. Require the admission `cohort_id` to equal the seal's declared
   `cohort_id`.
4. Require certificate/admission `issued_at` to be at or after the seal's
   `sealed_at`, using a deterministic comparable timestamp contract.
5. Add negative regressions for:
   - forged/mismatched canonical seal identity;
   - foreign cohort;
   - pre-seal admission;
   - malformed/ambiguous time representation if the timestamp contract
     permits strings and numbers.
6. Reuse/delete existing hash-shape-only logic. Do not implement cohort-rate
   evaluation.
7. Keep final net production at or below 350.
8. Run only the focused DFI-05 tests, Ruff, and `git diff --check`.
9. Do not commit.

Use Claude CLI only in the known working configuration:

`claude -p PROMPT --model sonnet --effort low --safe-mode --tools "Bash,Edit,Read" --dangerously-skip-permissions`

Ordinary Claude CLI with plugins/hooks/MCP caused repeated silent waits.
Safe-mode restored editing, but the last package still spent roughly sixteen
minutes analysing before its first production edit. Enforce the bounded
allowance and record this latency as efficiency evidence.

Run it through:

`/home/gutua/software-factory/giga-user/scripts/factory_turnstile.py`

with:

- control dir:
  `/home/gutua/software-factory/.control/dfi-05-deletion-refactor`
- worktree:
  `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-05-refactor`
- actor: `sonnet`

## DFI-05 acceptance sequence after finding 1

1. Prove no live lease and no production/JAA process.
2. Recompute candidate hash and net production budget.
3. Run the focused DFI-05 suite through the turnstile.
4. Run the exact same suite again and prove `reused:true`.
5. Run affected scheduler/task-manager/repository suites once.
6. Run Ruff and `git diff --check`.
7. Build a bounded deterministic review context; never include recursive
   controller state or giant one-line JSON.
8. Run independent Codex review against the exact candidate hash. Codex may
   not write. Bind the review weight to the exact 70/30 policy.
9. If Codex requests changes, return a new tiny package to Sonnet
   sequentially.
10. Give Fable the candidate hash, bounded diff, exact tests, budget, negative
    controls, allocation, and reuse receipt. Fable has no tools and must rule
    only on supplied evidence.
11. Commit only after Codex and Fable pass.
12. Re-certify the committed bytes so the certificate binds the committed
    candidate, not merely the pre-commit worktree.

## After DFI-05

Continue the revised DFI roadmap from:

`/home/gutua/software-factory/giga-user/reports/ORCHESTRATOR_V3_POST_DFI04_REVISED_ROADMAP_2026-07-23.md`

For every stage:

- one bounded stage/worktree/controller;
- Sonnet writes, Codex independently reviews, Fable rules at milestones;
- exact tests are reused, not rerun;
- full suites run only at defined wave/certification boundaries;
- record wall time, model allocation, tool calls, input/output tokens where
  observable, cache hits, duplicate rejection, and accepted-work ratio;
- no activation until the efficient profile is certified;
- prove real token/time savings on controlled work before JAA resumes.

Important known efficiency defects to include in the remaining programme:

- giant one-line controller/context JSON can flood Codex review context
  (observed 77k+ token review);
- ordinary Claude customisations/plugins/hooks/MCP can create 20-minute silent
  transport stalls;
- exact deterministic reuse existed previously but was inactive, producing
  zero savings;
- evidence reuse must bind exact candidate, command, runtime, and environment;
- no concurrency between mutable model operations.

## JAA sequence

Only after the efficient orchestrator profile is certified and controlled
savings are proven:

1. Read the JAA handoff and preserve its active uncommitted repair.
2. Re-establish exact JAA baseline, schema, test, and persistence state.
3. Resume JAA through the efficient orchestrator.
4. Keep Sonnet as majority coder, Codex as independent reviewer/coordinator,
   and Fable as milestone authority.
5. Finish all remaining slices without reducing test depth or evidence
   quality.
6. Run independent certification, migration/rollback/crash-recovery and
   integrity gates required by the JAA contracts.
7. Freeze the certified candidate and await Artiom's explicit sign-off.
8. Do not mutate frozen JAA while waiting.

Primary JAA handoff:

`/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3/docs/efficiency/JAA_ORCHESTRATOR_SKILLTREE_HANDOFF_2026-07-22.md`

## Career evidence to preserve

The strongest portfolio claim is not merely that the orchestrator built JAA:

> I measured a self-built autonomous software factory, discovered it was
> spending over one million tokens per accepted task, identified the
> architectural causes, and redesigned its assurance economics without
> weakening correctness.

The next phase must prove that claim quantitatively.

