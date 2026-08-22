#Requires -Version 5.1
#Requires -RunAsAdministrator

<#
.SYNOPSIS
Migrates the legacy Ubuntu WSL distro into a recoverable archive held inside ArtVault.

.DESCRIPTION
This is separate from migrate_windows_profile_to_artvault.sh because it owns a different
lifecycle boundary: quiescing, exporting, recovery-testing, and finally unregistering an
entire WSL distro. Stage and Verify never delete the source distro. Retire is deliberately
gated by both a recovery-import proof and an explicit archive digest.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Plan', 'Stage', 'Verify', 'Retire')]
    [string]$Mode,

    [string]$ExpectedArchiveSha256 = '',

    [switch]$ConfirmUnregisterUbuntu
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SourceDistro = 'Ubuntu'
$VaultDistro = 'ArtVault'
$TransitTask = 'GIGA-TransitVPN-V3-20260820'
$MigrationRoot = '/srv/artvault/migrations/ubuntu-retired-20260821'
$ArchivePath = "$MigrationRoot/ubuntu-root.tar"
$PartialArchivePath = "$ArchivePath.partial"
$StageReceiptPath = "$MigrationRoot/STAGE.json"
$VerifyReceiptPath = "$MigrationRoot/VERIFY.json"
$RetireReceiptPath = "$MigrationRoot/RETIRE.json"
$ProofDistro = 'UbuntuMigrationProof'
$ProofLocation = 'C:\VirtualEntities\UbuntuMigrationProof'
$Wsl = "$env:SystemRoot\System32\wsl.exe"

function Invoke-WslText {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $stderrPath = [IO.Path]::GetTempFileName()
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & $Wsl @Arguments 2> $stderrPath
        $exitCode = $LASTEXITCODE
        $stderr = @(Get-Content -LiteralPath $stderrPath -ErrorAction SilentlyContinue)
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
    if ($exitCode -ne 0) {
        throw "wsl.exe failed ($exitCode): $($stderr -join [Environment]::NewLine)"
    }
    return @($output)
}

function Get-Distros {
    return @(
        Invoke-WslText -Arguments @('--list', '--quiet') |
            ForEach-Object { ([string]$_).Trim([char]0).Trim() } |
            Where-Object { $_ }
    )
}

function Assert-DistroPresent {
    param([Parameter(Mandatory = $true)][string]$Name)

    if ((Get-Distros) -notcontains $Name) {
        throw "Required WSL distro is not registered: $Name"
    }
}

function Invoke-VaultShell {
    param([Parameter(Mandatory = $true)][string]$Command)

    return Invoke-WslText -Arguments @('-d', $VaultDistro, '-u', 'root', '--', 'sh', '-c', $Command)
}

function Write-VaultJson {
    param(
        [Parameter(Mandatory = $true)][string]$LinuxPath,
        [Parameter(Mandatory = $true)][object]$Value
    )

    $json = ($Value | ConvertTo-Json -Depth 8 -Compress) + "`n"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    $command = "umask 077; printf '%s' '$encoded' | base64 -d > '$LinuxPath'; " +
        "chown art:art '$LinuxPath'; chmod 600 '$LinuxPath'"
    [void](Invoke-VaultShell -Command $command)
}

function Read-VaultJson {
    param([Parameter(Mandatory = $true)][string]$LinuxPath)

    $json = (Invoke-VaultShell -Command "cat '$LinuxPath'") -join "`n"
    return $json | ConvertFrom-Json
}

function Get-VaultArchiveSha256 {
    $line = ((Invoke-VaultShell -Command "sha256sum '$ArchivePath'") -join "`n").Trim()
    return ($line -split '\s+')[0].ToLowerInvariant()
}

function Assert-HexSha256 {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -notmatch '^[0-9a-fA-F]{64}$') {
        throw 'ExpectedArchiveSha256 must be exactly 64 hexadecimal characters.'
    }
}

function Invoke-Plan {
    Assert-DistroPresent -Name $SourceDistro
    Assert-DistroPresent -Name $VaultDistro

    $sourceMachineId = ((Invoke-WslText -Arguments @('-d', $SourceDistro, '-u', 'root', '--',
        'cat', '/etc/machine-id')) -join '').Trim()
    $sourceUsedBytes = ((Invoke-WslText -Arguments @('-d', $SourceDistro, '-u', 'root', '--',
        'df', '-B1', '--output=used', '/'))[-1]).Trim()
    $vaultFreeBytes = ((Invoke-WslText -Arguments @('-d', $VaultDistro, '-u', 'root', '--',
        'df', '-B1', '--output=avail', '/'))[-1]).Trim()
    $task = Get-ScheduledTask -TaskName $TransitTask -ErrorAction SilentlyContinue

    [pscustomobject]@{
        schema = 'giga.artvault-ubuntu-migration-plan.v1'
        source_distro = $SourceDistro
        source_machine_id = $sourceMachineId
        source_used_bytes = [Int64]$sourceUsedBytes
        vault_distro = $VaultDistro
        vault_free_bytes = [Int64]$vaultFreeBytes
        archive_path = $ArchivePath
        transit_task_present = $null -ne $task
        transit_task_state = if ($null -eq $task) { 'Absent' } else { [string]$task.State }
        source_deleted = $false
    } | ConvertTo-Json -Compress
}

function Invoke-Stage {
    Assert-DistroPresent -Name $SourceDistro
    Assert-DistroPresent -Name $VaultDistro

    $task = Get-ScheduledTask -TaskName $TransitTask -ErrorAction SilentlyContinue
    $taskWasEnabled = $null -ne $task -and [string]$task.State -ne 'Disabled'
    $taskWasRunning = $null -ne $task -and [string]$task.State -eq 'Running'
    $stageSucceeded = $false

    try {
        if ($null -ne $task) {
            Disable-ScheduledTask -InputObject $task | Out-Null
            if ($taskWasRunning) {
                Stop-ScheduledTask -InputObject $task
            }
        }

        & $Wsl --terminate $SourceDistro
        if ($LASTEXITCODE -ne 0) {
            throw "Could not terminate $SourceDistro before export."
        }

        [void](Invoke-VaultShell -Command (
            "install -d -o art -g art -m 700 '$MigrationRoot'; " +
            "rm -f -- '$PartialArchivePath'"
        ))

        $sourceMachineId = ((Invoke-WslText -Arguments @('-d', $SourceDistro, '-u', 'root', '--',
            'cat', '/etc/machine-id')) -join '').Trim()
        & $Wsl --terminate $SourceDistro
        if ($LASTEXITCODE -ne 0) {
            throw "Could not re-terminate $SourceDistro after reading its machine identity."
        }

        $pipeline = "wsl.exe --export $SourceDistro - --format tar | " +
            "wsl.exe -d $VaultDistro -u root -- sh -c `"umask 077; dd of='$PartialArchivePath' status=none`""
        & $env:ComSpec /d /s /c $pipeline
        if ($LASTEXITCODE -ne 0) {
            throw "The local WSL export pipeline failed with exit code $LASTEXITCODE."
        }

        [void](Invoke-VaultShell -Command "test -s '$PartialArchivePath'; tar -tf '$PartialArchivePath' >/dev/null")
        $partialShaLine = ((Invoke-VaultShell -Command "sha256sum '$PartialArchivePath'") -join "`n").Trim()
        $archiveSha256 = ($partialShaLine -split '\s+')[0].ToLowerInvariant()
        $archiveBytes = [Int64](((Invoke-VaultShell -Command "stat -c %s '$PartialArchivePath'") -join '').Trim())

        [void](Invoke-VaultShell -Command (
            "mv -f -- '$PartialArchivePath' '$ArchivePath'; " +
            "chown art:art '$ArchivePath'; chmod 600 '$ArchivePath'"
        ))

        $receipt = [ordered]@{
            schema = 'giga.artvault-ubuntu-stage.v1'
            created_at_utc = [DateTime]::UtcNow.ToString('o')
            source_distro = $SourceDistro
            source_machine_id = $sourceMachineId
            archive_path = $ArchivePath
            archive_bytes = $archiveBytes
            archive_sha256 = $archiveSha256
            tar_list_passed = $true
            transit_task_was_enabled = $taskWasEnabled
            transit_task_was_running = $taskWasRunning
            source_still_registered = $true
            source_deleted = $false
        }
        Write-VaultJson -LinuxPath $StageReceiptPath -Value $receipt
        $stageSucceeded = $true
        $receipt | ConvertTo-Json -Compress
    }
    finally {
        if (-not $stageSucceeded -and $null -ne $task) {
            if ($taskWasEnabled) {
                Enable-ScheduledTask -InputObject $task | Out-Null
            }
            if ($taskWasRunning) {
                Start-ScheduledTask -InputObject $task
            }
        }
    }
}

function Invoke-Verify {
    Assert-DistroPresent -Name $SourceDistro
    Assert-DistroPresent -Name $VaultDistro
    if ((Get-Distros) -contains $ProofDistro) {
        throw "Recovery-proof distro already exists: $ProofDistro"
    }
    if (Test-Path -LiteralPath $ProofLocation) {
        throw "Recovery-proof location already exists: $ProofLocation"
    }

    $stage = Read-VaultJson -LinuxPath $StageReceiptPath
    $archiveSha256 = Get-VaultArchiveSha256
    if ($archiveSha256 -ne [string]$stage.archive_sha256) {
        throw 'The current archive digest does not match the staging receipt.'
    }
    [void](Invoke-VaultShell -Command "tar -tf '$ArchivePath' >/dev/null")

    $proofCreated = $false
    try {
        $pipeline = "wsl.exe -d $VaultDistro -u root -- cat '$ArchivePath' | " +
            "wsl.exe --import $ProofDistro $ProofLocation - --version 2"
        & $env:ComSpec /d /s /c $pipeline
        if ($LASTEXITCODE -ne 0) {
            throw "The recovery-import pipeline failed with exit code $LASTEXITCODE."
        }
        $proofCreated = $true

        $proofMachineId = ((Invoke-WslText -Arguments @('-d', $ProofDistro, '-u', 'root', '--',
            'cat', '/etc/machine-id')) -join '').Trim()
        if ($proofMachineId -ne [string]$stage.source_machine_id) {
            throw 'Recovery import has a different machine identity from the staged source.'
        }
        [void](Invoke-WslText -Arguments @('-d', $ProofDistro, '-u', 'root', '--', 'test', '-d', '/home/gutua'))
        [void](Invoke-WslText -Arguments @('-d', $ProofDistro, '-u', 'root', '--', 'test', '-f', '/etc/os-release'))

        $receipt = [ordered]@{
            schema = 'giga.artvault-ubuntu-recovery-proof.v1'
            created_at_utc = [DateTime]::UtcNow.ToString('o')
            archive_path = $ArchivePath
            archive_sha256 = $archiveSha256
            tar_list_passed = $true
            recovery_import_passed = $true
            recovered_machine_id = $proofMachineId
            required_home_present = $true
            source_still_registered = $true
            source_deleted = $false
        }
        Write-VaultJson -LinuxPath $VerifyReceiptPath -Value $receipt
        $receipt | ConvertTo-Json -Compress
    }
    finally {
        if ($proofCreated -and (Get-Distros) -contains $ProofDistro) {
            & $Wsl --unregister $ProofDistro | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "Could not unregister temporary recovery-proof distro $ProofDistro."
            }
        }
        if (Test-Path -LiteralPath $ProofLocation) {
            $remaining = @(Get-ChildItem -LiteralPath $ProofLocation -Force)
            if ($remaining.Count -eq 0) {
                Remove-Item -LiteralPath $ProofLocation -Force
            }
        }
    }
}

function Invoke-Retire {
    if (-not $ConfirmUnregisterUbuntu) {
        throw 'Retire requires -ConfirmUnregisterUbuntu.'
    }
    Assert-HexSha256 -Value $ExpectedArchiveSha256
    Assert-DistroPresent -Name $SourceDistro
    Assert-DistroPresent -Name $VaultDistro

    $stage = Read-VaultJson -LinuxPath $StageReceiptPath
    $verify = Read-VaultJson -LinuxPath $VerifyReceiptPath
    $archiveSha256 = Get-VaultArchiveSha256
    $expected = $ExpectedArchiveSha256.ToLowerInvariant()
    if ($archiveSha256 -ne $expected -or [string]$stage.archive_sha256 -ne $expected -or
        [string]$verify.archive_sha256 -ne $expected -or -not [bool]$verify.recovery_import_passed) {
        throw 'Archive, staging receipt, recovery receipt, and requested digest do not agree.'
    }

    $task = Get-ScheduledTask -TaskName $TransitTask -ErrorAction SilentlyContinue
    if ($null -ne $task -and [string]$task.State -eq 'Running') {
        Stop-ScheduledTask -InputObject $task
    }
    if ($null -ne $task) {
        Disable-ScheduledTask -InputObject $task | Out-Null
    }

    & $Wsl --terminate $SourceDistro
    if ($LASTEXITCODE -ne 0) {
        throw "Could not terminate $SourceDistro before retirement."
    }
    & $Wsl --unregister $SourceDistro | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not unregister $SourceDistro."
    }
    if ((Get-Distros) -contains $SourceDistro) {
        throw "$SourceDistro remains registered after unregister returned success."
    }
    if ($null -ne $task) {
        Unregister-ScheduledTask -TaskName $TransitTask -Confirm:$false
    }

    $receipt = [ordered]@{
        schema = 'giga.artvault-ubuntu-retirement.v1'
        created_at_utc = [DateTime]::UtcNow.ToString('o')
        retired_distro = $SourceDistro
        archive_path = $ArchivePath
        archive_sha256 = $archiveSha256
        recovery_import_passed = $true
        transit_task_removed = $null -eq (Get-ScheduledTask -TaskName $TransitTask -ErrorAction SilentlyContinue)
        source_still_registered = $false
        source_deleted = $true
    }
    Write-VaultJson -LinuxPath $RetireReceiptPath -Value $receipt
    $receipt | ConvertTo-Json -Compress
}

switch ($Mode) {
    'Plan' { Invoke-Plan }
    'Stage' { Invoke-Stage }
    'Verify' { Invoke-Verify }
    'Retire' { Invoke-Retire }
}
