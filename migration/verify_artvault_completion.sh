#!/usr/bin/env bash
set -uo pipefail

# Read-only completion verifier for the ArtVault WSL entity. It intentionally
# does not start a stopped distro: a stopped ArtVault is itself evidence that
# the headless/startup requirement is not satisfied.

gigabyte_host="${GIGABYTE_SSH_HOST:-gigabyte}"
identity_file="${ARTVAULT_IDENTITY_FILE:-${HOME}/.ssh/artvault_ed25519}"
serge_user="${SERGE_WINDOWS_USER:-serge}"
startup_task="${ARTVAULT_STARTUP_TASK:-GIGA-ArtVault-Startup}"
distro_name="${ARTVAULT_DISTRO_NAME:-ArtVault}"
existing_distro="${GIGABYTE_EXISTING_DISTRO:-Ubuntu}"
existing_distro_mode="${GIGABYTE_EXISTING_DISTRO_MODE:-absent}"
expected_retired_archive_bytes="${ARTVAULT_RETIRED_UBUNTU_ARCHIVE_BYTES:-121280153600}"
expected_retired_archive_sha256="${ARTVAULT_RETIRED_UBUNTU_ARCHIVE_SHA256:-43605ee9372532750de1522ae91cc1aa2fac8619e5706b832ba4c86b1d8d8abf}"
expected_node_version="${ARTVAULT_NODE_VERSION:-v22.23.2}"
expected_claude_version="${ARTVAULT_CLAUDE_VERSION:-2.1.237 (Claude Code)}"
expected_codex_version="${ARTVAULT_CODEX_VERSION:-codex-cli 0.148.0}"
require_claude="${ARTVAULT_REQUIRE_CLAUDE:-false}"

failures=0
warnings=0

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'ERROR missing_local_command=%s\n' "$1" >&2
    exit 2
  fi
}

for required_command in ssh ssh-keygen iconv base64 awk sed mktemp; do
  require_command "${required_command}"
done

require_remote_name() {
  local label="$1"
  local value="$2"
  if [[ ! "${value}" =~ ^[A-Za-z0-9._-]+$ ]]; then
    printf 'ERROR unsafe_%s=%q\n' "${label}" "${value}" >&2
    exit 2
  fi
}

require_remote_name distro_name "${distro_name}"
require_remote_name existing_distro "${existing_distro}"
require_remote_name serge_user "${serge_user}"
require_remote_name startup_task "${startup_task}"

if [[ "${require_claude}" != 'true' && "${require_claude}" != 'false' ]]; then
  printf 'ERROR ARTVAULT_REQUIRE_CLAUDE must be true or false, actual=%q\n' \
    "${require_claude}" >&2
  exit 2
fi

if [[ "${existing_distro_mode}" != 'running' && "${existing_distro_mode}" != 'absent' ]]; then
  printf 'ERROR GIGABYTE_EXISTING_DISTRO_MODE must be running or absent, actual=%q\n' \
    "${existing_distro_mode}" >&2
  exit 2
fi

if [[ ! "${expected_retired_archive_bytes}" =~ ^[0-9]+$ ]] || \
   [[ ! "${expected_retired_archive_sha256}" =~ ^[0-9a-f]{64}$ ]]; then
  printf '%s\n' 'ERROR invalid retired-Ubuntu archive expectation.' >&2
  exit 2
fi

emit_check() {
  local name="$1"
  local expected="$2"
  local actual="$3"
  if [[ "${actual}" == "${expected}" ]]; then
    printf 'CHECK %s PASS expected=%q actual=%q\n' "${name}" "${expected}" "${actual}"
  else
    printf 'CHECK %s FAIL expected=%q actual=%q\n' "${name}" "${expected}" "${actual}"
    failures=$((failures + 1))
  fi
}

emit_nonempty_check() {
  local name="$1"
  local actual="$2"
  if [[ -n "${actual}" ]]; then
    printf 'CHECK %s PASS actual=%q\n' "${name}" "${actual}"
  else
    printf 'CHECK %s FAIL actual=<empty>\n' "${name}"
    failures=$((failures + 1))
  fi
}

emit_positive_check() {
  local name="$1"
  local actual="$2"
  if [[ "${actual}" =~ ^[0-9]+$ ]] && (( actual > 0 )); then
    printf 'CHECK %s PASS actual=%q\n' "${name}" "${actual}"
  else
    printf 'CHECK %s FAIL expected=positive_integer actual=%q\n' "${name}" "${actual}"
    failures=$((failures + 1))
  fi
}

emit_warning() {
  local name="$1"
  local detail="$2"
  printf 'CHECK %s WARN detail=%q\n' "${name}" "${detail}"
  warnings=$((warnings + 1))
}

read -r -d '' powershell_script <<'POWERSHELL' || true
$ErrorActionPreference = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'

$distroName = $env:ARTVAULT_DISTRO_NAME
$existingDistro = $env:GIGABYTE_EXISTING_DISTRO
$sergeUser = $env:SERGE_WINDOWS_USER
$startupTask = $env:ARTVAULT_STARTUP_TASK

function Emit([string]$Name, $Value) {
    if ($null -eq $Value) {
        $text = ''
    }
    elseif ($Value -is [bool]) {
        $text = $Value.ToString().ToLowerInvariant()
    }
    else {
        $text = ([string]$Value).Replace("`r", ' ').Replace("`n", ' ').Trim()
    }
    Write-Output ("{0}={1}" -f $Name, $text)
}

function Distro-State([string]$Name) {
    $installed = @(& wsl.exe --list --quiet 2>$null | ForEach-Object { $_.Trim() })
    if ($installed -notcontains $Name) {
        return 'absent'
    }
    $running = @(& wsl.exe --list --running --quiet 2>$null | ForEach-Object { $_.Trim() })
    if ($running -contains $Name) {
        return 'running'
    }
    return 'stopped'
}

Emit 'schema' 'artvault.verification.v1'
Emit 'observed_at_utc' ([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))
Emit 'windows_computer' $env:COMPUTERNAME
Emit 'windows_identity' ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)

$os = Get-CimInstance Win32_OperatingSystem
Emit 'windows_caption' $os.Caption
Emit 'windows_version' $os.Version
Emit 'windows_last_boot_utc' ($os.LastBootUpTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))

$bitlocker = Get-BitLockerVolume -MountPoint 'C:'
Emit 'bitlocker_encryption_percentage' $bitlocker.EncryptionPercentage
Emit 'bitlocker_protection_on' ($bitlocker.ProtectionStatus.ToString() -eq 'On')

$vhdPath = 'C:\VirtualEntities\ArtVault\ext4.vhdx'
$vhd = Get-Item -LiteralPath $vhdPath
Emit 'artvault_vhd_present' ($null -ne $vhd)
Emit 'artvault_vhd_bytes' $vhd.Length
if ($null -ne $vhd) {
    $vhdAcl = Get-Acl -LiteralPath $vhdPath
    Emit 'artvault_vhd_owner' $vhdAcl.Owner
    Emit 'artvault_vhd_acl_identities' (($vhdAcl.Access.IdentityReference.Value | Sort-Object -Unique) -join ',')
}

$artVaultState = Distro-State $distroName
$existingState = Distro-State $existingDistro
Emit 'artvault_distro_state' $artVaultState
Emit 'existing_distro_state' $existingState

if ($artVaultState -eq 'running') {
    Emit 'artvault_machine_id' ((& wsl.exe -d $distroName -u root -- cat /etc/machine-id 2>$null) | Out-String)
    Emit 'artvault_hostname' ((& wsl.exe -d $distroName -u root -- hostname 2>$null) | Out-String)
    Emit 'artvault_user_id' ((& wsl.exe -d $distroName -u root -- id -u art 2>$null) | Out-String)
    Emit 'artvault_user_groups' ((& wsl.exe -d $distroName -u root -- id -Gn art 2>$null) | Out-String)

    $wslConf = ((& wsl.exe -d $distroName -u root -- cat /etc/wsl.conf 2>$null) | Out-String)
    Emit 'systemd_configured' ($wslConf -match '(?ms)\[boot\].*?systemd\s*=\s*true')
    Emit 'windows_automount_disabled' ($wslConf -match '(?ms)\[automount\].*?enabled\s*=\s*false')
    Emit 'windows_fstab_mounts_disabled' ($wslConf -match '(?ms)\[automount\].*?mountFsTab\s*=\s*false')
    Emit 'windows_interop_disabled' ($wslConf -match '(?ms)\[interop\].*?enabled\s*=\s*false')
    Emit 'default_user_art' ($wslConf -match '(?ms)\[user\].*?default\s*=\s*art')
    & wsl.exe -d $distroName -u root -- findmnt -n /mnt/c *> $null
    Emit 'windows_c_mounted' ($LASTEXITCODE -eq 0)
    & wsl.exe -d $distroName -u root -- test -e /proc/sys/fs/binfmt_misc/WSLInterop *> $null
    Emit 'wslinterop_binfmt_present' ($LASTEXITCODE -eq 0)
    & wsl.exe -d $distroName -u root -- /usr/bin/printenv WSL_INTEROP *> $null
    Emit 'wslinterop_environment_present' ($LASTEXITCODE -eq 0)

    $sshdEffective = @(& wsl.exe -d $distroName -u root -- sshd -T -C 'user=art,host=artvault,addr=100.64.0.1' 2>$null)
    function Sshd-Value([string]$Name) {
        $pattern = ('^{0}\s+' -f [regex]::Escape($Name))
        $line = $sshdEffective | Where-Object { $_ -match $pattern } | Select-Object -First 1
        if ($null -eq $line) {
            return ''
        }
        return ([regex]::Replace([string]$line, $pattern, '')).Trim()
    }
    foreach ($sshSetting in @(
        'permitrootlogin',
        'pubkeyauthentication',
        'passwordauthentication',
        'kbdinteractiveauthentication',
        'x11forwarding',
        'allowagentforwarding',
        'allowtcpforwarding',
        'allowstreamlocalforwarding',
        'permittunnel',
        'disableforwarding',
        'maxauthtries',
        'allowusers'
    )) {
        Emit ("sshd_effective_{0}" -f $sshSetting) (Sshd-Value $sshSetting)
    }

    & wsl.exe -d $distroName -u root -- test -f /var/lib/artvault/bootstrap-v1.complete *> $null
    Emit 'bootstrap_marker_present' ($LASTEXITCODE -eq 0)
    Emit 'ssh_enabled' (((& wsl.exe -d $distroName -u root -- systemctl is-enabled ssh 2>$null) | Out-String).Trim() -eq 'enabled')
    Emit 'ssh_active' (((& wsl.exe -d $distroName -u root -- systemctl is-active ssh 2>$null) | Out-String).Trim() -eq 'active')
    Emit 'tailscaled_enabled' (((& wsl.exe -d $distroName -u root -- systemctl is-enabled tailscaled 2>$null) | Out-String).Trim() -eq 'enabled')
    Emit 'tailscaled_active' (((& wsl.exe -d $distroName -u root -- systemctl is-active tailscaled 2>$null) | Out-String).Trim() -eq 'active')

    Emit 'node_version' ((& wsl.exe -d $distroName -u art -- node --version 2>$null) | Out-String)
    Emit 'claude_version' ((& wsl.exe -d $distroName -u art -- /home/art/.local/bin/claude --version 2>$null) | Out-String)
    Emit 'codex_version' ((& wsl.exe -d $distroName -u art -- /home/art/.local/bin/codex --version 2>$null) | Out-String)

    $codexStatus = ((& wsl.exe -d $distroName -u art -- /home/art/.local/bin/codex login status 2>&1) | Out-String)
    $codexStatusExit = $LASTEXITCODE
    Emit 'codex_logged_in' ($codexStatusExit -eq 0)

    $claudeStatusText = ((& wsl.exe -d $distroName -u art -- /home/art/.local/bin/claude auth status --json 2>$null) | Out-String)
    $claudeStatus = $claudeStatusText | ConvertFrom-Json
    Emit 'claude_logged_in' ([bool]$claudeStatus.loggedIn)
    Emit 'claude_auth_method' $claudeStatus.authMethod

    $tailscaleText = ((& wsl.exe -d $distroName -u root -- tailscale status --json 2>$null) | Out-String)
    $tailscaleStatus = $tailscaleText | ConvertFrom-Json
    Emit 'tailscale_backend_state' $tailscaleStatus.BackendState
    Emit 'tailscale_node_id' $tailscaleStatus.Self.ID
    Emit 'tailscale_dns_name' $tailscaleStatus.Self.DNSName
    $tailIps = @($tailscaleStatus.Self.TailscaleIPs)
    Emit 'tailscale_ipv4' (($tailIps | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1))
    Emit 'tailscale_online' ([bool]$tailscaleStatus.Self.Online)

    $remoteFingerprint = ((& wsl.exe -d $distroName -u art -- ssh-keygen -lf /home/art/.ssh/authorized_keys 2>$null) | Out-String)
    Emit 'authorized_key_fingerprint' $remoteFingerprint
    Emit 'ssh_host_ed25519_public_key' ((& wsl.exe -d $distroName -u root -- cat /etc/ssh/ssh_host_ed25519_key.pub 2>$null) | Out-String)
    Emit 'ssh_dir_mode_owner' ((& wsl.exe -d $distroName -u root -- stat -c '%a:%U:%G' /home/art/.ssh 2>$null) | Out-String)
    Emit 'authorized_keys_mode_owner' ((& wsl.exe -d $distroName -u root -- stat -c '%a:%U:%G' /home/art/.ssh/authorized_keys 2>$null) | Out-String)
    Emit 'codex_dir_mode_owner' ((& wsl.exe -d $distroName -u root -- stat -c '%a:%U:%G' /home/art/.codex 2>$null) | Out-String)
    Emit 'claude_dir_mode_owner' ((& wsl.exe -d $distroName -u root -- stat -c '%a:%U:%G' /home/art/.claude 2>$null) | Out-String)
    Emit 'codex_dir_type' ((& wsl.exe -d $distroName -u root -- stat -c '%F' /home/art/.codex 2>$null) | Out-String)
    Emit 'claude_dir_type' ((& wsl.exe -d $distroName -u root -- stat -c '%F' /home/art/.claude 2>$null) | Out-String)
    Emit 'artvault_root_filesystem_source' ((& wsl.exe -d $distroName -u root -- findmnt -n -o SOURCE -T / 2>$null) | Out-String)
    Emit 'codex_dir_filesystem_source' ((& wsl.exe -d $distroName -u root -- findmnt -n -o SOURCE -T /home/art/.codex 2>$null) | Out-String)
    Emit 'claude_dir_filesystem_source' ((& wsl.exe -d $distroName -u root -- findmnt -n -o SOURCE -T /home/art/.claude 2>$null) | Out-String)
    Emit 'codex_auth_file_type' ((& wsl.exe -d $distroName -u root -- stat -c '%F' /home/art/.codex/auth.json 2>$null) | Out-String)
    Emit 'codex_auth_file_mode_owner' ((& wsl.exe -d $distroName -u root -- stat -c '%a:%U:%G' /home/art/.codex/auth.json 2>$null) | Out-String)
    Emit 'codex_auth_file_filesystem_source' ((& wsl.exe -d $distroName -u root -- findmnt -n -o SOURCE -T /home/art/.codex/auth.json 2>$null) | Out-String)

    $retiredArchive = '/srv/artvault/migrations/ubuntu-retired-20260821/ubuntu-root.tar'
    $retiredStageReceipt = '/srv/artvault/migrations/ubuntu-retired-20260821/STAGE.json'
    $retiredVerifyReceipt = '/srv/artvault/migrations/ubuntu-retired-20260821/VERIFY.json'
    $retiredReceipt = '/srv/artvault/migrations/ubuntu-retired-20260821/RETIRE.json'
    & wsl.exe -d $distroName -u root -- test -f $retiredArchive *> $null
    Emit 'retired_ubuntu_archive_present' ($LASTEXITCODE -eq 0)
    Emit 'retired_ubuntu_archive_bytes' ((& wsl.exe -d $distroName -u root -- stat -c '%s' $retiredArchive 2>$null) | Out-String)
    foreach ($receipt in @(
        @('retired_ubuntu_stage_receipt_present', $retiredStageReceipt),
        @('retired_ubuntu_verify_receipt_present', $retiredVerifyReceipt),
        @('retired_ubuntu_retire_receipt_present', $retiredReceipt)
    )) {
        & wsl.exe -d $distroName -u root -- test -f $receipt[1] *> $null
        Emit $receipt[0] ($LASTEXITCODE -eq 0)
    }
    $retiredReceiptText = ((& wsl.exe -d $distroName -u root -- cat $retiredReceipt 2>$null) | Out-String)
    $retiredDigest = [regex]::Match($retiredReceiptText, '"archive_sha256":"([0-9a-f]{64})"').Groups[1].Value
    Emit 'retired_ubuntu_archive_sha256_receipt' $retiredDigest
    Emit 'retired_ubuntu_recovery_passed' ($retiredReceiptText -match '"recovery_import_passed":true')
    Emit 'retired_ubuntu_source_deleted' ($retiredReceiptText -match '"source_deleted":true')
}

if ($existingState -eq 'running') {
    Emit 'existing_machine_id' ((& wsl.exe -d $existingDistro -u root -- cat /etc/machine-id 2>$null) | Out-String)
    Emit 'existing_transitvpn_process_count' ((& wsl.exe -d $existingDistro -u root -- pgrep -fc '[t]ransitvpn' 2>$null) | Out-String)
    Emit 'existing_factory_daemon_count' ((& wsl.exe -d $existingDistro -u root -- pgrep -fc '[c]ontrol.daemon' 2>$null) | Out-String)
}

foreach ($serviceName in @('sshd', 'Tailscale', 'RustDesk')) {
    $service = Get-Service -Name $serviceName
    Emit ("host_service_{0}_status" -f $serviceName.ToLowerInvariant()) $service.Status
    Emit ("host_service_{0}_start_type" -f $serviceName.ToLowerInvariant()) $service.StartType
}

$task = Get-ScheduledTask -TaskName $startupTask
Emit 'startup_task_present' ($null -ne $task)
if ($null -ne $task) {
    $taskInfo = Get-ScheduledTaskInfo -TaskName $startupTask
    Emit 'startup_task_state' $task.State
    Emit 'startup_task_principal' $task.Principal.UserId
    Emit 'startup_task_logon_type' $task.Principal.LogonType
    Emit 'startup_task_execute' $task.Actions.Execute
    Emit 'startup_task_arguments' $task.Actions.Arguments
    Emit 'startup_task_last_result' $taskInfo.LastTaskResult
    Emit 'startup_task_execution_time_limit' $task.Settings.ExecutionTimeLimit
    $bootTriggers = @($task.Triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskBootTrigger' })
    Emit 'startup_task_boot_trigger_count' $bootTriggers.Count
    if ($bootTriggers.Count -eq 1) {
        Emit 'startup_task_boot_delay' $bootTriggers[0].Delay
    }
}

$legacyTransitTask = Get-ScheduledTask -TaskName 'GIGA-TransitVPN-V3-20260820'
Emit 'legacy_transit_task_present' ($null -ne $legacyTransitTask)

$users = @(Get-LocalUser)
$admins = @(Get-LocalGroupMember -Group 'Administrators')
Emit 'windows_local_users' (($users.Name | Sort-Object) -join ',')
Emit 'windows_admins' (($admins.Name | Sort-Object) -join ',')
$serge = $users | Where-Object { $_.Name -ieq $sergeUser } | Select-Object -First 1
Emit 'serge_account_present' ($null -ne $serge)
Emit 'serge_account_enabled' ([bool]$serge.Enabled)
if ($null -ne $serge) {
    Emit 'serge_is_administrator' ([bool]($admins | Where-Object { $_.SID.Value -eq $serge.SID.Value }))
    Emit 'serge_password_required' ([bool]$serge.PasswordRequired)
    Emit 'serge_may_change_password' ([bool]$serge.UserMayChangePassword)
    $sergeAdsi = [ADSI]("WinNT://$env:COMPUTERNAME/$sergeUser,user")
    Emit 'serge_password_change_required' ([int]$sergeAdsi.InvokeGet('PasswordExpired') -ne 0)
    if ($null -ne $vhd) {
        Emit 'serge_has_direct_vhd_ace' ([bool]($vhdAcl.Access | Where-Object { $_.IdentityReference.Value -match "\\$([regex]::Escape($sergeUser))$" }))
    }
}
$uacPolicy = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'
Emit 'uac_enabled' ([int]$uacPolicy.EnableLUA -eq 1)
POWERSHELL

encoded_script="$(printf '%s' "${powershell_script}" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\r\n')"

printf 'VERIFY host=%q distro=%q existing_distro=%q serge_user=%q\n' \
  "${gigabyte_host}" "${distro_name}" "${existing_distro}" "${serge_user}"

remote_output="$(
  printf '%s\n' \
    "[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('${encoded_script}')) | Invoke-Expression" \
    | ssh \
      -o BatchMode=yes \
      -o ConnectTimeout=10 \
      "${gigabyte_host}" \
      "set ARTVAULT_DISTRO_NAME=${distro_name}&& set GIGABYTE_EXISTING_DISTRO=${existing_distro}&& set SERGE_WINDOWS_USER=${serge_user}&& set ARTVAULT_STARTUP_TASK=${startup_task}&& powershell.exe -NoLogo -NoProfile -NonInteractive -OutputFormat Text -Command -" \
      2>&1
)"
remote_status=$?
remote_output="${remote_output//$'\r'/}"

if (( remote_status != 0 )); then
  printf 'ERROR remote_query_failed host=%q exit=%d output=%q\n' \
    "${gigabyte_host}" "${remote_status}" "${remote_output}" >&2
  exit 2
fi

# The PowerShell program emits only explicitly selected, non-secret evidence.
printf '%s\n' "${remote_output}"

evidence_value() {
  local key="$1"
  printf '%s\n' "${remote_output}" \
    | awk -F= -v wanted="${key}" '$1 == wanted { sub(/^[^=]*=/, ""); print; exit }'
}

emit_check schema 'artvault.verification.v1' "$(evidence_value schema)"
emit_check artvault_distro_state 'running' "$(evidence_value artvault_distro_state)"
emit_check existing_distro_state "${existing_distro_mode}" "$(evidence_value existing_distro_state)"
emit_check artvault_vhd_present 'true' "$(evidence_value artvault_vhd_present)"
emit_positive_check artvault_vhd_bytes "$(evidence_value artvault_vhd_bytes)"
emit_nonempty_check artvault_machine_id "$(evidence_value artvault_machine_id)"
emit_check artvault_hostname 'artvault' "$(evidence_value artvault_hostname)"
emit_check artvault_user_id '1000' "$(evidence_value artvault_user_id)"

artvault_groups="$(evidence_value artvault_user_groups)"
if [[ " ${artvault_groups} " == *' sudo '* ]]; then
  printf 'CHECK artvault_user_sudo PASS actual=%q\n' "${artvault_groups}"
else
  printf 'CHECK artvault_user_sudo FAIL actual=%q\n' "${artvault_groups}"
  failures=$((failures + 1))
fi

emit_check systemd_configured 'true' "$(evidence_value systemd_configured)"
emit_check windows_automount_disabled 'true' "$(evidence_value windows_automount_disabled)"
emit_check windows_fstab_mounts_disabled 'true' "$(evidence_value windows_fstab_mounts_disabled)"
emit_check windows_interop_disabled 'true' "$(evidence_value windows_interop_disabled)"
emit_check default_user_art 'true' "$(evidence_value default_user_art)"
emit_check windows_c_mounted 'false' "$(evidence_value windows_c_mounted)"
emit_check wslinterop_environment_present 'false' "$(evidence_value wslinterop_environment_present)"
printf 'CHECK wslinterop_binfmt_global INFO actual=%q\n' \
  "$(evidence_value wslinterop_binfmt_present)"
emit_check sshd_permitrootlogin 'no' "$(evidence_value sshd_effective_permitrootlogin)"
emit_check sshd_pubkeyauthentication 'yes' "$(evidence_value sshd_effective_pubkeyauthentication)"
emit_check sshd_passwordauthentication 'no' "$(evidence_value sshd_effective_passwordauthentication)"
emit_check sshd_kbdinteractiveauthentication 'no' "$(evidence_value sshd_effective_kbdinteractiveauthentication)"
emit_check sshd_x11forwarding 'no' "$(evidence_value sshd_effective_x11forwarding)"
emit_check sshd_allowagentforwarding 'no' "$(evidence_value sshd_effective_allowagentforwarding)"
emit_check sshd_allowtcpforwarding 'no' "$(evidence_value sshd_effective_allowtcpforwarding)"
emit_check sshd_allowstreamlocalforwarding 'no' "$(evidence_value sshd_effective_allowstreamlocalforwarding)"
emit_check sshd_permittunnel 'no' "$(evidence_value sshd_effective_permittunnel)"
emit_check sshd_disableforwarding 'yes' "$(evidence_value sshd_effective_disableforwarding)"
emit_check sshd_maxauthtries '3' "$(evidence_value sshd_effective_maxauthtries)"
emit_check sshd_allowusers 'art' "$(evidence_value sshd_effective_allowusers)"
emit_check bootstrap_marker_present 'true' "$(evidence_value bootstrap_marker_present)"
emit_check ssh_enabled 'true' "$(evidence_value ssh_enabled)"
emit_check ssh_active 'true' "$(evidence_value ssh_active)"
emit_check tailscaled_enabled 'true' "$(evidence_value tailscaled_enabled)"
emit_check tailscaled_active 'true' "$(evidence_value tailscaled_active)"

emit_check node_version "${expected_node_version}" "$(evidence_value node_version)"
emit_check claude_version "${expected_claude_version}" "$(evidence_value claude_version)"
emit_check codex_version "${expected_codex_version}" "$(evidence_value codex_version)"
emit_check codex_logged_in 'true' "$(evidence_value codex_logged_in)"
if [[ "${require_claude}" == 'true' ]]; then
  emit_check claude_logged_in 'true' "$(evidence_value claude_logged_in)"
else
  printf 'CHECK claude_logged_in SKIP requirement=disabled actual=%q\n' \
    "$(evidence_value claude_logged_in)"
fi
emit_check tailscale_backend_state 'Running' "$(evidence_value tailscale_backend_state)"
emit_check tailscale_online 'true' "$(evidence_value tailscale_online)"
tailscale_ipv4="$(evidence_value tailscale_ipv4)"
emit_nonempty_check tailscale_ipv4 "${tailscale_ipv4}"

emit_check ssh_dir_mode_owner '700:art:art' "$(evidence_value ssh_dir_mode_owner)"
emit_check authorized_keys_mode_owner '600:art:art' "$(evidence_value authorized_keys_mode_owner)"
emit_check codex_dir_mode_owner '700:art:art' "$(evidence_value codex_dir_mode_owner)"
emit_check claude_dir_mode_owner '700:art:art' "$(evidence_value claude_dir_mode_owner)"
emit_check codex_dir_type 'directory' "$(evidence_value codex_dir_type)"
emit_check claude_dir_type 'directory' "$(evidence_value claude_dir_type)"
artvault_root_filesystem_source="$(evidence_value artvault_root_filesystem_source)"
emit_nonempty_check artvault_root_filesystem_source "${artvault_root_filesystem_source}"
emit_check codex_dir_on_artvault_rootfs \
  "${artvault_root_filesystem_source}" \
  "$(evidence_value codex_dir_filesystem_source)"
emit_check claude_dir_on_artvault_rootfs \
  "${artvault_root_filesystem_source}" \
  "$(evidence_value claude_dir_filesystem_source)"
emit_check codex_auth_file_type 'regular file' "$(evidence_value codex_auth_file_type)"
emit_check codex_auth_file_mode_owner '600:art:art' \
  "$(evidence_value codex_auth_file_mode_owner)"
emit_check codex_auth_file_on_artvault_rootfs \
  "${artvault_root_filesystem_source}" \
  "$(evidence_value codex_auth_file_filesystem_source)"

local_fingerprint=''
if [[ -f "${identity_file}.pub" ]]; then
  local_fingerprint="$(ssh-keygen -lf "${identity_file}.pub" 2>/dev/null | awk '{print $2}')"
fi
remote_fingerprint="$(evidence_value authorized_key_fingerprint | sed -n 's/.*\(SHA256:[^ ]*\).*/\1/p')"
emit_nonempty_check local_ssh_fingerprint "${local_fingerprint}"
emit_check authorized_key_matches_local "${local_fingerprint}" "${remote_fingerprint}"

ssh_host_public_key="$(evidence_value ssh_host_ed25519_public_key)"
ssh_host_key_type="$(awk '{print $1}' <<< "${ssh_host_public_key}")"
ssh_host_key_data="$(awk '{print $2}' <<< "${ssh_host_public_key}")"
emit_check ssh_host_key_type 'ssh-ed25519' "${ssh_host_key_type}"
emit_nonempty_check ssh_host_key_data "${ssh_host_key_data}"

direct_ssh='unavailable'
if [[ -n "${tailscale_ipv4}" && -f "${identity_file}" ]]; then
  known_hosts_file="$(mktemp)"
  chmod 0600 "${known_hosts_file}"
  if [[ "${ssh_host_key_type}" == 'ssh-ed25519' && -n "${ssh_host_key_data}" ]]; then
    printf '%s %s %s\n' \
      "${tailscale_ipv4}" "${ssh_host_key_type}" "${ssh_host_key_data}" \
      > "${known_hosts_file}"
  fi
  direct_output="$(
    ssh \
      -i "${identity_file}" \
      -o BatchMode=yes \
      -o ConnectTimeout=10 \
      -o IdentitiesOnly=yes \
      -o StrictHostKeyChecking=yes \
      -o UserKnownHostsFile="${known_hosts_file}" \
      -o GlobalKnownHostsFile=/dev/null \
      "art@${tailscale_ipv4}" \
      'printf ARTVAULT_DIRECT_OK' \
      2>/dev/null
  )"
  rm -f "${known_hosts_file}"
  if [[ "${direct_output}" == 'ARTVAULT_DIRECT_OK' ]]; then
    direct_ssh='verified'
  else
    direct_ssh='failed'
  fi
fi
emit_check direct_ssh 'verified' "${direct_ssh}"

emit_check startup_task_present 'true' "$(evidence_value startup_task_present)"
emit_check startup_task_state 'Running' "$(evidence_value startup_task_state)"
emit_check startup_task_execution_time_limit 'PT0S' "$(evidence_value startup_task_execution_time_limit)"
emit_check startup_task_boot_trigger_count '1' "$(evidence_value startup_task_boot_trigger_count)"
emit_check startup_task_boot_delay 'PT30S' "$(evidence_value startup_task_boot_delay)"
startup_arguments="$(evidence_value startup_task_arguments)"
if [[ "${startup_arguments}" == *'-d ArtVault'* && "${startup_arguments}" == *'/usr/bin/sleep infinity'* ]]; then
  printf 'CHECK startup_task_action PASS actual=%q\n' "${startup_arguments}"
else
  printf 'CHECK startup_task_action FAIL actual=%q\n' "${startup_arguments}"
  failures=$((failures + 1))
fi
startup_last_result="$(evidence_value startup_task_last_result)"
if [[ "${startup_last_result}" == '267009' ]]; then
  # 0x00041301 (SCHED_S_TASK_RUNNING) is the expected result for the
  # deliberately non-terminating `sleep infinity` keepalive action.
  printf 'CHECK startup_task_last_result PASS actual=%q meaning=SCHED_S_TASK_RUNNING\n' \
    "${startup_last_result}"
else
  printf 'CHECK startup_task_last_result FAIL expected=267009 actual=%q\n' \
    "${startup_last_result}"
  failures=$((failures + 1))
fi

existing_machine_id="$(evidence_value existing_machine_id)"
artvault_machine_id="$(evidence_value artvault_machine_id)"
if [[ "${existing_distro_mode}" == 'running' ]]; then
  emit_nonempty_check existing_machine_id "${existing_machine_id}"
  if [[ -n "${artvault_machine_id}" && -n "${existing_machine_id}" && "${artvault_machine_id}" != "${existing_machine_id}" ]]; then
    printf 'CHECK distro_machine_ids_distinct PASS\n'
  else
    printf 'CHECK distro_machine_ids_distinct FAIL artvault=%q existing=%q\n' \
      "${artvault_machine_id}" "${existing_machine_id}"
    failures=$((failures + 1))
  fi
  emit_positive_check existing_transitvpn_process_count "$(evidence_value existing_transitvpn_process_count)"
  emit_positive_check existing_factory_daemon_count "$(evidence_value existing_factory_daemon_count)"
else
  emit_check legacy_transit_task_present 'false' "$(evidence_value legacy_transit_task_present)"
  emit_check retired_ubuntu_archive_present 'true' "$(evidence_value retired_ubuntu_archive_present)"
  emit_check retired_ubuntu_archive_bytes \
    "${expected_retired_archive_bytes}" \
    "$(evidence_value retired_ubuntu_archive_bytes)"
  emit_check retired_ubuntu_stage_receipt_present 'true' \
    "$(evidence_value retired_ubuntu_stage_receipt_present)"
  emit_check retired_ubuntu_verify_receipt_present 'true' \
    "$(evidence_value retired_ubuntu_verify_receipt_present)"
  emit_check retired_ubuntu_retire_receipt_present 'true' \
    "$(evidence_value retired_ubuntu_retire_receipt_present)"
  emit_check retired_ubuntu_archive_sha256_receipt \
    "${expected_retired_archive_sha256}" \
    "$(evidence_value retired_ubuntu_archive_sha256_receipt)"
  emit_check retired_ubuntu_recovery_passed 'true' \
    "$(evidence_value retired_ubuntu_recovery_passed)"
  emit_check retired_ubuntu_source_deleted 'true' \
    "$(evidence_value retired_ubuntu_source_deleted)"
fi
emit_check host_sshd_running 'Running' "$(evidence_value host_service_sshd_status)"
emit_check host_tailscale_running 'Running' "$(evidence_value host_service_tailscale_status)"
emit_check host_rustdesk_running 'Running' "$(evidence_value host_service_rustdesk_status)"

emit_check serge_account_present 'true' "$(evidence_value serge_account_present)"
emit_check serge_account_enabled 'true' "$(evidence_value serge_account_enabled)"
emit_check serge_is_administrator 'true' "$(evidence_value serge_is_administrator)"
emit_check serge_password_required 'true' "$(evidence_value serge_password_required)"
emit_check serge_may_change_password 'true' "$(evidence_value serge_may_change_password)"
emit_check serge_password_change_required 'true' "$(evidence_value serge_password_change_required)"
emit_check serge_has_direct_vhd_ace 'false' "$(evidence_value serge_has_direct_vhd_ace)"
emit_check uac_enabled 'true' "$(evidence_value uac_enabled)"

if [[ "$(evidence_value bitlocker_protection_on)" != 'true' ]]; then
  emit_warning bitlocker 'C: protection is not reported On'
fi

printf 'SUMMARY failures=%d warnings=%d\n' "${failures}" "${warnings}"
if (( failures > 0 )); then
  exit 1
fi
