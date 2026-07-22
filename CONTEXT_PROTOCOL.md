# Context Protocol — maintenance rules for CONTEXT.md

*Session 02 deliverable. One canonical file, many dated copies, zero platform lock-in.*

## Single-source discipline

`CONTEXT.md` in this folder is canonical. Every deployment (Claude preferences block,
ChatGPT box 1, the Telegram bot's startup read, any future surface — GPT, Kimi, local
models) is a **copy or condensation** of it, never an independent edit. If a surface's copy
is wrong, the fix happens here first, then re-deploys. The file is plain markdown with no
platform features — portability is a design law, not an aspiration.

## Tiers and cadence

| Tier | Changes | Update trigger |
|---|---|---|
| IDENTITY | rarely | on real life changes only |
| SITUATION | monthly | monthly sweep + any standing-decision change |
| ACTIVE | weekly | the Monday memory sweep may propose ACTIVE-tier edits in its report |

## Size law

One screen, forever. CONTEXT.md is the identity tier of the memory architecture — the hot
layer. Memories go to `memory/entries/`; evidence goes to `corpus/`. If this file wants to
grow, something is being filed in the wrong tier.

## Staleness rule

Every deployed copy carries its deploy date in its header line. A copy older than one month
is presumed stale — recheck against canonical before trusting it. The deployed-copies table
in CONTEXT.md records where copies live and when they were pasted.

## Verification (the recitation test)

After any deployment: ask that surface cold, "What do you know about my situation and
current priorities?" Deployment passes only if the recitation is faithful to this file —
no inventions, no omissions of the career clock, Korean deadline, or standing decisions.
Record pass/fail + date in the deployed-copies table.
