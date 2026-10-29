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

[provider-specific account diagnostic removed]

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

[provider-specific account diagnostic removed]


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

The current canonical source is commit `9020c1ceece54438900e2904d929a292834c73d3` (tree `13cac253d1272beac0a094c2b033b176fda10781`). Its full test suite passed on ArtVault Linux x86_64 with Python 3.12.3: **423 passed, 1 skipped, and 2 subtests passed** in 74.95 seconds. The skip is the Darwin sandbox-profile test, which does not apply on Linux.

The current source built a wheel and source archive with build 1.6.1 using the canonical custom backend. Each artifact installed into the existing ArtVault project test environment, `pip check` found no broken requirements, the CLI help command succeeded, and the supported-scan canary passed against the installed artifact (1 passed for each format). The wheel contains the MIT licence and excludes the source-only quickstart; the source archive contains the licence, quickstart and custom build backend. Artifact hashes and exact sizes are in `evidence/release-artifacts/0.1.3b3.json` under `latest_candidate_validation_20261029_9020c1c`.

[provider-specific account diagnostic removed]

The current operational Graphify index contains 2,554 nodes. Its manifest includes the changed workflow and test file, but it does not bind the index to a source commit. The index remains untracked operational output and is not treated as a release artifact. The package version is still 0.1.3b3; these builds are not for distribution. No public release has been made.
