# Factory Turnstile v1 — scope and budget addendum

The original 750-production-line ceiling was set before decomposition. Package A alone requires
approximately 710 readable lines to implement durable state, exact candidate identity, process
leases, recovery and bounded stop semantics. Retaining the original total would force the review,
single-flight test, context, allocation and CLI contracts into roughly 40 lines, which is neither
credible nor auditable.

The revised ceiling for the **complete** controller is **1,500 physical production lines** across
`factory_control/*.py` and `scripts/factory_turnstile.py`. Tests and documentation are excluded.
This is a ceiling, not a target. Duplication must still be refactored.

The stronger anti-entropy gate is scope:

- one stage at a time;
- one exclusive model operation at a time;
- exact candidate sealing and hand-off;
- independent review;
- truthful single-flight test receipts;
- bounded context packs;
- work-allocation reporting;
- explicit certification, pause, stop and recovery.

The controller must not acquire queues, autonomous scheduling, retries, task decomposition, model
routing, prompt generation, daemon loops, project planning, plugin systems or general orchestration.
Those belong to orchestrator-v3. Adding any such feature is a no-go regardless of line count.

This addendum supersedes only the original 750-line ceiling. Every safety and verification
requirement in `FACTORY_TURNSTILE_V1_WORK_ORDER_2026-07-23.md` remains binding.
