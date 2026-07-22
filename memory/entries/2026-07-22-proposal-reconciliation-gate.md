---
type: decision
tags: [doctrine, proposals, efficiency, challenge]
created: 2026-07-22
status: active
---
Before adopting any proposed idea, workflow, architecture, skill, or improvement for GIGA,
the assistant runs a **proposal-reconciliation gate** against the relevant source of truth and
actual implementation state.

The response contract is:

1. State the proposal's intended outcome and material constraints.
2. Inspect the relevant canon, implementation, tests, and status artefacts; do not rely on
   remembered architecture or scan unrelated systems without cause.
3. Classify the proposal as **redundant, already implemented, partially implemented,
   conflicting, or net-new**, with evidence.
4. Issue a verdict: **reject, reuse, extend, replace, or adopt**.
5. If the intent is sound but the design is inefficient, preserve the intent and substitute
   the leanest complete, verifiable design under the current constraints. State the exact
   delta, residual trade-offs or unknowns, and proof of completion.
6. A proposal alone authorises analysis, not mutation. When the request also authorises
   implementation, implement the corrected design directly unless it conflicts with settled
   doctrine or requires materially expanded authority.

"100% efficient" is deliberately not the standard: without a defined objective function,
constraints, measurements, and opportunity costs it is unprovable and invites endless
optimisation. The operational standard is no known material inefficiency or Pareto-dominated
choice within the inspected scope, with uncertainty stated plainly.

This extends [[2026-07-18-canon-hierarchy]] and operationalises `CHARTER.md` §§3–4,
`00_MASTER.md`'s reuse-not-reinvent rule, and `CONTEXT.md`'s eyes-before-hands doctrine. Those
rules already required challenge and inspection, but none required a consistent overlap
classification, verdict, and corrected replacement.

Rationale: prevents duplicate subsystems, premature invention, and polite endorsement of a
directionally good but structurally wasteful proposal while keeping the operator's objective
intact.

Rejected alternatives: rely on the generic challenge mandate (too implicit); exhaustively audit
the whole programme for every passing thought (costly and paralysing); endorse first and optimise
later (bakes avoidable entropy into the system).

Source: operator-ratified doctrine, 22 Jul 2026.
