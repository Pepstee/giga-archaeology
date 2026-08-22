#Requires -Version 5.1
#Requires -RunAsAdministrator

[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$TargetUser = 'serge',

    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$TaskName = 'GIGA-Serge-Wallpaper',

    [Parameter(Mandatory = $true)]
    [string]$WallpaperPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{64}$')]
    [string]$WallpaperSha256,

    [Parameter(Mandatory = $true)]
    [string]$ApplyScriptPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{64}$')]
    [string]$ApplyScriptSha256
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$wallpaperRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $env:ProgramData 'ArtVault\Wallpapers')
).TrimEnd('\') + '\'

function Resolve-VerifiedFile {
    param(
        [Parameter(Mandatory = $true)][string]$LiteralPath,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256
    )

    $fullPath = [System.IO.Path]::GetFullPath($LiteralPath)
    if (-not $fullPath.StartsWith(
            $wallpaperRoot,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
        throw "Verified file must be beneath $wallpaperRoot"
    }
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        throw "Verified file does not exist: $fullPath"
    }
    $actualSha256 = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $ExpectedSha256) {
        throw "Verified file digest mismatch: $fullPath"
    }
    return $fullPath
}

$wallpaperFullPath = Resolve-VerifiedFile `
    -LiteralPath $WallpaperPath `
    -ExpectedSha256 $WallpaperSha256
$applyScriptFullPath = Resolve-VerifiedFile `
    -LiteralPath $ApplyScriptPath `
    -ExpectedSha256 $ApplyScriptSha256

$localUser = Get-LocalUser -Name $TargetUser -ErrorAction Stop
if (-not $localUser.Enabled) {
    throw "Target local user is disabled: $TargetUser"
}

$targetAccount = "$env:COMPUTERNAME\$TargetUser"
$targetSid = (
    New-Object System.Security.Principal.NTAccount($env:COMPUTERNAME, $TargetUser)
).Translate([System.Security.Principal.SecurityIdentifier]).Value
if ($targetSid -ne $localUser.SID.Value) {
    throw 'The resolved target account SID does not match Get-LocalUser.'
}

$powerShellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments = @(
    '-NoLogo'
    '-NoProfile'
    '-NonInteractive'
    '-ExecutionPolicy Bypass'
    ('-File "{0}"' -f $applyScriptFullPath)
    ('-WallpaperPath "{0}"' -f $wallpaperFullPath)
    ('-WallpaperSha256 {0}' -f $WallpaperSha256)
    ('-TaskName {0}' -f $TaskName)
) -join ' '

$action = New-ScheduledTaskAction -Execute $powerShellExe -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $targetAccount
$principal = New-ScheduledTaskPrincipal `
    -UserId $targetAccount `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Apply the shared Matrix wallpaper inside Serge''s profile at first interactive sign-in.' `
    -Force | Out-Null

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if ($task.Principal.UserId -notin @($targetAccount, $targetSid)) {
    throw 'The wallpaper task principal does not match the Serge account.'
}
if ($task.Principal.LogonType -ne 'Interactive') {
    throw 'The wallpaper task is not restricted to an interactive logon.'
}
if ($task.Actions.Count -ne 1 -or
    $task.Actions[0].Execute -ne $powerShellExe -or
    $task.Actions[0].Arguments -ne $arguments) {
    throw 'The wallpaper task action does not match the verified installer contract.'
}

$receiptDirectory = Join-Path $wallpaperRoot 'receipts'
New-Item -ItemType Directory -Force -Path $receiptDirectory | Out-Null
$receiptPath = Join-Path $receiptDirectory 'serge-task-install.json'
[pscustomobject]@{
    schema = 'giga.windows-wallpaper-task.v1'
    installed_at_utc = [DateTime]::UtcNow.ToString('o')
    task_name = $TaskName
    target_user = $TargetUser
    target_sid = $targetSid
    principal = $task.Principal.UserId
    logon_type = $task.Principal.LogonType.ToString()
    run_level = $task.Principal.RunLevel.ToString()
    wallpaper_path = $wallpaperFullPath
    wallpaper_sha256 = $WallpaperSha256
    apply_script_path = $applyScriptFullPath
    apply_script_sha256 = $ApplyScriptSha256
    state = $task.State.ToString()
} | ConvertTo-Json -Compress | Set-Content -LiteralPath $receiptPath -Encoding UTF8

Get-Content -LiteralPath $receiptPath
