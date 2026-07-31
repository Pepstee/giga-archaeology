# Wave 0F — Memory Truth and Validation Preflight

## Outcome

**Migration is not ready.** The existing 70-entry Markdown memory can be inventoried
deterministically, but it is not safe to use as an unqualified active-truth source or to cut
over to v2.

This wave is read-only with respect to the live system. No file under `memory/`, no context
file, database, graph, service, or current implementation was edited.

## Current inventory

| Measure | Result |
|---|---:|
| Entry files | 70 |
| Indexed entries | 69 |
| Parseable current frontmatter | 70 |
| Active lifecycle | 67 |
| Superseded lifecycle | 2 |
| Archived lifecycle | 1 |
| Decisions / facts / ideas / reminders / questions | 14 / 33 / 2 / 21 / 0 |
| Current validator | **FAIL** |
| Current errors / warnings | 1 / 2 |
| Existing focused tests | 8/8 pass |

The current validation error is index coverage. The two warnings are missing explicit
provenance on fact/decision entries. Paths and content are intentionally omitted from this
report; the existing validator remains the path-level diagnostic authority.

## Actual runtime path

```text
Telegram or daily batch
  -> process_event
  -> provider_prompt
  -> compile_context
  -> provider proposal
  -> validate_proposal (temporary projection)
  -> commit_proposal (one file at a time)
  -> final validate_memory
  -> receipt / daily cursor advance
```

The path has four critical gaps:

1. `compile_context` runs without first requiring `validate_memory`.
2. It searches every entry without lifecycle parsing. The one archived and two superseded
   entries are therefore still eligible for lexical, reminder, or linked-neighbour selection.
3. Baseline validation is observed during proposal validation, but a clean baseline is not a
   mandatory pre-context/pre-provider gate.
4. Multi-file commits are atomic per file, not as a whole snapshot. A final validation
   failure can occur after some files have already been replaced.

The daily path correctly delays cursor advancement until `process_event` reports success, but
it inherits the same missing pre-context gate and per-file commit boundary.

## What v2 adds

- content-addressed entry, revision, claim and tombstone identities;
- exact source precedence and explicit unknown values;
- immutable revision history;
- claim-level temporal and epistemic metadata;
- symmetrical contradiction edges;
- a separate active-truth view;
- tombstones that preserve falsified/retracted content as labelled non-active evidence;
- transitive invalidation of context, proposal, commit, daily, graph, profile and training
  artifacts;
- mandatory pre/post gates and whole-snapshot rollback;
- read-only shadow compatibility with no dual writes or silent fallback.

`MEMORY_SCHEMA_V2.json` is the canonical interchange schema. It deliberately makes
`evaluated_at` part of the memory snapshot hash so temporal inclusion is reproducible.
Derived artifacts are outside the snapshot hash to avoid circular hashing, but each one must
bind the snapshot and active-truth hashes it consumed.

## Migration rules

The migration must preserve every Markdown byte in a root revision. It must not infer missing
authority, confidence, dates, temporal bounds, or evidence. Each legacy entry initially
becomes a history-only `legacy-entry-assertion` with explicit unknowns. Semantic splitting
creates descendant claims and a new revision; it never rewrites the root evidence.

Legacy `archived` and `superseded-by` states remain inactive. A correction creates a new claim
or revision plus a tombstone/supersession relation. False statements remain visible only as
labelled history, never as active truth.

## Acceptance blockers

| ID | Blocker |
|---|---|
| MEM-P0-001 | Live validator is red. |
| MEM-P0-002 | No mandatory validation before context. |
| MEM-P0-003 | Inactive lifecycle is not excluded from context. |
| MEM-P0-004 | No whole-snapshot atomic commit/rollback. |
| MEM-P0-005 | No claim, contradiction, temporal, tombstone, or active-truth layer. |
| MEM-P1-002 | Legacy frontmatter is untyped and unknown values are not represented safely. |
| MEM-P1-003 | Negative controls and enforcement-stage tests are absent from the live suite. |

Two provenance warnings additionally require review. Cutover also requires operator review of
the active claim set and operator authorization for false/privacy tombstones.

## Produced contracts

- `MEMORY_SCHEMA_V2.json` — canonical snapshot JSON Schema.
- `MEMORY_TRUTH_CONTRACT.md` — identity, precedence, contradiction, active-truth, invalidation,
  rollback and compatibility semantics.
- `MEMORY_MIGRATION_PLAN.json` — observed counts, risks, phases, acceptance and rollback plan.
- `TOMBSTONE_CONTRACT.json` — append-only removal from active truth.
- `MANDATORY_VALIDATION_GATE.json` — pre/post context, proposal, commit and scheduled gates.
- `validate_memory_preflight.py` — read-only contract, legacy-inventory and v2-snapshot
  validator.
- `test_validate_memory_preflight.py` — focused deterministic negative controls.

## Validator commands

```bash
python3 architecture/modularization/preflight/memory/validate_memory_preflight.py contracts
python3 architecture/modularization/preflight/memory/validate_memory_preflight.py legacy
python3 architecture/modularization/preflight/memory/validate_memory_preflight.py legacy --acceptance
python3 architecture/modularization/preflight/memory/validate_memory_preflight.py snapshot SNAPSHOT.json
python3 architecture/modularization/preflight/memory/validate_memory_preflight.py snapshot SNAPSHOT.json --acceptance
```

Inventory mode verifies that the preflight observation has not drifted. Acceptance mode is
intentionally fail-closed until the declared blockers are resolved and a v2 migration is
separately authorized.
