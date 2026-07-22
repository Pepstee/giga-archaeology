# Session 05 log — Calibration & prompt bank

*Status: IN PROGRESS. Automated calibration is live; prompt-bank work remains.*

## 20 Jul — manual ledger superseded by an autonomous prediction loop

The operator explicitly rejected manual prediction entry. Jarvis now generates up to 20
falsifiable forecasts per daily run from timestamped Claude/ChatGPT/Codex behaviour, commits
them before outcomes, and resolves them from later evidence. Claude is preferred and GPT is
fallback; both run read-only for this phase. Storage is local SQLite at
`~/.jarvis/prediction_ledger.sqlite3`, using the factory-certified prediction-ledger canary.

Accuracy cannot be quietly inflated by model self-adjudication. Digital-trace forecasts
precommit literal match terms and are resolved by an exhaustive deterministic scan. Real-world
forecasts require later explicit evidence and >=90-confidence adjudication. Every forecast,
snapshot hash, source fingerprint, provider, run and adjudication is retained.

Durable artefacts: `scripts/prediction_automation.py`, integration in
`scripts/daily_personal_knowledge.py`, `PREDICTION_AUTOMATION.md`, and
`tests/test_prediction_automation.py`. Four focused tests and the full twelve-test GIGA suite
passed before deployment. The first live cycle then committed 20 GPT-generated forecasts;
the production ledger verified all 20 rows and correctly reports all 20 as unresolved pending
post-forecast evidence.

## Still open

- Let the automated ledger accumulate enough resolved examples for meaningful calibration.
- Build the prompt-pattern bank from Session 04's proven patterns.
- Write `REVIEW_CADENCE.md` and programme review when the remaining deliverables close.
