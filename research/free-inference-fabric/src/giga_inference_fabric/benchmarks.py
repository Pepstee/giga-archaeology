from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash_fixture(path: Path) -> str:
    """Bind a benchmark fixture without following symlinks outside its admitted tree."""
    root = path.expanduser().resolve(strict=True)
    digest = hashlib.sha256()
    if root.is_file():
        digest.update(b"file\0")
        digest.update(root.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(root.read_bytes())
        return digest.hexdigest()
    if not root.is_dir():
        raise ValueError("benchmark fixture must be a regular file or directory")
    ignored_directories = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
    ignored_files = {".DS_Store"}
    files = []
    for candidate in root.rglob("*"):
        relative = candidate.relative_to(root)
        if candidate.is_symlink():
            raise ValueError(f"benchmark fixture contains a symlink: {candidate.relative_to(root)}")
        if any(part in ignored_directories for part in relative.parts):
            continue
        if candidate.is_file() and candidate.name not in ignored_files and candidate.suffix != ".pyc":
            files.append(candidate)
    for candidate in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = candidate.relative_to(root).as_posix()
        digest.update(b"path\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(candidate.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_benchmark_contract(fixture_ref: str, evaluator_ref: str) -> dict:
    fixture = Path(fixture_ref).expanduser().resolve(strict=True)
    command = shlex.split(evaluator_ref)
    if not command:
        raise ValueError("benchmark evaluator command cannot be empty")
    command_hash = hashlib.sha256(_canonical(command)).hexdigest()
    return {
        "schema": "giga.benchmark-binding.v1",
        "fixture_ref": str(fixture),
        "fixture_sha256": hash_fixture(fixture),
        "evaluator_command": command,
        "evaluator_sha256": command_hash,
    }


def verify_benchmark_contract(contract: dict) -> dict:
    expected = {
        "schema", "fixture_ref", "fixture_sha256", "evaluator_command", "evaluator_sha256",
    }
    if set(contract) != expected or contract.get("schema") != "giga.benchmark-binding.v1":
        raise ValueError("invalid benchmark binding contract")
    fixture = Path(contract["fixture_ref"])
    if hash_fixture(fixture) != contract["fixture_sha256"]:
        raise ValueError("benchmark fixture drift detected")
    command = contract["evaluator_command"]
    if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError("invalid benchmark evaluator command")
    if hashlib.sha256(_canonical(command)).hexdigest() != contract["evaluator_sha256"]:
        raise ValueError("benchmark evaluator binding drift detected")
    return {
        "schema": "giga.evaluator-contract.v1",
        "required": [],
        "forbidden": [],
        "commands": [command],
        "cwd": str(fixture if fixture.is_dir() else fixture.parent),
        "timeout_seconds": 300,
    }
