# Changelog

## 0.1.3b1 — developer beta candidate

- Documented installation, the supported deterministic Python path and compact-context consumption.
- Made Giga capability validation an optional integration; repositories containing capability manifests
  refuse mapping when that validator is unavailable. Unrelated Python repositories no longer need Giga.
- Added regression checks for absent and broken optional integration.
- Added a real-repository verification against pinned ItsDangerous source and refreshed the structural source graph.
- Public publication and licence admission remain separate from preparation.

## 0.1.2

- Declared the four required parser packages and emitted them in wheel metadata.
- Verified a fresh installation and synthetic scan without manual parser installation.

## 0.1.1

- Internal portable Archaeology package; clean-install parser dependencies were incomplete.
