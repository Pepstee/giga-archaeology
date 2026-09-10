from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts.audit_execution_policy import BypassAuditError, audit


ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> Path:
    from test_execution_policy import ExecutionPolicyTests as _PolicyFixture
    fixture = _PolicyFixture()
    fixture.setUp()
    try:
        registry = copy.deepcopy(fixture.registry)
    finally:
        fixture.doCleanups()
    root = tmp_path / "project"
    records = []
    for relative in ("scripts/jarvis_telegram.py", "twin_core/telegram_pipeline.py"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
        records.append({"path": relative, "sha256": _sha(target), "bytes": target.stat().st_size})
    registry["capabilities"][0]["evidence"] = records
    target = root / "execution/capabilities.v1.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(registry))
    return root


def _rebind(root: Path, relative: str) -> None:
    registry_path = root / "execution/capabilities.v1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    path = root / relative
    for record in registry["capabilities"][0]["evidence"]:
        if record["path"] == relative:
            record["sha256"] = _sha(path)
            record["bytes"] = path.stat().st_size
            break
    else:
        raise AssertionError(f"missing evidence record: {relative}")
    registry_path.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def test_generated_audit_is_deterministic_and_narrow(tmp_path) -> None:
    root = _fixture(tmp_path)
    first = audit(root)
    second = audit(root)
    assert first == second
    assert first["status"] == "pass"
    assert first["coverage_claim"] == "one-telegram-memory-proposal-seam-only"
    assert first["execution_authorized"] is False
    assert first["authority_granted"] is False
    assert first["command_execution"] is False
    assert first["provider_called"] is False
    assert first["runtime_enforcement"] is False
    assert first["findings"]["scripts/jarvis_telegram.py"]["provider_calls"] == 1
    assert first["findings"]["twin_core/telegram_pipeline.py"]["provider_imports"] == 0


def test_second_direct_provider_call_is_blocked(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "scripts/jarvis_telegram.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "def _shadow_route(event_id: str, instructions: str) -> Mapping[str, Any]:",
            "def _shadow_route(event_id: str, instructions: str) -> Mapping[str, Any]:\n"
            "    run_proposal(instructions, cwd=GIGA, timeout=1, model=MODEL)",
        ),
        encoding="utf-8",
    )
    _rebind(root, "scripts/jarvis_telegram.py")
    with pytest.raises(BypassAuditError) as raised:
        audit(root)
    assert raised.value.reason == "BYPASS_PROVIDER_CALL"


def test_worker_binding_bypass_is_blocked(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "scripts/jarvis_telegram.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("worker=_worker,", "worker=run_proposal,"), encoding="utf-8"
    )
    _rebind(root, "scripts/jarvis_telegram.py")
    with pytest.raises(BypassAuditError) as raised:
        audit(root)
    assert raised.value.reason == "BYPASS_WORKER_BINDING"


def test_pipeline_provider_import_is_blocked(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "twin_core/telegram_pipeline.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "from .store import TwinStore",
            "from .store import TwinStore\nfrom twin_core.provider_adapters import run_proposal",
        ),
        encoding="utf-8",
    )
    _rebind(root, "twin_core/telegram_pipeline.py")
    with pytest.raises(BypassAuditError) as raised:
        audit(root)
    assert raised.value.reason == "BYPASS_PIPELINE_PROVIDER_IMPORT"


def test_aliased_provider_boundary_is_blocked(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "scripts/jarvis_telegram.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "import run_proposal  #", "import run_proposal as provider_call  #"
    )
    text = text.replace("return run_proposal(", "return provider_call(")
    path.write_text(text, encoding="utf-8")
    _rebind(root, "scripts/jarvis_telegram.py")
    with pytest.raises(BypassAuditError) as raised:
        audit(root)
    assert raised.value.reason == "BYPASS_PROVIDER_IMPORT"


def test_worker_before_shadow_receipt_is_blocked(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "twin_core/telegram_pipeline.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "            previous_route = store.latest_receipt(event_id, route_operation)",
        "            result = worker(instructions)\n"
        "            previous_route = store.latest_receipt(event_id, route_operation)",
    )
    text = text.replace(
        "        result = worker(instructions)\n        if result is None:",
        "        if result is None:",
    )
    path.write_text(text, encoding="utf-8")
    _rebind(root, "twin_core/telegram_pipeline.py")
    with pytest.raises(BypassAuditError) as raised:
        audit(root)
    assert raised.value.reason == "BYPASS_PIPELINE_ORDER"


def test_missing_provider_boundary_receipt_is_blocked(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "twin_core/telegram_pipeline.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "operation=PROVIDER_BOUNDARY_OPERATION,",
            "operation=\"unregistered.provider.boundary\",",
        ),
        encoding="utf-8",
    )
    _rebind(root, "twin_core/telegram_pipeline.py")
    with pytest.raises(BypassAuditError) as raised:
        audit(root)
    assert raised.value.reason == "BYPASS_PIPELINE_PROVIDER_RECEIPT"


def test_bound_source_symlink_is_blocked(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    source = root / "scripts/jarvis_telegram.py"
    elsewhere = tmp_path / "jarvis-copy.py"
    shutil.copy2(source, elsewhere)
    source.unlink()
    source.symlink_to(elsewhere)
    with pytest.raises(BypassAuditError) as raised:
        audit(root)
    assert raised.value.reason in {"BYPASS_REGISTRY_INVALID", "BYPASS_PATH_SYMLINK"}


def test_registry_or_unbound_source_drift_blocks_before_audit(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "scripts/jarvis_telegram.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(BypassAuditError) as raised:
        audit(root)
    assert raised.value.reason == "BYPASS_REGISTRY_INVALID"


def test_receipt_hash_covers_the_full_receipt(tmp_path) -> None:
    receipt = audit(_fixture(tmp_path))
    expected = receipt.pop("receipt_sha256")
    raw = json.dumps(
        receipt,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert hashlib.sha256(raw).hexdigest() == expected


def test_receipt_changes_when_audited_source_changes(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    original = audit(root)
    path = root / "scripts/jarvis_telegram.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace('MODEL = "sonnet"', 'MODEL = "sonnet-v2"'), encoding="utf-8"
    )
    _rebind(root, "scripts/jarvis_telegram.py")
    changed = audit(root)
    assert changed["receipt_sha256"] != original["receipt_sha256"]
    assert changed["registry_sha256"] != original["registry_sha256"]


def test_fixture_registry_is_not_mutated_by_failed_audit(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    registry_path = root / "execution/capabilities.v1.json"
    before = copy.deepcopy(json.loads(registry_path.read_text(encoding="utf-8")))
    path = root / "twin_core/telegram_pipeline.py"
    path.write_text(
        path.read_text(encoding="utf-8") + "\nworker('bypass')\n", encoding="utf-8"
    )
    _rebind(root, "twin_core/telegram_pipeline.py")
    with pytest.raises(BypassAuditError):
        audit(root)
    after = json.loads(registry_path.read_text(encoding="utf-8"))
    assert after["schema_version"] == before["schema_version"]
    assert after["capabilities"][0]["capability_id"] == CAPABILITY_ID


CAPABILITY_ID = "telegram-memory-proposal"


@pytest.mark.parametrize('replacement', [
    '    return _process_event(**kwargs)\n',
    '    return _process_event(**kwargs)\n    _require_corpus_access()\n',
    '    if False: _require_corpus_access()\n    return _process_event(**kwargs)\n',
])
def test_public_guard_mutation_refuses(tmp_path, replacement):
    root = _fixture(tmp_path)
    path = root / 'twin_core/telegram_pipeline.py'
    original = '    _require_corpus_access()\n    return _process_event(**kwargs)\n'
    text = path.read_text()
    assert original in text
    path.write_text(text.replace(original, replacement))
    _rebind(root, 'twin_core/telegram_pipeline.py')
    with pytest.raises(BypassAuditError, match='BYPASS_PUBLIC_CORPUS_GUARD'):
        audit(root)


def test_private_pipeline_alias_refuses(tmp_path):
    root = _fixture(tmp_path)
    path = root / 'scripts/jarvis_telegram.py'
    text = path.read_text()
    original = 'import ProcessingOutcome, process_event'
    assert original in text
    path.write_text(text.replace(original, 'import ProcessingOutcome, _process_event as process_event'))
    _rebind(root, 'scripts/jarvis_telegram.py')
    with pytest.raises(BypassAuditError, match='BYPASS_PUBLIC_ENTRYPOINT'):
        audit(root)
