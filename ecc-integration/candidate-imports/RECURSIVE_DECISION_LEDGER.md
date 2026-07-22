# Recursive decision ledger contract (staged, not deployed)

Repeated model rollouts can measure stability and search alternatives; they do not create truth or
approval.

Each append-only rollout records:

- rollout id and timestamp;
- prior accepted winner and watchlist;
- fresh information and its age;
- search space, methods, trial count and effective independent trial count;
- top candidates and metrics;
- marks: `accept`, `watch`, `reject`, `decay-watch`, `needs-replay`;
- coherence with prior winner and latest rollout;
- failed freshness, replay, risk or authority gates;
- live-promotion eligibility, normally false.

A candidate advances only when it beats the prior winner on a predeclared metric, deterministic
correctness/replay checks pass, risk limits are explicit, evidence is durable, and the relevant
human/authority gate approves the live step. Trading, deployment, migration, capital allocation and
destructive work default to paper, dry-run, preview or staged mode.

Source: ECC `skills/recursive-decision-ledger/SKILL.md` at commit
`96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`.
