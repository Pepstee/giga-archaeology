# Orchestrator-v3 Ox Supervisor Checkpoint — 2026-08-24

## Authority and operating boundary

- Persistent objective: finish Orchestrator-v3 to the highest genuinely achievable production standard, requirement by requirement, including deterministic execution, overseer integration, STOP/authority/recovery/evidence controls, and proven end-to-end software production.
- Codex is supervisor, scope owner, and independent verifier only.
- `openrouter/stealth/ox-alpha` with variant `max` is the required heavy implementation and reasoning engine.
- Live and Gigabyte runtime remain STOP-protected. No production activation, merge, push, or canonical-source mutation is authorised by this checkpoint.
- Situation Monitor may be developed only by or through Orchestrator-v3. Orchestrator must own decomposition, durable state, authority, recovery, tests, evidence, admission, and receipts. Direct standalone Ox or Codex editing is forbidden.

## Canonical source truth

- Canonical checkout: `/Users/admin/Documents/agentic-orchestrator/projects/orchestrator-v3`
- Branch: `efficiency/e2-shadow-cache`
- HEAD: `85bd10a8a02c413b15ccb939a66f162a5f7df5e8`
- Tree: `10a43ca7fb52f3ae6c12d111bd250c098ac99b1a`
- Origin: `https://github.com/Pepstee/orchestrator-v3.git`
- Remote branch of the same name is exactly at the local HEAD.
- `origin/main` is `bb88b40`; canonical HEAD is 35 commits ahead and 0 behind its merge base with `origin/main`.
- No upstream is configured. Do not pull blindly.
- Canonical checkout was clean and was not mutated.

## Isolated lane and provenance

- Candidate lane: `/Users/admin/Documents/giga-user/.worktrees/orchestrator-v3-supervisor`
- Branch: `codex/supervisor-lifecycle`
- Isolated baseline: `dde1a25b6ec5587e5b16c1b05ad2d624ca7e89c2`
- Complete-source restoration commit: `df2ce9764ba03d5f90dcb23df3647ba27d20dd29`
- Restoration commit author: `Artiom <gutu.artiom444@gmail.com>`
- Candidate is intentionally uncommitted and unintegrated.
- Tracked diff SHA-256: `54f293b063c18f56fc3a37d63fc8699218a104deacbb26fcaff49d1017f6016c`
- Untracked file hashes:
  - `control/supervisor.py`: `6e79d43a3301dfbcce249731928bc5db2f386c0a9fb29389b69ffdf6a25f07ce`
  - `tests/test_daemon_cycle_observer.py`: `cf5aa14c52d399a43c533a06a2e7438cdb3b25f3b533d175e9e8574b51af9ade`
  - `tests/test_supervisor.py`: `8ca6c85ecae1978a5bca9aca7212a90270e01d4345ea9720fb18e16026568da8`

Modified tracked files:

- `README.md`
- `control/daemon.py`
- `memory/knowledge.py`
- `memory/pulse.py`
- `memory/rehydrate.py`
- `tests/test_memory_pulse.py`
- `tests/test_rehydrate_corrupt_encoding.py`

Untracked candidate files:

- `control/supervisor.py`
- `tests/test_daemon_cycle_observer.py`
- `tests/test_supervisor.py`

## Candidate purpose

The candidate adds a provider-neutral supervisor lifecycle, paired daemon cycle-fence/observer hooks, bounded durable cycle receipts, restart recovery for pending cycles, deterministic pulse/diary projection, idempotent knowledge-index repair, and bounded context rehydration. It is a Codex-authored candidate created before the operator made Ox-only heavy implementation provenance binding. Ox must independently adopt, revise, or reject it before promotion.

## Independent review and verification already obtained

- Three adversarial reviewer passes were performed. The final reviewer reported no remaining P0/P1 finding after earlier STOP-race, crash-fence, receipt-bound, context-eviction, boot-gate, unknown-effect, stale-index, timestamp, and minimum-budget findings were addressed.
- Focused lifecycle/daemon/memory suite: 102 passed.
- Earlier architecture/overseer/STOP/memory/roadmap suite: 111 passed before the final small repairs.
- Ruff on changed files: passed.
- Import-linter: 94 files, 251 dependencies, L2 contract kept.
- `./acceptance`: passed replay demo.
- `python acceptance_authenticity_demo.py`: passed planted-violation and legitimate-sample checks.
- `git diff --check`: passed.
- Dry run reported STOP/isolation/boot/session/pending/rehydration state without mutation.

## Current real gate failure

Full-suite run failed at:

`tests/architecture/test_replay_corrupt_record_coverage.py::test_every_replay_style_entrypoint_has_type_corrupt_coverage`

The architecture gate reports:

`control/supervisor.py::_load_pending` lacks explicit type-corrupt test coverage.

Evidence before interruption: 297 passed, 1 failed. The other four tests in that architecture file pass when this exact gate is deselected.

Read-only direct falsification confirms `_load_pending` already fails closed for a non-dict record, boolean sequence, string timestamp, list rehydration payload, and list report. The required repair is therefore an Ox-authored production-shaped regression test, not a weakening or renaming of the architecture gate.

Acceptance criteria for the repair:

1. Exercise `_load_pending` directly or through its public recovery path with a wrong-typed durable pending receipt.
2. Assert a specific fail-closed `SupervisorRefusal` outcome.
3. Use the existing test vocabulary so the static architecture gate recognises real coverage.
4. Do not rename the loader, weaken discovery, add a fake token-only test, change STOP, or broaden scope.
5. Run the exact architecture gate, supervisor tests, focused suite, then independent verification.

## Confirmed nested-evidence replay defects

Unrestricted-host adversarial replay found a second, material defect in the same bounded slice.
`_load_pending` validates a completed pending receipt's `report` only as a dictionary. A temporary
receipt containing a string `cycle`, list `claim_count`, mapping `ingested_total`, negative
`project_actions_total`, and string `recovered` was accepted by `_recover_pending`, projected into
the pulse/diary evidence, and then deleted with the pending fence.

This is a real evidence-integrity failure. Ox must make completed reports reconstruct through one
strict production cycle-report schema (or an equivalently complete validator), reject unknown or
wrong-typed fields deterministically, preserve the pending fence on refusal, and add direct corrupt
and valid round-trip tests. Do not create a second receipt schema or weaken recovery.

The same falsification against `rehydration` also failed: string booleans, a negative byte count,
list-valued SHA-256 and wrong-typed source counters were accepted, projected into the pulse, and the
pending fence was deleted. Ox must validate the complete persisted receipt, including the canonical
rehydration-report shape, rather than special-casing only one nested dictionary.

## Full-suite environment findings

A remainder run with only the known architecture gate deselected reached 1,251 passes before being stopped at 35%. The additional failures were environment-caused:

- 100 Edge HTTP setup errors and four related Edge failures: this managed task sandbox refuses localhost socket binding with `PermissionError: [Errno 1] Operation not permitted`.
- Nine daemon E2E failures: their subprocesses never reached dispatch because the mandatory boot self-test correctly refused after real macOS isolation-certification tests failed inside the managed sandbox. A direct harness probe showed `BootRefusal` after 232 boot tests passed and the host-isolation checks failed.

These results are not a full-suite pass and must not be represented as one. The socket and host-isolation suites require a suitable independent host environment.

After the task received unrestricted host access, the complete remainder suite (with only the known
corrupt-entrypoint gate deselected) ran to completion: 3,640 passed, 5 skipped, and 2 failed. Both
failures were independently classified:

- The empty-inbox unattended daemon drill timed out at 90 seconds under full-suite load, then passed
  alone in 70.30 seconds. Treat it as a timing-sensitive full-suite flake until a clean complete
  rerun proves otherwise; do not weaken its semantics.
- `test_real_market_aligner_programme_is_read_as_seventeen_ordered_slices` failed because the outer
  Orchestrator repository ignores its nested JAA repository, so an isolated Git clone omitted the
  required `IMPLEMENTATION_SLICES.yaml`. The exact canonical file was restored into the ignored
  test-fixture location with SHA-256
  `42b6f2b63acc6c172a86db624966cd55c43f84632578917d641a3fb6c21dd0fe`; the test then passed.

Unrestricted targeted verification produced 85 passes and the one expected architecture-gate
failure. No complete green suite may be claimed until Ox repairs both replay defects and a fresh
complete run passes without exclusion.

## Ox process/session evidence

OpenCode model/variant: `openrouter/stealth/ox-alpha`, `max`.

- Earlier dedicated session: `ses_fd02fb5b8ffeTOxwVTj0PrGlgs`; failed before work because OpenRouter was unreachable.
- Connectivity probe session: `ses_fcff4e81fffefYI5Js5rqwypQe`; zero model tokens, zero edits, provider-side server error.
- Bounded repair session: `ses_fcff3c08cffeuE30dlgVgv0j79`; zero model tokens, zero edits, provider-side server error.
- OpenCode log confirms `https://models.opencode.ai/api.json` is unreachable from this task environment.
- Fresh unrestricted Ox lane:
  `/Users/admin/Documents/ox-alpha-giga-workspace/projects/orchestrator-v3-supervisor-lifecycle-20260824`.
  It has an independent `.git` directory and exactly reproduced all recorded candidate hashes.
- Fresh Ox session: `ses_fcfc35810ffeAKcEqBatAufUU9`; zero implementation tokens and zero edits.
  OpenRouter refused every retry with `free-models-per-day-stealth` rate-limit exhaustion.
- The pre-existing Ox checkout at
  `/Users/admin/Documents/ox-alpha-giga-workspace/projects/orchestrator-v3` has unrelated dirty
  `infra/llm.py` work and was deliberately left untouched.

Codex did not substitute itself after the binding directive. The candidate has not changed since the recorded hashes.

## Next safe sequence

1. Restore network/provider reachability for OpenCode without changing the isolated candidate lane.
2. Resume Ox Alpha max session `ses_fcfc35810ffeAKcEqBatAufUU9` in the exact lane after its daily
   provider quota resets. Give it the corrupt-entrypoint coverage repair, strict nested-report
   replay validation, and this checkpoint as one bounded lifecycle slice.
3. Require Ox to inspect and explicitly adopt, revise, or reject the full pre-existing candidate; do not treat it as Ox-authored merely because Ox adds one test.
4. Independently review the resulting diff and rerun targeted gates.
5. Run the full suite in an environment that permits localhost sockets and real host-isolation certification.
6. Only after independent review and complete verification, commit verified isolated work as `Artiom <gutu.artiom444@gmail.com>` and prepare promotion evidence.
7. Do not integrate or activate production without the repository's normal review path. Preserve STOP.

## Next admitted slice after receipt repair

Repository search confirms that the new supervisor is tested only in-process. Existing daemon
drills exercise real subprocess SIGKILL/restart, but no test launches `control.supervisor` as the
actual OS process. Before richer model-driven Overseer policy, add one bounded supervisor lifecycle
E2E slice that reuses the daemon harness/runtime rather than inventing another execution system.

Required evidence:

1. Launch the real supervisor CLI/process with deterministic test isolation and stub agents.
2. Kill it after a durable start fence and real claim, then restart independently.
3. Prove the same canonical session survives, the orphan is reclaimed and settled once, the
   pending fence clears only after one matching pulse and diary projection, and no task or evidence
   is duplicated.
4. Prove an armed STOP refuses before new supervisor state or dispatch.
5. Prove a second process cannot become a concurrent supervisor writer.
6. Keep every wait bounded by observed on-disk state; no fixed sleeps as correctness evidence.
7. Run the focused process drills and complete suite before this slice may be committed.

Only after that process-level recovery proof should the programme admit richer Overseer action
policy or a paid-provider end-to-end software-production canary.

## Final provider-blocked checkpoint

At `2026-08-24 05:44:39 KST`, the third consecutive goal turn's final evidence-backed resume of
Ox session `ses_fcfc35810ffeAKcEqBatAufUU9` again failed before its first implementation token with
`AI_APICallError: Rate limit exceeded: free-models-per-day-stealth.` The OpenCode log records the
last retry beginning at `2026-08-23T20:43:12Z` and repeated provider refusals through at least
`2026-08-23T20:44:26Z`.

The isolated lane remained unchanged:

- tracked binary-diff SHA-256:
  `54f293b063c18f56fc3a37d63fc8699218a104deacbb26fcaff49d1017f6016c`
- branch: `codex/supervisor-lifecycle`
- HEAD: `df2ce9764ba03d5f90dcb23df3647ba27d20dd29`
- no Ox worker process remained; PID `20237` was the pre-existing unrelated OpenCode TUI and was
  left untouched
- canonical Orchestrator-v3 was not mutated, integrated, activated, or represented as certified
- STOP remained preserved

Because the operator's binding provenance rule requires Ox Alpha to be the heavy implementation
engine and forbids Codex from replacing it for convenience, no compliant implementation progress
is possible until the external Ox quota resets or equivalent Ox provider capacity becomes
available. The persistent goal is therefore blocked, not complete. Resume from the exact session,
lane, candidate hash, defect list, and next-safe sequence above.

## 28 August continuation — persistent Overseer candidate restored

Ox Alpha did not recover. Three fresh probes ended with zero implementation tokens, and the final
diagnostic established the terminal cause: OpenCode now returns
`ProviderModelNotFoundError: Model not found: openrouter/stealth/ox-alpha` (reference
`err_9371b147`). This is provider removal, not a convenience choice or a temporary coding failure.
Codex therefore continued as the disclosed fallback after preserving the Ox evidence.

The previous lifecycle candidate was repaired and preserved as `d5010d2`, then cherry-picked onto
the newest known v3 candidate lineage (`5d5147e`) in the isolated worktree:

`/Users/admin/Documents/ox-alpha-giga-workspace/worktrees/orchestrator-overseer-v2-restore-20260828`

The restored candidate now includes:

- an outer non-blocking singleton that relaunches a crashed supervisor and keeps it down under STOP;
- one durable supervisor session and crash-recoverable per-cycle evidence fences;
- strict nested rehydration and daemon-report replay validation;
- two-hour bounded observation pulses with the v2 quiet-ledger gate;
- durable beliefs and diary projection, health alarms and twelve-hour status heartbeat;
- sender-locked, offset-durable two-way Telegram through private `state/telegram.json`;
- a read-only Overseer model role with zero tool calls and a real checked-in model-routing receipt;
- explicit operator-message plan admission through deterministic control code; ordinary model
  observations cannot mutate projects, and abandon/reprioritise remain advisory.

Verification evidence:

- focused/architecture gate: 118 passed;
- full repository suite: 3,709 passed, 5 skipped, 1 deselected in 641.74 seconds;
- the sole deselection is the pre-existing scoped-assurance test whose JAA
  `IMPLEMENTATION_SLICES.yaml` fixture is absent from this isolated Orchestrator checkout;
- real Codex Overseer canary: valid structured result, zero tool calls, 13,935 observed tokens;
- real outer-process drill: two consecutive supervisor refusals were relaunched as configured;
- real cross-process singleton drill: second owner refused with exit 3;
- refreshed graph: 6,388 nodes / 21,355 edges;
- graph SHA-256: `ed55912b1cfdf9c5f33d78d56a28a3aaa27abd8f92dddee2fb66fa4f729cd077`;
- graph manifest SHA-256: `c1fb16a18146c087ca351164a415f72934d318b19cb7a1392b9d401f8d502f01`.

Milestone commit `244f7439114b0d79bbde7d74eaf324b6aee19829` was authored as
`Artiom Gutu <gutu.artiom444@gmail.com>` and pushed to
`origin/codex/overseer-v2-restore-20260828`.

The candidate is implemented and verified but deliberately not live. Production/Gigabyte STOP
was not changed, the protected production lineage was not integrated, and no Telegram credential
was copied into Git. Activation still requires the normal independent integration review, a fresh
isolation receipt because the shipped manifest set changed, private transfer of the dedicated v2
Overseer Telegram configuration, and then an explicit controlled launch on the intended runtime.
