# Slice 01 report — immutable inventory

## Outcome

Slice 01 is independently useful now. `giga-archaeologist inventory` produces a
deterministic, self-hashed repository inventory without importing target code or
writing inside the target repository.

The live candidate inventory recorded:

- 1,073 included tracked/admitted files;
- 1,970 Python symbols;
- 40 declared entrypoints;
- 69 byte-identical duplicate groups;
- 157 sensitive paths excluded without recording their names;
- zero Python parse failures.

The inventory receipt is
`49d11d0681b7cc8a833afc88fb3a81ac6529e28ca439d18de565555c8c87e471`.
The complete local evidence is stored outside Git at
`/Users/admin/Documents/developer-tools/giga-archaeologist-evidence/slice01-e361d7fc`.

## Safety properties proved

- Target code is parsed with `ast`; it is never imported or executed.
- Git runs with optional locks disabled and global/system configuration ignored.
- Repository symlinks are hashed as link text and never followed.
- File identity, size and mutation timestamps are checked around every read.
- Untracked files are unread unless named by an explicit exact-path admission.
- Personal-memory, corpus, Vault, application, private-output and secret prefixes
  are excluded; only the excluded-path-list hash and count are retained.
- Evidence output must be external, create-once and mode 0600 under a private
  directory.
- The document says `cleanup_permitted=false` and grants no authority.

## Reuse and duplicate search

The existing `modules/operations` package is the canonical owner. Searches of
both GIGA trees, all current branches/worktrees, the old `audit-work/v3` probe,
and the existing modularisation graph found no Archaeologist owner. Existing
Graphify and migration receipts are reused as evidence sources; the separate
scanner installation remains outside the repositories.

## Verification

- Focused inventory tests: 6 passed.
- Complete operations tests: 45 passed.
- Ruff lint and formatting: passed.
- Candidate inventory CLI: passed against the real worktree.
- Git whitespace check: passed.
- Repository state remained unchanged by the inventory command.

The same one-shot temporary evidence was moved recoverably to
`/Users/admin/.Trash/giga-archaeologist-slice01-e361d7fc-install-proof` after the
canonical external copy was generated.

## Knowledge graph status

The existing modularisation graph was queried before implementation and contains
330 nodes and 1,210 edges. It predates this slice, so it remains `PARTIAL`: the
new Archaeologist files are not yet represented. No architecture-completeness or
no-feature-loss claim relies on that stale graph.

## Nonclaims

No scanner has run. No hypothesis has been generated or accepted. Nothing has
been called dead, redundant, disconnected, or safe to remove. No quarantine,
cleanup, deletion, migration, protected integration or deployment occurred.
