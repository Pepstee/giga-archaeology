from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.mapper import (
    MapperError,
    query_mapper,
    refresh_mapper,
)
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)
from modules.operations.archaeology.runtime_map import parse_capability_registry


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def _registry(*, observed_at: str = "2026-08-29T13:30:00+00:00") -> dict:
    payload = {
        "authority": "adoption-and-liveness-status-only",
        "capabilities": [
            {
                "authority": {
                    "capabilities": ["governance.payload.verify"],
                    "external_effects": False,
                    "privacy": "faceless",
                    "vault_required": False,
                },
                "claim": "ACTIVE",
                "entrypoint": {
                    "argv": ["python3", "scripts/verify_derived_agent_payloads.py"],
                    "working_directory": ".",
                },
                "execution_authority_granted": False,
                "id": "derived-agent-payloads",
                "last_failure_at": None,
                "last_success_at": "2026-08-29T07:38:51Z",
                "liveness_receipt": {
                    "bytes": 2762,
                    "path": "capabilities/receipts/derived-agent-payloads.json",
                    "sha256": "8" * 64,
                },
                "manifest_sha256": "9" * 64,
                "next_check_at": "2026-09-05T07:38:51Z",
                "owner": "giga-user/governance-payload-generator",
                "reason": "current owner proof is bound",
                "recovery": {
                    "disable_argv": [],
                    "reconcile_argv": [
                        "python3",
                        "scripts/verify_derived_agent_payloads.py",
                        "--write",
                    ],
                    "status_argv": [
                        "python3",
                        "scripts/verify_derived_agent_payloads.py",
                    ],
                },
                "responsibility": "Generate and verify derived agent payloads.",
                "state": "ACTIVE",
                "trigger": {
                    "identity": "operator-or-governance-milestone",
                    "kind": "manual",
                },
            }
        ],
        "execution_authority_granted": False,
        "observed_at": observed_at,
        "retrospective_socket": {
            "candidates": [],
            "feeds": [],
            "promotion_authority": False,
            "schema": "giga.retrospective-capability-candidates.v1",
        },
        "schema": "giga.capability-adoption-registry.v1",
        "source_authority": "git-head",
        "summary": {"capabilities_total": 1},
    }
    payload["registry_sha256"] = hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    return payload


def _write_registry(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    path.chmod(0o600)


@pytest.fixture()
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "runtime-map"\nversion = "1"\n', encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def test_m10_imports_gate_status_without_minting_authority(
    repository: Path, tmp_path: Path
) -> None:
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    runtime = tmp_path / "runtime" / "registry.json"
    runtime.parent.mkdir(mode=0o700)
    _write_registry(runtime, _registry())
    refresh_navigation_inventory(repository, inventory)
    run = refresh_mapper(inventory, mapper, runtime_registries=(runtime,))
    assert run.manifest["runtime_inputs"] == [
        {
            "bytes": runtime.stat().st_size,
            "file_sha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
            "observed_at": "2026-08-29T13:30:00+00:00",
            "path": str(runtime.resolve()),
            "registry_sha256": _registry()["registry_sha256"],
            "source_authority": "git-head",
        }
    ]
    assert run.manifest["counts"]["runtime_capabilities_active"] == 1
    result = query_mapper(
        mapper,
        "derived-agent-payloads",
        maps=("runtime_topology",),
        fact_limit=50,
    )
    capability = next(
        item for item in result["results"] if item["kind"] == "RUNTIME_CAPABILITY"
    )
    assert capability["attributes"]["state"] == "ACTIVE"
    assert capability["attributes"]["owner"] == "giga-user/governance-payload-generator"
    assert capability["attributes"]["map_authority"] is False
    assert capability["attributes"]["execution_authority_granted"] is False
    predicates = {item["predicate"] for item in capability["facts"]["relations"]}
    assert {
        "GATE_BINDS_ENTRYPOINT",
        "GATE_BINDS_LIVENESS_RECEIPT",
        "GATE_BINDS_TRIGGER",
        "GATE_REPORTS_CAPABILITY_STATE",
    } <= predicates
    assert result["coverage"][0]["details"]["map_authority"] is False


def test_m10_runtime_input_identity_invalidates_reuse(
    repository: Path, tmp_path: Path
) -> None:
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    runtime = tmp_path / "runtime" / "registry.json"
    runtime.parent.mkdir(mode=0o700)
    _write_registry(runtime, _registry())
    refresh_navigation_inventory(repository, inventory)
    first = refresh_mapper(inventory, mapper, runtime_registries=(runtime,))
    _write_registry(runtime, _registry(observed_at="2026-08-29T14:30:00+00:00"))
    second = refresh_mapper(inventory, mapper, runtime_registries=(runtime,))
    assert second.manifest["run_id"] != first.manifest["run_id"]
    assert (
        second.manifest["runtime_inputs"][0]["file_sha256"]
        != first.manifest["runtime_inputs"][0]["file_sha256"]
    )


def test_m10_refuses_tamper_ambiguous_json_and_unsafe_files(
    repository: Path, tmp_path: Path
) -> None:
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    runtime = tmp_path / "runtime" / "registry.json"
    runtime.parent.mkdir(mode=0o700)
    refresh_navigation_inventory(repository, inventory)

    tampered = _registry()
    tampered["registry_sha256"] = "f" * 64
    _write_registry(runtime, tampered)
    with pytest.raises(MapperError, match="self hash differs"):
        refresh_mapper(inventory, mapper, runtime_registries=(runtime,))

    runtime.write_text('{"schema":"a","schema":"b"}\n', encoding="utf-8")
    runtime.chmod(0o600)
    with pytest.raises(MapperError, match="duplicate JSON key"):
        refresh_mapper(inventory, mapper, runtime_registries=(runtime,))

    _write_registry(runtime, _registry())
    runtime.chmod(0o644)
    with pytest.raises(MapperError, match="private single-link"):
        refresh_mapper(inventory, mapper, runtime_registries=(runtime,))

    _write_registry(runtime, _registry())
    alias = runtime.parent / "registry-alias.json"
    alias.symlink_to(runtime)
    with pytest.raises(MapperError, match="canonical and non-symlink"):
        refresh_mapper(inventory, mapper, runtime_registries=(alias,))

    duplicate = runtime.parent / "registry-duplicate.json"
    _write_registry(duplicate, _registry())
    with pytest.raises(MapperError, match="duplicate evidence"):
        refresh_mapper(inventory, mapper, runtime_registries=(runtime, duplicate))

    inside = repository / "registry.json"
    _write_registry(inside, _registry())
    with pytest.raises(MapperError, match="outside the scanned repository"):
        refresh_mapper(inventory, mapper, runtime_registries=(inside,))


def test_m10_parser_refuses_candidate_promotion_and_execution_authority() -> None:
    payload = _registry()
    payload["execution_authority_granted"] = True
    payload["registry_sha256"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in payload.items() if key != "registry_sha256"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    with pytest.raises(ValueError, match="authority boundary"):
        parse_capability_registry(json.dumps(payload).encode())
