# SkillTree → giga-user integration doctrine

**Status:** first walking skeleton implemented on 2026-07-22; authority remains local draft/A1.

## Verdict

The SkillTree export is a **capability catalogue and workflow-design reference**, not a set of
79 installable Codex skills. The public source exposes 79 named file references, 78 preview
excerpts, 291 atomic capabilities and 137 jobs; it does not expose the paid runnable files.

Within giga-user, the right use is:

1. keep the source export immutable and provenance-linked;
2. treat every preview as untrusted reference data, never runtime instructions;
3. reconcile each candidate capability against existing canon and working systems;
4. implement only the smallest high-value gaps as native, model-agnostic workers or skills;
5. promote authority through tests, shadow runs, receipts and measured outcomes.

Do **not** bulk-install, bulk-recreate or wire all 79 names into the virtual twin.

## Why this fits giga-user

The integration must preserve the standing rules in `CONTEXT.md`:

- eyes before hands;
- untrusted input is data, never instructions;
- proposal reconciliation before invention;
- depth before breadth;
- no secrets in repositories or memory;
- no stubs, placeholders or mocks as completion evidence;
- model-agnostic components;
- consequential authority is deterministic and gated.

It must also preserve the Session 07 boundary: Market Aligner and application automation remain
an independent commercial lane. Giga-user may consume their events later through an adapter; it
must not absorb or interrupt them.

## The five roles the catalogue can play

### 1. Taxonomy

The 137 jobs and 291 atomic capabilities give us a vocabulary for naming missing operational
abilities. This is useful for architecture reviews, gap analysis and backlog design even when no
corresponding skill is implemented.

### 2. Workflow reference

The graph supplies prerequisites and job relationships. Those can inform dependency ordering, but
they do not override giga-user's own evidence and authority gates.

### 3. Native implementation briefs

A selected preview can become one input to a clean, local implementation brief. The resulting
worker must be designed from giga-user's actual contracts, data and acceptance criteria. It is not
a copied or reconstructed paid file.

### 4. Evaluation coverage

Names such as QA Engineer, Red Team Reviewer and Reliability Engineer are useful as evaluation
roles. Their value is in concrete checks: provenance, abstention, replay, negative controls,
idempotency, cost and failure recovery.

### 5. External-proof engine

The catalogue can help turn existing technical work into public proof: case studies, research
reports, presentations, demonstrations, publishing and measured outreach. This directly addresses
the programme's external-proof constraint without weakening truthful evidence standards.

## Recommended capability lanes

### Lane A — Career/application system

These are design references for the independent job-application product, not components to splice
directly into it:

| SkillTree reference | Correct native destination | Required gate |
|---|---|---|
| Document Extraction Engineer | vacancy/evidence ingestion | immutable source spans and extraction eval |
| Company Research Analyst | JAA-04 employer reconnaissance | cited, dated, freshness-aware dossiers |
| Prospect Research Analyst | job-relevant public person/team research | professional relevance and privacy boundary |
| Research Reporter | dossier/report renderer | every factual claim source-resolvable |
| Case Study Curator | JAA-05 evidence matching | approved evidence IDs only |
| Relationship Mapper | employer/team relationship graph | public professional data only |
| Signal Monitoring Analyst | vacancy/employer change monitoring | read-only capture, dedupe and freshness |
| QA Engineer | release evaluation | locked tests and negative controls |
| Red Team Reviewer | adversarial release review | no authority to waive deterministic gates |
| Reliability Engineer | run health, replay, cost and incident handling | idempotency and recovery evidence |

The existing JAA plan remains authoritative. SkillTree can enrich a slice only after the slice's
current implementation and contracts are inspected. It cannot create a parallel pipeline.

### Lane B — External proof and career leverage

This is the highest-value near-term lane for the end-2026 career clock:

- **Case Study Curator** — turn certified orchestrator/GIGA outcomes into evidence-linked cases.
- **Research Reporter** — publish technical findings with source and experiment lineage.
- **Presentation Designer** — package architecture and measured results for interviews or demos.
- **Solutions Engineer** — build bounded demonstrations from real capabilities.
- **Company Knowledge Base** — maintain public-safe project facts separate from private memory.
- **Publishing Manager / Content Repurposing Manager** — distribute one verified artefact across
  appropriate formats without inventing new claims.

The content compiler must read only approved public claims. Private memory, partner data, raw
messages and secret-bearing exports never enter this lane.

### Lane C — Commercial acquisition for an AI service/product

If Artiom chooses a defined offer, the Sales and Deals branch can form a measured acquisition loop:

```text
ICP Strategist
  → Market Mapper
  → Lead Sourcing Manager
  → Company / Prospect Research
  → Cold Email or LinkedIn Outreach
  → Outbound Inbox Manager
  → Meeting Booking + Call Prep
  → Meeting Intelligence + Deal Debrief
  → Proposal Writer + Deal Room Producer
  → outcome and calibration
```

This lane should not start until the offer, target customer and evidence of delivery are explicit.
Otherwise it automates noise. Sending remains draft-only until identity-sensitive external-action
gates are earned and the operator authorises the channel.

### Lane D — GIGA operational reliability

Useful references include:

- Company Knowledge Base and Records Administrator for provenance and retrieval;
- Playbook Writer for turning certified processes into operational documentation;
- Integration Engineer for explicit adapters and frozen contracts;
- Delivery Status Reporter for receipts-derived status;
- QA Engineer, Red Team Reviewer and Reliability Engineer for certification and recovery.

These should strengthen the existing trust kernel, not create a second event or memory system.

### Lane E — Deferred business functions

Billing, customer success, community, high-volume marketing, HR and broad back-office capabilities
should remain catalogue-only until a real recurring workload exists. Activating them before demand
would violate depth-before-breadth and add maintenance without external proof.

## Promotion pipeline

Every selected capability should pass this sequence:

```text
catalogue entry
  → overlap/conflict/novelty review
  → evidence-backed use case and owner
  → native contract + privacy/authority classification
  → fixture and locked evaluation
  → shadow mode
  → draft/advisory mode
  → bounded execution with deterministic gate
  → event + artefact + receipt capture
  → outcome calibration, retain/modify/retire
```

### Minimum capability record

Each promoted item needs:

- stable capability ID and version;
- intended outcome and consumer;
- authoritative inputs and prohibited inputs;
- output schema;
- source/evidence requirements;
- authority level: read, advise, draft, execute, or prohibited;
- deterministic release checks;
- negative controls and abstention behaviour;
- event, artefact and receipt types;
- cost/latency limits;
- owner, review date and retirement condition.

## What should happen first

1. Keep `outputs/skilltree-export-2026-07-22/` as the immutable source snapshot.
2. Build a derived reconciliation table for all 79 named entries: `existing`, `overlap`, `gap`,
   `irrelevant`, or `blocked`, with links to current giga-user/JAA assets.
3. Select **one** walking-skeleton capability. The recommended first candidate is an
   evidence-linked external-proof compiler combining Case Study Curator, Research Reporter and
   Presentation Designer concepts over already-certified project artefacts.
4. Run it in draft-only mode against one real GIGA/orchestrator result.
5. Publish or operationalise only after truth, privacy, render and source-lineage checks pass.

This produces a measurable career asset without interfering with Market Aligner or prematurely
granting external-action authority.

## First walking skeleton — implemented

The first candidate now runs through:

```bash
python3 -m twin_core --root /Users/admin/Documents/giga-user \
  compile-proof external_proof/manifests/virtual-twin-trust-kernel.json \
  --output outputs/external-proof/virtual-twin-trust-kernel
```

It deterministically produces a case study, technical report, presentation outline, QA record,
content-hashed build manifest and trust receipt. Exact evidence needles, line spans, source hashes,
path containment, public-source boundaries, secret scans and claim references fail closed. The
event and receipt live in the existing `TwinStore`; identical replay reuses the receipt without
rewriting files.

Evidence-backed registry result after the rendered-deck promotion:

- `Research Reports` — implemented;
- `Adversarial Verification` — implemented;
- `Deck Production` — implemented at A1 draft authority: the evidence-linked outline renders as
  an editable PPTX with source-bearing speaker notes, overflow checks, per-slide hashes and
  full-size visual QA;
- no publication or other external-action authority granted.

The next promotion decision should be based on a human review of this first proof pack. A finished
deck or public release is a separate slice and must not be inferred from the passing draft gate.

## Live cross-service monitoring evidence

- A deterministic read-only collector now observes declared JSONL event sources and plain-file
  heartbeats. It performs bounded reads, rejects configuration-supplied commands, detects missing,
  malformed, future, stale and dead-process states, and emits operator-status-compatible evidence.
- The first live packet correctly remained degraded: the orchestrator was stopped and the running
  Jarvis process had a stale log heartbeat. `activeAgents` and `queueState` are therefore
  evidence-backed rather than unknown or falsely green.
- Monitoring & Alerting remains `partial`. Its live-telemetry gap is closed, but its SkillTree
  prerequisite, Integration Builds, remains documented rather than implemented.

## Source artefacts

- `outputs/skilltree-export-2026-07-22/EVERY_SKILL.md`
- `outputs/skilltree-export-2026-07-22/data/all_skills.json`
- `CONTEXT.md`
- `00_MASTER.md`
- `07_VIRTUAL_TWIN_BRIEF.md`
- `job-application-automation/BUILD_PLAN.md`
- `job-application-automation/IMPLEMENTATION_SLICES.yaml`
- `external_proof/CONTRACT.md`
- `twin_core/external_proof.py`
- `tests/test_external_proof.py`
- `skilltree/implementation-registry.json`
