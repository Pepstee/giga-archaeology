import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_root_layout", ROOT / "scripts" / "audit_root_layout.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


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
