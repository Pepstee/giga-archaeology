# Orchestrator v2/v3 versus native Codex autonomy

Date: 25 July 2026  
Status: evidence-backed preliminary comparison; controlled head-to-head benchmark not yet run  
Measurement cutoff: 25 July 2026, 17:48 UTC for the native Codex session; approximately
17:44 UTC for the Gigabyte supervisor snapshot  
Companion protocol: `ORCHESTRATOR_VS_NATIVE_CODEX_BENCHMARK_V1.md`

## Verdict

Native Codex currently beats v3 at **continuity economics**: one agent retains ownership of a
changing problem, plans and replans inside the same trajectory, uses tools directly, compacts its
own context, and crosses many implementation/test/repair steps without buying a new
planner-builder-tester-judge conversation for each step. [inference, confidence 0.96]

V3 beats native Codex at **defensibility**: exact state, revision-bound receipts, deterministic
host assurance, independent semantic judgement, isolated worktrees, explicit retries, STOP,
certificates and replayable operational decisions. [verified, confidence 0.99]

Neither is the complete target:

- native Codex is fast and adaptive, but its trajectory is not a deterministic workflow
  authority or a commercial certificate;
- v3 is highly auditable, but it repeatedly decomposes one cognitive job into costly role
  transitions and repeatedly assures work that has not materially changed;
- the current thin Codex/Sonnet/Fable supervisor demonstrates unattended continuity, but it is
  an external control script around Codex rather than proof that v3 has acquired that capability.

The design target should therefore be:

> **Codex-like continuous cognition inside a thin v3 deterministic perimeter.**

The deterministic layer should own identity, authority, isolation, budgets, durable checkpoints,
side effects, evidence and certification. A persistent work capsule should own the internal
plan→edit→test→diagnose→repair loop. The factory should not represent every thought or microstep as
a separately planned and judged task. [architectural conclusion, confidence 0.94]

This report does **not** claim that native Codex is token-cheap. The measured app session is
enormous. Its advantage is that 98.53% of recorded input was cache-served and that the same
trajectory retained operational ownership; it did not eliminate context, it made context
continuity economically usable.

## Systems being compared

Four distinct systems must not be conflated:

| ID | System | Boundary |
|---|---|---|
| N | Native Codex | The app/CLI agent loop: reasoning, compaction, tools, optional subagents, sandbox and task/session persistence. |
| T | Thin persistent stack | `systemd` + durable prompt/checkpoint + `codex exec` coordinator + sequential Sonnet coder + Fable milestone rulings. This is the current unattended incumbent on Gigabyte. |
| V2 | Orchestrator v2 | Event-sourced task queue, model roles, dispatcher, overseer, scorecard, gates and project loop that built v3. |
| V3 | Orchestrator v3/E1–E6 | Stronger task/evidence/isolation/assurance architecture used for the JAA pressure test, before DFI authority cutover. |
| DFI | V3 deterministic-infrastructure candidate | Certified but inactive DFI commits through DFI-07R; DFI-08 was still under repair at the measurement cutoff. |

Official Codex documentation confirms that native Codex can run non-interactively with JSONL
output and resume sessions, that subagents are coordinated by Codex and keep delegated work out of
the main context, and that sandbox/approval policy is built into the execution surface:
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode.md),
[subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents.md), and
[agent approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security.md).

## Evidence grades

- **A:** deterministic event log, git object, exact receipt, provider usage record or local Codex
  session telemetry.
- **B:** reconstruction from A-grade timestamps or several independently matching A-grade records.
- **C:** report/self-description not independently reconstructable from the current snapshot.
- **Unknown:** the instrument does not capture the measure honestly.

No cross-system task count, line count or “certificate” count is treated as equivalent merely
because the labels are similar.

## Hard measurements

### Summary table

| Measure | Native Codex app session (N) | Thin Gigabyte stack (T) | V2 | V3/JAA historical |
|---|---:|---:|---:|---:|
| Observed window | 18–25 Jul | 25 Jul 04:21 UTC onward | 7–19 Jul | 19–22 Jul |
| Calendar span | 169.8 h | 13.4 h at snapshot | 294.1 h | 75.7 h |
| Recorded work/model wall time | 97.58 turn-hours, includes waits | incomplete while active | 112.6 agent-hours | 10.40 measured model-hours |
| Work/result attempts | 102 completed non-import turns | 3 completed coordinator attempts + 1 active | 1,529 results | 115 work measurements |
| Accepted/successful units | not comparable | DFI-06 and DFI-07R certified | 877 successful results; 895 done transitions | 42 accepted attempts; 41 unique accepted task IDs |
| Rejected/failed units | not comparable | one coordinator attempt failed; DFI-08 still unsettled | 652 failed results | 73 rejected attempts |
| Success/acceptance ratio | unknown | not meaningful at n=3 | 57.36% result success | 36.52% attempt acceptance |
| Requeues | native internal steering, not separately exposed | successor restarts at process level | 538 | 137 |
| Provider-reported input tokens | 2,923,396,215 | ≥147,932,749 Codex + Claude fields below | not instrumented | 43,248,058 total tokens |
| Cached input | 2,880,313,856 (98.53%) | ≥145,944,576 Codex | not instrumented | present in role measurements, incomplete historically |
| Uncached input | 43,082,359 | ≥1,988,173 Codex | not instrumented | available only in newer measurements |
| Output tokens | 4,385,752 | ≥239,355 Codex; 769,202 Claude | not instrumented | included in total |
| Reasoning output | 1,241,276 | ≥30,086 Codex | not instrumented | included where provider supplied it |
| Tokens / unique accepted task | invalid unit | invalid unit | unknown | 1,054,831 |
| Recorded tool-call envelopes | 7,131 function + 11,931 custom | hundreds; exact lower bound in coordinator JSONL | unknown | 336 in scorecard window |
| Context compactions | 81 | internal to each Codex/Claude run | ephemeral role calls | ephemeral role calls |
| Operator interventions | not separable from new goals/status requests | at least one gate requested ratification | unknown | not reliably reconstructed |
| Reported cost | subscription, not per-call | Claude list-price telemetry ≥$25.77 | $1,501.25 provider-equivalent budget telemetry | $0 in subscription-backed measurements; not actual cost |

All figures in this table are A-grade except:

- T’s “certified units” and operator intervention count are B-grade reconstructions;
- native turn-hours include waiting/monitoring and are not model compute;
- T token figures are strict lower bounds because failed Codex attempt 2 and active attempt 4 had
  no terminal usage record at cutoff;
- v2 and v3 “success” use different definitions.

### Native Codex session

The active Codex session file contained:

- 102 completed non-import turns and five started but non-terminal turns;
- 97.58 summed turn-hours, median 2.67 minutes, p95 99.6 minutes and a maximum
  2,058.5-minute turn;
- 81 context compactions;
- 7,131 function-call records, including 4,631 waits, 1,347 command executions and 1,118
  session writes/polls;
- 11,931 custom tool calls;
- 2.923 billion input tokens, of which 2.880 billion were cached;
- 43.08 million uncached input, 4.39 million output and 1.24 million reasoning-output tokens.

The 2.923-billion figure is a provider telemetry counter, not subscription billing and not a
claim that all cached tokens consume quota equally. It does prove that native continuity is based
on aggressive repeated-context caching rather than on tiny contexts. [verified, confidence 1.00]

### Thin persistent Gigabyte stack

Between 04:21 UTC and the cutoff:

- attempt 1 ran 2h09m and certified DFI-06;
- attempt 2 ran 2h58m and ended in a failed Codex turn with 39 explicit error events;
- attempt 3 ran 5h23m, completed DFI-07R and later stopped at a DFI-08 budget-ratification gate;
- attempt 4 resumed and remained active at cutoff;
- DFI-06 and DFI-07R were committed by 12:33 UTC, approximately 8.20 calendar hours after
  launch;
- completed, usage-bearing Codex runs recorded at least 147.93 million input tokens, 98.66%
  cached, plus 239,355 output and 30,086 reasoning-output tokens;
- twelve settled Claude sessions across DFI-06–DFI-08 recorded eight successes, four errors,
  347 turns, 3.75 model-hours, 24.57 million cache-read tokens, 1.05 million cache-creation
  tokens, 769,202 output tokens and $25.77 provider-equivalent cost;
- one further Sonnet session was active and therefore absent from the terminal totals.

This stack proves durable unattended process continuity better than native app-only execution,
but the process is still suffering repeated repair/certification cycles: DFI-08 had reached a
fifth repair package and remained uncertified. [verified fact + inference, confidence 0.96]

### V2

V2’s own deterministic scorecard reports:

- 1,529 result events: 877 successful and 652 failed;
- 112.6 time-in-agent hours and a 4.4-minute mean run;
- 538 requeues, 11 identical-attempt refusals and nine budget-breaker trips;
- 23 project confirmation/certification events, or 66 runs per event;
- 695 successful `orchestrator-v3` results and 499 failed results;
- 359 v3 merge commits in the inspected project history;
- 57.36% result-event success.

The top three failure classes were provider/rate-limit failures: 163 Claude usage-limit results,
49 unrecognised Claude exits treated as limits, and 47 corresponding Codex exits. This means at
least 259/652 failed result events (39.7%) were provider-availability failures rather than
identified product defects. [verified, confidence 1.00]

V2 was productive, but “v2 built v3 in roughly a week” is not a quality-normalised victory:
the initial v3 sign-off was later invalidated by runtime wiring, isolation, recovery,
certification and efficiency defects. V2’s output therefore proves throughput, not commercial
correctness parity. [inference, confidence 0.98]

### V3/JAA

The preserved v3 efficiency scorecard reports:

- 115 model attempts;
- 42 accepted attempts, 41 unique accepted task IDs and 73 rejected attempts;
- 43,248,058 provider-reported tokens;
- 1,054,831 tokens per unique accepted task;
- 19,684,671 tokens attached to rejected work;
- 16,495,512 tokens attached to failed assurance, a subset of rejected work;
- 336 tool calls and 37,454 seconds of recorded model wall time.

The host-assurance log adds:

- 77 manifests: 58 passed and 19 failed;
- 152 command receipts, 124 fresh executions and approximately 28–29 reuse hits;
- 10,477 seconds of aggregate host-assurance elapsed time;
- 155 active reuse probes, 29 hits and 126 misses in that window.

Historical shadow evidence recorded 101 exact reusable matches out of 101 candidates, but all were
re-executed while reuse remained shadow-only. Later active reuse is real but arrived after most of
the JAA burn. [verified, confidence 1.00]

## Code and assurance mass

Line counts are not productivity, but they quantify maintenance and review surface.

| Revision | Production Python/shell | Test Python/shell | Combined |
|---|---:|---:|---:|
| V2 `07ea5aa` | 11,038 | 5,081 | 16,119 |
| V3 production baseline `35efb19` | 17,217 | 48,161 | 65,378 |
| DFI-04 `dcf5097` | 24,416 | 53,097 | 77,513 |
| DFI-06 `f3822b0` | 26,555 | 57,937 | 84,492 |
| DFI-07R `d1d0ba7` | 27,389 | 59,028 | 86,417 |

Consequences:

- V3’s baseline executable/test surface is 4.06 times v2’s.
- V3 baseline has 2.80 test lines per production line; v2 has 0.46.
- DFI-00→07R adds 10,172 production and 10,867 test lines over the v3 baseline:
  +59.1% production and +32.2% combined surface before authority cutover.
- The live DFI-08 candidate adds another 646-line execution ledger and 969 test lines, plus one
  project configuration line, but was not certified at cutoff.

This is not evidence that the assurance code is useless. It is evidence that deterministic
infrastructure has become a product of comparable complexity to the factory it is meant to
control. Every added authority path creates more code that must itself be independently assured.
[inference, confidence 0.97]

## Architectural comparison

| Property | Native Codex | Thin stack | V2 | V3/DFI |
|---|---|---|---|---|
| Cognitive continuity | Excellent within one long turn/session | Excellent while service and session live | Low: short role calls | Low: role/task boundaries dominate |
| Dynamic self-correction | Native inside one trajectory | Native coordinator + Sonnet packages | Replan/requeue cycle | Replan/requeue/judge cycle |
| Context economics | Huge but 98.53% cache-served in measured session | Strong cache reuse within each model run | Mostly fresh ephemeral prompts | Bounded prompts, but fresh role transitions and large semantic closures |
| Deterministic scheduling | No; model chooses next tool/action | Shell/checkpoint chooses coarse stage | Partial host state machine + LLM planner | Increasingly strong; DFI compiler remains inactive |
| Durable node identity | Session/turn IDs, not product workflow identity | Ad hoc stage directories and hashes | Task IDs/events | Strong operation, scope, closure and receipt identities |
| Crash recovery | Session resume; exact external side-effect recovery not guaranteed | `systemd` restart + durable checkpoint; custom | Reclaim/requeue, may repeat work | Worktree checkpoints, settle fences; durable activity ledger still under construction |
| Independent judgement | Optional subagent/review, same orchestrator | Codex review + Fable milestone authority | Judge role | Host assurance + independent semantic judge |
| Auditability | Detailed trajectory JSONL, very large | Detailed but fragmented across control files | Compact append-only events and scorecard | Strongest structured evidence, but many overlapping event families |
| Isolation/authority | Built-in sandbox/approvals/worktrees | Full-access launch plus external leases | Workspaces and L9 fences | Strong worktree/isolation/STOP/fenced authority |
| Side-effect/idempotency | Tool-specific; not a universal workflow contract | Script-specific | Limited | Explicit target; not fully cut over |
| Parallelism | Built-in subagents; Codex handles routing/waiting | Sequential mutable worker by design | Worker pool | Planned mechanical disjoint lanes |
| Commercial defensibility | Weak by itself | Medium; process receipts exist | Medium-low | High if DFI cutover and release proof complete |
| Coordination tax | Lowest | Medium | High | Highest |

Official Codex guidance explicitly notes that subagents reduce main-context pollution but consume
additional tokens. That supports, rather than contradicts, the central diagnosis: delegation is
valuable when it isolates genuinely independent work, not when every ordinary transition becomes
a new model conversation. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents.md)

## Why native Codex currently feels more autonomous

### 1. It has one cognitive owner

Codex does not normally purchase a separate planner verdict before every edit, a separate tester
interpretation after every edit, and a separate planner turn after every finding. One loop can
inspect, act, observe and revise until the task is settled.

V3’s role separation is useful for independence, but it incorrectly applies independence to
micro-coordination as well as terminal assurance. The result is a handoff tax on ordinary thought.
[inference, confidence 0.97]

### 2. It treats tool observations as continuation, not as new work

A failed test becomes the next observation in the same trajectory. In v3 it can become a failed
task result, transition, fingerprint, requeue, planner input, new worktree attempt, host gate and
new judge context. The latter is more defensible, but much more expensive.

### 3. It caches a stable prefix

Native Codex’s 98.53% cached-input ratio shows that a large, stable context prefix can be reused
across thousands of tool interactions. V3 deliberately uses ephemeral role calls for contamination
control, but loses the economic benefit of a persistent working set.

The right response is not one immortal, unbounded chat. It is a bounded persistent **work capsule**
whose immutable contract and context prefix are stable until the component closes.

### 4. It compacts internally

The measured native session compacted 81 times without requiring an external planner to
reconstruct the work. V3’s summaries, task results and receipts are stronger evidence, but they are
also repeatedly expanded back into model-readable prose.

### 5. Native orchestration is mostly implicit

Codex’s orchestration code is a platform capability and is not part of this repository’s
maintenance surface. V3 must build, test and certify every scheduler, schema, ledger, cache,
checkpoint and gate it owns. Comparing only runtime tokens hides this construction tax.

## Where v3 is genuinely superior

The answer is not to abandon v3 and use a naked Codex session:

1. A Codex trajectory records what happened; v3 can prove which exact product closure was
   authorised and certified.
2. Native resume does not by itself prove exactly-once durable consumption of a provider result
   or a consequential side effect.
3. Native tool success is not automatically a component certificate with dependency, runtime,
   evidence and revision bindings.
4. Native self-review is not independent review.
5. A long autonomous session can drift, overfit to its own previous reasoning, silently weaken
   tests or retain contaminated context. V3 has explicit gates against these classes.
6. V3 can make model/provider choice replaceable while retaining one workflow truth.

These are commercially material advantages. The error is not building them; it is placing them
inside the inner cognitive loop rather than around its meaningful boundaries.

## Precise diagnosis of the gap

The current gap is not one bug. It is a difference in **unit of orchestration**:

```text
Native Codex unit
  one bounded goal
    -> inspect -> plan -> edit -> test -> diagnose -> repair -> finish

Current v3 unit
  one role action
    -> schedule -> package context -> call model -> parse -> settle -> assure
    -> schedule another role action -> package context again -> call model again

Required v3 unit
  one certified work capsule
    -> deterministic admission and immutable contract
    -> persistent model-owned inspect/edit/test/repair loop
    -> durable checkpoints and host gates at material state changes
    -> independent delta review at capsule boundary
    -> full independent review at release
```

V3 should determinise **authority and evidence**, not attempt to determinise every intermediate
reasoning step. [architectural conclusion, confidence 0.96]

## Preliminary winners

These are not benchmark scores; they are evidence-bound current verdicts:

| Objective | Current winner | Confidence | Reason |
|---|---|---:|---|
| Long adaptive implementation continuity | Native Codex / thin stack | 0.99 | Direct measured multi-hour turns, compaction and tool continuity |
| Unattended process survival | Thin stack | 0.97 | `systemd` + checkpoint + successor restarts |
| Historical raw production throughput | V2 | 0.90 | 695 successful v3 task results in 12.25 days, but quality not normalised |
| Deterministic evidence and release defensibility | V3 | 0.99 | Exact host/closure/certificate and isolation mechanisms |
| Current token efficiency per accepted v3 task | Native comparison unknown | — | Work units differ; v3’s 1.055m/task cannot be divided into native turns honestly |
| Current maintenance simplicity | Native Codex, then V2 | 0.99 | V3/DFI repository surface is materially larger |
| Multi-model independent scrutiny | Thin stack / V3 | 0.95 | Sequential Sonnet author, Codex review, Fable authority |
| Commercial-production readiness | None | 0.98 | Native lacks v3’s product assurance; v3 has not activated/proved efficient DFI |

## What cannot be concluded from history

The following claims would be dishonest:

- “Codex is X times faster than v3” — no identical work package has been run through both.
- “V2 is better because it finished v3 in a week” — the original sign-off did not survive
  independent runtime audit.
- “V3 is safer because it has more tests” — quality depends on test power and escaped defects,
  not volume.
- “98.53% cached means 98.53% free” — quota and provider economics are not represented by raw
  token counts alone.
- “Two DFI certificates in 8.2 hours is a stable throughput rate” — the sample is tiny and
  DFI-08’s repeated failures immediately show high variance.
- “Native Codex has no observability” — it has detailed trajectory logs; what it lacks is v3’s
  deterministic product/evidence semantics.

## Decisive next step

Run the companion benchmark with:

1. identical frozen repository revisions and work contracts;
2. an architecture-isolated track using the same model profile and budgets;
3. a production-policy track letting each system use its intended model split;
4. hidden tests, mutation controls and blind independent review outside both contenders;
5. separate cached input, uncached input, output, reasoning, wall time, operator touches and
   subscription-limit deltas;
6. forced restart/provider-return and repeated-input cases;
7. median, p90 and failure distribution, not one showcase run.

Until that benchmark exists, the correct engineering move is to use this report as a causal
diagnosis, not as a leaderboard.

## Evidence anchors

### Gigabyte source and runtime

- V2 repository: `/home/gutua/software-factory/agentic-orchestrator`, revision `07ea5aa`
- V3 production: `/home/gutua/software-factory/agentic-orchestrator/projects/orchestrator-v3`,
  revision `35efb19`
- DFI-06: `f3822b037b2ecf1459fa1651ec3ececd103e65da`
- DFI-07R: `d1d0ba75fb7d1cfab0d8fcfa207c4895746176a0`
- thin supervisor:
  `/home/gutua/software-factory/.control/fable-governed-dfi-20260725`

### Evidence hashes at cutoff

- V2 task log:
  `0826487716e6cf45a81be189364962e3f05299dc4f5cade24b6865b6cd14cd77`
- V2 budget log:
  `0811576a31b19a6a34163790e9bde3b21137a7c7dd711215a79e3fb19a6d0fa3`
- V3 task log:
  `454014e2b903b891c205c5dfb61ade45ec4c7826831cfc2330793722bfffaf9b`
- V3 host-assurance log:
  `76be88f434da9642a33254c2e905dda7d5796b92de8b0f7aa0a8c9b1b9139c34`
- V3 shadow-cache log:
  `16b6e9ff9577fac5983e496f6b45a7bb88ddadfac88544a55bd068607e8eaa25`
- V3 active deterministic-cache log:
  `542ace6482e49f469d077f25a1704cad0af3d27eb1dd5d860fd4a9df76142280`
- V3 project-certification log:
  `70bfe30a63b73a18cf95bf044981e605137a7adb25ed9496798af779ed9796d6`
- thin-supervisor sorted file-manifest hash at snapshot:
  `951362f492d374a6814f977aa476b00fd48fd45dbaf8051d4d3b78db20e3b021`

The native session is append-active, so its evidence is bound by the measurement timestamp and
counter values rather than a terminal file hash. A prefix snapshot at 174,957,854 bytes hashed to
`b80e73de52b4c4fc5aa14afe124ec9724bf86ebb5cfc397f8476c4a991cc5f3c`
shortly before the final 17:48 token counter was read.

## Confidence

- Raw runtime and code measurements: 1.00.
- Architectural description of current systems: 0.97.
- Causal diagnosis of v3’s coordination tax: 0.96.
- Recommendation for a persistent work capsule inside a deterministic perimeter: 0.94.
- Any cross-system speed multiplier before the controlled benchmark: deliberately unclaimed.

