"""Status-only retrospective capability feeds from accepted Archaeology evidence.

The exact v1 consumer contract has no promotion field: the canonical adoption consumer adds
``promotion_authority=false`` when it ingests the feed.  This producer never infers a capability
candidate from generic reachability, duplication or semantic facts.  Until a reviewed candidate
fact class exists, the truthful candidate set is empty.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import subprocess
from typing import Any
from collections.abc import Mapping

from .mapper import current_mapper_run


CANDIDATE_FEED_SCHEMA = "giga.retrospective-capability-candidates.v1"
CANDIDATE_FEED_SCHEMA_V2 = "giga.retrospective-capability-candidates.v2"
PRODUCER_VERSION = "giga.archaeologist.mapper-capability-feed.v1"
PRODUCER_VERSION_V2 = "giga.archaeologist.mapper-capability-feed.v2"
REVIEWED_ARCHAEOLOGIST_CANDIDATE_ID = "archaeologist-mapper-disconnected"
REVIEWED_ARCHAEOLOGIST_CAPABILITY_ID = "archaeologist-mapper"
DEFAULT_EVIDENCE_LEDGER = Path(
    "architecture/archaeologist/feeds/"
    "retrospective-capability-feed-evidence-gap-ledger.json"
)
GIT_OBJECT_SOURCE_STATUS_REVIEWED = "TRACKED_REVIEWED_HISTORY"
GIT_OBJECT_REPO_ALIAS = "giga-user"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


class CapabilityFeedError(ValueError):
    """The mapper cannot emit a current, consumer-compatible candidate feed."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _self_hash(payload: Mapping[str, Any]) -> str:
    material = dict(payload)
    material.pop("self_sha256", None)
    return _sha256(
        json.dumps(
            material, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    )


def _reject_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant: {value}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CapabilityFeedError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise CapabilityFeedError(f"{label} must be a JSON object")
    return value


def _validate_self_hash(payload: Mapping[str, Any], label: str) -> None:
    recorded = payload.get("self_sha256")
    if not isinstance(recorded, str) or _SHA256.fullmatch(recorded) is None:
        raise CapabilityFeedError(f"{label} has an invalid self hash")
    if recorded != _self_hash(payload):
        raise CapabilityFeedError(f"{label} self hash differs")


def _timestamp(value: str) -> str:
    if not isinstance(value, str):
        raise CapabilityFeedError("generated_at must be a timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CapabilityFeedError("generated_at is not a real timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CapabilityFeedError("generated_at must include a UTC offset")
    return value


def _relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CapabilityFeedError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or any(not part for part in path.parts)
    ):
        raise CapabilityFeedError(f"{label} must be repository-relative")
    return str(path)


def _oid(value: object, label: str) -> str:
    if not isinstance(value, str) or _GIT_OID.fullmatch(value) is None:
        raise CapabilityFeedError(f"{label} is not a valid Git object id")
    return value


def _git(root: Path, *arguments: str) -> bytes:
    environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
        "TZ": "UTC",
    }
    process = subprocess.run(
        [
            "/usr/bin/git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(root),
            *arguments,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
    )
    if process.returncode != 0:
        raise CapabilityFeedError("Git identity check failed")
    return process.stdout


def _git_text(root: Path, *arguments: str) -> str:
    return _git(root, *arguments).decode("utf-8", "strict").strip()


def _read_repository_file(root: Path, relative: str, label: str) -> bytes:
    path = root / _relative(relative, label)
    if not path.is_file():
        raise CapabilityFeedError(f"{label} is unavailable")
    return path.read_bytes()


def _verify_current_head(manifest: dict[str, Any]) -> Path:
    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        raise CapabilityFeedError("mapper has no repository identity")
    root_value = repository.get("root")
    git = repository.get("git")
    if not isinstance(root_value, dict) or not isinstance(git, dict):
        raise CapabilityFeedError("mapper repository identity is incomplete")
    try:
        root = Path(root_value.get("path", "")).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CapabilityFeedError("mapper repository root is unavailable") from exc
    if git.get("stable_during_scan") is not True:
        raise CapabilityFeedError("mapper source changed during its inventory scan")
    after = git.get("after")
    if not isinstance(after, dict) or after.get("clean") is not True:
        raise CapabilityFeedError("mapper does not bind a clean Git source state")
    head = _git(root, "rev-parse", "HEAD").decode("ascii", "strict").strip()
    tree = _git(root, "rev-parse", "HEAD^{tree}").decode("ascii", "strict").strip()
    status = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if status:
        raise CapabilityFeedError("current source differs from clean Git HEAD")
    if head != git.get("head") or tree != git.get("tree"):
        raise CapabilityFeedError("mapper source commit/tree is not current Git HEAD")
    return root


def _reviewed_remote_retains_commit(root: Path, commit: str) -> None:
    refs = _git(
        root,
        "for-each-ref",
        "--format=%(refname)",
        f"--contains={commit}",
        "refs/remotes/",
    )
    if not refs.strip():
        raise CapabilityFeedError("reviewed evidence is not retained by a remote ref")


def _git_object_source_ref(
    root: Path,
    *,
    commit: str,
    tree: str,
    path: str,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    commit = _oid(commit, "evidence commit")
    tree = _oid(tree, "evidence tree")
    path = _relative(path, "evidence path")
    if _git_text(root, "rev-parse", "--verify", f"{commit}^{{commit}}") != commit:
        raise CapabilityFeedError("evidence commit cannot be resolved exactly")
    if _git_text(root, "rev-parse", "--verify", f"{commit}^{{tree}}") != tree:
        raise CapabilityFeedError("evidence tree does not match commit")
    _reviewed_remote_retains_commit(root, commit)
    listing = _git(root, "ls-tree", "-z", commit, "--", path)
    entries = [entry for entry in listing.split(b"\0") if entry]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise CapabilityFeedError("evidence path is not a unique tracked blob")
    metadata, listed_path = entries[0].split(b"\t", 1)
    parts = metadata.split()
    if (
        len(parts) != 3
        or parts[1] != b"blob"
        or listed_path.decode("utf-8", "strict") != path
    ):
        raise CapabilityFeedError("evidence path is not a tracked file blob")
    blob = parts[2].decode("ascii", "strict")
    raw = _git(root, "cat-file", "blob", blob)
    record = {
        "kind": "git-object-file",
        "repo_alias": GIT_OBJECT_REPO_ALIAS,
        "commit": commit,
        "tree": tree,
        "path": path,
        "git_blob_oid": blob,
        "sha256": _sha256(raw),
        "bytes": len(raw),
        "source_status": GIT_OBJECT_SOURCE_STATUS_REVIEWED,
    }
    if expected is not None:
        expected_record = {
            "path": _relative(expected.get("path"), "accepted evidence path"),
            "git_blob_oid": _oid(
                expected.get("git_blob_oid"), "accepted evidence blob"
            ),
            "sha256": expected.get("sha256"),
            "bytes": expected.get("bytes"),
        }
        if (
            not isinstance(expected_record["sha256"], str)
            or _SHA256.fullmatch(expected_record["sha256"]) is None
            or not isinstance(expected_record["bytes"], int)
            or isinstance(expected_record["bytes"], bool)
        ):
            raise CapabilityFeedError("accepted evidence digest is invalid")
        if {
            "path": record["path"],
            "git_blob_oid": record["git_blob_oid"],
            "sha256": record["sha256"],
            "bytes": record["bytes"],
        } != expected_record:
            raise CapabilityFeedError("accepted evidence differs from Git object")
    return record


def _source_commit_for_ledger(root: Path, ledger_path: str) -> str:
    commit = _git_text(root, "rev-list", "-n", "1", "HEAD", "--", ledger_path)
    if not commit:
        raise CapabilityFeedError("accepted evidence ledger has no Git history")
    return _oid(commit, "accepted evidence commit")


def _legacy_inventory_manifest_sha256(root: Path, ledger: Mapping[str, Any]) -> str:
    current_static = ledger.get("current_static_feed")
    if not isinstance(current_static, Mapping):
        raise CapabilityFeedError("accepted evidence ledger has no static feed binding")
    static_path = _relative(current_static.get("path"), "static v1 feed path")
    static_feed = _strict_json(
        _read_repository_file(root, static_path, "static v1 feed"), "static v1 feed"
    )
    _validate_self_hash(static_feed, "static v1 feed")
    identity = static_feed.get("inventory_manifest_sha256")
    if not isinstance(identity, str) or _SHA256.fullmatch(identity) is None:
        raise CapabilityFeedError("static v1 feed inventory identity is invalid")
    return identity


def _reviewed_archaeologist_candidate(
    root: Path, ledger: Mapping[str, Any], *, source_commit: str
) -> dict[str, Any]:
    intents = ledger.get("requested_candidate_intents")
    if not isinstance(intents, list):
        raise CapabilityFeedError("accepted evidence ledger has no candidate intents")
    matches = [
        item
        for item in intents
        if isinstance(item, Mapping)
        and item.get("candidate_id") == REVIEWED_ARCHAEOLOGIST_CANDIDATE_ID
    ]
    if len(matches) != 1:
        raise CapabilityFeedError("accepted Archaeologist candidate evidence is unique")
    intent = matches[0]
    if (
        intent.get("capability_id") != REVIEWED_ARCHAEOLOGIST_CAPABILITY_ID
        or intent.get("requested_disposition") != "DISCONNECTED"
    ):
        raise CapabilityFeedError("accepted Archaeologist candidate intent is invalid")
    accepted_evidence = intent.get("accepted_evidence")
    if not isinstance(accepted_evidence, list) or not accepted_evidence:
        raise CapabilityFeedError("accepted Archaeologist candidate lacks evidence")
    source_tree = _git_text(root, "rev-parse", f"{source_commit}^{{tree}}")
    source_refs = [
        _git_object_source_ref(
            root,
            commit=source_commit,
            tree=source_tree,
            path=str(item.get("path")),
            expected=item,
        )
        for item in sorted(accepted_evidence, key=lambda row: str(row.get("path", "")))
    ]
    logical_ids = {
        (record["kind"], record["repo_alias"], record["commit"], record["path"])
        for record in source_refs
    }
    if len(logical_ids) != len(source_refs):
        raise CapabilityFeedError("accepted Archaeologist evidence has duplicates")
    return {
        "candidate_id": REVIEWED_ARCHAEOLOGIST_CANDIDATE_ID,
        "capability_id": REVIEWED_ARCHAEOLOGIST_CAPABILITY_ID,
        "disposition": "DISCONNECTED",
        "owner_hint": "giga-user/operations/archaeology",
        "source_refs": source_refs,
        "entrypoint_hints": [
            "python3 modules/operations/scripts/archaeology.py mapper-query capability",
            "python3 modules/operations/scripts/archaeology.py mapper-audit",
        ],
        "reason": (
            "Accepted Archaeology mapper/navigation capability evidence exists in "
            "retained producer Git history, but the adoption consumer has no adopted "
            "archaeologist-mapper manifest. This feed is status-only."
        ),
    }


def build_reviewed_archaeologist_v2_capability_feed(
    repository_root: Path,
    *,
    generated_at: str,
    evidence_ledger: Path = DEFAULT_EVIDENCE_LEDGER,
    source_commit: str | None = None,
) -> dict[str, Any]:
    """Emit the reviewed non-empty v2 feed for the Archaeologist mapper candidate.

    Research/scientific module evidence remains UNKNOWN and is intentionally not emitted.
    """

    try:
        root = repository_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CapabilityFeedError("repository root is unavailable") from exc
    ledger_path = _relative(str(evidence_ledger), "accepted evidence ledger path")
    ledger = _strict_json(
        _read_repository_file(root, ledger_path, "accepted evidence ledger"),
        "accepted evidence ledger",
    )
    _validate_self_hash(ledger, "accepted evidence ledger")
    evidence_commit = source_commit or _source_commit_for_ledger(root, ledger_path)
    evidence_commit = _oid(evidence_commit, "accepted evidence commit")
    evidence_tree = _git_text(root, "rev-parse", f"{evidence_commit}^{{tree}}")
    ledger_ref = _git_object_source_ref(
        root,
        commit=evidence_commit,
        tree=evidence_tree,
        path=ledger_path,
        expected={
            "path": ledger_path,
            "git_blob_oid": _git_text(
                root, "rev-parse", f"{evidence_commit}:{ledger_path}"
            ),
            "sha256": _sha256(
                _git(root, "cat-file", "blob", f"{evidence_commit}:{ledger_path}")
            ),
            "bytes": len(
                _git(root, "cat-file", "blob", f"{evidence_commit}:{ledger_path}")
            ),
        },
    )
    candidate = _reviewed_archaeologist_candidate(
        root, ledger, source_commit=evidence_commit
    )
    candidate["source_refs"].append(ledger_ref)
    payload = {
        "schema": CANDIDATE_FEED_SCHEMA_V2,
        "producer": (
            f"{PRODUCER_VERSION_V2};"
            f"source_sha256={_sha256(Path(__file__).read_bytes())};"
            f"evidence_commit={evidence_commit};"
            f"evidence_tree={evidence_tree};"
            f"evidence_ledger_self_sha256={ledger['self_sha256']}"
        ),
        "inventory_manifest_sha256": _legacy_inventory_manifest_sha256(root, ledger),
        "generated_at": _timestamp(generated_at),
        "candidates": [candidate],
    }
    payload["self_sha256"] = _self_hash(payload)
    return payload


def write_reviewed_archaeologist_v2_capability_feed(
    repository_root: Path,
    output_directory: Path,
    *,
    generated_at: str,
    evidence_ledger: Path = DEFAULT_EVIDENCE_LEDGER,
    source_commit: str | None = None,
) -> Path:
    """Write the reviewed v2 feed using its self hash as the filename."""

    payload = build_reviewed_archaeologist_v2_capability_feed(
        repository_root,
        generated_at=generated_at,
        evidence_ledger=evidence_ledger,
        source_commit=source_commit,
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    output = (
        output_directory
        / f"retrospective-capability-candidates-v2-{payload['self_sha256']}.json"
    )
    if output.exists():
        existing = _strict_json(output.read_bytes(), "existing v2 feed")
        if existing != payload:
            raise CapabilityFeedError("content-addressed v2 feed path already differs")
        return output
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output


def build_retrospective_capability_feed(
    mapper_store: Path, *, generated_at: str
) -> dict[str, Any]:
    """Emit the exact status-only v1 consumer document from a current clean map.

    Generic mapper facts are intentionally insufficient to assign a capability disposition.  The
    producer therefore emits no false-positive candidates until a separate reviewed fact producer
    supplies that exact fact class.
    """

    run = current_mapper_run(mapper_store)
    _verify_current_head(run.manifest)
    inventory = run.manifest.get("inventory")
    if not isinstance(inventory, dict):
        raise CapabilityFeedError("mapper has no inventory binding")
    inventory_manifest_sha256 = inventory.get("manifest_file_sha256")
    mapper_manifest_sha256 = run.manifest.get("receipt_sha256")
    if (
        not isinstance(inventory_manifest_sha256, str)
        or len(inventory_manifest_sha256) != 64
    ):
        raise CapabilityFeedError("mapper inventory manifest identity is invalid")
    if not isinstance(mapper_manifest_sha256, str) or len(mapper_manifest_sha256) != 64:
        raise CapabilityFeedError("mapper manifest identity is invalid")
    producer_source_sha256 = _sha256(Path(__file__).read_bytes())
    git_identity = run.manifest["repository"]["git"]
    payload = {
        "schema": CANDIDATE_FEED_SCHEMA,
        "producer": (
            f"{PRODUCER_VERSION};source_sha256={producer_source_sha256};"
            f"mapper_manifest_sha256={mapper_manifest_sha256};"
            f"mapper_commit={git_identity['head']};mapper_tree={git_identity['tree']}"
        ),
        "inventory_manifest_sha256": inventory_manifest_sha256,
        "generated_at": _timestamp(generated_at),
        "candidates": [],
    }
    payload["self_sha256"] = _self_hash(payload)
    return payload
