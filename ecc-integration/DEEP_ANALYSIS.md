# ECC deep analysis and selective-import decision

## Outcome

ECC has been forked to `https://github.com/Pepstee/ECC`, cloned with `origin` pointing to the fork
and `upstream` pointing to `affaan-m/ECC`, and pinned to commit
`96789caaf90501ff9b55bf1b00f1c28cf3fccbeb` (tree
`cf976f78c1abc540e45d32f65bd7db7f5fae3a6e`). The upstream checkout remains unmodified.

The correct integration model is **vendor intelligence, not product merger**. ECC and
orchestrator-v3 remain separate products. Useful, portable contracts are staged here; nothing is
installed globally and nothing in the orchestrator repositories was changed.

## Exhaustive inventory

The deterministic inventory records 3,330 source files, 45,928,875 bytes, and all 278 canonical
skills. It records a SHA-256 and static risk indicators for every file. ECC's replicated harness
surfaces produce 889 total `SKILL.md` files, but the canonical catalog is `skills/*/SKILL.md`.

The extraction-completion audit found and corrected one stale inventory record: the stored
`yarn.lock` hash did not match the clean pinned Git blob, while the other 3,329 records did. The
inventory generator now reads `git ls-files` rather than the working-directory tree, preventing
ignored coverage reports or bytecode caches from contaminating future inventories.

Upstream's validated catalog contains:

- 67 agents;
- 94 commands;
- 278 canonical skills;
- 122 rules;
- 21 hook matchers;
- 32 install modules;
- 79 install components;
- 7 profiles.

The full per-file ledger is `COMPONENT_INVENTORY.json`; all canonical skill decisions are in
`SKILL_CLASSIFICATION.json`.

## Skill triage

Every canonical skill has a disposition. The conservative first pass produced:

- 11 `adapt_candidate`;
- 111 `reference_only` because they contain mutation, credential, network or autonomous-operation
  indicators;
- 156 `defer_on_demand` because no present giga-user requirement justifies activating them.

The 11 candidates are `agent-eval`, `eval-harness`, `production-audit`,
`recursive-decision-ledger`, `repo-scan`, `safety-guard`, `security-scan`, `skill-comply`,
`token-budget-advisor`, `verification-loop`, and `workspace-surface-audit`. This status means
“inspect/adapt,” not “install.” Several already overlap giga-user concepts or installed capabilities
and must win an isolated evaluation before activation.

## Subsystem decisions

| Subsystem | Decision | Reason |
|---|---|---|
| Adapter compliance vocabulary | Import concept | Honest distinction between native, adapter-backed, instruction-backed and reference-only |
| Evaluator artifact/negative-control model | Import concept and validator | Strengthens evidence-based promotion without automatic mutation |
| HUD/status field vocabulary | Import mapped contract | Useful portable status shape; receipts remain authoritative |
| Install plan/apply/state/rollback separation | Import architecture only | Good lifecycle design, but ECC's implementation targets global harness homes |
| Supply-chain/workflow/path-safety fixtures | Import negative-test specification | Strong tests; local implementation must use giga schemas |
| Full agent/command/rule catalog | Defer | Large trigger and doctrine surface with no proof of local incremental value |
| Hooks and continuous learning | Reject deployment | Enforcement differs by harness and automatic mutation conflicts with promotion gates |
| Dashboard/control pane | Reference only | UI ideas are useful; legacy dashboard has a network-binding issue |
| ECC2 Rust control plane | Reference only | Explicitly alpha and overlaps orchestrator-v3 |
| MCP templates/external services | Defer | Require separate credential, privacy and necessity review |
| Language/framework recipes | On-demand only | Install only when a real project creates a measured need |

## Verification evidence

- `npm test`: 3,133 passed, 0 failed.
- Node 24 `npm run coverage`: passed at 89.14% statements, 79.70% branches, 93.91% functions,
  89.14% lines.
- Node 26 coverage: incompatible with the pinned yargs package (`require` unavailable in ESM scope);
  not counted as an ECC logic failure, but recorded as a runtime compatibility constraint.
- `npm run security:ioc-scan`: pass, 207 files inspected.
- adapter compliance: 11 adapters, pass.
- observability readiness: 21/21, ready.
- npm signatures: 210/210 verified; 24 attestations verified.
- ECC2 `cargo test --all-targets`: 462 passed, 0 failed (14 dead-code warnings).
- ECC2 strict `cargo clippy --all-targets -- -D warnings`: failed with 67 diagnostics, including
  dead code, derivable implementations, overly wide function signatures and style/maintainability
  findings. This reinforces the upstream alpha classification; it is not a test failure.
- npm vulnerability advisory scan: unavailable due registry endpoint/network failure; this remains a
  runtime-promotion evidence gap.
- Graphify structural extraction: 46,851 nodes and 58,245 links. Its broad query showed label
  collisions around generic headings such as “Installation”; therefore it is retained as structural
  evidence, not treated as authoritative semantic classification.
- Candidate governance-kit: 3/3 tests pass.
- Upstream check/import ledger: 2/2 tests pass.

## What was imported

The ECC package as a whole remains marked `deployed: false` in `IMPORT_LEDGER.json`. The
status-field map and adapter-evidence contract have since advanced through separate acceptance
gates into repository-local, read-only deterministic compilers; every other candidate below
remains staged:

1. adapter evidence schema and validator;
2. evaluator promotion schema requiring a rejected negative control;
3. pinned import-provenance schema;
4. mapped status-field contract;
5. selective deployment/rollback contract;
6. security negative-test specification;
7. deterministic upstream inventory and safe fetch/diff checker.

The completed portable-finding pass additionally stages:

8. evaluation/compliance evidence with deterministic graders and ordered traces;
9. operational readiness evidence, missing-evidence states and hard score caps;
10. capability-surface selection that explicitly prices token/runtime/supply-chain overhead;
11. canonical session snapshots plus read-only pre-conflict collision advisories;
12. version-bound human annotation and approval receipts;
13. independent-product public/gated integration boundaries;
14. append-only repeated-rollout decision ledgers that cannot turn confidence into approval.

`PORTABLE_FINDINGS.json` maps all 11 adaptation-candidate skills and every imported finding to
pinned source hashes. `scripts/validate_extraction.py` makes the extraction-complete claim fail
closed if coverage, hashes, destinations, the upstream pin or the import ledger drift.

## Future-proof update design

The fork is an availability lane; the commit pin is the reproducibility boundary. Future upstream
changes are fetched and diffed, never auto-merged or auto-deployed. A changed hash creates a new
candidate. The complete tests, inventory, classification, security review and explicit promotion
must run again before the pin moves.

`check_upstream.py --fetch` updates only the remote-tracking reference, reports changed paths and
affected canonical skills, and hard-codes `safe_to_auto_deploy: false`.

## Current safety decision

The isolated analysis and staged contract-only imports are safe. Wholesale ECC deployment is not.
The next authorized step should be a promotion review of these staged artifacts, followed by one
small target implementation at a time. No active capability should be claimed until the generated
giga-user implementation registry and target-specific verification prove it.
