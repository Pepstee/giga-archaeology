Before we plan anything, a standing reminder fires on exactly this trigger — and it has history you'll want front and center.

**Reminder surfaced: P0 isolation-loss drill (R-102, milestone-gating) — ACTIVE, second firing**

It already fired once, on 17 Jul, when Slice 9 certified *without* the drill. The overseer then confirmed it was worse than stated: v3 has no worktree/sandbox creation site at all, and `infra/workspace.py task_workdir()` silently falls back to the shared project tree — the exact masking R-102 forbids. A scoped improvement round was enqueued: loud+gating at that seam, plus `tests/test_isolation_loss_drill.py` (failure injection + back-to-valid companion).

So framing matters: this is not a fresh certification — it's a re-certification review after a failed one, and the reminder's own exit criteria are your gate.

**Proposed review agenda (gates, in order):**

1. **Drill test exists and is wired in.** `tests/test_isolation_loss_drill.py` is present in v3's tree with both the failure-injection case and the back-to-valid companion — and it's referenced by Slice 9's acceptance criteria, not just sitting in the tree.
2. **The seam gates.** `infra/workspace.py task_workdir()`: a failed sandbox/worktree create must be loud and gating. Any silent fallback to the shared project tree is an automatic fail.
3. **Inheritance detector re-run.** `claude-orchestrator-main/scripts/repro_worktree_orphan.py` against v3's implementation. Exit 0 means v3 inherited the defect — hard fail.
4. **Doctrine compliance.** Per the standing decisions: the cure lives in v3 only (v2 stays frozen; defects flag forward with inheritance-detector tests as acceptance criteria). The detector run should go into the certification record.
5. **Close the loop in memory.** If gates 1–3 pass: certify, and I amend the reminder — Slice 9 satisfied — but it stays active with its remaining trigger: re-check at Slice 20 (Theseus). It does not get archived yet.

One constraint: this session only sees the memory folder, not v3's tree, so I can't run the detector or confirm the test file myself. Either attach the orchestrator folder here, or run gates 1–3 on your side and bring me the results — I'll update the reminder and file the certification outcome.

No other reminders trigger on this one: the notification-trail check is armed for the operator-channel slice, not Slice 9.

Want me to file this agenda as an entry linked to the P0 reminder, so the review has a traceable plan of record?
