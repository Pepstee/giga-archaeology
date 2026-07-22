# ECC portable extraction completion receipt

**Pinned source:** `affaan-m/ECC@96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`  
**Extraction status:** complete for this pinned commit  
**Deployment status:** ECC remains globally undeployed; staged specifications grant no authority

## What “complete” means

- All 3,330 pinned Git files are present and SHA-256 verified against
  `COMPONENT_INVENTORY.json`.
- All 278 canonical skills have an explicit disposition in `SKILL_CLASSIFICATION.json`.
- All 11 `adapt_candidate` skills are mapped to a portable finding, an existing local method or a
  named deferral in `PORTABLE_FINDINGS.json`.
- All 12 import-ledger entries bind an exact upstream path/hash to an existing destination.
- The portable-finding ledger contains 15 findings:
  - 2 implemented as read-only deterministic components;
  - 10 staged specifications;
  - 1 already covered by the deterministic inventory method;
  - 1 deferred until repository-wide enforcement;
  - 1 deferred on demand pending real token telemetry.
- The upstream checkout is clean and unchanged.

Complete does **not** mean copying every ECC skill, installing ECC, enabling hooks, importing its
control plane or accepting its product claims. The 156 on-demand and 111 reference-only skill
decisions remain explicitly enumerable in `SKILL_CLASSIFICATION.json`; they are not an undefined
backlog.

## Newly extracted portable specifications

- deterministic evaluation and behavioural-compliance evidence;
- operational readiness checks, missing-evidence states and hard score caps;
- capability-surface selection with token/runtime/supply-chain tax;
- canonical session snapshots and pre-conflict collision advisories;
- version-bound human artifact annotations and approval receipts;
- independent-product public/gated integration boundaries;
- append-only repeated-rollout decision ledgers.

These join the earlier adapter evidence, operator status, evaluator negative controls, selective
deployment, import provenance and security-negative-test contracts.

## Audit defect corrected

The completion validator found that the stored `yarn.lock` inventory record did not match the clean
pinned Git blob. The other 3,329 hashes matched. The inventory record was corrected, and
`scripts/audit_ecc.py` now inventories `git ls-files` rather than ignored/generated working-tree
artifacts such as coverage output or bytecode caches. A fresh replay produces the same inventory.

## Graph evidence boundary

The ECC knowledge graph usefully confirmed the evaluation/compliance implementation cluster and
the rule/skill/CLI/API/MCP surface hierarchy. Generic label collisions produced irrelevant paths
for plan feedback and some proximity terms, so the exact pinned documents—not graph traversal—are
the authority for those findings.

## Verification

```bash
python3 ecc-integration/scripts/validate_extraction.py
python3 -m pytest -q tests ecc-integration/tests
```

The extraction validator independently checks source hashes, destination containment, candidate
coverage, ledger coverage and the shared commit pin. Negative tests prove missing candidate
coverage, source-hash tampering and destination escape fail closed.

## What happens next

The extraction freeze in `FUTURE_WORK.md` has served its purpose. Lifting it permits architecture
review of how to give determinism real enforcement across giga-user; it does not itself authorise
global rewiring or deployment. That must remain a separately designed, tested and approved slice.
