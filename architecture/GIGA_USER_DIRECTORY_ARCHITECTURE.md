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
