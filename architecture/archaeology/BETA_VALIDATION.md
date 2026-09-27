# Developer beta validation — 0.1.3b2

The mapping canary and regression results below were established on 0.1.3b1.
Version 0.1.3b2 changes licensing and packaging only; mapper source is unchanged.

This is the release-specific evidence summary. Installation and supported scope are in README.md;
historical ownership/identity evidence remains in IDENTITY_MIGRATION.md.

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
