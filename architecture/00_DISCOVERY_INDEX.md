# GIGA architecture discovery index

This directory is the durable hand-off for the three-pass reassessment requested on
2026-07-20. It is intentionally separate from `corpus/` and its exports.

## Reading routes

| Time available | Read | Purpose |
|---|---|---|
| 5 minutes | `01_LIGHT_MAP.md` | Boundaries, major stores, live processes and immediate cautions |
| 20–30 minutes | `02_MEDIUM_MAP.md` | Module responsibilities and end-to-end data flows |
| 60+ minutes | `03_DEEP_MAP.md` | Code-level behaviour, schemas, failure modes and verified invariants |
| Historical provenance | `../retrospectives/gpt2_2026-2023-03_to_2026-07-forward-ledger.md` | Full month-by-month review of the separate ChatGPT account, including authorship and safety boundaries |
| Designing the twin | `04_VIRTUAL_TWIN_TARGET.md` | Target capabilities, authority model and success criteria |
| Implementing | `05_TRANSITION_ROADMAP.md` | Current-to-target gaps, dependency order and acceptance gates |

## Interpretation law

The three maps are cumulative. The light map is not wrong but deliberately compressed; the
medium map adds operational detail; the deep map is authoritative where they differ. Every
claim should be traceable to a file, executable check, database inspection or live-process
observation. The existing Graphify graph is an input, never the sole source of truth.

## Scope guard

- Corpus exports and archives are read-only source evidence. No discovery or implementation
  step may edit, delete, normalise in place or repack them.
- Derived artefacts go in new files/directories.
- `market-aligner/`, `market-aligner-artiom/` and the actively running external Korea Job
  Scraper are read-only for this programme while commercial-product development continues.
