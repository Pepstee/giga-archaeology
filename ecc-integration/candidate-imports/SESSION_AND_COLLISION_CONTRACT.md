# Session snapshot and collision-advisory contract (staged, not deployed)

## Canonical read-only session snapshot

Harness-specific session readers should normalize into a versioned JSON snapshot containing:

- adapter id and schema version;
- session id, kind, lifecycle state and source target;
- workers with separate lifecycle `state` and operational `health`;
- runtime identity, declared intent, outputs and artifact references;
- derived worker/state/health aggregates that exactly reconcile with worker records.

Unknown optional scalars use `null`; unknown lists use empty arrays. Adapter-specific details stay
nested. Consumers branch on schema version and do not infer tmux, Git, worktree or Markdown
semantics from undocumented fields.

## Pre-conflict collision advisory

For multiple workers, calculate collision risk from independently inspectable channels:

- edited line/file overlap;
- dependency coupling between touched files;
- directory-tree proximity as a weak prior;
- later, intent look-ahead or symbol/call coupling when proven.

Combine channels deterministically and expose the component scores. Two thresholds create:

- `clear`: no action;
- `traffic-advisory`: exchange intent and evidence;
- `resolution-advisory`: recommend deterministic right-of-way.

During extraction this contract grants no authority to message, stop, steer or reprioritise an
agent. Any later steering requires the deferred execution/authority gate and explicit collision
fixtures.

Sources: ECC `docs/SESSION-ADAPTER-CONTRACT.md` and `docs/design/agent-proximity.md` at commit
`96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`.
