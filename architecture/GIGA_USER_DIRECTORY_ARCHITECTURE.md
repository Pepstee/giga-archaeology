# Giga-user directory architecture

## Decision

`giga-user` is a programme workspace, not a single application repository. Its
top level is therefore organised by ownership zone while stable code and
evidence paths remain in place.

The machine-readable contract is `architecture/root-layout.v1.json`. Run
`python3 scripts/audit_root_layout.py` to find unclassified top-level entries.

## Ownership zones

| Zone | Purpose | Examples |
|---|---|---|
| Authority | Programme constitution and briefs | `00_MASTER.md`, `CHARTER.md` |
| Platform | Shared code, contracts, architecture and tests | `twin_core/`, `scripts/`, `tests/` |
| Knowledge | Memory, evidence, research and reports | `memory/`, `corpus/`, `research/` |
| Projects | Outcomes with their own lifecycle | `life-logging/`, `projects/land-investment-monitor/` |
| External workspaces | Independent or imported repositories | `upstreams/`, `market-aligner/` |
| Runtime and delivery | Generated output, migration and transfer state | `outputs/`, `staging/` |
| Intake | New unclassified material awaiting ownership | `intake/` |

## Project shape

New projects should use this shape where the layers are needed:

```text
<project>/
├── README.md
├── <subproject>/
│   ├── README.md
│   ├── config/
│   ├── scripts/
│   ├── files/ or recordings/
│   ├── processing/
│   ├── outputs/
│   └── state/
└── docs/
```

Raw private inputs, transient processing data, generated outputs and runtime
state must be ignored explicitly. Source, configuration, schemas and concise
manifests remain tracked.

## Migration rules

1. New loose files land in `intake/`, never directly in the root.
2. Assign an owner and destination before promoting intake material.
3. Do not move a live path merely for visual uniformity. First migrate its
   imports, absolute references, schedules, tests and provenance records.
4. Historical receipts and hashes are evidence. Preserve their recorded paths;
   record a new migration receipt instead of rewriting history.
5. The Gigabyte laptop is a release target. Dubbing Studio remains local until
   full certification or an explicit maturity decision, then is published to
   GitHub and deployed from that release.

## Current transition

Several root artifacts are explicit legacy exceptions because active reports,
tests or lineage records still reference them. They are visible technical debt,
not the precedent for new files. The audit reports them separately.

Direct project paths such as `life-logging/` and
`job-application-automation/` remain stable. `projects/registry.v1.json`
provides one canonical catalogue without forcing breaking moves.

## Recovered control package

The root `pyproject.toml` reuses the PEP 517 backend from the
`research-module-web-acquisition` worktree at `3f40755b4bb8ce990f5e84f8030a7d5c147fa897`.
`modules/platform/packaging/giga_build_backend.py` adapts that owner to the current
layout without moving the source tree. It packages an explicit list of Python
source files and rejects symlinks. It does not traverse or package the personal
corpus, runtime data, credentials, or historical reports.

Build with `python -m pip wheel --no-deps --no-build-isolation . --wheel-dir DIST`.
Install the resulting wheel into a virtual environment. The package exposes
`giga-twin`, `giga-sovereignty`, and `giga-operator-status`; operational commands
still need their explicit input files and workspace paths. Use an explicit
temporary `--database` when checking `giga-twin init`.

This increment restores installation of the current code. It does not claim that
all donor capabilities, governance assets, or the complete installable folder
have been consolidated or migrated. The donor's daily-checkpoint command and
optional research dependencies remain outside this initial package until their
implementations are reconciled. `tests/test_root_package.py` verifies reproducible
archives, source-distribution rebuilds, clean installation, command loading, and
initialisation of an empty SQLite store.
