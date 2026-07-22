# Session 04 — Prompt Corpus & Reasoning Retrospective

*Read `00_MASTER.md` first. Mission: the warcraftlogs of Artiom. He audits his machine's
cognition with a register, falsification, and discard-rates — nobody audits HIS. Land his AI
conversation history as an owned corpus and run the first structured retrospective over his
own prompting and reasoning. This is the workstream least like anything anyone else does,
and the most durable edge of the five.*

## Deliverables

1. **The corpus, landed and owned**: walk him through exporting Claude and ChatGPT history
   (both support account-level export); land under `corpus/` here with a simple layout
   (`corpus/claude/`, `corpus/chatgpt/`, dated). Raw exports are immutable; derived views go
   in `corpus/derived/`. This folder is private infrastructure — reiterate the no-secrets law
   (exports may contain sensitive threads; he decides inclusions, session helps triage).
2. **The retrospective evaluator** — a re-runnable script (`scripts/retrospective.py` or a
   prompt-harness document if scripting fits badly): given a corpus window, produce a
   structured report over HIS side of conversations. Dimensions (starting set — refine with
   him): under-specification rate (prompts that needed follow-up to become actionable);
   decision reversals (asked, got, then reversed); repeated questions (asked what his own
   corpus already answered); unit/mechanism misreads (the "3-per-era" class); prompts that
   produced his best-rated outcomes (what do they share); challenge-response pattern (how
   often did pushback change his decision — his ratified-pushback rate).
3. **The first retrospective report** (`retrospectives/2026-07.md`): findings as HYPOTHESES
   with evidence quotes, run past him for confirm/discard — record the discard rate (the
   calibration discipline, applied to claims about himself). End with 2–3 concrete charter
   amendments or habit changes, fed to Session 01's charter as proposals.
4. **Cadence**: monthly re-run documented in the report header; the evaluator makes it cheap.

## Capture channels & the provenance rule (settled with the operator, 16 Jul)

The corpus records only what HE authored. Three provenance classes exist on his machine:
hand-authored (web/desktop chats, Cowork sessions, interactive Claude Code, his Telegram
directives to the orchestrator — extract those from the orchestrator's event log as
operator-message payloads, read-only); machine-authored (the daemon's `claude -p` invocations
— EXCLUDED: they are versioned in git already, prompts-as-production-code); hybrid (his
authored briefs — include the artefact, not its executions). Channels, in order: account
exports = canonical; Cowork local session transcripts = harvest; a Claude Code
UserPromptSubmit hook = OPTIONAL plumbing for interactive-Code only — if used, it must record
cwd/session/timestamp so derivation can filter machine invocations out (the daemon runs under
the same user account; a naive global hook would pollute the corpus with machine prompts).
Raw captures are immutable; provenance filtering happens in `corpus/derived/`, never at
capture time. Do NOT use a preferences-text instruction for capture — an instruction is a
wish, only a hook is a check (his own doctrine), and silent gaps poison pattern recognition.

## Method notes

- Fable's strength here is disconfirming itself — every behavioural claim needs quoted
  evidence from the corpus, and the report must include a "weakest findings" section.
- Respect the observer effect honestly: the corpus is what he DID say, under old
  configurations; post-charter data will differ — note the baseline boundary.
- Volume management: start with the most recent 4–6 weeks, not everything; the evaluator
  should accept a date window.

## Done when

Corpus landed with layout + immutability rule; evaluator re-runnable; first report written,
reviewed with him, discard-rate recorded; charter proposals handed off in the log; master
table updated.
