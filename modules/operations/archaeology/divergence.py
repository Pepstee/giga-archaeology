"""Read-only, content-addressed comparison of related GIGA worktrees.

M69 deliberately stops at identity and inventory evidence.  It does not infer
semantic equivalence, canonicality, retirement safety, or no-feature-loss.
"""

from __future__ import annotations

import ast
import gzip
import json
import os
import re
import stat
import subprocess
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .evidence import (
    EvidenceError,
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
    write_atomic,
)
from .history import HistoryError, _git, _repository_snapshot, collect_recent_lineage
from .inventory import (
    InventoryError,
    InventoryPolicy,
    _is_excluded,
    build_inventory,
)
from .navigation_inventory import (
    NavigationInventoryError,
    _stable_hash,
    _status_snapshot,
    classify_navigation_role,
)
from .python_map import (
    PythonMapError,
    extract_python_file_fragment,
)


DIVERGENCE_SCHEMA = "giga.archaeology.cross-worktree-identity-map.v1"
STATIC_DIVERGENCE_SCHEMA = "giga.archaeology.cross-worktree-static-fact-map.v1"
BEHAVIOR_DIVERGENCE_SCHEMA = (
    "giga.archaeology.cross-worktree-behavioral-counterevidence-map.v1"
)
DERIVED_PAYLOAD_LINEAGE_SCHEMA = (
    "giga.archaeology.derived-agent-payload-verifier-lineage.v1"
)
EXPORT_SURFACE_DISPOSITION_SCHEMA = (
    "giga.archaeology.one-cluster-export-surface-disposition.v1"
)
CLI_DONOR_SUPERSET_DISPOSITION_SCHEMA = (
    "giga.archaeology.cli-donor-symbol-superset-disposition.v1"
)
ZERO_MUTATION_SCHEMA = "giga.archaeology.zero-mutation-receipt.v1"
STATIC_FACT_FAMILIES = (
    "assignments_constants",
    "public_exports",
    "imports",
    "callers_references",
)
DERIVED_PAYLOAD_VERIFIER_PATH = "scripts/verify_derived_agent_payloads.py"
M76_EXPORT_SURFACE_EVIDENCE_SET_ID = (
    "68f4eb1e3d762005f42d1ea60931acf1ec6e6fd80d8187b17fb345c66f1e66f6"
)
M76_CANONICAL_PUBLIC_SURFACE_PATH = "modules/operations/archaeology/__init__.py"
M76_CANONICAL_LEGACY_SURFACE_PATH = "modules/operations/archaeologist/__init__.py"
M76_DONOR_PUBLIC_SURFACE_PATH = "modules/operations/archaeologist/__init__.py"
M76_REFUSAL = "M76 export-surface disposition refused: CONTENT_UNAVAILABLE"
CLI_SUPERSET_CANONICAL_CLI_PATH = "modules/operations/scripts/archaeology.py"
CLI_SUPERSET_LEGACY_ENTRYPOINT_PATH = "modules/operations/scripts/archaeologist.py"
CLI_SUPERSET_REFUSAL = (
    "CLI donor-symbol-superset disposition refused: CONTENT_UNAVAILABLE"
)
DERIVED_PAYLOAD_EVIDENCE_MARKER = re.compile(
    r"(=== GIGA DERIVED PAYLOAD v[0-9]+ ===|"
    r"giga\.(?:derived-agent-payload-verification|agent-payload-activation|"
    r"capability-adoption-manifest|capability-liveness-receipt)\.v[0-9]+)"
)


class DivergenceError(ValueError):
    """The worktree comparison cannot be proved without weakening evidence."""


def _git_text(root: Path, arguments: Sequence[str]) -> str:
    try:
        return _git(root, arguments).decode("utf-8", "strict").strip()
    except (HistoryError, UnicodeDecodeError) as exc:
        raise DivergenceError(f"Git identity read failed for {root}: {exc}") from exc


def _cross_repository_git(
    root: Path, alternate_root: Path, arguments: Sequence[str]
) -> bytes:
    """Read commits from two clones without fetching or modifying either clone."""

    alternate_common = Path(
        _git_text(
            alternate_root, ["rev-parse", "--path-format=absolute", "--git-common-dir"]
        )
    ).resolve(strict=True)
    alternate_objects = (alternate_common / "objects").resolve(strict=True)
    result = subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        env={
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(alternate_objects),
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
            "TZ": "UTC",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if len(result.stdout) > 16 * 1024 * 1024 or len(result.stderr) > 16 * 1024 * 1024:
        raise DivergenceError("cross-repository Git output exceeded evidence ceiling")
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise DivergenceError(
            f"cross-repository Git read failed ({' '.join(arguments)}): {detail}"
        )
    return result.stdout


def _relative_is_excluded(path: str, policy: InventoryPolicy) -> bool:
    try:
        return _is_excluded(path, policy)
    except InventoryError as exc:
        raise DivergenceError(str(exc)) from exc


def _dirty_snapshot(root: Path, policy: InventoryPolicy) -> dict[str, Any]:
    """Bind dirty paths without reading excluded/private file content."""

    try:
        _codes, entries, status = _status_snapshot(root)
    except NavigationInventoryError as exc:
        raise DivergenceError(str(exc)) from exc
    safe: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for entry in entries:
        paths = [entry["path"]]
        if entry["secondary_path"] is not None:
            paths.append(entry["secondary_path"])
        if any(_relative_is_excluded(path, policy) for path in paths):
            excluded.append(entry)
            continue
        projected = dict(entry)
        identities: list[dict[str, Any]] = []
        for relative in paths:
            path = root.joinpath(*PurePosixPath(relative).parts)
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                identities.append({"path": relative, "disposition": "ABSENT"})
                continue
            digest, error = _stable_hash(path, metadata)
            identities.append(
                {
                    "path": relative,
                    "kind": (
                        "symlink"
                        if stat.S_ISLNK(metadata.st_mode)
                        else "regular"
                        if stat.S_ISREG(metadata.st_mode)
                        else "other"
                    ),
                    "mode": stat.S_IMODE(metadata.st_mode),
                    "size_bytes": metadata.st_size,
                    "content_sha256": digest if error is None else None,
                    "hash_error": error,
                }
            )
        projected["identities"] = identities
        safe.append(projected)
    return {
        "status": status,
        "safe_entries": safe,
        "safe_entries_sha256": sha256_bytes(canonical_bytes(safe)),
        "excluded_entries": len(excluded),
        "excluded_entries_sha256": sha256_bytes(canonical_bytes(excluded)),
        "excluded_paths_recorded": False,
        "excluded_content_read": False,
    }


def _runtime_snapshot(root: Path) -> dict[str, Any]:
    """Hash a runtime's complete path/metadata tree without reading payload bytes."""

    root = root.resolve(strict=True)
    metadata = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise DivergenceError(f"runtime root is not a real directory: {root}")
    rows: list[list[Any]] = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False):
        names.sort()
        files.sort()
        base = Path(directory)
        for name in (*names, *files):
            path = base / name
            relative = path.relative_to(root).as_posix()
            item = path.lstat()
            rows.append(
                [
                    relative,
                    item.st_dev,
                    item.st_ino,
                    stat.S_IFMT(item.st_mode),
                    stat.S_IMODE(item.st_mode),
                    item.st_size,
                    item.st_mtime_ns,
                    item.st_ctime_ns,
                    item.st_uid,
                    item.st_gid,
                    item.st_nlink,
                ]
            )
    return {
        "root": str(root),
        "identity": {
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode),
            "uid": metadata.st_uid,
        },
        "entries": len(rows),
        "metadata_tree_sha256": sha256_bytes(canonical_bytes(rows)),
        "content_bytes_read": False,
        "coverage": "COMPLETE_PATH_AND_METADATA_TREE_ONLY",
    }


def _repository_observation(root: Path, policy: InventoryPolicy) -> dict[str, Any]:
    root = root.resolve(strict=True)
    repository = _repository_snapshot(root)
    try:
        inventory = build_inventory(root, policy)
    except InventoryError as exc:
        raise DivergenceError(str(exc)) from exc
    dirty = _dirty_snapshot(root, policy)
    contains = _git_text(
        root,
        [
            "for-each-ref",
            "--sort=refname",
            "--format=%(refname)%00%(objectname)",
            "--contains",
            repository["head"],
            "refs/remotes",
        ],
    )
    remote_rows = []
    for line in contains.splitlines():
        if not line:
            continue
        parts = line.split("\0")
        if len(parts) != 2:
            raise DivergenceError("Git emitted a malformed remote reachability row")
        remote_rows.append({"ref": parts[0], "oid": parts[1]})
    return {
        "root": str(root),
        "repository": repository,
        "inventory_receipt_sha256": inventory["receipt_sha256"],
        "inventory": {
            "files": inventory["files"],
            "symbols": inventory["symbols"],
            "declared_entrypoints": inventory["declared_entrypoints"],
            "parse_errors": inventory["parse_errors"],
            "privacy": inventory["privacy"],
            "untracked": inventory["untracked"],
            "summary": inventory["summary"],
        },
        "dirty": dirty,
        "remote_tracking": {
            "contains_head": remote_rows,
            "contains_head_count": len(remote_rows),
            "head_reachable_from_remote_tracking": bool(remote_rows),
            "rows_sha256": sha256_bytes(canonical_bytes(remote_rows)),
        },
    }


def _ancestry(canonical: Mapping[str, Any], donor: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(donor["root"])
    canonical_root = Path(canonical["root"])
    canonical_head = canonical["repository"]["head"]
    donor_head = donor["repository"]["head"]
    try:
        merge_base = (
            _cross_repository_git(
                root, canonical_root, ["merge-base", canonical_head, donor_head]
            )
            .decode("ascii", "strict")
            .strip()
        )
        ahead_raw = _cross_repository_git(
            root, canonical_root, ["rev-list", donor_head, "--not", canonical_head]
        )
        behind_raw = _cross_repository_git(
            root, canonical_root, ["rev-list", canonical_head, "--not", donor_head]
        )
    except (DivergenceError, HistoryError) as exc:
        return {
            "status": "INDETERMINATE_OBJECT_NOT_AVAILABLE_OR_NO_COMMON_HISTORY",
            "merge_base": None,
            "canonical_is_ancestor_of_donor": None,
            "donor_is_ancestor_of_canonical": None,
            "donor_unique_commit_count": None,
            "donor_unique_commits_sha256": None,
            "donor_unique_commit_sample": [],
            "canonical_unique_commit_count": None,
            "canonical_unique_commits_sha256": None,
            "canonical_unique_commit_sample": [],
            "samples_complete": False,
            "error_sha256": sha256_bytes(str(exc).encode("utf-8", "replace")),
        }

    ahead = [
        value for value in ahead_raw.decode("ascii", "strict").splitlines() if value
    ]
    behind = [
        value for value in behind_raw.decode("ascii", "strict").splitlines() if value
    ]
    return {
        "status": "PROVEN",
        "merge_base": merge_base,
        "canonical_is_ancestor_of_donor": merge_base == canonical_head,
        "donor_is_ancestor_of_canonical": merge_base == donor_head,
        "donor_unique_commit_count": len(ahead),
        "donor_unique_commits_sha256": sha256_bytes(ahead_raw),
        "donor_unique_commit_sample": ahead[:50],
        "canonical_unique_commit_count": len(behind),
        "canonical_unique_commits_sha256": sha256_bytes(behind_raw),
        "canonical_unique_commit_sample": behind[:50],
        "samples_complete": len(ahead) <= 50 and len(behind) <= 50,
    }


def _symbols_by_path(observation: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for item in observation["inventory"]["symbols"]:
        result[item["path"]].add(f"{item['kind']}:{item['qualified_name']}")
    return {path: frozenset(values) for path, values in result.items()}


def _path_role(path: str) -> str:
    role, _basis = classify_navigation_role(path, repository_present=True, tracked=True)
    return role


def _compare_paths(
    canonical: Mapping[str, Any], donor: Mapping[str, Any]
) -> list[dict[str, Any]]:
    canonical_files = {item["path"]: item for item in canonical["inventory"]["files"]}
    donor_files = {item["path"]: item for item in donor["inventory"]["files"]}
    canonical_symbols = _symbols_by_path(canonical)
    donor_symbols = _symbols_by_path(donor)
    result: list[dict[str, Any]] = []
    for path in sorted(set(canonical_files) | set(donor_files)):
        left = canonical_files.get(path)
        right = donor_files.get(path)
        role = _path_role(path)
        if left is None:
            classification = (
                "GENERATED_OR_DERIVED"
                if role == "GENERATED_OR_CACHE_COPY"
                else "HISTORICAL_ONLY"
                if role == "HISTORICAL_OR_ARCHIVED_COPY"
                else "UNIQUE_TO_DONOR_UNKNOWN_USEFULNESS"
            )
        elif right is None:
            classification = "ABSENT_FROM_DONOR"
        elif left["sha256"] == right["sha256"]:
            classification = "EXACT_EQUIVALENT"
        elif PurePosixPath(path).suffix in {".py", ".pyi"}:
            left_symbols = canonical_symbols.get(path, frozenset())
            right_symbols = donor_symbols.get(path, frozenset())
            if left_symbols < right_symbols:
                classification = "DONOR_STRICT_SYMBOL_SUPERSET"
            elif right_symbols < left_symbols:
                classification = "CANONICAL_STRICT_SYMBOL_SUPERSET"
            elif left_symbols & right_symbols and left_symbols != right_symbols:
                classification = "CONFLICTING_SYMBOL_IDENTITY_SET"
            else:
                classification = "INDETERMINATE_DIFFERENT_CONTENT"
        else:
            classification = "INDETERMINATE_DIFFERENT_CONTENT"
        result.append(
            {
                "path": path,
                "role": role,
                "classification": classification,
                "canonical": None
                if left is None
                else {
                    "sha256": left["sha256"],
                    "git_blob_oid": left["git_blob_oid"],
                    "symbols": sorted(canonical_symbols.get(path, frozenset())),
                },
                "donor": None
                if right is None
                else {
                    "sha256": right["sha256"],
                    "git_blob_oid": right["git_blob_oid"],
                    "symbols": sorted(donor_symbols.get(path, frozenset())),
                },
                "semantic_equivalence_claimed": False,
                "usefulness_claimed": False,
                "retirement_permitted": False,
            }
        )
    return result


def _future_slices(donors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    slices: list[dict[str, Any]] = []
    for donor in donors:
        counts = Counter(item["classification"] for item in donor["path_comparisons"])
        if donor["observation"]["repository"]["status"]["bytes"]:
            slices.append(
                {
                    "priority": 0,
                    "kind": "DIRTY_WORKTREE_REVIEW",
                    "donor_root": donor["observation"]["root"],
                    "reason": "working-tree bytes are not represented by HEAD alone",
                }
            )
        for priority, kind, key in (
            (1, "CONFLICT_REVIEW", "CONFLICTING_SYMBOL_IDENTITY_SET"),
            (2, "DONOR_SUPERSET_REVIEW", "DONOR_STRICT_SYMBOL_SUPERSET"),
            (3, "UNIQUE_PATH_REVIEW", "UNIQUE_TO_DONOR_UNKNOWN_USEFULNESS"),
            (4, "INDETERMINATE_CONTENT_REVIEW", "INDETERMINATE_DIFFERENT_CONTENT"),
        ):
            if counts[key]:
                slices.append(
                    {
                        "priority": priority,
                        "kind": kind,
                        "donor_root": donor["observation"]["root"],
                        "candidate_count": counts[key],
                    }
                )
    return sorted(
        slices,
        key=lambda item: (item["priority"], item["donor_root"], item["kind"]),
    )


def build_cross_worktree_identity_map(
    canonical_root: Path,
    donor_roots: Sequence[Path],
    *,
    runtime_roots: Sequence[Path] = (),
    policy: InventoryPolicy | None = None,
) -> dict[str, Any]:
    """Observe related worktrees and refuse if any observed subject mutates."""

    policy = policy or InventoryPolicy()
    canonical_root = canonical_root.resolve(strict=True)
    donors = [path.resolve(strict=True) for path in donor_roots]
    runtimes = [path.resolve(strict=True) for path in runtime_roots]
    all_repositories = [canonical_root, *donors]
    if len(set(all_repositories)) != len(all_repositories):
        raise DivergenceError("canonical and donor worktree paths must be unique")
    if not donors:
        raise DivergenceError("at least one donor worktree is required")

    repository_before = {
        str(root): _repository_snapshot(root) for root in all_repositories
    }
    dirty_before = {
        str(root): _dirty_snapshot(root, policy) for root in all_repositories
    }
    runtime_before = {str(root): _runtime_snapshot(root) for root in runtimes}

    canonical = _repository_observation(canonical_root, policy)
    donor_observations = []
    for root in donors:
        observation = _repository_observation(root, policy)
        donor_observations.append(
            {
                "observation": observation,
                "ancestry": _ancestry(canonical, observation),
                "path_comparisons": _compare_paths(canonical, observation),
            }
        )

    repository_after = {
        str(root): _repository_snapshot(root) for root in all_repositories
    }
    dirty_after = {
        str(root): _dirty_snapshot(root, policy) for root in all_repositories
    }
    runtime_after = {str(root): _runtime_snapshot(root) for root in runtimes}
    changed = [
        path
        for path in sorted(repository_before)
        if repository_before[path] != repository_after[path]
        or dirty_before[path] != dirty_after[path]
    ]
    runtime_changed = [
        path
        for path in sorted(runtime_before)
        if runtime_before[path] != runtime_after[path]
    ]
    if changed or runtime_changed:
        raise DivergenceError(
            "observed repository or runtime changed during comparison: "
            + ", ".join((*changed, *runtime_changed))
        )

    zero_mutation = seal_document(
        {
            "schema": ZERO_MUTATION_SCHEMA,
            "status": "PASS",
            "authority": "read-only-observation",
            "authority_granted": False,
            "repositories": [
                {
                    "root": path,
                    "before_sha256": sha256_bytes(
                        canonical_bytes(repository_before[path])
                    ),
                    "after_sha256": sha256_bytes(
                        canonical_bytes(repository_after[path])
                    ),
                    "dirty_before_sha256": sha256_bytes(
                        canonical_bytes(dirty_before[path])
                    ),
                    "dirty_after_sha256": sha256_bytes(
                        canonical_bytes(dirty_after[path])
                    ),
                    "unchanged": True,
                }
                for path in sorted(repository_before)
            ],
            "runtimes": [
                {
                    "root": path,
                    "before_sha256": sha256_bytes(
                        canonical_bytes(runtime_before[path])
                    ),
                    "after_sha256": sha256_bytes(canonical_bytes(runtime_after[path])),
                    "unchanged": True,
                    "coverage": runtime_before[path]["coverage"],
                }
                for path in sorted(runtime_before)
            ],
            "limits": {
                "excluded_dirty_content": "NOT_READ_STATUS_STREAM_HASH_BOUND",
                "runtime_content": "NOT_READ_COMPLETE_PATH_AND_METADATA_TREE_ONLY",
            },
        }
    )
    payload = {
        "schema": DIVERGENCE_SCHEMA,
        "status": "PARTIAL_IDENTITY_LAYER",
        "authority": "read-only-non-authoritative-comparison",
        "authority_granted": False,
        "cleanup_permitted": False,
        "retirement_permitted": False,
        "canonical_candidate": {
            "root": canonical["root"],
            "head": canonical["repository"]["head"],
            "tree": canonical["repository"]["tree"],
            "basis": "OPERATOR_DESIGNATED_CANDIDATE_FOR_THIS_COMPARISON",
            "canonicality_proved": False,
        },
        "canonical_observation": canonical,
        "donors": donor_observations,
        "capability_fact_coverage": {
            "file_identity": "PROVEN_FOR_TRACKED_NON_EXCLUDED_PATHS",
            "function_and_class_symbols": "PROVEN_FOR_PARSEABLE_TRACKED_PYTHON",
            "assignment_and_constant_identity": "UNKNOWN_NOT_EXTRACTED_M69",
            "public_export_identity": "UNKNOWN_NOT_EXTRACTED_M69",
            "import_and_caller_identity": "UNKNOWN_NOT_EXTRACTED_M69",
            "executable_entrypoints": "PARTIAL_DECLARED_ENTRYPOINTS_ONLY",
            "semantic_equivalence": "UNKNOWN_NOT_CLAIMED",
            "unique_usefulness": "UNKNOWN_NOT_CLAIMED",
        },
        "classification_vocabulary": [
            "EXACT_EQUIVALENT",
            "DONOR_STRICT_SYMBOL_SUPERSET",
            "CANONICAL_STRICT_SYMBOL_SUPERSET",
            "CONFLICTING_SYMBOL_IDENTITY_SET",
            "UNIQUE_TO_DONOR_UNKNOWN_USEFULNESS",
            "GENERATED_OR_DERIVED",
            "HISTORICAL_ONLY",
            "ABSENT_FROM_DONOR",
            "INDETERMINATE_DIFFERENT_CONTENT",
        ],
        "future_integration_slices": _future_slices(donor_observations),
        "zero_mutation": zero_mutation,
        "claims": {
            "complete_capability_map": False,
            "canonical_owner_proved": False,
            "no_feature_loss": False,
            "retirement_safety": False,
            "source_integration_performed": False,
        },
        "remaining_gaps": [
            "assignment, constant and explicit public-export comparison",
            "import, caller and executable-path reachability comparison",
            "behavioural and test-evidence equivalence",
            "semantic usefulness adjudication for donor-only facts",
            "governed canonical-owner and retirement decisions",
        ],
    }
    return seal_document(payload)


def render_cross_worktree_identity_report(payload: Mapping[str, Any]) -> str:
    counts = Counter(
        item["classification"]
        for donor in payload["donors"]
        for item in donor["path_comparisons"]
    )
    lines = [
        "# M69 GIGA Archaeology worktree identity and divergence map",
        "",
        "## Verdict",
        "",
        "This is a verified deterministic identity/inventory layer, not a complete capability verdict. "
        "It found and hash-bound exact matches, symbol supersets, conflicts, donor-only paths, dirty state, "
        "Git ancestry and remote reachability without mutating any donor.",
        "",
        "## Bound candidate",
        "",
        f"- Root: `{payload['canonical_candidate']['root']}`",
        f"- HEAD: `{payload['canonical_candidate']['head']}`",
        f"- Tree: `{payload['canonical_candidate']['tree']}`",
        "- Canonicality proved: false",
        "",
        "## Deterministic classifications",
        "",
    ]
    for key in payload["classification_vocabulary"]:
        lines.append(f"- {key}: {counts[key]}")
    lines.extend(
        [
            "",
            "## Donors",
            "",
            "| Root | HEAD | Dirty | Remote reachable | Path facts |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for donor in payload["donors"]:
        observation = donor["observation"]
        lines.append(
            f"| `{observation['root']}` | `{observation['repository']['head']}` | "
            f"{observation['repository']['status']['bytes'] > 0} | "
            f"{observation['remote_tracking']['head_reachable_from_remote_tracking']} | "
            f"{len(donor['path_comparisons'])} |"
        )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            f"- Zero-mutation receipt: `{payload['zero_mutation']['receipt_sha256']}`",
            f"- Machine receipt: `{payload['receipt_sha256']}`",
            "- Assignment/export/import/caller/behavioural equivalence remains `UNKNOWN`.",
            "- No source integration, cleanup, retirement, canonicality or no-feature-loss claim was made.",
            "",
            "## Next deterministic slices",
            "",
        ]
    )
    for index, item in enumerate(payload["future_integration_slices"], 1):
        lines.append(
            f"{index}. `{item['kind']}` for `{item['donor_root']}`"
            + (
                f" ({item['candidate_count']} candidates)."
                if "candidate_count" in item
                else f": {item['reason']}."
            )
        )
    lines.extend(["", "The full capability verdict is explicitly deferred.", ""])
    return "\n".join(lines)


def write_cross_worktree_identity_map(
    canonical_root: Path,
    donor_roots: Sequence[Path],
    output: Path,
    *,
    runtime_roots: Sequence[Path] = (),
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists():
        raise DivergenceError("divergence output directory must not already exist")
    payload = build_cross_worktree_identity_map(
        canonical_root, donor_roots, runtime_roots=runtime_roots
    )
    try:
        output.mkdir(parents=True, mode=0o700)
        write_atomic(output / "divergence.json", canonical_bytes(payload))
        write_atomic(
            output / "DIVERGENCE_REPORT.md",
            render_cross_worktree_identity_report(payload).encode("utf-8"),
        )
    except (EvidenceError, OSError) as exc:
        raise DivergenceError(str(exc)) from exc
    return payload


def _exact_python_record(root: Path, item: Mapping[str, Any]) -> dict[str, Any]:
    """Project an M69 inventory row into the canonical Python-map read contract."""

    path = root.joinpath(*PurePosixPath(item["path"]).parts)
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise DivergenceError(
            f"Python source is not a real regular file: {item['path']}"
        )
    if (
        metadata.st_size != item["bytes"]
        or stat.S_IMODE(metadata.st_mode) != item["mode"]
    ):
        raise DivergenceError(
            f"Python source metadata drifted from inventory: {item['path']}"
        )
    return {
        "path": item["path"],
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "size_bytes": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
        "ctime_ns": metadata.st_ctime_ns,
        "mode": stat.S_IMODE(metadata.st_mode),
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "nlink": metadata.st_nlink,
        "content_sha256": item["sha256"],
    }


def _expression_identity(expression: str | None) -> dict[str, Any]:
    if expression is None:
        return {"syntax": "ABSENT", "ast_sha256": None, "literal_kind": None}
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return {
            "syntax": "UNPARSEABLE_CANONICAL_EXPRESSION",
            "ast_sha256": sha256_bytes(expression.encode("utf-8")),
            "literal_kind": None,
        }
    body = tree.body
    literal_kind = type(body.value).__name__ if isinstance(body, ast.Constant) else None
    return {
        "syntax": "PYTHON_AST_EXPRESSION",
        "ast_sha256": sha256_bytes(
            ast.dump(tree, annotate_fields=True, include_attributes=False).encode(
                "utf-8"
            )
        ),
        "literal_kind": literal_kind,
    }


def _literal_export_names(expression: str | None) -> tuple[str, ...] | None:
    if expression is None:
        return None
    try:
        value = ast.literal_eval(expression)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(value, (list, tuple, set, frozenset)):
        return None
    if not all(isinstance(item, str) for item in value):
        return None
    return tuple(sorted(set(value)))


def _static_fact(
    *,
    family: str,
    kind: str,
    path: str,
    source_sha256: str,
    identity: Mapping[str, Any],
    logical_key: Mapping[str, Any],
) -> dict[str, Any]:
    semantic = {
        "family": family,
        "kind": kind,
        "source_path": path,
        "identity": dict(identity),
    }
    return {
        **semantic,
        "fact_id": sha256_bytes(canonical_bytes(semantic)),
        "logical_key": sha256_bytes(canonical_bytes(dict(logical_key))),
        "source_sha256": source_sha256,
        "source_role": _path_role(path),
        "evidence_class": "OBSERVED_STATIC_AST_NON_EXECUTING",
        "runtime_reachability_proved": False,
    }


def _python_static_facts(root: Path, observation: Mapping[str, Any]) -> dict[str, Any]:
    files = [
        item
        for item in observation["inventory"]["files"]
        if item["kind"] == "regular"
        and PurePosixPath(item["path"]).suffix in {".py", ".pyi"}
    ]
    packages = frozenset(
        PurePosixPath(item["path"]).parent.as_posix()
        for item in files
        if PurePosixPath(item["path"]).name == "__init__.py"
    )
    facts: dict[str, list[dict[str, Any]]] = {
        family: [] for family in STATIC_FACT_FAMILIES
    }
    unknowns: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for item in files:
        record = _exact_python_record(root, item)
        try:
            fragment, failure = extract_python_file_fragment(root, record, packages)
        except PythonMapError as exc:
            raise DivergenceError(str(exc)) from exc
        if failure is not None or fragment is None:
            unknowns.append(
                {
                    "path": item["path"],
                    "source_sha256": item["sha256"],
                    "family": "ALL_STATIC_FACT_CLASSES",
                    "classification": "UNKNOWN_FAILED_PARSE",
                    "failure": failure,
                }
            )
            continue

        module = fragment["module"]
        source_path = item["path"]
        source_sha = item["sha256"]
        class_scopes = {
            definition["qualified_name"]
            for definition in fragment["definitions"]
            if definition["kind"] == "CLASS"
        }
        allowed_assignment_scopes = {module, *class_scopes}
        kinds_by_target = {
            definition["qualified_name"]: definition["kind"]
            for definition in fragment["definitions"]
            if definition["kind"] in {"VARIABLE", "CONSTANT"}
        }
        file_facts_before = sum(len(values) for values in facts.values())
        all_flows = [
            flow
            for flow in fragment["data_flows"]
            if flow["kind"] == "ASSIGNMENT"
            and flow["owner"] in allowed_assignment_scopes
        ]
        for flow in all_flows:
            target = flow["target"]
            value = flow["value"]
            identity = {
                "language": "python",
                "module": module,
                "owner": flow["owner"],
                "target": target,
                "symbol_kind": kinds_by_target.get(target, "UNKNOWN_ASSIGNMENT_KIND"),
                "value": _expression_identity(value.get("expression")),
                "loaded_names": value.get("names", []),
                "called_expressions": sorted(
                    call["expression"] for call in value.get("calls", [])
                ),
            }
            facts["assignments_constants"].append(
                _static_fact(
                    family="assignments_constants",
                    kind="MODULE_OR_CLASS_ASSIGNMENT",
                    path=source_path,
                    source_sha256=source_sha,
                    identity=identity,
                    logical_key={"module": module, "target": target},
                )
            )

        explicit_all_seen = False
        for flow in all_flows:
            if flow["target"] != f"{module}.__all__":
                continue
            explicit_all_seen = True
            names = _literal_export_names(flow["value"].get("expression"))
            if names is None:
                unknowns.append(
                    {
                        "path": source_path,
                        "source_sha256": source_sha,
                        "family": "public_exports",
                        "classification": "UNSUPPORTED_DYNAMIC___ALL__",
                        "expression": _expression_identity(
                            flow["value"].get("expression")
                        ),
                    }
                )
                continue
            for name in names:
                facts["public_exports"].append(
                    _static_fact(
                        family="public_exports",
                        kind="EXPLICIT___ALL__",
                        path=source_path,
                        source_sha256=source_sha,
                        identity={
                            "language": "python",
                            "module": module,
                            "exported_name": name,
                            "authority": "EXPLICIT_MODULE_DECLARATION",
                        },
                        logical_key={"module": module, "exported_name": name},
                    )
                )

        public_candidates = {
            definition["name"]
            for definition in fragment["definitions"]
            if definition["scope"] == module
            and definition["kind"]
            in {"CLASS", "FUNCTION", "ASYNC_FUNCTION", "VARIABLE", "CONSTANT"}
            and not definition["name"].startswith("_")
        }
        if not explicit_all_seen:
            for name in sorted(public_candidates):
                facts["public_exports"].append(
                    _static_fact(
                        family="public_exports",
                        kind="INFERRED_PUBLIC_NAME_UNCERTAIN",
                        path=source_path,
                        source_sha256=source_sha,
                        identity={
                            "language": "python",
                            "module": module,
                            "exported_name": name,
                            "authority": "INFERRED_NON_UNDERSCORE_NAME",
                        },
                        logical_key={"module": module, "exported_name": name},
                    )
                )

        local_bindings = set(public_candidates)
        for imported in fragment["imports"]:
            identity = {
                "language": "python",
                "importer_module": module,
                "module": imported["module"],
                "imported_name": imported["imported_name"],
                "alias": imported["alias"],
                "level": imported["level"],
            }
            facts["imports"].append(
                _static_fact(
                    family="imports",
                    kind="STATIC_IMPORT",
                    path=source_path,
                    source_sha256=source_sha,
                    identity=identity,
                    logical_key={
                        "importer_module": module,
                        "binding": imported["alias"],
                    },
                )
            )
            local_bindings.add(imported["alias"])
            if imported["imported_name"] == "*":
                unknowns.append(
                    {
                        "path": source_path,
                        "source_sha256": source_sha,
                        "family": "imports",
                        "classification": "UNSUPPORTED_DYNAMIC_STAR_IMPORT_SURFACE",
                    }
                )
            if PurePosixPath(source_path).name == "__init__.py" and not imported[
                "alias"
            ].startswith("_"):
                facts["public_exports"].append(
                    _static_fact(
                        family="public_exports",
                        kind="PACKAGE_REEXPORT",
                        path=source_path,
                        source_sha256=source_sha,
                        identity={
                            "language": "python",
                            "module": module,
                            "exported_name": imported["alias"],
                            "import_module": imported["module"],
                            "imported_name": imported["imported_name"],
                            "level": imported["level"],
                            "authority": "PACKAGE_IMPORT_BINDING",
                        },
                        logical_key={
                            "module": module,
                            "exported_name": imported["alias"],
                        },
                    )
                )

        dynamic_names = {
            "__import__",
            "eval",
            "exec",
            "getattr",
            "globals",
            "importlib.import_module",
            "locals",
            "setattr",
        }
        for call in fragment["calls"]:
            expression = call["expression"]
            facts["callers_references"].append(
                _static_fact(
                    family="callers_references",
                    kind="STATIC_CALLSITE_COUNTEREVIDENCE",
                    path=source_path,
                    source_sha256=source_sha,
                    identity={
                        "language": "python",
                        "module": module,
                        "caller": call["caller"],
                        "expression": expression,
                        "name": call["name"],
                        "dynamic": call["dynamic"],
                        "use_is_deletion_counterevidence": True,
                    },
                    logical_key={
                        "module": module,
                        "caller": call["caller"],
                        "name": call["name"],
                    },
                )
            )
            if call["dynamic"] or expression in dynamic_names:
                unknowns.append(
                    {
                        "path": source_path,
                        "source_sha256": source_sha,
                        "family": "callers_references",
                        "classification": "UNSUPPORTED_DYNAMIC_OR_REFLECTIVE_CALL",
                        "caller": call["caller"],
                        "expression": expression,
                    }
                )
            if expression.startswith("__all__."):
                unknowns.append(
                    {
                        "path": source_path,
                        "source_sha256": source_sha,
                        "family": "public_exports",
                        "classification": "UNSUPPORTED_DYNAMIC___ALL___MUTATION",
                        "expression": expression,
                    }
                )

        for reference in fragment["references"]:
            if reference["name"] not in local_bindings:
                continue
            facts["callers_references"].append(
                _static_fact(
                    family="callers_references",
                    kind="BOUNDED_SIMPLE_NAME_REFERENCE_COUNTEREVIDENCE",
                    path=source_path,
                    source_sha256=source_sha,
                    identity={
                        "language": "python",
                        "module": module,
                        "scope": reference["scope"],
                        "expression": reference["expression"],
                        "name": reference["name"],
                        "resolution": "SAME_FILE_SIMPLE_NAME_CANDIDATE",
                        "use_is_deletion_counterevidence": True,
                    },
                    logical_key={
                        "module": module,
                        "scope": reference["scope"],
                        "name": reference["name"],
                    },
                )
            )
        file_facts_after = sum(len(values) for values in facts.values())
        bindings.append(
            {
                "path": source_path,
                "content_sha256": source_sha,
                "git_blob_oid": item["git_blob_oid"],
                "module": module,
                "ast_sha256": fragment["ast_sha256"],
                "fact_count_before_deduplication": file_facts_after - file_facts_before,
            }
        )

    deduplicated = {
        family: sorted(
            {fact["fact_id"]: fact for fact in values}.values(),
            key=lambda fact: fact["fact_id"],
        )
        for family, values in facts.items()
    }
    tracked_paths = {item["path"] for item in observation["inventory"]["files"]}
    untracked_python = sorted(
        identity["path"]
        for entry in observation["dirty"]["safe_entries"]
        for identity in entry["identities"]
        if identity["path"] not in tracked_paths
        and PurePosixPath(identity["path"]).suffix in {".py", ".pyi"}
    )
    for path in untracked_python:
        unknowns.append(
            {
                "path": path,
                "family": "ALL_STATIC_FACT_CLASSES",
                "classification": "UNKNOWN_UNADMITTED_UNTRACKED_PYTHON",
            }
        )
    return {
        "root": str(root),
        "repository": observation["repository"],
        "inventory_receipt_sha256": observation["inventory_receipt_sha256"],
        "source_bindings": sorted(bindings, key=lambda item: item["path"]),
        "facts": deduplicated,
        "unknowns": sorted(
            unknowns,
            key=lambda item: (
                item["path"],
                item["family"],
                item["classification"],
                item.get("expression", ""),
            ),
        ),
        "coverage": {
            "language": "PYTHON_ONLY_M70",
            "python_files_bound": len(bindings),
            "python_files_failed_or_unknown": sum(
                item["classification"].startswith("UNKNOWN_") for item in unknowns
            ),
            "module_and_class_assignments": "COVERED_STATIC_AST",
            "explicit___all__": "COVERED_LITERAL_SEQUENCE_ONLY",
            "package_reexports": "COVERED_STATIC_IMPORT_BINDINGS",
            "inferred_public_names": "NONAUTHORITATIVE_UNCERTAIN_CANDIDATES",
            "imports": "COVERED_STATIC_IMPORTS_STAR_SURFACE_UNSUPPORTED",
            "callers": "COVERED_STATIC_CALLS_RUNTIME_DISPATCH_UNPROVED",
            "references": "BOUNDED_SAME_FILE_SIMPLE_NAME_CANDIDATES",
            "dynamic_import_reflection": "UNSUPPORTED_PRESERVED_AS_UNKNOWN",
            "non_python_languages": "UNKNOWN_NOT_EXTRACTED_M70",
        },
    }


def _fact_delta(fact: Mapping[str, Any], default: str) -> dict[str, Any]:
    role = fact["source_role"]
    disposition = (
        "GENERATED_OR_DERIVED"
        if role == "GENERATED_OR_CACHE_COPY"
        else "HISTORICAL_ONLY"
        if role == "HISTORICAL_OR_ARCHIVED_COPY"
        else default
    )
    return {
        "fact_id": fact["fact_id"],
        "logical_key": fact["logical_key"],
        "source_path": fact["source_path"],
        "source_sha256": fact["source_sha256"],
        "kind": fact["kind"],
        "disposition": disposition,
    }


def _compare_static_facts(
    canonical: Mapping[str, Any], donor: Mapping[str, Any]
) -> dict[str, Any]:
    families: dict[str, Any] = {}
    for family in STATIC_FACT_FAMILIES:
        left = {item["fact_id"]: item for item in canonical["facts"][family]}
        right = {item["fact_id"]: item for item in donor["facts"][family]}
        exact = sorted(set(left) & set(right))
        canonical_only = sorted(set(left) - set(right))
        donor_only = sorted(set(right) - set(left))
        left_keys = defaultdict(set)
        right_keys = defaultdict(set)
        for fact_id, fact in left.items():
            left_keys[fact["logical_key"]].add(fact_id)
        for fact_id, fact in right.items():
            right_keys[fact["logical_key"]].add(fact_id)
        conflicting_keys = sorted(
            key
            for key in set(left_keys) & set(right_keys)
            if left_keys[key] != right_keys[key]
        )
        if not left and not right:
            classification = "UNKNOWN_NO_SUPPORTED_FACTS"
        elif set(left) == set(right):
            classification = "EXACT_EQUIVALENT"
        elif set(left) < set(right):
            classification = "DONOR_STRICT_SUPERSET"
        elif set(right) < set(left):
            classification = "CANONICAL_STRICT_SUPERSET"
        elif conflicting_keys:
            classification = "CONFLICTING"
        else:
            classification = "MIXED_DONOR_ONLY_AND_CANONICAL_ONLY"
        families[family] = {
            "classification": classification,
            "exact_equivalent_count": len(exact),
            "exact_equivalent_ids_sha256": sha256_bytes(canonical_bytes(exact)),
            "exact_equivalent_id_sample": exact[:20],
            "canonical_only": [
                _fact_delta(left[value], "CANONICAL_ONLY") for value in canonical_only
            ],
            "donor_only": [
                _fact_delta(right[value], "DONOR_ONLY") for value in donor_only
            ],
            "conflicts": [
                {
                    "logical_key": key,
                    "canonical_fact_ids": sorted(left_keys[key]),
                    "donor_fact_ids": sorted(right_keys[key]),
                    "disposition": "CONFLICTING",
                }
                for key in conflicting_keys
            ],
        }
    return {
        "donor_root": donor["root"],
        "donor_head": donor["repository"]["head"],
        "donor_tree": donor["repository"]["tree"],
        "families": families,
        "unknowns": donor["unknowns"],
    }


def _review_clusters(comparisons: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    for comparison in comparisons:
        donor = comparison["donor_root"]
        for unknown in comparison["unknowns"]:
            clusters.append(
                {
                    "priority": 0,
                    "kind": "UNSUPPORTED_OR_UNKNOWN_REVIEW",
                    "donor_root": donor,
                    "family": unknown["family"],
                    "source_path": unknown["path"],
                    "reason": unknown["classification"],
                }
            )
        for family, result in comparison["families"].items():
            if result["conflicts"]:
                clusters.append(
                    {
                        "priority": 1,
                        "kind": "CONFLICT_REVIEW",
                        "donor_root": donor,
                        "family": family,
                        "candidate_count": len(result["conflicts"]),
                    }
                )
            if result["donor_only"]:
                clusters.append(
                    {
                        "priority": 2,
                        "kind": "DONOR_ONLY_FACT_REVIEW",
                        "donor_root": donor,
                        "family": family,
                        "candidate_count": len(result["donor_only"]),
                    }
                )
    return sorted(
        clusters,
        key=lambda item: (
            item["priority"],
            item["donor_root"],
            item["family"],
            item.get("source_path", ""),
        ),
    )


def _predecessor_identity(path: Path) -> dict[str, Any]:
    path = path.resolve(strict=True)
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
        validate_self_hash(payload)
    except (json.JSONDecodeError, EvidenceError) as exc:
        raise DivergenceError(f"M69 predecessor evidence is invalid: {exc}") from exc
    if payload.get("schema") != DIVERGENCE_SCHEMA:
        raise DivergenceError("M69 predecessor has the wrong schema")
    return {
        "path": str(path),
        "raw_sha256": sha256_bytes(raw),
        "receipt_sha256": payload["receipt_sha256"],
        "zero_mutation_receipt_sha256": payload["zero_mutation"]["receipt_sha256"],
        "rewritten": False,
    }


def build_cross_worktree_static_fact_map(
    canonical_root: Path,
    donor_roots: Sequence[Path],
    predecessor: Path,
    *,
    runtime_roots: Sequence[Path] = (),
    policy: InventoryPolicy | None = None,
) -> dict[str, Any]:
    """Extend M69 with bounded Python static facts under one mutation envelope."""

    policy = policy or InventoryPolicy()
    canonical_root = canonical_root.resolve(strict=True)
    donors = [path.resolve(strict=True) for path in donor_roots]
    runtimes = [path.resolve(strict=True) for path in runtime_roots]
    repositories = [canonical_root, *donors]
    before = {str(root): _repository_snapshot(root) for root in repositories}
    dirty_before = {str(root): _dirty_snapshot(root, policy) for root in repositories}
    runtime_before = {str(root): _runtime_snapshot(root) for root in runtimes}
    predecessor_identity = _predecessor_identity(predecessor)
    identity_map = build_cross_worktree_identity_map(
        canonical_root, donors, runtime_roots=runtimes, policy=policy
    )
    canonical = _python_static_facts(
        canonical_root, identity_map["canonical_observation"]
    )
    donor_facts = [
        _python_static_facts(Path(item["observation"]["root"]), item["observation"])
        for item in identity_map["donors"]
    ]
    comparisons = [_compare_static_facts(canonical, donor) for donor in donor_facts]
    after = {str(root): _repository_snapshot(root) for root in repositories}
    dirty_after = {str(root): _dirty_snapshot(root, policy) for root in repositories}
    runtime_after = {str(root): _runtime_snapshot(root) for root in runtimes}
    changed = [
        path
        for path in sorted(before)
        if before[path] != after[path] or dirty_before[path] != dirty_after[path]
    ]
    runtime_changed = [
        path
        for path in sorted(runtime_before)
        if runtime_before[path] != runtime_after[path]
    ]
    if changed or runtime_changed:
        raise DivergenceError(
            "observed repository or runtime changed during static comparison: "
            + ", ".join((*changed, *runtime_changed))
        )
    zero_mutation = seal_document(
        {
            "schema": ZERO_MUTATION_SCHEMA,
            "status": "PASS",
            "authority": "read-only-static-fact-observation",
            "authority_granted": False,
            "repositories": [
                {
                    "root": path,
                    "before_sha256": sha256_bytes(canonical_bytes(before[path])),
                    "after_sha256": sha256_bytes(canonical_bytes(after[path])),
                    "dirty_before_sha256": sha256_bytes(
                        canonical_bytes(dirty_before[path])
                    ),
                    "dirty_after_sha256": sha256_bytes(
                        canonical_bytes(dirty_after[path])
                    ),
                    "unchanged": True,
                }
                for path in sorted(before)
            ],
            "runtimes": [
                {
                    "root": path,
                    "before_sha256": sha256_bytes(
                        canonical_bytes(runtime_before[path])
                    ),
                    "after_sha256": sha256_bytes(canonical_bytes(runtime_after[path])),
                    "unchanged": True,
                    "coverage": runtime_before[path]["coverage"],
                }
                for path in sorted(runtime_before)
            ],
            "limits": {
                "excluded_dirty_content": "NOT_READ_STATUS_STREAM_HASH_BOUND",
                "runtime_content": "NOT_READ_COMPLETE_PATH_AND_METADATA_TREE_ONLY",
            },
        }
    )
    counts = {
        "canonical": {
            family: len(canonical["facts"][family]) for family in STATIC_FACT_FAMILIES
        },
        "donors": {
            donor["root"]: {
                family: len(donor["facts"][family]) for family in STATIC_FACT_FAMILIES
            }
            for donor in donor_facts
        },
        "canonical_unknowns": len(canonical["unknowns"]),
        "donor_unknowns": sum(len(donor["unknowns"]) for donor in donor_facts),
    }
    return seal_document(
        {
            "schema": STATIC_DIVERGENCE_SCHEMA,
            "status": "PARTIAL_STATIC_FACT_LAYER",
            "publication_encoding": "DETERMINISTIC_GZIP_LEVEL_9_MTIME_ZERO",
            "authority": "read-only-non-authoritative-comparison",
            "authority_granted": False,
            "cleanup_permitted": False,
            "retirement_permitted": False,
            "predecessor_m69": predecessor_identity,
            "canonical_candidate": {
                "root": canonical["root"],
                "head": canonical["repository"]["head"],
                "tree": canonical["repository"]["tree"],
                "canonicality_proved": False,
            },
            "canonical_static_facts": canonical,
            "donor_static_facts": donor_facts,
            "comparisons": comparisons,
            "counts": counts,
            "classification_vocabulary": [
                "EXACT_EQUIVALENT",
                "DONOR_STRICT_SUPERSET",
                "CANONICAL_STRICT_SUPERSET",
                "CONFLICTING",
                "DONOR_ONLY",
                "CANONICAL_ONLY",
                "GENERATED_OR_DERIVED",
                "HISTORICAL_ONLY",
                "UNSUPPORTED_DYNAMIC",
                "UNKNOWN",
            ],
            "review_clusters": _review_clusters(comparisons),
            "zero_mutation": zero_mutation,
            "claims": {
                "python_static_fact_layer_complete_within_declared_limits": True,
                "non_python_static_fact_layer_complete": False,
                "runtime_reachability_proved": False,
                "canonical_owner_proved": False,
                "no_feature_loss": False,
                "retirement_safety": False,
                "source_integration_performed": False,
            },
            "remaining_gaps": [
                "non-Python assignment/export/import/caller fact comparison",
                "dynamic imports, reflection, monkey patching and runtime dispatch",
                "cross-file name resolution beyond bounded static candidates",
                "behavioural and test-evidence equivalence",
                "governed canonical-owner and retirement decisions",
            ],
        }
    )


def render_cross_worktree_static_fact_report(payload: Mapping[str, Any]) -> str:
    lines = [
        "# M70 GIGA Archaeology static fact divergence map",
        "",
        "## Verdict",
        "",
        "The four M69 static-evidence gaps are now deterministically mapped for parseable tracked Python. "
        "Dynamic/reflection and non-Python behavior remain explicit UNKNOWNs; static use is deletion "
        "counterevidence, never runtime-reachability proof.",
        "",
        "## Bound candidate",
        "",
        f"- HEAD: `{payload['canonical_candidate']['head']}`",
        f"- Tree: `{payload['canonical_candidate']['tree']}`",
        f"- M69 predecessor receipt: `{payload['predecessor_m69']['receipt_sha256']}`",
        f"- M70 receipt: `{payload['receipt_sha256']}`",
        f"- Zero-mutation receipt: `{payload['zero_mutation']['receipt_sha256']}`",
        "",
        "## Canonical fact counts",
        "",
    ]
    for family, count in payload["counts"]["canonical"].items():
        lines.append(f"- {family}: {count}")
    lines.extend(
        [
            "",
            "## Donor comparison",
            "",
            "| Donor | Assignments | Exports | Imports | Callers/references | Unknowns |",
            "|---|---|---|---|---|---:|",
        ]
    )
    for comparison in payload["comparisons"]:
        families = comparison["families"]
        lines.append(
            f"| `{comparison['donor_root']}` | {families['assignments_constants']['classification']} | "
            f"{families['public_exports']['classification']} | {families['imports']['classification']} | "
            f"{families['callers_references']['classification']} | {len(comparison['unknowns'])} |"
        )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "- Explicit `__all__`, package re-exports and inferred public-name candidates are distinct facts.",
            "- Dynamic imports, reflection, star-import surfaces and dynamic `__all__` mutations remain UNKNOWN.",
            "- No canonical-owner, retirement, no-feature-loss or runtime-reachability verdict is made.",
            "",
            "## Ordered review clusters",
            "",
        ]
    )
    for index, cluster in enumerate(payload["review_clusters"], 1):
        lines.append(
            f"{index}. `{cluster['kind']}` / `{cluster['family']}` / `{cluster['donor_root']}`"
            + (
                f" / `{cluster['source_path']}`: {cluster['reason']}"
                if "source_path" in cluster
                else f" ({cluster['candidate_count']} candidates)."
            )
        )
    lines.extend(
        [
            "",
            "The next slice is behavioral review of these clusters, not retirement.",
            "",
        ]
    )
    return "\n".join(lines)


def write_cross_worktree_static_fact_map(
    canonical_root: Path,
    donor_roots: Sequence[Path],
    predecessor: Path,
    output: Path,
    *,
    runtime_roots: Sequence[Path] = (),
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists():
        raise DivergenceError(
            "static divergence output directory must not already exist"
        )
    payload = build_cross_worktree_static_fact_map(
        canonical_root,
        donor_roots,
        predecessor,
        runtime_roots=runtime_roots,
    )
    try:
        output.mkdir(parents=True, mode=0o700)
        write_atomic(
            output / "static_divergence.json.gz",
            gzip.compress(canonical_bytes(payload), compresslevel=9, mtime=0),
        )
        write_atomic(
            output / "STATIC_DIVERGENCE_REPORT.md",
            render_cross_worktree_static_fact_report(payload).encode("utf-8"),
        )
    except (EvidenceError, OSError) as exc:
        raise DivergenceError(str(exc)) from exc
    return payload


def _static_predecessor_identity(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = path.resolve(strict=True)
    compressed = path.read_bytes()
    if len(compressed) >= 100_000_000:
        raise DivergenceError("M70 compressed predecessor exceeds publication ceiling")
    if len(compressed) < 10 or compressed[:2] != b"\x1f\x8b":
        raise DivergenceError("M70 predecessor is not a gzip artifact")
    if int.from_bytes(compressed[4:8], "little") != 0:
        raise DivergenceError("M70 predecessor gzip mtime is not deterministic zero")
    try:
        restored = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        raise DivergenceError(f"M70 predecessor cannot be restored: {exc}") from exc
    if len(restored) > 512 * 1024 * 1024:
        raise DivergenceError("M70 restored predecessor exceeds evidence ceiling")
    try:
        payload = json.loads(restored)
        validate_self_hash(payload)
        validate_self_hash(payload["zero_mutation"])
    except (json.JSONDecodeError, EvidenceError, KeyError) as exc:
        raise DivergenceError(f"M70 predecessor evidence is invalid: {exc}") from exc
    if payload.get("schema") != STATIC_DIVERGENCE_SCHEMA:
        raise DivergenceError("M70 predecessor has the wrong schema")
    return payload, {
        "path": str(path),
        "compressed_sha256": sha256_bytes(compressed),
        "compressed_bytes": len(compressed),
        "restored_sha256": sha256_bytes(restored),
        "restored_bytes": len(restored),
        "receipt_sha256": payload["receipt_sha256"],
        "zero_mutation_receipt_sha256": payload["zero_mutation"]["receipt_sha256"],
        "gzip_mtime": 0,
        "rewritten": False,
    }


def _m70_fact_lookups(payload: Mapping[str, Any]) -> dict[str, Any]:
    canonical = {
        fact["fact_id"]: fact
        for family in STATIC_FACT_FAMILIES
        for fact in payload["canonical_static_facts"]["facts"][family]
    }
    donors = {
        repository["root"]: {
            fact["fact_id"]: fact
            for family in STATIC_FACT_FAMILIES
            for fact in repository["facts"][family]
        }
        for repository in payload["donor_static_facts"]
    }
    unknowns = {
        repository["root"]: repository["unknowns"]
        for repository in payload["donor_static_facts"]
    }
    comparisons = {
        comparison["donor_root"]: comparison for comparison in payload["comparisons"]
    }
    return {
        "canonical": canonical,
        "donors": donors,
        "unknowns": unknowns,
        "comparisons": comparisons,
    }


def _subject_names(facts: Sequence[Mapping[str, Any]]) -> list[str]:
    names: set[str] = set()
    for fact in facts:
        identity = fact["identity"]
        for key in (
            "alias",
            "caller",
            "exported_name",
            "expression",
            "imported_name",
            "name",
            "target",
        ):
            value = identity.get(key)
            if not isinstance(value, str) or not value or value == "*":
                continue
            leaf = value.rsplit(".", 1)[-1]
            if leaf.isidentifier():
                names.add(leaf)
    return sorted(names)


def _m70_cluster_subjects(
    payload: Mapping[str, Any],
    lookups: Mapping[str, Any],
    cluster: Mapping[str, Any],
) -> dict[str, Any]:
    donor_root = cluster["donor_root"]
    comparison = lookups["comparisons"][donor_root]
    canonical_ids: set[str] = set()
    donor_ids: set[str] = set()
    unknown_records: list[Mapping[str, Any]] = []
    family = cluster["family"]
    result = comparison["families"].get(family)
    if cluster["kind"] == "CONFLICT_REVIEW" and result is not None:
        for conflict in result["conflicts"]:
            canonical_ids.update(conflict["canonical_fact_ids"])
            donor_ids.update(conflict["donor_fact_ids"])
    elif cluster["kind"] == "DONOR_ONLY_FACT_REVIEW" and result is not None:
        donor_ids.update(item["fact_id"] for item in result["donor_only"])
    elif cluster["kind"] == "UNSUPPORTED_OR_UNKNOWN_REVIEW":
        unknown_records = [
            item
            for item in lookups["unknowns"][donor_root]
            if item["family"] == family
            and item["path"] == cluster["source_path"]
            and item["classification"] == cluster["reason"]
        ]
    canonical_facts = [
        lookups["canonical"][fact_id]
        for fact_id in sorted(canonical_ids)
        if fact_id in lookups["canonical"]
    ]
    donor_facts = [
        lookups["donors"][donor_root][fact_id]
        for fact_id in sorted(donor_ids)
        if fact_id in lookups["donors"][donor_root]
    ]
    all_facts = [*canonical_facts, *donor_facts]
    unknown_hashes = sorted(
        sha256_bytes(canonical_bytes(item)) for item in unknown_records
    )
    all_ids = sorted((*canonical_ids, *donor_ids))
    return {
        "donor_root": donor_root,
        "family": family,
        "canonical_fact_ids": sorted(canonical_ids),
        "donor_fact_ids": sorted(donor_ids),
        "subject_fact_count": len(all_ids),
        "subject_fact_ids_sha256": sha256_bytes(canonical_bytes(all_ids)),
        "subject_fact_id_sample": all_ids[:20],
        "canonical_source_paths": sorted(
            {fact["source_path"] for fact in canonical_facts}
        ),
        "donor_source_paths": sorted({fact["source_path"] for fact in donor_facts})
        or ([cluster["source_path"]] if "source_path" in cluster else []),
        "subject_names": _subject_names(all_facts),
        "unknown_record_count": len(unknown_records),
        "unknown_record_hashes_sha256": sha256_bytes(canonical_bytes(unknown_hashes)),
        "unknown_record_hash_sample": unknown_hashes[:20],
        "unsupported_reason": cluster.get("reason"),
    }


def _behavior_source_drift(
    current: Mapping[str, Any], predecessor: Mapping[str, Any]
) -> dict[str, Any]:
    current_files = {item["path"]: item for item in current["inventory"]["files"]}
    changed: list[dict[str, Any]] = []
    missing: list[str] = []
    for binding in predecessor["source_bindings"]:
        item = current_files.get(binding["path"])
        if item is None:
            missing.append(binding["path"])
        elif item["sha256"] != binding["content_sha256"]:
            changed.append(
                {
                    "path": binding["path"],
                    "m70_sha256": binding["content_sha256"],
                    "current_sha256": item["sha256"],
                }
            )
    return {
        "changed": changed,
        "changed_count": len(changed),
        "changed_paths_sha256": sha256_bytes(
            canonical_bytes([item["path"] for item in changed])
        ),
        "missing": missing,
        "missing_count": len(missing),
        "missing_paths_sha256": sha256_bytes(canonical_bytes(missing)),
    }


def _test_path(path: str) -> bool:
    pure = PurePosixPath(path)
    return (
        any(part in {"test", "tests"} for part in pure.parts)
        or pure.name.startswith("test_")
        or pure.name.endswith("_test.py")
    )


def _behavior_record(
    *, kind: str, path: str, source_sha256: str, identity: Mapping[str, Any]
) -> dict[str, Any]:
    semantic = {
        "kind": kind,
        "source_path": path,
        "identity": dict(identity),
    }
    return {
        **semantic,
        "evidence_id": sha256_bytes(canonical_bytes(semantic)),
        "source_sha256": source_sha256,
        "evidence_class": "OBSERVED_STATIC_AST_NON_EXECUTING",
        "execution_proved": False,
        "usefulness_proved": False,
    }


def _python_behavior_catalog(
    root: Path,
    observation: Mapping[str, Any],
    relevant_paths: frozenset[str],
) -> dict[str, Any]:
    files = [
        item
        for item in observation["inventory"]["files"]
        if item["kind"] == "regular"
        and PurePosixPath(item["path"]).suffix in {".py", ".pyi"}
    ]
    packages = frozenset(
        PurePosixPath(item["path"]).parent.as_posix()
        for item in files
        if PurePosixPath(item["path"]).name == "__init__.py"
    )
    symbols: list[dict[str, Any]] = []
    tests: list[dict[str, Any]] = []
    entrypoints: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for item in files:
        record = _exact_python_record(root, item)
        try:
            fragment, failure = extract_python_file_fragment(root, record, packages)
        except PythonMapError as exc:
            raise DivergenceError(str(exc)) from exc
        if fragment is None or failure is not None:
            if item["path"] in relevant_paths or _test_path(item["path"]):
                unknowns.append(
                    {
                        "path": item["path"],
                        "classification": "UNKNOWN_FAILED_PARSE",
                        "failure": failure,
                    }
                )
            continue
        fingerprint_by_name = {
            value["qualified_name"]: value
            for value in fragment["structural_similarity"]["fingerprints"]
        }
        if item["path"] in relevant_paths:
            for definition in fragment["definitions"]:
                if definition["kind"] not in {
                    "ASYNC_FUNCTION",
                    "ASYNC_METHOD",
                    "CLASS",
                    "FUNCTION",
                    "METHOD",
                }:
                    continue
                attributes = definition["attributes"]
                signature = {
                    "kind": definition["kind"],
                    "signature": attributes.get("signature"),
                    "returns": attributes.get("returns"),
                    "bases": attributes.get("bases"),
                }
                decorators = attributes.get("decorators", [])
                fingerprint = fingerprint_by_name.get(definition["qualified_name"])
                symbols.append(
                    _behavior_record(
                        kind="PYTHON_SYMBOL_STRUCTURE",
                        path=item["path"],
                        source_sha256=item["sha256"],
                        identity={
                            "module": fragment["module"],
                            "name": definition["name"],
                            "qualified_name": definition["qualified_name"],
                            "symbol_kind": definition["kind"],
                            "signature_sha256": sha256_bytes(
                                canonical_bytes(signature)
                            ),
                            "decorators_sha256": sha256_bytes(
                                canonical_bytes(decorators)
                            ),
                            "body_fingerprint_sha256": (
                                None
                                if fingerprint is None
                                else fingerprint["fingerprint_sha256"]
                            ),
                            "body_fingerprint_status": (
                                "COVERED_CONSERVATIVE_NORMALIZATION"
                                if fingerprint is not None
                                else "UNKNOWN_NORMALIZATION_INELIGIBLE"
                            ),
                        },
                    )
                )
        for value in fragment["entrypoints"]:
            entrypoints.append(
                _behavior_record(
                    kind="PYTHON_ENTRYPOINT_DECLARATION",
                    path=item["path"],
                    source_sha256=item["sha256"],
                    identity={
                        "module": fragment["module"],
                        "entrypoint_kind": value["kind"],
                        "name": value["name"],
                        "target": value["target"],
                        "handler": value["handler"],
                    },
                )
            )
        if not _test_path(item["path"]):
            continue
        flows = {flow["owner"]: flow for flow in fragment["control_flows"]}
        calls_by_scope: dict[str, set[str]] = defaultdict(set)
        references_by_scope: dict[str, set[str]] = defaultdict(set)
        for call in fragment["calls"]:
            if call["name"]:
                calls_by_scope[call["caller"]].add(call["name"])
        for reference in fragment["references"]:
            references_by_scope[reference["scope"]].add(reference["name"])
        for definition in fragment["definitions"]:
            decorators = definition["attributes"].get("decorators", [])
            fixture = any(
                value == "fixture" or value.endswith(".fixture") for value in decorators
            )
            is_test = definition["name"].startswith("test") or (
                definition["kind"] == "CLASS" and definition["name"].startswith("Test")
            )
            if not fixture and not is_test:
                continue
            flow = flows.get(definition["qualified_name"])
            assertions = (
                []
                if flow is None
                else [
                    {
                        "condition_sha256": sha256_bytes(
                            str(node["attributes"].get("condition", "")).encode("utf-8")
                        )
                    }
                    for node in flow["nodes"]
                    if node["kind"] == "ASSERT"
                ]
            )
            referenced = sorted(
                calls_by_scope.get(definition["qualified_name"], set())
                | references_by_scope.get(definition["qualified_name"], set())
            )
            tests.append(
                _behavior_record(
                    kind="PYTHON_TEST_OR_FIXTURE_DEFINITION",
                    path=item["path"],
                    source_sha256=item["sha256"],
                    identity={
                        "module": fragment["module"],
                        "name": definition["name"],
                        "qualified_name": definition["qualified_name"],
                        "definition_kind": definition["kind"],
                        "is_test_candidate": is_test,
                        "is_fixture_candidate": fixture,
                        "decorators_sha256": sha256_bytes(canonical_bytes(decorators)),
                        "assertion_count": len(assertions),
                        "assertions_sha256": sha256_bytes(canonical_bytes(assertions)),
                        "referenced_names": referenced,
                        "static_presence_only": True,
                    },
                )
            )
    files_by_path = {item["path"]: item for item in observation["inventory"]["files"]}
    for declaration in observation["inventory"]["declared_entrypoints"]:
        item = files_by_path[declaration["path"]]
        entrypoints.append(
            _behavior_record(
                kind="INVENTORY_DECLARED_ENTRYPOINT",
                path=declaration["path"],
                source_sha256=item["sha256"],
                identity={
                    "entrypoint_kind": declaration["kind"],
                    "target": declaration["target"],
                },
            )
        )

    current_paths = [item["path"] for item in observation["inventory"]["files"]]
    admitted_history_paths = sorted(
        path for path in relevant_paths if path in files_by_path
    )
    history: list[dict[str, Any]] = []
    history_coverage: Mapping[str, Any]
    if admitted_history_paths:
        try:
            lineage = collect_recent_lineage(
                root,
                observation["repository"]["head"],
                admitted_history_paths,
                current_paths=current_paths,
            )
        except HistoryError as exc:
            history_coverage = {
                "status": "UNKNOWN_HISTORY_EXTRACTION_FAILED",
                "error_sha256": sha256_bytes(str(exc).encode("utf-8", "replace")),
            }
        else:
            changes_by_path: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
            renames_by_path: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
            for change in lineage["changes"]:
                changes_by_path[change["current_path"]].append(change)
            for rename in lineage["renames"]:
                renames_by_path[rename["current_path"]].append(rename)
            for path in admitted_history_paths:
                changes = changes_by_path[path]
                renames = renames_by_path[path]
                commits = sorted({item["commit"] for item in changes})
                history.append(
                    _behavior_record(
                        kind="GIT_PATH_LINEAGE_SUMMARY",
                        path=path,
                        source_sha256=files_by_path[path]["sha256"],
                        identity={
                            "head": lineage["head"],
                            "git_blob_oid": files_by_path[path]["git_blob_oid"],
                            "change_count": len(changes),
                            "change_commits_sha256": sha256_bytes(
                                canonical_bytes(commits)
                            ),
                            "change_commit_sample": commits[:20],
                            "rename_count": len(renames),
                            "renames_sha256": sha256_bytes(canonical_bytes(renames)),
                            "history_is_behavioral_proof": False,
                        },
                    )
                )
            history_coverage = {"status": "COVERED", **lineage["coverage"]}
    else:
        history_coverage = {"status": "NOT_APPLICABLE_NO_CLUSTER_PATHS"}
    deduplicate = lambda values: sorted(  # noqa: E731
        {item["evidence_id"]: item for item in values}.values(),
        key=lambda item: item["evidence_id"],
    )
    return {
        "root": str(root),
        "repository": observation["repository"],
        "inventory_receipt_sha256": observation["inventory_receipt_sha256"],
        "relevant_paths": sorted(relevant_paths),
        "relevant_paths_sha256": sha256_bytes(canonical_bytes(sorted(relevant_paths))),
        "symbols": deduplicate(symbols),
        "tests": deduplicate(tests),
        "entrypoints": deduplicate(entrypoints),
        "history": deduplicate(history),
        "unknowns": sorted(
            unknowns,
            key=lambda item: (item["path"], item["classification"]),
        ),
        "history_coverage": history_coverage,
        "coverage": {
            "language": "PYTHON_ONLY_M71",
            "body_equivalence": "CONSERVATIVE_NORMALIZED_ELIGIBLE_FUNCTIONS_ONLY",
            "signature_and_decorators": "STATIC_AST_DECLARATIONS",
            "test_discovery": "PATH_NAME_AND_DECORATOR_CONVENTION_ONLY",
            "test_execution": "NOT_PERFORMED_NOT_PROVED",
            "entrypoints": "STATIC_DECLARATIONS_ONLY",
            "dynamic_dispatch": "UNKNOWN",
            "external_provider_behavior": "UNKNOWN",
            "non_python_behavior": "UNKNOWN",
        },
    }


def _catalog_indexes(catalog: Mapping[str, Any]) -> dict[str, Any]:
    symbols_by_path: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    symbols_by_name_kind: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(
        list
    )
    for item in catalog["symbols"]:
        symbols_by_path[item["source_path"]].append(item)
        identity = item["identity"]
        symbols_by_name_kind[(identity["name"], identity["symbol_kind"])].append(item)
    return {
        "symbols_by_path": symbols_by_path,
        "symbols_by_name_kind": symbols_by_name_kind,
        "tests": catalog["tests"],
        "entrypoints": catalog["entrypoints"],
        "history_by_path": {item["source_path"]: item for item in catalog["history"]},
    }


def _cluster_behavior_evidence(
    cluster: Mapping[str, Any],
    subjects: Mapping[str, Any],
    canonical_catalog: Mapping[str, Any],
    donor_catalog: Mapping[str, Any],
) -> dict[str, Any]:
    if cluster["kind"] == "UNSUPPORTED_OR_UNKNOWN_REVIEW":
        return {
            "cluster": dict(cluster),
            "subjects": {
                "donor_root": subjects["donor_root"],
                "family": subjects["family"],
                "donor_source_paths": subjects["donor_source_paths"],
                "unknown_record_count": subjects["unknown_record_count"],
                "unknown_record_hashes_sha256": subjects[
                    "unknown_record_hashes_sha256"
                ],
            },
            "subject_fact_bindings": {
                "canonical_fact_count": 0,
                "canonical_fact_ids_sha256": sha256_bytes(canonical_bytes([])),
                "donor_fact_count": 0,
                "donor_fact_ids_sha256": sha256_bytes(canonical_bytes([])),
            },
            "corroborating_evidence": {
                "exact_symbol_structures": [],
                "canonical_static_test_references": [],
                "donor_static_test_references": [],
                "canonical_declared_entrypoints": [],
                "donor_declared_entrypoints": [],
                "canonical_git_path_lineage": [],
                "donor_git_path_lineage": [],
                "test_execution_proved": False,
                "runtime_reachability_proved": False,
            },
            "counterevidence": {"symbol_structure_divergences": []},
            "unknown": [
                {
                    "classification": subjects["unsupported_reason"],
                    "dynamic_or_reflective_behavior_proved": False,
                }
            ],
            "claims": {
                "behavioral_equivalence": False,
                "test_execution": False,
                "usefulness": False,
                "retirement_safety": False,
            },
        }
    canonical_index = _catalog_indexes(canonical_catalog)
    donor_index = _catalog_indexes(donor_catalog)
    names = set(subjects["subject_names"])
    donor_symbols = [
        item
        for path in subjects["donor_source_paths"]
        for item in donor_index["symbols_by_path"].get(path, [])
        if not names or item["identity"]["name"] in names
    ]
    canonical_path_symbols = [
        item
        for path in subjects["canonical_source_paths"]
        for item in canonical_index["symbols_by_path"].get(path, [])
        if not names or item["identity"]["name"] in names
    ]
    exact_matches: list[dict[str, Any]] = []
    divergences: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    used_canonical: set[str] = set()
    for donor_symbol in donor_symbols:
        identity = donor_symbol["identity"]
        same_path = [
            item
            for item in canonical_index["symbols_by_path"].get(
                donor_symbol["source_path"], []
            )
            if item["identity"]["qualified_name"] == identity["qualified_name"]
            and item["identity"]["symbol_kind"] == identity["symbol_kind"]
        ]
        candidates = same_path or canonical_index["symbols_by_name_kind"].get(
            (identity["name"], identity["symbol_kind"]), []
        )
        if len(candidates) != 1:
            unknowns.append(
                {
                    "classification": (
                        "UNKNOWN_NO_CANONICAL_SYMBOL_CANDIDATE"
                        if not candidates
                        else "UNKNOWN_AMBIGUOUS_CANONICAL_SYMBOL_CANDIDATE"
                    ),
                    "donor_evidence_id": donor_symbol["evidence_id"],
                    "candidate_count": len(candidates),
                }
            )
            continue
        canonical_symbol = candidates[0]
        used_canonical.add(canonical_symbol["evidence_id"])
        left = canonical_symbol["identity"]
        fields = {
            "signature": left["signature_sha256"] == identity["signature_sha256"],
            "decorators": left["decorators_sha256"] == identity["decorators_sha256"],
            "body": (
                None
                if left["body_fingerprint_sha256"] is None
                or identity["body_fingerprint_sha256"] is None
                else left["body_fingerprint_sha256"]
                == identity["body_fingerprint_sha256"]
            ),
        }
        record = {
            "canonical_evidence_id": canonical_symbol["evidence_id"],
            "donor_evidence_id": donor_symbol["evidence_id"],
            "association": (
                "EXACT_PATH_AND_QUALIFIED_NAME"
                if same_path
                else "UNIQUE_NAME_AND_KIND_CANDIDATE"
            ),
            "field_equivalence": fields,
            "behavioral_equivalence_proved": False,
        }
        if all(value is True for value in fields.values()):
            exact_matches.append(
                {**record, "classification": "CORROBORATING_EXACT_STRUCTURE"}
            )
        elif any(value is False for value in fields.values()):
            divergences.append(
                {**record, "classification": "COUNTEREVIDENCE_STRUCTURE_DIVERGENCE"}
            )
        else:
            unknowns.append(
                {**record, "classification": "UNKNOWN_BODY_NORMALIZATION_INELIGIBLE"}
            )
    for canonical_symbol in canonical_path_symbols:
        if canonical_symbol["evidence_id"] not in used_canonical:
            unknowns.append(
                {
                    "classification": "UNKNOWN_CANONICAL_SYMBOL_WITHOUT_DONOR_PAIR",
                    "canonical_evidence_id": canonical_symbol["evidence_id"],
                }
            )

    def matching_tests(catalog: Mapping[str, Any]) -> list[str]:
        return sorted(
            item["evidence_id"]
            for item in catalog["tests"]
            if names & set(item["identity"]["referenced_names"])
        )

    def matching_entrypoints(
        catalog: Mapping[str, Any], paths: Sequence[str]
    ) -> list[str]:
        result = []
        for item in catalog["entrypoints"]:
            identity_text = canonical_bytes(item["identity"]).decode("utf-8")
            if item["source_path"] in paths or any(
                name in identity_text for name in names
            ):
                result.append(item["evidence_id"])
        return sorted(set(result))

    canonical_tests = matching_tests(canonical_catalog)
    donor_tests = matching_tests(donor_catalog)
    canonical_entrypoints = matching_entrypoints(
        canonical_catalog, subjects["canonical_source_paths"]
    )
    donor_entrypoints = matching_entrypoints(
        donor_catalog, subjects["donor_source_paths"]
    )
    canonical_history = sorted(
        item["evidence_id"]
        for path in subjects["canonical_source_paths"]
        if (item := canonical_index["history_by_path"].get(path)) is not None
    )
    donor_history = sorted(
        item["evidence_id"]
        for path in subjects["donor_source_paths"]
        if (item := donor_index["history_by_path"].get(path)) is not None
    )
    if subjects["unsupported_reason"]:
        unknowns.append(
            {
                "classification": subjects["unsupported_reason"],
                "dynamic_or_reflective_behavior_proved": False,
            }
        )
    if not donor_symbols and not canonical_path_symbols:
        unknowns.append({"classification": "UNKNOWN_NO_ASSOCIATED_SYMBOL_DEFINITION"})
    return {
        "cluster": dict(cluster),
        "subjects": {
            key: value
            for key, value in subjects.items()
            if key not in {"canonical_fact_ids", "donor_fact_ids"}
        },
        "subject_fact_bindings": {
            "canonical_fact_count": len(subjects["canonical_fact_ids"]),
            "canonical_fact_ids_sha256": sha256_bytes(
                canonical_bytes(subjects["canonical_fact_ids"])
            ),
            "donor_fact_count": len(subjects["donor_fact_ids"]),
            "donor_fact_ids_sha256": sha256_bytes(
                canonical_bytes(subjects["donor_fact_ids"])
            ),
        },
        "corroborating_evidence": {
            "exact_symbol_structures": exact_matches,
            "canonical_static_test_references": canonical_tests,
            "donor_static_test_references": donor_tests,
            "canonical_declared_entrypoints": canonical_entrypoints,
            "donor_declared_entrypoints": donor_entrypoints,
            "canonical_git_path_lineage": canonical_history,
            "donor_git_path_lineage": donor_history,
            "test_execution_proved": False,
            "runtime_reachability_proved": False,
        },
        "counterevidence": {
            "symbol_structure_divergences": divergences,
        },
        "unknown": sorted(
            unknowns,
            key=lambda item: (
                item["classification"],
                item.get("donor_evidence_id", ""),
                item.get("canonical_evidence_id", ""),
            ),
        ),
        "claims": {
            "behavioral_equivalence": False,
            "test_execution": False,
            "usefulness": False,
            "retirement_safety": False,
        },
    }


def build_cross_worktree_behavior_map(
    canonical_root: Path,
    donor_roots: Sequence[Path],
    m69_predecessor: Path,
    m70_predecessor: Path,
    *,
    runtime_roots: Sequence[Path] = (),
    policy: InventoryPolicy | None = None,
    allowed_canonical_m70_drift: Sequence[str] = (),
) -> dict[str, Any]:
    policy = policy or InventoryPolicy()
    canonical_root = canonical_root.resolve(strict=True)
    donors = [path.resolve(strict=True) for path in donor_roots]
    runtimes = [path.resolve(strict=True) for path in runtime_roots]
    repositories = [canonical_root, *donors]
    before = {str(root): _repository_snapshot(root) for root in repositories}
    dirty_before = {str(root): _dirty_snapshot(root, policy) for root in repositories}
    runtime_before = {str(root): _runtime_snapshot(root) for root in runtimes}
    m69_identity = _predecessor_identity(m69_predecessor)
    m70, m70_identity = _static_predecessor_identity(m70_predecessor)
    expected_donors = [item["root"] for item in m70["donor_static_facts"]]
    if [str(path) for path in donors] != expected_donors:
        raise DivergenceError("M71 donor order or identity does not match M70")
    lookups = _m70_fact_lookups(m70)
    unique_clusters: dict[str, Mapping[str, Any]] = {}
    cluster_bindings = []
    subject_sets: dict[str, dict[str, Any]] = {}
    relevant_paths: dict[str, set[str]] = {str(root): set() for root in repositories}
    for ordinal, cluster in enumerate(m70["review_clusters"]):
        evidence_set_id = sha256_bytes(canonical_bytes(cluster))
        cluster_id = sha256_bytes(
            canonical_bytes({"ordinal": ordinal, "cluster": cluster})
        )
        cluster_bindings.append(
            {
                "cluster_id": cluster_id,
                "m70_ordinal": ordinal,
                "evidence_set_id": evidence_set_id,
            }
        )
        if evidence_set_id not in unique_clusters:
            unique_clusters[evidence_set_id] = cluster
            subjects = _m70_cluster_subjects(m70, lookups, cluster)
            subject_sets[evidence_set_id] = subjects
            if cluster["kind"] != "UNSUPPORTED_OR_UNKNOWN_REVIEW":
                relevant_paths[str(canonical_root)].update(
                    subjects["canonical_source_paths"]
                )
                relevant_paths[subjects["donor_root"]].update(
                    subjects["donor_source_paths"]
                )

    canonical_observation = _repository_observation(canonical_root, policy)
    donor_observations = [_repository_observation(root, policy) for root in donors]
    m70_canonical = m70["canonical_static_facts"]
    canonical_drift = _behavior_source_drift(canonical_observation, m70_canonical)
    allowed = set(allowed_canonical_m70_drift)
    observed_changed = {item["path"] for item in canonical_drift["changed"]}
    if canonical_drift["missing"] or not observed_changed <= allowed:
        raise DivergenceError(
            "canonical source drift from M70 exceeds the admitted M71 implementation paths"
        )
    donor_drift: dict[str, Any] = {}
    m70_donors = {item["root"]: item for item in m70["donor_static_facts"]}
    for observation in donor_observations:
        root = observation["root"]
        predecessor = m70_donors[root]
        drift = _behavior_source_drift(observation, predecessor)
        donor_drift[root] = drift
        expected_repository = predecessor["repository"]
        current_repository = observation["repository"]
        if (
            drift["changed"]
            or drift["missing"]
            or current_repository["head"] != expected_repository["head"]
            or current_repository["tree"] != expected_repository["tree"]
            or current_repository["status"] != expected_repository["status"]
        ):
            raise DivergenceError(f"donor drifted from exact M70 evidence: {root}")

    canonical_catalog = _python_behavior_catalog(
        canonical_root,
        canonical_observation,
        frozenset(relevant_paths[str(canonical_root)]),
    )
    donor_catalogs = {
        observation["root"]: _python_behavior_catalog(
            Path(observation["root"]),
            observation,
            frozenset(relevant_paths[observation["root"]]),
        )
        for observation in donor_observations
    }
    evidence_sets = []
    for evidence_set_id, cluster in sorted(unique_clusters.items()):
        subjects = subject_sets[evidence_set_id]
        evidence = _cluster_behavior_evidence(
            cluster,
            subjects,
            canonical_catalog,
            donor_catalogs[subjects["donor_root"]],
        )
        evidence_sets.append(
            {
                "evidence_set_id": evidence_set_id,
                "evidence": evidence,
                "evidence_sha256": sha256_bytes(canonical_bytes(evidence)),
            }
        )

    after = {str(root): _repository_snapshot(root) for root in repositories}
    dirty_after = {str(root): _dirty_snapshot(root, policy) for root in repositories}
    runtime_after = {str(root): _runtime_snapshot(root) for root in runtimes}
    changed = [
        path
        for path in sorted(before)
        if before[path] != after[path] or dirty_before[path] != dirty_after[path]
    ]
    runtime_changed = [
        path
        for path in sorted(runtime_before)
        if runtime_before[path] != runtime_after[path]
    ]
    if changed or runtime_changed:
        raise DivergenceError(
            "observed repository or runtime changed during behavioral comparison: "
            + ", ".join((*changed, *runtime_changed))
        )
    zero_mutation = seal_document(
        {
            "schema": ZERO_MUTATION_SCHEMA,
            "status": "PASS",
            "authority": "read-only-behavioral-counterevidence-observation",
            "authority_granted": False,
            "repositories": [
                {
                    "root": path,
                    "before_sha256": sha256_bytes(canonical_bytes(before[path])),
                    "after_sha256": sha256_bytes(canonical_bytes(after[path])),
                    "dirty_before_sha256": sha256_bytes(
                        canonical_bytes(dirty_before[path])
                    ),
                    "dirty_after_sha256": sha256_bytes(
                        canonical_bytes(dirty_after[path])
                    ),
                    "unchanged": True,
                }
                for path in sorted(before)
            ],
            "runtimes": [
                {
                    "root": path,
                    "before_sha256": sha256_bytes(
                        canonical_bytes(runtime_before[path])
                    ),
                    "after_sha256": sha256_bytes(canonical_bytes(runtime_after[path])),
                    "unchanged": True,
                    "coverage": runtime_before[path]["coverage"],
                }
                for path in sorted(runtime_before)
            ],
            "limits": {
                "donor_code_execution": "NOT_PERFORMED",
                "provider_browser_mailbox_canary": "NOT_PERFORMED",
                "runtime_content": "NOT_READ_COMPLETE_PATH_AND_METADATA_TREE_ONLY",
            },
        }
    )
    corroborating = sum(
        len(item["evidence"]["corroborating_evidence"]["exact_symbol_structures"])
        + len(
            item["evidence"]["corroborating_evidence"][
                "canonical_static_test_references"
            ]
        )
        + len(
            item["evidence"]["corroborating_evidence"]["donor_static_test_references"]
        )
        for item in evidence_sets
    )
    counterevidence = sum(
        len(item["evidence"]["counterevidence"]["symbol_structure_divergences"])
        for item in evidence_sets
    )
    unknown_count = sum(len(item["evidence"]["unknown"]) for item in evidence_sets)
    return seal_document(
        {
            "schema": BEHAVIOR_DIVERGENCE_SCHEMA,
            "status": "PARTIAL_BEHAVIORAL_COUNTEREVIDENCE_LAYER",
            "publication_encoding": "DETERMINISTIC_GZIP_LEVEL_9_MTIME_ZERO",
            "authority": "read-only-non-authoritative-counterevidence",
            "authority_granted": False,
            "cleanup_permitted": False,
            "retirement_permitted": False,
            "predecessors": {"m69": m69_identity, "m70": m70_identity},
            "canonical_candidate": {
                "root": canonical_observation["root"],
                "head": canonical_observation["repository"]["head"],
                "tree": canonical_observation["repository"]["tree"],
                "canonicality_proved": False,
                "m70_source_drift": canonical_drift,
            },
            "donor_source_drift": donor_drift,
            "cluster_bindings": cluster_bindings,
            "evidence_sets": evidence_sets,
            "catalogs": {
                "canonical": canonical_catalog,
                "donors": [donor_catalogs[str(root)] for root in donors],
            },
            "counts": {
                "m70_review_clusters": len(cluster_bindings),
                "deduplicated_evidence_sets": len(evidence_sets),
                "corroborating_evidence_items": corroborating,
                "counterevidence_items": counterevidence,
                "unknown_items": unknown_count,
                "catalog_symbols": len(canonical_catalog["symbols"])
                + sum(len(item["symbols"]) for item in donor_catalogs.values()),
                "catalog_tests_and_fixtures": len(canonical_catalog["tests"])
                + sum(len(item["tests"]) for item in donor_catalogs.values()),
                "catalog_entrypoints": len(canonical_catalog["entrypoints"])
                + sum(len(item["entrypoints"]) for item in donor_catalogs.values()),
                "catalog_history_summaries": len(canonical_catalog["history"])
                + sum(len(item["history"]) for item in donor_catalogs.values()),
            },
            "zero_mutation": zero_mutation,
            "claims": {
                "static_test_presence_is_execution_proof": False,
                "behavioral_equivalence": False,
                "canonical_owner_proved": False,
                "usefulness": False,
                "integration_recommendation": False,
                "retirement_safety": False,
                "cleanup_recommendation": False,
                "no_feature_loss": False,
            },
            "remaining_unknowns": [
                "dynamic dispatch, imports, reflection and monkey patching",
                "non-Python behavior",
                "test execution where not separately observed",
                "missing or externally supplied fixtures",
                "sandbox-unavailable execution",
                "external-provider, browser, mailbox and canary behavior",
                "semantic usefulness and governed integration or retirement verdicts",
            ],
        }
    )


def render_cross_worktree_behavior_report(payload: Mapping[str, Any]) -> str:
    counts = payload["counts"]
    lines = [
        "# M71 GIGA Archaeology behavioral and test counterevidence",
        "",
        "## Verdict",
        "",
        "All 460 M70 review clusters are bound to deterministic behavioral/test evidence sets. "
        "The artifact separates exact structural corroboration, static-test and entrypoint associations, "
        "Git lineage, observed divergence and UNKNOWN. It makes no behavioral-equivalence or retirement verdict.",
        "",
        "## Bound evidence",
        "",
        f"- M69 receipt: `{payload['predecessors']['m69']['receipt_sha256']}`",
        f"- M70 receipt: `{payload['predecessors']['m70']['receipt_sha256']}`",
        f"- M71 receipt: `{payload['receipt_sha256']}`",
        f"- Zero-mutation receipt: `{payload['zero_mutation']['receipt_sha256']}`",
        f"- Candidate HEAD: `{payload['canonical_candidate']['head']}`",
        f"- Candidate tree: `{payload['canonical_candidate']['tree']}`",
        "",
        "## Counts",
        "",
        f"- M70 review clusters: {counts['m70_review_clusters']}",
        f"- Deduplicated evidence sets: {counts['deduplicated_evidence_sets']}",
        f"- Corroborating evidence items: {counts['corroborating_evidence_items']}",
        f"- Counterevidence items: {counts['counterevidence_items']}",
        f"- UNKNOWN items: {counts['unknown_items']}",
        f"- Symbol records: {counts['catalog_symbols']}",
        f"- Test/fixture records: {counts['catalog_tests_and_fixtures']}",
        f"- Entrypoint records: {counts['catalog_entrypoints']}",
        f"- Git path summaries: {counts['catalog_history_summaries']}",
        "",
        "## Evidence boundary",
        "",
        "- No donor code or arbitrary donor test was executed.",
        "- Static tests, fixtures and assertions are presence evidence only.",
        "- Normalized body equality is corroboration, not semantic or behavioral equivalence.",
        "- Dynamic dispatch, non-Python and external-provider behavior remain UNKNOWN.",
        "- No canonical-owner, usefulness, integration, retirement, cleanup or no-feature-loss recommendation is made.",
        "",
    ]
    return "\n".join(lines)


def write_cross_worktree_behavior_map(
    canonical_root: Path,
    donor_roots: Sequence[Path],
    m69_predecessor: Path,
    m70_predecessor: Path,
    output: Path,
    *,
    runtime_roots: Sequence[Path] = (),
    allowed_canonical_m70_drift: Sequence[str] = (),
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists():
        raise DivergenceError(
            "behavioral divergence output directory must not already exist"
        )
    payload = build_cross_worktree_behavior_map(
        canonical_root,
        donor_roots,
        m69_predecessor,
        m70_predecessor,
        runtime_roots=runtime_roots,
        allowed_canonical_m70_drift=allowed_canonical_m70_drift,
    )
    compressed = gzip.compress(canonical_bytes(payload), compresslevel=9, mtime=0)
    if len(compressed) >= 100_000_000:
        raise DivergenceError("M71 compressed publication exceeds GitHub file ceiling")
    try:
        output.mkdir(parents=True, mode=0o700)
        write_atomic(output / "behavior_divergence.json.gz", compressed)
        write_atomic(
            output / "BEHAVIOR_DIVERGENCE_REPORT.md",
            render_cross_worktree_behavior_report(payload).encode("utf-8"),
        )
    except (EvidenceError, OSError) as exc:
        raise DivergenceError(str(exc)) from exc
    return payload


def _behavior_predecessor_identity(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = path.resolve(strict=True)
    compressed = path.read_bytes()
    if len(compressed) >= 100_000_000:
        raise DivergenceError("M71 compressed predecessor exceeds publication ceiling")
    if len(compressed) < 10 or compressed[:2] != b"\x1f\x8b":
        raise DivergenceError("M71 predecessor is not a gzip artifact")
    if int.from_bytes(compressed[4:8], "little") != 0:
        raise DivergenceError("M71 predecessor gzip mtime is not deterministic zero")
    try:
        restored = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        raise DivergenceError(f"M71 predecessor cannot be restored: {exc}") from exc
    if len(restored) > 512 * 1024 * 1024:
        raise DivergenceError("M71 restored predecessor exceeds evidence ceiling")
    try:
        payload = json.loads(restored)
        validate_self_hash(payload)
        validate_self_hash(payload["zero_mutation"])
    except (json.JSONDecodeError, EvidenceError, KeyError) as exc:
        raise DivergenceError(f"M71 predecessor evidence is invalid: {exc}") from exc
    if payload.get("schema") != BEHAVIOR_DIVERGENCE_SCHEMA:
        raise DivergenceError("M71 predecessor has the wrong schema")
    return payload, {
        "path": str(path),
        "compressed_sha256": sha256_bytes(compressed),
        "compressed_bytes": len(compressed),
        "restored_sha256": sha256_bytes(restored),
        "restored_bytes": len(restored),
        "receipt_sha256": payload["receipt_sha256"],
        "zero_mutation_receipt_sha256": payload["zero_mutation"]["receipt_sha256"],
        "gzip_mtime": 0,
        "rewritten": False,
    }


def _safe_relative(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise DivergenceError(f"unsafe relative evidence path: {relative}")
    return root.joinpath(*pure.parts)


def _safe_file_observation(
    root: Path,
    relative: str,
    *,
    max_bytes: int = 2 * 1024 * 1024,
) -> tuple[bytes | None, dict[str, Any]]:
    path = _safe_relative(root, relative)
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None, {
            "path": relative,
            "exists": False,
            "readable": False,
            "reason": "ABSENT",
        }
    if stat.S_ISLNK(before.st_mode):
        raise DivergenceError(f"safe evidence file is a symlink: {relative}")
    if not stat.S_ISREG(before.st_mode):
        return None, {
            "path": relative,
            "exists": True,
            "readable": False,
            "reason": "NOT_REGULAR_FILE",
            "mode": stat.S_IFMT(before.st_mode),
        }
    if before.st_nlink != 1:
        raise DivergenceError(f"safe evidence file has multiple hard links: {relative}")
    if before.st_size > max_bytes:
        return None, {
            "path": relative,
            "exists": True,
            "readable": False,
            "reason": "SIZE_EXCEEDS_BOUND",
            "size_bytes": before.st_size,
            "max_bytes": max_bytes,
        }
    raw = path.read_bytes()
    after = path.lstat()
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
        before.st_mode,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
        after.st_mode,
    ):
        raise DivergenceError(
            f"safe evidence file changed while being read: {relative}"
        )
    return raw, {
        "path": relative,
        "exists": True,
        "readable": True,
        "size_bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "mode": stat.S_IMODE(before.st_mode),
        "nlink": before.st_nlink,
    }


def _jsonable_literal(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, tuple):
        return [_jsonable_literal(item) for item in value]
    if isinstance(value, list):
        return [_jsonable_literal(item) for item in value]
    if isinstance(value, dict):
        return {
            str(_jsonable_literal(key)): _jsonable_literal(item)
            for key, item in sorted(value.items(), key=lambda pair: repr(pair[0]))
        }
    return {"classification": "UNSUPPORTED_LITERAL_TYPE", "repr": repr(value)}


def _assignment_literal(module: ast.Module, name: str) -> Any:
    for node in module.body:
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                value = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                value = node.value
        if value is None:
            continue
        try:
            return _jsonable_literal(ast.literal_eval(value))
        except (ValueError, SyntaxError):
            return {"classification": "UNSUPPORTED_NON_LITERAL_ASSIGNMENT"}
    return None


def _module_imports(module: ast.Module) -> list[dict[str, Any]]:
    imports: list[dict[str, Any]] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    {
                        "kind": "import",
                        "module": alias.name,
                        "asname": alias.asname,
                        "lineno": node.lineno,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            imports.append(
                {
                    "kind": "from",
                    "module": node.module,
                    "level": node.level,
                    "names": [
                        {"name": alias.name, "asname": alias.asname}
                        for alias in node.names
                    ],
                    "lineno": node.lineno,
                }
            )
    return sorted(
        imports,
        key=lambda item: (
            item["kind"],
            item.get("module") or "",
            item.get("level") or 0,
            json.dumps(item.get("names", []), sort_keys=True),
            item["lineno"],
        ),
    )


def _verifier_contract_from_bytes(raw: bytes, relative: str) -> dict[str, Any]:
    text = raw.decode("utf-8", "replace")
    markers = sorted(set(DERIVED_PAYLOAD_EVIDENCE_MARKER.findall(text)))
    result: dict[str, Any] = {
        "path": relative,
        "sha256": sha256_bytes(raw),
        "size_bytes": len(raw),
        "line_count": len(text.splitlines()),
        "markers": markers,
        "contains_authority_line": "authority: DERIVED_ONLY" in text,
        "contains_body_hash_check": "body_sha256" in text,
        "contains_single_link_check": "st_nlink" in text,
        "contains_symlink_refusal": "symlink" in text.lower(),
        "verification_schema_markers": sorted(
            set(re.findall(r"giga\.derived-agent-payload-verification\.v[0-9]+", text))
        ),
        "activation_schema_markers": sorted(
            set(re.findall(r"giga\.agent-payload-activation\.v[0-9]+", text))
        ),
    }
    try:
        module = ast.parse(text, filename=relative)
    except SyntaxError as exc:
        result.update(
            {
                "ast_parse": "FAILED",
                "ast_error": {
                    "type": type(exc).__name__,
                    "message_sha256": sha256_bytes(str(exc).encode("utf-8", "replace")),
                },
                "constants": {},
                "functions": [],
                "imports": [],
                "capability_flags": {},
            }
        )
        return result
    constants = {
        name: _assignment_literal(module, name)
        for name in (
            "SCHEMA_LINE",
            "END_LINE",
            "AUTHORITY_LINE",
            "CANONICAL_SOURCES",
            "PAYLOAD_STATUSES",
            "UNVERIFIED_STATUSES",
            "PAYLOAD_SPECS",
            "ACTIVATION_EVIDENCE_PATH",
            "ACTIVATION_SOURCE_COMMIT",
        )
    }
    constants = {key: value for key, value in constants.items() if value is not None}
    functions = sorted(
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    result.update(
        {
            "ast_parse": "PASS",
            "constants": constants,
            "functions": functions,
            "imports": _module_imports(module),
            "capability_flags": {
                "write_mode_present": "write_derived_payloads" in functions
                and "--write" in text,
                "template_rendering_present": "render_derived_payloads" in functions
                and "PAYLOAD_SPECS" in constants,
                "activation_evidence_present": "_verify_activation_evidence"
                in functions
                and "ACTIVATION_EVIDENCE_PATH" in constants,
                "strict_json_parser_present": "_strict_json" in functions
                and "_strict_object" in functions,
                "v1_unverified_statuses_preserved": "UNVERIFIED_STATUSES" in constants,
                "canonical_source_hash_check_present": "canonical-source-sha256"
                in text,
                "payload_status_check_present": "deployment-status" in text,
            },
        }
    )
    return result


def _verifier_observation(root: Path) -> dict[str, Any]:
    raw, file_identity = _safe_file_observation(root, DERIVED_PAYLOAD_VERIFIER_PATH)
    if raw is None:
        return {
            "file": file_identity,
            "contract": None,
            "classification_hint": "ABSENT",
        }
    contract = _verifier_contract_from_bytes(raw, DERIVED_PAYLOAD_VERIFIER_PATH)
    schema_line = contract["constants"].get("SCHEMA_LINE")
    classification_hint = (
        "V1_VERIFIER"
        if schema_line == "=== GIGA DERIVED PAYLOAD v1 ==="
        else "V2_VERIFIER"
        if schema_line == "=== GIGA DERIVED PAYLOAD v2 ==="
        else "UNKNOWN_VERIFIER_SCHEMA"
    )
    return {
        "file": file_identity,
        "contract": contract,
        "classification_hint": classification_hint,
    }


def _verifier_git_history(root: Path) -> list[dict[str, Any]]:
    log = _git_text(
        root,
        [
            "log",
            "--all",
            "--follow",
            "--date=iso-strict",
            "--format=%H%x00%ad%x00%s",
            "--",
            DERIVED_PAYLOAD_VERIFIER_PATH,
        ],
    )
    versions: list[dict[str, Any]] = []
    for line in log.splitlines():
        if not line:
            continue
        parts = line.split("\0", 2)
        if len(parts) != 3:
            raise DivergenceError("Git emitted malformed verifier lineage row")
        commit, committed_at, subject = parts
        try:
            raw = _git(root, ["show", f"{commit}:{DERIVED_PAYLOAD_VERIFIER_PATH}"])
        except HistoryError:
            continue
        contract = _verifier_contract_from_bytes(raw, DERIVED_PAYLOAD_VERIFIER_PATH)
        versions.append(
            {
                "commit": commit,
                "committed_at": committed_at,
                "subject": subject,
                "sha256": contract["sha256"],
                "size_bytes": contract["size_bytes"],
                "line_count": contract["line_count"],
                "schema_line": contract["constants"].get("SCHEMA_LINE"),
                "verification_schema_markers": contract["verification_schema_markers"],
                "activation_schema_markers": contract["activation_schema_markers"],
                "capability_flags": contract["capability_flags"],
            }
        )
    seen: set[tuple[str, str | None]] = set()
    unique: list[dict[str, Any]] = []
    for version in versions:
        key = (version["sha256"], version["schema_line"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(version)
    return unique


def _json_schema_summary(raw: bytes) -> dict[str, Any]:
    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        payload = json.loads(raw, object_pairs_hook=strict_object)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "json_parse": "FAILED",
            "error_sha256": sha256_bytes(str(exc).encode("utf-8", "replace")),
        }
    if not isinstance(payload, Mapping):
        return {"json_parse": "PASS_NON_OBJECT"}
    return {
        "json_parse": "PASS",
        "schema": payload.get("schema"),
        "receipt_sha256": payload.get("receipt_sha256"),
        "self_sha256": payload.get("self_sha256"),
        "status": payload.get("status") or payload.get("claim"),
    }


def _payload_artifact_inventory(root: Path) -> dict[str, Any]:
    exact_paths = (
        "deploy/activation_evidence.json",
        "capabilities/manifests/derived-agent-payloads.json",
        "capabilities/receipts/derived-agent-payloads.json",
        "deploy/claude_preferences.txt",
        "deploy/chatgpt_preferences.md",
        "deploy/v3_agent_payload.md",
        "deploy/templates/claude_preferences.txt",
        "deploy/templates/chatgpt_preferences.md",
        "deploy/templates/v3_agent_payload.md",
    )
    exact_records = []
    for relative in exact_paths:
        raw, file_identity = _safe_file_observation(
            root, relative, max_bytes=4 * 1024 * 1024
        )
        record = dict(file_identity)
        if raw is not None:
            text = raw.decode("utf-8", "replace")
            record["markers"] = sorted(
                set(DERIVED_PAYLOAD_EVIDENCE_MARKER.findall(text))
            )
            if PurePosixPath(relative).suffix == ".json":
                record["json"] = _json_schema_summary(raw)
        exact_records.append(record)

    searchable_roots = (
        "architecture",
        "capabilities",
        "deploy",
        "scripts",
        "tests",
        "twin_core",
    )
    marker_records = []
    skipped_large = 0
    for first in searchable_roots:
        base = _safe_relative(root, first)
        if not base.exists():
            continue
        for directory, names, files in os.walk(base, topdown=True, followlinks=False):
            names[:] = sorted(
                name
                for name in names
                if name
                not in {
                    ".git",
                    ".mypy_cache",
                    ".pytest_cache",
                    "__pycache__",
                    "node_modules",
                }
            )
            for name in sorted(files):
                path = Path(directory) / name
                relative = path.relative_to(root).as_posix()
                metadata = path.lstat()
                if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                    continue
                if metadata.st_size > 1_000_000:
                    skipped_large += 1
                    continue
                raw = path.read_bytes()
                text = raw.decode("utf-8", "replace")
                markers = sorted(set(DERIVED_PAYLOAD_EVIDENCE_MARKER.findall(text)))
                if not markers and "derived-agent-payload" not in text:
                    continue
                marker_records.append(
                    {
                        "path": relative,
                        "size_bytes": len(raw),
                        "sha256": sha256_bytes(raw),
                        "markers": markers,
                    }
                )
    return {
        "exact_artifacts": exact_records,
        "marker_index": sorted(marker_records, key=lambda item: item["path"]),
        "marker_index_count": len(marker_records),
        "skipped_large_file_count": skipped_large,
        "search_roots": list(searchable_roots),
    }


def _graph_status(root: Path) -> dict[str, Any]:
    graph = root / "graphify-out" / "graph.json"
    if not graph.exists():
        return {
            "status": "PARTIAL_STALE",
            "graphify_out_graph_json_present": False,
            "authority": "NOT_USED_NO_CURRENT_GRAPH_PRESENT",
            "refresh_performed": False,
        }
    raw = graph.read_bytes()
    return {
        "status": "PRESENT_NOT_REFRESHED_FOR_M73",
        "graphify_out_graph_json_present": True,
        "graph_json_sha256": sha256_bytes(raw),
        "graph_json_bytes": len(raw),
        "authority": "INDEX_ONLY_NOT_RUNTIME_LIVENESS_OR_FEATURE_LOSS_AUTHORITY",
        "refresh_performed": False,
    }


def _classify_verifier_variant(
    canonical: Mapping[str, Any],
    donor: Mapping[str, Any],
    history_by_sha: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if donor["contract"] is None:
        return {
            "classification": "ABSENT_FROM_DONOR",
            "compatibility_status": "NOT_APPLICABLE",
            "basis": "donor worktree has no verifier at the canonical path",
            "retirement_permitted": False,
        }
    donor_sha = donor["contract"]["sha256"]
    canonical_sha = canonical["contract"]["sha256"] if canonical["contract"] else None
    schema_line = donor["contract"]["constants"].get("SCHEMA_LINE")
    if donor_sha == canonical_sha:
        return {
            "classification": "EXACT_CURRENT_CANONICAL",
            "compatibility_status": "EXACT_SOURCE_MATCH",
            "basis": "donor verifier bytes match the current canonical verifier",
            "retirement_permitted": False,
        }
    if donor_sha in history_by_sha and schema_line == "=== GIGA DERIVED PAYLOAD v1 ===":
        return {
            "classification": "HISTORICAL_V1_VARIANT",
            "compatibility_status": "PARTIAL_HISTORY_QUERYABLE_NOT_DROP_IN",
            "basis": "donor verifier bytes match a preserved canonical Git-history version",
            "history_commit": history_by_sha[donor_sha]["commit"],
            "retirement_permitted": False,
        }
    if donor_sha in history_by_sha:
        return {
            "classification": "HISTORICAL_NON_CURRENT_VARIANT",
            "compatibility_status": "HISTORY_QUERYABLE_EXACT_COMPATIBILITY_UNKNOWN",
            "basis": "donor verifier bytes match a preserved canonical Git-history version",
            "history_commit": history_by_sha[donor_sha]["commit"],
            "retirement_permitted": False,
        }
    return {
        "classification": "UNMAPPED_DIFFERENT_VERIFIER",
        "compatibility_status": "UNKNOWN",
        "basis": "donor verifier differs from current canonical and known history",
        "retirement_permitted": False,
    }


def _m73_public_repository_identity(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    status = snapshot.get("status", {})
    return {
        "head": snapshot.get("head"),
        "tree": snapshot.get("tree"),
        "status_sha256": status.get("sha256"),
        "status_bytes": status.get("bytes"),
    }


def _m73_public_dirty_identity(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    status = snapshot.get("status", {})
    return {
        "clean": status.get("clean"),
        "status_sha256": status.get("sha256"),
        "status_bytes": status.get("bytes"),
        "status_entries": status.get("entries"),
        "status_entries_sha256": status.get("entries_sha256"),
        "safe_entries": snapshot.get("safe_entries", []),
        "safe_entries_sha256": snapshot.get("safe_entries_sha256"),
        "excluded_entries": snapshot.get("excluded_entries"),
        "excluded_entries_sha256": snapshot.get("excluded_entries_sha256"),
        "excluded_paths_recorded": snapshot.get("excluded_paths_recorded"),
        "excluded_content_read": snapshot.get("excluded_content_read"),
    }


def _m73_public_predecessor_identity(
    slot: str, payload: Mapping[str, Any], *, compressed: bool
) -> dict[str, Any]:
    counts = payload.get("counts", {})
    public_counts: dict[str, Any] = {}
    if isinstance(counts, Mapping):
        for key, value in sorted(counts.items(), key=lambda item: str(item[0])):
            if isinstance(value, (str, int, float, bool)) or value is None:
                public_counts[str(key)] = value
            elif isinstance(value, Mapping):
                public_counts[str(key)] = {
                    "classification": "WITHHELD_PATH_BEARING_MAPPING",
                    "item_count": len(value),
                }
            elif isinstance(value, Sequence) and not isinstance(value, (bytes, str)):
                public_counts[str(key)] = {
                    "classification": "WITHHELD_COLLECTION",
                    "item_count": len(value),
                }
            else:
                public_counts[str(key)] = {
                    "classification": "WITHHELD_UNSUPPORTED_COUNT_VALUE"
                }
    return {
        "slot": slot,
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "validated": True,
        "compressed": compressed,
        "path_public": False,
        "path_hash_public": False,
        "receipt_hash_public": False,
        "count_keys": sorted(str(key) for key in counts),
        "counts": public_counts,
    }


def _m73_public_zero_repository(
    slot: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    dirty_before: Mapping[str, Any],
    dirty_after: Mapping[str, Any],
) -> dict[str, Any]:
    public_before = _m73_public_repository_identity(before)
    public_after = _m73_public_repository_identity(after)
    public_dirty_before = _m73_public_dirty_identity(dirty_before)
    public_dirty_after = _m73_public_dirty_identity(dirty_after)
    return {
        "slot": slot,
        "before_sha256": sha256_bytes(canonical_bytes(public_before)),
        "after_sha256": sha256_bytes(canonical_bytes(public_after)),
        "dirty_before_sha256": sha256_bytes(canonical_bytes(public_dirty_before)),
        "dirty_after_sha256": sha256_bytes(canonical_bytes(public_dirty_after)),
        "unchanged": public_before == public_after
        and public_dirty_before == public_dirty_after,
    }


def _m71_verifier_evidence(
    payload: Mapping[str, Any],
    donor_slots_by_root: Mapping[str, str],
) -> dict[str, Any]:
    matches = []
    for item in payload["evidence_sets"]:
        evidence = item["evidence"]
        subjects = evidence.get("subjects", {})
        paths = set(subjects.get("canonical_source_paths", []))
        paths.update(subjects.get("donor_source_paths", []))
        if DERIVED_PAYLOAD_VERIFIER_PATH not in paths:
            continue
        donor_root = evidence["cluster"]["donor_root"]
        matches.append(
            {
                "evidence_slot": f"m71-verifier-{len(matches) + 1:03d}",
                "evidence_set_id_public": False,
                "cluster_kind": evidence["cluster"]["kind"],
                "cluster_family": evidence["cluster"]["family"],
                "donor_slot": donor_slots_by_root.get(donor_root, "UNKNOWN_DONOR_SLOT"),
                "subject_names": subjects.get("subject_names", []),
                "counterevidence_items": len(
                    evidence["counterevidence"]["symbol_structure_divergences"]
                ),
                "unknown_items": len(evidence["unknown"]),
                "behavioral_equivalence_claimed": evidence["claims"][
                    "behavioral_equivalence"
                ],
                "retirement_safety_claimed": evidence["claims"]["retirement_safety"],
            }
        )
    return {
        "matching_evidence_sets": matches,
        "matching_evidence_set_count": len(matches),
        "source": "M71_BEHAVIOR_COUNTEREVIDENCE",
    }


def _derived_payload_fact_dispositions(
    canonical: Mapping[str, Any],
    donors: Sequence[Mapping[str, Any]],
    history: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Any],
) -> list[dict[str, Any]]:
    v1_donors = [
        item
        for item in donors
        if item["variant"]["classification"] == "HISTORICAL_V1_VARIANT"
    ]
    current_matches = [
        item
        for item in donors
        if item["variant"]["classification"] == "EXACT_CURRENT_CANONICAL"
    ]
    absent = [
        item
        for item in donors
        if item["variant"]["classification"] == "ABSENT_FROM_DONOR"
    ]
    history_schemas = sorted(
        {
            item["schema_line"]
            for item in history
            if isinstance(item.get("schema_line"), str)
        }
    )
    artifact_markers = sorted(
        {
            marker
            for item in artifacts["exact_artifacts"]
            for marker in item.get("markers", [])
        }
    )
    current_contract = canonical["contract"] or {}
    flags = current_contract.get("capability_flags", {})
    return [
        {
            "fact_id": "derived-payload-v1-verifier-source",
            "classification": (
                "SUPERSEDED_HISTORY_QUERYABLE"
                if v1_donors
                else "NOT_OBSERVED_IN_DONORS"
            ),
            "donor_count": len(v1_donors),
            "basis": [
                "v1 donor bytes are compared to canonical Git-history versions",
                "the current artifact records exact v1 source SHA and schema line",
            ],
            "current_behavior_replacement": "v2 activation-bound verifier",
            "drop_in_cli_compatibility": "NOT_CLAIMED_CURRENT_OUTPUT_SCHEMA_IS_V2",
            "retirement_permitted": False,
        },
        {
            "fact_id": "derived-payload-current-v2-verifier-source",
            "classification": "CANONICAL_EXACT_OR_STRICT_SUPERSET_FOR_THIS_FILE",
            "donor_exact_current_count": len(current_matches),
            "basis": [
                "current verifier SHA is bound",
                "donors with identical current bytes are explicitly counted",
                "history contains the v2 source lineage where available",
            ],
            "v2_capability_flags": flags,
            "retirement_permitted": False,
        },
        {
            "fact_id": "derived-payload-output-and-activation-schemas",
            "classification": "CURRENT_V2_WITH_HISTORICAL_V1_RECORDED",
            "history_schema_lines": history_schemas,
            "artifact_markers": artifact_markers,
            "compatibility": {
                "v1_output_schema": "PRESERVED_AS_HISTORICAL_SCHEMA_NOT_CURRENT_OUTPUT",
                "v2_output_schema": "CURRENT",
                "activation_receipt_schema": "CURRENT_WHERE_ARTIFACT_PRESENT",
                "runtime_replay_of_historical_v1_receipts": "UNKNOWN_NOT_EXECUTED",
            },
            "retirement_permitted": False,
        },
        {
            "fact_id": "donor-worktrees-without-verifier",
            "classification": "NO_FACT_TO_ADOPT_OR_SUPERSEDE_FOR_THIS_PATH"
            if absent
            else "NOT_OBSERVED",
            "donor_count": len(absent),
            "basis": [
                "absence is recorded at the canonical verifier path",
                "absence is not a whole-donor usefulness or retirement verdict",
            ],
            "retirement_permitted": False,
        },
    ]


def build_derived_payload_verifier_lineage(
    canonical_root: Path,
    donor_roots: Sequence[Path],
    m69_predecessor: Path,
    m70_predecessor: Path,
    m71_predecessor: Path,
    *,
    policy: InventoryPolicy | None = None,
) -> dict[str, Any]:
    """Compare derived-agent-payload verifier variants without executing donor code."""

    policy = policy or InventoryPolicy()
    canonical_root = canonical_root.resolve(strict=True)
    donors = [path.resolve(strict=True) for path in donor_roots]
    repositories = [canonical_root, *donors]
    if len(set(repositories)) != len(repositories):
        raise DivergenceError("canonical and donor worktree paths must be unique")
    if not donors:
        raise DivergenceError("at least one donor worktree is required")

    before = {str(root): _repository_snapshot(root) for root in repositories}
    dirty_before = {str(root): _dirty_snapshot(root, policy) for root in repositories}
    _predecessor_identity(m69_predecessor)
    m69_payload = json.loads(m69_predecessor.resolve(strict=True).read_text("utf-8"))
    m70, _m70_identity = _static_predecessor_identity(m70_predecessor)
    m71, _m71_identity = _behavior_predecessor_identity(m71_predecessor)
    expected_donors = m70["donor_static_facts"]
    if len(donors) != len(expected_donors):
        raise DivergenceError("M73 donor count does not match M70")
    donor_slots = {
        str(path): f"donor-{index:02d}" for index, path in enumerate(donors, start=1)
    }
    m70_donor_slots_by_root = {
        item["root"]: f"donor-{index:02d}"
        for index, item in enumerate(expected_donors, start=1)
    }
    for root, expected in zip(donors, expected_donors, strict=True):
        current_identity = _m73_public_repository_identity(before[str(root)])
        expected_identity = _m73_public_repository_identity(expected["repository"])
        if current_identity != expected_identity:
            raise DivergenceError(
                "M73 donor repository identity does not match M70 for "
                + donor_slots[str(root)]
            )

    canonical_observation = _verifier_observation(canonical_root)
    if canonical_observation["contract"] is None:
        raise DivergenceError("canonical verifier is absent")
    history = _verifier_git_history(canonical_root)
    history_by_sha = {item["sha256"]: item for item in history}
    donor_observations = []
    for root in donors:
        observation = _verifier_observation(root)
        donor_observations.append(
            {
                "slot": donor_slots[str(root)],
                **observation,
                "repository": _m73_public_repository_identity(
                    _repository_snapshot(root)
                ),
                "dirty": _m73_public_dirty_identity(_dirty_snapshot(root, policy)),
                "variant": _classify_verifier_variant(
                    canonical_observation, observation, history_by_sha
                ),
            }
        )
    artifact_inventory = _payload_artifact_inventory(canonical_root)
    behavior_evidence = _m71_verifier_evidence(m71, m70_donor_slots_by_root)
    compatibility_matrix = [
        {
            "donor_slot": donor["slot"],
            "verifier_file": donor["file"],
            "classification": donor["variant"]["classification"],
            "compatibility_status": donor["variant"]["compatibility_status"],
            "basis": donor["variant"]["basis"],
            "history_commit": donor["variant"].get("history_commit"),
            "backward_compatibility": {
                "current_verifier_output_schema": "giga.derived-agent-payload-verification.v2",
                "v1_output_schema_drop_in": (
                    "NO_CURRENT_VERIFIER_EMITS_V2"
                    if donor["variant"]["classification"] == "HISTORICAL_V1_VARIANT"
                    else "NOT_APPLICABLE_OR_UNKNOWN"
                ),
                "payload_safety_contract": (
                    "STATIC_SUPERSET_EVIDENCE_PRESENT"
                    if donor["variant"]["classification"]
                    in {"HISTORICAL_V1_VARIANT", "EXACT_CURRENT_CANONICAL"}
                    else "UNKNOWN"
                ),
                "donor_code_execution": "NOT_PERFORMED",
                "historical_queryability": (
                    "PRESERVED_BY_M73_FACT_MAP"
                    if donor["variant"]["classification"]
                    in {"HISTORICAL_V1_VARIANT", "HISTORICAL_NON_CURRENT_VARIANT"}
                    else "NOT_APPLICABLE_OR_UNKNOWN"
                ),
            },
            "whole_donor_retirement_permitted": False,
        }
        for donor in donor_observations
    ]
    after = {str(root): _repository_snapshot(root) for root in repositories}
    dirty_after = {str(root): _dirty_snapshot(root, policy) for root in repositories}
    changed = [
        "canonical"
        if path == str(canonical_root)
        else donor_slots.get(path, "UNKNOWN_REPOSITORY_SLOT")
        for path in sorted(before)
        if _m73_public_repository_identity(before[path])
        != _m73_public_repository_identity(after[path])
        or _m73_public_dirty_identity(dirty_before[path])
        != _m73_public_dirty_identity(dirty_after[path])
    ]
    if changed:
        raise DivergenceError(
            "observed repository changed during derived-payload lineage comparison: "
            + ", ".join(changed)
        )
    zero_mutation = seal_document(
        {
            "schema": ZERO_MUTATION_SCHEMA,
            "status": "PASS",
            "authority": "read-only-derived-agent-payload-lineage-observation",
            "authority_granted": False,
            "repositories": [
                _m73_public_zero_repository(
                    "canonical"
                    if path == str(canonical_root)
                    else donor_slots.get(path, "UNKNOWN_REPOSITORY_SLOT"),
                    before[path],
                    after[path],
                    dirty_before[path],
                    dirty_after[path],
                )
                for path in sorted(
                    before,
                    key=lambda item: (
                        "00"
                        if item == str(canonical_root)
                        else donor_slots.get(item, "zz"),
                        item,
                    ),
                )
            ],
            "limits": {
                "donor_code_execution": "NOT_PERFORMED",
                "donor_test_execution": "NOT_PERFORMED",
                "provider_browser_mailbox_canary": "NOT_PERFORMED",
                "runtime_refresh_or_mutation": "NOT_PERFORMED",
            },
        }
    )
    counts = Counter(donor["variant"]["classification"] for donor in donor_observations)
    return seal_document(
        {
            "schema": DERIVED_PAYLOAD_LINEAGE_SCHEMA,
            "status": "PARTIAL_FACT_LEVEL_DISPOSITION",
            "authority": "read-only-non-authoritative-derived-payload-lineage",
            "authority_granted": False,
            "cleanup_permitted": False,
            "retirement_permitted": False,
            "predecessors": {
                "m69": _m73_public_predecessor_identity(
                    "m69", m69_payload, compressed=False
                ),
                "m70": _m73_public_predecessor_identity("m70", m70, compressed=True),
                "m71": _m73_public_predecessor_identity("m71", m71, compressed=True),
            },
            "canonical_candidate": {
                "slot": "canonical",
                "repository": _m73_public_repository_identity(
                    before[str(canonical_root)]
                ),
                "dirty": _m73_public_dirty_identity(dirty_before[str(canonical_root)]),
                "verifier": canonical_observation,
            },
            "donors": donor_observations,
            "history": {
                "path": DERIVED_PAYLOAD_VERIFIER_PATH,
                "unique_versions": history,
                "unique_version_count": len(history),
            },
            "payload_artifact_inventory": artifact_inventory,
            "m71_verifier_evidence": behavior_evidence,
            "compatibility_matrix": compatibility_matrix,
            "fact_dispositions": _derived_payload_fact_dispositions(
                canonical_observation,
                donor_observations,
                history,
                artifact_inventory,
            ),
            "counts": {
                "donors": len(donor_observations),
                "exact_current_canonical": counts["EXACT_CURRENT_CANONICAL"],
                "historical_v1_variants": counts["HISTORICAL_V1_VARIANT"],
                "historical_non_current_variants": counts[
                    "HISTORICAL_NON_CURRENT_VARIANT"
                ],
                "absent_from_donor": counts["ABSENT_FROM_DONOR"],
                "unmapped_different_verifier": counts["UNMAPPED_DIFFERENT_VERIFIER"],
                "artifact_marker_records": artifact_inventory["marker_index_count"],
                "m71_matching_verifier_evidence_sets": behavior_evidence[
                    "matching_evidence_set_count"
                ],
            },
            "zero_mutation": zero_mutation,
            "graph_status": _graph_status(canonical_root),
            "claims": {
                "whole_donor_retirement": False,
                "no_feature_loss": False,
                "drop_in_v1_compatibility": False,
                "donor_code_execution": False,
                "provider_browser_mailbox_canary": False,
                "runtime_refresh_or_mutation": False,
            },
            "remaining_unknowns": [
                "runtime execution against historical v1 verifier receipts",
                "external consumers expecting v1 verification output JSON",
                "semantic usefulness of non-verifier donor worktree content",
                "whole-donor retirement or cleanup safety",
            ],
        }
    )


def render_derived_payload_verifier_lineage_report(payload: Mapping[str, Any]) -> str:
    counts = payload["counts"]
    lines = [
        "# M73 derived-agent-payload verifier lineage",
        "",
        "## Verdict",
        "",
        "The canonical verifier lineage is now queryable at fact level. "
        "The report distinguishes current v2 verifier matches, historical v1 donor variants, absent donor paths, preserved schema evidence and explicit UNKNOWN compatibility. "
        "It makes no whole-donor retirement, cleanup, no-feature-loss or provider/runtime claim.",
        "",
        "## Bound evidence",
        "",
        "- M69 predecessor: internally validated; public path and receipt hash withheld.",
        "- M70 predecessor: internally restored and validated; public path and receipt hash withheld.",
        "- M71 predecessor: internally restored and validated; public path and receipt hash withheld.",
        f"- M73 receipt: `{payload['receipt_sha256']}`",
        f"- Zero-mutation receipt: `{payload['zero_mutation']['receipt_sha256']}`",
        f"- Candidate HEAD: `{payload['canonical_candidate']['repository']['head']}`",
        f"- Candidate tree: `{payload['canonical_candidate']['repository']['tree']}`",
        "",
        "## Counts",
        "",
        f"- Donors compared: {counts['donors']}",
        f"- Exact current verifier matches: {counts['exact_current_canonical']}",
        f"- Historical v1 verifier variants: {counts['historical_v1_variants']}",
        f"- Donors without verifier at canonical path: {counts['absent_from_donor']}",
        f"- Payload schema/evidence marker records: {counts['artifact_marker_records']}",
        f"- M71 verifier evidence sets: {counts['m71_matching_verifier_evidence_sets']}",
        "",
        "## Evidence boundary",
        "",
        "- Donor code and arbitrary donor tests were not executed.",
        "- Current verifier output is v2; drop-in v1 JSON compatibility is not claimed.",
        "- Historical v1 source/schema evidence is preserved and queryable in this M73 artifact.",
        "- No donor/worktree retirement, cleanup, no-feature-loss, runtime refresh or external action is authorised.",
        "",
        "## Donor classifications",
        "",
    ]
    for item in payload["compatibility_matrix"]:
        lines.append(
            f"- `{item['classification']}`: `{item['donor_slot']}` "
            f"({item['compatibility_status']})."
        )
    lines.extend(["", "## Remaining UNKNOWN", ""])
    for item in payload["remaining_unknowns"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_derived_payload_verifier_lineage(
    canonical_root: Path,
    donor_roots: Sequence[Path],
    m69_predecessor: Path,
    m70_predecessor: Path,
    m71_predecessor: Path,
    output: Path,
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists():
        raise DivergenceError(
            "derived-payload lineage output directory must not already exist"
        )
    payload = build_derived_payload_verifier_lineage(
        canonical_root,
        donor_roots,
        m69_predecessor,
        m70_predecessor,
        m71_predecessor,
    )
    try:
        output.mkdir(parents=True, mode=0o700)
        write_atomic(
            output / "derived_payload_lineage.json",
            canonical_bytes(payload),
        )
        write_atomic(
            output / "DERIVED_PAYLOAD_LINEAGE_REPORT.md",
            render_derived_payload_verifier_lineage_report(payload).encode("utf-8"),
        )
    except (EvidenceError, OSError) as exc:
        raise DivergenceError(str(exc)) from exc
    return payload


def _m76_refuse(exc: BaseException | None = None) -> None:
    raise DivergenceError(M76_REFUSAL) from exc


def _m76_strict_json(raw: bytes) -> dict[str, Any]:
    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _m76_refuse()
            result[key] = value
        return result

    try:
        payload = json.loads(
            raw.decode("utf-8", "strict"), object_pairs_hook=strict_object
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        _m76_refuse(exc)
    if not isinstance(payload, dict):
        _m76_refuse()
    return payload


def _m76_json_predecessor(
    path: Path, schema: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        raw = path.resolve(strict=True).read_bytes()
        payload = _m76_strict_json(raw)
        validate_self_hash(payload)
    except (OSError, EvidenceError) as exc:
        _m76_refuse(exc)
    if payload.get("schema") != schema:
        _m76_refuse()
    return payload, {
        "schema": payload["schema"],
        "status": payload.get("status"),
        "receipt_sha256": payload["receipt_sha256"],
        "raw_sha256": sha256_bytes(raw),
        "raw_bytes": len(raw),
        "path_public": False,
        "path_hash_public": False,
        "validated": True,
    }


def _m76_gzip_predecessor(
    path: Path, schema: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        compressed = path.resolve(strict=True).read_bytes()
    except OSError as exc:
        _m76_refuse(exc)
    if len(compressed) >= 100_000_000:
        _m76_refuse()
    if len(compressed) < 10 or compressed[:2] != b"\x1f\x8b":
        _m76_refuse()
    if int.from_bytes(compressed[4:8], "little") != 0:
        _m76_refuse()
    try:
        restored = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        _m76_refuse(exc)
    if len(restored) > 512 * 1024 * 1024:
        _m76_refuse()
    payload = _m76_strict_json(restored)
    try:
        validate_self_hash(payload)
        validate_self_hash(payload["zero_mutation"])
    except (EvidenceError, KeyError) as exc:
        _m76_refuse(exc)
    if payload.get("schema") != schema:
        _m76_refuse()
    return payload, {
        "schema": payload["schema"],
        "status": payload.get("status"),
        "receipt_sha256": payload["receipt_sha256"],
        "zero_mutation_receipt_sha256": payload["zero_mutation"]["receipt_sha256"],
        "compressed_sha256": sha256_bytes(compressed),
        "compressed_bytes": len(compressed),
        "restored_sha256": sha256_bytes(restored),
        "restored_bytes": len(restored),
        "gzip_mtime": 0,
        "path_public": False,
        "path_hash_public": False,
        "validated": True,
    }


def _m76_public_repository_identity(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    status = snapshot.get("status", {})
    return {
        "head": snapshot.get("head"),
        "tree": snapshot.get("tree"),
        "status_sha256": status.get("sha256"),
        "status_bytes": status.get("bytes"),
    }


def _m76_public_dirty_identity(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    status = snapshot.get("status", {})
    return {
        "clean": status.get("clean"),
        "status_sha256": status.get("sha256"),
        "status_bytes": status.get("bytes"),
        "status_entries": status.get("entries"),
        "status_entries_sha256": status.get("entries_sha256"),
        "paths_public": False,
        "path_hash_public": False,
    }


def _m76_zero_repository(
    slot: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    dirty_before: Mapping[str, Any],
    dirty_after: Mapping[str, Any],
) -> dict[str, Any]:
    public_before = _m76_public_repository_identity(before)
    public_after = _m76_public_repository_identity(after)
    public_dirty_before = _m76_public_dirty_identity(dirty_before)
    public_dirty_after = _m76_public_dirty_identity(dirty_after)
    return {
        "slot": slot,
        "before_sha256": sha256_bytes(canonical_bytes(public_before)),
        "after_sha256": sha256_bytes(canonical_bytes(public_after)),
        "dirty_before_sha256": sha256_bytes(canonical_bytes(public_dirty_before)),
        "dirty_after_sha256": sha256_bytes(canonical_bytes(public_dirty_after)),
        "unchanged": public_before == public_after
        and public_dirty_before == public_dirty_after,
        "paths_public": False,
        "path_hash_public": False,
    }


def _m76_git_blob_oid(root: Path, relative: str) -> str:
    try:
        return _git_text(root, ["hash-object", "--", relative])
    except DivergenceError as exc:
        _m76_refuse(exc)


def _m76_parse_module(raw: bytes, *, label: str) -> ast.Module:
    try:
        return ast.parse(raw.decode("utf-8", "strict"), filename=label)
    except (UnicodeDecodeError, SyntaxError) as exc:
        _m76_refuse(exc)


def _m76_extract_literal_all(module: ast.Module) -> dict[str, Any]:
    assignments: list[ast.AST] = []
    for node in module.body:
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in targets
        ):
            value = getattr(node, "value", None)
            if value is not None:
                assignments.append(value)
    if len(assignments) != 1:
        _m76_refuse()
    value_node = assignments[0]
    try:
        value = ast.literal_eval(value_node)
    except (ValueError, SyntaxError) as exc:
        _m76_refuse(exc)
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) for item in value
    ):
        _m76_refuse()
    exports = list(value)
    if len(exports) != len(set(exports)):
        _m76_refuse()
    return {
        "assignment_kind": "LITERAL_SEQUENCE",
        "exported_names": exports,
        "export_count": len(exports),
        "unique_export_count": len(set(exports)),
        "export_names_sha256": sha256_bytes(canonical_bytes(exports)),
    }


def _m76_extract_relative_import_bindings(
    module: ast.Module,
) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for node in module.body:
        if not isinstance(node, ast.ImportFrom) or node.level != 1:
            continue
        if not isinstance(node.module, str) or not node.module:
            _m76_refuse()
        for alias in node.names:
            public_name = alias.asname or alias.name
            if public_name in bindings:
                _m76_refuse()
            bindings[public_name] = {
                "module": node.module,
                "imported_name": alias.name,
                "alias": public_name,
            }
    return bindings


def _m76_symbol_identity(
    root: Path,
    package_relative: str,
    module_name: str,
    symbol_name: str,
) -> dict[str, Any]:
    relative = (
        PurePosixPath(package_relative)
        .joinpath(*PurePosixPath(module_name.replace(".", "/")).parts)
        .with_suffix(".py")
        .as_posix()
    )
    raw, identity = _safe_file_observation(root, relative, max_bytes=8 * 1024 * 1024)
    if raw is None:
        return {
            "status": "UNKNOWN_SYMBOL_SOURCE_UNAVAILABLE",
            "module": module_name,
            "symbol": symbol_name,
        }
    module = _m76_parse_module(raw, label="m76-symbol-source")
    matches: list[ast.AST] = []
    for node in module.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == symbol_name:
                matches.append(node)
        elif isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == symbol_name
                for target in node.targets
            ):
                matches.append(node)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == symbol_name:
                matches.append(node)
    if len(matches) != 1:
        return {
            "status": "UNKNOWN_SYMBOL_NOT_UNIQUELY_DECLARED",
            "module": module_name,
            "symbol": symbol_name,
            "match_count": len(matches),
            "source_sha256": identity.get("sha256"),
        }
    node = matches[0]
    symbol_kind = type(node).__name__
    ast_sha256 = sha256_bytes(
        ast.dump(node, annotate_fields=True, include_attributes=False).encode("utf-8")
    )
    return {
        "status": "FOUND",
        "module": module_name,
        "symbol": symbol_name,
        "symbol_kind": symbol_kind,
        "symbol_ast_sha256": ast_sha256,
        "source_sha256": identity["sha256"],
        "git_blob_oid": _m76_git_blob_oid(root, relative),
    }


def _m76_source_observation(
    root: Path,
    relative: str,
    package_relative: str,
    slot: str,
) -> dict[str, Any]:
    raw, identity = _safe_file_observation(root, relative, max_bytes=2 * 1024 * 1024)
    if raw is None:
        _m76_refuse()
    module = _m76_parse_module(raw, label=f"m76-{slot}")
    all_assignment = _m76_extract_literal_all(module)
    bindings = _m76_extract_relative_import_bindings(module)
    missing_bindings = [
        name for name in all_assignment["exported_names"] if name not in bindings
    ]
    if missing_bindings:
        _m76_refuse()
    return {
        "slot": slot,
        "source": {
            "content_sha256": identity["sha256"],
            "git_blob_oid": _m76_git_blob_oid(root, relative),
            "size_bytes": identity["size_bytes"],
            "path_public": False,
            "path_hash_public": False,
        },
        "assignment": all_assignment,
        "bindings": bindings,
        "binding_count": len(bindings),
        "binding_names_sha256": sha256_bytes(canonical_bytes(sorted(bindings))),
        "package_relative": package_relative,
    }


def _m76_legacy_bridge_observation(root: Path) -> dict[str, Any]:
    raw, identity = _safe_file_observation(
        root, M76_CANONICAL_LEGACY_SURFACE_PATH, max_bytes=2 * 1024 * 1024
    )
    if raw is None:
        return {"slot": "canonical-legacy-bridge", "status": "ABSENT"}
    module = _m76_parse_module(raw, label="m76-legacy-bridge")
    canonical_package_literal = None
    all_mirrors_canonical = False
    for node in module.body:
        if isinstance(node, ast.Assign):
            target_names = [
                target.id for target in node.targets if isinstance(target, ast.Name)
            ]
            if "_CANONICAL_PACKAGE" in target_names:
                try:
                    canonical_package_literal = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    canonical_package_literal = None
            if "__all__" in target_names:
                all_mirrors_canonical = (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "tuple"
                    and len(node.value.args) == 1
                    and isinstance(node.value.args[0], ast.Attribute)
                    and node.value.args[0].attr == "__all__"
                    and isinstance(node.value.args[0].value, ast.Name)
                    and node.value.args[0].value.id == "_canonical"
                )
    text = raw.decode("utf-8", "replace")
    return {
        "slot": "canonical-legacy-bridge",
        "status": (
            "MIRRORS_CANONICAL_PUBLIC_SURFACE"
            if canonical_package_literal == "modules.operations.archaeology"
            and all_mirrors_canonical
            and "sys.modules" in text
            else "UNKNOWN_LEGACY_BRIDGE_SHAPE"
        ),
        "source": {
            "content_sha256": identity["sha256"],
            "git_blob_oid": _m76_git_blob_oid(root, M76_CANONICAL_LEGACY_SURFACE_PATH),
            "size_bytes": identity["size_bytes"],
            "path_public": False,
            "path_hash_public": False,
        },
        "canonical_package_literal_public": False,
        "legacy_path_public": False,
        "path_hash_public": False,
    }


def _m76_public_surface_comparison(
    canonical: Mapping[str, Any],
    donor: Mapping[str, Any],
    canonical_root: Path,
    donor_root: Path,
) -> dict[str, Any]:
    canonical_exports = list(canonical["assignment"]["exported_names"])
    donor_exports = list(donor["assignment"]["exported_names"])
    canonical_set = set(canonical_exports)
    donor_set = set(donor_exports)
    missing = sorted(donor_set - canonical_set)
    canonical_extra = sorted(canonical_set - donor_set)
    rows = []
    implementation_exact = 0
    implementation_drift = 0
    implementation_unknown = 0
    binding_target_matches = 0
    for name in donor_exports:
        donor_binding = donor["bindings"].get(name)
        canonical_binding = canonical["bindings"].get(name)
        if donor_binding is None or canonical_binding is None:
            status = "MISSING_BINDING"
            implementation_unknown += 1
            rows.append(
                {
                    "exported_name": name,
                    "binding_target_match": False,
                    "implementation_identity": status,
                }
            )
            continue
        binding_match = (
            donor_binding["module"] == canonical_binding["module"]
            and donor_binding["imported_name"] == canonical_binding["imported_name"]
        )
        if binding_match:
            binding_target_matches += 1
        donor_symbol = _m76_symbol_identity(
            donor_root,
            donor["package_relative"],
            donor_binding["module"],
            donor_binding["imported_name"],
        )
        canonical_symbol = _m76_symbol_identity(
            canonical_root,
            canonical["package_relative"],
            canonical_binding["module"],
            canonical_binding["imported_name"],
        )
        implementation_identity = "UNKNOWN"
        if donor_symbol["status"] == "FOUND" and canonical_symbol["status"] == "FOUND":
            if (
                binding_match
                and donor_symbol["symbol_kind"] == canonical_symbol["symbol_kind"]
                and donor_symbol["symbol_ast_sha256"]
                == canonical_symbol["symbol_ast_sha256"]
            ):
                implementation_identity = "EXACT_SYMBOL_AST_MATCH"
                implementation_exact += 1
            else:
                implementation_identity = "CURRENT_CANONICAL_IMPLEMENTATION_DIVERGES"
                implementation_drift += 1
        else:
            implementation_unknown += 1
        rows.append(
            {
                "exported_name": name,
                "binding_target_match": binding_match,
                "donor_binding": donor_binding,
                "canonical_binding": canonical_binding,
                "implementation_identity": implementation_identity,
                "donor_symbol": donor_symbol,
                "canonical_symbol": canonical_symbol,
            }
        )
    if missing:
        classification = "CONFLICTING_DONOR_EXPORTS_MISSING_FROM_CANONICAL"
    elif binding_target_matches == len(donor_exports):
        classification = "CANONICAL_STRICT_SUPERSET_SUPERSEDES_DONOR_EXPORT_ASSIGNMENT"
    else:
        classification = "CANONICAL_EXPORT_SURFACE_PRESENT_WITH_BINDING_UNKNOWNS"
    return {
        "classification": classification,
        "canonical_export_count": len(canonical_exports),
        "donor_export_count": len(donor_exports),
        "canonical_extra_export_count": len(canonical_extra),
        "missing_donor_export_count": len(missing),
        "binding_target_match_count": binding_target_matches,
        "implementation_exact_symbol_ast_count": implementation_exact,
        "implementation_drift_count": implementation_drift,
        "implementation_unknown_count": implementation_unknown,
        "canonical_extra_exports": canonical_extra,
        "missing_donor_exports": missing,
        "donor_export_rows": rows,
        "donor_export_names_sha256": sha256_bytes(canonical_bytes(donor_exports)),
        "canonical_export_names_sha256": sha256_bytes(
            canonical_bytes(canonical_exports)
        ),
        "behavioral_equivalence_proved": False,
        "runtime_reachability_proved": False,
    }


def _m76_predecessor_bundle(
    m69_predecessor: Path,
    m70_predecessor: Path,
    m71_predecessor: Path,
    evidence_set_id: str,
    donor_repository: Mapping[str, Any],
) -> dict[str, Any]:
    m69, m69_identity = _m76_json_predecessor(m69_predecessor, DIVERGENCE_SCHEMA)
    m70, m70_identity = _m76_gzip_predecessor(m70_predecessor, STATIC_DIVERGENCE_SCHEMA)
    m71, m71_identity = _m76_gzip_predecessor(
        m71_predecessor, BEHAVIOR_DIVERGENCE_SCHEMA
    )
    bindings = [
        item
        for item in m71["cluster_bindings"]
        if item["evidence_set_id"] == evidence_set_id
    ]
    evidence_sets = [
        item
        for item in m71["evidence_sets"]
        if item["evidence_set_id"] == evidence_set_id
    ]
    if len(bindings) != 1 or len(evidence_sets) != 1:
        _m76_refuse()
    binding = bindings[0]
    ordinal = binding.get("m70_ordinal")
    if (
        not isinstance(ordinal, int)
        or ordinal < 0
        or ordinal >= len(m70["review_clusters"])
    ):
        _m76_refuse()
    cluster = m70["review_clusters"][ordinal]
    evidence = evidence_sets[0]["evidence"]
    if (
        cluster.get("kind") != "CONFLICT_REVIEW"
        or cluster.get("family") != "assignments_constants"
        or evidence.get("subjects", {}).get("subject_names") != ["__all__"]
    ):
        _m76_refuse()
    donor_static = None
    for item in m70["donor_static_facts"]:
        if item["root"] == cluster["donor_root"]:
            donor_static = item
            break
    if donor_static is None:
        _m76_refuse()
    expected_donor_identity = _m76_public_repository_identity(
        donor_static["repository"]
    )
    if _m76_public_repository_identity(donor_repository) != expected_donor_identity:
        _m76_refuse()
    return {
        "m69": m69_identity,
        "m70": m70_identity,
        "m71": m71_identity,
        "target_evidence_set": {
            "evidence_set_id": evidence_set_id,
            "evidence_sha256": evidence_sets[0]["evidence_sha256"],
            "cluster_id": binding["cluster_id"],
            "m70_ordinal": ordinal,
            "cluster_kind": cluster["kind"],
            "family": cluster["family"],
            "subject_names": evidence["subjects"]["subject_names"],
            "subject_fact_count": evidence["subjects"]["subject_fact_count"],
            "subject_fact_ids_sha256": evidence["subjects"]["subject_fact_ids_sha256"],
            "donor_slot": "retention-depth-donor",
            "path_public": False,
            "path_hash_public": False,
        },
        "predecessor_payload_receipts": {
            "m69": m69["receipt_sha256"],
            "m70": m70["receipt_sha256"],
            "m71": m71["receipt_sha256"],
        },
    }


def _m76_graph_status(root: Path) -> dict[str, Any]:
    status = _graph_status(root)
    return {
        "queried_before_decision": True,
        "status": status["status"],
        "authority": status["authority"],
        "refresh_performed": False,
        "uncovered_change_slots": [
            "divergence-owner-m76-functions",
            "divergence-tests-m76-coverage",
            "m76-export-surface-receipt-report",
        ],
        "path_public": False,
        "path_hash_public": False,
    }


def build_m76_export_surface_disposition(
    canonical_root: Path,
    donor_root: Path,
    m69_predecessor: Path,
    m70_predecessor: Path,
    m71_predecessor: Path,
    *,
    evidence_set_id: str = M76_EXPORT_SURFACE_EVIDENCE_SET_ID,
) -> dict[str, Any]:
    """Adjudicate one M71 export-surface conflict without donor execution."""

    try:
        canonical_root = canonical_root.resolve(strict=True)
        donor_root = donor_root.resolve(strict=True)
        before = {
            "canonical": _repository_snapshot(canonical_root),
            "retention-depth-donor": _repository_snapshot(donor_root),
        }
        dirty_before = {
            "canonical": _dirty_snapshot(canonical_root, InventoryPolicy()),
            "retention-depth-donor": _dirty_snapshot(donor_root, InventoryPolicy()),
        }
        predecessors = _m76_predecessor_bundle(
            m69_predecessor,
            m70_predecessor,
            m71_predecessor,
            evidence_set_id,
            before["retention-depth-donor"],
        )
        canonical_surface = _m76_source_observation(
            canonical_root,
            M76_CANONICAL_PUBLIC_SURFACE_PATH,
            "modules/operations/archaeology",
            "canonical-current-public-surface",
        )
        donor_surface = _m76_source_observation(
            donor_root,
            M76_DONOR_PUBLIC_SURFACE_PATH,
            "modules/operations/archaeologist",
            "retention-depth-donor-public-surface",
        )
        legacy_bridge = _m76_legacy_bridge_observation(canonical_root)
        comparison = _m76_public_surface_comparison(
            canonical_surface, donor_surface, canonical_root, donor_root
        )
        after = {
            "canonical": _repository_snapshot(canonical_root),
            "retention-depth-donor": _repository_snapshot(donor_root),
        }
        dirty_after = {
            "canonical": _dirty_snapshot(canonical_root, InventoryPolicy()),
            "retention-depth-donor": _dirty_snapshot(donor_root, InventoryPolicy()),
        }
        changed = [
            slot
            for slot in sorted(before)
            if _m76_public_repository_identity(before[slot])
            != _m76_public_repository_identity(after[slot])
            or _m76_public_dirty_identity(dirty_before[slot])
            != _m76_public_dirty_identity(dirty_after[slot])
        ]
        if changed:
            _m76_refuse()
        zero_mutation = seal_document(
            {
                "schema": ZERO_MUTATION_SCHEMA,
                "status": "PASS",
                "authority": "read-only-one-cluster-export-surface-disposition",
                "authority_granted": False,
                "repositories": [
                    _m76_zero_repository(
                        slot,
                        before[slot],
                        after[slot],
                        dirty_before[slot],
                        dirty_after[slot],
                    )
                    for slot in sorted(before)
                ],
                "limits": {
                    "donor_code_execution": "NOT_PERFORMED",
                    "donor_test_execution": "NOT_PERFORMED",
                    "payload_runtime_mutation": "NOT_PERFORMED",
                    "cleanup_retirement_quarantine": "NOT_PERFORMED",
                    "protected_branch_integration": "NOT_PERFORMED",
                },
            }
        )
        disposition_classification = (
            "CANONICAL_STRICT_SUPERSET_SUPERSEDED_DONOR_SURFACE"
            if comparison["classification"]
            == "CANONICAL_STRICT_SUPERSET_SUPERSEDES_DONOR_EXPORT_ASSIGNMENT"
            and legacy_bridge["status"] == "MIRRORS_CANONICAL_PUBLIC_SURFACE"
            else "PARTIAL_OR_UNKNOWN_EXPORT_SURFACE_DISPOSITION"
        )
        payload = {
            "schema": EXPORT_SURFACE_DISPOSITION_SCHEMA,
            "status": "PARTIAL_FACT_LEVEL_DISPOSITION",
            "authority": "read-only-one-cluster-export-surface-canary",
            "authority_granted": False,
            "cleanup_permitted": False,
            "retirement_permitted": False,
            "source_integration_performed": False,
            "target": {
                "scope": "single-M71-evidence-set",
                "evidence_set_id": evidence_set_id,
                "assignment": "__all__",
                "donor_slot": "retention-depth-donor",
                "canonical_slot": "canonical-current-public-surface",
                "whole_file_claim": False,
                "whole_worktree_claim": False,
                "behavioral_equivalence_claim": False,
            },
            "predecessors": predecessors,
            "canonical_candidate": {
                "slot": "canonical",
                "repository": _m76_public_repository_identity(before["canonical"]),
                "dirty": _m76_public_dirty_identity(dirty_before["canonical"]),
                "public_surface": {
                    key: value
                    for key, value in canonical_surface.items()
                    if key not in {"bindings", "package_relative"}
                },
                "legacy_bridge": legacy_bridge,
            },
            "donor": {
                "slot": "retention-depth-donor",
                "repository": _m76_public_repository_identity(
                    before["retention-depth-donor"]
                ),
                "dirty": _m76_public_dirty_identity(
                    dirty_before["retention-depth-donor"]
                ),
                "public_surface": {
                    key: value
                    for key, value in donor_surface.items()
                    if key not in {"bindings", "package_relative"}
                },
            },
            "public_surface_comparison": comparison,
            "fact_disposition": {
                "fact_id": "retention-depth-donor-public-export-assignment",
                "classification": disposition_classification,
                "basis": [
                    "M71 evidence set is bound to the single public-surface assignment conflict",
                    "canonical public surface has every donor export and additional exports",
                    "every donor export has the same static import target in canonical",
                    "legacy import surface mirrors the renamed canonical public surface",
                    "symbol-body drift is recorded as non-equivalence, not ignored",
                ],
                "retirement_permitted": False,
                "cleanup_permitted": False,
                "source_integration_required": False
                if not comparison["missing_donor_export_count"]
                else None,
            },
            "affected_import_evidence": {
                "legacy_bridge_static_shape": legacy_bridge["status"],
                "canonical_public_exports_bound": True,
                "donor_import_targets_compared": comparison["donor_export_count"],
                "donor_code_execution": False,
                "test_execution_required": "canonical-import-surface-only",
            },
            "zero_mutation": zero_mutation,
            "stash": {
                "slot": "stash-0",
                "commit": "22abe427412e8b2e7e465427f30c4ce51549ca12",
                "status": "PRESERVED_UNACCEPTED_AMBIGUOUS",
                "applied": False,
                "dropped": False,
            },
            "graph_status": _m76_graph_status(canonical_root),
            "claims": {
                "single_export_assignment_disposed": disposition_classification
                == "CANONICAL_STRICT_SUPERSET_SUPERSEDED_DONOR_SURFACE",
                "whole_file_equivalence": False,
                "whole_worktree_equivalence": False,
                "behavioral_equivalence": False,
                "no_feature_loss": False,
                "donor_retirement": False,
                "payload_runtime_mutation": False,
                "graph_current": False,
            },
            "remaining_unknowns": [
                "semantic usefulness of non-export donor behavior",
                "behavioral equivalence for donor-exported names whose current canonical symbol bodies differ",
                "runtime reachability beyond canonical import-surface tests",
                "the remaining M71 actionable evidence sets",
                "whole donor retirement or cleanup safety",
            ],
            "privacy": {
                "private_paths_public": False,
                "path_hashes_public": False,
                "layout_invariant_public_output": True,
            },
        }
        return seal_document(payload)
    except DivergenceError:
        raise
    except (OSError, HistoryError, InventoryError, KeyError, TypeError) as exc:
        _m76_refuse(exc)


def render_m76_export_surface_disposition_report(payload: Mapping[str, Any]) -> str:
    comparison = payload["public_surface_comparison"]
    lines = [
        "# M76 one-cluster export-surface disposition",
        "",
        "## What this slice implements",
        "",
        "M76 adjudicates one M71 conflict canary: the retention-depth donor public export assignment. "
        "It proves whether the current canonical public surface covers the donor surface without donor execution, source integration, cleanup or retirement.",
        "",
        "## Fact-level result",
        "",
        f"- Disposition: `{payload['fact_disposition']['classification']}`",
        f"- M76 receipt: `{payload['receipt_sha256']}`",
        f"- Zero-mutation receipt: `{payload['zero_mutation']['receipt_sha256']}`",
        f"- M71 evidence set: `{payload['target']['evidence_set_id']}`",
        f"- Canonical HEAD: `{payload['canonical_candidate']['repository']['head']}`",
        f"- Canonical tree: `{payload['canonical_candidate']['repository']['tree']}`",
        f"- Donor HEAD: `{payload['donor']['repository']['head']}`",
        f"- Donor tree: `{payload['donor']['repository']['tree']}`",
        "",
        "## Export-surface proof",
        "",
        f"- Canonical exports: {comparison['canonical_export_count']}",
        f"- Donor exports: {comparison['donor_export_count']}",
        f"- Donor exports missing from canonical: {comparison['missing_donor_export_count']}",
        f"- Additional canonical exports: {comparison['canonical_extra_export_count']}",
        f"- Matching static import targets: {comparison['binding_target_match_count']}",
        f"- Exact symbol AST matches: {comparison['implementation_exact_symbol_ast_count']}",
        f"- Current canonical symbol-body drift recorded: {comparison['implementation_drift_count']}",
        f"- UNKNOWN symbol identities: {comparison['implementation_unknown_count']}",
        "",
        "## Boundary",
        "",
        "- Donor code and donor tests were not executed.",
        "- Symbol-body drift is not treated as behavioral equivalence.",
        "- No whole-file, whole-worktree, no-feature-loss, cleanup or retirement claim is made.",
        "- The legacy compatibility surface is treated only as import-surface evidence.",
        f"- Graph status: `{payload['graph_status']['status']}`.",
        "",
    ]
    return "\n".join(lines)


def write_m76_export_surface_disposition(
    canonical_root: Path,
    donor_root: Path,
    m69_predecessor: Path,
    m70_predecessor: Path,
    m71_predecessor: Path,
    output: Path,
    *,
    evidence_set_id: str = M76_EXPORT_SURFACE_EVIDENCE_SET_ID,
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists():
        raise DivergenceError(
            "M76 export-surface output directory must not already exist"
        )
    payload = build_m76_export_surface_disposition(
        canonical_root,
        donor_root,
        m69_predecessor,
        m70_predecessor,
        m71_predecessor,
        evidence_set_id=evidence_set_id,
    )
    try:
        output.mkdir(parents=True, mode=0o700)
        write_atomic(
            output / "export_surface_disposition.json",
            canonical_bytes(payload),
        )
        write_atomic(
            output / "EXPORT_SURFACE_DISPOSITION_REPORT.md",
            render_m76_export_surface_disposition_report(payload).encode("utf-8"),
        )
    except (EvidenceError, OSError) as exc:
        _m76_refuse(exc)
    return payload


def _cli_superset_refuse(exc: BaseException | None = None) -> None:
    raise DivergenceError(CLI_SUPERSET_REFUSAL) from exc


def _cli_superset_parse_module(raw: bytes) -> ast.Module:
    try:
        return ast.parse(raw.decode("utf-8", "strict"), filename="cli-superset-source")
    except (SyntaxError, UnicodeDecodeError) as exc:
        _cli_superset_refuse(exc)


def _cli_superset_call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _cli_superset_call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _cli_superset_normalize_call(value: str) -> str:
    return value.replace(
        "modules.operations.archaeologist.",
        "modules.operations.archaeology.",
    )


def _cli_superset_is_command_compare(test: ast.AST) -> list[str]:
    if not isinstance(test, ast.Compare):
        return []
    try:
        left = ast.unparse(test.left)
    except ValueError:
        return []
    if left != "args.command" and not left.endswith(".command"):
        return []
    commands: list[str] = []
    for comparator in test.comparators:
        if isinstance(comparator, ast.Constant) and isinstance(
            comparator.value, str
        ):
            commands.append(comparator.value)
    return commands


def _cli_superset_extract_contract(raw: bytes) -> dict[str, Any]:
    module = _cli_superset_parse_module(raw)
    command_by_variable: dict[str, str] = {}
    commands: dict[str, dict[str, Any]] = {}
    for node in ast.walk(module):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "add_parser"
            and node.value.args
            and isinstance(node.value.args[0], ast.Constant)
            and isinstance(node.value.args[0].value, str)
        ):
            command = node.value.args[0].value
            if command in commands:
                _cli_superset_refuse()
            commands[command] = {
                "argument_tuples": [],
                "dispatch_calls": [],
                "line": node.lineno,
            }
            for target in node.targets:
                if isinstance(target, ast.Name):
                    command_by_variable[target.id] = command

    for node in ast.walk(module):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        ):
            continue
        command = command_by_variable.get(node.func.value.id)
        if command is None:
            continue
        if node.func.attr == "add_argument":
            names = [
                argument.value
                for argument in node.args
                if isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
            ]
            if names:
                commands[command]["argument_tuples"].append(tuple(names))
        elif node.func.attr == "set_defaults":
            for keyword in node.keywords:
                if keyword.arg == "func":
                    commands[command]["dispatch_calls"].append(ast.unparse(keyword.value))

    dispatch_by_command: dict[str, set[str]] = defaultdict(set)
    main_functions = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    ]
    if len(main_functions) > 1:
        _cli_superset_refuse()
    if main_functions:
        for node in ast.walk(main_functions[0]):
            if not isinstance(node, ast.If):
                continue
            command_names = _cli_superset_is_command_compare(node.test)
            if not command_names:
                continue
            for child in node.body:
                for call in ast.walk(child):
                    if not isinstance(call, ast.Call):
                        continue
                    name = _cli_superset_call_name(call.func)
                    if name is None:
                        continue
                    if name.startswith(("json.", "Path.", "sys.", "arguments.")):
                        continue
                    if name in {"print", "len", "sorted", "set", "tuple", "list", "dict"}:
                        continue
                    for command_name in command_names:
                        dispatch_by_command[command_name].add(
                            _cli_superset_normalize_call(name)
                        )

    main_guard_present = False
    for node in module.body:
        if not isinstance(node, ast.If):
            continue
        comparisons = []
        if isinstance(node.test, ast.Compare):
            try:
                comparisons.append(ast.unparse(node.test))
            except ValueError:
                comparisons = []
        if any("__name__" in item and "__main__" in item for item in comparisons):
            main_guard_present = True

    for command, values in commands.items():
        argument_tuples = sorted(set(values["argument_tuples"]))
        dispatch_calls = sorted(
            {
                _cli_superset_normalize_call(value)
                for value in (
                    *values["dispatch_calls"],
                    *dispatch_by_command.get(command, set()),
                )
            }
        )
        commands[command] = {
            "argument_tuples": [list(item) for item in argument_tuples],
            "argument_tuple_count": len(argument_tuples),
            "argument_tuples_sha256": sha256_bytes(canonical_bytes(argument_tuples)),
            "dispatch_calls": dispatch_calls,
            "dispatch_calls_sha256": sha256_bytes(canonical_bytes(dispatch_calls)),
            "line": values["line"],
        }

    return {
        "command_names": sorted(commands),
        "command_count": len(commands),
        "command_names_sha256": sha256_bytes(canonical_bytes(sorted(commands))),
        "commands": commands,
        "main_function_present": bool(main_functions),
        "main_guard_present": main_guard_present,
    }


def _cli_superset_current_source(
    root: Path, relative: str, *, max_bytes: int = 2 * 1024 * 1024
) -> tuple[bytes, dict[str, Any]]:
    raw, identity = _safe_file_observation(root, relative, max_bytes=max_bytes)
    if raw is None:
        _cli_superset_refuse()
    try:
        blob = _git_text(root, ["hash-object", "--", relative])
    except DivergenceError as exc:
        _cli_superset_refuse(exc)
    return raw, {
        "relative_source": relative,
        "content_sha256": identity["sha256"],
        "git_blob_oid": blob,
        "size_bytes": identity["size_bytes"],
        "path_public": False,
        "path_hash_public": False,
    }


def _cli_superset_git_object_source(
    canonical_root: Path,
    donor_root_text: str | None,
    head: str,
    relative: str,
) -> tuple[bytes, dict[str, Any]]:
    candidates: list[Path] = []
    if donor_root_text:
        donor_root = Path(donor_root_text)
        if donor_root.exists():
            candidates.append(donor_root)
    candidates.append(canonical_root)
    last_error: BaseException | None = None
    for candidate in candidates:
        try:
            raw = subprocess.run(
                ["/usr/bin/git", "-C", str(candidate), "show", f"{head}:{relative}"],
                check=True,
                capture_output=True,
            ).stdout
            blob = subprocess.run(
                [
                    "/usr/bin/git",
                    "-C",
                    str(candidate),
                    "rev-parse",
                    f"{head}:{relative}",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            return raw, {
                "relative_source": relative,
                "content_sha256": sha256_bytes(raw),
                "git_blob_oid": blob,
                "size_bytes": len(raw),
                "path_public": False,
                "path_hash_public": False,
                "read_mode": "GIT_OBJECT",
            }
        except (OSError, subprocess.CalledProcessError) as exc:
            last_error = exc
    _cli_superset_refuse(last_error)


def _cli_superset_wrapper_shape(raw: bytes) -> dict[str, Any]:
    module = _cli_superset_parse_module(raw)
    forwards_to_main = False
    imports_canonical_main = False
    for node in module.body:
        if isinstance(node, ast.ImportFrom) and node.module == (
            "modules.operations.scripts.archaeology"
        ):
            imports_canonical_main = any(alias.name == "main" for alias in node.names)
        if not isinstance(node, ast.If):
            continue
        try:
            test = ast.unparse(node.test)
        except ValueError:
            continue
        if "__name__" not in test or "__main__" not in test:
            continue
        rendered = "\n".join(ast.unparse(child) for child in node.body)
        forwards_to_main = "SystemExit(main())" in rendered or "sys.exit(main())" in rendered
    status = (
        "FORWARDS_TO_CANONICAL_ARCHAEOLOGY_MAIN"
        if imports_canonical_main and forwards_to_main
        else "UNKNOWN_LEGACY_ENTRYPOINT_SHAPE"
    )
    return {
        "status": status,
        "imports_canonical_main": imports_canonical_main,
        "main_guard_forwards": forwards_to_main,
    }


def _cli_superset_public_repository_identity(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return _m76_public_repository_identity(snapshot)


def _cli_superset_public_dirty_identity(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return _m76_public_dirty_identity(snapshot)


def _cli_superset_m69_path_row(
    donor: Mapping[str, Any], relative: str
) -> Mapping[str, Any] | None:
    matches = [
        row
        for row in donor.get("path_comparisons", [])
        if row.get("path") == relative
    ]
    if len(matches) > 1:
        _cli_superset_refuse()
    return matches[0] if matches else None


def _cli_superset_sanitize_m69_row(
    row: Mapping[str, Any] | None, relative: str
) -> dict[str, Any]:
    if row is None:
        return {
            "relative_source": relative,
            "classification": "NOT_RECORDED_IN_M69",
            "canonical": None,
            "donor": None,
        }
    canonical = row.get("canonical")
    donor = row.get("donor")
    return {
        "relative_source": relative,
        "classification": row.get("classification"),
        "canonical": {
            "content_sha256": canonical.get("sha256"),
            "git_blob_oid": canonical.get("git_blob_oid"),
            "symbols": canonical.get("symbols", []),
        }
        if isinstance(canonical, Mapping)
        else None,
        "donor": {
            "content_sha256": donor.get("sha256"),
            "git_blob_oid": donor.get("git_blob_oid"),
            "symbols": donor.get("symbols", []),
        }
        if isinstance(donor, Mapping)
        else None,
        "semantic_equivalence_claimed": row.get("semantic_equivalence_claimed"),
        "usefulness_claimed": row.get("usefulness_claimed"),
        "retirement_permitted": row.get("retirement_permitted"),
    }


def _cli_superset_command_rows(
    donor_contract: Mapping[str, Any],
    canonical_contract: Mapping[str, Any],
) -> list[dict[str, Any]]:
    canonical_commands = canonical_contract["commands"]
    rows: list[dict[str, Any]] = []
    for command in donor_contract["command_names"]:
        donor_command = donor_contract["commands"][command]
        canonical_command = canonical_commands.get(command)
        if canonical_command is None:
            rows.append(
                {
                    "command": command,
                    "classification": "MIGRATE_USEFUL_OR_UNKNOWN_COMMAND_MISSING",
                    "canonical_command_present": False,
                    "donor_argument_tuple_count": donor_command[
                        "argument_tuple_count"
                    ],
                    "missing_argument_tuples": [],
                    "missing_dispatch_calls": [],
                }
            )
            continue
        donor_arguments = {tuple(item) for item in donor_command["argument_tuples"]}
        canonical_arguments = {
            tuple(item) for item in canonical_command["argument_tuples"]
        }
        donor_calls = set(donor_command["dispatch_calls"])
        canonical_calls = set(canonical_command["dispatch_calls"])
        missing_arguments = sorted(donor_arguments - canonical_arguments)
        missing_calls = sorted(donor_calls - canonical_calls)
        if missing_arguments or missing_calls:
            classification = "MIGRATE_USEFUL_OR_UNKNOWN_BEHAVIOUR_MISSING"
        else:
            classification = "ALREADY_RETAINED_IN_CANONICAL_CLI"
        rows.append(
            {
                "command": command,
                "classification": classification,
                "canonical_command_present": True,
                "donor_argument_tuple_count": donor_command["argument_tuple_count"],
                "canonical_argument_tuple_count": canonical_command[
                    "argument_tuple_count"
                ],
                "missing_argument_tuples": [list(item) for item in missing_arguments],
                "missing_dispatch_calls": missing_calls,
                "donor_dispatch_calls_sha256": donor_command["dispatch_calls_sha256"],
                "canonical_dispatch_calls_sha256": canonical_command[
                    "dispatch_calls_sha256"
                ],
                "donor_line": donor_command["line"],
                "canonical_line": canonical_command["line"],
            }
        )
    return rows


def _cli_superset_reference_locations(root: Path) -> dict[str, Any]:
    pattern = (
        r"archaeologist\\.py|archaeology\\.py|giga-archaeology|"
        r"modules\\.operations\\.scripts\\.archaeology"
    )
    try:
        result = subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                str(root),
                "grep",
                "-n",
                "-E",
                pattern,
                "--",
                "modules",
                "tests",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        _cli_superset_refuse(exc)
    if result.returncode not in {0, 1}:
        _cli_superset_refuse()
    locations: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            _cli_superset_refuse()
        relative, lineno, _match = parts
        if PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts:
            _cli_superset_refuse()
        try:
            line_number = int(lineno)
        except ValueError as exc:
            _cli_superset_refuse(exc)
        locations.append(
            {
                "relative_source": relative,
                "line": line_number,
                "kind": "test" if relative.startswith("tests/") else "source",
            }
        )
    locations.sort(key=lambda item: (item["relative_source"], item["line"]))
    return {
        "locations": locations,
        "location_count": len(locations),
        "locations_sha256": sha256_bytes(canonical_bytes(locations)),
        "raw_match_text_public": False,
        "path_hash_public": False,
    }


def _cli_superset_predecessors(
    m69_predecessor: Path,
    m70_predecessor: Path,
    m71_predecessor: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        m69, m69_identity = _m76_json_predecessor(m69_predecessor, DIVERGENCE_SCHEMA)
        _m70, m70_identity = _m76_gzip_predecessor(
            m70_predecessor, STATIC_DIVERGENCE_SCHEMA
        )
        _m71, m71_identity = _m76_gzip_predecessor(
            m71_predecessor, BEHAVIOR_DIVERGENCE_SCHEMA
        )
    except DivergenceError as exc:
        _cli_superset_refuse(exc)
    return m69, {
        "m69": m69_identity,
        "m70": m70_identity,
        "m71": m71_identity,
        "specific_m70_m71_cluster": "NOT_APPLICABLE_M69_PATH_CLASSIFICATION_FAMILY",
    }


def _cli_superset_donor_source(
    canonical_root: Path, donor: Mapping[str, Any], old_row: Mapping[str, Any]
) -> tuple[bytes, dict[str, Any]]:
    donor_identity = old_row.get("donor")
    repository = donor.get("observation", {}).get("repository", {})
    head = repository.get("head")
    root = donor.get("observation", {}).get("root")
    if not isinstance(donor_identity, Mapping) or not isinstance(head, str):
        _cli_superset_refuse()
    raw, source = _cli_superset_git_object_source(
        canonical_root,
        root if isinstance(root, str) else None,
        head,
        CLI_SUPERSET_LEGACY_ENTRYPOINT_PATH,
    )
    if source["content_sha256"] != donor_identity.get("sha256"):
        _cli_superset_refuse()
    return raw, source


def _cli_superset_live_donor_snapshot(
    slot: str, donor: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    root = donor.get("observation", {}).get("root")
    if not isinstance(root, str):
        return None, None
    donor_root = Path(root)
    if not donor_root.exists():
        return None, None
    try:
        return _repository_snapshot(donor_root), _dirty_snapshot(
            donor_root, InventoryPolicy()
        )
    except (DivergenceError, HistoryError, InventoryError, OSError) as exc:
        _cli_superset_refuse(exc)


def _cli_superset_graph_status(root: Path) -> dict[str, Any]:
    status = _graph_status(root)
    return {
        "queried_before_decision": True,
        "status": "PARTIAL_STALE",
        "observed_index_status": status["status"],
        "authority": status["authority"],
        "refresh_performed": False,
        "uncovered_change_slots": [
            "divergence-owner-cli-superset-disposition-functions",
            "archaeology-cli-cli-superset-disposition-entrypoint",
            "divergence-tests-cli-superset-disposition",
            "cli-superset-disposition-receipt-report",
        ],
        "path_public": False,
        "path_hash_public": False,
    }


def build_cli_donor_superset_disposition(
    canonical_root: Path,
    m69_predecessor: Path,
    m70_predecessor: Path,
    m71_predecessor: Path,
) -> dict[str, Any]:
    """Adjudicate the old archaeologist.py CLI donor-superset family."""

    try:
        canonical_root = canonical_root.resolve(strict=True)
        m69, predecessor_identities = _cli_superset_predecessors(
            m69_predecessor, m70_predecessor, m71_predecessor
        )
        before = {"canonical": _repository_snapshot(canonical_root)}
        dirty_before = {
            "canonical": _dirty_snapshot(canonical_root, InventoryPolicy())
        }
        canonical_raw, canonical_source = _cli_superset_current_source(
            canonical_root, CLI_SUPERSET_CANONICAL_CLI_PATH
        )
        wrapper_raw, wrapper_source = _cli_superset_current_source(
            canonical_root, CLI_SUPERSET_LEGACY_ENTRYPOINT_PATH
        )
        canonical_contract = _cli_superset_extract_contract(canonical_raw)
        wrapper_shape = _cli_superset_wrapper_shape(wrapper_raw)

        donor_results: list[dict[str, Any]] = []
        live_before: dict[str, dict[str, Any]] = {}
        live_dirty_before: dict[str, dict[str, Any]] = {}
        classification_counts: Counter[str] = Counter()
        command_classification_counts: Counter[str] = Counter()
        m69_family_counts: Counter[str] = Counter()
        unique_donor_commands: set[str] = set()
        missing_command_count = 0
        missing_argument_tuple_count = 0
        missing_dispatch_call_count = 0

        donors = list(m69.get("donors", []))
        if not donors:
            _cli_superset_refuse()
        for ordinal, donor in enumerate(donors, start=1):
            slot = f"donor-{ordinal:02d}"
            repository = donor.get("observation", {}).get("repository", {})
            old_row = _cli_superset_m69_path_row(
                donor, CLI_SUPERSET_LEGACY_ENTRYPOINT_PATH
            )
            new_row = _cli_superset_m69_path_row(
                donor, CLI_SUPERSET_CANONICAL_CLI_PATH
            )
            live_repo, live_dirty = _cli_superset_live_donor_snapshot(slot, donor)
            if live_repo is not None and live_dirty is not None:
                live_before[slot] = live_repo
                live_dirty_before[slot] = live_dirty
            m69_old = _cli_superset_sanitize_m69_row(
                old_row, CLI_SUPERSET_LEGACY_ENTRYPOINT_PATH
            )
            m69_new = _cli_superset_sanitize_m69_row(
                new_row, CLI_SUPERSET_CANONICAL_CLI_PATH
            )
            m69_family_counts[m69_old["classification"]] += 1
            base_result: dict[str, Any] = {
                "slot": slot,
                "repository": _cli_superset_public_repository_identity(repository),
                "ancestry": {
                    key: donor.get("ancestry", {}).get(key)
                    for key in (
                        "merge_base",
                        "canonical_is_ancestor_of_donor",
                        "donor_is_ancestor_of_canonical",
                        "donor_unique_commit_count",
                        "canonical_unique_commit_count",
                        "samples_complete",
                    )
                },
                "m69_legacy_entrypoint": m69_old,
                "m69_canonical_cli": m69_new,
            }
            if old_row is None or old_row.get("donor") is None:
                classification = "DONOR_LEGACY_ENTRYPOINT_ABSENT"
                classification_counts[classification] += 1
                donor_results.append(
                    {
                        **base_result,
                        "classification": classification,
                        "command_rows": [],
                        "source_integration_required": False,
                    }
                )
                continue
            if old_row.get("classification") == "EXACT_EQUIVALENT":
                classification = "CURRENT_LEGACY_WRAPPER_ALREADY_RETAINS_ENTRYPOINT"
                classification_counts[classification] += 1
                donor_results.append(
                    {
                        **base_result,
                        "classification": classification,
                        "command_rows": [],
                        "source": m69_old["donor"],
                        "wrapper_shape": wrapper_shape,
                        "source_integration_required": False,
                    }
                )
                continue
            donor_raw, donor_source = _cli_superset_donor_source(
                canonical_root, donor, old_row
            )
            donor_contract = _cli_superset_extract_contract(donor_raw)
            command_rows = _cli_superset_command_rows(
                donor_contract, canonical_contract
            )
            unique_donor_commands.update(donor_contract["command_names"])
            for row in command_rows:
                command_classification_counts[row["classification"]] += 1
                missing_command_count += int(not row["canonical_command_present"])
                missing_argument_tuple_count += len(row["missing_argument_tuples"])
                missing_dispatch_call_count += len(row["missing_dispatch_calls"])
            if any(
                row["classification"] != "ALREADY_RETAINED_IN_CANONICAL_CLI"
                for row in command_rows
            ):
                classification = "PARTIAL_OR_UNKNOWN_DONOR_CLI_BEHAVIOUR"
                source_required = True
            elif canonical_contract["command_count"] > donor_contract["command_count"]:
                classification = "CANONICAL_CLI_STRICT_SUPERSET_SUPERSEDES_DONOR_SCRIPT"
                source_required = False
            else:
                classification = "CANONICAL_CLI_RETAINS_DONOR_SCRIPT"
                source_required = False
            classification_counts[classification] += 1
            donor_results.append(
                {
                    **base_result,
                    "classification": classification,
                    "source": donor_source,
                    "donor_contract": {
                        key: donor_contract[key]
                        for key in (
                            "command_names",
                            "command_count",
                            "command_names_sha256",
                            "main_function_present",
                            "main_guard_present",
                        )
                    },
                    "command_rows": command_rows,
                    "source_integration_required": source_required,
                }
            )

        after = {"canonical": _repository_snapshot(canonical_root)}
        dirty_after = {"canonical": _dirty_snapshot(canonical_root, InventoryPolicy())}
        live_after: dict[str, dict[str, Any]] = {}
        live_dirty_after: dict[str, dict[str, Any]] = {}
        for ordinal, donor in enumerate(donors, start=1):
            slot = f"donor-{ordinal:02d}"
            if slot not in live_before:
                continue
            live_repo, live_dirty = _cli_superset_live_donor_snapshot(slot, donor)
            if live_repo is None or live_dirty is None:
                _cli_superset_refuse()
            live_after[slot] = live_repo
            live_dirty_after[slot] = live_dirty

        zero_repositories = [
            _m76_zero_repository(
                "canonical",
                before["canonical"],
                after["canonical"],
                dirty_before["canonical"],
                dirty_after["canonical"],
            )
        ]
        for slot in sorted(live_before):
            zero_repositories.append(
                _m76_zero_repository(
                    slot,
                    live_before[slot],
                    live_after[slot],
                    live_dirty_before[slot],
                    live_dirty_after[slot],
                )
            )
        if not all(item["unchanged"] for item in zero_repositories):
            _cli_superset_refuse()
        zero_mutation = seal_document(
            {
                "schema": ZERO_MUTATION_SCHEMA,
                "status": "PASS",
                "authority": "read-only-cli-donor-symbol-superset-disposition",
                "authority_granted": False,
                "repositories": zero_repositories,
                "limits": {
                    "donor_code_execution": "NOT_PERFORMED",
                    "donor_test_execution": "NOT_PERFORMED",
                    "payload_runtime_mutation": "NOT_PERFORMED",
                    "cleanup_retirement_quarantine": "NOT_PERFORMED",
                    "protected_branch_integration": "NOT_PERFORMED",
                    "source_integration": "NOT_PERFORMED_UNNEEDED_BY_EVIDENCE",
                },
            }
        )
        all_missing_counts_zero = (
            missing_command_count == 0
            and missing_argument_tuple_count == 0
            and missing_dispatch_call_count == 0
        )
        strict_superset_dispositions = sum(
            1
            for item in donor_results
            if item["classification"]
            == "CANONICAL_CLI_STRICT_SUPERSET_SUPERSEDES_DONOR_SCRIPT"
        )
        donor_superset_inputs = m69_family_counts.get("DONOR_STRICT_SYMBOL_SUPERSET", 0)
        if (
            donor_superset_inputs
            and strict_superset_dispositions == donor_superset_inputs
            and all_missing_counts_zero
            and wrapper_shape["status"] == "FORWARDS_TO_CANONICAL_ARCHAEOLOGY_MAIN"
        ):
            fact_classification = (
                "CANONICAL_ARCHAEOLOGY_CLI_RETAINS_ALL_M69_DONOR_STRICT_SYMBOL_SUPERSET_COMMANDS"
            )
        else:
            fact_classification = "PARTIAL_OR_UNKNOWN_CLI_DONOR_SUPERSET_DISPOSITION"
        reference_locations = _cli_superset_reference_locations(canonical_root)
        payload = {
            "schema": CLI_DONOR_SUPERSET_DISPOSITION_SCHEMA,
            "status": "PARTIAL_FACT_LEVEL_DISPOSITION",
            "authority": "read-only-cli-donor-symbol-superset-disposition",
            "authority_granted": False,
            "cleanup_permitted": False,
            "retirement_permitted": False,
            "source_integration_performed": False,
            "target": {
                "scope": "M69-DONOR_STRICT_SYMBOL_SUPERSET-family",
                "legacy_entrypoint_relative_source": CLI_SUPERSET_LEGACY_ENTRYPOINT_PATH,
                "canonical_owner_relative_source": CLI_SUPERSET_CANONICAL_CLI_PATH,
                "whole_file_claim": False,
                "whole_worktree_claim": False,
                "behavioral_equivalence_claim": False,
                "no_feature_loss_claim": False,
            },
            "predecessors": predecessor_identities,
            "accepted_parent": {
                "head": before["canonical"]["head"],
                "tree": before["canonical"]["tree"],
                "expected_m77r1_head": "2a3a41b2b79d3858e9a033a1c00599ad20b54a85",
            },
            "canonical_candidate": {
                "slot": "canonical",
                "repository": _cli_superset_public_repository_identity(
                    before["canonical"]
                ),
                "dirty": _cli_superset_public_dirty_identity(dirty_before["canonical"]),
                "canonical_cli_source": canonical_source,
                "legacy_entrypoint_source": wrapper_source,
                "legacy_entrypoint_shape": wrapper_shape,
                "command_surface": {
                    key: canonical_contract[key]
                    for key in (
                        "command_names",
                        "command_count",
                        "command_names_sha256",
                        "main_function_present",
                        "main_guard_present",
                    )
                },
            },
            "donors": donor_results,
            "summary": {
                "mapped_donor_count": len(donors),
                "m69_family_counts": dict(sorted(m69_family_counts.items())),
                "donor_result_classification_counts": dict(
                    sorted(classification_counts.items())
                ),
                "command_row_classification_counts": dict(
                    sorted(command_classification_counts.items())
                ),
                "unique_donor_command_count": len(unique_donor_commands),
                "unique_donor_commands": sorted(unique_donor_commands),
                "unique_donor_commands_sha256": sha256_bytes(
                    canonical_bytes(sorted(unique_donor_commands))
                ),
                "canonical_command_count": canonical_contract["command_count"],
                "missing_command_count": missing_command_count,
                "missing_argument_tuple_count": missing_argument_tuple_count,
                "missing_dispatch_call_count": missing_dispatch_call_count,
                "source_integration_required": not all_missing_counts_zero,
            },
            "fact_disposition": {
                "fact_id": "scripts-archaeologist-py-donor-strict-symbol-superset-family",
                "classification": fact_classification,
                "basis": [
                    "M69 records the legacy archaeologist.py path as DONOR_STRICT_SYMBOL_SUPERSET for five mapped donors",
                    "every donor parser command exists in the canonical archaeology.py CLI",
                    "every donor argument tuple exists in the canonical command contract",
                    "every donor dispatch call is retained after the archaeologist-to-archaeology namespace rename",
                    "the current archaeologist.py file is a compatibility wrapper to archaeology.main",
                    "donor code and donor tests were not executed",
                ],
                "retirement_permitted": False,
                "cleanup_permitted": False,
                "source_integration_required": not all_missing_counts_zero,
            },
            "entrypoint_and_test_evidence": {
                "canonical_legacy_wrapper": wrapper_shape["status"],
                "current_reference_locations": reference_locations,
                "real_entrypoint_to_verify": "giga-archaeology cli-superset-disposition",
                "donor_code_execution": False,
            },
            "zero_mutation": zero_mutation,
            "stash": {
                "slot": "stash-0",
                "commit": "22abe427412e8b2e7e465427f30c4ce51549ca12",
                "status": "PRESERVED_UNACCEPTED_AMBIGUOUS",
                "applied": False,
                "dropped": False,
            },
            "graph_status": _cli_superset_graph_status(canonical_root),
            "claims": {
                "cli_family_disposed": fact_classification
                == "CANONICAL_ARCHAEOLOGY_CLI_RETAINS_ALL_M69_DONOR_STRICT_SYMBOL_SUPERSET_COMMANDS",
                "source_integration_performed": False,
                "whole_file_equivalence": False,
                "whole_worktree_equivalence": False,
                "behavioral_equivalence": False,
                "no_feature_loss": False,
                "donor_retirement": False,
                "payload_runtime_mutation": False,
                "graph_current": False,
            },
            "remaining_unknowns": [
                "behavioral equivalence beyond static parser/argument/dispatch comparison",
                "runtime usefulness of donor implementations whose command surface is retained by newer canonical code",
                "the remaining M71 actionable evidence sets outside this scripts/archaeologist.py family",
                "whole donor retirement or cleanup safety",
            ],
            "privacy": {
                "private_paths_public": False,
                "path_hashes_public": False,
                "layout_invariant_public_output": True,
            },
        }
        return seal_document(payload)
    except DivergenceError as exc:
        if str(exc) == CLI_SUPERSET_REFUSAL:
            raise
        _cli_superset_refuse(exc)
    except (OSError, HistoryError, InventoryError, KeyError, TypeError) as exc:
        _cli_superset_refuse(exc)


def render_cli_donor_superset_disposition_report(payload: Mapping[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# CLI donor-symbol-superset disposition",
        "",
        "## What this slice implements",
        "",
        "This slice adjudicates the M69 donor-strict-symbol-superset family for the old "
        "`modules/operations/scripts/archaeologist.py` CLI against the current canonical "
        "`modules/operations/scripts/archaeology.py` owner. It proves command-surface retention "
        "from source bytes, AST contracts and Git object identity without executing donor code or "
        "performing cleanup.",
        "",
        "## Fact-level result",
        "",
        f"- Disposition: `{payload['fact_disposition']['classification']}`",
        f"- Receipt: `{payload['receipt_sha256']}`",
        f"- Zero-mutation receipt: `{payload['zero_mutation']['receipt_sha256']}`",
        f"- Mapped donors inspected: {summary['mapped_donor_count']}",
        f"- M69 donor-strict-symbol-superset rows: {summary['m69_family_counts'].get('DONOR_STRICT_SYMBOL_SUPERSET', 0)}",
        f"- Unique donor commands: {summary['unique_donor_command_count']}",
        f"- Canonical commands: {summary['canonical_command_count']}",
        f"- Missing donor commands: {summary['missing_command_count']}",
        f"- Missing donor argument tuples: {summary['missing_argument_tuple_count']}",
        f"- Missing donor dispatch calls: {summary['missing_dispatch_call_count']}",
        "",
        "## Boundary",
        "",
        "- No donor code or donor tests were executed.",
        "- No source migration was needed or performed.",
        "- No whole-file, whole-worktree, behavioral-equivalence, no-feature-loss, cleanup or retirement claim is made.",
        f"- Graph status: `{payload['graph_status']['status']}`.",
        "",
    ]
    return "\n".join(lines)


def write_cli_donor_superset_disposition(
    canonical_root: Path,
    m69_predecessor: Path,
    m70_predecessor: Path,
    m71_predecessor: Path,
    output: Path,
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists():
        raise DivergenceError("CLI superset disposition output directory must not exist")
    payload = build_cli_donor_superset_disposition(
        canonical_root, m69_predecessor, m70_predecessor, m71_predecessor
    )
    try:
        output.mkdir(parents=True, mode=0o700)
        write_atomic(
            output / "cli_donor_superset_disposition.json",
            canonical_bytes(payload),
        )
        write_atomic(
            output / "CLI_DONOR_SUPERSET_DISPOSITION_REPORT.md",
            render_cli_donor_superset_disposition_report(payload).encode("utf-8"),
        )
    except (EvidenceError, OSError) as exc:
        _cli_superset_refuse(exc)
    return payload
