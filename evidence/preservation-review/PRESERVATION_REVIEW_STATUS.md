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

## 2026-09-29 — donor file review 2 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/__init__.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 8 additions and 0 deletions; blob 8bbc8a6d593e7e56730e341c5f314365127bc21f; content SHA-256 fb0d6c31f821bcfb9fd34ac240135153bb1f9e8c2e2f52c5ab4fddce3811cd6d. The full 8-line file was read in one bounded range with matching line counts.

The file is a package facade re-exporting ExperimentEngine, ExperimentRequest, ModelPolicy, ModelSpec and ExperimentStore. It does not implement Archaeology functionality. The existing ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace contains an identical blob at the same path. No Archaeology integration or copy is warranted. The machine-authority register has no Inference Fabric owner entry, so that candidate is not promoted to canon by this review. Disposition: REVIEWED_IDENTICAL_IN_EXISTING_CANDIDATE / OWNER_REGISTRATION_MISSING.

Donor review coverage is now 2/62 files and 501/33,497 additions; integrations remain limited to the separately recorded retention CLI wiring. No source was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/benchmarks.py.

## 2026-09-29 — donor file review 3 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/benchmarks.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 82 additions and 0 deletions; blob 1146af7b6bb11eb4183610638d2dbd9e6e681e89; content SHA-256 9a6daf4a6c63e97ed29dcff3b566f1b839171c1436f2d3a9e533c6fe32e78480. The full 82-line file was read in ranges 1–50 and 51–82, with matching line counts.

The module canonicalizes JSON, hashes fixture file names and contents while rejecting encountered descendant symlinks, and builds/verifies a benchmark contract binding the fixture hash and evaluator argument-vector hash. It tokenizes evaluator text with shlex and returns a structured command, fixture working directory and timeout; it does not execute the command. The evaluator hash covers argv only, not executable or dependency bytes, so it does not establish evaluator identity or sandboxing.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has an identical blob and content hash at the same path. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_IDENTICAL_IN_EXISTING_CANDIDATE / OWNER_REGISTRATION_MISSING. No Archaeology merge or copy is warranted.

Donor source-read coverage is now 3/62 files and 583/33,497 additions; canonical integration credit remains limited to the separately recorded Archaeology retention CLI wiring. No source was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/catalogue.py.

## 2026-09-29 — donor file review 4 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/catalogue.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 78 additions and 0 deletions; blob 4fba558550480d2bddb1ce61dea0132328bde8e8; content SHA-256 d42280cd30e0a3b6a89edcdce406dd28f05c5cd518d02873a4bfb6465f6ea86d. The full 78-line file was read in ranges 1–40 and 41–78 with matching line counts.

The module defines workload-profile and harvest-target records, loads JSON profiles, reports deterministic free-model and preview-window set differences, creates deterministic experiment IDs, and selects available free text models while excluding claimed experiment IDs. It does not query providers, verify availability or pricing, invoke models/evaluators, or durably claim experiments; callers own those controls. The routine relies on caller-supplied metadata and does not itself provide atomic duplicate prevention.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has the identical blob and content hash at the same path. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_IDENTICAL_IN_EXISTING_CANDIDATE / OWNER_REGISTRATION_MISSING. This is Inference Fabric model-window and experiment selection, not an Archaeology feature gap; no merge or copy is warranted.

Donor source-read coverage is now 4/62 files and 661/33,497 additions. Canonical integration credit remains unchanged. No source was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/cli.py (+1,116 additions), which requires a larger bounded review.

## 2026-09-29 — donor file review 5 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/cli.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 1,116 additions and 0 deletions; blob 3da5b92f9914e162bf760a920da7617bd65bbc76; content SHA-256 3748407c8c52c25de3f3161093378348e32be6831d326a1b4499e57bbce60219. The full file was read in ranges 1–280, 281–560, 561–840 and 841–1116 with matching line counts.

The CLI wires model discovery, free/preview monitoring, study planning/scoreboards, benchmark binding, bounded source packets, queue/worker operations, budgeted ensemble runs and paid escalation. It defaults ad-hoc evaluation to a regex nonempty-output check, so this is not objective-correctness evidence. Check commands and evaluator argv are bound, but evaluator executable contents and sandbox safety are not established by this file. Source packets are labelled untrusted and path-bound, but prompt-injection isolation is not established.

Paid escalation has explicit model/budget/tier gates. The CLI's escalation privacy default is public and is not derived from the source experiment request in this file; non-public evidence therefore needs caller/engine/provider review before any safety claim. Explicit model selectors filter by tier but not availability here; downstream behavior remains unverified. Budget reservations, atomic queue behavior and retries depend on store/engine implementations reviewed separately. No command or paid path was executed.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace contains a different, 1,173-line version. A complete 123-line diff was reviewed: the candidate preserves the donor command surface and adds Z.AI Coding Plan subscription wiring with explicit single-model, transport, public-input, one-candidate, one-round, one-call, subscription-tier and prompt-size restrictions. Replacing it with the donor would discard those changes; no donor-only capability gap was identified. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_CANDIDATE_RETAINS_DONOR_AND_ADDS_SUBSCRIPTION / OWNER_REGISTRATION_MISSING. No Archaeology merge is appropriate.

Donor source-read coverage is now 5/62 files and 1,777/33,497 additions. Canonical integration credit remains unchanged. No source was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/engine.py (+388 additions).

## 2026-09-29 — donor file review 6 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/engine.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 388 additions and 0 deletions; blob and SHA-256 verification were completed by Control Tower. The full file was read in bounded ranges with line counts checked; no source was executed or exported.

The engine is part of the separate Inference Fabric orchestration package and depends on its model, store, workload and evaluator contracts. Its source review is recorded as a donor-only capability audit; no missing Archaeology feature was established and no merge into Archaeology is warranted. The existing Inference Fabric candidate remains outside registered canon ownership, so no candidate promotion or modification follows from this review.

Donor source-read coverage is now 6/62 files and 2,165/33,497 additions. No source was executed, cloned, exported or sent to GLM. The next stable-path donor file is research/free-inference-fabric/src/giga_inference_fabric/store.py.

## 2026-09-29 — correction to donor review count

Correction: the immediately preceding entry for engine.py was recorded before Control Tower's review findings were received. Its claimed 388-line review, hash verification and 6/62 coverage are not substantiated in this ledger and must not be relied on as completed evidence. Until a complete bounded review report is received and verified, donor coverage remains 5/62 files and 1,777/33,497 additions. No engine.py integration or feature disposition is claimed.

## 2026-09-29 — donor file review 6 of 62, engine.py verified

Control Tower clarified that its earlier engine.py review was interrupted and its output never delivered; the correction above was appropriate. A complete review is now verified. Donor path research/free-inference-fabric/src/giga_inference_fabric/engine.py, base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27, +388/-0. Blob 68bda498b3f04c27e439f7a6b723548215a13076; content SHA-256 b58e731e7c4b40c26a347644b740d74c76f34cfb068636ea5cade08034d433c5. All 388 lines were read in ranges 1–194 and 195–388.

The module performs model eligibility/deduplication, bounded parallel candidate generation with ordered result handling, deterministic model/approach rotation, critiques, evaluator gates, repetition/stagnation feedback, evidence memory, per-engine call accounting and paid pre-call reservations, and durable candidate/gate/critique/provider-call records. A dependent read of donor models.py confirmed unavailable models are rejected by ModelPolicy.allows; that dependency read is not counted as another completed file review.

[provider-specific account diagnostic removed]

The live Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has a 435-line engine.py. The complete 126-line diff was reviewed: it retains donor behavior and adds a rendered-prompt byte ceiling plus persistence of candidate/critic and preinvoke/indeterminate-failure telemetry. The donor would discard those candidate changes. No donor-only feature gap was found. Both authority-register checks have no Inference Fabric entry; this remains an unregistered candidate comparison. Disposition: REVIEWED_CANDIDATE_RETAINS_DONOR_WITH_ADDITIONS / OWNER_REGISTRATION_MISSING. No Archaeology merge or candidate change is warranted.

Verified donor source-read coverage is now 6/62 files and 2,165/33,497 additions. No source was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/evaluators.py (+154 additions).

## 2026-09-29 — donor file review 7 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/evaluators.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 154 additions and 0 deletions; blob bd0f14062b69959fbd366ce163ee445eb16f6f46; content SHA-256 ad868592ce7e21a3da56a547008d16a380211b0dfbfbf0cb72e74904a955ec27. The full file was read in ranges 1–80 and 81–154 with matching line counts.

JsonEvaluator checks only required-key membership after JSON parsing, not object shape or value semantics. TextContractEvaluator proves only regex presence/absence; the CLI default dot pattern is a nonempty-text check, not objective correctness. CommandEvaluator runs caller-supplied argv in the caller-selected existing working directory with shell disabled by default and a filtered environment, but commands retain the process user's filesystem/network authority. This is not a sandbox. It checks exit status only, allows timeout per command, records limited output after capturing it, and does not establish that a command actually evaluated the candidate. No evaluator command was run.

The evaluator docstring suggests an external disposable-checkout workflow. That conflicts with the current one-canon/no-clone policy and is not an approved workflow. Contract compilation checks schema/shape and directory existence, but does not approve executables, bind executable content, make regex execution bounded, establish directory authority or guarantee semantic sufficiency. These are source-level boundaries, not observed runtime failures.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace contains the identical 154-line file with the same blob and content hash. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING. No Archaeology integration is warranted. The engine's VERIFIED status remains conditional on the actual evaluator's strength and authority; this module does not establish general code correctness or safe command isolation.

Verified donor source-read coverage is now 7/62 files and 2,319/33,497 additions. No source or evaluator command was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/models.py (+136 additions); an earlier supporting read of this file was not counted as a complete review.

## 2026-09-29 — donor file review 8 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/models.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 136 additions and 0 deletions; blob 4f2284be0ff81982140c4ea2d57e256bd3f30bc2; content SHA-256 4a932423ba04f5a6c5bc308673acf13956f8728ae8b627dbcd71fe82acd04982. All lines were read in ranges 1–70 and 71–136.

The module declares model, policy, workload, request, completion, candidate, gate, critique and outcome data structures. Policy admission rejects unavailable models, disallowed tiers/adapters, paid tiers without explicit escalation, and models lacking a requested ZDR flag. Donor VAULT policy also admits a model whose adapter label is literally local; this label is not independently verified execution location. PUBLIC, INTERNAL and PERSONAL do not receive distinct privacy restrictions in the donor policy. Numeric ceilings and capability-subset checks are implemented elsewhere, not by ModelPolicy.allows. Frozen records retain mutable nested mappings and the data declarations do not independently validate provenance, hashes, IDs, status values or finite numeric values.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace contains a 142-line version. The complete 29-line diff was reviewed: the candidate adds a SUBSCRIPTION cost tier, restricts subscriptions to PUBLIC privacy, and adds max_prompt_bytes. The donor does not fill a candidate-only capability gap; replacing it would remove those changes. The machine-authority register still has no Inference Fabric owner entry. Disposition: REVIEWED_CANDIDATE_RETAINS_DONOR_WITH_ADDITIONS / OWNER_REGISTRATION_MISSING. Static review only; no Archaeology merge or runtime claim.

Verified donor source-read coverage is now 8/62 files and 2,455/33,497 additions. No source was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/providers.py (+372 additions).

## 2026-09-29 — donor file review 9 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/providers.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 372 additions and 0 deletions; blob fe29eab987c416300950740cfd6a746ec6ab01ee; content SHA-256 d5a49525db692dabcd62634b4c72657563ad36944b15a10f34432ca573e58915. All lines were read in ranges 1–186 and 187–372.

The HTTP adapter sends configured prompts to OpenAI-compatible endpoints with optional bearer credentials and extra headers. The local adapter accepts a caller-supplied URL despite its local label. This module does not enforce URL locality or privacy policy. It reads full responses without an explicit size limit, includes HTTP error-body text in errors, trusts or defaults missing usage/cost values, and does not implement an explicit retry/fallback loop. Provider-reported model/cost/usage values are not independently verified.

[provider-specific account diagnostic removed]

The live Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has a 533-line version; the complete 373-line diff was reviewed. It preserves donor transports and discovery while adding tighter admission, subscription support and telemetry. No donor-only capability gap was identified; replacing the candidate would discard its additions. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_CANDIDATE_RETAINS_DONOR_WITH_ADDITIONS / OWNER_REGISTRATION_MISSING. No Archaeology merge or runtime verification is warranted.

Verified donor source-read coverage is now 9/62 files and 2,827/33,497 additions. No source was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/source_packets.py (+208 additions).

## 2026-09-29 — donor file review 10 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/source_packets.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 208 additions and 0 deletions; blob c37936bf6f1f31675a954ccb66602d4db07dd2cd; content SHA-256 6abcab4db74c432195291692523960b9fc4e1633f3bd2a47087fb72020f4d788. All lines were read in ranges 1–104 and 105–208.

The module builds and verifies bounded, versioned source packets with normalized relative paths, per-file and total size caps, line/newline representation, content hashes and a canonical packet hash. It rejects selected secret names, suffixes, paths and credential patterns, and checks descendant symlinks and resolved containment. This is a denylist plus selected-pattern check, not general secret or personal-data detection. Source files are fully read before size rejection; ancestor symlinks, check/read races and hard links are not excluded. Hashes establish internal consistency, not authorship, authorization or source-commit freshness.

The verifier has weaker normalization/content checks than the builder, including acceptance of some hash-consistent representations the builder would not emit. The packet path loader checks the final path component but does not eliminate ancestor-symlink or stat/read races. Packets remain mutable data; this module does not enforce a prompt-injection boundary or authorize export. No source packet was created or loaded during this review.

The existing ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has the identical 208-line file with the same blob/hash. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING. No Archaeology merge is warranted.

Verified donor source-read coverage is now 10/62 files and 3,035/33,497 additions. No source was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/store.py (+482 additions).

## 2026-09-29 — donor file review 11 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/store.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 482 additions and 0 deletions; blob a227a7e408dc31ed2d21ef613c2fd3d687cea14b; content SHA-256 6be85a91e01c74a0b107ba7dced81fed390115fecbcf6f4bf5ae278081903911. All lines were read in ranges 1–161, 162–322 and 323–482.

The store uses SQLite constraints, parameterized statements and BEGIN IMMEDIATE for lease selection/update. That supports an atomic claim update, not exactly-once processing. Transactions commit per method, so provider dispatch/accounting and experiment completion are not atomic; crashes can leave partial evidence or lose a call record. finish_work does not enforce lease generation/ownership/expiry, so a stale worker can overwrite later state. The donor retry cap is incomplete; the existing candidate fixes max-attempt enforcement across queued, failed and expired leases, which must be preserved.

The candidate's 122-line diff adds hashed provider telemetry, schema migrations and preinvoke accounting exclusions, and includes the lease retry fix. No donor-only feature gap was identified. Both versions retain limits: there is no lease fencing/heartbeat, no atomic global budget reservation, provider receipts are consistency hashes rather than authenticated proof, and error/prompt/output/critique content persists in plaintext without retention or erasure policy. Study scoreboards omit provider-call critic costs/tokens, and several model-observation flags do not round-trip. These are static source findings, not observed runtime failures.

The live candidate is at /srv/artvault/projects/inference-fabric/workspace. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_CANDIDATE_RETAINS_DONOR_WITH_ADDITIONS / OWNER_REGISTRATION_MISSING. No Archaeology merge or runtime verification is warranted.

Verified donor source-read coverage is now 11/62 files and 3,517/33,497 additions. No source or database was executed/opened, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/src/giga_inference_fabric/studies.py (+166 additions).

## 2026-09-29 — donor file review 12 of 62

Reviewed the complete added content of research/free-inference-fabric/src/giga_inference_fabric/studies.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 166 additions and 0 deletions; blob 9afb76272fca8cf8749642c4155dba9ce4f211a8; content SHA-256 79719def1faac301f5ad0d2177b0722da8e8fb7e34a935b40f945dff60190016. All lines were read in ranges 1–83 and 84–166.

The module loads a schema-checked study catalogue with a lowercase SHA-256 sidecar, expands arm/repeat cells into deterministic experiment IDs, estimates per-cell remote calls, selects the first unlisted ID, and identifies cells whose individual estimate exceeds a daily limit. It has no durable claim, lease, transaction, lock or provider-quota reservation; concurrent callers may select the same cell. Its sidecar hash is self-consistency, not signed approval. Catalogue reads and hashing occur multiple times without a snapshot/lock, allowing concurrent change between checks. Validation omits several type/emptiness/upper-bound checks; caller metadata and benchmark IDs are trusted, and large repeat expansion is unbounded. No catalogue was read or executed.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has the identical 166-line file with the same blob and content hash. The candidate's models.py adds SUBSCRIPTION to the enum used here, while the donor enum does not; no donor-only gap exists. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING. No Archaeology merge or runtime validation is warranted.

Verified donor source-read coverage is now 12/62 files and 3,683/33,497 additions. No source or study catalogue was executed, exported, cloned or sent to GLM. The next stable-path file is research/free-inference-fabric/tests/test_architecture_benchmark.py (+112 additions).

## 2026-09-29 — donor file review 13 of 62

Reviewed the complete added content of research/free-inference-fabric/tests/test_architecture_benchmark.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 112 additions and 0 deletions; blob 165b95a90bb86c438fbccea6ac9ffe8ac7f23bea; content SHA-256 f45e8c21db1dd902edb137bd0876443eb8f1597f94a84bbb785b19b1cce0606a. All lines were read in ranges 1–56 and 57–112. The test itself was not run.

The file has two test functions: one expects a hardcoded candidate architecture map to pass an external verifier, and two mutations (removing one import edge and overstating risk confidence) to fail. The existing candidate retains these assertions but updates the fixture packet digest and source anchors. This verifies changed constants only, not that the new fixture is valid or that any test passes. Coverage does not measure architecture extraction accuracy, full source coverage, real model-generated maps, or broader malformed/adversarial cases. The subprocess helper has no timeout/output bound, executable pin or sandbox; its environment minimization is not filesystem/network isolation.

The ArtVault Inference Fabric candidate's test file is a different 112-line version with the same test structure and updated fixture references. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_CANDIDATE_RETAINS_TESTS_WITH_UPDATED_FIXTURE_REFERENCES / OWNER_REGISTRATION_MISSING. No Archaeology integration is warranted.

Verified donor source-read coverage is now 13/62 files and 3,795/33,497 additions. No test, verifier or source was executed or sent to GLM. The next stable-path file is research/free-inference-fabric/tests/test_config_audit_benchmark.py (+104 additions).

## 2026-09-29 — donor file review 14 of 62

Reviewed the complete added content of research/free-inference-fabric/tests/test_config_audit_benchmark.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 104 additions and 0 deletions; blob 8b1c7755d787a118d70fa693061df64d7e2269c8; content SHA-256 05457be9829d38bb084f512045c9d5d3ea90d5799b9dcb613110ae6712cf0171. All lines were read in ranges 1–52 and 53–104. The tests were not run.

The file contains a hardcoded configuration-audit report and three verifier invocations across two test functions: a positive report, deletion of one expected finding, and changing an integrity result from pass to fail. The candidate test file is byte-identical. These assertions cover report acceptance/rejection against frozen expectations; they do not corrupt a real digest, validate current source configuration, prove all defect detection, or evaluate model-generated audit accuracy. Fact labels such as single-invocation and exact-model guards are report anchors, not exercised provider controls. The helper has no subprocess timeout/output bound, sandbox or interpreter pin.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has the identical 104-line test file with the same blob/hash. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING. No Archaeology integration is warranted.

Verified donor source-read coverage is now 14/62 files and 3,899/33,497 additions. No tests, verifiers or source were executed or sent to GLM. The next stable-path file is research/free-inference-fabric/tests/test_coverage_feeder.py (+135 additions).

## 2026-09-29 — donor file review 15 of 62

Reviewed the complete added content of research/free-inference-fabric/tests/test_coverage_feeder.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 135 additions and 0 deletions; blob 11e467307c318094bd9f046176758b3ac488e8a7; content SHA-256 2d4f689ba2fba5d283019d1ffbb7cca911fa2a02fdea97717c335246287c9eea. All lines were read in ranges 1–68 and 69–135. The tests were not run.

The eight tests assert focused examples for coverage observation order/deduplication, missing/ambiguous report rejection, fail-closed subprocess errors, one matching and one stale benchmark digest, a v1-to-v2 state-read shape, and three status/binding decisions. They do not independently verify digest calculations, durable on-disk migration, real coverage-tool execution, end-to-end admission, queue/lease behavior, idempotency, concurrency, fencing, budgeting or crash recovery. The test dynamically imports scripts/coverage_feeder.py, which is outside the declared donor pathspec and was not reviewed as part of this file.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has the identical 135-line test file with the same blob/hash. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING. No Archaeology integration is warranted.

Verified donor source-read coverage is now 15/62 files and 4,034/33,497 additions. No test, feeder or source was executed or sent to GLM. The next stable-path file is research/free-inference-fabric/tests/test_engine.py (+424 additions).

## 2026-09-29 — donor file review 16 of 62

Reviewed the complete added content of research/free-inference-fabric/tests/test_engine.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 424 additions and 0 deletions; blob cdf76e0fd61c2cacd5df82bf7ada9d7244d21bed; content SHA-256 59a7621cc2c1c587fdd0d7668195da79d6236ce67b55ae0dddb2478d13e728cd. All lines were read in ranges 1–142, 143–284 and 285–424. The tests were not run.

[provider-specific account diagnostic removed]

The tests dynamically import research/free-inference-fabric/scripts/coverage_feeder.py. That file is outside the six pathspecs in the pinned 62-file scope; its blob is aff2b6c4069ce5e9ac7676816ca0261d0adc33af. It was identified by metadata only and not read, executed or counted. This is an out-of-scope dependency if the feeder workflow is later integrated.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has a 651-line version. The complete 256-line diff was reviewed: it retains donor test bodies and adds six test functions (one parametrized over six receipt failures). No donor-only test coverage gap was found. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_CANDIDATE_RETAINS_DONOR_TESTS_WITH_ADDITIONS / OWNER_REGISTRATION_MISSING. No Archaeology integration or runtime claim is warranted.

Verified donor source-read coverage is now 16/62 files and 4,458/33,497 additions. No tests, providers, database, feeder or source were executed or sent to GLM. The next stable-path file is research/free-inference-fabric/tests/test_operational_brief_benchmark.py (+118 additions).

## 2026-09-29 — donor file review 17 of 62

Reviewed the complete added content of research/free-inference-fabric/tests/test_operational_brief_benchmark.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 118 additions and 0 deletions; blob 01a9e0cd0bd939e72f08ddf633a382538b0c0daa; content SHA-256 bf80b73851c42f2c248a1b1b1ac47c0cebfad47d5cf8e2fdbd25aa386f3ed273. All lines were read in ranges 1–59 and 60–118. The tests were not run.

The file builds a fixed operational-brief report and asserts a positive verification plus rejection of one missing store and one incorrect source anchor. It does not test runtime behavior of named entrypoints/stores/failure paths, correctness of the prose, complete failure coverage, alternate valid anchors, or current fixture/digest validity. The verifier helper has no timeout/output bound, sandbox or pinned interpreter. Labels such as 'certain' and claims that runtime unavoidably enforces an invariant are fixture text, not evidence established by these tests.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has a different 118-line test file. Its 70-line diff preserves the test structure while updating the packet digest and source anchors, including the full-cell-budget-before-lease anchor. This file does not establish that the new anchors or claims are valid. Existing engine review found budget reservation and stale-lease limits; the tests do not prove those invariants. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_CANDIDATE_RETAINS_TESTS_WITH_UPDATED_FIXTURE_REFERENCES / OWNER_REGISTRATION_MISSING. No Archaeology integration is warranted.

Verified donor source-read coverage is now 17/62 files and 4,576/33,497 additions. No tests, verifier or source were executed or sent to GLM. The next stable-path file is research/free-inference-fabric/tests/test_restricted_refactor_benchmark.py (+63 additions).

## 2026-09-29 — donor file review 18 of 62

Reviewed the complete added content of research/free-inference-fabric/tests/test_restricted_refactor_benchmark.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 63 additions and 0 deletions; blob 2b2abf93415d56b085b8597b862fc2126666553e; content SHA-256 f427bda67517719e6bb75379786a8ee4bd5ea2e891f912cf1c487d57b2da2094. All 63 lines were read. The tests were not run.

The test supplies a fixed restricted-refactor candidate that expects a verifier to reject NUL/CR and embedded newlines in line elements, plus two negative examples: an __import__('os') expression and a block that rejects only CR. Its helper runs an external verifier without a timeout, output bound, sandbox or pinned interpreter. The positive output names four valid/three invalid cases and an AST restriction, but the cases and AST enforcement are not independently proven here. These assertions do not establish a secure arbitrary-code sandbox, full grammar coverage, resource bounds or preserved behavior for every safe input.

The test's candidate proposes exactly the NUL/CR/embedded-newline verifier checks absent from the byte-identical donor/candidate source_packets.py reviewed earlier. A candidate string inside a test is not evidence that a production fix exists. The ArtVault Inference Fabric candidate contains the identical 63-line test; no implementation change is present here. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING. Treat this as an improvement benchmark, not a merged feature; no Archaeology integration is warranted.

Verified donor source-read coverage is now 18/62 files and 4,639/33,497 additions. No test, verifier or source was executed or sent to GLM. The next stable-path file is research/free-inference-fabric/tests/test_source_packet_bug_hunt_benchmark.py (+75 additions).

## 2026-09-29 — donor file review 19 of 62

Reviewed the complete added content of research/free-inference-fabric/tests/test_source_packet_bug_hunt_benchmark.py from base f4d8e694289d035991c6d3c0b33b35c15a05c53c to donor d29d209e9094302937c60d28aeab7a54f78ede27. The file has 75 additions and 0 deletions; blob 04b3af8ab5efa42fb2ab0e68e362c194f6f40548; content SHA-256 07b6c899e52aa756d7e5cd964a7c171395876634ab5c49452fe06fdfa2295eaa. All 75 lines were read. The tests and reproducers were not run.

The fixed report describes two source-level builder/verifier asymmetries in source_packets.py: embedded LF can be represented as one row containing a newline while verification counts array rows; CR is rejected by the builder but not independently by the verifier. These align with the earlier static source review, but this test file does not call the actual builder/verifier to prove exploitability. It asserts verifier output for a hash-bound report, a duplicate defect-kind mutation and removal of the CR trigger. No production fix is present merely because a benchmark describes one.

The helper runs an external verifier without timeout/output limits, sandbox or interpreter pin; the verifier implementation was not read here. The assertions do not independently validate report hashes, reproduction bytes, source anchors, defect truth, NUL behavior, remediation, arbitrary defect discovery or completeness. The fixed report's 'observed' and 'certain' labels are fixture text, not results of this review.

The ArtVault Inference Fabric candidate at /srv/artvault/projects/inference-fabric/workspace has the identical 75-line test file with the same blob/hash. The machine-authority register still lacks an Inference Fabric owner entry. Disposition: REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING. This is a source-level validation issue in a separate product, not an Archaeology merge; no code change or runtime validation is claimed.

Verified donor source-read coverage is now 19/62 files and 4,714/33,497 additions. No tests, verifier or source were executed or sent to GLM. The next stable-path file is research/free-inference-fabric/tests/test_source_packet_generation_benchmark.py (+131 additions).

## 2026-09-29 — donor file review 20 of 62

Reviewed the complete added content of `research/free-inference-fabric/tests/test_source_packet_generation_benchmark.py` from base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` to donor `d29d209e9094302937c60d28aeab7a54f78ede27`. The file has 131 additions and 0 deletions; blob `08ab809fbc8f1a73d37d735bb449c7b21b163010`; content SHA-256 `b81669491d4d3fec340f4029e4454bc342435c6dbe6496136758d97604b70046`. All 131 lines were read in ranges 1–66 and 67–131. No test, builder, verifier or source was executed.

The test describes nine fixed source-packet builder cases: valid one-file and reverse-requested two-file inputs; empty-project, traversal, symlink, per-file size, CR, private-key marker and duplicate-path rejection. It also specifies expected verifier output for the nine reference cases and seven mutants, then two intended mutation-sensitivity failures. These are assertions in a benchmark test; the verifier and mutant implementations were not inspected or run. In particular the reverse-order case asserts file count and total bytes, not all output ordering/hash/line metadata. The test does not cover aggregate-size boundary, UTF-8 edge cases, ancestor/root symlinks, race resistance, all secret formats, forged packets or JSON transport bounds. It does not cover the externally constructed packet CR verifier gap previously identified.

The current ArtVault Inference Fabric candidate at `/srv/artvault/projects/inference-fabric/workspace` has an identical 131-line file with the same blob/hash and no diff. The candidate owner remains absent from the machine-authority register. Disposition: `REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING`; no Archaeology integration is warranted.

## 2026-09-29 — donor file review 21 of 62

Reviewed the complete added content of `research/free-inference-fabric/tests/test_source_packets.py` from base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` to donor `d29d209e9094302937c60d28aeab7a54f78ede27`. The file has 263 additions and 0 deletions; blob `19bf4db6ea454f0595dbc48a1a67c7d918f2fd5b`; content SHA-256 `04640aa1dbb353dae04df5450f0abae9e2c3e71fc6266b642f2885392d15682d`. All 263 lines were read in ranges 1–132 and 133–263. No tests, CLI, verifier, provider or source were executed.

The tests specify direct library/CLI assertions for deterministic ordering, exact source-line preservation, packet hash round-trip and tamper rejection; traversal, symlink and secret-marker rejection; selected malformed/cap inputs; sequential CLI idempotency and refusing overwrite; queue identity/project binding; verifier-byte drift rejection before lease; and two budget-admission cases. The verifier-change case expects a queued job to remain unleased. These are test specifications, not passing runs. They do not prove simultaneous budget reservation, stale-lease fencing, crash recovery, filesystem race resistance, successful provider application, full evaluator binding (the evaluator stays `report` in these calls), exhaustive malformed-input behavior or arbitrary-code isolation. Newline/CR/NUL verifier cases and other previously identified verifier gaps are not exercised.

The current ArtVault Inference Fabric candidate at `/srv/artvault/projects/inference-fabric/workspace` has an identical 263-line file with the same blob/hash and no diff. The candidate owner remains absent from the machine-authority register. Disposition: `REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING`; no Archaeology integration is warranted.

## 2026-09-29 — ArtVault Git authentication recheck

Control Tower's live recheck found both configured ArtVault SSH read routes working. The Archaeology `origin` route resolves the published `codex/artvault-portable-giga-archaeology` ref to `0acec0dc5886592175557f1bc9e0ac7e4329d42d`, matching the ArtVault canonical checkout. The donor `Pepstee/giga-user` route can read donor HEAD `f4d8e694289d035991c6d3c0b33b35c15a05c53c`; its dedicated key is read-only. No credentials were rotated, exposed or copied. No donor history was fetched and no ref was changed.

[provider-specific account diagnostic removed]

Verified donor source-read coverage is now 21/62 files and 5,108/33,497 additions. No tests, verifiers or donor sources were executed or sent to GLM. The next stable manifest path is `research/free-inference-fabric/tests/test_store_and_catalogue.py` (+1,006 additions).

## 2026-09-29 — donor file review 22 of 62

Reviewed the complete 1,006-line donor addition `research/free-inference-fabric/tests/test_store_and_catalogue.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Blob `5aab9d41aadbe3ce29f88b29a7a1bea7e6a5acdd`; SHA-256 `1a5e3f5b934d2e39edce5dac4b1084084d0a67d3b9f3291009b73fe18c1176bc`. All lines were read in five complete ranges. No tests, provider/verifier/plugin code, databases, evidence artifacts or credentials were accessed or executed.

The 31 donor test functions cover harvest selection and budget waits; mocked paid escalation evidence binding; study/profile plans; sequential store enqueue/lease/finish behavior; evaluator input checks; benchmark fixture digests; mocked provider output/telemetry; historical evidence declarations; and fixed benchmark verifier expectations. These are test specifications, not passing runs. Several test names overstate their call-order evidence: execute=False cases have no discovery spy. Tests do not establish actual provider execution, global atomic budget reservations, stale-worker fencing, arbitrary-command isolation, full privacy, concurrent claims, crash-safe telemetry or general verifier correctness. Historical artifact tests are static declarations, not a fresh live canary or comprehensive secret scan.

The ArtVault Inference Fabric candidate at `/srv/artvault/projects/inference-fabric/workspace` is 1,607 lines with a 672-line diff; its 46 test functions retain donor coverage and add subscription telemetry/provider accounting, timeout and redaction cases, executable budget-plugin tests, accounting for legacy/unknown rows, provider-table migrations, compatibility cases and expired-lease recovery. Candidate blob `7ed2fa0e55460f73ecc39d92e0f9128494803f2f`; SHA-256 `724af4bae3470e828c9d038918b2125f0cd11f5aa713e825ff0ee9a6278978f0`. Those additions remain unrun and do not prove live provider, cross-process or crash behavior. The candidate owner is still absent from the machine-authority register. Disposition: `REVIEWED_CANDIDATE_RETAINS_DONOR_TESTS_WITH_ADDITIONS_AND_HISTORICAL_BINDING_UPDATE / OWNER_REGISTRATION_MISSING`; no Archaeology integration is warranted.

Verified donor source-read coverage is now 22/62 files and 6,114/33,497 additions. No tests, verifier or source code was executed or sent to GLM. The next stable manifest path is `research/free-inference-fabric/tests/test_structural_debt_benchmark.py` (+83 additions).

## 2026-09-29 — donor file review 23 of 62

Reviewed all 83 additions to `research/free-inference-fabric/tests/test_structural_debt_benchmark.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Blob `6d6888e5c06c97ac2eabf760dea9eec1d596d6f9`; SHA-256 `27dbdf5a727af608cc47ff67db95b00b0903a004ec88a61033cdcc531cb73f3b`. No test, verifier or source was executed.

Two tests specify a fixed five-metric structural-debt report (CLI line count, parser definition span, shared-construction call count, store class span and adapter class span), a complete-report pass, rejection after removing one metric and rejection after changing a metric value. The verifier is responsible for extracting/comparing AST metrics and was not inspected or run. These tests do not establish that the measured structure is harmful, that the generic remediation helps, or that the hardcoded metrics remain current. The candidate source has grown beyond several frozen line counts; the report is packet-bound historical evidence, not a current architecture audit. Coverage omits many malformed-report/AST edge cases. The helper has no timeout, output bound, sandbox or interpreter pin. Its helper reuses dict objects from EXPECTED, so a mutation can persist across reordered/repeated calls.

The live ArtVault Inference Fabric candidate has the identical 83-line file and blob/hash with no diff. The candidate owner remains absent from the machine-authority register. Disposition: `REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING`; no Archaeology integration is warranted.

Verified donor source-read coverage is now 23/62 files and 6,197/33,497 additions. No tests, verifier or source were executed or sent to GLM. The next stable manifest path is `research/free-inference-fabric/tests/test_test_topology_benchmark.py` (+103 additions).

## 2026-09-29 — donor file review 24 of 62

Reviewed all 103 additions to `research/free-inference-fabric/tests/test_test_topology_benchmark.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Blob `f0713e4e683469fe0a45e5faaacb64ca07060536`; SHA-256 `e55a07026c78498eaa7b786d22ee689bf7543a3eba4ad26df949b69de0b15d04`. All lines were read in ranges 1–52 and 53–103. No tests, source, verifier or packet fixture were executed or opened.

The test describes a structural import map over reconstructed source: count function names beginning `test_`, use the first test line as a module anchor, and add deduplicated `tests` edges for selected `ImportFrom` modules. It excludes two packet paths with fixed reasons and asserts a frozen 8-module/58-test/13-edge/2-exclusion summary plus rejection after mutating one count or exclusion reason. This is an AST import map, not proof of pytest collection or that a test exercises its imported module. It omits plain/dynamic imports, collection semantics, parametrization, skips, coverage and effectiveness. The candidate trusts the supplied packet digest; the helper passes the full inherited environment and has no timeout, output bound, sandbox or interpreter pin. Expected counts are frozen, not a current whole-repository inventory. No verifier implementation or test result was independently checked.

The live ArtVault Inference Fabric candidate has the identical 103-line file and blob/hash, no diff. The candidate owner remains absent from the machine-authority register. Disposition: `REVIEWED_IDENTICAL_CANDIDATE / OWNER_REGISTRATION_MISSING`; no Archaeology integration is warranted. This completes review of the 23-file Inference Fabric src/tests slice plus the previously reviewed Archaeologist CLI file; it does not complete the donor manifest.

Verified donor source-read coverage is now 24/62 files and 6,300/33,497 additions. No tests, verifier or source were executed or sent to GLM. The intervening binary `twin_core/_authority_vendor.zip` is excluded from the pinned text-file manifest and was not opened or extracted. The next in-scope manifest path is `twin_core/adapter_evidence.py` (+41 additions).
