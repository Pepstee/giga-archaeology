#!/usr/bin/env python3
"""Reject private or secret-bearing blobs before they enter governed Git history.

The detector vocabulary reuses the faceless product bundle auditor from product commit
``3019de75ce478e8fd8bcec9e8f690413069c2ded`` and the preserved extracted-identity receipt from
historical GIGA commit ``7368f541``.  This file is a distinct owner because it audits exact Git
index/tree objects at the admission lifecycle, rather than copying or packaging a product tree.

Activation installs approved bytes in private Git metadata so worktree changes cannot weaken the
hook. A local operator can still deliberately disable Git hooks; ``status`` detects that drift and
the protected commit-range workflow remains the binding remote admission boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class PrivacyAdmissionError(RuntimeError):
    """A staged or committed Git object violates the private-data boundary."""


_KNOWN_PRIVATE_BLOB_SHA256 = frozenset(
    {
        "0ed48218b2637726ef2277a42aff9f0a835da6c793e679cc9f73c1352e285de3",
        "4340150d01defe3123eee3b96ac12a3d1fab998c7961080209e60ebc24a952c4",
        "74f5f2ca99135689a50a1a699475c17546f4fde89e25c283eb3921e71e74e1f9",
        "7640e8f5901ae70822f5dd5577d86ef1eac43f7c645cf9de98c3258bccb88235",
        "18196a8042deff2eeb3aa9a684de33b5ebd9acd0104d7e6814432df785a598fb",
        "5010e2ab2bf06fa7b6b3b14d943be34bfe9dd08de7d3ea238ce31d4f8293b0af",
        "0a88ce82c27c10be40b01d8b4d25587695e859a2c4f4db3aa41c8a9afeeb1e89",
        "49273c59f1214caad52b1f6af2ab8b99f9c98bc23c6d0abc1ebd94ca217dbef1",
    }
)
_KNOWN_PRIVATE_PATH_SHA256 = frozenset(
    ['3d4cc0ba6d25eb563bb6a10d29576a8e218baab7db8d7cf3e5eb5c23bbe56c76', '493923c1459d07f7336bcedf4a32eb0fa4a5d95719dcf90844da1511610920ad', '59d16d1a332d1d5cd7a216bc4abd237ed10a283c7b55d48cf61cc91364903c01', '74dd82de7066dacb835ed2c4b042ff570ccf4b1b3d114a9c7403fd79bea9ef0f', 'a7589b17e149f775159477a21ceaddea8cc65d75ebb3c596c0c91e752c4b836f', 'b925c3c61c7b88a2244b7bdd123dcb59e2266a591edcbd3f2494ea233d979a3b', 'f73487e774f081c3264c58a83223d3134c5c3c9f147d3241874d1a13e3a837b1']
)
_PRIVATE_DATA_PARTS = frozenset(
    {
        "application-data",
        "application-evidence",
        "candidate-evidence",
        "canary-data",
        "canary-evidence",
        "live-canary",
        "personal-vault",
        "portable-vault",
        "runtime_evidence",
        "vault-data",
    }
)
_PRIVATE_DATA_PREFIXES = (("applications",), ("docs", "applications"))
_PRIVATE_DOCUMENT_SUFFIXES = frozenset(
    {".doc", ".docx", ".jpg", ".jpeg", ".odt", ".pdf", ".png", ".rtf"}
)
_PRIVATE_DOCUMENT_NAMES = ("cover-letter", "cover_letter", "curriculum-vitae", "resume")
_SECRET_FILENAMES = frozenset({".env", "credentials.json", "id_ed25519", "id_rsa"})
_SECRET_SUFFIXES = frozenset({".key", ".p12", ".pem", ".pfx"})
_MAX_BLOB_BYTES = 64 * 1024 * 1024
_MAX_TOTAL_BYTES = 512 * 1024 * 1024
_TOKEN_PATTERNS = (
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(rb"\b[0-9]{8,10}:[A-Za-z0-9_-]{30,}\b"),
)
_CREDENTIAL_ASSIGNMENT = re.compile(
    rb"(?im)(?:^[ \t]*(?:export[ \t]+)?|[{,][ \t]*)"
    rb"(?P<key_quote>[\"']?)"
    rb"(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|"
    rb"refresh[_-]?token|(?:aws[_-]?)?secret[_-]?access[_-]?key|secret[_-]?key)"
    rb"(?P=key_quote)"
    rb"[ \t]*[:=][ \t]*(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s#;]+)"
)
_CONTROLLER_PATH = "scripts/staged_privacy_admission.py"
_HOOK_PATH = ".githooks/pre-commit"
_HOOK_BYTES = b"""#!/bin/sh
set -eu
echo "privacy admission is not activated; run: python3 scripts/staged_privacy_admission.py activate" >&2
exit 2
"""
_INSTALLED_HOOK_BYTES = b"""#!/bin/sh
set -eu
hook_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
exec python3 "$hook_dir/controller.py" index
"""


@dataclass(frozen=True)
class GitEntry:
    mode: str
    kind: str
    object_id: str
    path: str


def _git(
    root: Path, *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    for variable in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_WORK_TREE",
    ):
        environment.pop(variable, None)
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", *arguments],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise PrivacyAdmissionError(f"Git object inspection failed: {message}")
    return result


def _repository_root(path: Path) -> tuple[Path, tuple[int, ...]]:
    supplied = path.absolute()
    try:
        supplied_stat = supplied.lstat()
    except OSError as exc:
        raise PrivacyAdmissionError(f"repository path is unavailable: {exc}") from exc
    if stat.S_ISLNK(supplied_stat.st_mode) or not stat.S_ISDIR(supplied_stat.st_mode):
        raise PrivacyAdmissionError("repository path is not a non-symlink directory")
    result = _git(supplied, "rev-parse", "--show-toplevel")
    try:
        root = Path(result.stdout.decode("utf-8", "strict").strip())
        root_stat = root.lstat()
    except (OSError, UnicodeDecodeError) as exc:
        raise PrivacyAdmissionError("repository root is not inspectable") from exc
    if (
        not root.is_absolute()
        or stat.S_ISLNK(root_stat.st_mode)
        or not stat.S_ISDIR(root_stat.st_mode)
        or root_stat.st_uid != os.getuid()
    ):
        raise PrivacyAdmissionError(
            "repository root is not an owned non-symlink directory"
        )
    identity = (
        root_stat.st_dev,
        root_stat.st_ino,
        root_stat.st_uid,
        root_stat.st_mode,
        root_stat.st_nlink,
    )
    return root, identity


def _revalidate_root(root: Path, identity: tuple[int, ...]) -> None:
    current = root.lstat()
    observed = (
        current.st_dev,
        current.st_ino,
        current.st_uid,
        current.st_mode,
        current.st_nlink,
    )
    if observed != identity or stat.S_ISLNK(current.st_mode):
        raise PrivacyAdmissionError("repository root identity changed during admission")


def _installed_directory(root: Path, *, create: bool) -> Path:
    raw = _git(root, "rev-parse", "--git-common-dir").stdout
    try:
        value = raw.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise PrivacyAdmissionError("Git common directory is malformed") from exc
    common = Path(value)
    if not common.is_absolute():
        common = root / common
    common = common.absolute()
    try:
        common_stat = common.lstat()
    except OSError as exc:
        raise PrivacyAdmissionError("Git common directory is unavailable") from exc
    if (
        stat.S_ISLNK(common_stat.st_mode)
        or not stat.S_ISDIR(common_stat.st_mode)
        or common_stat.st_uid != os.getuid()
    ):
        raise PrivacyAdmissionError("Git common directory is unsafe")
    installed = common / "giga-privacy-admission"
    if not installed.exists() and create:
        installed.mkdir(mode=0o700)
    try:
        installed_stat = installed.lstat()
    except OSError as exc:
        raise PrivacyAdmissionError(
            "installed privacy admission directory is unavailable"
        ) from exc
    if (
        stat.S_ISLNK(installed_stat.st_mode)
        or not stat.S_ISDIR(installed_stat.st_mode)
        or installed_stat.st_uid != os.getuid()
        or stat.S_IMODE(installed_stat.st_mode) != 0o700
    ):
        raise PrivacyAdmissionError("installed privacy admission directory is unsafe")
    unexpected = sorted(
        entry.name
        for entry in os.scandir(installed)
        if entry.name not in {"controller.py", "pre-commit"}
    )
    if unexpected:
        raise PrivacyAdmissionError(
            "installed privacy admission directory contains unknown files"
        )
    return installed


def _install_file(path: Path, body: bytes) -> None:
    if path.exists() or path.is_symlink():
        current = path.lstat()
        if (
            not stat.S_ISREG(current.st_mode)
            or stat.S_ISLNK(current.st_mode)
            or current.st_uid != os.getuid()
            or current.st_nlink != 1
        ):
            raise PrivacyAdmissionError(
                f"installed privacy admission file is unsafe: {path.name}"
            )
    temporary = path.parent / f".{path.name}.install-{os.getpid()}"
    descriptor = os.open(
        temporary,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o700,
    )
    try:
        view = memoryview(body)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.replace(temporary, path)
        os.chmod(path, 0o700, follow_symlinks=False)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def _installed_file(path: Path, expected: bytes) -> str:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise PrivacyAdmissionError(
            f"installed privacy admission file is unavailable: {path.name}"
        ) from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise PrivacyAdmissionError(
            f"installed privacy admission file is unsafe: {path.name}"
        )
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        retained = os.fstat(descriptor)
        body = b""
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            body += chunk
            if len(body) > _MAX_BLOB_BYTES:
                raise PrivacyAdmissionError(
                    f"installed privacy admission file is oversized: {path.name}"
                )
    finally:
        os.close(descriptor)
    if (retained.st_dev, retained.st_ino, retained.st_size) != (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
    ) or body != expected:
        raise PrivacyAdmissionError(
            f"installed privacy admission file differs: {path.name}"
        )
    return hashlib.sha256(body).hexdigest()


def _canonical_path(raw: bytes) -> str:
    try:
        value = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise PrivacyAdmissionError("Git contains a non-UTF-8 path") from exc
    parsed = PurePosixPath(value)
    if (
        not value
        or parsed.is_absolute()
        or value != parsed.as_posix()
        or any(part in {"", ".", ".."} for part in parsed.parts)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise PrivacyAdmissionError("Git contains a non-canonical path")
    return value


def _index_entries(raw: bytes) -> dict[str, GitEntry]:
    entries: dict[str, GitEntry] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_id, stage = metadata.decode("ascii").split(" ", 2)
        except (UnicodeDecodeError, ValueError) as exc:
            raise PrivacyAdmissionError("Git index contains a malformed entry") from exc
        path = _canonical_path(raw_path)
        if stage != "0" or path in entries:
            raise PrivacyAdmissionError(
                "Git index contains an unresolved or duplicate entry"
            )
        entries[path] = GitEntry(mode, "blob", object_id, path)
    return entries


def _tree_entries(root: Path, revision: str) -> dict[str, GitEntry]:
    raw = _git(root, "ls-tree", "-r", "-z", revision).stdout
    entries: dict[str, GitEntry] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, object_id = metadata.decode("ascii").split(" ", 2)
        except (UnicodeDecodeError, ValueError) as exc:
            raise PrivacyAdmissionError("Git tree contains a malformed entry") from exc
        path = _canonical_path(raw_path)
        if path in entries:
            raise PrivacyAdmissionError("Git tree contains a duplicate path")
        entries[path] = GitEntry(mode, kind, object_id, path)
    return entries


def _contains_private_key(body: bytes) -> bool:
    for marker in (
        b"PRIVATE KEY",
        b"RSA PRIVATE KEY",
        b"EC PRIVATE KEY",
        b"OPENSSH PRIVATE KEY",
    ):
        begin = b"-----BEGIN " + marker + b"-----\n"
        end = b"-----END " + marker + b"-----"
        start = body.find(begin)
        finish = body.find(end, start + len(begin)) if start >= 0 else -1
        if finish < 0:
            continue
        payload = (
            body[start + len(begin) : finish].replace(b"\r", b"").replace(b"\n", b"")
        )
        if len(payload) >= 64 and all(
            byte in b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
            for byte in payload
        ):
            return True
    return False


def _reject_private_path(path: str) -> None:
    lowered = tuple(part.casefold() for part in PurePosixPath(path).parts)
    if hashlib.sha256(path.encode("utf-8")).hexdigest() in _KNOWN_PRIVATE_PATH_SHA256:
        raise PrivacyAdmissionError(
            "known private identity artifact is staged"
        )
    if any(
        part in _PRIVATE_DATA_PARTS
        or part.startswith("source-extracted-identity-artifacts")
        for part in lowered
    ) or any(lowered[: len(prefix)] == prefix for prefix in _PRIVATE_DATA_PREFIXES):
        raise PrivacyAdmissionError(f"private evidence or Vault path is staged: {path}")
    name = lowered[-1]
    suffix = PurePosixPath(name).suffix
    if (
        name in _SECRET_FILENAMES
        or suffix in _SECRET_SUFFIXES
        or (name.startswith(".env.") and name != ".env.example")
    ):
        raise PrivacyAdmissionError(f"secret-bearing filename is staged: {path}")
    stem = re.sub(r"[ ._]+", "-", PurePosixPath(name).stem)
    cv_token = "cv" in stem.split("-")
    if suffix in _PRIVATE_DOCUMENT_SUFFIXES and (
        cv_token or any(marker in stem for marker in _PRIVATE_DOCUMENT_NAMES)
    ):
        raise PrivacyAdmissionError(f"private career document is staged: {path}")


def _reject_private_body(path: str, body: bytes) -> str:
    digest = hashlib.sha256(body).hexdigest()
    if digest in _KNOWN_PRIVATE_BLOB_SHA256:
        raise PrivacyAdmissionError(f"known private identity blob is staged: {path}")
    if _contains_private_key(body):
        raise PrivacyAdmissionError(f"private key material is staged: {path}")
    if any(
        pattern.search(body) for pattern in _TOKEN_PATTERNS
    ) or _contains_assigned_credential(body):
        raise PrivacyAdmissionError(f"credential-shaped content is staged: {path}")
    return digest


def _contains_assigned_credential(body: bytes) -> bool:
    for match in _CREDENTIAL_ASSIGNMENT.finditer(body):
        value = match.group("value").strip().strip(b"'\"")
        if len(value) < 12:
            continue
        lowered = value.lower()
        if (
            re.fullmatch(rb"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?", value)
            or (value.startswith(b"{{") and value.endswith(b"}}"))
            or (value.startswith(b"<") and value.endswith(b">"))
            or any(
                marker in lowered
                for marker in (
                    b"change-me",
                    b"change_me",
                    b"example",
                    b"placeholder",
                    b"redacted",
                    b"your-api-key",
                    b"your_api_key",
                )
            )
        ):
            continue
        return True
    return False


def _owned_worktree_file(root: Path, relative: str, expected_mode: int) -> bytes:
    path = root / relative
    try:
        before = path.lstat()
    except OSError as exc:
        raise PrivacyAdmissionError(
            f"privacy admission file is unavailable: {relative}"
        ) from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or before.st_uid != os.getuid()
        or before.st_nlink != 1
        or stat.S_IMODE(before.st_mode) != expected_mode
    ):
        raise PrivacyAdmissionError(f"privacy admission file is unsafe: {relative}")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        retained = os.fstat(descriptor)
        if (retained.st_dev, retained.st_ino, retained.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            raise PrivacyAdmissionError(f"privacy admission file changed: {relative}")
        body = b""
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            body += chunk
            if len(body) > _MAX_BLOB_BYTES:
                raise PrivacyAdmissionError(
                    f"privacy admission file is oversized: {relative}"
                )
    finally:
        os.close(descriptor)
    after = path.lstat()
    if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ):
        raise PrivacyAdmissionError(f"privacy admission file changed: {relative}")
    return body


def _validate_admission_files(
    root: Path, entries: dict[str, GitEntry]
) -> tuple[dict[str, str], dict[str, bytes]]:
    controller = _owned_worktree_file(root, _CONTROLLER_PATH, 0o755)
    hook = _owned_worktree_file(root, _HOOK_PATH, 0o755)
    if hook != _HOOK_BYTES:
        raise PrivacyAdmissionError(
            "privacy admission hook differs from its canonical body"
        )
    identities: dict[str, str] = {}
    retained_bodies: dict[str, bytes] = {}
    for relative, expected, expected_mode in (
        (_CONTROLLER_PATH, controller, "100755"),
        (_HOOK_PATH, hook, "100755"),
    ):
        entry = entries.get(relative)
        if entry is None or entry.kind != "blob" or entry.mode != expected_mode:
            raise PrivacyAdmissionError(
                f"privacy admission file is not exact in Git: {relative}"
            )
        body = _git(root, "cat-file", "blob", entry.object_id).stdout
        if body != expected:
            raise PrivacyAdmissionError(
                f"privacy admission worktree differs from Git: {relative}"
            )
        identities[relative] = hashlib.sha256(body).hexdigest()
        retained_bodies[relative] = expected
    return identities, retained_bodies


def activate_hook(path: Path) -> dict[str, object]:
    root, identity = _repository_root(path)
    index_raw = _git(root, "ls-files", "--stage", "-z").stdout
    files, retained = _validate_admission_files(root, _index_entries(index_raw))
    installed = _installed_directory(root, create=True)
    controller = retained[_CONTROLLER_PATH]
    _install_file(installed / "controller.py", controller)
    _install_file(installed / "pre-commit", _INSTALLED_HOOK_BYTES)
    installed_files = {
        "controller.py": _installed_file(installed / "controller.py", controller),
        "pre-commit": _installed_file(installed / "pre-commit", _INSTALLED_HOOK_BYTES),
    }
    _git(root, "config", "--local", "core.hooksPath", str(installed))
    configured = _git(root, "config", "--local", "--get", "core.hooksPath").stdout
    if configured != os.fsencode(installed) + b"\n":
        raise PrivacyAdmissionError("privacy admission hook activation did not persist")
    if _git(root, "ls-files", "--stage", "-z").stdout != index_raw:
        raise PrivacyAdmissionError("Git index changed during hook activation")
    _revalidate_root(root, identity)
    return {
        "schema": "giga.staged-privacy-hook-activation.v1",
        "status": "ACTIVE",
        "hooks_path_scope": "git-common-private",
        "files": files,
        "installed_files": installed_files,
        "execution_authority_granted": False,
    }


def hook_status(path: Path) -> dict[str, object]:
    root, identity = _repository_root(path)
    configured = _git(root, "config", "--local", "--get", "core.hooksPath", check=False)
    if configured.returncode != 0:
        raise PrivacyAdmissionError("privacy admission hook is not activated")
    installed = _installed_directory(root, create=False)
    if configured.stdout != os.fsencode(installed) + b"\n":
        raise PrivacyAdmissionError("privacy admission hook is not activated")
    head = (
        _git(root, "rev-parse", "--verify", "HEAD^{commit}")
        .stdout.decode("ascii")
        .strip()
    )
    files, retained = _validate_admission_files(root, _tree_entries(root, head))
    controller = retained[_CONTROLLER_PATH]
    installed_files = {
        "controller.py": _installed_file(installed / "controller.py", controller),
        "pre-commit": _installed_file(installed / "pre-commit", _INSTALLED_HOOK_BYTES),
    }
    _revalidate_root(root, identity)
    return {
        "schema": "giga.staged-privacy-hook-status.v1",
        "status": "ACTIVE",
        "hooks_path_scope": "git-common-private",
        "head_commit": head,
        "files": files,
        "installed_files": installed_files,
        "execution_authority_granted": False,
    }


def _audit_entries(
    root: Path,
    entries: list[GitEntry],
    source: dict[str, object],
    *,
    protect_control_files: bool = False,
) -> dict[str, object]:
    manifest = hashlib.sha256()
    total = 0
    running_controller = Path(__file__).read_bytes() if protect_control_files else b""
    for entry in sorted(entries, key=lambda item: item.path):
        if entry.kind != "blob" or entry.mode not in {"100644", "100755"}:
            raise PrivacyAdmissionError(
                f"symlink, gitlink, or special entry is staged: {entry.path}"
            )
        _reject_private_path(entry.path)
        try:
            size = int(_git(root, "cat-file", "-s", entry.object_id).stdout)
        except ValueError as exc:
            raise PrivacyAdmissionError("Git reported a malformed blob size") from exc
        if size > _MAX_BLOB_BYTES or total + size > _MAX_TOTAL_BYTES:
            raise PrivacyAdmissionError(
                f"staged privacy inspection bound exceeded: {entry.path}"
            )
        body = _git(root, "cat-file", "blob", entry.object_id).stdout
        if len(body) != size:
            raise PrivacyAdmissionError(
                f"Git blob size changed during inspection: {entry.path}"
            )
        if (
            protect_control_files
            and entry.path == _CONTROLLER_PATH
            and body != running_controller
        ):
            raise PrivacyAdmissionError(
                "privacy controller update requires explicit activation before commit"
            )
        if protect_control_files and entry.path == _HOOK_PATH and body != _HOOK_BYTES:
            raise PrivacyAdmissionError(
                "privacy hook update requires exact reviewed bytes and activation"
            )
        body_sha256 = _reject_private_body(entry.path, body)
        total += size
        manifest.update(entry.mode.encode("ascii") + b"\0")
        manifest.update(entry.path.encode("utf-8") + b"\0")
        manifest.update(bytes.fromhex(body_sha256))
    return {
        "schema": "giga.staged-privacy-admission.v1",
        "status": "PASS",
        "source": source,
        "scanned_blob_count": len(entries),
        "scanned_bytes": total,
        "scanned_manifest_sha256": manifest.hexdigest(),
        "private_payload_admitted": False,
    }


def audit_index(path: Path) -> dict[str, object]:
    root, identity = _repository_root(path)
    before = _git(root, "ls-files", "--stage", "-z").stdout
    index = _index_entries(before)
    head_result = _git(root, "rev-parse", "--verify", "HEAD^{commit}", check=False)
    if head_result.returncode == 0:
        head = head_result.stdout.decode("ascii").strip()
        committed = _tree_entries(root, head)
        selected = [
            entry
            for path_name, entry in index.items()
            if path_name not in committed
            or (entry.mode, entry.object_id)
            != (committed[path_name].mode, committed[path_name].object_id)
        ]
    else:
        head = None
        selected = list(index.values())
    result = _audit_entries(
        root,
        selected,
        {
            "kind": "index",
            "base_commit": head,
            "index_sha256": hashlib.sha256(before).hexdigest(),
        },
        protect_control_files=True,
    )
    if _git(root, "ls-files", "--stage", "-z").stdout != before:
        raise PrivacyAdmissionError("Git index changed during privacy admission")
    _revalidate_root(root, identity)
    return result


def audit_range(path: Path, base: str, tip: str) -> dict[str, object]:
    root, identity = _repository_root(path)
    base_oid = (
        _git(root, "rev-parse", "--verify", f"{base}^{{commit}}")
        .stdout.decode("ascii")
        .strip()
    )
    tip_oid = (
        _git(root, "rev-parse", "--verify", f"{tip}^{{commit}}")
        .stdout.decode("ascii")
        .strip()
    )
    if (
        _git(
            root,
            "merge-base",
            "--is-ancestor",
            base_oid,
            tip_oid,
            check=False,
        ).returncode
        != 0
    ):
        raise PrivacyAdmissionError("privacy range base is not an ancestor of its tip")
    commits = _git(
        root, "rev-list", "--reverse", "--topo-order", tip_oid, f"^{base_oid}"
    ).stdout.splitlines()
    selected_by_identity: dict[tuple[str, str, str, str], GitEntry] = {}
    for raw_commit in commits:
        try:
            commit = raw_commit.decode("ascii")
        except UnicodeDecodeError as exc:
            raise PrivacyAdmissionError(
                "Git returned a malformed commit identity"
            ) from exc
        for entry in _tree_entries(root, commit).values():
            selected_by_identity[
                (entry.path, entry.mode, entry.kind, entry.object_id)
            ] = entry
    selected = list(selected_by_identity.values())
    result = _audit_entries(
        root,
        selected,
        {
            "kind": "commit-range",
            "base_commit": base_oid,
            "tip_commit": tip_oid,
            "introduced_commit_count": len(commits),
        },
    )
    _revalidate_root(root, identity)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("activate", "status", "index", "range"))
    parser.add_argument("base", nargs="?")
    parser.add_argument("tip", nargs="?")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.command != "range" and (args.base is not None or args.tip is not None):
        parser.error(f"{args.command} does not accept revisions")
    if args.command == "range" and (args.base is None or args.tip is None):
        parser.error("range requires base and tip revisions")
    try:
        if args.command == "activate":
            result = activate_hook(args.root)
        elif args.command == "status":
            result = hook_status(args.root)
        elif args.command == "index":
            result = audit_index(args.root)
        else:
            result = audit_range(args.root, args.base, args.tip)
        sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
        return 0
    except (OSError, PrivacyAdmissionError) as exc:
        print(
            json.dumps({"status": "REFUSED", "error": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
