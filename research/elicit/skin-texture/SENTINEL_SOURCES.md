# Sentinel-source coverage check

Status: **preliminary protocol validation, not campaign acquisition and not a treatment
ranking**.

These sources were found through direct PubMed/Cochrane discovery only to test whether
`CAMPAIGN.json` covers the major evidence families and contested claims. They have not yet been
imported into the scientific-evidence ledger, checked against full text, or assigned a
`giga.scientific-appraisal.v1` record.

## Photoaging and texture

- A 2025 systematic review and meta-analysis of eight randomised trials (1,361 participants)
  reports improvement in fine and coarse photodamage wrinkles with topical tretinoin versus
  vehicle: <https://pubmed.ncbi.nlm.nih.gov/41236273/>.
- A 2024 systematic review comparing tretinoin with other topical agents describes tretinoin as
  the reference treatment while emphasizing poor tolerability and generally weak or biased
  comparator evidence: <https://pubmed.ncbi.nlm.nih.gov/39348007/>.
- A 2022 meta-analysis comparing ablative and non-ablative laser rejuvenation found only small
  samples and no clear efficacy or safety superiority: <https://pubmed.ncbi.nlm.nih.gov/35107665/>.
- Recent systematic reviews report promising radiofrequency-microneedling outcomes but also
  major device/parameter heterogeneity and relevant manufacturer affiliations:
  <https://pubmed.ncbi.nlm.nih.gov/41947517/> and
  <https://pubmed.ncbi.nlm.nih.gov/42047762/>.

Coverage consequence: the campaign must extract concentration/device parameters, objective
outcomes, tolerability, phototype, conflicts and durability rather than treating each modality as
one uniform intervention.

## Atrophic acne scars

- A 2024 meta-analysis directly compares fractional CO2 with Er:YAG laser:
  <https://pubmed.ncbi.nlm.nih.gov/38733085/>.
- A systematic review of non-energy techniques separates ice-pick, rolling and boxcar scars and
  covers subcision, needling, fillers and peels:
  <https://pubmed.ncbi.nlm.nih.gov/29799567/>.
- A clinical-trial review focuses on subcision and combination approaches:
  <https://pubmed.ncbi.nlm.nih.gov/36315903/>.
- A 2020 meta-analysis evaluates PRP as an adjunct rather than silently crediting the underlying
  needling or subcision procedure to PRP: <https://pubmed.ncbi.nlm.nih.gov/32061047/>.

Coverage consequence: scar subtype, tethering and combination attribution are mandatory
extraction fields.

## Hypertrophic scars and keloids

- International recommendations emphasize multimodal algorithms and earlier combination
  treatment rather than a single universal intervention:
  <https://pubmed.ncbi.nlm.nih.gov/25068544/>.
- A 2024 network meta-analysis compares drug interventions across 20 randomised trials and 1,114
  participants: <https://pubmed.ncbi.nlm.nih.gov/38285997/>.
- A 2024 laser network meta-analysis includes 18 studies and highlights combination treatment,
  while different scar characteristics respond differently:
  <https://pubmed.ncbi.nlm.nih.gov/38760539/>.
- Cochrane reviews show why common recommendations such as silicone and laser therapy still
  require certainty and bias appraisal:
  <https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD013878.pub2/full> and
  <https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD011642.pub2/full>.

Coverage consequence: recurrence, symptom relief, scar type, location and follow-up length are
primary outcomes, not footnotes.

## Contested and emerging claims

- Multiple reviews report positive pooled results for oral collagen, but a 2025 meta-analysis
  found no benefit in high-quality or non-industry-funded subgroups and concluded that current
  clinical evidence does not support its use for preventing or treating skin aging:
  <https://pubmed.ncbi.nlm.nih.gov/40324552/>.
- A 2026 review of 25 collagen trials reports frequent positive outcomes but rates the majority
  at high risk of bias: <https://pubmed.ncbi.nlm.nih.gov/42342959/>.
- A recent exosome review reports promising signals while calling for larger, standardized,
  longer-term trials: <https://pubmed.ncbi.nlm.nih.gov/41912205/>.

Coverage consequence: funding, trial quality, preregistration, product composition, regulatory
status and clinical-versus-surrogate outcomes must be extracted before classifying a claim as
effective or a misconception.

## Protocol changes produced by this check

- Added an explicit non-industry/high-quality collagen query.
- Separated PRP adjunct effects from the base procedure.
- Required device settings and manufacturer conflicts for energy-based treatments.
- Required scar phenotype and tethering for atrophic-scar comparisons.
- Made recurrence mandatory for keloids.
- Added `evidence_conflicted`, `surrogate_only` and `transient_not_remodelling` misconception
  classes.
