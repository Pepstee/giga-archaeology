# JAA historical Package 020–024 failure audit

You are a read-only independent Codex auditor. Work only in the detached
snapshot:

`/home/gutua/software-factory/.worktrees/jaa-package-audit-20260728`

The snapshot is exact commit
`894484336111913ea728985f13e1dbfed35448fd`. Do not edit, stage, commit, create
branches, mutate runtime evidence, call Claude/Fable, access public networks or
perform consequential actions.

## Objective

Explain exactly why the broad JAA-05 run reports five failures and eighteen
errors in Package 020–024 tests while the current focused JAA-05 production
ingestion tests pass.

Determine, with file/line and evidence references:

1. Which results are deliberate one-shot/state-dependent historical contracts.
2. Which are stale evidence bindings caused by later accepted runtime state.
3. Which, if any, reveal a current product-code regression at commit `8944843`.
4. The correct certification treatment for every failing/erroring test:
   rerun in a reconstructed immutable fixture, mark as historical non-rerunnable
   evidence, repair the test contract, or block certification.
5. The smallest safe remediation, if remediation is genuinely needed.

Read only the relevant repository instructions, Package 020–024 tests and the
specific control artefacts they bind. Do not sweep unrelated corpora or repeat
large suites. Verify claims with hashes and focused read-only commands.

Return a concise but complete final audit with a result table and explicit
`BLOCKS_CURRENT_JAA05_CERTIFICATION: YES|NO`. The final response is captured
durably by the outer service.
