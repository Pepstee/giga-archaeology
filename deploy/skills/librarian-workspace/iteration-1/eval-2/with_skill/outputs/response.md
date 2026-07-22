Before we plan anything: a standing reminder just fired on this exact topic, and it changes what this review is.

**Reminder surfaced — [[2026-07-16-reminder-p0-isolation-drill]]** (trigger: "when discussing v3 Slice 9 planning, P0 certification, or Theseus"). This is its second firing. First firing, 17 Jul: Slice 9 certified WITHOUT the isolation-loss drill, and the overseer confirmed it was worse than stated — v3 has no worktree/sandbox creation site, and `infra/workspace.py task_workdir()` silently falls back to the shared project tree, the exact masking R-102 forbids. The overseer enqueued a scoped improvement round. So per memory, this review is not a routine certification pass — it is a re-certification of a slice whose original certification is known-deficient on R-102.

That gives the review three non-negotiable gates (the reminder's exit conditions):

1. `tests/test_isolation_loss_drill.py` exists in v3's tree — failure injection plus back-to-valid companion.
2. The `task_workdir()` fallback is loud and gating — a failed workspace create must never become a silent ungated run on the shared tree.
3. Re-run the inheritance detector `claude-orchestrator-main/scripts/repro_worktree_orphan.py` against v3 — exit 0 means the defect was inherited; the gate requires non-zero.

Only when all three hold does the reminder retire — and even then it re-arms once at Slice 20 (Theseus). I've amended the entry with this second firing (acting, not rescheduling) and folded the gates in; index updated.

Two framing notes from the rest of memory:

- [[2026-07-16-standing-decisions-orchestrator]]: v2 stays frozen — anything this review finds flags forward into v3 as acceptance criteria with inheritance-detector tests, never as v2 patches. The review report should be written in that shape from the start: finding → v3 acceptance criterion → detector test.
- [[2026-07-16-reminder-v3-notification-trail]] stays dormant unless Slice 9's scope touches the operator/notification channel — if it does, its three checks (journaled sends, provider-correct remedies, no self-calling handlers in the notify path) join the gate list. Tell me if that's in scope.

Proposed skeleton for the review plan:

1. **Status check** — did the overseer's scoped improvement round land? (Does the drill test exist yet? Does the fallback gate?) This decides whether we're reviewing a fix or chasing one.
2. **Gate verification** — the three items above, run in order; the detector run is the evidence artifact.
3. **Scope sweep** — the rest of Slice 9's certified claims, re-checked against the same standard: no silent fallbacks at any seam.
4. **Report** — findings as forward-flagged acceptance criteria per the standing decisions; Slice 20 re-check noted.

Where do you want to start — shall I check v3's tree for `tests/test_isolation_loss_drill.py` and the `task_workdir()` gating first? And confirm whether the operator channel is inside Slice 9's scope. I'll file the review plan as a decision entry once you ratify the shape.
