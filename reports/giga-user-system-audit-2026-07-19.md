# GIGA-user System Audit — Mechanics and Forward Path

**Date:** 19 July 2026  
**Scope:** the `giga-user` folder as a personal operating system, not a review of the
orchestrator or Market Aligner codebases embedded inside it.  
**Method:** direct inspection of the charter/context/master hierarchy, corpus manifest,
memory protocol and index, live Jarvis process/state/logs, ingestion scripts, retrospective
graph, directory layout and outstanding session briefs. No secrets were read or reproduced.

## Verdict

GIGA is already a credible **personal knowledge and governance substrate**. It has an owned
corpus, explicit doctrine, a hot context layer, a linked memory store, daily capture, multiple
model surfaces and an unusually strong epistemic rule: claims about the operator require data
or confirmation.

It is not yet a digital self or a closed-loop personal operating system. It is strongest at
**capture → storage → interpretation** and weakest at **evaluation → decision → authorised
action → measured outcome → correction**. In its present form it can increasingly explain
Artiom, but it cannot yet demonstrate that it predicts him, improves his decisions or reliably
works instead of him.

## The global goal, reconstructed from canon

The folder currently states the goal in three different places and at three different levels:

1. **End-state:** organic growth into a digitalised self that develops memory, accuracy,
   speaking style, thinking style and self-scrutiny, then lives locally and works instead of
   Artiom (`memory/entries/2026-07-18-bot-maturation-roadmap.md`).
2. **Operating doctrine:** become a top-0.1% AI user through logs, calibration, verification
   and an owned corpus (`CONTEXT.md`).
3. **External constraint:** produce material AI/IT results by the end of 2026, with the
   orchestrator as the headline portfolio asset (`CONTEXT.md`, `CHARTER.md`).

These should be made one explicit hierarchy:

> **Build a provider-independent, evidence-grounded digital Artiom that remembers, models,
> predicts, challenges and eventually executes useful work under traceable authority—while
> producing material external AI/IT results by 31 December 2026.**

The end-state is the direction; the 2026 result is the forcing function; GIGA is the operator
model and evidence substrate; the orchestrator is the future execution engine.

## How the system currently works

```text
AI exports + local chats + Instagram + operator messages
                         |
                         v
                  extraction scripts
                         |
                         v
      canonical corpus + MANIFEST (cold evidence)
              |                     |
              v                     v
     CONTEXT.md (hot)       retrospectives / graph
              |                     |
              +----------+----------+
                         v
        memory entries + INDEX (warm knowledge)
                         |
             +-----------+-----------+
             v                       v
       Telegram Jarvis        Claude / ChatGPT / Codex
             |                       |
             +-----------+-----------+
                         v
                  advice and filing

Missing closed loop:
  decision -> authorised action -> outcome receipt -> calibration -> model update
```

### 1. Governance and canon

- `00_MASTER.md` is the programme control table and session sequencer.
- `CHARTER.md` defines how assistants should respond.
- `CONTEXT.md` defines current identity, priorities and standing doctrine.
- `memory/MEMORY_PROTOCOL.md` defines memory mutation and retrieval behaviour.
- `corpus/MANIFEST.md` defines source inventory and counting rules.
- Briefs define bounded workstreams; session logs record what happened.

This separation is conceptually strong. The weakness is that it is enforced socially by
instructions, not mechanically. There is no root-level validator checking canon drift,
missing deliverables, stale deployments, broken links or contradictory status declarations.

### 2. Capture and corpus

`scripts/extract_prompts.py` rebuilds a canonical human-prompt snapshot from local Cowork,
Codex desktop and landed account exports. Separate extractors handle ChatGPT, Instagram and
Discord. The manifest correctly distinguishes raw, training and two-sided transcript views.

This is the strongest part of the system: provenance is explicit and the canonical snapshot
prevents additive double-counting. Two mechanics nevertheless need correction:

- the daily extractor overwrites `prompts_<date>.jsonl` repeatedly on the same day, which is
  inconsistent with the stated raw-immutability law;
- the folder has no checksum catalogue or discovered backup/restore contract for roughly
  1.7 GB of unusually sensitive and difficult-to-recreate data.

### 3. Memory and retrieval

The memory uses one Markdown file per thought, an index, explicit links, supersession rather
than deletion, an access log and a learned five-item working set. This is appropriate at the
current 41-entry size. The distinction between hot context, warm memory and cold corpus is
sound and model-independent.

The system is still prompt-routed. A model is told to read the correct files, follow links,
write only within `memory/` and avoid inventing facts. There is no deterministic memory packet,
retrieval test set, provenance check or technical write boundary. The planned mature
architecture correctly names these omissions, but the new ChatGPT export has already met one
of its stated activation triggers.

### 4. Jarvis and daily ingestion

The Telegram daemon is live and sender-locked. It reads the same canon as the other surfaces,
uses Claude first and Codex/GPT second, and launches the daily pipeline after 06:00 Vietnam
time. The provider fallback worked on 19 July: the daily state records GPT as the successful
provider.

The live mechanics have four material weaknesses:

1. **Backlog is not scalable.** The state has 2,704 seen fingerprints while the canonical
   snapshot contains 20,107 records. Exact recomputation found **17,406 pending records**
   (17,109 from the newly landed ChatGPT export). At 120 records per day, catch-up takes 146
   runs. The limit is record-count based, not token based; historical backfill and daily delta
   are different jobs and should not share one queue.
2. **“Success” is not a commit receipt.** A non-empty model reply causes every batch
   fingerprint to be marked seen. The runner does not verify which entry files changed,
   whether the index is valid, whether provenance was attached, or whether a partial run
   silently omitted records.
3. **Telegram failure handling can swallow work.** If both librarians fail, the bot tells the
   operator the message is safe, but then persists the Telegram offset anyway. There is no
   local inbox/dead-letter record to retry. The original remains in Telegram history, but it
   is no longer automatically processed.
4. **Safety is instructional rather than enforced.** Both daily providers run with bypassed
   permissions over the entire GIGA root. “Write only inside memory” is a prompt, not a
   filesystem capability. This is especially important because the system intentionally
   processes untrusted transcript data.

There are no tests for the GIGA scripts, although the Python and shell files currently pass
syntax parsing. By contrast, the embedded project/audit code contains more than 200 tests.

### 5. Analysis, graph and calibration

The retrospective work is unusually deep and now has a month-by-month ledger, evidence matrix
and operator corrections. This is the beginning of thinking-style and self-scrutiny modelling.

It remains a manually edited analysis product. Session 04 has not recorded a completed
confirm/refine/discard ledger or discard rate. Session 05—the prediction ledger, prompt bank
and monthly maintenance contract—has not started. Consequently there is no measurement of:

- retrieval accuracy;
- false-memory or stale-memory rate;
- prediction calibration;
- whether a recommendation improved an outcome;
- whether style/thinking imitation wins blinded comparison;
- whether autonomous work was correct without human repair.

The existing graph proves the derived-artifact problem. It covers only four retrospective
files, not the GIGA system, and still contains the old “Attachment and Rehumanisation” node
after the source report was corrected. There is no source-change invalidation or freshness
gate.

### 6. Folder boundary and operational hygiene

The root is 1.7 GB and mixes four different classes of material:

- GIGA control plane and scripts;
- 792 MB corpus plus a 599 MB Instagram export zip;
- a 289 MB Market Aligner working tree and a near-duplicate delivery copy;
- a 51 MB v3 audit workspace with its own nested Git repository.

The GIGA root itself is not a Git repository. Thus its central doctrine, memory scripts and
reports do not have discovered version history, while a nested audit project does. Generated
build trees, virtual environments, caches, logs, backup-suffixed source files and duplicated
project copies inflate searches and make the folder harder to reason about. `market-aligner`
and `market-aligner-artiom` are nearly identical aside from generated/runtime material and one
source file, so their authority boundary is unclear.

The Jarvis configuration and state files are mode `0644`; the config contains a bot token and
should be owner-readable only. The memory index also exposes detailed travel references in
the always-loaded layer. A prior corpus review found a historical plaintext Instagram
credential. Security remediation is therefore a current requirement, not theoretical
hardening.

## What is genuinely good and should be preserved

1. **Plain-file, provider-neutral canon.** This is the right substrate for longevity.
2. **Hot/warm/cold separation.** Context, memory and corpus have distinct jobs.
3. **Explicit epistemic law.** Corpus-derived or operator-confirmed behavioural claims are a
   strong foundation for a faithful twin.
4. **Supersession and provenance instincts.** The system already treats corrections as data.
5. **Multiple capture mouths, one store.** Telegram, folder chats and daily harvesting avoid
   platform ownership of memory.
6. **External deadline.** The end-2026 career clock prevents the digital-self project from
   becoming purely introspective—if it is actually enforced.

## The forward path, in order

### P0 — Define the acceptance system (one day)

Create one `GLOBAL_GOAL.md` and a machine-readable maturity scorecard. Each maturation stage
needs an observable gate:

| Capability | Gate before promotion |
|---|---|
| Memory | important facts retrieved with source citations on a fixed test set |
| Accuracy | measured false-memory, contradiction and stale-answer rates below thresholds |
| Speaking style | blinded register-specific A/B preference against a generic assistant |
| Thinking style | held-out decisions/predictions reproduced or improved with calibration |
| Self-scrutiny | catches operator errors on a review set without inventing defects |
| Agency | completes bounded real tasks with outcome receipts, authority compliance and low repair rate |

The scorecard should include the external metric: verified AI/IT money, users, interviews,
client outcomes or independently evaluated portfolio results by 31 December 2026.

### P0 — Make the live loop trustworthy (two to four days)

1. Add a durable Telegram inbox and processing states: received → claimed → committed or
   dead-letter. Advance the Telegram offset after local receipt, but acknowledge completion
   only after a verified commit; retry failures automatically.
2. Make daily ingestion transactional. The worker emits a receipt listing input hashes,
   created/amended files, index validation and unresolved records. Mark only receipted records
   seen.
3. Enforce the write boundary technically: run the worker in a staging worktree/directory,
   validate its diff, then apply only allowed `memory/`, `corpus/MANIFEST.md` and receipt
   changes.
4. Change the batch limit from record count to a token/character budget.
5. Make timezone a context/config value rather than hard-coded Vietnam time.
6. Add tests for retry, partial-write, corrupt state, duplicate delivery, injection payload,
   provider fallback, index rebuild and stale-context detection.

### P0 — Close the security and durability holes (one day)

1. Restrict `~/.jarvis/config.json`, state and offset files to `0600`; rotate any exposed or
   uncertain credentials.
2. Move booking references and comparable sensitive operational data out of the always-loaded
   index; load them only on an authorised route.
3. Add a secret scan over new corpus and memory derivatives with quarantine—not deletion—on
   detection.
4. Put the GIGA control plane under version control while excluding raw corpus, credentials,
   logs, environments and generated outputs.
5. Add raw-asset hashes and a tested encrypted backup/restore procedure. Make snapshots
   timestamped or content-addressed so “immutable” is mechanically true.

### P1 — Separate historical backfill from daily change capture (two to three days)

- Rebase the daily state against already reviewed historical material.
- Process the 17,109-turn ChatGPT history as a one-off conversation/month hierarchy, not 120
  prompts per day. Extract candidate memories with provenance, then require collision and
  calibration before promotion.
- Keep daily ingestion only for genuinely new local turns.
- Store a durable receipt for each source shard so re-runs are idempotent.

### P1 — Finish the programme's missing feedback loops (one week)

1. **Close Session 04:** convert the ongoing conversational corrections into a structured
   hypothesis ledger with confirm/refine/discard verdicts and a discard rate. Feed accepted
   changes into the charter/operator model.
2. **Run Session 05:** build the prediction ledger, score it, harvest the prompt bank and
   establish the monthly review contract. This is not administrative polish; it is the
   measurement layer required for thinking-style and self-scrutiny claims.
3. **Run Session 03:** connect email/calendar read-only and ship the brief after the injection
   and receipt boundary exists. This becomes the first daily action-selection surface.

### P1 — Formalise the GIGA ↔ orchestrator contract (two days)

The current statement that v3 will “consume this folder” is direction, not an interface.
Specify:

- the deterministic operator packet v3 receives;
- read/write authority per tier;
- how v3 requests memory and returns outcome receipts;
- how corrections supersede derived knowledge;
- how provider-independent evaluations are run;
- which actions always require operator approval.

This is the bridge from a knowledgeable assistant to an agent that can safely work instead
of the operator.

### P2 — Refactor the physical workspace (after the live loop is safe)

Keep the GIGA control plane small. Move or reference large domains explicitly:

```text
giga-user/
  control/        charter, context, master, scorecard, protocols
  memory/         warm derived knowledge
  corpus/         manifest + derived views; raw vault mounted/referenced separately
  evaluations/    retrieval, calibration, style, reasoning and agency tests
  receipts/       ingestion, deployment and action outcomes
  interfaces/     Telegram, morning brief, provider adapters
  reports/        retrospective and system audits
  projects/       manifests/links to separately versioned projects, not copied worktrees
```

Resolve the two Market Aligner copies, archive the Instagram zip when its active operation
finishes, and keep the v3 audit repository outside the personal-knowledge scan boundary.

### P2 — Add derived-artifact invalidation

Maintain a registry for every derived artefact: source files/hashes, build command, generated
time and freshness. A source correction must mark the retrospective graph, condensed context,
deployed copies and training views stale. Rebuild the graph over the **system architecture**
separately from the personal-characterisation graph.

## The single next move

Do **not** add more corpus sources, train a style model or widen agent autonomy next. First
ship a two-part “trust kernel”:

1. `GLOBAL_GOAL.md` + measurable maturity scorecard;
2. transactional Jarvis inbox/ingestion with receipts, retries, technical write confinement
   and tests.

Then close Sessions 04 and 05. Only after those gates exist should Session 03 widen live data
access or v3 consume GIGA as an operator model.

The strategic change is from **more memory** to **measured faithful agency**.

## Verification performed

- Root size and directory composition inspected; no root `.git` found.
- Live Jarvis process confirmed running since 09:03 local time on 19 July.
- Daily state inspected without exposing config secrets.
- Pending canonical records recomputed from the script's own fingerprint contract:
  17,406 pending / 146 batches at the current limit.
- All GIGA Python scripts passed syntax parsing; all shell scripts passed `bash -n`.
- No test files target the GIGA scripts/protocols.
- Existing graph inspected: 26 nodes / 33 edges over four retrospective files only.

