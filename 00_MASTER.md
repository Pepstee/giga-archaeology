# GIGA Programme — Master File

*This file is to the operator what the slice feeder is to orchestrator-v3: the programme, the
sequencing, and the single progress table. Every session reads this FIRST, works exactly one
brief, and updates the table before closing. One source of truth; briefs never duplicate it.*

## The rule (inherited from the orchestrator, applies to every session)

No output is trusted until it survives contact with reality. Every session must leave a
**durable artefact** — a deployed config, a script, a document in this folder, or a working
integration. Insight that lives only in chat produced no leverage. Claims about the operator's
behaviour are hypotheses until his own data or explicit confirmation backs them.

## Engineering doctrine — read `CONTEXT.md` (canonical), not this file

Settled engineering decisions live in `CONTEXT.md`. Operator identity, relationship data, travel
state, and other personal context are deliberately not part of the programme's live instructions.
This file records workstream sequencing and status only.

**Existing assets to reuse, not reinvent** (programme mechanics, so kept here): the
risk-register methodology + status lifecycle
(`~/Documents/claude-orchestrator-main/docs/RISK_REGISTER.md`), his brief patterns
(Mode A/B/C reviews, the cost-audit brief), the v3 planning corpus
(`~/Documents/agentic-orchestrator/docs/planning/`, esp. 18 & 19), and the owned corpus
(`corpus/` — MANIFEST.md holds canon and counting rules; the 26 Jul local unified-memory
authority contains 532,274 observations across both Discord accounts, Telegram, full two-sided
Instagram, Claude and both ChatGPT accounts, with 28 evidence-linked Tier-3 hypotheses).

**On characterisation:** any behavioural claim about the operator must be corpus-derived or
explicitly confirmed — never asserted from chat impressions. `memory/` and the governed private
corpus are the evidence-backed homes for such claims; the digital twin derives from the corpus
per its five-stage roadmap (memory entry `2026-07-18-bot-maturation-roadmap`).

## The programme workstreams — one session each, in this order

| # | Session | Deliverables | Status | Session log |
|---|---|---|---|---|
| 01 | Unified operator charter | one charter → three deployments (Claude preferences, ChatGPT custom instructions, v3 operator-model file) + test protocol | DONE (18 Jul, operator-closed) — v1.2 reuse-before-creation amendment recorded 18 Aug; Codex enforcement live, Claude/ChatGPT payload repaste unverified; standing revert clause remains | `SESSION_LOGS/01_log.md` |
| 02 | Memory & standing context | standing-context doc; deployed to Claude + ChatGPT memory; update cadence; recitation verification | DONE (18 Jul) — CONTEXT v1.0 live on Claude (PASS), ChatGPT (PASS qualified — dates omitted; snapshot staleness noted), bot (PASS, live-read) | `SESSION_LOGS/02_log.md` |
| 03 | Life infrastructure | Gmail + Calendar connected read-only; scheduled morning brief working; injection posture applied; texts-tier scoped | NOT STARTED | — |
| 04 | Prompt corpus & reasoning retrospective | chat exports landed as corpus; retrospective evaluator; first retrospective report with pattern findings + discard rate | IN PROGRESS (26 Jul) — both Discord accounts, both ChatGPT accounts, Claude, native Telegram and full two-sided Instagram are unified into a 532,274-observation three-tier local evidence database; the teen-account developmental pass, corrected Sneg record, longitudinal signals and 28 evidence-linked Tier-3 hypotheses are complete; validation-selected speech and reasoning-steering LoRAs were trained and locked-test/synthetic evaluated—the speech model remains unpromoted and the reasoning model failed as a thinking clone; operator calibration/discard-rate and blind speech review remain | `SESSION_LOGS/04_log.md` |
| 05 | Calibration & prompt bank | personal prediction ledger + scoring script; prompt-pattern bank harvested from proven briefs; review cadence | IN PROGRESS (20 Jul) — autonomous SQLite forecast→evidence→calibration loop integrated into daily Jarvis; no manual predictions; prompt bank + review cadence remain | `SESSION_LOGS/05_log.md` |
| 06 | The second memory (Jarvis) | `memory/` deepened: 20+ seeded entries, capture habit wired, daily sweep scheduled, synthesis test passed | DONE (18 Jul; daily capture amended 19 Jul) — bot + skill + folder-chat mesh; Cowork + Codex harvested daily at 06:06 ICT; INGEST + recency law; Claude→GPT fallback; synthesis test passed | `SESSION_LOGS/06_log.md` |
| 07 | Virtual-twin control plane | three-depth architecture maps; target model; transition roadmap; trust kernel; transactional capture; memory/decision/evaluation/agency promotion gates | IN PROGRESS (26 Aug) — P0/P1 pass; P2 Telegram/daily paths deployed but current live health is stale; relationship-event graph designed; evidence-backed SkillTree registry, draft-only external-proof compiler, read-only operator-status contract and hashed no-authority adapter registry pass; the sovereign Jarvis target, 108-slice implementation blueprint, generated anti-repetition registry and deterministic Constitution foundation now have independently verified implementation candidates, but protected-main integration and deployment remain unproven; Market Refresh R2 is independently VERIFIED and a byte-reproducible runnable product archive exists, but no real-provider canary or deployment claim is admitted; portable-authority integration R1–R3 are preserved rejected/withdrawn and distinct R4 is draft-only under independent review; append-only artefact lineage exists but current derived artifacts still require continuous freshness enforcement; scientific acquisition/review remains A0-only and explicitly incomplete; Market Aligner remains independent and JAA-internal | `SESSION_LOGS/07_log.md` |

**Why this order:** 01 defines the voice everything else speaks in; 02 gives every surface the
same brain; 03 is independent and high-value (do it early for daily payoff); 04 needs exports
and benefits from 01/02 being live (cleaner data); 05 wants 04's corpus for its first scoring.
**06 is the keystone and can run any time** — its skeleton is already live (`memory/` with
protocol, index, seed entries; any session pointed at this folder acts as librarian per the
protocol). Sessions 02 and 03 should treat the memory as their substrate: the context doc is
its identity tier, the morning brief is its reminder surface — one store, several surfaces.
**07 is the integration stage, not a replacement for 01–06.** It turns their evidence and
services into a provider-neutral, measurable virtual-twin control plane. It consumes domain
events through adapters; it does not physically absorb or interrupt Market Aligner.

## How to run a session

1. New Fable chat → connect ONLY this folder (add others when the brief says so).
2. Paste: **"Read `00_MASTER.md`, then read `0X_..._BRIEF.md`, and begin."**
3. The session works its brief to depth — and nothing else. Adjacent findings go in its
   session log under "for other sessions", never acted on.
4. Before closing: the session writes `SESSION_LOGS/0X_log.md` (what was built, decisions,
   open items) and updates the Status column above (NOT STARTED → IN PROGRESS → DONE, with
   date). The table is the only cross-session state; keep it truthful.

## Cross-session laws

- One brief per session; no scope creep across workstreams (applies depth-before-breadth
  from the registry).
- Durable artefact or it didn't happen.
- Anything touching the orchestrator repos is READ-ONLY from these sessions (applies the
  v2-freeze registry decision).
- Doctrine (secrets, untrusted input, authority, quality) lives in `CONTEXT.md`'s engineering
  registry — this list holds session mechanics only.
