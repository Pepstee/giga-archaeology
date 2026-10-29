"""Small cross-platform primitives shared by local Archaeology stores."""

from __future__ import annotations

import errno
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import BinaryIO


def current_user_id() -> int:
    """Return the host UID field used in local evidence manifests."""
    getter = getattr(os, "getuid", None)
    if getter is not None:
        return int(getter())
    # Windows exposes st_uid as zero. ACL ownership is checked separately below.
    return int(Path.home().stat().st_uid)


def _run_powershell(script: str, path: Path) -> bool:
    executable = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if executable is None:
        return False
    environment = os.environ.copy()
    environment["GIGA_ARCHAEOLOGY_PRIVATE_PATH"] = str(path)
    try:
        result = subprocess.run(
            [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def secure_new_private_directory(path: Path) -> bool:
    """Apply a protected Windows DACL to a newly created empty store."""
    if os.name != "nt":
        return True
    script = r"""
$ErrorActionPreference = 'Stop'
$path = $env:GIGA_ARCHAEOLOGY_PRIVATE_PATH
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = New-Object System.Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true, $false)
$acl.SetOwner($user)
$inherit = [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
$rights = [System.Security.AccessControl.FileSystemRights]::FullControl
$propagation = [System.Security.AccessControl.PropagationFlags]::None
$allow = [System.Security.AccessControl.AccessControlType]::Allow
foreach ($sid in @($user.Value, 'S-1-5-18', 'S-1-5-32-544')) {
    $identity = [System.Security.Principal.SecurityIdentifier]::new($sid)
    $rule = [System.Security.AccessControl.FileSystemAccessRule]::new($identity, $rights, $inherit, $propagation, $allow)
    [void]$acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $path -AclObject $acl
exit 0
"""
    return _run_powershell(script, path)


def private_directory_is_current_user(
    path: Path, metadata: os.stat_result, *, mode: int = 0o700
) -> bool:
    """Check a local store's owner and privacy boundary on the active host."""
    if not stat.S_ISDIR(metadata.st_mode):
        return False
    if os.name != "nt":
        return (
            metadata.st_uid == current_user_id()
            and stat.S_IMODE(metadata.st_mode) == mode
        )

    # Windows has no POSIX UID/mode contract. Require the current SID to own the
    # directory and reject every allow ACE except current user, SYSTEM,
    # Administrators and Creator Owner. Missing PowerShell or ACL query errors
    # fail closed.
    executable = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if executable is None:
        return False
    script = r"""
$ErrorActionPreference = 'Stop'
$path = $env:GIGA_ARCHAEOLOGY_PRIVATE_PATH
$current = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = Get-Acl -LiteralPath $path
$owner = $acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
if ($owner -ne $current.Value) { exit 31 }
$allowed = @($current.Value, 'S-1-5-18', 'S-1-5-32-544', 'S-1-3-0')
foreach ($rule in $acl.Access) {
    if ($rule.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Allow) {
        $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if ($sid -notin $allowed) { exit 32 }
    }
}
exit 0
"""
    environment = os.environ.copy()
    environment["GIGA_ARCHAEOLOGY_PRIVATE_PATH"] = str(path)
    try:
        result = subprocess.run(
            [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def set_private_file_mode(descriptor: int, mode: int) -> None:
    """Set POSIX file permissions; on Windows the verified parent ACL governs."""
    fchmod = getattr(os, "fchmod", None)
    if fchmod is not None:
        fchmod(descriptor, mode)
    elif os.name != "nt":
        raise OSError("file permission changes are unavailable on this host")


def set_private_path_mode(path: Path, mode: int) -> None:
    """Set POSIX permissions; verified Windows parent ACLs govern files."""
    if os.name != "nt":
        os.chmod(path, mode, follow_symlinks=False)


def sync_directory(path: Path) -> None:
    """Persist directory metadata where the host exposes directory fsync."""
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


_WINDOWS_LOCK_CONTENTION_ERRNOS = frozenset(
    code
    for code in (
        errno.EACCES,
        errno.EAGAIN,
        getattr(errno, "EDEADLK", None),
        getattr(errno, "EWOULDBLOCK", None),
    )
    if code is not None
)
_WINDOWS_LOCK_CONTENTION_WINERRORS = frozenset({32, 33})


def _is_windows_lock_contention(error: OSError) -> bool:
    """Return whether a Windows lock failure means that another process owns it."""
    return (
        isinstance(error, BlockingIOError)
        or error.errno in _WINDOWS_LOCK_CONTENTION_ERRNOS
        or getattr(error, "winerror", None) in _WINDOWS_LOCK_CONTENTION_WINERRORS
    )


def git_executable() -> str | None:
    """Resolve Git from the active host instead of assuming a macOS path."""
    return shutil.which("git")


def git_environment(executable: str) -> dict[str, str]:
    """Build a deterministic Git environment while retaining Windows essentials."""
    environment = {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "PATH": os.pathsep.join((os.path.dirname(executable), os.defpath)),
        "TZ": "UTC",
    }
    if os.name == "nt":
        for name in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP"):
            value = os.environ.get(name)
            if value:
                environment[name] = value
    return environment


def lock_file(handle: BinaryIO, *, blocking: bool = True) -> None:
    """Lock one byte on Windows or the open file on POSIX."""
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        if handle.read(1) == b"":
            handle.seek(0)
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(
                handle.fileno(), msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1
            )
        except OSError as exc:
            if not blocking and _is_windows_lock_contention(exc):
                raise BlockingIOError("lock is already held") from exc
            raise
        return

    import fcntl

    operation = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
    fcntl.flock(handle.fileno(), operation)


def unlock_file(handle: BinaryIO) -> None:
    """Release a lock acquired by :func:`lock_file`."""
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
