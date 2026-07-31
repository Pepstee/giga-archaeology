# Employer Verdict

This is the strongest solo portfolio artifact I would expect to see for a senior backend/platform or agentic-systems role, and — unusually — most of its headline claims survive independent falsification. I did not take the README on faith: I ran real multi-process and multi-thread contention against the event log, tore a JSONL line inside a multi-byte codepoint, simulated `ENOSPC` on the append path, planted architecture-law violations into shipped modules, forged an isolation receipt with a recomputed integrity hash, and planted seven shapes of placeholder code into a real source file. Every one of those mechanisms behaved exactly as documented. That is rare; the usual portfolio failure mode is a confident README over a hollow tree, and this is not that. The serious caveats are three. First, **authorship is genuinely ambiguous**: 728 of 809 commits are authored by `orchestrator <orchestrator@local>` — the system committing its own output — accounting for ~48k of the ~69k added Python lines, over a 14-day window. That is the project's *thesis*, not a deception, but it means the interview must establish which parts the candidate can derive from scratch rather than recognise. Second, **the most impressive claims are the least verifiable**: the live GPT-only factory runs, token-reduction percentages and 3,566-test suite results in `docs/efficiency/` have no checked-in receipts, because `state/` and `projects/` are gitignored. Third, there are **real defects a reviewer will find**: one test cannot pass on a clean clone, the dashboard accepts a cookie as auth for state-changing POSTs with no CSRF defence, there is no CI, no declared dependencies, and no licence. Interview at senior level; do not hire sight-unseen at any level until the live exercises below are passed.

---

# 1. Sixty-Second Screening Impression

**Recruiter (30 seconds, skims README):** Impressive-sounding and immediately intimidating. "Event-sourced," "crash-safe," "total state machine," "fail-closed," "certification." No screenshot, no demo GIF, no licence, no CI badge, no one-line "what is this for." The README is ~280 dense lines with sentences running 6+ clauses. A recruiter will either forward it as "looks serious" or bounce off it entirely. **Portfolio presentation is the weakest link relative to the engineering.**

**Engineering manager (60 seconds, opens the tree):** Fourteen top-level packages, 338 Python files, 65k lines, 243 test files. Instantly reads as either exceptional or over-engineered. Then `git shortlog`: 728 commits by `orchestrator@local`, 81 by a human, over 14 days. That is the moment the EM's question changes from "is this good?" to "**who wrote this, and what does the candidate actually understand?**" Everything downstream hinges on that. To their credit the candidate did not hide it — the author identity is right there in the log and the whole project is *about* machine-authored code.

**Senior engineer (60 seconds, opens `infra/atomic_io.py` and `infra/event_store.py`):** Immediately recognises non-tutorial work. The `flock` is taken on the **parent directory**, not the file, with a correct justification (opening the file with `O_CREAT` would create it and silently skip the first-creation directory fsync). `read_jsonl` decodes with `errors="replace"` specifically because a strict decode raises out of the *line iterator*, past the `JSONDecodeError` handler. `int_seq` excludes `bool` because `isinstance(True, int)`. `_last_seq` refuses to trust the tail unless the window *witnesses* two strictly-increasing records. This is someone who has been bitten by real durability bugs — or is extremely good at reproducing the reasoning of someone who has. The senior engineer's next move is exactly mine: try to break it.

---

# 2. What This Proves — Concrete, Independently Verified

Everything in this section I executed myself against a `/tmp` copy. Commands and outputs are in the appendix.

### 2.1 The durability core is real, not narrated

**Cross-process seq serialization** (`infra/event_store.py:148-159`, `infra/atomic_io.py:120-146`). I ran 8 genuine OS processes × 40 appends against one log:

```
8 REAL OS processes x 40 appends all landed | got 320
seqs distinct & gapless 0..319 | dupes=0
6 threads x 50 appends: 300 records | gapless 0..299: True
```

The critical design point is that the lock spans the *read of last-seq* through the durable write, not just the write — two processes on a cached in-memory seq would both compute the same next value. The code comment says this; the test proves it.

**Torn-line tolerance including mid-codepoint tears** (`infra/atomic_io.py:164-181`). I wrote a record containing `héllo—wörld ✅`, truncated 4 bytes to land inside the emoji, and replayed:

```
torn mid-codepoint: replay does not raise | 1 survived
append-after-tear: intact 'a' + new 'c' both readable | ['a', 'c']
append-after-tear: seqs distinct | [0, 1]
```

The `_ends_mid_line` repair (`atomic_io.py:109-117,155`) prevents the next append concatenating onto the torn line and losing both.

**Foreign-record resistance in the tail scan** (`infra/event_store.py:68-140`). I spliced a valid-but-lower `seq: 1` record at EOF after 5 real events:

```
foreign lower-seq at tail -> next seq = true max+1 (5) | got 5
```

The fast path correctly declined to trust the rightmost record and fell back to `_full_scan_last_seq`. The docstring even states the residual assumption honestly: contamination that fabricates a strictly-increasing run spanning the *entire* window is indistinguishable without a full scan. **Stating the limit of your own guarantee is a senior habit.**

**Log-first ordering under append failure** — the claim I most expected to fail. I subclassed `EventStore` to raise `OSError(ENOSPC)` on append:

```
append failed as expected: [Errno 28] No space left on device
live in-memory status after failed append: in_progress
replayed status:                           in_progress
LOG-FIRST HOLDS: True
failed create left task in memory? False | live repo has t2: False
```

Live process state never diverged from what replay reconstructs. This is the invariant most event-sourcing toy projects get wrong.

### 2.2 Create-time integrity refuses corruption *before* the log sees it

`dispatch/repository.py:275-314` + `core/models.py:46-97`. All seven refusals raised `ValueError` and **wrote nothing**:

```
create refuses duplicate id / self dependency / priority='1' /
       unhashable project / depends_on str / payload non-dict / cycle d->e->d
refusals wrote NOTHING to the log | log grew by 1 (only 'e' legit)
```

The `validate_engine_fields` docstring (`core/models.py:47-79`) is the single best piece of writing in the repository: it derives the guarded field list from **what the engine actually does to each field** (`project` is counted in a `Counter` → must be hashable; `last_reason` is a dict key in two grouping sites; `acceptance_criteria` is joined into a prompt, where a bare `str` "silently shreds into one bullet per character") rather than from the dataclass annotations, and explicitly names the earlier bug — "Enumerating only the fields that looked engine-ish is what left project out before." That is a real post-mortem, not decoration.

### 2.3 The BLOCKED lifecycle is order-independent and transitive — proven, not asserted

`dispatch/repository.py:799-866`. I built a 4-link chain `r→a→b→c`, failed the root, and ran **one** `claim_next()`:

```
one claim cycle blocks the WHOLE chain (a,b,c)
each link names its OWN stuck dependency:
  {"a": "dependency 'r' failed",
   "b": "dependency 'a' is blocked",
   "c": "dependency 'b' is blocked"}
one claim cycle releases the whole chain
blocked/unblocked lifecycle survives replay
```

Both sweeps run to a fixpoint and run *before* selection, ignoring the concurrency cap — so a stuck task at depth ≥2 cannot starve silently while healthy work flows. The dirty-flag optimisation is measurably effective: 200 `claim_next()` calls over a 1000-task queue produced **21 sweeps / 179 skips** in 66ms.

### 2.4 The architecture laws are executable, with working positive *and* negative controls

This is the part most portfolios fake. `tests/architecture/test_file_preservation.py` and `test_layering.py` are real AST walks, not regex. I ran both against the clean tree and then against a copy with planted violations:

```
clean L7: []                        (89 shipped files scanned)
clean L2: []                        (93 modules walked)
planted -> L7 violations found: ['dispatch/dispatcher.py: Path.replace']
planted -> L2 violations found: [('infra/triage.py', ['dispatch'])]
```

Both scanners named the exact planted location. More importantly, `test_file_preservation.py:225-251` (`test_required_evasions_are_all_caught`) pins a **hand-written** list of ways to destroy the event log that is *deliberately not derived from the `MUTATORS` catalogue* — with a docstring explaining that the previous control asserted `set(offenders) == set(FORBIDDEN)` and therefore "was green because it was blind." The arity discrimination (`Path.replace(target)` takes one arg, `str.replace(old,new)` takes two) is the correct way to be exhaustive without false-positiving ordinary string handling — and `test_negative_control_innocent_homonyms_are_not_flagged` proves it.

Directly executed, no pytest: **30 architecture assertions passed**; 8 "failures" were all missing `git`/`ruff` in my sandbox copy.

### 2.5 The isolation boundary certifies against *this machine* and fails closed on every tamper

`dispatch/isolation.py`. `bwrap` was present, so I ran the real thing:

```
$ python3 -m dispatch.isolation certify --root "$PWD"
certified linux-bubblewrap; receipt e769c1ec7021f787...
drills: {allowed_write: true, forbidden_write: true, forbidden_signal: true,
         forbidden_network: true, shipped_agent: true}
```

These are genuine drills (`isolation.py:384-470`): write inside the worktree, write outside (must fail), `SIGTERM` an external PID (must fail), network, and a real shipped-agent subprocess. Then I attacked the receipt:

| Tamper | Result |
|---|---|
| flip a drill to `false` | REFUSE — integrity hash mismatch |
| flip a drill **and recompute the hash** | REFUSE — required drill not passing |
| spoof kernel release | REFUSE — hash mismatch |
| edit `dispatch/runner.py` (a boundary file) | REFUSE — implementation changed since certification |
| `config.enabled=false` | REFUSE — not explicitly enabled |
| delete receipt | REFUSE — unavailable |

The receipt binds machine identity, the executable's SHA-256, and a digest over five named boundary files — and `_certify_isolation` **disables first**, so an interrupted recertification cannot leave an older receipt live. `control/daemon.py:127-134` raises `BootRefusal` before ingest or claim if this fails. Verified fail-closed.

### 2.6 The authenticity gate is original work and it actually works

`validation/authenticity.py` (735 lines) scans shipped source for placeholder markers, assembling its own vocabulary from fragments at runtime **so the scanner is not exempt from its own sweep**. I planted seven shapes into a real module:

```
CAUGHT  TODO marker in a comment
CAUGHT  hollow function (pass body)
CAUGHT  ellipsis body
CAUGHT  NotImplementedError stub
CAUGHT  facade identifier (class DummyRunner)
CAUGHT  fake abstractmethod exemption (no ABC base)
CAUGHT  rebound exemption word (abstractmethod = lambda f: f)
clean   legitimate ABC + @abstractmethod  -> passed=True   (no false positive)
```

The last two are the interesting ones: `@abstractmethod` on a class with no abstract base is a runtime no-op, so it earns no exemption; and a file that rebinds `abstractmethod` loses the exemption in that file. The module's docstring states this cost honestly — "ten rounds of this gate's history so far, each finding one more shape the previous version could not see." I have not seen this mechanism elsewhere.

### 2.7 The E2E tests are real, not in-process theatre

`tests/test_daemon_e2e_sigkill_resume.py` spawns the daemon harness as a genuine `subprocess.Popen`, seeds work **only** by dropping JSON into the real inbox directory, sends real `SIGKILL`, confirms death via `os.waitpid` (`WNOHANG`-polled, not a fixed sleep), boots a second independent process against the same state dir, and asserts against a brand-new `TaskRepository.replay(EventStore(...))`. Nothing from the killed process's `Popen` object decides pass/fail. `tests/test_project_completion.py` failed under my shim precisely *because* the tests gate shells out to real `pytest`, which is absent — that failure is itself evidence the gate is not mocked.

### 2.8 Commits that show real defect hunting

The human commits are the strongest authorship signal available. `4cad325` ("Close two adversarial defects") reads:

> `settle()` passed agent-supplied `kind`/`body` through untyped… so a list kind or int body raised `TypeError`/`AttributeError` — neither an `InvalidEntry`, so both escaped `settle()`'s `except InvalidEntry`, against its own docstring. Nothing was logged, so the task wedged `IN_PROGRESS`, replay could not recover it, and `reclaim_orphans` re-queued and re-crashed it on every boot… **Both pinned by tests that fail on the pre-fix code (33 of 61 red against stashed source).**

Tracing a type leak to a permanent boot-crash loop, *and* verifying the new tests are non-vacuous against stashed source, is exactly the discipline you want. `62081d6` unifies a `bool`-vs-`int` guard into a single `int_seq` definition shared by store and repository — a class fix, not a spot fix. `33a5192` is titled "Fix four agent-seam defects a green suite could not see."

---

# 3. Architecture and Implementation Assessment

**Coherence — strong.** One idea runs through everything: *durable log is the truth; memory is a cache; every gate fails closed.* The layer order in `pyproject.toml [tool.importlinter]` is mirrored and machine-checked inside the suite (`test_layering.py`), with the scope discovered **from disk, not from the layer list** — so a package that escapes the contract by not being listed is flagged rather than silently unenforced (`test_every_shipped_package_is_a_declared_layer`). An undeclared package is ranked innermost so it fails closed. That is careful.

**Boundaries — mostly clean, one soft spot.** Layer discipline is verified across 93 modules with zero violations. The agent wire protocol (`agents/common.py`) is minimal and correct: one JSON payload in, exactly one `AgentResult` line out, and a handler exception is converted into a caused `ok=false` result rather than leaking a traceback onto stdout. The seam that concerns me is `control/scoped_completion.py` at **1002 lines** — by far the largest module, and the one place the "small module, one job" discipline visibly frays.

**Determinism — good, with a disclosed compromise.** `tests/conftest.py` installs an **autouse** fixture that replaces `runner._resolve_isolation` with a passthrough executable for the *entire* suite. This is disclosed in the docstring and the README, and the dedicated certification tests override it — but it means "agents run isolated" is proven by a handful of drills and by my live `bwrap` run, not by the 2,355-test suite. That is the right trade-off, honestly labelled, and it should be stated in interview rather than discovered.

**Persistence — the strongest area.** Append-only JSONL, tolerant reader, snapshot compaction with a **log-identity anchor**: `_load_valid_snapshot` (`repository.py:40-64`) rejects a snapshot whose `seq` is present in the current log but whose event at that seq has a different `ts` — catching the replaced-log case that a naive `seq <= log_head` check waves through. I verified this: a snapshot taken over a deleted-and-recreated log produced `{'new'}`, no phantom `old`.

**Concurrency — correct where it is claimed, inconsistent where it is not.** `EventStore.append` is properly serialized. But `infra/usage_log.py:25` and `graph/store.py:160,173` call `append_jsonl` **without** `locked()`. Records are short so `O_APPEND` is effectively atomic on POSIX, but the `_ends_mid_line` read-then-write repair is a TOCTOU under contention. Low severity; inconsistent discipline. The lock is also taken on the *parent directory*, so every writer under `state/` contends on one lock — correctness-safe, coarse, and a fine interview question.

**Failure handling — genuinely fail-closed.** `control/self_test.py` is the model: no bypass flag (asserted absent by an architecture test), a hang/spawn-failure/`ValueError` folded into a refusal rather than an escaping exception (`_run_checked`), and `_uncollected` anchoring node-id matching per line with `path::` — because a path that is a suffix-substring of another law-linked path would otherwise read as "collected" on the strength of a *different* file's node ids, letting a law whose check file was emptied pass the gate. That is a subtle vacuity hole, found and closed.

**Model integration — specific and credible.** `infra/llm.py` (738 lines) shells out to real provider CLIs with correct, non-generic flags: `--dangerously-skip-permissions` (with a comment explaining that without it `-p` denies file-editing tools and the builder reports "a cheerful 'wrote 0 file(s)'"), `--safe-mode`, `--strict-mcp-config`, and a Codex config block setting `project_doc_max_bytes=0` so repository `AGENTS.md`/`CLAUDE.md` cannot conflict with the task contract. There is a tool-call budget enforced by streaming the Codex event protocol and killing on breach (`_run_with_tool_budget`), typed exceptions (`ResumeFailed`, `LocalRuntimeUnavailable`, `ToolBudgetExceeded`), and token-usage parsing. Prompt-injection defence is real: `infra/prompt_safety.py` neutralises `<` **wholesale** rather than escaping the exact delimiter spelling, so no case/whitespace/attribute variant can forge a close tag — and `tests/test_injection_drill.py` drives a hostile corpus document with a forged `</CORPUS-DATA>` reopen through the *real* `CorpusStore → build_prompt` path (7 tests, all passing). I cannot verify every CLI flag exists without network: **UNKNOWN**.

**Operability — the weakest dimension.** No CI configuration of any kind (no `.github/`, no Makefile, no Dockerfile). `pyproject.toml` declares **zero dependencies** — yet `control/self_test.py` hard-requires `pytest` to boot, so a fresh `pip install -e .` produces a daemon that refuses to start. No licence. No production supervisor CLI (the README concedes this). No structured metrics endpoint beyond the dashboard. POSIX-only by design (`fcntl`). Linux isolation via `--ro-bind / /` means the whole host filesystem is readable inside the sandbox — acknowledged in the README's "Known boundaries," but it means the boundary protects *integrity*, not *confidentiality*.

---

# 4. Code and Assurance Quality

**Maintainability — good.** 15,370 non-blank source lines, 0 syntax errors, consistent stdlib-only style, `from __future__ import annotations` throughout, type hints everywhere. Prose fraction (comments + docstrings ÷ source lines) is **0.18** — high but not absurd; the density is concentrated in the durability core where it is earned.

**Duplication — very low.** AST-hashing 2,055 functions of ≥4 statements found only **4 duplicate groups entirely within source**: `load_connector_manifests`/`_source_dir` shared between `memory/connectors.py` and `memory/corpus.py`, `_checkpoint_touched` between builder and tester, and `_group_blocked_by_reason`/`_blocked_by_reason` between `edge/cli.py` and `edge/server.py`. The last is same-layer and trivially extractable. For a 65k-line tree that is an excellent result and argues against naive mass generation.

**Tests — 2,355 test functions across 243 files, plus 228 `parametrize` decorators.** Only **one** file uses `MagicMock`; 641 uses of `monkeypatch` (explicit seam injection) and 40 files driving real subprocesses. That ratio is the right way round.

What I could execute (via a minimal pytest shim I wrote, since pytest is unavailable offline):

```
top-level unit suite:  1912 passed, 225 failed, 33 skipped
architecture (direct):   30 passed
```

I triaged the failures and **found no genuine product defect among them**. The clusters were: my shim's `capsys` returning empty strings (all `test_cli_*` failures); my shim's `parametrize` unpacking a list case-value as multiple arguments — I re-tested `int_seq` and `last_reason`/`reason` guards directly and both refuse all corrupt inputs correctly; `pytest.param` unimplemented in my shim; and missing `pytest`/`ruff`/`git` binaries in my copy. `test_project_completion` failures traced to the gate genuinely shelling out to real pytest.

**Negative controls — present and unusually rigorous.** Every scanner has both a positive control (each catalogued rule fires) and a negative control (innocent code is clean). `test_file_preservation.py`'s `test_sanctioned_writer_is_real_and_actually_uses_the_primitives` asserts that `atomic_io.py` *itself* still performs the raw I/O it is exempted for — so the exemption cannot go stale. `test_readme_roadmap_accuracy.py` pins forbidden phrases against files that exist on disk, with a "table is not empty" control on the table itself. The candidate has internalised that **a test that cannot fail proves nothing**.

**Does the evidence support the claims?** Overwhelmingly yes for the engine, the laws, the isolation receipt and the authenticity gate. **No** for the live-factory efficiency claims — see §5.

---

# 5. Portfolio Credibility and Authorship Risk

**The authorship split, stated plainly:**

| | Commits | Non-merge Python lines added |
|---|---|---|
| `orchestrator <orchestrator@local>` | 728 (369 non-merge) | **48,190** |
| `Artiom <…>` (human) | 81 | **20,801** |

Span: 2026-07-08 → 2026-07-22 — **14 days** for ~69k added lines. Eighteen of the 81 human commits carry `Co-Authored-By: Claude Opus 4.8` or `Claude Fable 5` trailers. `git blame` on the core: `dispatch/repository.py` 571 orchestrator / 342 human; `core/state_machine.py` 30 / 0; `infra/event_store.py` 167 / 14; `validation/authenticity.py` 489 / 246.

**This is not concealment** — the commit identities are plain, the trailers are disclosed, and a self-building factory is the entire point. But an employer must be clear-eyed: **the candidate's demonstrated contribution is architecture, adversarial review and defect closure, not line-by-line authorship.** That is a legitimate and increasingly valuable skill; it is also a *different* skill from the one most job descriptions describe, and the interview must test which one is present. The human commits are the best evidence, and they are good evidence — but they are hardening passes over a body of code the human did not type.

**Generated-code smell:** low-to-moderate. The tell is not the code — it is the *prose*. Docstrings routinely run 20–40 lines with an argumentative, essay-like register ("Enumerating only the fields that looked engine-ish is what left project out before"; "It was green because it was blind"). Human engineers under deadline do not write like this at this density across 338 files. The *reasoning* is sound and often subtle, so this reads as machine-drafted from genuine human insight rather than as invention — but a reviewer will notice, and the candidate should expect to be asked to explain a docstring they did not write.

**Excessive documentation:** yes, and it works against them. The README is ~280 lines of dense compound sentences; §"What it does, end to end" contains a single 26-line bullet. `docs/efficiency/E6_GPT_ONLY_CERTIFICATION.md` is 250 lines of operational narrative. There is no diagram, no screenshot, no 90-second demo.

**Unverifiable sophistication — the most important credibility issue.** `docs/efficiency/` reports specific numbers: "3,566 passed, 4 skipped in 426.46 seconds"; "75.9% fewer tokens"; "15.4 times faster"; "the index is now 13 owned paths." **None of it is checked in.** `state/` and `projects/` are gitignored; there are no receipts, no logs, no eval-store snapshots. The docs are impressively *honest* — they report the JAA product being **rejected** by its own judge, a 1,200-second timeout, a routing defect found in production, and explicitly caveat that a comparison "establishes the rollout threshold, not a controlled model benchmark" — but honest unverifiable claims are still unverifiable.

**One finding that cuts both ways.** README claims "A live Codex model-routing benchmark is checked in for the judge assignment." I checked `tests/fixtures/eval_store/model_routing_receipts.log` (12 records) and computed inter-record timing:

```
codex:gpt-5.6-terra    (judge):  3 records, mean gap 5.888s   <- consistent with LIVE calls
claude:claude-sonnet-5 (pm/build/test): 9 records, gaps ~0.00015s  <- NOT live LLM calls
```

The README is **precisely accurate** — it says *live* only of the judge assignment, and the judge rows show ~5.9s per call. That is careful, defensible writing and it raises my confidence in the README overall. But `tests/architecture/test_model_change_requires_receipt.py`'s own docstring says the fixture was "produced by the real `validation.benchmark.run_benchmark` … machinery — never hand-written JSON," which is *technically* true (real machinery, stubbed `call`) while reading considerably stronger than the artefact supports. Net effect: the "a model change requires a receipt" law is, for three of four agents, anchored on receipts that were never produced by a real model call. **Fix the docstring, not the README.**

**What would make me doubt understanding:** if the candidate cannot, live, explain why `locked()` opens the parent directory rather than the file; why `read_jsonl` uses `errors="replace"`; why `_last_seq` demands two witnesses before trusting the tail; or why `_uncollected` anchors on `path::`. Those four are the load-bearing insights. If they land, the authorship question resolves favourably regardless of who typed the lines.

---

# 6. Red Flags and Weaknesses, Ranked by Hiring Significance

### Real engineering defects

**1. A test cannot pass on a clean clone.** `tests/test_scoped_assurance.py:184` reads `projects/job-application-automation/IMPLEMENTATION_SLICES.yaml`. `projects/` is gitignored (`.gitignore:11`), nothing under it is tracked, and the test has **no `skipif` guard**. The README's own verification command — `python3 -m pytest tests/ -q` — therefore goes red on a fresh checkout. For a repository whose entire thesis is "the gates are the proof," this is the single most damaging defect: it is the first thing a technical reviewer runs and the first thing that fails. *Highest significance despite being a one-line fix.*

**2. CSRF exposure on state-changing endpoints.** `edge/server.py:318-322` accepts a `token` **cookie** as authentication, and `POST /api/stop`, `/api/confirm`, `/api/correction` are gated only by that check. There is no CSRF token, no `Origin`/`Referer` validation, and no `SameSite` handling anywhere in the module or its tests (`grep` for `SameSite|csrf|Origin|Referer` returns nothing). Any page the operator visits could `POST` to `127.0.0.1` and trip the kill-switch or inject a correction. Loopback binding and a random token limit blast radius, and the constant-time comparison (`secrets.compare_digest`) is correct — but accepting an ambient credential for state change without CSRF defence is textbook, and the module's docstring claims the token "is the *only* auth this module has" as though that settles it. A backend/platform interviewer will find this.

**3. No CI, no declared dependencies, no licence.** Zero `[project.dependencies]` / `[project.optional-dependencies]`, yet `control/self_test.py` hard-requires `pytest` to boot — I reproduced the resulting `BootRefusal: … No module named pytest`. There is no `.github/`, no Makefile, no Dockerfile, no `LICENSE`. Nothing proves the suite is green *right now*, on any machine but the author's.

**4. Live-run evidence is entirely unverifiable.** §5. The most impressive claims in the repository have no checked-in artefacts.

**5. Isolation provides integrity, not confidentiality.** `--ro-bind / /` (`isolation.py:268`) exposes the entire host filesystem read-only to the agent — SSH keys, browser profiles, everything. The README lists this as a known boundary, which is honest, but for an autonomous agent running untrusted model output it is the more interesting half of the threat model.

**6. Minor correctness inconsistencies.** `EventStore._seq` is written in `__init__` and `append` but **never read anywhere** — dead state left over from the pre-lock design. `apply()` validates `reason` *after* the legality check (`repository.py:319-328`), so an illegal transition carrying a corrupt reason silently no-ops rather than raising; defensible (nothing is logged) but it makes the docstring's "the write path must accept only what replay will reconstruct" order-dependent. `usage_log`/`graph` append without the `locked()` discipline `EventStore` uses.

**7. One 1,002-line module.** `control/scoped_completion.py` is 4× the next largest and is where the layering discipline visibly weakens.

### Portfolio presentation problems

**8. Authorship is invisible without git forensics.** No `AUTHORS`, no "what I built vs. what the system built" section. The single highest-leverage fix in the whole repository.

**9. README is impenetrable at speed.** No diagram, no demo, no screenshot, no 3-sentence pitch. Most reviewers will not reach the good parts.

**10. Two commits titled `x`** (`8be14ab`, `5294114`) — cosmetic, but noticed.

**11. Roadmap advertises unfinished scope.** `graph`, `scheduling`, `selfdev` and the research contract ship as skeletons with no production consumer. The README labels them accurately ("future integration", "extension work"), which is to its credit — but their presence inflates the apparent surface area and invites "why is this here?"

---

# 7. Interview Plan

Ten exercises, ordered so the first four resolve the authorship question decisively.

1. **Whiteboard, no notes:** `atomic_io.locked()` takes `flock` on `path.parent`, not on `path`. Give me both reasons. *(Looking for: works whether the file exists yet; and opening `path` with `O_CREAT` would create it before `append_jsonl` sees it, silently skipping the first-creation directory fsync.)*

2. **Live debugging:** I hand you a log whose final line is truncated inside a multi-byte UTF-8 codepoint. Walk me from the raw bytes to `claim_next()` returning a task. Which single line stops this bricking every future boot, and what exception escapes past which handler if you remove it?

3. **Live coding, 25 min:** Implement `_last_seq`'s bounded tail scan from scratch. Then I add a foreign record with a valid lower `seq` at EOF. Make it correct. Then state the residual assumption your fix does *not* cover. *(The repo's own docstring states it; can the candidate rederive it?)*

4. **Design critique of their own code:** `EventStore._seq` is assigned in `__init__` and `append` and read nowhere. Why is it there, and should it be? *(Tests whether they know their own tree or are reading it fresh with me.)*

5. **Extend under constraint, 30 min:** Add `per_agent_cap` alongside `per_project_cap` in `claim_next()`, preserving order-independence, the fixpoint sweeps and the dirty-flag optimisation — and add the test that would have caught you getting it wrong.

6. **Security:** Walk me through `POST /api/stop` from a malicious page the operator has open in another tab. What stops it? *(There is no CSRF defence and a cookie is accepted. I want them to find it, not defend it.)* Then: what changes if `--host 0.0.0.0`?

7. **Assurance judgment:** `tests/conftest.py` replaces `runner._resolve_isolation` autouse for the entire suite. What does the 2,355-test suite therefore *not* prove, and what would you build to close that gap without making every test cost a `bwrap` spawn?

8. **Evidence integrity:** The `claude:claude-sonnet-5` rows in `model_routing_receipts.log` are ~0.15ms apart; the `codex` judge rows are ~5.9s apart. Explain the difference, and tell me whether `test_model_change_requires_receipt.py`'s docstring is accurate. *(A candidate who owns this will answer immediately and correct the docstring.)*

9. **Reproduce on my machine, 20 min, screen-shared:** clone fresh, get `python3 -m pytest tests/ -q` to green. *(They will hit `test_scoped_assurance.py:184` — the untracked YAML — and the missing dependency declarations. I want to watch them diagnose it.)*

10. **Ownership boundary, direct:** Point at the three files you are proudest of. For each: did you write it, did the orchestrator write it and you reviewed it, or did you specify it and accept the output? Then pick one the orchestrator wrote and explain a design decision in it you would now reverse.

---

# 8. Hiring Recommendation by Target

**Graduate / junior — INTERVIEW, but this is a mismatch.** Nothing here is junior-level work and the candidate would be mis-levelled. Do not use this posting.

**Mid-level (backend) — INTERVIEW, strong expected hire.** The verified durability, integrity and recovery work comfortably exceeds mid-level. Primary risk is the authorship gap, which questions 1–4 resolve inside 40 minutes. If they land, this is an easy yes.

**Senior (backend / platform) — INTERVIEW, this is the right target.** The mechanisms that matter at senior level are all present and all verified: log-first ordering under `ENOSPC`, cross-process seq serialization under real contention, snapshot log-identity anchoring, fixpoint dependency sweeps, machine-bound fail-closed certification receipts, and executable architecture laws with working negative controls. The senior-level *gaps* are equally clear and all operational: no CI, no dependency declarations, no licence, a CSRF hole, a clean-clone-red test, one 1,000-line module. Those are correctable in a day and are exactly what code review exists to catch. Hire contingent on §7 questions 1–4, 6 and 9.

**AI / agent specialist — INTERVIEW, strongest fit in the list.** Real provider-CLI integration with correct, specific flags; enforced tool-call budgets via streaming event parsing; a working prompt-injection drill against the real corpus path with delimiter-forging defence; credential redaction; separated builder/tester/judge roles where the tester **executes the suite it writes** rather than treating a file delta as success; revision-bound judge evidence; and an agent isolation boundary that is certified against the live machine and refuses on drift. Very few candidates have shipped agent *containment* rather than agent *prompting*. Caveat: the live end-to-end factory loop is unverifiable here, so probe it verbally and hard (question 8).

**Backend / platform (infra-leaning) — INTERVIEW.** Seatbelt SBPL generation and bubblewrap namespace configuration are credible, specific systems knowledge, and the receipt design (machine identity + executable hash + boundary-file digest + disable-first) is genuinely good. Against that: POSIX-only, no containerisation of the orchestrator itself, no CI, no packaging, no observability beyond a stdlib dashboard. Interview at senior; expect to invest in operational maturity.

**Do not inflate to staff/principal.** The scope is ambitious and the mechanisms are sound, but there is no evidence of the things staff level requires: no collaborators, no code review from anyone else, no production traffic, no incident history, no API stability commitments, no team-facing decisions.

---

# 9. Scorecard

| Dimension | Score | Justification |
|---|---|---|
| **Engineering depth** | **8/10** | Bool-excluded seq guards, mid-codepoint tear tolerance, witnessed-ordering tail scan, log-first under simulated `ENOSPC`, snapshot identity anchoring, fixpoint transitive sweeps — I verified all of them independently. Not 9+ because I could not attribute the deepest code to the candidate's own hand and there is no concurrency work beyond `flock`. |
| **System design** | **8/10** | One coherent idea carried through 13 layers, mechanically enforced, with scope discovered from disk so it cannot silently under-cover. Docked for `scoped_completion.py` at 1,002 lines and for skeleton packages (`graph`, `scheduling`, `selfdev`) inflating the surface. |
| **Code quality** | **7/10** | 0 syntax errors, 4 source-only duplicate function bodies out of 2,055, consistent typed stdlib style. Docked for essay-density docstrings, 187 lines over 100 chars with `E501` disabled, and dead `EventStore._seq`. |
| **Testing & assurance** | **8/10** | 2,355 test functions, real `SIGKILL`/`waitpid` E2E, positive *and* negative controls on every scanner, explicit non-vacuity checks, only one file using `MagicMock`. Docked hard for one clean-clone-red test, no CI, and suite-wide autouse isolation passthrough. |
| **Reliability / operability** | **6/10** | Crash-safety and fail-closed gates verified end-to-end; `BootRefusal` and receipt tampering both confirmed. But no CI, no declared deps (the daemon cannot boot after a clean install), no supervisor CLI, no metrics endpoint, POSIX-only, host filesystem readable inside the sandbox. |
| **Documentation** | **7/10** | Exceptionally precise — the "live benchmark for the judge assignment" phrasing survived forensic timing analysis, and `docs/efficiency/` reports its own failures and states its own limits. Docked for impenetrability at speed, no diagram/demo, and one internal docstring overstating the fixture's provenance. |
| **Originality** | **9/10** | The self-non-exempting authenticity gate, laws-as-data with a PRIME meta-check, disable-first machine-bound isolation receipts, the substring-shadowing collection guard, and the witnessed-ordering tail scan are mechanisms I have not seen elsewhere. Not tutorial patterns. |
| **Commercial readiness** | **4/10** | No CI, no licence, no packaging, no container, no deps, single-operator scope, POSIX-only, and the product this factory built (JAA) is uncertified by the factory's own gates. A demonstrator, not a product. |
| **Portfolio clarity** | **5/10** | The engineering is far better than its presentation. Authorship requires `git shortlog` to discover, the README needs 20 minutes, there is no demo, and the headline efficiency evidence is gitignored. This score is costing the candidate interviews. |
| **Overall hire confidence** | **7/10** | High confidence the *system* is real — I broke nothing I tried to break. Moderate confidence the *candidate* can rebuild it, pending §7 questions 1–4. That gap, not the engineering, is what holds this at 7. |

---

# 10. Highest-Return Portfolio Improvements

1. **Fix the clean-clone red test and add CI.** Add a `skipif` (or check in a small fixture) at `tests/test_scoped_assurance.py:184`, declare `pytest`/`ruff`/`import-linter` under `[project.optional-dependencies]`, and add a GitHub Actions workflow running ruff + the suite + `./acceptance` + `python3 -m dispatch.isolation certify`. *Right now the README's own verification command fails on a fresh checkout — everything else is downstream of that.*

2. **Add an `AUTHORSHIP.md` and lead the README with it.** State plainly: N commits by the orchestrator, N by you; here are the five files you designed and the twelve defect classes you found and closed, with commit hashes (`4cad325`, `62081d6`, `33a5192`, `9f0a183`). *You are currently being penalised for ambiguity you could convert into your single strongest differentiator: "I built a system that writes code, then found the bugs its green test suite could not see."*

3. **Check in the evidence.** A `evidence/` directory with the isolation receipt, the certification log, one real eval-store benchmark run, and the pytest/ruff output behind the `3,566 passed` claim. *Your most impressive work is currently unfalsifiable, which for a sceptical reviewer means uncredited.*

4. **Rewrite the top 40 lines of the README.** One sentence on what it is, one diagram (inbox → claim → isolated agent → gates → certification log), one 60-second asciinema of `./acceptance` plus the isolation certify, then the depth. *Keep the dense material — move it below the fold.*

5. **Close the CSRF gap and add the drill.** Require the `X-Auth-Token` header for all mutating methods (drop cookie acceptance for `POST`), validate `Origin`, and add `tests/test_edge_server_csrf.py` with a positive control. *A one-hour fix that removes the one finding a backend interviewer is guaranteed to land.*

6. **Correct `test_model_change_requires_receipt.py`'s docstring.** State that the judge rows are live Codex calls and the remaining rows were produced by the real machinery against a deterministic `call`. *Your README already gets this right; make the code match, and the timing forensics become a story you tell rather than one told about you.*

7. **Split `control/scoped_completion.py`** and add `LICENSE` (MIT/Apache-2.0). *Cheapest remaining credibility gains.*

---

# 11. Evidence Appendix

**Repository state.** `HEAD = 35efb19b07867bb58e1288479513078cf9ab65e4` ("certify Gigabyte Linux isolation", Artiom, 2026-07-22 21:52:31 +0100). Detached HEAD; other branch `efficiency/e2-shadow-cache`. Working tree clean (0 modified). 809 commits (359 merges) spanning 2026-07-08 → 2026-07-22. Authors: `orchestrator <orchestrator@local>` 728 (369 non-merge, +48,190/−1,861 Python lines); `Artiom` 81 (+20,801/−1,752). 18 human commits carry `Co-Authored-By: Claude Opus 4.8` / `Claude Fable 5`. 3.6 MB excluding `.git`.

**Scale.** 338 Python files / 65,378 lines total: source 15,370 non-blank lines across 89 shipped files in 13 packages; tests 47,984 lines across 243 files containing 2,355 test functions and 228 `parametrize` decorators. Docs: 10 Markdown files, 1,134 lines. Comment+docstring prose fraction of source: 0.18. No `.github/`, no Makefile, no Dockerfile, no `LICENSE`, no declared dependencies.

**Environment.** Python 3.14.4, Linux 6.18.33.1-microsoft-standard-WSL2 (x86_64). `/usr/bin/bwrap` present. `pytest`, `ruff`, `lint-imports` **not installed**; no network available to install them. `/workspace` treated as read-only throughout; all execution against copies at `/tmp/eval`, `/tmp/plant`, `/tmp/auth`.

**Commands run and outcomes.**

| # | Command / probe | Result |
|---|---|---|
| 1 | `python3 -m compileall -q /tmp/eval` | exit 0 — 0 syntax errors |
| 2 | `./acceptance` | exit 0 — replay matches pre-restart state |
| 3 | `python3 acceptance_authenticity_demo.py` | exit 0 — violation `passed=False`, legitimate `passed=True` |
| 4 | 8 OS processes × 40 `EventStore.append` | 320 records, seqs distinct & gapless 0–319 |
| 5 | 6 threads × 50 `EventStore.append` | 300 records, gapless 0–299 |
| 6 | Truncate 4 bytes mid-emoji, replay + append | no raise; intact + new records readable; seqs distinct |
| 7 | Splice `seq:1` at EOF after 5 events; `_last_seq` | returned 5 (true max+1) — no seq reissue |
| 8 | 7 create-integrity refusals (dup/self-dep/cycle/4 type shapes) | all `ValueError`; log grew by exactly the 1 legitimate create |
| 9 | 4-link chain, root FAIL, one `claim_next()` | a,b,c all BLOCKED, per-link reasons correct; released in one cycle; survives replay |
| 10 | crash → `replay()` → `reclaim_orphans()` | 1 reclaimed, QUEUED, durable across a further replay |
| 11 | `per_project_cap` 1 then 2 | 2nd claim refused, then permitted |
| 12 | Priority ordering | `['hi','lo','lo2']` — desc priority, creation-order tie-break |
| 13 | Poisoned `task_created` (`priority:"1"`) on disk | skipped on replay; `claim_next()` survives |
| 14 | Snapshot over deleted-and-recreated log | `{'new'}` — no phantom task |
| 15 | `EventStore.append` raising `OSError(ENOSPC)` | live status == replayed status; failed create left no trace |
| 16 | Architecture tests executed directly (no pytest) | 30 passed; 8 failed (missing `git`/`ruff` only); 5 skipped (fixtures) |
| 17 | Plant `Path.replace` in `dispatch/dispatcher.py`; plant `infra→dispatch` import | L7: `['dispatch/dispatcher.py: Path.replace']`; L2: `[('infra/triage.py', ['dispatch'])]`; clean tree: `[]`/`[]` (89 files / 93 modules) |
| 18 | `python3 -m dispatch.isolation certify --root "$PWD"` | exit 0; receipt `e769c1ec…`; all 5 drills true |
| 19 | 6 receipt/config/source tamper vectors incl. hash-recomputed forgery | all REFUSE with distinct correct reasons; restore → ACCEPT |
| 20 | `check_authenticity` on clean tree + 7 planted stub shapes + 1 legit ABC | clean pass; all 7 caught; no false positive |
| 21 | Full top-level suite via custom pytest shim | 1,912 passed / 225 failed / 33 skipped — **all failures triaged to shim or missing binaries** |
| 22 | Direct re-verification of shim-suspect guards (`int_seq`, `last_reason`, `apply` reason) | all refuse correctly; confirmed shim artefacts |
| 23 | AST duplicate-body hash over 2,055 functions | 4 duplicate groups entirely within source |
| 24 | Timing analysis of `model_routing_receipts.log` | codex/judge ~5.888s per call (live); claude rows ~0.00015s (not live) |
| 25 | Performance probe | 1,000-task log replay 11ms; 200 `claim_next` = 21 sweeps / 179 skips in 66ms; ~7,900 appends/s |
| 26 | `git check-ignore projects/`; `git ls-files projects` | ignored at `.gitignore:11`; zero tracked files |

**Key files inspected.** `core/models.py`, `core/state_machine.py`, `infra/atomic_io.py`, `infra/event_store.py`, `infra/llm.py`, `infra/prompt_safety.py`, `infra/usage_log.py`, `dispatch/repository.py`, `dispatch/isolation.py`, `control/daemon.py`, `control/self_test.py`, `charter/laws.py`, `validation/authenticity.py`, `validation/benchmark.py`, `agents/common.py`, `agents/judge.py`, `edge/server.py`, `pyproject.toml`, `tests/conftest.py`, `tests/architecture/test_file_preservation.py`, `tests/architecture/test_layering.py`, `tests/architecture/test_readme_roadmap_accuracy.py`, `tests/architecture/test_model_change_requires_receipt.py`, `tests/e2e/_daemon_harness.py`, `tests/test_daemon_e2e_sigkill_resume.py`, `tests/test_injection_drill.py`, `tests/test_scoped_assurance.py`, `docs/efficiency/E6_GPT_ONLY_CERTIFICATION.md`.

**Limitations of this review — stated explicitly.**
- `pytest`, `ruff` and `lint-imports` were unavailable and could not be installed. The suite was executed through a **minimal pytest shim I wrote**, which does not support `capsys` capture, `pytest.param`, `MonkeyPatch.context`, or list-valued `parametrize` cases. The 225 failures are therefore **not** a measurement of suite health; I triaged them and found no genuine product defect, but I cannot certify the suite green. The repository's claim of "3,566 passed, 4 skipped" is **UNVERIFIED**.
- The macOS Seatbelt adapter could not be exercised (Linux host). Only its SBPL rendering was read and its structural tests reasoned about. The Linux bubblewrap path was fully exercised.
- No live model calls were made. The plan→build→test→judge→certify loop was verified only through deterministic substitutes; **whether the factory produces useful software end-to-end with real providers is UNKNOWN** from this repository alone.
- All `docs/efficiency/` measurements (token reductions, wall-clock speedups, suite timings, JAA canary outcomes) are **UNVERIFIED** — the artefacts live under gitignored `state/` and `projects/`.
- I did not audit `control/scoped_completion.py` (1,002 lines), `validation/assurance.py`, `validation/deterministic_cache.py`, `graph/`, `memory/overseer.py` or `selfdev/` in depth.
- Author attribution rests on git metadata, which is trivially forgeable. I treated the split as reported and did not attempt to corroborate it independently.