# Developer beta validation — 0.1.3b3

The mapping canary and regression results below were established on 0.1.3b1. Version 0.1.3b2 added the operator-selected MIT licence and packaging metadata. Version 0.1.3b3 fixes a SQLite URI compatibility issue and makes the contributor test setup explicit.

This is the release-specific evidence summary. Installation and supported scope are in README.md;
historical ownership/identity evidence remains in IDENTITY_MIGRATION.md.

## Additional verification for 0.1.3b3

- On the registered ArtVault Linux host, the full suite passed on Python 3.11, 3.12, 3.13 and 3.14: 375 passed, 1 skipped, 2 subtests passed on each interpreter.
- The Python 3.11 run covers the SQLite URI compatibility fix.
- The 0.1.3b3 wheel built with pip and the source archive built with the PEP 517 frontend from the registered canonical source. The wheel installed, `pip check` was clean, and `giga-archaeology --help` succeeded. Wheel SHA-256: `4accc4bc028e76ad86e1627b57f91d88a74ceab5c4fac25bf0c3a2a78c784b54`; source archive SHA-256: `502ed029eae0c302c403d93894febd8189d73b63ddf39b2997c51ed8593a2cd4`. The source archive was not extracted into another project tree.
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

The existing source graph was rebuilt with Graphify's deterministic Python AST extractor from
the registered canonical source directory, without another project checkout.
It covers 42 Python source files, 1274 nodes and 5362 edges, including the
packaging backend. Paths are repository-relative and every input has a SHA-256 in manifest.json.
Graph SHA-256: `7f57155d04e5f9ddd61fd19f65d8d6d0edd7d0b1c6e6ada39ce8e6dac48bd68d`.
Manifest SHA-256: `c6ac4fc2e3e01ee139fb41c1a7205e54922b82701531e413e5da9934112e1c31`.
The previously mismatched source files are included with their current hashes.
Markdown prose, runtime behaviour and semantic extraction remain outside this structural graph.
No model calls were used for graph generation.

## Release boundary

The narrow Python mapping beta is technically verified within the scope above. The operator selected MIT, supplied in LICENSE; public distribution has not been performed. Runtime installation on
ArtVault is a separate action; source synchronisation does not imply services were upgraded.

## MIT packaging verification

Version 0.1.3b2 includes identical MIT text in the source archive, wheel and prepared metadata. Licence-Expression and Licence-File metadata, wheel RECORD hashes and repeat-build identity were checked. Mapper source is unchanged from the verified 0.1.3b1 canary.
