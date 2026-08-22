# ArtVault on Gigabyte — deployment receipt — 2026-08-20

**Status:** COMPLETE — the separate WSL entity, filesystem boundary, Linux identity, SSH
identity, startup task, independent Codex credential and direct Tailscale access are deployed and
verified. Claude Code remains installed but intentionally logged out because the operator does not
use it and explicitly removed it from scope on 2026-08-21. Serge's separate Windows administrator
account is provisioned. Cold-reboot, first-login and recovery drills are recorded separately as
recommended operational follow-ups; they are not completion requirements of the stated ArtVault
objective.

This is a distinct receipt rather than an amendment to
`GIGABYTE_MIGRATION_COMPLETION_2026-07-22.md`. That record covers the existing Ubuntu software
factory. ArtVault has a different virtual disk, user, remote identity, credential lifecycle,
startup mechanism and Windows-account boundary.

## Intended boundary

ArtVault is a headless Ubuntu WSL2 entity owned by the existing Windows account
`admin\gutua`. It holds its own OpenAI/Codex session and is remotely entered as Linux user `art`.
A separate Windows account for Serge has full local
administrator capability for engineering work while not normally seeing ArtVault's WSL
registration or filesystem. That separate account is now provisioned; its first physical login
and password replacement remain for Serge.

This design protects against ordinary use and accidental interference. It does **not** attempt
to resist a determined or compromised Windows administrator.

## Verified live state

Evidence below was read from the Gigabyte on 2026-08-20 after deployment. The final hardened
bootstrap completed at `2026-08-20T11:25:21Z`; the post-bootstrap verifier and targeted live
probes ran through `2026-08-20T11:32:33Z`. Completion probes ran again through
`2026-08-21T01:18:44Z`. This describes live state, not merely the intended state in the bootstrap
scripts.

### Windows host and WSL registration

| Item | Verified value |
|---|---|
| Host OS | Microsoft Windows 11 Home, version `10.0.26200`, build `26200`, 64-bit |
| Host volume protection | `C:` 100% BitLocker-encrypted, protection on, XTS-AES 128 |
| User Account Control | enabled |
| WSL distribution | `ArtVault`, WSL version 2, running |
| Registration owner | Current-user WSL registry of `admin\gutua` |
| Distribution base path | `C:\VirtualEntities\ArtVault` |
| Virtual disk | `C:\VirtualEntities\ArtVault\ext4.vhdx` |
| Virtual disk current host-file length | `3,965,714,432` bytes |
| Guest block-device capacity | `274,877,906,944` bytes (256 GiB) |
| Guest root filesystem size | `269,427,478,528` bytes |
| Default Linux UID | `1000` |

The existing `Ubuntu` WSL2 distribution remains separately registered at
`C:\Users\gutua\AppData\Local\wsl\{33dd9ee6-3276-4f93-8993-13240a8643ff}`. It was running and
reachable as `gutua` at the receipt snapshot. Existing personal-capture watcher/review processes
and the TransitVPN-v3 factory daemon were also observed running. This proves those workloads
survived the ArtVault deployment snapshot; it is not a broader correctness certification of
their work.

### ArtVault guest identity and tools

| Item | Verified value |
|---|---|
| Guest OS | Ubuntu 24.04.4 LTS |
| Hostname | `artvault` |
| Operator | `art`, UID/GID `1000:1000`, home `/home/art`, shell `/bin/bash` |
| Privilege | member of `sudo`; `/etc/sudoers.d/90-artvault-operator` grants passwordless sudo |
| Node.js | `v22.23.2` |
| Tailscale | `1.102.3` |
| Claude Code | `2.1.237` |
| Codex CLI | `0.148.0` |
| Bootstrap marker | `/var/lib/artvault/bootstrap-v1.complete` |
| Bootstrap completion time | `2026-08-20T11:25:21Z` |

Private entity locations and modes were verified as:

```text
art:art 0700 /home/art/.ssh
art:art 0600 /home/art/.ssh/authorized_keys
art:art 0700 /home/art/.claude
art:art 0700 /home/art/.codex
art:art 0750 /srv/artvault
```

No project tree or provider credential store was copied from the existing Ubuntu distribution.

The hardened bootstrap now makes the reproducible inputs explicit:

- Node.js is pinned to `v22.23.2`; the downloaded archive is verified against Node's published
  `SHASUMS256.txt` before extraction.
- Claude Code is installed as the unprivileged `art` user from the exact npm version
  `@anthropic-ai/claude-code@2.1.237`.
- Codex is installed as `art` with the official installer constrained by
  `CODEX_RELEASE=0.148.0`.
- Tailscale remains sourced from its signed stable Ubuntu repository rather than being version
  pinned; `1.102.3` is the version observed in this deployment.

After installation, the bootstrap fails closed if `sshd -t` fails, if any required effective
SSH setting is absent, if `/mnt/c` or `cmd.exe` is available, if `WSL_INTEROP` is present in the
ArtVault process environment, if credential-directory ownership or modes differ from the values
above, or if SSH/Tailscale are not both enabled and active. It records the resulting versions and
public-key fingerprint only after those assertions pass. The global WSLInterop binfmt entry may
be visible because WSL distributions share a kernel and the existing Ubuntu distro enables
interop; it is informational and is not evidence that ArtVault has an interop socket/environment.

### Guest-to-host isolation

`/etc/wsl.conf` is live with systemd enabled, Windows-drive automount disabled,
`mountFsTab=false`, Windows interoperability disabled, Windows PATH injection disabled, default
user `art`, and hostname `artvault`. Disabling fstab processing closes a second automatic-mount
path rather than relying only on `[automount] enabled=false`.

Runtime probes passed:

```text
windows_mount=absent
windows_interop=absent
```

This prevents routine access from ArtVault to `C:` and prevents invoking Windows executables
from the guest. It does not create a hostile-host security boundary: Windows still owns and runs
the WSL virtual disk.

### SSH identity

OpenSSH is enabled and active. Its effective configuration was verified as:

```text
permitrootlogin no
pubkeyauthentication yes
passwordauthentication no
kbdinteractiveauthentication no
allowusers art
x11forwarding no
allowagentforwarding no
allowtcpforwarding no
gatewayports no
permittunnel no
maxauthtries 3
allowstreamlocalforwarding no
disableforwarding yes
```

`X11Forwarding`, SSH-agent forwarding, TCP forwarding, Unix-domain socket forwarding and SSH
tunnel devices are therefore unavailable to the `art` login. The blanket
`disableforwarding yes` setting reinforces those individual restrictions. `gatewayports no` is
also effective. The bootstrap explicitly asserts every item above except `gatewayports no`,
which is an independently verified OpenSSH effective default and is additionally rendered moot
for remote listeners by both `allowtcpforwarding no` and `disableforwarding yes`.

The dedicated client key is stored on the operator's Mac at:

```text
/Users/admin/.ssh/artvault_ed25519
/Users/admin/.ssh/artvault_ed25519.pub
```

Only the public key is installed in ArtVault. The local public key and installed authorized key
have the same fingerprint:

```text
SHA256:tXXvFap3rm4Vzz4FoWL7Xvi/1rfjtTmUhjCUOPLfKhw
```

The public key is embedded in the reproducible bootstrap as non-secret provisioning data. Each
bootstrap run replaces `/home/art/.ssh/authorized_keys` with exactly that one public-key line,
sets `art:art` ownership and mode `0600`, verifies the enclosing SSH directory and credential
directory modes, and records the installed fingerprint in the bootstrap marker. The independent
Mac-side verifier then compares that live fingerprint with
`/Users/admin/.ssh/artvault_ed25519.pub`. The private key is never transmitted by the bootstrap.

The private key content is deliberately absent from this repository and receipt.

### Windows filesystem ACL

The owner-hardening step is complete:

| Path | Owner | Inheritance | Access entries |
|---|---|---|---|
| `C:\VirtualEntities` | `admin\gutua` | protected | `SYSTEM:F`, `admin\gutua:F` |
| `C:\VirtualEntities\ArtVault` | `admin\gutua` | inherited from parent | `SYSTEM:F`, `admin\gutua:F` |
| `C:\VirtualEntities\ArtVault\ext4.vhdx` | `admin\gutua` | inherited from parent | `SYSTEM:F`, `admin\gutua:F` |

`Users`, `Authenticated Users`, `Administrators` and the deployed `serge` account have no
access-control entry on this tree. The final verifier independently reported
`serge_has_direct_vhd_ace=false`. Explicit deny rules were deliberately avoided; absence of an
allow entry provides the clean accidental-use boundary without making recovery brittle.

### Startup task

The Windows scheduled task `GIGA-ArtVault-Startup` exists and was running at the snapshot:

| Field | Verified value |
|---|---|
| Principal | `gutua`, S4U logon, highest run level |
| Trigger | Windows startup, delayed 30 seconds |
| Action | `wsl.exe -d ArtVault -u root -- /usr/bin/sleep infinity` |
| Execution limit | none (`PT0S`) |
| Multiple instances | ignore new |
| Recovery | 3 restarts, 1-minute interval; start when available |
| Observed state | `Running` |
| Last task result | `267009` / `0x00041301` (task is currently running) |

Inside ArtVault, both `ssh.service` and `tailscaled.service` were enabled and active. The running
task proves the S4U principal can start and retain the per-user distro in the current system
state. A timed keeper observation began from the task's recorded `LastRunTime` of
`2026-08-20T12:14:23+01:00`; at `2026-08-20T12:21:33+01:00` the task was still `Running`, its
result was still `267009`, ArtVault was running, and both guest services were active. The
continuous observed interval was 430 seconds, exceeding the required three-minute keeper
probe. This proves retention in the current Windows session. A real Windows cold reboot has not
yet been performed, so boot persistence remains an unverified recommended operational follow-up
rather than a completed claim.

## Provider and remote-access state

Required provider and remote identities are live:

| Identity | Live result | Consequence |
|---|---|---|
| Tailscale | `BackendState=Running`, online, `100.101.96.58`, `artvault.tail201f6c.ts.net.` | direct tailnet path live |
| Codex | `Logged in using ChatGPT` | independent ArtVault OpenAI/ChatGPT credential live |
| Claude | installed; `loggedIn=false`, `authMethod=none` | intentionally unused and out of scope |

The completion verifier also asserts that `/home/art/.codex` and `/home/art/.claude` are real
directories rather than symbolic links, retain `art:art` ownership and mode `0700`, and reside on
the same ArtVault root filesystem as `/`. Combined with the distinct VHD and machine identity,
the disabled Windows mounts/interoperability, and the fresh interactive login flows, this proves
the resulting session stores belong to ArtVault rather than referencing the host or existing
Ubuntu distribution.

The Codex credential file is a real regular file at `/home/art/.codex/auth.json`, owned by
`art:art`, mode `0600`, and on the same ArtVault root filesystem as `/`. It was created by the
fresh device-authorization flow launched from ArtVault; no existing Ubuntu credential file or
provider directory was copied. The verifier checks only its type, ownership, mode and filesystem
location and never reads or emits its contents.

From the Mac, the verifier connected directly to `art@100.101.96.58` using only
`/Users/admin/.ssh/artvault_ed25519`, an ephemeral strict `known_hosts` file constructed from the
previously recorded ArtVault Ed25519 host public key, and `StrictHostKeyChecking=yes`. The command
returned the exact expected marker. No host-hop or disabled host-key check was used.

Provider login links, device codes, OAuth verifier values, API keys and session tokens must never
be recorded in this receipt or committed to the repository.

## Mac text interface

`migration/ArtVault Codex.command` is the canonical Mac terminal entry point. No earlier ArtVault
launcher existed. The completion verifier could not serve this responsibility because it is an
observational, deliberately non-interactive lifecycle check; keeping the launcher separate avoids
turning verification into a stateful user interface.

The launcher:

- opens the native interactive Codex terminal directly in `/srv/artvault`;
- uses only `/Users/admin/.ssh/artvault_ed25519` and the separately pinned
  `/Users/admin/.ssh/artvault_known_hosts` host key;
- requires public-key authentication and strict host-key checking, disables password and
  keyboard-interactive fallback, and disables forwarding and SSH connection sharing;
- offers `--check` to verify the Mac key fingerprint, pinned host key, remote `art` identity,
  exact ArtVault server fingerprint, local file modes, remote `art` identity, ArtVault hostname,
  working directory, Codex executable and live ChatGPT login without opening the interface.

The Mac SSH configuration also has a matching `Host artvault` entry, so `ssh artvault` is the
canonical direct shell path when a full Linux shell is needed. A Desktop symbolic link points to
the single canonical launcher rather than duplicating it.

At `2026-08-21T01:17:02Z`, `--check` returned `ArtVault Codex is ready`. A separate pseudo-terminal
smoke test displayed OpenAI Codex v0.148.0, model `gpt-5.6-sol`, and directory `/srv/artvault`; the
one-time trust prompt for that protected, operator-owned directory was accepted, and the test then
exited cleanly. The interface is therefore proven interactively, not only by a status probe.

## Windows handoff state

The separate local Windows account is provisioned. The final verifier reported:

| Item | Live result |
|---|---|
| Account | `serge`, present and enabled |
| Local administration | exactly one membership in local `Administrators` |
| Password required | `true` |
| User may change password | `true` |
| Password expired / change required at next login | `true` |
| User Account Control | enabled |
| Direct ACE on `C:\VirtualEntities\ArtVault\ext4.vhdx` | none |

Provisioning was deliberately fail-closed:

1. The first transport attempt never reached provisioning, created no Windows account, and left
   only an empty temporary Keychain item; that empty item was removed.
2. The first actual provisioning attempt encountered the unavailable
   `LocalUser.PasswordNeverExpires` property during postcondition verification. It emitted no
   credential and left the partially configured account disabled.
3. The replacement ADSI `UserFlags`/`PasswordExpired` implementation was reviewed. An explicit
   reset then succeeded, re-read every required postcondition, enabled the account only after
   those checks passed, and emitted the temporary credential once.

The temporary password is stored only in the operator Mac's login Keychain under service
`Gigabyte/serge/temporary-password`. Its value is intentionally absent from this receipt, the
repository, chat and shell history. Serge must use it only for the first physical login and
replace it immediately with his own password; Windows already enforces that replacement.

Machine-side administrator capability and the accidental VHD ACL boundary are now proven. At
Serge's first login, both ordinary and elevated `wsl.exe --list --verbose` should still show none
of `gutua`'s distributions, and `C:\VirtualEntities` should return access denied. Those
session-specific checks remain pending until the physical handoff.

## Objective completion evidence

All current objective gates have fresh evidence:

1. Tailscale is authenticated inside ArtVault under its own node identity and reports online at
   the address and DNS name recorded above.
2. The Mac connected directly to that address as `art` with the dedicated key and strict host-key
   verification.
3. Codex was authenticated by a fresh device flow started inside ArtVault and its native login
   status succeeds.
4. The Codex credential store is a real, permission-restricted file on ArtVault's own root
   filesystem; no existing Ubuntu credential was copied.
5. The canonical verifier completed with `SUMMARY failures=0 warnings=0` at
   `2026-08-21T01:04:09Z`, while the existing Ubuntu workload and Windows handoff controls also
   remained healthy.

## Recommended operational follow-ups

These drills strengthen recovery and handoff assurance, but they are outside the durable ArtVault
goal and do not block its completion:

1. Perform one controlled Windows cold reboot. Require the startup task to return to `Running`,
   ArtVault to be running, SSH and Tailscale to be active, and direct Mac SSH to succeed without
   an interactive Windows login.
2. Complete Serge's first physical login and forced password replacement, then run the
   ordinary/elevated WSL-visibility, ACL and representative administrator-capability checks
   described above.
3. Switch between the `gutua` and Serge sessions and verify that the existing Ubuntu workloads
   remain live and ArtVault remains remotely reachable.
4. Produce an encrypted off-device recovery export or an explicit alternative recovery plan.

## Honest limitations

- A determined Windows administrator can take ownership of the VHD tree, rewrite its ACL, copy or
  mount the VHD, stop WSL, alter networking, install SYSTEM-level monitoring, or delete/fill the
  disk. The present design intentionally addresses accidents, not a malicious administrator.
- `SYSTEM` retains full control because Windows and WSL require host-level operation. Software or
  drivers that Serge deliberately installs as SYSTEM can therefore affect ArtVault.
- WSL2 distributions use shared host resources. No ArtVault-only CPU or RAM cap is claimed; a
  Windows `.wslconfig` limit would also affect the existing Ubuntu workload. The idle keepalive
  task does not itself guarantee negligible resource use once work is launched in ArtVault.
- Host BitLocker protects the disk when the machine is powered off; it does not isolate ArtVault
  from an administrator of an already-unlocked Windows installation.
- Claude Code is installed for possible future use but is deliberately unauthenticated. The
  current verifier defaults `ARTVAULT_REQUIRE_CLAUDE=false`; setting it to `true` restores Claude
  authentication as a hard completion gate.

## Reproducible artifacts

The canonical deployment sources are:

- `migration/bootstrap_artvault_wsl.sh`
  - SHA-256 at this receipt snapshot:
    `7c2b05e86ad72f912d13b69901f563e4b905e42eb7a37a4b705d500fda178afc`
- `migration/install_artvault_startup_task_gigabyte.ps1`
  - SHA-256 at this receipt snapshot:
    `8b088cedd228c1ad1b7ec2479dd2ab87bee30e47642dea8379a996f874aafa30`
- `migration/verify_artvault_completion.sh`
  - SHA-256 at this receipt snapshot:
    `eaa736e623090bcd70e67435f1b9aa2b23db3d91476642b56a9a2b77c8d7d54d`
- `migration/provision_serge_local_admin.ps1`
  - SHA-256 at this receipt snapshot:
    `1fae77d57b900b7dc299d3c0ef7102d858ba861b7d7da0db2f53658339db85bb`
- `migration/ArtVault Codex.command`
  - SHA-256 at this receipt snapshot:
    `ddfba53c4bffccfe70b70d8575c5d27f3a30f8fc239dab3211891b4949b506f6`

These hashes bind this receipt to the inspected versions of the scripts. Any later script change
requires fresh hashes and re-verification of the affected live state; it does not retroactively
change what was observed here.
