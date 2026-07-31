# DFI-06 expanded completion work order

## Starting point

- Worktree: `/home/gutua/software-factory/.worktrees/orchestrator-v3-dfi-06`
- Branch: `di/dfi-06-delta-economics`
- Committed base: `4be0741`
- Preserved dirty checkpoint hash before resumed repair:
  `04c51570027c7372b69e650b9df91922d7685bf92582747f7af0df281a92a947`
- STOP remains armed.
- Production orchestrator and JAA are out of scope.

## Mission

Complete the already-started signed review-evidence journal and integrate it with the
DFI-06 full-versus-delta economics comparator. Do not redesign the subsystem again.
Close the eight findings in
`codex_signed_implementation_rereview.txt`, migrate all affected fixtures and callers,
run the targeted suite, and stop on a coherent passing candidate.

## Required properties

1. Ed25519 signing and verification work with real OpenSSL. The signing implementation
   must handle Ed25519's one-shot input requirement without exposing the private key or
   weakening descriptor ownership.
2. Public key, canonical key fingerprint, runtime identity, operation identity, scope,
   envelope, and complete journal provenance are mandatory at every public comparison
   boundary.
3. Journal entries, pending records, and sealed heads have exact schemas and mandatory
   signatures. No unsigned or legacy bypass exists in the production path.
4. Pending recovery authenticates both prior and proposed states, handles both crash
   branches, and durably removes settled pending state.
5. Parent paths and final files are opened relative to protected directory descriptors
   with no symlink traversal. Stable lock ownership and post-replace authoritative reopen
   are mechanically tested.
6. Every historical receipt and every new receipt is validated according to its exact
   full or delta host-assurance contract.
7. Full/delta relationships are mandatory and exact, including operation lineage,
   exhaustive/reviewed resources, criteria, prior findings, and affected invariants.
8. Identities include every effective field, including elapsed data and signed
   provenance. Mutation tests prove omissions and substitutions miss or refuse.

## Working rules

- Sonnet is the primary coder. Codex performs independent review and certification.
- Only one writer may hold the worktree lease.
- Run focused tests during repair; run the full suite only after focused convergence.
- Do not weaken a production invariant merely to preserve obsolete tests. Migrate tests
  to the ratified mandatory contract.
- Do not add compatibility shims, optional fallbacks, placeholders, stubs, mocks posing
  as integration evidence, or hidden side stores.
- Stay inside the allowlist and 2,200-line hard ceiling in
  `DFI06_OPERATOR_SCOPE_RATIFICATION_2026-07-24.md`.
- End the coding pass with a concise changed-file summary and exact test results. Do not
  commit; the independent certifier owns the final commit.
