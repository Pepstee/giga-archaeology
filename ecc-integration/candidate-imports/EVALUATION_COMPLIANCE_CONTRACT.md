# Evaluation and behavioural-compliance contract (staged, not deployed)

Portable findings from ECC's `agent-eval`, `eval-harness`, `skill-comply`, and
`verification-loop` surfaces:

1. Define capability and regression criteria before implementation.
2. Pin the task input, source revision, model/agent identity, configuration and judge versions.
3. Every scenario has at least one deterministic grader. A model grader may add interpretation but
   cannot be the only release gate.
4. Run supportive, neutral and competing-prompt scenarios to measure whether a rule is followed
   without the user restating it.
5. Preserve the ordered tool/event trace. Compliance includes temporal ordering, not merely the
   presence of expected actions.
6. Report `pass@k` (at least one success) separately from `pass^k` (all trials succeed). Critical
   paths require repeat stability, not a lucky successful retry.
7. Track cost, latency and variance beside quality; an improvement that silently multiplies cost
   or instability is not free.
8. Require accepted examples, rejected negative controls, missing-evidence cases and an explicit
   human-review lane for ambiguous or high-impact judgments.
9. Promotion binds the eval definition, traces, grader outputs and source hashes. A prose summary
   alone is not evidence.

No ECC runner, Claude subprocess, generated scenario, hook recommendation or skill is imported by
this contract.

Sources at ECC commit `96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`:

- `skills/agent-eval/SKILL.md`
- `skills/eval-harness/SKILL.md`
- `skills/skill-comply/SKILL.md`
- `skills/verification-loop/SKILL.md`
- `docs/architecture/evaluator-rag-prototype.md`
