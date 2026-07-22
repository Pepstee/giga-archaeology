# ECC status contract mapping (staged, not deployed)

| ECC field | Giga-user interpretation | Decision |
|---|---|---|
| `context` | Task, model, repository, worktree, context pressure | Adopt concept; never infer missing values |
| `toolCalls` | Recent and pending tool operations | Adopt concept as receipt-derived status |
| `activeAgents` | Active workers, objective, isolation and handoff paths | Adopt concept; orchestrator remains authoritative |
| `todos` | Current in-progress work and pending gates | Adopt concept |
| `checks` | Named local/remote verification with evidence links | Adopt concept and require timestamps |
| `cost` | Tokens, spend, budget and trend | Reference until trustworthy provider telemetry exists |
| `risk` | Dirty state, stale calls, conflicts and manual-review flags | Adopt concept; unknown is not green |
| `queueState` | PR, issue, conflict and promotion queues | Reference; do not create tracker work automatically |
| `sessionControls` | Explicitly supported create/resume/status/stop/diff actions | Adopt capability declaration, not action authority |
| `sync` | Durable GitHub/Linear/handoff publication state | Adopt only as receipts of completed sync |

Source: ECC `docs/architecture/hud-status-session-control.md` at
`96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`. The useful rule is that unavailable signals remain
unavailable; adapters must never paint missing evidence green.
