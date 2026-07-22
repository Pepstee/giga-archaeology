---
type: idea
tags: [memory-system, needs, tasks, automation, virtual-twin]
created: 2026-07-21
status: active
---
Add a durable **Need to do** read-model to the second memory. It has two capture paths:

1. A direct operator statement such as "I need to ..." becomes an accepted active need.
2. A need inferred from conversations or corpus evidence becomes a proposal with its source
   excerpt and confidence; it does not become active until the operator accepts or edits it.

Every accepted need must have an outcome, a concrete next action, a trigger or review point,
dependencies, and observable completion evidence. The system must distinguish one-off needs,
habits, projects, appointments and purchases, and must never treat an LLM inference as proof
that something was completed. `memory/entries/` remains the source of truth; `memory/NEEDS.md`
is only a generated operational view.

This extends [[2026-07-18-memory-derived-not-dictated]]: automated derivation remains the
default, but task activation is a separate consent boundary. It also gives the virtual twin
in [[2026-07-18-bot-maturation-roadmap]] a missing action layer between recall and agency.

Source: direct operator design request, 21 Jul 2026.
