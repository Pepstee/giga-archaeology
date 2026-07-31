# Deterministic scientific pipeline implementation report

Date: 2026-07-28  
Scope: initial scientific-list processing for the skin-texture, collagen-stimulation,
photoaging and scar-treatment campaign  
Authority: A0 evidence preparation only

## Outcome

The requested deterministic front end is implemented. Query construction, normalization,
provider mapping, exact deduplication, fuzzy-pair triage, eligibility proposals, feature
extraction, prioritization, negative controls, PRISMA accounting, exclusion sampling, lawful
full-text routing, state transitions, saturation checks and readiness checks execute without an
LLM.

The system deliberately does not make treatment conclusions. Human screening, verified full-text
appraisal, effect extraction, risk-of-bias assessment and synthesis remain mandatory before any
effectiveness comparison.

## Implemented controls

1. **Versioned search ontology and query compiler**
   - All 37 protocol questions and two negative controls are bound to explicit condition,
     intervention and outcome concepts.
   - PubMed, Europe PMC and ClinicalTrials.gov receive provider-native expressions.
   - Compiled campaigns fail closed if a selected provider expression is absent.
   - The compiler is network-free and content-hashes its manifest.

2. **Canonical record projection**
   - HTML decoding, Unicode NFKC normalization, whitespace normalization and strict identifier
     validation are deterministic.
   - Raw provider provenance and acquisition identifiers are retained.
   - Unmapped records are reported and block readiness.

3. **Duplicate handling**
   - DOI, PMID, PMCID, NCT identifier and normalized-title/year matches may collapse
     deterministically.
   - Similar-title pairs are suggestions only and are never automatically merged.
   - Human pair decisions bind the exact candidate-pair set, are append-only in the review
     ledger and require explicit evidence.

4. **Eligibility and list processing**
   - Retractions, explicit animal/laboratory-only studies, provider-typed non-research
     publications and unrelated records receive reason-coded proposals.
   - Compiled-query retrieval with incomplete visible metadata goes to manual review rather than
     automatic exclusion.
   - Ontology hits retain exact title/abstract spans.
   - Study design, named scales, sample-size mentions, follow-up, phototype and funding/conflict
     mentions are extracted deterministically.

5. **LLM containment**
   - The default pipeline invokes no LLM.
   - Any future LLM receives only ambiguity-queue records.
   - Its strict contract requires supplied verbatim evidence spans.
   - An LLM proposal is stored separately and cannot change a review state.

6. **Full-text boundary**
   - The route order is Europe PMC XML, an existing lawful open URL, Unpaywall, publisher DOI,
     institutional library, then author request.
   - Paywall circumvention is forbidden.
   - Explicit Europe PMC downloads validate the official host, response size and XML and reject
     DTD/entity declarations.
   - Extraction binds every section to the source-file hash and does not mark it appraised.

7. **State and promotion gates**
   - Review state is held in an owner-only append-only SQLite ledger with actor-specific legal
     transitions and a hash chain.
   - Negative controls must be excluded.
   - A deterministic false-exclusion sample requires complete human decisions and a configured
     error threshold.
   - Search saturation requires three distinct cumulative snapshots and two consecutive passes
     with no new intervention family and less than 1% new retained candidates.
   - Replaying the same snapshot cannot count toward saturation.
   - Screening readiness fails closed and never authorizes treatment ranking.

## Real-data verification

### Broad sensitivity ledger

- Provider records: 1,968
- Acquisition entries: 71
- Mapped records: 1,968
- Candidate groups after exact deduplication: 1,755
- Exact duplicate retrievals collapsed: 213
- Possible fuzzy duplicate pairs requiring human decisions: 4
- Proposed inclusion: 130
- Proposed exclusion: 1,116
- Manual review: 509
- Lawful full-text plans: 639
- Append-only review events: 5,265
- Review-ledger audit: passed
- LLM proposals: 0

An exact rerun before adding the separate readiness report produced the same artifact-tree SHA-256:
`12f8d010fe297bd507f9c95957e1eadb3de30bc5277c820e0fa53ac9d0ec871a`.

### Compiled-query pilot

- Provider records: 400
- Candidate groups: 385
- Proposed inclusion: 209
- Manual review: 170
- Proposed exclusion: 6

The six exclusions are provider-typed comments, editorials or letters. The rule correction moved
compiled-query records without sufficient visible metadata evidence into manual review, reducing
automatic exclusions from the earlier 99 to six.

### Negative controls

- Provider records: 40
- Candidate groups: 38
- Proposed exclusion: 38
- Failures: 0
- Promotion gate: passed

## Current fail-closed result

`deterministic-screening-final/READINESS_REPORT.json` correctly reports
`screening_ready: false`. The following work cannot be manufactured by automation:

- resolve four possible duplicate pairs;
- complete and validate the false-exclusion audit sample;
- record final human eligibility decisions for all 1,755 groups;
- execute cumulative refined searches and prove the two-pass saturation rule;
- obtain and verify decisive full texts;
- complete structured risk-of-bias, effect, harm, durability, applicability and conflict
  appraisal;
- synthesize separately by condition and outcome.

`full_text_appraisal_complete`, `scientific_synthesis_complete` and
`effectiveness_ranking_authorised` all remain false.

## Verification

- Static compilation: passed
- Ruff checks: passed
- Focused scientific tests: 59 passed
- Full owned test suite: 179 passed
- Real negative-control run: passed
- Real compiled-query pilot: passed
- Real broad-pass deterministic replay: byte-identical
- Mutation coverage includes append-only ledger tampering, replayed saturation snapshots,
  invalid actor transitions, invented LLM evidence spans, credential-shaped persistence,
  malicious XML entity declarations and malformed duplicate decisions.

