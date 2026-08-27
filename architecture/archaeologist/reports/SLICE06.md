# Slice 06 report — reversible quarantine canary

## Outcome

Slice 06 completes the safe Archaeologist pipeline. The
`giga-archaeologist quarantine-canary` command accepts only one
`VERIFIED_CANDIDATE` reproduced from its exact four-document evidence chain and
only inside a clean, current-UID, no-remote Git fixture under the macOS scratch
tree. It cannot target the live GIGA repository.

The final canary used synthetic `src/candidate.py`. It:

1. captured the clean fixture HEAD, tree, status and exact file identity;
2. moved the tracked candidate into a private quarantine path;
3. proved Git observed the transition;
4. ran the single admitted unit-test command inside a sandbox;
5. restored the same file automatically; and
6. required the original inode, bytes, metadata, HEAD, tree and clean Git status
   before publishing `PASS`.

The test probe passed, and the quarantine receipt is
`f6b41a90c63edf054f27b48c53fee677058b72ef40a0555d88fa73e7e849e4b2`.
Complete private evidence is stored at
`/Users/admin/Documents/developer-tools/giga-archaeologist-evidence/slice06-2e4b68ac-r2`.

## Safety boundary

- The disposable marker is committed and self-hashed, and binds the exact
  target and only admitted probe command.
- The supplied Judge is recomputed byte-for-byte from inventory, hypotheses,
  counterevidence and history; a self-hashed forged decision still refuses.
- The candidate must be one tracked current-UID regular single-link file whose
  bytes match the bound inventory.
- The probe has no network authority, no repository-write authority and no
  read authority inside the operator's home directory except the disposable
  repository itself. Its only writable location is a temporary scratch folder.
- A failed probe produces `REJECT` but still requires exact restoration.
- A non-candidate, dirty repository, remote-bearing repository, non-scratch
  path, mismatched marker, drifted file or incomplete evidence refuses before
  quarantine.
- Cleanup, deletion, live GIGA quarantine, integration and deployment remain
  outside the programme.

An earlier implementation canary at `slice06-2e4b68ac` was superseded before
the milestone when the read sandbox was narrowed. It is preserved as historical
development evidence and is not the accepted Slice 06 receipt.

## Verification

Six quarantine tests cover successful restoration, failed-probe restoration,
non-candidate refusal, forged-Judge refusal, live/non-scratch refusal, and
direct sandbox denial of personal reads and repository writes. Together with
the Judge tests, the focused boundary has 12 passing tests. The complete
operations suite passes 67 tests; foundation, lint, formatting, compilation and
diff checks pass.

The canonical owner remains `modules/operations/archaeologist`; all six slices
are independently runnable and verified. No target file has been deleted.

## Knowledge graph status

The separate folder-navigation graph remains `STALE/PARTIAL`. The Archaeologist
now emits exact local paths, hashes and evidence relationships useful to that
future graph, but it deliberately remains a non-authoritative discovery and
canary pipeline rather than becoming a second graph owner.
