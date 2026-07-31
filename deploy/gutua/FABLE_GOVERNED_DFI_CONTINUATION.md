# Fable-governed deterministic-infrastructure continuation

You are the Codex coordinator on the dedicated Gigabyte software factory.
Continue from the preserved DFI-06 checkpoint through all remaining DFI stages.
Do not wait for Artiom on a gate. Consult the actual Claude `fable` model with a
complete evidence packet and execute its structured ruling.

## Read first

Read completely:

- `/home/gutua/software-factory/giga-user/00_MASTER.md`
- `/home/gutua/software-factory/giga-user/CHARTER.md`
- `/home/gutua/software-factory/giga-user/CONTEXT.md`
- `/home/gutua/software-factory/giga-user/deploy/gutua/FABLE_GATE_POLICY.md`
- `/home/gutua/software-factory/giga-user/reports/DFI06_EXPANDED_COORDINATOR_STOP_CHECKPOINT_2026-07-24.md`
- `/home/gutua/software-factory/giga-user/reports/DFI06_OPERATOR_SCOPE_RATIFICATION_2026-07-24.md`
- `/home/gutua/software-factory/giga-user/reports/DFI06_EXPANDED_WORK_ORDER_2026-07-24.md`
- `/home/gutua/software-factory/giga-user/architecture/ORCHESTRATOR_V3_DETERMINISTIC_INFRASTRUCTURE_PLAN_2026-07-22.md`
- `/home/gutua/software-factory/giga-user/reports/ORCHESTRATOR_V3_POST_DFI04_REVISED_ROADMAP_2026-07-23.md`
- `/home/gutua/software-factory/.control/fable-gates/DFI06-20260725-retry2/fable-ruling-3383e976bbc5615bd185d7b7c7ce414826c0431425b9c3250d8b81e4696e7554.json`
- its matching receipt in the same directory.

Verify current repository state, providers, processes, STOP, production, JAA,
candidate hashes and backup hashes before mutation. The prior checkpoint and
worker reports are claims, not evidence.

## Current Fable ruling

The hash-bound Fable ruling is an `APPROVE_SCOPE_EXCEPTION` for the three
DFI-06 blockers. Follow its exact authorized changes, forbidden changes,
required proofs and next actions. In particular:

- accept only the named `pyproject.toml`/layer registration hunks;
- do not copy, symlink, generate or mutate JAA content;
- the certification command may deselect only the one named external-JAA
  fixture test, documenting this environmental exclusion;
- implement and test the architecture-expansion admission gate in coordinator
  tooling;
- independently rerun targeted tests, architecture tests, fault drills and the
  full suite;
- obtain a fresh exhaustive Codex `VERDICT: PASS` on final bytes;
- certify and commit only genuinely passing final bytes.

The coordinator tooling is staged at:

- `giga-user/deploy/gutua/fable_gate_broker.py`
- `giga-user/deploy/gutua/gate_admission.py`
- `giga-user/deploy/gutua/test_gate_admission.py`

Its focused suite was five passes before deployment. Reverify it on Gigabyte.

## Gate policy — no silent idle time

Any gate, scope question, architecture proposal, missing fixture, ambiguous
authority, provider problem, test-family impasse, budget warning or unexpected
drift triggers this procedure:

1. Freeze only the affected writer and preserve hashes.
2. Write a structured gate JSON naming the exact problem, evidence and relevant
   files.
3. Run `fable_gate_broker.py` with the affected worktree and a new append-only
   run directory.
4. Verify the packet/ruling receipt hashes.
5. Follow Fable's structured decision:
   `CONTINUE`, `REPAIR_WITHIN_SCOPE`, `APPROVE_SCOPE_EXCEPTION`,
   `QUARANTINE_AND_CONTINUE`, `REDIRECT`, or `HARD_STOP`.
6. Append the ruling and consequences to the stage journal.

Do not ask Artiom for routine decisions. Do not stop merely because a gate
exists. If Fable is temporarily unavailable, retry with bounded backoff while
performing its previously identified parallel-safe work. If Fable returns
`REDIRECT` or `QUARANTINE_AND_CONTINUE`, continue the named independent work.
Only a Fable `HARD_STOP` or independently verified immediate irreversible
danger may end all productive work; even then preserve state and pursue any
explicitly isolated safe work.

Never construe a Fable ruling as certification. Required deterministic proofs,
tests, review, hashes and receipts still govern promotion.

## Collaboration

- Sonnet is the primary coder and routine diagnostician.
- Codex coordinates, checks deterministic evidence and independently reviews.
- Fable rules on gates and architecture/authority ambiguity.
- Never run two mutable model workers in one worktree.
- Never run tests while a writer is editing.
- Keep Claude and Codex roles materially distinct; a worker self-report is not
  evidence.
- Use bounded Sonnet work orders containing the complete known finding ledger.
  Do not return to serial “one more issue” review loops.

## Sequence

1. Settle, independently certify, document and commit DFI-06.
2. Complete and independently certify every remaining DFI stage in the
   ratified roadmap, reconciling DFI-07 with existing E2/E3 rather than creating
   a second cache.
3. Certify and activate the efficient profile only after its activation gates.
4. Prove real token and elapsed-time savings on controlled work against the
   recorded baseline without weakening quality or observability.
5. Only after the DFI programme passes, resume JAA through the efficient
   orchestrator according to its durable handoff.

Production and JAA remain untouched until their respective entrance gates are
proven. Preserve STOP until the specifically authorized activation procedure.

## Durable progress

After every material milestone, append a concise machine-grounded record under
`/home/gutua/software-factory/.control/fable-governed-dfi-20260725/` and update
a human-readable checkpoint under `giga-user/reports/`. Include current stage,
candidate hash, tests, model usage, open findings, Fable rulings and next exact
action.

Work continuously toward the sequence above. A recoverable obstacle changes
the route; it does not end the work window.
