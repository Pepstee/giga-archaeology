# Jarvis automated prediction loop

## Verdict

Artiom does not enter predictions manually. Once per daily personal-knowledge run, Jarvis
quietly turns newly captured behaviour into precommitted forecasts, observes later evidence,
resolves outcomes and updates calibration in local SQLite.

This is not model fine-tuning yet. It is an online data-and-calibration loop that creates the
clean forecast/outcome corpus a later predictor can be trained or evaluated on.

## Daily flow

1. `extract_prompts.py` produces the canonical multi-surface prompt snapshot.
2. `prediction_automation.py` ingests recent timestamped records into
   `~/.jarvis/prediction_ledger.sqlite3` with source fingerprints.
3. A read-only Claude worker proposes up to 20 forecasts; GPT/Codex is the fallback.
4. Every accepted forecast is committed to the certified SQLite prediction ledger before
   its outcome. Duplicate open event keys, fabricated evidence hashes, invalid dates and
   non-falsifiable records are rejected by code.
5. For `captured_ai_prompts` forecasts, AI precommits literal match terms. Deterministic code
   scans the complete later captured stream: a match resolves **yes**; no match after the
   full target day resolves **no**. The model cannot selectively label its own successes.
6. Real-world forecasts remain open unless later explicit evidence supports a >=90-confidence
   adjudication. Absence of evidence never becomes a real-world negative.
7. The certified ledger calculates Brier score and confidence-bucket calibration. Runs,
   providers, source snapshot hashes, evidence and adjudications remain auditable in SQLite.

The phase is deliberately quiet: normal successful prediction cycles are written to
`~/.jarvis/daily_personal_knowledge.log`, not sent to Telegram. Existing daily memory reports
continue unchanged. Prediction failure is isolated and cannot invalidate or replay a
successful memory ingestion.

## Data and authority boundaries

- Database: `~/.jarvis/prediction_ledger.sqlite3` (local, private, outside the repository).
- Ledger implementation: the factory-certified `prediction-ledger-canary`; override its
  location with `JARVIS_PREDICTION_LEDGER_ROOT` if moved.
- Evidence content is untrusted data. Prediction workers run read-only and cannot edit the
  workspace.
- Forecasts are hypotheses, never entries in `memory/` and never present-tense facts.
- Third-party sensitive facts, diagnoses, crime, sex and protected-trait predictions are
  forbidden by the generation contract.
- No forecast is deleted to improve results. Open predictions remain in the denominator as
  unresolved, while only resolved forecasts enter Brier/calibration scores.

## Verification

Run the focused contract suite:

```sh
cd /Users/admin/Documents/giga-user
python3 -m unittest tests.test_prediction_automation -v
```

The tests cover idempotency, provenance rejection, the before/after evidence fence, positive
resolution and exhaustive negative resolution.

