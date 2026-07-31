# JAA and DFI parallel execution checkpoint

Date: 25 July 2026  
Execution host: Gigabyte, WSL Ubuntu

## Decision

JAA completion and orchestrator-v3 deterministic-infrastructure work are separate delivery
problems. JAA depended on DFI only while the plan required JAA to be built by the efficient
orchestrator. Under native Codex supervision, that dependency no longer exists.

They may therefore progress concurrently, subject to shared-resource and authority controls.

## Lane 0 — blind portfolio experiment

The portfolio experiment remains active and must not be displaced by either build lane.

- Persistent unit: `blind-opus5-portfolio-20260725.service`
- Control root:
  `/home/gutua/software-factory/.control/blind-opus-portfolio-20260725`
- V2 immutable commit: `32efb0797905078a6917d748ce93efd46f7527be`
- V3 immutable commit: `35efb19b07867bb58e1288479513078cf9ab65e4`
- Current clean attempt IDs: `v2-opus5-r3`, then `v3-opus5-r3`
- The arms run sequentially and fail closed. V3 cannot start until the V2 result validates as
  a non-error `claude-opus-5` report against an unchanged read-only snapshot.
- Earlier Opus 5 attempts remain preserved as authentication failures. Opus 4.8 pilot reports
  remain labelled pilots and cannot substitute for the requested Opus 5 reports.

## Lane 1 — JAA through native Codex supervision

Canonical source:

`/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3/projects/job-application-automation`

Current clean source commit:

`3679d98` (`evidence: bind complete JAA-01 replay repair`)

Isolated implementation worktree:

`/home/gutua/software-factory/.worktrees/jaa-native-completion`

Branch:

`codex/jaa-native-completion-20260725`

The completed read-only audit found:

| Slice | Honest current state |
|---|---|
| JAA-00 | Real baseline code and historical adoption evidence; preserve as baseline rather than current certification. |
| JAA-01 | Real code, named tests and a receipt whose source-content hash matches the current tree. |
| JAA-02–03 | Real code and receipts, but the receipts are stale against current source. |
| JAA-04 | Real implementation and all named tests; only Increment A is evidenced, against an older revision. Increment B's authentic 30-dossier corpus and current full receipt are unfinished. |
| JAA-05–16 | Not implemented. Their declared owned modules and acceptance/negative-control tests are absent from Git, and no receipts exist. |

`ASSURANCE_MANIFEST.json` incorrectly declares JAA-05 through JAA-16 `complete`. Those
declarations are not progress evidence and must be corrected before any status report can use
the manifest.

The smallest safe JAA action is to finish JAA-04 Increment B only: complete and validate the
in-flight 30-dossier corpus, bind it to the current source revision, run its named acceptance
and negative-control suites, and issue or withhold a current receipt. JAA-05 may not start
before that gate passes.

Two additional Increment B interface defects were confirmed before any network run:

1. The checked `jaa04_admitted_queue.json` is
   `jaa04.admitted-queue.v1` and has no `raw_store`, while
   `scripts/capture_jaa_04.py` accepts only
   `jaa04.official-admitted-queue.v2` with bound raw-response provenance.
   The documented command therefore cannot run from the clean current checkout.
2. `.gitignore` and `docs/JAA04_AUTHORITY_ACQUISITION.md` say in-flight SQLite and raw
   response bytes are external and untracked, but commit `b0bd9e3` added the whole
   `runtime_evidence/jaa04/inflight/` tree to Git. The tracked set includes the queue
   database, WAL/SHM files and raw response captures.

No acquisition should run into the tracked directory. The repair package must reconcile the
v1/v2 queue contract, preserve authentic raw provenance, move resumable runtime state to an
external workspace, and add a negative test that a clean checkout's documented command is
actually consumable.

JAA will use native Codex as the persistent coordinator and final cross-provider reviewer.
Claude models are workers selected by task risk; they do not own durable programme state or
certification.

## Lane 2 — orchestrator DFI

The DFI lane remains in its existing dedicated branches, worktrees and control directories.
It must not use the JAA worktree or modify the nested canonical JAA repository.

The read-only reconstruction established:

| Stage | Commit | Honest state |
|---|---|---|
| DFI-00–03 | `83003f6` → `8eb97ce` | Committed ancestors in the certified candidate lineage. |
| DFI-04 | `dcf5097` | Certified isolated candidate; not merged or activated. |
| DFI-05 | `163844c` | Certified. |
| DFI-06 | `f3822b0` | Certified inactive; observational only. |
| DFI-07R | `d1d0ba7` | Certified CAS/artifact substrate; inactive. |
| DFI-08R7 | uncommitted from `d1d0ba7` | Failed and uncertified four-file Slice A candidate. |

Current DFI authority:

`/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-08`

Its only dirty paths are `pyproject.toml`, `infra/execution_ledger.py`,
`tests/test_execution_ledger.py`, and
`tests/architecture/test_execution_ledger_architecture.py`. The preserved candidate produced
22 passes and 14 failures; its review found 15 issues. The attempted repair made no byte
changes because Claude authentication failed.

The controlling checkpoint is:

`/home/gutua/software-factory/giga-user/reports/DFI08R7_CLAUDE_AUTH_BLOCKED_CHECKPOINT_2026-07-25.md`

with SHA-256
`5893b1a8818528f47d960edfa05de89439bdfd14f6e5a4c9da7053d55124bc0b`.

The next admitted DFI action is to rerun the preserved authentication-failure gate through
`fable_gate_broker.py` in a fresh append-only directory, then obey the resulting structured
Fable decision. No fresh implementation or blind Sonnet retry is authorised before that.

## Shared-resource controls

### Claude authentication

Every future Claude worker call on Gigabyte must acquire:

`/home/gutua/software-factory/.control/claude-global.lock`

The deployed launcher is:

`/home/gutua/software-factory/giga-user/deploy/gutua/run_claude_serialized.sh`

This serialises Claude credential refresh and execution across JAA, DFI and review work. Codex
analysis, deterministic host tests and disjoint file operations may continue concurrently.

### Write authority

- One mutable actor per worktree.
- No concurrent writer and reviewer on the same candidate.
- JAA and DFI use disjoint worktrees, branches, checkpoints and service units.
- Canonical/production checkouts remain untouched until a candidate passes its own gates.
- Deterministic tests may run concurrently only when they do not share mutable databases,
  caches, workspaces or evidence destinations.

### Model roles

- Codex frontier model: coordinator, integration owner, evidence ledger, final review and
  acceptance decision.
- Claude Sonnet: default implementation worker.
- Claude Haiku: bounded triage and mechanical read-heavy tasks; never final authority.
- Claude Opus: difficult architecture/debugging and independent milestone review.
- Claude Fable: rare highest-risk milestone ruling or rescue assessment; not routine coding.

“All models” does not mean every model touches every task. Models are invoked where their
capability changes the expected result; unnecessary independent re-analysis is token waste.

## Completion rules

JAA and DFI certify independently.

JAA is complete only when the source tree, implementation manifest, deterministic tests,
negative controls, runtime receipts and end-to-end product evidence agree at one clean commit.

DFI is complete only when each admitted stage is committed and certified, the efficient
profile is activated, and controlled work demonstrates measured token/time improvement without
quality or evidence regression.

Neither lane may claim progress from declarations, prose, generated test names or unexecuted
manifests.
