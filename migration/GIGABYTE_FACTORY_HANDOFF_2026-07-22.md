# Start here — Gigabyte software factory handoff — 2026-07-22

## Immediate command

Do not launch the factory. Read, in order:

1. `giga-user/00_MASTER.md`
2. `giga-user/CHARTER.md`
3. `giga-user/CONTEXT.md` — standing doctrine only; personal corpus is not present
4. `agentic-orchestrator/projects/orchestrator-v3/docs/efficiency/JAA_ORCHESTRATOR_SKILLTREE_HANDOFF_2026-07-22.md`
5. this file
6. `agentic-orchestrator/projects/orchestrator-v3/docs/efficiency/E1_CONTEXT_CONTAINMENT.md`
   through `E6_GPT_ONLY_CERTIFICATION.md`

`agentic-orchestrator/projects/orchestrator-v3/STOP` must remain armed.

## Exact migrated source state

### Outer orchestrator

- Branch: `main`
- Commit: `07ea5aaee3531f7b5a2d42af56e3e285f79f8eac`
- Worktree: clean at migration inventory

### orchestrator-v3

- Branch: `efficiency/e2-shadow-cache`
- Commit: `253a9eb677ed10fe7176d6dea098ddaa9ebf4c29`
- Required dirty state to preserve exactly:

```text
 M dispatch/isolation.py
 M dispatch/runner.py
 M tests/test_container_runner_integration.py
?? tests/test_linux_isolation_certification.py
```

These are active Linux/container isolation changes. Do not revert, overwrite or fold them into an
unrelated commit. They are the first source state to settle on the WSL host.

### JAA

- Repository: `agentic-orchestrator/projects/orchestrator-v3/projects/job-application-automation`
- Branch: `main`
- Commit: `3679d98b1402b434e1e55c79b8b7d8a4f0a3c14a`
- Worktree: clean at migration inventory
- JAA-00: certified
- JAA-01: **not certified**
- Last exact suites before the final semantic rejection: 91 state-machine tests and 10 adversarial
  tests passed. Those passes do not waive the semantic findings below.

The older handoff says an uncommitted JAA repair was still active. That statement is historical:
the repair was subsequently settled in commits `a9f94bc` and `3679d98`. The current clean JAA HEAD
above is authoritative.

## Work order: orchestrator efficiency first

The migration changes the operating system and invalidates macOS host/isolation evidence. Before
resuming JAA development:

1. Keep `STOP` armed and prove no daemon is running.
2. Inspect and settle the four dirty Linux/container files. Run their focused tests, negative
   controls, `git diff --check`, architecture gates and the complete relevant regression suite.
3. Produce a fresh Linux/WSL isolation receipt. Never reuse the macOS isolation receipt.
4. Establish a fresh WSL baseline for wall time, provider tokens, tool calls, deterministic work,
   semantic review and cache hit/miss telemetry.
5. Verify the checked GPT-only launcher actually selects the certified active profile. A config
   file containing `active` is not evidence that the running process used it.
6. Run deterministic cache/reuse canaries: first a forced miss/fresh pass, then an exact repeat.
   Require active `deterministic_reuse_probe` events, a valid receipt hit and an avoided execution.
   Shadow observations alone provide no saving.
7. Prove exact duplicate suppression, pass-only reuse, external-evidence reuse, host assurance,
   bounded zero-tool semantic review, context containment and telemetry on WSL. Each change must
   retain its rollback mode and fail closed on identity/policy/source drift.
8. Run the representative efficiency benchmark. Compare quality gates and semantic verdicts as
   well as tokens and time. Do not claim projected savings as measured savings.
9. Commit and bind the WSL efficiency/isolation certificate only after every gate passes.

Do not raise tool/token budgets to conceal repeated work. The target is fewer repeated operations,
not weaker assurance.

## Work order: JAA second

After the WSL orchestrator profile is certified, continue JAA-01 from exactly three unresolved
persistence-integrity findings:

1. A matching `research-observation` proposal created while a job was still queued can be reused
   during completion. Require and replay-verify the proposal origin
   `employer_researching -> null`, probabilistic actor, exact idempotency key, observation and model.
2. Missing source/claim identifiers are coerced to the string `"None"`. Require non-empty unique
   source and claim IDs and valid citation sets before any write; use the same strict validator in
   writer, retry and replay paths.
3. A present but incomplete model dictionary is collapsed to no model. Reject malformed or
   ambiguous model metadata; bind the same exact identity in completion and replay.

For each finding, add an adversarial regression that proves failure before durable writes. Then:

1. run focused lifecycle tests;
2. run the exact JAA-01 state-machine and adversarial manifest commands;
3. commit the source repair;
4. regenerate commit-bound runtime evidence;
5. run WSL host assurance;
6. create one fresh validation task;
7. require a complete zero-tool semantic review;
8. certify JAA-01 only if all gates pass;
9. proceed sequentially to JAA-02 and later components.

No JAA component may be declared production-ready from tests alone. Final readiness still requires
all component receipts, isolation, replay/restart proof, failure drills, end-to-end acceptance and
a clean release commit.

## Provider and credential state

Repository state and instructions are migrated; login sessions are not. Re-authenticate Codex,
Claude, GitHub and any external evidence provider inside WSL. Never recover a raw credential by
copying it from a chat into a repository or handoff document.

## Path compatibility

Some preserved instructions contain Mac absolute paths. The migration creates WSL compatibility
links under `/Users/admin/` pointing to `/home/gutua/software-factory/` and the WSL user config.
Those links are compatibility infrastructure, not duplicate source trees.
