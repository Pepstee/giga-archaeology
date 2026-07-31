# Software-factory work priority policy — 2026-07-29

**Recorded at:** 2026-07-29T11:34:02+01:00

The operator established this priority order:

1. **JAA**
2. **DFI**
3. **Everything else**

## Allocation rules

- JAA may consume as many justified model calls, agents, tokens and work
  packages as required. It has no artificial usage throttle.
- DFI may use multiple agents when parallel work is genuinely independent and
  the expected speed or assurance return justifies the coordination cost.
- Everything outside JAA and DFI is limited to one active agent at a time.

## Safety-preserving interpretation

- JAA receives first claim on contested model capacity.
- Parallel agents use isolated scopes or worktrees, explicit ownership and one
  integration writer per mutable branch. No two agents may make overlapping
  edits.
- Claude/Fable remains a specialised shared lane with one host-wide serialized
  invocation at a time. This protects transcripts, OAuth state and ruling
  lineage; it is not a token or usage throttle.
- Deterministic tests, exact-source checks, STOP protection, external-action
  gates and certification standards remain unchanged.
- Fable remains unavailable until its documented reset at
  `2026-07-30T04:00:00+01:00`; Sol remains temporary deputy until then.

