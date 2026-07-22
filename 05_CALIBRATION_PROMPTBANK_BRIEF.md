# Session 05 — Calibration & the Prompt Bank

*Read `00_MASTER.md` first. Mission: two pieces of standing infrastructure that close the
programme. First, a personal prediction ledger — he estimates constantly ("P0 by the
weekend") and never scores himself; his own orchestrator now calibrates its thresholds
empirically, and he deserves the same instrument. Second, a prompt-pattern bank — his proven
briefs (Mode A/B/C reviews, the cost audit, the session briefs in this folder) are elite
prompt engineering that currently gets re-improvised instead of reused.*

## Deliverables

1. **Automated SQLite prediction loop** — operator override, 20 Jul: he makes no manual
   predictions. AI generates falsifiable forecasts from captured behaviour and input; code
   precommits them, validates later evidence and computes calibration at scale. The loop must
   prevent hindsight, selective resolution and self-confirming labels. Canonical design and
   deployment are in `PREDICTION_AUTOMATION.md`.
2. **Accumulate automatically**: no hand-seeded forecasts. The daily Jarvis run grows the
   ledger quietly; the first scoring review happens only after a meaningful resolved sample.
3. **`promptbank/`** — the pattern bank. Harvest, generalise, and file his proven patterns:
   the invariant-analysis brief (Mode A), inverted-concern (Mode C), the cost-audit brief,
   the "rule" preamble (claims→executable), the session-brief pattern this folder uses, plus
   2–3 more mined from his corpus if Session 04 has run. Each entry: when to use, the
   template with slots, one real usage example, and what makes it work. Index in
   `promptbank/README.md`.
4. **`REVIEW_CADENCE.md`** — the standing rhythm that keeps all five workstreams alive: the
   monthly sweep (retrospective run, ledger scoring, context-doc refresh, charter amendments)
   as ONE checklist with an estimated 60-minute budget. This document is the programme's
   maintenance contract — the difference between infrastructure and a burst of enthusiasm.

## Method notes

- Calibration honesty: the first scoring will likely be humbling — frame scores as data,
  never judgement; the orchestrator's discard-rate framing ("falsified = the process working")
  applies verbatim.
- The prompt bank is pull-infrastructure: entries must be findable by problem ("I suspect a
  specific bug" → Mode C), so the index is organised by situation, not by name.
- Keep both tools boring and file-based — they must outlive any particular AI product.

## Done when

Ledger live with seeded predictions and a working scorer; prompt bank holds ≥6 patterns with
real examples; review cadence written and first monthly sweep scheduled; log + master table
updated. Programme complete — the last act of this session is a short `PROGRAMME_REVIEW.md`:
what the five sessions built, what remains hypothesis, and the one metric to watch per
workstream.
