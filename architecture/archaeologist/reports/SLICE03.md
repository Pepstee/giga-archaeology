# Slice 03 report — entrypoint and dynamic-use counterevidence

## Outcome

Slice 03 is independently useful now. `giga-archaeologist counterevidence`
consumes the exact self-hashed inventory and hypothesis documents, reparses
inventoried Python without importing it, and emits evidence capable of blocking
obvious scanner false positives.

The live run inspected 881 hypotheses and recorded:

- 148 hypotheses with counterevidence `PRESENT`;
- 733 hypotheses with counterevidence `UNKNOWN`;
- 40 declared project entrypoints;
- 163 `__main__` guards;
- 78 decorated symbols;
- 535 potentially dynamic registration/loading calls;
- 2,675 import records.

The counterevidence receipt is
`71ef389b6a56f07d1d80e04a1fe7b1d969cbc2ad78ab34338df1fb8dd80c478d`.
Complete local evidence is at
`/Users/admin/Documents/developer-tools/giga-archaeologist-evidence/slice03-da262776`.

## False-positive controls

- Declared console scripts, executable/module entrypoints, cross-file imports,
  decorators, name references and literal dynamic-load/registration calls are
  preserved with exact file and line locations.
- Counterevidence is attached to the exact input hypothesis ID; the inventory,
  hypothesis file hashes and their self-hashes are cross-bound.
- A positive signal means only that cleanup is unsafe without more analysis.
- No signal can become `ABSENT`; it becomes `UNKNOWN` because no runtime trace
  exists yet.
- Evidence is capped per hypothesis, with truncation disclosed, so a large
  reference fan-out cannot exhaust the report.
- The target is descriptor-read and hash-checked against inventory bytes before
  parsing. No target module is imported or executed.
- Every record retains the original `OBSERVED` hypothesis state and explicitly
  denies authority and cleanup permission.

## Applied learning

This slice began by auditing real scanner paths and found the Slice 2 synthetic
projection-prefix/format-suffix defect. That issue was repaired and separately
receipted in commit `da262776` before this model consumed a fresh input chain.
This prevented counterevidence from being attached to non-openable pseudo-paths.

## Verification and scope

Focused tests prove console-entrypoint and dynamic-string signals produce
`PRESENT`, an isolated unreferenced file remains `UNKNOWN`, tampered cross-links
refuse, output is private/create-once, and source Git state is unchanged. The
complete operations and foundation gates also pass.

The canonical owner remains `modules/operations/archaeologist`; existing Slice
1 and 2 evidence helpers are reused. No runtime tracing, Git history comparison,
Judge decision, quarantine, deletion, protected integration or deployment is
claimed.

## Knowledge graph status

The GIGA folder navigation graph remains `STALE/PARTIAL`. This slice preserves
exact navigable file/line relationships that the future two-layer inventory +
Graphify map can ingest, but does not present itself as that graph or block on
its refresh.
