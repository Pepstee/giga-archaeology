# Compiled skin-texture research run

Date: 2026-07-28  
Campaign: `skin-texture-collagen-scars-2026`  
Search manifest SHA-256:
`78e61ab526d5d58480bcf7116a59ec3f8765dd3f5d6f02bbd60fbf5e618f2c66`  
Final deterministic projection: `compiled-full-results-2026-07-28-v4`  
Authority: evidence discovery and initial screening only

## Result

The refined version of the earlier skin-texture, collagen-stimulation, anti-aging and
scar-treatment research has been run across all 37 prespecified questions. All provider jobs
completed through Europe PMC, PubMed and ClinicalTrials.gov, all records were preserved in a new
append-only ledger, and the deterministic screening projection covers every question.

This is not yet an effectiveness ranking. The module correctly blocks conclusions until human
eligibility screening, lawful full-text appraisal and search saturation are complete.

## Acquisition

- Provider jobs planned: 71
- Provider jobs represented in the final ledger: 71
- Pending jobs after completion: 0
- Provider records: 6,108
  - Europe PMC: 2,853
  - PubMed: 2,577
  - ClinicalTrials.gov: 678
- Acquisition-ledger entries: 71
- Acquisition-ledger audit: passed
- Acquisition ledger head:
  `669e83edb1517082578753760fde659aac751d904b7a9cb7a76ac96933e6e770`
- Records mapped back to their prespecified question: 6,108/6,108
- Questions with retrieved candidates: 37/37

One PubMed response terminated early while transmitting a chunked payload. Forty-seven completed
jobs were already durable. A replay skipped them and executed only the remaining 24 jobs. This
verified recovery and idempotent resumption under a real transport interruption.

## Deterministic screening

- Retrieval records: 6,108
- Exact duplicate retrievals collapsed: 1,964
- Unique candidate groups: 4,144
- Multi-provider groups: 320
- Groups retrieved by more than one question: 1,156
- Possible near-duplicate pairs: 5, none automatically merged
- Proposed inclusion: 2,248
- Manual review: 1,868
- Proposed exclusion: 28
- Lawful full-text plans: 4,116
- Open-access candidate groups: 1,133
- Groups with a PMCID: 1,102
- Review-ledger events: 12,432
- Review-ledger audit: passed
- LLM calls and proposals: 0
- Exact artifact-tree replay: passed
- Final artifact-tree SHA-256:
  `e8890ea6aef04acd1fc146e54de0c258123923499f00d8e8560892f3d7b8c676`

The 28 exclusion proposals are limited to:

- 22 explicitly titled animal studies;
- four retracted studies;
- two explicitly laboratory-only studies.

The exclusion sample contains 11 records and still requires human verification.

## Metadata-level evidence landscape

These are provider metadata classifications, not verified study appraisals:

| Design bucket | Candidate groups |
|---|---:|
| Primary or other | 1,576 |
| Randomized controlled trial | 1,209 |
| Nonsystematic review | 449 |
| Systematic review | 283 |
| Meta-analysis | 210 |
| Clinical trial | 127 |
| Guideline | 87 |
| Cohort or longitudinal | 74 |
| Protocol | 59 |
| Case series | 46 |
| Controlled trial | 21 |
| Case-control | 3 |

Major ontology families found in title/abstract metadata:

| Intervention family | Candidate groups |
|---|---:|
| Fractional lasers | 322 |
| Microneedling/radiofrequency | 298 |
| Scar laser/cryotherapy | 288 |
| Topical retinoids | 224 |
| Light/ultrasound/plasma | 218 |
| Peels/dermabrasion | 208 |
| Biostimulators/fillers | 168 |
| Other topical agents | 160 |
| Subcision/fillers | 157 |
| Photoprotection | 154 |
| Intralesional scar drugs | 151 |
| Silicone/pressure | 147 |
| Regenerative treatments | 128 |
| Keloid surgery/adjuvants | 120 |
| TCA/punch procedures | 94 |
| Isotretinoin procedural timing | 87 |
| Combination scar treatment | 61 |
| Oral collagen | 49 |
| Vitamin E/onion products | 35 |
| Home dermarolling | 6 |
| Facial manipulation/exercise | 5 |
| Topical collagen | 3 |
| Pore-treatment claims | 1 |

Large family counts show search coverage, not efficacy. Sparse counts can mean genuinely thin
research, restrictive terminology or incomplete indexing; they do not prove ineffectiveness.

## Real-data defects found and corrected

The run exercised the safety gates against real provider data and found three projection defects.
Earlier projections remain preserved as audit traces.

1. PubMed sometimes applies `Letter` or another editorial type alongside a genuine clinical-study
   or systematic-review description. Publication type alone no longer causes automatic exclusion;
   conflicting cases go to manual review.
2. “Porcine collagen filler” described intervention material in a human scar comparison and was
   mistaken for an animal study. Bare `porcine` no longer triggers exclusion; explicit porcine
   model/skin/wound language still does.
3. Two overview searches shared expressions with deeper primary-trial searches. Query attribution
   now binds provider, expression and request limit, preserving all 37 question identities.
4. Negative-control-only ontology labels overlapped real microneedling terminology. Control-only
   concepts are now excluded from main intervention-family and saturation accounting.

## Current readiness

The final readiness report is correctly red:

- acquisition mapping: passed;
- acquisition/review ledger integrity: passed;
- negative controls: passed, 38/38 excluded;
- possible duplicates resolved: pending, five pairs;
- sampled exclusion audit: pending, 11 records;
- human eligibility decisions: pending;
- search saturation: pending.

`full_text_appraisal_complete`, `scientific_synthesis_complete` and
`effectiveness_ranking_authorised` remain `false`.

## Correct next stage

The dominant ambiguity is missing metadata: 1,772 manual-review records have no abstract. The
correct sequence is:

1. enrich missing abstracts and lawful full-text availability through official sources;
2. resolve the five near-duplicate pairs;
3. complete the 11-record exclusion audit;
4. perform final human eligibility screening, using deterministic priority order;
5. execute targeted amendment searches and prove two consecutive low-yield saturation passes;
6. retrieve and appraise decisive full texts;
7. extract comparable effects, harms, durability, phototype applicability and conflicts;
8. synthesize separately for photoaging, atrophic scars, hypertrophic scars and keloids.

No current artifact should be interpreted as personal medical advice or as a treatment league
table.
