# DFI-05 mechanical repair F2 — exact authority before model invocation

You are the sole writer. Fix only Codex finding 2. Do not commit.

In `agents/task_manager.py`, a schema-valid fallback must not make the model
reachable until the host admission and every task/scope binding are verified.

Before prompt construction or `call(...)`:

- obtain epoch from the host admission marker;
- call `verify_scope_admission(task, epoch)`;
- validate the fallback against admitted:
  parent task, project, epoch, intent receipt, manifest, scope certificate,
  programme position, current slice, and component maximum authority;
- reject any mismatch with `llm_invoked=false`.

The repository remains responsible for comparing scheduler profile to its
active profile; do not invent a second profile authority inside the stateless
agent. The task manager must nevertheless reject every fallback/scope/task
binding it can deterministically verify.

Refactor the existing post-response proposal validator to reuse the same
validated scope/binding result. Move/delete duplicated schema-only or binding
logic rather than layering another validator.

Add one parametrized negative regression covering stale/cross parent, project,
epoch, intent, manifest, certificate, position, slice, and maximum authority.
Every case must prove the model callable was never invoked.

Run the focused DFI-05 test file, relevant task-manager tests if needed, Ruff,
and `git diff --check`. Current net production is 345; final must be at most
350 against `dcf5097`. No other finding, no full suite, no pipelines, no
commit.
