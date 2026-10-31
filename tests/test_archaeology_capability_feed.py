from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from modules.operations.archaeology.capability_feed import (
    CANDIDATE_FEED_SCHEMA,
    CANDIDATE_FEED_SCHEMA_V2,
    DEFAULT_EVIDENCE_LEDGER,
    REVIEWED_ARCHAEOLOGIST_CANDIDATE_ID,
    CapabilityFeedError,
    build_reviewed_archaeologist_v2_capability_feed,
    build_retrospective_capability_feed,
    write_reviewed_archaeologist_v2_capability_feed,
)
from modules.operations.archaeology.mapper import refresh_mapper
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)
from twin_core.capability_adoption import (
    CapabilityAdoptionError,
    compile_adoption_registry,
    observe_liveness,
)


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def _git_value(root: Path, *arguments: str) -> str:
    return (
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        .stdout.decode("utf-8", "strict")
        .strip()
    )


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_blob_record(root: Path, relative: str) -> dict:
    blob = _git_value(root, "rev-parse", f"HEAD:{relative}")
    raw = subprocess.run(
        ["git", "cat-file", "blob", blob],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    return {
        "path": relative,
        "git_blob_oid": blob,
        "sha256": _sha(raw),
        "bytes": len(raw),
    }


@pytest.fixture()
def mapped_repository(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "src").mkdir()
    (root / "src/owner.py").write_text(
        "def dormant_candidate():\n    return 'not classified'\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    refresh_mapper(inventory, mapper)
    return root, mapper


@pytest.fixture()
def reviewed_evidence_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    evidence_files = {
        "capabilities/manifests/archaeologist-mapper.json": '{"id":"archaeologist-mapper"}\n',
        (
            "architecture/archaeology/receipts/"
            "M76_ONE_CLUSTER_EXPORT_SURFACE_DISPOSITION/"
            "export_surface_disposition.json"
        ): '{"status":"ACCEPTED","slice":"M76"}\n',
        (
            "architecture/archaeology/receipts/"
            "M77R2_CLI_DONOR_SYMBOL_SUPERSET_DISPOSITION/"
            "cli_donor_superset_disposition.json"
        ): '{"status":"ACCEPTED","slice":"M77R2"}\n',
    }
    for relative, content in evidence_files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    static_feed_path = (
        root / "architecture/archaeologist/feeds/"
        "retrospective-capability-candidates-a92e873b644b2bbccc2e0e88132daaf9f8abbd7cd467742fe58ec60c10cd17fa.json"
    )
    static_feed_path.parent.mkdir(parents=True, exist_ok=True)
    static_feed = {
        "schema": CANDIDATE_FEED_SCHEMA,
        "producer": "fixture.v1",
        "inventory_manifest_sha256": "3" * 64,
        "generated_at": "2026-08-29T18:28:50Z",
        "candidates": [],
        "self_sha256": "",
    }
    static_feed["self_sha256"] = _self_hash(static_feed)
    static_feed_path.write_text(
        json.dumps(static_feed, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "accepted evidence")
    accepted_evidence = [
        _git_blob_record(root, relative) for relative in evidence_files
    ]
    ledger_path = root / DEFAULT_EVIDENCE_LEDGER
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = {
        "schema": "giga.archaeology.retrospective-capability-feed.evidence-gap-ledger.v1",
        "status": "BLOCKED_NO_TRUTHFUL_NONEMPTY_V1_FEED",
        "current_static_feed": {
            "path": str(static_feed_path.relative_to(root)),
        },
        "requested_candidate_intents": [
            {
                "candidate_id": REVIEWED_ARCHAEOLOGIST_CANDIDATE_ID,
                "capability_id": "archaeologist-mapper",
                "requested_disposition": "DISCONNECTED",
                "decision": "DO_NOT_EMIT_UNDER_V1",
                "accepted_evidence": accepted_evidence,
            },
            {
                "candidate_id": "scientific-research-module-unknown",
                "capability_id": "scientific-research-module",
                "requested_disposition": "UNKNOWN_NOT_AVAILABLE_IN_V1",
                "decision": "DO_NOT_EMIT_UNDER_V1",
            },
        ],
        "self_sha256": "",
    }
    ledger["self_sha256"] = _self_hash(ledger)
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "accepted feed gap ledger")
    _git(root, "update-ref", "refs/remotes/origin/reviewed-archaeology", "HEAD")
    return root


def _self_hash(payload: dict) -> str:
    material = dict(payload)
    material.pop("self_sha256")
    return hashlib.sha256(
        json.dumps(
            material, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def test_feed_matches_exact_consumer_shape_and_mints_no_false_candidates(
    mapped_repository: tuple[Path, Path],
) -> None:
    _root, mapper = mapped_repository
    feed = build_retrospective_capability_feed(
        mapper, generated_at="2026-08-29T18:30:00Z"
    )
    assert set(feed) == {
        "schema",
        "producer",
        "inventory_manifest_sha256",
        "generated_at",
        "candidates",
        "self_sha256",
    }
    assert feed["schema"] == CANDIDATE_FEED_SCHEMA
    assert "source_sha256=" in feed["producer"]
    assert "mapper_manifest_sha256=" in feed["producer"]
    assert "mapper_commit=" in feed["producer"]
    assert "mapper_tree=" in feed["producer"]
    assert feed["candidates"] == []
    assert feed["self_sha256"] == _self_hash(feed)
    assert "promotion_authority" not in feed


def test_feed_refuses_dirty_or_advanced_source(
    mapped_repository: tuple[Path, Path],
) -> None:
    root, mapper = mapped_repository
    (root / "untracked.py").write_text("drift = True\n", encoding="utf-8")
    with pytest.raises(CapabilityFeedError, match="differs from clean Git HEAD"):
        build_retrospective_capability_feed(mapper, generated_at="2026-08-29T18:30:00Z")
    (root / "untracked.py").unlink()
    (root / "src/owner.py").write_text(
        "def dormant_candidate():\n    return 'changed'\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "advance")
    with pytest.raises(CapabilityFeedError, match="not current Git HEAD"):
        build_retrospective_capability_feed(mapper, generated_at="2026-08-29T18:30:00Z")


@pytest.mark.parametrize("value", ("not-a-time", "2026-08-29T18:30:00"))
def test_feed_refuses_malformed_or_naive_time(
    mapped_repository: tuple[Path, Path], value: str
) -> None:
    _root, mapper = mapped_repository
    with pytest.raises(CapabilityFeedError, match="generated_at"):
        build_retrospective_capability_feed(mapper, generated_at=value)


def test_v2_feed_emits_only_reviewed_archaeologist_candidate(
    reviewed_evidence_repository: Path,
) -> None:
    feed = build_reviewed_archaeologist_v2_capability_feed(
        reviewed_evidence_repository, generated_at="2026-09-01T00:00:00Z"
    )
    assert feed["schema"] == CANDIDATE_FEED_SCHEMA_V2
    assert feed["inventory_manifest_sha256"] == "3" * 64
    assert "promotion_authority" not in feed
    assert feed["self_sha256"] == _self_hash(feed)
    assert [candidate["candidate_id"] for candidate in feed["candidates"]] == [
        REVIEWED_ARCHAEOLOGIST_CANDIDATE_ID
    ]
    candidate = feed["candidates"][0]
    assert candidate["capability_id"] == "archaeologist-mapper"
    assert candidate["disposition"] == "DISCONNECTED"
    assert "scientific" not in json.dumps(feed, sort_keys=True)
    commit = _git_value(
        reviewed_evidence_repository,
        "rev-list",
        "-n",
        "1",
        "HEAD",
        "--",
        str(DEFAULT_EVIDENCE_LEDGER),
    )
    assert {source["kind"] for source in candidate["source_refs"]} == {
        "git-object-file"
    }
    assert {source["repo_alias"] for source in candidate["source_refs"]} == {
        "giga-user"
    }
    assert {source["source_status"] for source in candidate["source_refs"]} == {
        "TRACKED_REVIEWED_HISTORY"
    }
    assert {source["commit"] for source in candidate["source_refs"]} == {commit}
    assert len(candidate["source_refs"]) == 4


def test_v2_feed_refuses_tampered_accepted_evidence(
    reviewed_evidence_repository: Path,
) -> None:
    ledger_path = reviewed_evidence_repository / DEFAULT_EVIDENCE_LEDGER
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["requested_candidate_intents"][0]["accepted_evidence"][0]["sha256"] = (
        "0" * 64
    )
    ledger["self_sha256"] = _self_hash(ledger)
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(CapabilityFeedError, match="differs from Git object"):
        build_reviewed_archaeologist_v2_capability_feed(
            reviewed_evidence_repository, generated_at="2026-09-01T00:00:00Z"
        )


def test_v2_feed_refuses_duplicate_accepted_evidence(
    reviewed_evidence_repository: Path,
) -> None:
    ledger_path = reviewed_evidence_repository / DEFAULT_EVIDENCE_LEDGER
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["requested_candidate_intents"][0]["accepted_evidence"].append(
        dict(ledger["requested_candidate_intents"][0]["accepted_evidence"][0])
    )
    ledger["self_sha256"] = _self_hash(ledger)
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(CapabilityFeedError, match="duplicates"):
        build_reviewed_archaeologist_v2_capability_feed(
            reviewed_evidence_repository, generated_at="2026-09-01T00:00:00Z"
        )


def test_v2_feed_refuses_unretained_reviewed_history(
    reviewed_evidence_repository: Path,
) -> None:
    _git(
        reviewed_evidence_repository,
        "update-ref",
        "-d",
        "refs/remotes/origin/reviewed-archaeology",
    )
    with pytest.raises(CapabilityFeedError, match="not retained by a remote ref"):
        build_reviewed_archaeologist_v2_capability_feed(
            reviewed_evidence_repository, generated_at="2026-09-01T00:00:00Z"
        )


def test_v2_feed_writer_uses_self_hash_filename(
    reviewed_evidence_repository: Path, tmp_path: Path
) -> None:
    output = write_reviewed_archaeologist_v2_capability_feed(
        reviewed_evidence_repository,
        tmp_path,
        generated_at="2026-09-01T00:00:00Z",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == (
        f"retrospective-capability-candidates-v2-{payload['self_sha256']}.json"
    )
    assert payload["self_sha256"] == _self_hash(payload)


def test_cli_emits_v2_reviewed_archaeologist_feed(
    reviewed_evidence_repository: Path,
) -> None:
    code_root = Path(__file__).resolve().parents[1]
    process = subprocess.run(
        [
            "python3",
            str(code_root / "modules/operations/scripts/archaeology.py"),
            "mapper-capability-feed",
            "--schema-version",
            "v2",
            "--repository-root",
            str(reviewed_evidence_repository),
            "--generated-at",
            "2026-09-01T00:00:00Z",
        ],
        cwd=code_root,
        env={"PYTHONPATH": str(code_root), **os.environ},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert process.returncode == 0, process.stderr.decode()
    payload = json.loads(process.stdout)
    assert payload["schema"] == CANDIDATE_FEED_SCHEMA_V2
    assert payload["candidates"][0]["candidate_id"] == (
        REVIEWED_ARCHAEOLOGIST_CANDIDATE_ID
    )


def test_cli_v2_missing_repository_root_failure_is_generic(tmp_path: Path) -> None:
    code_root = Path(__file__).resolve().parents[1]
    failures = []
    for missing in (
        tmp_path / "private-a" / "operator" / "vaultish-layout-a",
        tmp_path / "private-b" / "operator" / "vaultish-layout-b",
    ):
        process = subprocess.run(
            [
                "python3",
                str(code_root / "modules/operations/scripts/archaeology.py"),
                "mapper-capability-feed",
                "--schema-version",
                "v2",
                "--repository-root",
                str(missing),
                "--generated-at",
                "2026-09-01T00:00:00Z",
            ],
            cwd=code_root,
            env={"PYTHONPATH": str(code_root), **os.environ},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        failures.append(process.stderr)
        assert process.returncode == 2
        assert str(missing) not in process.stderr.decode("utf-8")
        assert missing.name not in process.stderr.decode("utf-8")
    assert failures[0] == failures[1]


def _prepare_adoption_consumer_fixture(root: Path) -> None:
    (root / "src").mkdir(exist_ok=True)
    (root / "src/owner.py").write_text("def owned():\n    return True\n", encoding="utf-8")
    (root / "proofs").mkdir(exist_ok=True)
    (root / "proofs/owner.json").write_text('{"status":"accepted"}\n', encoding="utf-8")
    manifest = {
        "schema": "giga.capability-adoption-manifest.v1",
        "id": "fixture-capability",
        "owner": "fixture/team",
        "responsibility": "Exercise the adoption consumer contract.",
        "claim": "ADOPTED",
        "implementation_paths": ["src/owner.py"],
        "configuration_paths": [],
        "proof_paths": ["proofs/owner.json"],
        "entrypoint": {"argv": ["python3", "src/owner.py"], "working_directory": "."},
        "trigger": {"kind": "manual", "identity": "fixture"},
        "authority": {
            "capabilities": ["fixture.read"],
            "privacy": "synthetic fixture only",
            "external_effects": False,
            "vault_required": False,
        },
        "recovery": {
            "status_argv": ["python3", "src/owner.py"],
            "reconcile_argv": [],
            "disable_argv": [],
        },
        "liveness_receipt": "capabilities/receipts/fixture-capability.json",
    }
    manifest_path = root / "capabilities/manifests/archaeologist-mapper.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "prepare synthetic adoption consumer fixture")


def _write_v2_candidate_feed(root: Path, *, generated_at: str = "2026-09-02T00:00:00Z") -> str:
    feed = build_reviewed_archaeologist_v2_capability_feed(
        root, generated_at=generated_at
    )
    relative = "architecture/archaeologist/feeds/candidates-v2.json"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(feed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _git(root, "add", relative)
    _git(root, "commit", "-qm", "write synthetic v2 candidate feed")
    return relative


def test_v2_candidate_feed_is_consumed_as_status_only_and_reported_pathlessly(
    reviewed_evidence_repository: Path,
) -> None:
    root = reviewed_evidence_repository
    _prepare_adoption_consumer_fixture(root)
    v2_path = _write_v2_candidate_feed(root)
    legacy_path = next(
        path.relative_to(root).as_posix()
        for path in (root / "architecture/archaeologist/feeds").glob("*.json")
        if json.loads(path.read_text(encoding="utf-8"))["schema"] == CANDIDATE_FEED_SCHEMA
    )

    registry = compile_adoption_registry(
        root,
        "2026-09-03T00:00:00Z",
        candidate_feeds=(legacy_path, v2_path),
        require_git_head=True,
    )
    socket = registry["retrospective_socket"]
    candidate = socket["candidates"][0]
    assert socket["schema"] == "giga.retrospective-capability-socket.v2"
    assert socket["accepted_feed_schemas"] == [
        CANDIDATE_FEED_SCHEMA,
        "giga.retrospective-capability-candidates.v2",
    ]
    assert [feed["schema"] for feed in socket["feeds"]] == [
        CANDIDATE_FEED_SCHEMA,
        "giga.retrospective-capability-candidates.v2",
    ]
    assert candidate["capability_id"] == "archaeologist-mapper"
    assert {source["kind"] for source in candidate["source_refs"]} == {
        "git-object-file"
    }
    assert {source["repo_alias"] for source in candidate["source_refs"]} == {"giga-user"}
    assert candidate["execution_authority_granted"] is False
    assert socket["promotion_authority"] is False

    report = observe_liveness(root, registry)
    disconnected = report["implemented_but_disconnected"]
    assert disconnected == [
        {
            "candidate_id": "archaeologist-mapper-disconnected",
            "capability_id": "archaeologist-mapper",
            "state": "DISCONNECTED",
            "has_entrypoint_hint": True,
            "evidence_source_count": 4,
            "evidence_source_kinds": ["git-object-file"],
        }
    ]
    serialized = json.dumps(disconnected, sort_keys=True)
    assert "giga-user/operations/archaeology" not in serialized
    assert "architecture/archaeology/receipts" not in serialized
    assert "owner.py" not in serialized


def test_v2_candidate_feed_rejects_mismatched_git_tree(
    reviewed_evidence_repository: Path,
) -> None:
    root = reviewed_evidence_repository
    _prepare_adoption_consumer_fixture(root)
    feed = build_reviewed_archaeologist_v2_capability_feed(
        root, generated_at="2026-09-02T00:00:00Z"
    )
    feed["candidates"][0]["source_refs"][0]["tree"] = "0" * 40
    feed["self_sha256"] = _self_hash(feed)
    path = "architecture/archaeologist/feeds/candidates-v2.json"
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(feed, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CapabilityAdoptionError, match="tree differs"):
        compile_adoption_registry(
            root,
            "2026-09-03T00:00:00Z",
            candidate_feeds=(path,),
            require_git_head=False,
        )


def test_v2_reviewed_history_requires_a_retaining_remote_ref(
    reviewed_evidence_repository: Path,
) -> None:
    root = reviewed_evidence_repository
    _prepare_adoption_consumer_fixture(root)
    path = _write_v2_candidate_feed(root)
    _git(root, "update-ref", "-d", "refs/remotes/origin/reviewed-archaeology")

    with pytest.raises(CapabilityAdoptionError, match="not retained by a remote reference"):
        compile_adoption_registry(
            root,
            "2026-09-03T00:00:00Z",
            candidate_feeds=(path,),
            require_git_head=False,
        )
