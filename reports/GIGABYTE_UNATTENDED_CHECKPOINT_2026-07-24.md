# Gigabyte unattended checkpoint — DFI-06 to DFI-07

Prepared: 2026-07-24

## Verdict

The Gigabyte is prepared to continue independently after the Mac disconnects.
One bounded Sonnet writer is completing expanded DFI-06. A persistent Codex coordinator
is waiting behind it and cannot overlap it. When Sonnet exits or reaches its 45-minute
runtime ceiling, the coordinator will inspect the real candidate, complete and certify
DFI-06, then create and execute the bounded DFI-07 work order.

The unattended window has an absolute deadline of
`2026-07-24T22:48:47Z` (`23:48:47` UK summer time). It may finish earlier. Restart attempts
are capped at three; the deadline survives service restarts.

## Active services

- Current sole writer:
  `dfi06-expanded-polish-20260724.service`
  - Sonnet
  - 45-minute runtime maximum
  - DFI-06 worktree only
  - no commit authority
- Follow-on coordinator:
  `codex-gigabyte-dfi06-dfi07-20260724.service`
  - Codex
  - 14-hour absolute window
  - `Restart=on-failure`, but wrapper restart ceiling = 3
  - waits without model use while the Sonnet service is active

## Safety state at arming

- Production orchestrator git status: clean
- Production HEAD: `35efb19`
- STOP SHA-256:
  `b9fd288d7acdf65e8169f99ffb64e8ffc587e91cdfe4ac59c900c782878c13d7`
- JAA path changes: 0
- DFI-06 dirty expansion: preserved, archived and hash-recorded
- Disk: approximately 905 GiB free at the last check
- Gigabyte AC power: online
- Windows AC sleep timeout: disabled
- Windows AC hibernate timeout: disabled
- Display timeout: 30 minutes; display shutdown does not stop the services

## Authorised autonomous sequence

1. Complete the already-started bounded Sonnet repair.
2. Run the 189-test DFI-06 targeted suite.
3. Close remaining findings without another architecture expansion.
4. Run fault drills, static contract checks and the complete orchestrator suite.
5. Run one fresh exhaustive Codex review; bounded repair/delta review only if necessary.
6. Write the DFI-06 certificate and commit the branch without merging or activating it.
7. Create DFI-07 from that certified commit.
8. Reconcile DFI-07 with E2/E3 so there is one deterministic-reuse mechanism.
9. Implement, test, independently certify and commit DFI-07 if all gates pass.
10. If time remains, harden/re-verify DFI-06 and DFI-07 or prepare—but do not implement—
    DFI-08.

Production activation, JAA mutation and STOP removal are forbidden during this run.

## Hard stop conditions

The coordinator must leave a resumable checkpoint instead of improvising if:

- STOP changes or production/JAA becomes dirty;
- a second mutable worker appears;
- DFI-06 or DFI-07 leaves its ratified boundary;
- a line budget is breached;
- provider authentication/quota prevents the assigned role;
- review demands another architecture expansion;
- a required authority or candidate binding cannot be proved.

## Monitoring

From a later SSH session:

```bash
wsl.exe -d Ubuntu -- bash -lc \
  'systemctl --user status dfi06-expanded-polish-20260724.service \
   codex-gigabyte-dfi06-dfi07-20260724.service --no-pager'
```

Coordinator activity:

```bash
wsl.exe -d Ubuntu -- bash -lc \
  'tail -n 80 /home/gutua/software-factory/.control/gigabyte-dfi06-dfi07-20260724/activity.jsonl'
```

Final coordinator message:

```bash
wsl.exe -d Ubuntu -- bash -lc \
  'cat /home/gutua/software-factory/.control/gigabyte-dfi06-dfi07-20260724/final.txt'
```

The systemd services run on the Gigabyte. Closing the Mac, Codex desktop, RustDesk, SSH,
or Tailscale on the Mac does not terminate them.
