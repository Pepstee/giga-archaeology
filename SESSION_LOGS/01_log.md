# Session 01 log — Unified Operator Charter

*Status: IN PROGRESS. Started 16 Jul 2026 (evening), continuing 17 Jul. This chat also ran
programme-adjacent work (librarian bot setup, corpus landings) at the operator's direction —
recorded in `interim_corpus_log_20260717.md`.*

## Built

- `CHARTER.md` v1.0 — ratified by the operator as-is (16 Jul). Nine sections; every clause
  tagged to corpus evidence [C] or interview answer [I‑n].
- `deploy/claude_preferences.txt` — **deployed** 17 Jul: pasted into Claude → Settings →
  General → "Instructions for Claude". (First attempt pasted the file *path*; corrected to
  full text. Replaced the old two-line preference.)
- `deploy/chatgpt_custom_instructions.txt` — written, two-box format. **NOT yet deployed.**
- `deploy/v3_operator_model.md` — staged, machine-readable YAML. Orchestrator repos untouched.

## Method notes

- Corpus mined first (all 466 hand-typed prompts read in-session before any characterisation).
- Interview: 8 excavator-style questions, all answered 16–17 Jul. Key rulings: "when unsure,
  write short — short is king"; never assume repo knowledge; inline claim marks + numeric
  confidence together; career clock = end of 2026; pushback confirmed welcome, ratified
  decisions off-limits.
- Q4 (remembered excellent/terrible responses) was delegated back: "you have the memory, you
  tell me why" → distilled into CHARTER §8 from corpus evidence.

## A/B test (the shipping gate) — RESULT (17 Jul)

- Protocol as run: 3 old-config baselines (~04:30), charter deployed (~04:40), 3 reruns
  (~13:30). **Two pairs voided by the operator** — correctly: the Korean and Instagram
  baseline chats had become working sessions in the interim (lessons delivered; unfollow
  operation live), so the reruns answered in a changed world. Contamination, not comparison.
- Surviving pair (skills prompt), judged blind, shuffled: **"Response B [old config] is
  slightly less confusing but overall they are the same."**
- Diagnosis: the loss was decoration — inline "(0.8)" notation and verdict scaffolding on a
  low-stakes answer. Charter machinery misapplied to stakes that didn't warrant it.
- **Amendment v1.1** (17 Jul): confidence marks now stake-scaled — plain-prose "~85%" only
  where being wrong is costly; no decoration on low-stakes answers. All four charter/deploy
  files updated.
- **Open gate:** charter does NOT ship on this evidence. New closing condition: one week of
  natural usage under v1.1; the Session 04 retrospective judges real responses against the
  old register and closes (or reverts) the charter. Lesson for future tests: synthetic
  reruns break the moment world-state moves — test on live prompts, immediately paired.

## Open items

1. ~~Repaste v1.1 Claude preferences~~ — done (operator, 17 Jul).
2. ~~Deploy ChatGPT custom instructions~~ — done (operator, 17 Jul).
3. Session 04: run the week-of-usage verdict; then master table 01 → DONE (or revert).
4. Repaste the 18 Aug v1.2 payloads into live Claude and ChatGPT settings and verify recitation.

## Amendment — 18 Aug 2026

- The operator directly ratified **reuse before creation**: search for and extend the canonical
  existing file that already performs the same job; prohibit parallel or near-duplicate files.
- A new file is allowed only for a distinct responsibility, lifecycle, ownership boundary, or
  required format, with the non-reuse reason recorded.
- Updated the existing canonical registry, charter, three deployment payloads, project and global
  Codex instruction files, master status, and this log. No new policy file was created.
- Codex enforcement is live through the project and global `AGENTS.md` files. Live
  Claude/ChatGPT repaste remains unverified.

## For other sessions

- **Session 03:** Gmail connector was connected 17 Jul (read-only) — untouched here per
  one-brief law. Injection posture required before any briefing surface consumes inbox.
- **Session 04:** revision seam — retrospectives feed charter amendments (CHARTER §9).
  Full cowork transcripts still unlanded; see corpus/MANIFEST.md pending table.
- **Session 05:** the interview surfaced that he wants numeric confidence everywhere — the
  prediction ledger should score assistant confidence marks too, not just his own estimates.
- **Session 06:** Telegram librarian went live mid-session (see master table row 06).
