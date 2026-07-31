# JAA-06 isolated preparation lane

You are the sole writer in:

`/home/gutua/software-factory/.worktrees/jaa06-prep-20260728`

Branch: `codex/jaa06-preparation-20260728`.
Base commit: `894484336111913ea728985f13e1dbfed35448fd`.

This is a precursor preparation branch, not certification and not integration.
The active JAA-05 supervisor owns the main worktree. Never edit that worktree,
merge, rebase, push, or modify shared control/runtime evidence.

## Objective

Prepare JAA-06 so implementation can begin quickly after JAA-05 is certified:

1. Read repository instructions, `BUILD_PLAN.md`, `IMPLEMENTATION_SLICES.yaml`,
   current JAA-05/JAA-06 source and tests, and only directly relevant contracts.
2. Produce a precise JAA-06 requirements and dependency matrix bound to the
   base commit.
3. Identify current JAA-05 interfaces JAA-06 consumes and assumptions that
   must be revalidated after JAA-05 certification.
4. Add or improve deterministic tests/fixtures for JAA-06 only where they
   express already-ratified requirements and fail for a genuine missing
   capability. Do not weaken, duplicate or rewrite existing accepted tests.
5. Produce an acceptance matrix covering positive, negative, tamper, crash,
   idempotency, privacy, audit-lineage and rollback behaviour.
6. Run only focused JAA-06 tests and static checks. Record exact results.
7. Commit the bounded preparation as one clean commit if it adds durable value.

Do not implement production JAA-06 behaviour, change JAA-05, update assurance
status, claim certification, call Claude/Fable, use external networks, ingest
private data or perform consequential actions. If existing JAA-06 tests and
contracts are already complete, produce a gap report instead of manufacturing
work.

Your final response must state exact HEAD, changed files, tests, remaining
assumptions and whether the branch is safe to review after JAA-05 certification.
