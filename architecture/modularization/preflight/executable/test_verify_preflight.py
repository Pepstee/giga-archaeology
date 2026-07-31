from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VERIFY = Path(__file__).with_name("verify_preflight.py")
SPEC = importlib.util.spec_from_file_location("verify_preflight", VERIFY)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

def test_preflight_and_private_backup_manifests_are_valid():
    backup = Path("/Users/admin/.giga/backups/giga-modularization-preflight-20260730")
    assert MODULE.verify_manifest(VERIFY.parent / "preflight-manifest.json") == []
    assert MODULE.verify_manifest(backup / "backup-manifest.json") == []
