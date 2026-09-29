"""Location inventory contract tests. No project copies or worktrees are created."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.operations.archaeology import location_inventory as locations
from modules.operations.archaeology.evidence import canonical_bytes, seal_document, validate_self_hash
from modules.operations.scripts.archaeology import main

NOW = "2026-09-29T09:00:00Z"
HEAD = "a" * 40
FIXTURE = Path(__file__).parent / "fixtures/location_inventory.json"


def declaration(path: Path, **values):
    return {"project_id": "example", "host": "build-host", "path": str(path),
            "declared_owner": "operator", "authority_level": "project",
            "canon_level": "canonical_development_owner", "role": "development", **values}


@pytest.fixture
def metadata_root(tmp_path, monkeypatch):
    # An empty directory with an empty marker, not a runnable project or Git copy.
    root = tmp_path / "subject"
    root.mkdir()
    (root / ".git").mkdir()
    calls = []

    def git(path, args, accepted=(0,)):
        calls.append((path, args))
        assert path == root
        if args[0] == "rev-parse":
            return 0, (HEAD + "\n").encode()
        if args[0] == "symbolic-ref":
            return 0, b"refs/heads/main\n"
        if args[0] == "diff-index":
            assert "--cached" in args
            return 0, b""
        if args[0] == "worktree":
            return 0, (f"worktree {root}\0HEAD {HEAD}\0branch refs/heads/main\0\0"
                       f"worktree /example/unregistered-linked\0HEAD {HEAD}\0detached\0locked private reason\0\0").encode()
        if args[0] == "config":
            assert "--no-includes" in args
            return 0, b"remote.origin.url\nhttps://person:<redacted-email>/team/repo.git?secret=token#fragment\0"
        raise AssertionError(args)

    monkeypatch.setattr(locations, "_git", git)
    return root, calls, git


def test_deterministic_inspection_keeps_declaration_and_observation_separate(metadata_root):
    root, calls, _ = metadata_root
    roots = [declaration(root, declared_head="b" * 40),
             declaration(Path("/example/remote"), host="remote", canon_level="historical")]
    first = locations.inspect_locations(roots, local_host="build-host", observed_at=NOW)
    second = locations.inspect_locations(list(reversed(roots)), local_host="build-host", observed_at=NOW)
    assert canonical_bytes(first) == canonical_bytes(second)
    validate_self_hash(first)
    local = next(r for r in first["locations"] if r["declared"]["host"] == "build-host")
    assert local["declared"]["declared_head"] == "b" * 40
    assert local["observed"]["head"] == HEAD
    assert local["declared_head_matches_observed"] is False
    assert local["observed"]["dirty"] == {"state": "UNKNOWN", "index": "CLEAN", "worktree": "NOT_INSPECTED", "untracked": "NOT_INSPECTED"}
    assert local["observed"]["remotes"] == [{"name": "origin", "identity": "example.invalid/team/repo", "status": "OBSERVED"}]
    assert b"password" not in canonical_bytes(first)
    assert all(not w["path_inspected"] for w in local["observed"]["worktrees"])
    assert len(local["observed"]["worktrees"]) == 2
    assert first["coverage"]["scanned_roots"] == [str(root)]
    assert first["coverage"]["global_completeness"] is False
    assert first["safe_to_delete"] is False
    assert all(path == root for path, _ in calls)


def test_staged_dirty_and_detached_are_observations(metadata_root, monkeypatch):
    root, _, git = metadata_root
    def probe(path, args, accepted=(0,)):
        if args[0] in {"diff-index", "symbolic-ref"}:
            return 1, b""
        return git(path, args, accepted)
    monkeypatch.setattr(locations, "_git", probe)
    row = locations.inspect_locations([declaration(root)], local_host="build-host", observed_at=NOW)["locations"][0]
    assert row["observed"]["dirty"]["state"] == "DIRTY"
    assert row["observed"]["detached"] is True
    assert row["observed"]["branch"] is None


def test_multiple_canon_levels_and_conflicts():
    roots, source = locations.load_location_roots(FIXTURE)
    payload = locations.inspect_locations(roots, local_host="no-local-fixture-host", observed_at=NOW, evidence_source=source)
    assert not payload["conflicts"]
    assert {r["declared"]["canon_level"] for r in payload["locations"]} == {"canonical_source", "canonical_runtime", "inactive", "noncanonical"}
    roots.append({**roots[0], "path": "/example/second-source"})
    roots.append({**roots[0], "declared_owner": "different-owner"})
    payload = locations.inspect_locations(roots, local_host="no-local-fixture-host", observed_at=NOW)
    assert {c["kind"] for c in payload["conflicts"]} == {"MULTIPLE_DECLARED_CANONS", "CONFLICTING_PATH_DECLARATIONS"}
    assert not payload["authority_granted"]


def test_excluded_foreign_sensitive_and_broad_roots_never_probe(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("outside scope")
    monkeypatch.setattr(locations, "_observe", forbidden)
    roots = [declaration(tmp_path / "omit", excluded=True),
             declaration(tmp_path / "excluded" / "child"),
             declaration(tmp_path / "private" / "project"),
             declaration(Path("/")),
             declaration(Path("/example/remote"), host="remote")]
    payload = locations.inspect_locations(roots, local_host="build-host", observed_at=NOW, excluded_roots=[str(tmp_path / "excluded")])
    assert {r["observed"]["status"] for r in payload["locations"]} == {"EXCLUDED", "SENSITIVE_ROOT_EXCLUDED", "BROAD_ROOT_REFUSED", "REMOTE_HOST_NOT_INSPECTED"}
    assert payload["coverage"]["attempted_roots"] == []


def test_missing_non_git_and_inaccessible_paths(tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    inaccessible = tmp_path / "inaccessible"
    original = locations._no_symlinks
    def guarded(path):
        if path == inaccessible:
            raise PermissionError("fixture")
        return original(path)
    monkeypatch.setattr(locations, "_no_symlinks", guarded)
    monkeypatch.setattr(locations, "_git", lambda *a: pytest.fail("no Git probe allowed"))
    payload = locations.inspect_locations([declaration(empty), declaration(inaccessible), declaration(tmp_path / "missing")], local_host="build-host", observed_at=NOW)
    assert {r["observed"]["status"] for r in payload["locations"]} == {"NOT_GIT", "INACCESSIBLE", "MISSING"}
    assert payload["coverage"]["scanned_roots"] == []


def test_symlinked_roots_and_markers_refused(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("host lacks symlink permission")
    (target / ".git").symlink_to(tmp_path, target_is_directory=True)
    payload = locations.inspect_locations([declaration(link), declaration(target)], local_host="build-host", observed_at=NOW)
    assert all(r["observed"]["status"] == "REFUSED_PATH" for r in payload["locations"])


def test_git_failure_partial_and_head_race(metadata_root, monkeypatch):
    root, _, git = metadata_root
    heads = iter([HEAD, "b" * 40])
    def probe(path, args, accepted=(0,)):
        if args[0] == "config":
            raise locations.LocationInventoryError("failure")
        if args[0] == "rev-parse":
            return 0, next(heads).encode()
        return git(path, args, accepted)
    monkeypatch.setattr(locations, "_git", probe)
    row = locations.inspect_locations([declaration(root)], local_host="build-host", observed_at=NOW)["locations"][0]
    assert row["observed"]["status"] == "UNSTABLE"
    assert "local-remote-config" in row["observed"]["unknowns"]


def test_partial_git_metadata_and_linked_marker(metadata_root, monkeypatch):
    root, _, git = metadata_root
    # Exercise a gitdir pointer without creating an actual linked worktree.
    (root / ".git").rmdir()
    (root / ".git").write_text("gitdir: /example/registered/common/worktrees/linked\n")
    def probe(path, args, accepted=(0,)):
        if args[0] == "worktree":
            raise locations.LocationInventoryError("unavailable")
        return git(path, args, accepted)
    monkeypatch.setattr(locations, "_git", probe)
    row = locations.inspect_locations([declaration(root)], local_host="build-host", observed_at=NOW)["locations"][0]
    assert row["observed"]["status"] == "PARTIAL"
    assert row["observed"]["head"] == HEAD
    assert row["observed"]["worktrees"] == []
    assert "worktrees" in row["observed"]["unknowns"]


def test_unselected_registered_root_never_probed(metadata_root, monkeypatch):
    root, calls, _ = metadata_root
    payload = locations.inspect_locations(
        [declaration(root), declaration(Path("/example/other"), project_id="other")],
        local_host="build-host", project_ids=["example"], observed_at=NOW,
    )
    assert payload["coverage"]["scanned_roots"] == [str(root)]
    assert {g["reason"] for g in payload["coverage"]["gaps"]} == {"PROJECT_NOT_SELECTED"}
    assert all(path == root for path, _ in calls)


def test_machine_register_keeps_global_host_and_project_authority_distinct(tmp_path):
    register = tmp_path / "register.json"
    register.write_text(json.dumps({"schema": "giga.machine-authority.v1", "authority": {"canonical_host": "old-host"},
        "hosts": {"build-host": {"role": "candidate", "roots": [{"id": "example", "path": "/example/source", "status": "canonical_development_owner", "purpose": "development", "verified_head": HEAD}]},
                  "old-host": {"role": "canonical", "roots": [{"id": "example", "path": "/example/history", "status": "inactive"}]}}}))
    roots, source = locations.load_location_roots(register)
    payload = locations.inspect_locations(roots, local_host="fixture-other-host", observed_at=NOW, evidence_source=source)
    row = next(r for r in payload["locations"] if r["declared"]["host"] == "build-host")
    assert row["declared"]["host_role"] == "candidate"
    assert row["declared"]["canon_level"] == "canonical_development_owner"
    assert row["declared"]["declared_owner"] is None
    assert source["global_authority"] == {"canonical_host": "old-host"}
    assert not payload["conflicts"]


def test_refresh_query_fresh_stale_unknown_and_tampering(metadata_root, tmp_path, monkeypatch):
    root, _, _ = metadata_root
    receipt = tmp_path / "inventory.json"
    payload = locations.refresh_locations([declaration(root, declared_at="2026-09-01T00:00:00Z"), declaration(Path("/example/remote"), host="remote")], receipt, local_host="build-host", observed_at=NOW)
    monkeypatch.setattr(locations, "_observe", lambda *a: pytest.fail("query must never rescan"))
    result = locations.query_locations(receipt, as_of=NOW)
    assert {r["freshness"] for r in result["results"]} == {"WITHIN_MAX_AGE", "UNKNOWN"}
    assert {r["declaration_freshness"] for r in result["results"]} == {"STALE", "UNKNOWN"}
    assert result["live_state_rechecked"] is False
    result = locations.query_locations(receipt, "build-host", as_of="2026-09-30T09:00:01Z")
    assert [r["freshness"] for r in result["results"]] == ["STALE"]
    result = locations.query_locations(receipt, as_of="2026-09-28T00:00:00Z")
    assert all(r["freshness"] == "UNKNOWN" for r in result["results"])
    payload["locations"][0]["declared"]["canon_level"] = "forged"
    receipt.write_text(json.dumps(payload))
    with pytest.raises(locations.LocationInventoryError, match="hash mismatch"):
        locations.query_locations(receipt)


def test_refresh_never_writes_into_a_subject_or_overwrites(metadata_root, tmp_path):
    root, _, _ = metadata_root
    roots = [declaration(root)]
    with pytest.raises(locations.LocationInventoryError, match="outside"):
        locations.refresh_locations(roots, root / "receipt.json", local_host="build-host")
    output = tmp_path / "receipt.json"
    output.write_text("operator data")
    with pytest.raises(locations.LocationInventoryError, match="new receipt"):
        locations.refresh_locations(roots, output, local_host="build-host")
    assert output.read_text() == "operator data"


def test_cli_inspect_refresh_query_and_error(metadata_root, tmp_path, capsys):
    root, _, _ = metadata_root
    common = ["--root", str(root), "--local-host", "build-host", "--observed-at", NOW]
    assert main(["locations-inspect", *common]) == 0
    inspected = json.loads(capsys.readouterr().out)
    output = tmp_path / "receipt.json"
    assert main(["locations-refresh", *common, "--output", str(output)]) == 0
    assert json.loads(capsys.readouterr().out) == inspected
    assert main(["locations-query", "subject", "--receipt", str(output), "--as-of", NOW]) == 0
    assert len(json.loads(capsys.readouterr().out)["results"]) == 1
    assert main(["locations-inspect", "--roots-file", str(FIXTURE), "--local-host", "build-host", "--project-id", "absent"]) == 2
    assert json.loads(capsys.readouterr().err)["status"] == "REFUSED"


@pytest.mark.parametrize("path", ["relative", "/example/../other", "", "/example/\x00oops"])
def test_invalid_root_fails_before_probe(path, monkeypatch):
    monkeypatch.setattr(locations, "_observe", lambda *a: pytest.fail("invalid root probed"))
    with pytest.raises(locations.LocationInventoryError):
        locations.inspect_locations([{**declaration(Path("/example")), "path": path}], local_host="build-host")


@pytest.mark.parametrize("value,expected", [
    ("<redacted-email>:team/repo.git", "example.invalid/team/repo"),
    ("https://user:<redacted-email>/team/repo.git?token=secret", "example.invalid/team/repo"),
    ("/private/local-repo", None), ("ext::execute payload", None),
    ("file:///private/source", None), ("https://host/a%20b", None),
])
def test_remote_identity_redacts(value, expected):
    assert locations._remote_identity(value) == expected


def test_git_invocation_has_read_only_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(locations, "git_executable", lambda: "/usr/bin/git")
    def run(argv, **kwargs):
        assert "--no-optional-locks" in argv
        assert "core.fsmonitor=false" in argv
        assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
        assert kwargs["env"]["GIT_NO_LAZY_FETCH"] == "1"
        assert "GIT_DIR" not in kwargs["env"]
        assert kwargs["cwd"] == tmp_path
        return type("Result", (), {"returncode": 0, "stdout": b"ok", "stderr": b""})()
    monkeypatch.setattr(locations.subprocess, "run", run)
    assert locations._git(tmp_path, ["rev-parse", "HEAD"]) == (0, b"ok")


def test_api_and_packaging_expose_location_module():
    import modules.operations.archaeology as api
    import modules.operations.archaeologist.location_inventory as legacy
    from modules.platform.packaging.archaeology_build_backend import SOURCE_FILES
    assert api.inspect_locations is locations.inspect_locations
    assert legacy is locations
    assert "modules/operations/archaeology/location_inventory.py" in SOURCE_FILES


@pytest.mark.parametrize("raw", ['{"schema":"x","schema":"y"}', '{"schema":"unknown"}', '[]'])
def test_invalid_register_refused_before_observation(tmp_path, raw):
    path = tmp_path / "input.json"
    path.write_text(raw)
    with pytest.raises(locations.LocationInventoryError):
        locations.load_location_roots(path)


def test_malformed_or_authority_granting_sealed_receipt_refused(tmp_path):
    receipt = tmp_path / "receipt.json"
    value = locations.inspect_locations([declaration(Path("/example/remote"), host="remote")], local_host="build-host", observed_at=NOW)
    del value["receipt_sha256"]
    value["safe_to_delete"] = True
    receipt.write_bytes(canonical_bytes(seal_document(value)))
    with pytest.raises(locations.LocationInventoryError, match="authority boundary"):
        locations.query_locations(receipt)
    value["safe_to_delete"] = False
    value["locations"] = ["invalid"]
    receipt.write_bytes(canonical_bytes(seal_document(value)))
    with pytest.raises(locations.LocationInventoryError, match="location record"):
        locations.query_locations(receipt)


def test_query_time_and_duplicate_input_validation(tmp_path):
    root = declaration(tmp_path / "missing")
    with pytest.raises(locations.LocationInventoryError, match="duplicate"):
        locations.inspect_locations([root, root], local_host="build-host")
    with pytest.raises(locations.LocationInventoryError, match="timezone-aware"):
        locations.inspect_locations([root], local_host="build-host", observed_at="2026-09-29T00:00:00")


def test_refresh_output_symlink_refused(metadata_root, tmp_path):
    root, _, _ = metadata_root
    output_parent = tmp_path / "output-link"
    try:
        output_parent.symlink_to(root, target_is_directory=True)
    except OSError:
        pytest.skip("host lacks symlink permission")
    with pytest.raises(locations.LocationInventoryError):
        locations.refresh_locations([declaration(root)], output_parent / "receipt.json", local_host="build-host")
    assert not (root / "receipt.json").exists()
