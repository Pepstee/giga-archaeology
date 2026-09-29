"""Minimal deterministic PEP 517 backend for the Archaeology library wheel; adapted from the existing GIGA PEP 517 backend."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import re
import stat
import tomllib
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

NAME = "giga_archaeology"
DISPLAY_NAME = "giga-archaeology"
VERSION = "0.1.3b3"
DIST_INFO = f"{NAME}-{VERSION}.dist-info"
# Required eagerly by mapper compiler identity, including Python-only scans.
REQUIRED_DEPENDENCIES = [
    "tree-sitter==0.26.0",
    "tree-sitter-bash==0.25.1",
    "tree-sitter-javascript==0.25.0",
    "tree-sitter-typescript==0.23.2",
]
ROOT = Path(__file__).resolve().parents[3]
# Reused from the modularisation donor. Keep an explicit code-only allowlist:
# discovering arbitrary files in this mixed private/source checkout is forbidden.
SOURCE_FILES = (
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "THIRD_PARTY_NOTICES.md",
    "architecture/archaeology/BETA_VALIDATION.md",
    "architecture/archaeology/LOCATION_INVENTORY.md",
    'modules/operations/archaeologist/__init__.py',
    'modules/operations/archaeology/__init__.py',
    'modules/operations/archaeology/benchmark.py',
    'modules/operations/archaeology/capability_feed.py',
    'modules/operations/archaeology/cgc_bridge.py',
    'modules/operations/archaeology/cleanup_map.py',
    'modules/operations/archaeology/consultation.py',
    'modules/operations/archaeology/counterevidence.py',
    'modules/operations/archaeology/divergence.py',
    'modules/operations/archaeology/dossier.py',
    'modules/operations/archaeology/evidence.py',
    'modules/operations/archaeology/flow_policy.py',
    'modules/operations/archaeology/governance_map.py',
    'modules/operations/archaeology/history.py',
    'modules/operations/archaeology/hypotheses.py',
    'modules/operations/archaeology/inventory.py',
    'modules/operations/archaeology/javascript_map.py',
    'modules/operations/archaeology/judge.py',
    'modules/operations/archaeology/location_inventory.py',
    'modules/operations/archaeology/map_catalog.py',
    'modules/operations/archaeology/mapper.py',
    'modules/operations/archaeology/navigation_inventory.py',
    'modules/operations/archaeology/navigation_maintenance.py',
    'modules/operations/archaeology/os_support.py',
    'modules/operations/archaeology/operational_map.py',
    'modules/operations/archaeology/python_map.py',
    'modules/operations/archaeology/quality_map.py',
    'modules/operations/archaeology/quarantine.py',
    'modules/operations/archaeology/retention.py',
    'modules/operations/archaeology/runtime_map.py',
    'modules/operations/archaeology/sandbox.py',
    'modules/operations/archaeology/scip_map.py',
    'modules/operations/archaeology/semantic_graph.py',
    'modules/operations/archaeology/shell_map.py',
    'modules/operations/scripts/archaeologist.py',
    'modules/operations/scripts/archaeology.py',
)
# Runnable contributor/user demo belongs in the source archive, not the runtime wheel.
SDIST_FILES = (
    "examples/quickstart.py",
)


def _read_source(relative: str) -> bytes:
    path = ROOT
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"symlink source forbidden: {relative}")
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"source must be a regular file: {relative}")
    return path.read_bytes()


def _project() -> dict[str, Any]:
    project = tomllib.loads(_read_source("pyproject.toml").decode())["project"]
    if project["name"] != DISPLAY_NAME or project["version"] != VERSION:
        raise ValueError("project identity disagrees with build backend")
    if project.get("dependencies") != REQUIRED_DEPENDENCIES or project.get("dynamic"):
        raise ValueError("Archaeology requires the pinned parser backends")
    if project.get("license") != "MIT" or project.get("license-files") != ["LICENSE"]:
        raise ValueError("Archaeology licence metadata must match the MIT release")
    extras = project.get("optional-dependencies", {})
    if not isinstance(extras, dict):
        raise ValueError("optional dependencies must be named groups")
    for name, requirements in extras.items():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError("optional dependency name must be normalised")
        if not isinstance(requirements, list) or not requirements:
            raise ValueError("optional dependency group must contain requirements")
        if any(not isinstance(item, str) or not item or any(c in item for c in "\r\n;")
               for item in requirements):
            raise ValueError("optional requirements must be single-line and unconditional")
    return project


def _metadata() -> bytes:
    project = _project()
    dependencies = "".join(
        f"Requires-Dist: {requirement}\n" for requirement in project["dependencies"]
    )
    extras = "".join(
        f"Provides-Extra: {name}\n" + "".join(
            f'Requires-Dist: {requirement}; extra == "{name}"\n'
            for requirement in requirements
        )
        for name, requirements in sorted(project.get("optional-dependencies", {}).items())
    )
    return (
        "Metadata-Version: 2.4\n"
        "License-Expression: MIT\n"
        "License-File: LICENSE\n"
        f"Name: {project['name']}\n"
        f"Version: {project['version']}\n"
        f"Summary: {project['description']}\n"
        f"Requires-Python: {project['requires-python']}\n"
        f"{dependencies}"
        f"{extras}"
        "Description-Content-Type: text/markdown\n\n"
        + _read_source("README.md").decode("utf-8")
    ).encode()


def _wheel() -> bytes:
    return b"Wheel-Version: 1.0\nGenerator: giga-build-backend 1\nRoot-Is-Purelib: true\nTag: py3-none-any\n"


def _entry_points() -> bytes:
    return ("[console_scripts]\n" + "".join(
        f"{name} = {target}\n" for name, target in sorted(_project()["scripts"].items())
    )).encode()


def _sources() -> Iterable[tuple[str, bytes]]:
    for relative in sorted(SOURCE_FILES):
        yield relative, _read_source(relative)


def _record_line(path: str, content: bytes) -> tuple[str, str, str]:
    digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
    return path, f"sha256={digest}", str(len(content))


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, (1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def _wheel_members() -> list[tuple[str, bytes]]:
    members = list(_sources())
    members.extend((
        (f"{DIST_INFO}/licenses/LICENSE", _read_source("LICENSE")),
        (f"{DIST_INFO}/METADATA", _metadata()),
        (f"{DIST_INFO}/WHEEL", _wheel()),
        (f"{DIST_INFO}/entry_points.txt", _entry_points()),
    ))
    return sorted(members)


def get_requires_for_build_wheel(config_settings: dict[str, Any] | None = None) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    destination = Path(metadata_directory) / DIST_INFO
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "licenses").mkdir()
    (destination / "licenses" / "LICENSE").write_bytes(_read_source("LICENSE"))
    (destination / "METADATA").write_bytes(_metadata())
    (destination / "WHEEL").write_bytes(_wheel())
    (destination / "entry_points.txt").write_bytes(_entry_points())
    return DIST_INFO


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    filename = f"{NAME}-{VERSION}-py3-none-any.whl"
    destination = Path(wheel_directory) / filename
    members = _wheel_members()
    records = [_record_line(path, content) for path, content in members]
    record_path = f"{DIST_INFO}/RECORD"
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(records)
    writer.writerow((record_path, "", ""))
    members.append((record_path, buffer.getvalue().encode()))
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, content in sorted(members):
            archive.writestr(_zip_info(path), content)
    return filename


def get_requires_for_build_sdist(config_settings: dict[str, Any] | None = None) -> list[str]:
    return []


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    filename = f"{NAME}-{VERSION}.tar.gz"
    destination = Path(sdist_directory) / filename
    prefix = f"{NAME}-{VERSION}"
    sources = list(_sources()) + [
        (relative, _read_source(relative)) for relative in sorted(SDIST_FILES)
    ] + [
        ("pyproject.toml", _read_source("pyproject.toml")),
        ("PKG-INFO", _metadata()),
        (
            "modules/platform/packaging/archaeology_build_backend.py",
            _read_source("modules/platform/packaging/archaeology_build_backend.py"),
        ),
    ]
    with destination.open("wb") as raw:
        import gzip

        with (
            gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
            tarfile.open(fileobj=compressed, mode="w") as archive,
        ):
            for relative, content in sorted(sources):
                info = tarfile.TarInfo(f"{prefix}/{relative}")
                info.size = len(content)
                info.mtime = 0
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
    return filename
