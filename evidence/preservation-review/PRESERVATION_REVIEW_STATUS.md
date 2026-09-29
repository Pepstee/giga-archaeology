# Archaeology preservation review status

Date: 2026-09-28
Status: `PARTIAL_BLOCKED`
Goal: preserve and adjudicate the scoped donor modularisation history

## Canonical owner

- Host: ArtVault
- Workspace: `/srv/artvault/projects/giga-archaeologist/workspace`
- Branch: `codex/artvault-portable-giga-archaeology`
- Baseline HEAD before the preservation-ledger increment: `cddc30e165928e83316e3116b129a9183a3dceb0`
- Upstream: `origin/codex/artvault-portable-giga-archaeology`
- Baseline HEAD/upstream equality: `0 ahead, 0 behind`
- Preservation-ledger revision subsequently pushed and fetched: `8844a39008b98a38aba357b5eb28c2eae704db65`
- Existing untracked `__pycache__` directories: preserved
- Authority-register ArtVault entry head: `2f9f5a3b576b7558274d9a22cae43410d160ef6e`
- Authority-register worker state: `launch_pending`
- Exact register ownership state: ArtVault `canonical_development_owner`; legacy Mac
  entry `inactive_after_artvault_handoff`
- Register head/worker fields: stale relative to current HEAD and this same-session goal; register not modified

The registered authority is `/srv/artvault/control/machine-authority.v1.json`. Its
ArtVault handoff names this workspace as the canonical development owner and explicitly
supersedes the legacy Mac-wide canonical field for this destination. The authority file
was read only and was not modified.

## Donor coverage

- Expected donor ref: `codex/preserve-giga-modularisation-history-20260928`
- Expected donor commit: `d29d209e9094302937c60d28aeab7a54f78ede27`
- Expected scope: 62 Python files and 33,497 additions
- Verified files: `0/62`
- Verified additions: `0/33,497`
- Verified donor dispositions: `0`
- Comparison-only archive dispositions: `13` (not donor-verified)
- Verified canonical integrations: `0`

## Exact blocker

The donor commit and ref are absent from the canonical repository's local objects and
refs. A scoped query of the configured `giga-user-archive` remote for the exact branch
failed in the normal runtime with:

`fatal: unable to access 'https://github.com/Pepstee/giga-user.git/': Could not resolve host: github.com`

The same exact-ref query through the approved network route failed with:

`fatal: could not read Username for 'https://github.com': No such device or address`

No full donor-history fetch, clone, worktree, mirror, project snapshot, or private-corpus
transfer was attempted. A scoped code-only donor export or an accessible read-only ref is
required before file-level review can begin.

The configured named remote URL is `https://github.com/Pepstee/giga-user.git`, and the
exact donor commit object check also returned `fatal: Not a valid object name`; no donor
object was imported.

Latest exact-ref recheck was unchanged: normal runtime again failed with the recorded
DNS error, and the approved network route again failed with the recorded GitHub
authentication error. No source route became available.

## Historical Mac metadata reconciliation

The following results were supplied from a completed read-only metadata reconciliation
against the inactive Mac historical Git object store. No checkout, source-code read, code
execution, or write was performed there; these results are evidence only and do not
establish donor coverage:

| Comparison | Scope | Files | Additions |
| --- | --- | ---: | ---: |
| `d29d209e9094302937c60d28aeab7a54f78ede27` vs `origin/main` | all-text numstat | `696` | `2,217,709` |
| `d29d209e9094302937c60d28aeab7a54f78ede27` vs `origin/main` | Python-only | `210` | `74,974` |
| `d29d209e9094302937c60d28aeab7a54f78ede27` vs `ab4b6111` | all-text numstat | `352` | `71,795` |
| `d29d209e9094302937c60d28aeab7a54f78ede27` vs `ab4b6111` | Python-only | `136` | `52,991` |

Prefix aggregation found no subtree matching exactly `62` files and `33,497` additions
for either base or either file scope. The claimed donor scope therefore remains
unreconciled; verified donor coverage remains `0/62` and `0/33,497`.

An additional read-only reconciliation covered all `143` first-parent snapshots,
including `d29d209e9094302937c60d28aeab7a54f78ede27`, against both `origin/main` and
`ab4b6111`. No snapshot had exactly `62` numeric-text paths plus `33,497` additions;
Python-only checks also found no match. No checkout, source-code read, execution, or
write occurred in the inactive Mac object store. This further leaves the claimed donor
scope unreconciled and does not change verified coverage.

## Scoped tarball comparison evidence

`/srv/artvault/incoming/archaeology-scoped-candidate.tar.gz` is retained as comparison
evidence only. It is not the named donor ref and does not establish donor coverage.

- SHA-256: `489e26ec657399fa5a0167769cc34383643cfcd5b2f56807d1568167da37de43`
- Archive regular files: `78`
- Archive regular-file bytes: `2,482,217`
- Archive date: `2026-09-09`
- Ref/commit provenance: absent
- Extraction: none
- In-memory stream comparison with current canonical source: `65` exact matches, `13` different, `0` missing
- Archive-to-canon line delta: `+209/-87`
- In-memory provenance scan: `0` named-ref hits, `0` named-commit hits, and `0` `.git`
  metadata members among the `78` regular files
- Observed differences: current-canon portability, optional Giga integration, explicit sandbox opt-out, code-only Graphify metadata, and related tests

The comparison-only differing paths are:

- `modules/operations/archaeology/history.py`
- `modules/operations/archaeology/hypotheses.py`
- `modules/operations/archaeology/inventory.py`
- `modules/operations/archaeology/mapper.py`
- `modules/operations/archaeology/navigation_inventory.py`
- `modules/operations/archaeology/navigation_maintenance.py`
- `modules/operations/archaeology/retention.py`
- `modules/operations/archaeology/scip_map.py`
- `modules/operations/scripts/archaeology.py`
- `scripts/graphify_codex_backend.py`
- `tests/test_archaeology_hypotheses.py`
- `tests/test_archaeology_mapper.py`
- `tests/test_graphify_codex_backend.py`

This is a bounded tarball-to-canon path mapping only. The 65 exact paths and these 13
different paths are not donor-file verification, feature disposition, or evidence for
the named donor ref; donor coverage remains `0/62`.

For each differing path, the comparison target is the same relative path in the
canonical workspace; its current disposition is `comparison-only / donor provenance
unverified`, pending proof of the named donor ref:

| Comparison path | Canonical target | Disposition |
| --- | --- | --- |
| `modules/operations/archaeology/history.py` | same canonical path | comparison-only; provenance unverified |
| `modules/operations/archaeology/hypotheses.py` | same canonical path | comparison-only; provenance unverified |
| `modules/operations/archaeology/inventory.py` | same canonical path | comparison-only; provenance unverified |
| `modules/operations/archaeology/mapper.py` | same canonical path | comparison-only; provenance unverified |
| `modules/operations/archaeology/navigation_inventory.py` | same canonical path | comparison-only; provenance unverified |
| `modules/operations/archaeology/navigation_maintenance.py` | same canonical path | comparison-only; provenance unverified |
| `modules/operations/archaeology/retention.py` | same canonical path | comparison-only; provenance unverified |
| `modules/operations/archaeology/scip_map.py` | same canonical path | comparison-only; provenance unverified |
| `modules/operations/scripts/archaeology.py` | same canonical path | comparison-only; provenance unverified |
| `scripts/graphify_codex_backend.py` | same canonical path | comparison-only; provenance unverified |
| `tests/test_archaeology_hypotheses.py` | same canonical path | comparison-only; provenance unverified |
| `tests/test_archaeology_mapper.py` | same canonical path | comparison-only; provenance unverified |
| `tests/test_graphify_codex_backend.py` | same canonical path | comparison-only; provenance unverified |

These facts do not change donor coverage, which remains `0/62` files and `0/33,497`
additions until the named donor commit is proven.

## Comparison-only semantic dispositions

The following are dispositions of the archive-to-canon deltas only. They identify the
current canonical target and the observed safe disposition; they do not verify the
named donor and do not increase donor coverage.

| Path | Observed archive delta | Comparison disposition and canonical target |
| --- | --- | --- |
| `modules/operations/archaeology/history.py` | Replaces `os_support` Git discovery/environment policy with `/usr/bin/git` and a reduced environment | Retain current portable helper behavior; no archive integration; target remains the canonical `history.py` |
| `modules/operations/archaeology/hypotheses.py` | Removes `/usr/local/bin` from the scanner `PATH` | Retain current canonical PATH policy; no archive integration; target remains the canonical `hypotheses.py` |
| `modules/operations/archaeology/inventory.py` | Replaces portable Git discovery/environment policy with `/usr/bin/git` | Retain current portable helper behavior; no archive integration; target remains the canonical `inventory.py` |
| `modules/operations/archaeology/mapper.py` | Makes `twin_core` capability adoption unconditional and removes absent-optional-backend handling | Retain optional Giga integration and its explicit absence behavior; no archive integration; target remains the canonical `mapper.py` |
| `modules/operations/archaeology/navigation_inventory.py` | Replaces portable Git discovery and ignore/ancestry helpers with `/usr/bin/git` | Retain current portable helper behavior; no archive integration; target remains the canonical `navigation_inventory.py` |
| `modules/operations/archaeology/navigation_maintenance.py` | Replaces shared locking helper with POSIX-only `fcntl.flock` | Retain shared cross-platform locking; no archive integration; target remains the canonical `navigation_maintenance.py` |
| `modules/operations/archaeology/retention.py` | Replaces shared locking helpers with POSIX-only `fcntl.flock` | Retain shared cross-platform locking; no archive integration; target remains the canonical `retention.py` |
| `modules/operations/archaeology/scip_map.py` | Replaces shared locking helpers with POSIX-only `fcntl.flock`/descriptors | Retain shared cross-platform locking; no archive integration; target remains the canonical `scip_map.py` |
| `modules/operations/scripts/archaeology.py` | Removes the explicit `--no-sandbox` opt-out and its plumbing | Retain the current documented CLI contract; no archive integration; target remains the canonical `archaeology.py` |
| `scripts/graphify_codex_backend.py` | Always records a Codex backend and queries Codex version, including code-only extraction | Retain code-only Graphify metadata that does not require Codex; no archive integration; target remains the canonical `graphify_codex_backend.py` |
| `tests/test_archaeology_hypotheses.py` | Deletes sandbox opt-out CLI tests | Retain current regression coverage; no archive test deletion; target remains the canonical test file |
| `tests/test_archaeology_mapper.py` | Deletes optional-backend and broken-dependency tests | Retain current optional-integration regression coverage; no archive test deletion; target remains the canonical test file |
| `tests/test_graphify_codex_backend.py` | Deletes the code-only/no-Codex assertion | Retain current code-only regression coverage; no archive test deletion; target remains the canonical test file |

Current-canon verification for these comparison targets: `51 passed, 2 subtests passed`
in `tests/test_archaeology_hypotheses.py`, `tests/test_archaeology_mapper.py`, and
`tests/test_graphify_codex_backend.py`. This validates current behavior only; it is not
validation of the unproven archive or the named donor.

## Delegation and graph boundary

- Suitable donor batches: `BLOCKED`, because synchronized code-only inputs are unavailable.
- GLM worker launch: none. No alternate model or duplicate worker was substituted.
- Graph status: `STALE`. The existing source-graph manifest predates the current repair and
  does not include `modules/operations/archaeology/os_support.py` or
  `tests/test_os_support.py`.
- Existing graph manifest evidence: `4,879` bytes, SHA-256
  `c6ac4fc2e3e01ee139fb41c1a7205e54922b82701531e413e5da9934112e1c31`; exact membership
  checks for both repaired paths returned `False`.
- Whole-donor, no-feature-loss, retirement, and cleanup claims: not made.

## Blocked and not-applicable units

| Unit | State | Evidence-bound disposition |
| --- | --- | --- |
| Donor ref `codex/preserve-giga-modularisation-history-20260928` | `BLOCKED` | Exact ref query fails DNS in the normal runtime and authentication on the approved route; no donor object is local |
| Donor commit `d29d209e9094302937c60d28aeab7a54f78ede27` | `BLOCKED` | Exact commit-object check is invalid; the archive has no ref/commit provenance |
| 62-file membership and 33,497 additions | `BLOCKED` | Cannot be reconciled without proven donor ref/export; coverage stays `0/62` and `0/33,497` |
| GLM code-only batches | `BLOCKED / NOT STARTED` | Synchronized donor inputs and a verified route are unavailable; no worker launched |
| Archive 78-file comparison | `COMPARISON-ONLY` | 65 exact, 13 different, 0 missing; usable for bounded canon comparison but not donor coverage |
| Donor feature integrations | `NOT APPLICABLE` | No donor-proven feature can be selected or integrated from provenance-free evidence |
| Source-graph refresh | `DEFERRED; STALE RECORDED` | Existing manifest omits the repaired paths; refreshing it would not resolve donor provenance |
| Windows locking repair | `VERIFIED` | Focused repair and affected tests passed; pushed and fetched in the canonical branch |

## Unaffected verified work

- Windows non-blocking lock error classification repaired in
  `modules/operations/archaeology/os_support.py`.
- Focused repair tests added in `tests/test_os_support.py`.
- Affected verification: `101 passed`.
- Latest affected-suite rerun: `101 passed in 5.41s` with
  `PYTHONDONTWRITEBYTECODE=1`.
- Latest combined affected/comparison-suite rerun: `152 passed, 2 subtests passed in
  24.59s` with `PYTHONDONTWRITEBYTECODE=1`.
- Repair commit: `cddc30e165928e83316e3116b129a9183a3dceb0`.
- Repair commit pushed and fetched; local HEAD and upstream equal that exact revision.

## Required continuation

Reopen this status only when a scoped, code-only source for the named donor ref is
available. Then produce the complete per-file/per-feature coverage ledger, canonical
mapping, disposition, independent validation, integration result, and remote revision
proof. Until then this review remains `PARTIAL_BLOCKED`.

## Remote revision proof

- Repair revision: `cddc30e165928e83316e3116b129a9183a3dceb0`
- Preservation-ledger revision: `8844a39008b98a38aba357b5eb28c2eae704db65`
- Comparison-disposition revision: `433d2e4c41085207273805896bb1e2441c16b781`
- Metadata-reconciliation revision: `4faabae800573dd2d145890957c91ccee1b363be`
- Combined canonical-test revision: `c46e06b53178307a058fd9208ab60dfc42e5da9a`
- First-parent scope-reconciliation revision: `f6471dac5d70d0f1d46068d1bfe129d3f11f295f`
- The preservation-ledger revision was pushed to
  `origin/codex/artvault-portable-giga-archaeology` and fetched back; the exact check
  was `0 ahead, 0 behind`.

## 2026-09-29 — authentication and GitHub publication access update

This addendum supersedes the earlier statement that commit
`d29d209e9094302937c60d28aeab7a54f78ede27` could not be retrieved at all. A read-only authenticated
GitHub API route can retrieve that commit from `Pepstee/giga-user`; ArtVault's own HTTPS remote to
that repository still fails because GitHub credentials are not configured there.

- Control Tower confirmed the named branch `codex/preserve-giga-modularisation-history-20260928`
  exists in the historical Mac object store but is not published as a GitHub branch. The exact branch
  lookup returns 404.
- The GitHub API returns commit `d29d209e9094302937c60d28aeab7a54f78ede27`, parent
  `5e6aa8bc13a8ae228f741f08c4ab3ff7e7f50039`, with 10 changed files, 127 additions and 60 deletions.
  GitHub reports its signature status as unsigned. This is a single commit, not the requested
  62-file / 33,497-addition scope.
- Therefore the commit object is now API-retrievable, but its relationship to the missing named ref,
  the requested donor scope, and the full addition set remains unproven. Donor coverage stays
  `0/62` files and `0/33,497` additions. No donor code was integrated from this observation.
- GitHub repository metadata identifies `Pepstee/giga-archaeology` as private; its releases endpoint
  currently returns an empty list. Public discoverability and stars require a later operator-directed
  publication decision. No visibility, credential, key, or release setting was changed.

The authentication failure is thus narrowed to missing GitHub credentials for the archive repository
on ArtVault. The connected GitHub API is sufficient for bounded read-only commit inspection, but it
does not provide a verified ref or an authenticated Git transport for the full donor scope.

## 2026-09-29 — exact donor-scope and Archaeology CLI review

Control Tower reproduced the requested scope from base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` to donor `d29d209e9094302937c60d28aeab7a54f78ede27`. Exact pathspecs were `research/free-inference-fabric/src`, `research/free-inference-fabric/tests`, `twin_core`, `modules/operations/archaeology`, `modules/operations/scripts`, and `modules/research`. The result is 62 Python paths, 33,497 additions and 255 deletions; the sorted manifest digest is `f07e4dbd4711b5ede7f6ac5ee08ef981ea9348ab5f9e3bbf3a03527a1169ac7f`. Compared with Archaeology canon commit `0fb589b6fc21312bd357770def3e363772a9c3de`, 4 paths differ and 58 are absent at the same path. This path-only result does not establish capability loss or ownership.

One file has been fully reviewed in bounded source ranges: `modules/operations/scripts/archaeologist.py`, 493 added lines, donor blob `044aaa152e08d097f5e91bca485ca1e5fdc1f815`, content SHA-256 `33e57f7975d36472ceb3fa1a3a55c762f3f5b3015e3e805458373eb57a220d2c`. The verified ranges were 1–180, 181–360 and 361–493. The only CLI feature missing from the current Archaeology command surface was `navigation-retention`. The canonical `modules/operations/archaeology/retention.py` already defines `RetentionPolicy` and `run_navigation_retention`, with direct behavior tests in `tests/test_archaeology_retention.py`. The donor’s 15 retention tests cover implementation behavior but contain no dedicated CLI wiring test.

The canonical `modules/operations/scripts/archaeology.py` now exposes the donor’s retention command and options, with mutation remaining opt-in through `--apply`. A CLI regression test verifies the serialized policy and sealed `DRY_RUN` receipt. Verification on ArtVault Linux: the focused test passed; the full retention test file passed 83 tests; direct CLI help lists the new command. The code and test change is not yet committed at the time of this note.

Coverage is 1/62 files and 493/33,497 additions. The other 61 files have not been reviewed or integrated. No donor source was sent to GLM. ArtVault has repo-scoped SSH access to Archaeology but no verified route to `Pepstee/giga-user`; bounded source inspection used the authenticated Mac Git object store. Public visibility and release remain separate operator-directed actions and have not occurred.

## 2026-09-29 — CLI commit and graph provenance follow-up

The Archaeology CLI integration and regression test were committed as aafe486bcdf34a1ebd680f6a1bac379eb8ceefb7 and pushed to origin/codex/artvault-portable-giga-archaeology; the upstream comparison is 0 ahead and 0 behind. This supersedes the earlier note that the code and test were not yet committed.

The source graph was refreshed in a source-scoped update at that commit. All 1,222 prior nodes and 3,824 prior edges were preserved; two call edges were added. The resulting graph has 1,222 nodes, 3,826 edges and 36 communities. Graph SHA-256: 60026e2f5e31c579c369a6b22979171b400a5e0b90817b09d44af1c49e0d52ec. Manifest SHA-256: a0131c3c2abe40cd021e04b96a36b1b494d5965b4f7844820248444e9c0be9e2. The Graphify path query reaches run_navigation_retention() from the CLI entrypoint. The corrected refresh has no unrelated node or edge removals.

## 2026-09-29 — Control Tower auth-route resolution

Control Tower rechecked the live routes. The registered ArtVault Archaeology origin and its repo-scoped key are healthy: branch lookup returns the same commit as the canon, and GitHub identifies the key as read/write for Pepstee/giga-archaeology. GitHub's SSH exit code 1 with its standard no-shell message is expected and is not an authentication failure.

The donor failure is specific to ArtVault Git transport for Pepstee/giga-user: its unauthenticated HTTPS request cannot prompt for credentials. ArtVault does not have the donor repo alias or gh CLI. The authenticated Mac GitHub API can read bounded donor commit metadata; it does not prove access to the requested named branch or whole scope. No canon push route was broken. Operator-authorized remediation is now in progress: a dedicated read-only deploy key on ArtVault for that exact donor repository, without reusing the Archaeology key or transferring Mac account tokens. No visibility or ref changes are part of this work.

## 2026-09-29 — donor read-auth remediation completed

Control Tower provisioned a dedicated Ed25519 deploy key on ArtVault and registered it only as a verified read-only key on Pepstee/giga-user. ArtVault retains the private key; no token or private key was transferred. A strict-host-checking SSH alias now targets only this repository. Fresh ls-remote succeeds and reports HEAD f4d8e694289d035991c6d3c0b33b35c15a05c53c. The Archaeology key and origin are unchanged.

Authentication is resolved for bounded donor reads. The previously requested historical branch is still unpublished as a ref, so its absence remains a provenance/ref limitation; the pinned donor commit and exact manifest remain the verified scope. No clone, archive copy, checkout, visibility/ref change, or source export was performed.
