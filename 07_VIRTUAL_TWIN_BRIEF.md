# Session 07 — Virtual-twin control plane

*Read `00_MASTER.md` and `01_CHARTER_BRIEF.md` first. Mission: turn the evidence, memory and
services already in GIGA into a local-first virtual twin that remembers accurately, supports
Artiom's decisions, observes outcomes and earns bounded authority through measured gates.*

## Non-negotiable boundaries

- Raw exports are immutable. Derived processing always creates new files and retains source
  hashes.
- Markdown memory is the human-auditable personal canon. The operational SQLite store is an
  event/receipt/index layer, never a competing biography.
- Market Aligner and application automation remain an independent commercially viable product
  lane. Session 07 may design an event adapter only after that boundary stabilises; it may not
  pause, rewrite or physically absorb the product.
- Fine-tuning changes behavioural priors, not current facts. No model training or third-party
  upload occurs until the operator authorises the reviewed dataset and locked evaluation.
- External action authority is earned by gates: observation and advice precede execution;
  irreversible, identity-sensitive, financial and high-impact actions require operator control.

## Required sequence

1. Evidence protection and three discovery depths.
2. Explicit virtual-twin target, memory model and authority model.
3. Dependency-ordered transition roadmap with measurable promotion gates.
4. Trust kernel: append-only events, idempotent processing, receipts, derived-artefact lineage,
   memory validation, health and maturity truth.
5. Transactional capture and backfill under crash/retry/injection tests.
6. Memory-accuracy retrieval and locked evaluation.
7. Goal, preference, decision and outcome operating system in shadow mode.
8. Read-only external state and daily counsel.
9. Mode-specific speaking style, then thinking/self-scrutiny evaluation.
10. Bounded agency and domain adapters only after their gates pass.

## Canonical artefacts

- `architecture/00_DISCOVERY_INDEX.md` through `05_TRANSITION_ROADMAP.md`
- `architecture/EXPORT_IMMUTABILITY_BASELINE.sha256`
- `twin_core/`
- `tests/test_twin_store.py`, `tests/test_integrity.py`, and memory/runtime tests
- `SESSION_LOGS/07_log.md`

## Done when

The target is not “a chatbot that sounds like Artiom.” Completion requires empirically accurate
memory, useful and calibrated decisions, explicit source/authority/receipt trails, safe external
state integration, mode-correct behaviour, provider independence, recovery drills and proven
bounded agency. Each phase promotes only when its test gate passes.
