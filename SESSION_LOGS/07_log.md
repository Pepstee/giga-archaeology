# Session 07 log — Virtual-twin control plane

*Status: IN PROGRESS. P0 and P1 pass; P2 transactional capture is next.*

## 20 Jul — three-depth reassessment and target design

The complete GIGA workspace was inventoried in three cycles. The light map gives a fast subsystem
view; the medium map traces data, memory and runtime flows; the deep map verifies schemas, record
counts, process state, permissions, tests, drift and failure modes. Graphify was used only as the
first surface lens: its 26-node graph covered one retrospective rather than the architecture, so
the reports are grounded in direct filesystem, JSONL, SQLite, process and test inspection.

Durable artefacts: `architecture/00_DISCOVERY_INDEX.md`, `01_LIGHT_MAP.md`, `02_MEDIUM_MAP.md`,
`03_DEEP_MAP.md`, `04_VIRTUAL_TWIN_TARGET.md`, `05_TRANSITION_ROADMAP.md`, and the immutable export
baseline. All derived JSONL corpora scanned without malformed records and their counts agree with
the corpus manifest. All four raw export hashes matched before and after implementation.

## 20 Jul — trust kernel implementation

Added the provider-neutral `twin_core` package and secure local store at
`~/.giga/twin.sqlite3`. It now supplies append-only idempotent events, processing transitions,
receipts, goals, decisions, action foundations and source-hashed derived-artefact registration.
The operator-confirmed virtual-twin goal and first trust-kernel decision are seeded.

Added deterministic memory validation, runtime health, export verification and machine-readable
maturity commands. Fixed six existing memory/provenance issues without deleting entries or
placing sensitive travel references in the always-loaded index. Hardened `~/.jarvis` permissions
to owner-only.

The read-only prediction worker's Claude command previously lost its prompt because a variadic
flag consumed it. The command was corrected, unit-tested and live-smoke-tested: Claude truthfully
reports quota exhaustion; Codex succeeds under a read-only sandbox. SQLite lifecycle leakage in
`prediction_automation.py` was also fixed. The complete GIGA suite now passes 23 tests; the
prediction suite passes with resource warnings treated as errors.

## 20 Jul — P2 Telegram transaction path deployed

Added a bounded deterministic context compiler, strict model proposal schema, temporary projected
memory validation, create/replace preconditions, deletion/path/symlink denial, index-last atomic
file commits and idempotent partial replay. Telegram updates are now stored with an idempotency key
and capture receipt before any provider call. Processing failures remain retryable; successful
replays use their committed reply receipt without invoking a model again; offset writes are atomic.

Providers no longer write files. Claude runs with no tools; Codex runs from an empty disposable
workspace with a read-only sandbox, ignored user config/rules and a strict output schema. A live
Claude→Codex smoke test returned the exact no-write proposal. The full suite passes 32 tests with
resource warnings treated as failures. After that gate, the idle Telegram child was restarted
under the existing supervisor and the replacement remained live. No token, offset, export or
Market Aligner file was rewritten.

The daily harvester was then moved onto the same proposal lifecycle. It now selects genuinely new
events before historical ChatGPT backfill, uses a character budget as well as a record ceiling,
retains every delta under a content-addressed filename, and advances its seen-state atomically only
after a committed receipt. The old Claude/Codex danger-bypass writer was removed; prediction Codex
fallback also runs from an empty disposable read-only workspace. The full suite now passes 33
tests. A forced live batch was not run because Market Aligner's independent certification agent was
active; the next scheduled daily run will exercise the new path without interrupting it.

## Still open

- P2: first real-message/daily receipt inspection and live transition fault injection. Telegram
  and daily capture/proposal legs are deployed.
- P3: typed temporal/epistemic memory, deterministic retrieval compiler and locked recall eval.
- P4+: preference/decision outcomes, external read-only state, style/thinking evaluations and
  bounded agency according to `architecture/05_TRANSITION_ROADMAP.md`.
- Session 03 life-infrastructure connectors and Session 04/05 prompt-bank/calibration work remain
  independently open.

## 22 Jul — four-friend relationship event graph designed

Added `architecture/07_RELATIONSHIP_EVENT_GRAPH.md` for the Andrei/Bottle, Serge, Allen and
Joel pilot. The design rejects a neural model as the factual authority and separates immutable
message evidence, deterministic interaction structure and probabilistic relationship
interpretation. It specifies canonical people/account/thread/message/session/episode/state IDs,
cross-platform identity assertions, exact source pointers, group-context preservation,
one-sided/pasted-source coverage, deduplication without provenance loss, monthly temporal state
vectors, semantic annotation review and profile-graph projection.

The anticipated Telegram export is the first major landing source. Its gate is: immutable hash
and manifest, read-only schema/count inspection, canonical JSONL extraction with native IDs and
archive positions, operator-confirmed identity mapping, raw/canonical reconciliation, exact
sequence retrieval, and only then semantic analysis. The current 26-node Graphify output remains
a high-level characterisation projection; it is not the relationship evidence store.

## 22 Jul — SkillTree registry and external-proof walking skeleton

The public SkillTree export is now operated as an evidence-backed taxonomy rather than treated as
installed capability. The `skilltree-operator` audit covers all 137 jobs and computes status only
from exact durable evidence. After this slice the registry records four implemented, two external,
three partial, five available, two blocked and 121 documented jobs. Research Reports and
Adversarial Verification are now implemented; Deck Production is partial because the current
output is an evidence-linked outline rather than a finished branded deck.

Added `twin_core.external_proof` and the `compile-proof` CLI. It accepts only draft/A1 manifests,
requires exact source needles, records line spans and SHA-256s, rejects private source roots,
secrets, path escape and unknown claims, writes atomically, registers all derived artefacts in the
existing `TwinStore`, and appends a committed receipt. The first real run compiled the virtual-twin
trust-kernel evidence into a case study, technical report, presentation outline, QA record, build
manifest and trust receipt. An identical replay returned the same receipt without rewriting files.

The canonical `tests/` suite passes 47 tests; the seven focused compiler tests include negative
controls and a real CLI run. Repository-wide unconstrained pytest discovery still collides on the
two intentionally independent Market Aligner copies, so the canonical giga-user suite remains
`pytest tests`. Market Aligner itself was not modified.

The new proof artefacts pass their lineage checks. The full historical derived-artefact registry
remains red because several 20 Jul architecture registrations refer to files legitimately changed
later. They require an explicit rebuild/supersession slice and were not re-baselined here.

## 22 Jul — append-only lineage migration and reconciliation

Replaced the single-row overwrite model with schema-v2 revision history. Migration preserved all
12 former registrations byte-for-byte as `legacy` revisions. New builds and reconciliations now
create a `current` revision and mark the prior one `superseded`; history is queryable and the active
projection remains backward-compatible. Reconciliation requires an `operator_confirmed` event and
explicit passing verification evidence. Negative controls prove model-inferred authority and failed
gates cannot promote revisions.

Before migration, SQLite's backup API created the owner-only recovery copy
`~/.giga/backups/twin-before-lineage-v2-c0f203a1ccf73824.sqlite3` with SHA-256
`c0f203a1ccf738244c519de956cb575e0716b3e4a87659c924448afe0add9abb`. The proof pack was then
rebuilt through its real compiler, producing six genuine `built` current revisions. The six
architecture records were adopted under the bounded reconciliation policy as `reconciled`, not
misrepresented as rebuilt.

The committed receipts are `architecture/08_LINEAGE_RECONCILIATION.json` and `.md`. Their gates
record 51 passing canonical tests, five matching immutable exports, 53/53 indexed memory entries
with no findings, no out-of-scope failing registration and an owner-only matching backup. Final
state: SQLite integrity `ok`; 12 active registrations; 33 revisions; six current built, six current
reconciled and 21 superseded; aggregate artefact audit green; P1 passed. Reconciliation reports
are now immutable and state-addressed; `architecture/08_LINEAGE_RECONCILIATION.*` is only the
latest-state convenience copy. The exact original bytes of the two receipts created before that
hardening were recovered, hash-matched and mapped in
`architecture/lineage-reconciliation/LEGACY_REPORT_RECOVERY.json`. A final exact command replay
returned the existing immutable receipt and left both revision and receipt counts unchanged.

## 22 Jul — evidence-bound transcript processing

Promoted SkillTree **Transcript Processing** from partial to implemented without modifying the
source export. Added `twin_core/transcript_actions.py` and `scripts/process_transcript.py` to turn
local UTF-8 transcripts into source-hashed action, decision, open-question and learning-gap
candidates. Every candidate retains its exact line number, speaker, evidence hash and
`needs_review` status. A separate named-operator approval command produces a packet-bound receipt;
the compiler itself has draft-only authority and cannot silently promote inferred facts.

`tests/test_transcript_actions.py` covers compilation, provenance, explicit approval, unknown-ID
rejection, missing inputs and source/output collision. Together with the SkillTree integrity tests,
six focused tests pass. The refreshed 137-node registry now records five implemented, two external,
two partial, five available, two blocked and 121 documented capabilities. The remaining partial
nodes are Deck Production and Monitoring & Alerting; Call Capture remains available rather than
implemented because universal recording and consent capture are still absent.

## 2026-07-22 — SOP Generation and live orchestrator efficiency evidence

- Added `twin_core/sop_compiler.py` and `scripts/compile_sop.py`. The compiler admits only
  approved successful workflow steps repeated across at least two independent runs, binds exact
  source hashes and line ranges, rejects escape/tamper/inconsistent sequences, and remains
  draft-only until a separate named release receipt.
- Added `tests/test_sop_compiler.py`; the SOP and SkillTree integrity set passes 6/6.
- Refreshed the immutable-export-derived registry without changing the export: 6 implemented,
  2 external, 2 partial, 5 available, 2 blocked, 120 documented.
- Recorded the real-runtime efficiency audit in
  `architecture/ORCHESTRATOR_EFFICIENCY_RUNTIME_AUDIT_2026-07-22.md`: 99 control tests pass;
  cache/host/context/effort controls are active; semantic closure size remains the next measured
  token target.
- Hardened the semantic judge at orchestrator revision `7f3dcf8` to perform one exhaustive review
  and return every known actionable finding together. The focused regression set passes 27/27.
  Its first live JAA-01 use returned two independent defects in one verdict, replacing two likely
  serial judge/fix cycles while preserving host assurance and final semantic independence.

## 2026-07-22 — SkillTree Deck Production promotion

- Promoted **Deck Production** from partial to implemented at A1 draft authority. Added
  `scripts/render_external_proof_deck.mjs`, which validates the existing external-proof manifest
  and renders six editable PowerPoint slides through `@oai/artifact-tool`; each claim slide carries
  its exact evidence in speaker notes and no publication authority is granted.
- Produced `outputs/external-proof/virtual-twin-trust-kernel/virtual-twin-trust-kernel.pptx` and a
  hash-bound `deck-qa.json`. The generic slide overflow gate passed, all six slides were rendered
  and inspected individually, and independent OOXML tests prove six slides, six notes pages, all
  five claim IDs, the human-review warning and exact manifest/renderer/PPTX/render hashes.
- The refreshed immutable-export-derived registry now records 7 implemented, 2 external, 1
  partial, 5 available, 2 blocked and 120 documented capabilities. Twelve focused external-proof,
  Deck Production and SkillTree audit tests pass. The source export remains unchanged.

## 2026-07-22 — first ECC-derived implementation: read-only operator status

- Implemented `giga.operator-status.v1` as a deterministic repository-local compiler, CLI and
  published JSON Schema. Its ten stable sections use typed evidence envelopes; absent runtime
  signals remain `unknown`, never green or zero.
- The compiler reads only contained evidence and has no network, Git, subprocess, tracker, session
  control or orchestrator authority. Optional runtime packets are rejected when malformed,
  unsupported, future-dated or path-escaping, and are marked `stale` after the declared threshold.
- Added a canonical snapshot and reconciled human/machine summaries. The owned project suites pass
  70 tests, including negative controls and schema/compiler parity. Unconstrained repository-wide
  pytest remains an invalid boundary because it collects archived foreign repositories under the
  corpus and upstream trees; `pytest tests ecc-integration/tests` is green.
- Updated the ECC import ledger for this one read-only import and expanded Monitoring & Alerting
  evidence. The refreshed SkillTree audit intentionally retains that node as `partial` and
  ineligible to advance: live cross-service telemetry and the Integration Builds prerequisite are
  still incomplete.

## 2026-07-22 — second ECC-derived implementation: adapter evidence registry

- Implemented `giga.adapter-evidence.v1` manifests and the compiled
  `giga.adapter-registry.v1`. The compiler requires explicit supported assets, unsupported
  surfaces, authority, owner, risks, onramp, verification commands, source documents, evidence
  paths and a timezone-aware verification timestamp.
- Every local proof file is root-contained and SHA-256 hashed. Consumers re-hash the registry
  before trusting it; changed, missing, malformed, duplicated, future-dated, absolute,
  path-escaping or symlinked evidence fails closed. Stale adapter claims degrade to
  `reference-only`.
- Manifest commands remain inert strings: compilation executes none, and the registry explicitly
  grants no authority. The first registered adapter is the native read-only operator-status
  compiler; live tools, agents, costs, queues and session mutation remain unsupported.
- Operator status now consumes and re-validates the registry. The owned giga/ECC suite passes 90
  tests, with 34 focused contract/integration/audit checks. The SkillTree audit keeps Integration
  Builds `documented` and Monitoring & Alerting `partial`/ineligible; stronger governance evidence
  did not manufacture live integration or monitoring capability.

## 2026-07-22 — pinned ECC portable extraction completed

- Recorded repository-wide deterministic enforcement as deferred in
  `ecc-integration/FUTURE_WORK.md`, with an explicit freeze against rewiring giga-user before the
  extraction was complete and a separate later design/approval gate.
- Completed portable extraction for pinned ECC commit `96789ca`: all 3,330 inventoried files now
  hash-verify, all 278 canonical skills have dispositions, and all 11 adaptation candidates map to
  an imported, already-covered or named deferred finding. The upstream checkout remains clean.
- Added seven consolidated staged specifications covering evaluation/compliance, operational
  assurance, capability-surface/token-tax policy, session snapshots and collision advisories,
  version-bound human approval, independent-product integration and recursive decision ledgers.
  No ECC runner, hook, installer, server, UI or authority surface was imported.
- `PORTABLE_FINDINGS.json` now contains 15 source-hashed findings and the import ledger contains 12
  exact entries. `scripts/validate_extraction.py` validates all 3,330 hashes, commit/coverage
  consistency, contained destinations and ledger coverage; tampered hashes, missing candidates and
  destination escape fail closed.
- The completion audit found one stale `yarn.lock` record in the old inventory. The clean pinned Git
  blob was authoritative; the inventory was corrected and its generator now uses `git ls-files`,
  excluding ignored coverage/bytecode artifacts. A fresh inventory replay is exact.
- Final validation: 102 owned giga/ECC/staging tests pass. The extraction-complete receipt is
  `ecc-integration/EXTRACTION_COMPLETE.md`. This completion permits a later architecture review of
  deterministic enforcement; it does not itself authorise global rewiring.

## 2026-07-22 — cross-service telemetry

- Added `twin_core/cross_service_monitor.py`, its CLI, declarative service manifest, live evidence
  packet and tests. The collector is read-only, bounded, and cannot execute content from the
  manifest. It detects silent stalls, dead processes, missing/malformed sources and future events.
- The first real observation reported the stopped orchestrator and stale Jarvis heartbeat as
  degraded, then fed those states into operator status. Monitoring & Alerting remains partial
  because Integration Builds is still a documented-only prerequisite.

## 2026-07-22 — deterministic execution-boundary design

- Completed the architecture review authorised by the ECC extraction-complete receipt. The durable
  decision is `architecture/10_DETERMINISTIC_EXECUTION_BOUNDARY.md`; it is explicitly design-only,
  grants no authority and does not rewire any live path.
- Selected a small in-process deterministic policy kernel, one canonical execution-capability
  registry and a static bypass audit over declared official entry points. Rejected documentation
  alone as unenforceable and deferred a daemon/MCP gateway because its operational and token tax is
  not justified by the current local process model.
- Source inventory found two current proposal callers sharing the safe Telegram lifecycle, a
  duplicate direct provider implementation in the daily prediction worker, direct Jarvis process
  launch, direct network notifications and standalone mutation surfaces. The design makes these
  explicit migration boundaries rather than falsely claiming a global gate already exists.
- Separated database, request-contract and registry version domains. The first shadow and Telegram
  slices can run on live TwinStore schema v2; schema v3 remains a separate controlled migration
  decision under its existing readiness receipt.
- Proposed Telegram memory proposal routing as the first later enforcement slice because it already
  has idempotent replay, no-tool typed model proposals, deterministic validation/commit and durable
  receipts. Repository-wide enforcement remains unapproved until coverage, bypass, ordering,
  repeat-stability, recovery, approval-binding, cost and rollback gates pass.
- No SkillTree status or evidence declaration changed. Integration Builds remains documented and
  Monitoring & Alerting remains partial.

## 2026-07-28 — provider-neutral scientific evidence acquisition

- Replaced the paid-Elicit dependency with a provider-neutral acquisition layer covering Europe
  PMC, PubMed, Semantic Scholar, OpenAlex, ClinicalTrials.gov, Crossref and Unpaywall. Elicit
  remains optional and paid; it is no longer required for the skin evidence campaign.
- Bound every acquisition to its provider in the append-only hash-chained ledger. Complete raw
  JSON is retained, while API keys and provider-required contact emails are excluded from the
  immutable request envelope. Official-host checks and credential rejection fail closed.
- Added direct ClinicalTrials.gov search, Crossref DOI verification, Unpaywall lawful-OA
  resolution and SHA-256 registration of papers already held lawfully. Sci-Hub, Z-Library,
  credential sharing and paywall circumvention are explicitly unsupported.
- Added a provider-expanded, network-free-by-default campaign runner. The reliable default is
  Europe PMC plus PubMed; Semantic Scholar became opt-in after its unauthenticated live endpoint
  returned HTTP 429. OpenAlex and Unpaywall are configuration-gated.
- Bounded live checks passed for Europe PMC, PubMed, ClinicalTrials.gov and Crossref, with clean
  temporary ledger audits. The provider contracts and complete owned suite pass 153 tests.
  Scientific conclusions, full campaign completion, treatment ranking and medical execution
  authority remain unclaimed; all outputs remain A0 until source-specific human appraisal.

## 2026-07-28 — skin-texture evidence campaign sensitivity pass

- Executed all 37 prespecified skin-texture, photoaging, collagen and scar queries through Europe
  PMC, PubMed and ClinicalTrials.gov into a dedicated append-only ledger. The ledger audit passes
  with 71 acquisition entries and 1,968 retained provider records.
- Added a deterministic analysis stage that deduplicates by DOI, PMID, NCT identifier and exact
  normalized title/year, without destroying provider provenance. It produced 1,761 candidate
  groups, collapsing 207 duplicate retrievals, plus screening and lawful-full-text queues.
- Added separate hashes for canonical queue payloads and the exact CSV files. Repeated generation
  is byte-identical. A validation test exposed and fixed accent handling in normalized titles.
- The sensitivity pass is not an effectiveness ranking. Inspection identified substantial
  off-topic noise because long natural-language research questions were passed to lexical
  biomedical engines. The protocol now requires provider-appropriate query refinement and formal
  eligibility screening before appraisal or treatment conclusions.
- Focused scientific tests pass 38/38; the owned `tests/` suite passes 158/158. Unbounded
  repository-root pytest remains invalid because it collects duplicated archived and upstream
  repositories as live test modules.

## 2026-07-28 — deterministic scientific-list processing

- Implemented the versioned ontology and provider-specific search compiler for all 37 skin
  questions and two unrelated negative controls. Compiled campaigns fail closed rather than
  falling back to the original natural-language questions.
- Added deterministic canonicalization, provenance-preserving exact deduplication, review-only
  fuzzy pairs, reason-coded eligibility proposals, source-located ontology features, study-design
  buckets, prioritization, PRISMA accounting, exclusion sampling and LLM ambiguity queues. An LLM
  is not invoked by default and has proposal-only authority under a verbatim-span contract.
- Added human-bound duplicate decisions, lawful full-text routing, hardened Europe PMC XML
  acquisition/extraction, an owner-only append-only actor-bounded review ledger, replay-resistant
  search saturation and a fail-closed screening-readiness report.
- Regenerated the broad pass deterministically: 1,968 records map to 1,755 groups after 213 exact
  retrieval duplicates; 130 inclusion, 1,116 exclusion and 509 manual-review proposals; four
  possible duplicate pairs; 639 full-text plans. The 5,265-event review ledger audits clean.
- The compiled live pilot now routes incomplete-metadata hits to manual review: 400 records form
  385 groups with 209 inclusion, 170 manual-review and six non-research-publication exclusion
  proposals. Negative controls pass 38/38. The broad output replay was byte-identical.
- The readiness gate remains correctly red: duplicate resolution, false-exclusion audit, final
  human screening and genuine cumulative search saturation are incomplete. Full-text appraisal,
  synthesis, ranking, medical recommendation and execution authority remain false.
- Added `research/elicit/skin-texture/DETERMINISTIC_PIPELINE_REPORT.md`. Focused scientific tests
  pass 59/59 and the complete owned suite passes 179/179.

## 2026-07-28 — full compiled skin research run

- Executed all 37 refined skin-texture, photoaging, collagen and scar questions as 71
  provider-specific jobs into a new owner-only ledger. Europe PMC, PubMed and
  ClinicalTrials.gov returned 6,108 records; all 71 acquisitions and the ledger hash chain audit
  clean.
- A live PubMed chunked transfer failed after 47 jobs were durable. Exact replay skipped those
  jobs and acquired only the remaining 24, proving resumability under a real network failure.
- Final v4 projection maps 6,108/6,108 records and 37/37 questions, collapses 1,964 exact
  duplicate retrievals into 4,144 groups, flags five near-duplicate pairs, and emits 2,248
  inclusion, 28 exclusion and 1,868 manual-review proposals plus 4,116 lawful full-text plans.
  The 12,432-event review ledger audits clean and no LLM was called.
- Real-data audit corrected four unsafe projection defects: editorial labels conflicting with
  research designs now go to manual review; porcine filler material is not treated as an animal
  model; shared expressions are disambiguated by request limit; and control-only ontology labels
  cannot pollute main intervention-family or saturation accounting.
- The final projection replay is exact at artifact-tree SHA-256
  `e8890ea6aef04acd1fc146e54de0c258123923499f00d8e8560892f3d7b8c676`.
  Readiness remains correctly red for five duplicate decisions, the 11-record exclusion audit,
  human screening and saturation. Full text, synthesis and treatment ranking remain unclaimed.
- Durable run report:
  `research/elicit/skin-texture/COMPILED_RESEARCH_RUN_2026-07-28.md`.

## 2026-07-29 — six-stage scientific review funnel

- Implemented a deterministic metadata → abstract → evidence hierarchy → selective full-text →
  condition/intervention grouping → appraisal/synthesis funnel in
  `twin_core/scientific_review_funnel.py`, exposed through `scripts/scientific_pipeline.py`.
- Added official PubMed EFetch abstract batching at 200 PMIDs, queue-wide retrieval,
  identifier-exact enrichment, conflict preservation and automatic feature/eligibility
  recomputation. Existing abstracts are never overwritten; any applied abstract changes its
  SHA-256 and invalidates stale human eligibility decisions.
- Added strict contracts for abstract decisions, full-text study extraction and synthesis
  sign-off. Full-text extraction now requires population, protocol, comparator, sample size,
  outcomes, source-located effects, follow-up, harms, withdrawals, funding, conflicts,
  applicability and risk of bias.
- Evidence prioritisation starts with guidelines/systematic reviews, then controlled trials,
  observational safety/durability evidence and lower designs. Trials retain an explicit
  reference-coverage check rather than being silently treated as covered by a review.
- Effectiveness ranking fails closed unless the duplicate report is hash-valid and complete,
  every eligibility decision is abstract-hash-bound, every selected study has verified
  full-text extraction, bias/effects/harms/conflicts are complete, and a human signs the exact
  comparison-matrix hash. Recommendation authority remains false even after those gates.
- Real-data execution processed all 4,144 groups and queued 2,144 missing abstracts: 1,485 have
  PubMed routes, 277 have PMC routes, 1,361 have DOI routes and 655 lack a machine identifier.
  All review and ranking gates remain correctly red; no LLM was called.
- Focused research tests pass 67/67; canonical owned tests pass 192/192; schemas parse, code
  compiles and diff hygiene passes. Root-recursive pytest remains invalid because it collects
  archived corpus and upstream repository copies under duplicate Python module names.
