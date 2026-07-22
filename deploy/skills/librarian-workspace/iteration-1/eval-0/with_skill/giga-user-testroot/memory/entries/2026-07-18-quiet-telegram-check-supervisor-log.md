---
type: decision
tags: [orchestrator, operations, runbook, telegram]
created: 2026-07-18
status: active
---
Operational rule: if the orchestrator's Telegram channel goes quiet for more than a day,
check `supervisor.log` **before** restarting anything. Quiet is a symptom, not a diagnosis —
restarts can destroy state, so restart-first triage is forbidden.

Rationale: silence on the channel is an ambiguous signal. Per
[[2026-07-16-reminder-v3-notification-trail]], v2's notify path is fire-and-forget and
unjournaled (and was mitigated 17 Jul with `"plain": false` in state/telegram.json), so a
quiet channel can mean the *notify path* broke while the orchestrator itself runs fine —
or the reverse. Only the log distinguishes the two; a blind restart can wipe the evidence
along with live state.

Rejected alternative: restart-first ("turn it off and on again") — rejected because it
destroys state and the diagnostic trail.

Extends the standing operational doctrine in [[2026-07-16-standing-decisions-orchestrator]]
(runbook rule, not a v2 code fix, so it does not violate the v2 freeze).
