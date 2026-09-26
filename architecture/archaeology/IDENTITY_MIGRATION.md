# GIGA Archaeology identity migration

## ArtVault quick-start

- Workspace: `/srv/artvault/projects/giga-archaeologist/workspace`
- Entry point: `/srv/artvault/projects/giga-archaeologist/.venv/bin/python /srv/artvault/projects/giga-archaeologist/workspace/modules/operations/scripts/archaeology.py --help`
- Runtime stores belong outside source; keep them under the operator's runtime-store locations, not inside the workspace tree.
- Live Codex semantic extraction is not yet configured; scanning runs without it until a separate governed setup enables it.

**Canonical product name:** GIGA Archaeology  
**Canonical Python package:** `modules.operations.archaeology`  
**Canonical command:** `modules/operations/scripts/archaeology.py` (`giga-archaeology`)

The operator renamed the mapper from *Archaeologist* to *Archaeology*. This is an identity migration
of the existing owner, not a fork, rewrite, second mapper, or new capability.

## Canonical and compatibility surfaces

- All implementation modules live under `modules/operations/archaeology/`.
- The old Python package and command contain compatibility forwarding only. They resolve to the
  canonical module objects and contain no mapping implementation.
- Current programme documentation and benchmark corpora live under `architecture/archaeology/`.
- Current launchd templates and the capability manifest reference the canonical command and source
  paths. Already-installed launchers may continue through the compatibility command until their
  next separately governed installation refresh.

## Deliberately stable legacy identifiers

The following remain unchanged because they identify already-published evidence or persisted
machine contracts rather than the current product name:

- serialized `giga.archaeologist.*` schema identifiers;
- historical reports, receipts and feeds under `architecture/archaeologist/`;
- the adopted `archaeologist-mapper` capability ID and its liveness-receipt path;
- existing private runtime-store paths and reversible-quarantine marker names.

Changing those strings would invalidate evidence, strand installed state, or silently break
consumers. New human-facing documentation must use *Archaeology*. A future wire-format version may
adopt a new namespace only through an explicit migration with backward-readable evidence.

## ArtVault component migration

The existing ArtVault owner is `/srv/artvault/projects/giga-archaeologist`. Export the reviewed
Archaeology component and its source dependencies, never the containing GIGA checkout or private
runtime stores. Keep the existing installation's Git history and evidence when updating it.

The mapper-r1 donor's scanner configuration is retained: `GIGA_ARCHAEOLOGIST_VULTURE`,
`GIGA_ARCHAEOLOGIST_JSCPD` and `GIGA_ARCHAEOLOGIST_CGC_PYTHON` override defaults. Vulture and jscpd
can be discovered on PATH, and CodeGraphContext uses the current Python interpreter by default.
An explicit CLI tools root takes precedence. Scanner versions and isolation checks still apply.
The later mapper-r1 donor's `hypotheses --no-sandbox` option is retained as an explicit opt-out
from the operating-system scanner sandbox. Default CLI runs use the sandbox. This option selects
execution mode; it does not grant authority to access additional data or modify source repositories.

`scripts/graphify_codex_backend.py` preserves the distinct optional backend from donor
`d61efc9a5e037422211ccddf8f6accf78699d5a8`. No equivalent existed in the canonical script owner.
It reuses `twin_core.provider_adapters` for structured output with measured usage. Create-once
publication uses the native exclusive rename primitive on macOS and Linux and refuses replacement.
Semantic extraction requires Graphify and an available, authenticated Codex CLI. Code-only
extraction runs without Codex and records its AST backend and zero model usage. Source preservation and
offline tests do not establish live semantic extraction. The local-endpoint semantic pipeline
remains a separate supported backend.

The old navigation donor directories are absent, but their source-filtered Git refs remain:
integration `f46286915404abfe06fec5b086cf69210379d0f4` and producer freeze
`66626dfa620132955d397cdc9ddb7306476b1d2d`. Their 14 and 16 CLI commands and argument tuples are
retained in the current 50-command surface. Scoped symbol comparison found no missing definitions.
This establishes surface retention, not exhaustive behavioural equivalence of every changed body.

Python 3.11 or newer is required. Mac launchd templates are host-specific and must not be installed
on Linux. Runtime stores must be explicit, external to source, and scoped to authorised inputs.
Maintenance retention can apply changes by default, so migration verification uses disposable
stores rather than existing operator data.
