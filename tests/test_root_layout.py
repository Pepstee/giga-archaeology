import importlib.util
import hashlib
import json
from pathlib import Path
import stat
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_root_layout", ROOT / "scripts" / "audit_root_layout.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
PRIVATE_EXTRACTION = (
    ROOT
    / "job-application-automation"
    / "candidate-evidence"
    / "source-extracted-identity-artifacts-0e5f289d"
)
PRIVATE_EXTRACTION_RECEIPT = PRIVATE_EXTRACTION.with_suffix(".receipt.json")


def test_current_root_is_classified_and_project_paths_exist():
    contract = MODULE.load_contract(
        ROOT / "architecture" / "root-layout.v1.json"
    )

    unknown, _legacy, missing = MODULE.audit(ROOT, contract)

    assert unknown == []
    assert missing == []


def test_unknown_entry_is_reported(tmp_path):
    (tmp_path / "mystery.bin").touch()
    contract = {
        "zones": {"projects": {"paths": [], "registry": "projects.json"}},
        "legacy_root_exceptions": [],
        "ignored_root_patterns": [],
    }
    (tmp_path / "projects.json").write_text('{"projects": []}', encoding="utf-8")

    unknown, legacy, missing = MODULE.audit(tmp_path, contract)

    assert unknown == ["mystery.bin", "projects.json"]
    assert legacy == []
    assert missing == []


def test_source_extracted_identity_payloads_are_excluded_from_git() -> None:
    canary = PRIVATE_EXTRACTION / "git-admission-canary.pdf"
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", str(canary.relative_to(ROOT))],
        cwd=ROOT,
        check=False,
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", str(PRIVATE_EXTRACTION.relative_to(ROOT))],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    assert tracked.stdout == b""

    receipt = json.loads(PRIVATE_EXTRACTION_RECEIPT.read_text(encoding="utf-8"))
    receipt_sha256 = receipt.pop("receipt_sha256")
    canonical = json.dumps(
        receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert receipt_sha256 == hashlib.sha256(canonical).hexdigest()
    assert receipt["payload_directory"] == PRIVATE_EXTRACTION.name
    if PRIVATE_EXTRACTION.exists():
        assert stat.S_IMODE(PRIVATE_EXTRACTION.stat().st_mode) == 0o700
        for item in receipt["files"]:
            path = PRIVATE_EXTRACTION / item["preserved_path"]
            assert path.is_file() and not path.is_symlink()
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            assert path.stat().st_size == item["bytes"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
