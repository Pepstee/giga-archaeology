# Fable adjudication brief — DFI-05 post-Codex repair overflow

You are the architecture authority. Use only the supplied evidence. Do not use
tools, browse, spawn subagents, or inspect repositories.

Return a concise ruling with:

1. `GO_DELETION_REFRACTOR`, `SPLIT_REQUIRED`, `CEILING_REVIEW`, or `NO_GO`;
2. whether the current 521-line dirty state may be retained only as a temporary
   repair source while a sole writer deletion-refactors it;
3. exact non-negotiable acceptance conditions and line accounting;
4. whether cohort rate evaluation belongs in DFI-05 or a later stage, given the
   original work order says DFI-05 prepares/tests the feeder and seal but does
   not claim the activation soak;
5. the safest next single-writer sequence.

## Existing ruling

You previously raised DFI-05 from 250 to 350 net production lines and ruled:

- finish at or below 350 against `dcf5097`; 351 stops for re-adjudication;
- one stage must include host admission, repository claim gating,
  stale/conflict checks, host-issued certificates, hard-failure
  classification, and bounded task-manager proposal validation;
- default off; no config, side store, cache, activation, STOP clearing, or JAA;
- reuse existing `task_created`, scheduler JSONL, fallback v2, scope/compiler
  records, and task-manager parser;
- DFI-15 was reduced to 150 so the total programme cap remained 3,330.

## Preserved candidate before review

- base: `dcf509753845552a906a5a1a04fcdad754cb6471`
- patch: `e7f7d438d33133c7deebd7894f70cba33df340bac3780603c2501a32a007b125`
- net production: 348 (358 additions, 10 deletions)
- focused/affected evidence: 14 + 86 tests passed
- Ruff and diff hygiene passed
- Sonnet reported coherent; no edits.

## Independent Codex rejection

Codex found four high-severity authority gaps:

1. cohort ID/seal was only hash-shaped; admission did not validate the
   canonical seal, reject pre-seal/foreign cohort episodes, or implement
   denominator/minimum/ceiling semantics;
2. task manager validated only fallback schema before model invocation, so
   stale/cross-parent/cross-project/cross-epoch/over-broad authority could
   reach the model;
3. repository claim checked outer parent but not embedded fallback parent,
   project, or intent receipt;
4. replay verification ignored `task_contract_hash`, did not recompute slice
   hash, and did not bind instruction registry, assurance contract, findings,
   or untrusted-data bytes.

Codex returned `CHANGES_REQUIRED`; no review pass was recorded.

## Interrupted Sonnet repair state

A single Sonnet writer was given all four findings and told to remain at or
below 350 or fail explicitly. The Claude request was silent for about 20
minutes. As it was stopped through the certified controller, it completed a
large edit and returned CLI exit 0 with only `Execution error`, no trustworthy
report. The controller sealed then paused the bytes without certifying them.

Current dirty production accounting:

- 531 additions
- 10 deletions
- net 521
- 171 lines over the ratified ceiling
- same 14 changed paths; no commit
- no post-repair tests or review are trusted
- production STOP remains armed; daemon inactive; JAA untouched.

Approximate expansion by file:

- `agents/task_manager.py`: 101 → 138 diff lines
- `control/scope_admission.py`: 86 → 137
- `dispatch/repository.py`: 58 → 62
- `infra/schema_registry.py`: 22 → 48
- `infra/scope_admission.py`: 56 → 111
- focused test file: 339 → 348

The current 521-line bytes may contain useful implementations of the four
required repairs, but they are unreviewed partial work and cannot be accepted.

## Question

Does the correct next move remain a deletion-heavy consolidation back to the
350 ceiling in this single stage, or has the evidence now proved that the
ratified boundary must be split/reallocated? Do not approve extra lines merely
because they exist; protect completeness and the programme cap together.
