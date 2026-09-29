from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.operations.archaeology import scip_map

from modules.operations.archaeology.evidence import (
    canonical_bytes,
    seal_document,
    sha256_bytes,
)
from modules.operations.archaeology.dossier import (
    build_context_projection,
    build_dossier,
)
from modules.operations.archaeology.mapper import (
    MapperError,
    query_mapper,
    refresh_mapper,
)
from modules.operations.archaeology.navigation_inventory import (
    current_navigation_run,
    refresh_navigation_inventory,
)
from modules.operations.archaeology.scip_map import (
    SCIP_MANIFEST_SCHEMA,
    SCIP_PROJECT_CATALOG_SCHEMA,
    SCIP_PYTHON_NPM_INTEGRITY,
    SCIP_TYPESCRIPT_NPM_INTEGRITY,
    ScipMapError,
    _reuse_previous_python_index,
    current_scip_store,
    discover_scip_projects,
    load_scip_index,
    parse_scip_index,
    refresh_scip_store,
)


def _varint(value: int) -> bytes:
    result = bytearray()
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def _field(number: int, value: int | bytes | str) -> bytes:
    if isinstance(value, int):
        return _varint(number << 3) + _varint(value)
    if isinstance(value, str):
        value = value.encode()
    return _varint((number << 3) | 2) + _varint(len(value)) + value


def test_python_scip_repair_is_exact_and_rejects_ambiguous_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken = scip_map._SCIP_PYTHON_BROKEN_FRAGMENT
    repaired = scip_map._SCIP_PYTHON_REPAIRED_FRAGMENT
    payload = b"prefix:" + broken + b":suffix"
    expected = b"prefix:" + repaired + b":suffix"
    monkeypatch.setattr(
        scip_map, "SCIP_PYTHON_ENTRYPOINT_SHA256", sha256_bytes(payload)
    )
    monkeypatch.setattr(
        scip_map, "SCIP_PYTHON_PATCHED_ENTRYPOINT_SHA256", sha256_bytes(expected)
    )
    assert scip_map._patch_scip_python_entrypoint(payload) == expected
    with pytest.raises(ScipMapError, match="entrypoint identity"):
        scip_map._patch_scip_python_entrypoint(payload + b"drift")
    duplicate = broken + broken
    monkeypatch.setattr(
        scip_map, "SCIP_PYTHON_ENTRYPOINT_SHA256", sha256_bytes(duplicate)
    )
    with pytest.raises(ScipMapError, match="repair target is not unique"):
        scip_map._patch_scip_python_entrypoint(duplicate)


def test_python_scip_private_runtime_copies_only_admitted_regular_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "package"
    dist = package / "dist"
    typeshed = dist / "typeshed-fallback" / "stdlib"
    typeshed.mkdir(parents=True)
    payload = b"prefix:" + scip_map._SCIP_PYTHON_BROKEN_FRAGMENT + b":suffix"
    repaired = b"prefix:" + scip_map._SCIP_PYTHON_REPAIRED_FRAGMENT + b":suffix"
    entrypoint = dist / "scip-python.js"
    entrypoint.write_bytes(payload)
    (dist / "vendor.js").write_bytes(b"vendor")
    (dist / "pyright-internal.js").write_bytes(b"pyright")
    (typeshed / "subprocess.pyi").write_bytes(b"class CompletedProcess: ...\n")
    package_digest = scip_map._tree_digest(package)[0]
    monkeypatch.setattr(scip_map, "SCIP_PYTHON_PACKAGE_TREE_SHA256", package_digest)
    monkeypatch.setattr(
        scip_map, "SCIP_PYTHON_ENTRYPOINT_SHA256", sha256_bytes(payload)
    )
    monkeypatch.setattr(
        scip_map, "SCIP_PYTHON_PATCHED_ENTRYPOINT_SHA256", sha256_bytes(repaired)
    )
    monkeypatch.setattr(scip_map, "SCIP_PYTHON_VENDOR_SHA256", sha256_bytes(b"vendor"))
    monkeypatch.setattr(
        scip_map, "SCIP_PYTHON_PYRIGHT_SHA256", sha256_bytes(b"pyright")
    )
    staging = tmp_path / "staging"
    staging.mkdir()
    runtime_entrypoint = scip_map._prepare_patched_python_runtime(
        package, entrypoint, staging, package_digest
    )
    assert runtime_entrypoint.read_bytes() == repaired
    assert (runtime_entrypoint.parent / "vendor.js").read_bytes() == b"vendor"
    assert (
        runtime_entrypoint.parent / "typeshed-fallback/stdlib/subprocess.pyi"
    ).read_bytes() == b"class CompletedProcess: ...\n"
    assert all(not item.is_symlink() for item in runtime_entrypoint.parent.rglob("*"))
    assert runtime_entrypoint.stat().st_mode & 0o777 == 0o600


def test_python_project_configuration_is_exact_and_stable() -> None:
    sources = [
        {"path": "pkg/helper.py"},
        {"path": "pkg/main.py"},
    ]

    raw = scip_map._python_project_configuration(sources)
    parsed = tomllib.loads(raw.decode("utf-8"))

    assert parsed["tool"]["pyright"]["include"] == [
        "pkg/helper.py",
        "pkg/main.py",
    ]
    assert parsed["tool"]["pyright"]["exclude"] == []
    assert raw == scip_map._python_project_configuration(sources)
    with pytest.raises(ScipMapError, match="stable closure"):
        scip_map._python_project_configuration(list(reversed(sources)))


def test_python_snapshot_indexes_exact_bytes_and_records_live_drift(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    shadow = tmp_path / "shadow"
    (root / ".hidden").mkdir(parents=True)
    shadow.mkdir()
    hidden = b"HIDDEN = True\n"
    stable = b"STABLE = True\n"
    changed_before = b"VALUE = 'before'\n"
    (root / ".hidden/worker.py").write_bytes(hidden)
    (root / "stable.py").write_bytes(stable)
    (root / "changed.py").write_bytes(b"VALUE = 'after'\n")
    sources = [
        {
            "path": ".hidden/worker.py",
            "content_sha256": sha256_bytes(hidden),
            "size_bytes": len(hidden),
        },
        {
            "path": "changed.py",
            "content_sha256": sha256_bytes(changed_before),
            "size_bytes": len(changed_before),
        },
        {
            "path": "stable.py",
            "content_sha256": sha256_bytes(stable),
            "size_bytes": len(stable),
        },
        {
            "path": "missing.py",
            "content_sha256": "f" * 64,
            "size_bytes": 10,
        },
    ]

    indexed, excluded = scip_map._snapshot_python_sources(root, shadow, sources)

    assert indexed == [sources[2]]
    assert (shadow / "stable.py").read_bytes() == stable
    assert (shadow / "stable.py").stat().st_mode & 0o777 == 0o600
    assert [item["path"] for item in excluded] == [
        ".hidden/worker.py",
        "changed.py",
        "missing.py",
    ]
    assert {item["reason"] for item in excluded} == {
        "CURRENT_SOURCE_DRIFTED_BEFORE_INDEXING",
        "SCIP_PYTHON_DOT_PATH_UNSUPPORTED",
    }
    assert all(len(item["tool_error_sha256"]) == 64 for item in excluded)


def _occurrence(symbol: str, line: int, start: int, end: int, roles: int = 0) -> bytes:
    packed = b"".join(_varint(item) for item in (line, start, end))
    return _field(1, packed) + _field(2, symbol) + _field(3, roles) + _field(5, 15)


def _symbol(symbol: str, name: str, kind: int = 12) -> bytes:
    return _field(1, symbol) + _field(5, kind) + _field(6, name)


def _typescript_index(paths: list[str], *, package: str = "fixture") -> bytes:
    tool = _field(1, "scip-typescript") + _field(2, "0.4.0")
    metadata = (
        _field(1, 0)
        + _field(2, tool)
        + _field(3, "file:///private/fixture")
        + _field(4, 1)
    )
    symbol = f"scip-typescript npm {package} 1.0.0 `src/core`/buildService()."
    result = bytearray(_field(1, metadata))
    for path in paths:
        document = _field(1, path) + _field(4, "typescript") + _field(6, 1)
        if path == "src/core.ts":
            document += _field(2, _occurrence(symbol, 9, 16, 28, roles=1))
            document += _field(3, _symbol(symbol, "buildService", 12))
        elif path == "src/main.ts":
            document += _field(2, _occurrence(symbol, 2, 32, 44))
        result.extend(_field(2, document))
    return bytes(result)


def _index(
    paths: list[str], *, embed_text: bool = False, duplicate_occurrence: bool = False
) -> bytes:
    tool = _field(1, "scip-python") + _field(2, "0.6.6") + _field(3, "fixture")
    metadata = (
        _field(1, 0)
        + _field(2, tool)
        + _field(3, "file:///private/fixture")
        + _field(4, 1)
    )
    result = bytearray(_field(1, metadata))
    for path in paths:
        document = _field(1, path) + _field(4, "python") + _field(6, 1)
        if path.endswith("cli.py"):
            project = "scip-python python fixture mapped-python 1 pkg.cli/Child#run()."
            external = "scip-python python 3.11 builtins/set#add()."
            document += _field(2, _occurrence(project, 7, 8, 11, roles=1))
            document += _field(2, _occurrence(external, 8, 15, 18))
            if duplicate_occurrence:
                document += _field(2, _occurrence(external, 8, 15, 18))
            document += _field(3, _symbol(project, "run"))
        if embed_text:
            document += _field(5, "source must not be retained")
        result.extend(_field(2, document))
    result.extend(
        _field(3, _symbol("scip-python python 3.11 builtins/set#add().", "add", 6))
    )
    return bytes(result)


@pytest.fixture()
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Fixture"], cwd=root, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "<redacted-email>"],
        cwd=root,
        check=True,
    )
    (root / "pkg").mkdir()
    (root / "pkg/__init__.py").write_text("", encoding="utf-8")
    (root / "pkg/base.py").write_text("class Base:\n    pass\n", encoding="utf-8")
    (root / "pkg/cli.py").write_text(
        "class Child:\n    def run(self, values):\n        result = set()\n        result.add(values)\n        return result\n",
        encoding="utf-8",
    )
    (root / "pkg/never.py").write_text(
        "raise RuntimeError('do not import')\n", encoding="utf-8"
    )
    (root / "web/src").mkdir(parents=True)
    (root / "web/package.json").write_text(
        '{"name":"fixture","private":true,"version":"1.0.0"}\n', encoding="utf-8"
    )
    (root / "web/tsconfig.json").write_text(
        '{"compilerOptions":{"strict":true},"include":["src/**/*.ts"]}\n',
        encoding="utf-8",
    )
    (root / "web/src/core.ts").write_text(
        "export function buildService(): number { return 1; }\n", encoding="utf-8"
    )
    (root / "web/src/main.ts").write_text(
        'import { buildService } from "./core";\nbuildService();\n', encoding="utf-8"
    )
    (root / "web2/src").mkdir(parents=True)
    (root / "web2/package.json").write_text(
        '{"name":"fixture-two","private":true,"version":"1.0.0"}\n',
        encoding="utf-8",
    )
    (root / "web2/tsconfig.json").write_text(
        '{"compilerOptions":{"strict":true},"include":["src/**/*.ts"]}\n',
        encoding="utf-8",
    )
    (root / "web2/src/core.ts").write_text(
        "export function buildService(): number { return 2; }\n", encoding="utf-8"
    )
    (root / "web2/src/main.ts").write_text(
        'import { buildService } from "./core";\nbuildService();\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    return root


def _write_input(inventory_store: Path, output: Path, payload: bytes) -> Path:
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    connection.row_factory = __import__("sqlite3").Row
    rows = [
        dict(row)
        for row in connection.execute(
            """SELECT path,content_sha256,size_bytes FROM files
               WHERE semantic_eligible=1 AND kind='regular' AND suffix='.py'
                 AND scan_error IS NULL AND hash_status IN ('hashed','reused')
               ORDER BY path"""
        )
    ]
    connection.close()
    output.mkdir(mode=0o700)
    index_path = output / "index.scip"
    index_path.write_bytes(payload)
    index_path.chmod(0o600)
    parsed = parse_scip_index(payload)
    occurrences = sum(len(item.occurrences) for item in parsed.documents)
    definitions = sum(
        bool(item.roles & 1) for doc in parsed.documents for item in doc.occurrences
    )
    manifest = seal_document(
        {
            "schema": SCIP_MANIFEST_SCHEMA,
            "status": "OBSERVED_LOCAL_PRECISION_INDEX",
            "authority_granted": False,
            "inventory": {"receipt_sha256": inventory.manifest["receipt_sha256"]},
            "sources": {
                "files": rows,
                "closure_sha256": sha256_bytes(canonical_bytes(rows)),
                "source_text_embedded": False,
            },
            "tool": {
                "package": "@sourcegraph/scip-python",
                "version": "0.6.6",
                "npm_integrity": SCIP_PYTHON_NPM_INTEGRITY,
            },
            "index": {
                "path": "index.scip",
                "sha256": sha256_bytes(payload),
                "bytes": len(payload),
            },
            "counts": {
                "documents": len(parsed.documents),
                "occurrences": occurrences,
                "definitions": definitions,
                "references": occurrences - definitions,
                "symbols": sum(len(item.symbols) for item in parsed.documents),
                "external_symbols": len(parsed.external_symbols),
                "relationships": 0,
            },
        }
    )
    manifest_path = output / "manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest))
    manifest_path.chmod(0o600)
    return manifest_path


def _write_typescript_input(
    inventory_store: Path, output: Path, payload: bytes, *, project_root: str = "web"
) -> Path:
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    connection.row_factory = __import__("sqlite3").Row
    prefix = f"{project_root}/"
    sources = [
        dict(row)
        for row in connection.execute(
            """SELECT path,content_sha256,size_bytes FROM files
               WHERE semantic_eligible=1 AND kind='regular'
                 AND suffix IN ('.cjs','.js','.jsx','.mjs','.ts','.tsx')
                 AND scan_error IS NULL AND hash_status IN ('hashed','reused')
                 AND content_sha256 IS NOT NULL AND path LIKE ?
               ORDER BY path""",
            (f"{prefix}%",),
        )
    ]
    config_paths = (f"{prefix}package.json", f"{prefix}tsconfig.json")
    configs = [
        dict(row)
        for row in connection.execute(
            """SELECT path,content_sha256,size_bytes FROM files
               WHERE path IN (?,?) ORDER BY path""",
            config_paths,
        )
    ]
    connection.close()
    output.mkdir(mode=0o700)
    index_path = output / "index.scip"
    index_path.write_bytes(payload)
    index_path.chmod(0o600)
    parsed = parse_scip_index(payload)
    occurrences = sum(len(item.occurrences) for item in parsed.documents)
    definitions = sum(
        bool(item.roles & 1) for doc in parsed.documents for item in doc.occurrences
    )
    manifest = seal_document(
        {
            "schema": SCIP_MANIFEST_SCHEMA,
            "status": "OBSERVED_LOCAL_PRECISION_INDEX",
            "authority_granted": False,
            "inventory": {"receipt_sha256": inventory.manifest["receipt_sha256"]},
            "sources": {
                "language": "typescript-javascript",
                "project_root": project_root,
                "files": sources,
                "configs": configs,
                "closure_sha256": sha256_bytes(
                    canonical_bytes({"sources": sources, "configs": configs})
                ),
                "source_text_embedded": False,
            },
            "tool": {
                "package": "@sourcegraph/scip-typescript",
                "version": "0.4.0",
                "npm_integrity": SCIP_TYPESCRIPT_NPM_INTEGRITY,
            },
            "index": {
                "path": "index.scip",
                "sha256": sha256_bytes(payload),
                "bytes": len(payload),
            },
            "counts": {
                "documents": len(parsed.documents),
                "occurrences": occurrences,
                "definitions": definitions,
                "references": occurrences - definitions,
                "symbols": sum(len(item.symbols) for item in parsed.documents),
                "external_symbols": len(parsed.external_symbols),
                "relationships": 0,
            },
        }
    )
    manifest_path = output / "manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest))
    manifest_path.chmod(0o600)
    return manifest_path


def test_scip_precision_is_optional_additive_and_queryable(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    paths = [
        row[0]
        for row in connection.execute(
            "SELECT path FROM files WHERE semantic_eligible=1 AND suffix='.py' ORDER BY path"
        )
    ]
    connection.close()
    manifest = _write_input(inventory_store, tmp_path / "scip", _index(paths))
    loaded = load_scip_index(manifest, inventory)
    assert len(loaded.index.documents) == 4
    assert loaded.manifest_record()["manifest_path"] == str(manifest.resolve())

    mapper = tmp_path / "mapper"
    run = refresh_mapper(inventory_store, mapper, scip_manifest=manifest)
    assert run.manifest["counts"]["scip_documents"] == 4
    assert run.manifest["counts"]["scip_occurrences"] == 2
    assert run.manifest["scip_input"]["authority_granted"] is False

    result = query_mapper(mapper, "add", maps=("symbols", "dependencies", "types"))
    precise = [item for item in result["results"] if item["kind"] == "SCIP_SYMBOL"]
    assert len(precise) == 1
    assert precise[0]["name"] == "add"
    assert precise[0]["truth_class"] == "OBSERVED"
    facts = precise[0]["facts"]["observations"]
    assert facts[0]["predicate"] == "SCIP_REFERENCE"
    assert facts[0]["source"]["path"] == "pkg/cli.py"
    assert facts[0]["source"]["line_start"] == 9

    dossier = build_dossier(
        mapper,
        "implementation",
        ("add",),
        overall_limit=20,
        fact_limit=10,
    )
    precise_dossier = [
        item for item in dossier["results"] if item["kind"] == "SCIP_SYMBOL"
    ]
    assert len(precise_dossier) == 1
    assert precise_dossier[0]["name"] == "add"
    assert set(precise_dossier[0]["map_ids"]) >= {"symbols", "dependencies"}

    local = query_mapper(mapper, "run", maps=("symbols",))
    local_scip = next(
        item
        for item in local["results"]
        if item["kind"] == "SCIP_SYMBOL" and item["name"] == "run"
    )
    assert local_scip["source"]["path"] == "pkg/cli.py"
    assert local_scip["attributes"]["definition_paths"] == ["pkg/cli.py"]

    context = build_context_projection(
        mapper,
        "implementation",
        ("run",),
        token_budget=512,
        include_semantic=False,
    )
    assert any(
        item["kind"] == "PYTHON_SYMBOL" and item["name"] == "run"
        for item in context["entries"]
    )
    assert not any(
        item["kind"] == "SCIP_SYMBOL"
        and item["attributes"]["definition_paths"] == ["pkg/cli.py"]
        and item["name"] == "run"
        for item in context["entries"]
    )
    assert context["omissions"]["redundant_precision_entity_ids"]
    assert context["ranking"]["algorithm"] == (
        "giga.personalized-file-rank.v3-precision-deduplicated-map-aware"
    )


def test_duplicate_scip_occurrences_are_coalesced_as_one_observed_fact(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    paths = [
        row[0]
        for row in connection.execute(
            "SELECT path FROM files WHERE semantic_eligible=1 AND suffix='.py' ORDER BY path"
        )
    ]
    connection.close()
    manifest = _write_input(
        inventory_store,
        tmp_path / "scip",
        _index(paths, duplicate_occurrence=True),
    )

    run = refresh_mapper(inventory_store, tmp_path / "mapper", scip_manifest=manifest)

    assert run.manifest["counts"]["scip_occurrences"] == 2
    assert run.manifest["counts"]["scip_duplicate_occurrences_coalesced"] == 1
    result = query_mapper(
        tmp_path / "mapper", "add", maps=("symbols", "dependencies", "types")
    )
    precise = [item for item in result["results"] if item["kind"] == "SCIP_SYMBOL"]
    assert len(precise) == 1
    assert len(precise[0]["facts"]["observations"]) == 1


def test_python_indexer_fatal_file_is_exactly_bound_and_marks_mapper_partial(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    connection.row_factory = __import__("sqlite3").Row
    sources = [
        dict(row)
        for row in connection.execute(
            """SELECT path,content_sha256,size_bytes FROM files
               WHERE semantic_eligible=1 AND kind='regular' AND suffix='.py'
                 AND scan_error IS NULL AND hash_status IN ('hashed','reused')
               ORDER BY path"""
        )
    ]
    connection.close()
    failed = sources[0]
    retained_paths = [item["path"] for item in sources[1:]]
    manifest_path = _write_input(
        inventory_store, tmp_path / "scip-partial", _index(retained_paths)
    )
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "OBSERVED_LOCAL_PRECISION_INDEX_PARTIAL"
    manifest["sources"]["excluded_files"] = [
        {
            **failed,
            "reason": "CURRENT_SOURCE_CHANGED_INDEXER_REFRESH_FAILED",
            "tool_error_sha256": "f" * 64,
        }
    ]
    manifest = seal_document(
        {key: value for key, value in manifest.items() if key != "receipt_sha256"}
    )
    manifest_path.write_bytes(canonical_bytes(manifest))

    loaded = load_scip_index(manifest_path, inventory)
    assert [item.relative_path for item in loaded.index.documents] == retained_paths
    mapper = refresh_mapper(
        inventory_store, tmp_path / "mapper-partial", scip_manifest=manifest_path
    )
    assert mapper.manifest["status"] == "PARTIAL"
    assert mapper.manifest["scip_input"]["excluded_files"] == [
        {
            **failed,
            "reason": "CURRENT_SOURCE_CHANGED_INDEXER_REFRESH_FAILED",
            "tool_error_sha256": "f" * 64,
        }
    ]


def test_failed_python_refresh_reuses_only_unchanged_previous_documents(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    paths = [
        row[0]
        for row in connection.execute(
            "SELECT path FROM files WHERE semantic_eligible=1 AND suffix='.py' ORDER BY path"
        )
    ]
    connection.close()
    previous_manifest = _write_input(
        inventory_store, tmp_path / "previous", _index(paths)
    )
    (repository / "pkg/cli.py").write_text("CHANGED = True\n", encoding="utf-8")
    refresh_navigation_inventory(repository, inventory_store)

    reused = _reuse_previous_python_index(
        inventory_store,
        tmp_path / "reused",
        previous_manifest,
        ScipMapError("SCIP Python compilation failed: fixture"),
    )

    assert reused.manifest["status"] == "OBSERVED_LOCAL_PRECISION_INDEX_PARTIAL"
    assert [item["path"] for item in reused.manifest["sources"]["excluded_files"]] == [
        "pkg/cli.py"
    ]
    assert "pkg/cli.py" not in {item.relative_path for item in reused.index.documents}
    assert reused.manifest["reuse"]["retained_documents"] == len(paths) - 1


def test_scip_parser_refuses_source_text_and_manifest_drift(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    paths = [
        row[0]
        for row in connection.execute(
            "SELECT path FROM files WHERE semantic_eligible=1 AND suffix='.py' ORDER BY path"
        )
    ]
    connection.close()
    with pytest.raises(ScipMapError, match="embeds source text"):
        parse_scip_index(_index(paths, embed_text=True))

    manifest_path = _write_input(inventory_store, tmp_path / "scip", _index(paths))
    manifest = json.loads(manifest_path.read_text())
    manifest["sources"]["files"][0]["content_sha256"] = "0" * 64
    manifest = seal_document(
        {key: value for key, value in manifest.items() if key != "receipt_sha256"}
    )
    manifest_path.write_bytes(canonical_bytes(manifest))
    with pytest.raises(ScipMapError, match="source closure mismatch"):
        load_scip_index(manifest_path, inventory)


def test_scip_manifest_refuses_unbound_python_repair_evidence(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    paths = [
        row[0]
        for row in connection.execute(
            "SELECT path FROM files WHERE semantic_eligible=1 AND suffix='.py' ORDER BY path"
        )
    ]
    connection.close()
    manifest_path = _write_input(inventory_store, tmp_path / "scip", _index(paths))
    manifest = json.loads(manifest_path.read_text())
    manifest["tool"]["package_tree_sha256"] = scip_map.SCIP_PYTHON_PACKAGE_TREE_SHA256
    manifest["tool"]["patch"] = {
        "id": scip_map.SCIP_PYTHON_PATCH_ID,
        "upstream_entrypoint_sha256": scip_map.SCIP_PYTHON_ENTRYPOINT_SHA256,
        "patched_entrypoint_sha256": (scip_map.SCIP_PYTHON_PATCHED_ENTRYPOINT_SHA256),
        "installed_package_unchanged": True,
    }
    admitted = seal_document(
        {key: value for key, value in manifest.items() if key != "receipt_sha256"}
    )
    manifest_path.write_bytes(canonical_bytes(admitted))
    load_scip_index(manifest_path, inventory)

    admitted["tool"]["patch"]["id"] = "unreviewed-repair"
    tampered = seal_document(
        {key: value for key, value in admitted.items() if key != "receipt_sha256"}
    )
    manifest_path.write_bytes(canonical_bytes(tampered))
    with pytest.raises(ScipMapError, match="repair evidence is invalid"):
        load_scip_index(manifest_path, inventory)


def test_scip_index_reuses_exact_python_closure_across_non_python_change(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    paths = [
        row[0]
        for row in connection.execute(
            "SELECT path FROM files WHERE semantic_eligible=1 AND suffix='.py' ORDER BY path"
        )
    ]
    connection.close()
    manifest = _write_input(inventory_store, tmp_path / "scip", _index(paths))
    exact = load_scip_index(manifest, inventory)
    assert exact.inventory_binding_status == "EXACT_INVENTORY_RECEIPT"

    (repository / "README.md").write_text("documentation only\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repository, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "documentation"],
        cwd=repository,
        check=True,
    )
    refresh_navigation_inventory(repository, inventory_store)
    advanced = current_navigation_run(inventory_store)
    reused = load_scip_index(manifest, advanced)
    assert (
        reused.inventory_binding_status
        == "CURRENT_SOURCE_CLOSURE_REUSED_AFTER_INVENTORY_ADVANCE"
    )
    assert (
        reused.current_inventory_receipt_sha256 == advanced.manifest["receipt_sha256"]
    )

    (repository / "pkg/cli.py").write_text(
        "def changed():\n    return 1\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "pkg/cli.py"], cwd=repository, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "python change"],
        cwd=repository,
        check=True,
    )
    refresh_navigation_inventory(repository, inventory_store)
    changed = current_navigation_run(inventory_store)
    with pytest.raises(ScipMapError, match="source closure mismatch"):
        load_scip_index(manifest, changed)


def test_typescript_scip_project_is_prefixed_additive_and_queryable(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)
    payload = _typescript_index(["src/core.ts", "src/main.ts"])
    manifest = _write_typescript_input(inventory_store, tmp_path / "scip-ts", payload)
    loaded = load_scip_index(manifest, current_navigation_run(inventory_store))
    assert [item.relative_path for item in loaded.index.documents] == [
        "web/src/core.ts",
        "web/src/main.ts",
    ]

    mapper = tmp_path / "mapper"
    run = refresh_mapper(inventory_store, mapper, scip_manifest=manifest)
    assert run.manifest["counts"]["scip_documents"] == 2
    assert run.manifest["scip_input"]["tool"]["package"] == (
        "@sourcegraph/scip-typescript"
    )
    result = query_mapper(mapper, "buildService", maps=("symbols",))
    precise = [item for item in result["results"] if item["kind"] == "SCIP_SYMBOL"]
    assert len(precise) == 1
    observations = precise[0]["facts"]["observations"]
    assert {item["predicate"] for item in observations} == {
        "SCIP_DEFINITION",
        "SCIP_REFERENCE",
    }
    assert {item["source"]["path"] for item in observations} == {
        "web/src/core.ts",
        "web/src/main.ts",
    }


def test_multiple_scip_indexes_federate_in_stable_order_without_overlap(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)
    inventory = current_navigation_run(inventory_store)
    connection = __import__("sqlite3").connect(
        inventory.run_directory / "inventory.sqlite3"
    )
    python_paths = [
        row[0]
        for row in connection.execute(
            "SELECT path FROM files WHERE semantic_eligible=1 AND suffix='.py' ORDER BY path"
        )
    ]
    connection.close()
    python_manifest = _write_input(
        inventory_store, tmp_path / "scip-python", _index(python_paths)
    )
    typescript_manifest = _write_typescript_input(
        inventory_store,
        tmp_path / "scip-typescript",
        _typescript_index(["src/core.ts", "src/main.ts"]),
    )
    typescript_manifest_two = _write_typescript_input(
        inventory_store,
        tmp_path / "scip-typescript-two",
        _typescript_index(["src/core.ts", "src/main.ts"], package="fixture-two"),
        project_root="web2",
    )

    mapper = tmp_path / "mapper"
    run = refresh_mapper(
        inventory_store,
        mapper,
        scip_manifests=(typescript_manifest, python_manifest, typescript_manifest_two),
    )
    assert run.manifest["scip_input"] is None
    assert len(run.manifest["scip_inputs"]) == 3
    assert run.manifest["counts"]["scip_documents"] == len(python_paths) + 4
    assert {item["tool"]["package"] for item in run.manifest["scip_inputs"]} == {
        "@sourcegraph/scip-python",
        "@sourcegraph/scip-typescript",
    }
    assert query_mapper(mapper, "buildService", maps=("symbols",))["result_count"]
    assert query_mapper(mapper, "add", maps=("symbols",))["result_count"]

    reused = refresh_mapper(
        inventory_store,
        mapper,
        scip_manifests=(
            typescript_manifest_two,
            python_manifest,
            typescript_manifest,
        ),
    )
    assert reused.manifest["run_id"] == run.manifest["run_id"]
    with pytest.raises(MapperError, match="duplicate manifest paths"):
        refresh_mapper(
            inventory_store,
            tmp_path / "duplicate",
            scip_manifest=python_manifest,
            scip_manifests=(python_manifest,),
        )
    overlapping_manifest = _write_typescript_input(
        inventory_store,
        tmp_path / "scip-typescript-overlap",
        _typescript_index(["src/core.ts", "src/main.ts"], package="overlap"),
    )
    with pytest.raises(MapperError, match="document closures overlap"):
        refresh_mapper(
            inventory_store,
            tmp_path / "overlap",
            scip_manifests=(typescript_manifest, overlapping_manifest),
        )


def test_scip_project_discovery_is_closed_stable_and_reports_incomplete_configs(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "unsupported/src").mkdir(parents=True)
    (repository / "unsupported/package.json").write_text(
        '{"name":"unsupported","private":true}\n', encoding="utf-8"
    )
    (repository / "unsupported/src/main.ts").write_text(
        "export const value = 1;\n", encoding="utf-8"
    )
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)

    first = discover_scip_projects(inventory_store)
    second = discover_scip_projects(inventory_store)
    assert first["schema"] == SCIP_PROJECT_CATALOG_SCHEMA
    assert first["authority_granted"] is False
    assert first["projects"] == second["projects"]
    assert first["counts"] == {
        "candidates": 4,
        "supported": 3,
        "unsupported": 1,
        "python": 1,
        "typescript_javascript": 3,
    }
    projects = {item["project_id"]: item for item in first["projects"]}
    assert projects["python:repository"]["eligible_for_federation"] is True
    assert projects["typescript:web"]["disposition"] == "SUPPORTED"
    assert projects["typescript:web2"]["disposition"] == "SUPPORTED"
    assert projects["typescript:unsupported"] == {
        "project_id": "typescript:unsupported",
        "language": "typescript-javascript",
        "project_root": "unsupported",
        "disposition": "UNSUPPORTED_INCOMPLETE_CONFIG",
        "eligible_for_federation": False,
        "source_closure_sha256": None,
        "source_count": 0,
        "config_count": 1,
        "missing_configs": ["tsconfig.json"],
        "overlaps": [],
    }


def test_scip_project_discovery_refuses_overlapping_typescript_closures(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "web/nested").mkdir()
    (repository / "web/nested/package.json").write_text(
        '{"name":"nested","private":true}\n', encoding="utf-8"
    )
    (repository / "web/nested/tsconfig.json").write_text(
        '{"include":["*.ts"]}\n', encoding="utf-8"
    )
    (repository / "web/nested/child.ts").write_text(
        "export const nested = 1;\n", encoding="utf-8"
    )
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)

    catalog = discover_scip_projects(inventory_store)
    projects = {item["project_id"]: item for item in catalog["projects"]}
    assert projects["typescript:web"]["eligible_for_federation"] is False
    assert projects["typescript:web"]["overlaps"] == ["web/nested"]
    assert projects["typescript:web/nested"]["eligible_for_federation"] is False
    assert projects["typescript:web/nested"]["overlaps"] == ["web"]
    assert catalog["counts"]["unsupported"] == 2


def test_atomic_scip_refresh_preserves_previous_generation_on_failure(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory_store = tmp_path / "inventory"
    refresh_navigation_inventory(repository, inventory_store)

    def fake_build(
        inventory_store: Path,
        output: Path,
        **_: object,
    ) -> SimpleNamespace:
        output.mkdir(mode=0o700)
        index = b"exact-index"
        (output / "index.scip").write_bytes(index)
        manifest = seal_document(
            {
                "schema": SCIP_MANIFEST_SCHEMA,
                "status": "OBSERVED_LOCAL_PRECISION_INDEX",
                "authority_granted": False,
                "index": {
                    "path": "index.scip",
                    "sha256": sha256_bytes(index),
                    "bytes": len(index),
                },
                "counts": {"documents": 1, "occurrences": 2},
            }
        )
        manifest_path = output / "manifest.json"
        manifest_path.write_bytes(canonical_bytes(manifest))
        return SimpleNamespace(manifest_path=manifest_path, manifest=manifest)

    monkeypatch.setattr(
        "modules.operations.archaeology.scip_map.build_scip_index", fake_build
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.scip_map.build_typescript_scip_index",
        fake_build,
    )
    store = tmp_path / "store"
    first = refresh_scip_store(
        inventory_store,
        store,
        node=tmp_path / "node",
        python_indexer_entrypoint=tmp_path / "python-indexer",
        python_package_json=tmp_path / "python-package.json",
        typescript_indexer_entrypoint=tmp_path / "typescript-indexer",
        typescript_package_json=tmp_path / "typescript-package.json",
    )
    assert first.catalog["counts"] == {
        "indexes": 3,
        "documents": 3,
        "occurrences": 6,
        "bytes": 33,
    }
    assert len(first.manifest_paths) == 3
    pointer_before = (store / "CURRENT.json").read_bytes()

    def fail_build(*_: object, **__: object) -> None:
        raise ScipMapError("injected build failure")

    monkeypatch.setattr(
        "modules.operations.archaeology.scip_map.build_scip_index", fail_build
    )
    with pytest.raises(ScipMapError, match="injected build failure"):
        refresh_scip_store(
            inventory_store,
            store,
            node=tmp_path / "node",
            python_indexer_entrypoint=tmp_path / "python-indexer",
            python_package_json=tmp_path / "python-package.json",
            typescript_indexer_entrypoint=tmp_path / "typescript-indexer",
            typescript_package_json=tmp_path / "typescript-package.json",
        )
    assert (store / "CURRENT.json").read_bytes() == pointer_before
    assert current_scip_store(store).catalog["run_id"] == first.catalog["run_id"]
    assert not list((store / "runs").glob(".staging-*"))
