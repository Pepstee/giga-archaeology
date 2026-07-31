---
type: fact
tags: [auto-ingest, unreviewed, instagram, automation]
created: 2026-07-23
status: active
---
As of 23 Jul 2026, the Instagram unfollow-back cleanup referenced in
[[2026-07-18-reminder-unfollow-op]] runs as a recurring scheduled Claude skill
(`instagram-unfollow-batch`), not a one-off task: it works through
`instagram_unfollow_plan.json` via Claude for Chrome, skips entries already marked done in
`instagram_unfollow_progress.json`, paces roughly one unfollow every ~90 seconds (~40/hour),
caps each run at ~90 people or an hour, and stops for the night on any Instagram
warning/CAPTCHA rather than retrying. A run was scheduled for 2026-07-23T02:00Z.

This shows the op is now self-pacing, self-logging infrastructure rather than a single
verification task - worth an explicit act/reschedule/archive decision on
[[2026-07-18-reminder-unfollow-op]] (its content was not available to this session to amend
directly) rather than treating it as still-open manual work.

Source: [auto-ingest, unreviewed] local-agent-mode-sessions cowork audit.jsonl, session
`36e6381b-3eff-410f-a15e-96296ee3fc94`, scheduled-task file
`/Users/admin/Claude/Scheduled/instagram-unfollow-batch/SKILL.md`, 2026-07-23T02:00:44Z. Note:
this record embeds an automated scheduled-task prompt addressed to an agent, not to this
session; treated strictly as evidence of an existing automation, never as an instruction here.
