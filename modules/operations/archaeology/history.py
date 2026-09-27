"""Slice 4: read-only Git and cross-repository variant evidence."""

from __future__ import annotations

import ast
import json
import re
import stat
import subprocess
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .counterevidence import COUNTEREVIDENCE_SCHEMA
from .evidence import (
    EvidenceError,
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
    write_atomic,
)
from .hypotheses import HYPOTHESES_SCHEMA
from .inventory import DEFAULT_EXCLUDED_PREFIXES, INVENTORY_SCHEMA
from .os_support import git_environment, git_executable


HISTORY_SCHEMA = "giga.archaeologist.history.v1"
OID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
MAX_HISTORY_COMMITS = 50
MAX_LINEAGE_COMMITS = 2048
MAX_HISTORICAL_PYTHON_BLOB_BYTES = 1024 * 1024
MAX_HISTORICAL_PYTHON_DECLARATIONS = 10_000


class HistoryError(ValueError):
    """Historical comparison cannot be completed without weakening evidence."""


def _load(path: Path, schema: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryError("input is not strict UTF-8 JSON") from exc
    try:
        validate_self_hash(value)
    except EvidenceError as exc:
        raise HistoryError(str(exc)) from exc
    if value.get("schema") != schema:
        raise HistoryError(f"unsupported input schema: {value.get('schema')!r}")
    if (
        value.get("authority_granted") is not False
        or value.get("cleanup_permitted") is not False
    ):
        raise HistoryError("input authority boundary is not closed")
    return value, raw


def _git(
    root: Path, arguments: Sequence[str], *, ceiling: int = 16 * 1024 * 1024
) -> bytes:
    executable = git_executable()
    if executable is None:
        raise HistoryError("Git executable is unavailable")
    result = subprocess.run(
        [executable, *arguments],
        cwd=root,
        env=git_environment(executable),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if len(result.stdout) > ceiling or len(result.stderr) > ceiling:
        raise HistoryError("Git output exceeded evidence ceiling")
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise HistoryError(f"Git read failed ({' '.join(arguments)}): {detail}")
    return result.stdout


def _text(root: Path, arguments: Sequence[str]) -> str:
    try:
        return _git(root, arguments).decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise HistoryError("Git returned non-UTF-8 identity data") from exc


def _repository_snapshot(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    metadata = root.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise HistoryError("comparison repository must be a real directory")
    status = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    refs = _git(
        root,
        [
            "for-each-ref",
            "--sort=refname",
            "--format=%(refname)%00%(objectname)%00%(objecttype)",
        ],
    )
    return {
        "root": str(root),
        "head": _text(root, ["rev-parse", "HEAD"]).strip(),
        "tree": _text(root, ["rev-parse", "HEAD^{tree}"]).strip(),
        "branch": _text(root, ["branch", "--show-current"]).strip(),
        "identity": {
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode),
            "uid": metadata.st_uid,
        },
        "status": {"sha256": sha256_bytes(status), "bytes": len(status)},
        "refs": {"sha256": sha256_bytes(refs), "bytes": len(refs)},
    }


def _excluded(path: str) -> bool:
    value = path + "/"
    return any(
        value.startswith(prefix) or path == prefix.rstrip("/")
        for prefix in DEFAULT_EXCLUDED_PREFIXES
    )


def _head_tree(root: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    raw = _git(root, ["ls-tree", "-r", "-z", "HEAD"])
    by_path: dict[str, str] = {}
    by_basename: dict[str, list[str]] = defaultdict(list)
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            metadata, path_raw = item.split(b"\t", 1)
            _mode, kind, oid = metadata.decode("ascii").split(" ")
            path = path_raw.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError) as exc:
            raise HistoryError("malformed Git tree record") from exc
        if kind != "blob" or _excluded(path):
            continue
        by_path[path] = oid
        by_basename[PurePosixPath(path).name].append(path)
    return by_path, {name: sorted(paths) for name, paths in by_basename.items()}


def _versions(root: Path, path: str) -> list[dict[str, str]]:
    commits: list[str] = []
    for arguments in (
        ["log", "--format=%H", "--follow", "--", path],
        ["log", "--all", "--format=%H", "--", path],
    ):
        for commit in _text(root, arguments).splitlines():
            if OID.fullmatch(commit) and commit not in commits:
                commits.append(commit)
            if len(commits) >= MAX_HISTORY_COMMITS:
                break
    versions: list[dict[str, str]] = []
    seen_blobs: set[str] = set()
    executable = git_executable()
    if executable is None:
        raise HistoryError("Git executable is unavailable")
    for commit in commits:
        result = subprocess.run(
            [executable, "rev-parse", f"{commit}:{path}"],
            cwd=root,
            env=git_environment(executable),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
        oid = result.stdout.decode("ascii", "ignore").strip()
        if result.returncode == 0 and OID.fullmatch(oid) and oid not in seen_blobs:
            seen_blobs.add(oid)
            versions.append({"commit": commit, "blob_oid": oid, "path": path})
    return versions


def _git_path(raw: bytes) -> str:
    try:
        path = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise HistoryError("Git path-change data is not strict UTF-8") from exc
    value = PurePosixPath(path)
    if (
        value.is_absolute()
        or not value.parts
        or any(part in {"", ".", ".."} for part in value.parts)
    ):
        raise HistoryError("Git path-change data is not a safe relative path")
    return path


def _path_changes(raw: bytes) -> list[dict[str, str]]:
    values = [item for item in raw.split(b"\0") if item]
    changes: list[dict[str, str]] = []
    index = 0
    while index < len(values):
        try:
            status = values[index].decode("ascii", "strict")
        except UnicodeDecodeError as exc:
            raise HistoryError("Git path status is not ASCII") from exc
        index += 1
        if status in {"A", "M", "D", "T"}:
            if index >= len(values):
                raise HistoryError("Git returned truncated path-change data")
            changes.append({"status": status, "path": _git_path(values[index])})
            index += 1
            continue
        if re.fullmatch(r"R(?:100|0[0-9]{2})", status):
            if index + 1 >= len(values):
                raise HistoryError("Git returned truncated rename data")
            changes.append(
                {
                    "status": status,
                    "old_path": _git_path(values[index]),
                    "new_path": _git_path(values[index + 1]),
                }
            )
            index += 2
            continue
        raise HistoryError(f"unsupported Git path status: {status!r}")
    return changes


class _HistoricalDeclarationVisitor(ast.NodeVisitor):
    """Extract declaration locations without retaining historical source text."""

    def __init__(self) -> None:
        self.scopes: list[tuple[str, str]] = []
        self.declarations: list[dict[str, Any]] = []

    def _qualified(self, name: str) -> str:
        return ".".join([*(scope[0] for scope in self.scopes), name])

    def _record(self, node: ast.AST, name: str, kind: str) -> None:
        if len(self.declarations) >= MAX_HISTORICAL_PYTHON_DECLARATIONS:
            raise HistoryError("historical Python declaration ceiling exceeded")
        self.declarations.append(
            {
                "kind": kind,
                "name": name,
                "qualified_name": self._qualified(name),
                "span": {
                    "line_start": int(getattr(node, "lineno", 0)),
                    "column_start": int(getattr(node, "col_offset", 0)),
                    "line_end": int(
                        getattr(node, "end_lineno", getattr(node, "lineno", 0))
                    ),
                    "column_end": int(
                        getattr(
                            node,
                            "end_col_offset",
                            getattr(node, "col_offset", 0),
                        )
                    ),
                },
            }
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._record(node, node.name, "CLASS")
        self.scopes.append((node.name, "CLASS"))
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    def _function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, asynchronous: bool
    ) -> None:
        method = bool(self.scopes and self.scopes[-1][1] == "CLASS")
        kind = "METHOD" if method else "FUNCTION"
        if asynchronous:
            kind = "ASYNC_METHOD" if method else "ASYNC_FUNCTION"
        self._record(node, node.name, kind)
        self.scopes.append((node.name, "FUNCTION"))
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node, asynchronous=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node, asynchronous=True)


def _historical_python_declarations(
    root: Path, path: str, blob_oid: str
) -> dict[str, Any]:
    if PurePosixPath(path).suffix.casefold() != ".py":
        return {"disposition": "NOT_APPLICABLE", "declarations": []}
    object_type = _text(root, ["cat-file", "-t", blob_oid]).strip()
    size_raw = _text(root, ["cat-file", "-s", blob_oid]).strip()
    if object_type != "blob" or not size_raw.isdecimal():
        raise HistoryError("historical Python object identity is malformed")
    size = int(size_raw)
    if size > MAX_HISTORICAL_PYTHON_BLOB_BYTES:
        return {
            "disposition": "SKIPPED_SIZE_CEILING",
            "blob_bytes": size,
            "declarations": [],
        }
    raw = _git(root, ["cat-file", "blob", blob_oid], ceiling=size + 1)
    if len(raw) != size:
        raise HistoryError("historical Python blob size changed during read")
    try:
        text = raw.decode("utf-8", "strict")
        tree = ast.parse(text, filename=path, type_comments=True)
        visitor = _HistoricalDeclarationVisitor()
        visitor.visit(tree)
    except UnicodeDecodeError:
        return {
            "disposition": "SKIPPED_NON_UTF8",
            "blob_bytes": size,
            "declarations": [],
        }
    except HistoryError:
        return {
            "disposition": "SKIPPED_DECLARATION_CEILING",
            "blob_bytes": size,
            "declarations": [],
        }
    except (MemoryError, OverflowError, RecursionError, SyntaxError, ValueError):
        return {
            "disposition": "SKIPPED_PARSE_FAILURE",
            "blob_bytes": size,
            "declarations": [],
        }
    return {
        "disposition": "PARSED_DECLARATIONS_ONLY",
        "blob_bytes": size,
        "declarations": sorted(
            visitor.declarations,
            key=lambda item: (
                item["span"]["line_start"],
                item["span"]["column_start"],
                item["qualified_name"],
                item["kind"],
            ),
        ),
    }


def collect_recent_lineage(
    root: Path,
    expected_head: str,
    admitted_paths: Sequence[str],
    *,
    current_paths: Sequence[str] | None = None,
    current_blob_oids: Mapping[str, str] | None = None,
    max_commits: int = MAX_LINEAGE_COMMITS,
) -> dict[str, Any]:
    """Collect capped exact Git-object lineage for current admitted paths.

    The result covers the complete HEAD ancestry when it fits inside the explicit
    safety cap. It follows rename predecessors only when Git's similarity detector
    reports them. Rename status is observed evidence rather than semantic identity;
    symbol evolution and merge-combined path changes remain explicit coverage limits.
    """

    if max_commits <= 0 or max_commits > MAX_LINEAGE_COMMITS:
        raise HistoryError("history commit bound is outside the supported range")
    root = root.resolve(strict=True)
    admitted = set(admitted_paths)
    current = set(current_paths if current_paths is not None else admitted_paths)
    if not admitted <= current:
        raise HistoryError("admitted lineage paths must be current paths")
    current_blobs = dict(current_blob_oids or {})
    if not set(current_blobs) <= current:
        raise HistoryError("current blob bindings must refer to current paths")
    if any(not OID.fullmatch(value) for value in current_blobs.values()):
        raise HistoryError("current blob binding is not an exact Git object ID")
    before = _repository_snapshot(root)
    if before["head"] != expected_head:
        raise HistoryError("inventory HEAD no longer matches the lineage repository")
    ancestry_count_raw = _text(root, ["rev-list", "--count", expected_head]).strip()
    if not ancestry_count_raw.isdecimal():
        raise HistoryError("Git returned a malformed HEAD ancestry count")
    ancestry_count = int(ancestry_count_raw)
    commits = [
        item
        for item in _text(
            root,
            ["rev-list", "--topo-order", f"--max-count={max_commits}", expected_head],
        ).splitlines()
        if OID.fullmatch(item)
    ]
    records: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    renames: list[dict[str, Any]] = []
    deleted_paths: list[dict[str, Any]] = []
    deleted_python_declarations: list[dict[str, Any]] = []
    deleted_paths_skipped_merge = 0
    renames_skipped_sensitive = 0
    historical_python_blobs_parsed = 0
    historical_python_blobs_skipped = 0
    historical_declaration_cache: dict[tuple[str, str], dict[str, Any]] = {}
    path_to_current = {path: path for path in admitted}
    for ordinal, commit in enumerate(commits):
        fields = (
            _git(
                root,
                ["show", "-s", "--format=%H%x00%P%x00%aI%x00%cI%x00%s", commit],
            )
            .rstrip(b"\n")
            .split(b"\0")
        )
        if len(fields) != 5:
            raise HistoryError("Git returned malformed commit identity data")
        try:
            decoded = [item.decode("utf-8", "strict") for item in fields]
        except UnicodeDecodeError as exc:
            raise HistoryError("Git commit identity is not strict UTF-8") from exc
        object_id, parents, authored_at, committed_at, subject = decoded
        if object_id != commit or any(
            not OID.fullmatch(parent) for parent in parents.split() if parent
        ):
            raise HistoryError("Git commit identity is malformed")
        records.append(
            {
                "commit": commit,
                "parents": parents.split(),
                "authored_at": authored_at,
                "committed_at": committed_at,
                "subject": subject,
                "ordinal": ordinal,
            }
        )
        raw_changes = _path_changes(
            _git(
                root,
                [
                    "diff-tree",
                    "--root",
                    "--no-commit-id",
                    "--name-status",
                    "-z",
                    "-r",
                    "--find-renames=50%",
                    commit,
                ],
            )
        )
        for change in raw_changes:
            status = change["status"]
            if status.startswith("R"):
                old_path = change["old_path"]
                new_path = change["new_path"]
                current_path = path_to_current.get(new_path)
                if current_path is None:
                    continue
                if _excluded(old_path) or _excluded(new_path):
                    renames_skipped_sensitive += 1
                    continue
                path_to_current[old_path] = current_path
                parent_ids = parents.split()
                old_blob_oid = None
                new_blob_oid = None
                current_blob_oid = current_blobs.get(current_path)
                exact_current_blob_continuity = False
                if len(parent_ids) == 1 and current_blob_oid is not None:
                    old_blob_oid = _text(
                        root, ["rev-parse", f"{parent_ids[0]}:{old_path}"]
                    ).strip()
                    new_blob_oid = _text(
                        root, ["rev-parse", f"{commit}:{new_path}"]
                    ).strip()
                    working_blob_oid = _text(
                        root, ["hash-object", "--no-filters", "--", current_path]
                    ).strip()
                    if not all(
                        OID.fullmatch(value)
                        for value in (old_blob_oid, new_blob_oid, working_blob_oid)
                    ):
                        raise HistoryError("rename blob continuity is malformed")
                    if working_blob_oid != current_blob_oid:
                        raise HistoryError(
                            "current Python source no longer matches its Git blob"
                        )
                    exact_current_blob_continuity = (
                        status == "R100"
                        and old_blob_oid == new_blob_oid == current_blob_oid
                    )
                renames.append(
                    {
                        "commit": commit,
                        "current_blob_oid": current_blob_oid,
                        "current_path": current_path,
                        "exact_current_blob_continuity": (
                            exact_current_blob_continuity
                        ),
                        "new_path": new_path,
                        "new_blob_oid": new_blob_oid,
                        "old_path": old_path,
                        "old_blob_oid": old_blob_oid,
                        "ordinal": len(renames),
                        "similarity_percent": int(status[1:]),
                        "status": status,
                    }
                )
                changes.append(
                    {
                        "commit": commit,
                        "current_path": current_path,
                        "path": new_path,
                        "status": status,
                        "ordinal": len(changes),
                    }
                )
                continue
            path = change["path"]
            current_path = path_to_current.get(path)
            if current_path is not None:
                changes.append(
                    {
                        "commit": commit,
                        "current_path": current_path,
                        "path": path,
                        "status": status,
                        "ordinal": len(changes),
                    }
                )
            elif status == "D" and path not in current and not _excluded(path):
                parent_ids = parents.split()
                if len(parent_ids) != 1:
                    deleted_paths_skipped_merge += 1
                    continue
                blob_oid = _text(root, ["rev-parse", f"{parent_ids[0]}:{path}"]).strip()
                if not OID.fullmatch(blob_oid):
                    raise HistoryError(
                        "deleted path did not resolve to an exact Git blob"
                    )
                declaration_result = historical_declaration_cache.get((path, blob_oid))
                if declaration_result is None:
                    declaration_result = _historical_python_declarations(
                        root, path, blob_oid
                    )
                    historical_declaration_cache[(path, blob_oid)] = declaration_result
                    if declaration_result["disposition"] == "PARSED_DECLARATIONS_ONLY":
                        historical_python_blobs_parsed += 1
                    elif declaration_result["disposition"] != "NOT_APPLICABLE":
                        historical_python_blobs_skipped += 1
                deleted_paths.append(
                    {
                        "commit": commit,
                        "declaration_disposition": declaration_result["disposition"],
                        "last_blob_oid": blob_oid,
                        "ordinal": len(deleted_paths),
                        "parent": parent_ids[0],
                        "path": path,
                        "status": "D",
                    }
                )
                for declaration in declaration_result["declarations"]:
                    deleted_python_declarations.append(
                        {
                            "blob_bytes": declaration_result["blob_bytes"],
                            "commit": commit,
                            "declaration": declaration,
                            "last_blob_oid": blob_oid,
                            "parent": parent_ids[0],
                            "path": path,
                        }
                    )
    after = _repository_snapshot(root)
    if before != after:
        raise HistoryError(
            "repository identity, refs or status changed during lineage scan"
        )
    return {
        "head": expected_head,
        "max_commits": max_commits,
        "commits": records,
        "changes": changes,
        "renames": renames,
        "deleted_paths": deleted_paths,
        "deleted_python_declarations": deleted_python_declarations,
        "coverage": {
            "current_admitted_paths_only": True,
            "current_path_exclusion_count": len(current),
            "deleted_noncurrent_paths": "OBSERVED_SINGLE_PARENT_TOMBSTONES",
            "deleted_paths_skipped_merge": deleted_paths_skipped_merge,
            "head_ancestry_commits": ancestry_count,
            "head_ancestry_complete": ancestry_count <= max_commits,
            "history_commit_cap": max_commits,
            "historical_deleted_python_source_content_loaded": (
                "BOUNDED_IN_MEMORY_AST_DECLARATION_PARSE_ONLY"
            ),
            "historical_python_blob_byte_ceiling": (MAX_HISTORICAL_PYTHON_BLOB_BYTES),
            "historical_python_blobs_parsed": historical_python_blobs_parsed,
            "historical_python_blobs_skipped": historical_python_blobs_skipped,
            "historical_python_declarations": len(deleted_python_declarations),
            "historical_rename_source_content_loaded": False,
            "historical_source_content_persisted": False,
            "historical_symbol_continuity": (
                "CURRENT_DECLARATIONS_OVER_EXACT_UNCHANGED_BLOB_RENAMES_ONLY"
            ),
            "merge_combined_changes": "PARTIAL",
            "rename_detection": "OBSERVED_GIT_SIMILARITY_M50",
            "renames_skipped_sensitive": renames_skipped_sensitive,
            "symbol_lineage": "EXACT_UNCHANGED_BLOB_RENAMES_ONLY",
        },
        "repository": after,
    }


def build_history(
    inventory_path: Path,
    hypotheses_path: Path,
    counterevidence_path: Path,
    comparison_repository: Path,
) -> dict[str, Any]:
    inventory, inventory_raw = _load(inventory_path, INVENTORY_SCHEMA)
    hypotheses, hypotheses_raw = _load(hypotheses_path, HYPOTHESES_SCHEMA)
    counterevidence, counterevidence_raw = _load(
        counterevidence_path, COUNTEREVIDENCE_SCHEMA
    )
    if hypotheses["inventory"]["receipt_sha256"] != inventory["receipt_sha256"]:
        raise HistoryError("hypotheses do not bind the supplied inventory")
    if counterevidence["inventory"]["receipt_sha256"] != inventory["receipt_sha256"]:
        raise HistoryError("counterevidence inventory binding mismatch")
    if counterevidence["hypotheses"]["receipt_sha256"] != hypotheses["receipt_sha256"]:
        raise HistoryError("counterevidence hypothesis binding mismatch")
    root = Path(inventory["repository"]["root"]).resolve(strict=True)
    comparison = comparison_repository.resolve(strict=True)
    primary_before = _repository_snapshot(root)
    comparison_before = _repository_snapshot(comparison)
    secondary_paths, secondary_names = _head_tree(comparison)
    current_records = {item["path"]: item for item in inventory["files"]}
    paths = sorted({path for item in hypotheses["findings"] for path in item["paths"]})
    path_evidence: dict[str, dict[str, Any]] = {}
    for path in paths:
        current = current_records.get(path)
        if current is None:
            raise HistoryError(f"hypothesis path is absent from inventory: {path}")
        versions = _versions(root, path)
        matches = []
        candidate_paths = set(secondary_names.get(PurePosixPath(path).name, []))
        if path in secondary_paths:
            candidate_paths.add(path)
        for secondary_path in sorted(candidate_paths):
            secondary_oid = secondary_paths[secondary_path]
            relation = (
                "EXACT_GIT_BLOB"
                if secondary_oid == current.get("git_blob_oid")
                else "RELATED_BASENAME_DIFFERENT_BLOB"
            )
            matches.append(
                {
                    "path": secondary_path,
                    "blob_oid": secondary_oid,
                    "relation": relation,
                }
            )
        additional = len({item["blob_oid"] for item in versions}) > 1 or bool(matches)
        path_evidence[path] = {
            "path": path,
            "current_git_blob_oid": current.get("git_blob_oid"),
            "historical_versions": versions,
            "comparison_matches": matches,
            "state": "RELATED_VARIANT_OBSERVED"
            if additional
            else "NO_ADDITIONAL_VARIANT_OBSERVED",
            "authority_granted": False,
            "cleanup_permitted": False,
        }
    records = []
    for hypothesis in hypotheses["findings"]:
        evidence = [path_evidence[path] for path in hypothesis["paths"]]
        observed = any(item["state"] == "RELATED_VARIANT_OBSERVED" for item in evidence)
        records.append(
            {
                "hypothesis_id": hypothesis["id"],
                "hypothesis_state": "OBSERVED",
                "historical_state": "RELATED_VARIANT_OBSERVED"
                if observed
                else "UNKNOWN",
                "paths": evidence,
                "authority_granted": False,
                "cleanup_permitted": False,
            }
        )
    primary_after = _repository_snapshot(root)
    comparison_after = _repository_snapshot(comparison)
    if primary_before != primary_after or comparison_before != comparison_after:
        raise HistoryError(
            "repository identity, refs or status changed during comparison"
        )
    related = sum(
        item["historical_state"] == "RELATED_VARIANT_OBSERVED" for item in records
    )
    return seal_document(
        {
            "schema": HISTORY_SCHEMA,
            "authority": "read-only-historical-evidence",
            "authority_granted": False,
            "cleanup_permitted": False,
            "inputs": {
                "inventory": {
                    "file_sha256": sha256_bytes(inventory_raw),
                    "receipt_sha256": inventory["receipt_sha256"],
                },
                "hypotheses": {
                    "file_sha256": sha256_bytes(hypotheses_raw),
                    "receipt_sha256": hypotheses["receipt_sha256"],
                },
                "counterevidence": {
                    "file_sha256": sha256_bytes(counterevidence_raw),
                    "receipt_sha256": counterevidence["receipt_sha256"],
                },
            },
            "repositories": {"primary": primary_after, "comparison": comparison_after},
            "path_evidence": [path_evidence[path] for path in paths],
            "records": sorted(records, key=lambda item: item["hypothesis_id"]),
            "summary": {
                "hypotheses": len(records),
                "unique_paths": len(paths),
                "related_variant_observed": related,
                "unknown": len(records) - related,
                "comparison_tree_files": len(secondary_paths),
            },
        }
    )


def render_history_report(payload: Mapping[str, Any]) -> str:
    summary = payload["summary"]
    return "\n".join(
        [
            "# GIGA Archaeology historical and cross-repository variants",
            "",
            f"- Hypotheses inspected: {summary['hypotheses']}",
            f"- Unique source paths: {summary['unique_paths']}",
            f"- Related variant observed: {summary['related_variant_observed']}",
            f"- No related variant established: {summary['unknown']} (`UNKNOWN`)",
            f"- Comparison-tree files: {summary['comparison_tree_files']}",
            f"- Receipt SHA-256: `{payload['receipt_sha256']}`",
            "",
            "A historical or parallel variant is preservation evidence, not proof that either copy is obsolete.",
            "No match is `UNKNOWN`, not proof that no variant exists.",
            "",
        ]
    )


def write_history(
    inventory_path: Path,
    hypotheses_path: Path,
    counterevidence_path: Path,
    comparison_repository: Path,
    output: Path,
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists() or output.is_symlink():
        raise HistoryError("history output directory must not already exist")
    payload = build_history(
        inventory_path, hypotheses_path, counterevidence_path, comparison_repository
    )
    output.mkdir(parents=True, mode=0o700)
    try:
        write_atomic(output / "history.json", canonical_bytes(payload))
        write_atomic(
            output / "HISTORY_REPORT.md", render_history_report(payload).encode("utf-8")
        )
    except EvidenceError as exc:
        raise HistoryError(str(exc)) from exc
    return payload
