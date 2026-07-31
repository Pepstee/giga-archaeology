# Orchestrator v3: from initial sign-off to commercial production readiness

Date: 2026-07-23

## Verdict

Estimated progress from the original post-v2 v3 sign-off to genuine commercial-production
readiness: **58% complete** [inference, confidence 0.70; plausible range 54–62%].

This is a risk-weighted maturity estimate, not a percentage of tasks, slices or lines of code.
The remaining work contains the hardest authority, recovery, incremental-assurance, cutover and
operational-proof gates. DFI-04 passing would move the estimate to roughly 60%; it is not yet
certified.

## Roadmap

| Cumulative progress | Stage | State | What it established |
|---:|---|---|---|
| 0% | v3 initially signed off after being built by v2 | Historical starting point | A large green suite and apparently complete architecture, later shown not to prove runtime wiring or unattended safety. |
| 8% | Independent deep audit | Done, 19 Jul | Found P0/P1 defects: bypassed boot gate, missing runtime completion/certification, discarded planner output, unsafe host fallback, crash-stranded work, non-executing tester and other gaps. |
| 18% | Core safety and functional remediation | Done, 19 Jul | Closed all non-deferred audit findings, wired the real factory loop, introduced certified isolation, strict result boundaries, restart recovery, real testing and project certification. |
| 25% | Live prediction-ledger canary | Done, 19 Jul | Proved a real plan→build→test→judge→certify→improve→certify loop. Exposed and repaired live-only defects. Qualification: degraded GPT-only provider proof, not the normal provider split. |
| 35% | JAA as production pressure test | Partial, 20–22 Jul | Began a substantially more demanding product. JAA-00/JAA-01 work exposed persistence, evidence-binding, timeout, supervision and semantic-review weaknesses. JAA remains unfinished and paused. |
| 44% | First efficiency programme, E0–E6 | Implemented and partly live-proven, 21–22 Jul | Added context containment, tool/token ceilings, telemetry, deterministic cache, pass-only reuse, host assurance, external-evidence reuse and GPT-only continuity. A controlled JAA validation fell from the reported ~922k tokens to 202,282 tokens, but this did not solve the structural economics. |
| 49% | Efficiency diagnosis and evidence | Done, 22 Jul | Measured 43,248,058 provider-reported tokens, 1,054,831 tokens per unique accepted task and 73 rejected attempts out of 115. Identified repeated full semantic review, planner calls, lost sub-work, inactive reuse and factory/product co-development as the main causes. |
| 53% | Gigabyte migration and Linux production baseline | Done, 22 Jul | Moved the software-factory authority and GIGA governance layer to Gigabyte, preserved the Mac as a separate tool, and certified Gigabyte Linux isolation at production commit `35efb19`. STOP remains armed. |
| 56% | Deterministic-infrastructure architecture | Done, then independently revised, 22–23 Jul | Designed the factory epoch, canonical schemas, finding ledger, workflow compiler, operation identity, transactional ledger, CAS, impact proof, incremental certificates, concurrency, routing, observability and cutover. Fable then found the original 17-slice programme too large and incorrectly ordered. |
| **58%** | **DFI-00–DFI-03 certified; DFI-04 completion under repair** | **Current** | Epoch, canonical schema, finding ledger and shadow workflow compiler are certified but inactive/shadow-only. DFI-04 has the right architecture, but Fable found an epoch-rotation wedge, persistence/verification defects and missing behavioural evidence. Sonnet is implementing the bounded completion under Fable authority; Codex is integrating and certifying. |
| 60% | DFI-04 certified, still inactive | Next gate | Close crash/re-settlement windows, durable scheduler decisions, enforced profile adoption, real existing-test verification, daemon boot tests and the ≤500-net-production-line gate. No production cutover yet. |
| 64% | Corrected programme contract and early economics proof | Ahead | Ratify fallback semantics; replace impossible historical-replay recall with scope-certified canaries plus forward shadow soak; run DFI-11-lite delta review in observation-only mode; split/generate the schema registry and compact routine evidence. |
| 75% | Durable execution substrate | Ahead | Re-cut and implement the substance of DFI-05–DFI-10: CAS, transactional single-writer ledger, fenced leadership, general pass-only operation reuse, durable model-response supervision, generic checkpoints/join and deterministic impact analysis. Reuse existing E2/E3 instead of building a duplicate cache. |
| 84% | Incremental semantic assurance | Ahead | Prove delta review in shadow with 100% material-finding recall and adversarial incompleteness controls; activate composable delta certificates only for eligible revisions; retain full semantic review for first certificates, expansions, integration and every release. |
| 89% | Safe throughput and economic routing | Ahead | Add mechanically disjoint builder/test-author concurrency, evidence-gated model routing, provider-health handling and transactional budget reservation. Benchmark each route; do not make expensive models the default. |
| 94% | New authority cutover and internal factory certification | Ahead | Deliver complete audit/explanation surfaces, backups and clean-host restore; cut authority under STOP to the deterministic engine; retire duplicate legacy paths; pass crash, tamper, outage, disk-full, dual-daemon, stale-worker and rollback drills; publish measured before/after economics. |
| 98% | Sustained JAA proving run | Ahead | Resume JAA only on a frozen certified epoch. Settle JAA-01, then build/certify JAA-02…JAA-16 in dependency order. Require all receipts, end-to-end acceptance, restart/replay proof and a clean release commit. Use JAA as evidence of sustained production, not as the mechanism for debugging the factory again. |
| **100%** | **Commercial-production sign-off** | **End point** | Close deferred attacker-centric hardening relevant to commercial use; replace the temporary isolation arrangement with the better portable container method; prove the normal Sonnet/Claude workforce plus independent GPT judge split; establish release/upgrade/rollback procedures, secret/network policy, observability and cost SLOs, incident runbooks, backup/restore, and a sustained no-severity-1 soak. |

## Why the current estimate is 58%

It is not lower because v3 now has a real functional loop, a live completed canary, certified
isolation, thousands of passing tests, E1–E6 controls, a frozen Linux production baseline and four
certified deterministic-infrastructure slices.

It is not higher because the final transactional execution authority, general durable operation
reuse, model-response recovery, semantic delta certification, safe concurrency, economic routing,
cutover, full JAA proof and commercial operating gates do not yet exist as certified production
behaviour.

## Immediate critical path

1. Finish and independently certify DFI-04 without activation.
2. Ratify the revised programme contract and fallback ceiling.
3. Run the early shadow delta-review experiment to validate the largest prospective saving.
4. Re-cut DFI-05–DFI-16 into fewer, outcome-owned slices under the entropy budget.
5. Build the durable execution substrate.
6. Certify incremental assurance, then concurrency and model routing.
7. Cut over once, retire duplicate authority, and certify the factory.
8. Resume and finish JAA on the frozen certified factory.
9. Pass the final commercial operating and security gate.

## Evidence anchors

- `reports/orchestrator-v3-deep-audit-2026-07-19.md`
- `architecture/ORCHESTRATOR_EFFICIENCY_RUNTIME_AUDIT_2026-07-22.md`
- `architecture/ORCHESTRATOR_V3_DISPROPORTIONATE_SPEED_RETURNS_2026-07-22.md`
- `architecture/ORCHESTRATOR_V3_DETERMINISTIC_INFRASTRUCTURE_PLAN_2026-07-22.md`
- `reports/FABLE_ORCHESTRATOR_DI_ASSESSMENT_2026-07-23.md`
- Gigabyte: `docs/efficiency/JAA_ORCHESTRATOR_SKILLTREE_HANDOFF_2026-07-22.md`
