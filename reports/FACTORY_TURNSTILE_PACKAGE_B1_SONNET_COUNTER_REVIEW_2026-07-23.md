# Factory Turnstile B1 — Sonnet counter-review

Operate read-only in
`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.

Do not edit, write, execute commands/tests, spawn subagents, commit or touch another worktree. Use
read/search tools only. Review the diff from Package A commit
`90e37d324c4b60cfa3f4e7a7f92736fcb5dd6020`.

Sealed pre-review evidence:

- candidate `e035870fd6979a2dc50a70aed65ec861c18ffdefda54dcb99b02dd18d9282fc3`
- source SHA-256 `b8fc2f79df2cdacdcc6fab9c78c256ab0d497068cf8949b7e5bc28a77c1eab9a`
- test SHA-256 `f5dbb260ea1f5011c2324346546c7b63a578c228753a2630a31c385e152d8319`
- independent host suite 183/183 passed
- py_compile and diff check passed
- production 1,067 physical lines including exports

Review B1 only: state extension, independent reviewer enforcement, exact-candidate/writer binding,
direct child process lifecycle, mutation detection, accepted-review/ledger persistence, phase
transitions, launch/stop/recovery behaviour, deep state validation and the helper refactor.

Return `PASS` or `CHANGES_REQUESTED`. Every blocker must include severity, exact file/line and a
reproducible failure scenario. Distinguish later B2/C requirements from B1 defects. State whether
B1 may freeze and B2 begin. Do not claim to run tests.
