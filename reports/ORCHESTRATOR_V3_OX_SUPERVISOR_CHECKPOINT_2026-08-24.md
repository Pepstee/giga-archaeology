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

## 28 August final independent closure — supersedes the candidate verdict above

Independent Codex 5.6 Sol review initially rejected commit `244f743` for a real outer-lock
self-deadlock, insufficient Telegram sender/authority binding, corrupt-offset data loss, conflicting
journal acceptance, non-finite quiet-gate timestamps and unenforced secret-file privacy. Those
findings were repaired without activating production. Successive review rounds then found and
closed three upgrade/identity edge cases: environment-dependent singleton identity, incomplete
multi-page first-contact draining, legacy journal timestamp recovery, and an unproven legacy
Telegram cursor identity. The final legacy cursor path now enters a durable
`migration_required` state and cannot use its offset until continuity is explicitly confirmed in
the owner-only private configuration.

Final behavior deliberately preserves the v3 authority boundary: the Overseer provides persistent
observation, durable mind, health reporting and sender-bound private Telegram dialogue, but model
directives are advisory. Consequential work still enters only through the signed, scoped and
expiring work-order admission boundary; free-text model output cannot create executable plans.

Final evidence:

- branch: `codex/overseer-v2-restore-20260828`;
- final HEAD: `f6e8abc` (`fix: require legacy cursor continuity proof`);
- all milestone commits authored as `Artiom Gutu <gutu.artiom444@gmail.com>` and pushed to origin;
- final independent verdict: `PASS` with no P0/P1/P2;
- complete repository suite: 3,722 passed, 5 expected skips, 1 deliberate deselection;
- deliberate deselection remains the pre-existing scoped-assurance test whose nested JAA
  `IMPLEMENTATION_SLICES.yaml` fixture is absent from this isolated checkout;
- lint and architecture gates passed;
- final macOS isolation receipt:
  `9b7dba2af8e78105640f2a765dacb776fd669b1284630cdc15e6d164ae1f6263`;
- refreshed graph: 6,445 nodes / 21,525 edges;
- graph SHA-256: `2ff376015c1ea9d3b72dc9cd64b3afb3c287b23216d1da9da7a79b683b675767`;
- graph manifest SHA-256:
  `a11de2eecf3e4f9c579d4f287b77349819f1ddf1d825aa38ef06e9a65abe7e41`.

The certified candidate is still not the live production runtime. Canonical production and
Gigabyte STOP remain untouched, and the dedicated v2 Overseer Telegram secret remains outside Git.
Activation requires promoting this reviewed branch through the intended integration path, issuing
a fresh isolation receipt on that exact target checkout, copying the private Telegram config with
mode `0600`, and deliberately starting the outer service without silently removing STOP.

### Canonical promotion completed, runtime still deliberately stopped

After the independent `PASS`, canonical Mac v3 at
`/Users/admin/Documents/agentic-orchestrator/projects/orchestrator-v3` was verified clean and an
ancestor of the certified lineage, then fast-forwarded only from `85bd10a` to `f6e8abc`. The
dedicated v2 Overseer Telegram configuration was copied into canonical private runtime state as
`state/telegram.json` with mode `0600`; no secret entered Git. Canonical target isolation then
certified with receipt
`cfa150d5669e8550736447eb94f1fb33656a9b33270d6ac0ab22049624d6934a`.

The existing canonical `STOP` remains armed and no Overseer/factory process was launched. This
preserves the operator's earlier explicit idle/limit instruction. Source restoration, private bot
provisioning and target certification are complete; live activation remains one separate deliberate
operator decision because starting the v2-equivalent outer lifecycle also starts the v3 supervisor
and factory rather than a harmless notification-only process.

## 28 August live restoration — persistent Overseer operational

The operator explicitly requested restoration. Subsequent independent review and repair advanced
the certified source from `f6e8abc` to exact commit
`db14c9261e29aaa81831f0a5fe8674a5519a34eb`. The final independent reviewer returned `PASS` with no
P0/P1/P2 findings. The complete exact-candidate suite passed `3,761`, skipped `5`, and deliberately
deselected the one pre-existing scoped-assurance test whose nested JAA fixture is absent from the
Orchestrator checkout. The widened independent review passed `383` checks and the focused review
passed `306` checks. Canonical Mac v3 was fast-forwarded only to `db14c92`, and
`origin/efficiency/e2-shadow-cache` now resolves to that same commit.

macOS prevents a background LaunchAgent from traversing the canonical repository under
`Documents`; a direct deployment there was observed hanging in the kernel before Python could
enter application code. A distinct, hash-bound runtime checkout was therefore created at
`/Users/admin/.local/share/orchestrator-v3-runtime`. It is an 84 MB operational deployment of the
same exact commit, with current durable Overseer/event state and project source but without the
12 GB isolation scratch, historical runtime clones, virtual environments or private canary
evidence. The reviewed source of truth remains the canonical repository. The canonical `STOP`
remains armed; only the deployed runtime STOP was recoverably archived as
`state/operator-stops/STOP-before-overseer-activation-20260828T142001Z`.

The persistent user service is
`/Users/admin/Library/LaunchAgents/com.pepstee.orchestrator-v3.overseer.plist`. It pins the reviewed
runtime, Homebrew Python and child-process PATH, starts at login, maintains one outer singleton,
and relaunches a failed child supervisor. Deployment validation produced:

- runtime source commit: `db14c9261e29aaa81831f0a5fe8674a5519a34eb`;
- runtime isolation receipt:
  `cb3af5754a8333421be15adea40aec8ddcc3968dccd67ddb653d8796908b2802`;
- dry run: `238` law-linked checks passed, isolation ready, durable session valid, bounded
  rehydration present, no pending stale cycle;
- live canary task: `overseer-pulse-live-canary-20260828T142400Z`, events `2848` through `2854`;
- canary result: accepted `true`, provider `codex`, model `gpt-5.6-terra`, zero tool calls,
  `13,789` observed tokens;
- DV-2 projection: `settle_dv2`, exact knowledge entry
  `dv2-fc83700b5a668599050d65ffad3dab5b5d2bf688e54cbd47a04b340d14e40c70`;
- authority result: one advisory directive recorded, zero executable tasks admitted;
- duplicate-service drill: second owner refused with exit `3`;
- crash-recovery drill: outer PID `9574` replaced terminated supervisor PID `9577` with PID `9923`
  within six seconds while retaining the same durable session;
- dedicated Overseer Telegram delivery: passed; sender/chat configuration remains private with
  mode `0600`, and the durable cursor is identity-bound and `ready`;
- failed historical pulse `overseer-pulse-3cf9291e2bda17dc1de3` remains immutable and was not
  requeued.

The final canonical graph refresh covers the exact source commit: `7,298` nodes, `23,092` edges and
`297` communities. Graph SHA-256 is
`6899ba75494e247476793f155ce061e582999c79087633d3a6751e74c1ad3950`; manifest SHA-256 is
`257ff5d85c39259b654142c0974f50b8d5c8db58cb87ec3855298a0479624ace`.

Operational verdict: the v2-style persistent Overseer is restored and running. It has durable
memory, periodic observation, health/recovery, private Telegram dialogue and governed advisory
intervention. Unlike v2, model text cannot directly mutate projects: consequential work still
requires the signed bounded work-order path. The canonical development checkout remains safely
STOP-protected while the dedicated runtime performs the persistent service role.
