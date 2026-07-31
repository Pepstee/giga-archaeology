---
type: decision
tags: [software-factory, JAA, DFI, agents, model-allocation, priority]
created: 2026-07-29
status: active
---
Artiom set the software-factory priority order to: (1) JAA, (2) DFI, and
(3) everything else.

JAA has no artificial model, agent or token throttle. DFI may use multiple
agents when independent partitioning and the expected return justify it.
Everything else is limited to one active agent at a time.

The host-wide one-worker rule applies to the specialised Claude/Fable lane,
not to Codex as a whole. Claude/Fable calls remain serialized for OAuth,
transcript and ruling-lineage integrity; parallel mutable work still requires
isolated ownership and one integration writer per branch.

Source: direct operator instruction on 2026-07-29, recorded in
`reports/FACTORY_WORK_PRIORITY_POLICY_2026-07-29.md`.

This clarifies the execution allocation for
[[2026-07-29-dfi11-peak-ratification]] and extends
[[2026-07-26-dfi09-operator-ratification]] without weakening its assurance
gates.

