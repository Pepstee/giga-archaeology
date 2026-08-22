#Requires -Version 5.1
#Requires -RunAsAdministrator
#Requires -Modules Microsoft.PowerShell.LocalAccounts

[CmdletBinding()]
param(
    [switch]$ResetExisting
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$InformationPreference = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'
$VerbosePreference = 'SilentlyContinue'
$WarningPreference = 'Stop'

$userName = 'serge'
$fullName = 'Serge'
$description = 'Engineering administrator; ArtVault separated'
$administratorsSid = [System.Security.Principal.SecurityIdentifier]'S-1-5-32-544'

function Get-UnbiasedRandomIndex {
    param(
        [Parameter(Mandatory)]
        [System.Security.Cryptography.RandomNumberGenerator]$Random,

        [Parameter(Mandatory)]
        [ValidateRange(1, 256)]
        [int]$UpperExclusive
    )

    $sample = New-Object byte[] 1
    $ceiling = 256 - (256 % $UpperExclusive)

    do {
        $Random.GetBytes($sample)
    } while ([int]$sample[0] -ge $ceiling)

    return [int]$sample[0] % $UpperExclusive
}

function New-StrongTemporaryPassword {
    param(
        [ValidateRange(20, 64)]
        [int]$Length = 32
    )

    # Avoid visually ambiguous characters and shell quoting characters while
    # retaining four character classes and more than 190 bits of entropy.
    $upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ'.ToCharArray()
    $lower = 'abcdefghijkmnopqrstuvwxyz'.ToCharArray()
    $digits = '23456789'.ToCharArray()
    $symbols = '!@#%*+-_=?:,.'.ToCharArray()
    $all = $upper + $lower + $digits + $symbols
    $characters = New-Object char[] $Length
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()

    try {
        # Guarantee Windows password-complexity classes, then fill and shuffle
        # with rejection-sampled cryptographic randomness (no modulo bias).
        $characters[0] = $upper[(Get-UnbiasedRandomIndex -Random $random -UpperExclusive $upper.Count)]
        $characters[1] = $lower[(Get-UnbiasedRandomIndex -Random $random -UpperExclusive $lower.Count)]
        $characters[2] = $digits[(Get-UnbiasedRandomIndex -Random $random -UpperExclusive $digits.Count)]
        $characters[3] = $symbols[(Get-UnbiasedRandomIndex -Random $random -UpperExclusive $symbols.Count)]

        for ($index = 4; $index -lt $Length; $index++) {
            $characters[$index] = $all[(Get-UnbiasedRandomIndex -Random $random -UpperExclusive $all.Count)]
        }

        for ($index = $Length - 1; $index -gt 0; $index--) {
            $swapIndex = Get-UnbiasedRandomIndex -Random $random -UpperExclusive ($index + 1)
            $temporary = $characters[$index]
            $characters[$index] = $characters[$swapIndex]
            $characters[$swapIndex] = $temporary
        }

        return -join $characters
    }
    finally {
        [Array]::Clear($characters, 0, $characters.Length)
        $random.Dispose()
    }
}

if (-not [Environment]::Is64BitProcess) {
    throw 'Run this script in 64-bit Windows PowerShell; LocalAccounts is unavailable in 32-bit PowerShell.'
}

$existing = Get-LocalUser -Name $userName -ErrorAction SilentlyContinue
if ($null -ne $existing -and -not $ResetExisting.IsPresent) {
    throw "Local user '$userName' already exists. Refusing to change it without -ResetExisting."
}

$temporaryPassword = $null
$securePassword = $null
$accountTouched = $false
$credentialEmitted = $false

try {
    $temporaryPassword = New-StrongTemporaryPassword
    $securePassword = ConvertTo-SecureString -String $temporaryPassword -AsPlainText -Force

    if ($null -eq $existing) {
        $operation = 'created'
        $account = New-LocalUser `
            -Name $userName `
            -Password $securePassword `
            -FullName $fullName `
            -Description $description `
            -AccountNeverExpires `
            -Disabled
        $accountTouched = $true

        Set-LocalUser `
            -InputObject $account `
            -AccountNeverExpires `
            -PasswordNeverExpires $false `
            -UserMayChangePassword $true `
            -Confirm:$false
    }
    else {
        $operation = 'reset'
        $account = $existing
        $accountTouched = $true

        # An explicit reset is fail-closed: the existing account remains
        # disabled if any later configuration or credential-output step fails.
        Disable-LocalUser -InputObject $account -Confirm:$false
        Set-LocalUser `
            -InputObject $account `
            -Password $securePassword `
            -FullName $fullName `
            -Description $description `
            -AccountNeverExpires `
            -PasswordNeverExpires $false `
            -UserMayChangePassword $true `
            -Confirm:$false
    }

    $account = Get-LocalUser -Name $userName
    $administrators = Get-LocalGroup -SID $administratorsSid
    $isAdministrator = @(
        Get-LocalGroupMember -Group $administrators |
            Where-Object { [string]$_.SID -eq [string]$account.SID }
    ).Count -eq 1

    if (-not $isAdministrator) {
        # Passing the LocalUser object avoids accidentally resolving a domain
        # principal with the same display name.
        Add-LocalGroupMember -Group $administrators -Member $account -Confirm:$false
    }

    # Microsoft documents PasswordExpired=1 on the WinNT provider as the
    # local-account "must change password at next logon" control.
    $adsiPath = "WinNT://$env:COMPUTERNAME/$userName,user"
    $adsiUser = [ADSI]$adsiPath
    $userFlags = [int]$adsiUser.InvokeGet('UserFlags')
    $passwordNotRequiredFlag = 0x0020
    $passwordNeverExpiresFlag = 0x10000
    $userFlags = $userFlags -band (-bnot ($passwordNotRequiredFlag -bor $passwordNeverExpiresFlag))
    $adsiUser.Put('UserFlags', $userFlags)
    $adsiUser.Put('PasswordExpired', [int]1)
    $adsiUser.SetInfo()

    Enable-LocalUser -InputObject $account -Confirm:$false

    # Re-read every required postcondition before disclosing the temporary
    # credential. Any failure leaves the account disabled and emits no secret.
    $verifiedAccount = Get-LocalUser -Name $userName
    $verifiedMembers = @(
        Get-LocalGroupMember -Group $administrators |
            Where-Object { [string]$_.SID -eq [string]$verifiedAccount.SID }
    )
    $verifiedAdsiUser = [ADSI]$adsiPath
    $passwordChangeRequired = [int]$verifiedAdsiUser.InvokeGet('PasswordExpired') -ne 0
    $verifiedUserFlags = [int]$verifiedAdsiUser.InvokeGet('UserFlags')
    $passwordNotRequired = ($verifiedUserFlags -band $passwordNotRequiredFlag) -ne 0
    $passwordNeverExpires = ($verifiedUserFlags -band $passwordNeverExpiresFlag) -ne 0

    if (-not $verifiedAccount.Enabled) {
        throw "Local user '$userName' is not enabled after provisioning."
    }
    if ($verifiedMembers.Count -ne 1) {
        throw "Local user '$userName' is not exactly once in the local Administrators group."
    }
    if (-not $verifiedAccount.PasswordRequired -or $passwordNotRequired) {
        throw "Local user '$userName' does not require a password."
    }
    if ($passwordNeverExpires) {
        throw "Local user '$userName' unexpectedly has the password-never-expires flag enabled."
    }
    if (-not $verifiedAccount.UserMayChangePassword) {
        throw "Local user '$userName' is not allowed to replace the temporary password."
    }
    if (-not $passwordChangeRequired) {
        throw "Local user '$userName' is not marked to change its password at next logon."
    }

    $result = [ordered]@{
        schema = 'giga.windows-local-account.v1'
        operation = $operation
        computer_name = $env:COMPUTERNAME
        username = $userName
        sid = [string]$verifiedAccount.SID
        administrators_sid = [string]$administratorsSid
        enabled = $true
        password_change_required = $true
        temporary_password = $temporaryPassword
        emitted_at_utc = [DateTime]::UtcNow.ToString('o')
    }

    # This is the script's only success output and the only disclosure of the
    # temporary credential. Callers must capture stdout directly; never tee it.
    $resultJson = $result | ConvertTo-Json -Compress
    [Console]::Out.WriteLine($resultJson)
    [Console]::Out.Flush()
    $credentialEmitted = $true
}
catch {
    if ($accountTouched -and -not $credentialEmitted) {
        Disable-LocalUser -Name $userName -Confirm:$false -ErrorAction SilentlyContinue
    }
    throw
}
finally {
    if ($null -ne $securePassword) {
        $securePassword.Dispose()
    }
    $temporaryPassword = $null
    $securePassword = $null
    $resultJson = $null
}
