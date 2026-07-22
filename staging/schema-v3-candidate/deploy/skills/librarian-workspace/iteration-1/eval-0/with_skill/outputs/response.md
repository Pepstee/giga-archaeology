Filed as a **decision** (standing operational rule): `entries/2026-07-18-quiet-telegram-check-supervisor-log.md` — channel quiet >1 day → read `supervisor.log` before any restart; quiet is a symptom, restarts can destroy state. Index updated.

**Collisions:**

- **Extends, and is strengthened by, [[2026-07-16-reminder-v3-notification-trail]]**: v2's notify path is fire-and-forget and unjournaled, and you flipped `"plain": false` on 17 Jul to break the llm↔notify cycle. That makes a quiet channel doubly ambiguous — silence could mean the orchestrator died, *or* that the notify path itself broke (possibly as a side-effect of that very mitigation) while the orchestrator runs fine. Your new rule is exactly the right triage for that ambiguity, and it's one more argument for v3's journaled-notifications requirement: with a send journal, "quiet" would be diagnosable from the journal, not just supervisor.log.
- **Consistent with [[2026-07-16-standing-decisions-orchestrator]]**: this is a runbook rule, not a v2 code fix, so it doesn't violate the v2 freeze. No contradictions with any standing decision.
- One connection you may not have made: this rule is itself a candidate acceptance criterion for v3's operator channel — "silence must be distinguishable from failure" — worth carrying forward when the notification-trail reminder fires.

**Reminders:** none due today (MH725 check-in triggers 2026-07-25; the two v3 reminders trigger on v3 planning/certification, not now).
