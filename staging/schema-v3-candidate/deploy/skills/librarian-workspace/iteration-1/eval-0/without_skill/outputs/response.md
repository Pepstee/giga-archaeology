Filed as a standing decision: `entries/2026-07-18-orchestrator-quiet-check-log-first.md` — if the orchestrator's Telegram channel is quiet for more than a day, read supervisor.log before restarting anything; quiet is a symptom, restarts can destroy state. INDEX.md updated.

Two collisions worth noting:

1. It rhymes with the v2-freeze rationale in [[2026-07-16-standing-decisions-orchestrator]] — same underlying rule: every intervention carries STOP-window/state risk, so diagnosis always precedes action. This entry is effectively the runtime counterpart of that build-time decision.

2. It sharpens [[2026-07-16-reminder-v3-notification-trail]] — a quiet channel actually has two distinct failure modes: the orchestrator is genuinely stuck, or the notify path itself died (the 16 Jul "phantom login alerts" class of hole). supervisor.log is what disambiguates them. When v3 plans its operator channel, this suggests a concrete acceptance criterion beyond notify-journaling: a heartbeat or liveness signal, so silence becomes distinguishable from failure instead of requiring a human to notice a quiet day. I've left that as a note here rather than filing it as a separate idea — say the word and I'll promote it.
