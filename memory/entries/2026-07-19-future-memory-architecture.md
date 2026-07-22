---
type: reminder
tags: [jarvis, memory-system, architecture, backlog, non-priority]
created: 2026-07-19
trigger: after Sessions 04 and 05, or when the memory store exceeds 100 entries / new GPT or Discord exports have been ingested
status: active
---
Develop Jarvis's mature personal-knowledge architecture. **Not a current priority.**

Scope when triggered:

- deterministic memory packet assembled before every model call — no reliance on the model
  remembering to read files;
- bounded always-loaded core (`CONTEXT.md`) plus learned working set;
- query router over entries with one-hop linked-neighbour prefetch;
- cold-corpus retrieval for verification and gap recovery, never bulk context loading;
- provenance, as-of dates, contradiction detection, supersession and confidence;
- derived personal knowledge graph, rebuilt from canonical sources rather than hand-maintained;
- identical provider-neutral packet for Claude, GPT, local models and future models;
- cache/KV-cache optimisation treated only as an expendable performance layer;
- measurable retrieval, confusion, false-memory and stale-memory evaluations.

Done means Jarvis can manage a 500–1000 MB personal-knowledge bank without context bloat,
silent contradictions or provider lock-in, and every answer can trace important claims back
to source evidence.

Rationale: the present file/index protocol is sufficient for the current small store. Building
the full architecture before the corpus and retrospective/calibration data mature would be
premature optimisation.

Source: operator decision, 19 Jul 2026: “for the future ... set a task (not prio) to develop
a memory architecture”. Related: [[2026-07-18-bot-maturation-roadmap]],
[[2026-07-18-memory-derived-not-dictated]], [[2026-07-18-canon-hierarchy]].
