# Orchestrator v3 Deep Audit

**Audit target:** `/Users/admin/Documents/agentic-orchestrator/projects/orchestrator-v3`  
**Baseline:** `f87b5658fd1b6d65b296bec79a41ebee778c1a74`  
**Started:** 2026-07-19  
**Mode:** read-only audit of v3; this report is appended as evidence is found. No v3 fixes.

## Scope and method

The audit covers design-contract consistency, architecture and layering, runtime control flow,
concurrency, persistence/replay, recovery, safety boundaries, provider/model routing, agent prompts,
memory, validation/certification, operator surfaces, dead or duplicate machinery, dependency and
configuration hygiene, and test blind spots. A green test suite is treated as evidence only for the
behaviour it exercises, never as proof of absence of defects.

Each candidate is recorded only after a source trace or executable probe. Severity means:

- **P0:** unsafe to operate; credible destructive/security/correctness failure.
- **P1:** launch blocker or systemic reliability/design failure.
- **P2:** material defect, scaling limit, or maintainability hazard.
- **P3:** local weakness, redundancy, or documentation/ergonomics debt.

## Findings ledger

### F-001 — P2 — Canonical README materially contradicts the shipped system

**Evidence.** `README.md:159-163` declares the engine “Complete and green” and says everything it
claims is implemented. Yet its own roadmap says the tester, daemon, and persistent run loop do not
exist (`README.md:175-186,198-200`), while all three are present at `agents/tester.py`,
`control/daemon.py`, and the daemon tests. It also calls gates “unwired” and says no daemon consumes
the KB (`README.md:183-190`), contradicted by `control/daemon.py:27-32,51-61,92-135`. The README's
“deliberately small” description is stale against 8,408 production lines and 41,466 test lines.

**Impact.** The operator and future agents cannot use the repository's primary document to decide
what exists, what remains risky, or what is safe to launch. In an autonomous factory, stale
capability claims are an operational control defect: they cause duplicate work, skipped setup, and
false certification lineage.

**Status.** Verified directly against the current baseline. Documentation defect; no code fix made.

### F-002 — P0 — The advertised fail-closed boot gate is not wired to the daemon

**Evidence.** `charter/laws.py:28-30` declares BG1 active: “Boot self-test gates dispatch”.
`control/self_test.py:65-94` implements `run_boot_self_test`. A repository-wide call-site search
finds no production caller at all; every reference is the definition, tests, or prose.
`control/daemon.py:114-128` goes directly from STOP check and repository construction to
`run_concurrent(...)` without invoking the boot gate. The daemon's E2E harness invokes this same
unguarded entrypoint.

**Impact.** A production daemon dispatches work even when an active law's check is missing or
failing. This invalidates the central “enforcement before features; no bypass” guarantee and means
the suite proves the gate function in isolation, not the claimed system property. Any supervisor
starting `run_daemon` gets a fail-open runtime despite a green PRIME/BG1 test set.

**Status.** Verified by source-wide call graph and direct daemon trace. Launch blocker; no fix made.

### F-003 — P0 — The production planner emits a task type the production registry cannot dispatch

**Evidence.** The planner explicitly instructs the model to produce `validate` tasks and preserves
that value in spawned tasks (`agents/task_manager.py:31-39,99-111,164-176`). The closed port
catalogue names `validate` as judge review (`dispatch/manifest.py:23`), but
`registry/manifests/` contains only builder/implement, task_manager/plan, and tester/test. Importing
the real registry confirms its keys are exactly `['implement', 'plan', 'test']`. The dispatcher
returns an unknown-task-type failure for absent entries (`dispatch/dispatcher.py:_run_one`), which
the failure taxonomy treats as permanent. The daemon E2E harness masks this mismatch by supplying
its own stub registry with a synthetic `validate` entry (`tests/e2e/_daemon_harness.py:46`).

**Impact.** Any normal plan containing the review step the system prompt itself requests will
permanently fail at dispatch. This breaks the claimed completion pipeline and makes the production
factory structurally incapable of executing its own planning contract.

**Status.** Verified with the live registry object and source trace. Launch blocker; no fix made.

### F-004 — P0 — Completion, evaluation, and certification are orphaned libraries, not runtime gates

**Evidence.** Production call-site searches show:

- `validation.gates.evaluate_completion()` is called only by `tests/test_gates.py`.
- `validation.eval_gate.run_gate()` is called only by tests.
- No production code constructs and records a `CertificationRecord`; all `CertificationLog.record`
  uses are tests.
- No control/dispatch/agent/registry/edge production path runs acceptance or authenticity as part
  of task settlement or project completion.

`control/daemon.py` only ingests and drains tasks. `dispatch.repository.settle()` can mark each task
DONE after the KB gate, but no higher-level project state invokes the four-gate completion contract.

**Impact.** v3 can finish tasks but cannot certify a software project. Tests, acceptance,
cross-provider judgment, authenticity, eval non-regression, and the certification log are detached
components. The system can therefore appear drained/DONE without ever evaluating the completion
contract it advertises as defining “done”. This blocks the proposed software-factory launch.

**Status.** Verified by repository-wide production call-site analysis. Launch blocker; no fix made.

### F-005 — P0 — The claimed incremental replan loop does not exist

**Evidence.** `agents/task_manager.py:1-8` says the daemon re-invokes the planner whenever a
project queue drains and feeds back current state; `:149-162` says the daemon reads
`metadata.planner_done` to terminate the loop. Repository-wide search finds no production consumer
of `planner_done`, no queue-drain replan logic, no project goal registry, and no construction of the
planner's documented `state` payload. `control/daemon.py:114-135` merely rebuilds the repository,
ingests inbox files, drains current tasks, and sleeps.

**Impact.** One externally seeded plan can fan out one batch, but the factory cannot autonomously
inspect what happened, plan the next increment, decide the goal is complete, or enter improvement
rounds. The defining v3 control loop exists only in the planner's prose and output metadata.

**Status.** Verified by full call-site and metadata-consumer search. Launch blocker; no fix made.

### F-006 — P0 — Planner output is never admitted into the task repository

**Evidence.** `AgentResult` defines `spawned_tasks` (`core/models.py:120-129`), and the task manager
returns its planned batch through that field (`agents/task_manager.py:164-193`). Neither
`dispatch.dispatcher` nor `TaskRepository.settle()` reads `result.spawned_tasks`; settlement writes
knowledge/result events and completes only the parent (`dispatch/repository.py:370-446`). A
repository-wide search finds no production consumer. Daemon E2E fan-out is synthetic: its stub
agent writes new JSON files directly to the inbox rather than exercising `spawned_tasks`.

**Impact.** A real `plan` task can report “planned N next task(s)” and reach DONE while creating
zero implement/test/validate tasks. The nominal software factory therefore cannot progress from a
goal to work at all through its production planner contract.

**Status.** Verified by end-to-end data-flow trace. Launch blocker; no fix made.

### F-007 — P0 — Unverified container execution auto-enables merely because `orb` is on PATH

**Evidence.** `dispatch/runner.py:64-66,81-85` selects container execution whenever `orb` or a
binary named `container` is discoverable. There is no opt-in allowlist or default-OFF gate. The
module documents that its CLI shape is assumed (`:16-22`). The ratified completion-contract
decision requires the opposite: container execution stays default OFF until a real OrbStack drill
passes on this machine. Current E2E tests explicitly skip their real daemon paths when either binary
is installed; `tests/test_container_runner_integration.py` uses a fake runtime, not OrbStack.

**Impact.** Installing OrbStack changes production behaviour globally and routes every task through
an unverified command line. This can stop all execution on the operator's actual machine—the exact
failure the contract decision was designed to prevent—and current daemon E2E coverage disappears in
that environment instead of testing the path.

**Status.** Verified by source/config search and contract comparison. Launch blocker; no fix made.

### F-008 — P1 — The generated production container profiles cannot execute the shipped agents

**Evidence.** The real registry commands are host-absolute Python invocations such as
`/opt/homebrew/opt/python@3.14/bin/python3.14 -m agents.builder`. The generated profile mounts only
the project worktree and `/tmp/scratch` (`dispatch/container.py:55-58`), never the interpreter,
orchestrator package, Claude CLI, or Python environment. All three checked-in manifests omit
`llm:*`, `network:*`, and secret capabilities, so their real profiles have no network egress and no
Claude OAuth reference. An executable inspection of `TASK_TYPE_TO_AGENT` and `generate_profile`
confirmed this shape for plan, implement, and test. The “integration” test's fake runtime merely
returns JSON and never creates an isolated environment or executes the trailing agent command
(`tests/test_container_runner_integration.py:29-39`).

**Impact.** Even if the assumed Orb CLI were correct, the sandbox has neither the code nor
credentials/network required to run the agent it is asked to launch. Container detection therefore
turns a functioning host path into deterministic fleet-wide failure.

**Status.** Verified from real manifest/profile generation. Launch blocker while container
auto-detection exists; no fix made.

### F-009 — P0 — v3 has no Codex/OpenAI provider despite the ratified factory routing decision

**Evidence.** `infra/llm.py:27,50-68` accepts only `claude` and `ollama`; no Codex/OpenAI path
exists. `registry/agents.py:32-45` hard-codes task manager, builder, and tester to Claude Sonnet.
There is no judge assignment at all. The ratified v3 contract explicitly requires a Codex provider
seam and a cross-provider Codex judge, with same-provider judging only as an outage fallback.

**Impact.** The intended Codex-led launch cannot be configured through the production provider
seam. Claude exhaustion remains a total execution dependency, and anti-collusion judgment is both
absent and impossible under the current registry.

**Status.** Verified by provider and registry enumeration. Launch blocker; no fix made.

### F-010 — P1 — “Test” tasks author test files but never execute them

**Evidence.** `agents/tester.py:80-130` snapshots the tree, asks the LLM to write tests, and reports
success if any file changed. It contains no test-command discovery or subprocess execution. No
other production control/dispatch path runs a deliverable's test suite after a tester task. The
only pytest execution in production modules checks v3's own law/module tests, not generated project
tests. The four-gate completion path that could later execute tests is itself unwired (F-004).

**Impact.** A syntactically invalid, vacuous, or failing test file is accepted as a successful test
task solely because bytes changed. Downstream dependencies can proceed on the false premise that
the implementation passed independent testing.

**Status.** Verified by full production execution-path search. Launch blocker; no fix made.

### F-011 — P0 — Normal fallback gives autonomous agents unrestricted host permissions

**Evidence.** Without a detected container, `dispatch.runner` deliberately starts agents as bare
host subprocesses (`dispatch/runner.py:64-78`). Every Claude call uses
`--dangerously-skip-permissions` (`infra/llm.py:69-78`). The only boundary is `cwd`; no OS sandbox,
filesystem allowlist, environment scrub, network restriction, or child-process policy is applied.
The subprocess also inherits the entire daemon environment. The settle fence watches only changes
to the orchestrator git tree after the call; it cannot prevent or repair reads/exfiltration or
writes elsewhere on the computer.

**Impact.** A prompt-injected or mistaken builder/tester can read secrets, alter arbitrary user
files, invoke external commands, and send data over the network. This is unsafe for unattended
operation on the operator's primary computer.

**Status.** Verified by process and permission trace. Safety launch blocker; no fix made.

### F-012 — P0 — Production daemon never reclaims tasks left IN_PROGRESS after a crash

**Evidence.** `TaskRepository.reclaim_orphans()` exists (`dispatch/repository.py:530-541`) but has
no production caller. `control.daemon.run_daemon()` rebuilds the repository each cycle and proceeds
directly to ingest/dispatch. The SIGKILL E2E test appears to validate recovery only because its
test-only harness manually calls `repo.reclaim_orphans()` before invoking the daemon
(`tests/e2e/_daemon_harness.py:110-119`). That recovery wrapper does not exist in production.

**Impact.** After daemon death, every claimed task remains durably IN_PROGRESS forever. It is not
claimable, so restart does not resume it. This falsifies the core “restart = resume” claim on the
actual production entrypoint and can strand a project permanently after any crash or forced update.

**Status.** Verified by production/test call-site split. Launch blocker; no fix made.

### F-013 — P1 — Agent-result validation is permissive enough to forge success and crash dispatch

**Evidence.** `AgentResult.from_dict()` validates only that the outer value is a dict, then coerces
`ok` with Python `bool()` and leaves every other field untyped (`core/models.py:134-142`). Thus
`{"ok":"false"}` becomes `ok=True`; non-string summaries and non-list knowledge/spawned tasks are
accepted. A direct probe confirmed these conversions. A second executable probe used a valid JSON
agent response with `metadata: []`: `_spawn_and_parse()` accepted it, then the normal uncontained
fallback attempted `result.metadata["container_fallback"] = True` and raised `TypeError` from
`run_agent_for_task`. `dispatch.run_concurrent()` calls `future.result()` without an exception
boundary (`dispatch/dispatcher.py:107-112`), so this can escape the daemon with the task still
IN_PROGRESS. Existing tests explicitly exercise a truthy integer `ok` as accepted behaviour rather
than enforcing a boolean contract.

**Impact.** Foreign/custom/corrupt agent output can silently turn failure into success or terminate
the dispatch loop. Combined with missing production orphan reclaim (F-012), one malformed response
can both kill the daemon and permanently strand the task.

**Status.** Verified by source trace and two executable probes. No fix made.

### F-014 — P0 — The settle fence fails the contract's “quarantine that task's work” requirement

**Evidence.** `_advance()` integrates a successful task's project worktree before invoking the
self-modification fence (`dispatch/dispatcher.py:148-167`). If the fence then detects orchestrator
tampering, it changes the result to failure but does not revert the already-merged project commit
(`:168-184`). The focused fence test asserts only restoration of the orchestrator tree and terminal
task state; it never gives the offending task a project worktree or asserts its deliverable changes
were quarantined.

**Impact.** A malicious task can modify the orchestrator and still land arbitrary changes in the
deliverable's main branch. The ledger says FAILED while the failed task's product changes remain
live—state and artefact truth diverge.

**Status.** Verified by ordering trace and test-coverage inspection. Safety blocker; no fix made.

### F-015 — P0 — The new settle fence can restore an attacker's tampered source under concurrency

**Evidence.** Each task snapshots the shared orchestrator tree independently after submission
(`dispatch/dispatcher.py:88-104`). If task A tampers before task B's snapshot, B records the
tampered tree as its legitimate baseline. When A settles, it restores clean source. When B later
settles, B sees the clean tree as a delta and `settle_fence()` checks out HEAD then reapplies B's
baseline patch (`infra/worktree.py:94-99`)—reintroducing A's tamper. An executable two-snapshot
probe reproduced exactly this sequence: A restored `SAFE=True`; B's fence then restored
`SAFE=False`.

**Impact.** The safety mechanism can deterministically reinstate malicious source and falsely blame
an innocent concurrent task. The current two-case drill is single-task and cannot detect this.

**Status.** Reproduced against the current implementation. Safety blocker; no fix made.

### F-016 — P1 — Untracked binary files bypass the settle fence completely

**Evidence.** `snapshot_orchestrator_tree()` enumerates untracked files but attempts UTF-8 text
decoding and silently skips `UnicodeDecodeError` (`infra/worktree.py:55-63`). An executable probe
created an untracked file containing non-UTF-8 bytes after the baseline; `settle_fence()` returned
an empty verdict and left the file in place. Git's tracked diff does not include untracked files, so
there is no second detection path.

**Impact.** An agent can plant an executable, archive, model, database, or any source payload with
one invalid UTF-8 byte in the orchestrator tree without quarantine, failure, or journal evidence.

**Status.** Reproduced against the current implementation. Safety blocker; no fix made.

## Interim significance ranking

Requested during the audit on 2026-07-19. This ranks the 16 findings validated at that point by
real-world consequence to an unattended software factory, not by ease of repair. The broader audit
was not yet closed, so later findings may enter above or between these positions.

1. **F-011 — unrestricted host execution.** Highest consequence: one mistaken or injected agent
   can read secrets, alter arbitrary files, execute programs, and exfiltrate data from the
   operator's primary computer. This is a direct machine-compromise boundary, not merely a factory
   correctness bug.
2. **F-015 — concurrent settle fence can reinstall attacker source.** The mechanism intended to
   prevent self-modification can itself put malicious source back after apparently restoring it.
   This defeats the last local safety control and produces false attribution.
3. **F-002 — production dispatch bypasses the fail-closed boot gate.** Every machine-enforced law
   can be red or absent while the daemon still starts agents. This invalidates the trust root for
   all lower-level checks.
4. **F-004 — no runtime completion or certification gate.** The factory can present a drained/DONE
   state without tests, acceptance, authenticity, independent judgment, eval non-regression, or a
   certification record. This is the largest false-success defect.
5. **F-006 — planner output is discarded.** The real planner can complete while admitting none of
   its planned work. The factory cannot progress from a goal to implementation through its own
   production contract.
6. **F-012 — crash restart does not reclaim work.** A normal daemon crash or forced update leaves
   every claimed task permanently IN_PROGRESS. The advertised restart/resume property is absent in
   production.
7. **F-014 — a failed self-modifying task's product changes remain merged.** The ledger records
   failure while the offending task's deliverable mutation stays live, destroying agreement
   between task truth and repository truth.
8. **F-013 — malformed agent output can forge success or kill dispatch.** A string `"false"`
   becomes success; malformed metadata can crash the daemon and, because of F-012, strand the task.
   This is an untrusted-boundary validation failure with both integrity and availability impact.
9. **F-003 — planner and registry disagree on `validate`.** Any standards-compliant plan containing
   the requested review step deterministically reaches a permanent unknown-task failure.
10. **F-007 — unverified container path auto-enables.** Merely installing OrbStack globally changes
    fleet execution to an unverified assumed CLI and suppresses the real daemon E2E path.
11. **F-008 — generated container profiles cannot run the agents.** This compounds F-007: the
    sandbox lacks the interpreter, orchestrator package, Claude CLI, network, and credentials, so
    auto-detection is expected to produce fleet-wide failure.
12. **F-010 — tester never runs tests.** A failing, invalid, or vacuous test file is accepted as
    successful testing because only a file delta is checked.
13. **F-005 — no incremental replan loop.** Even if planner fan-out were admitted, the daemon has
    no queue-drain feedback/replanning mechanism and cannot autonomously iterate to a goal.
14. **F-009 — no Codex/OpenAI provider or cross-provider judge.** The ratified Codex-led routing is
    impossible, Claude exhaustion remains a total dependency, and independent judgment cannot be
    configured. Serious for the intended deployment, but less intrinsically dangerous than the
    execution and truth-integrity defects above.
15. **F-016 — untracked binary fence bypass.** A concrete safety hole that permits payloads to
    remain without evidence. It ranks below the broader F-011/F-015 failures because those already
    defeat the boundary more comprehensively.
16. **F-001 — stale contradictory README.** Operationally harmful and entropy-producing, but it
    does not itself execute unsafe behaviour or falsify runtime state.

### Certification consequence

Any one of F-002, F-004, F-006, F-011, F-012, F-014, or F-015 is independently sufficient to
withhold certification. In combination, the current baseline is neither safe to run unattended nor
functionally capable of operating as the claimed autonomous software factory.

## Threat-model separation requested by operator

On 2026-07-19 the operator deprioritised defects whose practical significance depends primarily
on a deliberate attacker targeting the code. This changes remediation priority, not the factual
validity of the findings.

### Deferred cybersecurity hardening

- **F-016 — untracked binary fence bypass.** The clearest attacker-centric finding: deliberately
  adding an invalid UTF-8 byte defeats the text-only untracked-file inspection. Although generated
  binary artefacts could trigger it accidentally, exploitation of the bypass as a source-persistence
  technique is principally adversarial. Defer for now per operator direction.

### Security language present, but not attacker-dependent — do not defer on that basis

- **F-011 — unrestricted host execution.** Secret theft and exfiltration are cybersecurity
  consequences, but the underlying defect does not require an attacker. A mistaken path, bad shell
  command, hallucinated cleanup, or malformed agent instruction can alter unrelated personal files
  while operating normally. Treat as unattended-operation safety.
- **F-015 — concurrent settle fence restores unauthorised source.** The probe used an attacker-style
  scenario to expose the mechanism, but an ordinary agent accidentally editing v3 during concurrent
  work produces the same stale-baseline restoration. Treat as concurrency and source-integrity.
- **F-014 — failed task changes remain merged.** This occurs whenever a task violates the source
  boundary, accidentally or deliberately. The defect is transaction ordering and false repository
  state, not attacker access.
- **F-002 — boot gate bypass.** An attack could benefit from it, but ordinary missing or failing
  checks are sufficient. Treat as fail-closed correctness.
- **F-013 — malformed agent result.** Hostile output could exploit it, but ordinary model/schema
  drift already triggers false success or daemon failure. Treat as boundary correctness.

### Purely functional/reliability findings

**F-001, F-003, F-004, F-005, F-006, F-007, F-008, F-009, F-010, and F-012** do not depend on an
attacker. They remain in scope for certification and remediation.

### Revised remediation order with attacker-centric hardening deferred

1. F-011
2. F-015
3. F-002
4. F-004
5. F-006
6. F-012
7. F-014
8. F-013
9. F-003
10. F-007
11. F-008
12. F-010
13. F-005
14. F-009
15. F-001

F-016 is moved to the deferred cybersecurity backlog. No finding is removed from the audit record.

### F-017 — P1 — Dispatcher and runner disagree on the canonical project root

**Evidence.** `dispatch.dispatcher` passes the daemon root directly to `resolve_project_dir()` for
worktree create, integrate, and remove, producing `<daemon-root>/<project>`. By contrast,
`dispatch.runner._run_containerized()` calls `task_workdir(..., projects_root=root / "projects")`,
and `infra.workspace.default_projects_root()` plus its documentation define
`<daemon-root>/projects/<project>` as canonical. An executable F-014 regression drill created the
documented project path and proved `_advance()` tried to remove a different worktree under the
wrong root, leaving the rejected task's branch directory alive.

**Impact.** The dispatcher can integrate and clean one repository while the runner resolves or
mounts another. Isolation, settlement, and deliverable state therefore disagree about which tree a
task owns; rejected work can leak as orphan worktrees and containerized execution can target a path
different from the branch the dispatcher prepared.

**Status.** Discovered while patching F-014; remediation included in the current authorized safety
change set and pending full-suite verification.

## Remediation addendum — agent-safety change set

**Authorized:** 2026-07-19  
**v3 commit:** `33dfe4af9481e5a7d436989bf5bc6ed068a9b2a2`  
**Scope:** F-002, F-011, F-013, F-014, F-015, plus F-017 discovered by the F-014 drill.  
**Excluded:** F-016 remains deferred attacker-centric hardening by operator decision.

### Closed — F-011: unrestricted host execution

The bare subprocess fallback was removed from `dispatch.runner`. With neither `orb` nor
`container` available, the runner returns a caused, permanently classified isolation refusal and
does not start the agent command. There is no environment or function parameter that opts back
into uncontained execution. ISO is now an active charter law linked to the real runner integration
suite. A negative control supplies a command that would create a marker file and proves the file
is never created, including when an apparent unsafe-override environment variable is set.

**Operational consequence:** on this machine there is currently no detected production isolation
runtime, and F-007/F-008 remain open. Therefore v3 now refuses agent work rather than running it
unsafely. This is an intentional fail-closed state, not a claim that the factory is launch-ready.

### Closed — F-002: boot gate bypass

`control.daemon.run_daemon()` now calls the real `run_boot_self_test(SOURCE_ROOT)` once before any
invocation capable of dispatching. A red verdict raises `BootRefusal` before inbox ingestion or
dispatch; STOP and a zero-cycle no-op remain non-dispatching exits. BG1's machine-check now includes
the daemon wiring drill itself, preventing later regression to an orphaned gate.

### Closed — F-013: permissive result boundary and worker exception escape

`AgentResult.from_dict()` now requires exact booleans, string summary/cause, list containers with
typed elements, dict metadata, and a non-empty cause for failure. Values such as `"false"`, `1`,
`metadata=[]`, and `knowledge=42` are refused rather than coerced or admitted. The dispatcher now
folds any worker-future exception into a caused failed attempt that spends the ordinary bounded
failure ladder instead of terminating the daemon and leaving the claim unsettled.

### Closed — F-014: failed task work merged before source verdict

`_advance()` now runs the source settle fence before project integration. On a violation, the task
worktree is removed without merging and the quarantine/failure event is settled. The executable
drill writes a real product file in a real git worktree, tampers with orchestrator source, and
proves the project main branch never receives the file and the rejected worktree is removed.

### Closed in the production dispatcher — F-015: stale concurrent baselines

`run_concurrent()` captures one immutable orchestrator-source baseline before submitting any task
in the drain and passes that same object to every settlement. No later task can snapshot another
task's in-flight source delta and reapply it as a legitimate baseline. A concurrency wiring drill
proves exactly one snapshot and the same baseline at both fences. Combined with F-011, production
agents cannot access the host source tree outside the isolation profile.

### Closed — F-017: split project roots

Dispatcher worktree create, integration, and removal now consistently resolve projects under
`<daemon-root>/projects/<project>`, matching `task_workdir()`, container mounting, and the documented
workspace contract. The transactional F-014 drill exercises this corrected end-to-end path.

### Verification evidence

- `python3 -m compileall -q .` — PASS.
- `python3 -m ruff check .` — PASS.
- Direct safety regression set — 34/34 PASS.
- Uninterrupted full suite — **3,354 passed, 4 skipped, 0 failed** in 420.42 seconds.
- Production-shaped `run_boot_self_test(SOURCE_ROOT)` — **PASS: 221 law-linked checks across 17
  files**.
- v3 worktree clean after commit; daemon/supervisor deliberately remain stopped.

### Certification consequence after remediation

These six findings no longer justify withholding certification at commit `33dfe4a`. Certification
is still withheld: among other open launch blockers, F-003 through F-010 and F-012 remain unresolved,
and safe agent execution cannot proceed until the real container path is repaired and drilled.

## Discarded candidates

_Candidates falsified by source trace or probe are recorded here to prevent later re-litigation._

## Coverage and limitations

_Completed at audit close._

## Remediation addendum — F-007/F-008 certified isolation and executable agents

**Authorized:** 2026-07-19  
**v3 commit:** `b17a060423306db48ed132ceccb096f5cfd8d01d`  
**Scope:** F-007 and F-008 only; no model-routing, completion-gate, planner, tester, or other open
finding was changed in this patch.

### Closed — F-007: PATH presence auto-enabled an unverified runtime

Production runtime discovery was removed. Agent execution now requires the fixed local files
`state/isolation/config.json` and `state/isolation/certification.json`; neither PATH contents nor an
environment variable can activate or bypass the boundary. The receipt binds the fixed
`/usr/bin/sandbox-exec` executable hash, macOS release/machine identity, the isolation/runner/
manifest implementation digest, and four passing real-machine drills. Any relevant code, manifest,
OS, or runtime change invalidates the receipt until explicit recertification.

Certification disables dispatch before testing and re-enables it only after proving: a write in
the allowed worktree succeeds; a write outside it is denied; a sandboxed process cannot signal an
unrelated host process; and the shipped `agents.dummy` module executes through the real wire
contract. The daemon now checks receipt validity before the BG-1 law gate, inbox ingestion, or task
claiming. Missing/stale certification therefore leaves queued work untouched instead of consuming
retries. E2E adapters are injected directly inside test processes and are no longer placed on PATH;
the old runtime-dependent skips were removed.

### Closed — F-008: generated profiles could not execute shipped agents

The production adapter is a real macOS Seatbelt process boundary rather than the previously
imagined OrbStack CLI. It executes the registry's absolute host Python command with the shipped
module tree on `PYTHONPATH`, keeps the daemon root as the subprocess working directory, and permits
writes only beneath the resolved task worktree and a task-id-hashed scratch directory. Full parent
environment inheritance was removed: baseline process variables are explicit, provider credentials
are admitted only for `llm:` manifests, named secrets only for `secrets:` declarations, and network
access only when a `network:` capability exists. Claude updater/nonessential traffic is disabled in
agent children.

The builder, task-manager, and tester manifests now declare the Anthropic LLM and documented Claude
network endpoints they actually require. A real production-adapter test ran the registry's shipped
builder module through Apple Seatbelt, invoked a deterministic local Claude-compatible CLI, created
the requested file only in its worktree, and returned the builder's real artifacts/knowledge
contract. The CLI double replaces only the external paid provider in this test; neither the runner,
sandbox, registry entry, Python module, builder logic, nor filesystem boundary is stubbed.

### Verification evidence

- `python3.14 -m ruff check .` — PASS.
- Focused final containment/architecture set — **34/34 PASS**.
- Daemon E2E set after removing PATH-dependent skips — **9/9 PASS**.
- Uninterrupted final full suite — **3,360 passed, 4 skipped, 0 failed** in 456.98 seconds.
- Production-shaped boot gate after the final commit — **227 law-linked checks passed across 18
  files**.
- Final local certification receipt —
  `c58431908bed71391a53776c0d2770feaed8c58a00fd0daf42b149e34f4d54bc`; production preflight
  accepted it.
- v3 worktree clean at `b17a060`; daemon/supervisor deliberately remain stopped.

### Explicit residual boundaries

- This production adapter is macOS-only. Other operating systems fail closed until separately
  implemented and certified.
- Seatbelt does not expose a dependable hostname allowlist here, so network enforcement is
  capability-gated (no network vs outbound network), not per-host, despite retaining the exact
  endpoint inventory in the generated profile data.
- The current adapter permits host file reads so Python, the Claude CLI, system libraries, and
  local authentication can function, while constraining writes and signals. Read-confidentiality/
  exfiltration hardening remains a separate threat-model item; this patch does not pretend to have
  solved it.
- No live paid-provider request was made during certification. Local CLI/module execution is
  proven; live Claude availability, current quota, and authentication remain operational checks at
  launch time.

F-007 and F-008 no longer independently justify withholding certification. Overall v3
certification is still withheld because the other functional findings in this report remain open.

## Remediation addendum — remaining functional factory findings

**Authorized:** 2026-07-19  
**v3 commit:** `6e298927dde3ce85771c082c17aae4278312c777`  
**Scope:** F-001, F-003, F-004, F-005, F-006, F-009, F-010, and F-012.  
**Explicit exclusion:** F-016 remains deferred attacker-centric hardening by operator decision.

### Closed — F-001: contradictory canonical documentation

`README.md` now distinguishes implemented factory behaviour from operational launch evidence. It
names the real planner/build/test/judge loop, project completion path, production daemon, provider
seams, certified isolation boundary, partial roadmap items, deferred F-016 boundary, and the still
unrun live paid-provider drill. An architecture test rejects the previous stale claims and requires
the shipped factory seams to remain named.

### Closed — F-003/F-009: missing validate port and Codex provider

The manifest-derived registry now includes a real `validate` port backed by `agents.judge`. The
judge is assigned to `codex:gpt-5.6-terra`, independent of the Claude planner/builder/tester. The
LLM seam executes headless ephemeral Codex turns in read-only mode, parses its JSONL event stream,
fails when no final agent message exists, and reports Codex-specific authentication remediation.
The checked-in eval ledger carries three live passing model-routing receipts for this assignment.

Judge verdicts use a strict JSON contract and carry the exact project-content revision reviewed.
Certification refuses an otherwise passing verdict from an older revision. The refreshed judge
manifest participates in the isolation implementation digest and the machine receipt was
recertified after the change.

### Closed — F-004: orphan completion, eval, and certification libraries

`control.project_completion.certify_project()` is now the production completion caller. It runs
the real project suite, executable acceptance, revision-bound independent judge, authenticity scan,
and any configured behavioural non-regression eval. A full pass appends per-gate details and the
content revision to `CertificationLog`; a partial pass appends no certification. Identical evidence
for the same revision is idempotent.

Agent-authored test, acceptance, and eval declarations execute through
`control.gate_runner.isolated_gate_executor`, not as privileged daemon-host shell commands. The
executor fails closed without a certified receipt, admits no network/provider credentials, and
makes only the project and gate scratch writable. A gate that mutates deliverable content causes a
revision-stability failure rather than certifying a different artefact from the one reviewed.

### Closed — F-005: missing incremental control loop

`control.project_loop.advance_projects()` groups durable plan lineage, waits for an increment to
reach terminal states, and feeds current files plus DONE/FAILED evidence into the next plan. A
`planner_done=true` result invokes project certification; failed gates become repair evidence. A
passing build certification opens one post-certification improvement phase, and a passing
improvement closes the root loop through a replayable `project_loop_closed` event. Deterministic
follow-up IDs and durable closure prevent duplicate work across daemon cycles and restarts.

Malformed or echoed planner output no longer masquerades as an empty plan: only a valid literal
JSON step array may set `planner_done`. Unknown task ports and malformed step contracts fail before
dead work enters the repository.

### Closed — F-006: discarded planner child graph

Planner output is admitted by `TaskRepository.settle()` through one atomic `tasks_spawned` event.
The entire graph is type-, project-, dependency-, collision-, and cycle-validated before append.
Each child is durably blocked on its parent, covering a crash between child admission and parent
completion. Replay reconstructs parent→child lineage, retries return the already-committed batch,
and even an empty batch is a durable exactly-once decision. A failed append consumes no in-memory
creation sequence.

### Closed — F-010: tester accepted authored bytes without executing them

The tester now executes the suite after independently authoring tests and fails the task when that
suite fails. Projects can declare explicit commands; otherwise deterministic discovery covers
Python/pytest, Node/npm, Go, and Rust. No declaration and no discoverable suite is a failure, never
a default pass. The same execution gate is reused by project completion.

### Closed — F-012: production restart stranded IN_PROGRESS tasks

`control.daemon.run_daemon()` now replays and reclaims orphans once per boot after isolation and
BG-1 preflight, before inbox ingestion or any new claim. The E2E harness no longer performs this
recovery itself. Real subprocess SIGKILL tests prove both one crash and repeated crashes recover
through the production daemon entrypoint and durable event log.

### Verification evidence

- `python3.14 -m compileall -q ...` — PASS.
- `python3.14 -m ruff check .` — PASS.
- `lint-imports` — **79 files, 159 dependencies; L2 contract kept**.
- Focused architecture/factory set — **331/331 PASS**.
- Unattended factory plus SIGKILL E2E set — **5/5 PASS**.
- Uninterrupted final full suite — **3,411 passed, 4 skipped, 0 failed** in 317.10 seconds.
- Production-shaped boot gate — **228 law-linked checks passed across 18 files**.
- Executable `./acceptance` — PASS.
- Refreshed local isolation receipt —
  `30c5b20b97f4db956d0fc40259c076f04f6c8d0f223965ad73f3f117290a7390`; production preflight
  accepted it.
- Daemon/supervisor deliberately remain stopped.

### Certification consequence

All non-deferred findings in this audit are closed at `6e29892`. F-016 remains recorded and open by
explicit operator deferral; stronger portable containerisation also remains a documented future
improvement. This closes the code-audit remediation, not the separate operational launch proof: a
fully live paid-provider plan→build→test→judge→certify run has not yet been executed and must not be
reported as passing until it survives that drill.

## Live factory canary addendum — prediction/calibration ledger

**Executed:** 2026-07-19 15:19–18:26 Europe/London  
**v3 source HEAD after canary fixes:** `9d0602d`  
**Product:** `projects/prediction-ledger-canary`  
**Closed product revision:**
`6ff2cb6532e909b717696a31166bc49b7c2603c29a50221e3a6cc1368e2821a6`

### Outcome

The first live factory canary completed its durable plan→build→test→judge→certify→improve→certify
loop. The event log records **131 claims**, both root project loops have durable closure revisions,
and no canary task remains QUEUED or IN_PROGRESS. Historical failed attempts remain in the event
history rather than being erased.

The delivered product is a standard-library Python/SQLite prediction ledger with:

- add, resolve, list, statistics, and read-only integrity-verification commands;
- stable prediction IDs, 1–99 confidence validation, dates/notes, UTC timestamps, and single-use
  resolution;
- Brier scoring and confidence buckets in human-readable and JSON modes;
- bounded SQLite lock handling, transactional writes, controlled path/database errors, and
  concurrent-process coverage;
- a root acceptance declaration plus separate real demo workflow; and
- README usage documentation and a standard-library unittest entrypoint.

Three certifications were appended, all with tests, executable acceptance, revision-bound judge,
and authenticity gates green:

1. Build revision `e7c5f9b…162d`: **21 pytest tests + 13 subtests passed**.
2. Improved revision `14d9362…e767b`: **36 pytest tests + 17 subtests passed**.
3. Placeholder-free handoff revision `6ff2cb6…821a6`: **41 pytest tests + 17 subtests passed**.

Independent operator verification after final closure also passed: `python3 run_tests.py` ran **38/38
unittest cases**, `./acceptance` produced two resolved predictions with mean Brier score `0.0400`,
the `verify` CLI surface was present, no implementation/documentation placeholder marker remained,
and the product worktree was clean.

### Live defects exposed and closed during the canary

The canary found defects the pre-canary static/full-suite work had not exercised:

- Codex agents needed a task-local writable `CODEX_HOME` while authentication remained read-only;
  certified externally-sandboxed calls now use Codex's outer-sandbox mode. (`b8b5520`, `9673106`)
- The settle fence quarantined the exact root `STOP` kill-switch; exact control-file exclusions now
  preserve `STOP` while lookalikes remain quarantined. (`51772cc`)
- Project-loop failure feedback used generic terminal policy and retained superseded failures;
  concrete result causes now survive and older repaired failures do not create endless replans.
  (`51772cc`, `1baeb01`)
- Authenticity self-scan included runtime/output trees and read TODO-like strings from Codex cache;
  runtime `state` and generated `projects` are no longer treated as v3 source. (`51772cc`)
- Test discovery inspected absolute path parts, so every suite beneath `projects/.worktrees` was
  discarded because an ancestor was named `.worktrees`; exclusions are now relative to the task
  root. (`1537302`)
- Failed tester worktrees disappeared with their useful diagnostics; bounded model summary and
  touched-file telemetry now survive in the durable result. (`23a8ddd`)
- Real pytest opens `/dev/null` as its inactive logging sink; Seatbelt now permits exactly that
  literal device while outside-workspace writes remain denied. The isolation receipt was
  regenerated and accepted. (`ee6c615`)
- The acceptance declaration contract was too implicit, causing repeated script-body/command-file
  confusion. One canonical contract is now shared conditionally by planner, builder, and tester,
  including the `$0` shell-context trap. (`3bf264b`, `2c36d24`, `9d0602d`)
- Improvement mode could request another unconstrained improvement batch forever. It is now exactly
  one bounded post-certification batch plus evidence-driven repair, followed by certification and
  durable closure. (`025f960`)

### Final v3 verification

- Boot gate: **232 law-linked checks passed across 18 files**.
- Focused prompt/acceptance tests after the final contract change: **84 passed**.
- Focused improvement-loop tests: **40 passed**.
- Final uninterrupted v3 suite: **3,427 passed, 4 skipped, 0 failed** in 463.46 seconds.
- v3 source worktree: clean at `9d0602d`.
- Production daemon: deliberately stopped after durable project closure.

### Qualification and remaining work

This is a real live-provider software-factory run, but it is a **degraded single-provider proof**:
Claude quota was exhausted, so planner, builder, tester, and judge all used
`codex:gpt-5.6-terra` through explicit outage overrides. Role separation, isolation, independent
worktrees, revision-bound judging, and certification were exercised; normal Claude→Codex
cross-provider disagreement was not. Do not describe this canary as proof of that normal provider
split.

Remaining operational/design gaps:

- file-scope instructions such as “modify only test files” are still prompt-enforced rather than
  mechanically checked; one canary builder changed `acceptance` while repairing a test;
- Codex CLI results currently record `cost_usd: 0.0`, so the 131-claim count is auditable but monetary
  cost/token observability is not;
- the operator launched the bounded library daemon directly because v3 still lacks a polished
  production supervisor CLI;
- normal Claude planner/builder/tester plus Codex judge operation still needs a live drill after
  Claude quota returns; and
- stronger portable containerisation remains deferred as already recorded.

## Token-efficiency remediation addendum — JAA factory

**Audited and patched:** 2026-07-21  
**v3 commits:** `5d81aae`, `7946d34`, and `bb88b40`  
**Factory state:** deliberately stopped; root `STOP` retained. The historical efficiency PAUSE was
acknowledged and cleared only to dispatch the single controlled canary below; the canary stayed
under budget, so no new PAUSE was created.

### Finding — the inefficiency was real and larger than the latest headline

The reported JAA-00 repair used roughly 922k tokens. A controlled pre-guard replay of the narrow
JAA-00 independent-test task then used **789,964 tokens** in 300.02 seconds: 783,771 input,
729,088 cached input, 54,683 uncached input, and 6,193 output. Cached input remains consumed model
context and does not make the run efficient. Historical telemetry also contains a JAA-04 policy
serialization retest at **1,629,048 tokens** in 347.35 seconds and a temporal-cohort retest at
**448,082 tokens** in 153.48 seconds.

The 789,964-token replay had a tiny direct task prompt. Its cost accumulated across Codex's
repeated observe/tool/observe turns rather than entering as one giant user prompt. The dominant
cause was therefore an unbounded agent interaction loop, compounded by three avoidable context and
filesystem taxes:

- Codex factory homes loaded optional interactive apps, plugins, memories and project instruction
  material that a bounded worker did not need.
- Project inventory code descended into ignored runtime trees. One inspected product had 19,554
  files but only 305 Git deliverable files; its ignored virtual environment alone was 421 MB.
- Per-task scratch retained copied/downloaded Codex runtime state. Before cleanup it held 338 task
  directories occupying 63,667,940 KiB (about 60.7 GiB).

### Remediation — bounded context and bounded interaction

`5d81aae` made factory calls explicit and lean: repository instructions and optional interactive
features are disabled for Codex workers; reasoning effort is role-bound; stored tool output is
bounded; Claude factory calls use their customisation-free mode; file inventories use Git's
tracked-plus-untracked boundary; exact task scratch is removed after durable settlement; and
provider telemetry separates cached, uncached, output and reasoning tokens. A 300,000-token
post-turn circuit breaker writes a durable efficiency pause and prevents the next claim.

`7946d34` adds the missing in-flight control. Codex JSONL is now consumed while the worker runs,
and distinct command, file-change, MCP and web-search items are counted at the process boundary.
The process is terminated when it attempts to exceed its role ceiling:

- task manager: 0 tool calls;
- builder: 16;
- tester: 12; and
- judge: 14.

The worker runs in a disposable certified worktree, so a killed over-budget turn cannot merge its
partial edits. Tool-budget exhaustion is classified as permanent for that task shape, preventing
the dispatcher from spending the same budget again automatically; the task must be narrowed or
receive an explicit bounded override. Codex factory context now auto-compacts at 32,000 tokens and
retains at most 2,000 tokens from each tool output.

### Verification evidence

- Focused provider/agent/registry/triage suite: **186 passed**.
- Final uninterrupted v3 suite: **3,482 passed, 4 skipped, 0 failed** in 388.97 seconds.
- Ruff and diff hygiene: PASS.
- Real subprocess negative control: a later filesystem write did not occur after the simulated
  worker exceeded its tool ceiling.
- Real Codex CLI canary using `gpt-5.6-terra`: with a one-tool limit, the live process was
  terminated on observed call 2 after 10.06 seconds (`GUARD_PASS`).
- Refreshed macOS isolation receipt after the final retry-policy commit:
  `69cad44cfd630eb70059ba9e7b764ed177aa508da07cfe76016d80ed1285feec`; production preflight
  accepted it.
- Historical disposable scratch removed and empty root recreated: 338 directories / about 60.7
  GiB reclaimed. Product source, event history, STOP, PAUSE and authentication files were not
  removed.

### Representative JAA canary and honest residual boundary

The already-queued read-only JAA-00 validation was then dispatched as the only permitted claim
while the root STOP sentinel remained armed. It completed within the guard at **202,282 tokens**
(198,743 input, 161,024 cached input, 37,719 uncached input and 3,539 output), **9 tool calls**, and
133.32 seconds. This is about **78% below the operator-reported 922k repair** (roughly 4.6x better)
and 74% below the 789,964-token pre-guard replay. No product file changed and task scratch returned
to zero bytes.

The canary was useful work rather than a synthetic pass: the judge rejected JAA-00 because the
declared preserved migration receipt and source/adopted runtime databases were unavailable through
`JAA_RUNTIME_DATA_ROOT`; the manifest's JAA-00 evidence list was empty, so database reconciliation,
old-copy recovery and runtime/secret-reference claims could not be independently verified. This is
a product-evidence blocker, not an efficiency failure.

The run also exposed one remaining loop waste: a revision-bound judge rejection was initially
classified as recoverable and requeued against unchanged bytes. `infra.triage` now treats
`judge rejected project` as terminal for that exact task state, forcing repair/replanning before
another independent review instead of spending another approximately 202k tokens on an identical
verdict. The already-requeued canary task was administratively terminalised from its durable
existing result without starting another agent; the log records `task_retry_cancelled`, and the
task is now FAILED for repair routing.

Codex still emits exact usage only at turn completion, so the in-flight guard constrains the
principal cost driver (tool turns), while the exact 300k token check remains a post-turn backstop.
One canary is not enough to claim a stable fleet-wide 4.6x improvement; builder and tester samples
must also be measured. The factory remains STOPPED while the concrete JAA-00 evidence blocker is
replanned.
