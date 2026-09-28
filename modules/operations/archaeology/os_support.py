"""Small cross-platform primitives shared by local Archaeology stores."""

from __future__ import annotations

import errno
import os
import shutil
from typing import BinaryIO


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
