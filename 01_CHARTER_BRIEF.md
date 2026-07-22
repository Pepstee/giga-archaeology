# Session 01 — The Unified Operator Charter

*Read `00_MASTER.md` first. Mission: Artiom's orchestrator has a constitution with machine
checks; his Claude has two lines of preferences; his ChatGPT has none. Produce ONE operator
charter and deploy it to all three surfaces. This is the highest-leverage evening in the
programme — it defines the voice every later session speaks in.*

## Deliverables (all four, in this folder + deployed)

1. `CHARTER.md` — the canonical document. **Policies, not constants** (no "respond in N
   characters" cargo cult): default register, depth rule, challenge mandate, evidence
   standards, formatting defaults, assumption-handling, what-to-always-surface.
2. `deploy/claude_preferences.txt` — condensed for Claude's personal-preferences field, and
   WALK HIM THROUGH pasting it (Settings → Profile → preferences).
3. `deploy/chatgpt_custom_instructions.txt` — the two-box format (about-me / how-to-respond),
   same charter, that surface's constraints.
4. `deploy/v3_operator_model.md` — the machine-readable variant staged for orchestrator-v3's
   future operator-model capability (do NOT touch the orchestrator repos; stage it here).

## Method

1. **Start from DATA, not impressions — there is deliberately no personal profile in
   00_MASTER.** Your two evidence sources: the extracted corpus (`corpus/raw/prompts_*.jsonl`,
   545 hand-authored prompts — mine it for how he actually writes, what he asks for, what he
   corrects) and the interview below. Any behavioural claim you form must cite corpus
   evidence or his explicit answer; characterisation without evidence is the failure mode
   this whole programme exists to kill.
2. **Interview him — deep, not a form.** Cover at least: how hard should pushback be, and on
   what topics is it unwelcome; when does he want one-line answers vs essays; what should
   NEVER be assumed; which past AI responses does he remember as excellent or terrible, and
   why (get 2–3 concrete examples each — they're worth more than any abstraction); how should
   uncertainty be expressed; what standing goals should shape every answer (career clock).
3. **Draft the charter with him in the loop** — each clause traceable to either an observed
   pattern or his explicit answer. Include a "challenge mandate" section: the evidence says he
   ratifies good disagreement; encode the licence AND its limits.
4. **Deploy all three variants**, then run the **test protocol**: take 3 real prompts from his
   recent usage, run them under old and new configuration, have him judge blind which
   response serves him better. The charter ships only if it wins.
5. Set a revision trigger: the charter is versioned here; Session 04's retrospectives feed
   amendments to it (note the seam in your log).

## Done when

`CHARTER.md` exists and is deployed to both live surfaces; the A/B test is run and recorded;
the v3 variant is staged; `SESSION_LOGS/01_log.md` written; master table updated.
