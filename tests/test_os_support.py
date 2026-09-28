from __future__ import annotations

import errno
import sys

import pytest

from modules.operations.archaeology import os_support


class _FakeMsvcrt:
    LK_LOCK = 1
    LK_NBLCK = 2
    LK_UNLCK = 3

    def __init__(self, error: OSError | None = None) -> None:
        self.error = error

    def locking(self, _fd: int, _mode: int, _size: int) -> None:
        if self.error is not None:
            raise self.error


def test_windows_nonblocking_lock_maps_contention_to_blocking_io_error(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / "lock"
    fake_msvcrt = _FakeMsvcrt(OSError(errno.EACCES, "lock violation"))
    monkeypatch.setattr(os_support.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    with lock_path.open("a+b") as handle:
        with pytest.raises(BlockingIOError, match="lock is already held"):
            os_support.lock_file(handle, blocking=False)


def test_windows_nonblocking_lock_preserves_unrelated_os_error(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / "lock"
    error = OSError(errno.ENOENT, "invalid lock target")
    fake_msvcrt = _FakeMsvcrt(error)
    monkeypatch.setattr(os_support.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    with lock_path.open("a+b") as handle:
        with pytest.raises(OSError) as raised:
            os_support.lock_file(handle, blocking=False)

    assert not isinstance(raised.value, BlockingIOError)
    assert raised.value.errno == errno.ENOENT


def test_windows_sharing_violation_winerror_counts_as_contention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = OSError("sharing violation")
    error.winerror = 32
    assert os_support._is_windows_lock_contention(error)
