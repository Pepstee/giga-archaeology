"""Explicit-root location observations; declarations never grant map authority.

No directory walk, project content read, remote contact, or worktree traversal is
performed. Dirty state is deliberately limited to the index versus HEAD: a clean
index cannot establish a clean working tree without inspecting project contents.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from .evidence import canonical_bytes, seal_document, sha256_bytes, validate_self_hash, write_atomic
from .navigation_inventory import SENSITIVE_COMPONENTS
from .os_support import git_environment, git_executable

ROOTS_SCHEMA = "giga.archaeology.location-roots.v1"
LOCATION_SCHEMA = "giga.archaeology.location-inventory.v1"
QUERY_SCHEMA = "giga.archaeology.location-query.v1"
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_AUTHORITY_SUMMARY_TEXT = 128
CANON_LEVELS = frozenset({"canonical", "canonical_development_owner", "canonical_source", "canonical_runtime"})


class LocationInventoryError(ValueError):
    """A location request or receipt violates the bounded observation contract."""


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise LocationInventoryError(f"{label} must be a non-empty string without control characters")
    return value


def _time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("timezone missing")
        return result.astimezone(UTC)
    except (TypeError, ValueError, AttributeError) as exc:
        raise LocationInventoryError("timestamps must be timezone-aware ISO 8601") from exc


def _timestamp(value: str | None) -> str:
    instant = datetime.now(UTC) if value is None else _time(value)
    return instant.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _path(value: Any) -> str:
    value = _text(value, "path")
    path = PureWindowsPath(value) if PureWindowsPath(value).drive else PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts:
        raise LocationInventoryError("location paths must be absolute without parent traversal")
    return str(path)


def _no_symlinks(path: Path) -> None:
    # Ancestor lstat only, never enumerate a directory or follow a link.
    for part in (*reversed(path.parents), path):
        if stat.S_ISLNK(part.lstat().st_mode):
            raise LocationInventoryError("symlink path is outside the observation policy")


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    try:
        _no_symlinks(path.absolute())
        if not stat.S_ISREG(path.stat().st_mode):
            raise LocationInventoryError("input must be a regular file")
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise LocationInventoryError("input exceeds size limit")
        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in items:
                if key in result:
                    raise LocationInventoryError("duplicate JSON key")
                result[key] = value
            return result
        payload = json.loads(raw, object_pairs_hook=pairs)
        if not isinstance(payload, dict):
            raise LocationInventoryError("input must be a JSON object")
        return payload, sha256_bytes(raw)
    except (OSError, UnicodeError, ValueError) as exc:
        raise LocationInventoryError(f"cannot read location evidence: {type(exc).__name__}") from exc


def _bounded_authority_summary(value: Any, text_fields: Sequence[str],
                               boolean_fields: Sequence[str] = ()) -> dict[str, Any]:
    """Allowlist short context fields; never copy nested operational records.

    Unsupported or oversized values are omitted, not truncated into a potentially
    misleading authority claim. The input digest binds the full original record.
    """
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for field in text_fields:
        item = value.get(field)
        if (isinstance(item, str) and 0 < len(item) <= MAX_AUTHORITY_SUMMARY_TEXT
                and not any(ord(c) < 32 for c in item)):
            result[field] = item
    for field in boolean_fields:
        if isinstance(value.get(field), bool):
            result[field] = value[field]
    return result


def load_location_roots(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read one explicit roots document or the registered machine-authority shape.

    Bounded host/global declarations remain context, never promoted into a
    per-project canonical owner. Unsupported schemas fail before any root probe.
    """
    payload, digest = _read_json(path)
    roots: list[dict[str, Any]] = []
    if payload.get("schema") == ROOTS_SCHEMA:
        roots = payload.get("roots")
    elif payload.get("schema") == "giga.machine-authority.v1":
        hosts = payload.get("hosts")
        if not isinstance(hosts, dict):
            raise LocationInventoryError("authority register hosts must be an object")
        for host, declaration in sorted(hosts.items()):
            if not isinstance(declaration, dict) or not isinstance(declaration.get("roots"), list):
                raise LocationInventoryError("authority host must have an explicit roots list")
            for entry in declaration["roots"]:
                if not isinstance(entry, dict):
                    raise LocationInventoryError("authority root must be an object")
                roots.append({
                    "project_id": entry.get("id"), "host": host, "path": entry.get("path"),
                    "declared_owner": entry.get("owner"),
                    "authority_level": "project-entry",
                    "canon_level": entry.get("status", "unknown"),
                    "role": entry.get("purpose", "unknown"),
                    "declared_head": entry.get("verified_head"),
                    "declared_at": entry.get("verified_at"),
                    "authority_source": "machine-authority-register",
                    "host_role": declaration.get("role"),
                })
    else:
        raise LocationInventoryError("unsupported location roots schema")
    if not isinstance(roots, list) or not roots or len(roots) > 1000:
        raise LocationInventoryError("roots must contain between 1 and 1000 declarations")
    return roots, {"kind": "registered-input",
                   "sha256": digest, "schema": payload["schema"],
                   "global_authority": _bounded_authority_summary(
                       payload.get("authority"), ("canonical_host", "promotion_host"),
                       ("automatic_remote_promotion",)),
                   "handoff_summary": _bounded_authority_summary(
                       payload.get("development_handoff"), ("status", "target_host"))}


def _declaration(root: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(root, Mapping):
        raise LocationInventoryError("root declaration must be an object")
    result = {key: _text(root.get(key), key) for key in ("project_id", "host")}
    result["path"] = _path(root.get("path"))
    for key in ("declared_owner", "declared_head", "declared_at", "host_role"):
        value = root.get(key)
        result[key] = None if value is None else _text(value, key)
    for key in ("role", "canon_level", "authority_level", "authority_source"):
        result[key] = _text(root.get(key, "unknown"), key)
    result["excluded"] = root.get("excluded", False)
    if not isinstance(result["excluded"], bool):
        raise LocationInventoryError("excluded must be a boolean")
    if result["declared_at"] is not None:
        _time(result["declared_at"])
    return result


def _git(root: Path, args: Sequence[str], accepted: tuple[int, ...] = (0,)) -> tuple[int, bytes]:
    executable = git_executable()
    if executable is None:
        raise LocationInventoryError("GIT_UNAVAILABLE")
    environment = git_environment(executable)
    environment.update({"GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1"})
    try:
        result = subprocess.run(
            [executable, "--no-optional-locks", "-c", "core.fsmonitor=false",
             "-c", f"core.hooksPath={os.devnull}", *args],
            cwd=root, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LocationInventoryError(type(exc).__name__) from exc
    if result.returncode not in accepted or len(result.stdout) > MAX_INPUT_BYTES:
        # Raw stderr may contain credentials from repository configuration.
        raise LocationInventoryError("GIT_METADATA_UNAVAILABLE")
    return result.returncode, result.stdout


def _remote_identity(value: str) -> str | None:
    """Retain only conservative host/repository identity, never credentials."""
    try:
        if "://" in value:
            url = urlsplit(value)
            if url.scheme not in {"https", "http", "ssh", "git"}:
                return None
            host, path = url.hostname, url.path.lstrip("/")
        else:
            match = re.fullmatch(r"(?:[^@/:\s]+@)?([^/:\s]+):([^?#\s]+)", value)
            if not match:
                return None
            host, path = match.groups()
        if not host or not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            return None
        if not path or not re.fullmatch(r"[A-Za-z0-9_./-]+", path) or ".." in path.split("/"):
            return None
        return host.lower() + "/" + path.removesuffix(".git")
    except ValueError:
        return None


def _worktrees(raw: bytes) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for block in raw.decode("utf-8", "strict").split("\0\0"):
        if not block:
            continue
        fields = {}
        for line in block.split("\0"):
            if line:
                key, _, value = line.partition(" ")
                fields[key] = value
        if "worktree" not in fields:
            raise LocationInventoryError("malformed worktree metadata")
        result.append({"path": fields["worktree"], "head": fields.get("HEAD"),
                       "branch": fields.get("branch"), "bare": "bare" in fields,
                       "detached": "detached" in fields, "locked": "locked" in fields,
                       "prunable": "prunable" in fields, "path_inspected": False,
                       "evidence_source": "git-worktree-list-porcelain-z"})
    return sorted(result, key=lambda item: item["path"])


def _observe(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "OBSERVED", "branch": None, "head": None,
        "dirty": {"state": "UNKNOWN", "index": "UNKNOWN", "worktree": "NOT_INSPECTED",
                  "untracked": "NOT_INSPECTED"}, "worktrees": [], "remotes": [],
        "unknowns": ["working_tree_and_untracked_dirty_state", "copy_equivalence"],
        "evidence_sources": ["root-lstat"]}
    try:
        _no_symlinks(root)
        if not stat.S_ISDIR(root.lstat().st_mode):
            result["status"] = "NOT_DIRECTORY"
            return result
        marker = root / ".git"
        # Require a direct Git marker: never discover a repository in a parent.
        marker_mode = marker.lstat().st_mode
        if not (stat.S_ISDIR(marker_mode) or stat.S_ISREG(marker_mode)):
            raise LocationInventoryError("UNSUPPORTED_GIT_MARKER")
    except FileNotFoundError:
        result["status"] = "NOT_GIT" if root.is_dir() else "MISSING"
        return result
    except PermissionError:
        result["status"] = "INACCESSIBLE"
        return result
    except (OSError, LocationInventoryError):
        result["status"] = "REFUSED_PATH"
        return result

    def read(label: str, args: Sequence[str], accepted: tuple[int, ...] = (0,)) -> tuple[int, bytes] | None:
        try:
            data = _git(root, args, accepted)
            result["evidence_sources"].append("git-" + label)
            return data
        except LocationInventoryError:
            result["unknowns"].append(label)
            result["status"] = "PARTIAL"
            return None

    head = read("head", ["rev-parse", "--verify", "HEAD"])
    if head:
        value = head[1].decode("ascii", "replace").strip()
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
            result["head"] = value
        else:
            result["status"] = "PARTIAL"
            result["unknowns"].append("invalid_head_metadata")
    branch = read("branch", ["symbolic-ref", "--quiet", "HEAD"], (0, 1))
    if branch:
        result["branch"] = branch[1].decode("utf-8", "strict").strip() if branch[0] == 0 else None
        result["detached"] = branch[0] == 1
    if head:
        index = read("index-vs-head", ["diff-index", "--cached", "--quiet", "--no-ext-diff",
                     "--no-textconv", "--ignore-submodules=all", "HEAD", "--"], (0, 1))
        if index:
            result["dirty"]["index"] = "DIRTY" if index[0] else "CLEAN"
            if index[0]:
                result["dirty"]["state"] = "DIRTY"
    trees = read("worktrees", ["worktree", "list", "--porcelain", "-z"])
    if trees:
        result["worktrees"] = _worktrees(trees[1])
    remotes = read("local-remote-config", ["config", "--local", "--no-includes", "--null",
                   "--get-regexp", r"^remote\..*\.url$"], (0, 1))
    if remotes:
        for item in remotes[1].decode("utf-8", "strict").split("\0"):
            if item:
                key, _, url = item.partition("\n")
                identity = _remote_identity(url)
                result["remotes"].append({"name": key[7:-4], "identity": identity,
                                          "status": "OBSERVED" if identity else "REDACTED_OR_UNSUPPORTED"})
        result["remotes"].sort(key=lambda item: (item["name"], item["identity"] or ""))
    after = read("head-after", ["rev-parse", "--verify", "HEAD"])
    if head and after and head[1] != after[1]:
        result["status"] = "UNSTABLE"
        result["unknowns"].append("head_changed_during_observation")
    result["unknowns"] = sorted(set(result["unknowns"]))
    return result


def inspect_locations(
    roots: Sequence[Mapping[str, Any]], *, local_host: str,
    observed_at: str | None = None, excluded_roots: Sequence[str] = (),
    project_ids: Sequence[str] = (), evidence_source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Observe exactly the declared local roots; remote/excluded roots are gaps."""
    _text(local_host, "local_host")
    now = _timestamp(observed_at)
    if not roots or len(roots) > 1000:
        raise LocationInventoryError("provide between 1 and 1000 roots")
    declarations = sorted((_declaration(root) for root in roots), key=canonical_bytes)
    if len({canonical_bytes(d) for d in declarations}) != len(declarations):
        raise LocationInventoryError("duplicate root declarations")
    excluded = tuple(Path(_path(p)) for p in excluded_roots)
    selected = set(project_ids)
    if selected - {d["project_id"] for d in declarations}:
        raise LocationInventoryError("selected project ID is absent from the register")
    rows = []
    for declaration in declarations:
        path = Path(declaration["path"])
        reason = None
        if selected and declaration["project_id"] not in selected:
            reason = "PROJECT_NOT_SELECTED"
        elif declaration["excluded"]:
            reason = "EXCLUDED"
        elif declaration["host"] != local_host:
            reason = "REMOTE_HOST_NOT_INSPECTED"
        elif not path.is_absolute():
            reason = "FOREIGN_PATH_SYNTAX"
        elif any(path == p or path.is_relative_to(p) for p in excluded):
            reason = "EXCLUDED"
        elif path in {Path(path.anchor), Path.home(), *map(Path, ("/home", "/Users", "/srv", "/etc", "/usr", "/var", "/tmp"))}:
            reason = "BROAD_ROOT_REFUSED"
        elif any(part.casefold() in SENSITIVE_COMPONENTS for part in path.parts):
            reason = "SENSITIVE_ROOT_EXCLUDED"
        observation = {"status": reason, "head": None, "branch": None,
                       "dirty": {"state": "UNKNOWN", "index": "UNKNOWN",
                                 "worktree": "NOT_INSPECTED", "untracked": "NOT_INSPECTED"},
                       "worktrees": [], "remotes": [], "evidence_sources": [],
                       "unknowns": ["location_not_inspected"]}
        if not reason:
            try:
                observation = _observe(path)
            except (UnicodeError, LocationInventoryError):
                observation["status"] = "INVALID_GIT_METADATA"
                observation["unknowns"] = ["git_metadata_could_not_be_decoded"]
        rows.append({"location_id": sha256_bytes(canonical_bytes(declaration)),
                     "declared": declaration, "observed": observation,
                     "observed_at": None if reason else now,
                     "declared_head_matches_observed": None if not declaration["declared_head"] or not observation["head"]
                     else declaration["declared_head"] == observation["head"]})
    conflicts = []
    for project in sorted({d["project_id"] for d in declarations}):
        for level in sorted(CANON_LEVELS):
            claims = [r for r in rows if r["declared"]["project_id"] == project and r["declared"]["canon_level"] == level]
            if len({(r["declared"]["host"], r["declared"]["path"], r["declared"]["declared_owner"]) for r in claims}) > 1:
                conflicts.append({"kind": "MULTIPLE_DECLARED_CANONS", "project_id": project,
                                  "canon_level": level, "location_ids": sorted(r["location_id"] for r in claims)})
    for host, path in sorted({(d["host"], d["path"]) for d in declarations}):
        claims = [r for r in rows if (r["declared"]["host"], r["declared"]["path"]) == (host, path)]
        if len({r["location_id"] for r in claims}) > 1:
            conflicts.append({"kind": "CONFLICTING_PATH_DECLARATIONS", "host": host, "path": path,
                              "location_ids": sorted(r["location_id"] for r in claims)})
    return seal_document({
        "schema": LOCATION_SCHEMA, "authority": "read-only-location-observation",
        "authority_granted": False, "cleanup_permitted": False, "safe_to_delete": False,
        "observed_at": now, "local_host": local_host, "locations": rows, "conflicts": conflicts,
        "evidence_source": dict(evidence_source or {"kind": "explicit-roots-api"}),
        "coverage": {"global_completeness": False,
            "requested_roots": [{"host": d["host"], "path": d["path"]} for d in declarations],
            "attempted_roots": [r["declared"]["path"] for r in rows if r["observed_at"]],
            "scanned_roots": [r["declared"]["path"] for r in rows if r["observed"]["status"] in {"OBSERVED", "PARTIAL", "UNSTABLE"}],
            "excluded_roots": sorted(str(p) for p in excluded), "selected_project_ids": sorted(selected),
            "gaps": [{"location_id": r["location_id"], "reason": r["observed"]["status"]} for r in rows if r["observed"]["status"] != "OBSERVED"],
            "unknowns": ["unregistered_locations", "working_tree_and_untracked_dirty_state",
                         "remote_liveness", "listed_worktree_path_state", "copy_equivalence"],
            "worktree_paths_followed": False, "project_contents_read": False},
    })


def refresh_locations(roots: Sequence[Mapping[str, Any]], output: Path, **kwargs: Any) -> dict[str, Any]:
    """Publish one immutable receipt outside every declared local root."""
    local_host = kwargs.get("local_host")
    destination = output.resolve(strict=False)
    # Check existing output ancestors without admitting a redirected publication.
    for parent in (*reversed(output.absolute().parents), output.absolute()):
        if parent.is_symlink():
            raise LocationInventoryError("symlink output is forbidden")
    for root in roots:
        declaration = _declaration(root)
        if declaration["host"] == local_host:
            path = Path(declaration["path"])
            if destination == path or destination.is_relative_to(path):
                raise LocationInventoryError("output must be outside all declared local roots")
    if output.exists() or output.is_symlink():
        raise LocationInventoryError("refresh output must be a new receipt file")
    payload = inspect_locations(roots, **kwargs)
    try:
        write_atomic(output, canonical_bytes(payload))
    except (OSError, ValueError) as exc:
        raise LocationInventoryError("cannot publish immutable location receipt") from exc
    return payload


def query_locations(receipt: Path, query: str = "", *, as_of: str | None = None,
                    max_age_seconds: int = 86400) -> dict[str, Any]:
    """Query a sealed snapshot only; querying never reopens observed locations."""
    payload, digest = _read_json(receipt)
    try:
        validate_self_hash(payload)
    except ValueError as exc:
        raise LocationInventoryError("location receipt hash mismatch") from exc
    if payload.get("schema") != LOCATION_SCHEMA or any(payload.get(k) is not False for k in ("authority_granted", "cleanup_permitted", "safe_to_delete")):
        raise LocationInventoryError("invalid location receipt schema or authority boundary")
    rows = payload.get("locations")
    if not isinstance(rows, list) or not isinstance(payload.get("conflicts"), list):
        raise LocationInventoryError("invalid location receipt records")
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("global_completeness") is not False:
        raise LocationInventoryError("invalid location receipt coverage")
    if not isinstance(query, str) or any(ord(c) < 32 for c in query):
        raise LocationInventoryError("query must be text without control characters")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds < 0:
        raise LocationInventoryError("max_age_seconds must be a nonnegative integer")
    now = _timestamp(as_of)
    results = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("observed"), dict) or "observed_at" not in row:
            raise LocationInventoryError("invalid location record")
        declared = _declaration(row.get("declared"))
        if row.get("location_id") != sha256_bytes(canonical_bytes(declared)):
            raise LocationInventoryError("location identity mismatch")
        if query.casefold() not in canonical_bytes(row["declared"]).decode().casefold():
            continue
        timestamp = row["observed_at"]
        age = None if timestamp is None else (_time(now) - _time(timestamp)).total_seconds()
        freshness = "UNKNOWN" if age is None or age < 0 else "STALE" if age > max_age_seconds else "WITHIN_MAX_AGE"
        declared_time = declared["declared_at"]
        declared_age = None if declared_time is None else (_time(now) - _time(declared_time)).total_seconds()
        declared_freshness = ("UNKNOWN" if declared_age is None or declared_age < 0 else
                              "STALE" if declared_age > max_age_seconds else "WITHIN_MAX_AGE")
        results.append({**row, "freshness": freshness, "age_seconds": age,
                        "declaration_freshness": declared_freshness})
    return seal_document({"schema": QUERY_SCHEMA, "authority_granted": False,
        "cleanup_permitted": False, "safe_to_delete": False, "query": query, "as_of": now,
        "max_age_seconds": max_age_seconds, "source_receipt_sha256": payload["receipt_sha256"],
        "source_file_sha256": digest, "results": results, "coverage": payload["coverage"],
        "conflicts": payload["conflicts"], "live_state_rechecked": False})
