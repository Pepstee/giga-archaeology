# DFI-12 operator peak and activation-threshold ratification — 2026-07-30

**Recorded at:** 2026-07-30T18:32:23+09:00  
**Peak statement SHA-256:** `1e452bed2767c8c9720d9a728efc56f50eaf6d3165e743127530358cd37e001e`  
**Threshold statement SHA-256:** `305788d3d56b4fbc60019c8811cc5e45b640858349562f5d394dfdb321d87a49`

## Operator statements

The operator first supplied the complete ratification with an incorrect
`5,899` peak. That statement was refused and no DFI-12 worktree or mutation
was created.

The operator then corrected the peak to `5,299`. The corrective message
omitted only the leading `I` before `, the operator`; the immediately preceding
message supplied that leading character and every other term. The durable
normalized statement below records the unambiguous combined correction while
preserving this normalization disclosure:

> I, the operator, ratify a temporary programme peak of 5,299 net lines
> exclusively for DFI-12 active incremental certificates, expiring at DFI-12
> post-commit certification, conferring no downstream headroom and no claim
> against the reserved >=1,979-line cutover retirement tranche, bound to gate
> packet sha256
> 8adbaa1b9acd02c4df89473598be9940bd6c2f1f9fdfe54bd352ad00b9e96197
> and to the DFI-12 Fable admission ruling sha256 recorded in the activation
> receipt.

The operator also stated exactly:

> I also ratify the DFI-12 activation threshold of at least 25% measured
> judge-token reduction on the delta-eligible subset, with complete telemetry,
> 100% material-verdict parity, zero material-finding loss, and missing
> telemetry failing the gate.

## Activated authority

This ratification activates only the conditional DFI-12 admission:

- gate: `DFI12-ADMISSION-DRAFT-20260730`;
- gate packet SHA-256:
  `8adbaa1b9acd02c4df89473598be9940bd6c2f1f9fdfe54bd352ad00b9e96197`;
- Fable ruling SHA-256:
  `a02ecf55964c8d503f84826fd66e6ea19ad4fa127f1c9731534facd280c6c142`;
- certified base:
  `17d1b23bb617a2b775ba54a37747ed6dabee0b76`;
- temporary programme peak: at most `5,299` net production lines;
- DFI-12 gross additions: at most `700`;
- DFI-12 net additions: at most `650`, with net line `651` a hard stop;
- activation quality threshold: at least `25%` measured judge-token reduction
  on the delta-eligible subset, complete telemetry, `100%` material-verdict
  parity and zero material-finding loss;
- scope: DFI-12 active incremental certificates through DFI-12 post-commit
  certification only.

## Authority not granted

This decision does not authorise DFI-13 or later stages, production cutover,
STOP/service/daemon/epoch mutation, JAA access, push, canonical merge,
deployment, any delta-only integration or release certificate, modification
of `agents/judge.py` or `control/workflow_compiler.py`, or any claim against
the reserved `>=1,979`-line cutover retirement tranche.
