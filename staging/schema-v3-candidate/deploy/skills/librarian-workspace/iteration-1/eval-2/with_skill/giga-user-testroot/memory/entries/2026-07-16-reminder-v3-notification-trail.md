---
type: reminder
tags: [orchestrator-v3, notifications, v2-hole]
created: 2026-07-16
status: active
---
When v3's notification/operator-channel capability is planned or certified, verify two v2 holes
died: (1) **notifications must be journaled** — v2's `infra/notify.py` is fire-and-forget, so a
16 Jul incident hunt ("who keeps telling me to log in?") required archaeology across two other
logs, and the overseer was wrongly suspected because the real sender (`infra/llm.py` auth
fail-fast) leaves no trace; every outbound message needs a durable send record (ts, sender
component, channel, verbatim text). (2) **Provider-correct remedies** — v2 hard-codes "run
`claude login`" in the auth alert regardless of which provider failed, producing the nonsense
"lost access to Codex — run claude login". Both frozen in v2 by doctrine; fix belongs to v3.
Related: one Telegram channel carries multiple senders under one name — v3 should attribute
messages to their component. (3) **No self-calling error handlers in the notify path** — v2's
plain-speech rewriter calls the LLM from inside notify(); the LLM's failure handler calls
notify() back (llm.py↔notify.py cycle), so a failing rewrite can itself emit the untraceable
"run claude login" alerts that flooded the night of 16–17 Jul. Mitigated 17 Jul by setting
`"plain": false` in v2's state/telegram.json (config-only, reversible; also the experiment —
alerts stopping proves the mechanism, alerts continuing arrive raw and name their true sender).
[[2026-07-16-standing-decisions-orchestrator]]
