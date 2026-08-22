$ErrorActionPreference = 'Stop'

$taskName = 'GIGA-ArtVault-Startup'
$distroName = 'ArtVault'
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$installedDistros = @(wsl.exe --list --quiet | ForEach-Object { $_.Trim() })

if ($installedDistros -notcontains $distroName) {
    throw "WSL distribution '$distroName' is not registered for $currentIdentity"
}

$action = New-ScheduledTaskAction `
    -Execute "$env:SystemRoot\System32\wsl.exe" `
    -Argument "-d $distroName -u root -- /usr/bin/sleep infinity"
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = 'PT30S'
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentIdentity `
    -LogonType S4U `
    -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Keep the per-user ArtVault WSL entity running after Windows boots.' `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
Write-Output "STARTED $taskName as $currentIdentity"
