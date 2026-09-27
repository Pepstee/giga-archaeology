"""Small operating-system primitives shared by Archaeologist storage owners."""

from __future__ import annotations

import os
import shutil
from typing import BinaryIO


def git_executable() -> str | None:
    """Resolve Git from the user's installation instead of a host-specific path."""
    return shutil.which("git")


def git_environment(executable: str) -> dict[str, str]:
    """Return the minimal deterministic environment shared by local Git reads."""
    return {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "PATH": os.pathsep.join((os.path.dirname(executable), os.defpath)),
        "TZ": "UTC",
    }


def lock_file(handle: BinaryIO, *, blocking: bool = True) -> None:
    """Lock one byte (Windows) or the lock file (POSIX), normalising contention."""
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
            if not blocking:
                raise BlockingIOError("lock is already held") from exc
            raise
        return

    import fcntl

    operation = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
    fcntl.flock(handle.fileno(), operation)


def unlock_file(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
