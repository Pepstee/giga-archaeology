# Offer Accelerator integration assessment

**Date:** 22 July 2026  
**Source:** `The Offer Accelerator Toolkit (4) (1).pdf` (74 pages; internal licensed copy)  
**Related Codex task:** `Track three active projects` (`019f7a0d-e71b-7a52-b5cd-ca3198e10bcc`)  
**Decision:** selectively adopt the workflow structure; do not adopt the prompts as authorities.

## Executive verdict

The PDF is useful as a stage-completeness checklist. It confirms five career-workflow assets:

1. achievement repository and reusable STAR stories;
2. vacancy-tailored application documents and answers;
3. company/role interview dossier;
4. compensation research and negotiation preparation;
5. holistic offer comparison.

Giga-user and JAA already have a stronger design for stages 2 and much of stage 3: evidence IDs,
requirement-to-evidence mapping, eligibility gates, exact artefact hashes, bounded Humanizer edits,
manual release and submission receipts. The PDF contributes most at stages 1, 3, 4 and 5.

## Authority boundary

The PDF is a methodology source, not candidate evidence. Its examples, claims, salary figures and
sample metrics must never enter the candidate ledger. Its copy-and-paste prompts are advisory and
must not override giga-user's truth, privacy, eligibility, evidence, release or receipt gates.

The document is visibly licensed to the operator's email address. Use it internally; do not
republish or distribute the PDF or reproduce its prompt text as a public product.

## Combined operating model

```text
Approved evidence ledger
  -> achievement candidates
  -> operator-ratified achievement repository + STAR bank
  -> Market Aligner ranked opportunity
  -> live/eligibility/legitimacy gate
  -> account research + requirement-to-evidence matrix
  -> CV / optional letter / form answers
  -> bounded Humanizer diff
  -> truth + ATS + consistency revalidation
  -> manual submission + exact receipt
  -> interview dossier + STAR retrieval
  -> offer + negotiation record
  -> offer evaluation against explicit priorities
  -> outcome events returned to JAA
```

## What to adopt

| PDF component | Decision | Correct giga-user implementation |
|---|---|---|
| Achievement Repository | Adopt | A structured view over approved claims and evidence, retaining source IDs and contribution boundaries. |
| Quantification questions | Adopt cautiously | Ask for missing metrics, but preserve `unknown`; qualitative outcomes beat invented numbers. |
| Five or six STAR stories | Adopt | Store reusable scenario records with situation/task/action/result, evidence IDs, competency tags, role narratives and operator approval. |
| Tailored resume | Already covered | Continue requirement-to-evidence planning and UK CV construction through `resume-cover-letter`. |
| Cover letter for every role | Reject | Write one only when required or when company-specific evidence provides expected value. |
| Application answers | Adopt | Generate from the same locked approved-claim set and retain the exact submitted answer. |
| Networking/follow-up templates | Conditional | Use only when a real strategy calls for outreach; never auto-send in the manual bridge. |
| Interview closer | Adopt and strengthen | Account research produces a cited company/team/role dossier; retrieve only approved STAR evidence and identify unknowns explicitly. |
| Negotiation navigator | Adopt later | Create compensation evidence, target, walk-away threshold and non-salary priorities only when salary is asked or an offer exists. Use current UK data, not sample ranges. |
| Offer evaluator | Adopt later | Compare written offers using explicit operator weights and uncertainty, preserving objective fields separately from subjective judgement. |
| VA-based application volume | Reject for now | It conflicts with the current training cohort, exact-claim control and receipt discipline. Reconsider only behind certified JAA release controls. |

## Additions from the related Codex task

- Begin with ranks 15–20 as genuine training applications, not the strongest roles.
- Promote to ranks 10–14 after two clean submissions and ranks 1–9 after three clean
  submissions across at least two application surfaces.
- The current planned sequence is Freelancerprox, Zscaler and Graphcore, subject to live,
  legitimacy, eligibility and genuine-interest checks.
- Humanizer is a bounded final style critic, followed by fact and ATS revalidation.
- LinkedIn must be repositioned from sales/education toward an evidence-supported early-career
  AI automation and systems profile; the other task is still preparing the publish-ready pack.
- Excellence Exalted Limited can support a truthful Founder & Director / Software and Automation
  Builder narrative. Internally commissioned company work remains internal product work until
  independent customers, users or outcomes exist.
- One deployed teaching-operations platform is stronger proof than three disconnected demo
  projects: website and lead capture, teacher/learner workflow, lesson/homework/feedback tooling,
  and administration automation with measured real use.

## New data objects worth adding to JAA's planned schema

1. `achievement_record`: approved claim IDs, evidence IDs, role narrative, safe wording, metrics
   with source/status, contribution boundary and approval state.
2. `star_scenario`: situation, task, actions, results, evidence IDs, competency tags, suitable
   question tags, variants, approval state and last-practised date.
3. `interview_dossier`: vacancy/research snapshot hashes, likely questions, selected scenario IDs,
   cited company facts, candidate questions and unresolved unknowns.
4. `negotiation_case`: written offer hash, current-market sources and dates, target/walk-away
   values, negotiable components, communications and final terms.
5. `offer_evaluation`: objective compensation fields, explicit preference weights, uncertainty,
   deal-breakers, recommendation and operator decision.

These should extend JAA's canonical event/evidence model, not become a second mutable career
database inside giga-user.

## Immediate use

Before the first training application, build a small approved achievement repository and three to
five evidence-backed STAR scenarios from existing project and employment evidence. Do not wait for
a perfect lifelong repository. The first application and interview cycle should expose missing
facts, metrics and scenario coverage; feed those gaps back through the evidence-approval route.

The PDF therefore improves the plan, but does not replace it. It supplies missing lifecycle stages
around the existing evidence-first compiler.
