# ECC import security review

## Executive summary

The pinned ECC source is suitable as reviewed upstream material, and the small contract-only
candidate staged in this folder is safe to keep isolated. **ECC is not safe to install wholesale
into giga-user or Codex.** No critical vulnerability was proven in the reviewed commit, but the
installer, hooks, auto-update path, unauthenticated dashboard, coverage blind spots, and alpha Rust
control plane make direct deployment inappropriate.

The JavaScript/Python security guidance catalog contained no general Node CLI or desktop-Python
reference specific to this stack, so this review used repository trust boundaries, upstream tests,
negative fixtures, static inspection and dependency evidence. Rust was reviewed separately through
Cargo tests/clippy and upstream alpha declarations.

## High priority

### SEC-01 — Do not import auto-update or the global installer

**Impact:** a compromised or wrongly selected local ECC tree could execute its own installer and
rewrite harness configuration.

`scripts/auto-update.js:124-153` calls a repository trusted when its `package.json` merely uses one
of two expected names and the install script exists; `scripts/auto-update.js:250-267` then fetches,
pulls, and executes that script. This is stronger than no check and the path-safety suite is good,
but package name is not source identity or commit attestation. The installer also intentionally
targets user-level `.claude`/`.codex` homes.

Decision: reject runtime import. Preserve only the read-only plan/apply/state/rollback architecture,
with commit hashes and explicit promotion.

## Medium priority

### SEC-02 — The legacy capability dashboard is not loopback-bound explicitly

`scripts/dashboard-web.js:789-803` exposes agents, skills, commands, rules, MCP metadata and hooks
without authentication and calls `server.listen(PORT)` without a host. The newer control-pane and
plan-canvas servers explicitly use `127.0.0.1` and Host/Origin checks; this older dashboard does not.

Decision: do not import it. Any future UI must bind `127.0.0.1`, validate Host and Origin, default to
read-only, and require a separate authorization boundary for mutations.

### SEC-03 — Passing aggregate coverage hides untested executable entry points

The Node 24 coverage run passed the configured thresholds at 89.14% statements, 79.70% branches,
93.91% functions and 89.14% lines. However, `scripts/orchestrate-worktrees.js` and
`scripts/hooks/cursor-session-env.js` reported 0% coverage, while several update/install/coordination
paths were materially below the aggregate. Aggregate green therefore does not certify every import
candidate.

Decision: any ported executable needs its own positive, negative, path-escape and rollback tests.

### SEC-04 — Codex support is instruction-backed, not enforcement parity

ECC's own adapter matrix describes Codex as instruction-backed. Claude/OpenCode hook behavior cannot
be treated as a runtime security boundary in Codex.

Decision: import policy as declarations and tests only; never claim a hook control is deployed until
the target harness produces enforcement evidence.

## Low priority / evidence gaps

### SEC-05 — Registry advisory lookup was unavailable

`npm audit --ignore-scripts --json` failed twice because the npm bulk-advisory request returned an
endpoint/network error. This is not evidence of a vulnerability or of a clean dependency set.
`npm audit signatures` did succeed: all 210 packages had verified registry signatures and 24 had
verified attestations. The repository's own supply-chain IOC scan also passed.

Decision: dependency-bearing runtime promotion remains blocked until an advisory scan succeeds (npm,
OSV, or equivalent) against the pinned lockfile.

### SEC-06 — ECC2 is explicitly alpha

`ecc2/README.md:1-5`, `28-35`, and `80-99` calls the control plane alpha, incomplete, and not GA.

Decision: comparative reference only. Do not merge it with orchestrator-v3.

## Positive evidence

- Complete upstream Node suite: 3,133/3,133 passed.
- Coverage gate passed on Node 24; the Node 26 failure is a yargs/ESM compatibility issue.
- Supply-chain IOC, workflow-security, personal-path, secret-safe curl, adapter compliance and
  observability readiness checks passed.
- 210 npm package signatures verified; 24 attestations verified.
- Candidate governance-kit tests: 3/3 passed; upstream-sync/ledger tests: 2/2 passed.
- ECC2 Rust tests: 462/462 passed. Strict clippy failed on 67 warning-level diagnostics; the control
  plane remains reference-only.
- The pinned upstream checkout was clean after generated test artifacts were removed from tracked
  state.

## Security disposition

- `safe`: pinned read-only source, inventories, graph, reports, and staged contract-only candidate.
- `conditionally safe`: individually ported validators after local fixtures and target-specific
  tests.
- `unsafe now`: global install, auto-update, hooks, dashboard, automatic learning/promotion, ECC2
  orchestration, and wholesale skill activation.
