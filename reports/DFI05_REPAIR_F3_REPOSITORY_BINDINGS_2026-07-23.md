# DFI-05 mechanical repair F3 — repository embedded bindings

You are the sole writer. Fix only Codex finding 3 in the current fresh
worktree. Do not commit.

In `dispatch/repository.py::_authorized_planner_fallback`, the outer scheduler
decision parent is checked, but the embedded fallback must also satisfy:

- `record["parent_task_id"] == task.task_id`
- `record["project"] == task.project`
- `record["intent_receipt_id"] ==` the admitted scope intent receipt ID

Add focused negative regressions for cross-parent, cross-project, and
cross-intent embedded records. Reuse existing test helpers; do not duplicate
production validation elsewhere.

Run only the smallest relevant test selection, Ruff on changed files, and
`git diff --check`. Recalculate net production against `dcf5097`. Preserve all
other bytes and keep the whole stage at or below 350 net lines. Do not consult
or apply the overflow patch for this mechanical change. Exit nonzero if the
complete repair cannot fit.
