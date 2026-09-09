---
name: skilltree-operator
description: Audit, query, prioritise, and advance the evidence-backed SkillTree capability registry inside giga-user. Use when asked what capabilities are implemented, available, partial, blocked, missing, highest-value, or next to build; when converting the exported SkillTree taxonomy into working giga-user capabilities; or when verifying that a claimed capability has durable implementation evidence.
---

# SkillTree Operator

Treat the public SkillTree export as a taxonomy and dependency graph, never as proof that a capability exists.

## Audit

1. Run `scripts/audit_tree.py` from this skill with the giga-user source root and export
   directory. Pass `--evidence-root` when declared repository-relative evidence resolves in a
   separate read-only checkout (it defaults to the source root; it is never written to).
2. Read the generated JSON registry for exact status. The canonical human surface is
   `skilltree/IMPLEMENTATION_STATUS.md`; `skilltree/IMPLEMENTATION_REPORT.md` is a compatibility
   symlink to it, so the older path can never hold a divergent copy. Re-run generation after any
   evidence-map change, then run the same command with `--check --compat-report
   skilltree/IMPLEMENTATION_REPORT.md` to refuse drift against the tracked registry, status file
   and symlink.
3. Report separately:
   - `implemented`: explicit durable evidence exists and all declared evidence paths resolve;
   - `partial`: some declared implementation evidence exists, but the completion contract is not met;
   - `available`: a matching installed or deployed skill exists but is not integrated and evidenced in giga-user;
   - `external`: the capability is intentionally provided by another canonical project;
   - `documented`: the export describes it, but no implementation evidence is registered;
   - `blocked`: an explicit external, legal, credential, or operator dependency prevents execution.
4. Never promote a status from prose, a preview, a plan, or a filename alone.

## Implement a node

1. Read the node, its prerequisites, human-control rule, and playbook entry from the registry.
2. Refuse downstream implementation when a hard prerequisite is neither implemented nor explicitly external.
3. Reuse existing giga-user services and installed skills before creating another skill.
4. For a new or modified skill, invoke `skill-creator`, keep instructions concise, add deterministic scripts for repeatable work, and validate the skill.
5. Add an explicit evidence declaration to `references/evidence-map.json` only after durable artefacts exist.
6. Re-run the audit. A node is complete only when the registry computes `implemented` and its checks pass.

## Prioritise

Rank eligible nodes using dependency centrality, operator relevance, reuse across active programmes, time-to-value, and implementation cost. Prefer foundation nodes that unlock multiple downstream capabilities. Do not recommend sales or back-office automation merely because the source taxonomy assigns it a high autonomy level.

## Integrity rules

- Preserve `outputs/skilltree-export-*` unchanged.
- Keep Market Aligner/JAA an independent external capability; link to it rather than copying it into giga-user.
- Do not interpret an installed connector, skill, model, preview, or API key as a deployed workflow.
- Preserve human approval requirements from the source playbook.
- Cite the evidence paths responsible for every `implemented`, `partial`, or `external` claim.

Read `references/status-contract.md` when changing status semantics or evidence declarations.
