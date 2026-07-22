---
type: fact
tags: [corpus, giga-programme, milestone]
created: 2026-07-16
status: active
---
The owned prompt corpus is complete as of 16 Jul 2026: 2,584 hand-authored prompts across two
channels (cowork 566, claude-web 2,018), spanning June 2024 → July 2026, extracted with
provenance filtering (machine sessions excluded, replays deduplicated) by
`scripts/extract_prompts.py`. Raw web export (incl. `memories.json`, project docs) preserved
immutably under `corpus/claude-export/`. This is the concrete realisation of the founding
idea [[2026-07-16-wow-elvui-edge]] — the "owned corpus" leg of the durable edge now exists as
files, not intention. Feeds Session 01 (charter evidence) and Session 04 (retrospectives).

UPDATE (as of 2026-07-19): the canonical prompt snapshot has grown to 2,983 records across
three harvested channels/register sources: 787 Cowork, 2,120 Claude web/design, and 76
Codex-only desktop turns. The original 2,584 figure remains the 16 Jul milestone, not the
current count. Source: `corpus/inbox/daily_delta_2026-07-19.jsonl` (120-record batch;
claude-web sessions and local Cowork audit sessions) reconciled with
`corpus/raw/prompts_20260719.jsonl` and `corpus/MANIFEST.md`.

UPDATE 2 (as of 2026-07-19): the historical ChatGPT export raises the canonical snapshot to
20,107 records: 17,109 ChatGPT-web human text turns plus 2,998 current Claude/Cowork/Codex
turns. Its canonical two-sided view holds 35,678 text turns across 2,644 conversations,
spanning Sep 2023–Dec 2025. It does not contain 2026 ChatGPT history or retained conversation
text before Sep 2023. Source: `corpus/raw/chatgpt_prompts_20260719.jsonl`,
`corpus/transcripts/chatgpt_conversations.jsonl`, and `corpus/MANIFEST.md`.

UPDATE 3 (as of 2026-07-20): the latest canonical snapshot now contains 20,358 records:
17,109 ChatGPT-web, 2,120 Claude-web/design, 787 Cowork and 342 Codex-only desktop turns.
The 251-record increase since the prior manifest is entirely additional Codex capture.
Source: `corpus/raw/prompts_20260719.jsonl` physical-line and channel counts, verified
2026-07-20; `corpus/MANIFEST.md` updated in the same sweep.
