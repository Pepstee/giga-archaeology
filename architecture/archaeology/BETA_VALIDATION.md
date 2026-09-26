# Developer beta validation — 0.1.3b1

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
canonical Git blobs and the reviewed candidate patch, without another project checkout.
It covers 42 Python source files, 1274 nodes and 5360 edges, including the
packaging backend. Paths are repository-relative and every input has a SHA-256 in manifest.json.
Graph SHA-256: `032616e4cd027370a85a94c55eaa540218e3d40327ebd0fab1de4ad430bc59a5`.
Manifest SHA-256: `8561dd23a0e08efe08a7286fbefe9cbc88d907375597a697e5bf93871ed67398`.
The previously mismatched source files are included with their current hashes.
Markdown prose, runtime behaviour and semantic extraction remain outside this structural graph.
No model calls were used for graph generation.

## Release boundary

The narrow Python mapping beta is technically verified within the scope above. Licence selection
is awaiting the operator and public distribution has not been performed. Runtime installation on
ArtVault is a separate action; source synchronisation does not imply services were upgraded.
