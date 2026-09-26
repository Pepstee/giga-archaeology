"""Shared Linux isolation for the existing scanner and quarantine owners.

This replaces their common command construction without introducing another
execution workflow. Callers supply only explicit runtime inputs and scratch.
"""

from pathlib import Path
from typing import Sequence


def linux_sandbox_command(
    scratch: Path, argv: Sequence[str], *, read_only: Sequence[Path], cwd: Path
) -> list[str]:
    command = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session"]
    for runtime in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(runtime).exists():
            command.extend(["--ro-bind", runtime, runtime])
    command.extend([
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--bind", str(scratch), str(scratch),
    ])
    for path in read_only:
        command.extend(["--ro-bind", str(path), str(path)])
    command.extend(["--chdir", str(cwd), "--clearenv"])
    for key, value in {
        "PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC",
        "HOME": str(scratch), "TMPDIR": str(scratch),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
    }.items():
        command.extend(["--setenv", key, value])
    return [*command, "--", *argv]
