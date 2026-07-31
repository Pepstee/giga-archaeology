# DFI-05 Sonnet settlement order

You are the sole DFI-05 writer.

Read:

- deterministic context pack:
  `/home/gutua/software-factory/.control/dfi-05-scope-admission/contexts/context_9f5aadf69dcfcf38b2940494aed36e2043e16f0fbb694f0466156f3ab0491955.json`
- worktree work order:
  `docs/efficiency/DFI_05_WORK_ORDER_2026-07-23.md`
- stop checkpoint:
  `/home/gutua/software-factory/giga-user/reports/DFI05_INTERMODEL_CONCURRENCY_STOP_CHECKPOINT_2026-07-23.md`

The preserved patch hash is
`e7f7d438d33133c7deebd7894f70cba33df340bac3780603c2501a32a007b125`.
Treat every earlier concurrent test claim as invalid.

Independently inspect the complete dirty diff against base
`dcf509753845552a906a5a1a04fcdad754cb6471`. Keep only coherent work and
repair every concrete contract or regression defect you find.

Constraints:

- preserve default-off semantics, existing JSONL authorities, STOP/JAA
  isolation, and all Fable conditions;
- net counted production additions must be at most 350;
- do not hide logic outside counted production or weaken scope;
- run only focused/affected suites named by the changed tests with direct
  pytest invocations;
- run Ruff and `git diff --check`;
- do not run the complete suite and do not use pipelines;
- recalculate the exact production budget;
- do not commit.

Exit zero only when the candidate is internally sound and focused evidence
passes. Otherwise fail explicitly.
