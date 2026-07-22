---
type: decision
tags: [orchestrator, operations, telegram, runbook]
created: 2026-07-18
status: active
---
Operational rule: if the orchestrator's Telegram channel goes quiet for more than a day,
check supervisor.log BEFORE restarting anything. Quiet is a symptom, not a diagnosis —
a restart can destroy exactly the state that would have explained the silence.

Related: [[2026-07-16-standing-decisions-orchestrator]] (same instinct as the v2 freeze:
every intervention carries STOP-window/fence/state risk, so diagnose before touching);
[[2026-07-16-reminder-v3-notification-trail]] (a quiet channel has two distinct failure
modes — orchestrator actually stuck vs. notify path dead — and supervisor.log is what
disambiguates them).
