# External-proof compiler contract

## Scope

Compile approved, source-linked claims into three local draft artefacts:

- a case study;
- a structured technical report;
- a presentation outline.

The compiler is deterministic and does not call a model. It has no publication, messaging,
application or other external-action authority.

## Input

The JSON manifest must declare:

- `schema_version: "1.0"`;
- a stable `slug`, title and summary;
- `mode: "draft"` and `authority_level: "A1"`;
- claims with unique IDs, statements, kinds and exact evidence needles;
- report sections and presentation slides that reference only declared claim IDs.

Evidence paths are repository-relative. Every needle must occur verbatim in its source. The
compiler records the source hash and matching line number.

## Public-safety boundary

The compiler rejects evidence from private or operationally sensitive roots, including `memory/`,
`corpus/`, Market Aligner data, raw SkillTree capture, `.env` files and private state. It also
rejects common secret, credential, email-address and telephone-number patterns in public claims.

This allow-by-manifest design does not make arbitrary local files public-safe. A human still owns
release under the company or operator's name.

## Outputs

Each run writes only:

- `case-study.md`;
- `technical-report.md`;
- `presentation-outline.md`;
- `qa.json`;
- `build-manifest.json`;
- `trust-receipt.json`.

All prose claims carry their claim ID. `qa.json` records deterministic gate results.
`build-manifest.json` binds the input manifest, source hashes and output hashes.
`trust-receipt.json` points to the committed receipt in the existing GIGA trust kernel.

## State and replay

The run is appended as an event in `TwinStore`; processing follows claimed → staged → validated →
committed. Derived artefacts are registered against exact source hashes. An identical replay uses
the prior committed receipt after re-hashing the artefacts, without rewriting them.

Any source or output change causes the lineage audit to fail until a new compilation succeeds.

## Release boundary

Passing compilation means **verified local draft**, not approved publication. Publication requires
a separate human-controlled release decision and is deliberately outside this walking skeleton.

