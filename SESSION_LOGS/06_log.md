# Session 06 log — The Second Memory (Jarvis)

*Status: IN PROGRESS. Running across chats by design — the keystone workstream is allowed to
(00_MASTER: "can run any time").*

## Built so far

- **16 Jul:** skeleton (`memory/` + protocol + index + 3 seed entries) and Telegram
  librarian script (`scripts/jarvis_telegram.py` + supervisor).
- **17 Jul:** bot configured (`~/.jarvis/config.json`), launched, **verified end-to-end** —
  Telegram message → `entries/2026-07-16-librarian-live.md` → index regenerated, COLLIDE and
  REMIND both fired. 4 entries in store.
- **18 Jul:** **`librarian` skill built** — `deploy/skills/librarian/SKILL.md`, packaged as
  `librarian.skill` and handed to the operator for one-click install. Design rulings encoded
  (from the operator-relayed review): the skill names its one store by path and must request
  access or refuse loudly if the giga folder is absent — never file into a local
  improvisation; tool-agnostic (files + shell only) so it ports to Claude Code and v3;
  `MEMORY_PROTOCOL.md` stays canonical, the skill is a wrapper.
- v3 adoption path: **staged, not copied** — orchestrator repos remain read-only from here;
  when v3 consumes these skills they enter as reviewed, versioned artefacts through a
  certification round (operator's A1/ME-8 laws), because portable instructions are portable
  behaviour changes.

## Capture mesh (current)

Telegram bot (phone, anywhere) · any giga-folder cowork chat (protocol) · any chat at all
once the skill is installed. One store, several mouths.

## Design redefinition (18 Jul, operator-ratified)

Memory is **derived, not dictated**: manual capture (Telegram/chats) stays as an optional
mouth, but the pipeline is corpus → extractor → **INGEST pass** (new protocol duty 4), with
entries carrying **prediction triggers**. First extraction batch run same day: 15 entries
mined from the landed corpus (trip structure, Transnistria purposes + dentist reminder,
degree/SCAFAD, social circle, budget doctrine, client work, appearance workstream, sprint-vs-
flight collision prediction, export-ingest standing reminder, twin modes decision).
**Store: 24 entries — seeding target exceeded.** Skill evals: 18/18 with-skill (viewer in
`deploy/skills/librarian-workspace/`); near-zero delta vs baseline is an artefact — baselines
were folder-pointed, so the protocol recruited them; the skill's value is triggering in
folder-less chats (test via description optimisation, later).

## DONE — 18 Jul

1. ~~Seeding 20+~~ — 35 entries (corpus extraction + ChatGPT-memory ingest + live bot filings).
2. ~~Weekly sweep~~ — scheduled task `weekly-memory-sweep`, Mondays 06:06 local (= 6am ICT
   while he travels), report delivered via Telegram; first run 20 Jul.
3. ~~Synthesis test~~ — PASSED: "what's colliding around the 25th?" → three entries connected
   by slug, near-miss excluded, and an internal date conflict (sprint end 23 vs 25 Jul)
   flagged to the operator instead of bridged. Stage-2 accuracy behaviour, unscripted.

Post-DONE additions this session: INGEST duty + recency law in the protocol ("a June plan is
not a July fact" — the first extraction filed three stale entries; live supersession caught
all three); bot patched to carry CONTEXT.md (Session 02 parity).

## Post-DONE amendment (18 Jul, colibri-derived)

Two retrieval laws added to the protocol after studying colibri's architecture (see memory
entry `2026-07-18-colibri-local-frontier`): **prefetch-on-route** (a retrieval loads its
[[linked]] entries one hop out) and the **learned working set** (all reads logged to
`memory/access.log`; the Monday sweep promotes the month's most-touched entries into a ≤5
line block atop INDEX.md). Zero code changes — every librarian inherits via the protocol;
the sweep task prompt updated as maintainer. The access log doubles as future corpus:
attention data for the virtual twin.

## Post-DONE amendment (19 Jul, daily model-agnostic capture)

The quota-bound Claude weekly task was disabled and replaced with a daily 06:06 ICT pipeline:
`extract_prompts.py` now harvests both Claude Cowork and native Codex desktop tasks (machine
`codex_exec`, orchestrator cwd, injected wrappers, imported duplicates, and `[[task:...]]`
jobs excluded). `daily_personal_knowledge.py` computes a bounded unseen delta (120/run),
INGESTs it under the recency/untrusted-data laws, sweeps reminders and working set, then reports
to Telegram. The Telegram daemon is the clock and launches it after 06:00 Vietnam time;
Claude is preferred worker, GPT/Codex deputy. No provider scheduler or calendar is required.

## Post-DONE amendment (19 Jul, fine-tuning readiness)

Fine-tuning preparation was converted from an informal MLX run kit into a provider-neutral,
tested data contract. Added `FINE_TUNING_READINESS.md`,
`corpus/training/DATASET_CONTRACT.md`, `scripts/prepare_finetune_data.py` and unit tests;
extended the ChatGPT extractor with namespaced outputs so the forthcoming second account
cannot overwrite the first; the canonical prompt harvester now selects the newest snapshot
per namespace rather than one file globally. Built a source-hashed current casual v1 split (6,490/100/468,
one possible-credential quarantine, training unauthorised) and generated separate unapproved
operator-next-turn candidates from ChatGPT and Claude. Discord remains era-tagged style-only
unless genuine incoming context is recovered. The earlier scheduled casual-v0 attempt is now
recorded accurately: prefetch succeeded, but no adapter was produced.

## Open thread carried forward

Sprint-end date conflict (23 vs 25 Jul) awaits the operator's word; whichever entry loses
gets superseded.

## For other sessions

- Session 05: brief-pattern skills (review / cost-audit / risk-register) deliberately held
  until the prompt-bank harvest — encode winners, not templates.
- Session 03: korean-daily skill candidate noted; also the weekly sweep schedule (above).
