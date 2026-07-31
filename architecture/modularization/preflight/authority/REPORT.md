# Wave 0D authority resolution and migration batches

**Date:** 2026-07-31  
**Scope:** `/Users/admin/Documents/giga-user`, excluding Dubbing Studio  
**Authority:** operator-authorised modularisation plan, subject to deterministic
preflight gates  
**Mutation boundary:** this wave wrote only
`architecture/modularization/preflight/authority/`; it moved or edited no
pre-existing path

## Verdict

The target modular architecture is authorised. The machine map is structurally
valid and covers all **72** current top-level paths exactly once. Repository
evidence resolved **11 of the 12** Wave 0A ambiguities. The original unresolved
item, `market-aligner-artiom/`, remains fail-closed. A concurrent task then
created `life-admin/` after the checkpoint; it is recorded as a second,
post-checkpoint blocker without inspecting or changing its contents. Both paths
are excluded from every executable batch.

The repository-wide gate remains `acceptance_ready: false` because those two
authority decisions are outstanding. The 13 planned batches remain individually
`ready-after-lock-and-preconditions`; this is not permission to execute them.

Current disposition totals:

| Disposition | Paths |
|---|---:|
| retain | 22 |
| move | 19 |
| protected/no-touch | 12 |
| generated | 10 |
| quarantine | 2 |
| archive | 6 |
| externalize | 1 |

Forty-three paths have critical compatibility requirements. “Generated” does not
mean disposable: `outputs/` contains registries, receipts and the exhaustive
skill inventory.

## Authority basis

The existing directory decision says GIGA is a programme workspace rather than
one application and already divides it into authority, platform, knowledge,
projects, external workspaces, runtime/delivery and intake
([`GIGA_USER_DIRECTORY_ARCHITECTURE.md:5`](../../../GIGA_USER_DIRECTORY_ARCHITECTURE.md),
[`GIGA_USER_DIRECTORY_ARCHITECTURE.md:14`](../../../GIGA_USER_DIRECTORY_ARCHITECTURE.md)).
Its move law requires reference, import, schedule, test and provenance
migration before changing live paths
([`GIGA_USER_DIRECTORY_ARCHITECTURE.md:46`](../../../GIGA_USER_DIRECTORY_ARCHITECTURE.md)).

The current machine contract declares the Mac canonical and Gutua a protected
candidate source; timestamps and apparent completeness grant no authority
([`MAC_GUTUA_AUTHORITY_AND_SNAPSHOT_POLICY.md:8`](../../../MAC_GUTUA_AUTHORITY_AND_SNAPSHOT_POLICY.md)).
Adoption requires a Mac branch, review, tests and a promotion receipt
([`MAC_GUTUA_AUTHORITY_AND_SNAPSHOT_POLICY.md:19`](../../../MAC_GUTUA_AUTHORITY_AND_SNAPSHOT_POLICY.md)).

The mapping therefore uses this precedence:

1. explicit operator decisions;
2. `CONTEXT.md` settled doctrine;
3. `00_MASTER.md` programme status;
4. `CHARTER.md` behaviour;
5. `memory/MEMORY_PROTOCOL.md`;
6. project and machine registries;
7. root-layout contract;
8. candidate-bound certificates and tests;
9. reports, plans, outputs and caches.

Reports, filenames, physical copies and newer timestamps cannot promote
themselves.

## Target modular architecture

The root retains the canonical governance entrypoints: `AGENTS.md`,
`00_MASTER.md`, the seven briefs, `CHARTER.md`, `CONTEXT.md`,
`CONTEXT_PROTOCOL.md` and `.gitignore`.

The approved first-class zones are:

```text
giga-user/
├── canonical root entrypoints
├── architecture/
├── modules/
│   ├── digital-twin/
│   ├── platform/
│   ├── calibration/
│   ├── sovereignty/
│   ├── integrations/
│   ├── operations/
│   ├── deployment/
│   ├── proof/
│   ├── research/
│   └── skills/
│       ├── owned/
│       ├── capability-registry/
│       ├── docs/
│       └── catalogs/          # reference indexes, never copied cache authority
├── projects/ and approved stable direct project paths
├── corpus/, memory/, research/, retrospectives/
├── external/
├── runtime/
├── archive/
├── quarantine/
└── intake/
```

`modules/skills/` has explicit owner **giga-user platform**. Its future
canonical owned source is `modules/skills/owned/`; its evidence-backed
capability registry is `modules/skills/capability-registry/`.

## Skills boundary

The exhaustive inventory found **5,708** physical manifests, but only **68**
router-catalog entries. Presence does not prove installation, trust or
callability
([`skill inventory README:5`](../../../../outputs/skill-filesystem-inventory-2026-07-30/README.md)).

The authority map preserves every one of its 21 source classes and separates:

- **GIGA-owned:** two deployable skills, `librarian` and
  `skilltree-operator`; future target `modules/skills/owned/`, no Wave 0 move.
- **Active personal/system:** Codex, shared-agent, Claude-personal and scheduled
  automation roots; reference-only host catalogue.
- **External plugins:** installed plugin caches; exact version/path indexed,
  never vendored as owned code.
- **Marketplace/catalogue/cache:** Claude marketplace checkout, Codex temporary
  mirror and Graphify repository caches; presence is not installation.
- **Historical/upstream:** Orchestrator-v3 corpus, ECC upstream and GIGA corpus
  snapshots; evidence only, never bulk promoted.
- **Runtime/project copies:** runtime caches and project-local skills remain
  owned by their runtime or project.

The physical split is material: the inventory records 2 GIGA-owned deploy
manifests, 2 staged copies, 45 installed plugin-cache manifests, 618 temporary
Codex marketplace mirrors, 3,917 Orchestrator skill-corpus manifests and 889 ECC
upstream manifests
([`skill inventory README:15`](../../../../outputs/skill-filesystem-inventory-2026-07-30/README.md)).

## Protected paths

The following are no-touch until separate hash/reference gates pass:

- the ChatGPT, Instagram and both Discord archives;
- the raw Telegram `result.json`;
- `corpus/`, `memory/` and `research/`;
- the mixed external `audit-work/` workspace;
- the concurrent `life-admin/` workspace pending writer, ownership and
  reference-closure reconciliation;
- independent canonical `market-aligner/`;
- the licensed Offer Accelerator source PDF.

Archive relocation targets in `authority-map.v1.json` are descriptive future
destinations, not permission to touch these sources. The existing export
baseline and migration receipts must remain valid.

## Wave 0D adjudications

| Wave 0A ambiguity | Evidence-backed resolution |
|---|---|
| Orchestrator architecture synthesis | Archive as a dated subordinate snapshot; its own closing rule puts code, certificates and standing decisions above its prose. |
| `SESSION_LOGS/` | Retain as the canonical historical programme ledger because the master and briefs link it directly. Header drift is content reconciliation, not path authority. |
| V3 contract decisions | Archive as ratified historical external-system decisions; the file says repository landing satisfies ratification. |
| `audit-work/` | Protect/no-touch as the mixed external audit workspace already described by the root-layout zone. |
| `company-admin/` | Move to and register `projects/company-admin`; its closure ledger and evidence establish an active project and deadline. |
| `deploy/` | Split exhaustively: `deploy/skills/**` belongs only to the specialised-skills batch; the other five children belong only to deployment. |
| `ecc-integration/` | Split authored evidence/code/tests from generated `graphify-out`; every current child has one batch owner. |
| `reports/` | Retain in the root-layout knowledge zone; live authority documents cite report receipts. Supersession indexing remains a content-governance task. |
| `scripts/` | Route all 41 current source files to explicit owning modules. |
| `tests/` | Route all 38 current test files with their owning modules. |
| `tier1-findings.md` | Archive as external Orchestrator finding evidence, not personal-memory authority. |
| `market-aligner-artiom/` | **Unresolved.** Machine authority identifies a candidate duplicate, but no comparison-backed reconciliation decision exists. |
| post-checkpoint `life-admin/` drift | **Unresolved and protected/no-touch.** Its future `projects/life-admin` target is descriptive only. Identify the originating task, seal the tree, register the project, then migrate it in a later isolated batch. |

Both unresolved paths are listed only in `deferred`; neither appears in a batch
source set. `market-aligner-artiom/` requires sealing and comparison with
canonical `market-aligner/`, followed by a ratified merge, archive, delete or
continued-quarantine outcome. `life-admin/` requires the originating task,
sealed tree, project registration and a later isolated migration batch.

## Migration batches

[`MIGRATION_BATCHES.v1.json`](MIGRATION_BATCHES.v1.json) defines 13
dependency-ordered batches and 137 exclusive source paths. It includes:

- first-class `modules/skills/` treatment with owned, evaluation, registry,
  tooling and test destinations;
- exhaustive per-file routes for 41 scripts and 38 tests;
- non-overlapping child splits for `deploy/` and `ecc-integration/`;
- compatibility updates, focused tests, rollback checks and expected
  post-move paths for every batch;
- a binding to the authority-map and executable-inventory hashes;
- explicit no-touch, retained and deferred sets.

No source path is shared by two batches, no destination overlaps another, and
no protected/no-touch path is present in a batch.

## Root-move gate

[`ROOT_MOVE_LOCK.md`](ROOT_MOVE_LOCK.md) defines an atomic-directory,
single-writer lock at:

```text
~/.giga/locks/giga-user-root-move.v1.lock
```

It binds host/boot/PID identity, root inode, branch, HEAD, dirty-state digest,
manifest hash, path batch and migration order. A stale heartbeat is never
permission to delete the lock. The gate requires:

- structurally valid live-root manifest;
- no blocked ambiguity in the selected batch;
- sealed manifest/Git/status/path candidate;
- protected-source hashes;
- reference closure including untracked files, launch agents and systemd;
- preserved skill ownership classes;
- one branch/worktree and one writer;
- ordered dry run and rollback;
- focused/full tests and immutable-baseline verification;
- candidate-bound migration and promotion receipts.

## Outputs and verification

- [`authority-map.v1.json`](authority-map.v1.json) — complete 72-path mapping,
  target architecture, skills taxonomy, dependencies, provenance,
  compatibility and migration order.
- [`MIGRATION_BATCHES.v1.json`](MIGRATION_BATCHES.v1.json) — dependency-ordered
  execution contract with exclusive source sets, compatibility work, tests and
  rollback checks.
- [`build_authority_map.py`](build_authority_map.py) — deterministic live-root
  measurement plus reviewed mapping source.
- [`build_migration_batches.py`](build_migration_batches.py) — deterministic
  migration-batch generator and exhaustive script/test routing table.
- [`validate_authority_map.py`](validate_authority_map.py) — structural and
  readiness validator.
- [`test_authority_map.py`](test_authority_map.py) — focused positive and
  negative tests.
- [`ROOT_MOVE_LOCK.md`](ROOT_MOVE_LOCK.md) — lock and acceptance contract.

Validation commands:

```bash
python3 architecture/modularization/preflight/authority/build_authority_map.py --write
python3 architecture/modularization/preflight/authority/build_migration_batches.py
python3 architecture/modularization/preflight/authority/validate_authority_map.py
python3 -m unittest discover -s architecture/modularization/preflight/authority -p 'test_*.py' -v
```

Structural and batch validation must pass. `acceptance_ready` correctly remains
`false` until the `market-aligner-artiom/` and `life-admin/` authority decisions
are ratified, even though both paths are excluded from the unchanged 13 planned
batches.
