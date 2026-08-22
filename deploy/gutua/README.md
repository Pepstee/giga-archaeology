# `gutua` runtime and development handoff

`gutua` (the UK Gigabyte laptop) is the authoritative 24/7 execution host for
Orchestrator v3, JAA development, and Market Aligner. The Mac is the preferred
machine for digital-twin experiments, but it is not a concurrent JAA worker or
database writer.

## Authority boundaries

- JAA source of truth: `/home/gutua/giga/orchestrator-v3/projects/job-application-automation`
- Orchestrator v3 state: `/home/gutua/giga/orchestrator-v3/state`
- Market Aligner source: `/home/gutua/giga/market-aligner`
- Mutable databases: `/home/gutua/giga/shared/market-aligner`
- Private giga-user corpus: `/home/gutua/giga/giga-user`
- Health snapshot: `/home/gutua/giga/health/status.json`
- Automated database snapshots: `/home/gutua/giga/backups/daily`
- Manual cutover/probe snapshots: `/home/gutua/giga/backups/market-aligner`
- Preserved v2 cold standby: `/home/gutua/cold-standby/orchestrator-v2-20260722T120000Z`
- Preserved Mac JAA worktrees: `/home/gutua/giga/archives/jaa-mac-worktrees-20260722.tar.gz`

Do not develop JAA independently on the Mac after cutover. Bring changes back
with Git, or perform an explicit quiesce/snapshot/reverse-handoff. Never allow
the Mac and `gutua` to write the Market Aligner SQLite files concurrently.

## Services

```text
orchestrator-v3.service              continuous v3/JAA factory
market-aligner-collector.service     continuous Scrapling-aware collection
market-aligner-processor.timer       scoring and opportunity-gate cycle
giga-database-backup.timer           online SQLite snapshots with retention
giga-health.timer                    compact health JSON
```

The active Codex CLI is `0.145.0`; `0.139.0` was the pre-cutover version and
can be restored with `npm install -g @openai/codex@0.139.0` if the newer CLI
itself regresses. The Linux Bubblewrap receipt must be regenerated after any
orchestrator isolation/runner/manifest change:

```bash
cd /home/gutua/giga/orchestrator-v3
.venv/bin/python -m dispatch.isolation certify --root "$PWD"
```

Inspect them from WSL:

```bash
systemctl status orchestrator-v3.service market-aligner-collector.service
systemctl list-timers market-aligner-processor.timer giga-database-backup.timer giga-health.timer
journalctl -u orchestrator-v3.service -n 100 --no-pager
journalctl -u market-aligner-collector.service -n 100 --no-pager
```

The units restart failed long-running processes automatically. Systemd journal
retention is capped at 1 GiB persistent / 256 MiB runtime with a 30-day maximum.
The Windows scheduled task starts Ubuntu/WSL after login; Windows AC
sleep/hibernate and the AC lid-close sleep action are disabled.

## Safe pause and resume

Pause v3 before touching its canonical checkout or state:

```bash
sudo systemctl stop orchestrator-v3.service
touch /home/gutua/giga/orchestrator-v3/STOP
```

Resume only after the checkout and state are coherent:

```bash
mkdir -p /home/gutua/giga/orchestrator-v3/state/operator-stops
mv /home/gutua/giga/orchestrator-v3/STOP \
  /home/gutua/giga/orchestrator-v3/state/operator-stops/STOP.manual-$(date -u +%Y%m%dT%H%M%SZ)
sudo systemctl start orchestrator-v3.service
```

Pause Market Aligner before database maintenance:

```bash
sudo systemctl stop market-aligner-collector.service market-aligner-processor.timer
sudo systemctl stop market-aligner-processor.service
```

## Fetching databases to the Mac

From the giga-user directory on the Mac:

```bash
./deploy/gutua/fetch_market_aligner_databases.sh /absolute/destination
```

This asks `gutua` to create consistent SQLite online backups first, then copies
that immutable snapshot over Tailscale. Treat the fetched files as read-only.

## Rollback

If v3 fails, arm its `STOP` file and stop/disable its service. The old v2 tree
remains untouched at `/home/gutua/agentic-orchestrator`, with an independently
verified snapshot and Git bundle in the cold-standby directory above. Restore
v2 manually only after confirming v3 is stopped; never run both factories
against the same project or state.

## Constitutional lane gate — Increment 1

`gate_admission.py constitution` is the canonical gateway for the v1 work-order
lifecycle. It reuses the existing admission gateway and the existing Factory
Turnstile; it does not introduce another scheduler or execution owner.
`constitutional_gate.py` is separate because contract validation,
starting-state capture, proof execution, replay and override-ledger validation
have a different lifecycle from legacy Fable finding admission and the
provider writer lease. The public lane boundary remains `gate_admission.py`.

The machine contract is
`contracts/constitutional-work-order.v1.schema.json`. It binds the exact
`CHARTER.md` version/hash; one increment and explicit non-goals; repository,
relative path and action scope; branch/commit/dirty-state evidence; direct-argv
acceptance proofs; the preserved rollback state; external/irreversible
authority; semantic-review policy; and completion requirements.

Capture deterministic inputs before adding the human-owned objective:

```bash
python3 deploy/gutua/gate_admission.py constitution snapshot \
  --constitution CHARTER.md \
  --worktree /absolute/worktree
```

The native lane reads `work-order.json` from its control directory. It fails
before model launch unless preflight yields a hash-valid `PASS` or `WARN`, then
initializes a work-order-specific Factory Turnstile stage and runs Codex with
`workspace-write` and `never` approval. A completion marker is only a claim:
the gateway runs every proof in a no-network host sandbox, checks the Git delta
against scope, emits a completion receipt, and replays it independently. The
terminal status becomes `OBJECTIVE_COMPLETE_VERIFIED` only when technical
correctness and constitutional compliance both pass.

Contextual breadth or quality is never inferred by regex. When semantic review
is required, create the no-tools Fable receipt with:

```bash
python3 deploy/gutua/fable_gate_broker.py \
  --constitutional-work-order /absolute/control/work-order.json \
  --worktree /absolute/worktree \
  --run-dir /absolute/control/semantic-run \
  --semantic-receipt-out /absolute/control/semantic-review.json
```

Missing or ambiguous semantic evidence yields `HELD_FOR_REVIEW`; a warning is
non-blocking. Only `SEMANTIC_REVIEW_HELD` is overrideable in v1.
`record-override` requires identity, reason, exact reason/path/action scope and
expiry and appends a hash-chained receipt to
`.control/constitution-overrides.jsonl`. Mechanical failures—including scope,
secret, authority, hash, starting-state and proof failures—cannot be overridden.

Increment 1 covers `dual_lane_20260726/run_native_lane.sh` only. Other
historical and current successor launchers remain outside the gate until later
verified increments. Do not claim factory-wide coverage before each launch
surface is migrated and proven.

### Verified Gigabyte checkpoint (2026-08-18)

The installed launcher completed a disposable worktree through preflight, the
existing Factory Turnstile, a bounded worker, sandboxed proof execution and
independent completion replay. Its terminal status was
`OBJECTIVE_COMPLETE_VERIFIED`; both technical correctness and constitutional
compliance were `PASS`. Two independent verification replays were byte-for-byte
identical. Durable evidence is retained on the Gigabyte under
`/home/gutua/software-factory/.control/constitutional-gate-increment1-20260818/`:

- `live-fixture-v4/control/fixture-summary.json` — compliant real-lane proof;
- `negative-fixture-summary.json` — deterministic underspecification and
  scope-escape rejections;
- `rollback-before-247700442837fd0c/` — pre-install files, hashes and Git
  status for the preserved last working state.

The owned suite passed 19 tests on the Gigabyte and 18 tests with one
platform-specific skip on macOS. Historical native units that systemd attempted
to start without work orders exited 42 before model launch. Because their
existing `default.target.wants` enablement caused a restart loop, they were
reversibly disabled and stopped; their unit files and control-directory state
were unchanged. Remediation evidence is in `service-remediation-v2/`. No JAA or
Market Aligner product file was changed or worker launched by this increment.
This is evidence for the named native launcher only, not for the uncovered
successor launchers.

V1 detects Git-visible path escape at completion and rejects the completion;
it does not yet confine writes to the allowlist at write time. Do not describe
post-execution detection as preventive path isolation.

## Constitutional lane gate — Increment 2

Increment 2 adds a preventive filesystem boundary to the same
`dual_lane_20260726/run_native_lane.sh` path. It reuses the v1 work order,
preflight, admission gateway, Factory Turnstile, completion proofs, replay and
receipts. There is no second gate or scheduler. After preflight and before the
Turnstile admits the worker, `constitutional_gate.py plan-confinement` resolves
and hashes the worker, Bubblewrap, worktree, Git metadata, protected inputs and
the minimal existing allowlisted roots. The Turnstile launches
`constitutional_gate.py run-confined`, which revalidates those bindings and
executes the worker inside the recorded Bubblewrap namespace.

For this launcher, the repository is mounted read-only and only the minimal
existing `scope.allowed_paths` roots are rebound read-write. Git metadata,
canonical Constitution/policy/control-plane files, work-order/preflight inputs,
host home and sibling factory state are not persistently writable. Host home,
`/root`, `/mnt` and `/media` are masked; the exact worktree, worker executable
and Codex authentication file are selectively rebound read-only. `/tmp`,
`/run` and the in-namespace Codex cache are ephemeral. A changed executable,
stale writable-tree identity, symlink mount root, hard-link alias, nested mount,
special file, missing path, unavailable/untrusted Bubblewrap, or Git-mutation
action fails closed with a stable mechanical reason code before worker launch.
The semantic reviewer and operator override cannot waive these failures.

This is write confinement, not complete read or external-action isolation.
The worker can read the mounted worktree, normal world-readable system files
and the read-only Codex authentication file required by the provider. It keeps
host networking. It can write to ephemeral temporary storage and to its
inherited stdout/stderr streams. Completion-time Git scope checking remains a
second line of defense and still does not observe ignored files by itself;
Bubblewrap is what prevents ignored/transient out-of-scope writes on this path.

The v1 schema remains compatible, but an allowed root must already exist with
an unambiguous file/directory type. A valid order requesting a path or action
that cannot be mounted safely is blocked as unrepresentable rather than being
guessed into a broader writable directory. This is a mechanical safety hold,
not a stylistic or LLM judgment.

### Verified Gigabyte checkpoint (2026-08-19)

Exactly one disposable, non-product lane completed through the installed public
launcher with terminal status `OBJECTIVE_COMPLETE_VERIFIED`. The Turnstile
receipt names only the fixture worker under the Increment 2 evidence root; no
JAA, DFI or Market Aligner worker was invoked. Inside Bubblewrap:

- the allowlisted write succeeded;
- tracked, ignored, `..` traversal and symlink writes failed with `EROFS`;
- the hard-link escape failed with `EXDEV`;
- `.git`, `/var/tmp` and the Codex auth file were read-only;
- the work order, dummy credential and unrelated factory/control-plane files
  were absent; and
- temporary `/tmp` output was ephemeral and absent on the host afterward.

Each attempt ran as a child process and its exit code, stderr and hashes are in
`live-fixture-v1/worktree/allowed/worker-evidence.json`. The named acceptance
proof passed. A separately self-hashed marker-only completion was rejected with
exit 42 and `PROOF_MISSING`. Two valid completion replays are byte-identical.
Durable receipts and the pre-install rollback are under
`/home/gutua/software-factory/.control/constitutional-gate-increment2-20260818/`.
The primary evidence files are:

- `live-fixture-v1/control/increment2-live-summary.json`;
- `live-fixture-v1/control/replay-and-marker-summary.json`;
- `live-fixture-v1/negative-missing-bwrap/summary.json`;
- `live-fixture-v1/control/write-confinement-plan.json`;
- `live-fixture-v1/control/write-confinement-execution.json`; and
- `rollback-before-increment2/sha256sum.txt`.

The installed code hashes at this checkpoint are
`c0e72af83ee4d77844710e496168c689be0b5ed4639bd1ad1e8f8b43004ddc70`
for `constitutional_gate.py`,
`aa5da3e63fd3fd61c3d97abd4cbb9ace56430915311a13736e7285c1a305e2a5`
for the native launcher and
`4ec1e9d7a67a111c284f90448b0fd3b6018e0f4dc1f9ee8b2fd4d6d2df0e7085`
for the owned tests. The work-order file hash is
`20a9d81becf3db1449673bb21b8783a25d4f8a3913ce430bd105a96756803953`;
the valid replay file hash is
`f7f7016fada927c125fa993aa591db27ea2f62329c9ce3d2ea9c1564381e0a5d`.

Coverage remains intentionally limited to
`dual_lane_20260726/run_native_lane.sh`; every successor or alternate launcher
is uncovered. The next smallest increment is to select one live successor
launch surface, reconcile its lifecycle read-only, and apply this same proven
boundary without weakening or generalizing it prematurely.

## Constitutional lane gate — Increment 3

Increment 3 extends the same gate to exactly one successor boundary: the
existing MAJAA launcher installed at
`/home/gutua/software-factory/.control/majaa-24h-20260810/bin/run_agent_loop.sh`.
It was selected because four installed user units call that exact file
(`majaa-overseer`, `majaa-jaa-operational`, `majaa-market-handoff` and
`majaa-adversarial-cv`) and their lane state was updated through 2026-08-18.
That is the smallest shared boundary for the current MAJAA software-factory
work. All four units were disabled and inactive during installation and proof;
no product worker was interrupted or started.

The earlier service-state discrepancy was a systemd namespace discrepancy, not
evidence that unit files disappeared. `systemctl --user` resolves
`giga-jaa-native.service` and `giga-dfi-native.service` from
`/home/gutua/.config/systemd/user/` as loaded, disabled, inactive and dead. The
system manager reports those same names as not-found because user unit files are
outside its unit namespace. Increment 3 did not recreate, enable, start or edit
either historical unit. Fresh final state and unit-file hashes are retained in
`user-units-final.txt`, `system-manager-units-final.txt` and
`user-unit-files-final.sha256` under the Increment 3 evidence root.

The successor launcher now enters through the existing
`gate_admission.py constitution` gateway. It performs launcher-bound preflight
before resolving or starting a worker, creates an initial Bubblewrap plan,
initializes the existing Factory Turnstile under the work-order hash, and gives
the Turnstile exclusive ownership of every confined worker process. The
work-order authority names the launcher's canonical absolute path and SHA-256;
preflight checks its owner, mode, content and Linux process ancestry. Planning,
execution, completion and replay carry the same launcher binding. A different
launcher, a modified launcher, or a caller that merely passes the path as an
argument cannot reuse that authority.

Each worker round gets a new confinement plan from the still hash-bound
preflight. This is necessary because a legitimate prior round can change an
allowed mount's identity. Replanning preserves the fail-closed identity check;
the launcher never reuses a stale plan and never weakens
`MOUNT_IDENTITY_MISMATCH`. Existing mutable Codex session state remains an
explicit `LAUNCHER_SESSION_RESUME_UNREPRESENTABLE` hold rather than a reason to
expose the host Codex home.

### Verified Gigabyte checkpoint (2026-08-19)

One disposable non-product fixture identity and lane,
`constitution-increment3-fixture-v1`, completed through the installed public
launcher. Before its work order existed, the launcher exited 42 with
`CONTRACT_UNREADABLE`, created zero round files and did not start the fixture
worker. With the valid order, round 1 wrote only the completion marker; the
named proof and verification both exited 42 and rejected that claim. Round 2
ran through the Factory Turnstile and Bubblewrap, after which the terminal
status became `OBJECTIVE_COMPLETE_VERIFIED` with both technical correctness and
constitutional compliance `PASS`.

Inside the final worker namespace, the allowlisted write succeeded. Separate
child processes attempting tracked, ignored/transient, `..` traversal,
symlink, Git-metadata and `/var/tmp` writes failed at write time with read-only
filesystem errors. The launcher, work order, dummy credential, Constitution
and user configuration were absent; the existing Codex authentication file
was present only as a read-only file and its content was not copied into
evidence. Process exit codes, stderr hashes and mount evidence are in
`live-fixture-v1/worktree/allowed/worker-evidence.json`.

The Factory Turnstile recorded two successful writer settlements, ended
`sealed`, and retained no live lease. Two independent completion replays and
the launcher's saved verification are byte-for-byte identical. The final replay
file SHA-256 is
`ebc37ab2ae31e74852ddaeb28648324cd330e1aeaa419a492173eaa20776641e`;
the work-order SHA-256 is
`82c9ebba9159d8c49819c5514f43943da032d36a6034b28f60984843d6383a23`.
The self-hashed final audit is
`/home/gutua/software-factory/.control/constitutional-gate-increment3-20260819/increment3-final-audit.json`
(file SHA-256
`e9f01594bb54db44e040cfceebc8f64da33111d17211d45304a2e988af534cf1`,
receipt SHA-256
`fc4ba191f1131432e53103f747bce05bccb7a52e8c73ecf1f91debd39320c6d8`).
It independently validates 13 self-hashed receipts. The same evidence root
retains the missing-order rejection, final receipt chain, Turnstile state,
process and service snapshots, and two diagnostic attempts that exposed stale
multi-round plan reuse and missing Turnstile ownership before this checkpoint;
those diagnostic receipts are preserved but are not claimed as passing.

The installed gate suite passed 27 tests on Gigabyte and 25 tests with two
Linux-only skips on macOS. The existing Factory Turnstile suite passed 439
tests. The frozen Increment 2 receipt still replays byte-for-byte with SHA-256
`f7f7016fada927c125fa993aa591db27ea2f62329c9ce3d2ea9c1564381e0a5d`.
The final installed hashes are:

- `1f1f6eb6e6251e05a10762768b54797940b209cc0a3d1cb16a43885f45eeec44`
  — `constitutional_gate.py`;
- `296b62e7eae92d8cde90f28d620a5996cd9f066e0b8bb2962c487db58f3e183e`
  — `test_gate_admission.py`;
- `227209c85895e28570ef562bf41b91095ef81b41c19a7a987bd20d282027f68d`
  — `constitutional-work-order.v1.schema.json`; and
- `b6a2af7264e1161ff60d8a42a2c62386acae53b67a9c04baab1eb6e0bfc76f0a`
  — the selected successor launcher.

The preserved pre-Increment 3 rollback is
`/home/gutua/software-factory/.control/constitutional-gate-increment3-20260819/rollback-before-increment3/`.
Its manifest re-verifies and has SHA-256
`6cb06eda871148a237626afd36174f8426565718fd3b58172a34d0c8d1310841`.

This checkpoint prevents out-of-scope persistent writes on the selected
launcher, but it does not provide complete read isolation or a network
namespace. The worker may read the mounted worktree and ordinary system files,
retains host networking, can write ephemeral `/tmp` and `/run`, and can write
its inherited output streams. Completion-time Git scope/proof checks remain
defence in depth. Historical native launchers and the enabled 2026-07-30/
2026-08-01 successor wait paths remain uncovered; no other launcher is covered
by implication. The next smallest increment is to reconcile and migrate one of
those actual wait-to-worker process chains, again with a disposable fixture and
without re-enabling a product unit.

## Constitutional lane gate — Increment 4

Increment 4 extends the same gate across exactly one enabled wait-to-worker
chain:

```text
giga-jaa-single-codex-successor3.service
  -> dual_lane_20260730/run_jaa_successor3_wait.sh
  -> .control/majaa-24h-20260810/bin/run_agent_loop.sh
  -> gate_admission.py constitution
  -> Factory Turnstile
  -> constitutional_gate.py run-confined
```

This chain was selected after a read-only inventory, not because its earlier
exit status was assumed to make it current. Its user unit was loaded and
enabled, was pulled in by `default.target`, and repeatedly reached the actual
wait-to-worker seam. Retained journal output shows that, after successor2 was
no longer active, the old downstream supervisor found historical
`started_at` state, reported that the control directory already contained a
run, and exited 73. `Restart=on-failure` then retried it every 30 seconds. The
2026-08-01 JAA chain was waiting behind this unit, while the DFI chain's own
predecessor state was already terminal. This evidence made successor3 the
smallest operationally relevant boundary; it does not prove that the
historical product objective should be resumed.

The optional v1 `wait_to_worker` contract binds the downstream launcher, wait
wrapper and user-unit transition. It records each canonical path and SHA-256,
the wrapper and unit-file ownership/mode, the exact unit name, fragment path,
`ExecStart`, manager and unit-file state. Live admission verifies those bytes,
the loaded systemd metadata, the exact user-unit cgroup, and both wrapper and
launcher in `/proc` ancestry before worker resolution. Confinement planning,
execution, completion and replay retain the same binding. Static replay does
not require the disposable unit to remain active, but it still re-hashes its
bound files. A different wrapper, unit, launcher, caller ancestry or cgroup
cannot reuse the work order.

The existing wait wrapper now calls the already-gated MAJAA launcher and keeps
it as a child so the live ancestry is observable. The selected unit adds
`RestartPreventExitStatus=42`: a constitutional hard block remains an explicit
failure but does not become a restart storm. Installation used `daemon-reload`
only; the product unit was not manually started, stopped, restarted, enabled or
disabled. Its already-scheduled retry entered the new gate, rejected the
missing historical work order with `CONTRACT_UNREADABLE` before worker
resolution, and settled at `failed/failed`, exit 42, `NRestarts=0`. It remains
enabled, so a future user-manager boot can make one gated attempt; it cannot
silently launch the old supervisor without a valid chain-bound work order.

### Enforcement boundary

Hard pre-launch rejection now covers malformed or missing work orders,
Constitution/work-order hash mismatch, changed wrapper/unit/launcher bytes,
changed systemd identity or `ExecStart`, wrong cgroup or caller ancestry,
unrepresentable confinement, protected secrets, and hash-integrity failures.
These are mechanical checks with stable reason codes. Operator overrides
cannot waive secret, hash or filesystem-confinement protections.

Once admitted, Bubblewrap permits persistent writes only to the canonical
allowlisted roots in the work order. The disposable proof shows that tracked,
ignored/transient, symlink, `..` traversal and `.git` escapes fail inside the
worker namespace at write time. The fixture credential was read-only and host
`.ssh` was unavailable. Factory Turnstile alone acquires and settles the writer
lease.

Named acceptance proofs, final Git scope, technical correctness and
constitutional compliance are still completion checks. A marker is only a
claim: the marker-only fixture was rejected with `PROOF_FAILED`, followed by
`COMPLETION_UNVERIFIED` and `TECHNICAL_CORRECTNESS_FAILED`. Contextual scope or
design quality remains reviewable semantic evidence rather than a brittle hard
block; Increment 4 did not recalibrate that reviewer.

This is not complete read or network isolation. An admitted worker can read
the mounted worktree, its selectively mounted read-only provider credential
and ordinary system files, and retains host networking. `/tmp` and `/run` are
ephemeral, and inherited output streams remain writable. Completion-time Git
scope verification remains defence in depth rather than the primary write
boundary.

### Verified Gigabyte checkpoint (2026-08-19)

One disposable, non-product user unit exercised this exact wrapper-to-launcher
seam. It is linked but not enabled and is now `inactive/dead`, with no restart
policy. Missing and invalid orders blocked before the worker sentinel;
independently mutated launcher, unit and wrapper hashes were rejected with
`LAUNCHER_HASH_MISMATCH`, `WORKER_UNIT_HASH_MISMATCH` and
`WAIT_WRAPPER_HASH_MISMATCH`. Calling the gate outside the unit was rejected
for launcher, wrapper and unit ancestry mismatch.

The compliant run wrote one allowed result, recorded exit status 1 for every
forbidden write attempt inside Bubblewrap, passed its named proof, and reached
`OBJECTIVE_COMPLETE_VERIFIED`. Its work-order SHA-256 is
`c6e31970a0ef5292c357118aaa826d6f934a620accf05a96027b7b168cdf93b0`.
The saved completion verification and two independent replays are
byte-identical with SHA-256
`e4325a06f1835474cdfa9528c875e560fb177bd8ed017054929e30a7f7cf17b7`.
The final receipt self-hash is
`b7cb742972f78266b48da44814b3fa99a343123ce5c4c76dd24ffd7f0c1343e3`.

The fixture Turnstile ended `sealed` with a null lease and one settled writer.
Its state and event-ledger hashes are respectively
`c43010ce9753e03e4db41ee122dbe20f880d312b3fbff356bbf3088c85ce6134`
and
`850ee9e3d3d42cdd9177aeeb75f93e1f5fc5130f42bbff25d49daedd1e75e830`.
The lock was independently reacquired after completion. No Codex, Claude, JAA,
DFI or Market Aligner product worker was started by, descended from, or
overlapped the fixture proof interval (18:02:48–18:03:52 BST). The system
Market Aligner timer had finished its preceding independent cycle at 18:01:27
and began another at 18:16:40, after the proof. That later cycle was visible in
the final global process snapshot under `/system.slice/market-aligner-processor.service`;
it was not stopped or modified and must not be misreported as global process
absence. The selected chain itself remained blocked before worker resolution.

Durable evidence is retained under
`/home/gutua/software-factory/.control/constitutional-gate-increment4-20260819/`
and in the existing MAJAA state root. The primary paths are:

- `increment4-final-audit.json` — self-hashed final checkpoint and installed
  state;
- `live-fixture-v1/` — one fixture, its worktree, negative inputs, ancestry
  rejection, workers and replay copies;
- `.control/majaa-24h-20260810/state/constitution-increment4-fixture-compliant/`
  — the passing receipt chain and settled Turnstile;
- `.control/majaa-24h-20260810/state/constitution-increment4-fixture-marker-only/`
  — the rejected completion claim;
- `.control/majaa-24h-20260810/state/jaa-single-codex-successor3/`
  — the production chain's pre-worker missing-contract rejection; and
- `rollback/pre-increment4/` — exact prior bytes and a verified manifest with
  SHA-256
  `d17f39a1a71550c2f7cc4268856a80b13ff8c5e99f15338072e5d8adb1e845ed`.

The final installed gate suite passed 30 tests on Gigabyte and 28 applicable
tests with two Linux-only skips on macOS. The unchanged Factory Turnstile suite
passed 439 tests. Final installed hashes are recorded in the self-hashed audit;
the enforcement-critical values are:

- `ce11af8b14f3ff78be116fbc85dc0e06816da89fb6785bc493303f5ae83ead05`
  — `constitutional_gate.py`;
- `0b684bc1635873742f6d94897435434add8eaafcf5b71c41f4e90d4e72724f7c`
  — `constitutional-work-order.v1.schema.json`;
- `3cfeb987adb085027f00920255114e4286f224ed4da5bd65b075f9eccc7a7a13`
  — the MAJAA launcher;
- `1d20d517d8b455717574eaaabe6210f3ff3625d370e59b765aceccca65d354e9`
  — the selected wait wrapper; and
- `9c4931195c7a242a21bc2ee98ed978a093e9ff1d0a46511001280063976edac0`
  — both installed copies of the selected unit.

Coverage remains deliberately narrow. In particular,
`giga-jaa-honest-completion-successor.service` and
`giga-dfi-behaviour-completion-successor.service` are still enabled but
uncovered, and no other launcher inherits Increment 4 authority. The next
smallest increment is a fresh read-only inventory followed by migration of
exactly one of those remaining wait chains through the same disposable proof;
it is not part of this checkpoint.
