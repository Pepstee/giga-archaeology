# Fable handoff — inter-model Factory Turnstile

**Date:** 2026-07-23  
**Authority:** Artiom has stopped Codex and handed this work to Fable.  
**Immediate objective:** Assess, correct and implement the inter-model concurrency control
harness before any DFI-05, production or JAA work resumes.

## Verdict-first state

- DFI-04 is validly certified and committed.
- DFI-05 is dirty, preserved and explicitly **not certified**.
- The unattended factory continuation order is paused by the operator.
- Production STOP is armed; the production service is inactive.
- JAA remains paused and untouched.
- Windows Codex, WSL Claude/Sonnet and all pytest/Ruff processes were stopped.
- Two bounded Sonnet attempts to implement the new harness were terminated after long first-turn
  inference latency. Neither wrote code.

The new turnstile worktree therefore contains only two untracked instruction documents and no
implementation:

```text
?? reports/FACTORY_TURNSTILE_V1_WORK_ORDER_2026-07-23.md
?? reports/FACTORY_TURNSTILE_V1_PACKAGE_A_2026-07-23.md
```

## Gigabyte paths

- Software-factory root:
  `/home/gutua/software-factory`
- GIGA governance:
  `/home/gutua/software-factory/giga-user`
- Turnstile implementation worktree:
  `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`
- Turnstile branch:
  `factory/turnstile-v1`
- Turnstile base:
  `82cb47ef82d6973c08513686bcca6ed0469418a7`
- Dirty DFI-05 worktree — preserve, do not modify:
  `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-05`
- Production orchestrator-v3 — preserve, do not modify:
  `/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3`

## Read order

Read these completely before deciding or editing:

1. `/home/gutua/software-factory/giga-user/CHARTER.md`
2. `/home/gutua/software-factory/giga-user/CONTEXT.md`
3. `/home/gutua/software-factory/giga-user/reports/DFI05_INTERMODEL_CONCURRENCY_STOP_CHECKPOINT_2026-07-23.md`
4. `/home/gutua/software-factory/giga-user/migration/GIGABYTE_UNATTENDED_FACTORY_CONTINUATION_ORDER_2026-07-23.md`
5. `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/reports/FACTORY_TURNSTILE_V1_WORK_ORDER_2026-07-23.md`
6. `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/reports/FACTORY_TURNSTILE_V1_PACKAGE_A_2026-07-23.md`
7. `/home/gutua/software-factory/giga-user/reports/ORCHESTRATOR_V3_POST_DFI04_REVISED_ROADMAP_2026-07-23.md`

## What failed in the unattended run

1. Codex and Sonnet wrote/reasoned over the same mutable DFI-05 worktree concurrently.
2. Complete pytest suites were launched repeatedly while files were changing.
3. Commands used `pytest ... | tail` without truthful pipeline exit capture, so failing pytest
   runs appeared successful.
4. The monolithic Codex task accumulated approximately 44.27 million tokens, approximately
   43.56 million of them cached input, through repeated context carry-over.
5. The intended 30/70 Codex/Claude division was not measured or enforced.

The preserved DFI-05 candidate has 348 net production lines but is not accepted. Its exact recovery
patch and failures are bound in the stop checkpoint. Do not inspect it by editing or attempt to
finish it until the turnstile is independently reviewed and installed.

## Required solution

The proposed solution is one deterministic **Factory Turnstile**:

```text
Sonnet exclusive write turn
→ seal exact candidate hash
→ Codex independent read-only review
→ Sonnet exclusive repair turn if needed
→ seal again
→ single-flight deterministic tests
→ Fable milestone ruling
→ Codex independent certification
```

The complete required contract is in
`FACTORY_TURNSTILE_V1_WORK_ORDER_2026-07-23.md`. It includes:

- durable locked state and append-only events;
- exact Git candidate identity;
- exclusive process leases and orphan recovery;
- review-time mutation detection;
- single-flight test receipts with real child exit codes;
- exact passing-result reuse and no failed-result reuse;
- explicit full-suite authorisation;
- bounded deterministic context packs;
- measured 30/70 weighted model-work allocation;
- graceful process-group stop;
- adversarial tests.

## Fable's task

1. Independently assess the work order before implementation. Identify anything that could still
   allow concurrent writers, stale evidence, masked exits, context bloat, attribution gaming,
   deadlock, PID-reuse error or unsafe recovery.
2. Amend the contract only when the amendment closes a demonstrated gap. Record every amendment.
3. Keep all work confined to the clean turnstile worktree. Do not touch DFI-05, production, JAA,
   STOP or services.
4. Implement in small sequential packages. Only one writer process may exist at any time.
5. Prefer Sonnet for approximately 70% of substantive implementation/test-authoring packages.
   Fable may lead and adjudicate, but must not create overlapping writers or inflate the ratio with
   low-value work.
6. Use fresh bounded model sessions. A model invocation that produces no useful progress within a
   declared time bound must be stopped and replaced by a smaller package; never launch a second
   writer beside it.
7. Do not run the whole giga-user or orchestrator suite. Run only the focused Python 3.12/3.14
   turnstile tests, compilation checks and `git diff --check` specified by the work order.
8. Never pipe a test command into `tail` to decide success. Preserve the tested process's actual
   exit code.
9. Inspect the final diff and exact line count. No stubs, placeholders, silent waivers or tests
   that merely restate implementation.
10. Produce a durable candidate report binding paths, hashes, commands, exit codes, test counts,
    allocation and residual risks.

## Independence boundary

Fable/Claude must not self-certify the final harness. When the implementation and focused evidence
are ready:

- seal the exact candidate hash;
- stop all writer/test processes;
- leave the turnstile branch uncommitted unless the governing work order is amended with explicit
  authority;
- report **READY FOR INDEPENDENT CODEX REVIEW**, not certified;
- provide one compact handoff to Codex containing only the contract, diff/hash and evidence
  receipts.

Codex must then review the sealed snapshot without writing concurrently. If Codex makes a material
correction, it acquires the sole writer turn and Claude subsequently reviews that new sealed
snapshot.

## Terminal conditions

Stop and ask Artiom only if:

- the required contract cannot be implemented safely within the isolated harness;
- a missing authority decision would materially change the design;
- provider/tool access prevents meaningful progress;
- the candidate cannot pass focused evidence without weakening a mandatory property.

Do not resume the broader unattended continuation order. The only authorised objective is the
Factory Turnstile candidate and its handoff for independent review.
