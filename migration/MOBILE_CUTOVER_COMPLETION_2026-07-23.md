# Gigabyte mobile cutover — completion receipt — 2026-07-23

**Checkpoint ID:** `GIGA-MOBILE-CUTOVER-2026-07-23-DFI04-NO-GO`

**Outcome:** PASS for migration. NO-GO remains binding for DFI-04 certification and production
activation.

## What is now authoritative on Gigabyte

- Software-factory root: `/home/gutua/software-factory`
- Production orchestrator-v3:
  `/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3`
- Isolated DFI-04 worktree:
  `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-04`
- GIGA laws, gates, reports, skills and continuation instructions:
  `/home/gutua/software-factory/giga-user`
- Cutover evidence and recoverable backups:
  `/home/gutua/software-factory/.mobile-cutover-20260723`

The Gigabyte is the sole writer for orchestrator-v3, JAA and future factory-built software.
The Mac remains authoritative for the digital twin, Jarvis/personal memory, Market Aligner and
personal exports/corpora.

## Preserved complete baseline

The four full 22 July archives were re-hashed on Gigabyte before the incremental cutover:

```text
a69336ada7915d68d6aff3f3dd9f47b8399fcd36a8aed8851f5d1e72661ae3a9  agentic-orchestrator-20260722.tar.zst
3e08f0f70783123eac8a513e45d00fee2ccca8b92a7cfdc59387b54154aeb893  giga-user-no-exports-20260722.tar.zst
122bb1697d4057666f5e81627e937507434c75273990dd3c97cb59a88e84153a  factory-user-control-layer-20260722.tar.zst
f7ed88d3cc83294d85e1ced8da481140d24677b695bdaa8d5adce999989dcc61  factory-graphify-repos-20260722.tar.zst
```

They remain under `/home/gutua/software-factory/.archives-20260722`.

## Current-state inventory

New source manifests were created before transfer:

- Mac `agentic-orchestrator`: 210,637 entries, 164,137 files,
  16,415,182,959 regular-file bytes,
  digest `446a71ba07dfcd347f86429091704805176b0a795f047f500c6a4d9a9ddd155e`
- Mac `giga-user` excluding personal exports/corpus: 40,816 entries, 36,645 files,
  3,079,349,729 regular-file bytes,
  digest `91428299be7ef7fb537c6a4054de285d770e1595152cd30bce10ed74a9a83416`

The 22 July full archives already held the complete baseline. The 23 July incremental transfer
therefore moved only new state:

- 27 changed/new GIGA files, including all current reports, architecture documents, memory
  doctrine, knowledge-graph query output and the exact checkpoint;
- 14 exact DFI-04 candidate files;
- current Codex, agent and Claude skill trees plus portable standing rules;
- the complete Mac orchestrator-v3 Git ref bundle, including the local DFI branches;
- source manifests and the exact delta path list.

Transfer archive hashes:

```text
54c3133d07da7897e7a6e92d781286c3c4b60fb7246cf6c9bc5b47f759ffcca8  giga-user-delta-20260723.tar.zst
372c3fbaf6da351ec14f537c7e24840c78f48e0c949e85aea59387a09075305c  dfi04-candidate-20260723.tar.zst
46732a60ce6657a68a802b522eb6dcd89aa73c3cce514f7b00afd01ac4094697  portable-control-layer-20260723.tar.zst
25c767154bfa36a60802124409167cbbe070af27afe15fe67926750ee46525e3  checkpoint-assets-small-20260723.tar.zst
```

Transfer-generated AppleDouble `._*` metadata was pruned only from isolated staging trees before
activation. No source or canonical factory file was deleted.

## Verification gates passed

1. Production orchestrator-v3 remained:
   - branch `efficiency/e2-shadow-cache`
   - commit `35efb19b07867bb58e1288479513078cf9ab65e4`
2. Production `STOP` remained armed.
3. `orchestrator-v3.service` remained inactive.
4. The isolated DFI-04 worktree remained:
   - branch `di/dfi-04-task-adapter`
   - commit `274c6d0d68209084aa8ee3bf3265672f67c0bb02`
   - baseline tree `3ce0646f0254b45726860345e470c037a0e869fa`
5. All 14 DFI-04 source/test files matched the Mac SHA-256 values exactly.
6. Checksum-mode `rsync` dry runs reported no drift for:
   - DFI-04 staging versus the isolated worktree;
   - the GIGA delta versus the active Gigabyte GIGA tree;
   - Codex skills;
   - agent skills;
   - Claude skills.
7. The DFI-04 production-line calculation remained 496 net added lines:
   `457 additions - 31 deletions + 70 untracked production lines`.
8. The orchestrator-v3 Git bundle verified as a complete SHA-1 history.
9. The Gigabyte skill-router audit passed after activation:
   48 discovered skills; 21 Codex skill files, 3 agent skill files and 3 Claude skill files.
10. Codex and GitHub CLI passed live authentication checks after migration. Claude's status
    command reported a Max login, but the first real Sonnet request exposed a stale credential
    and failed safely with HTTP 401 before changing files.

## Recoverability

Before overlay:

- the entire remote DFI-04 worktree was copied to
  `.mobile-cutover-20260723/backups/orchestrator-v3-dfi-04-before-overlay`;
- every pre-existing GIGA destination file in the 27-file delta was copied under
  `.mobile-cutover-20260723/backups/giga-user-pre-overlay`;
- the active portable control layer was copied under
  `.mobile-cutover-20260723/backups/active-control-layer`.

No Mac source was removed. Mac cleanup remains a separate destructive operation and was not
authorised by this cutover.

## Authentication

One operator action is required:

```bash
claude auth login --claudeai
```

Run it inside Gigabyte WSL. Codex remains logged in using ChatGPT and GitHub CLI remains logged in
as `Pepstee`.

The bounded Sonnet resume was attempted once after migration. It exited immediately with
`401 Invalid authentication credentials`; the production commit, STOP state, isolated DFI-04
numstat and all candidate hashes remained unchanged. Its log is:

`/home/gutua/software-factory/.mobile-cutover-20260723/logs/dfi04-sonnet-resume.log`

Raw credentials, tokens, browser sessions, auth stores, personal chat databases and
`~/.jarvis` were not transferred.

## Deliberate exclusions

- `giga-user/corpus/`
- `giga-user/package.zip`
- `giga-user/instagram-artiom.png-2026-07-16-58GCGdnZ.zip`
- `giga-user/1916b63abd801fbb5abf9b44f98d87a68ccd5db992b2a4d30567dd8a4ed29a85-2026-07-19-08-37-41-df72519dd898472489071b0441745ac3.zip`

These remain on the Mac by design.

## Exact continuation boundary

DFI-04 is migrated but not certified. Its missing write-ahead decision/restart-redrive contract
is recorded in:

`migration/MOBILE_CUTOVER_CHECKPOINT_2026-07-23_DFI04_NO_GO.md`

Resume in this order:

1. Sonnet implements the missing write-ahead commit, restart redrive, exact daemon evidence and
   verifier repairs in the isolated DFI-04 worktree, remaining within 500 net production lines.
2. Codex independently reviews semantics, scope, line budget, STOP behavior and dual-Python tests.
3. Fable gives one bounded GO/NO-GO milestone ruling.
4. Gigabyte runs the authoritative focused, affected and full certification suites.
5. Certify and commit DFI-04 only after every gate passes.
6. Re-slice and complete the remaining deterministic-efficiency programme.
7. Measure real token/time savings without weakening quality or auditability.
8. Resume JAA only after the deterministic profile is certified and active.

JAA was not touched or resumed during migration.
