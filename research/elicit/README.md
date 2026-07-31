# Provider-neutral scientific evidence module

Status: **public-provider acquisition and deterministic initial-screening stack implemented,
live-control-verified and fail-closed; human screening and full-text appraisal pending**.

This module acquires scientific literature through official public APIs and preserves the
sanitised request envelope, complete raw JSON response, study metadata and later human
appraisal in an owner-only append-only ledger. It does not treat any provider, paper abstract
or LLM synthesis as recommendation authority. Elicit remains an optional legacy provider, not
a dependency.

## Boundary

```text
Research question
  -> Europe PMC + PubMed + Semantic Scholar discovery
  -> optional OpenAlex expansion
  -> direct ClinicalTrials.gov registry search
  -> Crossref DOI verification + Unpaywall lawful-OA resolution
  -> immutable third-party acquisition record
  -> source-specific human appraisal
  -> deterministic evidence/applicability gates
  -> A0 action-planning candidate
  -> separate operator/clinical decision
```

The final candidate always has:

- `authority_level: A0`;
- `recommendation_authority: false`;
- `ready_for_execution: false`.

Passing every gate means only that the evidence set is sufficiently documented to inform a
plan. It does not mean the intervention is medically appropriate or authorised.

## Files

- `twin_core/scientific_evidence.py` — hash-chained SQLite ledger, study-tier classifier and
  readiness gates.
- `twin_core/scientific_providers.py` — strict official-host adapters and provider-neutral
  projections for Europe PMC, PubMed, Semantic Scholar, OpenAlex, ClinicalTrials.gov,
  Crossref and Unpaywall.
- `twin_core/scientific_evidence_cli.py` — CLI implementation.
- `twin_core/scientific_campaign.py` — deterministic campaign validation, selection, dry-run,
  replay detection and explicit execution.
- `twin_core/scientific_query_compiler.py` — version-bound ontology compiler for PubMed,
  Europe PMC and ClinicalTrials.gov expressions.
- `twin_core/scientific_screening.py` — canonical normalization, exact deduplication,
  review-only fuzzy matching, conservative eligibility proposals, feature extraction, negative
  controls, exclusion-audit sampling and PRISMA accounting.
- `twin_core/scientific_review_state.py` — owner-only append-only human-review and
  proposal-state ledger; LLM proposals cannot change eligibility state.
- `twin_core/scientific_fulltext.py` — lawful full-text routing and hash-bound Europe PMC XML
  acquisition/extraction.
- `twin_core/scientific_saturation.py` and `twin_core/scientific_readiness.py` — distinct-snapshot
  saturation and fail-closed screening promotion gates.
- `twin_core/scientific_review_funnel.py` — the six-stage metadata → abstract → hierarchy →
  selective-full-text → condition grouping → appraisal/synthesis review funnel.
- `scripts/scientific_evidence.py` — provider-neutral repository entry point.
- `scripts/run_scientific_campaign.py` — public-provider campaign runner.
- `scripts/scientific_pipeline.py` — deterministic query compilation, screening, audit,
  full-text and state-machine entry point.
- `scripts/elicit_evidence.py` — repository entry point.
- `scripts/run_elicit_campaign.py` — optional legacy Elicit campaign runner.
- `contracts/scientific-appraisal.v1.schema.json` — strict appraisal input contract.
- `contracts/scientific-action-candidate.v1.schema.json` — non-authoritative candidate output
  contract.
- `contracts/scientific-eligibility-decisions.v1.schema.json` — human abstract-screening
  decisions bound to the exact abstract SHA-256.
- `contracts/scientific-study-extraction.v1.schema.json` — full-text population, protocol,
  comparator, outcome, effect, harms, follow-up, funding and bias extraction.
- `contracts/scientific-synthesis-signoff.v1.schema.json` — human approval bound to the exact
  comparison-matrix SHA-256.
- `tests/test_scientific_evidence.py` — offline transport, persistence, tamper, appraisal and
  safety-gate tests.

Runtime state defaults to:

```text
~/.giga/scientific-evidence.sqlite3
```

The default directory is owner-only (`0700`) and every database is made owner-only (`0600`).
API keys and contact email addresses are read from the process environment and are never
written to the ledger. Every client rejects non-official hosts. Offline imports containing
credential-shaped request fields are rejected before persistence.

## Provider setup

Europe PMC, PubMed, Semantic Scholar, ClinicalTrials.gov and Crossref work without a paid
account. The reliable default search fans out to Europe PMC and PubMed. Semantic Scholar
remains an explicit expansion provider because its unauthenticated shared pool can return
HTTP 429.

Optional configuration:

```bash
export NCBI_API_KEY="..."                 # free; raises the PubMed rate limit
export OPENALEX_API_KEY="..."             # free key; $1 daily API allowance
export SCIENTIFIC_CONTACT_EMAIL="..."      # polite Crossref/NCBI identification
export UNPAYWALL_EMAIL="..."               # required by Unpaywall
export SEMANTIC_SCHOLAR_API_KEY="..."      # optional free key
```

Never put keys or contact emails in this repository, a research question, memory file or
appraisal. Search terms leave the local machine, so omit private medical identifiers and
unnecessary personal data.

Official references:

- <https://europepmc.org/developers>
- <https://www.ncbi.nlm.nih.gov/books/NBK25497/>
- <https://www.semanticscholar.org/product/api>
- <https://developers.openalex.org/>
- <https://clinicaltrials.gov/data-api/api>
- <https://www.crossref.org/documentation/retrieve-metadata/rest-api/>
- <https://unpaywall.org/api>

## Acquire evidence

Start with a small paper search. Retractions are excluded by default.

```bash
python3 scripts/scientific_evidence.py search-papers \
  "randomized trials of resistance training frequency and hypertrophy in trained adults" \
  --type RCT \
  --max-results 10
```

Select or add providers explicitly:

```bash
python3 scripts/scientific_evidence.py search-papers \
  "topical retinoids for photoaging in adults" \
  --provider europe_pmc \
  --provider pubmed \
  --provider semantic_scholar \
  --provider openalex \
  --max-results 10
```

OpenAlex requires `OPENALEX_API_KEY`; the other three providers do not require a paid account.

Search ClinicalTrials.gov directly:

```bash
python3 scripts/scientific_evidence.py search-trials \
  "creatine supplementation cognitive outcomes adults" \
  --max-results 10
```

Verify a DOI with Crossref and resolve lawful open copies through Unpaywall:

```bash
python3 scripts/scientific_evidence.py lookup-doi \
  "10.1000/example" \
  --provider crossref \
  --provider unpaywall
```

`UNPAYWALL_EMAIL` must be configured. Resolution records only metadata and provider-declared
lawful locations; it does not bypass publisher access controls.

Elicit reports remain available only as an optional paid-provider path:

```bash
python3 scripts/scientific_evidence.py start-report \
  "What are the benefits and adverse effects of topical retinoids for photoaging in adults?"

python3 scripts/scientific_evidence.py start-review \
  research/elicit/SYSTEMATIC_REVIEW_PROTOCOL.example.json
```

Reports and systematic reviews are forced private by the adapter. The protocol must be reviewed
before the command is run; the module never creates a paid long-running review speculatively.

## Offline and locally held document import

An existing Elicit export or captured API response can be imported without an API key:

```bash
python3 scripts/scientific_evidence.py import-response \
  --endpoint search/papers \
  --request request.json \
  --response response.json \
  --observed-at 2026-07-28T12:00:00Z
```

The command returns deterministic source-record IDs. Exact replay is idempotent.

A paper already obtained lawfully can be registered without copying its full text into the
database:

```bash
python3 scripts/scientific_evidence.py import-document ~/Documents/paper.pdf \
  --title "Paper title" \
  --year 2025 \
  --doi "10.1000/example"
```

The ledger stores its filename, byte length and SHA-256 hash, not its filesystem path or
contents.

## Copyright and access boundary

The module deliberately has no Sci-Hub, Z-Library, credential-sharing, paywall-bypass or
publisher-access-circumvention adapter. Those services are not treated as citable acquisition
providers. Exhaustive lawful retrieval means:

1. Europe PMC open full text and PubMed Central links;
2. Unpaywall-declared repository and publisher open copies;
3. publisher or institutional-library access held by the operator;
4. author manuscripts and preprints at lawful repositories;
5. documents the operator already possesses lawfully, registered by hash.

Unavailable full text remains `not_obtained`; the system never silently substitutes an abstract
for full-text verification.

## Six-stage review funnel

Build the initial fail-closed review workspace from a completed screening snapshot:

```bash
python3 scripts/scientific_pipeline.py review-funnel \
  DEDUP_GROUPS.jsonl \
  ELIGIBILITY_PROPOSALS.jsonl \
  FEATURES.jsonl \
  review-funnel-output \
  --duplicate-decision-report DUPLICATE_DECISION_REPORT.json
```

This makes:

1. `METADATA_SCREENING_REPORT.json`;
2. `ABSTRACT_RETRIEVAL_QUEUE.jsonl` and `ABSTRACT_SCREENING_QUEUE.csv`;
3. `EVIDENCE_PRIORITY_QUEUE.csv`;
4. `SELECTIVE_FULLTEXT_QUEUE.jsonl`;
5. `EVIDENCE_GROUPS.json`;
6. `EVIDENCE_COMPARISON_MATRIX.jsonl` and `REVIEW_FUNNEL_READINESS.json`.

No proposed inclusion is promoted to the full-text queue until a human decision file passes
`scientific-eligibility-decisions.v1`. A decision is rejected if its recorded abstract hash
does not match the current abstract.

Retrieve every available PubMed abstract in the generated queue in official API batches of at
most 200:

```bash
python3 scripts/scientific_pipeline.py fetch-abstract-queue \
  review-funnel-output/ABSTRACT_RETRIEVAL_QUEUE.jsonl \
  review-funnel-output/PUBMED_ABSTRACTS.jsonl
```

Merge those records and deterministically recompute every feature and eligibility proposal:

```bash
python3 scripts/scientific_pipeline.py merge-abstracts \
  DEDUP_GROUPS.jsonl \
  review-funnel-output/PUBMED_ABSTRACTS.jsonl \
  SEARCH_ONTOLOGY.json \
  SEARCH_SPEC.json \
  enriched-screening
```

Existing abstracts are never overwritten. Identifier ambiguity, a conflicting existing
abstract, an empty provider response, or an unmatched PMID is preserved as a conflict for human
resolution. Any applied abstract invalidates earlier human decisions by changing the abstract
hash.

After eligibility decisions, rerun `review-funnel` with
`--eligibility-decisions`. Review guidelines and systematic reviews first, then pivotal trials
whose coverage by those reviews has been checked, followed by controlled observational safety
and durability evidence. The full paper—not its abstract—must be extracted with
`research/elicit/STUDY_EXTRACTION_TEMPLATE.json` and supplied through `--extractions`.

The funnel cannot authorise an effectiveness ranking unless duplicate decisions, eligibility,
all selected full-text extractions, risk of bias, source-located effects, harms/conflicts and a
hash-bound human synthesis sign-off all pass. Even then, it grants comparison authority only:
`recommendation_authority` remains `false`.

## Appraise each source

Search metadata remains an unverified third-party claim. Copy
`research/elicit/APPRAISAL_TEMPLATE.json`, replace the source ID and fill every field after
checking the actual paper, supporting table/figure and retraction status:

```bash
python3 scripts/scientific_evidence.py appraise appraisal.json
```

The deterministic evidence tiers are deliberately coarse:

- `T1` — guideline, systematic review or meta-analysis before risk-of-bias downgrade;
- `T2` — randomised controlled trial before downgrade;
- `T3` — controlled non-randomised, longitudinal, cohort or case-control evidence;
- `T4` — cross-sectional, case-series or mechanistic human evidence;
- `T5` — animal, in-vitro, expert-opinion or uncategorised evidence;
- `U` — unusable because critical risk of bias was recorded.

This is a sorting mechanism, not a substitute for GRADE, RoB 2, ROBINS-I or domain expertise.

## Evaluate an action-planning candidate

```bash
python3 scripts/scientific_evidence.py candidate \
  --question "Would intervention X improve outcome Y for this population?" \
  --intervention "Run a reversible, measured N-of-1 trial of X" \
  --risk-class low_risk_lifestyle \
  --source SOURCE_ID_1 \
  --source SOURCE_ID_2
```

The candidate is blocked unless all of these are true:

- every source is appraised;
- at least two independent studies are present;
- the full text and supporting locator were human-verified;
- retraction status is clear;
- harms and conflicts were assessed;
- population applicability is direct or partial;
- effect estimate and uncertainty were extracted;
- at least one `T1` or `T2` source remains;
- contradictions were absent or explicitly addressed;
- clinical candidates have recorded clinician review.

Even a passing candidate remains A0 and cannot execute.

## Inspect and audit

```bash
python3 scripts/scientific_evidence.py sources
python3 scripts/scientific_evidence.py source SOURCE_RECORD_ID
python3 scripts/scientific_evidence.py status
python3 scripts/scientific_evidence.py audit
```

`audit` recomputes request, response, source and appraisal hashes, verifies the ledger chain and
checks database permissions. SQLite triggers reject updates and deletions to the evidence tables.

## Run a multi-query campaign

Campaigns are dry-run by default. This validates every provider-specific request, reports the
maximum requested records and identifies requests already present in the ledger without
contacting any provider:

```bash
python3 scripts/run_scientific_campaign.py \
  research/elicit/skin-texture/CAMPAIGN.json \
  --phase 1
```

Live API calls require the explicit `--execute` flag. The default paper stack is Europe PMC
and PubMed; ClinicalTrials.gov is used automatically for trial queries. Add Semantic Scholar
or OpenAlex explicitly after configuring their free keys. Start with a bounded slice:

```bash
python3 scripts/run_scientific_campaign.py \
  research/elicit/skin-texture/CAMPAIGN.json \
  --phase 1 \
  --max-requests 2 \
  --execute
```

## Compile and screen without an LLM

Compile the versioned skin ontology and all 37 questions into provider-native Boolean
expressions. This command is network-free:

```bash
python3 scripts/scientific_pipeline.py compile-search \
  research/elicit/skin-texture/CAMPAIGN.json \
  research/elicit/skin-texture/SEARCH_ONTOLOGY.json \
  research/elicit/skin-texture/SEARCH_SPEC.json \
  research/elicit/skin-texture/compiled-search
```

The compiled campaign fails closed if a selected provider lacks its compiled expression. Screen
an acquired ledger deterministically:

```bash
python3 scripts/scientific_pipeline.py screen \
  ~/.giga/skin-texture-evidence.sqlite3 \
  research/elicit/skin-texture/CAMPAIGN.json \
  research/elicit/skin-texture/compiled-search/COMPILED_SEARCH_MANIFEST.json \
  research/elicit/skin-texture/SEARCH_ONTOLOGY.json \
  research/elicit/skin-texture/SEARCH_SPEC.json \
  research/elicit/skin-texture/deterministic-screening-final \
  --review-database ~/.giga/skin-texture-review-final.sqlite3
```

This stage performs no LLM or API call. It never merges a fuzzy duplicate automatically, never
makes a final human eligibility decision and never ranks treatments. Human duplicate decisions
are accepted only through the hash-bound decision template. LLM use, if explicitly added later,
is confined to the ambiguity queue: it must cite verbatim supplied spans and can only propose,
never commit, a decision.

The deterministic promotion gate combines the separately acquired negative controls with the
append-only review ledger:

```bash
python3 scripts/scientific_pipeline.py readiness \
  research/elicit/skin-texture/deterministic-screening-final/SCREENING_SUMMARY.json \
  research/elicit/skin-texture/negative-control-results-final/SCREENING_SUMMARY.json \
  --review-database ~/.giga/skin-texture-review-final.sqlite3 \
  --output research/elicit/skin-texture/deterministic-screening-final/READINESS_REPORT.json
```

It remains red until the exclusion audit, four possible-duplicate decisions, 1,755 human
eligibility decisions and genuine cumulative search-saturation evidence are complete. Even a
green screening gate cannot authorize effectiveness ranking; verified full text, structured
appraisal, synthesis and any clinical review remain separate later gates.

The later full compiled run supersedes those broad-pass counts for the active skin campaign. Its
canonical projection is
`research/elicit/skin-texture/compiled-full-results-2026-07-28-v4`: 6,108 records, all 37
questions, 4,144 candidate groups, five possible duplicate pairs, 2,248 inclusion proposals, 28
exclusion proposals and 1,868 manual reviews. See
`research/elicit/skin-texture/COMPILED_RESEARCH_RUN_2026-07-28.md`. The original broad pass and
intermediate projections remain preserved as audit evidence.

Completed requests are skipped on later runs. `--refresh` deliberately repeats them and is only
valid with `--execute`.

## Known boundary before the first live pilot

The implementation is tested against injected provider transports and official response
contracts. Until a bounded live pilot is recorded, the following are not yet claimed:

- live availability of every provider from the operator's current network;
- current OpenAlex key and allowance compatibility;
- current Semantic Scholar unauthenticated throttling behavior;
- a completed systematic review;
- full-text extraction accuracy against human review.

The first live pilot should use one bounded, low-risk question, compare provider overlap and
manually verify every projected field in a small subset before the module informs any personal
routine.
