$ErrorActionPreference = 'Stop'

$taskName = 'GIGA-TransitVPN-V3-20260820'
$launcher = '/mnt/c/Users/gutua/launch_transitvpn_v3_full_codex_gigabyte.sh'
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction `
    -Execute 'wsl.exe' `
    -Argument "-d Ubuntu -- /bin/bash $launcher"
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentIdentity `
    -LogonType Interactive `
    -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 19) `
    -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
Write-Output "STARTED $taskName"
