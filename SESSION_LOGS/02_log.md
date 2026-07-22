# Session 02 log — Memory & Standing Context

*Status: deliverables complete, deployment pending operator (three pastes + one restart +
recitation tests). Run inside the Session 01 chat at the operator's direction — context
already loaded there; depth law satisfied by keeping one workstream per work-block.*

## Built

- `CONTEXT.md` v1.0 — three tiers (IDENTITY / SITUATION / ACTIVE) + standing-decisions
  block + deployed-copies table. Size law: one screen forever. Hyun included by explicit
  ratification; degree/SCAFAD facts corpus-verified before inclusion.
- `CONTEXT_PROTOCOL.md` — single-source discipline, tier cadences (ACTIVE tier may be
  amended by the Monday memory sweep), staleness rule (dated copies, >1 month = stale),
  recitation test definition.
- `deploy/claude_preferences.txt` — now carries charter v1.1 + STANDING CONTEXT block (one
  field, one paste).
- `deploy/chatgpt_custom_instructions.txt` — box 1 rewritten as full context, box 2 charter.
- **Bot parity patch:** `scripts/jarvis_telegram.py` SYSTEM prompt now loads `CONTEXT.md` at
  startup, must not contradict it, flags when a new memory should amend it, may consult
  `corpus/MANIFEST.md` to name evidence but never bulk-reads raw corpus. Restart required.

## Architecture rulings (operator-ratified this session)

- "Personal knowledge" = his term for the whole digital laying-down of his memories.
  Tiered: CONTEXT.md (hot, one screen) → memory/entries + INDEX (warm, one line per entry)
  → corpus/ (cold, evidence only, INGEST distils upward, never context-loaded raw).
- Model-agnostic everywhere: plain markdown, no platform features; every surface carries a
  dated copy or condensation of canon.
- Knowledge graph: derived graph.json from [[links]]+tags, graphify-style, regenerated on
  write — deferred until ~100 entries (ceremony below that). Sub-indices by domain at the
  same threshold.

## Remaining (operator, ~5 min total)

1. Re-paste `deploy/claude_preferences.txt` into Claude → Settings → Instructions.
2. Paste both boxes of `deploy/chatgpt_custom_instructions.txt` into ChatGPT.
3. Restart the bot: `pkill -f jarvis_telegram.py` (supervisor relaunches with the patch).
4. Recitation test on all three surfaces: "What do you know about my situation and current
   priorities?" — record pass/fail in CONTEXT.md's table. Session 02 → DONE on three passes.

## For other sessions

- Session 03: morning brief = Gmail + memory reminders (no Calendar — he doesn't use one;
  parked option: a calendar only the AI writes to, fed by date-triggered reminders).
- Session 04: the charter's week-of-usage verdict (01 closed by operator ruling; revert
  clause stands).
