# GIGA Archaeologist implementation programme

The pipeline converts scanner output into reviewable hypotheses and prevents a
false positive from becoming an accepted cleanup action. Each slice is useful
on its own and is committed only after its receipt and report are verified.

| Slice | Independently useful result | State | Receipt | Report |
| --- | --- | --- | --- | --- |
| 01 | Immutable repository/symbol/entrypoint/ref/duplicate inventory | VERIFIED | `receipts/SLICE01.json` | `reports/SLICE01.md` |
| 02 | Read-only scanner observations | VERIFIED + PATH REPAIR | `receipts/SLICE02.json`, `receipts/SLICE02_REPAIR01.json` | `reports/SLICE02.md` |
| 03 | Entrypoint and dynamic-use counterevidence model | VERIFIED | `receipts/SLICE03.json` | `reports/SLICE03.md` |
| 04 | Git and cross-repository historical capability comparison | NOT STARTED | `receipts/SLICE04.json` | `reports/SLICE04.md` |
| 05 | Deterministic fail-closed Judge and lifecycle | NOT STARTED | `receipts/SLICE05.json` | `reports/SLICE05.md` |
| 06 | Reversible quarantine canary with automatic restoration | NOT STARTED | `receipts/SLICE06.json` | `reports/SLICE06.md` |

## Non-negotiable boundary

- Discovery has read-only source access and writes only external evidence.
- Every scanner result begins as `OBSERVED`; it is never called dead, redundant,
  safe, or removable.
- Missing evidence is `UNKNOWN`; disagreement is `CONFLICT`.
- Only the deterministic Judge can mint `VERIFIED_CANDIDATE`.
- Slice 6 may exercise quarantine only in a disposable worktree and must restore
  automatically before returning.
- Actual deletion and protected-branch integration are outside this programme.

## Knowledge-map relationship

Archaeologist evidence is not the GIGA knowledge graph. The folder-navigation
map is a separate, non-authoritative two-layer capability: a complete local
deterministic file inventory plus a semantic Graphify layer for supported
content. Until that replacement is current, the old narrow retrospective graph
and the modularisation graph are both reported as `STALE/PARTIAL`; neither may
authorize or block an Archaeologist lifecycle transition.
