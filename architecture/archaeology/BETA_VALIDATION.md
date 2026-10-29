# Developer beta validation — 0.1.3b3

The mapping canary and regression results below were established on 0.1.3b1. Version 0.1.3b2 added the operator-selected MIT licence and packaging metadata. Version 0.1.3b3 fixes a SQLite URI compatibility issue and makes the contributor test setup explicit.

This is the release-specific evidence summary. Installation and supported scope are in README.md;
historical ownership/identity evidence remains in IDENTITY_MIGRATION.md.

## Additional verification for 0.1.3b3

- On the registered ArtVault Linux host, the full suite passed on Python 3.11, 3.12, 3.13 and 3.14: 375 passed, 1 skipped, 2 subtests passed on each interpreter.
- The Python 3.11 run covers the SQLite URI compatibility fix.
- The 0.1.3b3 wheel built with pip and the source archive built with the PEP 517 frontend from the registered canonical source. The wheel installed, `pip check` was clean, and `giga-archaeology --help` succeeded. Final artifact digests are recorded outside the package in `evidence/release-artifacts/0.1.3b3.json`; embedding a wheel's own digest in a document included in that wheel would make the digest self-referential. The source archive was not extracted into another project tree.
- macOS and Windows were not run for this candidate. The earlier macOS arm64 evidence below applies to the 0.1.3b1/b2 code state and does not certify the 0.1.3b3 changes.

## Verified on macOS arm64 / Python 3.14

- The standalone wheel installs using public parser dependencies only. No Giga control-plane package,
  private source checkout, PYTHONPATH injection, API key or model call is needed for the tested path.
- Pip dependency check, inventory, map generation, structural query and compact context all pass.
- The source distribution builds through pip into a byte-identical wheel.
- Three optional-integration regression tests pass without Giga: plain mapping remains available,
  Giga capability manifests are refused when their validator is missing, and a broken installed
  backend is not silently treated as absent.
- All 27 tests in test_archaeology_mapper.py pass with the existing Giga integration installed.

## Independent repository canary

Repository: https://github.com/pallets/itsdangerous, tag 2.2.0, upstream commit
`096c8d42545d3b68ea21a4f890fb2b2d8979c0bd`.
The archive SHA and raw command outputs are preserved in operator-local release evidence.
An unchanged archive was given a local Git fixture commit because the scanner requires Git metadata;
that local fixture commit is not represented as upstream history.

The scan admitted 60 files and produced 1,457 entities and 2,649 relations. Independent source-AST
checks confirmed locations for Serializer, dumps, loads, dump_payload and load_payload, plus the
base64_decode -> want_bytes static call. Repeated compact-context output was byte-identical and
Git status stayed clean. No third-party application code was executed by the scan.

These six anchors are not a whole-repository precision/recall measurement. Performance on large
repositories, other Python versions/platforms, other languages and optional semantic providers is
not established by this canary. No model-token savings claim is made.

## Structural source graph

The graph was refreshed from the same 42 Python source files in the registered canonical
workspace with Graphify 0.7.10's deterministic AST extractor at commit
`f83ef0ab922ed461efdfcdce7d6b7992c012aa3b`. It contains 1,222 nodes, 3,824 edges and
37 communities. All 42 repository-relative input hashes match the manifest.

Graph SHA-256: `b87cac9f54031dcc29fcce7157232bed46e571ef78232d36007771bdeeb9cbf3`.
Manifest SHA-256: `7950a68ae7abcdf1eba6bba8a760a2301bf3677673cf8237e44a95ba26c1a607`.

Compared with the prior graph, 84 prior node IDs are absent and 32 IDs are new. This
records current structural extraction, not feature completeness or a node-by-node
equivalence proof. Markdown prose, runtime behaviour and semantic extraction remain
outside this code graph. No model calls were used for graph generation.
## Release boundary

The narrow Python mapping beta is technically verified within the scope above. The operator selected MIT, supplied in LICENSE; public distribution has not been performed. Runtime installation on
ArtVault is a separate action; source synchronisation does not imply services were upgraded.

## MIT packaging verification

Version 0.1.3b2 includes identical MIT text in the source archive, wheel and prepared metadata. Licence-Expression and Licence-File metadata, wheel RECORD hashes and repeat-build identity were checked. Mapper source is unchanged from the verified 0.1.3b1 canary.

## 2026-09-29 — retention CLI and source graph refresh

The navigation-retention CLI integration was committed and pushed in aafe486bcdf34a1ebd680f6a1bac379eb8ceefb7 (Restore navigation retention CLI command). The retention regression file passed all 83 tests on ArtVault Linux, and direct CLI help confirmed the command and options. The existing 0.1.3b3 wheel and source archive predate this revision and do not contain it; they are not release artifacts for this source state.

The structural source graph now reflects commit aafe486bcdf34a1ebd680f6a1bac379eb8ceefb7. Graphify 0.7.10 processed 42 Python inputs with zero source-hash mismatches. It contains 1,222 nodes, 3,826 edges and 36 communities. The graph query confirms the path from archaeology.py through main() to run_navigation_retention().

Graph SHA-256: 60026e2f5e31c579c369a6b22979171b400a5e0b90817b09d44af1c49e0d52ec.
Manifest SHA-256: a0131c3c2abe40cd021e04b96a36b1b494d5965b4f7844820248444e9c0be9e2.

A first graph merge was rejected because it would have removed 147 unrelated nodes and 754 edges. The corrected source-scoped update preserved every prior node and edge and added two call edges for the CLI integration. This graph evidence establishes structural linkage only; it does not establish product completeness or cross-platform readiness.

## 2026-09-29 — cross-platform CI baseline and current run blocker

A new GitHub Actions workflow was added at .github/workflows/ci.yml for the full pytest suite on Ubuntu, macOS and Windows with Python 3.11–3.14. It installs the Linux bubblewrap package, limits parallel jobs to three, cancels stale runs, and ignores evidence-only commits.

Run 36557068700 on commit 781243c completed Linux and macOS across all four Python versions successfully. On hosted Linux, the two tests requiring network namespaces were skipped only when the runner returned an explicit permission-denied error; ArtVault Linux ran the affected retention/quarantine files with 89 passed and 1 skipped. The Windows jobs exposed a test portability issue: fcntl was imported unconditionally and multiple test helpers invoked /usr/bin/git. The fcntl lock test now uses Archaeology's cross-platform lock helper; quarantine probe tests are marked unsupported on Windows; test Git commands resolve through PATH. These changes are in commits 444eb2e and d9d9209.

The subsequent runs on d9d9209, f12be83 and 0647f6b failed before assigning a runner and produced no test logs. GitHub's check annotation for run 36558636501 says the job could not start because runner admission was blocked. Therefore the Windows portability changes have not yet been verified by CI; the earlier Windows failures cannot be presented as fixed. The README platform certification statement remains unchanged until a runner verifies the corrected matrix.

The project is still not ready for publication: the latest source is not represented by the existing 0.1.3b3 distribution artifacts, and public visibility/release has not been requested.

## 2026-09-29 — current-source clean-environment validation

The current canonical source was installed into a new isolated ArtVault virtual environment from the registered workspace with the declared `.[test]` extra. On Python 3.12.3, installation completed, `pip check` reported no broken requirements, and `giga-archaeology --help` succeeded. The full suite then passed: 376 passed, 1 skipped, and 2 subtests passed in 74.60 seconds. The skip is `tests/test_archaeology_quarantine.py:182`, which exercises a Darwin sandbox profile and does not apply on Linux.

The tested source was commit `a0d53cc87a1d013e1d32286d073b762185e455b3`; the following `a0d53cc`-range ledger updates contain preservation notes only, not product-code changes. This validates a clean Linux install and test run on Python 3.12, not the full OS/interpreter matrix. It does not certify macOS or Windows. The built metadata still identifies itself as `0.1.3b3`; these install-time checks do not make the older retained 0.1.3b3 release artifacts current or suitable for publication. No package was published.

A separate pre-existing shared ArtVault venv produced a `pip check` conflict because its installed `codegraphcontext 0.6.8` requires Tree-sitter below 0.26 while Archaeology pins 0.26.0. The isolated environment had no such conflict; the shared-environment warning is not evidence of a clean co-install with `codegraphcontext`.

## 2026-09-29 — supported CLI self-scan smoke

At source commit `b01521f6f6e9336a0e481b45c37ed7c0a470b9f9`, the clean installed Linux CLI ran the README's supported inventory-to-context path against the canonical Archaeology Git repository itself. Navigation inventory admitted 179 files and returned `CURRENT`; mapper refresh returned 38,439 entities and 86,002 relations with `CURRENT`; a symbol query for `run_navigation_retention` returned `PASS` with 10 results; implementation context returned `PASS` with 11 entries from 52 candidates (21 projectable), 582 `giga.lexical-token.v1` units used of 1,200, and 10 explicit omissions. The context field was 2,546 characters, reinforcing that the declared lexical-token budget is not a byte or JSON-envelope limit.

The inventory/map/query/context outputs were written under `/tmp`, outside the repository. The scan read source without executing it. This is a useful end-to-end smoke of the supported CLI workflow, not an independent accuracy benchmark; it does not establish completeness, precision/recall or portability beyond the tested ArtVault Linux/Python 3.12 environment.

## 2026-09-30 — release artifact install path and CI

The README now includes a PowerShell install path and distinguishes current Linux evidence from the older macOS canary. It does not claim that this candidate is cross-platform certified.

Commits 31c51a0698e070c818a9b1792ea744dfec776712 and 3205bf295d37644ab44e72762d187a2bea85419a extend the existing GitHub Actions matrix. On Python 3.12, each Ubuntu, macOS and Windows lane now builds the wheel and source archive, installs each artifact in a separate clean virtual environment, runs pip check, and invokes giga-archaeology --help. The matrix remains capped at three concurrent jobs. These hosted steps have not yet produced an accessible result for this increment.

On ArtVault Linux with Python 3.12.3, build 1.6.1 produced both artifacts from the candidate source. Each artifact installed into its own fresh virtual environment, pip check reported no broken requirements, and the CLI help command passed. The workflow YAML parsed successfully. This is Linux evidence only; the PowerShell recipe and macOS/Windows hosted artifact checks remain unverified.

The last recorded GitHub runner failure was before job assignment and reported that no runner was assigned. The repository's current hosted-run status could not be read from ArtVault during this increment, so no hosted pass is claimed.


## 2026-09-30 — current-source verification after location inventory

The canonical source now includes the location inventory implementation and its regression tests;
this code was added after the earlier 376-test run recorded above. On ArtVault Linux x86_64 with
Python 3.12.3, the full suite ran from the registered canonical workspace using the exact pinned
test dependencies in a disposable dependency-only environment: **418 passed, 1 skipped, and 2
subtests passed** in 75.33 seconds. The skip is specific to a platform-inapplicable sandbox case.
This run validates the current Python 3.12 source on Linux; it does not update the earlier Python
3.11–3.14, macOS, or Windows evidence.

Using Python build 1.6.1 and the custom PEP 517 backend, both the wheel and source archive built
successfully from the canonical source. Static archive inspection confirmed the project name and
version, Python floor, CLI entry point, Archaeology modules, README and license files, and that
TwinCore is excluded. The artifacts were not installed in this run. macOS and Windows remain
unverified, and no public release was created.


## 2026-09-30 — executable source-archive quickstart

The new `examples/quickstart.py` performs inventory, map refresh, symbol query, and bounded-context
rendering. It rejects an output store inside the scanned repository and refuses to write into a
non-empty external store. Full JSON receipts are saved locally; the terminal shows concise stage
summaries and bounded context. The custom PEP 517 backend includes the script in the source archive
and omits it from the runtime wheel; a regression test builds both formats and checks that boundary.

The walkthrough completed on ArtVault Linux/Python 3.12.3 against a temporary one-file synthetic
Git repository: inventory `CURRENT` (1 file), map `CURRENT` (21 entities and 21 relations), symbol
query `PASS` (8 results), and source-linked context for `Serializer.dumps` and related symbols. The
synthetic input and output stores were removed after the run. This exercised the canonical source
through a dependency-only environment with the source root on `PYTHONPATH`; it is not a clean
installed-wheel demo and does not certify macOS or Windows.

The full current-source suite passed on ArtVault Linux/Python 3.12.3: **421 passed, 1 skipped, and 2
subtests passed** in 75.44 seconds. The skip is the Darwin sandbox-profile test, which is not
applicable on Linux. Other interpreters and operating systems remain unverified for this source.


## Package discovery metadata

The PEP 621 project metadata now declares focused repository-analysis keywords and canonical
Repository/Issues URLs. The custom backend validates and emits them as Core Metadata fields. A
packaging regression checks the exact wheel metadata. No operating-system classifier is emitted while macOS and Windows remain unverified. The focused
packaging tests passed (4 passed), and the full current-source suite passed on ArtVault
Linux/Python 3.12.3: **422 passed, 1 skipped, and 2 subtests passed** in 74.96 seconds. The
skip remains the Darwin sandbox-profile test.

## 2026-10-29 — Privacy-safe paths and Python-version regression checks

Account-specific absolute home paths were removed from the scanner fallback, sandbox profile and regression fixtures. The sandbox regression now creates a real temporary protected file, so its denial check cannot pass merely because a hard-coded path is absent. The MIT notice uses the repository pseudonym. The tracked working-tree scan found no account-specific home path or real-name marker; remaining test email values use the reserved `example.invalid` domain.

The full current-source suite passed on ArtVault Linux/Python 3.12.3: **422 passed, 1 skipped, and 2 subtests passed**. The changed hypothesis, quarantine and packaging tests passed on Python 3.11, 3.12, 3.13 and 3.14 (24 passed and 1 Darwin-only skip on 3.11, 3.13 and 3.14; 24 passed and 1 skip on 3.12). Packaging metadata tests passed on Python 3.12 (4 passed). The Darwin sandbox execution remains unverified on this Linux host.


## 2026-10-29 — current source and installed distribution verification

The product and test code under verification is commit `9020c1ceece54438900e2904d929a292834c73d3` (tree `13cac253d1272beac0a094c2b033b176fda10781`). The later repository head contains documentation and validation updates only. Its full test suite passed on ArtVault Linux x86_64 with Python 3.12.3: **423 passed, 1 skipped, and 2 subtests passed** in 74.95 seconds. The skip is the Darwin sandbox-profile test, which does not apply on Linux.

The current source built a wheel and source archive with build 1.6.1 using the canonical custom backend. Each artifact installed into the existing ArtVault project test environment, `pip check` found no broken requirements, the CLI help command succeeded, and the supported-scan canary passed against the installed artifact (1 passed for each format). The wheel contains the MIT licence and excludes the source-only quickstart; the source archive contains the licence, quickstart and custom build backend. Artifact hashes and exact sizes are in `evidence/release-artifacts/0.1.3b3.json` under `latest_candidate_validation_20261029_9020c1c`.

GitHub Actions run 40819550308 on this commit ended with all 12 matrix jobs failing before any runner step started; no job logs were available. GitHub expanded the workflow matrix, but this run verifies no test results. macOS and Windows remain unverified, including the Windows inventory-fsync fix and the installed-artifact canary. The immediately preceding run showed the same zero-step failure pattern; an older run had a runner-admission annotation; this run's cause is unknown.

The current operational Graphify index contains 2,554 nodes. Its manifest includes the changed workflow and test file, but it does not bind the index to a source commit. The index remains untracked operational output and is not treated as a release artifact. The package version is still 0.1.3b3; these builds are not for distribution. No public release has been made.

## 2026-10-29 - complete Linux Python matrix on the current documentation head

At canonical source commit `058aa5f075975813ac3d087f1664ffaa92006353` on branch `codex/artvault-portable-giga-archaeology`, the full suite was run sequentially on ArtVault Linux x86_64 with the existing Python environments. Each run passed 423 tests, skipped one Darwin sandbox-profile test that does not apply on Linux, and passed 2 subtests:

| Python | Result | Duration |
| --- | --- | ---: |
| 3.11.16 | 423 passed, 1 skipped, 2 subtests passed | 79.40s |
| 3.12.3 | 423 passed, 1 skipped, 2 subtests passed | 74.05s |
| 3.13.15 | 423 passed, 1 skipped, 2 subtests passed | 75.46s |
| 3.14.7 | 423 passed, 1 skipped, 2 subtests passed | 79.08s |

The product and test files are unchanged from commit `9020c1ceece54438900e2904d929a292834c73d3`; the intervening commits change documentation and release evidence only. A WSL relay error interrupted the first Python 3.13 launch before pytest started; the ArtVault route recovered and the run then passed as recorded above.

GitHub Actions run [40819989797](https://github.com/Pepstee/giga-archaeology/actions/runs/40819989797), on documentation head `fbeb66487bacb7e0919f94a4222c3362018d425b`, expanded 12 jobs and failed all of them before any step began. It provides no test results. macOS and Windows remain unverified, including the installed-artifact checks. The no-runner failure remains an external hosted-CI blocker.

## 2026-10-29 — current-source package install and functional canary

At canonical commit `cfa49631d6510f22905a9d09f0c2d9ea549e35a3` (tree `d68511d67a0a195b97730012229efbaa79e4b80d`), build 1.6.1 produced the wheel and source archive on ArtVault Linux x86_64 with Python 3.12.3. Both formats installed in the existing Python 3.12 test environment; `pip check` and the `giga-archaeology --help` entrypoint passed for each. Installing the source archive built a wheel with the same SHA-256 as the directly built wheel.

The installed distribution then completed the documented inventory, map, symbol-query and context path against a one-file synthetic Git repository: inventory `CURRENT` (1 file), mapper `CURRENT` (14 entities, 12 relations), query `PASS` (4 results), and context `PASS` (131 characters). Full receipts remain under `/tmp/giga-archaeology-release-canary-cfa4963/store`; this is local test evidence and is not included in the release package.

The current product and test files are unchanged from the source tested in the Linux Python 3.11–3.14 matrix above. The latest hosted Actions run, [40822064209](https://github.com/Pepstee/giga-archaeology/actions/runs/40822064209), failed all 12 jobs before any step ran. GitHub exposed no job steps and the log endpoint returned 404 `BlobNotFound`, so the cause remains unknown. This is not a hosted pass. The full macOS matrix and all Windows checks remain unverified; separate native macOS package-smoke evidence is recorded below.

The package metadata still says `0.1.3b3`, whose existing filenames are already represented by historical artifacts. These newly built files are validation evidence only, not distributable replacements. No public release was created.

Separately, the exact wheel (SHA-256 `cad3b3d39f68a31c17f30ecde4c2de85843d18d18142eb29c9d6f0ccfd2ca447`) installed on native macOS 26.4.1 arm64 with Python 3.14.5. `pip check`, CLI help and the four-stage synthetic-repository canary passed: inventory `CURRENT` (1 file), map `CURRENT` (14 entities, 12 relations), query `PASS` (4 results), and context `PASS` (131 characters). This is package-smoke evidence, not a full macOS suite. Receipt hashes are in `evidence/release-artifacts/0.1.3b3.json`; local outputs remain under `/tmp/giga-archaeology-macos-canary-cfa4963/store`.

The two subsequent push runs, [40824313014](https://github.com/Pepstee/giga-archaeology/actions/runs/40824313014) on `dcdefb6b66938b3d267e2abe5754803e994a37e0` and [40824541437](https://github.com/Pepstee/giga-archaeology/actions/runs/40824541437) on `0bb629e9e21b774609a1d003c56568cf5fcf24cf`, also failed all 12 matrix jobs before runner steps. The latest job query returned zero steps; downloading its log returned 404 `BlobNotFound`. The failure cause is still unknown. These are hosted-service failures, not test results.

The next push run, [40824653871](https://github.com/Pepstee/giga-archaeology/actions/runs/40824653871) on `3f81e84b4511d014bb5f0ea901a2b4d92becf83c`, again failed before executing steps. Read-only inspection of all 12 job annotations found the same GitHub message: runner admission was blocked. Every job had zero steps and runner ID 0. Ubuntu 26 migration and macOS arm64 capacity warnings were also present, but no job reached a test. The hosted matrix therefore remains externally blocked, not failed by Archaeology test results.

The latest push run, [40824868315](https://github.com/Pepstee/giga-archaeology/actions/runs/40824868315) on `a742f8c986a46a74d34d7944c4fcdfb6e3d38af7`, repeated the same blocker. All 12 jobs failed before any runner step; no hosted tests ran. The other annotations were Ubuntu image migration and macOS arm64 capacity notices.

## 2026-10-29 — candidate artifact validation from a3ea235

At canonical source commit `a3ea235453782f0776b3c1e166257e03111bd1e0` (tree `36fab435dd6a178084eefbaa19dc45e283aa0160`), the Linux wheel and source archive installed in the existing Python 3.12.3 environment. `pip check` and each installed command-line help entrypoint passed. The installed source archive completed the synthetic inventory, map, symbol-query and bounded-context canary: 1 file, 14 entities, 12 relations, 4 query results and 131 context characters.

The same wheel bytes installed on native macOS 26.4.1 arm64 with Python 3.14.5. `pip check`, command-line help and the four-stage synthetic canary passed. This verifies a macOS wheel smoke path; it is not a full macOS test-suite result. Windows remains unverified. The full Linux Python 3.11–3.14 suite results above still apply because product and test files are unchanged from the tested source.

The candidate metadata and filenames still use `0.1.3b3`, which collides with historical candidate files. These builds are validation artifacts only. No public release was created. See `evidence/release-artifacts/0.1.3b3.json` under `latest_candidate_validation_20261029_a3ea235` for exact artifact hashes, sizes, install checks, canary receipt hashes and platform limits. This dated subsection records the a3ea235 build; later candidate builds are recorded in the ledger, and distributable files must be rebuilt from the final release commit.

## 2026-10-29 — README contribution guide included in distributions

The README links to `CONTRIBUTING.md`, so the explicit distribution allowlist now includes that
guide in both the wheel and source archive. A regression test checks that each archive contains the
exact source bytes. The focused packaging suite passed **5 tests**; the full ArtVault Linux/Python
3.12.3 suite passed **424 tests, 1 platform-specific skip, and 2 subtests** in 68.49 seconds.

GitHub Actions run [40825822360](https://github.com/Pepstee/giga-archaeology/actions/runs/40825822360)
on the preceding source commit completed with all 12 jobs failed before steps ran. The annotations
reported that no runner steps started. This run provides no CI test result.
macOS full-suite and Windows validation remain open. Distributable artifacts have not yet been
rebuilt from this source change; the `0.1.3b3` version collision remains, and no public release was
created.

## 2026-10-29 — build and hosted workflow from c169318

The preceding subsection was committed before its package rebuild; its pending-build statement
records that point in time. After commit `c169318f7459d97699d2c6f44c825363d3b01bc3` (tree
`984c9bed9fa1d164fd11ed082364e6bcb19cfd0a`), Python 3.12.3 on ArtVault Linux built the wheel and
source archive with build 1.6.1 and the canonical PEP 517 backend. Static inspection found 48 wheel
members and 47 source-archive members. Both contain the exact `CONTRIBUTING.md` source bytes, README
and MIT licence; the wheel omits the source-only quickstart, while the source archive includes it
and the build backend. Exact hashes and sizes are recorded in the release ledger. These artifacts
were not installed in this increment, so this build does not establish an installed-artifact canary.
They remain validation artifacts only: the version is still `0.1.3b3` and no public release was
created.

GitHub Actions run [40826776978](https://github.com/Pepstee/giga-archaeology/actions/runs/40826776978)
on this commit completed with all 12 matrix jobs failing before any step began. Every job had runner
ID 0 and zero steps; all 12 annotations reported no runner steps; no hosted tests ran. The hosted run supplies no test result. Linux/Python 3.12.3 local tests passed as recorded
above; macOS full-suite and Windows validation remain open.


## 2026-10-29 — current release evidence after c169318

The product and test sources remain at `c169318f7459d97699d2c6f44c825363d3b01bc3`. The following
`c2ff01a` and `d49944e` commits change release evidence only, so the 424-test Linux/Python 3.12.3
result recorded above still covers the current product and test files. The earlier Python 3.11–3.14
matrix predates the packaging-guide inclusion change and does not cover that final packaging
change.

At source commit `c2ff01a47030cc03a31f5df3761a334480415325`, ArtVault Linux/Python 3.12.3 rebuilt
the wheel and source archive. Static inspection confirmed 48 wheel members and 47 source-archive
members, with the exact contributor guide, README and MIT licence in both; the source archive also
contains the quickstart and build backend. The wheel SHA-256 is
`af5ec07295f30a2ab09303a6480fa5bf544c6bfe436ee68778728e5282815a28`; the source-archive SHA-256 is
`c953a6b653214990c4f234ab00c446b8e7ee16ae1d65948db36aadc20dbfa822`. These exact artifacts were
not installed and have no install canary. Earlier Linux and macOS smoke evidence belongs to other
same-version candidate bytes and does not transfer to these files.

The latest hosted Actions result remains [40826776978](https://github.com/Pepstee/giga-archaeology/actions/runs/40826776978)
on c169318. All 12 jobs failed before any runner step with zero runner steps; no hosted tests ran. The later evidence-only commits did not trigger another matrix run.
Windows and the full macOS suite remain unverified. Version `0.1.3b3` still collides with historical
candidate filenames. No public release was created.
