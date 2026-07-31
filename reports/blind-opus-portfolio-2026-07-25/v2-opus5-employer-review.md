I have completed a deep inspection. Here is the panel report.

---

# Blind Portfolio Assessment — `agentic-orchestrator` @ `32efb07`

## 1. Employer verdict

This is a genuinely substantial and unusually *falsifiable* piece of systems engineering: a 6,000-line autonomous multi-agent orchestrator whose headline claims — event-sourced replay, enforced layering, single-writer file discipline, durable restart-proof failure budgets, a boot gate that refuses to dispatch unless the constitution's own checks pass — I was able to **verify by execution, not by reading marketing**. 335 tests run hermetically in 3.2 seconds and 16 of 18 deliberate defects I injected into core invariants were caught. That puts it well above the median portfolio, which claims rigour and cannot demonstrate it. Against that, the presentation is close to self-sabotage: the README has not been touched since the first commit and still describes an empty skeleton pointing at a directory that does not exist; the one runnable end-to-end demo crashes on an `AttributeError` from a field rename made a week before HEAD; a test the project's own incident ledger names as the executable lesson for a real production failure is a proven false positive; and a planner-emitted dependency cycle strands a project permanently with no alarm, in a system whose entire thesis is "never let a project silently stall". The velocity (16 commits and ~2,000 lines in four hours on day one) makes authorship depth a real open question that only a live interview can settle. **Interview — strongly — for senior AI/agent and backend/platform roles, on the explicit condition that the candidate defends the mechanisms live; do not offer at senior level on the artifact alone.**

---

## 2. Sixty-second screening impression

**Recruiter.** Single author, 71 commits over seven active days, dense professional-sounding commit messages, a "laws" folder, a charter, a run ledger. Looks serious. Opens `README.md`: *"Foundation commit: the enforcement skeleton is green on an empty structure. Next: the P0 milestone."* Concludes the project is unfinished and moves on. **This is the single highest-cost defect in the submission.**

**Engineering manager.** Notices the git log immediately — commits like `4597f28` and `42813f4` read as real incident post-mortems with dates, task ids and named regressions ("the fence reverted this very fix mid-edit — operator-caveat demonstration no. 2"). Notices there is **no CI whatsoever** (no `.github/`, no `Makefile`, no `tox.ini`), only `scripts/check.sh` that nobody runs automatically. Notices the docs contradict each other: `docs/QUALITY_CHARTER.md:61` says "nothing is auto-marked done without your one-tap confirmation", `validation/gates.py:14-17` says "there is no human-confirmation gate". Flags: ships fast, keeps the narrative up to date only sometimes.

**Senior engineer.** Opens `dispatch/repository.py` and `control/pool.py` and sits up. The concurrency model is stated precisely and correctly — *only* the slow `invoke` runs on worker threads, every state mutation and every git operation is serialised on the main thread (`control/pool.py:1-13`, `_settle_one`). `core/state_machine.py` is a total transition table with a written rationale for why illegal pairs are no-ops rather than exceptions. `dispatch/dispatcher.py:92-101` hashes a canonical fingerprint of an attempt's inputs so a deterministic failure cannot be retried against unchanged inputs. Then notices `agents/judge.py:3` claims the judge runs on Codex while `registry/agents.py:53` puts it on Claude, and starts wondering how much of the prose is load-bearing.

---

## 3. What this proves (strongest concrete evidence)

Everything below I executed. Exact commands are in §12.

**a. The event log really is the system of record, and replay is proven equivalent — not asserted.**
`infra/event_store.py` + `dispatch/repository.py::replay` reconstruct tasks, priorities, confirmations, failure counters, attempt fingerprints and abandonment watermarks from the log alone. The proof is not a docstring: `tests/test_soak.py:71-73` drives 6 projects × 8 concurrent workers through *real git worktrees*, then asserts `{t.task_id: t.status for t in replayed.list()} == {...for t in repo.list()}`. That is a genuine property test for event sourcing, and it runs in 1 second.

**b. Failure budgets survive restart, and the test asserts the old bug's precondition.**
`tests/test_failure_budgets.py:53-71` first asserts `t.retries == 0` — *"precondition: replay resets the in-memory counter (the old hole)"* — and only then asserts the task still terminates. That is how someone who has actually been burned writes a regression test. Injecting mutation **M2** (drop the durable `hard_failure_count` guard in `dispatch/dispatcher.py:164`) and **M9** (stop rebuilding the counters in `replay`) were both caught.

**c. The boot self-test is a real mechanism, executed live.**
`control/self_test.py` regex-extracts every `tests/**.py` path named in `charter/laws.py`, requires each to exist, to *collect*, to *pass*, and requires the passed-count to be ≥ the file count — no bypass flag exists, and `tests/architecture/test_boot_self_test.py` asserts its absence. I ran the real code path:

```
BOOT SELF-TEST -> True | 91 law-linked checks passed (17 files)
```

Injecting mutation **M8** (add an `AGENTIC_SKIP_SELFTEST` bypass) produced `7 failed, 1 passed`. The no-bypass law has teeth.

**d. The architecture laws hold in fact, not only in configuration.**
Rather than trust `pyproject.toml`'s import-linter contracts (import-linter was unavailable), I re-derived them by AST analysis of every module: **0 L2 layering violations, 0 registry-leaf violations, 0 `selfdev` imports**. Likewise for L7: an independent regex scan of every runtime package found raw `open(w/a)` / `write_text` / `unlink` / `rmtree` **only** inside `infra/atomic_io.py`. Both headline claims are true.

**e. The gates are mechanically hard to cheat.**
`validation/authenticity.py` is a real AST walker that correctly exempts `Protocol`/`ABC`/`@abstractmethod`/`@overload` bodies. `validation/mutation.py` is a real stdlib mutation tester (comparison/arith/bool/constant/return-value operators, sandboxed copy, restore-between-mutants). `validation/acceptance_exec.py` requires a declared, executing, output-producing criterion. Injecting **M4** (authenticity always passes) → `5 failed`; **M11** (mutation score always passes) → `1 failed`; **M5** (no-declaration silently passes) → `1 failed`.

**f. The incident→test ratchet is real.**
`docs/planning/RUN_LEDGER.md` §3 names 13 regression tests as the executable lessons for 13 specific incidents. **All 13 exist, in the files named, and pass.** Most portfolios that claim this cannot survive the check.

**g. The failure taxonomy is thought through, not string-matched ad hoc.**
`infra/triage.py` is a single three-class taxonomy (`PERMANENT` / `TRANSIENT` / `RECOVERABLE`); `infra/llm.py:79-93` classifies a *bare non-zero exit with no diagnostic output* as transient with a written justification (that is how the Claude CLI surfaces a usage cap) — a subtle, experience-derived call. `control/prescreen.py` is explicitly fail-open by law, and injecting **M18** (make it fail closed) was caught.

**Negative-control summary — 16/18 injected defects caught:**

| | Mutation | Result |
|---|---|---|
| M1 | drop `QUEUED+BLOCK` from the state machine | **CAUGHT** (2 failed) |
| M2 | ignore the durable hard-failure budget | **CAUGHT** |
| M3 | drop the BG-3 input-fingerprint refusal | **CAUGHT** (3 failed) |
| M4 | authenticity gate always passes | **CAUGHT** (5 failed) |
| M5 | missing acceptance declaration passes | **CAUGHT** |
| M6 | stop refusing mock-path acceptance criteria | **MISSED** |
| M7 | an active law loses its machine-check | **CAUGHT** |
| M8 | add a boot-self-test bypass switch | **CAUGHT** (7 failed) |
| M9 | replay drops durable failure counters | **CAUGHT** |
| M10 | `EventStore.replay` yields nothing | **CAUGHT** (7 failed) |
| M11 | mutation gate always passes | **CAUGHT** |
| M12 | settle skips the L9R self-mod fence | **CAUGHT** |
| M13 | BG-2 breadth cap always unrestricted | **CAUGHT** |
| M14 | burn-rate breaker never trips | **CAUGHT** |
| M15 | `claim_next` ignores the per-project cap | **CAUGHT** |
| M16 | `write_json_atomic` writes non-atomically | **MISSED** |
| M17 | overseer may enqueue reserved `__` projects | **CAUGHT** |
| M18 | pre-screen fails closed instead of open | **CAUGHT** |

---

## 4. Architecture and implementation assessment

**Coherence — strong.** One thesis, carried consistently: *durable legible log + stateless agents + gates that cannot be cheated + laws with machine-checks*. The dependency arrow `edge → control → (dispatch|scheduling|validation) → pa → agents → memory → infra → core` is not decoration; it is enforced and it holds. `registry/` is a genuine leaf and is the single source for `task_type → agent → model`.

**Boundaries — good, with one deliberate and well-argued inversion.** `validation/assurance.py:9-10` explicitly duck-types the budget governor and takes it by injection *because* validation must not import control. That is a designer who understands why the rule exists rather than one obeying it.

**Determinism — good.** Every LLM call site is injectable (`call: LLMCall = call_llm` in every agent; `Invoke` in the dispatcher; `runner`/`opener`/`notifier`/`prescreen` injected elsewhere). Consequently the entire 335-test suite runs offline in 3.2 s. `_input_fingerprint` (`dispatch/dispatcher.py:92`) canonicalises with `sort_keys=True` and strips the volatile `workdir` key — correct.

**Persistence — good core, missing operational maturity.** `infra/atomic_io.py` does temp-file + `fsync` + `os.replace`, and `read_jsonl` tolerates a truncated final line. Two gaps: no parent-directory `fsync` after `os.replace` (so the rename itself is not durable across power loss), and **no log compaction or snapshotting**. `TaskRepository.last_results()` and `failure_causes()` each re-read the entire log from disk, and both are invoked from the daemon's per-cycle hook (`control/daemon.py:129`, `:518`). At the log volumes the project's own ledger describes (1,688 runs in one burn), that is a full-file scan every couple of seconds, forever.

**Concurrency — the best-reasoned part of the system.** `control/pool.py` confines worker threads to `invoke` only; claiming, recording, spawning, git merges and settling all happen on the single main thread, so there is no shared mutable state to corrupt. `claim_next` claims-on-select so two claims cannot hand out the same task. Per-project concurrency defaults to 1 (one writer per tree) with a documented knob to trade conflicts for parallelism, and cross-project concurrency is unaffected. `wait(..., timeout=maintenance_interval)` ensures the per-cycle maintenance still fires while every worker is mid-call — a starvation bug the author clearly hit and fixed.

**Failure handling — sophisticated, with one hole.** The ladder (`permanent fail-fast → budgeted transient requeue → BG-3 fingerprint refusal → PA fast-path → bounded retry → escalate`) is coherent and every rung is bounded by counters derived from the durable log. `propagate_prerequisite_failures` cascades transitively to a fixpoint so a stranded graph terminates. **The hole:** nothing validates the task graph the planner returns. `agents/task_manager.py:129-130` maps LLM-supplied `depends_on` indices with only a self-reference guard. I demonstrated the consequence:

```
select_next_task -> None
run_until_idle processed -> 0
cascade -> 0
statuses -> {'A': 'queued', 'B': 'queued'}
_all_terminal('cyc') -> False
monitor_projects outcomes -> []
=> project is permanently stranded: no replan, no escalation, no abandonment
```

A two-node cycle parks a project forever. `_all_terminal` never becomes true, so `monitor_projects` never evaluates it, so no replan, no overseer intervention, no abandonment, no notification. BG-5 guards only the overseer's own pulses. In a system whose README-level promise is "never let one silently stall", this is the most consequential engineering defect I found.

**Model integration — mature and honest about its own erosion.** `infra/llm.py` is a clean provider seam (claude / openai-codex / ollama) with session support only on the path that has it and graceful degradation elsewhere; `call_spec` gives declarative primary+fallback. `registry.model_for` supports reversible `AGENTIC_<AGENT>` overrides for provider outages. The overseer's "mind on disk" (`memory/overseer.py`: capped `BELIEFS.md`, append-only `journal.jsonl`, per-project dossiers, immutable CORE + evolvable EXTRA handoff) is a genuinely thoughtful continuity design — bounded by construction, with the provider session explicitly demoted to a cache. The `_is_canonical_uuid` guard, with its comment about the CLI rejecting bare 32-char hex, is exactly the kind of scar tissue you cannot invent.

*However*: the cross-provider-independence property (finding "F5") is the load-bearing justification for the judge gate, and it is currently **suspended** — all four of task_manager, builder, tester and judge sit on `claude` (`registry/agents.py:50-53`). Commit `d0feb84` says so plainly. Three separate docstrings still claim otherwise.

**Operability — personal-scale.** `infra/pidlock.py` is correct (including a real Windows liveness probe rather than the `os.kill(pid,0)` trap). `AGENTIC_DEADLINE_HOURS` writes its own `STOP` so a self-chosen stop stays stopped. `edge/server.py` is stdlib-only, read-only against the log, token-authenticated with `hmac.compare_digest` and an `HttpOnly; SameSite=Strict` cookie. But `run_forever.sh` relaunches unconditionally every 5 s with no backoff and no failure budget — a red boot self-test therefore produces a Telegram alert every 5 seconds indefinitely, which is precisely the "repeat-alert pathology" the project's own ledger names (5,384× in v1). It also exports `AGENTIC_BUDGET_USD` defaulting to `1000000`, which effectively disables the L6 cap it advertises.

---

## 5. Code and assurance quality

**Maintainability — good.** Modules are small and single-purpose (largest runtime file: `edge/server.py` at 578 lines, `control/daemon.py` at 543; the L3 guardrail is 800). Naming is consistent. A static scan found **zero unused imports** across the tree, which corroborates that `ruff check .` (E,F) really is run.

**Duplication — modest but real.** Four bespoke JSON-extraction routines that overlap heavily: `agents/judge.py::parse_verdict`, `agents/task_manager.py::parse_plan`, `agents/overseer.py::parse_directive` + `_extract_json_object`, `validation/assurance.py::_parse_hardening`. `control/scorecard.py::load_events` re-implements JSONL reading that `infra/atomic_io.read_jsonl` already provides. `SOFT_LIMIT = 800` is duplicated between `pyproject.toml` and `tests/architecture/test_loc_soft_guardrail.py` — with a comment acknowledging it — in a repo whose law L1 is "single source of truth". `write_json_atomic` and `write_text_atomic` are near-identical.

**Tests — above portfolio average, with two identified weaknesses.** 335 tests, hermetic, 3.2 s, no network, no LLM. `PYTEST_CURRENT_TEST` hard-mutes `notify`, bypasses `prescreen`, and disarms the L9R fence — each with a written justification tied to a real incident where the test suite rang the operator's actual phone. Tests are behavioural rather than mock-shaped, and several assert *bounds* rather than exact values (`assert rounds <= MAX_TRANSIENT_REQUEUES + task.max_retries + 2`).

The two weaknesses:

1. **A proven false positive on a headline behaviour.** `tests/test_acceptance_exec.py:39` runs `python acceptance.py sample.srt --mock` in an *empty* directory and asserts `not r.passed and "mock" in r.detail`. With the mock-refusal guard removed the test still passes, because the command fails for an unrelated reason and the word "mock" appears only because the detail string echoes the command back:

   ```
   UNMUTATED  detail: ... `python acceptance.py sample.srt --mock` demonstrates a mock path ...
   MUTATED    detail: ... `python acceptance.py sample.srt --mock` exited 2: can't open file ...
   assertion still holds: True
   ```

   `RUN_LEDGER.md:49` cites this exact test as the executable lesson for a real incident ("the June demo literally ran `acceptance.py --mock` against a dead package"). The lesson is not actually encoded.

2. **A law-linked check that cannot fail.** `tests/architecture/test_loc_soft_guardrail.py` ends in `assert True`. It is one of the 17 files the boot self-test requires, so law L3 contributes a check with zero discriminating power to the prime-directive count. This is *documented* as intentional ("soft guardrail, never blocks"), so it is not dishonest — but it means "every active law has a machine-check" is weaker than it sounds.

**Coverage gaps.** No test asserts the *atomicity* property of `atomic_io` (M16 missed) — L7's check verifies routing, not crash-safety. No test exercises `scripts/demo_e2e.py`. No coverage measurement exists.

**Does the evidence support the claims?** Mostly yes, and unusually so — but three claim classes do not survive contact:
- **Verifiable and true:** layering, single-writer, replay, durable budgets, boot gate, gate teeth, incident→test ratchet.
- **Stale relative to code:** cross-provider judge independence, the human confirmation gate, the "~207 tests" count, `README.md` in its entirety.
- **Unverifiable from the artifact:** every operational number in `RUN_LEDGER.md` (115/1,573 runs, the 90× oscillator, eight project repos, the eleven silent hours). `state/`, `projects/` and `.worktrees/` are gitignored and absent. These are *claims*, internally consistent with the code and commits, but not corroborated by evidence in the repository.

---

## 6. Portfolio credibility and authorship risk

**Generated-code smell: present, and not automatically disqualifying here.** Day one produced 16 commits and ~2,000 lines in four hours, including a 612-line commit ("P0 slice 4: provider-abstracted LLM seam + real Builder agent"). Commit messages run to 150+ words in polished, uniform prose. Docstrings account for 15% of runtime source. This pattern is consistent with heavy AI-assisted authorship. Since the project *is* an AI-orchestration system whose stated purpose is to build software autonomously, using AI to build it is thematically coherent rather than hypocritical — but the panel must not confuse "produced" with "understood".

**What argues *for* real understanding.** The 9–13 June commits are qualitatively different from the day-one burst: small (1–5 files), surgical, each naming a specific observed failure with a date, and each landing with a named test that exists and passes. `4597f28` fixes a bug where the project monitor resurrected seven abandoned projects within minutes, and explains the exact causal chain (cancellation changed the signature → evaluation found gates unmet → the stall path re-spawned work). `42813f4` documents an agent editing the very gate that was blocking it. `beb01ca` mutes notifications because the boot self-test's fixtures rang a real phone. You do not get this material from prompting; you get it from running the thing overnight and reading the wreckage.

**What argues *against*, or at least demands verification.** The stale docstrings are the tell. `agents/judge.py:3` still says "the registry assigns it to openai/codex"; `registry/agents.py:39` still says "Judge runs on a DIFFERENT PROVIDER from the Builder"; `control/project.py:8` still describes a `user` gate that `validation/gates.py:17` removed; `run_forever.sh` still says the judge runs on codex; `tests/test_llm_ollama.py:105` asserts the judge is on Claude under a comment reading `# F5 + zero marginal cost` — where Claude-judging is the *negation* of F5. A person carrying the whole model in their head does not leave four contradictory statements of the same fact. A person shipping fast with a generative assistant does.

**Excessive documentation.** ~2,500 lines of planning docs (vision, literature review, architecture, risk register, enforcement spec, decision registry, a 238-line architecture Q&A, a governance corpus). I spot-checked `11_ARCHITECTURE_QA.md` §A against the code and it is accurate. But the volume risks reading as ceremony, and ~3,400 lines of `docs/planning/port/v1/*.py` are explicitly **donor material from a predecessor system** (`PORT_LEDGER.md`) — inert, imported by nothing, and must not be credited as this project's engineering.

**Missing demonstrations — the credibility gap.** There is no artefact a reviewer can run to see the system work. `scripts/demo_e2e.py` — described in its own commit as the "full-stack e2e integration demo" — crashes:

```
AttributeError: 'ProjectOutcome' object has no attribute 'pending_user'
```

The field was renamed to `complete` in the 9 June checkpoint and the demo was never updated; no test covers it. With a one-line fix it runs, but its narrative is now wrong too: it prints `acceptance: False` and `pending_user=False`, so the "gated, hardened, parked for the user" happy path it advertises no longer happens (correctly — the D25 gate refuses the undeclared fixture). There are no screenshots, no captured runs, no committed sample event log, no CI badge.

**What would make me doubt understanding.** If the candidate cannot, unprompted: explain why illegal transitions are no-ops rather than exceptions and what that costs; explain what `base_state` is for and why an unchanged fingerprint must refuse rather than retry; explain why only `invoke` runs on worker threads; or say out loud that F5 is currently suspended and why.

---

## 7. Red flags and weaknesses, ranked by hiring significance

**Real engineering defects**

1. **Planner-emitted dependency cycles strand a project permanently and silently.** Demonstrated (§4). No graph validation, no liveness guard for project graphs, no alarm. Directly contradicts the system's central promise.
2. **Unbounded per-cycle log replay.** `failure_causes()` and `last_results()` re-read the whole event log on every daemon cycle (`control/daemon.py:129, :518`). No compaction, no snapshot, no index. A system designed to run for days degrades linearly and then some.
3. **A headline regression test is a proven false positive** (`test_mock_path_is_refused`), and the ledger presents it as the fix for a real incident.
4. **The assurance ladder fails open.** `validation/assurance.py:105-106` returns `GateResult(name, True, "tier skipped (error)")` on any exception. The ladder that is supposed to *block* self-certification silently passes a tier during a provider outage — in a system that self-certifies with no human gate.
5. **Supervisor has no crash-loop backoff or failure budget.** A red boot self-test yields relaunch-plus-notify every 5 s indefinitely. `run_forever.sh` also defaults the L6 budget cap to $1,000,000.
6. **Enforcement is runtime-only, not merge-time.** No CI exists. `scripts/check.sh` is manual. Two of the laws (L2 layering, L9 quarantine) are enforced *only* by `lint-imports`, which the boot self-test does not run — so the "no-bypass" boot gate covers pytest-linked laws only.
7. **`atomic_io` durability is one step short**: no parent-directory `fsync` after `os.replace`; no test pins the atomicity property (M16 missed).
8. **L9R self-mod fence runs `git checkout -- .` on the orchestrator tree** (`infra/worktree.py:151`), which will revert an operator's uncommitted work. The author documents this ("operator caveat") and a commit records it happening twice. Honest, but a production system should not have a destructive path that fires on ambiguity.

**Portfolio presentation problems**

9. **`README.md` untouched since commit 1** — describes an empty skeleton, contains a broken relative path to a non-existent sibling directory, and states "Next: the P0 milestone". This is the first thing every reviewer reads.
10. **The flagship demo is broken.** One-line `AttributeError`, plus a stale narrative.
11. **Systemic doc/code drift** on at least six load-bearing facts (F5 independence, the human gate, the judge provider, test count, pulse cadence, judge model in the launcher).
12. **All operational evidence is unverifiable** — `state/` gitignored, no committed run artefacts, no exported scorecard output.
13. **Authorship velocity** raises attribution questions the artifact cannot answer.

---

## 8. Interview plan

1. **Live, in the repo:** "Show me why a project with a dependency cycle never terminates. Then fix it." *(Tests ownership of `is_ready`/`_all_terminal`/`monitor_projects` and whether they can reason about liveness, not just safety.)*
2. **Whiteboard:** "Walk me through what happens between `repo.claim_next()` returning a task and `settle()` being called, naming which thread each step runs on and why." *(`control/pool.py` is the strongest work in the repo; they must own it.)*
3. "`test_mock_path_is_refused` passes even with `_MOCK_TELL` disabled. Show me why, then rewrite it so it fails." *(Do they recognise a false positive when shown one?)*
4. "Explain `_input_fingerprint`. Why `sort_keys=True`? Why exclude `workdir`? What breaks if `base_state` is empty? Why is refusing cheaper than re-failing?" *(BG-3 is the most original mechanism; it should be effortless.)*
5. "`core/state_machine.py` makes illegal transitions silent no-ops. Argue the other side — what does that design cost you, and where in this codebase would a silent no-op hide a bug?" *(A strong answer reaches fixpoint loops like `propagate_prerequisite_failures`, which has no progress guard.)*
6. "`AGENT_MODELS` puts builder, tester, judge and task_manager all on Claude, but three docstrings say the judge is cross-provider. Which is true today, why did it change, and what did you lose?" *(Tests whether they track their own system's state or recite its brochure.)*
7. "Your daemon calls `repo.failure_causes()` every cycle, which re-reads the whole log. Your own ledger describes a run with 1,688 agent runs. Design the fix." *(Compaction, snapshotting, incremental fold, or an in-memory index — any coherent answer is fine; not seeing the problem is not.)*
8. "`llm_tier` returns `passed=True` when the provider call throws. The system self-certifies with no human gate. Defend that, or change it." *(Fail-open vs fail-closed reasoning under an explicit threat model.)*
9. **Live:** "`scripts/demo_e2e.py` crashes. Fix it, and make it prove the happy path end-to-end under the current D25 acceptance gate." *(Twenty minutes; tests whether they can navigate their own system under mild pressure.)*
10. "Take me through the 12 June self-modification incident: what the builder did, why the fence exists, what `git checkout -- .` costs you, and what you would build instead if this ran on someone else's machine."

---

## 9. Hiring recommendation by target

| Target | Verdict | Reasoning |
|---|---|---|
| **Graduate / junior** | **Interview — but mis-levelled** | Scope, design vocabulary and assurance discipline are far beyond graduate work. Hiring at this level would be a mistake for both parties. If the answers in §8 are weak, this is *not* a fallback level; it would instead indicate the artifact substantially outruns the author. |
| **Mid-level (SWE II)** | **Interview — likely hire** | The demonstrated floor already clears mid-level comfortably: clean modules, injectable seams, meaningful tests, zero dead imports, laws that hold under adversarial mutation. The defects found (broken demo, stale README, one false-positive test) are typical mid-level polish gaps, not conceptual ones. |
| **Senior** | **Interview — do not pre-commit** | The *design instincts* are senior: enforced boundaries, event sourcing with a replay-equivalence proof, a correctly-argued concurrency model, durable restart-proof budgets, explicit fail-open/fail-closed reasoning. The *engineering discipline* is not yet senior: no CI, a silent liveness hole in the core promise, an unbounded per-cycle scan, six load-bearing documentation contradictions, and a broken flagship demo. Senior requires that §8 questions 1, 2, 4 and 7 are answered fluently and unaided. |
| **AI / agent specialist** | **Interview — strongest fit** | This is the standout. Almost every portfolio in this space is a prompt-chaining demo; this one treats the model as an unreliable subprocess behind a seam and spends its engineering on *what happens when the model is wrong*: anti-collusion test authorship, a stub-detecting authenticity gate, acceptance-by-execution, real mutation testing, a cheap local pre-screen in front of an expensive persistent agent, a bounded durable "mind on disk", and guardrails preventing the meta-agent from targeting reserved projects or the orchestrator itself (M17 caught). Very few candidates have thought this hard about agent containment. |
| **Backend / platform** | **Interview — solid** | Event sourcing, atomic IO, pid-locking with a correct Windows liveness probe, graceful drain, worktree isolation with a merge-conflict path, a durable circuit breaker, a stdlib-only authenticated control surface. Deductions for no CI, no packaging, no metrics/tracing beyond a JSONL log, no compaction, and a supervisor without backoff. |

---

## 10. Scorecard (0–10)

| Dimension | Score | Justification |
|---|---:|---|
| **Engineering depth** | **8** | Real, verified mechanisms rather than vocabulary: replay-equivalence proven under concurrency, restart-proof budgets, canonical input fingerprints refusing deterministic retries, a boot gate derived from the constitution and executed live (91 checks). Depth is confirmed by adversarial mutation, not by reading. |
| **System design** | **8** | Coherent single thesis; layering enforced and verified true; concurrency model correctly reasoned and correctly implemented; sensible trade-offs stated in prose *and* honoured in code. Deducted for the cycle-stall liveness hole and the absence of any compaction strategy. |
| **Code quality** | **7** | Small single-purpose modules, consistent naming, injectable seams throughout, zero unused imports, no raw file writes outside the sanctioned writer. Deducted for four overlapping JSON extractors, duplicated JSONL reading and LOC constant, and stale docstrings on load-bearing facts. |
| **Testing and assurance** | **7** | 335 hermetic tests in 3.2 s; behavioural not mock-shaped; bound assertions; a genuine property test for replay; 16/18 injected defects caught. Deducted for one proven false-positive test on a headline behaviour, one law-check that ends in `assert True`, no atomicity test, and no coverage measurement. |
| **Reliability / operability** | **6** | Strong crash-recovery story: pid lock, orphan reclaim, transient revival, graceful drain, deadline self-stop, durable burn breaker, quarantine-not-destroy. Undermined by the silent project stall, the unbounded per-cycle log scan, a supervisor with no backoff, a $1M default budget, and an assurance tier that fails open. |
| **Documentation** | **5** | Internally, the design docs are genuinely good and I verified `11_ARCHITECTURE_QA` against the code. Externally it fails where it matters most: the README is frozen at commit one with a broken path, and at least six statements across code and docs contradict the implementation. Documentation that misleads scores worse than documentation that is absent. |
| **Originality** | **8** | The synthesis is distinctive and I have not seen it assembled this way: laws-as-data each bound to an executable check, a boot self-test that refuses to dispatch on a red constitution, input-fingerprint refusal of identical deterministic re-attempts, an immutable-CORE + evolvable-EXTRA succession handoff, a persistent mind on disk with the provider session demoted to cache, and a cheap local screen gating an expensive persistent agent. Not a tutorial derivative. |
| **Commercial readiness** | **4** | Single-operator personal system. No CI, no packaging, no dependency pinning, no observability beyond JSONL and a phone ping, one shared bearer token and no TLS, no multi-tenancy, known liveness gaps, and a self-modification fence that can revert an operator's uncommitted work. Appropriate for its stated purpose; not deployable for anyone else. |
| **Portfolio clarity** | **4** | The artifact actively under-sells itself. A reviewer's first screen says "empty skeleton, next: P0"; the one runnable proof crashes; nothing shows the system working. I had to write a test harness and inject eighteen defects to discover how good it is — an employer will not. |
| **Overall hire confidence** | **7** | High confidence that this person builds ambitious systems with real mechanisms and can be shown to be right by experiment. Moderate uncertainty about how much of the artifact they own in depth, driven by day-one velocity and systemic doc drift. The interview in §8 resolves that in ninety minutes. |

---

## 11. Highest-return portfolio improvements

1. **Rewrite `README.md`.** Highest return by a wide margin. Current state, one architecture diagram, the verified numbers (335 tests / 3.2 s / 16-of-18 mutants caught), a 60-second quickstart, and the honest limitations. Delete the broken `../claude-orchestrator-main/` reference.
2. **Fix `scripts/demo_e2e.py`, add an acceptance declaration to its fixtures so the happy path genuinely passes, and cover it with a test** so it can never silently rot again. Commit its output as `docs/DEMO_OUTPUT.md`.
3. **Close the liveness hole**: validate the planner's returned graph (reject cycles and dangling dependencies), and add a per-project staleness guard so a non-terminal project that has made no progress for N cycles alarms and escalates. This turns the biggest defect into the biggest talking point.
4. **Add CI** (`.github/workflows/gates.yml` running `ruff` + `lint-imports` + `pytest`) and put the badge in the README. "A law without a machine-check is a wish" currently has no build to fail.
5. **Publish the negative-control evidence.** Commit a `docs/ASSURANCE.md` with a reproducible mutation-battery script and its results table. Almost nobody does this; it is the single most persuasive artefact in the repository and it is currently absent.
6. **Reconcile the six documentation contradictions** in one pass — F5 suspension, the removed human gate, the judge provider (code, docstrings, `run_forever.sh`), and the test count — and fix `test_mock_path_is_refused` so the ledger's claim becomes true.
7. **Commit a redacted sample `state/tasks.events.log`** plus `python -m control.scorecard` output. It converts the entire `RUN_LEDGER` from assertion to evidence at near-zero cost.

---

## 12. Evidence appendix

**Commit inspected:** `32efb0797905078a6917d748ce93efd46f7527be` — *"daemon: exclude .git and vcs/build dirs from the project file list fed to agents"*, Artiom `<gutu.artiom444@gmail.com>`, Sat 13 Jun 2026 23:10:08 +0100.

**Git state:** detached HEAD at `32efb07`; branches `main`, `origin/main`, `origin/feature/local-llm`; working tree clean; 71 commits; single author and committer throughout; no co-author or generated-with trailers; 4 commits with author≠commit date; active days 1–2 and 9–13 June 2026 (17/6/11/11/8/10/8 commits per day).

**Size:** 5,964 lines runtime Python across 12 packages; 4,391 lines of tests (335 test functions in 54 files); ~2,511 lines of Markdown docs; ~3,400 lines of inert v1 donor code under `docs/planning/port/v1/` (imported by nothing — verified). Prose density in runtime source: 3% comments, 15% docstrings.

**Environment constraint and how it was handled.** `pytest`, `ruff` and `import-linter` were not installed and network installation was prohibited. `/workspace` is read-only, so the repository was copied to `/tmp/eval/repo` (`git status` clean, HEAD verified). I wrote a minimal pytest-compatible shim at `/tmp/eval/shim/` implementing exactly the API surface these tests use (`fixture`, `raises`, `mark.skipif`, `tmp_path`, `monkeypatch`, `PYTEST_CURRENT_TEST`, `--collect-only`, `-k`, `N passed` summary). Fidelity evidence: it collected and executed all 335 defined `test_*` functions (matching `grep -c "^def test_"`), produced sensible per-file failure counts under 18 injected mutations, and satisfied `control/self_test.py`'s own collect-then-run-then-parse-count protocol. **Results should be read as strong but not identical to a real pytest run.**

**Commands run and outcomes:**

```bash
# Baseline (repeated 3×, identical)
cd /tmp/eval/repo && PYTHONPATH=/tmp/eval/shim:/tmp/eval/repo python3 -m pytest tests/ -q
  -> 335 passed        elapsed 3217 ms       exit 0

# Real boot-self-test code path
python3 -c "from control.self_test import run_boot_self_test; print(run_boot_self_test(Path('.')))"
  -> True | 91 law-linked checks passed (17 files)

# Independent verification of the import contracts (AST, not import-linter)
  -> L2 layering violations: 0 | registry-leaf violations: 0 | selfdev-import violations: 0

# Independent verification of law L7 (raw-write scan of all runtime packages)
  -> raw open(w/a) / write_text / unlink / rmtree found ONLY in infra/atomic_io.py

# RUN_LEDGER §3 corroboration
  -> all 13 named regression tests exist in the named files and pass

# Negative-control battery (18 mutations, targeted subsets, tree restored after each)
  -> 16 CAUGHT, 2 MISSED (M6 mock-path refusal, M16 atomic-write property)
  -> tree verified pristine afterwards (git status --porcelain empty)

# Demonstrated defects
scripts/demo_e2e.py            -> AttributeError: 'ProjectOutcome' object has no attribute 'pending_user'
  (one-line patch applied in /tmp only -> runs to completion, prints acceptance:False, pending_user:False)
dependency-cycle probe         -> both tasks QUEUED forever; _all_terminal False; monitor_projects returns []
test_mock_path_is_refused      -> passes identically with the _MOCK_TELL guard disabled (detail text shown in §5)

# Static hygiene
unused-import AST scan         -> 0 genuine findings (1 false positive: `from __future__ import annotations`)
secret scan                    -> no hardcoded credentials
CI configuration               -> none present (.github, Makefile, tox.ini, noxfile.py all absent)
```

**Important files inspected in full:** `charter/laws.py`, `core/state_machine.py`, `core/models.py`, `infra/{atomic_io,event_store,llm,worktree,notify,pidlock,triage}.py`, `dispatch/{repository,dispatcher,runner}.py`, `control/{daemon,pool,budget,breadth,project,self_test,prescreen,operator_chat,scorecard}.py`, `validation/{gates,authenticity,mutation,acceptance_exec,assurance}.py`, `agents/{common,judge,overseer,task_manager}.py`, `memory/overseer.py`, `registry/agents.py`, `edge/server.py` (partial), `run_forever.sh`, `scripts/{demo_e2e,demo_project,check.sh}`, `tests/{test_failure_budgets,test_acceptance_exec,test_soak,test_judge,test_llm_ollama,test_dispatcher}.py`, all of `tests/architecture/`, `README.md`, `CLAUDE.md`, `docs/QUALITY_CHARTER.md`, `docs/planning/{RUN_LEDGER,11_ARCHITECTURE_QA,port/PORT_LEDGER}.md`, `pyproject.toml`, `.gitignore`, `.claude/skills/*`.

**Limitations — stated as UNKNOWN rather than guessed:**
- Real `pytest`, `ruff` and `import-linter` were never executed; layering and lint were verified by independent means, but exact tool output is **UNKNOWN**.
- No provider was contacted. All LLM integration (`claude` / `codex` / `ollama` paths, session resume, `--dangerously-skip-permissions` behaviour) was exercised only through injected fakes. Whether the parsers match current real CLI output today is **UNKNOWN**.
- `state/`, `projects/` and `.worktrees/` are gitignored and absent. Every operational figure in `RUN_LEDGER.md` — the 115/1,573 run split, the 90× conflict oscillator, eight wedged repos, eleven silent hours, the Codex doormat incident — is **UNVERIFIED**. It is internally consistent with the code and commit history, and the 13 named regression tests it cites all exist, but the underlying runs cannot be corroborated from this artifact.
- Whether the system has ever certified a real project end-to-end with live agents is **UNKNOWN**; nothing in the repository demonstrates it.
- Authorship attribution between the candidate and AI tooling is **UNKNOWN** and, in my judgement, is the single question the interview must resolve.
- One mid-review anomaly was diagnosed as an artifact of my own harness, not the repository: a leftover mutation left `core/state_machine.py` broken, which caused `propagate_prerequisite_failures` to spin and fill a 3.9 GB tmpfs with a single 3.7 GB event log. **The repository is not responsible for that**; it is noted only because it incidentally revealed that the fixpoint loop has no progress guard — a latent fragility of the deliberate "illegal transitions are silent no-ops" design, worth raising in interview but not counted as a defect against HEAD.