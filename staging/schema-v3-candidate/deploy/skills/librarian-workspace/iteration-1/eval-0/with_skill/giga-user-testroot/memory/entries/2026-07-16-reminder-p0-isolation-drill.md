---
type: reminder
tags: [orchestrator, v3, safety]
created: 2026-07-16
trigger: when discussing v3 Slice 9 planning, P0 certification, or Theseus (Slice 20)
status: active
---
Verify the isolation-loss drill actually survived into Slice 9's REAL plan and certification:
a failed sandbox/worktree create must be loud and gating, never a silent ungated run
(register R-102, milestone-gating). Test with the inheritance detector:
`claude-orchestrator-main/scripts/repro_worktree_orphan.py` against v3's implementation —
exit 0 means v3 inherited the defect. Same check applies to Slice 20 candidates.

**Update 17 Jul (fired as designed):** Slice 9 DID certify without the drill; operator relayed
the flag; overseer confirmed worse-than-stated — v3 has NO worktree/sandbox creation site and
`infra/workspace.py task_workdir()` silently falls back to the shared project tree (the exact
masking R-102 forbids). Overseer enqueued a scoped improvement round: loud+gating at that seam
plus `tests/test_isolation_loss_drill.py` (failure injection + back-to-valid companion).
REMAINS ACTIVE until that test exists in v3's tree and the fallback gates — then also re-run
the inheritance detector, and re-check at Slice 20 (Theseus).
