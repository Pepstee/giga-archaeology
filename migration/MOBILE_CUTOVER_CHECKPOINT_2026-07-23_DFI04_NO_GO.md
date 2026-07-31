# MOBILE CUTOVER CHECKPOINT — DFI-04 WRITE-AHEAD NO-GO

**Checkpoint ID:** `GIGA-MOBILE-CUTOVER-2026-07-23-DFI04-NO-GO`

**Purpose:** freeze the current Mac-side work exactly before making the Mac mobile and continue
orchestrator-v3 completion only on the Gigabyte software-factory host.

## Authority and machine layout

- Gigabyte WSL factory root: `/home/gutua/software-factory`
- Gigabyte production orchestrator-v3:
  `/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3`
- Gigabyte isolated DFI-04 worktree:
  `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-04`
- Gigabyte GIGA control plane: `/home/gutua/software-factory/giga-user`
- Mac DFI-04 staging source frozen for this cutover:
  `/tmp/orchestrator-v3-dfi02.Jh3sKl/repo`

The Gigabyte is the sole writer for orchestrator-v3, JAA and future software-factory projects
after this checkpoint. The Mac remains authoritative for the digital twin, Jarvis/personal
memory, Market Aligner and personal exports/corpora.

## Frozen source identities

### Gigabyte production

- Branch: `efficiency/e2-shadow-cache`
- Commit: `35efb19b07867bb58e1288479513078cf9ab65e4`
- STOP: armed
- Activation: prohibited at this checkpoint

### Gigabyte DFI-04 baseline

- Branch: `di/dfi-04-task-adapter`
- Commit: `274c6d0d68209084aa8ee3bf3265672f67c0bb02`
- Baseline tree:
  `3ce0646f0254b45726860345e470c037a0e869fa`

### Mac DFI-04 staging baseline

- Branch: `local/dfi-04-task-adapter`
- Commit: `e879ff20e241c1b2c6bc5b7b75428194be68159d`
- Baseline tree:
  `3ce0646f0254b45726860345e470c037a0e869fa`

The Mac and Gigabyte DFI-04 commits differ only because each host has its own worktree commit;
their baseline Git trees are identical. Transfer the dirty candidate by file content and verify
hashes against this common tree. Do not merge the Mac commit object into production.

## Exact interrupted DFI-04 candidate

Modified:

```text
control/daemon.py
control/deterministic_scheduling.py
control/workflow_adapter.py
dispatch/repository.py
infra/schema_registry.py
memory/knowledge.py
tests/test_canonical_schema_registry.py
tests/test_deterministic_scheduling.py
tests/test_workflow_adapter.py
```

Untracked:

```text
control/scheduler_profile.py
tests/test_deterministic_resettlement.py
tests/test_existing_test_coverage.py
tests/test_scheduler_decisions_and_boot_matrix.py
tests/test_scheduler_profile_adoption.py
```

Production-line budget at freeze:

- tracked additions: 457
- tracked deletions: 31
- untracked `control/scheduler_profile.py`: 70 lines
- net added production lines: `457 - 31 + 70 = 496`
- ratified ceiling: 500

Tests observed before freeze:

- focused/affected Sonnet run: 258 passed
- earlier broader affected run: 333 passed, 4 skipped
- earlier full Mac run: 3,800 passed, 6 skipped, 1 environmental failure because the
  corpus-excluded Mac mirror lacked
  `projects/job-application-automation/IMPLEMENTATION_SLICES.yaml`
- Ruff and `git diff --check`: passed before the final interrupted correction

These are historical observations, not Gigabyte certification evidence.

## Binding technical status: NO-GO

Fable's bounded ruling is:
`reports/FABLE_DFI04_BOUNDED_MILESTONE_RULING_2026-07-23.md`.

Codex independent review is:
`reports/CODEX_DFI04_INDEPENDENT_REVIEW_2026-07-23.md`.

The candidate is not certifiable because its most important write-ahead invariant is still
missing:

1. compiler-active currently calls `admit_task_batch` before persisting the durable
   `scheduler_decision`;
2. therefore a crash can create admitted work without the decision being the commit point;
3. committed-but-incomplete decisions are not discovered and re-driven after restart;
4. the required crash/restart evidence does not exist;
5. matching adoption plus matching bundle, mismatched adoption plus bundle, and one real
   `build_factory_epoch` bundle integration test remain incomplete;
6. the static existing-test verifier still needs exact `test_` recognition and fail-closed
   handling for matched Python files that cannot be read or parsed.

The final Sonnet correction session was stopped by the operator before it changed the frozen
numstat. Do not claim that it repaired these blockers.

## Exact resume order on Gigabyte

1. Keep production STOP armed and confirm no daemon/service is active.
2. Verify that this exact dirty candidate has been restored in the isolated DFI-04 worktree.
3. Read, in order:
   - `giga-user/00_MASTER.md`
   - `giga-user/CHARTER.md`
   - this checkpoint
   - `giga-user/reports/FABLE_DFI04_BOUNDED_MILESTONE_RULING_2026-07-23.md`
   - `giga-user/reports/CODEX_DFI04_INDEPENDENT_REVIEW_2026-07-23.md`
4. Use Sonnet as the bounded coder workforce to implement the missing write-ahead commit,
   restart redrive, exact evidence matrix and verifier repairs within the 500-net-line ceiling.
5. Codex independently reviews semantics, diff scope, STOP behavior, line budget, dual-Python
   verifier behavior and tests.
6. Ask Fable for one narrow, no-tools, no-subagent GO/NO-GO milestone ruling.
7. Run the authoritative focused, affected and full suites on Gigabyte, including the real JAA
   programme file that was absent from the Mac staging mirror.
8. Certify and commit DFI-04 in the isolated worktree only after every gate passes.
9. Re-slice and complete the remaining deterministic-efficiency programme before resuming JAA.
10. Resume JAA only after the active deterministic profile proves measured savings without
    weakened quality, safety, observability or auditability.

## Provider state at cutover

Gigabyte status checks report:

- Codex: logged in using ChatGPT and usable
- GitHub CLI: logged in as `Pepstee` and usable
- Claude: `claude auth status` reports Claude Max, but the first real Sonnet invocation failed
  before making changes with `401 Invalid authentication credentials`

The operator must refresh Claude inside Gigabyte WSL with:

```bash
claude auth login --claudeai
```

Never copy raw credentials, auth stores or tokens from the Mac or chat history into the factory
tree.

## Explicit exclusions

Personal exports and canonical corpus payloads remain on the Mac:

- `giga-user/corpus/`
- `giga-user/package.zip`
- `giga-user/instagram-artiom.png-2026-07-16-58GCGdnZ.zip`
- `giga-user/1916b63abd801fbb5abf9b44f98d87a68ccd5db992b2a4d30567dd8a4ed29a85-2026-07-19-08-37-41-df72519dd898472489071b0441745ac3.zip`

Authentication/session stores, `~/.jarvis`, browser sessions and personal chat databases are also
excluded. The migration includes source, Git history, dirty worktrees, laws, gates, reports,
skills, knowledge graphs, assurance evidence, runtime evidence, scripts and continuation
instructions.
