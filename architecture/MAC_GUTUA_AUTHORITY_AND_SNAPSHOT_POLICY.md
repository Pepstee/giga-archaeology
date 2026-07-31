# Mac and Gutua authority and snapshot policy

**Policy ID:** `giga.machine-authority.mac-canonical.v1`  
**Effective:** 2026-07-30  
**Authority:** explicit operator decision  
**Machine-readable registry:** `architecture/machine-authority.v1.json`

## Decision

The Mac is the sole canonical host for GIGA and for software accepted into the
operator's active estate. Gutua is a protected candidate source. It may contain
newer, divergent or otherwise valuable work, but no file becomes canonical
merely because it exists on Gutua or has a later timestamp.

This policy supersedes only the machine-authority and sole-writer assignments in
`migration/GIGABYTE_MIGRATION_SCOPE_2026-07-22.md`. That document remains
immutable historical evidence of the earlier cutover decision.

## Non-negotiable rules

1. Nothing on Gutua is deleted, cleaned, overwritten or normalised as part of
   discovery, snapshotting or later reconciliation.
2. Gutua is never copied wholesale over the Mac.
3. Mac and Gutua snapshots are evidence, not promotion authority.
4. A Gutua change is adopted only through a Mac reconciliation branch, review,
   relevant tests and an explicit promotion receipt.
5. "Newer", "larger" and "more complete-looking" select material for review;
   they do not prove correctness.
6. Dubbing Studio remains protected while its independent cleanup is active.
   Snapshotting may observe and seal it but may not modify or reconcile it.
7. Existing Gutua services and worktrees may continue to exist, but they do not
   define canonical GIGA or project state.

## Host roles

### Mac — canonical

The Mac owns:

- canonical GIGA laws, memory, context, corpus and control-plane source;
- the accepted versions of Orchestrator, JAA, Dubbing Studio and other projects;
- promotion decisions and reconciliation receipts;
- the machine-authority registry and sealed cross-host snapshots.

### Gutua — protected candidate source

Gutua may hold:

- divergent Orchestrator and DFI branches/worktrees;
- JAA implementation and history;
- Dubbing Studio development;
- older deployment copies and software-factory control material;
- candidate changes not yet present on the Mac.

Gutua grants no automatic authority. Its contents remain available for later
comparison even after a candidate has been adopted on the Mac.

## Snapshot semantics

Snapshots use `giga.machine-source-snapshot.v1`.

For a Git repository the snapshot binds:

- HEAD, branch and tree;
- every Git ref and its object identity;
- all registered worktrees, including prunable/missing worktrees;
- porcelain status;
- the binary diff against HEAD;
- exact hashes of modified, staged and untracked files;
- submodule state and Git connectivity result.

Committed file contents are bound by Git tree and ref identities. Dirty and
untracked contents are bound independently so that a clean commit cannot hide
uncommitted candidate work.

For a non-Git software tree the snapshot binds every included file, directory
and symlink by relative path, portable mode, size, SHA-256 or link target.
Declared dependency, cache, generated-build and runtime exclusions are written
into the snapshot and therefore cannot be mistaken for inspected content.

Snapshots are written atomically, sealed with a manifest digest and made
read-only. A pair receipt binds the Mac snapshot, Gutua snapshot and exact
authority registry. Snapshot creation performs no promotion or comparison.

## Reconciliation boundary

This policy and its snapshots implement only the evidence boundary. They do not:

- choose which host has the better implementation;
- merge branches or copy project trees;
- start or stop services;
- delete redundant copies;
- certify JAA, Orchestrator or Dubbing Studio;
- change the active Git branch of any project.

Those are later, separately authorised operations.
