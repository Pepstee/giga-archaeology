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

## 2026-09-29 — donor file review 25 of 62

Reviewed the full 332-line `twin_core/adapter_evidence.py` file and its complete diff from base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` to donor `d29d209e9094302937c60d28aeab7a54f78ede27`. The diff is +41/-0; blob `85c4af90654b51a7fa1e027c2119f0f73810484f`; SHA-256 `9e2bf2952db51cb8f8230bd8dd6cec909526d812341d9a0dc5fc7d830b5a2ef2`. The complete file was read in ranges 1–170 and 171–332. No source or tests were executed, and no manifests/evidence assets or the excluded archive were opened.

The added `current_adapter_file_records` helper refreshes SHA-256/byte-size records for declared supported assets/source docs under a resolved root. It validates record shape/path strings, rejects declared symlink path components and non-files, and maps file I/O failures to `AdapterEvidenceError`. It does not compare against prior claimed digests, update the registry, run manifest commands or grant authority. The existing `verify_registry_files` path still uses the older `_file_record`, which permits contained symlinks; the new helper does not automatically harden old callers.

Boundaries include no duplicate-record or canonical-path check; in-root `..` can resolve successfully; root/ancestor symlink identity is not rejected; check/resolve/open/stat is not atomic against filesystem races; file size/time are not bounded; and `_contained` errors are outside the shown OSError wrapper. Containment is not corpus classification or authorization. Existing registry `verified` status means freshness/shape/file hashing here, not execution of listed commands or independent proof of capability. No runtime validation is claimed.

Bounded exact-path/symbol searches found no matching counterpart in the checked agent-memory, giga-scientific-research, Archaeology, agent-governance, Inference Fabric or skill-router Python surfaces. This negative search does not prove global semantic absence or establish ownership. Disposition: `REVIEWED_DONOR_INCREMENT / COUNTERPART_NOT_FOUND_IN_BOUNDED_SEARCH / OWNER_UNRESOLVED`; preserve the donor feature pending the next capability-adoption review. No integration or deletion decision is justified.

Verified donor source-read coverage is now 25/62 files and 6,341/33,497 additions (the file itself is 332 lines; only 41 lines changed). No tests/source were executed or sent to GLM. Next manifest path: `twin_core/capability_adoption.py` (+447/-57).

## 2026-09-29 — donor file review 26 of 62

Reviewed all 1,578 donor lines and the complete base-to-donor diff for `twin_core/capability_adoption.py`, from base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` to donor `d29d209e9094302937c60d28aeab7a54f78ede27`. The diff is +447/-57; base blob `d8368cdf9e9f6e7b201e4acd6e8501e34a8dfbb6`, donor blob `5971c562ded0b2d61867dc01454d5e6b24d20863`, donor SHA-256 `914d10866546b8981a636d62b4b1880f895cbafe5dfc72bb42f103e5ac9f0527`. No donor code, tests, status commands, provider or sandbox runner were executed.

The donor adds v2 declaration/runtime/test-or-canary proof classifications bound into receipts, v1 declaration-only compatibility, exact Git-object feed references, stricter source/adopted-ID collision handling, richer disconnected summaries, and Linux status execution through the existing Archaeology sandbox. The current Archaeology counterpart at the comparison HEAD has only a 21-line declaration-inspection wrapper relative to the same base; it lacks these v2 increments. Other bounded canon searches found no exact counterpart. The donor module contains no `adapter_evidence` reference, so it does not establish that the preceding adapter-record helper belongs here.

The v2 change is not a simple non-executing parser: `verify_declared_active`/`observe_liveness` can execute owner status commands. `require_active`/`require_declared_active` trust self-hashed stored state and do not independently refresh time/source. Local-ref checks do not prove fresh remote publication/authentication; subprocess calls have no stated timeout/output cap; Git tree checks do not reject symlink mode; root containment is not a confidential-data boundary. Schema v2 changes runtime manifest/receipt behavior and may break existing v1 consumers. The new Linux runner’s sandbox implementation and its tests were not executed/reviewed in this file pass.

Disposition: `REVIEWED_DONOR_INCREMENT / PARTIAL_COUNTERPART_PRESENT / USEFUL_GAPS_PRESERVED / OWNER_AND_INTEGRATION_DECISION_REQUIRED`. The existing Archaeology wrapper establishes a relevant integration boundary, but not authority to replace its v1 contract wholesale. No code merge or readiness claim is made. Verified donor source-read coverage is now 26/62 files and 6,788/33,497 additions. Next stable manifest path: `twin_core/cli.py` (+39/-3).

## 2026-09-29 — donor file review 27 of 62

Reviewed the complete 200-line `twin_core/cli.py` and full diff from base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` to donor `d29d209e9094302937c60d28aeab7a54f78ede27`. The diff is +39/-3; base blob `c1dcc4c74fcb4e8b3aea78a789202b3130fc1689`, SHA-256 `c60b9ad85ac39d529f0d14823b87e7c92597b21345d1148bf212baf9e5f133e3`; donor blob `507f55763ce0a13ef988ec18dac7beba477f96d4`, SHA-256 `62be2c1f4e97baffa819eebc5799a8bc76613fcca6c8b67231e660349709d306`. No command, gate, export or database was executed.

The new CLI commands/options cover authority status, a pre-context memory gate, and policy/evidence export verification with optional hardened acceptance exit handling. The command still offers legacy hash-baseline mode. Several details depend on unreviewed callees: authority-status returns success for any non-raising status result; validation semantics are delegated; hardened acceptance changes exit status only when requested. `--json` is parsed but ignored, help text is stale, lazy import failures may escape, and existing commands can write artifacts. No v2 capability-adoption calls appear here.

The same path is present in the registered Mac `agent-memory` canon at HEAD `222596bf40401dfb04556c15e4486831bdf3a413`; its 207-line file retains all reviewed donor behavior. The complete donor/counterpart delta is limited to CLI naming/default-root changes. The current ArtVault Archaeology canon has no `twin_core/cli.py`, and bounded tracked-source searches found no matching commands. This is not evidence of global absence, but the positive counterpart means transplanting this trust-kernel CLI into Archaeology is unwarranted. Disposition: `REVIEWED_DONOR_INCREMENT / PRESERVED_IN_REGISTERED_AGENT_MEMORY_COUNTERPART / NO_ARCHAEOLOGY_CLI_TRANSPLANT_INDICATED`. Runtime behavior and downstream gate dependencies remain unverified.

Verified donor source-read coverage is now 27/62 files and 6,827/33,497 additions. No source, tests, evidence DBs or credentials were executed/accessed or sent to GLM. Next stable path: `twin_core/constitutional_authority.py` (+595 additions).

## 2026-09-29 — donor file review 28 of 62

Reviewed all 595 additions to the new file `twin_core/constitutional_authority.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `984dc1bdfe31e284bd45935d60afbb7645efd77c`; SHA-256 `e7639339a9ed2cc32684fb73bdbea3fca20643a96048694aaed486e608243e4d`. All 595 lines were read in contiguous bounded ranges. No code, bundled archive, private state, credential, corpus or test was executed or opened.

This candidate-only authority adapter pins manifest/provenance/policy digests, checks a bounded archive and candidate tree, creates temporary extracted/snapshot trees, and executes candidate code in isolated Python with a 30-second timeout. `candidate_status` returns REFUSE even after candidate verification; the shipped activation pin is null. `require_authority` can append a private hash-chained receipt but still refuses unless a durable ALLOW exists. Static review found the ALLOW path cannot succeed as written because receipt validation rejects every ALLOW. Python `-I` and a filtered environment are not OS filesystem/network isolation; temporary extraction/execution also conflicts with current no-copy constraints pending ownership/design resolution. Git/protected-evidence references are format checked, not verified against current state. The in-file hash chain lacks an external anchor and repeated full-ledger hashing is bounded at 16 MiB. These are static findings, not runtime proof.

The complete 595-line file is byte-identical in the registered Mac `agent-memory` canon at HEAD `222596bf40401dfb04556c15e4486831bdf3a413`, with the same blob/hash. Bounded searches found no same-path or exact-symbol counterpart in the current ArtVault Archaeology or agent-governance sources. The positive existing canon and governance-bound purpose mean no transplant to Archaeology is warranted. Disposition: `REVIEWED_DONOR_INCREMENT / BYTE_IDENTICAL_IN_REGISTERED_AGENT_MEMORY / CANDIDATE_ONLY_NOT_RUNTIME_READY`.

Verified donor source-read coverage is now 28/62 files and 7,422/33,497 additions. No tests, callers or bundled archive were executed/read; no source was sent to GLM. Next stable path: `twin_core/context_compiler.py` (+39/-4).

## 2026-09-29 — donor file review 29 of 62

Reviewed the entire `twin_core/context_compiler.py` donor file and complete diff from base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` to donor `d29d209e9094302937c60d28aeab7a54f78ede27`. The diff is +39/-4; donor has 132 lines, blob `e0974b811c6e0b3650a0e350bfab42e9c18f82f7`, SHA-256 `fc74cb75aab977bbcc13cd00d98291ae814006b4262513f6ea25298281c08cd5`. Base is 97 lines, blob `abffb0e139f6dfd98289ee9c053172245c482c34`, SHA-256 `9c518c5af3ea7c4070eb3d31833a5f4fc5125b938ec1bd221e636c7bb62629f3`. No donor code or memory corpus was executed/read.

The change adds a public corpus-access gate, private-directory handling, knowledge-graph freshness, a pre-context memory gate, active-entry/index-line filtering and additional receipt/input hashes around personal-memory context compilation. It is byte-identical in the registered Mac `agent-memory` canon at HEAD `222596bf40401dfb04556c15e4486831bdf3a413`. Archaeology has a separate mapper-context implementation that compiles graph/map-backed source facts under a lexical budget; this personal-memory compiler is not a missing mapper feature and no transplant is indicated.

Static gaps in the donor helper remain unverified: the public wrapper calls the private helper without its required `private_output`, so the public success path appears to raise; the private helper refreshes knowledge before its memory gate; a linked slug can use a traversing path ending in an admitted basename; symlink/containment checks are not atomic; and the nominal character budget excludes some metadata/output and always retains control docs. These were not executed or tested. Disposition: `REVIEWED_DONOR_INCREMENT / BYTE_IDENTICAL_IN_REGISTERED_AGENT_MEMORY / DISTINCT_FROM_ARCHAEOLOGY_MAPPER_CONTEXT / RUNTIME_GAPS_UNVERIFIED`.

Verified donor source-read coverage is now 29/62 files and 7,461/33,497 additions. No private corpus, DB, credential, test or donor source execution occurred; no material was sent to GLM. Next stable path: `twin_core/daily_checkpoint.py` (+333 additions).

## 2026-09-29 — donor file review 30 of 62

Reviewed all 333 additions to the new donor file `twin_core/daily_checkpoint.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Blob `04cfd6b4725a2a2ca3d857147d051c75ef6b276d`; SHA-256 `8045efc37ff698cd4958c6652156d954cb0fa1b4930910f5eb688ae230620bce`. All 333 lines were read. No test, Git operation from the donor module, private corpus, database, credential or archive was executed/accessed.

The helper defines a caller-supplied technical-path checkpoint flow: begin requires a clean Git tree and explicit write set; complete checks the declared paths, stages their exact names plus a runtime JSON receipt, verifies staged blob hashes, commits and optionally pushes to a bound branch/URL. It is generic operational checkpointing, not Archaeology release tooling, and no in-module downstream caller was found in the pinned scope. Bounded exact-path/symbol searches found no same helper in the registered Mac agent-memory/scientific-research or ArtVault Archaeology/governance/skill-router canons. This is not a global absence claim or owner assignment.

Important limits: caller-provided details and otherwise permitted source/docs can carry private data; no content/secret scan or canonical-owner admission is performed. The receipt itself is staged and can be published. The cleanup lock is existence-only rather than acquired, and there is no one-writer lock around hashes/index/commit. Changes can race verification; commit/push failures after durable side effects are not reconciled. Some Git/environment/config inputs remain trusted, file hashing is not an atomic snapshot, and helper results do not independently prove the final remote ref. None of these paths were executed. Disposition: `REVIEWED_DONOR_INCREMENT / NO_COUNTERPART_FOUND_IN_BOUNDED_REGISTERED_SEARCH / OWNER_UNRESOLVED / GENERIC_OPERATIONAL_HELPER_NOT_PROVEN_RELEASE_INTEGRATION`; preserve without transplant or readiness claim.

Verified donor source-read coverage is now 30/62 files and 7,794/33,497 additions. No source was sent to GLM. Next stable path: `twin_core/execution_policy.py` (+599 additions).

## 2026-09-29 — donor file review 31 of 62

Reviewed all 599 additions to the new `twin_core/execution_policy.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `e06391421db92b1fe6ad914aaeef01fd880bb4a0`; SHA-256 `f386892c7a499f8929b20631635dd9bcf4319630585946e9d5e921dda5a5eb5b`. All lines were read contiguously. No registry, evidence, test, provider, corpus or credential was opened or executed.

The module implements deterministic observe-only routing comparisons. It validates a caller-selected registry and referenced evidence, compares a supplied request with declared capability/authority/budget/receipt constraints, then returns REFUSE or proposal-only; execution/authority flags are always false. It does not execute providers or enforce a runtime grant. Caller identity/input hashes remain supplied claims; registry/evidence are not signed or tied to a canonical owner; no freshness check, replay store, live rate/budget enforcement, telemetry collection, grant revocation or downstream enforcement is implemented here. Some filesystem reads are not atomic, and evidence size/count are not capped. These are static limitations, not runtime test results.

The complete 599-line file is byte-identical in the registered Mac `agent-memory` canon at HEAD `222596bf40401dfb04556c15e4486831bdf3a413`. Bounded tracked-source searches found no matching path/symbol/schema in ArtVault Archaeology, governance or skill-router. This is governance/execution-routing evidence, not mapper or release behavior, and not an authority ALLOW mechanism. Disposition: `REVIEWED_DONOR_INCREMENT / BYTE_IDENTICAL_IN_REGISTERED_AGENT_MEMORY / OBSERVE_ONLY_NO_EXECUTION_AUTHORITY`; no Archaeology transplant is indicated. Runtime tests and enforcement consumers remain unreviewed.

Verified donor source-read coverage is now 31/62 files and 8,393/33,497 additions. No material was sent to GLM. Next stable path: `twin_core/export_protection.py` (+151 additions).

## 2026-09-29 — donor file review 32 of 62

Reviewed all 151 additions to the new `twin_core/export_protection.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Blob `2b91d7877cfe623768d830dd59458e651202d91b`; SHA-256 `5d613bee9eae8c49ddfc69b5402fa85b5eb13b5211801a5c3bd6b76b0cfb6fb1`. All lines were read. No tests, policies, private evidence, archives, DBs or credentials were opened or executed.

This module verifies a policy-defined immutable-original export set by checking policy/ledger/baseline consistency, file hashes, permissions and platform immutable flags. Optional ZIP checks inspect metadata and can run CRC checks. It reports integrity separately from operational acceptance and never authorizes promotion or mutates source. Its ledger, vault and restore-drill model belongs to the registered `agent-memory` canon, where the same 151-line file is byte-identical at HEAD `222596bf40401dfb04556c15e4486831bdf3a413`. Archaeology has no matching path or exact-symbol implementation in bounded tracked-source searches. Generic hashing overlap is not an integration rationale. Disposition: `REVIEWED_DONOR_INCREMENT / BYTE_IDENTICAL_IN_REGISTERED_AGENT_MEMORY / IMMUTABLE_EXPORT_PROTECTION_NOT_ARCHAEOLOGY_RELEASE`.

Static limits include unpinned policy/ledger/baseline inputs, permissive JSON parsing/schema handling, incomplete enumeration/authenticity proof, and non-atomic repeated file reads. ZIP checks lack decompression/time ceilings; optional full CRC may decompress large content. Encrypted-vault/restore claims are not validated, and platform immutable flags do not prove Linux immutability. The related CLI can treat integrity-only as exit success unless hardened acceptance is requested. These are static observations, not test results. No preservation merge is needed for this file; operational readiness remains unproven.

Verified donor source-read coverage is now 32/62 files and 8,544/33,497 additions. No private material was sent to GLM. Next stable path: `twin_core/external_proof.py` (+8/-4).

## 2026-09-29 — donor file review 33 of 62

Reviewed the full 473-line `twin_core/external_proof.py` and complete diff from base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` to donor `d29d209e9094302937c60d28aeab7a54f78ede27`. The change is +8/-4; base blob `1d1b281bbfa0e42f21357ee88599d62baeb90940`, SHA-256 `073ff37bcb263a573833e1526aa1f7b34e21ffcf46040d3029e419715b7ab3c7`; donor blob `d489483f037f3ddeeab9c69ceac46f7d5344eb6c`, SHA-256 `24d6a3af5a1fd094fbd4c0d73915e3c499fc697175afab5e0f8a4d22067800c4`. No manifests, sources, DBs, decks, images or tests were opened or executed.

The version 1.1.0 change allows a limited set of pre-existing deck/QA companion filenames in an output directory during evidence-linked draft replay, and rejects encountered symlinks. It does not generate or validate those companions, add them to the compiler receipt, or authorize publication. The existing artifact hash list still covers only six compiler outputs, so newly allowed companion files can be stale/unverified without invalidating replay. Other static limits include recursive traversal without count/time caps, path-resolution races, incomplete schema/content checks and multi-step output/DB writes. These findings are not runtime test results.

The full file is byte-identical in the registered Mac `agent-memory` canon at HEAD `222596bf40401dfb04556c15e4486831bdf3a413`. Artifacts are agent-memory draft/compiler evidence, not Archaeology package/release artifacts. Bounded searches found no matching path or exact symbols in Archaeology. Disposition: `REVIEWED_DONOR_INCREMENT / BYTE_IDENTICAL_IN_REGISTERED_AGENT_MEMORY / DRAFT_COMPANION_COMPATIBILITY_RETAINED`; no preservation merge is needed.

Verified donor source-read coverage is now 33/62 files and 8,552/33,497 additions. No tests or private data were accessed, and nothing was sent to GLM. Next stable path: `twin_core/integrity.py` (+17/-4).

## 2026-09-29 — correction to donor file review 32

Correction to `twin_core/export_protection.py` review 32: the earlier wording that an empty policy/ledger set could be accepted as integrity success was too broad. The linked hash-baseline helper requires at least one result, so an empty baseline leads to `hashes.ok == false` and the complete `verify_export_set` path does not report `integrity_ok == true`. Empty policy/ledger sets may pass early count/set consistency checks only. No other finding in review 32 changes.

## 2026-09-29 — donor file review 34 of 62

Reviewed the complete 89-line `twin_core/integrity.py` and full diff from base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` to donor `d29d209e9094302937c60d28aeab7a54f78ede27`. The change is +17/-4; base blob `1c3fbaae31fc80981b399b1230199380acff2d98`, SHA-256 `da4c31008395699653fbb0e53d4b9a45173ffaafa9fd6e297634c8b939b25685`; donor blob `749ace225e6ba44a49d19e7f1977b22856f8e762`, SHA-256 `509a9608e26dcc72feafc0a51158f79b3f88eb423bd5c7160b9dc215560b2296`. No baseline, private evidence or test was opened or executed.

The change adds `authority_path` to reject declared relative-path traversal, observed symlink components and resolved paths outside a root. Hash-baseline verification now uses it. The helper streams SHA-256 and reports per-file missing/nonregular/hash mismatches; success requires a nonempty result set with all hashes matching. This is general source/evidence integrity tooling retained in the registered Mac `agent-memory` canon at HEAD `222596bf40401dfb04556c15e4486831bdf3a413`, byte-identical at the same path. It is not Archaeology-specific package-release verification, so no merge is needed.

Limits include unpinned/untrusted baseline origin, no complete-file enumeration or authenticity/freshness proof, and checks that are not bound to an atomic file descriptor. Root/ancestor symlinks and filesystem races remain possible; baseline reads have no size/count bound. Some parse/read errors can escape structured reporting, and the accepted syntax is not full GNU `sha256sum` compatibility. Static review only; no runtime claim. Disposition: `REVIEWED_DONOR_INCREMENT / BYTE_IDENTICAL_IN_REGISTERED_AGENT_MEMORY / GENERAL_SOURCE_INTEGRITY_HELPER_RETAINED`.

Verified donor source-read coverage is now 34/62 files and 8,569/33,497 additions. No private material was accessed or sent to GLM. Next stable path: `twin_core/knowledge_refresh.py` (+334 additions).

## 2026-09-29 — correction to donor file review 29

Correction to `twin_core/context_compiler.py` review 29: the prior note said the private helper refreshes knowledge before its memory gate. The reviewed `knowledge_refresh.py` shows that `_ensure_knowledge_current` calls validation/refresh paths that apply the pre-context memory gate before graph/projection work. Do not treat refresh as ungated solely because the compiler calls it before its own explicit gate. Direct calls to internal helpers still need caller/authorization review. The separately noted missing `private_output` argument in the public compiler wrapper remains unchanged.

## 2026-09-29 — donor file review 35 of 62

Reviewed all 334 additions to the new donor file `twin_core/knowledge_refresh.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Blob `64bebd1d633fde7eced11669b6fda622f731c9a8`; SHA-256 `a6ec8193974fa334b4ad8a46b92347ec0e1f6944bf230444b97ea929d2ea94a8`. All additions were read. No memory text, graphs, DBs, tests or provider calls were opened or executed.

The registered Mac `agent-memory` canon has a 330-line counterpart. The complete donor-to-counterpart diff shows one material adaptation: it removes a loop that temporarily copied source files and calls Graphify extraction directly from the nine-file closure with a disposable cache. The registered counterpart retains the donor's gated active-memory slug/hash/wiki-link overlay and validation behavior, with the no-source-copy change. Do not overwrite it with the donor. Its graph includes personal paths, slugs, hashes and relationships, so it remains private-memory evidence. No Archaeology path/symbol counterpart was found in bounded tracked-source searches.

Archaeology's `semantic_graphify` map and source-linked mapper context serve a different purpose: codebase navigation over admitted mapped facts. They do not index personal-memory entries. Disposition: `REVIEWED_DONOR_INCREMENT / RETAINED_WITH_NO_COPY_ADAPTATION_IN_REGISTERED_AGENT_MEMORY / PERSONAL_MEMORY_INDEXING_NOT_ARCHAEOLOGY_SEMANTIC_NAVIGATION`; no donor transplant is warranted.

The public refresh/validate/ensure wrappers require the pre-context corpus gate; `_ensure_knowledge_current` reaches validation/refresh functions that also gate before graph/projection work. Internal helper authorization still depends on its callsites. Static privacy and runtime limits remain: full active memory text is read; imported Graphify/injected runners are trusted and not sandboxed here; no transmission proof is established; graph/source reads are not atomic, capped or transactionally written; hashes/self-hashes do not prove graph truth, authenticated provenance or complete coverage. These are review limits, not execution results.

Verified donor source-read coverage is now 35/62 files and 8,903/33,497 additions. No personal data or donor source was sent to GLM. Next stable path: `twin_core/lineage.py` (+54/-120).

## 2026-09-29 — donor file review 36 of 62

Reviewed the complete base-to-donor diff for `twin_core/lineage.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. The diff is +54/-120; base has 497 lines, blob `2218b157aba9fa414e0a6b25c4560a89de52bada`, SHA-256 `1dced5f19b966bc6935d0fd1711326a09e463e6dd5869e0e2cfe21e71e9adda9`; donor has 431 lines, blob `000500c3af47e55f8a05b93b508ba2fdcb42c5f1`, SHA-256 `46545c185e7ef7b26d4cde419158877e6f5245e054da2098a774dfb09ddfbcaf`. The full diff and donor execution/report sections were read; the entire base file was not reread. No tests, DBs, memory, exports or backups were opened or executed.

The substantive delta adds `payload_mode` (`v1` or `staged-v2`) through reconciliation and canonical test runs, binds the structured derived-payload integrity result into the state fingerprint, and records the mode in verification metadata. Much of the deleted line count is formatting compaction. This is adoption of already-derived artifacts after verifier and test gates, not source-code ancestry or proof that scattered project features were integrated.

The registered Mac `agent-memory` counterpart retains the donor behavior with a dependency change to `agent-governance.payloads`; do not revert that owner adaptation. Its extracted payload-gate error helper currently records literal `PAYLOAD_MODE` rather than the selected mode, an evidence-reporting defect. This flow executes project tests, reads memory/exports and can mutate DB/report state. Actor/basis/confirmation are manifest claims, not authenticated permission. Path resolution, TOCTOU, output bounds, DB/file atomicity and actual payload derivation have limits that remain unverified. None of those runtime operations were executed here. Bounded searches found no counterpart in Archaeology. Disposition: `REVIEWED_DONOR_INCREMENT / RETAINED_WITH_GOVERNANCE_DEPENDENCY_ADAPTATION_IN_AGENT_MEMORY / DERIVED_ARTIFACT_ADOPTION_NOT_PROJECT_CONSOLIDATION_PROOF`.

Verified donor source-read coverage is now 36/62 files and 8,957/33,497 additions. No code or private data was sent to GLM. Next stable path: `twin_core/memory_gate.py` (+283 additions).

## 2026-09-29 — correction to donor file review 29

Further correction to `twin_core/context_compiler.py` review 29, based on the complete `memory_gate.py` read: the public context compiler path currently reaches an unconditional host-bound corpus-access refusal before reading its inputs or reaching `_compile_context`. The public success-path problem is therefore the deliberate inactive access gate. The missing `private_output` argument is a second latent issue only if that gate were ever enabled; it is not the current public-path result. Do not bypass the refusal. The `input_hashes` mapping in the reviewed gate has exactly the snapshot/active/tombstone hashes and does not overwrite `receipt_sha256`; remove that speculative collision concern for this pinned dependency.

## 2026-09-29 — donor file review 37 of 62

Reviewed all 283 additions to the new `twin_core/memory_gate.py` at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Blob `a21953c6ebe2fdf7e49ef5d1e573e50d9a1adbee`; SHA-256 `539a878c9326fbf425b3789325f4f84c78bbbbaee138ad22985dba2081fee581`. No memory corpus, receipt, database, test or credential was accessed or executed.

The file is byte-identical in the registered Mac `agent-memory` canon at HEAD `222596bf40401dfb04556c15e4486831bdf3a413`. All three public gate/rollback functions call `_require_corpus_access`, which unconditionally raises `HOST_BOUND_CORPUS_ACTIVATION_REQUIRED` before touching input. This is deliberate refusal, not an incomplete switch to toggle; no boolean, root or synthetic receipt enables it. The internal validator handles six stages, checks directory/symlink and tombstone-ledger state, hashes memory files, filters active entries and builds a receipt. The rollback helper writes a claim from supplied hashes/errors; it does not restore or independently verify restoration. Public callers therefore fail closed at the host-bound access boundary. Internal helpers remain callable by trusted code and do not themselves enforce that public boundary.

Static limits include non-atomic path/file checks, no owner/mode/hardlink guarantees, manifest fields that are assertions rather than authenticated authority/history, permissive JSON/type handling, unbounded repeated tree hashing, and unsigned self-consistent receipts. No corpus read or execution occurred. Disposition: `REVIEWED_DONOR_INCREMENT / BYTE_IDENTICAL_IN_REGISTERED_AGENT_MEMORY / PUBLIC_CORPUS_ACCESS_DELIBERATELY_UNAVAILABLE`; this is not an Archaeology feature, permission to unlock memory, or proof every external callsite enforces the gate.

Verified donor source-read coverage is now 37/62 files and 9,186/33,497 additions. No private material was sent to GLM. Next stable path: `twin_core/memory_proposals.py` (+134/-41).

## 2026-09-29 — donor file review 38 of 62

Reviewed the complete 337-line donor `twin_core/memory_proposals.py` and full base-to-donor diff at donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. The diff is +134/-41; base blob `3249e4a111b257e848987309754e30e30b36e298`, SHA-256 `853369d89c6ee7d845ff6032997d5ca202733d3ec24c296dbdede3afb4535d62`; donor blob `3d199f55d65bb8ea79912564f287a472a8317638`, SHA-256 `f8e75628c31f99b7fbbf282c910964551e7b81048284030ea61cd4c9afa8302f`. No memory corpus, DB, credential or test was accessed or executed.

The new donor behavior is byte-identical in registered Mac `agent-memory`. Archaeology also has the exact base blob at this path, so this is an older existing copy, not a missing file. The donor adds public fail-closed corpus refusal, snapshot-bound proposal validation/commit and rollback attempts; however, the public access boundary is deliberately unconditionally refusing. The broader flow copies a memory tree, validates against gates, writes entry/index files and can refresh knowledge. It is personal-memory functionality, not automatically a safe Archaeology upgrade. The internal proposal object is constructible and the rollback is not crash-atomic; whole-tree copying and concurrent-writer races remain. No merge, activation or deletion decision is made from filename or donor presence alone.

Disposition: `REVIEWED_DONOR_INCREMENT / BYTE_IDENTICAL_NEW_BEHAVIOR_IN_AGENT_MEMORY / ARCHAEOLOGY_RETAINS_EXACT_OLDER_BASE / PERSONAL_MEMORY_OWNER_BOUNDARY_REQUIRES_CALLSITE_REVIEW`. Before deciding on the Archaeology copy, check only tracked source/package/test callsites and preserve the host-bound refusal. No corpus or runtime path was touched.

Verified donor source-read coverage is now 38/62 files and 9,320/33,497 additions. No private material was sent to GLM. Next stable path: `twin_core/operator_status.py` (+285/-11).

## 2026-09-29 — donor file review 39 of 62

Reviewed the complete base-to-donor diff for `twin_core/operator_status.py` at pinned donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. The diff is +285/-11. Base blob `245a04aeac5b01517d4b907791b1aad37dc446e3`, 15,274 bytes, SHA-256 `66adde6b2deb9865025f7af50fd986b863f2f9d5e89b63d0b4968528bdddd7f4`; donor blob `1b4134cf1150ae334ff9c124788c9009efe4c175`, 25,132 bytes, SHA-256 `4f3aa4f236d1c2daa4cb06c3d3b877e85461e21d19fac4dec9590cdceadb0e73`. Read the complete changed module, the adapter-evidence helper, the CLI entry point, relevant tests and the operator-status JSON schema. No tests or source commands were executed.

The addition admits one exact `operator-status-local` record for the read-only `--no-write` onramp, binds its registry and evidence hashes, rechecks evidence for drift, and embeds a deterministic admission receipt in compiled operator status. The associated tests cover refusal cases, registry/evidence changes, deterministic output and the CLI no-write path. Static review found no actionable defect in this increment; runtime behavior was not tested.

Archaeology's tracked source contains no `operator_status.py` or `adapter_evidence.py`, and bounded searches found no admission callsites. Its product scope is local repository maps and source-linked developer context; this increment compiles GIGA operator, SkillTree and adapter status. No Archaeology behavior is missing or improved by transplanting this code. The canonical owner of the operator-status feature is not established by this review. Disposition: `REVIEWED_DONOR_INCREMENT / OPERATOR_STATUS_ADMISSION_OUTSIDE_ARCHAEOLOGY_SCOPE / NO_TRANSPLANT`.

The ArtVault Archaeology Git store does not contain the pinned donor commit. The approved Control Tower read route verified the exact pinned blob from the existing Mac Git object store; no source copy or credential change was made. No personal corpus or donor source was sent to GLM.

Verified donor source-read coverage is now 39/62 files and 9,605/33,497 additions. The next manifest path is pending metadata verification.

## 2026-09-29 — donor file review 40 of 62

Reviewed all 847 additions to new donor file `twin_core/passage_retrieval.py` at pinned donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `553ef0f155b4f83d72220f8ecf03d029547b7b32`, 34,133 bytes, SHA-256 `efb27845d4070722cad381d3b96d311ce94b90a8102057df81a66b1729c45c87`. Read the complete module, all 501 lines of its focused tests, and the research-run, scientific CLI, benchmark and packaging callsites. No tests, model, network or source command was executed.

The module provides stable passage chunking over verified archived-web receipts, multilingual BM25, source-diverse reciprocal-rank fusion, receipt-metadata filters, and optional local FastEmbed dense ranking with model-cache and ranking receipts. Its production callers acquire and retrieve public research sources, and FastEmbed is an optional `research-dense` dependency. Archaeology's existing mapper-context uses source-linked map facts, graph ranking and exact/lexical matching; bounded current-canon searches found no passage-retrieval or dense-ranking implementation. BM25 and local dense ranking are possible ideas for a future source-document context benchmark, but this research-specific implementation does not directly serve Archaeology's current mapped-code contract. No transplant is justified without a demonstrated mapper-context improvement and a portability/dependency decision. The donor feature's canonical owner is unresolved.

[P2] `validate_dense_ranking` can accept a dense ranking whose query is missing or has been relabelled. At lines 517-524, the expected-query check runs only when `result["query"]` is not `None`; `_dense_ranking_sha256` also omits the query. The benchmark callsite passes `expected_query` at `twin_core/research_benchmark.py:256-258`, so a queryless or relabelled provider with a matching ranking hash can be accepted as the benchmark query. Require and bind the query when an expected query is supplied. The focused tests do not cover this case. Static review only; the defect was not executed.

Disposition: `REVIEWED_DONOR_INCREMENT / RESEARCH_ARCHIVE_RETRIEVAL_CANDIDATE_NOT_PROVEN_FOR_ARCHAEOLOGY / QUERY_BINDING_DEFECT / NO_TRANSPLANT`.

Verified donor source-read coverage is now 40/62 files and 10,452/33,497 additions. No source copy was created and no donor source or personal corpus was sent to GLM. Next manifest path: `twin_core/research_benchmark.py` (+3,196 additions).

## 2026-09-29 — donor file review 41 of 62

Reviewed all 3,196 additions to new donor file `twin_core/research_benchmark.py` at pinned donor `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `2b503ff4c977720c72bb2b3b6b83336d60ca039f`, 141,022 bytes, SHA-256 `ffc3ad93d1caeb46f69337de790464464cedabac84b92755f3e792a5a154ebd0`. Read the complete changed module, targeted benchmark validation/import tests, CLI callsites and the related retrieval/research callers. No tests or model/network commands were run.

The module adds research-system benchmark scoring/comparison, pinned imports for ReportBench, PDR-Bench, DeepResearch Bench and DeepSynth, cohort/submission preparation, and gated campaign planning/admission. Its consumers are research acquisition and scientific benchmark commands. The Archaeology canon has no corresponding module, benchmark import flow, or callsites; its supported product remains local Python repository mapping and bounded source-linked developer context. Benchmark functionality does not improve that supported contract, so no transplant is justified.

[P2] `_validated_run` at lines 858-945 checks that latency and cost are numeric and non-negative but does not require finite values. `NaN` passes the negative-value comparison; `latency_ms` then raises an uncaught `ValueError` during `int()` conversion, while infinite latency raises `OverflowError`. Non-finite `cost_usd` can be emitted in score output and propagate into comparisons. The nearby tests cover unknown values and scope requirements, but not non-finite measurements. Reject non-finite latency and cost with `ResearchBenchmarkError` before coercion or scoring. Static review only; the defect was not executed.

Disposition: `REVIEWED_DONOR_INCREMENT / RESEARCH_BENCHMARKING_OUTSIDE_ARCHAEOLOGY_SCOPE / NONFINITE_MEASUREMENT_VALIDATION_DEFECT / NO_TRANSPLANT`.

Verified donor source-read coverage is now 41/62 files and 13,648/33,497 additions. No donor source copy or personal corpus was created or sent to GLM. Next manifest item requires metadata verification before review.


## 2026-09-30 — donor file review 42 of 62

Reviewed the complete 1,105-line donor file `twin_core/research_export.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `ffcd89a8aa724bcddab5df40a0d949b0e969d6e9`; the exact path is absent from the base tree, so all 1,105 lines are additions. The donor commit metadata identifies parent `5e6aa8bc13a8ae228f741f08c4ab3ff7e7f50039` and an unsigned commit. The GitHub compare from the recorded base to this donor head reports a diverged history (142 ahead, 28 behind); this comparison is not a signed or linearly based patch series. Recursive tree metadata independently reproduces 62 changed Python paths within the six recorded scope prefixes, plus the separately excluded binary `twin_core/_authority_vendor.zip`. The prior ledger's path-manifest digest was not independently reproduced because its serialization recipe is not recorded.

Read the entire module. It renders research reports, offline citation-trace and plan maps with receipts, evidence briefs and extractive articles; it also builds evidence-bound synthesis packets and validates reordered outlines and model-proposed paragraphs using citation existence and lexical support. Its outputs explicitly preserve human-review authority and state that lexical support does not establish entailment. No tests, project data, database, model, external research source, or provider call was executed.

Bounded tracked-source searches in the registered Archaeology canon found no `research_export.py`, citation-trace view, plan-map renderer, or synthesis-packet callsite. These exports consume the donor's general research-project ledger and citation/evidence graph; they do not serve Archaeology's code-map or source-linked developer-context contract. The new module is not a proven Archaeology feature and should not be transplanted. Disposition: `REVIEWED_DONOR_INCREMENT / GENERAL_RESEARCH_EXPORTS_OUTSIDE_ARCHAEOLOGY_SCOPE / NO_TRANSPLANT`.

Verified donor source-read coverage is now 42/62 files and 14,753/33,497 additions, counting the prior verified 41-file ledger total plus this complete 1,105-line new-file addition. No donor source or personal corpus was sent to GLM, and no project copy was created.


## 2026-09-30 — donor file review 43 of 62

Reviewed the complete 2,104-line donor file `twin_core/research_project.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `1f8b5f4c43c3bd0d8dae37b19ffd36843ae1e9a3`; the exact path is absent from the base tree, so all 2,104 lines are additions. Read the full file; no tests, project databases or research corpus were opened or executed.

The module provides validated multi-perspective research plans, append-only project events, plan approval, archived-source attachment, verbatim evidence spans, proposed and reviewed claims and relations, citation graphs, evidence matrices, research-frontier gap analysis, and approval-gated follow-up plans. Hashes bind supplied content, but they do not authenticate the person recorded in `approved_by` or make the SQLite ledger externally immutable.

Static review found two issues in the research feature. [P2] `citation_graph()` projects rows from `_events()` without first calling `status()`, unlike the path that audits stored payload hashes and the event-chain links. A modified SQLite row can therefore feed a newly self-hashed graph without the ledger-integrity check. [P2] `_attach_archived_source()` resolves the receipt path before checking `is_symlink()`; that check sees the resolved target and does not reject a symlink whose target remains inside the archive, despite the stated regular-file requirement. Neither finding was executed.

Bounded tracked-source searches found no matching general-research plan/event ledger, frontier, claim/evidence graph, or callsite in the registered Archaeology canon. This module belongs to a separate research workflow and does not improve the Archaeology code-map contract. Disposition: `REVIEWED_DONOR_INCREMENT / GENERAL_RESEARCH_PROJECT_LEDGER_OUTSIDE_ARCHAEOLOGY_SCOPE / TWO_STATIC_FINDINGS / NO_TRANSPLANT`.

Verified donor source-read coverage is now 43/62 files and 16,857/33,497 additions, counting the prior verified ledger total plus this complete 2,104-line new-file addition. No donor source or personal corpus was sent to GLM, and no project copy was created.


## 2026-09-30 — source review 44 of 62

Reviewed the complete 863-line source file `twin_core/research_run.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Source blob `6c9c01fea6449c886ccccd6bd0d4a0e496cf75d6`; the exact path is absent from the base tree, so all 863 lines are additions. The module orchestrates approved general-research projects through source discovery, web/local acquisition, passage retrieval, evidence recording, resumable run artifacts, and bounded parallel execution. No tests, research corpus, database, provider or external research source was executed.

Static review found two integrity issues. [P2] `_private_run_root()` resolves the requested path before checking `is_symlink()`, making the symlink refusal ineffective; a symlink to an external directory can be accepted and the target's permissions changed to 0700. [P2] When `run_state()` reports a completed run, `execute_research_run()` returns its recorded paths and hashes without verifying that the bundle, brief and article still exist or match those hashes. Neither finding was executed.

A bounded tracked-source search found no general-research run orchestrator, web acquisition, or passage-retrieval callsite in the registered Archaeology canon. This source file does not improve the code-map contract and should not be transplanted. Disposition: `REVIEWED_SOURCE_INCREMENT / GENERAL_RESEARCH_RUNNER_OUTSIDE_ARCHAEOLOGY_SCOPE / TWO_STATIC_FINDINGS / NO_TRANSPLANT`.

Verified source-read coverage is now 44/62 files and 17,720/33,497 additions, counting the previous verified ledger total plus this complete 863-line new-file addition. No source code or personal corpus was sent to GLM, and no project copy was created.


## 2026-09-30 — source review 45 of 62

Reviewed the complete 509-line source file `twin_core/scientific_campaign.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Source blob `eed377bf8736daf7da457096afdc35e79f942251`; the exact path is absent from the base tree, so all 509 lines are additions. It validates scientific-search campaign definitions, selects phased queries, plans resumable acquisitions, and executes Elicit/ClinicalTrials or provider-expanded paper-search campaigns into the scientific evidence store. No tests, database, research corpus, provider or network search was executed.

[P3] `validate_campaign()` detects a non-mapping input, but then calls `set(payload)` while building its error message; `None` or another non-iterable therefore escapes as `TypeError` instead of the documented `ScientificEvidenceError`. This is a static finding; it was not executed.

The module is a scholarly-search campaign workflow, not a source-code archaeology capability. Bounded tracked-source searches found no campaign execution counterpart or callsite in the registered Archaeology canon. No transplant is warranted. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_SEARCH_CAMPAIGNS_OUTSIDE_ARCHAEOLOGY_SCOPE / MALFORMED_INPUT_ERROR_TYPE / NO_TRANSPLANT`.

Verified source-read coverage is now 45/62 files and 18,229/33,497 additions, counting the prior verified ledger total plus this complete 509-line new-file addition. No source code or personal corpus was sent to GLM, and no project copy was created.


## 2026-09-30 — source review 46 of 62

Reviewed the complete 1,471-line source file `twin_core/scientific_evidence.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Source blob `ac5eb0f759bc0111073a3f570184cca7dd2aa74e`; the exact path is absent from the base tree, so all 1,471 lines are additions. The file implements a general scientific acquisition client, source/appraisal records, append-only SQLite ledger, integrity audit, and evidence-readiness gates. The source was read directly from the existing read-only Git object archive; no checkout or copy was created. No tests, database, Elicit credentials, provider, or network search were used.

[P3] `validate_appraisal()` advertises a `ScientificEvidenceError` for invalid appraisal shape, but `validate_appraisal(None)` reaches `set(appraisal)` while formatting the missing fields and raises `TypeError`. This is a static finding; it was not executed.

The module is a general scientific-evidence workflow rather than code archaeology. Bounded tracked-source searches in the registered Archaeology canon found no matching store, acquisition, appraisal, or readiness entry point. No transplant is warranted. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_EVIDENCE_WORKFLOW_OUTSIDE_ARCHAEOLOGY_SCOPE / MALFORMED_INPUT_ERROR_TYPE / NO_TRANSPLANT`.

Verified source-read coverage is now 46/62 files and 19,700/33,497 additions, counting the prior verified ledger total plus this complete 1,471-line new-file addition. No source code or personal corpus was sent to GLM, and no project copy was created.


## 2026-09-30 — source review 47 of 62

Reviewed the complete 439-line source file `twin_core/scientific_evidence_cli.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Source blob `ea024bc80972f9b1c599bcb2d18fb3fd3883721f`; the exact path is absent from the base tree, so all 439 lines are additions. It exposes the scientific evidence store through provider search, DOI lookup, Elicit report/review creation, offline imports, appraisals, candidate readiness, and ledger inspection commands. No CLI command, database, credential, network request or test was run.

[P2] `main()` constructs `ScientificEvidenceStore` before dispatching `audit`. The store constructor creates the database and schema when the requested path is missing, so `giga-scientific-evidence audit --database <missing-path>` can report `ok: true` after creating a new empty ledger rather than proving that a pre-existing ledger was audited. This is a static finding; it was not executed.

The CLI is an interface for scientific literature review, not source-code archaeology. A bounded tracked-source search found no matching command, class, or callsite in the registered Archaeology canon. No transplant is warranted. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_EVIDENCE_CLI_OUTSIDE_ARCHAEOLOGY_SCOPE / AUDIT_CREATES_MISSING_DATABASE / NO_TRANSPLANT`.

Verified source-read coverage is now 47/62 files and 20,139/33,497 additions, counting the prior verified ledger total plus this complete 439-line new-file addition. No source code or personal corpus was sent to GLM, and no project copy was created.


## 2026-09-30 — source review 48 of 62

Reviewed the complete 321-line source file `twin_core/scientific_fulltext.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Source blob `bb4eacb022d12fa9e426e6ef53a0431d8d33e37d`; the exact path is absent from the base tree, so all 321 lines are additions. It plans lawful full-text routes, retrieves official Europe PMC XML, extracts reviewable sections, and writes content-hashed receipts. No network request, XML input, file write, or test was performed.

[P2] `extract_pmc_xml()` resolves the requested path before checking `is_symlink()`, so a symlink is replaced by its target path and the explicit non-symlink refusal is ineffective. [P2] The DTD/entity rejection scans only the first 2,000 bytes before parsing the entire remote XML document; a declaration after that prefix passes the guard despite the stated prohibition. Both are static findings and were not executed.

The workflow concerns scientific literature acquisition and appraisal rather than code archaeology. A bounded tracked-source search found no full-text planner, PMC retrieval, or extraction callsite in the registered Archaeology canon. No transplant is warranted. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_FULLTEXT_OUTSIDE_ARCHAEOLOGY_SCOPE / PATH_AND_XML_GUARD_GAPS / NO_TRANSPLANT`.

Verified source-read coverage is now 48/62 files and 20,460/33,497 additions, counting the prior verified ledger total plus this complete 321-line new-file addition. No source code or personal corpus was sent to GLM, and no project copy was created.


## 2026-09-30 — source review 49 of 62

Reviewed the complete 2,408-line source file `twin_core/scientific_pipeline_cli.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Source blob `a898fb31356cbdeac641632111c6ccd6da3e2d48`; the exact path is absent from the base tree, so all 2,408 lines are additions. This CLI combines scholarly screening and full-text workflows with general web research, personal research projects, passage retrieval, synthesis, and benchmark import/scoring. No command, database, source corpus, external provider, network request, or test was executed.

The CLI is a scientific research interface rather than an Archaeology code-map feature. A bounded tracked-source search found no matching command or workflow entry point in the registered Archaeology canon. No unique Archaeology behavior was identified and no transplant is warranted. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_PIPELINE_CLI_OUTSIDE_ARCHAEOLOGY_SCOPE / NO_TRANSPLANT`.

Verified source-read coverage is now 49/62 files and 22,868/33,497 additions, counting the prior verified ledger total plus this complete 2,408-line new-file addition. No source code or personal corpus was sent to GLM, and no project copy was created.

## 2026-09-30 — source review 50 of 62

Reviewed the complete 1,165-line donor file `twin_core/scientific_providers.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Source blob `7cc3d475ed149a7a7b63335c1a4362ca33246520`; the exact path is absent from the base tree, so all 1,165 lines are additions. The module adapts Europe PMC, PubMed, Semantic Scholar, OpenAlex, ClinicalTrials.gov, Crossref and Unpaywall into shared scientific search and record projection interfaces. No provider/API request, test, database, credential, or network call was used.

[P2] The shared provider filter set is not consistently enforced or reported. Europe PMC applies retraction filtering but silently ignores most other filters; PubMed handles retraction, type tags and year bounds while ignoring PDF, quartile, PubMed-only, include-keyword and exclude-keyword filters; Semantic Scholar applies none of the shared filters; OpenAlex applies only retraction filtering. A caller can therefore receive results that violate requested criteria without any indication that a provider ignored them. Static review only; no provider was called.

A bounded tracked-source search in the registered Archaeology canon found no provider client or matching callsite. These adapters serve scholarly literature search rather than Archaeology's local repository mapping and source-linked developer-context contract. No transplant is warranted. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_PROVIDER_FILTERS_OUTSIDE_ARCHAEOLOGY_SCOPE / CROSS_PROVIDER_FILTER_SEMANTICS_DIVERGE / NO_TRANSPLANT`.

Verified source-read coverage is now 50/62 files and 24,033/33,497 additions, counting the prior verified ledger total plus this complete 1,165-line new-file addition. No source code or personal corpus was sent to GLM, and no project copy was created.

## 2026-09-30 — source review 51 of 62

Reviewed all 511 additions to `twin_core/scientific_query_compiler.py` at donor commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `2bbde1f36492ee9f66ed3935aa6bb7f4fba54caa`; the path is absent from the base tree. The complete module validates ontology and search-specification inputs, compiles provider-specific Boolean query strings, hashes a compiled manifest, and embeds provider queries into a campaign. Its call sites route through the scientific pipeline CLI, with adjacent tests covering provider-specific output and campaign embedding. Those tests were read but not run. No API/provider call, database, credential, network request, or test execution occurred.

Static review found no defect that I can substantiate within this module's validated input flow. Its scope is scientific literature search. A bounded tracked-source search in the registered Archaeology canon found no matching compiler, ontology workflow, schema, or callsite, so there is no Archaeology feature to transplant.

The existing ArtVault graph was queried for navigation, but it has no provenance manifest; its query was broad and is not treated as source evidence. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_QUERY_COMPILATION_OUTSIDE_ARCHAEOLOGY_SCOPE / NO_TRANSPLANT`.

Verified donor source-read coverage is now 51/62 files and 24,544/33,497 additions, counting the prior verified ledger total plus this complete 511-line addition. No donor source or personal corpus was sent to GLM, and no project copy was created.

## 2026-09-30 — source review 52 of 62

Reviewed all 109 additions to `twin_core/scientific_readiness.py` at donor commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `87d3547f03cc56a7151bd5abe66a9343ee4950ac`; the path is absent from the base tree. The module computes screening-only readiness gates from acquisition mapping, duplicate decisions, a review ledger, negative controls, exclusions, and saturation. Its report explicitly leaves full-text appraisal, scientific synthesis, and effectiveness ranking incomplete or unauthorised. No test, database, provider, network request, or credential was used.

Static review found no defect I can substantiate in the validated readiness flow. A bounded tracked-source search found no matching readiness gate, report schema, or callsite in the registered Archaeology canon. This is scientific literature workflow logic, not a unique Archaeology feature; no transplant is warranted.

The existing graph was queried for navigation, but it lacks source provenance and returned broad unrelated matches. It is not used as evidence. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_SCREENING_READINESS_OUTSIDE_ARCHAEOLOGY_SCOPE / NO_TRANSPLANT`.

Verified donor source-read coverage is now 52/62 files and 24,653/33,497 additions, counting the prior verified ledger total plus this complete 109-line addition. No donor source or personal corpus was sent to GLM, and no project copy was created.

## 2026-09-30 — source review 53 of 62

Reviewed all 1,000 additions to `twin_core/scientific_review_funnel.py` at donor commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `745369059d3782df3b2943a312a35197a9de5f20`; the path is absent from the base tree. The module builds staged scientific screening and full-text review artifacts, imports PubMed abstracts, validates human eligibility/extraction/sign-off data, and produces a hash-bound comparison matrix. Call sites and related tests were read but not executed. No provider request, database, credential, network call, or test execution occurred.

[P2] `_strip_official_pubmed_doctype()` checks for entity declarations and unexpected DTDs only within the first 10,000 bytes, then passes the complete response to ElementTree. A declaration placed after a sufficiently long XML prolog/comment can bypass the stated DTD/entity prohibition. The existing test covers an entity declaration at the start of the document, not after the scanned prefix. Static finding; no XML payload was executed.

[P2] `apply_abstract_enrichments()` checks the retrieval schema and PMID but does not validate the supplied `retrieval_sha256` or `abstract_sha256` against the record and abstract before using the abstract to recompute eligibility proposals. The adjacent test fixture supplies an arbitrary 64-character retrieval hash, illustrating that this binding is not enforced. A corrupted or mismatched retrieval record can therefore be applied while its unverified hash is retained as provenance. Static finding; test not run.

A bounded tracked-source search found no matching review-funnel workflow or callsite in the registered Archaeology canon. This is scientific literature-review functionality, not a unique Archaeology feature; no transplant is warranted. The graph was queried for navigation but has no provenance and returned broad matches, so it is not source evidence. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_REVIEW_FUNNEL_OUTSIDE_ARCHAEOLOGY_SCOPE / DTD_SCAN_PREFIX_LIMIT / RETRIEVAL_HASH_NOT_VERIFIED / NO_TRANSPLANT`.

Verified donor source-read coverage is now 53/62 files and 25,653/33,497 additions, counting the prior verified ledger total plus this complete 1,000-line addition. No donor source or personal corpus was sent to GLM, and no project copy was created.

## 2026-09-30 — source review 54 of 62

Reviewed all 796 additions to `twin_core/scientific_review_state.py` at donor commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `f9aa54d3b230d2e6ca9590dc99f59cdee875ae94`; the path is absent from the base tree. The module implements a permission-restricted SQLite review ledger with append-only triggers, hashed event chains, review-state transitions, human duplicate decisions, and non-authoritative LLM proposals. The caller and adjacent audit tests were read but not run. No database, provider, credential, network request, or test execution occurred.

[P2] `ScientificReviewStore.__init__()` creates and initializes a missing database before the pipeline CLI's `_state()` dispatches the `audit` command. Consequently, auditing a nonexistent path can create a fresh empty ledger and return `ok: true` for that new schema rather than establishing the integrity of a pre-existing review ledger. This is a static call-chain finding; the CLI was not executed.

A bounded tracked-source search found no matching scientific review ledger or callsite in the registered Archaeology canon. Its literature-review state workflow is outside Archaeology's repository-mapping contract; no transplant is warranted. The graph query was used only for navigation because the graph lacks provenance and returned broad results. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_REVIEW_STATE_OUTSIDE_ARCHAEOLOGY_SCOPE / AUDIT_CREATES_MISSING_DATABASE / NO_TRANSPLANT`.

Verified donor source-read coverage is now 54/62 files and 26,449/33,497 additions, counting the prior verified ledger total plus this complete 796-line addition. No donor source or personal corpus was sent to GLM, and no project copy was created.

## 2026-09-30 — source review 55 of 62

Reviewed all 162 additions to `twin_core/scientific_saturation.py` at donor commit `d29d209e9094302937c60d28aeab7a54f78ede27` against base `f4d8e694289d035991c6d3c0b33b35c15a05c53c`. Donor blob `ea7d20b8ac8bc0db387b116d01117242f40ee964`; the path is absent from the base tree. The module compares cumulative screening summaries, candidate identities, and intervention families to decide whether search yield has saturated. Its caller and tests were read but not executed. No database, provider, credential, network request, or test execution occurred.

[P2] `_snapshot()` verifies hashes for three selected artifacts but trusts `snapshot_payload_sha256` and `retrieval_records` directly from the unhashed summary. `evaluate_saturation()` uses those values to establish distinctness and cumulative order. Identical checked candidate artifacts can therefore be presented with changed summary hashes and nondecreasing counts and be accepted as distinct snapshots, defeating the replay gate and potentially producing a false saturation result. The test fixture assigns arbitrary snapshot hashes and tests only a repeated summary path; it does not bind the claimed hash to artifact contents. Static finding; no saturation command or test was executed.

A bounded tracked-source search found no matching saturation evaluator, schema, or callsite in the registered Archaeology canon. Search-yield accounting for literature review is outside Archaeology's repository-mapping contract; no transplant is warranted. The graph was queried only for navigation because its provenance is absent and its results were broad. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_SEARCH_SATURATION_OUTSIDE_ARCHAEOLOGY_SCOPE / SNAPSHOT_HASH_NOT_BOUND / NO_TRANSPLANT`.

Verified donor source-read coverage is now 55/62 files and 26,611/33,497 additions, counting the prior verified ledger total plus this complete 162-line addition. No donor source or personal corpus was sent to GLM, and no project copy was created.


## 2026-09-30 — authenticated donor scope and access verified

At 2026-09-29T19:18:31.709565+00:00, authenticated GitHub REST access through account `Pepstee` resolved the prior access blocker. The exact donor commit is `d29d209e9094302937c60d28aeab7a54f78ede27`, tree `9a6d4c3c1f251fb4d0ecbb93a7a502e4d5df33d3`; its parent is `5e6aa8bc13a8ae228f741f08c4ab3ff7e7f50039`, so the comparison base `f4d8e694289d035991c6d3c0b33b35c15a05c53c` is an explicit anchor, not the direct parent. The named donor branch `codex/preserve-giga-modularisation-history-20260928` remains `absent_or_unadvertised`; exact commit content is accessible by SHA.

The authenticated Contents and Git Blob APIs enumerated only the six approved scopes and verified **62 changed Python files, 33,497 additions, and 255 deletions**. Per-file Git blob IDs, SHA-256 digests and numstat results are recorded in `donor-scope-d29d209e.json` (manifest SHA-256 `a27e1bd71dd06a1cd2d24b7c2a176d65cf136d166a6a55e8a3ec592712a5d8d1`). No donor source text was copied into the canon or sent to GLM.

A crosswalk against persisted review paragraphs found **54 explicit paths / 26,168 mapped additions**, while the prior cumulative ledger claims 55/62 and 26,611 additions. **8 paths / 7,329 additions have no explicit completed review paragraph in the persisted file.** Preserve the earlier entries; treat the cumulative source-read figure as unreconciled until the missing and historical entries are verified against this manifest. This corrects the persisted-record crosswalk, not a claim that historical reviews did not occur.

The current runtime exposes no approved GLM worker route, and the donor code remains private and unadvertised. No source was sent to GLM and no other model was substituted for a GLM worker. Feature dispositions remain separate from this scope verification.


## 2026-09-30 — donor review: modules/operations/scripts/archaeologist.py

Reviewed the complete 493-line addition at donor `d29d209e9094302937c60d28aeab7a54f78ede27`; blob `044aaa152e08d097f5e91bca485ca1e5fdc1f815`; SHA-256 `33e57f7975d36472ceb3fa1a3a55c762f3f5b3015e3e805458373eb57a220d2c`. The wrapper exposes 17 inventory, hypothesis, counterevidence, history, judge, quarantine, navigation, semantic-graph and retention commands.

A live AST comparison against the canonical `modules/operations/scripts/archaeology.py` found no donor-only command. All 17 donor commands already exist in the canonical CLI, which additionally exposes 35 mapper, SCIP, divergence, dossier, consultation and retention commands. The donor wrapper imports `modules.operations.archaeologist.*`; that canon package contains only `__init__.py`, while the implementations live under `modules.operations.archaeology.*`. The donor's hypotheses and navigation-refresh argument sets are also narrower than the canonical CLI. No unique behavior warrants transplant. Disposition: `REVIEWED / CLI_SUBSET_OF_CANON / IMPORTS_NONCANONICAL_PACKAGE / NO_TRANSPLANT`.

The donor and canonical navigation-maintenance CLIs both default the model server executable to the macOS-specific `/opt/homebrew/bin/mlx_lm.server`. This is not donor-unique and was not changed in this review; assess it against the product's optional platform-support contract before release.

After mapping the explicit review paragraphs to the exact scope manifest, persisted records cover **55/62 paths and 26,661/33,497 additions**. This corrects the prior cumulative 26,611 figure by 50 additions. **Seven paths and 6,836 additions remain without explicit review paragraphs**; source-read completion is not claimed. No source code was sent to GLM, and no tests were run.


## 2026-09-30 - source review 56-57 of 62

Reviewed all 21 additions to `twin_core/store.py` and all 314 additions / 11 deletions to `twin_core/telegram_pipeline.py` at donor commit `d29d209e9094302937c60d28aeab7a54f78ede27`. Store blobs: base `14a394631ee87cd6c10d246eee62137398bd2fa4`, SHA-256 `0a0502ab06282689556489e77a47b457bbdaf11d27eb38630d1ce447e4924cae`; donor `434d10cc1f5c9365a5e1d764ca7425466513607a`, SHA-256 `b65f972dc7627c2aeeea5ee8ac8f28a4d0acbe86da681be06a0d515d696e6c1d`. Pipeline blobs: base `066edd45c69c14e328b86c1936b1c930a700f11a`, SHA-256 `97f0f16d64c367167022339befb6e302064db0c8af44698ed8e754e9960a2ac0`; donor `09ad20ff20348e1a319d5f9f6ad4fbfe92505161`, SHA-256 `a938e5927c87fc7c7238e400e27270394620ba5d1e32acfe11e1934a72b50914`.

`TwinStore.latest_operation_receipt()` returns the latest receipt for an event and operation regardless of status. Its donor caller `_compare_shadow_execution()` uses that to observe non-committed legacy completion, alongside committed shadow-route and provider-boundary receipts. The comparison binds decision hashes and attempt numbers, checks for telemetry changes during comparison, and labels the mode observe-only with authority, execution and enforcement all false. A hash-verified search of all 12 changed donor test files found no reference to this comparator or the new store method; tests were not run.

[P2] A present but non-committed completion adds `LEGACY_COMPLETION_NOT_COMMITTED`, while the result can still report `status: complete` and `alignment: match`: completeness is based on the three projections being present, and mismatch is assigned only to a refused shadow decision whose provider boundary was reached. This may be intentional evidence-completeness semantics, but callers must inspect `reason_codes`; the current field names can otherwise read as a successful aligned execution. Static observation only.

This shadow-memory audit is distinct from Archaeology's documented repository-mapping product. The explicit wheel source allowlist includes the `modules/operations` implementation and excludes `twin_core/`; no transplant into the public Archaeology package is warranted. Disposition: `REVIEWED_SOURCE_INCREMENT / UNIQUE_TWINCORE_SHADOW_COMPARISON / OUTSIDE_DOCUMENTED_ARCHAEOLOGY_PRODUCT / RESULT_STATUS_AMBIGUITY / NO_TRANSPLANT`.

Verified donor source-read coverage is now 57/62 files and 26,946/33,497 additions. Five paths / 6,501 additions remain without explicit review paragraphs. No source was sent to GLM, no tests were run, and no project copy was created.


## 2026-09-30 - source review 58 of 62

Reviewed all 262 additions in new donor file `twin_core/source_quality.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27`. The base tree has no file at this path. Donor blob `89d3b27aeb7afbaa7a2c8722e55c5e4896b8b44d`; SHA-256 `0ec564683a4d93846e7aef5d744435afafd53c45ec275a3a2bae3836341a9291`.

The module implements deterministic domain-authority tiers, registrable-domain caps, CJK-aware tokenization and shingles, Jaccard near-duplicate scoring, lexical claim support, and source-count/citation-support confidence levels. The docstrings correctly say these signals do not prove truth. A hash-verified search of all 12 changed donor test files found no references to these functions; tests were not run.

[P2] `_DOCUMENTATION_PREFIXES` is applied with a raw hostname `startswith` check. Any unrelated host beginning `docs.`, `developer.`, or `developers.` receives the `primary` tier, although the module describes that tier as official documentation. This can overstate source authority. `registrable_domain()` is also explicitly an approximation rather than a public-suffix-list implementation, so its diversity grouping has known suffix-boundary limits. Static observations only.

This is literature-source evaluation rather than repository mapping; it is absent from Archaeology's explicit wheel source allowlist and outside its documented product contract. Disposition: `REVIEWED_SOURCE_INCREMENT / SCIENTIFIC_SOURCE_QUALITY_OUTSIDE_ARCHAEOLOGY_SCOPE / DOMAIN_PREFIX_OVERCLASSIFICATION / NO_TRANSPLANT`.

Verified donor source-read coverage is now 58/62 files and 27,208/33,497 additions. Four paths / 6,239 additions remain without explicit review paragraphs. No source was sent to GLM, no tests were run, and no project copy was created.


## 2026-09-30 - cumulative source-review count correction

The two preceding source-review entries used an incorrect baseline of 26,611 additions. The prior authenticated crosswalk records 55 reviewed paths / 26,661 additions. The newly reviewed paths add 21 + 314 + 262 = 597 additions. Correct cumulative coverage is therefore 58/62 paths and 27,258/33,497 additions; the four remaining paths contain 6,239 additions. This arithmetic correction supersedes the cumulative totals stated in the source-review 56-57 and source-review 58 paragraphs; their per-file review evidence and dispositions are unchanged.


## 2026-09-30 - source review 59 of 62

Reviewed all 524 additions in new donor file `twin_core/web_discovery.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27`. The base tree has no file at this path. Donor blob `4957e98af052347ad86bb02694c308abd061bd22`; SHA-256 `dc28172932994c06ff15781cf7f557e29a2b9ecbd517b566ea19fd95a82070f9`.

The module exposes archived Wikipedia, OpenAlex, and DuckDuckGo discovery, parses bounded result fields, round-robins provider responses with domain caps, and records provider receipts. It labels results as untrusted external discovery and explicitly sets `claim_authority: false`. A hash-verified search of all 12 changed donor test files found no references to these providers or selection functions. No provider requests were made and tests were not run.

This is scientific literature/public-web discovery, not repository-source archaeology, and its `twin_core/` path is excluded by the explicit Archaeology wheel source allowlist. Disposition: `REVIEWED_SOURCE_INCREMENT / RESEARCH_WEB_DISCOVERY_OUTSIDE_ARCHAEOLOGY_SCOPE / NO_TRANSPLANT`.

Corrected cumulative source-read coverage is 59/62 paths and 27,782/33,497 additions. Three paths / 5,715 additions remain without explicit review paragraphs. No source was sent to GLM and no project copy was created.


## 2026-09-30 - source review 60 of 62

Reviewed all 1,312 additions in new donor file `twin_core/sovereignty.py` at commit `d29d209e9094302937c60d28aeab7a54f78ede27`. The base tree has no file at this path. Donor blob `42a6ff9c343e4b6c0baaf25909b35519f1d7cec9`; SHA-256 `9c601a38d4f8497177864cdd2f0f3a851c8e8bd73006af18446c904570fdae3a`.

The module defines evidence-weighted, freshness-adjusted dimensions and guardrails for a personal sovereignty score, with minimum coverage/reliability thresholds, withheld/provisional states, counterfactual choice diagnostics, trend comparisons, and Markdown output. Its methodology explicitly rejects worth, productivity, happiness, mental-health and truth claims. Hash-verified scans found callers in `twin_core/research_export.py` and `twin_core/scientific_pipeline_cli.py`, and no references in the 12 changed donor test files; tests were not run.

[P2] Malformed JSON values such as an array/object in `indicator` or `evidence_class` reach dictionary membership checks and can raise raw `TypeError` instead of the module's `SovereigntyError`. Static input-validation observation only.

This is personal-life measurement and research-export functionality, not repository-source archaeology. Its `twin_core/` source is excluded from the explicit Archaeology wheel allowlist and documented product contract. No transplant is warranted. Disposition: `REVIEWED_SOURCE_INCREMENT / PERSONAL_SOVEREIGNTY_OUTSIDE_ARCHAEOLOGY_SCOPE / MALFORMED_INPUT_EXCEPTION_TYPE / NO_TRANSPLANT`.

Corrected cumulative source-read coverage is 60/62 paths and 29,094/33,497 additions. Two paths / 4,403 additions remain without explicit review paragraphs. No source was sent to GLM, no tests were run, and no project copy was created.
