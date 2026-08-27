# Slice 04 report — historical and cross-repository variants

## Outcome

Slice 04 is independently useful now. `giga-archaeologist history` reads Git
objects and compares candidate paths with the clean
`/Users/admin/Documents/giga-modularisation-isolated` tree. It executes no code
and writes only external private evidence.

The live run inspected 881 hypotheses across 431 unique source paths:

- 877 hypotheses had at least one historical or comparison-tree variant;
- 4 remained `UNKNOWN`;
- 1,431 comparison matches used the exact same Git blob;
- 557 comparison matches shared a basename but had a different Git blob;
- the comparison tree contained 1,067 admitted non-private blob paths.

The history receipt is
`7e6f96c55a6c9ea581edcf1abc8c60463a21973463be3f010336940a3eb66c32`.
Complete evidence is stored at
`/Users/admin/Documents/developer-tools/giga-archaeologist-evidence/slice04-4d656f41/history`.

## Safety and interpretation

- All three prior documents are self-hash validated and cross-bound before Git
  history is read.
- Git runs with optional locks disabled, no system/global configuration and a
  bounded output ceiling.
- Primary and comparison HEAD/tree/branch, root identity, status and complete
  ref snapshots are captured before and after and must remain identical.
- History records use exact commit and blob object IDs; the comparison uses
  HEAD tree objects, not a possibly dirty working copy.
- Sensitive inventory prefixes are excluded from comparison indexing.
- A related historical/parallel version is a reason to preserve and inspect
  capability differences. It is never evidence that either version is stale,
  redundant or removable.
- A missing match is `UNKNOWN`; the implementation does not claim exhaustive
  absence across deleted names or repositories it was not given.

The high match count is expected because the compared GIGA tree shares much of
the same ancestry. It is useful as a strong preservation brake, not as a
quality score or duplication verdict.

## Verification and scope

Focused tests prove two Git versions and a differently located same-basename
comparison produce preservation evidence, a genuinely unobserved variant stays
`UNKNOWN`, tampered cross-document links refuse, both repositories remain
unchanged, and output is private/create-once. Complete operations and platform
foundation gates pass.

The canonical owner remains `modules/operations/archaeologist`. No capability
merge, file selection, Judge lifecycle transition, quarantine, deletion,
protected integration or deployment occurred.

## Knowledge graph status

The folder navigation graph is still `STALE/PARTIAL`. This slice supplies exact
commit/blob/path relationships suitable for its future semantic layer, but the
history packet remains non-authoritative and does not masquerade as the graph.
