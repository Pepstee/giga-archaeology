#Requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$WallpaperPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{64}$')]
    [string]$WallpaperSha256,

    [Parameter(Mandatory = $true)]
    [string]$TaskName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$wallpaperFullPath = [System.IO.Path]::GetFullPath($WallpaperPath)
$expectedRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $env:ProgramData 'ArtVault\Wallpapers')
).TrimEnd('\') + '\'
if (-not $wallpaperFullPath.StartsWith(
        $expectedRoot,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw 'WallpaperPath must be beneath the shared ArtVault wallpaper directory.'
}
if (-not (Test-Path -LiteralPath $wallpaperFullPath -PathType Leaf)) {
    throw 'The wallpaper file does not exist.'
}
$actualSha256 = (Get-FileHash -LiteralPath $wallpaperFullPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualSha256 -ne $WallpaperSha256) {
    throw 'The wallpaper does not match its expected SHA-256 digest.'
}

$desktopKey = 'HKCU:\Control Panel\Desktop'
New-Item -Path $desktopKey -Force | Out-Null
Set-ItemProperty -Path $desktopKey -Name Wallpaper -Value $wallpaperFullPath
Set-ItemProperty -Path $desktopKey -Name WallpaperStyle -Value '6'
Set-ItemProperty -Path $desktopKey -Name TileWallpaper -Value '0'

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ArtVaultWallpaper {
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool SystemParametersInfo(
        int action,
        int parameter,
        string value,
        int flags
    );
}
'@

$spiSetDesktopWallpaper = 0x0014
$spiUpdateIniFile = 0x0001
$spiSendChange = 0x0002
$applied = [ArtVaultWallpaper]::SystemParametersInfo(
    $spiSetDesktopWallpaper,
    0,
    $wallpaperFullPath,
    ($spiUpdateIniFile -bor $spiSendChange)
)
if (-not $applied) {
    $errorCode = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    throw "SystemParametersInfo failed with Win32 error $errorCode."
}

$receiptDirectory = Join-Path $expectedRoot 'receipts'
New-Item -ItemType Directory -Force -Path $receiptDirectory | Out-Null
$receiptPath = Join-Path $receiptDirectory ("{0}.json" -f $env:USERNAME.ToLowerInvariant())
[pscustomobject]@{
    schema = 'giga.windows-wallpaper.v1'
    applied_at_utc = [DateTime]::UtcNow.ToString('o')
    username = $env:USERNAME
    user_sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    wallpaper_path = $wallpaperFullPath
    wallpaper_sha256 = $actualSha256
    placement = 'fit'
} | ConvertTo-Json -Compress | Set-Content -LiteralPath $receiptPath -Encoding UTF8

try {
    Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null
}
catch {
    # The wallpaper has already been applied. A failed self-disable only means
    # the idempotent task may run again at the next sign-in.
}
