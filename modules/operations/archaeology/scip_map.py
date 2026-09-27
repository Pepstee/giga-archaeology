"""Privacy-bounded SCIP compiler and strict read-only index loader.

SCIP is an optional precision substrate.  It does not replace the canonical
Archaeology fact store and its observations never grant authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from .evidence import canonical_bytes, seal_document, sha256_bytes, validate_self_hash
from .navigation_inventory import NavigationRun, current_navigation_run
from .os_support import lock_file, unlock_file


SCIP_MANIFEST_SCHEMA = "giga.archaeologist.scip-index-manifest.v1"
SCIP_PROJECT_CATALOG_SCHEMA = "giga.archaeologist.scip-project-catalog.v1"
SCIP_STORE_CATALOG_SCHEMA = "giga.archaeologist.scip-store-catalog.v1"
SCIP_STORE_CURRENT_SCHEMA = "giga.archaeologist.scip-store-current.v1"
SCIP_PRODUCER_ID = "producer:scip-python-index-projector:v1"
SCIP_PYTHON_PACKAGE = "@sourcegraph/scip-python"
SCIP_PYTHON_VERSION = "0.6.6"
SCIP_PYTHON_NPM_INTEGRITY = (
    "sha512-qoKL1Rggg0o5newAFbCFAKlS0AjWxG5MA+mC28BtgxOv0DhO4zdL8u7151Fx"
    "EppDpXMVvm7+yXSjXotoVH9cMQ=="
)
SCIP_PYTHON_PACKAGE_TREE_SHA256 = (
    "0dbf91ad37f3159a7f438ce40d123f6b0d8a26671655ff82495e7df3a49097f4"
)
SCIP_PYTHON_ENTRYPOINT_SHA256 = (
    "55c645ed91e34ea4a2a7b47b1c482162cf173882e335a64c48ea6e8cbdb0ec05"
)
SCIP_PYTHON_PATCHED_ENTRYPOINT_SHA256 = (
    "c761967954ef19111c97cfe77a9590c1ce1ecc891dc22131113b9cd0632ac674"
)
SCIP_PYTHON_VENDOR_SHA256 = (
    "5a706ad958ccc0e6d41abacb441c5e21b84bc1d01720185f855b3982b00f480f"
)
SCIP_PYTHON_PYRIGHT_SHA256 = (
    "85e9edd2f09b927de696b09441f57470f06dbcb4279477034f856d76c77d47a8"
)
SCIP_PYTHON_PATCH_ID = "giga.scip-python.stdlib-package-fallback.v1"
_SCIP_PYTHON_BROKEN_FRAGMENT = (
    b"s.startsWith(this.cwd)?this.projectPackage:"
    b"this.config.pythonEnvironment.getPackageForModule(t)"
)
_SCIP_PYTHON_REPAIRED_FRAGMENT = (
    b"s.startsWith(this.cwd)?this.projectPackage:"
    b"this.config.pythonEnvironment.getPackageForModule(t)||this.guessPackage(t,s)"
)
SCIP_TYPESCRIPT_PRODUCER_ID = "producer:scip-typescript-index-projector:v1"
SCIP_TYPESCRIPT_PACKAGE = "@sourcegraph/scip-typescript"
SCIP_TYPESCRIPT_VERSION = "0.4.0"
SCIP_TYPESCRIPT_NPM_INTEGRITY = (
    "sha512-k+AtsrqmS41Sd5qjkZlHcmvoSQIvBOonRj4jpgp0KNFM6aqvMGpdSuPUqrUcg8E"
    "NTKjUbfaUVszgQwq3bCOvwA=="
)
TYPESCRIPT_SUFFIXES = (".cjs", ".js", ".jsx", ".mjs", ".ts", ".tsx")


class ScipMapError(ValueError):
    """A SCIP compiler input, index, or manifest is not trustworthy."""


@dataclass(frozen=True)
class ScipOccurrence:
    range: tuple[int, ...]
    symbol: str
    roles: int
    syntax_kind: int
    enclosing_range: tuple[int, ...]


@dataclass(frozen=True)
class ScipRelationship:
    symbol: str
    is_reference: bool
    is_implementation: bool
    is_type_definition: bool
    is_definition: bool


@dataclass(frozen=True)
class ScipSymbol:
    symbol: str
    documentation: tuple[str, ...]
    relationships: tuple[ScipRelationship, ...]
    kind: int
    display_name: str
    enclosing_symbol: str


@dataclass(frozen=True)
class ScipDocument:
    relative_path: str
    language: str
    position_encoding: int
    occurrences: tuple[ScipOccurrence, ...]
    symbols: tuple[ScipSymbol, ...]


@dataclass(frozen=True)
class ScipIndex:
    protocol_version: int
    tool_name: str
    tool_version: str
    tool_arguments: tuple[str, ...]
    project_root: str
    text_encoding: int
    documents: tuple[ScipDocument, ...]
    external_symbols: tuple[ScipSymbol, ...]


@dataclass(frozen=True)
class ScipIndexInput:
    manifest_path: Path
    index_path: Path
    manifest: Mapping[str, Any]
    index: ScipIndex
    current_inventory_receipt_sha256: str
    inventory_binding_status: str

    def manifest_record(self) -> dict[str, Any]:
        excluded = self.manifest.get("sources", {}).get("excluded_files", [])
        return {
            "manifest_path": str(self.manifest_path),
            "schema": self.manifest["schema"],
            "receipt_sha256": self.manifest["receipt_sha256"],
            "index_sha256": self.manifest["index"]["sha256"],
            "inventory_receipt_sha256": self.manifest["inventory"]["receipt_sha256"],
            "current_inventory_receipt_sha256": self.current_inventory_receipt_sha256,
            "inventory_binding_status": self.inventory_binding_status,
            "source_closure_sha256": self.manifest["sources"]["closure_sha256"],
            "documents": self.manifest["counts"]["documents"],
            "occurrences": self.manifest["counts"]["occurrences"],
            "definitions": self.manifest["counts"]["definitions"],
            "references": self.manifest["counts"]["references"],
            "relationships": self.manifest["counts"]["relationships"],
            "tool": self.manifest["tool"],
            "precision_status": self.manifest["status"],
            "excluded_files": excluded,
            "authority_granted": False,
        }


@dataclass(frozen=True)
class ScipStoreRun:
    store: Path
    run_directory: Path
    catalog: Mapping[str, Any]
    inventory_binding_status: str = "EXACT_INVENTORY_RECEIPT"

    @property
    def manifest_paths(self) -> tuple[Path, ...]:
        return tuple(
            self.run_directory / item["manifest_path"]
            for item in self.catalog["indexes"]
        )


@dataclass(frozen=True)
class ScipRefreshConfig:
    """Exact local toolchain and store used by ordinary maintenance."""

    store: Path
    node: Path
    python_indexer_entrypoint: Path
    python_package_json: Path
    typescript_indexer_entrypoint: Path
    typescript_package_json: Path
    timeout_seconds: int = 180


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _file_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _read_varint(payload: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(payload) and shift < 70:
        byte = payload[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
    raise ScipMapError("malformed SCIP protobuf varint")


def _protobuf_fields(payload: bytes) -> Iterable[tuple[int, int, Any]]:
    offset = 0
    while offset < len(payload):
        key, offset = _read_varint(payload, offset)
        number, wire = key >> 3, key & 7
        if number == 0:
            raise ScipMapError("SCIP protobuf field zero is invalid")
        if wire == 0:
            value, offset = _read_varint(payload, offset)
        elif wire == 1:
            if offset + 8 > len(payload):
                raise ScipMapError("truncated SCIP fixed64 field")
            value, offset = payload[offset : offset + 8], offset + 8
        elif wire == 2:
            length, offset = _read_varint(payload, offset)
            if length > len(payload) - offset:
                raise ScipMapError("truncated SCIP length-delimited field")
            value, offset = payload[offset : offset + length], offset + length
        elif wire == 5:
            if offset + 4 > len(payload):
                raise ScipMapError("truncated SCIP fixed32 field")
            value, offset = payload[offset : offset + 4], offset + 4
        else:
            raise ScipMapError("unsupported SCIP protobuf wire type")
        yield number, wire, value


def _text(value: bytes) -> str:
    try:
        return value.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ScipMapError("SCIP text is not strict UTF-8") from exc


def _packed_ints(value: bytes) -> tuple[int, ...]:
    values = []
    offset = 0
    while offset < len(value):
        item, offset = _read_varint(value, offset)
        values.append(item)
    return tuple(values)


def _parse_relationship(payload: bytes) -> ScipRelationship:
    values: dict[int, Any] = {}
    for number, wire, value in _protobuf_fields(payload):
        if number == 1 and wire == 2:
            values[number] = _text(value)
        elif number in {2, 3, 4, 5} and wire == 0:
            values[number] = bool(value)
    return ScipRelationship(
        symbol=values.get(1, ""),
        is_reference=values.get(2, False),
        is_implementation=values.get(3, False),
        is_type_definition=values.get(4, False),
        is_definition=values.get(5, False),
    )


def _parse_symbol(payload: bytes) -> ScipSymbol:
    symbol = display_name = enclosing_symbol = ""
    documentation: list[str] = []
    relationships: list[ScipRelationship] = []
    kind = 0
    for number, wire, value in _protobuf_fields(payload):
        if number == 1 and wire == 2:
            symbol = _text(value)
        elif number == 3 and wire == 2:
            documentation.append(_text(value))
        elif number == 4 and wire == 2:
            relationships.append(_parse_relationship(value))
        elif number == 5 and wire == 0:
            kind = int(value)
        elif number == 6 and wire == 2:
            display_name = _text(value)
        elif number == 8 and wire == 2:
            enclosing_symbol = _text(value)
    return ScipSymbol(
        symbol=symbol,
        documentation=tuple(documentation),
        relationships=tuple(relationships),
        kind=kind,
        display_name=display_name,
        enclosing_symbol=enclosing_symbol,
    )


def _parse_occurrence(payload: bytes) -> ScipOccurrence:
    ranges: list[int] = []
    enclosing: list[int] = []
    symbol = ""
    roles = syntax_kind = 0
    for number, wire, value in _protobuf_fields(payload):
        if number == 1 and wire == 2:
            ranges.extend(_packed_ints(value))
        elif number == 1 and wire == 0:
            ranges.append(int(value))
        elif number == 2 and wire == 2:
            symbol = _text(value)
        elif number == 3 and wire == 0:
            roles = int(value)
        elif number == 5 and wire == 0:
            syntax_kind = int(value)
        elif number == 7 and wire == 2:
            enclosing.extend(_packed_ints(value))
        elif number == 7 and wire == 0:
            enclosing.append(int(value))
    if len(ranges) not in {3, 4}:
        raise ScipMapError("SCIP occurrence range must contain three or four integers")
    if enclosing and len(enclosing) not in {3, 4}:
        raise ScipMapError("SCIP enclosing range must contain three or four integers")
    return ScipOccurrence(tuple(ranges), symbol, roles, syntax_kind, tuple(enclosing))


def _safe_relative_path(value: str) -> str:
    pure = PurePosixPath(value)
    if (
        not value
        or pure.is_absolute()
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != value
    ):
        raise ScipMapError("SCIP document path is not canonical and relative")
    return value


def _parse_document(payload: bytes) -> ScipDocument:
    relative_path = language = ""
    position_encoding = 0
    occurrences: list[ScipOccurrence] = []
    symbols: list[ScipSymbol] = []
    has_text = False
    for number, wire, value in _protobuf_fields(payload):
        if number == 1 and wire == 2:
            relative_path = _text(value)
        elif number == 2 and wire == 2:
            occurrences.append(_parse_occurrence(value))
        elif number == 3 and wire == 2:
            symbols.append(_parse_symbol(value))
        elif number == 4 and wire == 2:
            language = _text(value)
        elif number == 5 and wire == 2:
            has_text = bool(value)
        elif number == 6 and wire == 0:
            position_encoding = int(value)
    if has_text:
        raise ScipMapError("SCIP document embeds source text")
    return ScipDocument(
        relative_path=_safe_relative_path(relative_path),
        language=language,
        position_encoding=position_encoding,
        occurrences=tuple(occurrences),
        symbols=tuple(symbols),
    )


def _parse_metadata(payload: bytes) -> tuple[int, str, str, tuple[str, ...], str, int]:
    protocol = text_encoding = 0
    tool_name = tool_version = project_root = ""
    tool_arguments: list[str] = []
    for number, wire, value in _protobuf_fields(payload):
        if number == 1 and wire == 0:
            protocol = int(value)
        elif number == 2 and wire == 2:
            for tool_number, tool_wire, tool_value in _protobuf_fields(value):
                if tool_number == 1 and tool_wire == 2:
                    tool_name = _text(tool_value)
                elif tool_number == 2 and tool_wire == 2:
                    tool_version = _text(tool_value)
                elif tool_number == 3 and tool_wire == 2:
                    tool_arguments.append(_text(tool_value))
        elif number == 3 and wire == 2:
            project_root = _text(value)
        elif number == 4 and wire == 0:
            text_encoding = int(value)
    return (
        protocol,
        tool_name,
        tool_version,
        tuple(tool_arguments),
        project_root,
        text_encoding,
    )


def parse_scip_index(payload: bytes) -> ScipIndex:
    metadata: tuple[int, str, str, tuple[str, ...], str, int] | None = None
    documents: list[ScipDocument] = []
    external_symbols: list[ScipSymbol] = []
    for number, wire, value in _protobuf_fields(payload):
        if number == 1 and wire == 2:
            if metadata is not None:
                raise ScipMapError("SCIP index contains duplicate metadata")
            metadata = _parse_metadata(value)
        elif number == 2 and wire == 2:
            documents.append(_parse_document(value))
        elif number == 3 and wire == 2:
            external_symbols.append(_parse_symbol(value))
    if metadata is None:
        raise ScipMapError("SCIP index metadata is missing")
    paths = [document.relative_path for document in documents]
    if len(paths) != len(set(paths)):
        raise ScipMapError("SCIP documents must be unique")
    return ScipIndex(
        *metadata,
        tuple(sorted(documents, key=lambda item: item.relative_path)),
        tuple(sorted(external_symbols, key=lambda item: item.symbol)),
    )


def _eligible_python_sources(inventory: NavigationRun) -> list[dict[str, Any]]:
    database = inventory.run_directory / "inventory.sqlite3"
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            """SELECT path,content_sha256,size_bytes FROM files
               WHERE semantic_eligible=1 AND kind='regular' AND suffix='.py'
                 AND scan_error IS NULL AND hash_status IN ('hashed','reused')
                 AND content_sha256 IS NOT NULL
               ORDER BY path"""
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        raise ScipMapError("inventory contains no eligible Python sources")
    return [dict(row) for row in rows]


def _canonical_project_root(value: str) -> str:
    if value in {"", "."}:
        return "."
    return _safe_relative_path(value.rstrip("/"))


def _eligible_typescript_sources(
    inventory: NavigationRun, project_root: str
) -> list[dict[str, Any]]:
    project_root = _canonical_project_root(project_root)
    database = inventory.run_directory / "inventory.sqlite3"
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in TYPESCRIPT_SUFFIXES)
    prefix = "" if project_root == "." else f"{project_root}/"
    try:
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            f"""SELECT path,content_sha256,size_bytes FROM files
                WHERE semantic_eligible=1 AND kind='regular'
                  AND suffix IN ({placeholders})
                  AND scan_error IS NULL AND hash_status IN ('hashed','reused')
                  AND content_sha256 IS NOT NULL AND path LIKE ?
                ORDER BY path""",
            (*TYPESCRIPT_SUFFIXES, f"{prefix}%"),
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        raise ScipMapError(
            "inventory contains no eligible TypeScript/JavaScript sources "
            f"under {project_root}"
        )
    return [dict(row) for row in rows]


def _typescript_configs(
    inventory: NavigationRun, project_root: str
) -> list[dict[str, Any]]:
    project_root = _canonical_project_root(project_root)
    prefix = "" if project_root == "." else f"{project_root}/"
    expected = [f"{prefix}package.json", f"{prefix}tsconfig.json"]
    database = inventory.run_directory / "inventory.sqlite3"
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            """SELECT path,content_sha256,size_bytes FROM files
               WHERE path IN (?,?) AND kind='regular' AND scan_error IS NULL
                 AND hash_status IN ('hashed','reused')
                 AND content_sha256 IS NOT NULL
               ORDER BY path""",
            expected,
        ).fetchall()
    finally:
        connection.close()
    result = [dict(row) for row in rows]
    if [row["path"] for row in result] != sorted(expected):
        raise ScipMapError(
            "TypeScript project requires exact package.json and tsconfig.json"
        )
    return result


def discover_scip_projects(inventory_store: Path) -> dict[str, Any]:
    """Return a closed, inventory-bound catalog of supported SCIP projects."""

    inventory = current_navigation_run(inventory_store)
    database = inventory.run_directory / "inventory.sqlite3"
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        config_rows = connection.execute(
            """SELECT path,content_sha256,size_bytes FROM files
               WHERE kind='regular' AND scan_error IS NULL
                 AND hash_status IN ('hashed','reused')
                 AND content_sha256 IS NOT NULL
                 AND (path='package.json' OR path LIKE '%/package.json'
                      OR path='tsconfig.json' OR path LIKE '%/tsconfig.json')
               ORDER BY path"""
        ).fetchall()
    finally:
        connection.close()

    configs_by_root: dict[str, dict[str, dict[str, Any]]] = {}
    for row in config_rows:
        record = dict(row)
        path = PurePosixPath(record["path"])
        root = "." if str(path.parent) == "." else str(path.parent)
        configs_by_root.setdefault(root, {})[path.name] = record

    python_sources = _eligible_python_sources(inventory)
    candidates: list[dict[str, Any]] = [
        {
            "project_id": "python:repository",
            "language": "python",
            "project_root": ".",
            "disposition": "SUPPORTED",
            "eligible_for_federation": True,
            "source_closure_sha256": sha256_bytes(canonical_bytes(python_sources)),
            "source_count": len(python_sources),
            "config_count": 0,
            "missing_configs": [],
            "overlaps": [],
        }
    ]
    typescript_source_sets: dict[str, set[str]] = {}
    for project_root in sorted(configs_by_root):
        configs = configs_by_root[project_root]
        missing = sorted({"package.json", "tsconfig.json"} - set(configs))
        if missing:
            candidates.append(
                {
                    "project_id": f"typescript:{project_root}",
                    "language": "typescript-javascript",
                    "project_root": project_root,
                    "disposition": "UNSUPPORTED_INCOMPLETE_CONFIG",
                    "eligible_for_federation": False,
                    "source_closure_sha256": None,
                    "source_count": 0,
                    "config_count": len(configs),
                    "missing_configs": missing,
                    "overlaps": [],
                }
            )
            continue
        try:
            sources = _eligible_typescript_sources(inventory, project_root)
            exact_configs = _typescript_configs(inventory, project_root)
        except ScipMapError:
            candidates.append(
                {
                    "project_id": f"typescript:{project_root}",
                    "language": "typescript-javascript",
                    "project_root": project_root,
                    "disposition": "UNSUPPORTED_NO_ELIGIBLE_SOURCE",
                    "eligible_for_federation": False,
                    "source_closure_sha256": None,
                    "source_count": 0,
                    "config_count": len(configs),
                    "missing_configs": [],
                    "overlaps": [],
                }
            )
            continue
        typescript_source_sets[project_root] = {item["path"] for item in sources}
        candidates.append(
            {
                "project_id": f"typescript:{project_root}",
                "language": "typescript-javascript",
                "project_root": project_root,
                "disposition": "SUPPORTED",
                "eligible_for_federation": True,
                "source_closure_sha256": sha256_bytes(
                    canonical_bytes({"sources": sources, "configs": exact_configs})
                ),
                "source_count": len(sources),
                "config_count": len(exact_configs),
                "missing_configs": [],
                "overlaps": [],
            }
        )

    conflicts: dict[str, set[str]] = {}
    for left, right in combinations(sorted(typescript_source_sets), 2):
        if typescript_source_sets[left] & typescript_source_sets[right]:
            conflicts.setdefault(left, set()).add(right)
            conflicts.setdefault(right, set()).add(left)
    for candidate in candidates:
        project_root = candidate["project_root"]
        if project_root in conflicts:
            candidate["disposition"] = "UNSUPPORTED_OVERLAPPING_SOURCE_CLOSURE"
            candidate["eligible_for_federation"] = False
            candidate["overlaps"] = sorted(conflicts[project_root])

    candidates.sort(key=lambda item: (item["language"], item["project_root"]))
    supported = sum(item["eligible_for_federation"] for item in candidates)
    return seal_document(
        {
            "schema": SCIP_PROJECT_CATALOG_SCHEMA,
            "status": "OBSERVED_LOCAL_PROJECT_CATALOG",
            "authority": "non-authoritative-inventory-derived-project-discovery",
            "authority_granted": False,
            "generated_at": _utc_now(),
            "inventory": {
                "store": str(Path(inventory_store).resolve(strict=True)),
                "run_id": inventory.manifest["run_id"],
                "receipt_sha256": inventory.manifest["receipt_sha256"],
                "git": inventory.manifest["git"],
            },
            "detection": {
                "python": "one repository-wide eligible .py closure",
                "typescript": "exact co-located package.json and tsconfig.json",
                "overlap_policy": "mark every overlapping TypeScript closure unsupported",
                "source_text_embedded": False,
            },
            "projects": candidates,
            "counts": {
                "candidates": len(candidates),
                "supported": supported,
                "unsupported": len(candidates) - supported,
                "python": sum(item["language"] == "python" for item in candidates),
                "typescript_javascript": sum(
                    item["language"] == "typescript-javascript" for item in candidates
                ),
            },
        }
    )


def _write_atomic_document(path: Path, document: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    payload = canonical_bytes(document)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(temporary, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(descriptor)
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def current_scip_store(store: Path) -> ScipStoreRun:
    """Load the exact currently published atomic SCIP generation."""

    store = store.resolve(strict=True)
    pointer_path = store / "CURRENT.json"
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        validate_self_hash(pointer)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ScipMapError("SCIP store current pointer is invalid") from exc
    if pointer.get("schema") != SCIP_STORE_CURRENT_SCHEMA:
        raise ScipMapError("SCIP store current pointer schema is invalid")
    run_id = pointer.get("run_id")
    if not isinstance(run_id, str) or not run_id or "/" in run_id:
        raise ScipMapError("SCIP store run identity is invalid")
    run_directory = store / "runs" / run_id
    catalog_path = run_directory / "catalog.json"
    try:
        raw_catalog = catalog_path.read_bytes()
        catalog = json.loads(raw_catalog)
        validate_self_hash(catalog)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ScipMapError("SCIP store catalog is invalid") from exc
    if (
        catalog.get("schema") != SCIP_STORE_CATALOG_SCHEMA
        or sha256_bytes(raw_catalog) != pointer.get("catalog_file_sha256")
        or catalog.get("receipt_sha256") != pointer.get("catalog_receipt_sha256")
        or catalog.get("run_id") != run_id
    ):
        raise ScipMapError("SCIP store pointer and catalog differ")
    indexes = catalog.get("indexes")
    if not isinstance(indexes, list):
        raise ScipMapError("SCIP store indexes are invalid")
    excluded_files = 0
    for item in indexes:
        if not isinstance(item, dict):
            raise ScipMapError("SCIP store index record is invalid")
        manifest_path = run_directory / item.get("manifest_path", "")
        if (
            manifest_path.parent.parent != run_directory / "projects"
            or not manifest_path.is_file()
            or manifest_path.is_symlink()
        ):
            raise ScipMapError("SCIP store manifest path is unsafe")
        try:
            raw_manifest = manifest_path.read_bytes()
            manifest = json.loads(raw_manifest)
            validate_self_hash(manifest)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ScipMapError("SCIP store manifest is invalid") from exc
        if (
            sha256_bytes(raw_manifest) != item.get("manifest_file_sha256")
            or manifest.get("receipt_sha256") != item.get("manifest_receipt_sha256")
            or manifest.get("index", {}).get("sha256") != item.get("index_sha256")
            or len(manifest.get("sources", {}).get("excluded_files", []))
            != item.get("excluded_files", 0)
        ):
            raise ScipMapError("SCIP store manifest identity differs")
        excluded_files += item.get("excluded_files", 0)
        index_path = manifest_path.parent / manifest.get("index", {}).get("path", "")
        if (
            index_path.parent != manifest_path.parent
            or not index_path.is_file()
            or index_path.is_symlink()
        ):
            raise ScipMapError("SCIP store index path is unsafe")
        index_sha256, index_bytes = _file_sha256(index_path)
        if (
            index_sha256 != manifest["index"].get("sha256")
            or index_bytes != manifest["index"].get("bytes")
            or index_bytes != item.get("index_bytes")
        ):
            raise ScipMapError("SCIP store index byte identity differs")
    expected_status = (
        "OBSERVED_LOCAL_PRECISION_STORE_PARTIAL"
        if excluded_files
        else "OBSERVED_LOCAL_PRECISION_STORE"
    )
    if (
        catalog.get("status") != expected_status
        or pointer.get("status") != expected_status
    ):
        raise ScipMapError("SCIP store precision status is inconsistent")
    return ScipStoreRun(store, run_directory, catalog)


def _reuse_previous_python_index(
    inventory_store: Path,
    output_directory: Path,
    previous_manifest_path: Path,
    failure: ScipMapError,
) -> ScipIndexInput:
    """Carry forward only unchanged documents after a pinned backend failure."""

    inventory = current_navigation_run(inventory_store)
    try:
        previous_manifest = json.loads(previous_manifest_path.read_bytes())
        validate_self_hash(previous_manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ScipMapError("previous SCIP Python manifest is invalid") from exc
    if (
        previous_manifest.get("tool", {}).get("package") != SCIP_PYTHON_PACKAGE
        or previous_manifest.get("tool", {}).get("version") != SCIP_PYTHON_VERSION
        or previous_manifest.get("tool", {}).get("npm_integrity")
        != SCIP_PYTHON_NPM_INTEGRITY
    ):
        raise ScipMapError("previous SCIP Python tool identity is not reusable")
    _validate_python_patch_evidence(previous_manifest["tool"])
    previous_index_path = previous_manifest_path.parent / previous_manifest.get(
        "index", {}
    ).get("path", "")
    if previous_index_path.parent != previous_manifest_path.parent:
        raise ScipMapError("previous SCIP Python index path is unsafe")
    raw_index = previous_index_path.read_bytes()
    if sha256_bytes(raw_index) != previous_manifest["index"].get("sha256") or len(
        raw_index
    ) != previous_manifest["index"].get("bytes"):
        raise ScipMapError("previous SCIP Python index identity changed")
    parsed = parse_scip_index(raw_index)
    if parsed.tool_name != "scip-python" or parsed.tool_version != SCIP_PYTHON_VERSION:
        raise ScipMapError("previous SCIP Python index tool identity changed")
    previous_sources = previous_manifest.get("sources", {}).get("files")
    if not isinstance(previous_sources, list):
        raise ScipMapError("previous SCIP Python source evidence is invalid")
    current_sources = _eligible_python_sources(inventory)
    previous_by_path = {item.get("path"): item for item in previous_sources}
    retained_paths = {
        item["path"]
        for item in current_sources
        if previous_by_path.get(item["path"]) == item
    }
    excluded_files = [
        {
            **item,
            "reason": "CURRENT_SOURCE_CHANGED_INDEXER_REFRESH_FAILED",
            "tool_error_sha256": sha256_bytes(str(failure).encode("utf-8")),
        }
        for item in current_sources
        if item["path"] not in retained_paths
    ]
    if not excluded_files:
        raise ScipMapError(
            "SCIP Python failed without a changed source eligible for safe carry-forward"
        ) from failure
    retained_documents = tuple(
        item for item in parsed.documents if item.relative_path in retained_paths
    )
    if {item.relative_path for item in retained_documents} != retained_paths:
        raise ScipMapError("previous SCIP Python index lacks an unchanged source")
    filtered = replace(parsed, documents=retained_documents)
    occurrences = sum(len(item.occurrences) for item in retained_documents)
    definitions = sum(
        bool(item.roles & 1)
        for document in retained_documents
        for item in document.occurrences
    )
    relationships = sum(
        len(symbol.relationships)
        for symbol in (
            *filtered.external_symbols,
            *(symbol for document in retained_documents for symbol in document.symbols),
        )
    )
    output_directory.mkdir(mode=0o700)
    index_path = output_directory / "index.scip"
    index_path.write_bytes(raw_index)
    os.chmod(index_path, 0o600)
    source_closure = sha256_bytes(canonical_bytes(current_sources))
    manifest = seal_document(
        {
            "schema": SCIP_MANIFEST_SCHEMA,
            "status": "OBSERVED_LOCAL_PRECISION_INDEX_PARTIAL",
            "authority": "non-authoritative-optional-code-intelligence-evidence",
            "authority_granted": False,
            "generated_at": _utc_now(),
            "inventory": {
                "store": str(Path(inventory_store).resolve(strict=True)),
                "run_id": inventory.manifest["run_id"],
                "receipt_sha256": inventory.manifest["receipt_sha256"],
                "git": inventory.manifest["git"],
            },
            "sources": {
                "selection": "semantic_eligible=1 AND regular .py AND hash available",
                "closure_sha256": source_closure,
                "files": current_sources,
                "excluded_files": excluded_files,
                "source_text_embedded": False,
            },
            "reuse": {
                "strategy": "UNCHANGED_DOCUMENTS_FROM_PREVIOUS_VERIFIED_INDEX",
                "previous_manifest_receipt_sha256": previous_manifest["receipt_sha256"],
                "previous_index_sha256": previous_manifest["index"]["sha256"],
                "retained_documents": len(retained_documents),
                "excluded_current_files": len(excluded_files),
                "backend_failure_sha256": sha256_bytes(str(failure).encode("utf-8")),
            },
            "tool": previous_manifest["tool"],
            "index": {
                "path": "index.scip",
                "sha256": sha256_bytes(raw_index),
                "bytes": len(raw_index),
            },
            "counts": {
                "documents": len(retained_documents),
                "occurrences": occurrences,
                "definitions": definitions,
                "references": occurrences - definitions,
                "symbols": sum(len(item.symbols) for item in retained_documents),
                "external_symbols": len(filtered.external_symbols),
                "relationships": relationships,
            },
            "limitations": {
                "dynamic_runtime_resolution": "UNSUPPORTED",
                "facts_are_authority": False,
                "stdlib_snapshot": "INDEXER_BUNDLED_NOT_HOST_RUNTIME",
                "tool_derived": True,
                "changed_sources_have_scip_precision": False,
            },
        }
    )
    manifest_path = output_directory / "manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest))
    os.chmod(manifest_path, 0o600)
    return load_scip_index(manifest_path, inventory)


def refresh_scip_store(
    inventory_store: Path,
    store: Path,
    *,
    node: Path,
    python_indexer_entrypoint: Path,
    python_package_json: Path,
    typescript_indexer_entrypoint: Path,
    typescript_package_json: Path,
    timeout_seconds: int = 180,
) -> ScipStoreRun:
    """Atomically rebuild all supported discovered SCIP project closures."""

    store = store.absolute()
    if store.is_symlink():
        raise ScipMapError("SCIP store must not be a symlink")
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(store, 0o700)
    runs = store / "runs"
    runs.mkdir(mode=0o700, exist_ok=True)
    lock_path = store / "refresh.lock"
    lock_handle = lock_path.open("a+b")
    os.chmod(lock_path, 0o600)
    staging: Path | None = None
    locked = False
    try:
        lock_file(lock_handle)
        locked = True
        previous = None
        if (store / "CURRENT.json").is_file():
            previous = current_scip_store(store)
        discovery = discover_scip_projects(inventory_store)
        if (
            previous is not None
            and previous.catalog.get("discovery", {}).get("projects")
            == discovery["projects"]
        ):
            inventory = current_navigation_run(inventory_store)
            try:
                previous_inputs = tuple(
                    load_scip_index(path, inventory) for path in previous.manifest_paths
                )
            except ScipMapError:
                previous_inputs = ()
            if previous_inputs and len(previous_inputs) == len(previous.manifest_paths):
                statuses = {item.inventory_binding_status for item in previous_inputs}
                binding_status = (
                    "EXACT_INVENTORY_RECEIPT"
                    if statuses == {"EXACT_INVENTORY_RECEIPT"}
                    else "CURRENT_SOURCE_CLOSURE_REUSED_AFTER_INVENTORY_ADVANCE"
                )
                return ScipStoreRun(
                    previous.store,
                    previous.run_directory,
                    previous.catalog,
                    binding_status,
                )
        run_id = (
            _utc_now().replace(":", "").replace("-", "")
            + "-"
            + discovery["receipt_sha256"][:12]
        )
        staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=runs))
        os.chmod(staging, 0o700)
        projects_directory = staging / "projects"
        projects_directory.mkdir(mode=0o700)
        indexes: list[dict[str, Any]] = []
        for project in discovery["projects"]:
            if not project["eligible_for_federation"]:
                continue
            project_key = sha256_bytes(project["project_id"].encode())[:24]
            output = projects_directory / project_key
            if project["language"] == "python":
                try:
                    compiled = build_scip_index(
                        inventory_store,
                        output,
                        node=node,
                        indexer_entrypoint=python_indexer_entrypoint,
                        package_json=python_package_json,
                        timeout_seconds=timeout_seconds,
                    )
                except ScipMapError as exc:
                    if previous is None or not str(exc).startswith(
                        "SCIP Python compilation failed:"
                    ):
                        raise
                    candidates = [
                        path
                        for path in previous.manifest_paths
                        if json.loads(path.read_bytes()).get("tool", {}).get("package")
                        == SCIP_PYTHON_PACKAGE
                    ]
                    if len(candidates) != 1:
                        raise ScipMapError(
                            "previous SCIP store has no unique Python index"
                        ) from exc
                    compiled = _reuse_previous_python_index(
                        inventory_store, output, candidates[0], exc
                    )
            else:
                compiled = build_typescript_scip_index(
                    inventory_store,
                    output,
                    node=node,
                    indexer_entrypoint=typescript_indexer_entrypoint,
                    package_json=typescript_package_json,
                    project_root=project["project_root"],
                    timeout_seconds=timeout_seconds,
                )
            raw_manifest = compiled.manifest_path.read_bytes()
            indexes.append(
                {
                    "project_id": project["project_id"],
                    "language": project["language"],
                    "project_root": project["project_root"],
                    "source_closure_sha256": project["source_closure_sha256"],
                    "manifest_path": (
                        compiled.manifest_path.relative_to(staging).as_posix()
                    ),
                    "manifest_file_sha256": sha256_bytes(raw_manifest),
                    "manifest_receipt_sha256": compiled.manifest["receipt_sha256"],
                    "index_sha256": compiled.manifest["index"]["sha256"],
                    "index_bytes": compiled.manifest["index"]["bytes"],
                    "documents": compiled.manifest["counts"]["documents"],
                    "occurrences": compiled.manifest["counts"]["occurrences"],
                    "excluded_files": len(
                        compiled.manifest.get("sources", {}).get("excluded_files", [])
                    ),
                }
            )
        indexes.sort(key=lambda item: item["project_id"])
        excluded_files = sum(item["excluded_files"] for item in indexes)
        catalog = seal_document(
            {
                "schema": SCIP_STORE_CATALOG_SCHEMA,
                "status": (
                    "OBSERVED_LOCAL_PRECISION_STORE_PARTIAL"
                    if excluded_files
                    else "OBSERVED_LOCAL_PRECISION_STORE"
                ),
                "authority": "non-authoritative-atomic-code-intelligence-evidence",
                "authority_granted": False,
                "run_id": run_id,
                "generated_at": _utc_now(),
                "inventory": discovery["inventory"],
                "discovery": {
                    "receipt_sha256": discovery["receipt_sha256"],
                    "projects": discovery["projects"],
                    "counts": discovery["counts"],
                },
                "indexes": indexes,
                "counts": {
                    "indexes": len(indexes),
                    "documents": sum(item["documents"] for item in indexes),
                    "occurrences": sum(item["occurrences"] for item in indexes),
                    "bytes": sum(item["index_bytes"] for item in indexes),
                },
                "publication": {
                    "atomic": True,
                    "previous_generation_preserved_on_failure": True,
                    "source_text_embedded": False,
                },
            }
        )
        catalog_path = staging / "catalog.json"
        catalog_path.write_bytes(canonical_bytes(catalog))
        os.chmod(catalog_path, 0o600)
        final_directory = runs / run_id
        os.rename(staging, final_directory)
        staging = None
        raw_catalog = (final_directory / "catalog.json").read_bytes()
        pointer = seal_document(
            {
                "schema": SCIP_STORE_CURRENT_SCHEMA,
                "status": catalog["status"],
                "run_id": run_id,
                "catalog_file_sha256": sha256_bytes(raw_catalog),
                "catalog_receipt_sha256": catalog["receipt_sha256"],
                "updated_at": _utc_now(),
            }
        )
        _write_atomic_document(store / "CURRENT.json", pointer)
        return current_scip_store(store)
    except BaseException:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
        raise
    finally:
        if locked:
            unlock_file(lock_handle)
        lock_handle.close()


def _prefix_index_documents(index: ScipIndex, project_root: str) -> ScipIndex:
    project_root = _canonical_project_root(project_root)
    if project_root == ".":
        return index
    documents = tuple(
        replace(document, relative_path=f"{project_root}/{document.relative_path}")
        for document in index.documents
    )
    return replace(index, documents=documents)


def _tree_digest(root: Path) -> tuple[str, int, int]:
    entries = []
    total = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            continue
        digest, size = _file_sha256(path)
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": digest,
                "bytes": size,
            }
        )
        total += size
    return sha256_bytes(canonical_bytes(entries)), len(entries), total


def _patch_scip_python_entrypoint(payload: bytes) -> bytes:
    """Apply the one admitted upstream stdlib-package fallback repair."""

    if sha256_bytes(payload) != SCIP_PYTHON_ENTRYPOINT_SHA256:
        raise ScipMapError("SCIP Python entrypoint identity is not admitted")
    if payload.count(_SCIP_PYTHON_BROKEN_FRAGMENT) != 1:
        raise ScipMapError("SCIP Python repair target is not unique")
    repaired = payload.replace(
        _SCIP_PYTHON_BROKEN_FRAGMENT,
        _SCIP_PYTHON_REPAIRED_FRAGMENT,
        1,
    )
    if sha256_bytes(repaired) != SCIP_PYTHON_PATCHED_ENTRYPOINT_SHA256:
        raise ScipMapError("SCIP Python repaired entrypoint identity differs")
    return repaired


def _copy_private_regular_tree(source: Path, destination: Path) -> None:
    """Copy a package subtree without admitting links or special files."""

    source_metadata = source.lstat()
    if source.is_symlink() or not stat.S_ISDIR(source_metadata.st_mode):
        raise ScipMapError("SCIP Python runtime subtree is unsafe")
    destination.mkdir(mode=0o700)
    for item in sorted(source.rglob("*"), key=lambda path: path.as_posix()):
        metadata = item.lstat()
        if item.is_symlink():
            raise ScipMapError("SCIP Python runtime subtree contains a link")
        target = destination / item.relative_to(source)
        if stat.S_ISDIR(metadata.st_mode):
            target.mkdir(mode=0o700)
        elif stat.S_ISREG(metadata.st_mode):
            target.write_bytes(item.read_bytes())
            os.chmod(target, 0o600)
        else:
            raise ScipMapError("SCIP Python runtime subtree contains a special file")


def _prepare_patched_python_runtime(
    package_root: Path,
    indexer_entrypoint: Path,
    staging: Path,
    package_digest: str,
) -> Path:
    """Build an exact private runtime for the pinned upstream repair."""

    expected_entrypoint = package_root / "dist" / "scip-python.js"
    if indexer_entrypoint != expected_entrypoint:
        raise ScipMapError("SCIP Python entrypoint path is not canonical")
    if package_digest != SCIP_PYTHON_PACKAGE_TREE_SHA256:
        raise ScipMapError("SCIP Python package tree identity is not admitted")
    entrypoint_payload = indexer_entrypoint.read_bytes()
    repaired_payload = _patch_scip_python_entrypoint(entrypoint_payload)
    dist = package_root / "dist"
    admitted_siblings = {
        "vendor.js": SCIP_PYTHON_VENDOR_SHA256,
        "pyright-internal.js": SCIP_PYTHON_PYRIGHT_SHA256,
    }
    for name, expected_sha256 in admitted_siblings.items():
        path = dist / name
        metadata = path.lstat()
        if (
            path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or _file_sha256(path)[0] != expected_sha256
        ):
            raise ScipMapError("SCIP Python runtime dependency identity differs")
    runtime = staging / ".scip-python-runtime"
    runtime.mkdir(mode=0o700)
    repaired_entrypoint = runtime / "scip-python.js"
    repaired_entrypoint.write_bytes(repaired_payload)
    os.chmod(repaired_entrypoint, 0o600)
    for name in admitted_siblings:
        target = runtime / name
        target.write_bytes((dist / name).read_bytes())
        os.chmod(target, 0o600)
    _copy_private_regular_tree(
        dist / "typeshed-fallback", runtime / "typeshed-fallback"
    )
    return repaired_entrypoint


def _python_project_configuration(sources: Sequence[Mapping[str, Any]]) -> bytes:
    """Force Pyright to include the exact admitted non-dot source closure."""

    paths = [source.get("path") for source in sources]
    if (
        not paths
        or any(not isinstance(path, str) or not path for path in paths)
        or paths != sorted(paths)
        or len(paths) != len(set(paths))
    ):
        raise ScipMapError("SCIP Python source paths are not a stable closure")
    include = ",\n".join(f"  {json.dumps(path, ensure_ascii=True)}" for path in paths)
    return (
        '[project]\nname = "giga-user"\nversion = "0"\n'
        "[tool.pyright]\ninclude = [\n"
        + include
        + '\n]\nexclude = []\npythonVersion = "3.11"\n'
    ).encode("utf-8")


def _snapshot_python_sources(
    root: Path, shadow: Path, sources: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Copy only inventory-exact bytes and preserve truthful drift evidence."""

    indexed: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for supplied in sources:
        source = dict(supplied)
        if any(part.startswith(".") for part in PurePosixPath(source["path"]).parts):
            excluded.append(
                {
                    **source,
                    "reason": "SCIP_PYTHON_DOT_PATH_UNSUPPORTED",
                    "tool_error_sha256": sha256_bytes(
                        canonical_bytes(
                            {
                                "path": source["path"],
                                "tool": f"{SCIP_PYTHON_PACKAGE}@{SCIP_PYTHON_VERSION}",
                                "observation": (
                                    "dot-prefixed paths omitted despite exact include"
                                ),
                            }
                        )
                    ),
                }
            )
            continue
        source_path = root / source["path"]
        try:
            payload = source_path.read_bytes()
            actual_sha256 = sha256_bytes(payload)
            diagnostic = {
                "path": source["path"],
                "expected_sha256": source["content_sha256"],
                "expected_bytes": source["size_bytes"],
                "actual_sha256": actual_sha256,
                "actual_bytes": len(payload),
            }
        except OSError as exc:
            payload = b""
            diagnostic = {
                "path": source["path"],
                "expected_sha256": source["content_sha256"],
                "expected_bytes": source["size_bytes"],
                "read_error": type(exc).__name__,
            }
        if (
            len(payload) != source["size_bytes"]
            or diagnostic.get("actual_sha256") != source["content_sha256"]
        ):
            excluded.append(
                {
                    **source,
                    "reason": "CURRENT_SOURCE_DRIFTED_BEFORE_INDEXING",
                    "tool_error_sha256": sha256_bytes(canonical_bytes(diagnostic)),
                }
            )
            continue
        destination = shadow / source["path"]
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination.write_bytes(payload)
        os.chmod(destination, 0o600)
        indexed.append(source)
    return indexed, excluded


def _validate_python_patch_evidence(tool: Mapping[str, Any]) -> None:
    patch = tool.get("patch")
    if patch is None:
        return
    if (
        patch
        != {
            "id": SCIP_PYTHON_PATCH_ID,
            "upstream_entrypoint_sha256": SCIP_PYTHON_ENTRYPOINT_SHA256,
            "patched_entrypoint_sha256": SCIP_PYTHON_PATCHED_ENTRYPOINT_SHA256,
            "installed_package_unchanged": True,
        }
        or tool.get("package_tree_sha256") != SCIP_PYTHON_PACKAGE_TREE_SHA256
    ):
        raise ScipMapError("SCIP Python repair evidence is invalid")


def build_scip_index(
    inventory_store: Path,
    output_directory: Path,
    *,
    node: Path,
    indexer_entrypoint: Path,
    package_json: Path,
    timeout_seconds: int = 180,
) -> ScipIndexInput:
    """Compile exact eligible Python bytes in a private shadow tree."""

    inventory = current_navigation_run(inventory_store)
    root = Path(inventory.manifest["root"]["path"]).resolve(strict=True)
    if output_directory.exists() or output_directory.is_symlink():
        raise ScipMapError("SCIP output directory already exists")
    node = node.resolve(strict=True)
    indexer_entrypoint = indexer_entrypoint.resolve(strict=True)
    package_json = package_json.resolve(strict=True)
    if not os.access(node, os.X_OK):
        raise ScipMapError("SCIP Node executable is not executable")
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ScipMapError("SCIP package metadata is unreadable") from exc
    if (
        set(package) < {"name", "version"}
        or package.get("name") != SCIP_PYTHON_PACKAGE
        or package.get("version") != SCIP_PYTHON_VERSION
    ):
        raise ScipMapError("SCIP Python package identity is not admitted")
    package_root = package_json.parent
    try:
        indexer_entrypoint.relative_to(package_root)
    except ValueError as exc:
        raise ScipMapError("SCIP entrypoint is outside its package") from exc
    sources = _eligible_python_sources(inventory)
    source_closure = sha256_bytes(canonical_bytes(sources))
    package_digest, package_files, package_bytes = _tree_digest(package_root)
    node_digest, node_bytes = _file_sha256(node)
    parent = output_directory.absolute().parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=parent))
    os.chmod(staging, 0o700)
    started_at = _utc_now()
    shadow = Path("/private/tmp") / f"giga-scip-python-{source_closure[:32]}"
    shadow_owned = False
    try:
        repaired_entrypoint = _prepare_patched_python_runtime(
            package_root,
            indexer_entrypoint,
            staging,
            package_digest,
        )
        try:
            shadow.mkdir(mode=0o700)
            shadow_owned = True
        except FileExistsError as exc:
            raise ScipMapError(
                "deterministic SCIP Python shadow already exists"
            ) from exc
        try:
            indexed_sources, excluded_files = _snapshot_python_sources(
                root, shadow, sources
            )
            if not indexed_sources:
                raise ScipMapError(
                    "every eligible Python source drifted from inventory"
                )
            environment_path = shadow / "environment.json"
            environment_path.write_bytes(b"[]\n")
            os.chmod(environment_path, 0o600)
            project_configuration = _python_project_configuration(indexed_sources)
            project_path = shadow / "pyproject.toml"
            project_path.write_bytes(project_configuration)
            os.chmod(project_path, 0o600)
            git_environment = {
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "HOME": str(shadow),
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin",
                "TZ": "UTC",
            }
            for git_argv in (
                ["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "init", "-q"],
                [
                    "/usr/bin/git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "add",
                    "--all",
                    "--",
                ],
            ):
                git_result = subprocess.run(
                    git_argv,
                    cwd=shadow,
                    env=git_environment,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if git_result.returncode != 0:
                    raise ScipMapError("private SCIP shadow Git setup failed")
            shadow_index_path = shadow / "index.scip"
            argv = [
                str(node),
                str(repaired_entrypoint),
                "index",
                "--cwd",
                str(shadow),
                "--project-name",
                "giga-user",
                "--project-version",
                source_closure,
                "--environment",
                str(environment_path),
                "--output",
                str(shadow_index_path),
            ]
            result = subprocess.run(
                argv,
                cwd=shadow,
                env={
                    "HOME": str(shadow),
                    "LC_ALL": "C",
                    "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
                    "TMPDIR": str(shadow),
                    "TZ": "UTC",
                },
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
            if result.returncode != 0:
                raise ScipMapError(
                    "SCIP Python compilation failed: "
                    + result.stderr[-2000:].decode("utf-8", errors="replace")
                )
            raw_index = shadow_index_path.read_bytes()
        finally:
            if shadow_owned:
                shutil.rmtree(shadow)
                shadow_owned = False
        shutil.rmtree(repaired_entrypoint.parent)
        index_path = staging / "index.scip"
        index_path.write_bytes(raw_index)
        os.chmod(index_path, 0o600)
        parsed = parse_scip_index(raw_index)
        expected_paths = [source["path"] for source in indexed_sources]
        actual_paths = [document.relative_path for document in parsed.documents]
        if actual_paths != expected_paths:
            raise ScipMapError(
                "SCIP document closure differs from eligible inventory: "
                f"expected={len(expected_paths)} actual={len(actual_paths)} "
                f"missing={sorted(set(expected_paths) - set(actual_paths))[:20]!r} "
                f"extra={sorted(set(actual_paths) - set(expected_paths))[:20]!r} "
                f"actual_sample={actual_paths[:20]!r} "
                f"stdout={result.stdout[-1000:].decode('utf-8', errors='replace')!r} "
                f"stderr={result.stderr[-1000:].decode('utf-8', errors='replace')!r}"
            )
        if (
            parsed.tool_name != "scip-python"
            or parsed.tool_version != SCIP_PYTHON_VERSION
        ):
            raise ScipMapError("SCIP index reports an unexpected tool identity")
        occurrences = sum(len(document.occurrences) for document in parsed.documents)
        definitions = sum(
            bool(occurrence.roles & 1)
            for document in parsed.documents
            for occurrence in document.occurrences
        )
        relationships = sum(
            len(symbol.relationships)
            for symbol in (
                *parsed.external_symbols,
                *(
                    symbol
                    for document in parsed.documents
                    for symbol in document.symbols
                ),
            )
        )
        index_sha256, index_bytes = _file_sha256(index_path)
        manifest = seal_document(
            {
                "schema": SCIP_MANIFEST_SCHEMA,
                "status": (
                    "OBSERVED_LOCAL_PRECISION_INDEX_PARTIAL"
                    if excluded_files
                    else "OBSERVED_LOCAL_PRECISION_INDEX"
                ),
                "authority": "non-authoritative-optional-code-intelligence-evidence",
                "authority_granted": False,
                "generated_at": started_at,
                "inventory": {
                    "store": str(Path(inventory_store).resolve(strict=True)),
                    "run_id": inventory.manifest["run_id"],
                    "receipt_sha256": inventory.manifest["receipt_sha256"],
                    "git": inventory.manifest["git"],
                },
                "sources": {
                    "selection": "semantic_eligible=1 AND regular .py AND hash available",
                    "closure_sha256": source_closure,
                    "files": sources,
                    "excluded_files": excluded_files,
                    "source_text_embedded": False,
                },
                "tool": {
                    "package": SCIP_PYTHON_PACKAGE,
                    "version": SCIP_PYTHON_VERSION,
                    "npm_integrity": SCIP_PYTHON_NPM_INTEGRITY,
                    "package_tree_sha256": package_digest,
                    "package_files": package_files,
                    "package_bytes": package_bytes,
                    "patch": {
                        "id": SCIP_PYTHON_PATCH_ID,
                        "upstream_entrypoint_sha256": SCIP_PYTHON_ENTRYPOINT_SHA256,
                        "patched_entrypoint_sha256": (
                            SCIP_PYTHON_PATCHED_ENTRYPOINT_SHA256
                        ),
                        "installed_package_unchanged": True,
                    },
                    "node_sha256": node_digest,
                    "node_bytes": node_bytes,
                    "project_configuration_sha256": sha256_bytes(project_configuration),
                    "project_configuration_strategy": (
                        "EXACT_INVENTORY_SOURCE_PATH_INCLUDE"
                    ),
                    "protocol_version": parsed.protocol_version,
                    "reported_arguments": list(parsed.tool_arguments),
                    "project_root": parsed.project_root,
                    "text_encoding": parsed.text_encoding,
                },
                "index": {
                    "path": "index.scip",
                    "sha256": index_sha256,
                    "bytes": index_bytes,
                },
                "counts": {
                    "documents": len(parsed.documents),
                    "occurrences": occurrences,
                    "definitions": definitions,
                    "references": occurrences - definitions,
                    "symbols": sum(
                        len(document.symbols) for document in parsed.documents
                    ),
                    "external_symbols": len(parsed.external_symbols),
                    "relationships": relationships,
                },
                "limitations": {
                    "dynamic_runtime_resolution": "UNSUPPORTED",
                    "facts_are_authority": False,
                    "stdlib_snapshot": "INDEXER_BUNDLED_NOT_HOST_RUNTIME",
                    "tool_derived": True,
                },
            }
        )
        manifest_path = staging / "manifest.json"
        manifest_path.write_bytes(canonical_bytes(manifest))
        os.chmod(manifest_path, 0o600)
        os.rename(staging, output_directory)
        return load_scip_index(output_directory / "manifest.json", inventory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def build_typescript_scip_index(
    inventory_store: Path,
    output_directory: Path,
    *,
    node: Path,
    indexer_entrypoint: Path,
    package_json: Path,
    project_root: str,
    timeout_seconds: int = 180,
) -> ScipIndexInput:
    """Compile one exact TypeScript/JavaScript project in a private shadow tree."""

    inventory = current_navigation_run(inventory_store)
    root = Path(inventory.manifest["root"]["path"]).resolve(strict=True)
    project_root = _canonical_project_root(project_root)
    if output_directory.exists() or output_directory.is_symlink():
        raise ScipMapError("SCIP output directory already exists")
    node = node.resolve(strict=True)
    indexer_entrypoint = indexer_entrypoint.resolve(strict=True)
    package_json = package_json.resolve(strict=True)
    if not os.access(node, os.X_OK):
        raise ScipMapError("SCIP Node executable is not executable")
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ScipMapError("SCIP package metadata is unreadable") from exc
    if (
        set(package) < {"name", "version"}
        or package.get("name") != SCIP_TYPESCRIPT_PACKAGE
        or package.get("version") != SCIP_TYPESCRIPT_VERSION
    ):
        raise ScipMapError("SCIP TypeScript package identity is not admitted")
    package_root = package_json.parent
    try:
        indexer_entrypoint.relative_to(package_root)
    except ValueError as exc:
        raise ScipMapError("SCIP entrypoint is outside its package") from exc
    dependency_root = package_root.parent.parent
    if dependency_root.name != "node_modules":
        raise ScipMapError("SCIP TypeScript package is outside a node_modules closure")

    sources = _eligible_typescript_sources(inventory, project_root)
    configs = _typescript_configs(inventory, project_root)
    closure = {"sources": sources, "configs": configs}
    source_closure = sha256_bytes(canonical_bytes(closure))
    package_digest, package_files, package_bytes = _tree_digest(package_root)
    dependency_digest, dependency_files, dependency_bytes = _tree_digest(
        dependency_root
    )
    node_digest, node_bytes = _file_sha256(node)
    parent = output_directory.absolute().parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=parent))
    os.chmod(staging, 0o700)
    started_at = _utc_now()
    shadow = Path("/private/tmp") / f"giga-scip-typescript-{source_closure[:32]}"
    shadow_owned = False
    try:
        try:
            shadow.mkdir(mode=0o700)
            shadow_owned = True
        except FileExistsError as exc:
            raise ScipMapError(
                "deterministic SCIP TypeScript shadow already exists"
            ) from exc
        try:
            for source in (*configs, *sources):
                source_path = root / source["path"]
                destination = shadow / source["path"]
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                payload = source_path.read_bytes()
                if (
                    len(payload) != source["size_bytes"]
                    or sha256_bytes(payload) != source["content_sha256"]
                ):
                    raise ScipMapError(
                        "TypeScript project input drifted from inventory"
                    )
                destination.write_bytes(payload)
                os.chmod(destination, 0o600)
            project_directory = shadow if project_root == "." else shadow / project_root
            shadow_index_path = shadow / "index.scip"
            argv = [
                str(node),
                str(indexer_entrypoint),
                "index",
                "--cwd",
                str(project_directory),
                "--output",
                str(shadow_index_path),
                "--no-progress-bar",
                "--no-global-caches",
            ]
            result = subprocess.run(
                argv,
                cwd=project_directory,
                env={
                    "HOME": str(shadow),
                    "LC_ALL": "C",
                    "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
                    "TMPDIR": str(shadow),
                    "TZ": "UTC",
                },
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
            if result.returncode != 0:
                raise ScipMapError(
                    "SCIP TypeScript compilation failed: "
                    + result.stderr[-2000:].decode("utf-8", errors="replace")
                )
            raw_index = shadow_index_path.read_bytes()
        finally:
            if shadow_owned:
                shutil.rmtree(shadow)
                shadow_owned = False
        index_path = staging / "index.scip"
        index_path.write_bytes(raw_index)
        os.chmod(index_path, 0o600)
        parsed = parse_scip_index(index_path.read_bytes())
        actual_project_paths = [item.relative_path for item in parsed.documents]
        prefix = "" if project_root == "." else f"{project_root}/"
        expected_project_paths = [
            source["path"].removeprefix(prefix) for source in sources
        ]
        if actual_project_paths != expected_project_paths:
            raise ScipMapError(
                "SCIP TypeScript document closure differs from inventory: "
                f"expected={expected_project_paths!r} actual={actual_project_paths!r}"
            )
        if (
            parsed.tool_name != "scip-typescript"
            or parsed.tool_version != SCIP_TYPESCRIPT_VERSION
        ):
            raise ScipMapError("SCIP index reports an unexpected tool identity")
        parsed = _prefix_index_documents(parsed, project_root)
        occurrences = sum(len(document.occurrences) for document in parsed.documents)
        definitions = sum(
            bool(occurrence.roles & 1)
            for document in parsed.documents
            for occurrence in document.occurrences
        )
        relationships = sum(
            len(symbol.relationships)
            for symbol in (
                *parsed.external_symbols,
                *(
                    symbol
                    for document in parsed.documents
                    for symbol in document.symbols
                ),
            )
        )
        index_sha256, index_bytes = _file_sha256(index_path)
        manifest = seal_document(
            {
                "schema": SCIP_MANIFEST_SCHEMA,
                "status": "OBSERVED_LOCAL_PRECISION_INDEX",
                "authority": "non-authoritative-optional-code-intelligence-evidence",
                "authority_granted": False,
                "generated_at": started_at,
                "inventory": {
                    "store": str(Path(inventory_store).resolve(strict=True)),
                    "run_id": inventory.manifest["run_id"],
                    "receipt_sha256": inventory.manifest["receipt_sha256"],
                    "git": inventory.manifest["git"],
                },
                "sources": {
                    "selection": (
                        "semantic_eligible=1 AND regular TypeScript/JavaScript "
                        f"under {project_root} AND exact project configs"
                    ),
                    "language": "typescript-javascript",
                    "project_root": project_root,
                    "closure_sha256": source_closure,
                    "files": sources,
                    "configs": configs,
                    "source_text_embedded": False,
                },
                "tool": {
                    "package": SCIP_TYPESCRIPT_PACKAGE,
                    "version": SCIP_TYPESCRIPT_VERSION,
                    "npm_integrity": SCIP_TYPESCRIPT_NPM_INTEGRITY,
                    "package_tree_sha256": package_digest,
                    "package_files": package_files,
                    "package_bytes": package_bytes,
                    "dependency_tree_sha256": dependency_digest,
                    "dependency_files": dependency_files,
                    "dependency_bytes": dependency_bytes,
                    "node_sha256": node_digest,
                    "node_bytes": node_bytes,
                    "protocol_version": parsed.protocol_version,
                    "reported_arguments": list(parsed.tool_arguments),
                    "project_root": parsed.project_root,
                    "text_encoding": parsed.text_encoding,
                },
                "index": {
                    "path": "index.scip",
                    "sha256": index_sha256,
                    "bytes": index_bytes,
                },
                "counts": {
                    "documents": len(parsed.documents),
                    "occurrences": occurrences,
                    "definitions": definitions,
                    "references": occurrences - definitions,
                    "symbols": sum(
                        len(document.symbols) for document in parsed.documents
                    ),
                    "external_symbols": len(parsed.external_symbols),
                    "relationships": relationships,
                },
                "limitations": {
                    "dynamic_runtime_resolution": "UNSUPPORTED",
                    "facts_are_authority": False,
                    "external_dependencies": "NOT_COPIED_INTO_PROJECT_SHADOW",
                    "tool_derived": True,
                },
            }
        )
        manifest_path = staging / "manifest.json"
        manifest_path.write_bytes(canonical_bytes(manifest))
        os.chmod(manifest_path, 0o600)
        os.rename(staging, output_directory)
        return load_scip_index(output_directory / "manifest.json", inventory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def load_scip_index(manifest_path: Path, inventory: NavigationRun) -> ScipIndexInput:
    manifest_path = manifest_path.resolve(strict=True)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate_self_hash(manifest)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ScipMapError("SCIP manifest is invalid") from exc
    if (
        manifest.get("schema") != SCIP_MANIFEST_SCHEMA
        or manifest.get("authority_granted") is not False
    ):
        raise ScipMapError("SCIP manifest authority is invalid")
    tool = manifest.get("tool", {})
    tool_identity = (
        tool.get("package"),
        tool.get("version"),
        tool.get("npm_integrity"),
    )
    admitted_tools = {
        (
            SCIP_PYTHON_PACKAGE,
            SCIP_PYTHON_VERSION,
            SCIP_PYTHON_NPM_INTEGRITY,
        ),
        (
            SCIP_TYPESCRIPT_PACKAGE,
            SCIP_TYPESCRIPT_VERSION,
            SCIP_TYPESCRIPT_NPM_INTEGRITY,
        ),
    }
    if tool_identity not in admitted_tools:
        raise ScipMapError("SCIP manifest tool identity is not admitted")
    source_manifest = manifest.get("sources", {})
    if tool.get("package") == SCIP_PYTHON_PACKAGE:
        _validate_python_patch_evidence(tool)
        expected_sources = _eligible_python_sources(inventory)
        expected_configs: list[dict[str, Any]] | None = None
        expected_closure: Any = expected_sources
        project_root = "."
        expected_tool_name = "scip-python"
    else:
        project_root = _canonical_project_root(source_manifest.get("project_root", ""))
        expected_sources = _eligible_typescript_sources(inventory, project_root)
        expected_configs = _typescript_configs(inventory, project_root)
        expected_closure = {
            "sources": expected_sources,
            "configs": expected_configs,
        }
        expected_tool_name = "scip-typescript"
    exclusions = source_manifest.get("excluded_files", [])
    if not isinstance(exclusions, list) or (
        expected_tool_name != "scip-python" and exclusions
    ):
        raise ScipMapError("SCIP excluded source evidence is invalid")
    expected_by_path = {item["path"]: item for item in expected_sources}
    excluded_paths: set[str] = set()
    for exclusion in exclusions:
        if not isinstance(exclusion, dict) or set(exclusion) != {
            "path",
            "content_sha256",
            "size_bytes",
            "reason",
            "tool_error_sha256",
        }:
            raise ScipMapError("SCIP excluded source evidence is invalid")
        path = exclusion["path"]
        expected = expected_by_path.get(path)
        if (
            expected is None
            or path in excluded_paths
            or exclusion["content_sha256"] != expected["content_sha256"]
            or exclusion["size_bytes"] != expected["size_bytes"]
            or exclusion["reason"]
            not in {
                "CURRENT_SOURCE_CHANGED_INDEXER_REFRESH_FAILED",
                "CURRENT_SOURCE_DRIFTED_BEFORE_INDEXING",
                "SCIP_PYTHON_DOT_PATH_UNSUPPORTED",
            }
            or not isinstance(exclusion["tool_error_sha256"], str)
            or len(exclusion["tool_error_sha256"]) != 64
        ):
            raise ScipMapError("SCIP excluded source evidence is invalid")
        excluded_paths.add(path)
    expected_status = (
        "OBSERVED_LOCAL_PRECISION_INDEX_PARTIAL"
        if exclusions
        else "OBSERVED_LOCAL_PRECISION_INDEX"
    )
    if manifest.get("status") != expected_status:
        raise ScipMapError("SCIP precision status does not match exclusions")
    if (
        source_manifest.get("files") != expected_sources
        or source_manifest.get("closure_sha256")
        != sha256_bytes(canonical_bytes(expected_closure))
        or source_manifest.get("source_text_embedded") is not False
        or (
            expected_configs is not None
            and source_manifest.get("configs") != expected_configs
        )
    ):
        raise ScipMapError("SCIP source closure mismatch")
    index_path = manifest_path.parent / manifest.get("index", {}).get("path", "")
    if (
        index_path.parent != manifest_path.parent
        or not index_path.is_file()
        or index_path.is_symlink()
    ):
        raise ScipMapError("SCIP index path is unsafe")
    index_sha256, index_bytes = _file_sha256(index_path)
    if index_sha256 != manifest["index"].get("sha256") or index_bytes != manifest[
        "index"
    ].get("bytes"):
        raise ScipMapError("SCIP index byte identity mismatch")
    index = parse_scip_index(index_path.read_bytes())
    if index.tool_name != expected_tool_name or index.tool_version != tool.get(
        "version"
    ):
        raise ScipMapError("SCIP index tool identity mismatch")
    if expected_tool_name == "scip-typescript":
        index = _prefix_index_documents(index, project_root)
    allowed_paths = {
        item["path"] for item in expected_sources if item["path"] not in excluded_paths
    }
    if exclusions:
        index = replace(
            index,
            documents=tuple(
                item for item in index.documents if item.relative_path in allowed_paths
            ),
        )
    if [item.relative_path for item in index.documents] != [
        item["path"] for item in expected_sources if item["path"] not in excluded_paths
    ]:
        raise ScipMapError("SCIP parsed document closure mismatch")
    counts = manifest.get("counts", {})
    occurrences = sum(len(document.occurrences) for document in index.documents)
    definitions = sum(
        bool(item.roles & 1)
        for document in index.documents
        for item in document.occurrences
    )
    if (
        counts.get("documents") != len(index.documents)
        or counts.get("occurrences") != occurrences
        or counts.get("definitions") != definitions
        or counts.get("references") != occurrences - definitions
    ):
        raise ScipMapError("SCIP manifest counts mismatch")
    source_inventory_receipt = manifest.get("inventory", {}).get("receipt_sha256")
    current_inventory_receipt = inventory.manifest["receipt_sha256"]
    binding_status = (
        "EXACT_INVENTORY_RECEIPT"
        if source_inventory_receipt == current_inventory_receipt
        else "CURRENT_SOURCE_CLOSURE_REUSED_AFTER_INVENTORY_ADVANCE"
    )
    return ScipIndexInput(
        manifest_path,
        index_path,
        manifest,
        index,
        current_inventory_receipt,
        binding_status,
    )


def scip_symbol_name(symbol: str, display_name: str = "") -> str:
    """Return a conservative query label while retaining the raw SCIP identity."""

    if display_name:
        return display_name
    if symbol.startswith("local "):
        return symbol.removeprefix("local ")
    value = symbol.rstrip(".#/")
    if value.endswith("()"):
        value = value[:-2]
    for separator in ("#", "/", ".", " "):
        if separator in value:
            value = value.rsplit(separator, 1)[-1]
    return value.strip("`") or symbol
