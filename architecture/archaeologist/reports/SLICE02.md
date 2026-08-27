# Slice 02 report — read-only scanner observations

## Outcome

Slice 02 is independently useful now. `giga-archaeologist hypotheses` verifies
a Slice 1 inventory, copies only its admitted regular source files into an
external private projection, and runs three pinned scanners without giving any
scanner the original repository path.

The current accepted live run recorded:

- 880 total observations, all exactly `OBSERVED`;
- 80 Vulture Python unused-symbol observations;
- 800 jscpd syntactic duplicate-region observations;
- zero CodeGraphContext unreferenced-function observations;
- three completed scanners and zero failed scanners;
- no source-repository mutation and no global CodeGraphContext state.

The current hypothesis receipt is
`8f3afa2873563ac97316f8082631c0db1265cb060d03beb430342e949fb58d33`.
Complete raw scanner evidence is private and external at
`/Users/admin/Documents/developer-tools/giga-archaeologist-evidence/slice02-c9f2dbe8-path-repair`.

## Safety and false-positive boundary

- The projection is built only after each current source byte hash and file
  identity matches the self-hashed inventory.
- Scanners run under a macOS sandbox with network access denied and write
  access limited to their disposable scratch directory.
- CodeGraphContext uses a scratch-only configuration root and Kùzu database;
  the global `~/.codegraphcontext` identity is checked before and after.
- Output, errors and tool-native JSON are bounded, hash-bound and retained.
- A timeout, non-accepted exit or missing report is recorded as tool evidence;
  it cannot create a finding or improve a lifecycle state.
- Findings contain `authority_granted=false` and `cleanup_permitted=false`.
  Tool confidence is only reported tool metadata.
- Tool disagreement is intentionally unresolved. In particular,
  CodeGraphContext produced no candidate rows while Vulture and jscpd produced
  many observations; nothing is called corroborated, dead or redundant.

## Rejected first run and applied learning

The first real execution produced scanner results but also created
`~/.codegraphcontext/config.yaml`. That run was rejected and preserved at
`/Users/admin/Documents/developer-tools/giga-archaeologist-evidence/rejected-slice02-88bdf960-global-config-side-effect`.
Only the incidental two-file configuration directory was moved recoverably to
`/Users/admin/.Trash/codegraphcontext-incidental-slice02-rejected-20260828-0545`.

The repair added an explicit final write denial for that global path, made the
bridge assert its isolated configuration root, disabled project environment
loading, and added a before/after global-path identity check. The second live
run completed with the global path absent.

## Source-location repair

The first Slice 3 inspection found that the initially accepted Slice 2 parser
retained Vulture's synthetic `projection/` prefix and jscpd's virtual
`:format` suffix on some relative paths. Findings still carried no authority,
but those source locations were not reliably openable. That evidence is now
superseded rather than silently relabelled.

The parser now strips only a projection-root prefix and only a format suffix
whose exact unsuffixed file exists in the verified projection. It rejects every
result path that does not resolve to an inventoried projected file. The fresh
run proved all 880 observation paths are exact members of its input inventory,
with zero missing source paths and no global configuration side effect.

## Reuse and ownership

`modules/operations/archaeologist` remains the canonical owner; no parallel
scanner package was created. Slice 2 reuses Slice 1 inventory/evidence helpers
and the separately installed pinned CodeGraphContext 0.6.8, Vulture 2.16 and
jscpd 5.0.16 tools. The target repository is never imported or executed.

## Knowledge graph status

The existing narrow retrospective graph (reported elsewhere as 26 nodes and 33
edges) is not a map of the GIGA folder. The queried modularisation graph has 330
nodes and 1,210 edges but also predates these slices. Both are `STALE/PARTIAL`.
The required replacement is a separate two-layer local navigation index: a
complete deterministic folder inventory and a semantic Graphify layer with
exact source locations, incremental atomic refresh and honest exclusions. It
is not a gate and its absence does not weaken or block this scanner receipt.

## Nonclaims

No finding is corroborated or counterevidence-checked. No code is established
dead, disconnected, duplicate in meaning, redundant, safe, quarantinable or
removable. No target file was edited, moved or deleted. No protected integration
or deployment occurred.
