#Requires -Version 5.1
#Requires -RunAsAdministrator

[CmdletBinding()]
param(
    [ValidateRange(5, 60)]
    [int]$WakeIntervalMinutes = 10,

    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$TaskName = 'GIGA-Remote-Recovery-Wake'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$powerCfg = Join-Path $env:SystemRoot 'System32\powercfg.exe'
$cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe'
$scheme = 'SCHEME_CURRENT'
$subButtons = 'SUB_BUTTONS'
$subSleep = 'SUB_SLEEP'
$lidAction = '5ca83367-6e45-459f-a27b-476b1d01c936'
$standbyIdle = '29f6c1db-86da-48c5-9fdb-f2b67b1f44da'
$unattendedSleep = '7bc4a2f9-d8fc-4469-b07b-33eb785aaca0'
$wakeTimers = 'bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d'

function Invoke-PowerCfg {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = @(& $powerCfg @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "powercfg.exe failed ($LASTEXITCODE): $($output -join ' ')"
    }
    return $output
}

function Get-PowerSettingIndex {
    param(
        [Parameter(Mandatory = $true)][string]$Subgroup,
        [Parameter(Mandatory = $true)][string]$Setting,
        [Parameter(Mandatory = $true)][ValidateSet('AC', 'DC')][string]$PowerSource
    )

    $query = Invoke-PowerCfg -Arguments @('/qh', $scheme, $Subgroup, $Setting)
    $pattern = "Current $PowerSource Power Setting Index:\s+0x([0-9a-fA-F]+)"
    $match = [regex]::Match(($query -join "`n"), $pattern)
    if (-not $match.Success) {
        throw "Could not read $PowerSource index for power setting $Setting."
    }
    return [Convert]::ToUInt32($match.Groups[1].Value, 16)
}

$before = [ordered]@{
    ac_lid_action = Get-PowerSettingIndex -Subgroup $subButtons -Setting $lidAction -PowerSource AC
    dc_lid_action = Get-PowerSettingIndex -Subgroup $subButtons -Setting $lidAction -PowerSource DC
    ac_sleep_seconds = Get-PowerSettingIndex -Subgroup $subSleep -Setting $standbyIdle -PowerSource AC
    dc_sleep_seconds = Get-PowerSettingIndex -Subgroup $subSleep -Setting $standbyIdle -PowerSource DC
    ac_unattended_sleep_seconds = Get-PowerSettingIndex -Subgroup $subSleep -Setting $unattendedSleep -PowerSource AC
    dc_unattended_sleep_seconds = Get-PowerSettingIndex -Subgroup $subSleep -Setting $unattendedSleep -PowerSource DC
    ac_wake_timers = Get-PowerSettingIndex -Subgroup $subSleep -Setting $wakeTimers -PowerSource AC
    dc_wake_timers = Get-PowerSettingIndex -Subgroup $subSleep -Setting $wakeTimers -PowerSource DC
}

# Preserve all battery/DC behavior. On AC, closing the lid must not suspend the
# vault, normal and unattended sleep are disabled, and task wake timers are on.
Invoke-PowerCfg -Arguments @('/setacvalueindex', $scheme, $subButtons, $lidAction, '0') | Out-Null
Invoke-PowerCfg -Arguments @('/setacvalueindex', $scheme, $subSleep, $standbyIdle, '0') | Out-Null
Invoke-PowerCfg -Arguments @('/setacvalueindex', $scheme, $subSleep, $unattendedSleep, '0') | Out-Null
Invoke-PowerCfg -Arguments @('/setacvalueindex', $scheme, $subSleep, $wakeTimers, '1') | Out-Null
Invoke-PowerCfg -Arguments @('/setactive', $scheme) | Out-Null

$action = New-ScheduledTaskAction -Execute $cmdExe -Argument '/d /c exit 0'
$trigger = New-ScheduledTaskTrigger -Daily -At (Get-Date).AddMinutes(5)
$trigger.Repetition.Interval = "PT${WakeIntervalMinutes}M"
$trigger.Repetition.Duration = 'P1D'
$principal = New-ScheduledTaskPrincipal `
    -UserId 'SYSTEM' `
    -LogonType ServiceAccount `
    -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -WakeToRun

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Wake the Gigabyte from S3 sleep within ten minutes while AC wake timers are enabled.' `
    -Force | Out-Null

$after = [ordered]@{
    ac_lid_action = Get-PowerSettingIndex -Subgroup $subButtons -Setting $lidAction -PowerSource AC
    dc_lid_action = Get-PowerSettingIndex -Subgroup $subButtons -Setting $lidAction -PowerSource DC
    ac_sleep_seconds = Get-PowerSettingIndex -Subgroup $subSleep -Setting $standbyIdle -PowerSource AC
    dc_sleep_seconds = Get-PowerSettingIndex -Subgroup $subSleep -Setting $standbyIdle -PowerSource DC
    ac_unattended_sleep_seconds = Get-PowerSettingIndex -Subgroup $subSleep -Setting $unattendedSleep -PowerSource AC
    dc_unattended_sleep_seconds = Get-PowerSettingIndex -Subgroup $subSleep -Setting $unattendedSleep -PowerSource DC
    ac_wake_timers = Get-PowerSettingIndex -Subgroup $subSleep -Setting $wakeTimers -PowerSource AC
    dc_wake_timers = Get-PowerSettingIndex -Subgroup $subSleep -Setting $wakeTimers -PowerSource DC
}

if ($after.ac_lid_action -ne 0 -or
    $after.ac_sleep_seconds -ne 0 -or
    $after.ac_unattended_sleep_seconds -ne 0 -or
    $after.ac_wake_timers -ne 1) {
    throw 'The required AC remote-recovery power settings did not persist.'
}
foreach ($name in @(
        'dc_lid_action',
        'dc_sleep_seconds',
        'dc_unattended_sleep_seconds',
        'dc_wake_timers'
    )) {
    if ($after[$name] -ne $before[$name]) {
        throw "Battery/DC setting '$name' changed unexpectedly."
    }
}

$task = Get-ScheduledTask -TaskName $TaskName
if (-not $task.Settings.WakeToRun) {
    throw 'The recovery task is not configured with WakeToRun.'
}
if ($task.Principal.UserId -notin @('SYSTEM', 'S-1-5-18')) {
    throw 'The recovery task principal is not LocalSystem.'
}

$receiptDirectory = Join-Path $env:ProgramData 'ArtVault\RemoteRecovery'
New-Item -ItemType Directory -Force -Path $receiptDirectory | Out-Null
$receiptPath = Join-Path $receiptDirectory 'configuration-receipt.json'
$receipt = [ordered]@{
    schema = 'giga.remote-recovery.v1'
    configured_at_utc = [DateTime]::UtcNow.ToString('o')
    computer_name = $env:COMPUTERNAME
    task_name = $TaskName
    task_principal = $task.Principal.UserId
    wake_to_run = [bool]$task.Settings.WakeToRun
    wake_interval_minutes = $WakeIntervalMinutes
    before = $before
    after = $after
    limitation = 'Recovers from S3 sleep on AC; it cannot power on a fully shut-down laptop without firmware or external out-of-band hardware.'
}
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
$receipt | ConvertTo-Json -Depth 5 -Compress
