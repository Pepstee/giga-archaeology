#Requires -Version 5.1

<#
.SYNOPSIS
Completes a Windows-profile migration using an exact ArtVault-generated plan.

.DESCRIPTION
This host-side companion exists because ArtVault intentionally has WSL interop
disabled and DrvFS cannot remove some files protected by Windows ACLs. It only
removes regular files beneath C:\Users\gutua whose current SHA-256 matches the
digest in a caller-confirmed plan. It never deletes directories or schedules a
delete for reboot.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$PlanPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{64}$')]
    [string]$PlanSha256,

    [Parameter(Mandatory = $true)]
    [string]$ResultPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-SharedFileSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LiteralPath
    )

    $stream = $null
    $sha256 = $null
    try {
        # The final Windows profile databases remain open by per-user services.
        # Read them with the same sharing semantics as those services instead of
        # weakening the exact-hash deletion gate.
        $share = [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete
        $stream = [System.IO.FileStream]::new(
            $LiteralPath,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            $share
        )
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        return ([System.BitConverter]::ToString(
                $sha256.ComputeHash($stream)
            )).Replace('-', '').ToLowerInvariant()
    }
    finally {
        if ($null -ne $sha256) {
            $sha256.Dispose()
        }
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }
}

$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$currentPrincipal = New-Object System.Security.Principal.WindowsPrincipal($currentIdentity)
$isAdministrator = $currentPrincipal.IsInRole(
    [System.Security.Principal.WindowsBuiltInRole]::Administrator
)

$sourceRoot = [System.IO.Path]::GetFullPath('C:\Users\gutua')
$sourcePrefix = $sourceRoot.TrimEnd('\') + '\'
$planFullPath = [System.IO.Path]::GetFullPath($PlanPath)
$resultFullPath = [System.IO.Path]::GetFullPath($ResultPath)
$programDataRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $env:ProgramData 'ArtVaultMigration')
)
$programDataPrefix = $programDataRoot.TrimEnd('\') + '\'

if (-not $planFullPath.StartsWith(
        $programDataPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw 'PlanPath must be beneath the dedicated ProgramData migration directory.'
}
if (-not $resultFullPath.StartsWith(
        $programDataPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw 'ResultPath must be beneath the dedicated ProgramData migration directory.'
}
if ($planFullPath -eq $resultFullPath) {
    throw 'PlanPath and ResultPath must be different files.'
}

$resultDirectory = Split-Path -Parent $resultFullPath
[System.IO.Directory]::CreateDirectory($resultDirectory) | Out-Null
$writeProbePath = Join-Path $resultDirectory (
    '.cutover-write-probe-' + [System.Guid]::NewGuid().ToString('N') + '.tmp'
)
try {
    [System.IO.File]::WriteAllText($writeProbePath, 'preflight')
}
finally {
    if ([System.IO.File]::Exists($writeProbePath)) {
        [System.IO.File]::Delete($writeProbePath)
    }
}

$actualPlanSha256 = (Get-FileHash -LiteralPath $planFullPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualPlanSha256 -ne $PlanSha256) {
    throw 'The supplied plan digest does not match PlanPath.'
}

$lines = @([System.IO.File]::ReadAllLines($planFullPath))
if ($lines.Count -lt 3 -or
    $lines[0] -cne 'schema=giga.artvault-windows-host-delete-plan.v1' -or
    $lines[1] -cne 'source_root=C:\Users\gutua') {
    throw 'The plan header is missing or unsupported.'
}

$entries = New-Object System.Collections.Generic.List[object]
$seenPaths = New-Object 'System.Collections.Generic.HashSet[string]' (
    [System.StringComparer]::OrdinalIgnoreCase
)

foreach ($line in $lines[2..($lines.Count - 1)]) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        throw 'The plan contains an empty entry.'
    }
    $separator = $line.IndexOf('|')
    if ($separator -ne 64) {
        throw 'The plan contains an entry with an invalid separator position.'
    }
    $expectedSha256 = $line.Substring(0, 64)
    $relativePath = $line.Substring(65)
    if ($expectedSha256 -cnotmatch '^[0-9a-f]{64}$' -or
        [string]::IsNullOrWhiteSpace($relativePath) -or
        [System.IO.Path]::IsPathRooted($relativePath)) {
        throw 'The plan contains an invalid digest or relative path.'
    }

    $segments = @($relativePath -split '[\\/]')
    if ($segments.Count -eq 0 -or $segments -contains '..' -or $segments -contains '.') {
        throw 'The plan contains an unsafe path segment.'
    }
    $normalizedRelativePath = $relativePath.Replace('/', '\')
    $fullPath = [System.IO.Path]::GetFullPath(
        (Join-Path $sourceRoot $normalizedRelativePath)
    )
    if (-not $fullPath.StartsWith(
            $sourcePrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
        throw 'A plan entry resolves outside the fixed source profile.'
    }
    if (-not $seenPaths.Add($fullPath)) {
        throw 'The plan contains a duplicate source path.'
    }
    $entries.Add([pscustomobject]@{
        ExpectedSha256 = $expectedSha256
        RelativePath = $relativePath
        FullPath = $fullPath
    })
}

$failures = New-Object System.Collections.Generic.List[string]
$deletedCount = 0L
$deletedBytes = 0L
$alreadyAbsentCount = 0L
$takeownPath = Join-Path $env:SystemRoot 'System32\takeown.exe'
$icaclsPath = Join-Path $env:SystemRoot 'System32\icacls.exe'

foreach ($entry in $entries) {
    if (-not [System.IO.File]::Exists($entry.FullPath)) {
        $alreadyAbsentCount++
        continue
    }

    try {
        $item = Get-Item -LiteralPath $entry.FullPath -Force
        if ($item.PSIsContainer -or
            (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
            $failures.Add("not-regular-file|$($entry.RelativePath)")
            continue
        }
        $actualSha256 = Get-SharedFileSha256 -LiteralPath $entry.FullPath
        if ($actualSha256 -ne $entry.ExpectedSha256) {
            $failures.Add("hash-mismatch|$($entry.RelativePath)")
            continue
        }
        $fileBytes = [int64]$item.Length

        try {
            Remove-Item -LiteralPath $entry.FullPath -Force -ErrorAction Stop
        }
        catch {
            if (-not $isAdministrator) {
                throw
            }
            & $takeownPath /F $entry.FullPath /A *> $null
            $takeownStatus = $LASTEXITCODE
            & $icaclsPath $entry.FullPath /grant:r '*S-1-5-32-544:F' /C *> $null
            $icaclsStatus = $LASTEXITCODE
            if ($takeownStatus -ne 0 -or $icaclsStatus -ne 0) {
                throw 'Exact-file ownership or ACL repair failed.'
            }
            Remove-Item -LiteralPath $entry.FullPath -Force -ErrorAction Stop
        }

        if ([System.IO.File]::Exists($entry.FullPath)) {
            throw 'The file still exists after Remove-Item returned.'
        }
        $deletedCount++
        $deletedBytes += $fileBytes
    }
    catch {
        $failures.Add("delete-failed|$($entry.RelativePath)")
    }
}

$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($resultFullPath, $failures, $utf8WithoutBom)

[pscustomobject]@{
    schema = 'giga.artvault-windows-host-cutover-result.v1'
    plan_sha256 = $actualPlanSha256
    planned_files = $entries.Count
    deleted_files = $deletedCount
    deleted_file_bytes = $deletedBytes
    already_absent_files = $alreadyAbsentCount
    failure_count = $failures.Count
    result_path = $resultFullPath
    ran_as_administrator = $isAdministrator
} | ConvertTo-Json -Compress

if ($failures.Count -ne 0) {
    exit 1
}
