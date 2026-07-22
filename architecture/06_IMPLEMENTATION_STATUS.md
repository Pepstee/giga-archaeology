# Virtual-twin implementation status

*Machine-verifiable handoff · updated 2026-07-22*

The durable implementation has crossed the evidence-protection and trust-kernel gates. P2 is
active: the Telegram and daily legs are deployed; the first natural post-deployment daily run and
full transition fault injection remain before the phase can pass.

## What is live

- `python3 -m twin_core verify-exports` re-hashes all five immutable source archives and fails
  closed on missing, changed, malformed or root-escaping entries.
- `python3 -m twin_core validate-memory` checks schema, index coverage, links, supersession,
  provenance, review state and sensitive hot-index leakage. Current result: 53 entries, zero
  errors, zero warnings.
- `python3 -m twin_core health` derives corpus, process, permission, memory, prediction and
  trust-store state from runtime evidence.
- `python3 -m twin_core maturity` emits the full roadmap scorecard as JSON. Its numeric value is
  explicitly roadmap completion, not twin intelligence or accuracy.
- `python3 -m twin_core compile-proof ...` compiles exact evidence-linked claims into a local
  draft case study, technical report and presentation outline. It enforces A1/draft authority,
  public-source boundaries, secret scanning, path containment and deterministic source lineage;
  a committed receipt services identical replay without rewriting the artefacts.
- `~/.giga/twin.sqlite3` holds append-only events, processing attempts, receipts, goals,
  decisions, action foundations and owner-only derived-artefact lineage. Schema v2 retains every
  registration revision: a new build or verified adoption supersedes history instead of
  overwriting it.
- The five discovery/target/roadmap artefacts are registered with their content and source
  hashes. The operator's virtual-twin goal and first implementation decision are stored as
  operator-confirmed records.
- The Telegram daemon records an authorised update before provider invocation, gives the model a
  bounded deterministic context packet and no filesystem tools, validates its strict JSON
  create/replace proposal in a temporary complete memory projection, forbids deletion/path escape,
  then commits entries atomically per file with the index last. Offsets are atomic; a committed
  receipt services replays without a second model call.
- Daily ingestion now uses the same no-tool proposal and receipt lifecycle. It selects new evidence
  ahead of historical backlog, enforces both record and character budgets, writes run-addressed
  derived delta files, and advances `seen` state only after a committed memory receipt. The unsafe
  direct-write worker was removed. Prediction adjudication also runs from an empty disposable
  read-only provider workspace.

## Verified runtime boundary

Claude's no-tool worker currently exits with the operator's weekly-limit message. The Codex
fallback was invoked from an empty disposable workspace with a read-only sandbox and strict output
schema, and successfully returned the exact requested proposal. This confirms the provider
fallback contract instead of inferring it from command construction.

## Gate evidence

- 51 canonical giga-user tests pass with resource warnings promoted to failures, including event replay,
  retry recovery, proposal replay, invalid transitions, receipt foreign keys,
  secure permissions, memory validation, export mutation detection, provider command shape and
  seven external-proof compiler tests. The lineage tests also prove v1 migration preserves old
  hashes, model-inferred authority cannot reconcile an artefact, a failed gate cannot promote a
  revision, and an identical adoption is idempotent.
- The prediction automation's SQLite connections now close transactionally; its focused suite
  passes with `ResourceWarning` promoted to an error.
- All five export hashes, including the 1.17 GB second ChatGPT archive, match the
  pre-implementation baseline after the build and again after its chronological review.
- Market Aligner was inspected for boundary awareness only and was not modified.
- The first proof pack produced six source-hashed artefacts and a committed `TwinStore` receipt;
  identical replay returned the same event/receipt without rewriting files.

The six proof artefacts are rebuilt through their normal compiler whenever compiler evidence
changes. The older architecture registrations are handled separately by the bounded
`reconcile-lineage` command and `architecture/LINEAGE_RECONCILIATION_POLICY.json`. This is
explicitly a verified current-state adoption, not a fictional rebuild: it requires the canonical
tests, memory validator, immutable-export baseline and declared structure/source set to pass; it
then retains the old hashes as `superseded`, promotes operator-authorized `reconciled` revisions,
and writes a durable JSON/Markdown receipt.

The existing Telegram supervisor was retained and only its idle child was restarted after the
gate passed. The replacement process is live under that supervisor; the bot token and durable
offset were not rewritten.

## Deterministic control surfaces added 22 July

- `giga.operator-status.v1` compiles ten read-only evidence envelopes. Missing runtime telemetry
  stays unknown and degrades the report instead of being painted green.
- `giga.adapter-registry.v1` compiles root-contained adapter manifests, hashes every proof file,
  degrades stale claims to reference-only, executes no declared commands and grants no authority.
  Operator status re-hashes the registry before consuming its summary.
- The owned giga/ECC test boundary passes 90 tests. SkillTree still records Integration Builds as
  documented and Monitoring & Alerting as partial because governance contracts do not prove live
  integrations or complete cross-service telemetry.

## Next exact slice

Inspect the first real post-deployment Telegram receipt and the first natural daily run. Then kill
the live pipeline at each transition and prove replay/recovery before promoting P2. A forced daily
run was deliberately not launched while the independent Market Aligner certification agent was
actively consuming Codex; the scheduled run will use the new path without stealing its current
model slot.
