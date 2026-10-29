# Changelog

## 0.1.3b4 — release candidate refresh

- Uses a new candidate version so fresh artifacts cannot collide with historical `0.1.3b3` filenames.
- Refreshes release documentation and evidence for the current canonical source.
- Fixed build metadata version drift by deriving the artifact version from `pyproject.toml` and added regression coverage; scan behavior is unchanged.
- Publication remains pending cross-platform and installed-artifact verification.

## 0.1.3b3 — portability and clean test setup

- Added Python package keywords and repository/issue URLs to the built metadata.
- Added a Python quickstart walkthrough to the source archive with safeguards for output paths and existing data.
- Fixed SQLite URI attachment for Python 3.11 and added a dedicated test extra for repeatable contributor setup.
- Corrected the pinned Tree-sitter version assertion and documented the Linux sandbox prerequisite.
- Verified the full suite on ArtVault Linux with Python 3.11, 3.12, 3.13 and 3.14; macOS and Windows remain unverified for this candidate.
- Public publication remains separate from preparation.

## 0.1.3b2 — MIT-licensed developer beta

- Applied the operator-selected MIT licence to Archaeology. Added LICENSE because no existing licence file served this distribution.
- Included licence text in wheel and source distribution and emitted standard licence metadata.
- Third-party dependency terms are unchanged. Public publication remains separate.

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
