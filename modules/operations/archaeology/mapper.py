"""Authenticated shared fact store and M01 inventory/structure projections."""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import shutil
import sqlite3
import stat
import tempfile
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from .evidence import canonical_bytes, seal_document, sha256_bytes, validate_self_hash
from .cleanup_map import (
    CLEANUP_POLICY_SHA256,
    CLEANUP_POLICY_VERSION,
    PYTHON_STRUCTURE_POLICY_SHA256,
    PYTHON_STRUCTURE_POLICY_VERSION,
    safe_exact_duplicate_groups,
    safe_structural_duplicate_groups,
)
from .counterevidence import DYNAMIC_CALLS, build_counterevidence
from .flow_policy import (
    FLOW_POLICY_VERSION,
    POLICY_SHA256,
    classify_sink,
    classify_source,
)
from .history import HistoryError, collect_recent_lineage
from .governance_map import (
    GOVERNANCE_POLICY_SHA256,
    GOVERNANCE_POLICY_VERSION,
    GovernanceMapError,
    exact_hash_links,
    exact_json_path_references,
    explicit_markdown_declarations,
    explicit_markdown_path_references,
    governed_markdown_headings,
    governed_document_kind,
    self_hash_state,
    strict_json_object,
)
from .navigation_inventory import (
    EXPLICIT_FILE_SCOPE,
    NavigationRun,
    classify_navigation_role,
    current_navigation_run,
)
from .operational_map import (
    OPERATIONAL_POLICY_SHA256,
    OPERATIONAL_POLICY_VERSION,
    SQL_LITERAL_GRAMMAR,
    build_asset_role,
    parse_sql_literal,
    safe_build_declarations,
)
from .python_map import (
    PythonFragment,
    PythonMapError,
    extract_project_file_fragment,
    extract_python_file_fragment,
    extract_python_fragment,
    python_module_name,
    read_exact_artifact,
)
from .quality_map import (
    QUALITY_POLICY_SHA256,
    QUALITY_POLICY_VERSION,
    is_python_test_path,
    parse_coverage_json,
    parse_receipt_quality_claims,
    quality_asset_role,
)
from .runtime_map import (
    RUNTIME_POLICY_SHA256,
    RUNTIME_POLICY_VERSION,
    RuntimeMapError,
    RuntimeRegistryInput,
    load_runtime_registry,
)
from .javascript_map import (
    JAVASCRIPT_SUFFIXES,
    JavaScriptMapError,
    extract_javascript_file_fragment,
    javascript_backend_identity,
)
from .map_catalog import MAP_ENTITY_KINDS, build_map_catalog
from .semantic_graph import (
    SemanticGraphError,
    current_semantic_run,
    locate_semantic_graph,
)
from .shell_map import (
    ShellMapError,
    extract_shell_file_fragment,
    shell_backend_identity,
)
from .scip_map import (
    SCIP_PRODUCER_ID,
    SCIP_TYPESCRIPT_PRODUCER_ID,
    SCIP_TYPESCRIPT_PACKAGE,
    ScipIndexInput,
    ScipMapError,
    load_scip_index,
    scip_symbol_name,
)


MAPPER_SCHEMA = "giga.archaeologist.mapper-manifest.v2"
MAPPER_POINTER_SCHEMA = "giga.archaeologist.mapper-current-pointer.v1"
MAPPER_QUERY_SCHEMA = "giga.archaeologist.mapper-query-result.v1"
MAPPER_AUDIT_SCHEMA = "giga.archaeologist.mapper-audit.v1"
DATABASE_SCHEMA = 7
SUPPORTED_MAPS = (
    "inventory",
    "structure",
    "symbols",
    "dependencies",
    "types",
    "api_events",
    "calls",
    "control_flow",
    "data_flow_taint",
    "security_capabilities",
    "database_lineage",
    "build_deployment",
    "tests_coverage",
    "quality_findings",
    "duplicates_similarity",
    "reachability",
    "git_lineage",
    "ownership_canonicality",
    "requirements_decisions",
    "evidence_claims",
    "runtime_topology",
    "semantic_graphify",
)
MAP_OBSERVATION_PRIORITIES: Mapping[str, tuple[str, ...]] = {
    "reachability": ("STATIC_REACHABILITY", "DELETION_COUNTEREVIDENCE"),
}
PROJECT_MARKERS = {
    "Cargo.toml": "RUST_CRATE",
    "Gemfile": "RUBY_PROJECT",
    "Package.swift": "SWIFT_PACKAGE",
    "build.gradle": "GRADLE_PROJECT",
    "build.gradle.kts": "GRADLE_PROJECT",
    "composer.json": "PHP_PROJECT",
    "go.mod": "GO_MODULE",
    "package.json": "NODE_PROJECT",
    "pom.xml": "MAVEN_PROJECT",
    "pyproject.toml": "PYTHON_PROJECT",
    "setup.cfg": "PYTHON_PROJECT",
    "setup.py": "PYTHON_PROJECT",
}
TRUTH_CLASSES = (
    "PROVEN",
    "OBSERVED",
    "INFERRED",
    "CONFLICT",
    "UNKNOWN",
    "UNSUPPORTED",
)
INFERRED_CONFIDENCE_VALUES = (0.95, 0.85, 0.75, 0.65, 0.55)
DEFAULT_STATIC_INFERENCE_CONFIDENCE = 0.75
COVERAGE_STATES = (
    "COVERED",
    "PARTIAL",
    "FAILED",
    "SKIPPED_POLICY",
    "NOT_APPLICABLE",
    "UNSUPPORTED",
)
PYTHON_PRODUCER_IDS = (
    "producer:python-map-extractor:v1",
    "producer:operational-map-extractor:v1",
    "producer:quality-map-extractor:v1",
)
PYTHON_MAP_IDS = (
    "api_events",
    "build_deployment",
    "calls",
    "control_flow",
    "data_flow_taint",
    "database_lineage",
    "dependencies",
    "quality_findings",
    "security_capabilities",
    "symbols",
    "tests_coverage",
    "types",
)
PYTHON_COUNT_KEYS = (
    "python_files",
    "python_parse_failures",
    "python_source_snapshot_failures",
    "python_project_manifest_failures",
    "python_modules",
    "python_symbols",
    "python_references",
    "python_references_resolved",
    "python_imports",
    "python_imports_unresolved_or_external",
    "python_type_relations",
    "python_annotations",
    "python_entrypoints",
    "python_calls",
    "python_calls_resolved",
    "python_control_flows",
    "python_control_nodes",
    "python_control_edges",
    "python_data_sources",
    "python_security_effects",
    "python_static_flows",
    "python_possible_taint_paths",
    "python_declared_databases",
    "python_declared_data_objects",
    "python_literal_sql_operations",
    "build_assets",
    "safe_build_declarations",
    "python_test_candidates",
    "static_test_targets",
    "quality_assets",
    "coverage_files",
    "coverage_source_links",
    "python_sources",
)
SHELL_COUNT_KEYS = (
    "shell_files",
    "shell_parse_failures",
    "shell_scripts",
    "shell_symbols",
    "shell_functions",
    "shell_variables",
    "shell_references",
    "shell_references_resolved",
    "shell_commands",
    "shell_function_calls",
    "shell_dependencies",
    "shell_dependencies_resolved",
    "shell_entrypoints",
)
JAVASCRIPT_COUNT_KEYS = (
    "javascript_files",
    "javascript_parse_failures",
    "javascript_modules",
    "javascript_symbols",
    "javascript_references",
    "javascript_references_resolved",
    "javascript_imports",
    "javascript_imports_resolved",
    "javascript_calls",
    "javascript_calls_resolved",
    "javascript_cross_file_calls_resolved",
    "javascript_cross_file_references_resolved",
    "javascript_entrypoints",
    "javascript_exports",
    "javascript_exports_resolved",
    "javascript_import_bindings",
    "javascript_import_bindings_resolved",
    "javascript_commonjs_imports",
)
SCIP_COUNT_KEYS = (
    "scip_documents",
    "scip_symbols",
    "scip_external_symbols",
    "scip_occurrences",
    "scip_duplicate_occurrences_coalesced",
    "scip_definitions",
    "scip_references",
    "scip_relationships",
)


class MapperError(ValueError):
    """The mapper input, fact store, publication, or query is not trustworthy."""


@dataclass(frozen=True)
class MapperRun:
    run_directory: Path
    manifest: Mapping[str, Any]
    inventory_database: Path


@dataclass(frozen=True)
class PythonInputSet:
    """Exact inventory records that can affect the compound Python producer."""

    python_records: tuple[Mapping[str, Any], ...]
    project_records: tuple[Mapping[str, Any], ...]
    build_records: tuple[Mapping[str, Any], ...]
    quality_records: tuple[Mapping[str, Any], ...]
    records_by_path: Mapping[str, Mapping[str, Any]]
    source_identities_sha256: str
    implementation_sha256: str
    invalidation_key_sha256: str


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


def _json(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8").rstrip("\n")


def _private_store(path: Path, scanned_root: Path) -> Path:
    if path.exists() or path.is_symlink():
        existing = path.lstat()
        if path.is_symlink() or not stat.S_ISDIR(existing.st_mode):
            raise MapperError("mapper store must be a real directory")
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(scanned_root)
    except ValueError:
        pass
    else:
        raise MapperError("mapper store must be outside the scanned root")
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = resolved.lstat()
    if resolved.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise MapperError("mapper store must be a real directory")
    if metadata.st_uid != os.getuid():
        raise MapperError("mapper store must belong to the current user")
    if stat.S_IMODE(metadata.st_mode) != 0o700:
        raise MapperError("mapper store must have mode 0700")
    return resolved


def _replace_atomic(path: Path, payload: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)


def _root_key(inventory: NavigationRun) -> str:
    root = inventory.manifest["root"]
    identity = {
        "path": root["path"],
        "device": root["device"],
        "inode": root["inode"],
        "uid": root["uid"],
    }
    return sha256_bytes(canonical_bytes(identity))[:24]


def _artifact_id(root_key: str, path: str) -> str:
    return _entity_id("ARTIFACT", root_key, path)


def _directory_id(root_key: str, path: str) -> str:
    return _entity_id("DIRECTORY", root_key, path)


def _repository_id(root_key: str) -> str:
    return _entity_id("REPOSITORY", root_key, ".")


def _container_id(root_key: str, kind: str, path: str) -> str:
    return _entity_id("LOGICAL_CONTAINER", root_key, f"{kind}:{path}")


def _entity_id(kind: str, root_key: str, qualified_name: str) -> str:
    digest = sha256_bytes(canonical_bytes([kind, root_key, qualified_name]))
    return f"entity:{digest}"


def _fact_id(parts: Sequence[str]) -> str:
    return sha256_bytes(canonical_bytes(list(parts)))


def _configure_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        f"""
        PRAGMA foreign_keys=ON;
        PRAGMA trusted_schema=OFF;
        PRAGMA journal_mode=DELETE;
        PRAGMA synchronous=FULL;

        CREATE TABLE meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE producers (
            producer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            determinism_class TEXT NOT NULL,
            implementation_sha256 TEXT NOT NULL,
            configuration_json TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY,
            source_kind TEXT NOT NULL,
            path TEXT,
            identity_sha256 TEXT NOT NULL,
            privacy_class TEXT NOT NULL,
            attributes_json TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE entities (
            entity_id TEXT PRIMARY KEY,
            entity_kind TEXT NOT NULL,
            name TEXT NOT NULL,
            qualified_name TEXT NOT NULL,
            source_id TEXT REFERENCES sources(source_id),
            truth_class TEXT NOT NULL CHECK(truth_class IN {TRUTH_CLASSES}),
            confidence REAL GENERATED ALWAYS AS (
                CASE WHEN truth_class='INFERRED'
                     THEN {DEFAULT_STATIC_INFERENCE_CONFIDENCE}
                     ELSE NULL END
            ) STORED,
            producer_id TEXT NOT NULL REFERENCES producers(producer_id),
            snapshot_run_id TEXT NOT NULL,
            privacy_class TEXT NOT NULL,
            first_seen_run_id TEXT NOT NULL,
            last_seen_run_id TEXT NOT NULL,
            attributes_json TEXT NOT NULL,
            CHECK((truth_class='INFERRED' AND confidence IN {INFERRED_CONFIDENCE_VALUES})
               OR (truth_class<>'INFERRED' AND confidence IS NULL))
        ) WITHOUT ROWID;

        CREATE INDEX entities_name_idx ON entities(name);
        CREATE INDEX entities_qualified_name_idx ON entities(qualified_name);
        CREATE INDEX entities_kind_idx ON entities(entity_kind);

        CREATE TABLE artifact_properties (
            entity_id TEXT PRIMARY KEY REFERENCES entities(entity_id),
            inventory_record_sha256 TEXT NOT NULL,
            content_sha256 TEXT,
            kind TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            ctime_ns INTEGER NOT NULL,
            mode INTEGER NOT NULL,
            uid INTEGER NOT NULL,
            gid INTEGER NOT NULL,
            device INTEGER NOT NULL,
            inode INTEGER NOT NULL,
            nlink INTEGER NOT NULL,
            hash_status TEXT NOT NULL,
            git_status TEXT NOT NULL,
            git_tracked INTEGER NOT NULL,
            git_blob_oid TEXT,
            suffix TEXT NOT NULL,
            media_type TEXT,
            semantic_eligible INTEGER NOT NULL,
            semantic_reason TEXT NOT NULL,
            scan_error TEXT
        ) WITHOUT ROWID;

        CREATE INDEX artifact_properties_content_idx
            ON artifact_properties(content_sha256);
        CREATE INDEX artifact_properties_git_idx
            ON artifact_properties(git_status,git_tracked);

        CREATE TABLE relations (
            relation_id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL REFERENCES entities(entity_id),
            predicate TEXT NOT NULL,
            object_id TEXT NOT NULL REFERENCES entities(entity_id),
            source_id TEXT REFERENCES sources(source_id),
            truth_class TEXT NOT NULL CHECK(truth_class IN {TRUTH_CLASSES}),
            confidence REAL,
            producer_id TEXT NOT NULL REFERENCES producers(producer_id),
            snapshot_run_id TEXT NOT NULL,
            first_seen_run_id TEXT NOT NULL,
            last_seen_run_id TEXT NOT NULL,
            attributes_json TEXT NOT NULL,
            CHECK((truth_class='INFERRED' AND confidence IN {INFERRED_CONFIDENCE_VALUES})
               OR (truth_class<>'INFERRED' AND confidence IS NULL))
        ) WITHOUT ROWID;

        CREATE INDEX relations_subject_idx ON relations(subject_id,predicate);
        CREATE INDEX relations_object_idx ON relations(object_id,predicate);

        CREATE TABLE observations (
            observation_id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL REFERENCES entities(entity_id),
            predicate TEXT NOT NULL,
            value_json TEXT NOT NULL,
            source_id TEXT REFERENCES sources(source_id),
            truth_class TEXT NOT NULL CHECK(truth_class IN {TRUTH_CLASSES}),
            confidence REAL,
            producer_id TEXT NOT NULL REFERENCES producers(producer_id),
            snapshot_run_id TEXT NOT NULL,
            first_seen_run_id TEXT NOT NULL,
            last_seen_run_id TEXT NOT NULL,
            CHECK((truth_class='INFERRED' AND confidence IN {INFERRED_CONFIDENCE_VALUES})
               OR (truth_class<>'INFERRED' AND confidence IS NULL))
        ) WITHOUT ROWID;

        CREATE INDEX observations_entity_idx
            ON observations(entity_id,predicate);

        CREATE TABLE locations (
            location_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES sources(source_id),
            path TEXT NOT NULL,
            byte_start INTEGER,
            byte_end INTEGER,
            line_start INTEGER,
            line_end INTEGER,
            column_start INTEGER,
            column_end INTEGER
        ) WITHOUT ROWID;

        CREATE TABLE derivations (
            fact_id TEXT NOT NULL,
            parent_kind TEXT NOT NULL,
            parent_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            PRIMARY KEY(fact_id,parent_kind,parent_id)
        ) WITHOUT ROWID;

        CREATE TABLE coverage (
            producer_id TEXT NOT NULL REFERENCES producers(producer_id),
            map_id TEXT NOT NULL,
            fact_class TEXT NOT NULL,
            scope TEXT NOT NULL,
            disposition TEXT NOT NULL CHECK(disposition IN {COVERAGE_STATES}),
            sources_total INTEGER NOT NULL,
            sources_covered INTEGER NOT NULL,
            sources_failed INTEGER NOT NULL,
            sources_unsupported INTEGER NOT NULL,
            sources_skipped INTEGER NOT NULL,
            details_json TEXT NOT NULL,
            PRIMARY KEY(producer_id,map_id,fact_class,scope)
        ) WITHOUT ROWID;

        CREATE TABLE conflicts (
            conflict_id TEXT PRIMARY KEY,
            subject_id TEXT,
            fact_class TEXT NOT NULL,
            status TEXT NOT NULL,
            details_json TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE map_views (
            map_id TEXT PRIMARY KEY,
            version TEXT NOT NULL,
            status TEXT NOT NULL,
            required_fact_classes_json TEXT NOT NULL,
            query_contract_json TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE run_inputs (
            input_id TEXT PRIMARY KEY,
            input_kind TEXT NOT NULL,
            identity_sha256 TEXT NOT NULL,
            details_json TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE producer_inputs (
            producer_id TEXT PRIMARY KEY REFERENCES producers(producer_id),
            invalidation_key_sha256 TEXT NOT NULL,
            source_identities_sha256 TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            input_scope_json TEXT NOT NULL,
            execution TEXT NOT NULL
                CHECK(execution IN ('PARTIAL','RECOMPUTED','REUSED')),
            facts_reused INTEGER NOT NULL,
            facts_recomputed INTEGER NOT NULL,
            duration_seconds REAL NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE python_fragments (
            path TEXT PRIMARY KEY,
            fragment_kind TEXT NOT NULL
                CHECK(fragment_kind IN ('PYTHON_SOURCE','PROJECT_MANIFEST')),
            source_identity_sha256 TEXT NOT NULL,
            context_sha256 TEXT NOT NULL,
            extractor_sha256 TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            execution TEXT NOT NULL CHECK(execution IN ('RECOMPUTED','REUSED')),
            first_seen_run_id TEXT NOT NULL,
            last_seen_run_id TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE projection_reuse (
            path TEXT NOT NULL,
            source_id TEXT NOT NULL REFERENCES sources(source_id),
            producer_id TEXT NOT NULL REFERENCES producers(producer_id),
            entities_reused INTEGER NOT NULL,
            relations_reused INTEGER NOT NULL,
            observations_reused INTEGER NOT NULL,
            locations_reused INTEGER NOT NULL,
            reuse_reason TEXT NOT NULL,
            PRIMARY KEY(path,producer_id)
        ) WITHOUT ROWID;
        """
    )


def _inventory_connection(inventory: NavigationRun) -> sqlite3.Connection:
    database = inventory.run_directory / "inventory.sqlite3"
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _producer_hash() -> str:
    return _file_sha256(Path(__file__).resolve())[0]


def _capability_backend() -> tuple[type[Exception], Any] | None:
    """Load optional GIGA integration without hiding a broken installed backend."""
    try:
        from twin_core.capability_adoption import (
            CapabilityAdoptionError,
            inspect_capability_manifest,
        )
    except ModuleNotFoundError as exc:
        if exc.name not in {"twin_core", "twin_core.capability_adoption"}:
            raise
        return None
    return CapabilityAdoptionError, inspect_capability_manifest


def _compiler_identity() -> dict[str, Any]:
    files = [
        Path(__file__).resolve(),
        Path(extract_python_fragment.__code__.co_filename).resolve(),
        Path(classify_source.__code__.co_filename).resolve(),
        Path(parse_sql_literal.__code__.co_filename).resolve(),
        Path(parse_coverage_json.__code__.co_filename).resolve(),
        Path(safe_exact_duplicate_groups.__code__.co_filename).resolve(),
        Path(build_counterevidence.__code__.co_filename).resolve(),
        Path(collect_recent_lineage.__code__.co_filename).resolve(),
        Path(strict_json_object.__code__.co_filename).resolve(),
        Path(load_runtime_registry.__code__.co_filename).resolve(),
        Path(current_semantic_run.__code__.co_filename).resolve(),
        Path(extract_shell_file_fragment.__code__.co_filename).resolve(),
        Path(extract_javascript_file_fragment.__code__.co_filename).resolve(),
        Path(load_scip_index.__code__.co_filename).resolve(),
    ]
    capability_backend = _capability_backend()
    if capability_backend is not None:
        files.insert(8, Path(capability_backend[1].__code__.co_filename).resolve())
    entries = [{"path": path.name, "sha256": _file_sha256(path)[0]} for path in files]
    return {
        "files": entries,
        "capability_backend": "AVAILABLE" if capability_backend is not None else "UNAVAILABLE_OPTIONAL_GIGA_INTEGRATION",
        "flow_policy": FLOW_POLICY_VERSION,
        "flow_policy_sha256": POLICY_SHA256,
        "operational_policy": OPERATIONAL_POLICY_VERSION,
        "operational_policy_sha256": OPERATIONAL_POLICY_SHA256,
        "quality_policy": QUALITY_POLICY_VERSION,
        "quality_policy_sha256": QUALITY_POLICY_SHA256,
        "cleanup_policy": CLEANUP_POLICY_VERSION,
        "cleanup_policy_sha256": CLEANUP_POLICY_SHA256,
        "runtime_policy": RUNTIME_POLICY_VERSION,
        "runtime_policy_sha256": RUNTIME_POLICY_SHA256,
        "shell_backend": dict(shell_backend_identity()),
        "javascript_backend": dict(javascript_backend_identity()),
        "sha256": sha256_bytes(canonical_bytes(entries)),
    }


def _source_identity(record: Mapping[str, Any]) -> str:
    stable = dict(record)
    if stable.get("hash_status") in {"hashed", "reused"}:
        stable["hash_status"] = "available"
    return sha256_bytes(canonical_bytes(stable))


def _producer_source_identity(record: Mapping[str, Any]) -> str:
    """Hash only fields that can change the compound producer's fact output.

    Git status, inode and timestamps remain exact in the current inventory source
    metadata, but they do not change AST/build/quality facts and therefore must not
    cause a costly producer rerun after an otherwise byte-identical commit.
    """

    return sha256_bytes(
        canonical_bytes(
            {
                "path": record["path"],
                "kind": record["kind"],
                "content_sha256": record["content_sha256"],
                "suffix": record["suffix"],
                "semantic_eligible": record["semantic_eligible"],
                "semantic_reason": record["semantic_reason"],
                "executable": bool(record["mode"] & 0o111),
            }
        )
    )


def _privacy(record: Mapping[str, Any]) -> str:
    if record["semantic_reason"] == "sensitive-path":
        return "SENSITIVE_METADATA"
    return "LOCAL_METADATA"


def _parent_directories(path: str) -> Iterable[str]:
    current = path.rpartition("/")[0]
    while True:
        if not current:
            yield "."
            return
        yield current
        current = current.rpartition("/")[0]


def _confidence_for_truth(truth_class: str, confidence: float | None) -> float | None:
    """Normalize producer confidence without collapsing truth classes.

    Deterministic static inference uses the documented 0.75 rubric unless a
    producer supplies one of the closed discrete values.  Non-inferred facts
    must not carry confidence: PROVEN/OBSERVED describe provenance classes,
    not probabilities, while CONFLICT/UNKNOWN/UNSUPPORTED remain explicit.
    """

    if truth_class not in TRUTH_CLASSES:
        raise MapperError(f"unsupported mapper truth class: {truth_class}")
    if truth_class != "INFERRED":
        if confidence is not None:
            raise MapperError("only INFERRED facts may carry confidence")
        return None
    if confidence is None:
        return DEFAULT_STATIC_INFERENCE_CONFIDENCE
    if isinstance(confidence, bool) or confidence not in INFERRED_CONFIDENCE_VALUES:
        raise MapperError("INFERRED confidence must use the closed discrete rubric")
    return float(confidence)


def _insert_relation(
    connection: sqlite3.Connection,
    *,
    subject: str,
    predicate: str,
    object_: str,
    source_id: str,
    producer_id: str,
    snapshot_run_id: str,
    attributes: Mapping[str, Any] | None = None,
    truth_class: str = "PROVEN",
    confidence: float | None = None,
) -> None:
    confidence = _confidence_for_truth(truth_class, confidence)
    attributes_json = _json(dict(attributes or {}))
    relation_id = _fact_id(
        [
            subject,
            predicate,
            object_,
            source_id,
            producer_id,
            attributes_json,
        ]
    )
    connection.execute(
        """INSERT INTO relations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            relation_id,
            subject,
            predicate,
            object_,
            source_id,
            truth_class,
            confidence,
            producer_id,
            snapshot_run_id,
            snapshot_run_id,
            snapshot_run_id,
            attributes_json,
        ),
    )


def _insert_observation(
    connection: sqlite3.Connection,
    *,
    entity_id: str,
    predicate: str,
    value: Mapping[str, Any],
    source_id: str,
    producer_id: str,
    snapshot_run_id: str,
    truth_class: str = "PROVEN",
    confidence: float | None = None,
) -> str:
    confidence = _confidence_for_truth(truth_class, confidence)
    value_json = _json(dict(value))
    observation_id = _fact_id(
        [
            entity_id,
            predicate,
            value_json,
            source_id,
            producer_id,
        ]
    )
    connection.execute(
        "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            observation_id,
            entity_id,
            predicate,
            value_json,
            source_id,
            truth_class,
            confidence,
            producer_id,
            snapshot_run_id,
            snapshot_run_id,
            snapshot_run_id,
        ),
    )
    return observation_id


def _insert_location(
    connection: sqlite3.Connection,
    *,
    fact_id: str,
    source_id: str,
    path: str,
    span: Mapping[str, Any] | None,
) -> None:
    if span is None:
        return
    connection.execute(
        "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?)",
        (
            fact_id,
            source_id,
            path,
            span.get("byte_start"),
            span.get("byte_end"),
            span.get("line_start"),
            span.get("line_end"),
            span.get("column_start"),
            span.get("column_end"),
        ),
    )


def _resolve_relative_module(
    current_module: str,
    current_path: str,
    target: str,
    level: int,
) -> str | None:
    if level == 0:
        return target
    package = (
        current_module
        if PurePosixPath(current_path).name == "__init__.py"
        else current_module.rpartition(".")[0]
    )
    parts = [item for item in package.split(".") if item]
    ascend = level - 1
    if ascend > len(parts):
        return None
    base = parts[: len(parts) - ascend]
    if target:
        base.extend(target.split("."))
    return ".".join(base) or None


def _python_input_set(inventory: NavigationRun, root_key: str) -> PythonInputSet:
    """Bind the complete compound Python producer input without reading source bytes.

    The Python, operational and quality projections are one coupled producer today:
    cross-file symbol resolution and test/build links mean they must invalidate as a
    unit.  The key includes every inventory record the producer may read plus the
    exact implementation and policy closure.  This is deliberately coarser than
    source-local fragment reuse now sits beneath this group boundary; cross-file
    projection remains coupled and globally invalidated.
    """

    inventory_connection = _inventory_connection(inventory)
    try:
        python_records = tuple(
            dict(row)
            for row in inventory_connection.execute(
                """SELECT * FROM files
                   WHERE kind='regular' AND semantic_eligible=1
                     AND suffix IN ('.py','.pyi')
                   ORDER BY path"""
            )
        )
        project_records = tuple(
            dict(row)
            for row in inventory_connection.execute(
                """SELECT * FROM files
                   WHERE kind='regular' AND semantic_eligible=1
                     AND (path='pyproject.toml' OR path LIKE '%/pyproject.toml')
                   ORDER BY path"""
            )
        )
        safe_records = tuple(
            dict(row)
            for row in inventory_connection.execute(
                """SELECT * FROM files
                   WHERE kind='regular' AND semantic_eligible=1
                   ORDER BY path"""
            )
        )
    finally:
        inventory_connection.close()
    build_records = tuple(
        row for row in safe_records if build_asset_role(row["path"]) is not None
    )
    quality_records = tuple(
        row for row in safe_records if quality_asset_role(row["path"]) is not None
    )
    records_by_path = {
        record["path"]: {key: value for key, value in record.items() if key != "id"}
        for record in (
            *python_records,
            *project_records,
            *build_records,
            *quality_records,
        )
    }
    source_identities = [
        {"path": path, "identity_sha256": _producer_source_identity(record)}
        for path, record in sorted(records_by_path.items())
    ]
    source_digest = sha256_bytes(canonical_bytes(source_identities))
    implementation = {
        "database_schema": DATABASE_SCHEMA,
        "mapper_sha256": _producer_hash(),
        "python_map_sha256": _file_sha256(
            Path(extract_python_fragment.__code__.co_filename).resolve()
        )[0],
        "operational_map_sha256": _file_sha256(
            Path(parse_sql_literal.__code__.co_filename).resolve()
        )[0],
        "quality_map_sha256": _file_sha256(
            Path(parse_coverage_json.__code__.co_filename).resolve()
        )[0],
        "flow_policy_sha256": POLICY_SHA256,
        "operational_policy_sha256": OPERATIONAL_POLICY_SHA256,
        "quality_policy_sha256": QUALITY_POLICY_SHA256,
    }
    implementation_sha256 = sha256_bytes(canonical_bytes(implementation))
    invalidation_key = sha256_bytes(
        canonical_bytes(
            {
                "producer_group": list(PYTHON_PRODUCER_IDS),
                "root_key": root_key,
                "source_identities_sha256": source_digest,
                "implementation": implementation,
            }
        )
    )
    return PythonInputSet(
        python_records=python_records,
        project_records=project_records,
        build_records=build_records,
        quality_records=quality_records,
        records_by_path=records_by_path,
        source_identities_sha256=source_digest,
        implementation_sha256=implementation_sha256,
        invalidation_key_sha256=invalidation_key,
    )


def _previous_python_fragments(
    previous: MapperRun | None,
) -> dict[str, Mapping[str, Any]]:
    """Load the authenticated prior fragment index when its schema is exact."""

    if previous is None:
        return {}
    database_path = previous.run_directory / "facts.sqlite3"
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        schema = connection.execute(
            "SELECT value FROM meta WHERE key='database_schema'"
        ).fetchone()
        if schema is None or schema[0] != str(DATABASE_SCHEMA):
            return {}
        return {
            row["path"]: dict(row)
            for row in connection.execute(
                "SELECT * FROM python_fragments ORDER BY path"
            )
        }
    except sqlite3.DatabaseError as exc:
        raise MapperError("previous Python fragment index is unreadable") from exc
    finally:
        connection.close()


def _fragment_payload(
    row: Mapping[str, Any],
    *,
    expected_kind: str,
    expected_source_identity: str,
    expected_context: str,
    expected_extractor: str,
) -> tuple[Mapping[str, Any], str] | None:
    """Return a prior fragment only when every identity and payload binding matches."""

    if (
        row["fragment_kind"] != expected_kind
        or row["source_identity_sha256"] != expected_source_identity
        or row["context_sha256"] != expected_context
        or row["extractor_sha256"] != expected_extractor
    ):
        return None
    raw = row["payload_json"].encode("utf-8")
    if sha256_bytes(raw) != row["payload_sha256"]:
        raise MapperError(
            f"cached Python fragment payload hash mismatch: {row['path']}"
        )
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MapperError(
            f"cached Python fragment is not strict JSON: {row['path']}"
        ) from exc
    if not isinstance(payload, dict):
        raise MapperError(
            f"cached Python fragment root is not an object: {row['path']}"
        )
    expected_keys = (
        {"file", "failure"}
        if expected_kind == "PYTHON_SOURCE"
        else {"entrypoints", "failure"}
    )
    if set(payload) != expected_keys:
        raise MapperError(f"cached Python fragment has an open schema: {row['path']}")
    material = payload.get("file") if expected_kind == "PYTHON_SOURCE" else None
    if material is not None and (
        not isinstance(material, dict) or material.get("path") != row["path"]
    ):
        raise MapperError(f"cached Python fragment path mismatch: {row['path']}")
    entries = (
        payload.get("entrypoints") if expected_kind == "PROJECT_MANIFEST" else None
    )
    if entries is not None and (
        not isinstance(entries, list)
        or any(
            not isinstance(item, dict) or item.get("path") != row["path"]
            for item in entries
        )
    ):
        raise MapperError(f"cached project fragment path mismatch: {row['path']}")
    failure = payload.get("failure")
    if failure is not None and (
        not isinstance(failure, dict) or failure.get("path") != row["path"]
    ):
        raise MapperError(
            f"cached Python fragment failure path mismatch: {row['path']}"
        )
    if expected_kind == "PYTHON_SOURCE" and ((material is None) == (failure is None)):
        raise MapperError(
            f"cached Python fragment disposition is ambiguous: {row['path']}"
        )
    if expected_kind == "PROJECT_MANIFEST" and (
        not isinstance(entries, list) or (failure is not None and entries)
    ):
        raise MapperError(
            f"cached project fragment disposition is ambiguous: {row['path']}"
        )
    return payload, row["first_seen_run_id"]


def _store_python_fragment(
    connection: sqlite3.Connection,
    *,
    path: str,
    fragment_kind: str,
    source_identity: str,
    context_sha256: str,
    extractor_sha256: str,
    payload: Mapping[str, Any],
    execution: str,
    first_seen_run_id: str,
    last_seen_run_id: str,
) -> None:
    payload_json = _json(payload)
    connection.execute(
        "INSERT INTO python_fragments VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            path,
            fragment_kind,
            source_identity,
            context_sha256,
            extractor_sha256,
            sha256_bytes(payload_json.encode("utf-8")),
            payload_json,
            execution,
            first_seen_run_id,
            last_seen_run_id,
        ),
    )


def _extract_python_fragments_incremental(
    connection: sqlite3.Connection,
    *,
    root: Path,
    inputs: PythonInputSet,
    previous: MapperRun | None,
    snapshot_run_id: str,
) -> tuple[PythonFragment, dict[str, int]]:
    """Reuse exact source-local fragments and reparse only invalidated files.

    Cross-file resolution is deliberately performed after assembly by the canonical
    projector.  This milestone therefore saves source parsing, while reporting global
    projection recomputation honestly instead of claiming dependency-level reuse.
    """

    previous_rows = _previous_python_fragments(previous)
    current_paths = {
        record["path"] for record in (*inputs.python_records, *inputs.project_records)
    }
    package_directories = frozenset(
        str(PurePosixPath(record["path"]).parent)
        for record in inputs.python_records
        if PurePosixPath(record["path"]).name == "__init__.py"
    )
    extractor_sha256 = _file_sha256(
        Path(extract_python_file_fragment.__code__.co_filename).resolve()
    )[0]
    files: list[Mapping[str, Any]] = []
    entrypoints: list[Mapping[str, Any]] = []
    failures: list[Mapping[str, Any]] = []
    reused = 0
    recomputed = 0

    def source_failure(
        path: str, exc: PythonMapError, maps: Sequence[str]
    ) -> dict[str, Any]:
        return {
            "path": path,
            "status": "FAILED_SOURCE_SNAPSHOT",
            "error_class": type(exc).__name__,
            "error_sha256": sha256_bytes(str(exc).encode("utf-8", "replace")),
            "maps": list(maps),
        }

    for record in inputs.python_records:
        path = record["path"]
        source_identity = _producer_source_identity(record)
        context_sha256 = sha256_bytes(
            canonical_bytes(
                {
                    "fragment_kind": "PYTHON_SOURCE",
                    "module": python_module_name(path, package_directories),
                }
            )
        )
        cached = None
        if path in previous_rows:
            cached = _fragment_payload(
                previous_rows[path],
                expected_kind="PYTHON_SOURCE",
                expected_source_identity=source_identity,
                expected_context=context_sha256,
                expected_extractor=extractor_sha256,
            )
        if cached is None:
            try:
                file_fragment, failure = extract_python_file_fragment(
                    root, record, package_directories
                )
            except PythonMapError as exc:
                file_fragment = None
                failure = source_failure(
                    path,
                    exc,
                    (
                        "symbols",
                        "dependencies",
                        "types",
                        "api_events",
                        "calls",
                        "control_flow",
                        "data_flow_taint",
                        "security_capabilities",
                    ),
                )
            payload = {"file": file_fragment, "failure": failure}
            execution = "RECOMPUTED"
            first_seen = snapshot_run_id
            recomputed += 1
        else:
            payload, first_seen = cached
            execution = "REUSED"
            reused += 1
        if payload["file"] is not None:
            files.append(payload["file"])
        if payload["failure"] is not None:
            failures.append(payload["failure"])
        _store_python_fragment(
            connection,
            path=path,
            fragment_kind="PYTHON_SOURCE",
            source_identity=source_identity,
            context_sha256=context_sha256,
            extractor_sha256=extractor_sha256,
            payload=payload,
            execution=execution,
            first_seen_run_id=first_seen,
            last_seen_run_id=snapshot_run_id,
        )

    project_context = sha256_bytes(
        canonical_bytes({"fragment_kind": "PROJECT_MANIFEST", "format": "TOML"})
    )
    for record in inputs.project_records:
        path = record["path"]
        source_identity = _producer_source_identity(record)
        cached = None
        if path in previous_rows:
            cached = _fragment_payload(
                previous_rows[path],
                expected_kind="PROJECT_MANIFEST",
                expected_source_identity=source_identity,
                expected_context=project_context,
                expected_extractor=extractor_sha256,
            )
        if cached is None:
            try:
                project_entrypoints, failure = extract_project_file_fragment(
                    root, record
                )
            except PythonMapError as exc:
                project_entrypoints = ()
                failure = source_failure(path, exc, ("api_events", "build_deployment"))
            payload = {"entrypoints": list(project_entrypoints), "failure": failure}
            execution = "RECOMPUTED"
            first_seen = snapshot_run_id
            recomputed += 1
        else:
            payload, first_seen = cached
            execution = "REUSED"
            reused += 1
        entrypoints.extend(payload["entrypoints"])
        if payload["failure"] is not None:
            failures.append(payload["failure"])
        _store_python_fragment(
            connection,
            path=path,
            fragment_kind="PROJECT_MANIFEST",
            source_identity=source_identity,
            context_sha256=project_context,
            extractor_sha256=extractor_sha256,
            payload=payload,
            execution=execution,
            first_seen_run_id=first_seen,
            last_seen_run_id=snapshot_run_id,
        )

    fragment = PythonFragment(
        files=tuple(sorted(files, key=lambda item: item["path"])),
        project_entrypoints=tuple(
            sorted(
                entrypoints, key=lambda item: (item["path"], item["kind"], item["name"])
            )
        ),
        failures=tuple(sorted(failures, key=lambda item: item["path"])),
    )
    return fragment, {
        "python_fragments_total": len(current_paths),
        "python_fragments_reused": reused,
        "python_fragments_recomputed": recomputed,
        "python_fragments_deleted": len(set(previous_rows) - current_paths),
    }


def _insert_python_sources(
    connection: sqlite3.Connection,
    *,
    inputs: PythonInputSet,
    root_key: str,
    snapshot_run_id: str,
) -> dict[str, str]:
    source_by_path: dict[str, str] = {}
    for path, record in sorted(inputs.records_by_path.items()):
        source_id = f"source:artifact:{_fact_id([root_key, path, record['content_sha256'] or ''])}"
        source_by_path[path] = source_id
        connection.execute(
            "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?)",
            (
                source_id,
                "ARTIFACT",
                path,
                _source_identity(record),
                "LOCAL_SOURCE",
                _json(
                    {
                        "content_sha256": record["content_sha256"],
                        "inventory_run_id": snapshot_run_id,
                        "semantic_reason": record["semantic_reason"],
                    }
                ),
            ),
        )
    return source_by_path


def _build_python_maps(
    connection: sqlite3.Connection,
    *,
    inventory: NavigationRun,
    root_key: str,
    repository_id: str,
    manifest_source: str,
    producer_id: str,
    operational_producer_id: str,
    quality_producer_id: str,
    snapshot_run_id: str,
    inputs: PythonInputSet | None = None,
    source_by_path: Mapping[str, str] | None = None,
    previous: MapperRun | None = None,
) -> dict[str, int]:
    inputs = inputs or _python_input_set(inventory, root_key)
    python_records = list(inputs.python_records)
    project_records = list(inputs.project_records)
    build_records = list(inputs.build_records)
    quality_records = list(inputs.quality_records)
    root = Path(inventory.manifest["root"]["path"]).resolve(strict=True)
    try:
        fragment, fragment_counts = _extract_python_fragments_incremental(
            connection,
            root=root,
            inputs=inputs,
            previous=previous,
            snapshot_run_id=snapshot_run_id,
        )
    except PythonMapError as exc:
        raise MapperError(str(exc)) from exc

    records_by_path = dict(inputs.records_by_path)
    if source_by_path is None:
        source_by_path = _insert_python_sources(
            connection,
            inputs=inputs,
            root_key=root_key,
            snapshot_run_id=snapshot_run_id,
        )
    reused_source_ids = _copy_partial_python_projection(
        connection,
        previous=previous,
        source_by_path=source_by_path,
        inputs=inputs,
        snapshot_run_id=snapshot_run_id,
    )
    if reused_source_ids:
        connection = _SelectiveProjectionConnection(connection, reused_source_ids)

    module_by_path: dict[str, str] = {}
    module_ids_by_name: dict[str, list[str]] = {}
    file_by_path = {item["path"]: item for item in fragment.files}
    for item in fragment.files:
        path = item["path"]
        module_id = _entity_id("PYTHON_MODULE", root_key, f"{item['module']}:{path}")
        module_by_path[path] = module_id
        module_ids_by_name.setdefault(item["module"], []).append(module_id)
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                module_id,
                "PYTHON_MODULE",
                item["module"].rsplit(".", 1)[-1],
                item["module"],
                source_by_path[path],
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "language": "python",
                        "artifact_path": path,
                        "content_sha256": item["content_sha256"],
                        "ast_sha256": item["ast_sha256"],
                    }
                ),
            ),
        )

    definitions: dict[str, list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    for item in fragment.files:
        for definition in item["definitions"]:
            symbol_id = _entity_id(
                "PYTHON_SYMBOL",
                root_key,
                ":".join(
                    (
                        _artifact_id(root_key, item["path"]),
                        definition["qualified_name"],
                        definition["kind"],
                    )
                ),
            )
            definitions.setdefault(symbol_id, []).append((item, definition))

    symbol_by_path_qname: dict[tuple[str, str], list[str]] = {}
    symbols_by_module_leaf: dict[tuple[str, str], list[str]] = {}
    symbol_definition: dict[str, Mapping[str, Any]] = {}
    for symbol_id, occurrences in sorted(definitions.items()):
        first_item, first = occurrences[0]
        path = first_item["path"]
        source_id = source_by_path[path]
        symbol_definition[symbol_id] = first
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                symbol_id,
                "PYTHON_SYMBOL",
                first["name"],
                first["qualified_name"],
                source_id,
                "PROVEN" if len(occurrences) == 1 else "CONFLICT",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "language": "python",
                        "symbol_kind": first["kind"],
                        "definition_count": len(occurrences),
                        "definitions": [
                            {
                                "path": item["path"],
                                "span": definition["span"],
                                **definition["attributes"],
                            }
                            for item, definition in occurrences
                        ],
                    }
                ),
            ),
        )
        symbol_by_path_qname.setdefault((path, first["qualified_name"]), []).append(
            symbol_id
        )
        module = first_item["module"]
        symbols_by_module_leaf.setdefault((module, first["name"]), []).append(symbol_id)
        if source_id in reused_source_ids:
            continue
        for item, definition in occurrences:
            fact_id = _insert_observation(
                connection,
                entity_id=symbol_id,
                predicate="PYTHON_DEFINITION",
                value={
                    "path": item["path"],
                    "span": definition["span"],
                    "scope": definition["scope"],
                    "attributes": definition["attributes"],
                },
                source_id=source_by_path[item["path"]],
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="PROVEN" if len(occurrences) == 1 else "CONFLICT",
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_by_path[item["path"]],
                path=item["path"],
                span=definition["span"],
            )
        _insert_relation(
            connection,
            subject=module_by_path[path],
            predicate="DEFINES",
            object_=symbol_id,
            source_id=source_id,
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
        )

    def unique_symbol(path: str, qualified: str) -> str | None:
        candidates = symbol_by_path_qname.get((path, qualified), [])
        return candidates[0] if len(candidates) == 1 else None

    def lexical_symbol(path: str, module: str, scope: str, name: str) -> str | None:
        current = scope
        while current:
            found = unique_symbol(path, f"{current}.{name}")
            if found:
                return found
            if current == module or "." not in current:
                break
            current = current.rpartition(".")[0]
        found = symbols_by_module_leaf.get((module, name), [])
        return found[0] if len(found) == 1 else None

    import_aliases: dict[str, dict[str, str]] = {}
    declared_import_aliases: dict[str, dict[str, str]] = {}
    import_count = 0
    unresolved_imports = 0
    for item in fragment.files:
        path = item["path"]
        module = item["module"]
        aliases: dict[str, str] = {}
        declared_aliases: dict[str, str] = {}
        if source_by_path[path] in reused_source_ids:
            import_aliases[path] = aliases
            declared_import_aliases[path] = declared_aliases
            continue
        for imported in item["imports"]:
            resolved_name = _resolve_relative_module(
                module,
                path,
                imported["module"],
                imported["level"],
            )
            module_candidates = module_ids_by_name.get(resolved_name or "", [])
            target_module = (
                module_candidates[0] if len(module_candidates) == 1 else None
            )
            resolution = "EXACT_INTERNAL" if target_module else "UNRESOLVED_OR_EXTERNAL"
            value = {
                **imported,
                "resolved_module": resolved_name,
                "resolution": resolution,
                "target_module_id": target_module,
            }
            declared_target = resolved_name or imported["module"]
            if imported["imported_name"]:
                declared_target = ".".join(
                    part
                    for part in (declared_target, imported["imported_name"])
                    if part
                )
            if declared_target:
                declared_aliases[imported["alias"]] = declared_target
            fact_id = _insert_observation(
                connection,
                entity_id=module_by_path[path],
                predicate="PYTHON_IMPORT",
                value=value,
                source_id=source_by_path[path],
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_by_path[path],
                path=path,
                span=imported["span"],
            )
            import_count += 1
            if target_module:
                _insert_relation(
                    connection,
                    subject=module_by_path[path],
                    predicate="IMPORTS",
                    object_=target_module,
                    source_id=source_by_path[path],
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={"span": imported["span"], "text": value},
                )
                if imported["imported_name"]:
                    candidates = symbols_by_module_leaf.get(
                        (resolved_name or "", imported["imported_name"]), []
                    )
                    if len(candidates) == 1:
                        aliases[imported["alias"]] = candidates[0]
                else:
                    aliases[imported["alias"]] = target_module
            else:
                unresolved_imports += 1
        import_aliases[path] = aliases
        declared_import_aliases[path] = declared_aliases

    def resolve_reference(
        path: str,
        module: str,
        scope: str,
        name: str,
        expression: str,
    ) -> tuple[str | None, str]:
        aliases = import_aliases[path]
        target = lexical_symbol(path, module, scope, name)
        resolution = "EXACT_LEXICAL" if target else "UNRESOLVED"
        if target is None and expression in aliases:
            target = aliases[expression]
            resolution = "EXACT_IMPORT"
        if target is None and "." in expression:
            alias, _, leaf = expression.partition(".")
            imported_target = aliases.get(alias)
            if imported_target and imported_target.startswith("entity:"):
                imported_module = connection.execute(
                    "SELECT qualified_name FROM entities WHERE entity_id=? AND entity_kind='PYTHON_MODULE'",
                    (imported_target,),
                ).fetchone()
                if imported_module:
                    candidates = symbols_by_module_leaf.get(
                        (imported_module[0], leaf.rsplit(".", 1)[-1]), []
                    )
                    if len(candidates) == 1:
                        target = candidates[0]
                        resolution = "EXACT_IMPORT"
        return target, resolution

    def declared_expression(path: str, expression: str) -> str:
        head, separator, tail = expression.partition(".")
        declared = declared_import_aliases[path].get(head)
        if declared is None:
            return expression
        return f"{declared}.{tail}" if separator else declared

    reference_count = 0
    resolved_references = 0
    for item in fragment.files:
        path = item["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        module = item["module"]
        for reference in item["references"]:
            target, resolution = resolve_reference(
                path,
                module,
                reference["scope"],
                reference["name"],
                reference["expression"],
            )
            owner_candidates = symbol_by_path_qname.get((path, reference["scope"]), [])
            owner = (
                owner_candidates[0]
                if len(owner_candidates) == 1
                else module_by_path[path]
            )
            value = {
                **reference,
                "resolution": resolution,
                "target_entity_id": target,
            }
            fact_id = _insert_observation(
                connection,
                entity_id=owner,
                predicate="PYTHON_REFERENCE",
                value=value,
                source_id=source_by_path[path],
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_by_path[path],
                path=path,
                span=reference["span"],
            )
            reference_count += 1
            resolved_references += int(target is not None)

    callable_kinds = {
        "FUNCTION",
        "ASYNC_FUNCTION",
        "METHOD",
        "ASYNC_METHOD",
        "CLASS",
    }
    call_count = 0
    resolved_calls = 0
    for item in fragment.files:
        path = item["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        module = item["module"]
        for call in item["calls"]:
            target: str | None = None
            resolution = "UNRESOLVED_DYNAMIC" if call["dynamic"] else "UNRESOLVED"
            if not call["dynamic"]:
                target, resolution = resolve_reference(
                    path,
                    module,
                    call["caller"],
                    call["name"],
                    call["expression"],
                )
                if target is not None:
                    definition = symbol_definition.get(target)
                    if definition is None or definition["kind"] not in callable_kinds:
                        target = None
                        resolution = "UNRESOLVED_NON_CALLABLE"
            owner_candidates = symbol_by_path_qname.get((path, call["caller"]), [])
            owner = (
                owner_candidates[0]
                if len(owner_candidates) == 1
                else module_by_path[path]
            )
            value = {
                **call,
                "declared_expression": declared_expression(path, call["expression"]),
                "resolution": resolution,
                "target_entity_id": target,
            }
            fact_id = _insert_observation(
                connection,
                entity_id=owner,
                predicate="PYTHON_CALL",
                value=value,
                source_id=source_by_path[path],
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_by_path[path],
                path=path,
                span=call["span"],
            )
            if target is not None:
                _insert_relation(
                    connection,
                    subject=owner,
                    predicate="CALLS",
                    object_=target,
                    source_id=source_by_path[path],
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "expression": call["expression"],
                        "declared_expression": declared_expression(
                            path, call["expression"]
                        ),
                        "resolution": resolution,
                        "span": call["span"],
                    },
                )
                resolved_calls += 1
            call_count += 1

    control_flow_count = 0
    control_node_count = 0
    control_edge_count = 0
    for item in fragment.files:
        path = item["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        for flow in item["control_flows"]:
            owner_candidates = symbol_by_path_qname.get((path, flow["owner"]), [])
            if len(owner_candidates) != 1:
                continue
            owner = owner_candidates[0]
            node_ids: dict[str, str] = {}
            for node in flow["nodes"]:
                node_id = _entity_id(
                    "CONTROL_NODE",
                    root_key,
                    f"{_artifact_id(root_key, path)}:{node['node_key']}",
                )
                node_ids[node["node_key"]] = node_id
                qualified_name = f"{flow['owner']}::{node['kind']}"
                if node["span"] is not None:
                    qualified_name += (
                        f"@{node['span']['line_start']}:{node['span']['column_start']}"
                    )
                connection.execute(
                    "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        node_id,
                        "CONTROL_NODE",
                        node["kind"],
                        qualified_name,
                        source_by_path[path],
                        "PROVEN",
                        producer_id,
                        snapshot_run_id,
                        "LOCAL_SOURCE",
                        snapshot_run_id,
                        snapshot_run_id,
                        _json(
                            {
                                "language": "python",
                                "owner": flow["owner"],
                                "span": node["span"],
                                **node["attributes"],
                            }
                        ),
                    ),
                )
                _insert_relation(
                    connection,
                    subject=owner,
                    predicate="HAS_CONTROL_NODE",
                    object_=node_id,
                    source_id=source_by_path[path],
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                )
                fact_id = _insert_observation(
                    connection,
                    entity_id=node_id,
                    predicate="PYTHON_CONTROL_NODE",
                    value=node,
                    source_id=source_by_path[path],
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                )
                if node["span"] is not None:
                    _insert_location(
                        connection,
                        fact_id=fact_id,
                        source_id=source_by_path[path],
                        path=path,
                        span=node["span"],
                    )
                control_node_count += 1
            for edge in flow["edges"]:
                _insert_relation(
                    connection,
                    subject=node_ids[edge["source_key"]],
                    predicate=edge["predicate"],
                    object_=node_ids[edge["target_key"]],
                    source_id=source_by_path[path],
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes=edge["attributes"],
                )
                control_edge_count += 1
            control_flow_count += 1

    data_source_count = 0
    security_effect_count = 0
    static_flow_count = 0
    possible_taint_paths = 0
    source_values: dict[tuple[str, str], str] = {}
    effect_values: dict[tuple[str, str], str] = {}
    adjacency: dict[str, set[str]] = {}
    emitted_flow_keys: set[tuple[str, str, str, str, str]] = set()

    def span_key(span: Mapping[str, Any]) -> str:
        return _json(
            {
                "line_start": span["line_start"],
                "column_start": span["column_start"],
                "line_end": span["line_end"],
                "column_end": span["column_end"],
            }
        )

    def add_possible_flow(
        source: str,
        target: str,
        *,
        path: str,
        span: Mapping[str, Any],
        kind: str,
    ) -> None:
        nonlocal static_flow_count
        key = (source, target, path, span_key(span), kind)
        if key in emitted_flow_keys:
            return
        emitted_flow_keys.add(key)
        adjacency.setdefault(source, set()).add(target)
        _insert_relation(
            connection,
            subject=source,
            predicate="MAY_FLOW_TO",
            object_=target,
            source_id=source_by_path[path],
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
            truth_class="INFERRED",
            attributes={
                "flow_kind": kind,
                "policy_sha256": POLICY_SHA256,
                "span": span,
                "runtime_observed": False,
            },
        )
        static_flow_count += 1

    for item in fragment.files:
        path = item["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        module = item["module"]
        for call in item["calls"]:
            expression = declared_expression(path, call["expression"])
            source_category = classify_source(expression)
            sink_category = classify_sink(expression, call.get("arguments"))
            owner_candidates = symbol_by_path_qname.get((path, call["caller"]), [])
            owner = (
                owner_candidates[0]
                if len(owner_candidates) == 1
                else module_by_path[path]
            )
            if source_category is not None:
                source_id = _entity_id(
                    "DATA_SOURCE",
                    root_key,
                    f"{_artifact_id(root_key, path)}:{source_category}:{span_key(call['span'])}",
                )
                source_values[(path, span_key(call["span"]))] = source_id
                qualified_name = (
                    f"{source_category}:{call['caller']}@"
                    f"{call['span']['line_start']}:{call['span']['column_start']}"
                )
                connection.execute(
                    "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        source_id,
                        "DATA_SOURCE",
                        source_category,
                        qualified_name,
                        source_by_path[path],
                        "INFERRED",
                        producer_id,
                        snapshot_run_id,
                        "LOCAL_SOURCE",
                        snapshot_run_id,
                        snapshot_run_id,
                        _json(
                            {
                                "category": source_category,
                                "expression": expression,
                                "owner": call["caller"],
                                "policy": FLOW_POLICY_VERSION,
                                "policy_sha256": POLICY_SHA256,
                                "runtime_observed": False,
                                "span": call["span"],
                            }
                        ),
                    ),
                )
                _insert_relation(
                    connection,
                    subject=owner,
                    predicate="MAY_READ_DATA_SOURCE",
                    object_=source_id,
                    source_id=source_by_path[path],
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="INFERRED",
                    attributes={"policy_sha256": POLICY_SHA256},
                )
                fact_id = _insert_observation(
                    connection,
                    entity_id=source_id,
                    predicate="PYTHON_POSSIBLE_DATA_SOURCE",
                    value={
                        "category": source_category,
                        "expression": expression,
                        "policy": FLOW_POLICY_VERSION,
                        "policy_sha256": POLICY_SHA256,
                        "span": call["span"],
                    },
                    source_id=source_by_path[path],
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="INFERRED",
                )
                _insert_location(
                    connection,
                    fact_id=fact_id,
                    source_id=source_by_path[path],
                    path=path,
                    span=call["span"],
                )
                data_source_count += 1
            if sink_category is not None:
                effect_id = _entity_id(
                    "SECURITY_EFFECT",
                    root_key,
                    f"{_artifact_id(root_key, path)}:{sink_category}:{span_key(call['span'])}",
                )
                effect_values[(path, span_key(call["span"]))] = effect_id
                qualified_name = (
                    f"{sink_category}:{call['caller']}@"
                    f"{call['span']['line_start']}:{call['span']['column_start']}"
                )
                connection.execute(
                    "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        effect_id,
                        "SECURITY_EFFECT",
                        sink_category,
                        qualified_name,
                        source_by_path[path],
                        "INFERRED",
                        producer_id,
                        snapshot_run_id,
                        "LOCAL_SOURCE",
                        snapshot_run_id,
                        snapshot_run_id,
                        _json(
                            {
                                "authority_status": "NOT_EVALUATED",
                                "category": sink_category,
                                "execution_status": "NOT_OBSERVED",
                                "expression": expression,
                                "owner": call["caller"],
                                "policy": FLOW_POLICY_VERSION,
                                "policy_sha256": POLICY_SHA256,
                                "span": call["span"],
                            }
                        ),
                    ),
                )
                _insert_relation(
                    connection,
                    subject=owner,
                    predicate="MAY_CAUSE_EFFECT",
                    object_=effect_id,
                    source_id=source_by_path[path],
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="INFERRED",
                    attributes={
                        "authority_status": "NOT_EVALUATED",
                        "execution_status": "NOT_OBSERVED",
                        "policy_sha256": POLICY_SHA256,
                    },
                )
                fact_id = _insert_observation(
                    connection,
                    entity_id=effect_id,
                    predicate="PYTHON_POSSIBLE_SECURITY_EFFECT",
                    value={
                        "arguments": call["arguments"],
                        "category": sink_category,
                        "expression": expression,
                        "policy": FLOW_POLICY_VERSION,
                        "policy_sha256": POLICY_SHA256,
                        "span": call["span"],
                    },
                    source_id=source_by_path[path],
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="INFERRED",
                )
                _insert_location(
                    connection,
                    fact_id=fact_id,
                    source_id=source_by_path[path],
                    path=path,
                    span=call["span"],
                )
                security_effect_count += 1

    for item in fragment.files:
        path = item["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        module = item["module"]
        for flow in item["data_flows"]:
            owner_candidates = symbol_by_path_qname.get((path, flow["owner"]), [])
            owner = (
                owner_candidates[0]
                if len(owner_candidates) == 1
                else module_by_path[path]
            )
            target_candidates = symbol_by_path_qname.get((path, flow["target"]), [])
            target = target_candidates[0] if len(target_candidates) == 1 else owner
            resolved_sources = sorted(
                {
                    candidate
                    for name in flow["value"]["names"]
                    if (candidate := lexical_symbol(path, module, flow["owner"], name))
                    is not None
                }
            )
            call_sources = sorted(
                {
                    source_values[(path, span_key(call["span"]))]
                    for call in flow["value"]["calls"]
                    if (path, span_key(call["span"])) in source_values
                }
            )
            for source in (*resolved_sources, *call_sources):
                add_possible_flow(
                    source,
                    target,
                    path=path,
                    span=flow["span"],
                    kind=flow["kind"],
                )
            fact_id = _insert_observation(
                connection,
                entity_id=owner,
                predicate="PYTHON_STATIC_DATA_FLOW",
                value={
                    **flow,
                    "resolved_source_entity_ids": [*resolved_sources, *call_sources],
                    "target_entity_id": target,
                    "flow_certainty": "MAY",
                    "policy_sha256": POLICY_SHA256,
                },
                source_id=source_by_path[path],
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="INFERRED",
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_by_path[path],
                path=path,
                span=flow["span"],
            )

        for call in item["calls"]:
            effect = effect_values.get((path, span_key(call["span"])))
            if effect is None:
                continue
            argument_names = {
                name
                for argument in call["arguments"]["positional"]
                for name in argument["names"]
            } | {
                name
                for argument in call["arguments"]["keywords"]
                for name in argument["names"]
            }
            argument_sources = {
                candidate
                for name in argument_names
                if (candidate := lexical_symbol(path, module, call["caller"], name))
                is not None
            }
            nested_calls = [
                nested
                for argument in (
                    *call["arguments"]["positional"],
                    *call["arguments"]["keywords"],
                )
                for nested in argument["calls"]
            ]
            argument_sources.update(
                source_values[(path, span_key(nested["span"]))]
                for nested in nested_calls
                if (path, span_key(nested["span"])) in source_values
            )
            for source in sorted(argument_sources):
                add_possible_flow(
                    source,
                    effect,
                    path=path,
                    span=call["span"],
                    kind="CALL_ARGUMENT",
                )

    for source in sorted(source_values.values()):
        queue: list[tuple[str, tuple[str, ...]]] = [(source, (source,))]
        visited = {source}
        while queue:
            current, path_ids = queue.pop(0)
            for target in sorted(adjacency.get(current, ())):
                if target in visited:
                    continue
                next_path = (*path_ids, target)
                visited.add(target)
                if connection.execute(
                    "SELECT 1 FROM entities WHERE entity_id=? AND entity_kind='SECURITY_EFFECT'",
                    (target,),
                ).fetchone():
                    source_row = connection.execute(
                        "SELECT source_id FROM entities WHERE entity_id=?", (source,)
                    ).fetchone()
                    _insert_relation(
                        connection,
                        subject=source,
                        predicate="MAY_REACH_EFFECT",
                        object_=target,
                        source_id=source_row[0],
                        producer_id=producer_id,
                        snapshot_run_id=snapshot_run_id,
                        truth_class="INFERRED",
                        attributes={
                            "flow_certainty": "MAY",
                            "path_entity_ids": list(next_path),
                            "policy_sha256": POLICY_SHA256,
                            "runtime_observed": False,
                            "vulnerability_claim": False,
                        },
                    )
                    possible_taint_paths += 1
                else:
                    queue.append((target, next_path))

    database_entities: dict[tuple[str, str], str] = {}
    connection_bindings: dict[tuple[str, str], str] = {}
    database_object_ids: set[str] = set()
    declared_database_objects: set[tuple[str, str]] = set()
    database_query_count = 0
    database_object_count = 0

    for item in fragment.files:
        path = item["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        module = item["module"]
        calls_by_span = {span_key(call["span"]): call for call in item["calls"]}
        for flow in item["data_flows"]:
            matching_calls = [
                calls_by_span.get(span_key(nested["span"]))
                for nested in flow["value"]["calls"]
            ]
            connections = [
                call
                for call in matching_calls
                if call is not None
                and declared_expression(path, call["expression"]) == "sqlite3.connect"
                and call["arguments"]["positional"]
                and isinstance(call["arguments"]["positional"][0]["literal"], str)
            ]
            if len(connections) != 1:
                continue
            call = connections[0]
            declared_path = call["arguments"]["positional"][0]["literal"]
            database_key = (path, declared_path)
            database_id = database_entities.get(database_key)
            if database_id is None:
                database_id = _entity_id(
                    "DATABASE_DECLARATION",
                    root_key,
                    f"{_artifact_id(root_key, path)}:{declared_path}",
                )
                database_entities[database_key] = database_id
                connection.execute(
                    "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        database_id,
                        "DATABASE_DECLARATION",
                        PurePosixPath(declared_path).name or declared_path,
                        f"sqlite:{path}:{declared_path}",
                        source_by_path[path],
                        "PROVEN",
                        operational_producer_id,
                        snapshot_run_id,
                        "LOCAL_SOURCE",
                        snapshot_run_id,
                        snapshot_run_id,
                        _json(
                            {
                                "declaration": "sqlite3.connect",
                                "declared_path": declared_path,
                                "existence": "NOT_OBSERVED",
                                "operational_policy": OPERATIONAL_POLICY_VERSION,
                                "operational_policy_sha256": OPERATIONAL_POLICY_SHA256,
                                "runtime_observed": False,
                            }
                        ),
                    ),
                )
            connection_bindings[(path, flow["target"])] = database_id
            owner_candidates = symbol_by_path_qname.get((path, flow["owner"]), [])
            owner = (
                owner_candidates[0]
                if len(owner_candidates) == 1
                else module_by_path[path]
            )
            _insert_relation(
                connection,
                subject=owner,
                predicate="MAY_CONNECT_TO",
                object_=database_id,
                source_id=source_by_path[path],
                producer_id=operational_producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="PROVEN",
                attributes={"runtime_observed": False, "span": call["span"]},
            )

        for call in item["calls"]:
            expression = call["expression"]
            head, separator, leaf = expression.rpartition(".")
            if not separator or leaf not in {"execute", "executemany"}:
                continue
            if not call["arguments"]["positional"]:
                continue
            parsed = parse_sql_literal(call["arguments"]["positional"][0]["literal"])
            if parsed is None:
                continue
            receiver = head.rsplit(".", 1)[-1]
            candidates = [
                (target, database_id)
                for (candidate_path, target), database_id in connection_bindings.items()
                if candidate_path == path
                and target.rsplit(".", 1)[-1] == receiver
                and (
                    target.rpartition(".")[0] == call["caller"]
                    or target.rpartition(".")[0] == module
                )
            ]
            exact_database_scope = len(candidates) == 1
            if exact_database_scope:
                database_id = candidates[0][1]
            else:
                unknown_key = (path, f"UNKNOWN_RECEIVER:{receiver}")
                database_id = database_entities.get(unknown_key)
                if database_id is None:
                    database_id = _entity_id(
                        "DATABASE_DECLARATION",
                        root_key,
                        f"{_artifact_id(root_key, path)}:UNKNOWN_RECEIVER:{receiver}",
                    )
                    database_entities[unknown_key] = database_id
                    connection.execute(
                        "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            database_id,
                            "DATABASE_DECLARATION",
                            receiver,
                            f"sqlite-possible:{path}:{receiver}",
                            source_by_path[path],
                            "INFERRED",
                            operational_producer_id,
                            snapshot_run_id,
                            "LOCAL_SOURCE",
                            snapshot_run_id,
                            snapshot_run_id,
                            _json(
                                {
                                    "database_scope": "UNKNOWN",
                                    "declaration": "literal-sql-execute-receiver",
                                    "existence": "NOT_OBSERVED",
                                    "operational_policy": OPERATIONAL_POLICY_VERSION,
                                    "operational_policy_sha256": OPERATIONAL_POLICY_SHA256,
                                    "receiver": receiver,
                                    "runtime_observed": False,
                                }
                            ),
                        ),
                    )
            owner_candidates = symbol_by_path_qname.get((path, call["caller"]), [])
            owner = (
                owner_candidates[0]
                if len(owner_candidates) == 1
                else module_by_path[path]
            )
            predicate = {
                "READ": "MAY_READ_DATA_OBJECT",
                "WRITE": "MAY_WRITE_DATA_OBJECT",
                "SCHEMA_WRITE": "DECLARES_SCHEMA_OBJECT",
            }[parsed["operation"]]
            for table in parsed["tables"]:
                object_id = _entity_id(
                    "DATA_OBJECT",
                    root_key,
                    f"{database_id}:table:{table}",
                )
                if object_id not in database_object_ids:
                    database_object_ids.add(object_id)
                    database_object_count += 1
                    connection.execute(
                        "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            object_id,
                            "DATA_OBJECT",
                            table,
                            f"{database_id}:table:{table}",
                            source_by_path[path],
                            "PROVEN" if exact_database_scope else "INFERRED",
                            operational_producer_id,
                            snapshot_run_id,
                            "LOCAL_SOURCE",
                            snapshot_run_id,
                            snapshot_run_id,
                            _json(
                                {
                                    "database_entity_id": database_id,
                                    "object_kind": "SQL_TABLE",
                                    "database_scope": "EXACT_DECLARATION"
                                    if exact_database_scope
                                    else "UNKNOWN",
                                    "runtime_observed": False,
                                    "sql_grammar": SQL_LITERAL_GRAMMAR,
                                }
                            ),
                        ),
                    )
                declaration_key = (database_id, object_id)
                if declaration_key not in declared_database_objects:
                    declared_database_objects.add(declaration_key)
                    _insert_relation(
                        connection,
                        subject=database_id,
                        predicate="DECLARES_DATA_OBJECT"
                        if exact_database_scope
                        else "POSSIBLY_CONTAINS_DATA_OBJECT",
                        object_=object_id,
                        source_id=source_by_path[path],
                        producer_id=operational_producer_id,
                        snapshot_run_id=snapshot_run_id,
                        attributes={
                            "database_scope": "EXACT_DECLARATION"
                            if exact_database_scope
                            else "UNKNOWN",
                            "runtime_observed": False,
                        },
                        truth_class="PROVEN" if exact_database_scope else "INFERRED",
                    )
                _insert_relation(
                    connection,
                    subject=owner,
                    predicate=predicate,
                    object_=object_id,
                    source_id=source_by_path[path],
                    producer_id=operational_producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "database_scope": "EXACT_DECLARATION"
                        if exact_database_scope
                        else "UNKNOWN",
                        "operation": parsed["operation"],
                        "runtime_observed": False,
                        "span": call["span"],
                        "sql_grammar": parsed["grammar"],
                        "statement_sha256": parsed["statement_sha256"],
                    },
                    truth_class="PROVEN" if exact_database_scope else "INFERRED",
                )
                fact_id = _insert_observation(
                    connection,
                    entity_id=object_id,
                    predicate="SQL_LITERAL_OPERATION",
                    value={
                        "operation": parsed["operation"],
                        "owner": call["caller"],
                        "runtime_observed": False,
                        "span": call["span"],
                        "sql_grammar": parsed["grammar"],
                        "statement_sha256": parsed["statement_sha256"],
                    },
                    source_id=source_by_path[path],
                    producer_id=operational_producer_id,
                    snapshot_run_id=snapshot_run_id,
                )
                _insert_location(
                    connection,
                    fact_id=fact_id,
                    source_id=source_by_path[path],
                    path=path,
                    span=call["span"],
                )
                database_query_count += 1

    build_asset_count = 0
    build_declaration_count = 0
    for record in build_records:
        path = record["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        role = build_asset_role(path)
        if role is None:
            continue
        asset_id = _entity_id("BUILD_ASSET", root_key, _artifact_id(root_key, path))
        attributes: dict[str, Any] = {
            "content_sha256": record["content_sha256"],
            "declared_role": role,
            "deployment_status": "NOT_EVALUATED",
            "operational_policy": OPERATIONAL_POLICY_VERSION,
            "operational_policy_sha256": OPERATIONAL_POLICY_SHA256,
            "runtime_observed": False,
        }
        declarations: list[dict[str, Any]] = []
        if PurePosixPath(path).name == "BUNDLE.json" or path.startswith(
            "deploy/releases/"
        ):
            try:
                raw = read_exact_artifact(root, record)
            except PythonMapError as exc:
                raise MapperError(str(exc)) from exc
            declarations = safe_build_declarations(path, raw)
            attributes["safe_declarations"] = declarations
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                asset_id,
                "BUILD_ASSET",
                PurePosixPath(path).name,
                f"{role}:{path}",
                source_by_path[path],
                "PROVEN",
                operational_producer_id,
                snapshot_run_id,
                "LOCAL_METADATA",
                snapshot_run_id,
                snapshot_run_id,
                _json(attributes),
            ),
        )
        _insert_relation(
            connection,
            subject=repository_id,
            predicate="DECLARES_BUILD_ASSET",
            object_=asset_id,
            source_id=source_by_path[path],
            producer_id=operational_producer_id,
            snapshot_run_id=snapshot_run_id,
            attributes={"deployment_status": "NOT_EVALUATED", "role": role},
        )
        for declaration in declarations:
            _insert_observation(
                connection,
                entity_id=asset_id,
                predicate="SAFE_BUILD_DECLARATION",
                value=declaration,
                source_id=source_by_path[path],
                producer_id=operational_producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            build_declaration_count += 1
        build_asset_count += 1

    test_candidate_count = 0
    static_test_target_count = 0
    for item in fragment.files:
        path = item["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        if not is_python_test_path(path):
            continue
        module_id = module_by_path[path]
        for definition in item["definitions"]:
            if not definition["name"].startswith("test") or definition["kind"] not in {
                "FUNCTION",
                "ASYNC_FUNCTION",
                "METHOD",
                "ASYNC_METHOD",
            }:
                continue
            candidates = symbol_by_path_qname.get(
                (path, definition["qualified_name"]), []
            )
            if len(candidates) != 1:
                continue
            symbol_id = candidates[0]
            test_id = _entity_id(
                "TEST_CASE_CANDIDATE",
                root_key,
                f"{symbol_id}:{span_key(definition['span'])}",
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    test_id,
                    "TEST_CASE_CANDIDATE",
                    definition["name"],
                    definition["qualified_name"],
                    source_by_path[path],
                    "INFERRED",
                    quality_producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "discovery_rule": "python-test-path-and-name",
                            "execution_status": "NOT_OBSERVED",
                            "framework": "NOT_PROVEN",
                            "policy": QUALITY_POLICY_VERSION,
                            "policy_sha256": QUALITY_POLICY_SHA256,
                            "span": definition["span"],
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=module_id,
                predicate="DECLARES_TEST_CANDIDATE",
                object_=test_id,
                source_id=source_by_path[path],
                producer_id=quality_producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="INFERRED",
                attributes={"execution_status": "NOT_OBSERVED"},
            )
            _insert_relation(
                connection,
                subject=test_id,
                predicate="CANDIDATE_FOR_SYMBOL",
                object_=symbol_id,
                source_id=source_by_path[path],
                producer_id=quality_producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="INFERRED",
            )
            targets = connection.execute(
                """SELECT object_id,attributes_json FROM relations
                   WHERE subject_id=? AND predicate='CALLS'
                   ORDER BY object_id,relation_id""",
                (symbol_id,),
            ).fetchall()
            for target_id, attributes_json in targets:
                _insert_relation(
                    connection,
                    subject=test_id,
                    predicate="STATICALLY_CALLS_TEST_TARGET",
                    object_=target_id,
                    source_id=source_by_path[path],
                    producer_id=quality_producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="PROVEN",
                    attributes={
                        "execution_status": "NOT_OBSERVED",
                        "underlying_call": json.loads(attributes_json),
                    },
                )
                static_test_target_count += 1
            imported_modules = connection.execute(
                """SELECT object_id,attributes_json FROM relations
                   WHERE subject_id=? AND predicate='IMPORTS'
                   ORDER BY object_id,relation_id""",
                (module_id,),
            ).fetchall()
            for target_id, attributes_json in imported_modules:
                _insert_relation(
                    connection,
                    subject=test_id,
                    predicate="STATICALLY_IMPORTS_TEST_TARGET",
                    object_=target_id,
                    source_id=source_by_path[path],
                    producer_id=quality_producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="INFERRED",
                    attributes={
                        "execution_status": "NOT_OBSERVED",
                        "underlying_import": json.loads(attributes_json),
                    },
                )
                static_test_target_count += 1
            test_candidate_count += 1

    quality_asset_count = 0
    coverage_file_count = 0
    coverage_source_links = 0
    for record in quality_records:
        path = record["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        role = quality_asset_role(path)
        if role is None:
            continue
        asset_id = _entity_id(
            "QUALITY_ARTIFACT", root_key, _artifact_id(root_key, path)
        )
        attributes: dict[str, Any] = {
            "content_sha256": record["content_sha256"],
            "execution_status": "NOT_EVALUATED",
            "policy": QUALITY_POLICY_VERSION,
            "policy_sha256": QUALITY_POLICY_SHA256,
            "role": role,
            "source_tree_binding": "UNKNOWN",
        }
        coverage = None
        if role == "COVERAGE_REPORT":
            try:
                raw = read_exact_artifact(root, record)
            except PythonMapError as exc:
                raise MapperError(str(exc)) from exc
            coverage = parse_coverage_json(raw)
            attributes["coverage_parse"] = "PASS" if coverage is not None else "REFUSED"
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                asset_id,
                "QUALITY_ARTIFACT",
                PurePosixPath(path).name,
                f"{role}:{path}",
                source_by_path[path],
                "PROVEN",
                quality_producer_id,
                snapshot_run_id,
                "LOCAL_METADATA",
                snapshot_run_id,
                snapshot_run_id,
                _json(attributes),
            ),
        )
        _insert_relation(
            connection,
            subject=repository_id,
            predicate="DECLARES_QUALITY_ARTIFACT",
            object_=asset_id,
            source_id=source_by_path[path],
            producer_id=quality_producer_id,
            snapshot_run_id=snapshot_run_id,
            attributes={"execution_status": "NOT_EVALUATED", "role": role},
        )
        if coverage is not None:
            for file_record in coverage["files"]:
                covered_path = PurePosixPath(file_record["path"]).as_posix()
                coverage_id = _entity_id(
                    "COVERAGE_FILE",
                    root_key,
                    f"{asset_id}:{covered_path}",
                )
                connection.execute(
                    "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        coverage_id,
                        "COVERAGE_FILE",
                        PurePosixPath(covered_path).name,
                        covered_path,
                        source_by_path[path],
                        "PROVEN",
                        quality_producer_id,
                        snapshot_run_id,
                        "LOCAL_METADATA",
                        snapshot_run_id,
                        snapshot_run_id,
                        _json(
                            {
                                "coverage_summary": file_record["summary"],
                                "execution_observed_by_report": True,
                                "freshness": "UNKNOWN",
                                "report_sha256": record["content_sha256"],
                                "source_tree_binding": "ABSENT_UNLESS_SEPARATELY_PROVEN",
                            }
                        ),
                    ),
                )
                _insert_relation(
                    connection,
                    subject=asset_id,
                    predicate="REPORTS_COVERAGE_FOR",
                    object_=coverage_id,
                    source_id=source_by_path[path],
                    producer_id=quality_producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={"freshness": "UNKNOWN"},
                )
                target_module = module_by_path.get(covered_path)
                if target_module is not None:
                    _insert_relation(
                        connection,
                        subject=coverage_id,
                        predicate="COVERAGE_PATH_MATCHES_SOURCE",
                        object_=target_module,
                        source_id=source_by_path[path],
                        producer_id=quality_producer_id,
                        snapshot_run_id=snapshot_run_id,
                        attributes={
                            "freshness": "UNKNOWN",
                            "source_tree_binding": False,
                        },
                    )
                    coverage_source_links += 1
                coverage_file_count += 1
        quality_asset_count += 1

    annotation_count = 0
    for item in fragment.files:
        path = item["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        for annotation in item["annotations"]:
            candidates = symbol_by_path_qname.get((path, annotation["subject"]), [])
            owner = candidates[0] if len(candidates) == 1 else module_by_path[path]
            fact_id = _insert_observation(
                connection,
                entity_id=owner,
                predicate="PYTHON_ANNOTATION",
                value=annotation,
                source_id=source_by_path[path],
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_by_path[path],
                path=path,
                span=annotation["span"],
            )
            annotation_count += 1

    type_relations = 0
    for symbol_id, definition in symbol_definition.items():
        if definition["kind"] != "CLASS":
            continue
        source = connection.execute(
            "SELECT source_id FROM entities WHERE entity_id=?", (symbol_id,)
        ).fetchone()[0]
        if source in reused_source_ids:
            continue
        path = connection.execute(
            "SELECT path FROM sources WHERE source_id=?", (source,)
        ).fetchone()[0]
        module = file_by_path[path]["module"]
        for base in definition["attributes"].get("bases", []):
            leaf = base.rsplit(".", 1)[-1]
            candidates = symbols_by_module_leaf.get((module, leaf), [])
            target = candidates[0] if len(candidates) == 1 else None
            if target is None:
                imported = import_aliases.get(path, {}).get(base) or import_aliases.get(
                    path, {}
                ).get(base.split(".", 1)[0])
                if (
                    imported
                    and connection.execute(
                        "SELECT 1 FROM entities WHERE entity_id=? AND entity_kind='PYTHON_SYMBOL'",
                        (imported,),
                    ).fetchone()
                ):
                    target = imported
            if target:
                _insert_relation(
                    connection,
                    subject=symbol_id,
                    predicate="INHERITS",
                    object_=target,
                    source_id=source,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "declared_base": base,
                        "resolution": "EXACT_LEXICAL_OR_IMPORT",
                    },
                )
                type_relations += 1
            else:
                _insert_observation(
                    connection,
                    entity_id=symbol_id,
                    predicate="DECLARED_BASE",
                    value={"base": base, "resolution": "UNRESOLVED_OR_EXTERNAL"},
                    source_id=source,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                )

    endpoint_count = 0
    all_entrypoints = [
        *(
            {"path": item["path"], **entry}
            for item in fragment.files
            for entry in item["entrypoints"]
        ),
        *fragment.project_entrypoints,
    ]
    for entry in sorted(
        all_entrypoints,
        key=lambda item: (
            item["path"],
            item["kind"],
            item["name"],
            _json(item.get("span")),
        ),
    ):
        path = entry["path"]
        if source_by_path[path] in reused_source_ids:
            continue
        endpoint_id = _entity_id(
            "ENTRYPOINT",
            root_key,
            f"{entry['kind']}:{path}:{entry['name']}:{_json(entry.get('span'))}",
        )
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                endpoint_id,
                "ENTRYPOINT",
                entry["name"],
                f"{entry['kind']}:{entry['name']}",
                source_by_path[path],
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json({key: value for key, value in entry.items() if key != "path"}),
            ),
        )
        owner = module_by_path.get(path, repository_id)
        _insert_relation(
            connection,
            subject=owner,
            predicate="DECLARES_ENTRYPOINT",
            object_=endpoint_id,
            source_id=source_by_path[path],
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
        )
        handler = entry.get("handler")
        target: str | None = None
        if isinstance(handler, str) and handler:
            if ":" in entry.get("target", ""):
                target_module_name, _, target_name = entry["target"].partition(":")
                candidates = symbols_by_module_leaf.get(
                    (target_module_name, target_name), []
                )
                target = candidates[0] if len(candidates) == 1 else None
            elif path in file_by_path:
                target = lexical_symbol(
                    path,
                    file_by_path[path]["module"],
                    file_by_path[path]["module"],
                    handler.rsplit(".", 1)[-1],
                )
        if target:
            _insert_relation(
                connection,
                subject=endpoint_id,
                predicate="HANDLED_BY",
                object_=target,
                source_id=source_by_path[path],
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
        endpoint_count += 1

    python_failures = [
        item for item in fragment.failures if "symbols" in item.get("maps", ())
    ]
    project_failures = [
        item for item in fragment.failures if item.get("maps") == ["api_events"]
    ]
    source_snapshot_failures = len(
        {
            item["path"]
            for item in fragment.failures
            if item.get("status") == "FAILED_SOURCE_SNAPSHOT"
        }
    )
    parse_failures = sum(
        item.get("status") == "FAILED_PARSE" for item in python_failures
    )
    failed = len(python_failures)
    covered = len(fragment.files)
    coverage_rows = []
    for map_id, fact_class in (
        ("symbols", "PYTHON_SYMBOL_AND_REFERENCE"),
        ("dependencies", "PYTHON_IMPORT"),
        ("types", "PYTHON_DECLARED_TYPE"),
        ("api_events", "PYTHON_CLI_ENTRYPOINT"),
        ("calls", "PYTHON_STATIC_CALL"),
        ("control_flow", "PYTHON_STRUCTURED_CONTROL_FLOW"),
        ("data_flow_taint", "PYTHON_STATIC_MAY_FLOW"),
        ("security_capabilities", "PYTHON_POSSIBLE_SECURITY_EFFECT"),
    ):
        map_failures = [
            item for item in fragment.failures if map_id in item.get("maps", ())
        ]
        source_total = len(python_records) + (
            len(project_records) if map_id == "api_events" else 0
        )
        sources_covered = source_total - len(map_failures)
        limitations: dict[str, Any] = {
            "failures": map_failures,
            "language": "python",
            "namespace_packages": "PARTIAL",
            "dynamic_resolution": "UNSUPPORTED",
        }
        if map_id == "calls":
            limitations.update(
                {
                    "runtime_dispatch": "UNSUPPORTED",
                    "monkey_patching": "UNSUPPORTED",
                }
            )
        elif map_id == "control_flow":
            limitations.update(
                {
                    "implicit_exception_edges": "UNSUPPORTED",
                    "runtime_dispatch": "UNSUPPORTED",
                    "supported_boundary": "EXPLICIT_STRUCTURED_AST",
                }
            )
        elif map_id == "data_flow_taint":
            limitations.update(
                {
                    "clean_result_claim": "FORBIDDEN",
                    "flow_certainty": "MAY",
                    "interprocedural_summaries": "UNSUPPORTED",
                    "policy_sha256": POLICY_SHA256,
                    "runtime_observed": False,
                }
            )
        elif map_id == "security_capabilities":
            limitations.update(
                {
                    "authority_evaluated": False,
                    "capability_granted_by_map": False,
                    "policy_sha256": POLICY_SHA256,
                    "runtime_observed": False,
                    "vulnerability_claim": False,
                }
            )
        coverage_rows.append(
            (
                producer_id,
                map_id,
                fact_class,
                "semantic-eligible-python",
                "COVERED" if not map_failures else "PARTIAL",
                source_total,
                sources_covered,
                len(map_failures),
                0,
                0,
                _json(limitations),
            )
        )
    connection.executemany(
        "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)", coverage_rows
    )
    connection.executemany(
        "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            (
                operational_producer_id,
                "database_lineage",
                "PYTHON_LITERAL_SQL_OPERATION",
                "semantic-eligible-python",
                "PARTIAL",
                len(python_records),
                len(python_records) - failed,
                failed,
                0,
                0,
                _json(
                    {
                        "database_existence_observed": False,
                        "dynamic_sql": "UNSUPPORTED",
                        "orms": "UNSUPPORTED",
                        "row_content_read": False,
                        "runtime_schema": "UNSUPPORTED",
                        "sql_grammar": SQL_LITERAL_GRAMMAR,
                        "unknown_database_scope": "PRESERVED_INFERRED",
                    }
                ),
            ),
            (
                operational_producer_id,
                "build_deployment",
                "BUILD_AND_DEPLOYMENT_DECLARATION",
                "safe-build-path-policy",
                "PARTIAL",
                len(build_records),
                len(build_records),
                0,
                0,
                0,
                _json(
                    {
                        "artifact_existence_observed": False,
                        "deployment_status_evaluated": False,
                        "policy_sha256": OPERATIONAL_POLICY_SHA256,
                        "private_evidence_read": False,
                        "safe_json_projection_only": True,
                    }
                ),
            ),
        ),
    )
    connection.executemany(
        "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            (
                quality_producer_id,
                "tests_coverage",
                "PYTHON_TEST_CANDIDATE_AND_COVERAGE_ARTIFACT",
                "semantic-eligible-python-and-coverage-json",
                "PARTIAL",
                len(python_records) + len(quality_records),
                len(python_records) + len(quality_records) - failed,
                failed,
                0,
                0,
                _json(
                    {
                        "coverage_source_tree_binding": "UNKNOWN",
                        "execution_status_from_test_name": "NOT_OBSERVED",
                        "framework_discovery": "CONVENTION_ONLY",
                        "policy_sha256": QUALITY_POLICY_SHA256,
                    }
                ),
            ),
            (
                quality_producer_id,
                "quality_findings",
                "QUALITY_ARTIFACT_METADATA",
                "safe-quality-artifact-path-policy",
                "PARTIAL",
                len(quality_records),
                len(quality_records),
                0,
                0,
                0,
                _json(
                    {
                        "finding_content_parsed": False,
                        "result_status_evaluated": False,
                        "sarif_content_read": False,
                        "source_tree_binding": "UNKNOWN",
                    }
                ),
            ),
        ),
    )
    connection.executemany(
        "INSERT INTO map_views VALUES (?,?,?,?,?)",
        (
            (
                "symbols",
                "1",
                "AVAILABLE_PYTHON",
                _json(["PYTHON_MODULE", "PYTHON_SYMBOL", "PYTHON_REFERENCE"]),
                _json({"query": "name-path-qualified-name", "exact_spans": True}),
            ),
            (
                "dependencies",
                "1",
                "AVAILABLE_PYTHON_PARTIAL",
                _json(["PYTHON_IMPORT", "IMPORTS"]),
                _json({"reverse_impact": True, "unresolved_preserved": True}),
            ),
            (
                "types",
                "1",
                "AVAILABLE_PYTHON_PARTIAL",
                _json(["DECLARED_BASE", "INHERITS", "ANNOTATION"]),
                _json({"source_declared_only": True, "compiler_types": False}),
            ),
            (
                "api_events",
                "1",
                "AVAILABLE_PYTHON_CLI_PARTIAL",
                _json(["ENTRYPOINT", "DECLARES_ENTRYPOINT", "HANDLED_BY"]),
                _json({"argparse": True, "project_scripts": True, "http": False}),
            ),
            (
                "calls",
                "1",
                "AVAILABLE_PYTHON_STATIC_PARTIAL",
                _json(["PYTHON_CALL", "CALLS"]),
                _json(
                    {
                        "exact_lexical_and_import_resolution": True,
                        "runtime_dispatch": False,
                        "unresolved_preserved": True,
                    }
                ),
            ),
            (
                "control_flow",
                "1",
                "AVAILABLE_PYTHON_STRUCTURED_PARTIAL",
                _json(
                    [
                        "CONTROL_NODE",
                        "HAS_CONTROL_NODE",
                        "BRANCH_TRUE",
                        "BRANCH_FALSE",
                        "LOOP_BODY",
                        "LOOP_EXIT",
                    ]
                ),
                _json(
                    {
                        "explicit_structured_branches": True,
                        "implicit_exception_edges": False,
                        "runtime_dispatch": False,
                    }
                ),
            ),
            (
                "data_flow_taint",
                "1",
                "AVAILABLE_PYTHON_STATIC_MAY_FLOW_PARTIAL",
                _json(
                    [
                        "DATA_SOURCE",
                        "PYTHON_STATIC_DATA_FLOW",
                        "MAY_FLOW_TO",
                        "MAY_REACH_EFFECT",
                    ]
                ),
                _json(
                    {
                        "clean_result_claim": False,
                        "flow_certainty": "MAY",
                        "policy": FLOW_POLICY_VERSION,
                        "policy_sha256": POLICY_SHA256,
                    }
                ),
            ),
            (
                "security_capabilities",
                "1",
                "AVAILABLE_PYTHON_EFFECT_SURFACE_PARTIAL",
                _json(
                    [
                        "SECURITY_EFFECT",
                        "MAY_CAUSE_EFFECT",
                        "MAY_READ_DATA_SOURCE",
                        "MAY_REACH_EFFECT",
                    ]
                ),
                _json(
                    {
                        "authority_evaluated": False,
                        "capability_granted_by_map": False,
                        "policy": FLOW_POLICY_VERSION,
                        "policy_sha256": POLICY_SHA256,
                        "runtime_observed": False,
                    }
                ),
            ),
            (
                "database_lineage",
                "1",
                "AVAILABLE_PYTHON_LITERAL_SQL_PARTIAL",
                _json(
                    [
                        "DATABASE_DECLARATION",
                        "DATA_OBJECT",
                        "MAY_CONNECT_TO",
                        "MAY_READ_DATA_OBJECT",
                        "MAY_WRITE_DATA_OBJECT",
                        "DECLARES_SCHEMA_OBJECT",
                    ]
                ),
                _json(
                    {
                        "dynamic_sql": False,
                        "exact_literal_operations": True,
                        "row_content_read": False,
                        "runtime_observed": False,
                        "sql_grammar": SQL_LITERAL_GRAMMAR,
                    }
                ),
            ),
            (
                "build_deployment",
                "1",
                "AVAILABLE_SAFE_DECLARATION_PARTIAL",
                _json(
                    [
                        "BUILD_ASSET",
                        "DECLARES_BUILD_ASSET",
                        "SAFE_BUILD_DECLARATION",
                    ]
                ),
                _json(
                    {
                        "deployment_status_evaluated": False,
                        "private_evidence_read": False,
                        "runtime_observed": False,
                        "safe_json_projection_only": True,
                    }
                ),
            ),
            (
                "tests_coverage",
                "1",
                "AVAILABLE_STATIC_TEST_AND_COVERAGE_ARTIFACT_PARTIAL",
                _json(
                    [
                        "TEST_CASE_CANDIDATE",
                        "STATICALLY_CALLS_TEST_TARGET",
                        "STATICALLY_IMPORTS_TEST_TARGET",
                        "COVERAGE_FILE",
                        "COVERAGE_PATH_MATCHES_SOURCE",
                    ]
                ),
                _json(
                    {
                        "coverage_freshness": "UNKNOWN_UNLESS_BOUND",
                        "test_execution_observed": False,
                        "test_framework_proven": False,
                    }
                ),
            ),
            (
                "quality_findings",
                "1",
                "AVAILABLE_ARTIFACT_AND_SELF_HASHED_RECEIPT_CLAIM_PARTIAL",
                _json(
                    [
                        "QUALITY_ARTIFACT",
                        "DECLARES_QUALITY_ARTIFACT",
                        "QUALITY_CHECK_CLAIM",
                        "DOCUMENT_CLAIMS_QUALITY_CHECK",
                        "RECEIPT_REPORTS_QUALITY_STATUS",
                        "RECEIPT_COMMAND_LEXICALLY_REFERENCES_CURRENT_MODULE",
                    ]
                ),
                _json(
                    {
                        "finding_content_parsed": False,
                        "receipt_reported_status_evaluated": True,
                        "execution_independently_verified": False,
                        "receipt_command_current_path_match_proves_execution_source": False,
                        "source_tree_binding": "UNKNOWN",
                    }
                ),
            ),
        ),
    )

    def fact_count(table: str, clause: str, parameters: Sequence[Any] = ()) -> int:
        return int(
            connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {clause}", parameters
            ).fetchone()[0]
        )

    reference_count = sum(len(item["references"]) for item in fragment.files)
    resolved_references = fact_count(
        "observations",
        "predicate='PYTHON_REFERENCE' AND json_extract(value_json,'$.target_entity_id') IS NOT NULL",
    )
    import_count = sum(len(item["imports"]) for item in fragment.files)
    unresolved_imports = fact_count(
        "observations",
        "predicate='PYTHON_IMPORT' AND json_extract(value_json,'$.target_module_id') IS NULL",
    )
    call_count = sum(len(item["calls"]) for item in fragment.files)
    resolved_calls = fact_count("relations", "predicate='CALLS'")
    control_flow_count = sum(len(item["control_flows"]) for item in fragment.files)
    control_node_count = fact_count("entities", "entity_kind='CONTROL_NODE'")
    control_edge_count = fact_count(
        "relations",
        """subject_id IN (SELECT entity_id FROM entities WHERE entity_kind='CONTROL_NODE')
           AND object_id IN (SELECT entity_id FROM entities WHERE entity_kind='CONTROL_NODE')""",
    )
    data_source_count = fact_count("entities", "entity_kind='DATA_SOURCE'")
    security_effect_count = fact_count("entities", "entity_kind='SECURITY_EFFECT'")
    static_flow_count = fact_count("relations", "predicate='MAY_FLOW_TO'")
    possible_taint_paths = fact_count("relations", "predicate='MAY_REACH_EFFECT'")
    database_object_count = fact_count("entities", "entity_kind='DATA_OBJECT'")
    database_query_count = fact_count(
        "observations", "predicate='SQL_LITERAL_OPERATION'"
    )
    build_asset_count = fact_count("entities", "entity_kind='BUILD_ASSET'")
    build_declaration_count = fact_count(
        "observations", "predicate='SAFE_BUILD_DECLARATION'"
    )
    test_candidate_count = fact_count("entities", "entity_kind='TEST_CASE_CANDIDATE'")
    static_test_target_count = fact_count(
        "relations",
        "predicate IN ('STATICALLY_CALLS_TEST_TARGET','STATICALLY_IMPORTS_TEST_TARGET')",
    )
    quality_asset_count = fact_count("entities", "entity_kind='QUALITY_ARTIFACT'")
    coverage_file_count = fact_count("entities", "entity_kind='COVERAGE_FILE'")
    coverage_source_links = fact_count(
        "relations", "predicate='COVERAGE_PATH_MATCHES_SOURCE'"
    )
    annotation_count = fact_count("observations", "predicate='PYTHON_ANNOTATION'")
    type_relations = fact_count("relations", "predicate='INHERITS'")
    endpoint_count = fact_count("entities", "entity_kind='ENTRYPOINT'")
    database_entities_count = fact_count(
        "entities", "entity_kind='DATABASE_DECLARATION'"
    )
    return {
        **fragment_counts,
        "python_files": covered,
        "python_parse_failures": parse_failures,
        "python_source_snapshot_failures": source_snapshot_failures,
        "python_project_manifest_failures": len(project_failures),
        "python_modules": len(fragment.files),
        "python_symbols": len(definitions),
        "python_references": reference_count,
        "python_references_resolved": resolved_references,
        "python_imports": import_count,
        "python_imports_unresolved_or_external": unresolved_imports,
        "python_type_relations": type_relations,
        "python_annotations": annotation_count,
        "python_entrypoints": endpoint_count,
        "python_calls": call_count,
        "python_calls_resolved": resolved_calls,
        "python_control_flows": control_flow_count,
        "python_control_nodes": control_node_count,
        "python_control_edges": control_edge_count,
        "python_data_sources": data_source_count,
        "python_security_effects": security_effect_count,
        "python_static_flows": static_flow_count,
        "python_possible_taint_paths": possible_taint_paths,
        "python_declared_databases": database_entities_count,
        "python_declared_data_objects": database_object_count,
        "python_literal_sql_operations": database_query_count,
        "build_assets": build_asset_count,
        "safe_build_declarations": build_declaration_count,
        "python_test_candidates": test_candidate_count,
        "static_test_targets": static_test_target_count,
        "quality_assets": quality_asset_count,
        "coverage_files": coverage_file_count,
        "coverage_source_links": coverage_source_links,
        "python_sources": len(records_by_path),
    }


def _resolved_shell_dependency(
    script_path: str, literal: str, available_paths: set[str]
) -> tuple[str | None, str]:
    candidate = PurePosixPath(literal)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, "DYNAMIC_OR_OUTSIDE_ROOT"
    normalized = candidate.as_posix().removeprefix("./")
    possibilities = [normalized]
    parent = PurePosixPath(script_path).parent
    relative = (parent / normalized).as_posix()
    if relative not in possibilities:
        possibilities.append(relative)
    matches = sorted(item for item in possibilities if item in available_paths)
    if len(matches) == 1:
        return matches[0], "EXACT_INVENTORY_PATH"
    if len(matches) > 1:
        return None, "AMBIGUOUS_INVENTORY_PATH"
    return None, "UNRESOLVED_LITERAL"


def _build_shell_maps(
    connection: sqlite3.Connection,
    *,
    inventory: NavigationRun,
    root_key: str,
    producer_id: str,
    snapshot_run_id: str,
) -> dict[str, int]:
    """Add Bash syntax facts to the shared mapper without executing scripts."""

    inventory_connection = _inventory_connection(inventory)
    try:
        records = [
            dict(row)
            for row in inventory_connection.execute(
                """SELECT * FROM files
                   WHERE kind='regular' AND semantic_eligible=1 AND suffix='.sh'
                   ORDER BY path"""
            )
        ]
        available_paths = {
            row[0]
            for row in inventory_connection.execute(
                "SELECT path FROM files WHERE kind='regular' ORDER BY path"
            )
        }
    finally:
        inventory_connection.close()
    root = Path(inventory.manifest["root"]["path"]).resolve(strict=True)
    backend = dict(shell_backend_identity())
    failures: list[dict[str, str]] = []
    fragments: list[tuple[Mapping[str, Any], Mapping[str, Any], str]] = []
    for record in records:
        path = record["path"]
        source_id = f"source:artifact:{_fact_id([root_key, path, record['content_sha256'] or ''])}"
        connection.execute(
            "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?)",
            (
                source_id,
                "ARTIFACT",
                path,
                _source_identity(record),
                "LOCAL_SOURCE",
                _json(
                    {
                        "content_sha256": record["content_sha256"],
                        "inventory_run_id": snapshot_run_id,
                        "semantic_reason": record["semantic_reason"],
                    }
                ),
            ),
        )
        try:
            raw = read_exact_artifact(root, record)
            fragment = extract_shell_file_fragment(path, raw)
        except (PythonMapError, ShellMapError) as exc:
            failures.append({"path": path, "reason": str(exc)})
            continue
        fragments.append((record, fragment, source_id))

    function_count = 0
    variable_count = 0
    reference_count = 0
    resolved_reference_count = 0
    command_count = 0
    function_call_count = 0
    dependency_count = 0
    resolved_dependency_count = 0
    entrypoint_count = 0
    for record, fragment, source_id in fragments:
        path = fragment["path"]
        script_id = _entity_id("SHELL_SCRIPT", root_key, path)
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                script_id,
                "SHELL_SCRIPT",
                PurePosixPath(path).name,
                path,
                source_id,
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "backend": backend,
                        "content_sha256": record["content_sha256"],
                        "executable": bool(record["mode"] & 0o111),
                        "language": "bash",
                        "shebang": fragment["shebang"],
                        "tree_descendant_count": fragment["tree_descendant_count"],
                        "tree_root_type": fragment["tree_root_type"],
                    }
                ),
            ),
        )
        function_by_name: dict[str, str] = {}
        function_groups: dict[str, list[Mapping[str, Any]]] = {}
        for definition in fragment["functions"]:
            function_groups.setdefault(definition["name"], []).append(definition)
        for name, definitions in sorted(function_groups.items()):
            symbol_id = _entity_id("SHELL_SYMBOL", root_key, f"{path}:FUNCTION:{name}")
            function_by_name[name] = symbol_id
            truth = "PROVEN" if len(definitions) == 1 else "CONFLICT"
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    symbol_id,
                    "SHELL_SYMBOL",
                    name,
                    f"{path}::function:{name}",
                    source_id,
                    truth,
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "definition_count": len(definitions),
                            "definitions": [
                                {"path": path, "span": item["span"]}
                                for item in definitions
                            ],
                            "language": "bash",
                            "symbol_kind": "FUNCTION",
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=script_id,
                predicate="DEFINES",
                object_=symbol_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class=truth,
            )
            for definition in definitions:
                fact_id = _insert_observation(
                    connection,
                    entity_id=symbol_id,
                    predicate="SHELL_DEFINITION",
                    value={
                        "path": path,
                        "span": definition["span"],
                        "symbol_kind": "FUNCTION",
                    },
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class=truth,
                )
                _insert_location(
                    connection,
                    fact_id=fact_id,
                    source_id=source_id,
                    path=path,
                    span=definition["span"],
                )
            function_count += 1

        variable_groups: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for definition in fragment["assignments"]:
            scope = definition["scope"]
            if definition["assignment_kind"] == "COMMAND_ENVIRONMENT":
                scope = f"COMMAND@{definition['span']['line_start']}:{definition['span']['column_start']}"
            variable_groups.setdefault((scope, definition["name"]), []).append(
                definition
            )
        variable_by_scope_name: dict[tuple[str, str], str] = {}
        for (scope, name), definitions in sorted(variable_groups.items()):
            symbol_id = _entity_id(
                "SHELL_SYMBOL", root_key, f"{path}:VARIABLE:{scope}:{name}"
            )
            variable_by_scope_name[(scope, name)] = symbol_id
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    symbol_id,
                    "SHELL_SYMBOL",
                    name,
                    f"{path}::{scope.lower()}::variable:{name}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "assignment_kinds": sorted(
                                {item["assignment_kind"] for item in definitions}
                            ),
                            "definition_count": len(definitions),
                            "definitions": [
                                {"path": path, "span": item["span"]}
                                for item in definitions
                            ],
                            "language": "bash",
                            "scope": scope,
                            "symbol_kind": "VARIABLE",
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=function_by_name.get(scope, script_id),
                predicate="DEFINES",
                object_=symbol_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            for definition in definitions:
                fact_id = _insert_observation(
                    connection,
                    entity_id=symbol_id,
                    predicate="SHELL_DEFINITION",
                    value={
                        "assignment_kind": definition["assignment_kind"],
                        "path": path,
                        "scope": definition["scope"],
                        "span": definition["span"],
                        "symbol_kind": "VARIABLE",
                    },
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                )
                _insert_location(
                    connection,
                    fact_id=fact_id,
                    source_id=source_id,
                    path=path,
                    span=definition["span"],
                )
            variable_count += 1

        for reference in fragment["references"]:
            scope = reference["scope"]
            candidates = [
                variable_by_scope_name.get((scope, reference["name"])),
                variable_by_scope_name.get(("SCRIPT", reference["name"])),
            ]
            targets = [item for item in dict.fromkeys(candidates) if item is not None]
            target = targets[0] if len(targets) == 1 else None
            resolution = (
                "SAME_SCRIPT_DECLARATION"
                if target is not None
                else "UNRESOLVED_OR_ENVIRONMENT"
            )
            fact_id = _insert_observation(
                connection,
                entity_id=target or script_id,
                predicate="SHELL_REFERENCE",
                value={
                    "name": reference["name"],
                    "path": path,
                    "resolution": resolution,
                    "scope": scope,
                    "span": reference["span"],
                    "target_entity_id": target,
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="INFERRED" if target is not None else "PROVEN",
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_id,
                path=path,
                span=reference["span"],
            )
            reference_count += 1
            resolved_reference_count += int(target is not None)

        command_groups: dict[str, list[Mapping[str, Any]]] = {}
        for command in fragment["commands"]:
            command_groups.setdefault(command["name"], []).append(command)
        for name, commands in sorted(command_groups.items()):
            command_id = _entity_id("SHELL_COMMAND", root_key, f"{path}:{name}")
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    command_id,
                    "SHELL_COMMAND",
                    name,
                    f"{path}::command:{name}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "invocation_count": len(commands),
                            "language": "bash",
                            "literal_name": not any(
                                item["dynamic"] for item in commands
                            ),
                        }
                    ),
                ),
            )
            for command in commands:
                owner = function_by_name.get(command["scope"], script_id)
                _insert_relation(
                    connection,
                    subject=owner,
                    predicate="INVOKES_COMMAND",
                    object_=command_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={"span": command["span"]},
                )
                fact_id = _insert_observation(
                    connection,
                    entity_id=command_id,
                    predicate="SHELL_COMMAND_INVOCATION",
                    value={
                        "dynamic": command["dynamic"],
                        "path": path,
                        "scope": command["scope"],
                        "span": command["span"],
                    },
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                )
                _insert_location(
                    connection,
                    fact_id=fact_id,
                    source_id=source_id,
                    path=path,
                    span=command["span"],
                )
                local_target = function_by_name.get(name)
                if local_target is not None and not command["dynamic"]:
                    _insert_relation(
                        connection,
                        subject=owner,
                        predicate="CALLS",
                        object_=local_target,
                        source_id=source_id,
                        producer_id=producer_id,
                        snapshot_run_id=snapshot_run_id,
                        attributes={
                            "language": "bash",
                            "resolution": "SAME_SCRIPT_FUNCTION_NAME",
                            "span": command["span"],
                        },
                        truth_class="INFERRED",
                    )
                    function_call_count += 1
                for literal in command["script_dependencies"]:
                    resolved, resolution = _resolved_shell_dependency(
                        path, literal, available_paths
                    )
                    dependency_id = _entity_id(
                        "SHELL_DEPENDENCY", root_key, f"{path}:{literal}"
                    )
                    connection.execute(
                        "INSERT OR IGNORE INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            dependency_id,
                            "SHELL_DEPENDENCY",
                            PurePosixPath(literal).name,
                            f"{path}::dependency:{literal}",
                            source_id,
                            "PROVEN",
                            producer_id,
                            snapshot_run_id,
                            "LOCAL_SOURCE",
                            snapshot_run_id,
                            snapshot_run_id,
                            _json(
                                {
                                    "language": "bash",
                                    "literal": literal,
                                    "resolution": resolution,
                                    "resolved_path": resolved,
                                }
                            ),
                        ),
                    )
                    _insert_relation(
                        connection,
                        subject=script_id,
                        predicate="DEPENDS_ON_LITERAL",
                        object_=dependency_id,
                        source_id=source_id,
                        producer_id=producer_id,
                        snapshot_run_id=snapshot_run_id,
                        attributes={
                            "literal": literal,
                            "resolution": resolution,
                            "resolved_path": resolved,
                            "span": command["span"],
                        },
                    )
                    dependency_count += 1
                    resolved_dependency_count += int(resolved is not None)
            command_count += 1

        entrypoint_id = _entity_id("ENTRYPOINT", root_key, f"SHELL_SCRIPT:{path}")
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                entrypoint_id,
                "ENTRYPOINT",
                PurePosixPath(path).name,
                f"SHELL_SCRIPT:{path}",
                source_id,
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "executable": bool(record["mode"] & 0o111),
                        "kind": "SHELL_SCRIPT",
                        "path": path,
                        "shebang": fragment["shebang"],
                    }
                ),
            ),
        )
        _insert_relation(
            connection,
            subject=script_id,
            predicate="DECLARES_ENTRYPOINT",
            object_=entrypoint_id,
            source_id=source_id,
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
        )
        entrypoint_count += 1

    covered = len(fragments)
    failed = len(failures)
    for map_id, fact_class in (
        ("symbols", "BASH_SYMBOL_AND_REFERENCE"),
        ("dependencies", "BASH_LITERAL_SCRIPT_DEPENDENCY"),
        ("api_events", "BASH_SCRIPT_ENTRYPOINT"),
        ("calls", "BASH_COMMAND_AND_STATIC_FUNCTION_CALL"),
    ):
        connection.execute(
            "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                producer_id,
                map_id,
                fact_class,
                "semantic-eligible-dot-sh",
                "COVERED" if not failures else "PARTIAL",
                len(records),
                covered,
                failed,
                0,
                0,
                _json(
                    {
                        "backend": backend,
                        "dynamic_command_resolution": "UNSUPPORTED",
                        "failures": failures,
                        "language": "bash",
                        "name_resolution": "SAME_SCRIPT_INFERRED",
                        "scripts_without_dot_sh": "UNSUPPORTED",
                        "source_execution": False,
                    }
                ),
            ),
        )
    connection.execute(
        """UPDATE map_views
           SET status='AVAILABLE_PYTHON_AND_BASH_PARTIAL',
               required_fact_classes_json=?, query_contract_json=?
           WHERE map_id='symbols'""",
        (
            _json(
                [
                    "PYTHON_MODULE",
                    "PYTHON_SYMBOL",
                    "PYTHON_REFERENCE",
                    "SHELL_SCRIPT",
                    "SHELL_SYMBOL",
                    "SHELL_REFERENCE",
                ]
            ),
            _json(
                {
                    "exact_spans": True,
                    "languages": ["bash", "python"],
                    "query": "name-path-qualified-name",
                }
            ),
        ),
    )
    connection.execute(
        """UPDATE map_views
           SET status='AVAILABLE_PYTHON_AND_BASH_PARTIAL',
               required_fact_classes_json=?, query_contract_json=?
           WHERE map_id='dependencies'""",
        (
            _json(["PYTHON_IMPORT", "IMPORTS", "SHELL_DEPENDENCY"]),
            _json(
                {
                    "literal_shell_dependencies": True,
                    "reverse_impact": True,
                    "unresolved_preserved": True,
                }
            ),
        ),
    )
    connection.execute(
        """UPDATE map_views
           SET status='AVAILABLE_PYTHON_AND_BASH_ENTRYPOINT_PARTIAL',
               required_fact_classes_json=?, query_contract_json=?
           WHERE map_id='api_events'""",
        (
            _json(["ENTRYPOINT", "DECLARES_ENTRYPOINT", "HANDLED_BY"]),
            _json(
                {
                    "argparse": True,
                    "bash_scripts": True,
                    "http": False,
                    "project_scripts": True,
                }
            ),
        ),
    )
    connection.execute(
        """UPDATE map_views
           SET status='AVAILABLE_PYTHON_AND_BASH_STATIC_PARTIAL',
               required_fact_classes_json=?, query_contract_json=?
           WHERE map_id='calls'""",
        (
            _json(["PYTHON_CALL", "CALLS", "SHELL_COMMAND", "INVOKES_COMMAND"]),
            _json(
                {
                    "bash_same_script_function_resolution": True,
                    "exact_lexical_and_import_resolution": True,
                    "runtime_dispatch": False,
                    "unresolved_preserved": True,
                }
            ),
        ),
    )
    return {
        "shell_files": covered,
        "shell_parse_failures": failed,
        "shell_scripts": covered,
        "shell_symbols": function_count + variable_count,
        "shell_functions": function_count,
        "shell_variables": variable_count,
        "shell_references": reference_count,
        "shell_references_resolved": resolved_reference_count,
        "shell_commands": command_count,
        "shell_function_calls": function_call_count,
        "shell_dependencies": dependency_count,
        "shell_dependencies_resolved": resolved_dependency_count,
        "shell_entrypoints": entrypoint_count,
    }


def _resolved_javascript_import(
    module_path: str, specifier: str, available_paths: set[str]
) -> tuple[str | None, str]:
    if specifier.startswith(("node:", "#")) or not specifier.startswith("."):
        return None, "EXTERNAL_PACKAGE"
    candidate = PurePosixPath(specifier)
    if candidate.is_absolute():
        return None, "DYNAMIC_OR_OUTSIDE_ROOT"
    parent = PurePosixPath(module_path).parent
    base = posixpath.normpath((parent / candidate).as_posix())
    if base == ".." or base.startswith("../") or base.startswith("/"):
        return None, "DYNAMIC_OR_OUTSIDE_ROOT"
    possibilities = [base]
    if PurePosixPath(base).suffix not in JAVASCRIPT_SUFFIXES:
        possibilities.extend(
            f"{base}{suffix}" for suffix in sorted(JAVASCRIPT_SUFFIXES)
        )
        possibilities.extend(
            f"{base}/index{suffix}" for suffix in sorted(JAVASCRIPT_SUFFIXES)
        )
    matches = sorted(set(possibilities) & available_paths)
    if len(matches) == 1:
        return matches[0], "EXACT_INVENTORY_PATH"
    if len(matches) > 1:
        return None, "AMBIGUOUS_INVENTORY_PATH"
    return None, "UNRESOLVED_LITERAL"


def _javascript_span_key(span: Mapping[str, Any]) -> str:
    return ":".join(
        str(span[key])
        for key in ("byte_start", "byte_end", "line_start", "column_start")
    )


def _build_javascript_maps(
    connection: sqlite3.Connection,
    *,
    inventory: NavigationRun,
    root_key: str,
    producer_id: str,
    snapshot_run_id: str,
) -> dict[str, int]:
    """Add JS/TS syntax facts to the shared mapper without executing source."""

    inventory_connection = _inventory_connection(inventory)
    try:
        placeholders = ",".join("?" for _ in JAVASCRIPT_SUFFIXES)
        records = [
            dict(row)
            for row in inventory_connection.execute(
                f"""SELECT * FROM files
                    WHERE kind='regular' AND semantic_eligible=1
                      AND suffix IN ({placeholders}) ORDER BY path""",
                tuple(sorted(JAVASCRIPT_SUFFIXES)),
            )
        ]
        available_paths = {
            row[0]
            for row in inventory_connection.execute(
                "SELECT path FROM files WHERE kind='regular' ORDER BY path"
            )
        }
    finally:
        inventory_connection.close()
    root = Path(inventory.manifest["root"]["path"]).resolve(strict=True)
    backend = dict(javascript_backend_identity())
    failures: list[dict[str, str]] = []
    fragments: list[tuple[Mapping[str, Any], Mapping[str, Any], str]] = []
    for record in records:
        path = record["path"]
        source_id = f"source:artifact:{_fact_id([root_key, path, record['content_sha256'] or ''])}"
        connection.execute(
            "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?)",
            (
                source_id,
                "ARTIFACT",
                path,
                _source_identity(record),
                "LOCAL_SOURCE",
                _json(
                    {
                        "content_sha256": record["content_sha256"],
                        "inventory_run_id": snapshot_run_id,
                        "semantic_reason": record["semantic_reason"],
                    }
                ),
            ),
        )
        try:
            raw = read_exact_artifact(root, record)
            fragment = extract_javascript_file_fragment(path, raw)
        except (PythonMapError, JavaScriptMapError) as exc:
            failures.append({"path": path, "reason": str(exc)})
            continue
        fragments.append((record, fragment, source_id))

    module_by_path: dict[str, str] = {}
    for record, fragment, source_id in fragments:
        path = fragment["path"]
        module_id = _entity_id("JAVASCRIPT_MODULE", root_key, path)
        module_by_path[path] = module_id
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                module_id,
                "JAVASCRIPT_MODULE",
                PurePosixPath(path).name,
                path,
                source_id,
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "backend": backend,
                        "content_sha256": record["content_sha256"],
                        "executable": bool(record["mode"] & 0o111),
                        "language": fragment["language"],
                        "shebang": fragment["shebang"],
                        "tree_descendant_count": fragment["tree_descendant_count"],
                        "tree_root_type": fragment["tree_root_type"],
                    }
                ),
            ),
        )

    symbol_count = 0
    reference_count = 0
    resolved_reference_count = 0
    import_count = 0
    resolved_import_count = 0
    call_count = 0
    resolved_call_count = 0
    entrypoint_count = 0
    export_count = 0
    resolved_export_count = 0
    import_binding_count = 0
    resolved_import_binding_count = 0
    commonjs_import_count = 0
    cross_file_reference_count = 0
    cross_file_call_count = 0

    symbol_by_path_scope_name: dict[str, dict[tuple[str, str], list[str]]] = {}
    symbol_kind_by_id: dict[str, str] = {}
    symbol_truth_by_id: dict[str, str] = {}
    export_targets_by_path_name: dict[tuple[str, str], list[str]] = {}
    for record, fragment, source_id in fragments:
        path = fragment["path"]
        module_id = module_by_path[path]
        groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
        for definition in fragment["definitions"]:
            key = (
                definition["scope"],
                definition["name"],
                definition["symbol_kind"],
            )
            groups.setdefault(key, []).append(definition)
        symbol_by_scope_name: dict[tuple[str, str], list[str]] = {}
        symbol_id_by_key: dict[tuple[str, str, str], str] = {}
        for scope, name, symbol_kind in sorted(groups):
            symbol_id = _entity_id(
                "JAVASCRIPT_SYMBOL",
                root_key,
                f"{path}:{scope}:{symbol_kind}:{name}",
            )
            symbol_id_by_key[(scope, name, symbol_kind)] = symbol_id
            symbol_by_scope_name.setdefault((scope, name), []).append(symbol_id)
            symbol_kind_by_id[symbol_id] = symbol_kind
            symbol_truth_by_id[symbol_id] = (
                "PROVEN" if len(groups[(scope, name, symbol_kind)]) == 1 else "CONFLICT"
            )
        symbol_by_path_scope_name[path] = symbol_by_scope_name
        for exported in fragment["exports"]:
            candidates = symbol_by_scope_name.get(
                ("MODULE", exported["local_name"]), []
            )
            if len(candidates) == 1 and symbol_truth_by_id[candidates[0]] == "PROVEN":
                export_targets_by_path_name.setdefault(
                    (path, exported["exported_name"]), []
                ).append(candidates[0])
        ownership_relations: list[tuple[str, str, str]] = []
        for (scope, name, symbol_kind), definitions in sorted(groups.items()):
            symbol_id = symbol_id_by_key[(scope, name, symbol_kind)]
            truth = "PROVEN" if len(definitions) == 1 else "CONFLICT"
            qualified_scope = "module" if scope == "MODULE" else scope
            export_names = sorted(
                {
                    item["exported_name"]
                    for item in fragment["exports"]
                    if scope == "MODULE" and item["local_name"] == name
                }
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    symbol_id,
                    "JAVASCRIPT_SYMBOL",
                    name,
                    f"{path}::{qualified_scope}::{symbol_kind.lower()}:{name}",
                    source_id,
                    truth,
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "definition_count": len(definitions),
                            "definitions": [
                                {"path": path, "span": item["span"]}
                                for item in definitions
                            ],
                            "exported": bool(export_names)
                            or any(item["exported"] for item in definitions),
                            "export_names": export_names,
                            "language": fragment["language"],
                            "scope": scope,
                            "symbol_kind": symbol_kind,
                        }
                    ),
                ),
            )
            owner_candidates = symbol_by_scope_name.get(("MODULE", scope), [])
            owner = owner_candidates[0] if len(owner_candidates) == 1 else module_id
            ownership_relations.append((owner, symbol_id, truth))
            for definition in definitions:
                fact_id = _insert_observation(
                    connection,
                    entity_id=symbol_id,
                    predicate="JAVASCRIPT_DEFINITION",
                    value={
                        "exported": definition["exported"],
                        "path": path,
                        "scope": scope,
                        "span": definition["span"],
                        "symbol_kind": symbol_kind,
                    },
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class=truth,
                )
                _insert_location(
                    connection,
                    fact_id=fact_id,
                    source_id=source_id,
                    path=path,
                    span=definition["span"],
                )
            symbol_count += 1

        for owner, symbol_id, truth in ownership_relations:
            _insert_relation(
                connection,
                subject=owner,
                predicate="DEFINES",
                object_=symbol_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class=truth,
            )

        for exported in fragment["exports"]:
            candidates = sorted(
                set(symbol_by_scope_name.get(("MODULE", exported["local_name"]), []))
            )
            target = (
                candidates[0]
                if len(candidates) == 1
                and symbol_truth_by_id[candidates[0]] == "PROVEN"
                else None
            )
            resolution = (
                "EXACT_LOCAL_EXPORT"
                if target is not None
                else (
                    "CONFLICTING_LOCAL_EXPORT"
                    if len(candidates) == 1
                    and symbol_truth_by_id[candidates[0]] == "CONFLICT"
                    else (
                        "AMBIGUOUS_LOCAL_EXPORT"
                        if len(candidates) > 1
                        else "UNRESOLVED_LOCAL_EXPORT"
                    )
                )
            )
            value = {
                **exported,
                "resolution": resolution,
                "target_entity_id": target,
            }
            fact_id = _insert_observation(
                connection,
                entity_id=target or module_id,
                predicate="JAVASCRIPT_EXPORT",
                value=value,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_id,
                path=path,
                span=exported["span"],
            )
            if target is not None:
                _insert_relation(
                    connection,
                    subject=module_id,
                    predicate="EXPORTS",
                    object_=target,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "exported_name": exported["exported_name"],
                        "span": exported["span"],
                        "syntax": exported["syntax"],
                    },
                )
                resolved_export_count += 1
            export_count += 1

    for key, targets in tuple(export_targets_by_path_name.items()):
        export_targets_by_path_name[key] = sorted(set(targets))

    for record, fragment, source_id in fragments:
        path = fragment["path"]
        module_id = module_by_path[path]
        symbol_by_scope_name = symbol_by_path_scope_name[path]

        imported_names: set[str] = set()
        imported_bindings_by_local: dict[str, list[dict[str, Any]]] = {}
        namespace_path_by_local: dict[str, list[str]] = {}
        scope_bindings = {
            scope: set(names) for scope, names in fragment["scope_bindings"].items()
        }
        for imported in fragment["imports"]:
            resolved_path, resolution = _resolved_javascript_import(
                path, imported["specifier"], available_paths
            )
            binding_resolutions: list[dict[str, Any]] = []
            for binding in imported["bindings"]:
                imported_names.add(binding["local_name"])
                imported_name = binding["imported_name"]
                targets: list[str] = []
                direct_targets: list[str] = []
                binding_resolution = "UNRESOLVED_MODULE"
                if resolved_path is not None and resolved_path in module_by_path:
                    if imported_name == "*":
                        targets = [module_by_path[resolved_path]]
                        namespace_path_by_local.setdefault(
                            binding["local_name"], []
                        ).append(resolved_path)
                        if imported["syntax"] == "COMMONJS_REQUIRE":
                            direct_targets = export_targets_by_path_name.get(
                                (resolved_path, "default"), []
                            )
                        binding_resolution = "EXACT_CROSS_FILE_NAMESPACE"
                    else:
                        targets = export_targets_by_path_name.get(
                            (resolved_path, imported_name), []
                        )
                        binding_resolution = (
                            "EXACT_CROSS_FILE_EXPORT"
                            if len(targets) == 1
                            else (
                                "AMBIGUOUS_CROSS_FILE_EXPORT"
                                if len(targets) > 1
                                else "UNRESOLVED_EXPORTED_NAME"
                            )
                        )
                        direct_targets = list(targets)
                elif resolution == "EXTERNAL_PACKAGE":
                    binding_resolution = "EXTERNAL_PACKAGE"
                elif resolved_path is not None:
                    binding_resolution = "RESOLVED_PATH_NOT_MAPPED"
                item = {
                    **binding,
                    "direct_target_entity_ids": sorted(set(direct_targets)),
                    "resolution": binding_resolution,
                    "resolved_path": resolved_path,
                    "syntax": imported["syntax"],
                    "target_entity_ids": sorted(set(targets)),
                }
                binding_resolutions.append(item)
                imported_bindings_by_local.setdefault(binding["local_name"], []).append(
                    item
                )
                import_binding_count += 1
                resolved_import_binding_count += int(
                    binding_resolution
                    in {"EXACT_CROSS_FILE_EXPORT", "EXACT_CROSS_FILE_NAMESPACE"}
                )
            commonjs_import_count += int(imported["syntax"] == "COMMONJS_REQUIRE")
            dependency_id = _entity_id(
                "JAVASCRIPT_IMPORT",
                root_key,
                f"{path}:{imported['specifier']}:{_javascript_span_key(imported['span'])}",
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    dependency_id,
                    "JAVASCRIPT_IMPORT",
                    imported["specifier"],
                    f"{path}::import:{imported['specifier']}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "bindings": imported["bindings"],
                            "binding_resolutions": binding_resolutions,
                            "language": fragment["language"],
                            "path": path,
                            "resolution": resolution,
                            "resolved_path": resolved_path,
                            "span": imported["span"],
                            "syntax": imported["syntax"],
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=module_id,
                predicate="DECLARES_DEPENDENCY",
                object_=dependency_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            if resolved_path is not None and resolved_path in module_by_path:
                _insert_relation(
                    connection,
                    subject=module_id,
                    predicate="IMPORTS",
                    object_=module_by_path[resolved_path],
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "specifier": imported["specifier"],
                        "span": imported["span"],
                        "syntax": imported["syntax"],
                    },
                )
                resolved_import_count += 1
            fact_id = _insert_observation(
                connection,
                entity_id=dependency_id,
                predicate="JAVASCRIPT_IMPORT",
                value={
                    "bindings": imported["bindings"],
                    "binding_resolutions": binding_resolutions,
                    "resolution": resolution,
                    "resolved_path": resolved_path,
                    "specifier": imported["specifier"],
                    "span": imported["span"],
                    "syntax": imported["syntax"],
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_id,
                path=path,
                span=imported["span"],
            )
            import_count += 1

        def resolve_name(scope: str, name: str) -> tuple[str | None, str]:
            local = symbol_by_scope_name.get((scope, name), [])
            if len(local) == 1:
                return local[0], "SAME_LEXICAL_SCOPE"
            if len(local) > 1:
                return None, "AMBIGUOUS_LEXICAL_SCOPE"
            if scope != "MODULE" and name in scope_bindings.get(scope, set()):
                return None, "LOCAL_BINDING_WITHOUT_SYMBOL"
            imported = imported_bindings_by_local.get(name, [])
            direct_targets = sorted(
                {
                    target
                    for item in imported
                    for target in item["direct_target_entity_ids"]
                }
            )
            if len(direct_targets) == 1:
                return direct_targets[0], "EXACT_CROSS_FILE_IMPORT"
            if len(direct_targets) > 1:
                return None, "AMBIGUOUS_CROSS_FILE_IMPORT"
            module = symbol_by_scope_name.get(("MODULE", name), [])
            if len(module) == 1:
                return module[0], "SAME_MODULE_DECLARATION"
            if len(module) > 1:
                return None, "AMBIGUOUS_MODULE_DECLARATION"
            if imported:
                statuses = sorted({item["resolution"] for item in imported})
                return None, "IMPORTED_BINDING_" + "_OR_".join(statuses)
            if name in imported_names:
                return None, "IMPORTED_BINDING_UNRESOLVED"
            return None, "UNRESOLVED_OR_GLOBAL"

        def resolve_member(
            object_name: str, property_name: str
        ) -> tuple[str | None, str]:
            paths = sorted(set(namespace_path_by_local.get(object_name, [])))
            if len(paths) != 1:
                return (
                    None,
                    "AMBIGUOUS_CROSS_FILE_NAMESPACE"
                    if len(paths) > 1
                    else "DYNAMIC_OR_MEMBER_EXPRESSION",
                )
            targets = export_targets_by_path_name.get((paths[0], property_name), [])
            if len(targets) == 1:
                return targets[0], "EXACT_CROSS_FILE_NAMESPACE_MEMBER"
            return (
                None,
                "AMBIGUOUS_CROSS_FILE_NAMESPACE_MEMBER"
                if len(targets) > 1
                else "UNRESOLVED_CROSS_FILE_NAMESPACE_MEMBER",
            )

        for reference in fragment["references"]:
            target, resolution = resolve_name(reference["scope"], reference["name"])
            fact_id = _insert_observation(
                connection,
                entity_id=target or module_id,
                predicate="JAVASCRIPT_REFERENCE",
                value={
                    "name": reference["name"],
                    "path": path,
                    "resolution": resolution,
                    "scope": reference["scope"],
                    "span": reference["span"],
                    "target_entity_id": target,
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="INFERRED" if target is not None else "PROVEN",
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_id,
                path=path,
                span=reference["span"],
            )
            reference_count += 1
            resolved_reference_count += int(target is not None)
            cross_file_reference_count += int(resolution == "EXACT_CROSS_FILE_IMPORT")

        callable_kinds = {"CLASS", "FUNCTION", "FUNCTION_VARIABLE"}
        for call in fragment["calls"]:
            caller_candidates = symbol_by_scope_name.get(("MODULE", call["scope"]), [])
            caller = caller_candidates[0] if len(caller_candidates) == 1 else module_id
            target = None
            resolution = "DYNAMIC_OR_MEMBER_EXPRESSION"
            if call["callee_name"] is not None:
                target, resolution = resolve_name(call["scope"], call["callee_name"])
            elif (
                call["member_object"] is not None
                and call["member_property"] is not None
            ):
                target, resolution = resolve_member(
                    call["member_object"], call["member_property"]
                )
            if (
                target is not None
                and symbol_kind_by_id.get(target) not in callable_kinds
            ):
                target = None
                resolution = "UNRESOLVED_NON_CALLABLE_TARGET"
            call_id = _entity_id(
                "JAVASCRIPT_CALL",
                root_key,
                f"{path}:{_javascript_span_key(call['span'])}:{call['expression']}",
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    call_id,
                    "JAVASCRIPT_CALL",
                    call["expression"],
                    f"{path}::call:{call['expression']}@{call['span']['line_start']}:{call['span']['column_start']}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "callee_name": call["callee_name"],
                            "caller_scope": call["scope"],
                            "expression": call["expression"],
                            "language": fragment["language"],
                            "member_object": call["member_object"],
                            "member_property": call["member_property"],
                            "resolution": resolution,
                            "span": call["span"],
                            "target_entity_id": target,
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=caller,
                predicate="INVOKES_CALLSITE",
                object_=call_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            if target is not None:
                _insert_relation(
                    connection,
                    subject=caller,
                    predicate="CALLS",
                    object_=target,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="INFERRED",
                    attributes={"resolution": resolution, "span": call["span"]},
                )
                resolved_call_count += 1
            fact_id = _insert_observation(
                connection,
                entity_id=call_id,
                predicate="JAVASCRIPT_CALLSITE",
                value={
                    "caller_scope": call["scope"],
                    "expression": call["expression"],
                    "member_object": call["member_object"],
                    "member_property": call["member_property"],
                    "resolution": resolution,
                    "span": call["span"],
                    "target_entity_id": target,
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_id,
                path=path,
                span=call["span"],
            )
            call_count += 1
            cross_file_call_count += int(
                target is not None and resolution.startswith("EXACT_CROSS_FILE_")
            )

        if fragment["shebang"] is not None or bool(record["mode"] & 0o111):
            entrypoint_id = _entity_id(
                "ENTRYPOINT", root_key, f"JAVASCRIPT_MODULE:{path}"
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    entrypoint_id,
                    "ENTRYPOINT",
                    PurePosixPath(path).name,
                    f"JAVASCRIPT_MODULE:{path}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "executable": bool(record["mode"] & 0o111),
                            "handler": path,
                            "kind": "JAVASCRIPT_MODULE",
                            "language": fragment["language"],
                            "shebang": fragment["shebang"],
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=entrypoint_id,
                predicate="HANDLED_BY",
                object_=module_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            entrypoint_count += 1

    covered = len(fragments)
    failed = len(failures)
    for map_id, fact_class in (
        ("symbols", "JAVASCRIPT_TYPESCRIPT_SYMBOL_AND_REFERENCE"),
        ("dependencies", "JAVASCRIPT_TYPESCRIPT_LITERAL_IMPORT"),
        ("api_events", "JAVASCRIPT_TYPESCRIPT_MODULE_ENTRYPOINT"),
        ("calls", "JAVASCRIPT_TYPESCRIPT_STATIC_CALLSITE"),
    ):
        connection.execute(
            "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                producer_id,
                map_id,
                fact_class,
                "semantic-eligible-js-jsx-mjs-cjs-ts-tsx",
                "COVERED" if not failures else "PARTIAL",
                len(records),
                covered,
                failed,
                0,
                0,
                _json(
                    {
                        "backend": backend,
                        "dynamic_imports": "UNSUPPORTED",
                        "dynamic_member_calls": "UNRESOLVED_PRESERVED",
                        "failures": failures,
                        "languages": ["javascript", "tsx", "typescript"],
                        "name_resolution": "SAME_SCOPE_MODULE_AND_EXACT_CROSS_FILE_EXPORT",
                        "commonjs": {
                            "exports": "MODULE_SCOPE_IDENTIFIER_TARGETS",
                            "require": "MODULE_SCOPE_LITERAL_BINDINGS",
                        },
                        "source_execution": False,
                    }
                ),
            ),
        )

    connection.execute(
        """UPDATE map_views
           SET status='AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_PARTIAL',
               required_fact_classes_json=?, query_contract_json=?
           WHERE map_id='symbols'""",
        (
            _json(
                [
                    "PYTHON_MODULE",
                    "PYTHON_SYMBOL",
                    "PYTHON_REFERENCE",
                    "SHELL_SCRIPT",
                    "SHELL_SYMBOL",
                    "SHELL_REFERENCE",
                    "JAVASCRIPT_MODULE",
                    "JAVASCRIPT_SYMBOL",
                    "JAVASCRIPT_REFERENCE",
                ]
            ),
            _json(
                {
                    "exact_spans": True,
                    "languages": ["bash", "javascript", "python", "tsx", "typescript"],
                    "query": "name-path-qualified-name",
                }
            ),
        ),
    )
    connection.execute(
        """UPDATE map_views
           SET status='AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_PARTIAL',
               required_fact_classes_json=?, query_contract_json=?
           WHERE map_id='dependencies'""",
        (
            _json(
                ["PYTHON_IMPORT", "IMPORTS", "SHELL_DEPENDENCY", "JAVASCRIPT_IMPORT"]
            ),
            _json(
                {
                    "literal_javascript_imports": True,
                    "literal_commonjs_requires": True,
                    "cross_file_export_binding": True,
                    "literal_shell_dependencies": True,
                    "reverse_impact": True,
                    "unresolved_preserved": True,
                }
            ),
        ),
    )
    connection.execute(
        """UPDATE map_views
           SET status='AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_ENTRYPOINT_PARTIAL',
               required_fact_classes_json=?, query_contract_json=?
           WHERE map_id='api_events'""",
        (
            _json(["ENTRYPOINT", "DECLARES_ENTRYPOINT", "HANDLED_BY"]),
            _json(
                {
                    "argparse": True,
                    "bash_scripts": True,
                    "http": False,
                    "javascript_shebang_modules": True,
                    "project_scripts": True,
                }
            ),
        ),
    )
    connection.execute(
        """UPDATE map_views
           SET status='AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_STATIC_PARTIAL',
               required_fact_classes_json=?, query_contract_json=?
           WHERE map_id='calls'""",
        (
            _json(
                [
                    "PYTHON_CALL",
                    "CALLS",
                    "SHELL_COMMAND",
                    "INVOKES_COMMAND",
                    "JAVASCRIPT_CALL",
                    "INVOKES_CALLSITE",
                ]
            ),
            _json(
                {
                    "bash_same_script_function_resolution": True,
                    "exact_lexical_and_import_resolution": True,
                    "javascript_same_scope_or_module_resolution": True,
                    "javascript_cross_file_esm_commonjs_resolution": True,
                    "runtime_dispatch": False,
                    "unresolved_preserved": True,
                }
            ),
        ),
    )
    return {
        "javascript_files": covered,
        "javascript_parse_failures": failed,
        "javascript_modules": covered,
        "javascript_symbols": symbol_count,
        "javascript_references": reference_count,
        "javascript_references_resolved": resolved_reference_count,
        "javascript_imports": import_count,
        "javascript_imports_resolved": resolved_import_count,
        "javascript_calls": call_count,
        "javascript_calls_resolved": resolved_call_count,
        "javascript_cross_file_calls_resolved": cross_file_call_count,
        "javascript_cross_file_references_resolved": cross_file_reference_count,
        "javascript_entrypoints": entrypoint_count,
        "javascript_exports": export_count,
        "javascript_exports_resolved": resolved_export_count,
        "javascript_import_bindings": import_binding_count,
        "javascript_import_bindings_resolved": resolved_import_binding_count,
        "javascript_commonjs_imports": commonjs_import_count,
    }


def _reachability_usage_counterevidence(
    connection: sqlite3.Connection,
    candidates: Sequence[sqlite3.Row],
) -> dict[str, list[dict[str, Any]]]:
    """Collect bounded syntax evidence that prevents false absence claims.

    This reads only facts already admitted by deterministic language producers.  It
    does not make a runtime-reachability or deletion decision.  Exact resolved edges
    and references stay distinct from decorated-definition and dynamic-string syntax,
    whose target semantics remain merely observed.
    """

    candidate_ids = {row["entity_id"] for row in candidates}
    candidate_names: dict[str, set[str]] = {}
    for row in candidates:
        for name in (row["name"], row["qualified_name"]):
            if name:
                candidate_names.setdefault(name, set()).add(row["entity_id"])
    signals: dict[str, list[dict[str, Any]]] = {
        entity_id: [] for entity_id in candidate_ids
    }

    def add(
        target: str | None,
        *,
        source_id: str,
        source_path: str,
        source_fact_id: str,
        source_owner_id: str,
        kind: str,
        target_binding: str,
        truth_class: str,
        span: Mapping[str, Any] | None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if target not in candidate_ids or source_owner_id == target:
            return
        signals[target].append(
            {
                "details": dict(details or {}),
                "kind": kind,
                "source_fact_id": source_fact_id,
                "source_id": source_id,
                "source_owner_id": source_owner_id,
                "source_path": source_path,
                "span": dict(span) if span is not None else None,
                "target_binding": target_binding,
                "truth_class": truth_class,
            }
        )

    for row in connection.execute(
        """SELECT o.observation_id,o.entity_id,o.source_id,o.value_json,s.path
           FROM observations o JOIN sources s ON s.source_id=o.source_id
           WHERE o.predicate='PYTHON_REFERENCE'
           ORDER BY o.observation_id"""
    ):
        value = json.loads(row["value_json"])
        add(
            value.get("target_entity_id"),
            source_id=row["source_id"],
            source_path=row["path"],
            source_fact_id=row["observation_id"],
            source_owner_id=row["entity_id"],
            kind="RESOLVED_REFERENCE",
            target_binding="EXACT_ENTITY_ID",
            truth_class="PROVEN",
            span=value.get("span"),
            details={
                "expression": value.get("expression"),
                "resolution": value.get("resolution"),
            },
        )

    for row in connection.execute(
        """SELECT r.relation_id,r.subject_id,r.object_id,r.source_id,
                  r.predicate,r.attributes_json,s.path
           FROM relations r JOIN sources s ON s.source_id=r.source_id
           WHERE r.predicate IN ('CALLS','IMPORTS')
           ORDER BY r.relation_id"""
    ):
        attributes = json.loads(row["attributes_json"])
        add(
            row["object_id"],
            source_id=row["source_id"],
            source_path=row["path"],
            source_fact_id=row["relation_id"],
            source_owner_id=row["subject_id"],
            kind=f"RESOLVED_{row['predicate'][:-1]}",
            target_binding="EXACT_ENTITY_ID",
            truth_class="PROVEN",
            span=attributes.get("span"),
            details={"relation_predicate": row["predicate"]},
        )

    for row in connection.execute(
        """SELECT o.observation_id,o.entity_id,o.source_id,o.value_json,s.path
           FROM observations o JOIN sources s ON s.source_id=o.source_id
           WHERE o.predicate='PYTHON_DEFINITION'
           ORDER BY o.observation_id"""
    ):
        value = json.loads(row["value_json"])
        decorators = value.get("attributes", {}).get("decorators", [])
        if not decorators:
            continue
        add(
            row["entity_id"],
            source_id=row["source_id"],
            source_path=row["path"],
            source_fact_id=row["observation_id"],
            source_owner_id=f"definition:{row['observation_id']}",
            kind="DECORATED_DEFINITION",
            target_binding="EXACT_DEFINITION_SYNTAX",
            truth_class="OBSERVED",
            span=value.get("span"),
            details={"decorators": decorators},
        )

    for row in connection.execute(
        """SELECT o.observation_id,o.entity_id,o.source_id,o.value_json,s.path
           FROM observations o JOIN sources s ON s.source_id=o.source_id
           WHERE o.predicate='PYTHON_CALL'
           ORDER BY o.observation_id"""
    ):
        value = json.loads(row["value_json"])
        expression = value.get("declared_expression") or value.get("expression") or ""
        if expression.rsplit(".", 1)[-1] not in DYNAMIC_CALLS:
            continue
        arguments = value.get("arguments", {})
        argument_values = [
            *arguments.get("positional", []),
            *arguments.get("keywords", []),
        ]
        literals = sorted(
            {
                item.get("literal")
                for item in argument_values
                if isinstance(item, dict) and isinstance(item.get("literal"), str)
            }
        )
        for literal in literals:
            matched = sorted(candidate_names.get(literal, ()))
            for target in matched:
                add(
                    target,
                    source_id=row["source_id"],
                    source_path=row["path"],
                    source_fact_id=row["observation_id"],
                    source_owner_id=row["entity_id"],
                    kind="DYNAMIC_STRING_NAME_MATCH",
                    target_binding="LEXICAL_NAME_MATCH_NOT_SEMANTIC_BINDING",
                    truth_class="OBSERVED",
                    span=value.get("span"),
                    details={
                        "call": expression,
                        "literal": literal,
                        "matching_candidate_count": len(matched),
                    },
                )

    result: dict[str, list[dict[str, Any]]] = {}
    for target, items in signals.items():
        unique = {sha256_bytes(canonical_bytes(item)): item for item in items}
        if unique:
            result[target] = [unique[key] for key in sorted(unique)]
    return result


def _build_cleanup_maps(
    connection: sqlite3.Connection,
    *,
    inventory: NavigationRun,
    root_key: str,
    manifest_source: str,
    producer_id: str,
    snapshot_run_id: str,
) -> dict[str, int]:
    """Project exact duplicates and bounded static reachability into the fact store."""

    inventory_connection = _inventory_connection(inventory)
    try:
        duplicate_records = [
            dict(row)
            for row in inventory_connection.execute(
                """SELECT * FROM files
                   WHERE kind='regular' AND content_sha256 IN (
                       SELECT content_sha256 FROM duplicate_groups
                   ) ORDER BY content_sha256,path"""
            )
        ]
    finally:
        inventory_connection.close()
    groups, skipped_groups = safe_exact_duplicate_groups(duplicate_records)
    duplicate_members = 0
    for group in groups:
        digest = group["content_sha256"]
        group_id = _entity_id("DUPLICATE_GROUP", root_key, digest)
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                group_id,
                "DUPLICATE_GROUP",
                digest[:12],
                f"sha256:{digest}",
                manifest_source,
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_METADATA",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "authority_granted": False,
                        "cleanup_permitted": False,
                        "content_sha256": digest,
                        "copies": len(group["members"]),
                        "similarity_tier": "EXACT_CONTENT",
                    }
                ),
            ),
        )
        for record in group["members"]:
            path = record["path"]
            source_id = f"source:cleanup-artifact:{_fact_id([root_key, path, digest])}"
            source_record = {key: value for key, value in record.items() if key != "id"}
            connection.execute(
                "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?)",
                (
                    source_id,
                    "ARTIFACT",
                    path,
                    _source_identity(source_record),
                    "LOCAL_SOURCE",
                    _json(
                        {
                            "content_sha256": digest,
                            "inventory_run_id": snapshot_run_id,
                            "semantic_reason": record["semantic_reason"],
                        }
                    ),
                ),
            )
            member_id = _entity_id("DUPLICATE_MEMBER", root_key, path)
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    member_id,
                    "DUPLICATE_MEMBER",
                    PurePosixPath(path).name,
                    path,
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "authority_granted": False,
                            "cleanup_permitted": False,
                            "content_sha256": digest,
                            "exact_group": group_id,
                            "path": path,
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=group_id,
                predicate="HAS_EXACT_DUPLICATE_MEMBER",
                object_=member_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            duplicate_members += 1

    structural_records: list[dict[str, Any]] = []
    structural_functions_total = 0
    structural_functions_eligible = 0
    structural_functions_unsupported = 0
    structural_files_failed_parse = 0
    structural_skip_reasons: dict[str, int] = {}
    for row in connection.execute(
        """SELECT path,payload_json FROM python_fragments
           WHERE fragment_kind='PYTHON_SOURCE' ORDER BY path"""
    ):
        try:
            payload = json.loads(row["payload_json"])
            if set(payload) != {"file", "failure"}:
                raise ValueError("Python fragment wrapper is open")
            if payload["file"] is None:
                if not isinstance(payload["failure"], dict):
                    raise ValueError("Python fragment disposition is ambiguous")
                structural_files_failed_parse += 1
                continue
            if payload["failure"] is not None or not isinstance(payload["file"], dict):
                raise ValueError("Python fragment disposition is ambiguous")
            projection = payload["file"]["structural_similarity"]
            if (
                projection["policy"] != PYTHON_STRUCTURE_POLICY_VERSION
                or projection["policy_sha256"] != PYTHON_STRUCTURE_POLICY_SHA256
                or projection["eligible"] != len(projection["fingerprints"])
                or projection["functions_total"]
                != projection["eligible"] + sum(projection["skipped"].values())
            ):
                raise ValueError("structural fingerprint closure mismatch")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise MapperError(
                f"Python structural fragment is invalid: {row['path']}"
            ) from exc
        structural_functions_total += projection["functions_total"]
        structural_functions_eligible += projection["eligible"]
        structural_functions_unsupported += sum(projection["skipped"].values())
        for reason, count in projection["skipped"].items():
            structural_skip_reasons[reason] = (
                structural_skip_reasons.get(reason, 0) + count
            )
        structural_records.extend(dict(item) for item in projection["fingerprints"])

    structural_groups, structural_group_stats = safe_structural_duplicate_groups(
        structural_records
    )
    if structural_group_stats["malformed_records"]:
        raise MapperError("Python structural fingerprints failed closed validation")
    structural_members = 0
    for group in structural_groups:
        fingerprint = group["fingerprint_sha256"]
        group_id = _entity_id("STRUCTURAL_DUPLICATE_GROUP", root_key, fingerprint)
        member_paths = {member["path"] for member in group["members"]}
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                group_id,
                "STRUCTURAL_DUPLICATE_GROUP",
                fingerprint[:12],
                f"python-normalized-ast:{fingerprint}",
                manifest_source,
                "OBSERVED",
                producer_id,
                snapshot_run_id,
                "LOCAL_METADATA",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "authority_granted": False,
                        "cleanup_permitted": False,
                        "copies": len(group["members"]),
                        "cross_file": len(member_paths) > 1,
                        "deletion_permitted": False,
                        "fingerprint_sha256": fingerprint,
                        "normalization_policy_sha256": (PYTHON_STRUCTURE_POLICY_SHA256),
                        "semantic_equivalence_claimed": False,
                        "similarity_tier": "NORMALIZED_PYTHON_AST_EXACT",
                    }
                ),
            ),
        )
        for member in group["members"]:
            symbol_id = _entity_id(
                "PYTHON_SYMBOL",
                root_key,
                ":".join(
                    (
                        _artifact_id(root_key, member["path"]),
                        member["qualified_name"],
                        member["symbol_kind"],
                    )
                ),
            )
            symbol = connection.execute(
                """SELECT source_id FROM entities
                   WHERE entity_id=? AND entity_kind='PYTHON_SYMBOL'""",
                (symbol_id,),
            ).fetchone()
            if symbol is None:
                raise MapperError(
                    "Python structural fingerprint has no exact symbol: "
                    f"{member['path']}::{member['qualified_name']}"
                )
            source_id = symbol["source_id"]
            member_id = _entity_id(
                "STRUCTURAL_DUPLICATE_MEMBER",
                root_key,
                ":".join(
                    (
                        member["path"],
                        member["qualified_name"],
                        str(member["span"]["line_start"]),
                        fingerprint,
                    )
                ),
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    member_id,
                    "STRUCTURAL_DUPLICATE_MEMBER",
                    member["qualified_name"].rsplit(".", 1)[-1],
                    f"{member['path']}::{member['qualified_name']}",
                    source_id,
                    "OBSERVED",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "ast_node_count": member["ast_node_count"],
                            "authority_granted": False,
                            "cleanup_permitted": False,
                            "content_sha256": member["content_sha256"],
                            "deletion_permitted": False,
                            "fingerprint_sha256": fingerprint,
                            "normalization_policy_sha256": (
                                PYTHON_STRUCTURE_POLICY_SHA256
                            ),
                            "path": member["path"],
                            "qualified_name": member["qualified_name"],
                            "semantic_equivalence_claimed": False,
                            "span": member["span"],
                            "statement_count": member["statement_count"],
                            "symbol_id": symbol_id,
                            "symbol_kind": member["symbol_kind"],
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=group_id,
                predicate="HAS_STRUCTURAL_DUPLICATE_MEMBER",
                object_=member_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
            )
            _insert_relation(
                connection,
                subject=member_id,
                predicate="STRUCTURAL_FINGERPRINT_OF",
                object_=symbol_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
            )
            fact_id = _insert_observation(
                connection,
                entity_id=member_id,
                predicate="PYTHON_NORMALIZED_AST_FINGERPRINT",
                value={
                    "ast_node_count": member["ast_node_count"],
                    "fingerprint_sha256": fingerprint,
                    "normalization_policy_sha256": PYTHON_STRUCTURE_POLICY_SHA256,
                    "semantic_equivalence_claimed": False,
                    "span": member["span"],
                    "statement_count": member["statement_count"],
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_id,
                path=member["path"],
                span=member["span"],
            )
            structural_members += 1

    supported_predicates = ("HANDLED_BY", "CALLS", "IMPORTS")
    adjacency: dict[str, set[str]] = {}
    for row in connection.execute(
        """SELECT subject_id,object_id FROM relations
           WHERE predicate IN ('HANDLED_BY','CALLS','IMPORTS')
           ORDER BY subject_id,object_id"""
    ):
        adjacency.setdefault(row["subject_id"], set()).add(row["object_id"])
    roots = {
        row[0]
        for row in connection.execute(
            "SELECT entity_id FROM entities WHERE entity_kind='ENTRYPOINT'"
        )
    }
    for row in connection.execute(
        """SELECT subject_id,object_id FROM relations
           WHERE predicate IN ('DECLARES_ENTRYPOINT','HANDLED_BY')"""
    ):
        roots.update((row["subject_id"], row["object_id"]))
    reached = set(roots)
    frontier = list(sorted(roots))
    while frontier:
        current = frontier.pop()
        for target in sorted(adjacency.get(current, ())):
            if target not in reached:
                reached.add(target)
                frontier.append(target)

    candidates = connection.execute(
        """SELECT entity_id,source_id,entity_kind,name,qualified_name FROM entities
           WHERE entity_kind IN (
               'PYTHON_MODULE','PYTHON_SYMBOL','SHELL_SCRIPT','SHELL_SYMBOL',
               'JAVASCRIPT_MODULE','JAVASCRIPT_SYMBOL'
           )
           ORDER BY entity_id"""
    ).fetchall()
    usage_counterevidence = _reachability_usage_counterevidence(connection, candidates)
    reached_count = 0
    not_reached_count = 0
    usage_counterevidence_facts = 0
    exact_counterevidence_targets = 0
    observed_counterevidence_targets = 0
    unknown_counterevidence_targets = 0
    for row in candidates:
        is_reached = row["entity_id"] in reached
        signals = usage_counterevidence.get(row["entity_id"], [])
        exact_signals = sum(item["truth_class"] == "PROVEN" for item in signals)
        observed_signals = sum(item["truth_class"] == "OBSERVED" for item in signals)
        if exact_signals:
            usage_state = "PRESENT_EXACT_STATIC"
            exact_counterevidence_targets += 1
        elif observed_signals:
            usage_state = "PRESENT_OBSERVED_SYNTAX"
            observed_counterevidence_targets += 1
        else:
            usage_state = "UNKNOWN"
            unknown_counterevidence_targets += 1
        dynamic_state = (
            "PRESENT_OBSERVED_NAME_MATCH"
            if any(item["kind"] == "DYNAMIC_STRING_NAME_MATCH" for item in signals)
            else "UNKNOWN"
        )
        for signal in signals:
            value = {
                "authority_granted": False,
                "cleanup_permitted": False,
                "deletion_permitted": False,
                "details": signal["details"],
                "kind": signal["kind"],
                "runtime_observed": False,
                "source_fact_id": signal["source_fact_id"],
                "source_owner_id": signal["source_owner_id"],
                "target_binding": signal["target_binding"],
            }
            fact_id = _insert_observation(
                connection,
                entity_id=row["entity_id"],
                predicate="DELETION_COUNTEREVIDENCE",
                value=value,
                source_id=signal["source_id"],
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class=signal["truth_class"],
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=signal["source_id"],
                path=signal["source_path"],
                span=signal["span"],
            )
            usage_counterevidence_facts += 1
        state = (
            "REACHED_FROM_SUPPORTED_STATIC_ROOT"
            if is_reached
            else "NOT_REACHED_BY_SUPPORTED_STATIC_ROOTS"
        )
        _insert_observation(
            connection,
            entity_id=row["entity_id"],
            predicate="STATIC_REACHABILITY",
            value={
                "authority_granted": False,
                "cleanup_permitted": False,
                "deletion_permitted": False,
                "dynamic_counterevidence": dynamic_state,
                "entrypoint_roots": len(roots),
                "runtime_observed": False,
                "state": state,
                "supported_predicates": list(supported_predicates),
                "usage_counterevidence": {
                    "exact_facts": exact_signals,
                    "observed_facts": observed_signals,
                    "state": usage_state,
                },
            },
            source_id=row["source_id"],
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
            truth_class="PROVEN" if is_reached else "INFERRED",
        )
        reached_count += int(is_reached)
        not_reached_count += int(not is_reached)

    connection.executemany(
        "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            (
                producer_id,
                "duplicates_similarity",
                "EXACT_CONTENT_DUPLICATE_GROUP",
                "semantic-eligible-regular-files",
                "PARTIAL",
                len(groups) + skipped_groups,
                len(groups),
                0,
                skipped_groups,
                0,
                _json(
                    {
                        "approximate_similarity": "UNSUPPORTED",
                        "cleanup_permitted": False,
                        "content_read": False,
                        "deletion_permitted": False,
                        "policy_sha256": CLEANUP_POLICY_SHA256,
                        "sensitive_or-ineligible-groups": "SKIPPED_POLICY",
                    }
                ),
            ),
            (
                producer_id,
                "duplicates_similarity",
                "PYTHON_NORMALIZED_AST_STRUCTURAL_GROUP",
                "semantic-eligible-python-functions",
                "PARTIAL",
                structural_functions_total,
                structural_functions_eligible,
                0,
                structural_functions_unsupported,
                0,
                _json(
                    {
                        "cleanup_permitted": False,
                        "deletion_permitted": False,
                        "exact_file_groups_omitted": structural_group_stats[
                            "exact_file_groups_omitted"
                        ],
                        "groups": len(structural_groups),
                        "files_failed_parse": structural_files_failed_parse,
                        "normalization_policy": PYTHON_STRUCTURE_POLICY_VERSION,
                        "normalization_policy_sha256": (PYTHON_STRUCTURE_POLICY_SHA256),
                        "semantic_equivalence_claimed": False,
                        "semantic_similarity": "UNSUPPORTED",
                        "skipped_by_reason": structural_skip_reasons,
                        "truth_class": "OBSERVED",
                    }
                ),
            ),
            (
                producer_id,
                "reachability",
                "SUPPORTED_STATIC_ROOT_REACHABILITY",
                "supported-static-roots-and-usage-counterevidence",
                "PARTIAL",
                len(candidates),
                reached_count,
                0,
                0,
                not_reached_count,
                _json(
                    {
                        "counterevidence_owner": "modules.operations.archaeology.counterevidence",
                        "counterevidence_exact_targets": exact_counterevidence_targets,
                        "counterevidence_observed_targets": observed_counterevidence_targets,
                        "counterevidence_unknown_targets": unknown_counterevidence_targets,
                        "counterevidence_facts": usage_counterevidence_facts,
                        "dead_code_claim": "FORBIDDEN",
                        "dynamic_dispatch": "UNSUPPORTED",
                        "judge_owner": "modules.operations.archaeology.judge",
                        "not_reached_truth_class": "INFERRED",
                        "policy_sha256": CLEANUP_POLICY_SHA256,
                        "runtime_observed": False,
                    }
                ),
            ),
        ),
    )
    connection.executemany(
        "INSERT INTO map_views VALUES (?,?,?,?,?)",
        (
            (
                "duplicates_similarity",
                "1",
                "AVAILABLE_EXACT_AND_PYTHON_STRUCTURE_PARTIAL",
                _json(
                    [
                        "DUPLICATE_GROUP",
                        "DUPLICATE_MEMBER",
                        "HAS_EXACT_DUPLICATE_MEMBER",
                        "STRUCTURAL_DUPLICATE_GROUP",
                        "STRUCTURAL_DUPLICATE_MEMBER",
                        "HAS_STRUCTURAL_DUPLICATE_MEMBER",
                        "STRUCTURAL_FINGERPRINT_OF",
                    ]
                ),
                _json(
                    {
                        "authority_granted": False,
                        "cleanup_permitted": False,
                        "normalized_python_structure": True,
                        "semantic_equivalence_claimed": False,
                        "semantic_similarity": False,
                    }
                ),
            ),
            (
                "reachability",
                "2",
                "AVAILABLE_STATIC_WITH_USAGE_COUNTEREVIDENCE_PARTIAL",
                _json(["STATIC_REACHABILITY", "DELETION_COUNTEREVIDENCE"]),
                _json(
                    {
                        "dead_code_claim": False,
                        "dynamic_counterevidence": "OBSERVED_NAME_MATCH_OR_UNKNOWN",
                        "runtime_observed": False,
                        "usage_counterevidence": "EXACT_OBSERVED_OR_UNKNOWN",
                    }
                ),
            ),
        ),
    )
    return {
        "exact_duplicate_groups": len(groups),
        "exact_duplicate_members": duplicate_members,
        "duplicate_groups_skipped_policy": skipped_groups,
        "structural_duplicate_groups": len(structural_groups),
        "structural_duplicate_members": structural_members,
        "structural_functions_eligible": structural_functions_eligible,
        "structural_functions_total": structural_functions_total,
        "structural_functions_unsupported": structural_functions_unsupported,
        "static_reachability_roots": len(roots),
        "static_reachable_entities": reached_count,
        "static_not_reached_hypotheses": not_reached_count,
        "usage_counterevidence_facts": usage_counterevidence_facts,
        "usage_counterevidence_exact_targets": exact_counterevidence_targets,
        "usage_counterevidence_observed_targets": observed_counterevidence_targets,
        "usage_counterevidence_unknown_targets": unknown_counterevidence_targets,
    }


def _build_lineage_ownership_maps(
    connection: sqlite3.Connection,
    *,
    inventory: NavigationRun,
    root_key: str,
    repository_id: str,
    manifest_source: str,
    producer_id: str,
    snapshot_run_id: str,
) -> dict[str, int]:
    """Project bounded Git lineage and conservative ownership candidates."""

    inventory_connection = _inventory_connection(inventory)
    try:
        available_records = [
            dict(row)
            for row in inventory_connection.execute(
                """SELECT * FROM files
                   WHERE kind='regular' AND semantic_reason!='sensitive-path'
                   ORDER BY path"""
            )
        ]
    finally:
        inventory_connection.close()
    root = Path(inventory.manifest["root"]["path"]).resolve(strict=True)
    contract_records = [
        record
        for record in available_records
        if record["path"].startswith("capabilities/manifests/")
        and PurePosixPath(record["path"]).suffix.casefold() == ".json"
    ]
    capability_backend = _capability_backend()
    if contract_records and capability_backend is None:
        raise MapperError(
            "GIGA capability manifests require the optional giga integration: "
            "install giga-archaeology[giga] with access to giga-user-control-plane"
        )
    owner_contracts: list[dict[str, Any]] = []
    owner_contract_failures: list[dict[str, str]] = []
    declared_paths: set[str] = set()
    for record in contract_records:
        assert capability_backend is not None
        adoption_error, inspect_manifest = capability_backend
        try:
            contract = inspect_manifest(root, record["path"])
        except adoption_error as exc:
            owner_contract_failures.append({"path": record["path"], "reason": str(exc)})
            continue
        if contract["manifest_sha256"] != record["content_sha256"]:
            raise MapperError("capability owner contract drifted from inventory")
        owner_contracts.append(contract)
        declared_paths.update(contract["implementation_paths"])
        declared_paths.update(contract["configuration_paths"])
        declared_paths.update(contract["proof_paths"])
    records = [
        record
        for record in available_records
        if record["semantic_eligible"]
        or PurePosixPath(record["path"]).name.casefold() == "codeowners"
        or record["path"] in declared_paths
    ]
    ownership_ids: dict[str, str] = {}
    ownership_roles: dict[str, tuple[str, str]] = {}
    source_ids: dict[str, str] = {}
    canonical_candidates = 0
    for record in records:
        path = record["path"]
        role, basis = classify_navigation_role(
            path,
            repository_present=True,
            tracked=bool(record["git_tracked"]),
        )
        canonical_candidates += int(role == "CANONICAL_SOURCE_CANDIDATE")
        ownership_roles[path] = (role, basis)
        source_id = f"source:ownership-artifact:{_fact_id([root_key, path, record['content_sha256'] or ''])}"
        source_ids[path] = source_id
        source_record = {key: value for key, value in record.items() if key != "id"}
        connection.execute(
            "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?)",
            (
                source_id,
                "ARTIFACT",
                path,
                _source_identity(source_record),
                "LOCAL_SOURCE",
                _json(
                    {
                        "content_sha256": record["content_sha256"],
                        "inventory_run_id": snapshot_run_id,
                        "semantic_reason": record["semantic_reason"],
                    }
                ),
            ),
        )
        entity_id = _entity_id("OWNERSHIP_PATH", root_key, path)
        ownership_ids[path] = entity_id
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                entity_id,
                "OWNERSHIP_PATH",
                PurePosixPath(path).name,
                path,
                source_id,
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "canonicality_claimed": False,
                        "content_sha256": record["content_sha256"],
                        "git_blob_oid": record["git_blob_oid"],
                        "git_tracked": bool(record["git_tracked"]),
                        "role": role,
                        "role_basis": basis,
                    }
                ),
            ),
        )

    owner_contract_bindings = 0
    owner_contract_missing_paths = 0
    for contract in owner_contracts:
        source_id = source_ids[contract["manifest_path"]]
        contract_id = _entity_id("CAPABILITY_OWNER_CONTRACT", root_key, contract["id"])
        owner_id = _entity_id("DECLARED_CAPABILITY_OWNER", root_key, contract["owner"])
        binding_groups = {
            "DECLARES_IMPLEMENTATION_RESPONSIBILITY_FOR": contract[
                "implementation_paths"
            ],
            "DECLARES_CONFIGURATION_RESPONSIBILITY_FOR": contract[
                "configuration_paths"
            ],
            "DECLARES_PROOF_RESPONSIBILITY_FOR": contract["proof_paths"],
        }
        missing_paths = sorted(
            path
            for paths in binding_groups.values()
            for path in paths
            if path not in ownership_ids
        )
        owner_contract_missing_paths += len(missing_paths)
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                contract_id,
                "CAPABILITY_OWNER_CONTRACT",
                contract["id"],
                f"capability:{contract['id']}",
                source_id,
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "canonicality_claimed": False,
                        "claim": contract["claim"],
                        "declaration_only": True,
                        "execution_authority_granted": False,
                        "manifest_path": contract["manifest_path"],
                        "manifest_sha256": contract["manifest_sha256"],
                        "missing_declared_paths": missing_paths,
                        "owner": contract["owner"],
                        "responsibility": contract["responsibility"],
                        "validation": "CANONICAL_CAPABILITY_MANIFEST_VALIDATOR",
                    }
                ),
            ),
        )
        connection.execute(
            "INSERT OR IGNORE INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                owner_id,
                "DECLARED_CAPABILITY_OWNER",
                contract["owner"],
                contract["owner"],
                source_id,
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "canonicality_claimed": False,
                        "declaration_only": True,
                        "execution_authority_granted": False,
                    }
                ),
            ),
        )
        _insert_relation(
            connection,
            subject=repository_id,
            predicate="DECLARES_CAPABILITY_OWNER_CONTRACT",
            object_=contract_id,
            source_id=source_id,
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
            attributes={"authority": "DECLARATION_ONLY"},
        )
        _insert_relation(
            connection,
            subject=contract_id,
            predicate="DECLARES_RESPONSIBLE_OWNER",
            object_=owner_id,
            source_id=source_id,
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
            attributes={"authority": "DECLARATION_ONLY"},
        )
        for predicate, paths in binding_groups.items():
            for path in paths:
                target_id = ownership_ids.get(path)
                if target_id is None:
                    continue
                _insert_relation(
                    connection,
                    subject=owner_id,
                    predicate=predicate,
                    object_=target_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "authority": "DECLARATION_ONLY",
                        "capability_id": contract["id"],
                    },
                )
                owner_contract_bindings += 1
    head = inventory.manifest["git"].get("head")
    lineage = None
    scoped_inventory = inventory.manifest["scan"].get("scope") == EXPLICIT_FILE_SCOPE
    if isinstance(head, str) and head and not scoped_inventory:
        try:
            lineage = collect_recent_lineage(
                root,
                head,
                [path for path, entity_id in ownership_ids.items() if entity_id],
                current_paths=[record["path"] for record in available_records],
                current_blob_oids={
                    record["path"]: record["git_blob_oid"]
                    for record in records
                    if record["suffix"].casefold() == ".py"
                    and record["git_tracked"]
                    and record["git_status"] == "  "
                    and record["git_blob_oid"]
                },
            )
        except HistoryError as exc:
            raise MapperError(str(exc)) from exc
    commit_ids: dict[str, str] = {}
    git_change_count = 0
    git_rename_count = 0
    git_exact_blob_rename_boundaries = 0
    git_exact_historical_symbols = 0
    git_deleted_python_declarations = 0
    historical_ids: dict[str, str] = {}
    deleted_ids: dict[str, str] = {}
    if lineage is not None:
        for commit in lineage["commits"]:
            object_id = commit["commit"]
            source_id = f"source:git-commit:{object_id}"
            connection.execute(
                "INSERT INTO sources VALUES (?,?,?,?,?,?)",
                (
                    source_id,
                    "GIT_OBJECT",
                    None,
                    object_id,
                    "LOCAL_METADATA",
                    _json({"commit": object_id, "head": head}),
                ),
            )
            commit_id = _entity_id("GIT_COMMIT", root_key, object_id)
            commit_ids[object_id] = commit_id
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    commit_id,
                    "GIT_COMMIT",
                    object_id[:12],
                    object_id,
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_METADATA",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(commit),
                ),
            )
        for rename in lineage["renames"]:
            source_id = f"source:git-commit:{rename['commit']}"
            for path in (rename["old_path"], rename["new_path"]):
                if path in ownership_ids or path in historical_ids:
                    continue
                historical_id = _entity_id("HISTORICAL_PATH", root_key, path)
                historical_ids[path] = historical_id
                connection.execute(
                    "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        historical_id,
                        "HISTORICAL_PATH",
                        PurePosixPath(path).name,
                        path,
                        source_id,
                        "OBSERVED",
                        producer_id,
                        snapshot_run_id,
                        "LOCAL_METADATA",
                        snapshot_run_id,
                        snapshot_run_id,
                        _json(
                            {
                                "canonicality_claimed": False,
                                "current_path": rename["current_path"],
                                "historical_path": path,
                                "rename_detection": "GIT_SIMILARITY_HEURISTIC",
                                "search_text": (
                                    "historical path rename lineage moved evolution"
                                ),
                            }
                        ),
                    ),
                )
        for rename in lineage["renames"]:
            source_id = f"source:git-commit:{rename['commit']}"
            old_id = ownership_ids.get(rename["old_path"]) or historical_ids.get(
                rename["old_path"]
            )
            new_id = ownership_ids.get(rename["new_path"]) or historical_ids.get(
                rename["new_path"]
            )
            current_id = ownership_ids.get(rename["current_path"])
            if old_id is None or new_id is None or current_id is None:
                raise MapperError("Git rename lineage did not resolve to mapped paths")
            attributes = {
                "canonicality_claimed": False,
                "commit": rename["commit"],
                "current_blob_oid": rename["current_blob_oid"],
                "current_path": rename["current_path"],
                "detection": "GIT_SIMILARITY_HEURISTIC",
                "exact_current_blob_continuity": rename[
                    "exact_current_blob_continuity"
                ],
                "new_blob_oid": rename["new_blob_oid"],
                "old_blob_oid": rename["old_blob_oid"],
                "similarity_percent": rename["similarity_percent"],
                "status": rename["status"],
            }
            _insert_relation(
                connection,
                subject=old_id,
                predicate="RENAMED_PATH_TO",
                object_=new_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                attributes=attributes,
                truth_class="OBSERVED",
            )
            _insert_relation(
                connection,
                subject=old_id,
                predicate="HISTORICAL_PREDECESSOR_OF_CURRENT_PATH",
                object_=current_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                attributes=attributes,
                truth_class="OBSERVED",
            )
            git_rename_count += 1
            if not rename["exact_current_blob_continuity"]:
                continue
            git_exact_blob_rename_boundaries += 1
            current_symbols = connection.execute(
                """SELECT e.entity_id,e.name,e.qualified_name,e.attributes_json
                     FROM entities e JOIN sources s ON s.source_id=e.source_id
                    WHERE e.entity_kind='PYTHON_SYMBOL' AND s.path=?
                    ORDER BY e.entity_id""",
                (rename["current_path"],),
            ).fetchall()
            for symbol in current_symbols:
                symbol_attributes = json.loads(symbol["attributes_json"])
                if symbol_attributes.get("symbol_kind") not in {
                    "ASYNC_FUNCTION",
                    "ASYNC_METHOD",
                    "CLASS",
                    "FUNCTION",
                    "METHOD",
                }:
                    continue
                definitions = [
                    item
                    for item in symbol_attributes.get("definitions", [])
                    if item.get("path") == rename["current_path"]
                ]
                if len(definitions) != 1:
                    continue
                definition = definitions[0]
                occurrence_id = _entity_id(
                    "HISTORICAL_SYMBOL_OCCURRENCE",
                    root_key,
                    ":".join(
                        (
                            rename["commit"],
                            rename["old_path"],
                            symbol["entity_id"],
                        )
                    ),
                )
                occurrence_attributes = {
                    "canonicality_claimed": False,
                    "content_loaded_from_history": False,
                    "current_blob_oid": rename["current_blob_oid"],
                    "current_path": rename["current_path"],
                    "current_qualified_name": symbol["qualified_name"],
                    "current_symbol_id": symbol["entity_id"],
                    "exact_blob_continuity": True,
                    "historical_blob_oid": rename["old_blob_oid"],
                    "historical_path": rename["old_path"],
                    "module_identity_claimed": False,
                    "restoration_permitted": False,
                    "search_text": (
                        "historical symbol rename lineage evolution changed"
                    ),
                    "semantic_identity_inferred": False,
                    "span": definition["span"],
                    "symbol_kind": symbol_attributes["symbol_kind"],
                }
                connection.execute(
                    "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        occurrence_id,
                        "HISTORICAL_SYMBOL_OCCURRENCE",
                        symbol["name"],
                        f"{rename['old_path']}::{symbol['name']}",
                        source_id,
                        "PROVEN",
                        producer_id,
                        snapshot_run_id,
                        "LOCAL_METADATA",
                        snapshot_run_id,
                        snapshot_run_id,
                        _json(occurrence_attributes),
                    ),
                )
                observation_id = _insert_observation(
                    connection,
                    entity_id=occurrence_id,
                    predicate="EXACT_HISTORICAL_SYMBOL_OCCURRENCE",
                    value=occurrence_attributes,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                )
                _insert_location(
                    connection,
                    fact_id=observation_id,
                    source_id=source_id,
                    path=rename["old_path"],
                    span=definition["span"],
                )
                _insert_relation(
                    connection,
                    subject=old_id,
                    predicate="CONTAINS_EXACT_HISTORICAL_SYMBOL",
                    object_=occurrence_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "content_loaded_from_history": False,
                        "exact_blob_continuity": True,
                    },
                )
                _insert_relation(
                    connection,
                    subject=occurrence_id,
                    predicate="EXACT_BLOB_CONTINUITY_TO_CURRENT_SYMBOL",
                    object_=symbol["entity_id"],
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "module_identity_claimed": False,
                        "semantic_identity_inferred": False,
                    },
                )
                git_exact_historical_symbols += 1
        deleted_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for deletion in lineage["deleted_paths"]:
            deleted_by_path[deletion["path"]].append(deletion)
        for path, deletions in sorted(deleted_by_path.items()):
            most_recent = deletions[0]
            source_id = f"source:git-commit:{most_recent['commit']}"
            deleted_id = _entity_id("DELETED_PATH", root_key, path)
            deleted_ids[path] = deleted_id
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    deleted_id,
                    "DELETED_PATH",
                    PurePosixPath(path).name,
                    path,
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_METADATA",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "canonicality_claimed": False,
                            "content_loaded": False,
                            "current_path": False,
                            "deletion_events": len(deletions),
                            "last_blob_oid": most_recent["last_blob_oid"],
                            "most_recent_deletion_commit": most_recent["commit"],
                            "restoration_permitted": False,
                            "search_text": (
                                "deleted historical path removed lost forgotten"
                            ),
                        }
                    ),
                ),
            )
            for deletion in deletions:
                _insert_relation(
                    connection,
                    subject=commit_ids[deletion["commit"]],
                    predicate="DELETED_HISTORICAL_PATH",
                    object_=deleted_id,
                    source_id=f"source:git-commit:{deletion['commit']}",
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "canonicality_claimed": False,
                        "last_blob_oid": deletion["last_blob_oid"],
                        "parent": deletion["parent"],
                        "restoration_permitted": False,
                        "status": "D",
                    },
                )
        for record in lineage["deleted_python_declarations"]:
            declaration = record["declaration"]
            source_id = f"source:git-commit:{record['commit']}"
            deleted_id = deleted_ids[record["path"]]
            occurrence_id = _entity_id(
                "DELETED_PYTHON_DECLARATION",
                root_key,
                ":".join(
                    (
                        record["commit"],
                        record["last_blob_oid"],
                        record["path"],
                        declaration["qualified_name"],
                        declaration["kind"],
                        str(declaration["span"]["line_start"]),
                        str(declaration["span"]["column_start"]),
                    )
                ),
            )
            attributes = {
                "blob_bytes": record["blob_bytes"],
                "body_persisted": False,
                "canonicality_claimed": False,
                "content_loaded_for_parse": True,
                "content_persisted": False,
                "current_definition_match_claimed": False,
                "deletion_commit": record["commit"],
                "historical_blob_oid": record["last_blob_oid"],
                "historical_path": record["path"],
                "qualified_name": declaration["qualified_name"],
                "restoration_permitted": False,
                "search_text": (
                    "deleted python declaration historical symbol evolution "
                    "lost forgotten removed"
                ),
                "span": declaration["span"],
                "symbol_kind": declaration["kind"],
            }
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    occurrence_id,
                    "DELETED_PYTHON_DECLARATION",
                    declaration["name"],
                    f"{record['path']}::{declaration['qualified_name']}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_METADATA",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(attributes),
                ),
            )
            observation_id = _insert_observation(
                connection,
                entity_id=occurrence_id,
                predicate="EXACT_DELETED_PYTHON_DECLARATION",
                value=attributes,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=observation_id,
                source_id=source_id,
                path=record["path"],
                span=declaration["span"],
            )
            _insert_relation(
                connection,
                subject=deleted_id,
                predicate="CONTAINS_EXACT_DELETED_PYTHON_DECLARATION",
                object_=occurrence_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                attributes={
                    "body_persisted": False,
                    "historical_blob_oid": record["last_blob_oid"],
                    "restoration_permitted": False,
                },
            )
            git_deleted_python_declarations += 1
        for change in lineage["changes"]:
            path_id = ownership_ids.get(change["path"]) or historical_ids.get(
                change["path"]
            )
            commit_id = commit_ids.get(change["commit"])
            if path_id is None or commit_id is None:
                continue
            source_id = f"source:git-commit:{change['commit']}"
            _insert_relation(
                connection,
                subject=commit_id,
                predicate=(
                    "CHANGED_CURRENT_PATH"
                    if change["path"] in ownership_ids
                    else "CHANGED_HISTORICAL_PATH"
                ),
                object_=path_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                attributes={
                    "current_path": change["current_path"],
                    "status": change["status"],
                },
            )
            git_change_count += 1

        lineage_summary_id = _entity_id("GIT_LINEAGE_SUMMARY", root_key, head)
        lineage_summary_attributes = {
            "absence_claim_permitted": False,
            "canonicality_claimed": False,
            "change_relations": git_change_count,
            "commits": len(commit_ids),
            "deleted_paths": len(deleted_ids),
            "deleted_python_declarations": git_deleted_python_declarations,
            "deletion_events": sum(len(items) for items in deleted_by_path.values()),
            "exact_blob_rename_boundaries": git_exact_blob_rename_boundaries,
            "exact_historical_symbols": git_exact_historical_symbols,
            "head": head,
            "head_ancestry_commits": lineage["coverage"]["head_ancestry_commits"],
            "head_ancestry_complete": lineage["coverage"]["head_ancestry_complete"],
            "history_commit_cap": lineage["coverage"]["history_commit_cap"],
            "merge_combined_changes": lineage["coverage"]["merge_combined_changes"],
            "renames": git_rename_count,
            "restoration_permitted": False,
            "search_text": (
                "git history historical lineage changed rename deleted deletion "
                "removed lost forgotten evolution blob deleted python declaration "
                "historical symbol symbol evolution"
            ),
            "whole_history_claimed": False,
        }
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                lineage_summary_id,
                "GIT_LINEAGE_SUMMARY",
                "Git lineage summary",
                f"git-lineage:{head}",
                f"source:git-commit:{head}",
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_METADATA",
                snapshot_run_id,
                snapshot_run_id,
                _json(lineage_summary_attributes),
            ),
        )
        _insert_relation(
            connection,
            subject=repository_id,
            predicate="HAS_GIT_LINEAGE_SUMMARY",
            object_=lineage_summary_id,
            source_id=f"source:git-commit:{head}",
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
            attributes={
                "absence_claim_permitted": False,
                "authority_granted": False,
                "restoration_permitted": False,
            },
        )

    codeowner_rules = 0
    for record in records:
        if PurePosixPath(record["path"]).name.casefold() != "codeowners":
            continue
        try:
            raw = read_exact_artifact(root, record)
            text = raw.decode("utf-8", "strict")
        except (PythonMapError, UnicodeDecodeError) as exc:
            raise MapperError(
                f"CODEOWNERS read failed: {record['path']}: {exc}"
            ) from exc
        source_id = next(
            row[0]
            for row in connection.execute(
                "SELECT source_id FROM sources WHERE path=? ORDER BY source_id LIMIT 1",
                (record["path"],),
            )
        )
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            fields = stripped.split()
            if len(fields) < 2:
                continue
            pattern, owners = fields[0], fields[1:]
            rule_id = _entity_id(
                "CODEOWNER_RULE",
                root_key,
                f"{record['path']}:{line_number}:{pattern}:{' '.join(owners)}",
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    rule_id,
                    "CODEOWNER_RULE",
                    pattern,
                    f"{record['path']}:{line_number}:{pattern}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "canonicality_claimed": False,
                            "line": line_number,
                            "owners": owners,
                            "pattern": pattern,
                            "resolution": "DECLARATION_ONLY",
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=repository_id,
                predicate="DECLARES_CODEOWNER_RULE",
                object_=rule_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            codeowner_rules += 1

    exact_variant_groups = 0
    exact_variant_bindings = 0
    for group in connection.execute(
        """SELECT entity_id FROM entities
           WHERE entity_kind='DUPLICATE_GROUP' ORDER BY entity_id"""
    ):
        members = [
            row
            for row in connection.execute(
                """SELECT member.qualified_name AS path
                   FROM relations relation
                   JOIN entities member ON member.entity_id=relation.object_id
                   WHERE relation.subject_id=?
                     AND relation.predicate='HAS_EXACT_DUPLICATE_MEMBER'
                   ORDER BY member.qualified_name""",
                (group["entity_id"],),
            )
            if row["path"] in ownership_ids
        ]
        if len(members) < 2:
            continue
        exact_variant_groups += 1
        for member in members:
            path = member["path"]
            role, basis = ownership_roles[path]
            _insert_relation(
                connection,
                subject=group["entity_id"],
                predicate="HAS_EXACT_CONTENT_OWNERSHIP_VARIANT",
                object_=ownership_ids[path],
                source_id=source_ids[path],
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                attributes={
                    "canonicality_claimed": False,
                    "cleanup_permitted": False,
                    "deletion_permitted": False,
                    "path_role": role,
                    "path_role_basis": basis,
                    "variant_class": "EXACT_CONTENT",
                },
            )
            exact_variant_bindings += 1

    connection.executemany(
        "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            (
                producer_id,
                "git_lineage",
                "HEAD_ANCESTRY_PATH_GIT_LINEAGE",
                "head-ancestry-up-to-2048",
                "PARTIAL" if lineage is not None else "NOT_APPLICABLE",
                lineage["coverage"]["head_ancestry_commits"]
                if lineage is not None
                else 0,
                len(lineage["commits"]) if lineage is not None else 0,
                0,
                0,
                0,
                _json(
                    lineage["coverage"]
                    if lineage is not None
                    else {"reason": "historical-content-excluded-by-explicit-file-scope" if scoped_inventory else "inventory-root-has-no-head"}
                ),
            ),
            (
                producer_id,
                "ownership_canonicality",
                "PATH_ROLE_AND_DECLARED_CODEOWNER",
                "semantic-eligible-plus-declared-current-files",
                "PARTIAL",
                len(records),
                len(records),
                0,
                0,
                0,
                _json(
                    {
                        "canonical_authority_inferred": False,
                        "codeowner_glob_resolution": "UNSUPPORTED",
                        "explicit_governed_owner_contracts": "CAPABILITY_ADOPTION_MANIFESTS_DECLARATION_ONLY",
                        "exact_content_variant_bindings": exact_variant_bindings,
                        "exact_content_variant_groups": exact_variant_groups,
                        "owner_contract_failures": owner_contract_failures,
                        "owner_contract_missing_paths": owner_contract_missing_paths,
                        "nested_repository_resolution": "PARTIAL_ROOT_ONLY",
                    }
                ),
            ),
            (
                producer_id,
                "ownership_canonicality",
                "CAPABILITY_OWNER_CONTRACT_DECLARATION",
                "capabilities/manifests/*.json",
                (
                    "COVERED"
                    if not owner_contract_failures and owner_contract_missing_paths == 0
                    else "PARTIAL"
                ),
                len(contract_records),
                len(owner_contracts),
                len(owner_contract_failures),
                0,
                0,
                _json(
                    {
                        "canonical_authority_inferred": False,
                        "declaration_only": True,
                        "execution_authority_granted": False,
                        "failures": owner_contract_failures,
                        "missing_declared_paths": owner_contract_missing_paths,
                        "validator": "twin_core.capability_adoption.inspect_capability_manifest",
                    }
                ),
            ),
        ),
    )
    connection.executemany(
        "INSERT INTO map_views VALUES (?,?,?,?,?)",
        (
            (
                "git_lineage",
                "6",
                "AVAILABLE_SEARCHABLE_LINEAGE_SUMMARY_AND_EXACT_HISTORY_FACTS_PARTIAL",
                _json(
                    [
                        "GIT_COMMIT",
                        "GIT_LINEAGE_SUMMARY",
                        "HISTORICAL_PATH",
                        "HISTORICAL_SYMBOL_OCCURRENCE",
                        "DELETED_PATH",
                        "CHANGED_CURRENT_PATH",
                        "CHANGED_HISTORICAL_PATH",
                        "RENAMED_PATH_TO",
                        "HISTORICAL_PREDECESSOR_OF_CURRENT_PATH",
                        "DELETED_HISTORICAL_PATH",
                        "CONTAINS_EXACT_HISTORICAL_SYMBOL",
                        "EXACT_BLOB_CONTINUITY_TO_CURRENT_SYMBOL",
                        "HAS_GIT_LINEAGE_SUMMARY",
                    ]
                ),
                _json(
                    {
                        "history_commit_cap": 2048,
                        "head_ancestry_complete_when_within_cap": True,
                        "historical_content_loaded": False,
                        "historical_symbol_scope": "CURRENT_DECLARATIONS_OVER_EXACT_UNCHANGED_BLOB_RENAMES_ONLY",
                        "rename_detection": "OBSERVED_GIT_SIMILARITY_M50",
                        "symbol_lineage": False,
                    }
                ),
            ),
            (
                "ownership_canonicality",
                "2",
                "AVAILABLE_PATH_ROLE_OWNER_CONTRACT_AND_EXACT_VARIANTS_PARTIAL",
                _json(
                    [
                        "OWNERSHIP_PATH",
                        "CODEOWNER_RULE",
                        "CAPABILITY_OWNER_CONTRACT",
                        "DECLARED_CAPABILITY_OWNER",
                        "DECLARES_CODEOWNER_RULE",
                        "DECLARES_CAPABILITY_OWNER_CONTRACT",
                        "DECLARES_RESPONSIBLE_OWNER",
                        "DECLARES_IMPLEMENTATION_RESPONSIBILITY_FOR",
                        "DECLARES_CONFIGURATION_RESPONSIBILITY_FOR",
                        "DECLARES_PROOF_RESPONSIBILITY_FOR",
                        "HAS_EXACT_CONTENT_OWNERSHIP_VARIANT",
                    ]
                ),
                _json(
                    {
                        "canonicality_claimed": False,
                        "governed_owner_contracts": "CAPABILITY_ADOPTION_MANIFEST_DECLARATIONS",
                        "owner_contracts_grant_authority": False,
                        "variants_via_exact_duplicates": True,
                        "variant_direction_claimed": False,
                    }
                ),
            ),
        ),
    )
    return {
        "git_commits_mapped": len(commit_ids),
        "git_current_path_changes": git_change_count,
        "git_renames_mapped": git_rename_count,
        "git_exact_blob_rename_boundaries": git_exact_blob_rename_boundaries,
        "git_exact_historical_symbols_mapped": git_exact_historical_symbols,
        "git_deleted_python_declarations_mapped": git_deleted_python_declarations,
        "git_lineage_summaries_mapped": int(lineage is not None),
        "git_historical_paths_mapped": len(historical_ids),
        "git_deleted_paths_mapped": len(deleted_ids),
        "git_deletion_events_mapped": sum(
            len(items) for items in deleted_by_path.values()
        )
        if lineage is not None
        else 0,
        "ownership_paths": len(ownership_ids),
        "canonical_source_candidates": canonical_candidates,
        "codeowner_rules": codeowner_rules,
        "capability_owner_contracts": len(owner_contracts),
        "capability_owner_contract_bindings": owner_contract_bindings,
        "capability_owner_contract_failures": len(owner_contract_failures),
        "capability_owner_contract_missing_paths": owner_contract_missing_paths,
        "exact_content_ownership_variant_groups": exact_variant_groups,
        "exact_content_ownership_variant_bindings": exact_variant_bindings,
    }


def _build_governance_maps(
    connection: sqlite3.Connection,
    *,
    inventory: NavigationRun,
    root_key: str,
    repository_id: str,
    producer_id: str,
    snapshot_run_id: str,
) -> dict[str, int]:
    """Project strict governed documents, explicit IDs and exact evidence links."""

    inventory_connection = _inventory_connection(inventory)
    try:
        records = [
            dict(row)
            for row in inventory_connection.execute(
                """SELECT * FROM files
                   WHERE kind='regular' AND semantic_eligible=1
                     AND suffix IN ('.json','.md')
                     AND (
                       path LIKE 'architecture/%' OR path LIKE 'contracts/%'
                       OR path LIKE 'programme/%' OR path LIKE 'receipts/%'
                       OR path LIKE 'work_orders/%'
                     )
                   ORDER BY path"""
            )
        ]
        inventory_hash_by_path = {
            row["path"]: row["content_sha256"]
            for row in inventory_connection.execute(
                "SELECT path,content_sha256 FROM files ORDER BY path"
            )
        }
        reference_target_by_path = {
            row["path"]: dict(row)
            for row in inventory_connection.execute(
                """SELECT * FROM files
                   WHERE kind='regular' AND semantic_reason!='sensitive-path'
                   ORDER BY path"""
            )
        }
    finally:
        inventory_connection.close()
    root = Path(inventory.manifest["root"]["path"]).resolve(strict=True)
    parsed: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for record in records:
        path = record["path"]
        try:
            raw = read_exact_artifact(root, record)
            if record["suffix"] == ".json":
                value = strict_json_object(raw)
                parsed.append(
                    {
                        "record": record,
                        "raw": raw,
                        "json": value,
                        "json_path_references": exact_json_path_references(value),
                    }
                )
            else:
                declarations = explicit_markdown_declarations(raw)
                headings = governed_markdown_headings(raw)
                path_references = explicit_markdown_path_references(raw)
                parsed.append(
                    {
                        "record": record,
                        "raw": raw,
                        "declarations": declarations,
                        "headings": headings,
                        "path_references": path_references,
                    }
                )
        except (PythonMapError, GovernanceMapError) as exc:
            failures.append({"path": path, "reason": str(exc)})

    document_ids: dict[str, str] = {}
    hash_targets: dict[str, list[str]] = {}
    json_documents: list[dict[str, Any]] = []
    explicit_declarations = 0
    claimed_statuses = 0
    valid_self_hashes = 0
    quality_check_claims = 0
    quality_check_claims_rejected = 0
    quality_check_current_module_links = 0
    quality_check_current_path_refs = 0
    quality_claim_documents_covered = 0
    quality_claim_documents_unsupported = 0
    governed_heading_count = 0
    governed_heading_hierarchy_links = 0
    governed_heading_declaration_links = 0
    governed_path_references = 0
    governed_path_references_resolved = 0
    governed_path_references_unresolved = 0
    governed_path_references_ambiguous = 0
    governed_path_reference_heading_links = 0
    governed_path_reference_module_links = 0
    governed_json_path_references = 0
    governed_json_path_references_resolved = 0
    governed_json_path_references_unresolved = 0
    governed_json_path_reference_module_links = 0
    current_python_modules_by_path: dict[str, list[str]] = {}
    for module_id, attributes_json in connection.execute(
        """SELECT entity_id,attributes_json FROM entities
           WHERE entity_kind='PYTHON_MODULE' ORDER BY entity_id"""
    ):
        attributes = json.loads(attributes_json)
        artifact_path = attributes.get("artifact_path")
        if isinstance(artifact_path, str):
            current_python_modules_by_path.setdefault(artifact_path, []).append(
                module_id
            )
    for item in parsed:
        record = item["record"]
        path = record["path"]
        source_id = f"source:governed-document:{_fact_id([root_key, path, record['content_sha256'] or ''])}"
        source_record = {key: value for key, value in record.items() if key != "id"}
        connection.execute(
            "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?)",
            (
                source_id,
                "ARTIFACT",
                path,
                _source_identity(source_record),
                "LOCAL_SOURCE",
                _json(
                    {
                        "content_sha256": record["content_sha256"],
                        "inventory_run_id": snapshot_run_id,
                        "semantic_reason": record["semantic_reason"],
                    }
                ),
            ),
        )
        document_hash_state = "NOT_APPLICABLE"
        if "json" in item:
            value = item["json"]
            kind = governed_document_kind(path, value)
            hash_state = self_hash_state(value)
            document_hash_state = hash_state
            valid_self_hashes += int(hash_state == "VALID")
            attributes = {
                "authority_granted_by_map": False,
                "content_sha256": record["content_sha256"],
                "declared_authority": value.get("authority"),
                "declared_authority_granted": value.get("authority_granted"),
                "declared_schema": value.get("schema"),
                "document_kind": kind,
                "explicit_json_path_references": len(item["json_path_references"]),
                "self_hash_state": hash_state,
                "status_is_document_claim": True,
            }
            json_documents.append({**item, "kind": kind, "hash_state": hash_state})
        else:
            kind = "GOVERNED_MARKDOWN"
            attributes = {
                "authority_granted_by_map": False,
                "content_sha256": record["content_sha256"],
                "document_kind": kind,
                "explicit_declarations": len(item["declarations"]),
                "governed_headings": len(item["headings"]),
                "explicit_path_references": len(item["path_references"]),
                "heading_text_is_authority": False,
                "path_reference_is_governance_binding": False,
                "prose_body_parsed": False,
                "prose_similarity_links": False,
            }
        document_id = _entity_id(kind, root_key, path)
        document_ids[path] = document_id
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                document_id,
                kind,
                PurePosixPath(path).name,
                path,
                source_id,
                "PROVEN",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE",
                snapshot_run_id,
                snapshot_run_id,
                _json(attributes),
            ),
        )
        _insert_relation(
            connection,
            subject=repository_id,
            predicate="DECLARES_GOVERNED_DOCUMENT",
            object_=document_id,
            source_id=source_id,
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
        )
        if "json" in item and document_hash_state == "VALID":
            parsed_quality = parse_receipt_quality_claims(item["json"])
            if parsed_quality["proof_array_supported"]:
                quality_claim_documents_covered += 1
            else:
                quality_claim_documents_unsupported += 1
            quality_check_claims_rejected += parsed_quality["rejected_items"]
            for claim in parsed_quality["claims"]:
                claim_id = _entity_id(
                    "QUALITY_CHECK_CLAIM",
                    root_key,
                    f"{path}#proof:{claim['index']}:{claim['proof_id']}",
                )
                current_path_refs = []
                for candidate in claim["command_repository_path_candidates"]:
                    content_sha256 = inventory_hash_by_path.get(candidate["path"])
                    if not content_sha256:
                        continue
                    current_path_refs.append(
                        {
                            **candidate,
                            "content_sha256": content_sha256,
                            "execution_source_binding": False,
                            "match_semantics": "LEXICAL_CURRENT_INVENTORY_PATH",
                        }
                    )
                quality_check_current_path_refs += len(current_path_refs)
                attributes = {
                    **claim,
                    "authority_granted_by_map": False,
                    "current_inventory_path_refs": current_path_refs,
                    "source_receipt_path": path,
                    "source_receipt_self_hash_state": document_hash_state,
                    "search_text": " ".join(
                        [
                            claim["proof_id"],
                            claim["check_family"],
                            claim["reported_status"],
                            claim["reported_result"],
                            *claim["command"],
                        ]
                    ),
                }
                connection.execute(
                    "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        claim_id,
                        "QUALITY_CHECK_CLAIM",
                        claim["proof_id"],
                        f"{path}#proof:{claim['proof_id']}",
                        source_id,
                        "OBSERVED",
                        producer_id,
                        snapshot_run_id,
                        "LOCAL_SOURCE",
                        snapshot_run_id,
                        snapshot_run_id,
                        _json(attributes),
                    ),
                )
                _insert_relation(
                    connection,
                    subject=document_id,
                    predicate="DOCUMENT_CLAIMS_QUALITY_CHECK",
                    object_=claim_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={
                        "proof_id": claim["proof_id"],
                        "reported_status": claim["reported_status"],
                    },
                )
                _insert_observation(
                    connection,
                    entity_id=claim_id,
                    predicate="RECEIPT_REPORTS_QUALITY_STATUS",
                    value={
                        "execution_independently_verified": False,
                        "reported_result": claim["reported_result"],
                        "reported_status": claim["reported_status"],
                        "source_receipt_self_hash_state": document_hash_state,
                    },
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="OBSERVED",
                )
                for current_ref in current_path_refs:
                    for module_id in current_python_modules_by_path.get(
                        current_ref["path"], []
                    ):
                        _insert_relation(
                            connection,
                            subject=claim_id,
                            predicate=(
                                "RECEIPT_COMMAND_LEXICALLY_REFERENCES_CURRENT_MODULE"
                            ),
                            object_=module_id,
                            source_id=source_id,
                            producer_id=producer_id,
                            snapshot_run_id=snapshot_run_id,
                            attributes={
                                **current_ref,
                                "receipt_execution_cwd_proven": False,
                                "receipt_execution_source_binding": False,
                            },
                        )
                        quality_check_current_module_links += 1
                quality_check_claims += 1
        if record["content_sha256"]:
            hash_targets.setdefault(record["content_sha256"], []).append(document_id)
        if "json" in item and document_hash_state == "VALID":
            receipt_hash = item["json"]["receipt_sha256"]
            hash_targets.setdefault(receipt_hash, []).append(document_id)
        if "json" in item and isinstance(item["json"].get("status"), str):
            claimed_statuses += 1
            _insert_observation(
                connection,
                entity_id=document_id,
                predicate="DOCUMENT_CLAIMS_STATUS",
                value={
                    "authoritative_outcome": False,
                    "self_hash_state": document_hash_state,
                    "status": item["json"]["status"],
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
            )
        heading_ids_by_ordinal: dict[int, str] = {}
        heading_ids_by_line: dict[int, str] = {}
        for heading in item.get("headings", ()):
            heading_id = _entity_id(
                "GOVERNED_HEADING",
                root_key,
                f"{path}:{heading['ordinal']}:{heading['heading_level']}:{heading['title']}",
            )
            heading_ids_by_ordinal[heading["ordinal"]] = heading_id
            heading_ids_by_line[heading["line"]] = heading_id
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    heading_id,
                    "GOVERNED_HEADING",
                    heading["title"],
                    f"{path}#heading:{heading['ordinal']}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            **heading,
                            "authority_granted_by_map": False,
                            "heading_text_is_authority": False,
                            "prose_body_parsed": False,
                            "search_text": f"{heading['title']} {path}",
                        }
                    ),
                ),
            )
            heading_location_id = _insert_observation(
                connection,
                entity_id=heading_id,
                predicate="GOVERNED_HEADING_SOURCE_SPAN",
                value={
                    "heading_level": heading["heading_level"],
                    "span": heading["span"],
                    "title": heading["title"],
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=heading_location_id,
                source_id=source_id,
                path=path,
                span=heading["span"],
            )
            _insert_relation(
                connection,
                subject=document_id,
                predicate="DOCUMENT_CONTAINS_HEADING",
                object_=heading_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            parent_ordinal = heading["parent_ordinal"]
            if parent_ordinal is not None:
                _insert_relation(
                    connection,
                    subject=heading_ids_by_ordinal[parent_ordinal],
                    predicate="HEADING_CONTAINS_HEADING",
                    object_=heading_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                )
                governed_heading_hierarchy_links += 1
            governed_heading_count += 1
        for reference in item.get("path_references", ()):
            lexical_path = reference["normalized_path"]
            resolution_candidates = [lexical_path]
            if reference["syntax"] == "MARKDOWN_LINK_DESTINATION":
                document_parent = PurePosixPath(path).parent
                relative_path = (document_parent / lexical_path).as_posix()
                if relative_path not in resolution_candidates:
                    resolution_candidates.append(relative_path)
            resolved_candidates = [
                candidate
                for candidate in resolution_candidates
                if candidate in reference_target_by_path
            ]
            target_path = (
                resolved_candidates[0]
                if len(resolved_candidates) == 1
                else lexical_path
            )
            target_record = (
                reference_target_by_path[target_path]
                if len(resolved_candidates) == 1
                else None
            )
            target_source_identity = None
            if target_record is not None:
                target_source_record = {
                    key: value for key, value in target_record.items() if key != "id"
                }
                target_source_identity = _source_identity(target_source_record)
            if len(resolved_candidates) == 1:
                resolution = "EXACT_CURRENT_INVENTORY_PATH"
            elif resolved_candidates:
                resolution = "AMBIGUOUS_CURRENT_INVENTORY_PATH"
            else:
                resolution = "UNRESOLVED_CURRENT_INVENTORY_PATH"
            reference_id = _entity_id(
                "GOVERNED_PATH_REFERENCE",
                root_key,
                f"{path}:{reference['ordinal']}:{reference['literal']}",
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    reference_id,
                    "GOVERNED_PATH_REFERENCE",
                    target_path,
                    f"{path}#path-reference:{reference['ordinal']}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            **reference,
                            "authority_granted_by_map": False,
                            "governance_binding_claimed": False,
                            "implementation_satisfaction_claimed": False,
                            "resolution": resolution,
                            "resolution_candidates": resolution_candidates,
                            "resolved_path": target_path
                            if target_record is not None
                            else None,
                            "target_content_sha256": None
                            if target_record is None
                            else target_record["content_sha256"],
                            "target_git_tracked": None
                            if target_record is None
                            else bool(target_record["git_tracked"]),
                            "target_source_identity_sha256": target_source_identity,
                            "search_text": f"{reference['literal']} {target_path} {path}",
                        }
                    ),
                ),
            )
            reference_location_id = _insert_observation(
                connection,
                entity_id=reference_id,
                predicate="GOVERNED_EXPLICIT_PATH_REFERENCE_SOURCE_SPAN",
                value={
                    "literal": reference["literal"],
                    "normalized_path": reference["normalized_path"],
                    "resolution": resolution,
                    "resolved_path": target_path if target_record is not None else None,
                    "span": reference["span"],
                    "syntax": reference["syntax"],
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_location(
                connection,
                fact_id=reference_location_id,
                source_id=source_id,
                path=path,
                span=reference["span"],
            )
            _insert_relation(
                connection,
                subject=document_id,
                predicate="DOCUMENT_CONTAINS_EXPLICIT_PATH_REFERENCE",
                object_=reference_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            containing_heading_id = None
            for heading in item.get("headings", ()):
                if heading["line"] > reference["line"]:
                    break
                containing_heading_id = heading_ids_by_ordinal[heading["ordinal"]]
            if containing_heading_id is not None:
                _insert_relation(
                    connection,
                    subject=containing_heading_id,
                    predicate="HEADING_CONTAINS_EXPLICIT_PATH_REFERENCE",
                    object_=reference_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                )
                governed_path_reference_heading_links += 1
            if target_record is not None:
                ownership_id = _entity_id("OWNERSHIP_PATH", root_key, target_path)
                if (
                    connection.execute(
                        "SELECT 1 FROM entities WHERE entity_id=?", (ownership_id,)
                    ).fetchone()
                    is not None
                ):
                    _insert_relation(
                        connection,
                        subject=reference_id,
                        predicate="RESOLVES_TO_CURRENT_OWNERSHIP_PATH",
                        object_=ownership_id,
                        source_id=source_id,
                        producer_id=producer_id,
                        snapshot_run_id=snapshot_run_id,
                        attributes={
                            "canonicality_claimed": False,
                            "match_semantics": "EXACT_CURRENT_INVENTORY_PATH",
                        },
                    )
                for module_id in current_python_modules_by_path.get(target_path, ()):
                    _insert_relation(
                        connection,
                        subject=reference_id,
                        predicate="RESOLVES_TO_CURRENT_PYTHON_MODULE",
                        object_=module_id,
                        source_id=source_id,
                        producer_id=producer_id,
                        snapshot_run_id=snapshot_run_id,
                        attributes={
                            "governance_binding_claimed": False,
                            "match_semantics": "EXACT_CURRENT_INVENTORY_PATH",
                        },
                    )
                    governed_path_reference_module_links += 1
                governed_path_references_resolved += 1
            elif resolved_candidates:
                governed_path_references_ambiguous += 1
            else:
                governed_path_references_unresolved += 1
            governed_path_references += 1
        for declaration in item.get("declarations", ()):
            declaration_id = _entity_id(
                "GOVERNED_DECLARATION", root_key, f"{path}:{declaration['id']}"
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    declaration_id,
                    "GOVERNED_DECLARATION",
                    declaration["id"],
                    f"{path}:{declaration['id']}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            **declaration,
                            "authority_granted_by_map": False,
                            "prose_body_parsed": False,
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=document_id,
                predicate="DECLARES_EXPLICIT_ID",
                object_=declaration_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            heading_id = heading_ids_by_line.get(declaration["line"])
            if heading_id is not None:
                _insert_relation(
                    connection,
                    subject=heading_id,
                    predicate="HEADING_DECLARES_EXPLICIT_ID",
                    object_=declaration_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                )
                governed_heading_declaration_links += 1
            explicit_declarations += 1
        for reference in item.get("json_path_references", ()):
            target_path = reference["normalized_path"]
            target_record = reference_target_by_path.get(target_path)
            target_source_identity = None
            if target_record is not None:
                target_source_record = {
                    key: value for key, value in target_record.items() if key != "id"
                }
                target_source_identity = _source_identity(target_source_record)
            resolution = (
                "EXACT_CURRENT_INVENTORY_PATH"
                if target_record is not None
                else "UNRESOLVED_CURRENT_INVENTORY_PATH"
            )
            reference_id = _entity_id(
                "GOVERNED_JSON_PATH_REFERENCE",
                root_key,
                f"{path}:{reference['json_pointer']}:{reference['literal']}",
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    reference_id,
                    "GOVERNED_JSON_PATH_REFERENCE",
                    target_path,
                    f"{path}#json-pointer:{reference['json_pointer']}",
                    source_id,
                    "PROVEN",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_SOURCE",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            **reference,
                            "authority_granted_by_map": False,
                            "governance_binding_claimed": False,
                            "implementation_satisfaction_claimed": False,
                            "resolution": resolution,
                            "resolved_path": target_path
                            if target_record is not None
                            else None,
                            "target_content_sha256": None
                            if target_record is None
                            else target_record["content_sha256"],
                            "target_git_tracked": None
                            if target_record is None
                            else bool(target_record["git_tracked"]),
                            "target_source_identity_sha256": target_source_identity,
                            "search_text": (
                                f"{reference['field']} {reference['json_pointer']} "
                                f"{reference['literal']} {path}"
                            ),
                        }
                    ),
                ),
            )
            _insert_observation(
                connection,
                entity_id=reference_id,
                predicate="GOVERNED_JSON_PATH_REFERENCE_POINTER",
                value={
                    "field": reference["field"],
                    "json_pointer": reference["json_pointer"],
                    "literal": reference["literal"],
                    "normalized_path": target_path,
                    "resolution": resolution,
                    "resolved_path": target_path if target_record is not None else None,
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            _insert_relation(
                connection,
                subject=document_id,
                predicate="DOCUMENT_CONTAINS_EXPLICIT_JSON_PATH_REFERENCE",
                object_=reference_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
            )
            if target_record is not None:
                ownership_id = _entity_id("OWNERSHIP_PATH", root_key, target_path)
                if (
                    connection.execute(
                        "SELECT 1 FROM entities WHERE entity_id=?", (ownership_id,)
                    ).fetchone()
                    is not None
                ):
                    _insert_relation(
                        connection,
                        subject=reference_id,
                        predicate="RESOLVES_TO_CURRENT_OWNERSHIP_PATH",
                        object_=ownership_id,
                        source_id=source_id,
                        producer_id=producer_id,
                        snapshot_run_id=snapshot_run_id,
                        attributes={
                            "governance_binding_claimed": False,
                            "match_semantics": "EXACT_CURRENT_INVENTORY_PATH",
                        },
                    )
                for module_id in current_python_modules_by_path.get(target_path, ()):
                    _insert_relation(
                        connection,
                        subject=reference_id,
                        predicate="RESOLVES_TO_CURRENT_PYTHON_MODULE",
                        object_=module_id,
                        source_id=source_id,
                        producer_id=producer_id,
                        snapshot_run_id=snapshot_run_id,
                        attributes={
                            "governance_binding_claimed": False,
                            "match_semantics": "EXACT_CURRENT_INVENTORY_PATH",
                        },
                    )
                    governed_json_path_reference_module_links += 1
                governed_json_path_references_resolved += 1
            else:
                governed_json_path_references_unresolved += 1
            governed_json_path_references += 1

    exact_document_links = 0
    exact_payload_bindings = 0
    conflicting_payload_bindings = 0
    for item in json_documents:
        record = item["record"]
        path = record["path"]
        source_id = f"source:governed-document:{_fact_id([root_key, path, record['content_sha256'] or ''])}"
        document_id = document_ids[path]
        if item["hash_state"] == "INVALID":
            continue
        for link in exact_hash_links(item["json"]):
            for target_id in sorted(set(hash_targets.get(link["sha256"], ()))):
                if target_id == document_id:
                    continue
                _insert_relation(
                    connection,
                    subject=document_id,
                    predicate="EXACT_HASH_REFERENCES_DOCUMENT",
                    object_=target_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={"field": link["field"], "sha256": link["sha256"]},
                )
                exact_document_links += 1
        payload = item["json"].get("payload")
        if not isinstance(payload, list):
            continue
        for entry in payload:
            if not isinstance(entry, Mapping):
                continue
            target_path = entry.get("path")
            target_hash = entry.get("sha256")
            if not isinstance(target_path, str) or not isinstance(target_hash, str):
                continue
            actual_hash = inventory_hash_by_path.get(target_path)
            target_id = _entity_id("OWNERSHIP_PATH", root_key, target_path)
            target_exists = connection.execute(
                "SELECT 1 FROM entities WHERE entity_id=?", (target_id,)
            ).fetchone()
            matches = actual_hash == target_hash and target_exists is not None
            if matches:
                _insert_relation(
                    connection,
                    subject=document_id,
                    predicate="BINDS_EXACT_CURRENT_FILE",
                    object_=target_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    attributes={"path": target_path, "sha256": target_hash},
                    truth_class="PROVEN",
                )
                exact_payload_bindings += 1
            else:
                _insert_observation(
                    connection,
                    entity_id=document_id,
                    predicate="PAYLOAD_BINDING_CONFLICT",
                    value={
                        "actual_sha256": actual_hash,
                        "declared_sha256": target_hash,
                        "path": target_path,
                    },
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="CONFLICT" if actual_hash else "UNKNOWN",
                )
                conflicting_payload_bindings += 1

    connection.executemany(
        "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            (
                producer_id,
                "requirements_decisions",
                "STRICT_GOVERNED_DOCUMENT_HEADING_MARKDOWN_JSON_PATH_AND_EXPLICIT_ID",
                "safe-governance-prefix-json-markdown",
                "PARTIAL",
                len(records),
                len(parsed),
                len(failures),
                0,
                0,
                _json(
                    {
                        "explicit_identifier_required": True,
                        "failures": failures,
                        "heading_hierarchy_links": governed_heading_hierarchy_links,
                        "heading_text_is_authority": False,
                        "headings_parsed": governed_heading_count,
                        "path_reference_governance_binding_claimed": False,
                        "path_references_parsed": governed_path_references,
                        "path_references_ambiguous": governed_path_references_ambiguous,
                        "path_references_resolved": governed_path_references_resolved,
                        "path_references_unresolved": governed_path_references_unresolved,
                        "json_path_references_parsed": governed_json_path_references,
                        "json_path_references_resolved": (
                            governed_json_path_references_resolved
                        ),
                        "json_path_references_unresolved": (
                            governed_json_path_references_unresolved
                        ),
                        "policy_sha256": GOVERNANCE_POLICY_SHA256,
                        "prose_body_parsed": False,
                        "prose_similarity_links": False,
                    }
                ),
            ),
            (
                producer_id,
                "evidence_claims",
                "SELF_HASH_STATUS_EXACT_LINK_AND_PAYLOAD_BINDING",
                "safe-governed-json",
                "PARTIAL",
                len(json_documents),
                len(json_documents),
                0,
                0,
                0,
                _json(
                    {
                        "document_status_is_verified_outcome": False,
                        "evidence_filename_is_proof": False,
                        "invalid_self_hash_can_support_claim": False,
                        "policy_sha256": GOVERNANCE_POLICY_SHA256,
                    }
                ),
            ),
            (
                producer_id,
                "quality_findings",
                "SELF_HASHED_RECEIPT_QUALITY_CHECK_CLAIM",
                "safe-governed-json-proof-arrays",
                "PARTIAL",
                len(json_documents),
                quality_claim_documents_covered,
                0,
                quality_claim_documents_unsupported,
                sum(item["hash_state"] != "VALID" for item in json_documents),
                _json(
                    {
                        "execution_independently_verified": False,
                        "invalid_self_hash_can_support_claim": False,
                        "policy_sha256": QUALITY_POLICY_SHA256,
                        "quality_check_claims": quality_check_claims,
                        "current_inventory_module_links": (
                            quality_check_current_module_links
                        ),
                        "current_inventory_path_refs": quality_check_current_path_refs,
                        "current_path_match_proves_execution_source": False,
                        "rejected_proof_items": quality_check_claims_rejected,
                        "status_source": "self-hashed-receipt-report",
                    }
                ),
            ),
        ),
    )
    connection.executemany(
        "INSERT INTO map_views VALUES (?,?,?,?,?)",
        (
            (
                "requirements_decisions",
                "1",
                "AVAILABLE_STRICT_DOCUMENT_HEADING_MARKDOWN_JSON_PATH_AND_EXPLICIT_ID_PARTIAL",
                _json(
                    [
                        "CONTRACT",
                        "DECISION_DOCUMENT",
                        "GOVERNED_DECLARATION",
                        "GOVERNED_DOCUMENT",
                        "GOVERNED_HEADING",
                        "GOVERNED_JSON_PATH_REFERENCE",
                        "GOVERNED_MARKDOWN",
                        "GOVERNED_PATH_REFERENCE",
                        "DOCUMENT_CONTAINS_HEADING",
                        "DOCUMENT_CONTAINS_EXPLICIT_JSON_PATH_REFERENCE",
                        "DOCUMENT_CONTAINS_EXPLICIT_PATH_REFERENCE",
                        "HEADING_CONTAINS_HEADING",
                        "HEADING_CONTAINS_EXPLICIT_PATH_REFERENCE",
                        "HEADING_DECLARES_EXPLICIT_ID",
                        "RESOLVES_TO_CURRENT_OWNERSHIP_PATH",
                        "RESOLVES_TO_CURRENT_PYTHON_MODULE",
                        "REQUIREMENT_POLICY_DOCUMENT",
                        "WORK_ORDER",
                    ]
                ),
                _json(
                    {
                        "prose_similarity": False,
                        "strict_json": True,
                        "explicit_markdown_ids": True,
                        "governed_markdown_headings": True,
                        "governed_markdown_path_references": True,
                        "governed_json_path_references": True,
                        "heading_text_is_authority": False,
                        "path_reference_governance_binding_claimed": False,
                    }
                ),
            ),
            (
                "evidence_claims",
                "1",
                "AVAILABLE_SELF_HASH_AND_EXACT_BINDING_PARTIAL",
                _json(
                    [
                        "EVIDENCE_DOCUMENT",
                        "DOCUMENT_CLAIMS_STATUS",
                        "EXACT_HASH_REFERENCES_DOCUMENT",
                        "BINDS_EXACT_CURRENT_FILE",
                    ]
                ),
                _json(
                    {
                        "status_is_document_claim": True,
                        "payload_hash_binding": True,
                        "outcome_authority": False,
                    }
                ),
            ),
        ),
    )
    return {
        "governed_documents": len(parsed),
        "governed_document_failures": len(failures),
        "explicit_governed_declarations": explicit_declarations,
        "evidence_claimed_statuses": claimed_statuses,
        "evidence_valid_self_hashes": valid_self_hashes,
        "exact_governed_document_links": exact_document_links,
        "exact_evidence_payload_bindings": exact_payload_bindings,
        "evidence_payload_binding_conflicts": conflicting_payload_bindings,
        "quality_check_claims": quality_check_claims,
        "quality_check_claims_rejected": quality_check_claims_rejected,
        "quality_check_current_module_links": quality_check_current_module_links,
        "quality_check_current_path_refs": quality_check_current_path_refs,
        "governed_markdown_headings": governed_heading_count,
        "governed_heading_hierarchy_links": governed_heading_hierarchy_links,
        "governed_heading_declaration_links": governed_heading_declaration_links,
        "governed_markdown_path_references": governed_path_references,
        "governed_markdown_path_references_resolved": governed_path_references_resolved,
        "governed_markdown_path_references_unresolved": governed_path_references_unresolved,
        "governed_markdown_path_references_ambiguous": governed_path_references_ambiguous,
        "governed_path_reference_heading_links": governed_path_reference_heading_links,
        "governed_path_reference_module_links": governed_path_reference_module_links,
        "governed_json_path_references": governed_json_path_references,
        "governed_json_path_references_resolved": governed_json_path_references_resolved,
        "governed_json_path_references_unresolved": governed_json_path_references_unresolved,
        "governed_json_path_reference_module_links": (
            governed_json_path_reference_module_links
        ),
    }


def _build_runtime_maps(
    connection: sqlite3.Connection,
    *,
    registries: Sequence[RuntimeRegistryInput],
    root_key: str,
    repository_id: str,
    producer_id: str,
    snapshot_run_id: str,
) -> dict[str, int]:
    """Project canonical gate status without becoming the liveness authority."""

    capability_count = 0
    active_count = 0
    entrypoint_count = 0
    trigger_count = 0
    receipt_pointer_count = 0
    for runtime_input in registries:
        registry = runtime_input.registry
        source_id = f"source:capability-adoption-registry:{runtime_input.file_sha256}"
        connection.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?)",
            (
                source_id,
                "CAPABILITY_ADOPTION_REGISTRY",
                str(runtime_input.path),
                runtime_input.file_sha256,
                "LOCAL_RUNTIME_METADATA",
                _json(
                    {
                        "authority": registry["authority"],
                        "execution_authority_granted": False,
                        "observed_at": registry["observed_at"],
                        "registry_sha256": registry["registry_sha256"],
                        "source_authority": registry["source_authority"],
                    }
                ),
            ),
        )
        registry_id = _entity_id(
            "RUNTIME_REGISTRY", root_key, registry["registry_sha256"]
        )
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                registry_id,
                "RUNTIME_REGISTRY",
                runtime_input.path.name,
                f"capability-registry:{registry['registry_sha256']}",
                source_id,
                "OBSERVED",
                producer_id,
                snapshot_run_id,
                "LOCAL_RUNTIME_METADATA",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "authority": registry["authority"],
                        "execution_authority_granted": False,
                        "file_sha256": runtime_input.file_sha256,
                        "map_authority": False,
                        "observed_at": registry["observed_at"],
                        "registry_sha256": registry["registry_sha256"],
                        "source_authority": registry["source_authority"],
                    }
                ),
            ),
        )
        _insert_relation(
            connection,
            subject=repository_id,
            predicate="HAS_EXTERNAL_RUNTIME_STATUS_SNAPSHOT",
            object_=registry_id,
            source_id=source_id,
            producer_id=producer_id,
            snapshot_run_id=snapshot_run_id,
            truth_class="OBSERVED",
            attributes={"map_authority": False},
        )
        connection.execute(
            "INSERT INTO run_inputs VALUES (?,?,?,?)",
            (
                f"input:runtime-registry:{runtime_input.file_sha256}",
                "CAPABILITY_ADOPTION_REGISTRY",
                runtime_input.file_sha256,
                _json(runtime_input.manifest_record()),
            ),
        )
        for capability in registry["capabilities"]:
            capability_id = _entity_id(
                "RUNTIME_CAPABILITY",
                root_key,
                f"{registry['registry_sha256']}:{capability['id']}",
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    capability_id,
                    "RUNTIME_CAPABILITY",
                    capability["id"],
                    f"runtime-capability:{capability['id']}",
                    source_id,
                    "OBSERVED",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_RUNTIME_METADATA",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            "claim": capability["claim"],
                            "execution_authority_granted": False,
                            "last_failure_at": capability["last_failure_at"],
                            "last_success_at": capability["last_success_at"],
                            "manifest_sha256": capability["manifest_sha256"],
                            "map_authority": False,
                            "next_check_at": capability["next_check_at"],
                            "observed_at": registry["observed_at"],
                            "owner": capability["owner"],
                            "reason": capability["reason"],
                            "responsibility": capability["responsibility"],
                            "source_authority": registry["source_authority"],
                            "state": capability["state"],
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=registry_id,
                predicate="GATE_REPORTS_CAPABILITY_STATE",
                object_=capability_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
                attributes={
                    "execution_authority_granted": False,
                    "map_authority": False,
                    "state": capability["state"],
                },
            )
            _insert_observation(
                connection,
                entity_id=capability_id,
                predicate="CAPABILITY_AUTHORITY_ENVELOPE",
                value={
                    **capability["authority"],
                    "authority_source": "CAPABILITY_ADOPTION_GATE",
                    "map_authority": False,
                },
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
            )
            _insert_observation(
                connection,
                entity_id=capability_id,
                predicate="CAPABILITY_RECOVERY_DECLARATION",
                value={**capability["recovery"], "execution_observed": False},
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
            )

            entrypoint = capability["entrypoint"]
            entrypoint_id = _entity_id(
                "RUNTIME_ENTRYPOINT",
                root_key,
                f"{registry['registry_sha256']}:{capability['id']}:entrypoint",
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    entrypoint_id,
                    "RUNTIME_ENTRYPOINT",
                    entrypoint["argv"][0],
                    " ".join(entrypoint["argv"]),
                    source_id,
                    "OBSERVED",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_RUNTIME_METADATA",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json(
                        {
                            **entrypoint,
                            "binding": "GATE_REPORTED",
                            "execution_observed_by_map": False,
                        }
                    ),
                ),
            )
            _insert_relation(
                connection,
                subject=capability_id,
                predicate="GATE_BINDS_ENTRYPOINT",
                object_=entrypoint_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
                attributes={"execution_observed_by_map": False},
            )
            entrypoint_count += 1

            trigger = capability["trigger"]
            trigger_id = _entity_id(
                "RUNTIME_TRIGGER",
                root_key,
                f"{registry['registry_sha256']}:{capability['id']}:trigger",
            )
            connection.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    trigger_id,
                    "RUNTIME_TRIGGER",
                    trigger["identity"],
                    f"{trigger['kind']}:{trigger['identity']}",
                    source_id,
                    "OBSERVED",
                    producer_id,
                    snapshot_run_id,
                    "LOCAL_RUNTIME_METADATA",
                    snapshot_run_id,
                    snapshot_run_id,
                    _json({**trigger, "binding": "GATE_REPORTED"}),
                ),
            )
            _insert_relation(
                connection,
                subject=capability_id,
                predicate="GATE_BINDS_TRIGGER",
                object_=trigger_id,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
            )
            trigger_count += 1

            receipt = capability["liveness_receipt"]
            if receipt is not None:
                receipt_id = _entity_id(
                    "RUNTIME_EVIDENCE_POINTER",
                    root_key,
                    f"{registry['registry_sha256']}:{receipt['sha256']}",
                )
                connection.execute(
                    "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        receipt_id,
                        "RUNTIME_EVIDENCE_POINTER",
                        PurePosixPath(receipt["path"]).name,
                        receipt["path"],
                        source_id,
                        "OBSERVED",
                        producer_id,
                        snapshot_run_id,
                        "LOCAL_RUNTIME_METADATA",
                        snapshot_run_id,
                        snapshot_run_id,
                        _json(
                            {
                                **receipt,
                                "content_read_by_mapper": False,
                                "gate_validated": True,
                            }
                        ),
                    ),
                )
                _insert_relation(
                    connection,
                    subject=capability_id,
                    predicate="GATE_BINDS_LIVENESS_RECEIPT",
                    object_=receipt_id,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="OBSERVED",
                )
                receipt_pointer_count += 1
            capability_count += 1
            active_count += int(capability["state"] == "ACTIVE")

    disposition = "COVERED" if registries else "PARTIAL"
    connection.execute(
        "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            producer_id,
            "runtime_topology",
            "CAPABILITY_ADOPTION_REGISTRY",
            "external-runtime-registry-inputs",
            disposition,
            len(registries),
            len(registries),
            0,
            0 if registries else 1,
            0,
            _json(
                {
                    "canonical_liveness_authority": "EXTERNAL_CAPABILITY_ADOPTION_GATE",
                    "map_authority": False,
                    "reason": None
                    if registries
                    else "no runtime registry input supplied",
                    "runtime_process_discovery": False,
                }
            ),
        ),
    )
    connection.execute(
        "INSERT INTO map_views VALUES (?,?,?,?,?)",
        (
            "runtime_topology",
            "1",
            "AVAILABLE_EXTERNAL_GATE_STATUS_PARTIAL",
            _json(
                [
                    "RUNTIME_REGISTRY",
                    "RUNTIME_CAPABILITY",
                    "RUNTIME_ENTRYPOINT",
                    "RUNTIME_TRIGGER",
                    "RUNTIME_EVIDENCE_POINTER",
                ]
            ),
            _json(
                {
                    "canonical_liveness_authority": "EXTERNAL_CAPABILITY_ADOPTION_GATE",
                    "map_authority": False,
                    "query": "capability-owner-entrypoint-trigger-or-receipt",
                }
            ),
        ),
    )
    return {
        "runtime_registry_inputs": len(registries),
        "runtime_capabilities": capability_count,
        "runtime_capabilities_active": active_count,
        "runtime_entrypoints": entrypoint_count,
        "runtime_triggers": trigger_count,
        "runtime_receipt_pointers": receipt_pointer_count,
    }


def _build_semantic_view(
    connection: sqlite3.Connection,
    *,
    semantic_input: Mapping[str, Any] | None,
    producer_id: str,
) -> dict[str, int]:
    """Register the existing semantic graph as a federated, non-authoritative view."""

    if semantic_input is None:
        disposition = "PARTIAL"
        covered = 0
        unsupported = 1
        reason = "no authenticated semantic graph input supplied"
        nodes = 0
        edges = 0
    else:
        freshness = semantic_input["freshness"]
        disposition = "COVERED" if freshness == "CURRENT_INVENTORY_MATCH" else "PARTIAL"
        covered = int(disposition == "COVERED")
        unsupported = int(disposition != "COVERED")
        reason = None if disposition == "COVERED" else freshness
        nodes = semantic_input["graph"]["nodes"]
        edges = semantic_input["graph"]["edges"]
        connection.execute(
            "INSERT INTO run_inputs VALUES (?,?,?,?)",
            (
                f"input:semantic-graph:{semantic_input['manifest_receipt_sha256']}",
                "AUTHENTICATED_LOCAL_SEMANTIC_GRAPH",
                semantic_input["manifest_receipt_sha256"],
                _json(semantic_input),
            ),
        )
    connection.execute(
        "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            producer_id,
            "semantic_graphify",
            "AUTHENTICATED_LOCAL_SEMANTIC_GRAPH",
            "federated-semantic-store",
            disposition,
            1,
            covered,
            0,
            0,
            unsupported,
            _json(
                {
                    "authority_granted": False,
                    "deterministic_fact_override": False,
                    "freshness": None
                    if semantic_input is None
                    else semantic_input["freshness"],
                    "reason": reason,
                    "storage": "federated-authenticated-semantic-store",
                }
            ),
        ),
    )
    connection.execute(
        "INSERT INTO map_views VALUES (?,?,?,?,?)",
        (
            "semantic_graphify",
            "1",
            "AVAILABLE_FEDERATED_LOCAL_GRAPHIFY_PARTIAL",
            _json(["SEMANTIC_CONCEPT", "SEMANTIC_RELATION"]),
            _json(
                {
                    "authority_granted": False,
                    "deterministic_fact_override": False,
                    "query": "label-concept-or-source-location",
                    "storage": "federated-authenticated-semantic-store",
                }
            ),
        ),
    )
    return {
        "semantic_graph_inputs": int(semantic_input is not None),
        "semantic_nodes_available": nodes,
        "semantic_edges_available": edges,
    }


def _previous_python_group_reusable(
    previous: MapperRun | None, invalidation_key_sha256: str
) -> bool:
    if previous is None:
        return False
    database_path = previous.run_directory / "facts.sqlite3"
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        schema = connection.execute(
            "SELECT value FROM meta WHERE key='database_schema'"
        ).fetchone()
        if schema != (str(DATABASE_SCHEMA),):
            return False
        rows = connection.execute(
            f"""SELECT producer_id,invalidation_key_sha256
                FROM producer_inputs
                WHERE producer_id IN ({",".join("?" for _ in PYTHON_PRODUCER_IDS)})
                ORDER BY producer_id""",
            PYTHON_PRODUCER_IDS,
        ).fetchall()
        return rows == sorted(
            (producer_id, invalidation_key_sha256)
            for producer_id in PYTHON_PRODUCER_IDS
        )
    except sqlite3.DatabaseError:
        return False
    finally:
        connection.close()


def _producer_fact_counts(
    connection: sqlite3.Connection, producer_id: str
) -> dict[str, int]:
    counts = {
        "entities": int(
            connection.execute(
                "SELECT COUNT(*) FROM entities WHERE producer_id=?", (producer_id,)
            ).fetchone()[0]
        ),
        "relations": int(
            connection.execute(
                "SELECT COUNT(*) FROM relations WHERE producer_id=?", (producer_id,)
            ).fetchone()[0]
        ),
        "observations": int(
            connection.execute(
                "SELECT COUNT(*) FROM observations WHERE producer_id=?",
                (producer_id,),
            ).fetchone()[0]
        ),
    }
    counts["facts"] = sum(counts.values())
    return counts


def _copy_python_group(
    connection: sqlite3.Connection,
    *,
    previous: MapperRun,
    snapshot_run_id: str,
) -> dict[str, dict[str, int]]:
    """Copy one authenticated, unchanged producer group without rerunning it."""

    previous_database = previous.run_directory / "facts.sqlite3"
    connection.execute(
        "ATTACH DATABASE ? AS previous_mapper",
        (previous_database.as_uri() + "?mode=ro",),
    )
    placeholders = ",".join("?" for _ in PYTHON_PRODUCER_IDS)
    source_mismatch = int(
        connection.execute(
            f"""SELECT COUNT(*) FROM (
                   SELECT source_id FROM previous_mapper.entities
                     WHERE producer_id IN ({placeholders})
                   UNION
                   SELECT source_id FROM previous_mapper.relations
                     WHERE producer_id IN ({placeholders})
                   UNION
                   SELECT source_id FROM previous_mapper.observations
                     WHERE producer_id IN ({placeholders})
               ) needed
               LEFT JOIN sources current ON current.source_id=needed.source_id
               LEFT JOIN previous_mapper.sources old ON old.source_id=needed.source_id
               WHERE needed.source_id IS NOT NULL AND (
                   current.source_id IS NULL OR old.source_id IS NULL
                   OR current.path IS NOT old.path
                   OR current.privacy_class<>old.privacy_class
               )""",
            (*PYTHON_PRODUCER_IDS, *PYTHON_PRODUCER_IDS, *PYTHON_PRODUCER_IDS),
        ).fetchone()[0]
    )
    if source_mismatch:
        raise MapperError("incremental Python reuse source closure mismatch")
    connection.execute(
        f"""INSERT INTO entities(
               entity_id,entity_kind,name,qualified_name,source_id,truth_class,
               producer_id,snapshot_run_id,privacy_class,first_seen_run_id,
               last_seen_run_id,attributes_json)
             SELECT entity_id,entity_kind,name,qualified_name,source_id,truth_class,
                    producer_id,?,privacy_class,first_seen_run_id,?,attributes_json
             FROM previous_mapper.entities
             WHERE producer_id IN ({placeholders})
             ORDER BY entity_id""",
        (snapshot_run_id, snapshot_run_id, *PYTHON_PRODUCER_IDS),
    )
    connection.execute(
        f"""INSERT INTO relations(
               relation_id,subject_id,predicate,object_id,source_id,truth_class,
               confidence,producer_id,snapshot_run_id,first_seen_run_id,
               last_seen_run_id,attributes_json)
             SELECT relation_id,subject_id,predicate,object_id,source_id,truth_class,
                    confidence,producer_id,?,first_seen_run_id,?,attributes_json
             FROM previous_mapper.relations
             WHERE producer_id IN ({placeholders})
             ORDER BY relation_id""",
        (snapshot_run_id, snapshot_run_id, *PYTHON_PRODUCER_IDS),
    )
    connection.execute(
        f"""INSERT INTO observations(
               observation_id,entity_id,predicate,value_json,source_id,truth_class,
               confidence,producer_id,snapshot_run_id,first_seen_run_id,last_seen_run_id)
             SELECT observation_id,entity_id,predicate,value_json,source_id,truth_class,
                    confidence,producer_id,?,first_seen_run_id,?
             FROM previous_mapper.observations
             WHERE producer_id IN ({placeholders})
             ORDER BY observation_id""",
        (snapshot_run_id, snapshot_run_id, *PYTHON_PRODUCER_IDS),
    )
    connection.execute(
        f"""INSERT INTO locations
             SELECT l.* FROM previous_mapper.locations l
             WHERE EXISTS (
                 SELECT 1 FROM previous_mapper.relations r
                 WHERE r.relation_id=l.location_id
                   AND r.producer_id IN ({placeholders})
             ) OR EXISTS (
                 SELECT 1 FROM previous_mapper.observations o
                 WHERE o.observation_id=l.location_id
                   AND o.producer_id IN ({placeholders})
             )
             ORDER BY l.location_id""",
        (*PYTHON_PRODUCER_IDS, *PYTHON_PRODUCER_IDS),
    )
    connection.execute(
        f"""INSERT INTO coverage
             SELECT * FROM previous_mapper.coverage
             WHERE producer_id IN ({placeholders})
             ORDER BY producer_id,map_id,fact_class,scope""",
        PYTHON_PRODUCER_IDS,
    )
    connection.execute(
        f"""INSERT INTO map_views
             SELECT * FROM previous_mapper.map_views
             WHERE map_id IN ({",".join("?" for _ in PYTHON_MAP_IDS)})
             ORDER BY map_id""",
        PYTHON_MAP_IDS,
    )
    connection.execute(
        """INSERT INTO python_fragments(
               path,fragment_kind,source_identity_sha256,context_sha256,
               extractor_sha256,payload_sha256,payload_json,execution,
               first_seen_run_id,last_seen_run_id)
             SELECT path,fragment_kind,source_identity_sha256,context_sha256,
                    extractor_sha256,payload_sha256,payload_json,'REUSED',
                    first_seen_run_id,?
             FROM previous_mapper.python_fragments
             ORDER BY path""",
        (snapshot_run_id,),
    )
    return {
        producer_id: _producer_fact_counts(connection, producer_id)
        for producer_id in PYTHON_PRODUCER_IDS
    }


def _python_projection_interface(payload_json: str) -> Mapping[str, Any]:
    """Return only the file surface that can change another source's facts.

    The current cross-file projector resolves modules and symbols.  Calls, imports,
    annotations, data flow, SQL and control flow remain owned by the source that
    contains them.  A public-surface change therefore invalidates the entire
    coupled group; an implementation-only change can safely retain facts owned by
    every other exact source.
    """

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise MapperError("cached Python fragment is not strict JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"file", "failure"}:
        raise MapperError("cached Python fragment has an open schema")
    failure = payload["failure"]
    file_fragment = payload["file"]
    if failure is not None:
        if not isinstance(failure, dict):
            raise MapperError("cached Python failure is malformed")
        return {"disposition": "PARSE_FAILURE"}
    if not isinstance(file_fragment, dict):
        raise MapperError("cached Python file fragment is malformed")
    definitions = file_fragment.get("definitions")
    if not isinstance(definitions, list):
        raise MapperError("cached Python definitions are malformed")
    surface: list[dict[str, Any]] = []
    for definition in definitions:
        if not isinstance(definition, dict):
            raise MapperError("cached Python definition is malformed")
        attributes = definition.get("attributes")
        if not isinstance(attributes, dict):
            raise MapperError("cached Python definition attributes are malformed")
        bases = attributes.get("bases", [])
        if not isinstance(bases, list) or any(
            not isinstance(item, str) for item in bases
        ):
            raise MapperError("cached Python class bases are malformed")
        surface.append(
            {
                "name": definition.get("name"),
                "qualified_name": definition.get("qualified_name"),
                "kind": definition.get("kind"),
                "bases": bases,
            }
        )
    module = file_fragment.get("module")
    if not isinstance(module, str):
        raise MapperError("cached Python module identity is malformed")
    return {
        "disposition": "PARSED",
        "module": module,
        "definitions": surface,
    }


def _partial_projection_is_safe(
    connection: sqlite3.Connection,
    *,
    previous_connection: sqlite3.Connection,
    inputs: PythonInputSet,
) -> tuple[bool, set[str]]:
    """Prove that recomputed fragments did not change cross-file resolution.

    Missing/deleted Python files, producer drift, malformed cache state, and any
    module/symbol surface change fail closed to a complete projection.
    """

    current_producers = [
        tuple(row)
        for row in connection.execute(
            f"""SELECT producer_id,name,version,determinism_class,
                   implementation_sha256,configuration_json
            FROM producers
            WHERE producer_id IN ({",".join("?" for _ in PYTHON_PRODUCER_IDS)})
            ORDER BY producer_id""",
            PYTHON_PRODUCER_IDS,
        ).fetchall()
    ]
    previous_producers = [
        tuple(row)
        for row in previous_connection.execute(
            f"""SELECT producer_id,name,version,determinism_class,
                   implementation_sha256,configuration_json
            FROM producers
            WHERE producer_id IN ({",".join("?" for _ in PYTHON_PRODUCER_IDS)})
            ORDER BY producer_id""",
            PYTHON_PRODUCER_IDS,
        ).fetchall()
    ]
    if current_producers != previous_producers or len(current_producers) != len(
        PYTHON_PRODUCER_IDS
    ):
        return False, set()
    previous_scopes = previous_connection.execute(
        f"""SELECT input_scope_json FROM producer_inputs
            WHERE producer_id IN ({",".join("?" for _ in PYTHON_PRODUCER_IDS)})
            ORDER BY producer_id""",
        PYTHON_PRODUCER_IDS,
    ).fetchall()
    try:
        implementation_hashes = {
            json.loads(row[0]).get("implementation_sha256") for row in previous_scopes
        }
    except json.JSONDecodeError as exc:
        raise MapperError("previous producer input scope is malformed") from exc
    if implementation_hashes != {inputs.implementation_sha256}:
        return False, set()

    current_rows = {
        row[0]: row
        for row in connection.execute(
            """SELECT path,fragment_kind,payload_sha256,payload_json,execution
               FROM python_fragments ORDER BY path"""
        )
    }
    previous_rows = {
        row[0]: row
        for row in previous_connection.execute(
            """SELECT path,fragment_kind,payload_sha256,payload_json,execution
               FROM python_fragments ORDER BY path"""
        )
    }
    current_python = {
        path for path, row in current_rows.items() if row[1] == "PYTHON_SOURCE"
    }
    previous_python = {
        path for path, row in previous_rows.items() if row[1] == "PYTHON_SOURCE"
    }
    if current_python != previous_python:
        return False, set()

    recomputed_paths = {
        path for path, row in current_rows.items() if row[4] == "RECOMPUTED"
    }
    for path in sorted(recomputed_paths & current_python):
        current = current_rows[path]
        previous = previous_rows.get(path)
        if previous is None or previous[1] != "PYTHON_SOURCE":
            return False, set()
        if sha256_bytes(current[3].encode("utf-8")) != current[2]:
            raise MapperError(f"current Python fragment payload mismatch: {path}")
        if sha256_bytes(previous[3].encode("utf-8")) != previous[2]:
            raise MapperError(f"previous Python fragment payload mismatch: {path}")
        if _python_projection_interface(current[3]) != _python_projection_interface(
            previous[3]
        ):
            return False, set()
    return True, recomputed_paths


def _copy_partial_python_projection(
    connection: sqlite3.Connection,
    *,
    previous: MapperRun | None,
    source_by_path: Mapping[str, str],
    inputs: PythonInputSet,
    snapshot_run_id: str,
) -> set[str]:
    """Reuse exact source-owned facts when cross-file resolution is unchanged."""

    if previous is None:
        return set()
    previous_database = previous.run_directory / "facts.sqlite3"
    old = sqlite3.connect(f"file:{previous_database}?mode=ro", uri=True)
    try:
        old.execute("PRAGMA query_only=ON")
        schema = old.execute(
            "SELECT value FROM meta WHERE key='database_schema'"
        ).fetchone()
        if schema != (str(DATABASE_SCHEMA),):
            return set()
        safe, recomputed_paths = _partial_projection_is_safe(
            connection, previous_connection=old, inputs=inputs
        )
        if not safe:
            return set()
        previous_sources = {
            row[0]: (row[1], row[2], row[3], row[4])
            for row in old.execute(
                """SELECT source_id,path,identity_sha256,privacy_class,attributes_json
                   FROM sources ORDER BY source_id"""
            )
        }
        current_sources = {
            row[0]: (row[1], row[2], row[3], row[4])
            for row in connection.execute(
                """SELECT source_id,path,identity_sha256,privacy_class,attributes_json
                   FROM sources ORDER BY source_id"""
            )
        }
        reusable = {
            source_id
            for path, source_id in source_by_path.items()
            if path not in recomputed_paths
            and source_id in previous_sources
            and previous_sources[source_id][:3]
            == current_sources.get(source_id, ())[:3]
        }
        if not reusable:
            return set()
    except sqlite3.DatabaseError as exc:
        raise MapperError("previous partial projection is unreadable") from exc
    finally:
        old.close()

    connection.execute("PRAGMA defer_foreign_keys=ON")
    connection.execute(
        "CREATE TEMP TABLE reusable_projection_sources(source_id TEXT PRIMARY KEY)"
    )
    connection.executemany(
        "INSERT INTO reusable_projection_sources VALUES (?)",
        ((source_id,) for source_id in sorted(reusable)),
    )
    connection.execute(
        "ATTACH DATABASE ? AS previous_mapper",
        (previous_database.as_uri() + "?mode=ro",),
    )
    try:
        placeholders = ",".join("?" for _ in PYTHON_PRODUCER_IDS)
        connection.execute(
            f"""INSERT INTO entities(
                   entity_id,entity_kind,name,qualified_name,source_id,truth_class,
                   producer_id,snapshot_run_id,privacy_class,first_seen_run_id,
                   last_seen_run_id,attributes_json)
                 SELECT entity_id,entity_kind,name,qualified_name,source_id,truth_class,
                        producer_id,?,privacy_class,first_seen_run_id,?,attributes_json
                 FROM previous_mapper.entities
                 WHERE producer_id IN ({placeholders})
                   AND source_id IN (SELECT source_id FROM reusable_projection_sources)
                 ORDER BY entity_id""",
            (snapshot_run_id, snapshot_run_id, *PYTHON_PRODUCER_IDS),
        )
        connection.execute(
            f"""INSERT INTO relations(
                   relation_id,subject_id,predicate,object_id,source_id,truth_class,
                   confidence,producer_id,snapshot_run_id,first_seen_run_id,
                   last_seen_run_id,attributes_json)
                 SELECT relation_id,subject_id,predicate,object_id,source_id,truth_class,
                        confidence,producer_id,?,first_seen_run_id,?,attributes_json
                 FROM previous_mapper.relations
                 WHERE producer_id IN ({placeholders})
                   AND source_id IN (SELECT source_id FROM reusable_projection_sources)
                 ORDER BY relation_id""",
            (snapshot_run_id, snapshot_run_id, *PYTHON_PRODUCER_IDS),
        )
        connection.execute(
            f"""INSERT INTO observations(
                   observation_id,entity_id,predicate,value_json,source_id,truth_class,
                   confidence,producer_id,snapshot_run_id,first_seen_run_id,last_seen_run_id)
                 SELECT observation_id,entity_id,predicate,value_json,source_id,truth_class,
                        confidence,producer_id,?,first_seen_run_id,?
                 FROM previous_mapper.observations
                 WHERE producer_id IN ({placeholders})
                   AND source_id IN (SELECT source_id FROM reusable_projection_sources)
                 ORDER BY observation_id""",
            (snapshot_run_id, snapshot_run_id, *PYTHON_PRODUCER_IDS),
        )
        connection.execute(
            f"""INSERT INTO locations
                 SELECT l.* FROM previous_mapper.locations l
                 WHERE l.source_id IN (SELECT source_id FROM reusable_projection_sources)
                   AND (
                     EXISTS (SELECT 1 FROM previous_mapper.relations r
                             WHERE r.relation_id=l.location_id
                               AND r.producer_id IN ({placeholders}))
                     OR EXISTS (SELECT 1 FROM previous_mapper.observations o
                                WHERE o.observation_id=l.location_id
                                  AND o.producer_id IN ({placeholders})))
                 ORDER BY l.location_id""",
            (*PYTHON_PRODUCER_IDS, *PYTHON_PRODUCER_IDS),
        )
        reused_counts: dict[tuple[str, str], dict[str, int]] = {}
        for table, label in (
            ("entities", "entities"),
            ("relations", "relations"),
            ("observations", "observations"),
        ):
            for source_id, producer_id, count in connection.execute(
                f"""SELECT source_id,producer_id,COUNT(*) FROM {table}
                    WHERE source_id IN (SELECT source_id FROM reusable_projection_sources)
                      AND producer_id IN ({placeholders})
                    GROUP BY source_id,producer_id""",
                PYTHON_PRODUCER_IDS,
            ):
                reused_counts.setdefault((source_id, producer_id), {})[label] = int(
                    count
                )
        location_counts = {
            (source_id, producer_id): int(count)
            for source_id, producer_id, count in connection.execute(
                f"""SELECT l.source_id,COALESCE(r.producer_id,o.producer_id),COUNT(*)
                    FROM locations l
                    LEFT JOIN relations r ON r.relation_id=l.location_id
                    LEFT JOIN observations o ON o.observation_id=l.location_id
                    WHERE l.source_id IN (
                        SELECT source_id FROM reusable_projection_sources)
                      AND COALESCE(r.producer_id,o.producer_id) IN ({placeholders})
                    GROUP BY l.source_id,COALESCE(r.producer_id,o.producer_id)""",
                PYTHON_PRODUCER_IDS,
            )
        }
        for path, source_id in sorted(source_by_path.items()):
            if source_id not in reusable:
                continue
            for producer_id in PYTHON_PRODUCER_IDS:
                counts = reused_counts.get((source_id, producer_id), {})
                entities = counts.get("entities", 0)
                relations = counts.get("relations", 0)
                observations = counts.get("observations", 0)
                locations = location_counts.get((source_id, producer_id), 0)
                if entities or relations or observations:
                    connection.execute(
                        "INSERT INTO projection_reuse VALUES (?,?,?,?,?,?,?,?)",
                        (
                            path,
                            source_id,
                            producer_id,
                            entities,
                            relations,
                            observations,
                            locations,
                            "UNCHANGED_SOURCE_PUBLIC_SURFACE_STABLE",
                        ),
                    )
    finally:
        connection.execute("DROP TABLE reusable_projection_sources")
    return reusable


class _SelectiveProjectionConnection:
    """Suppress writes already copied from an authenticated previous projection."""

    def __init__(
        self, connection: sqlite3.Connection, reused_source_ids: set[str]
    ) -> None:
        self._connection = connection
        self._reused_source_ids = reused_source_ids

    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> Any:
        normalized = " ".join(sql.split()).upper()
        source_index = None
        if normalized.startswith("INSERT INTO ENTITIES VALUES"):
            source_index = 4
        elif normalized.startswith("INSERT INTO RELATIONS VALUES"):
            source_index = 4
        elif normalized.startswith("INSERT INTO OBSERVATIONS VALUES"):
            source_index = 4
        elif normalized.startswith("INSERT INTO LOCATIONS VALUES"):
            source_index = 1
        if (
            source_index is not None
            and len(parameters) > source_index
            and parameters[source_index] in self._reused_source_ids
        ):
            return _SUPPRESSED_WRITE
        return self._connection.execute(sql, parameters)

    def executemany(
        self, sql: str, parameters: Iterable[Sequence[Any]]
    ) -> sqlite3.Cursor:
        return self._connection.executemany(sql, parameters)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)


class _SuppressedWrite:
    """Sentinel cursor for source writes already copied from prior evidence."""

    rowcount = 0


_SUPPRESSED_WRITE = _SuppressedWrite()


def _carry_python_first_seen(
    connection: sqlite3.Connection,
    *,
    previous: MapperRun | None,
) -> None:
    """Carry stable fact history across a producer recomputation.

    Only exact stable IDs match.  New or source-versioned facts retain the current
    run as first_seen; unchanged logical entities and identical facts keep their
    authenticated earlier origin.
    """

    if previous is None:
        return
    previous_database = previous.run_directory / "facts.sqlite3"
    probe = sqlite3.connect(f"file:{previous_database}?mode=ro", uri=True)
    try:
        probe.execute("PRAGMA query_only=ON")
        schema = probe.execute(
            "SELECT value FROM meta WHERE key='database_schema'"
        ).fetchone()
    except sqlite3.DatabaseError:
        return
    finally:
        probe.close()
    if schema != (str(DATABASE_SCHEMA),):
        return
    attached = {row[1] for row in connection.execute("PRAGMA database_list").fetchall()}
    if "previous_mapper" not in attached:
        connection.execute(
            "ATTACH DATABASE ? AS previous_mapper",
            (previous_database.as_uri() + "?mode=ro",),
        )
    placeholders = ",".join("?" for _ in PYTHON_PRODUCER_IDS)
    for table, fact_id in (
        ("entities", "entity_id"),
        ("relations", "relation_id"),
        ("observations", "observation_id"),
    ):
        connection.execute(
            f"""UPDATE {table}
                SET first_seen_run_id=(
                    SELECT old.first_seen_run_id FROM previous_mapper.{table} old
                    WHERE old.{fact_id}={table}.{fact_id}
                )
                WHERE producer_id IN ({placeholders})
                  AND source_id NOT IN (SELECT source_id FROM projection_reuse)
                  AND EXISTS (
                    SELECT 1 FROM previous_mapper.{table} old
                    WHERE old.{fact_id}={table}.{fact_id}
                  )""",
            PYTHON_PRODUCER_IDS,
        )


def _python_fragment_counts(connection: sqlite3.Connection) -> dict[str, int]:
    total, reused, recomputed = connection.execute(
        """SELECT COUNT(*),
                  COALESCE(SUM(execution='REUSED'),0),
                  COALESCE(SUM(execution='RECOMPUTED'),0)
           FROM python_fragments"""
    ).fetchone()
    return {
        "python_fragments_total": int(total),
        "python_fragments_reused": int(reused),
        "python_fragments_recomputed": int(recomputed),
        "python_fragments_deleted": 0,
    }


def _projection_reuse_fact_counts(
    connection: sqlite3.Connection,
) -> dict[str, int]:
    counts = {producer_id: 0 for producer_id in PYTHON_PRODUCER_IDS}
    for producer_id, reused in connection.execute(
        """SELECT producer_id,
                  COALESCE(SUM(entities_reused+relations_reused+observations_reused),0)
           FROM projection_reuse GROUP BY producer_id ORDER BY producer_id"""
    ):
        if producer_id in counts:
            counts[producer_id] = int(reused)
    return counts


def _record_python_input_bindings(
    connection: sqlite3.Connection,
    *,
    inputs: PythonInputSet,
    per_producer_counts: Mapping[str, Mapping[str, int]],
    reused_fact_counts: Mapping[str, int],
    full_group_reused: bool,
    duration_seconds: float,
) -> None:
    for producer_id in PYTHON_PRODUCER_IDS:
        facts = int(per_producer_counts[producer_id]["facts"])
        reused = int(reused_fact_counts.get(producer_id, 0))
        if reused < 0 or reused > facts:
            raise MapperError("incremental Python reuse count is impossible")
        recomputed = facts - reused
        execution = (
            "REUSED"
            if (facts > 0 and recomputed == 0) or (facts == 0 and full_group_reused)
            else "PARTIAL"
            if reused
            else "RECOMPUTED"
        )
        connection.execute(
            "INSERT INTO producer_inputs VALUES (?,?,?,?,?,?,?,?,?)",
            (
                producer_id,
                inputs.invalidation_key_sha256,
                inputs.source_identities_sha256,
                len(inputs.records_by_path),
                _json(
                    {
                        "coupled_producers": list(PYTHON_PRODUCER_IDS),
                        "maps": list(PYTHON_MAP_IDS),
                        "implementation_sha256": inputs.implementation_sha256,
                        "scope": "python-project-build-quality-source-closure",
                    }
                ),
                execution,
                reused,
                recomputed,
                round(duration_seconds, 6),
            ),
        )


def _scip_range_span(values: Sequence[int]) -> dict[str, int | None]:
    if len(values) == 3:
        start_line, start_column, end_column = values
        end_line = start_line
    elif len(values) == 4:
        start_line, start_column, end_line, end_column = values
    else:  # already rejected by the strict SCIP parser
        raise MapperError("SCIP occurrence has an invalid range")
    return {
        "byte_start": None,
        "byte_end": None,
        "line_start": int(start_line) + 1,
        "line_end": int(end_line) + 1,
        "column_start": int(start_column),
        "column_end": int(end_column),
    }


def _scip_qualified_symbol(path: str | None, symbol: str) -> str:
    if symbol.startswith("local "):
        if path is None:
            raise MapperError("local SCIP symbol is missing its document")
        return f"local {path} {symbol.removeprefix('local ')}"
    return symbol


def _build_one_scip_map(
    connection: sqlite3.Connection,
    *,
    scip_input: ScipIndexInput,
    producer_id: str,
    entity_namespace: str,
    root_key: str,
    source_by_path: Mapping[str, str],
    manifest_source: str,
    snapshot_run_id: str,
) -> dict[str, int]:
    is_typescript = scip_input.manifest["tool"]["package"] == SCIP_TYPESCRIPT_PACKAGE
    index = scip_input.index
    input_record = scip_input.manifest_record()
    connection.execute(
        "INSERT INTO run_inputs VALUES (?,?,?,?)",
        (
            f"input:scip-index:{input_record['index_sha256']}",
            "SCIP_TYPESCRIPT_INDEX" if is_typescript else "SCIP_PYTHON_INDEX",
            input_record["index_sha256"],
            _json(input_record),
        ),
    )
    index_source = f"source:scip-index:{input_record['index_sha256']}"
    connection.execute(
        "INSERT INTO sources VALUES (?,?,?,?,?,?)",
        (
            index_source,
            "SCIP_INDEX_MANIFEST",
            None,
            scip_input.manifest["receipt_sha256"],
            "LOCAL_CODE_INTELLIGENCE_METADATA",
            _json(input_record),
        ),
    )
    resolved_source_by_path = dict(source_by_path)
    for document in index.documents:
        if document.relative_path in resolved_source_by_path:
            continue
        rows = connection.execute(
            "SELECT source_id FROM sources WHERE path=? ORDER BY source_id",
            (document.relative_path,),
        ).fetchall()
        if len(rows) != 1:
            raise MapperError(
                "SCIP document does not resolve to exactly one inventory source: "
                f"{document.relative_path}"
            )
        resolved_source_by_path[document.relative_path] = str(rows[0][0])

    symbol_info: dict[str, Any] = {}
    occurrence_paths: dict[str, list[str]] = {}
    definition_paths: dict[str, list[str]] = {}
    language_by_path = {
        document.relative_path: document.language for document in index.documents
    }
    raw_symbols: set[str] = set()
    local_symbols: set[tuple[str, str]] = set()
    for symbol in index.external_symbols:
        if symbol.symbol:
            symbol_info[symbol.symbol] = symbol
            raw_symbols.add(symbol.symbol)
        raw_symbols.update(item.symbol for item in symbol.relationships if item.symbol)
    for document in index.documents:
        for symbol in document.symbols:
            qualified = _scip_qualified_symbol(document.relative_path, symbol.symbol)
            if symbol.symbol:
                symbol_info[qualified] = symbol
                if symbol.symbol.startswith("local "):
                    local_symbols.add((document.relative_path, symbol.symbol))
                else:
                    raw_symbols.add(symbol.symbol)
            for relationship in symbol.relationships:
                if relationship.symbol and not relationship.symbol.startswith("local "):
                    raw_symbols.add(relationship.symbol)
        for occurrence in document.occurrences:
            if not occurrence.symbol:
                continue
            qualified = _scip_qualified_symbol(
                document.relative_path, occurrence.symbol
            )
            occurrence_paths.setdefault(qualified, []).append(document.relative_path)
            if occurrence.roles & 1:
                definition_paths.setdefault(qualified, []).append(
                    document.relative_path
                )
            if occurrence.symbol.startswith("local "):
                local_symbols.add((document.relative_path, occurrence.symbol))
            else:
                raw_symbols.add(occurrence.symbol)

    qualified_symbols = sorted(
        {
            *raw_symbols,
            *(_scip_qualified_symbol(path, value) for path, value in local_symbols),
        }
    )
    entity_by_symbol: dict[str, str] = {}
    for qualified in qualified_symbols:
        info = symbol_info.get(qualified) or symbol_info.get(
            qualified.split(" ", 2)[-1] if qualified.startswith("local ") else qualified
        )
        paths = sorted(set(occurrence_paths.get(qualified, ())))
        definitions = sorted(set(definition_paths.get(qualified, ())))
        source_id = (
            resolved_source_by_path.get(
                definitions[0] if definitions else paths[0], index_source
            )
            if definitions or paths
            else index_source
        )
        entity_id = _entity_id(
            "SCIP_SYMBOL", root_key, f"{entity_namespace}:{qualified}"
        )
        entity_by_symbol[qualified] = entity_id
        connection.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                entity_id,
                "SCIP_SYMBOL",
                scip_symbol_name(
                    qualified,
                    "" if info is None else info.display_name,
                ),
                qualified,
                source_id,
                "OBSERVED",
                producer_id,
                snapshot_run_id,
                "LOCAL_SOURCE" if paths else "PUBLIC_DEPENDENCY_METADATA",
                snapshot_run_id,
                snapshot_run_id,
                _json(
                    {
                        "language": language_by_path.get(paths[0], "") if paths else "",
                        "raw_scip_symbol": qualified,
                        "search_text": qualified.replace("/", ".")
                        .replace("#", ".")
                        .replace("().", ".")
                        .replace(" ", "."),
                        "symbol_kind": 0 if info is None else info.kind,
                        "display_name": "" if info is None else info.display_name,
                        "documentation": []
                        if info is None
                        else list(info.documentation),
                        "definition_paths": definitions,
                        "source_paths": paths,
                        "tool_derived": True,
                        "authority_granted": False,
                    }
                ),
            ),
        )

    definition_count = reference_count = duplicate_occurrences = 0
    emitted_observations: set[str] = set()
    for document in index.documents:
        source_id = resolved_source_by_path[document.relative_path]
        for occurrence in document.occurrences:
            if not occurrence.symbol:
                continue
            qualified = _scip_qualified_symbol(
                document.relative_path, occurrence.symbol
            )
            entity_id = entity_by_symbol[qualified]
            is_definition = bool(occurrence.roles & 1)
            predicate = "SCIP_DEFINITION" if is_definition else "SCIP_REFERENCE"
            value = {
                "path": document.relative_path,
                "range": list(occurrence.range),
                "enclosing_range": list(occurrence.enclosing_range),
                "roles": occurrence.roles,
                "syntax_kind": occurrence.syntax_kind,
                "position_encoding": document.position_encoding,
                "raw_scip_symbol": occurrence.symbol,
                "tool_derived": True,
                "authority_granted": False,
            }
            observation_identity = _fact_id(
                [entity_id, predicate, _json(value), source_id, producer_id]
            )
            if observation_identity in emitted_observations:
                duplicate_occurrences += 1
                continue
            emitted_observations.add(observation_identity)
            definition_count += int(is_definition)
            reference_count += int(not is_definition)
            fact_id = _insert_observation(
                connection,
                entity_id=entity_id,
                predicate=predicate,
                value=value,
                source_id=source_id,
                producer_id=producer_id,
                snapshot_run_id=snapshot_run_id,
                truth_class="OBSERVED",
            )
            _insert_location(
                connection,
                fact_id=fact_id,
                source_id=source_id,
                path=document.relative_path,
                span=_scip_range_span(occurrence.range),
            )

    emitted_relationships = 0
    for qualified, info in sorted(symbol_info.items()):
        subject = entity_by_symbol.get(qualified)
        if subject is None:
            continue
        paths = sorted(set(occurrence_paths.get(qualified, ())))
        source_id = (
            resolved_source_by_path.get(paths[0], index_source)
            if paths
            else index_source
        )
        for relationship in info.relationships:
            target = entity_by_symbol.get(relationship.symbol)
            if target is None:
                continue
            predicates = []
            if relationship.is_reference:
                predicates.append("SCIP_REFERENCE_EQUIVALENT")
            if relationship.is_implementation:
                predicates.append("SCIP_IMPLEMENTATION_OF")
            if relationship.is_type_definition:
                predicates.append("SCIP_TYPE_DEFINITION_OF")
            if relationship.is_definition:
                predicates.append("SCIP_DEFINITION_EQUIVALENT")
            for predicate in predicates:
                _insert_relation(
                    connection,
                    subject=subject,
                    predicate=predicate,
                    object_=target,
                    source_id=source_id,
                    producer_id=producer_id,
                    snapshot_run_id=snapshot_run_id,
                    truth_class="OBSERVED",
                    attributes={"tool_derived": True, "authority_granted": False},
                )
                emitted_relationships += 1

    for map_id, fact_class in (
        ("symbols", "SCIP_PRECISE_SYMBOL_OCCURRENCE"),
        ("dependencies", "SCIP_EXTERNAL_SYMBOL_RESOLUTION"),
        ("types", "SCIP_SYMBOL_RELATIONSHIP"),
    ):
        connection.execute(
            "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                producer_id,
                map_id,
                fact_class,
                (
                    "inventory-bound-semantic-eligible-typescript-javascript"
                    if is_typescript
                    else "inventory-bound-semantic-eligible-python"
                ),
                "PARTIAL",
                len(index.documents),
                len(index.documents),
                0,
                0,
                0,
                _json(
                    {
                        "index_sha256": input_record["index_sha256"],
                        "position_encodings": sorted(
                            {document.position_encoding for document in index.documents}
                        ),
                        "source_text_embedded": False,
                        "dependency_snapshot": (
                            "EXACT_INDEXER_DEPENDENCY_TREE_PROJECT_DEPS_NOT_COPIED"
                            if is_typescript
                            else "INDEXER_BUNDLED_NOT_HOST_RUNTIME"
                        ),
                        "tool_derived": True,
                        "authority_granted": False,
                    }
                ),
            ),
        )
    for map_id in ("symbols", "dependencies", "types"):
        row = connection.execute(
            "SELECT status,required_fact_classes_json,query_contract_json FROM map_views WHERE map_id=?",
            (map_id,),
        ).fetchone()
        current_status = str(row[0])
        required = json.loads(row[1])
        contract = json.loads(row[2])
        required.extend(
            item
            for item in ("SCIP_SYMBOL", "SCIP_DEFINITION", "SCIP_REFERENCE")
            if item not in required
        )
        backend = "typescript_javascript" if is_typescript else "python"
        contract.update(
            {
                f"precise_{backend}_backend": "SCIP",
                f"precise_{backend}_status": "OPTIONAL_PARTIAL",
                "tool_derived_authority": False,
            }
        )
        next_status = (
            current_status
            if current_status.endswith("_AND_SCIP_PRECISE_PARTIAL")
            else f"{current_status.removesuffix('_PARTIAL')}_AND_SCIP_PRECISE_PARTIAL"
        )
        connection.execute(
            "UPDATE map_views SET status=?,required_fact_classes_json=?,query_contract_json=? WHERE map_id=?",
            (
                next_status,
                _json(required),
                _json(contract),
                map_id,
            ),
        )
    return {
        "scip_documents": len(index.documents),
        "scip_symbols": len(qualified_symbols),
        "scip_external_symbols": len(index.external_symbols),
        "scip_occurrences": definition_count + reference_count,
        "scip_duplicate_occurrences_coalesced": duplicate_occurrences,
        "scip_definitions": definition_count,
        "scip_references": reference_count,
        "scip_relationships": emitted_relationships,
    }


def _build_scip_maps(
    connection: sqlite3.Connection,
    *,
    scip_inputs: Sequence[ScipIndexInput],
    root_key: str,
    source_by_path: Mapping[str, str],
    manifest_source: str,
    snapshot_run_id: str,
) -> dict[str, int]:
    totals = {key: 0 for key in SCIP_COUNT_KEYS}
    multiple = len(scip_inputs) > 1
    for scip_input in scip_inputs:
        is_typescript = (
            scip_input.manifest["tool"]["package"] == SCIP_TYPESCRIPT_PACKAGE
        )
        base_producer = (
            SCIP_TYPESCRIPT_PRODUCER_ID if is_typescript else SCIP_PRODUCER_ID
        )
        index_sha256 = scip_input.manifest["index"]["sha256"]
        producer_id = (
            f"{base_producer}:index-{index_sha256[:16]}" if multiple else base_producer
        )
        if multiple:
            base = connection.execute(
                "SELECT name,version,determinism_class,implementation_sha256,configuration_json "
                "FROM producers WHERE producer_id=?",
                (base_producer,),
            ).fetchone()
            if base is None:
                raise MapperError("SCIP base producer is missing")
            details = json.loads(base[4])
            details.update(
                {
                    "federated_input": True,
                    "index_sha256": index_sha256,
                }
            )
            connection.execute(
                "INSERT INTO producers VALUES (?,?,?,?,?,?)",
                (
                    producer_id,
                    f"{base[0]}_federated_input",
                    base[1],
                    base[2],
                    base[3],
                    _json(details),
                ),
            )
        counts = _build_one_scip_map(
            connection,
            scip_input=scip_input,
            producer_id=producer_id,
            entity_namespace=index_sha256 if multiple else "single",
            root_key=root_key,
            source_by_path=source_by_path,
            manifest_source=manifest_source,
            snapshot_run_id=snapshot_run_id,
        )
        for key, value in counts.items():
            totals[key] += value
    return totals


def _build_database(
    inventory: NavigationRun,
    destination: Path,
    runtime_registries: Sequence[RuntimeRegistryInput] = (),
    semantic_input: Mapping[str, Any] | None = None,
    scip_inputs: Sequence[ScipIndexInput] = (),
    previous: MapperRun | None = None,
) -> dict[str, int]:
    run_id = inventory.manifest["run_id"]
    root_key = _root_key(inventory)
    repository_id = _repository_id(root_key)
    implementation_hash = _producer_hash()
    python_implementation_hash = _file_sha256(
        Path(extract_python_fragment.__code__.co_filename).resolve()
    )[0]
    shell_implementation_hash = _file_sha256(
        Path(extract_shell_file_fragment.__code__.co_filename).resolve()
    )[0]
    javascript_implementation_hash = _file_sha256(
        Path(extract_javascript_file_fragment.__code__.co_filename).resolve()
    )[0]
    operational_implementation_hash = _file_sha256(
        Path(parse_sql_literal.__code__.co_filename).resolve()
    )[0]
    quality_implementation_hash = _file_sha256(
        Path(parse_coverage_json.__code__.co_filename).resolve()
    )[0]
    cleanup_implementation_hash = _file_sha256(
        Path(safe_exact_duplicate_groups.__code__.co_filename).resolve()
    )[0]
    capability_backend = _capability_backend()
    lineage_implementation_hash = sha256_bytes(
        canonical_bytes(
            [
                _file_sha256(
                    Path(collect_recent_lineage.__code__.co_filename).resolve()
                )[0],
                (
                    _file_sha256(Path(capability_backend[1].__code__.co_filename).resolve())[0]
                    if capability_backend is not None
                    else None
                ),
            ]
        )
    )
    governance_implementation_hash = sha256_bytes(
        canonical_bytes(
            [
                _file_sha256(Path(strict_json_object.__code__.co_filename).resolve())[
                    0
                ],
                _file_sha256(
                    Path(parse_receipt_quality_claims.__code__.co_filename).resolve()
                )[0],
            ]
        )
    )
    runtime_implementation_hash = _file_sha256(
        Path(load_runtime_registry.__code__.co_filename).resolve()
    )[0]
    semantic_implementation_hash = _file_sha256(
        Path(current_semantic_run.__code__.co_filename).resolve()
    )[0]
    scip_implementation_hash = _file_sha256(
        Path(load_scip_index.__code__.co_filename).resolve()
    )[0]
    inventory_producer = "producer:navigation-inventory-import:v1"
    structure_producer = "producer:structure-extractor:v1"
    python_producer = "producer:python-map-extractor:v1"
    shell_producer = "producer:shell-map-extractor:v1"
    javascript_producer = "producer:javascript-map-extractor:v2"
    operational_producer = "producer:operational-map-extractor:v1"
    quality_producer = "producer:quality-map-extractor:v1"
    cleanup_producer = "producer:cleanup-map-projector:v1"
    lineage_producer = "producer:lineage-ownership-projector:v1"
    governance_producer = "producer:governance-evidence-projector:v1"
    runtime_producer = "producer:runtime-registry-projector:v1"
    semantic_producer = "producer:semantic-graph-federation:v1"
    manifest_source = (
        f"source:inventory-manifest:{inventory.manifest['receipt_sha256']}"
    )
    database = sqlite3.connect(destination)
    database.row_factory = sqlite3.Row
    try:
        _configure_database(database)
        database.executemany(
            "INSERT INTO meta VALUES (?,?)",
            (
                ("database_schema", str(DATABASE_SCHEMA)),
                ("inventory_run_id", run_id),
                ("inventory_receipt_sha256", inventory.manifest["receipt_sha256"]),
                ("root_key", root_key),
            ),
        )
        database.executemany(
            "INSERT INTO producers VALUES (?,?,?,?,?,?)",
            (
                (
                    inventory_producer,
                    "navigation_inventory_import",
                    "1",
                    "DETERMINISTIC",
                    implementation_hash,
                    _json({"parent_schema": inventory.manifest["schema"]}),
                ),
                (
                    structure_producer,
                    "structure_extractor",
                    "1",
                    "DETERMINISTIC",
                    implementation_hash,
                    _json({"path_flavour": "PurePosixPath"}),
                ),
                (
                    python_producer,
                    "python_map_extractor",
                    "1",
                    "DETERMINISTIC",
                    python_implementation_hash,
                    _json(
                        {
                            "parser": "python-ast",
                            "content_policy": "semantic-eligible-local-only",
                            "flow_policy": FLOW_POLICY_VERSION,
                            "flow_policy_sha256": POLICY_SHA256,
                            "imports_target_code": False,
                        }
                    ),
                ),
                (
                    shell_producer,
                    "shell_map_extractor",
                    "1",
                    "DETERMINISTIC",
                    shell_implementation_hash,
                    _json(
                        {
                            "backend": dict(shell_backend_identity()),
                            "content_policy": "semantic-eligible-local-only",
                            "executes_source": False,
                            "language": "bash",
                            "scope": "dot-sh-files",
                        }
                    ),
                ),
                (
                    javascript_producer,
                    "javascript_map_extractor",
                    "2",
                    "DETERMINISTIC",
                    javascript_implementation_hash,
                    _json(
                        {
                            "backend": dict(javascript_backend_identity()),
                            "content_policy": "semantic-eligible-local-only",
                            "executes_source": False,
                            "languages": ["javascript", "tsx", "typescript"],
                            "scope": "js-jsx-mjs-cjs-ts-tsx-files",
                            "resolution": "same-file-and-exact-cross-file-esm-commonjs",
                        }
                    ),
                ),
                (
                    operational_producer,
                    "operational_map_extractor",
                    "1",
                    "DETERMINISTIC",
                    operational_implementation_hash,
                    _json(
                        {
                            "build_content_policy": "safe-allowlisted-declarations",
                            "database_row_content_read": False,
                            "operational_policy": OPERATIONAL_POLICY_VERSION,
                            "operational_policy_sha256": OPERATIONAL_POLICY_SHA256,
                            "sql_grammar": SQL_LITERAL_GRAMMAR,
                        }
                    ),
                ),
                (
                    quality_producer,
                    "quality_map_extractor",
                    "1",
                    "DETERMINISTIC",
                    quality_implementation_hash,
                    _json(
                        {
                            "coverage_content_policy": "summary-only-no-source-content",
                            "policy": QUALITY_POLICY_VERSION,
                            "policy_sha256": QUALITY_POLICY_SHA256,
                            "test_discovery": "python-path-and-name-convention",
                        }
                    ),
                ),
                (
                    cleanup_producer,
                    "cleanup_map_projector",
                    "1",
                    "DETERMINISTIC",
                    cleanup_implementation_hash,
                    _json(
                        {
                            "authority_granted": False,
                            "cleanup_permitted": False,
                            "deletion_permitted": False,
                            "policy": CLEANUP_POLICY_VERSION,
                            "policy_sha256": CLEANUP_POLICY_SHA256,
                            "sources": "authenticated-inventory-and-existing-fact-store",
                        }
                    ),
                ),
                (
                    lineage_producer,
                    "lineage_ownership_projector",
                    "1",
                    "DETERMINISTIC",
                    lineage_implementation_hash,
                    _json(
                        {
                            "canonical_authority_inferred": False,
                            "git_history_depth": 50,
                            "owner_role_source": "navigation_inventory",
                            "owner_contract_validator": "twin_core.capability_adoption.inspect_capability_manifest",
                            "renames": "unsupported",
                        }
                    ),
                ),
                (
                    governance_producer,
                    "governance_evidence_projector",
                    "1",
                    "DETERMINISTIC",
                    governance_implementation_hash,
                    _json(
                        {
                            "policy": GOVERNANCE_POLICY_VERSION,
                            "policy_sha256": GOVERNANCE_POLICY_SHA256,
                            "prose_similarity": False,
                            "status_is_document_claim": True,
                        }
                    ),
                ),
                (
                    runtime_producer,
                    "runtime_registry_projector",
                    "1",
                    "DETERMINISTIC",
                    runtime_implementation_hash,
                    _json(
                        {
                            "canonical_liveness_authority": "EXTERNAL_CAPABILITY_ADOPTION_GATE",
                            "map_authority": False,
                            "policy": RUNTIME_POLICY_VERSION,
                            "policy_sha256": RUNTIME_POLICY_SHA256,
                            "runtime_process_discovery": False,
                        }
                    ),
                ),
                (
                    semantic_producer,
                    "semantic_graph_federation",
                    "1",
                    "SEMANTIC",
                    semantic_implementation_hash,
                    _json(
                        {
                            "authority_granted": False,
                            "deterministic_fact_override": False,
                            "producer": "existing-local-graphify-pipeline",
                            "storage": "federated-authenticated-semantic-store",
                        }
                    ),
                ),
                (
                    SCIP_PRODUCER_ID,
                    "scip_python_index_projector",
                    "1",
                    "TOOL_DERIVED_DETERMINISTIC_PROJECTION",
                    scip_implementation_hash,
                    _json(
                        {
                            "authority_granted": False,
                            "optional_backend": True,
                            "producer": "@sourcegraph/scip-python",
                            "source_text_embedded": False,
                            "storage": "content-addressed-private-scip-index",
                        }
                    ),
                ),
                (
                    SCIP_TYPESCRIPT_PRODUCER_ID,
                    "scip_typescript_index_projector",
                    "1",
                    "TOOL_DERIVED_DETERMINISTIC_PROJECTION",
                    scip_implementation_hash,
                    _json(
                        {
                            "authority_granted": False,
                            "optional_backend": True,
                            "producer": SCIP_TYPESCRIPT_PACKAGE,
                            "source_text_embedded": False,
                            "storage": "content-addressed-private-scip-index",
                        }
                    ),
                ),
            ),
        )
        database.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?)",
            (
                manifest_source,
                "INVENTORY_MANIFEST",
                None,
                inventory.manifest["receipt_sha256"],
                "LOCAL_METADATA",
                _json(
                    {
                        "run_id": run_id,
                        "database_sha256": inventory.manifest["database"]["sha256"],
                        "row_digest_sha256": inventory.manifest["database"][
                            "row_digest_sha256"
                        ],
                    }
                ),
            ),
        )
        root_path = inventory.manifest["root"]["path"]
        database.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                repository_id,
                "REPOSITORY",
                Path(root_path).name,
                ".",
                manifest_source,
                "PROVEN",
                structure_producer,
                run_id,
                "LOCAL_METADATA",
                run_id,
                run_id,
                _json(
                    {
                        "root": inventory.manifest["root"],
                        "git": {
                            "branch": inventory.manifest["git"]["branch"],
                            "head": inventory.manifest["git"]["head"],
                            "tree": inventory.manifest["git"]["tree"],
                        },
                    }
                ),
            ),
        )

        files = _inventory_connection(inventory)
        directories = {"."}
        logical_candidates: dict[tuple[str, str], list[str]] = {}
        file_count = 0
        sensitive_count = 0
        try:
            for row in files.execute(
                "SELECT path,semantic_reason FROM files ORDER BY path"
            ):
                path = row["path"]
                directories.update(_parent_directories(path))
                sensitive_count += int(row["semantic_reason"] == "sensitive-path")
                marker_root, _, marker_name = path.rpartition("/")
                marker_root_path = marker_root or "."
                marker_kind = PROJECT_MARKERS.get(marker_name)
                if marker_kind is not None:
                    logical_candidates.setdefault(
                        (marker_kind, marker_root_path), []
                    ).append(path)
                if marker_name == "__init__.py":
                    logical_candidates.setdefault(
                        ("PYTHON_PACKAGE", marker_root_path), []
                    ).append(path)
                file_count += 1
        finally:
            files.close()

        for path in sorted(directories):
            name = Path(root_path).name if path == "." else PurePosixPath(path).name
            database.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    _directory_id(root_key, path),
                    "DIRECTORY",
                    name,
                    path,
                    manifest_source,
                    "PROVEN",
                    structure_producer,
                    run_id,
                    "LOCAL_METADATA",
                    run_id,
                    run_id,
                    _json({"path": path}),
                ),
            )

        for (kind, path), markers in sorted(logical_candidates.items()):
            ordered_markers = sorted(markers)
            name = Path(root_path).name if path == "." else PurePosixPath(path).name
            container_id = _container_id(root_key, kind, path)
            database.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    container_id,
                    "LOGICAL_CONTAINER",
                    name,
                    f"{kind}:{path}",
                    manifest_source,
                    "PROVEN",
                    structure_producer,
                    run_id,
                    "LOCAL_METADATA",
                    run_id,
                    run_id,
                    _json(
                        {
                            "container_kind": kind,
                            "root_path": path,
                            "markers": ordered_markers,
                        }
                    ),
                ),
            )
            _insert_relation(
                database,
                subject=repository_id,
                predicate="DECLARES",
                object_=container_id,
                source_id=manifest_source,
                producer_id=structure_producer,
                snapshot_run_id=run_id,
            )
            _insert_relation(
                database,
                subject=container_id,
                predicate="ROOTED_AT",
                object_=_directory_id(root_key, path),
                source_id=manifest_source,
                producer_id=structure_producer,
                snapshot_run_id=run_id,
            )

        _insert_relation(
            database,
            subject=repository_id,
            predicate="CONTAINS",
            object_=_directory_id(root_key, "."),
            source_id=manifest_source,
            producer_id=structure_producer,
            snapshot_run_id=run_id,
        )
        for path in sorted(directories - {"."}):
            parent = PurePosixPath(path).parent
            parent_path = "." if parent == PurePosixPath(".") else parent.as_posix()
            _insert_relation(
                database,
                subject=_directory_id(root_key, parent_path),
                predicate="CONTAINS",
                object_=_directory_id(root_key, path),
                source_id=manifest_source,
                producer_id=structure_producer,
                snapshot_run_id=run_id,
            )

        database.executemany(
            "INSERT INTO coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                (
                    inventory_producer,
                    "inventory",
                    "ARTIFACT",
                    ".",
                    "COVERED",
                    file_count,
                    file_count,
                    0,
                    0,
                    0,
                    _json(
                        {
                            "parent_inventory_errors": inventory.manifest["counts"][
                                "errors"
                            ]
                        }
                    ),
                ),
                (
                    structure_producer,
                    "structure",
                    "FILESYSTEM_CONTAINMENT",
                    ".",
                    "COVERED",
                    file_count + len(directories),
                    file_count + len(directories),
                    0,
                    0,
                    0,
                    _json(
                        {
                            "artifact_facts": "federated-authenticated-inventory",
                            "artifact_containment": "derived-from-qualified-name",
                            "stored_relations": "repository-and-directory-ancestry",
                        }
                    ),
                ),
                (
                    structure_producer,
                    "structure",
                    "LOGICAL_CONTAINER",
                    "supported-marker-set",
                    "COVERED",
                    len(logical_candidates),
                    len(logical_candidates),
                    0,
                    0,
                    0,
                    _json(
                        {
                            "project_markers": sorted(PROJECT_MARKERS),
                            "python_packages": "__init__.py",
                        }
                    ),
                ),
                (
                    structure_producer,
                    "structure",
                    "LOGICAL_CONTAINER_FORMAT_SUPPORT",
                    ".",
                    "PARTIAL",
                    1,
                    0,
                    0,
                    1,
                    0,
                    _json({"reason": "logical-package-detection-not-implemented"}),
                ),
            ),
        )
        database.executemany(
            "INSERT INTO map_views VALUES (?,?,?,?,?)",
            (
                (
                    "inventory",
                    "1",
                    "AVAILABLE",
                    _json(["ARTIFACT"]),
                    _json(
                        {
                            "query": "path-or-name",
                            "exact_source": True,
                            "storage": "federated-authenticated-inventory",
                        }
                    ),
                ),
                (
                    "structure",
                    "1",
                    "AVAILABLE_PARTIAL",
                    _json(
                        [
                            "DIRECTORY",
                            "ARTIFACT",
                            "LOGICAL_CONTAINER",
                            "CONTAINS",
                            "DECLARES",
                            "ROOTED_AT",
                        ]
                    ),
                    _json(
                        {
                            "query": "path-or-name",
                            "ancestors": True,
                            "artifact_containment": "derived-from-qualified-name",
                            "logical_packages": "supported-marker-set",
                        }
                    ),
                ),
            ),
        )
        database.execute(
            "INSERT INTO run_inputs VALUES (?,?,?,?)",
            (
                "input:navigation-inventory",
                "NAVIGATION_INVENTORY",
                inventory.manifest["receipt_sha256"],
                _json(
                    {
                        "run_id": run_id,
                        "database_sha256": inventory.manifest["database"]["sha256"],
                        "root": inventory.manifest["root"],
                        "git": inventory.manifest["git"],
                    }
                ),
            ),
        )
        python_inputs = _python_input_set(inventory, root_key)
        python_sources = _insert_python_sources(
            database,
            inputs=python_inputs,
            root_key=root_key,
            snapshot_run_id=run_id,
        )
        python_started = time.monotonic()
        python_reused = _previous_python_group_reusable(
            previous, python_inputs.invalidation_key_sha256
        )
        if python_reused:
            if previous is None:  # narrowed above; keeps type and failure explicit
                raise MapperError("incremental Python reuse lost its previous run")
            python_fact_counts = _copy_python_group(
                database,
                previous=previous,
                snapshot_run_id=run_id,
            )
            try:
                python_counts = {
                    key: int(previous.manifest["counts"][key])
                    for key in PYTHON_COUNT_KEYS
                }
            except (KeyError, TypeError, ValueError) as exc:
                raise MapperError(
                    "previous Python producer count closure is incomplete"
                ) from exc
            python_counts.update(_python_fragment_counts(database))
            python_reused_fact_counts = {
                producer_id: python_fact_counts[producer_id]["facts"]
                for producer_id in PYTHON_PRODUCER_IDS
            }
        else:
            python_counts = _build_python_maps(
                database,
                inventory=inventory,
                root_key=root_key,
                repository_id=repository_id,
                manifest_source=manifest_source,
                producer_id=python_producer,
                operational_producer_id=operational_producer,
                quality_producer_id=quality_producer,
                snapshot_run_id=run_id,
                inputs=python_inputs,
                source_by_path=python_sources,
                previous=previous,
            )
            python_fact_counts = {
                producer_id: _producer_fact_counts(database, producer_id)
                for producer_id in PYTHON_PRODUCER_IDS
            }
            _carry_python_first_seen(database, previous=previous)
            python_reused_fact_counts = _projection_reuse_fact_counts(database)
        python_duration = time.monotonic() - python_started
        _record_python_input_bindings(
            database,
            inputs=python_inputs,
            per_producer_counts=python_fact_counts,
            reused_fact_counts=python_reused_fact_counts,
            full_group_reused=python_reused,
            duration_seconds=python_duration,
        )
        shell_counts = _build_shell_maps(
            database,
            inventory=inventory,
            root_key=root_key,
            producer_id=shell_producer,
            snapshot_run_id=run_id,
        )
        javascript_counts = _build_javascript_maps(
            database,
            inventory=inventory,
            root_key=root_key,
            producer_id=javascript_producer,
            snapshot_run_id=run_id,
        )
        scip_counts = _build_scip_maps(
            database,
            scip_inputs=scip_inputs,
            root_key=root_key,
            source_by_path=python_sources,
            manifest_source=manifest_source,
            snapshot_run_id=run_id,
        )
        python_executions = {
            row[0]: row[1]
            for row in database.execute(
                "SELECT producer_id,execution FROM producer_inputs"
            )
        }
        cleanup_counts = _build_cleanup_maps(
            database,
            inventory=inventory,
            root_key=root_key,
            manifest_source=manifest_source,
            producer_id=cleanup_producer,
            snapshot_run_id=run_id,
        )
        lineage_counts = _build_lineage_ownership_maps(
            database,
            inventory=inventory,
            root_key=root_key,
            repository_id=repository_id,
            manifest_source=manifest_source,
            producer_id=lineage_producer,
            snapshot_run_id=run_id,
        )
        governance_counts = _build_governance_maps(
            database,
            inventory=inventory,
            root_key=root_key,
            repository_id=repository_id,
            producer_id=governance_producer,
            snapshot_run_id=run_id,
        )
        runtime_counts = _build_runtime_maps(
            database,
            registries=runtime_registries,
            root_key=root_key,
            repository_id=repository_id,
            producer_id=runtime_producer,
            snapshot_run_id=run_id,
        )
        semantic_counts = _build_semantic_view(
            database,
            semantic_input=semantic_input,
            producer_id=semantic_producer,
        )
        derivation_counts = _materialize_derivations(database)
        database.commit()
        database.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        stored_entities = database.execute("SELECT count(*) FROM entities").fetchone()[
            0
        ]
        relations = database.execute("SELECT count(*) FROM relations").fetchone()[0]
        sources = database.execute("SELECT count(*) FROM sources").fetchone()[0]
        return {
            "sources": sources,
            "entities": file_count + stored_entities,
            "stored_entities": stored_entities,
            "federated_artifacts": file_count,
            "relations": relations,
            **derivation_counts,
            "artifacts": file_count,
            "directories": len(directories),
            "logical_containers": len(logical_candidates),
            "sensitive_metadata": sensitive_count,
            "incremental_producers_reused": sum(
                1 for item in python_executions.values() if item == "REUSED"
            ),
            "incremental_producers_partial": sum(
                1 for item in python_executions.values() if item == "PARTIAL"
            ),
            "incremental_producers_recomputed": sum(
                1 for item in python_executions.values() if item == "RECOMPUTED"
            ),
            "incremental_facts_reused": sum(python_reused_fact_counts.values()),
            "incremental_facts_recomputed": sum(
                python_fact_counts[producer_id]["facts"]
                - python_reused_fact_counts[producer_id]
                for producer_id in PYTHON_PRODUCER_IDS
            ),
            "incremental_python_duration_seconds": round(python_duration, 6),
            **python_counts,
            **scip_counts,
            **shell_counts,
            **javascript_counts,
            **cleanup_counts,
            **lineage_counts,
            **governance_counts,
            **runtime_counts,
            **semantic_counts,
        }
    except BaseException:
        database.rollback()
        raise
    finally:
        database.close()


def _materialize_derivations(connection: sqlite3.Connection) -> dict[str, int]:
    """Close explicit fact-to-source and parent-fact provenance.

    Facts already carry foreign keys to their immediate source and endpoints.
    The normalized derivation table makes those chains uniformly queryable
    without asking consumers to understand every fact table's shape.
    """

    connection.execute(
        """INSERT INTO derivations(fact_id,parent_kind,parent_id,ordinal)
           SELECT entity_id,'SOURCE',source_id,0 FROM entities
           WHERE source_id IS NOT NULL ORDER BY entity_id"""
    )
    connection.execute(
        """INSERT INTO derivations(fact_id,parent_kind,parent_id,ordinal)
           SELECT relation_id,'SOURCE',source_id,0 FROM relations
           WHERE source_id IS NOT NULL ORDER BY relation_id"""
    )
    connection.execute(
        """INSERT INTO derivations(fact_id,parent_kind,parent_id,ordinal)
           SELECT relation_id,'SUBJECT_ENTITY',subject_id,1 FROM relations
           ORDER BY relation_id"""
    )
    connection.execute(
        """INSERT INTO derivations(fact_id,parent_kind,parent_id,ordinal)
           SELECT relation_id,'OBJECT_ENTITY',object_id,2 FROM relations
           ORDER BY relation_id"""
    )
    connection.execute(
        """INSERT INTO derivations(fact_id,parent_kind,parent_id,ordinal)
           SELECT observation_id,'SOURCE',source_id,0 FROM observations
           WHERE source_id IS NOT NULL ORDER BY observation_id"""
    )
    connection.execute(
        """INSERT INTO derivations(fact_id,parent_kind,parent_id,ordinal)
           SELECT observation_id,'SUBJECT_ENTITY',entity_id,1 FROM observations
           ORDER BY observation_id"""
    )
    counts = {
        row[0]: int(row[1])
        for row in connection.execute(
            """SELECT parent_kind,COUNT(*) FROM derivations
               GROUP BY parent_kind ORDER BY parent_kind"""
        )
    }
    return {
        "derivations": sum(counts.values()),
        "derivation_sources": counts.get("SOURCE", 0),
        "derivation_subject_entities": counts.get("SUBJECT_ENTITY", 0),
        "derivation_object_entities": counts.get("OBJECT_ENTITY", 0),
    }


def _table_digest(connection: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    tables = (
        "producers",
        "sources",
        "entities",
        "artifact_properties",
        "relations",
        "observations",
        "locations",
        "derivations",
        "coverage",
        "conflicts",
        "map_views",
        "run_inputs",
        "producer_inputs",
        "python_fragments",
        "projection_reuse",
    )
    for table in tables:
        columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
        order = ",".join(columns)
        for row in connection.execute(f"SELECT * FROM {table} ORDER BY {order}"):
            digest.update(canonical_bytes([table, *row]))
    return digest.hexdigest()


def _database_summary(
    path: Path,
    *,
    include_row_digest: bool = True,
    integrity_check: bool = True,
) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        if integrity_check:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity != ("ok",):
                raise MapperError("mapper database integrity check failed")
        schema = connection.execute(
            "SELECT value FROM meta WHERE key='database_schema'"
        ).fetchone()
        if schema != (str(DATABASE_SCHEMA),):
            raise MapperError("mapper database schema mismatch")
        counts = {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in (
                "sources",
                "entities",
                "artifact_properties",
                "relations",
                "observations",
                "locations",
                "derivations",
                "coverage",
                "conflicts",
                "map_views",
                "run_inputs",
                "producer_inputs",
                "python_fragments",
                "projection_reuse",
            )
        }
        summary = {
            "schema_version": DATABASE_SCHEMA,
            "sqlite_version": sqlite3.sqlite_version,
            "counts": counts,
        }
        if include_row_digest:
            summary["row_digest_sha256"] = _table_digest(connection)
        return summary
    finally:
        connection.close()


def _render_report(manifest: Mapping[str, Any]) -> str:
    counts = manifest["counts"]
    return "\n".join(
        (
            "# GIGA Archaeology mapper M01-M11",
            "",
            f"- Status: **{manifest['status']}**",
            f"- Inventory run: `{manifest['inventory']['run_id']}`",
            f"- Artifacts: {counts['artifacts']:,}",
            f"- Directories: {counts['directories']:,}",
            f"- Entities: {counts['entities']:,}",
            f"- Relations: {counts['relations']:,}",
            f"- Python files parsed: {counts.get('python_files', 0):,}",
            f"- Python symbols: {counts.get('python_symbols', 0):,}",
            f"- Python references: {counts.get('python_references', 0):,}",
            f"- Python imports: {counts.get('python_imports', 0):,}",
            f"- Python/CLI entrypoints: {counts.get('python_entrypoints', 0):,}",
            f"- Python calls: {counts.get('python_calls', 0):,}",
            f"- Python calls resolved: {counts.get('python_calls_resolved', 0):,}",
            f"- Python control nodes: {counts.get('python_control_nodes', 0):,}",
            f"- Python control edges: {counts.get('python_control_edges', 0):,}",
            f"- Python static flows: {counts.get('python_static_flows', 0):,}",
            f"- Python possible data sources: {counts.get('python_data_sources', 0):,}",
            f"- Python possible security effects: {counts.get('python_security_effects', 0):,}",
            f"- Python possible source/effect paths: {counts.get('python_possible_taint_paths', 0):,}",
            f"- Python declared databases: {counts.get('python_declared_databases', 0):,}",
            f"- Python declared data objects: {counts.get('python_declared_data_objects', 0):,}",
            f"- Python literal SQL operations: {counts.get('python_literal_sql_operations', 0):,}",
            f"- Build/deployment assets: {counts.get('build_assets', 0):,}",
            f"- Python test candidates: {counts.get('python_test_candidates', 0):,}",
            f"- Static test targets: {counts.get('static_test_targets', 0):,}",
            f"- Coverage file summaries: {counts.get('coverage_files', 0):,}",
            f"- Quality artifacts: {counts.get('quality_assets', 0):,}",
            f"- Receipt-reported quality checks: {counts.get('quality_check_claims', 0):,}",
            f"- Receipt-command current-module links: {counts.get('quality_check_current_module_links', 0):,}",
            f"- Governed Markdown headings: {counts.get('governed_markdown_headings', 0):,}",
            f"- Governed explicit path references: {counts.get('governed_markdown_path_references', 0):,}",
            f"- Governed JSON path references: {counts.get('governed_json_path_references', 0):,}",
            f"- Exact duplicate groups: {counts.get('exact_duplicate_groups', 0):,}",
            f"- Static not-reached hypotheses: {counts.get('static_not_reached_hypotheses', 0):,}",
            f"- Recent Git commits mapped: {counts.get('git_commits_mapped', 0):,}",
            f"- Ownership-path candidates: {counts.get('ownership_paths', 0):,}",
            f"- Governed documents: {counts.get('governed_documents', 0):,}",
            f"- Exact evidence payload bindings: {counts.get('exact_evidence_payload_bindings', 0):,}",
            f"- Runtime registry inputs: {counts.get('runtime_registry_inputs', 0):,}",
            f"- Runtime capabilities: {counts.get('runtime_capabilities', 0):,}",
            f"- Runtime capabilities ACTIVE: {counts.get('runtime_capabilities_active', 0):,}",
            f"- Federated semantic graph inputs: {counts.get('semantic_graph_inputs', 0):,}",
            f"- Semantic nodes available: {counts.get('semantic_nodes_available', 0):,}",
            f"- Semantic edges available: {counts.get('semantic_edges_available', 0):,}",
            f"- Python parse failures: {counts.get('python_parse_failures', 0):,}",
            f"- Incremental producers reused: {counts.get('incremental_producers_reused', 0):,}",
            f"- Incremental producers partial: {counts.get('incremental_producers_partial', 0):,}",
            f"- Incremental facts reused: {counts.get('incremental_facts_reused', 0):,}",
            f"- Incremental facts recomputed: {counts.get('incremental_facts_recomputed', 0):,}",
            f"- Python fragments reused: {counts.get('python_fragments_reused', 0):,}",
            f"- Python fragments recomputed: {counts.get('python_fragments_recomputed', 0):,}",
            f"- Python fragments deleted: {counts.get('python_fragments_deleted', 0):,}",
            f"- Database SHA-256: `{manifest['database']['sha256']}`",
            f"- Fact row digest: `{manifest['database']['row_digest_sha256']}`",
            "",
            "M01 provides compact exact inventory, filesystem containment and supported-marker",
            "logical container views. Unrecognized package systems and every later map remain",
            "partial or planned as declared by the map catalogue. Exact artifact properties remain",
            "in the authenticated inventory and are projected through the mapper instead of copied",
            "into a second database. File-to-directory",
            "containment is derived exactly from each artifact path at query time instead of",
            "materializing one redundant edge per file.",
            "M02 adds non-importing Python AST definitions, references, imports, declared types",
            "and bounded CLI entrypoints with exact spans and explicit unresolved boundaries.",
            "M03 adds source-static call edges and source-level structured control paths. Runtime",
            "dispatch and implicit exception edges remain explicitly unsupported.",
            "M04 adds policy-versioned source-static MAY-flow and possible effect surfaces. These",
            "facts neither prove execution/vulnerability nor grant authority; clean claims remain",
            "forbidden while interprocedural and runtime coverage are incomplete.",
            "M05 adds closed literal SQLite declarations/operations and safe build/deployment",
            "declaration roles. It reads no database rows or private evidence and does not infer",
            "that a declared database, artifact or deployment exists or is active.",
            "M06 adds convention-discovered test candidates, static test target links and bounded",
            "coverage/quality artifact metadata. Names do not prove execution; unbound coverage",
            "M07 adds exact-content duplicate groups and supported static-root reachability. A",
            "not-reached result is only an inferred navigation hypothesis; the existing",
            "Counterevidence/Judge pipeline remains the cleanup candidate owner and deletion is",
            "never authorized by this map.",
            "M08 adds bounded exact Git-object history for current admitted paths and conservative",
            "path/CODEOWNERS declarations. A tracked source is only a canonical-source candidate;",
            "authoritative ownership still requires a separately validated governed contract.",
            "M09 adds strict governed-document metadata, explicit heading IDs, self-hash state and",
            "exact hash/payload bindings. A document's PASS field remains an observed claim rather",
            "than a verified outcome, and prose similarity never creates deterministic edges.",
            "M10 imports private, content-addressed capability-adoption registry snapshots and",
            "projects gate-reported owner, entrypoint, trigger, envelope, receipt pointer and",
            "freshness state. The external adoption gate remains the sole liveness authority;",
            "the map grants no execution authority and performs no process discovery.",
            "M11 federates the existing authenticated local Graphify store without duplicating",
            "its graph rows. Semantic results retain exact source locations and are qualified",
            "against both the graph's selected-file hash and the current deterministic inventory.",
            "Semantic facts remain non-authoritative and cannot override deterministic facts.",
            "M16 adds stable relation/observation identities and an authenticated compound-Python",
            "producer invalidation boundary. Unchanged Python/operational/quality facts are copied",
            "without rerunning those producers. M17 adds authenticated source-local Python and",
            "project-manifest fragments: unchanged files are not reparsed after a neighboring",
            "source changes. Cross-file resolution remains globally recomputed and is reported",
            "as such; dependency-level projection reuse is not implied by fragment counters.",
            "freshness and quality result status remain UNKNOWN or NOT_EVALUATED.",
            "This local index grants no authority and does not replace direct source verification.",
            "",
        )
    )


def _read_json(path: Path) -> dict[str, Any]:
    def closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise MapperError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=closed_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MapperError(f"cannot read mapper evidence: {path.name}") from exc
    if not isinstance(payload, dict):
        raise MapperError("mapper evidence root must be an object")
    return payload


def _bound_inventory_database(mapper_manifest: Mapping[str, Any]) -> Path:
    binding = mapper_manifest.get("inventory")
    if not isinstance(binding, Mapping):
        raise MapperError("mapper inventory binding is missing")
    run_id = binding.get("run_id")
    if (
        not isinstance(run_id, str)
        or not run_id
        or PurePosixPath(run_id).name != run_id
    ):
        raise MapperError("mapper inventory run identity is invalid")
    try:
        store = Path(binding["store"]).resolve(strict=True)
        run_directory = store / "runs" / run_id
        inventory_manifest_path = run_directory / "manifest.json"
        inventory_database = run_directory / "inventory.sqlite3"
        inventory_manifest_raw = inventory_manifest_path.read_bytes()
    except (KeyError, OSError, TypeError) as exc:
        raise MapperError("bound inventory run is unavailable") from exc
    if sha256_bytes(inventory_manifest_raw) != binding.get("manifest_file_sha256"):
        raise MapperError("bound inventory manifest file hash mismatch")
    inventory_manifest = _read_json(inventory_manifest_path)
    try:
        validate_self_hash(inventory_manifest)
    except ValueError as exc:
        raise MapperError(str(exc)) from exc
    if (
        inventory_manifest.get("run_id") != run_id
        or inventory_manifest.get("receipt_sha256") != binding.get("receipt_sha256")
        or inventory_manifest.get("database", {}).get("sha256")
        != binding.get("database_sha256")
        or inventory_manifest.get("database", {}).get("row_digest_sha256")
        != binding.get("row_digest_sha256")
    ):
        raise MapperError("bound inventory authority mismatch")
    database_hash, database_bytes = _file_sha256(inventory_database)
    if database_hash != binding.get(
        "database_sha256"
    ) or database_bytes != inventory_manifest["database"].get("bytes"):
        raise MapperError("bound inventory database identity mismatch")
    return inventory_database


def current_mapper_run(store: Path) -> MapperRun:
    original_store = store
    try:
        metadata = original_store.lstat()
    except OSError as exc:
        raise MapperError("mapper store does not exist") from exc
    if original_store.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise MapperError("mapper store must be a real directory")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise MapperError("mapper store identity or mode mismatch")
    store = original_store.resolve(strict=True)
    pointer_path = store / "CURRENT.json"
    pointer = _read_json(pointer_path)
    try:
        validate_self_hash(pointer)
    except ValueError as exc:
        raise MapperError(str(exc)) from exc
    if pointer.get("schema") != MAPPER_POINTER_SCHEMA:
        raise MapperError("mapper pointer schema mismatch")
    run_id = pointer.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise MapperError("mapper pointer has invalid run_id")
    run_directory = store / "runs" / run_id
    manifest_path = run_directory / "manifest.json"
    database_path = run_directory / "facts.sqlite3"
    if (
        not run_directory.is_dir()
        or not manifest_path.is_file()
        or not database_path.is_file()
    ):
        raise MapperError("mapper current run is incomplete")
    manifest_raw = manifest_path.read_bytes()
    if sha256_bytes(manifest_raw) != pointer.get("manifest_file_sha256"):
        raise MapperError("mapper manifest file hash mismatch")
    manifest = _read_json(manifest_path)
    try:
        validate_self_hash(manifest)
    except ValueError as exc:
        raise MapperError(str(exc)) from exc
    if manifest.get("schema") != MAPPER_SCHEMA or manifest.get("run_id") != run_id:
        raise MapperError("mapper manifest identity mismatch")
    if pointer.get("manifest_receipt_sha256") != manifest.get("receipt_sha256"):
        raise MapperError("mapper pointer receipt binding mismatch")
    if pointer.get("inventory_receipt_sha256") != manifest["inventory"].get(
        "receipt_sha256"
    ):
        raise MapperError("mapper pointer inventory binding mismatch")
    database_hash, database_bytes = _file_sha256(database_path)
    if database_hash != manifest["database"]["sha256"]:
        raise MapperError("mapper database hash mismatch")
    if database_bytes != manifest["database"]["bytes"]:
        raise MapperError("mapper database size mismatch")
    summary = _database_summary(
        database_path, include_row_digest=False, integrity_check=False
    )
    if summary["counts"] != manifest["database"]["counts"]:
        raise MapperError("mapper database counts mismatch")
    inventory_database = _bound_inventory_database(manifest)
    return MapperRun(
        run_directory=run_directory,
        manifest=manifest,
        inventory_database=inventory_database,
    )


def _current_optional(store: Path) -> MapperRun | None:
    pointer = store / "CURRENT.json"
    if not pointer.exists() and not pointer.is_symlink():
        return None
    try:
        return current_mapper_run(store)
    except MapperError as exc:
        if str(exc) == "mapper database schema mismatch":
            # A schema upgrade must be able to build beside the authenticated
            # old run and replace CURRENT only after the new run verifies.
            # Every other invalid-current condition remains a hard refusal.
            return None
        raise


def _semantic_input_record(
    semantic_store: Path,
    scanned_root: Path,
    inventory: NavigationRun,
) -> dict[str, Any]:
    supplied = semantic_store.absolute()
    try:
        metadata = supplied.lstat()
    except OSError as exc:
        raise MapperError("semantic store is missing") from exc
    resolved = supplied.resolve(strict=True)
    if (
        supplied != resolved
        or supplied.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise MapperError("semantic store must be a canonical private directory")
    try:
        resolved.relative_to(scanned_root)
    except ValueError:
        pass
    else:
        raise MapperError("semantic store must live outside the scanned repository")
    try:
        semantic = current_semantic_run(resolved)
    except (SemanticGraphError, OSError) as exc:
        raise MapperError(f"semantic graph input refused: {exc}") from exc
    manifest = semantic.manifest
    if (
        manifest.get("authority_granted") is not False
        or manifest.get("authority") != "non-authoritative-local-navigation-index"
    ):
        raise MapperError("semantic graph authority boundary differs")
    if manifest.get("root") != str(scanned_root):
        raise MapperError("semantic graph belongs to a different repository root")
    graph = manifest["graph"]
    inventory_binding = manifest["inventory"]
    inventory_matches = (
        inventory_binding["manifest_receipt_sha256"]
        == inventory.manifest["receipt_sha256"]
    )
    return {
        "store": str(resolved),
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "manifest_receipt_sha256": manifest["receipt_sha256"],
        "manifest_file_sha256": sha256_bytes(
            (semantic.run_directory / "manifest.json").read_bytes()
        ),
        "inventory_run_id": inventory_binding["run_id"],
        "inventory_receipt_sha256": inventory_binding["manifest_receipt_sha256"],
        "freshness": "CURRENT_INVENTORY_MATCH"
        if inventory_matches
        else "STALE_INVENTORY_MISMATCH",
        "coverage": {
            "selected": manifest["coverage"]["selected"],
            "supported": manifest["coverage"]["supported"],
            "documents_selected": manifest["coverage"]["documents_selected"],
            "documents_total": manifest["coverage"]["documents_total"],
            "selected_files_sha256": manifest["coverage"]["selected_files_sha256"],
            "failures": len(manifest["failures"]),
        },
        "graph": {
            "path": graph["path"],
            "sha256": graph["sha256"],
            "bytes": graph["bytes"],
            "raw_sha256": graph["raw_sha256"],
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        },
    }


def refresh_mapper(
    inventory_store: Path,
    mapper_store: Path,
    *,
    runtime_registries: Sequence[Path] = (),
    semantic_store: Path | None = None,
    scip_manifest: Path | None = None,
    scip_manifests: Sequence[Path] = (),
) -> MapperRun:
    """Compile and atomically publish implemented facts from an authenticated inventory."""

    inventory = current_navigation_run(inventory_store)
    scanned_root = Path(inventory.manifest["root"]["path"]).resolve(strict=True)
    normalized_runtime_paths = tuple(
        sorted({Path(path).absolute() for path in runtime_registries}, key=str)
    )
    if len(normalized_runtime_paths) != len(runtime_registries):
        raise MapperError("runtime registry inputs contain duplicates")
    try:
        runtime_inputs = tuple(
            load_runtime_registry(path, scanned_root)
            for path in normalized_runtime_paths
        )
    except (RuntimeMapError, OSError) as exc:
        raise MapperError(f"runtime registry input refused: {exc}") from exc
    if len({item.file_sha256 for item in runtime_inputs}) != len(runtime_inputs) or len(
        {item.registry["registry_sha256"] for item in runtime_inputs}
    ) != len(runtime_inputs):
        raise MapperError("runtime registry inputs contain duplicate evidence")
    runtime_input_records = [item.manifest_record() for item in runtime_inputs]
    semantic_input = (
        None
        if semantic_store is None
        else _semantic_input_record(semantic_store, scanned_root, inventory)
    )
    requested_scip_paths = tuple(Path(path).absolute() for path in scip_manifests)
    if scip_manifest is not None:
        requested_scip_paths += (Path(scip_manifest).absolute(),)
    normalized_scip_paths = tuple(sorted(set(requested_scip_paths), key=str))
    if len(normalized_scip_paths) != len(requested_scip_paths):
        raise MapperError("SCIP inputs contain duplicate manifest paths")
    try:
        scip_inputs = tuple(
            load_scip_index(path, inventory) for path in normalized_scip_paths
        )
    except (ScipMapError, OSError) as exc:
        raise MapperError(f"SCIP input refused: {exc}") from exc
    if len({item.manifest["receipt_sha256"] for item in scip_inputs}) != len(
        scip_inputs
    ) or len({item.manifest["index"]["sha256"] for item in scip_inputs}) != len(
        scip_inputs
    ):
        raise MapperError("SCIP inputs contain duplicate evidence")
    scip_document_paths = [
        document.relative_path
        for item in scip_inputs
        for document in item.index.documents
    ]
    if len(scip_document_paths) != len(set(scip_document_paths)):
        raise MapperError("SCIP input document closures overlap")
    scip_input_records = [item.manifest_record() for item in scip_inputs]
    scip_input_record = scip_input_records[0] if len(scip_input_records) == 1 else None
    store = _private_store(mapper_store, scanned_root)
    previous = _current_optional(store)
    compiler = _compiler_identity()
    if (
        previous is not None
        and previous.manifest["inventory"]["receipt_sha256"]
        == inventory.manifest["receipt_sha256"]
        and previous.manifest.get("compiler", {}).get("sha256") == compiler["sha256"]
        and previous.manifest.get("runtime_inputs", []) == runtime_input_records
        and previous.manifest.get("semantic_input") == semantic_input
        and previous.manifest.get("scip_inputs", []) == scip_input_records
    ):
        return previous

    started_at = _utc_now()
    started = time.monotonic()
    run_id = (
        f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid.uuid4().hex[:12]}"
    )
    staging = store / f".staging-{run_id}"
    runs = store / "runs"
    runs.mkdir(exist_ok=True, mode=0o700)
    if staging.exists() or staging.is_symlink():
        raise MapperError("mapper staging path unexpectedly exists")
    staging.mkdir(mode=0o700)
    try:
        database_path = staging / "facts.sqlite3"
        counts = _build_database(
            inventory,
            database_path,
            runtime_inputs,
            semantic_input,
            scip_inputs,
            previous,
        )
        os.chmod(database_path, 0o600)
        summary = _database_summary(database_path)
        database_hash, database_bytes = _file_sha256(database_path)
        finished_at = _utc_now()
        mapper_status = (
            "CURRENT"
            if inventory.manifest["status"] == "CURRENT"
            and counts["python_source_snapshot_failures"] == 0
            and not any(
                item.manifest["status"].endswith("_PARTIAL") for item in scip_inputs
            )
            else "PARTIAL"
        )
        manifest = seal_document(
            {
                "schema": MAPPER_SCHEMA,
                "status": mapper_status,
                "run_id": run_id,
                "authority": "non-authoritative-local-codebase-navigation-index",
                "authority_granted": False,
                "inventory": {
                    "store": str(Path(inventory_store).resolve(strict=True)),
                    "run_id": inventory.manifest["run_id"],
                    "receipt_sha256": inventory.manifest["receipt_sha256"],
                    "manifest_file_sha256": sha256_bytes(
                        (inventory.run_directory / "manifest.json").read_bytes()
                    ),
                    "database_sha256": inventory.manifest["database"]["sha256"],
                    "row_digest_sha256": inventory.manifest["database"][
                        "row_digest_sha256"
                    ],
                },
                "repository": {
                    "root": inventory.manifest["root"],
                    "git": inventory.manifest["git"],
                },
                "compiler": compiler,
                "runtime_inputs": runtime_input_records,
                "semantic_input": semantic_input,
                "scip_input": scip_input_record,
                "scip_inputs": scip_input_records,
                "scan": {
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duration_seconds": round(time.monotonic() - started, 6),
                    "incremental_from": None
                    if previous is None
                    else previous.manifest["run_id"],
                    "unchanged_inventory_reuses_current": True,
                    "incremental_scope": "compound-python-producer-with-source-fragments",
                    "incremental_source_granularity": "per-file-extraction-and-source-owned-fact-reuse",
                    "producers_reused": counts["incremental_producers_reused"],
                    "producers_partial": counts["incremental_producers_partial"],
                    "producers_recomputed": counts["incremental_producers_recomputed"],
                    "facts_reused": counts["incremental_facts_reused"],
                    "facts_recomputed": counts["incremental_facts_recomputed"],
                    "python_fragments": {
                        "total": counts["python_fragments_total"],
                        "reused": counts["python_fragments_reused"],
                        "recomputed": counts["python_fragments_recomputed"],
                        "deleted": counts["python_fragments_deleted"],
                    },
                    "cross_file_resolution": (
                        "AFFECTED_SOURCES_RECOMPUTED_PUBLIC_SURFACE_STABLE"
                        if counts["incremental_producers_partial"]
                        else "REUSED_WITH_UNCHANGED_PRODUCER_GROUP"
                        if counts["incremental_producers_reused"]
                        else "GLOBAL_RECOMPUTED_FROM_ASSEMBLED_FRAGMENTS"
                    ),
                    "global_producers_recomputed": [
                        "cleanup",
                        "governance",
                        "inventory",
                        "javascript",
                        "lineage_ownership",
                        "runtime",
                        "semantic_federation",
                        "shell",
                        "structure",
                    ],
                },
                "maps": {
                    "available": list(SUPPORTED_MAPS),
                    "inventory": "AVAILABLE",
                    "structure": "AVAILABLE_PARTIAL",
                    "logical_packages": "AVAILABLE_SUPPORTED_MARKERS",
                    "symbols": "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_AND_SCIP_PRECISE_PARTIAL"
                    if scip_inputs
                    else "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_PARTIAL",
                    "dependencies": "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_AND_SCIP_PRECISE_PARTIAL"
                    if scip_inputs
                    else "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_PARTIAL",
                    "types": "AVAILABLE_PYTHON_AND_SCIP_PRECISE_PARTIAL"
                    if scip_inputs
                    else "AVAILABLE_PYTHON_PARTIAL",
                    "api_events": "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_ENTRYPOINT_PARTIAL",
                    "calls": "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_STATIC_PARTIAL",
                    "control_flow": "AVAILABLE_PYTHON_STRUCTURED_PARTIAL",
                    "data_flow_taint": "AVAILABLE_PYTHON_STATIC_MAY_FLOW_PARTIAL",
                    "security_capabilities": "AVAILABLE_PYTHON_EFFECT_SURFACE_PARTIAL",
                    "database_lineage": "AVAILABLE_PYTHON_LITERAL_SQL_PARTIAL",
                    "build_deployment": "AVAILABLE_SAFE_DECLARATION_PARTIAL",
                    "tests_coverage": "AVAILABLE_STATIC_TEST_AND_COVERAGE_ARTIFACT_PARTIAL",
                    "quality_findings": "AVAILABLE_ARTIFACT_AND_SELF_HASHED_RECEIPT_CLAIM_PARTIAL",
                    "duplicates_similarity": (
                        "AVAILABLE_EXACT_AND_PYTHON_STRUCTURE_PARTIAL"
                    ),
                    "reachability": (
                        "AVAILABLE_STATIC_WITH_USAGE_COUNTEREVIDENCE_PARTIAL"
                    ),
                    "git_lineage": "AVAILABLE_SEARCHABLE_LINEAGE_SUMMARY_AND_EXACT_HISTORY_FACTS_PARTIAL",
                    "ownership_canonicality": "AVAILABLE_PATH_ROLE_OWNER_CONTRACT_AND_EXACT_VARIANTS_PARTIAL",
                    "requirements_decisions": "AVAILABLE_STRICT_DOCUMENT_HEADING_MARKDOWN_JSON_PATH_AND_EXPLICIT_ID_PARTIAL",
                    "evidence_claims": "AVAILABLE_SELF_HASH_AND_EXACT_BINDING_PARTIAL",
                    "runtime_topology": "AVAILABLE_EXTERNAL_GATE_STATUS_PARTIAL",
                    "semantic_graphify": "AVAILABLE_FEDERATED_LOCAL_GRAPHIFY_PARTIAL",
                },
                "counts": counts,
                "database": {
                    **summary,
                    "path": "facts.sqlite3",
                    "sha256": database_hash,
                    "bytes": database_bytes,
                },
                "failures": [],
            }
        )
        manifest_path = staging / "manifest.json"
        manifest_path.write_bytes(canonical_bytes(manifest))
        os.chmod(manifest_path, 0o600)
        report_path = staging / "REPORT.md"
        report_path.write_text(_render_report(manifest), encoding="utf-8")
        os.chmod(report_path, 0o600)

        candidate = MapperRun(
            staging,
            manifest,
            inventory.run_directory / "inventory.sqlite3",
        )
        database_summary = _database_summary(
            candidate.run_directory / "facts.sqlite3", include_row_digest=False
        )
        if database_summary["counts"] != manifest["database"]["counts"]:
            raise MapperError("mapper staging verification failed")

        final = runs / run_id
        os.rename(staging, final)
        directory = os.open(runs, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        pointer = seal_document(
            {
                "schema": MAPPER_POINTER_SCHEMA,
                "status": mapper_status,
                "run_id": run_id,
                "manifest_file_sha256": sha256_bytes(
                    (final / "manifest.json").read_bytes()
                ),
                "manifest_receipt_sha256": manifest["receipt_sha256"],
                "inventory_receipt_sha256": inventory.manifest["receipt_sha256"],
                "updated_at": finished_at,
            }
        )
        _replace_atomic(store / "CURRENT.json", canonical_bytes(pointer))
        return current_mapper_run(store)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _ancestors(
    connection: sqlite3.Connection,
    entity_id: str,
    *,
    entity_kind: str | None = None,
    qualified_name: str | None = None,
    ceiling: int = 128,
) -> list[dict[str, Any]]:
    if entity_kind is None or qualified_name is None:
        entity = connection.execute(
            "SELECT entity_kind,qualified_name FROM entities WHERE entity_id=?",
            (entity_id,),
        ).fetchone()
        if entity is None:
            raise MapperError("mapper entity disappeared during query")
        entity_kind, qualified_name = entity
    prefix: list[dict[str, Any]] = []
    origin = entity_id
    if entity_kind == "ARTIFACT":
        parent = PurePosixPath(qualified_name).parent
        parent_path = "." if parent == PurePosixPath(".") else parent.as_posix()
        directory = connection.execute(
            """SELECT entity_id,entity_kind,qualified_name FROM entities
               WHERE entity_kind='DIRECTORY' AND qualified_name=?""",
            (parent_path,),
        ).fetchone()
        if directory is None:
            raise MapperError("artifact parent directory is missing")
        prefix.append(
            {
                "entity_id": directory[0],
                "kind": directory[1],
                "qualified_name": directory[2],
                "depth": 1,
            }
        )
        origin = directory[0]
    rows = connection.execute(
        """WITH RECURSIVE parents(entity_id,depth) AS (
               SELECT subject_id,1 FROM relations
               WHERE predicate='CONTAINS' AND object_id=?
               UNION ALL
               SELECT r.subject_id,p.depth+1 FROM relations r JOIN parents p
                 ON r.object_id=p.entity_id
               WHERE r.predicate='CONTAINS' AND p.depth < ?
           )
           SELECT e.entity_id,e.entity_kind,e.qualified_name,p.depth
           FROM parents p JOIN entities e ON e.entity_id=p.entity_id
           ORDER BY p.depth""",
        (origin, ceiling),
    ).fetchall()
    physical = [
        {
            "entity_id": row[0],
            "kind": row[1],
            "qualified_name": row[2],
            "depth": row[3] + len(prefix),
        }
        for row in rows
    ]
    return [*prefix, *physical]


def _entity_facts(
    connection: sqlite3.Connection,
    entity_id: str,
    *,
    limit: int = 200,
    preferred_observation_predicates: Sequence[str] = (),
) -> dict[str, Any]:
    relation_rows = connection.execute(
        """SELECT r.*,ss.path AS source_path,
                  se.entity_kind AS subject_kind,se.qualified_name AS subject_name,
                  oe.entity_kind AS object_kind,oe.qualified_name AS object_name
           FROM relations r
           JOIN entities se ON se.entity_id=r.subject_id
           JOIN entities oe ON oe.entity_id=r.object_id
           LEFT JOIN sources ss ON ss.source_id=r.source_id
           WHERE r.subject_id=? OR r.object_id=?
           ORDER BY r.predicate,r.subject_id,r.object_id,r.relation_id
           LIMIT ?""",
        (entity_id, entity_id, limit + 1),
    ).fetchall()
    priorities = tuple(dict.fromkeys(preferred_observation_predicates))
    priority_order = (
        "CASE o.predicate "
        + " ".join(f"WHEN ? THEN {index}" for index, _ in enumerate(priorities))
        + f" ELSE {len(priorities)} END"
        if priorities
        else "CASE WHEN 1 THEN 0 END"
    )
    observation_rows = connection.execute(
        f"""SELECT o.*,s.path AS source_path,
                  l.line_start,l.line_end,l.column_start,l.column_end
           FROM observations o
           LEFT JOIN sources s ON s.source_id=o.source_id
           LEFT JOIN locations l ON l.location_id=o.observation_id
           WHERE o.entity_id=? OR json_extract(o.value_json,'$.target_entity_id')=?
           ORDER BY {priority_order},o.predicate,o.observation_id
           LIMIT ?""",
        (entity_id, entity_id, *priorities, limit + 1),
    ).fetchall()
    fact_derivations = _fact_derivations(
        connection,
        [
            *(row["relation_id"] for row in relation_rows[:limit]),
            *(row["observation_id"] for row in observation_rows[:limit]),
        ],
    )
    relations = []
    for row in relation_rows[:limit]:
        outgoing = row["subject_id"] == entity_id
        relations.append(
            {
                "relation_id": row["relation_id"],
                "direction": "OUTGOING" if outgoing else "INCOMING",
                "predicate": row["predicate"],
                "other": {
                    "entity_id": row["object_id"] if outgoing else row["subject_id"],
                    "kind": row["object_kind"] if outgoing else row["subject_kind"],
                    "qualified_name": row["object_name"]
                    if outgoing
                    else row["subject_name"],
                },
                "truth_class": row["truth_class"],
                "confidence": row["confidence"],
                "first_seen_run_id": row["first_seen_run_id"],
                "last_seen_run_id": row["last_seen_run_id"],
                "source_path": row["source_path"],
                "attributes": json.loads(row["attributes_json"]),
                "derivations": fact_derivations.get(row["relation_id"], []),
            }
        )
    observations = []
    for row in observation_rows[:limit]:
        value = json.loads(row["value_json"])
        observations.append(
            {
                "observation_id": row["observation_id"],
                "role": "OWNED" if row["entity_id"] == entity_id else "TARGETED",
                "predicate": row["predicate"],
                "value": value,
                "truth_class": row["truth_class"],
                "confidence": row["confidence"],
                "first_seen_run_id": row["first_seen_run_id"],
                "last_seen_run_id": row["last_seen_run_id"],
                "source": {
                    "path": row["source_path"],
                    "line_start": row["line_start"],
                    "line_end": row["line_end"],
                    "column_start": row["column_start"],
                    "column_end": row["column_end"],
                },
                "derivations": fact_derivations.get(row["observation_id"], []),
            }
        )
    return {
        "relations": relations,
        "observations": observations,
        "relations_truncated": len(relation_rows) > limit,
        "observations_truncated": len(observation_rows) > limit,
        "fact_limit": limit,
    }


def _entity_location(
    connection: sqlite3.Connection, entity_id: str
) -> dict[str, Any] | None:
    """Return an entity's exact source span when its producer recorded one."""

    row = connection.execute(
        """SELECT l.path,l.byte_start,l.byte_end,l.line_start,l.line_end,
                  l.column_start,l.column_end
           FROM locations l JOIN observations o ON o.observation_id=l.location_id
           WHERE o.entity_id=?
           ORDER BY CASE o.predicate
                      WHEN 'PYTHON_DEFINITION' THEN 0
                      WHEN 'SHELL_DEFINITION' THEN 0
                      WHEN 'JAVASCRIPT_DEFINITION' THEN 0
                      ELSE 1
                    END,
                    o.predicate,o.observation_id LIMIT 1""",
        (entity_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def _fact_derivations(
    connection: sqlite3.Connection, fact_ids: Sequence[str]
) -> dict[str, list[dict[str, Any]]]:
    """Return deterministic normalized provenance for a bounded fact set."""

    identifiers = tuple(dict.fromkeys(fact_ids))
    if not identifiers:
        return {}
    rows = connection.execute(
        f"""SELECT fact_id,parent_kind,parent_id,ordinal FROM derivations
            WHERE fact_id IN ({",".join("?" for _ in identifiers)})
            ORDER BY fact_id,ordinal,parent_kind,parent_id""",
        identifiers,
    ).fetchall()
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(row["fact_id"], []).append(
            {
                "parent_kind": row["parent_kind"],
                "parent_id": row["parent_id"],
                "ordinal": row["ordinal"],
            }
        )
    return result


def _semantic_query_results(
    binding: Mapping[str, Any] | None,
    query: str,
    inventory: sqlite3.Connection,
    *,
    limit: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Query the bound Graphify store without allowing its CURRENT pointer to drift."""

    if binding is None:
        return [], False
    try:
        store = Path(binding["store"])
        current = current_semantic_run(store)
    except (KeyError, OSError, SemanticGraphError) as exc:
        raise MapperError(f"bound semantic graph is unavailable: {exc}") from exc
    manifest = current.manifest
    manifest_file_sha256 = sha256_bytes(
        (current.run_directory / "manifest.json").read_bytes()
    )
    if (
        manifest.get("run_id") != binding.get("run_id")
        or manifest.get("receipt_sha256") != binding.get("manifest_receipt_sha256")
        or manifest_file_sha256 != binding.get("manifest_file_sha256")
        or manifest.get("graph", {}).get("sha256")
        != binding.get("graph", {}).get("sha256")
    ):
        raise MapperError(
            "semantic graph advanced or drifted after mapper refresh; refresh the mapper"
        )
    selected_files = manifest.get("coverage", {}).get("selected_files")
    if not isinstance(selected_files, list) or sha256_bytes(
        canonical_bytes(selected_files)
    ) != binding.get("coverage", {}).get("selected_files_sha256"):
        raise MapperError("semantic graph selected-file binding mismatch")
    selected_hashes: dict[str, str] = {}
    for item in selected_files:
        if not isinstance(item, dict):
            raise MapperError("semantic graph selected-file entry is invalid")
        path = item.get("path")
        digest = item.get("sha256")
        if (
            not isinstance(path, str)
            or not path
            or PurePosixPath(path).is_absolute()
            or any(part in ("", ".", "..") for part in PurePosixPath(path).parts)
            or not isinstance(digest, str)
            or len(digest) != 64
            or path in selected_hashes
        ):
            raise MapperError("semantic graph selected-file identity is invalid")
        selected_hashes[path] = digest
    locate_limit = min(500, limit + 1)
    try:
        located = locate_semantic_graph(store, query, limit=locate_limit)
        validate_self_hash(located)
    except (SemanticGraphError, ValueError) as exc:
        raise MapperError(f"semantic graph query refused: {exc}") from exc
    if (
        located.get("graph", {}).get("run_id") != binding.get("run_id")
        or located.get("graph", {}).get("sha256")
        != binding.get("graph", {}).get("sha256")
        or located.get("authority_granted") is not False
    ):
        raise MapperError("semantic locate result is not bound to the mapper input")

    node_by_id = {item.get("id"): item for item in located["nodes"]}
    incident: dict[Any, list[dict[str, Any]]] = {
        identifier: [] for identifier in node_by_id
    }
    for edge in located["edges"]:
        fact = {
            "source": edge.get("source"),
            "target": edge.get("target"),
            "relation": edge.get("relation"),
            "semantic_confidence": edge.get("confidence"),
            "source_path": edge.get("source_file"),
            "source_location": edge.get("source_location"),
            "truth_class": "INFERRED",
            "authority_granted": False,
        }
        if edge.get("source") in incident:
            incident[edge["source"]].append(fact)
        if edge.get("target") in incident and edge.get("target") != edge.get("source"):
            incident[edge["target"]].append(fact)

    results: list[dict[str, Any]] = []
    graph_sha256 = binding["graph"]["sha256"]
    for node in located["nodes"]:
        node_id = node.get("id")
        path = node.get("source_file")
        selected_sha256 = selected_hashes.get(path) if isinstance(path, str) else None
        current_sha256 = None
        source_freshness = "UNKNOWN_SOURCE"
        if isinstance(path, str) and path:
            pure = PurePosixPath(path)
            if pure.is_absolute() or any(
                part in ("", ".", "..") for part in pure.parts
            ):
                raise MapperError("semantic graph node has unsafe source path")
            current_row = inventory.execute(
                "SELECT content_sha256,hash_status FROM files WHERE path=?", (path,)
            ).fetchone()
            if current_row is None:
                source_freshness = "MISSING_CURRENT_SOURCE"
            else:
                current_sha256 = current_row["content_sha256"]
                if selected_sha256 is None:
                    source_freshness = "UNSELECTED_SOURCE"
                elif (
                    current_row["hash_status"] in ("hashed", "reused")
                    and current_sha256 == selected_sha256
                ):
                    source_freshness = "CURRENT_SOURCE_MATCH"
                else:
                    source_freshness = "STALE_SOURCE_HASH"
        semantic_entity_id = (
            "semantic:"
            + hashlib.sha256(
                canonical_bytes(
                    {
                        "graph_sha256": graph_sha256,
                        "node_id": node_id,
                    }
                )
            ).hexdigest()
        )
        results.append(
            {
                "entity_id": semantic_entity_id,
                "kind": "SEMANTIC_CONCEPT",
                "name": str(node.get("label") or node_id or "semantic concept"),
                "qualified_name": f"semantic:{node_id}",
                "truth_class": "INFERRED",
                "privacy_class": "LOCAL_SEMANTIC_METADATA",
                "source": {
                    "path": path,
                    "source_location": node.get("source_location"),
                    "identity_sha256": selected_sha256 or graph_sha256,
                },
                "attributes": {
                    "file_type": node.get("file_type"),
                    "matched_terms": node.get("matched_terms", []),
                    "score": node.get("score"),
                    "semantic_graph_run_id": binding["run_id"],
                    "semantic_graph_sha256": graph_sha256,
                    "semantic_graph_freshness": binding["freshness"],
                    "source_freshness": source_freshness,
                    "selected_source_sha256": selected_sha256,
                    "current_source_sha256": current_sha256,
                    "authority_granted": False,
                    "deterministic_fact_override": False,
                },
                "facts": {
                    "semantic_relations": sorted(
                        incident.get(node_id, []),
                        key=lambda item: (
                            str(item["source"]),
                            str(item["relation"]),
                            str(item["target"]),
                            str(item["source_path"]),
                        ),
                    ),
                    "relations_truncated": False,
                },
            }
        )
    return results, len(located["nodes"]) > limit


def _query_ranking(
    item: Mapping[str, Any],
    query: str,
    *,
    selected_maps: Sequence[str],
    primary_maps: Sequence[str],
) -> dict[str, Any]:
    """Describe deterministic presentation order without minting a new fact."""

    kind = str(item["kind"])
    selected_matches = [
        map_id for map_id in selected_maps if kind in MAP_ENTITY_KINDS[map_id]
    ]
    primary_matches = [
        map_id for map_id in primary_maps if kind in MAP_ENTITY_KINDS[map_id]
    ]
    folded = query.casefold()
    qualified = str(item["qualified_name"]).casefold()
    name = str(item["name"]).casefold()
    if qualified == folded:
        lexical_tier = "EXACT_QUALIFIED_NAME"
        lexical_order = 0
    elif name == folded:
        lexical_tier = "EXACT_NAME"
        lexical_order = 1
    elif qualified.endswith("." + folded) or qualified.endswith("/" + folded):
        lexical_tier = "QUALIFIED_SUFFIX"
        lexical_order = 2
    else:
        lexical_tier = "SUBSTRING_OR_SEARCH_METADATA"
        lexical_order = 3
    return {
        "algorithm": "giga.map-aware-query-order.v2",
        "derived_not_fact": True,
        "primary_map_match": bool(primary_matches),
        "primary_map_matches": primary_matches,
        "selected_map_matches": selected_matches,
        "lexical_match": lexical_tier,
        "_sort": (
            0 if primary_matches else 1,
            0 if kind == "GIT_LINEAGE_SUMMARY" else 1,
            lexical_order,
            -len(primary_matches),
            kind,
            str(item["qualified_name"]),
        ),
    }


def query_mapper(
    store: Path,
    query: str,
    *,
    maps: Sequence[str] = ("inventory", "structure"),
    limit: int = 50,
    fact_limit: int = 50,
    include_facts: bool = True,
    include_ancestors: bool = True,
    search_query: str | None = None,
    routing: Mapping[str, Any] | None = None,
    _authenticated_run: MapperRun | None = None,
) -> dict[str, Any]:
    """Return exact implemented map results from the current fact store."""

    if not query or "\x00" in query:
        raise MapperError("mapper query must be non-empty")
    if isinstance(limit, bool) or limit <= 0 or limit > 1000:
        raise MapperError("mapper query limit must be between 1 and 1000")
    if isinstance(fact_limit, bool) or fact_limit <= 0 or fact_limit > 500:
        raise MapperError("mapper fact limit must be between 1 and 500")
    if not isinstance(include_ancestors, bool):
        raise MapperError("include_ancestors must be a boolean")
    effective_query = query if search_query is None else search_query
    if (
        not isinstance(effective_query, str)
        or not effective_query
        or "\x00" in effective_query
    ):
        raise MapperError("mapper search query must be non-empty")
    selected = tuple(dict.fromkeys(maps))
    if not selected:
        raise MapperError("at least one mapper view is required")
    unsupported = sorted(set(selected) - set(SUPPORTED_MAPS))
    if unsupported:
        raise MapperError(f"mapper views are not implemented: {', '.join(unsupported)}")
    routing_record = None
    primary_maps = selected
    if routing is not None:
        routing_record = dict(routing)
        try:
            validate_self_hash(routing_record)
        except (TypeError, ValueError) as exc:
            raise MapperError("mapper query routing receipt is invalid") from exc
        if routing_record.get("query") != query:
            raise MapperError("mapper query routing receipt binds a different query")
        if routing_record.get("search_query") != effective_query:
            raise MapperError(
                "mapper query routing receipt binds a different search query"
            )
        if tuple(routing_record.get("selected_maps", ())) != selected:
            raise MapperError("mapper query routing receipt binds different views")
        primary_maps = tuple(routing_record.get("primary_maps", ()))
        if not primary_maps or not set(primary_maps) <= set(selected):
            raise MapperError("mapper query routing receipt has invalid primary views")
    run = (
        _authenticated_run
        if _authenticated_run is not None
        else current_mapper_run(store)
    )
    database_path = run.run_directory / "facts.sqlite3"
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    inventory = sqlite3.connect(f"file:{run.inventory_database}?mode=ro", uri=True)
    inventory.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        inventory.execute("PRAGMA query_only=ON")
        available_views = {
            row[0] for row in connection.execute("SELECT map_id FROM map_views")
        }
        unavailable = sorted(set(selected) - available_views)
        if unavailable:
            raise MapperError(
                f"mapper views are absent from this run: {', '.join(unavailable)}"
            )
        allowed_kinds = {
            kind for map_id in selected for kind in MAP_ENTITY_KINDS[map_id]
        }
        allowed_kinds.difference_update({"ARTIFACT", "SEMANTIC_CONCEPT"})
        preferred_observation_predicates = (
            MAP_OBSERVATION_PRIORITIES.get("reachability", ())
            if selected == ("reachability",)
            else ()
        )
        primary_local_kinds = sorted(
            {
                kind
                for map_id in primary_maps
                for kind in MAP_ENTITY_KINDS[map_id]
                if kind not in {"ARTIFACT", "SEMANTIC_CONCEPT"}
            }
        )
        local_kinds = sorted(allowed_kinds) or ["__NO_LOCAL_ENTITY_KIND__"]
        primary_order = (
            f"CASE WHEN e.entity_kind IN ({','.join('?' for _ in primary_local_kinds)}) THEN 0 ELSE 1 END,"
            if primary_local_kinds
            else "CASE WHEN 1=1 THEN 0 ELSE 1 END,"
        )
        pattern = f"%{_like(effective_query.casefold())}%"
        local_rows = connection.execute(
            f"""SELECT e.*,s.path AS source_path,s.identity_sha256 AS source_sha256
               FROM entities e
               LEFT JOIN sources s ON s.source_id=e.source_id
               WHERE e.entity_kind IN ({",".join("?" for _ in local_kinds)})
                 AND (lower(e.name) LIKE ? ESCAPE '\\'
                  OR lower(e.qualified_name) LIKE ? ESCAPE '\\'
                  OR lower(COALESCE(json_extract(e.attributes_json,'$.search_text'),'')) LIKE ? ESCAPE '\\'
                  OR lower(COALESCE(s.path,'')) LIKE ? ESCAPE '\\')
               ORDER BY {primary_order}
                        CASE WHEN e.entity_kind='GIT_LINEAGE_SUMMARY' THEN 0 ELSE 1 END,
                        CASE
                          WHEN lower(e.qualified_name)=? THEN 0
                          WHEN lower(e.name)=? THEN 1
                          WHEN lower(e.qualified_name) LIKE ? ESCAPE '\\' THEN 2
                          ELSE 3
                        END,
                        e.entity_kind,e.qualified_name
               LIMIT ?""",
            (
                *local_kinds,
                pattern,
                pattern,
                pattern,
                pattern,
                *primary_local_kinds,
                effective_query.casefold(),
                effective_query.casefold(),
                f"%.{_like(effective_query.casefold())}",
                limit + 1,
            ),
        ).fetchall()
        artifact_rows = []
        if {"inventory", "structure"} & set(selected):
            artifact_rows = inventory.execute(
                """SELECT * FROM files
                   WHERE lower(path) LIKE ? ESCAPE '\\'
                   ORDER BY CASE
                              WHEN lower(path)=? THEN 0
                              WHEN lower(path)=? OR lower(path) LIKE ? ESCAPE '\\' THEN 1
                              ELSE 2
                            END,path
                   LIMIT ?""",
                (
                    pattern,
                    effective_query.casefold(),
                    effective_query.casefold(),
                    f"%/{_like(effective_query.casefold())}",
                    limit + 1,
                ),
            ).fetchall()
        candidates: list[dict[str, Any]] = []
        for row in local_rows:
            attributes = json.loads(row["attributes_json"])
            source_path = row["source_path"]
            source_identity = row["source_sha256"]
            if row["entity_kind"] == "LOGICAL_CONTAINER":
                source_path = attributes["markers"][0]
                marker = inventory.execute(
                    "SELECT * FROM files WHERE path=?",
                    (source_path,),
                ).fetchone()
                if marker is None:
                    raise MapperError("logical container marker is missing")
                marker_record = dict(marker)
                marker_record.pop("id", None)
                source_identity = _source_identity(marker_record)
            item = {
                "entity_id": row["entity_id"],
                "kind": row["entity_kind"],
                "name": row["name"],
                "qualified_name": row["qualified_name"],
                "truth_class": row["truth_class"],
                "confidence": row["confidence"],
                "first_seen_run_id": row["first_seen_run_id"],
                "last_seen_run_id": row["last_seen_run_id"],
                "privacy_class": row["privacy_class"],
                "source": {
                    "path": source_path,
                    "identity_sha256": source_identity,
                },
                "attributes": attributes,
                "derivations": _fact_derivations(connection, (row["entity_id"],)).get(
                    row["entity_id"], []
                ),
            }
            location = _entity_location(connection, row["entity_id"])
            if location is not None:
                item["source"]["location"] = location
            if include_ancestors and "structure" in selected:
                item["ancestors"] = _ancestors(
                    connection,
                    row["entity_id"],
                    entity_kind=row["entity_kind"],
                    qualified_name=row["qualified_name"],
                )
            if include_facts and {
                "symbols",
                "dependencies",
                "types",
                "api_events",
                "calls",
                "control_flow",
                "data_flow_taint",
                "security_capabilities",
                "database_lineage",
                "build_deployment",
                "tests_coverage",
                "quality_findings",
                "duplicates_similarity",
                "reachability",
                "git_lineage",
                "ownership_canonicality",
                "requirements_decisions",
                "evidence_claims",
                "runtime_topology",
                "symbols",
                "dependencies",
                "types",
            } & set(selected):
                item["facts"] = _entity_facts(
                    connection,
                    row["entity_id"],
                    limit=fact_limit,
                    preferred_observation_predicates=(preferred_observation_predicates),
                )
            candidates.append(item)

        semantic_truncated = False
        if "semantic_graphify" in selected:
            semantic_results, semantic_truncated = _semantic_query_results(
                run.manifest.get("semantic_input"),
                effective_query,
                inventory,
                limit=limit,
            )
            candidates.extend(semantic_results)

        root_key = connection.execute(
            "SELECT value FROM meta WHERE key='root_key'"
        ).fetchone()[0]
        for row in artifact_rows:
            record = dict(row)
            record.pop("id", None)
            path = record.pop("path")
            source_identity = _source_identity({"path": path, **record})
            artifact_entity_id = _artifact_id(root_key, path)
            item = {
                "entity_id": artifact_entity_id,
                "kind": "ARTIFACT",
                "name": PurePosixPath(path).name,
                "qualified_name": path,
                "truth_class": "PROVEN",
                "confidence": None,
                "privacy_class": _privacy(record),
                "source": {"path": path, "identity_sha256": source_identity},
                "attributes": {
                    key: record[key]
                    for key in (
                        "content_sha256",
                        "kind",
                        "size_bytes",
                        "mtime_ns",
                        "ctime_ns",
                        "mode",
                        "uid",
                        "gid",
                        "device",
                        "inode",
                        "nlink",
                        "hash_status",
                        "git_status",
                        "git_tracked",
                        "git_blob_oid",
                        "suffix",
                        "media_type",
                        "semantic_eligible",
                        "semantic_reason",
                        "scan_error",
                    )
                },
                "derivations": _fact_derivations(connection, (artifact_entity_id,)).get(
                    artifact_entity_id, []
                ),
            }
            if include_ancestors and "structure" in selected:
                item["ancestors"] = _ancestors(
                    connection,
                    item["entity_id"],
                    entity_kind="ARTIFACT",
                    qualified_name=path,
                )
            candidates.append(item)

        for item in candidates:
            ranking = _query_ranking(
                item,
                effective_query,
                selected_maps=selected,
                primary_maps=primary_maps,
            )
            item["ranking"] = {
                key: value for key, value in ranking.items() if key != "_sort"
            }
            item["_query_sort"] = ranking["_sort"]
        candidates.sort(key=lambda item: item["_query_sort"])
        truncated = len(candidates) > limit or semantic_truncated
        results = candidates[:limit]
        for item in results:
            del item["_query_sort"]
        coverage = []
        for row in connection.execute(
            f"SELECT * FROM coverage WHERE map_id IN ({','.join('?' for _ in selected)}) ORDER BY map_id,fact_class,scope",
            selected,
        ):
            item = dict(row)
            item["details"] = json.loads(item.pop("details_json"))
            coverage.append(item)
    finally:
        inventory.close()
        connection.close()
    return seal_document(
        {
            "schema": MAPPER_QUERY_SCHEMA,
            "status": "PASS",
            "authority": "non-authoritative-codebase-navigation-result",
            "authority_granted": False,
            "mapper_run_id": run.manifest["run_id"],
            "mapper_manifest_receipt_sha256": run.manifest["receipt_sha256"],
            "inventory_run_id": run.manifest["inventory"]["run_id"],
            "inventory_receipt_sha256": run.manifest["inventory"]["receipt_sha256"],
            "query": query,
            "search_query": effective_query,
            "maps": list(selected),
            "limit": limit,
            "fact_limit": fact_limit,
            "include_facts": include_facts,
            "include_ancestors": include_ancestors,
            "routing": routing_record,
            "ranking_policy": {
                "algorithm": "giga.map-aware-query-order.v1",
                "map_catalog_receipt_sha256": build_map_catalog()["receipt_sha256"],
                "primary_maps": list(primary_maps),
                "dependency_only_matches_rank_after_primary_maps": True,
                "lexical_match_breaks_ties_within_map_fit": True,
                "derived_not_fact": True,
            },
            "results": results,
            "coverage": coverage,
            "result_count": len(results),
            "truncated": truncated,
        }
    )


def audit_mapper(store: Path) -> dict[str, Any]:
    """Prove the normalized fact model and all 22 query views on one exact run.

    This is a read-only integrity receipt.  It authenticates the current mapper
    first, then checks referential integrity, source/location/parent provenance,
    the closed confidence rubric, coverage registration, and one real query
    through the complete view set.  It grants no architectural or execution
    authority and does not turn PARTIAL coverage into CURRENT coverage.
    """

    run = current_mapper_run(store)
    database_path = run.run_directory / "facts.sqlite3"
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    failures: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}

    def count(sql: str) -> int:
        return int(connection.execute(sql).fetchone()[0])

    def require_zero(check_id: str, sql: str) -> None:
        found = count(sql)
        checks[check_id] = {
            "violations": found,
            "status": "PASS" if found == 0 else "FAIL",
        }
        if found:
            failures.append({"check": check_id, "violations": found})

    try:
        connection.execute("PRAGMA query_only=ON")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_violations = len(
            connection.execute("PRAGMA foreign_key_check").fetchall()
        )
        checks["sqlite_integrity"] = {
            "integrity_check": integrity,
            "foreign_key_violations": foreign_key_violations,
            "status": "PASS"
            if integrity == "ok" and foreign_key_violations == 0
            else "FAIL",
        }
        if integrity != "ok" or foreign_key_violations:
            failures.append(
                {
                    "check": "sqlite_integrity",
                    "integrity_check": integrity,
                    "foreign_key_violations": foreign_key_violations,
                }
            )

        map_views = tuple(
            row[0]
            for row in connection.execute(
                "SELECT map_id FROM map_views ORDER BY map_id"
            )
        )
        coverage_maps = tuple(
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT map_id FROM coverage ORDER BY map_id"
            )
        )
        expected_maps = tuple(sorted(SUPPORTED_MAPS))
        map_registration_pass = (
            map_views == expected_maps
            and coverage_maps == expected_maps
            and tuple(sorted(run.manifest["maps"]["available"])) == expected_maps
        )
        checks["map_registration"] = {
            "status": "PASS" if map_registration_pass else "FAIL",
            "expected": len(expected_maps),
            "registered_views": len(map_views),
            "covered_maps": len(coverage_maps),
        }
        if not map_registration_pass:
            failures.append(
                {
                    "check": "map_registration",
                    "missing_views": sorted(set(expected_maps) - set(map_views)),
                    "missing_coverage": sorted(set(expected_maps) - set(coverage_maps)),
                    "unexpected_views": sorted(set(map_views) - set(expected_maps)),
                    "unexpected_coverage": sorted(
                        set(coverage_maps) - set(expected_maps)
                    ),
                }
            )

        require_zero(
            "every_fact_has_source",
            """SELECT
                 (SELECT COUNT(*) FROM entities WHERE source_id IS NULL) +
                 (SELECT COUNT(*) FROM relations WHERE source_id IS NULL) +
                 (SELECT COUNT(*) FROM observations WHERE source_id IS NULL)""",
        )
        require_zero(
            "source_derivations",
            """SELECT
                 (SELECT COUNT(*) FROM entities e WHERE NOT EXISTS (
                    SELECT 1 FROM derivations d WHERE d.fact_id=e.entity_id
                      AND d.parent_kind='SOURCE' AND d.parent_id=e.source_id)) +
                 (SELECT COUNT(*) FROM relations r WHERE NOT EXISTS (
                    SELECT 1 FROM derivations d WHERE d.fact_id=r.relation_id
                      AND d.parent_kind='SOURCE' AND d.parent_id=r.source_id)) +
                 (SELECT COUNT(*) FROM observations o WHERE NOT EXISTS (
                    SELECT 1 FROM derivations d WHERE d.fact_id=o.observation_id
                      AND d.parent_kind='SOURCE' AND d.parent_id=o.source_id))""",
        )
        require_zero(
            "relation_parent_derivations",
            """SELECT COUNT(*) FROM relations r WHERE NOT EXISTS (
                   SELECT 1 FROM derivations d WHERE d.fact_id=r.relation_id
                     AND d.parent_kind='SUBJECT_ENTITY' AND d.parent_id=r.subject_id)
                 OR NOT EXISTS (
                   SELECT 1 FROM derivations d WHERE d.fact_id=r.relation_id
                     AND d.parent_kind='OBJECT_ENTITY' AND d.parent_id=r.object_id)""",
        )
        require_zero(
            "observation_parent_derivations",
            """SELECT COUNT(*) FROM observations o WHERE NOT EXISTS (
                   SELECT 1 FROM derivations d WHERE d.fact_id=o.observation_id
                     AND d.parent_kind='SUBJECT_ENTITY' AND d.parent_id=o.entity_id)""",
        )
        require_zero(
            "derivation_kind_closure",
            """SELECT COUNT(*) FROM derivations
                 WHERE parent_kind NOT IN
                   ('SOURCE','SUBJECT_ENTITY','OBJECT_ENTITY')""",
        )
        require_zero(
            "location_source_provenance",
            """SELECT COUNT(*) FROM locations l
                 LEFT JOIN observations o ON o.observation_id=l.location_id
                 LEFT JOIN relations r ON r.relation_id=l.location_id
                 WHERE COALESCE(o.source_id,r.source_id) IS NULL
                    OR COALESCE(o.source_id,r.source_id)<>l.source_id""",
        )

        confidence_values = ",".join(str(value) for value in INFERRED_CONFIDENCE_VALUES)
        for table in ("entities", "relations", "observations"):
            require_zero(
                f"{table}_confidence_closure",
                f"""SELECT COUNT(*) FROM {table}
                      WHERE (truth_class='INFERRED'
                             AND (confidence IS NULL OR confidence NOT IN ({confidence_values})))
                         OR (truth_class<>'INFERRED' AND confidence IS NOT NULL)""",
            )
        confidence_distribution = {
            table: [
                {"truth_class": row[0], "confidence": row[1], "facts": int(row[2])}
                for row in connection.execute(
                    f"""SELECT truth_class,confidence,COUNT(*) FROM {table}
                         GROUP BY truth_class,confidence
                         ORDER BY truth_class,confidence"""
                )
            ]
            for table in ("entities", "relations", "observations")
        }
        derivation_distribution = {
            row[0]: int(row[1])
            for row in connection.execute(
                """SELECT parent_kind,COUNT(*) FROM derivations
                   GROUP BY parent_kind ORDER BY parent_kind"""
            )
        }

        stable_id_violations = 0
        for row in connection.execute(
            """SELECT relation_id,subject_id,predicate,object_id,source_id,
                      producer_id,attributes_json FROM relations"""
        ):
            expected = _fact_id(
                [
                    row["subject_id"],
                    row["predicate"],
                    row["object_id"],
                    row["source_id"],
                    row["producer_id"],
                    row["attributes_json"],
                ]
            )
            stable_id_violations += int(expected != row["relation_id"])
        for row in connection.execute(
            """SELECT observation_id,entity_id,predicate,value_json,source_id,
                      producer_id FROM observations"""
        ):
            expected = _fact_id(
                [
                    row["entity_id"],
                    row["predicate"],
                    row["value_json"],
                    row["source_id"],
                    row["producer_id"],
                ]
            )
            stable_id_violations += int(expected != row["observation_id"])
        checks["stable_fact_ids"] = {
            "status": "PASS" if stable_id_violations == 0 else "FAIL",
            "violations": stable_id_violations,
        }
        if stable_id_violations:
            failures.append(
                {"check": "stable_fact_ids", "violations": stable_id_violations}
            )

        current_run_id = run.manifest["inventory"]["run_id"]
        history_violations = sum(
            int(
                connection.execute(
                    f"""SELECT COUNT(*) FROM {table}
                        WHERE first_seen_run_id=''
                           OR last_seen_run_id<>?
                           OR snapshot_run_id<>?""",
                    (current_run_id, current_run_id),
                ).fetchone()[0]
            )
            for table in ("entities", "relations", "observations")
        )
        checks["fact_history_closure"] = {
            "status": "PASS" if history_violations == 0 else "FAIL",
            "violations": history_violations,
        }
        if history_violations:
            failures.append(
                {"check": "fact_history_closure", "violations": history_violations}
            )

        producer_input_rows = connection.execute(
            "SELECT * FROM producer_inputs ORDER BY producer_id"
        ).fetchall()
        bound_inventory = NavigationRun(
            run_directory=run.inventory_database.parent,
            manifest=_read_json(run.inventory_database.parent / "manifest.json"),
        )
        root_key = connection.execute(
            "SELECT value FROM meta WHERE key='root_key'"
        ).fetchone()[0]
        current_python_inputs = _python_input_set(bound_inventory, root_key)
        fragment_rows = {
            row["path"]: row
            for row in connection.execute(
                "SELECT * FROM python_fragments ORDER BY path"
            )
        }
        package_directories = frozenset(
            str(PurePosixPath(record["path"]).parent)
            for record in current_python_inputs.python_records
            if PurePosixPath(record["path"]).name == "__init__.py"
        )
        extractor_sha256 = _file_sha256(
            Path(extract_python_file_fragment.__code__.co_filename).resolve()
        )[0]
        expected_fragments: dict[str, tuple[str, str, str]] = {}
        for record in current_python_inputs.python_records:
            expected_fragments[record["path"]] = (
                "PYTHON_SOURCE",
                _producer_source_identity(record),
                sha256_bytes(
                    canonical_bytes(
                        {
                            "fragment_kind": "PYTHON_SOURCE",
                            "module": python_module_name(
                                record["path"], package_directories
                            ),
                        }
                    )
                ),
            )
        project_context = sha256_bytes(
            canonical_bytes({"fragment_kind": "PROJECT_MANIFEST", "format": "TOML"})
        )
        for record in current_python_inputs.project_records:
            expected_fragments[record["path"]] = (
                "PROJECT_MANIFEST",
                _producer_source_identity(record),
                project_context,
            )
        fragment_violations = int(set(fragment_rows) != set(expected_fragments))
        for path, (kind, source_identity, context_sha256) in expected_fragments.items():
            row = fragment_rows.get(path)
            if row is None:
                continue
            try:
                cached = _fragment_payload(
                    row,
                    expected_kind=kind,
                    expected_source_identity=source_identity,
                    expected_context=context_sha256,
                    expected_extractor=extractor_sha256,
                )
            except MapperError:
                cached = None
            fragment_violations += int(
                cached is None
                or row["last_seen_run_id"] != current_run_id
                or not row["first_seen_run_id"]
                or _json(cached[0]) != row["payload_json"]
            )
        fragment_reused = sum(
            row["execution"] == "REUSED" for row in fragment_rows.values()
        )
        fragment_recomputed = sum(
            row["execution"] == "RECOMPUTED" for row in fragment_rows.values()
        )
        fragment_scan = run.manifest["scan"].get("python_fragments", {})
        expected_deleted = 0
        previous_run_id = run.manifest["scan"].get("incremental_from")
        if previous_run_id is not None:
            if (
                not isinstance(previous_run_id, str)
                or PurePosixPath(previous_run_id).name != previous_run_id
            ):
                fragment_violations += 1
            else:
                previous_directory = run.run_directory.parent / previous_run_id
                previous_manifest_path = previous_directory / "manifest.json"
                previous_database_path = previous_directory / "facts.sqlite3"
                try:
                    previous_manifest = _read_json(previous_manifest_path)
                    validate_self_hash(previous_manifest)
                    previous_database_sha256, _ = _file_sha256(previous_database_path)
                    if (
                        previous_database_sha256
                        != previous_manifest["database"]["sha256"]
                    ):
                        raise MapperError("previous mapper database hash mismatch")
                    prior = sqlite3.connect(
                        f"file:{previous_database_path}?mode=ro", uri=True
                    )
                    try:
                        prior.execute("PRAGMA query_only=ON")
                        prior_paths = {
                            row[0]
                            for row in prior.execute(
                                "SELECT path FROM python_fragments ORDER BY path"
                            )
                        }
                    finally:
                        prior.close()
                    expected_deleted = len(prior_paths - set(expected_fragments))
                except (
                    KeyError,
                    OSError,
                    ValueError,
                    sqlite3.DatabaseError,
                    MapperError,
                ):
                    fragment_violations += 1
        fragment_violations += int(
            fragment_reused + fragment_recomputed != len(fragment_rows)
            or fragment_scan.get("total") != len(fragment_rows)
            or fragment_scan.get("reused") != fragment_reused
            or fragment_scan.get("recomputed") != fragment_recomputed
            or fragment_scan.get("deleted") != expected_deleted
        )
        checks["python_fragment_closure"] = {
            "status": "PASS" if fragment_violations == 0 else "FAIL",
            "violations": fragment_violations,
            "fragments": len(fragment_rows),
            "reused": fragment_reused,
            "recomputed": fragment_recomputed,
            "deleted": fragment_scan.get("deleted"),
            "resolution_scope": run.manifest["scan"].get("cross_file_resolution"),
        }
        if fragment_violations:
            failures.append(
                {
                    "check": "python_fragment_closure",
                    "violations": fragment_violations,
                }
            )
        expected_producers = tuple(sorted(PYTHON_PRODUCER_IDS))
        actual_producers = tuple(row["producer_id"] for row in producer_input_rows)
        incremental_failures = 0
        for row in producer_input_rows:
            try:
                scope = json.loads(row["input_scope_json"])
            except json.JSONDecodeError:
                incremental_failures += 1
                continue
            actual = _producer_fact_counts(connection, row["producer_id"])["facts"]
            key = row["invalidation_key_sha256"]
            source_digest = row["source_identities_sha256"]
            incremental_failures += int(
                len(key) != 64
                or any(character not in "0123456789abcdef" for character in key)
                or len(source_digest) != 64
                or any(
                    character not in "0123456789abcdef" for character in source_digest
                )
                or row["source_count"] < 0
                or row["source_count"] != len(current_python_inputs.records_by_path)
                or key != current_python_inputs.invalidation_key_sha256
                or source_digest != current_python_inputs.source_identities_sha256
                or scope.get("coupled_producers") != list(PYTHON_PRODUCER_IDS)
                or scope.get("implementation_sha256")
                != current_python_inputs.implementation_sha256
                or row["facts_reused"] + row["facts_recomputed"] != actual
                or (row["execution"] == "REUSED" and row["facts_recomputed"] != 0)
                or (row["execution"] == "RECOMPUTED" and row["facts_reused"] != 0)
                or (
                    row["execution"] == "PARTIAL"
                    and (row["facts_reused"] == 0 or row["facts_recomputed"] == 0)
                )
            )
        manifest_reused = int(run.manifest["scan"].get("facts_reused", -1))
        manifest_recomputed = int(run.manifest["scan"].get("facts_recomputed", -1))
        table_reused = sum(int(row["facts_reused"]) for row in producer_input_rows)
        table_recomputed = sum(
            int(row["facts_recomputed"]) for row in producer_input_rows
        )
        incremental_failures += int(actual_producers != expected_producers)
        incremental_failures += int(manifest_reused != table_reused)
        incremental_failures += int(manifest_recomputed != table_recomputed)
        incremental_failures += int(
            int(run.manifest["scan"].get("producers_reused", -1))
            != sum(row["execution"] == "REUSED" for row in producer_input_rows)
        )
        incremental_failures += int(
            int(run.manifest["scan"].get("producers_partial", -1))
            != sum(row["execution"] == "PARTIAL" for row in producer_input_rows)
        )
        projection_reused = int(
            connection.execute(
                """SELECT COALESCE(SUM(
                       entities_reused+relations_reused+observations_reused),0)
                   FROM projection_reuse"""
            ).fetchone()[0]
        )
        partial_producers = sum(
            row["execution"] == "PARTIAL" for row in producer_input_rows
        )
        all_reused = bool(producer_input_rows) and all(
            row["execution"] == "REUSED" for row in producer_input_rows
        )
        incremental_failures += int(
            projection_reused != (0 if all_reused else table_reused)
        )
        incremental_failures += int(
            table_reused > 0 and run.manifest["scan"].get("incremental_from") is None
        )
        incremental_failures += int(
            run.manifest["scan"].get("incremental_scope")
            != "compound-python-producer-with-source-fragments"
            or run.manifest["scan"].get("incremental_source_granularity")
            != "per-file-extraction-and-source-owned-fact-reuse"
            or run.manifest["scan"].get("cross_file_resolution")
            != (
                "REUSED_WITH_UNCHANGED_PRODUCER_GROUP"
                if all_reused
                else "AFFECTED_SOURCES_RECOMPUTED_PUBLIC_SURFACE_STABLE"
                if partial_producers
                else "GLOBAL_RECOMPUTED_FROM_ASSEMBLED_FRAGMENTS"
            )
        )
        checks["incremental_input_closure"] = {
            "status": "PASS" if incremental_failures == 0 else "FAIL",
            "violations": incremental_failures,
            "producers": len(producer_input_rows),
            "facts_reused": table_reused,
            "facts_recomputed": table_recomputed,
        }
        if incremental_failures:
            failures.append(
                {
                    "check": "incremental_input_closure",
                    "violations": incremental_failures,
                }
            )
    finally:
        connection.close()

    query_probe = query_mapper(
        store,
        "__mapper_integrity_probe_no_match__",
        maps=SUPPORTED_MAPS,
        limit=1,
        fact_limit=1,
        include_facts=False,
        _authenticated_run=run,
    )
    query_pass = (
        query_probe["status"] == "PASS" and tuple(query_probe["maps"]) == SUPPORTED_MAPS
    )
    checks["all_map_query_probe"] = {
        "status": "PASS" if query_pass else "FAIL",
        "maps": len(query_probe["maps"]),
        "query_receipt_sha256": query_probe["receipt_sha256"],
    }
    if not query_pass:
        failures.append({"check": "all_map_query_probe"})

    return seal_document(
        {
            "schema": MAPPER_AUDIT_SCHEMA,
            "status": "PASS" if not failures else "FAIL",
            "authority": "non-authoritative-local-mapper-integrity-audit",
            "authority_granted": False,
            "audited_at": _utc_now(),
            "mapper": {
                "run_id": run.manifest["run_id"],
                "status": run.manifest["status"],
                "manifest_receipt_sha256": run.manifest["receipt_sha256"],
                "database_sha256": run.manifest["database"]["sha256"],
                "database_row_digest_sha256": run.manifest["database"][
                    "row_digest_sha256"
                ],
                "inventory_run_id": run.manifest["inventory"]["run_id"],
                "inventory_receipt_sha256": run.manifest["inventory"]["receipt_sha256"],
            },
            "checks": checks,
            "confidence": {
                "allowed_inferred_values": list(INFERRED_CONFIDENCE_VALUES),
                "default_static_inference": DEFAULT_STATIC_INFERENCE_CONFIDENCE,
                "distribution": confidence_distribution,
            },
            "derivations": derivation_distribution,
            "failures": failures,
            "claims": {
                "all_22_map_views_queryable": query_pass,
                "fact_integrity_satisfied": not failures,
                "whole_folder_current": run.manifest["status"] == "CURRENT",
                "exhaustive_architecture_claim_allowed": False,
                "execution_authority_granted": False,
            },
        }
    )
