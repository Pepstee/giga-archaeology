# JAA + DFI remote lane restoration — 2026-07-28

## Outcome

Both independent Gigabyte software-factory lanes were restored from preserved
evidence and are executing under WSL user systemd.

Launch time: 2026-07-28 04:10 BST  
Shared deadline: 2026-07-28 16:10:32 BST  
Systemd runtime backstop: 12 hours 15 minutes

## Reconciled state

### DFI

- The operator's privileged DFI-08R7 drill was verified on disk:
  `dfi08r7_a2_ro02_privileged_20260726T151901Z.xml`, root-owned, one pass.
- DFI-08R7 is certified at
  `6c15f468dc1830f81a1d1901edf73819819aa5ba`.
- DFI-09 is certified at
  `df899d9a0e40cd8821746a47c1144657737b29ac`.
- The resumed lane begins from the clean DFI-09 worktree and is instructed to
  create a separate DFI-10 worktree/branch before mutation.

### JAA

- The current worktree is clean at Package 016:
  `a4f44905323abd21f926341e35263a478d381cf4`.
- JAA-04 remains uncertified pending one newly authorised build-004,
  successful 30-dossier publication and revision-bound certification.
- Preserved failed corpus builds remain evidence and are prohibited from reuse
  or relabelling.

## Stale-process correction

The expired `jaa-main-9h-tail-20260727.service` was waiting forever because
`jaa04-fresh-v5-8fdb25c.service` was `active (exited)`. Both stale transient
units were stopped. The failed expired twelve-hour supervisor was reset.
No worktree or evidence directory was deleted.

## Active units

- `giga-jaa-resumed-20260728.service`
  - invocation `4d18659ad3b2471ba8aee63beaea89ca`
  - control:
    `/home/gutua/software-factory/.control/resumed-dual-lane-20260728/jaa`
- `giga-dfi-resumed-20260728.service`
  - invocation `c021da6a9d78414fb8939a93092a67d9`
  - control:
    `/home/gutua/software-factory/.control/resumed-dual-lane-20260728/dfi`

Both units were verified as `active (running)` with live `codex exec` process
trees and growing `round-01/events.jsonl` files. Claude work is serialised
through the existing host-global lock.

## Resume work-order identities

- DFI prompt SHA-256:
  `5c29bd1e266616c99de4131b0d42e75c8edb2ecd850b8773e15c2c5c8c02208f`
- JAA prompt SHA-256:
  `338aef977974818adcf9dd991432a2b1278170ea7ee39c57586684f4f2c33030`

The Mac and Gigabyte copies were hash-compared and match.

## Read-only monitoring

```bash
systemctl --user status giga-jaa-resumed-20260728.service --no-pager
systemctl --user status giga-dfi-resumed-20260728.service --no-pager
tail -f /home/gutua/software-factory/.control/resumed-dual-lane-20260728/jaa/round-01/events.jsonl
tail -f /home/gutua/software-factory/.control/resumed-dual-lane-20260728/dfi/round-01/events.jsonl
```
