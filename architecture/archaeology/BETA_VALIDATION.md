# Developer beta validation history

This cumulative record covers candidates `0.1.3b1` through `0.1.3b4`. The current candidate’s final evidence appears in the dated `0.1.3b4` sections near the end. Historical results apply only to the source commits and artifact hashes they name. Exact host-local output paths are omitted.

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

The installed distribution then completed the documented inventory, map, symbol-query and context path against a one-file synthetic Git repository: inventory `CURRENT` (1 file), mapper `CURRENT` (14 entities, 12 relations), query `PASS` (4 results), and context `PASS` (131 characters). Full receipts remain under `[private local temporary path]`; this is local test evidence and is not included in the release package.

The current product and test files are unchanged from the source tested in the Linux Python 3.11–3.14 matrix above. The latest hosted Actions run, [40822064209](https://github.com/Pepstee/giga-archaeology/actions/runs/40822064209), failed all 12 jobs before any step ran. GitHub exposed no job steps and the log endpoint returned 404 `BlobNotFound`, so the cause remains unknown. This is not a hosted pass. The full macOS matrix and all Windows checks remain unverified; separate native macOS package-smoke evidence is recorded below.

The package metadata still says `0.1.3b3`, whose existing filenames are already represented by historical artifacts. These newly built files are validation evidence only, not distributable replacements. No public release was created.

Separately, the exact wheel (SHA-256 `cad3b3d39f68a31c17f30ecde4c2de85843d18d18142eb29c9d6f0ccfd2ca447`) installed on native macOS 26.4.1 arm64 with Python 3.14.5. `pip check`, CLI help and the four-stage synthetic-repository canary passed: inventory `CURRENT` (1 file), map `CURRENT` (14 entities, 12 relations), query `PASS` (4 results), and context `PASS` (131 characters). This is package-smoke evidence, not a full macOS suite. Receipt hashes are in `evidence/release-artifacts/0.1.3b3.json`; local outputs remain under `[private local temporary path]`.

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

## 2026-10-29 - canonical-source suite at 12358a8

At canonical source commit `12358a8c1ae2a64871ccd9f644a01b6b71ee4092` (tree `40103a5eabcfed382406f778e5cba2337174dc7f`), the full pytest suite ran from the registered ArtVault workspace on Linux x86_64 with Python 3.12.3: **424 passed, 1 skipped, and 2 subtests passed** in 74.13 seconds. The single skip is the Darwin sandbox-profile test, which is not applicable on Linux.

The run used `python -m pytest -q -p no:cacheprovider` with `PYTHONPATH` set to the exact canonical workspace and `PYTHONDONTWRITEBYTECODE=1`. This validates the canonical source tree only. The environment still contains an older installed `0.1.3b3` package; this run did not build or install a distribution and is not installed-artifact evidence. No checkout or source copy was created. Existing untracked project, graph, instruction, and cache data was preserved.

## 2026-10-29 — current 0.1.3b4 candidate

The current candidate uses version `0.1.3b4` to avoid collisions with historical `0.1.3b3` artifact filenames. The PEP 517 backend now derives its version from `pyproject.toml`; the focused packaging tests assert that the metadata, backend and wheel filename agree.

On canonical ArtVault Linux x86_64 with Python 3.12.3, the full suite passed: 424 passed, 1 skipped, and 2 subtests in 82.84 seconds. The focused packaging tests passed 5/5. These runs used the registered canonical source; no clone or worktree was created. A fresh wheel and source archive built successfully with build 1.6.1. The exact file digests and archive inspection are recorded in `evidence/release-artifacts/0.1.3b4.json`.

The `0.1.3b4` wheel passed a bounded install smoke into a temporary target with `--no-deps --no-index`: installed metadata was `0.1.3b4`, the imported module came from that target, `pip check` found no broken requirements, and the installed `giga-archaeology --help` entrypoint passed. Runtime dependencies came from the existing ArtVault Python 3.12.3 test environment; dependency resolution in a clean environment remains unverified. The exact temporary target was removed after the check.

The push-triggered GitHub Actions matrix failed before runner steps. All 12 jobs were rejected before runner assignment; no hosted tests ran. Full macOS-suite and Windows validation remain unverified. This candidate is unpublished.

## 2026-10-29 — clean dependency installs and platform canaries

This addendum supersedes the earlier statement above that clean dependency resolution was
unverified. The `0.1.3b4` wheel (SHA-256
`e507818166d7c236375f983eb97eee11bbb3fefd9701f78ee1c7e2a3ca4fedb0`) installed in fresh
virtual environments on Linux x86_64 / CPython 3.12.3, macOS arm64 / CPython 3.14.5, and
Windows AMD64 / CPython 3.12.16. Each resolved the four pinned Tree-sitter dependencies;
`pip check` or its uv equivalent and the installed `giga-archaeology --help` entrypoint passed.

The source archive (SHA-256
`6411cd389d5b9098eb540f65a8bdacb5fd1da6d1b63f414a948627e7d517cfe8`) installed in a fresh
Linux / CPython 3.12.3 environment with pip 24.0, resolved the same dependencies, passed
`pip check`, and built the same wheel digest. The installed command also completed an inventory
smoke against a one-file synthetic Git repository, reporting one file and one symbol with
read-only authority and cleanup disabled. Temporary environments and relay files were removed;
no source checkout or private corpus was copied. Exact scopes and rejected probe corrections are
in `evidence/release-artifacts/0.1.3b4.json`.

These are bounded install canaries, not full platform test suites. Full macOS and Windows suites
remain unverified. GitHub Actions run 40835341859 on older commit `e60544d`: all 12 jobs were rejected before runner assignment; no hosted tests ran. This pre-release candidate remains unpublished.

## 2026-10-29 — current source regression run

At canonical source commit `a260133cf9c1257d7aac855cab0e9db842f7cf48` (tree `d0792aeb3b294da2bae7e41b4b1c94427db3a3fa`), the full pytest suite ran in the registered ArtVault workspace on Linux x86_64 / CPython 3.12.3. `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q` completed with **425 passed, 1 skipped, and 2 subtests passed** in 82.78 seconds. The pre-existing untracked project data was preserved. This is source-tree test evidence; it does not certify a newly built wheel or sdist, macOS/Windows full-suite support, hosted CI, or publication readiness.

## 2026-10-29 — pre-rewrite hosted CI result

Push-triggered GitHub Actions run [40884610871](https://github.com/Pepstee/giga-archaeology/actions/runs/40884610871) targets source commit `c9cc259e73c35f9c4fdbb167bcdcdd59862b73e9` (tree `9103fe51de8fb048332befd479437ac47ed79608`). All 12 Linux, macOS, and Windows matrix jobs were rejected before runner assignment; no hosted tests ran. Full macOS-suite and Windows validation remain unverified; this candidate is unpublished.

## 2026-10-29 — current source artifact verification

The release ledger records the exact current-source wheel and source-archive build, metadata and archive checks, and any hash-bound installation canary. Each result applies only to the artifact hash recorded there. The current sdist is archive-inspected; no sdist installation canary is claimed because pip installation would extract another project copy.

## 2026-10-29 — full suite after portable temporary-path fixture update

At ArtVault HEAD `ace6f73459c703008d1460720c78c0b1191684e4` plus tracked working-tree diff SHA-256
`3fbe38052d1856e57526de522f7d02098ed86c58936839af94a5dd6fee7bc01b`, the full suite ran on Linux
x86_64 with CPython 3.12.3: **425 passed, 1 skipped, and 2 subtests passed** in 79.70 seconds.
The tested diff contained four tracked files: privacy-path redactions in this record and the two
candidate ledgers, plus the Darwin location-inventory fixture's switch from a fixed path to the
system temporary directory. Production implementation files were unchanged. This is source-tree
evidence only; it does not certify a newly built artifact, hosted CI, or full native macOS/Windows
suites. The diff hash binds the tested tree before this subsequent release-documentation update.

## 2026-10-29 — quickstart end-to-end evidence

The standalone quickstart was run from the canonical ArtVault source at ace6f73459c703008d1460720c78c0b1191684e4 against a one-file, committed synthetic Git repository. Inventory admitted one file; the mapper returned CURRENT with 25 entities and 30 relations; the calculate_total query returned two symbols; and bounded context included calculate_total and Invoice. The command exited 0, and the recorded module origin was the canonical modules/operations/scripts/archaeology.py. The private canary manifest SHA-256 is c3e1522b158ab5428c6f733dd40e5986c63c96c9d4ec2ce22a28ee4f74d49a29; all 44 preserved-file hashes verified. The synthetic fixture contained no private source.

The focused regression tests/test_archaeology_packaging.py::test_quickstart_runs_end_to_end_on_committed_repository passed: 1 passed in 0.85 seconds. It invokes QUICKSTART.main from the canonical source against a separate synthetic committed fixture and asserts inventory, mapping, symbol-query, and context results. Its private run-log SHA-256 is ec3c61992e3bb1a5aac88c5f3c5619a6eccaa445b8e776896e3c8c676f9f6278. This is focused source-tree evidence; it does not establish installed-distribution behaviour, the full suite, or full macOS/Windows test coverage.

## 2026-10-29 — wheel and source archive canaries

The 0.1.3b4 wheel was installed with pip using no dependency resolution and no index access into a bounded target outside the source workspace. Installed metadata reported version 0.1.3b4, the imported CLI module resolved beneath the exact target, and the installed giga-archaeology console command completed --help from outside the workspace. The target was removed after the results were captured. This used dependencies already present in the ArtVault test environment; it does not prove clean-environment dependency resolution. The hash-bound artifact and command evidence are in the release ledger.

The paired source archive was inspected without extraction. It contains the README, licence, and quickstart example, and excludes Git metadata. No source-archive installation canary is claimed because pip installation would extract another copy of the project. The exact archive hash and membership checks are recorded in the release ledger.

## 2026-10-29 - full Linux source suite after quickstart regression

At canonical ArtVault HEAD c9cc259e73c35f9c4fdbb167bcdcdd59862b73e9 (tree 9103fe51de8fb048332befd479437ac47ed79608) plus tracked working-tree diff SHA-256 8316510557181fc5a956056300657321647933ed16efc9cc4bb8063ca079be6d, the full pytest suite ran on Linux x86_64 with CPython 3.12.3:

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q

Result: **426 passed, 1 skipped, and 2 subtests passed** in 78.65 seconds. The tested six-file diff contained README and release-evidence updates plus test changes in tests/test_archaeology_packaging.py and tests/test_location_inventory.py; no production implementation files changed. This is source-tree evidence only. The documentation update in this section was written after the test run and is not part of its tested diff. It does not establish a rebuilt artifact, hosted CI, or full macOS/Windows test-suite coverage.

## 2026-10-29 — latest Linux source-tree verification

At canonical ArtVault HEAD c9cc259e73c35f9c4fdbb167bcdcdd59862b73e9 plus tracked diff SHA-256 9bccba549e1f299b175c7afe4dcb1dc163bbdd77da60bc631795687fd32941fd, the full pytest suite passed on Linux x86_64 with CPython 3.12.3: **426 passed, 1 skipped, and 2 subtests passed** in 84.44 seconds. This is source-tree evidence only. The run preceded the later evidence-ledger and documentation-only edits; production and test sources were not changed by those edits.

GitHub Actions run 40884610871 failed before runner assignment on both attempts. All 12 matrix jobs in each attempt had no runner and zero steps; no hosted tests ran and no job logs were available. Full macOS and Windows suites remain unverified.

The wheel and source archive with SHA-256 c7cdecdad7f8c37339690b9ad072251d34d7f13bb95148334d227796f6a1c0ad and 882e14bf2f4b0f5b39f03858da6e1c0fe9da3c2f9ed44542163943c6852b7897 record the build state when this entry was first written, before the README and BETA status correction. Those exact artifacts were not installed or rebuilt and remain historical evidence only. Any later build is recorded separately in evidence/release-artifacts/0.1.3b4.json. No install-canary or reproducibility claim applies to that earlier pair.


## 2026-10-30 — full suite recheck at published documentation checkpoint

At canonical ArtVault HEAD `c5f4f6685f98ef7ac22c87f6208e536bb4a2b27e`, the full suite ran on Linux x86_64 with CPython 3.12.3 using:

`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q`

Result: **426 passed, 1 skipped, and 2 subtests passed** in 89.11 seconds; the process exit code was 0. The tracked tree was clean before and after the run. This verifies the Linux source suite at the recorded commit only; the full macOS and Windows suites remain unverified.


## 2026-10-30 — superseded artifact build before validation-record update

At canonical ArtVault HEAD `b183e101b232502c51c8bf4f410567e98a73a47f`, build 1.6.1 produced a wheel and source archive. Their hashes and static inspection results remain in the release ledger. Both formats bundle `architecture/archaeology/BETA_VALIDATION.md`; these artifacts were built before this validation entry was added, so they contain older validation bytes and are superseded. Do not distribute them. A replacement build will be recorded in the release ledger after it is built from the corrected committed source. The ledger itself is excluded from the source archive, so it can carry the archive hashes without changing the packaged files.


## 2026-10-30 — latest Linux suite checkpoint

The earlier Linux full-suite run at canonical ArtVault source commit `9a1f8604ce99e7f65900f83d5f9a9d5f965cd079` (tree `20560be59f32de05e5c800e43b9fb656777ab5d8`) passed **429 tests, 1 skipped, and 2 subtests** in 88.59 seconds. It is retained here as a historical checkpoint.

The latest Linux full-suite run was recorded at canonical ArtVault HEAD `fe58a483af94d8a0cc3f8b7c72e2e69093dcfb77` with CPython 3.12.3: **429 passed, 1 skipped, and 2 subtests passed** in 91.73 seconds (exit code 0). This verifies Linux source tests only. The run followed source changes; the subsequent edits in this file and the README are documentation-only.

GitHub Actions run [41058173443](https://github.com/Pepstee/giga-archaeology/actions/runs/41058173443), for earlier commit `5b58e7fab099c17e4a6165faf0b67e65d44bd06b`, failed before runner assignment: all 12 jobs had zero runners and zero steps, so no hosted tests ran. That was the latest run checked for this checkpoint.

Full macOS and Windows suites remain unverified. Artifact checks are hash-specific; see the release evidence ledger. No public release has been made.

## 2026-10-30 — exact-hash Linux wheel canary before this documentation correction

Wheel SHA-256 `53eb9fc60debcd61e62c2fb1287fb43d1578bfa0e5690ec389be6c2d5abde442` passed a limited offline installation canary on ArtVault Linux x86_64 with CPython 3.12.3. Metadata version `0.1.3b4`, import origin beneath the temporary target, and both `giga-archaeology --help` and `giga-archaeologist --help` passed; the exact target was removed. The install used `--no-deps --no-index`, with dependencies supplied by the existing ArtVault environment, so clean dependency resolution remains unverified.

This wheel predates the documentation correction recorded here. Its canary does not verify a later wheel rebuild. Artifact hashes and subsequent verification are recorded in the release evidence ledger.

## 2026-10-30 — limited installation canary for the superseded wheel

The wheel with SHA-256 `14db98f5bd197243abaf694123afdec42b2276c213e14059fb048cbf5803c5e0` passed a limited offline install canary on ArtVault Linux with CPython 3.12.3. The installed distribution metadata reported version 0.1.3b4, the imported module resolved under the temporary install target, and both `giga-archaeology --help` and `giga-archaeologist --help` exited successfully. The exact target was removed and confirmed absent; the canon Git status was unchanged.

The install used `--no-deps --no-index`; runtime dependencies were already supplied by the existing ArtVault environment, so this does not verify dependency resolution in a clean environment. This wheel is superseded because the release documentation has been corrected. The replacement wheel and source archive are rebuilt from the corrected documents; their hashes and exact verification status are recorded in the release evidence ledger. The earlier macOS and Windows install canaries used a different wheel hash and do not verify the replacement artifacts.

GitHub Actions run [41058173443](https://github.com/Pepstee/giga-archaeology/actions/runs/41058173443) for commit `5b58e7fab099c17e4a6165faf0b67e65d44bd06b` failed before runner assignment: 12 jobs, zero runners, and zero steps started. No hosted tests ran. The full macOS and Windows suites remain unverified.
## 2026-10-30 — current-head CI and distribution status

At canonical ArtVault HEAD `fe58a483af94d8a0cc3f8b7c72e2e69093dcfb77`, the full Linux source suite passed with CPython 3.12.3: **429 passed, 1 skipped, and 2 subtests passed** in 91.73 seconds (exit code 0). This verifies the Linux source suite only.

Wheel SHA-256 `77dc42f5b53576461a7398c748005f26ab86d61b16407fb419dbd3bd957247f0` passed a limited exact-hash install canary on ArtVault Linux x86_64 with CPython 3.12.3. The target was removed and both console entrypoints and imported module origins were verified beneath that target. The canary used `--no-deps --no-index`; dependencies came from the existing ArtVault environment, so clean dependency resolution remains unverified. The wheel embeds the earlier README bytes and is superseded for distribution. The sdist SHA-256 `8df64f74b6e48cdce6833a611c510c6077f7c8859a89f6fd8ecc04f62389c3c2` was statically inspected but not installed; it also predates the current README and this validation update. Rebuild both artifacts from final documentation and run a new exact-hash wheel canary before distribution.

GitHub Actions workflow-dispatch run [41081019299](https://github.com/Pepstee/giga-archaeology/actions/runs/41081019299) targeted the same source HEAD. All 12 matrix jobs failed before steps were exposed, so no hosted tests ran. A sampled job log was unavailable (`404 BlobNotFound`); the causes are not established from the available job summaries. This supersedes run `41058173443` as the current hosted-CI status while retaining its historical record above.

The full macOS and Windows suites and exact-hash installation of artifacts built from the final documents remain unverified. No public release has been made.

## 2026-10-30 — hosted CI result after release-evidence commit

Push-triggered GitHub Actions run [41088033787](https://github.com/Pepstee/giga-archaeology/actions/runs/41088033787) targeted commit `4bad866c9ac95bcf7af3affe41ccbe50eed1be87`. All 12 matrix jobs ended with failure. The available job summaries expose no steps or log URLs; a sampled job-log request returned HTTP 404 `BlobNotFound`. No hosted tests or results were produced, and the cause is unknown. This run establishes no test result for Linux, macOS, or Windows.

The Linux source-suite result remains the earlier run at commit `fe58a483af94d8a0cc3f8b7c72e2e69093dcfb77`: 429 passed, 1 skipped, and 2 subtests passed on CPython 3.12.3. Full macOS and Windows suites remain unverified. No public release has been made.

## 2026-10-30 — current Linux suite and hosted runner status

At canonical ArtVault commit `63764612f527bfdf9a059ae6fcb809692c600a40` (tree `05c9f67b3c0825539b14eb9fc9268e5bef74d13d`), the full Linux source suite passed with **429 passed, 1 skipped, and 2 subtests passed** in 79.11 seconds (exit code 0). The later commit `9a0729f319f8c371d66aa0a151a36393de094fb8` changed only the release evidence ledger; the product and test files remain at the tested source state. This does not verify documentation packaging after this update or the full macOS/Windows suites.

GitHub Actions run [41105065947](https://github.com/Pepstee/giga-archaeology/actions/runs/41105065947) targeted commit `63efae4f80107f041ef04e93675b47b0e4e306aa`. All 12 jobs failed before starting test steps; each reported runner ID 0 and zero steps. No hosted tests or platform results were produced. The evidence-only commit after that run was excluded by the workflow's path filters and created no new run.

The current wheel and source archive must be rebuilt after this documentation update. Their hashes and any later exact-artifact checks belong in the release evidence ledger. No public release has been made.

## 2026-10-30 — latest push-triggered CI result

GitHub Actions run [41113562567](https://github.com/Pepstee/giga-archaeology/actions/runs/41113562567) targeted commit `9c097bc1ce05223eb1635466ac2749897c363229`. All 12 matrix jobs failed before runner assignment; each job had runner ID 0 and zero steps. No hosted tests ran, so the run establishes no test result for Linux, macOS, or Windows.

The latest full Linux source-suite result remains the run at canonical ArtVault commit `63764612f527bfdf9a059ae6fcb809692c600a40`: 429 passed, 1 skipped, and 2 subtests passed. Full macOS and Windows results remain unverified. The subsequent evidence-only commit does not change this test scope. No public release has been made.

## 2026-10-30 — latest push-triggered CI result after release documentation update

GitHub Actions run [41116885839](https://github.com/Pepstee/giga-archaeology/actions/runs/41116885839) targeted commit `8b2f901811edc75a72fcce01b3e432b47d280d23`. All 12 matrix jobs completed as failures before runner assignment; every job had runner ID 0 and zero started steps. No hosted tests ran, so this run establishes no test result for Linux, macOS, or Windows.

The latest full Linux source-suite result remains the run at canonical ArtVault commit `63764612f527bfdf9a059ae6fcb809692c600a40`: 429 passed, 1 skipped, and 2 subtests passed. Full macOS and Windows results remain unverified. No public release has been made.


## 2026-10-30 — full Linux suite and current-head CI recheck

At canonical ArtVault commit `ba2d3d4fd5161f34d4295169de69090135f4921e` (tree `9d459027e78a18e36dc45c87a280f1483526e217`), the full source suite ran on ArtVault Linux x86_64 with CPython 3.12.3:

```sh
cd /srv/artvault/projects/giga-archaeologist/workspace
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/srv/artvault/projects/giga-archaeologist/workspace
.venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=/tmp/archaeology-privacy-fullsuite-20261030
```

Result: **430 passed, 1 skipped, and 2 subtests passed**; exit code 0; elapsed time 85.523 seconds. This is Linux source-suite evidence for that exact commit. Full macOS and Windows suites remain unverified. Transcript command execution ID: `exec-fe4a0b3a-47a4-41fe-b526-b7acc16c5e70`; result message ID: `msg_03ec749a35d42887016ae4f6eeef8c8191ba4a0700a7459177`.

GitHub Actions run [41116885839](https://github.com/Pepstee/giga-archaeology/actions/runs/41116885839) targeted superseded commit `8b2f901811edc75a72fcce01b3e432b47d280d23`. All 12 matrix jobs failed before runner assignment, with zero runners and zero steps; no hosted tests ran and the cause is unknown. A GitHub API query at 2026-10-30 20:50:59 UTC for current HEAD `ba2d3d4fd5161f34d4295169de69090135f4921e` returned zero workflow runs. Neither observation establishes hosted platform test results.

No public release has been made. This documentation/evidence update does not rebuild or verify distribution artifacts; previously recorded wheel and sdist checks apply only to their exact recorded hashes and source bytes.


## 2026-10-30 — pre-update repository and hosted-CI checkpoint

This checkpoint was captured with the registered branch at `b7bed05953b3a0500a816af9f60caa3a6929bbef`. Its product and test files were unchanged from the full Linux source-suite run at `ba2d3d4fd5161f34d4295169de69090135f4921e`: 430 passed, 1 skipped, and 2 subtests passed on CPython 3.12.3. This carries forward Linux source evidence only; the later changes are release documentation and evidence. Full macOS and Windows suites remain unverified.

The latest observed Actions run is [41127578444](https://github.com/Pepstee/giga-archaeology/actions/runs/41127578444), for superseded commit `e31512e1aede3dd605ac8ffd6f78093eddfa4621`. All 12 matrix jobs ended before runner assignment, with zero runners and zero steps; no hosted tests ran. A GitHub API query at 2026-10-30 21:53 UTC returned zero workflow runs and zero check runs for then-current HEAD `b7bed05953b3a0500a816af9f60caa3a6929bbef`. The recorded provider annotation identifies runner admission restriction; no hosted test result was produced.

The exact-hash Linux quickstart canary and artifact hashes are recorded in `evidence/release-artifacts/0.1.3b4.json`. Those artifacts predate this README/BETA update and are superseded for distribution; rebuild and reverify them from the committed documentation checkpoint. Full macOS/Windows suites, hosted matrix results, and a public release remain outstanding.

## 2026-10-30 — current documentation artifact checkpoint

The successful install and quickstart canary described in the preceding section applies only to the exact wheel and source archive recorded in `current_artifact_rebuild_bc3d81a_20261030`. Those artifacts were built before that section was added. Because this validation file is packaged in both formats, the later documentation change requires a fresh build; do not treat the earlier hashes as current distribution artifacts.

The release ledger records the later rebuild from commit `740b910356f54894245d95e4aa9d9596ba7f2eda`: both formats built reproducibly, archive contents were inspected, and the full-archive privacy-marker scan found no local user paths or non-reserved email addresses. The exact wheel install canary for that later build was not run as of this checkpoint. No installed-artifact result is claimed for it. No public release has been made. Full macOS and Windows suites and hosted test results remain unverified.

## 2026-10-30 — current release-readiness checkpoint

The latest full Linux source-suite run was at canonical ArtVault commit
`6148ea80a05805cdc41998fb0081ccfe7e79d4be` (tree
`11f1256c0d4d6276b1f116d90e128158b374d8ae`): **430 passed, 1 skipped, and 2 subtests
passed** in 74.94 seconds on CPython 3.12.3. Production and test sources remained unchanged
through the later evidence-only commits; this verifies Linux source tests only. Full macOS and
Windows source suites remain unverified.

Push-triggered GitHub Actions run [41139822037](https://github.com/Pepstee/giga-archaeology/actions/runs/41139822037)
on documentation checkpoint `cb5322d09b7a4f6991f91939de104e541fcea7e0` ended before runner
assignment: all 12 jobs had zero steps and no hosted tests ran. The release ledger carries a
sanitized runner-admission summary.

The CI workflow path filters now include `architecture/archaeology/**` and `examples/**`, which
contain packaged validation documents and the quickstart. Changes to those user-facing files now
trigger the platform matrix and packaging smoke checks.

The active-branch privacy scan at commit `4f3652fe5992b232ce7afd753fffe64c72a9c8d6` inspected
106 tracked blobs and 214 reachable commit records: zero non-reserved email hits, zero local
profile-path hits across macOS, Linux, and Windows patterns, and zero reachable author or
committer email hits. Two email-like fixture strings use the reserved `.test` domain. The scan is
pattern-based and does not cover unreferenced server objects or external caches.

The reproducible wheel and source archive recorded for documentation commit `cb5322d` are
superseded because this checkpoint changes packaged documentation. Rebuild both formats after
commit. The exact-wheel installation canary still requires approval for its new hash. No public
package or GitHub release has been made.


## 2026-10-31 — latest Linux suite at sanitized history head

At canonical ArtVault commit c18b22d194dc1abdf25a5411e1d59471e7dbaff5 (tree
bfba732b9cff92f5f8c986d40ee5ead83e4c4265), the complete source suite passed on Linux x86_64
with CPython 3.12.3: **430 passed, 1 skipped, and 2 subtests passed** in 75.74 seconds (exit code 0).
The test ran from the registered canonical workspace; Git HEAD, tracked and staged diffs, and the
pre-existing untracked state were unchanged. The later commit 9e78460159316b38b37baa781d8d59a940ac75f1
changed only the release evidence ledger. This confirms Linux source tests only. Full macOS and Windows
source suites remain unverified.

GitHub Actions run [41146332388](https://github.com/Pepstee/giga-archaeology/actions/runs/41146332388)
targeted the same source revision. All 12 matrix jobs failed before runner assignment, with zero steps
started and no runner-side logs available. Actions is enabled. The current run's specific cause is
unconfirmed, and it establishes no hosted test results.

No public package or GitHub release has been made. The README and packaged validation document have
now been updated after this suite; rebuild both distribution artifacts from the corrected documentation
before any release.


## 2026-10-31 — full suite for documentation packaging guard

The full suite ran from the registered ArtVault Linux x86_64 workspace, based on HEAD
9e78460159316b38b37baa781d8d59a940ac75f1 with tracked-diff SHA-256
068f3fac89851e20701e69117bb60c63d0b809888fd78a0826bf8ac8db89f2fc. The tracked changes were
README.md, this validation record, and tests/test_archaeology_packaging.py. Result: **431 passed,
1 skipped, and 2 subtests passed** in 77.21 seconds with CPython 3.12.3 (exit code 0). The skip is
the existing platform-specific sandbox case. Git HEAD and Git status remained unchanged during the
run. Production implementation files were unchanged.

The added packaging regression asserts that the exact README and BETA_VALIDATION bytes appear in
both the wheel and source archive. The test is part of this full-suite result. Linux evidence only;
full macOS and Windows source suites remain unverified.

## 2026-10-31 -- hosted CI observation for sanitized history checkpoint

GitHub Actions run [41148503242](https://github.com/Pepstee/giga-archaeology/actions/runs/41148503242)
targeted source commit 74f700c76b143c08b100007153474c5681a888d4. All 12 matrix jobs failed before
runner assignment. No job steps ran and no hosted test results were produced. The release ledger keeps
provider-specific diagnostics out of this project record. This does not change the latest Linux
source-suite result above: hosted macOS and Windows verification remain open. No public package or
GitHub release has been made.

## 2026-10-31 -- hosted CI run at the sanitized-history checkpoint

GitHub Actions run [41152193550](https://github.com/Pepstee/giga-archaeology/actions/runs/41152193550)
targeted canonical source commit `dc4819f159bbab6226b3ea2c157cea7c9c97d14b`. All 12 matrix jobs
were rejected before runner assignment and no steps ran. The provider annotation is not reproduced in
this project record. No hosted test results were produced, so macOS and Windows verification remain
open. No public package or GitHub release has been made.

## 2026-10-31 -- latest hosted CI and exact wheel canary

GitHub Actions run [41154185074](https://github.com/Pepstee/giga-archaeology/actions/runs/41154185074) targeted source commit `928a832f2ffe16d8b755d15c34b9a32c3de81dc3`. All 12 matrix jobs failed before runner assignment and no test steps ran. One check confirms a runner admission restriction; this run produced no hosted test results. The latest Linux source-suite result remains 431 passed, 1 skipped, and 2 subtests passed on CPython 3.12.3, as recorded above. Full macOS and Windows suites remain unverified.

Wheel SHA-256 `167ceaba991db4d6dd9a83442d485e1d764d6463aa5cfb46329d87e2b49151e6` passed an exact-hash offline canary on ArtVault Linux with CPython 3.12.3. Distribution metadata reported `giga-archaeology` 0.1.3b4; both packaged CLI modules imported from the private target; `giga-archaeologist --help` and `giga-archaeology --help` passed; and the target was removed. The canary used `--no-deps --no-index`, so it relies on dependencies already present in the ArtVault environment and does not establish clean-environment dependency resolution.

This update changes documentation included in the wheel and source archive. The recorded wheel canary remains valid for its exact hash, but rebuild both formats from this committed documentation before distribution and verify the resulting hashes. No public package or GitHub release has been made.

## 2026-10-31 -- current hosted CI and package portability metadata

GitHub Actions run [41193319320](https://github.com/Pepstee/giga-archaeology/actions/runs/41193319320) targeted documentation checkpoint `ecb61d999625775b2d6875990c2e2aabd2f1f775`. All 12 matrix jobs stopped before runner assignment; runner ID was zero and no steps ran. The sampled check annotations indicate a runner-admission restriction, so this run produced no hosted test results. The prior run [41193178195](https://github.com/Pepstee/giga-archaeology/actions/runs/41193178195) on the package metadata and Windows CI changes had the same pre-run outcome. The new Windows lock-error-mapping test and supported-path matrix therefore remain unverified. Full macOS and Windows suites remain unverified.

The current Linux checkout passed the focused packaging and OS-support checks: **12 passed** (9 packaging tests and 3 OS-support tests). The package metadata now declares beta status, Linux/macOS/Windows, and Python 3.11 through 3.14. These metadata and CI improvements have not yet received hosted verification.

This document is included in both distributions. Rebuild the wheel and source archive from the committed documentation, verify both hashes, and run a new exact-hash wheel canary before distribution. No public package or GitHub release has been made.

## 2026-10-31 - full Linux suite on source commit c41cc49

The complete source suite passed on the registered ArtVault Linux x86_64 workspace with CPython 3.12.3 at source commit c41cc497e52a5a6dbee0f902fc6773a51f4c472b: **431 passed, 1 skipped, and 2 subtests passed** in 82.11 seconds (exit code 0). The tracked tree was clean before and after; all pre-existing untracked files were preserved. This validates Linux source tests only. Full macOS and Windows source suites remain unverified.

## 2026-10-31 - hosted CI for the quickstart documentation checkpoint

GitHub Actions run [41195220665](https://github.com/Pepstee/giga-archaeology/actions/runs/41195220665) targeted documentation commit fb7650a7657397f08e6a335fb91b1b8bc6cd34d7. All 12 matrix jobs stopped before runner assignment; the job records show no steps, so no hosted tests ran. Sampled annotations indicate a runner-admission restriction. This evidence applies to that revision only and does not establish the result for later commits. Linux source-suite evidence remains local to ArtVault; full macOS and Windows suites remain unverified.


## 2026-10-31 — current Linux suite and hosted CI run

The complete source suite passed on the registered ArtVault Linux x86_64 host with CPython 3.12.3: **434 passed, 1 skipped, and 2 subtests passed** in 76.45 seconds (exit code 0). The tested source tree matches commit `10eba5e3a081b26b9a7c308641061c60e558a248`; the commit identity was corrected after the test without changing the tree. This is Linux evidence for Python 3.12.3 only.

GitHub Actions run [41199872816](https://github.com/Pepstee/giga-archaeology/actions/runs/41199872816) targeted the same tree. All 12 visible job annotations show the jobs were not started before tests; no hosted tests ran. The run did not verify the macOS, Windows, or hosted Linux matrix. The cause recorded in those annotations has been omitted from this public-facing evidence.

The current 0.1.3b4 candidate has reproducible wheel and source archive builds, but the exact artifacts have not yet passed an install canary. The repository remains private, with no public package or GitHub release.

## 2026-10-31 — latest hosted CI observation

GitHub Actions run [41200562209](https://github.com/Pepstee/giga-archaeology/actions/runs/41200562209) targeted commit `e3e2a1d5b18c7e20f31e83e867a18ab6704b9d4e`. All 12 matrix jobs completed as failures, and the job-step records contain zero steps. The cause is unconfirmed for this run, so no hosted tests ran and no platform result can be claimed. The complete Linux source suite remains local evidence for CPython 3.12.3; full macOS and Windows suites remain unverified.

## 2026-10-31 — hosted CI observation reviewed for release record

GitHub Actions run [41202881050](https://github.com/Pepstee/giga-archaeology/actions/runs/41202881050) targeted earlier documentation checkpoint `14b40e3f2f93bf35dc620b4d85bb6c60798ed8ef`. The 12 matrix jobs failed before any steps ran; each job record had an empty runner name and zero steps. The available job records do not establish the cause, and this run produced no hosted test results. At inspection time, registered branch head `cdcdf530d9dbcfc934bd96dcc17f5e45e6b942c2` had zero check runs. This is a record of the inspected run, not a claim of hosted validation for a later commit. Hosted macOS and Windows validation remain unverified.

## 2026-11-01 — limited canaries for the prior documentation artifacts

The reproducible wheel and source archive were built from package inputs at commit
`bafb71f6a2ca06d631de36c3bc161c67741362e6`. Wheel SHA-256
`08ac3b56ab7ffcb7d0550ea5f53bbe2cd3ae50b317272b902549d9120b265bbe` and source archive
SHA-256 `f2409348cba4156135de0136ecf3974a1e383ac666e826b7e41ab3ecf0976ccd` each passed a
limited install canary on ArtVault Linux x86_64 with CPython 3.12.3. Distribution metadata and
installed module origin were verified; `giga-archaeologist --help` and
`giga-archaeology --help` both passed, and temporary install targets were removed.

During the sdist install canary, pip ran without build isolation or dependency resolution, and
the source archive build backend ran in a network-isolated environment. Runtime dependencies came
from the existing ArtVault environment. These checks do not verify a clean-environment dependency install, native macOS or
Windows execution, or hosted CI. Full macOS and Windows suites and hosted test results remain
unverified. No public package or GitHub release has been made, and the repository remains private.

These results apply only to the exact hashes above and the documentation snapshot used for that
build. Rebuild and verify both distribution formats after documentation changes; canary the exact
hashes intended for distribution.

## 2026-11-02 — hosted portability matrix

GitHub Actions run [41371777892](https://github.com/Pepstee/giga-archaeology/actions/runs/41371777892) tested commit
5edd6e8676c2610c9faa976ef0555c679f3bd77d and completed all 12 matrix jobs successfully.
Ubuntu and macOS full source suites passed on Python 3.11 through 3.14. Windows lock-error
mapping and supported-scan checks passed on Python 3.11 through 3.14. The Windows Python 3.12
job also built and installed a wheel and source archive from this commit and passed the installed
supported-scan checks for both formats.

This is the first successful hosted matrix recorded for the current branch. The earlier run
[41369814990](https://github.com/Pepstee/giga-archaeology/actions/runs/41369814990) failed on
Windows Python 3.12 and 3.13 with SQLite integer overflow during metadata insertion. That failure
did not recur in run 41371777892. Commit 5edd6e8 adds a pathless diagnostic that can report only
allowlisted SQLite metadata column names if the overflow recurs; no offending column was captured,
the cause remains unconfirmed, and no metadata conversion fix is claimed.

The Windows Python 3.12 package steps are CI evidence for builds from this commit; they are distinct
from the exact ArtVault canaries. Wheel SHA-256
08ac3b56ab7ffcb7d0550ea5f53bbe2cd3ae50b317272b902549d9120b265bbe and source archive SHA-256
f2409348cba4156135de0136ecf3974a1e383ac666e826b7e41ab3ecf0976ccd, built from the October 31
documentation snapshot, passed limited ArtVault Linux x86_64 CPython 3.12.3 install canaries.
Distribution metadata, installed module origin, and both CLI help commands passed; the sdist
backend ran without network access, with runtime dependencies from the existing environment. These
artifacts predate this documentation update and do not establish clean-environment dependency
resolution. Rebuild and verify both formats from the final documentation before distribution. The
repository remains private; no public package or GitHub release has been made.

## 2026-11-02 - current targeted checks and release state

The 36 repository test modules were run individually or in small groups from the registered
ArtVault canon after earlier whole-suite invocations were interrupted by WSL service failures.
They reported **441 passed, 1 skipped, and 2 subtests passed** in aggregate. This is targeted
module-level evidence, not a single successful full-suite run.

GitHub Actions run [41380822543](https://github.com/Pepstee/giga-archaeology/actions/runs/41380822543)
tested documentation snapshot commit `9df2def1924acfdb0ba5bb26031f171ee57ebbf2` and completed
all 12 matrix jobs successfully. Ubuntu and macOS full suites passed on Python 3.11 through 3.14.
Windows lock-error mapping and supported-scan checks passed on Python 3.11 through 3.14. The
Windows Python 3.12 job built and installed a wheel and source archive, passed pip requirement
checks and CLI help, and passed supported scans using both installed formats.

These package checks apply to the artifacts built in that GitHub workflow. They do not verify the
separately built ArtVault release artifacts. Exact artifact hashes and ArtVault canary status are
maintained in the existing release evidence ledger; canaries apply only to the exact bytes tested.
No public package or GitHub release has been made.

## 2026-11-02 — current Windows fix and runner admission

Commit `7c359b8dff3f721d3ba43b06b42129a3f8fc3fc6` contains the Windows filesystem-identity
SQLite fix. The focused ArtVault suite for `test_windows_supported_path.py`,
`test_navigation_inventory.py`, and `test_archaeology_mapper.py` passed **59 tests**. This is
targeted local evidence, not a full-suite result.

GitHub Actions run [41385898165](https://github.com/Pepstee/giga-archaeology/actions/runs/41385898165)
tested this commit. Both attempts ended with all 12 matrix jobs failing. On attempt 2, the job
records had empty runner names and no steps; each job completed within seconds. The log endpoint
returned `404 BlobNotFound`, and the run had no uploaded artifacts. GitHub blocked runner startup before any test step; no code-level result is available.

The previously canaried source archive SHA-256
`f2409348cba4156135de0136ecf3974a1e383ac666e826b7e41ab3ecf0976ccd` is historical and is not
available in the current ArtVault artifact locations. The current ArtVault sdist SHA-256 is
`4b68815dbe5372a13f0079fa6793625b8640e89b84480bb533014e7bd808417d`; it has not received an
authorized exact-hash install canary and is not cleared for release. Earlier canary evidence
remains scoped to its recorded bytes. No build, full-suite run, macOS/Windows artifact install,
public package, or GitHub release is verified by this entry.


## 2026-11-02 - Full local Linux suite and current hosted-run confirmation

The full source-tree suite passed **444 tests, 1 skipped, and 2 subtests** in 91.21 seconds on
ArtVault Linux x86_64 with CPython 3.12.3, at source commit
734a16957fb1b77b829dce031e614bb9bf84c59d. This run used PYTHONDONTWRITEBYTECODE=1 and
pytest's cache provider was disabled. It is Linux-only evidence; the full macOS and Windows suites
remain unverified.

GitHub Actions run [41387954350](https://github.com/Pepstee/giga-archaeology/actions/runs/41387954350)
was a push run for the same source commit. All 12 jobs completed as failures before any job steps
ran; the job API exposed no steps and a sampled job had an empty step list. No hosted test result is
claimed. The run is consistent with the runner-admission restriction recorded for the prior hosted
attempts. It does not establish a code-level test failure.

No current ArtVault wheel or source archive install canary is claimed by this entry. The October 31
canary remains scoped to its exact historical bytes. No public package or GitHub release has been
made.
