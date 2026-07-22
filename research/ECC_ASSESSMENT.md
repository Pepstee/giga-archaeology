# ECC repository assessment

**Repository:** `affaan-m/ECC`  
**Inspected commit:** `96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`  
**Inspection date:** 22 July 2026  
**Decision:** mine selectively; do not install wholesale.

## What ECC is

ECC 2.0 is a cross-harness workflow distribution containing 67 agent definitions, 94 command
definitions, 278 skills, rules, hooks, MCP templates, installers, session tooling, security
validators, observability contracts and an alpha Rust control plane (`ecc2`). Its strongest idea is
that durable workflows live once in shared skills/rules/scripts while thin adapters translate them
to Claude Code, Codex, Cursor, OpenCode, Gemini and other harnesses.

## Verification performed

- Cloned the public repository into an isolated temporary directory.
- Read the README, security policy, install planner/executor and the architecture documents for
  cross-harness portability, compliance, observability, evaluator/RAG and HUD/session control.
- Installed pinned Node dependencies with lifecycle scripts disabled.
- Ran the repository's complete `npm test` command successfully on the full checkout.
- Confirmed catalog validation for 67 agents, 94 commands, 278 skills, 122 rules, 21 hook
  matchers, 32 install modules, 79 install components and seven profiles.
- Resolved the Codex `minimal` install plan without applying it: 50 planned operations, including
  the global Codex `AGENTS.md`, platform configuration and workflow-quality assets.

An initial test attempt against a deliberately sparse checkout failed because required catalog
files had been excluded. The full-checkout rerun passed; the sparse failure was not counted as a
repository defect.

## Why wholesale installation is wrong here

1. The global install surface can touch `/Users/admin/.codex/AGENTS.md`, which already carries
   mandatory giga-user skill routing and project governance.
2. Adding hundreds of skills would increase trigger ambiguity, catalog noise and maintenance
   burden. Catalog presence would still not prove operational deployment.
3. ECC describes Codex support as instruction-backed because Codex lacks equivalent native hook
   enforcement. Many of ECC's strongest Claude/OpenCode controls therefore degrade on Codex.
4. The alpha ECC2 control plane overlaps directly with orchestrator-v3, whose gates, receipts,
   isolation and promotion rules are already the dedicated software-factory architecture.
5. Giga-user already has evidence preservation, append-only receipts, schema/entropy controls,
   graph retrieval and a mandatory skill router. Installing another operator doctrine would create
   competing sources of truth.

## Components worth mining

### 1. Harness adapter compliance matrix

Adopt the state vocabulary (`native`, `adapter-backed`, `instruction-backed`, `reference-only`)
and require every adapter claim to name its install path, verification command, risk note, owner,
source document and verification date. This would improve orchestrator-v3's provider/harness
certification without importing ECC's installer.

### 2. Portable HUD/status contract

Evaluate `ecc.hud-status.v1` as prior art for a provider-neutral operator view: context pressure,
tool calls, active agents, todos, checks, cost, risk, queues, session controls and tracker sync.
Map useful fields into orchestrator-v3 rather than copying the schema blindly.

### 3. Evaluator/RAG promotion artifacts

ECC's five-artifact contract is strong: scenario specification, trace, report, candidate playbook
and verifier result. The requirement for at least one rejected candidate is especially useful
negative-control evidence. Compare this with orchestrator-v3's certification and Theseus promotion
contracts.

### 4. Selective-install planning

The separation between a read-only install plan, explicit modules/components/profiles, an apply
stage and install-state record is good prior art for any future giga-user capability deployment.
The installed skill-router must remain the final authority over actual Codex skill lifecycle.

### 5. Security validators

Review, rather than install, the supply-chain IOC scanner, workflow-security validator, secret-safe
examples, protected-config checks and personal-path leak detector. Candidate controls should be
ported only with local threat models and negative tests.

## Low-priority material

- Generic language/framework agents and commands duplicate capabilities available on demand.
- Token-optimisation advice is mainly Claude-specific and should not override current model policy.
- Continuous-learning/instinct promotion overlaps with giga-user memory and evidence doctrine;
  automatic mutation would be unsafe without operator-confirmed promotion.
- ECC2 should remain comparative prior art while it is described upstream as alpha.
- Hosted ECC Tools and sponsor-linked services are external products, not required dependencies.

## Safe next step

Perform a five-item comparative design review against orchestrator-v3 and giga-user:

1. adapter compliance evidence;
2. status/HUD field mapping;
3. evaluator artifact and negative-control mapping;
4. selective deployment/rollback contracts;
5. security-validator test cases.

For each item, classify the result as `already stronger`, `adopt concept`, `port tested code`, or
`reject`. Do not run ECC's installer and do not import its complete skill catalog.
