from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from modules.operations.archaeology.evidence import canonical_bytes, validate_self_hash
from modules.operations.archaeology.hypotheses import (
    HypothesisError,
    ScannerPaths,
    write_hypotheses,
)
from modules.operations.archaeology.inventory import write_inventory


@pytest.mark.parametrize("no_sandbox", [False, True])
@pytest.mark.parametrize("explicit_root", [False, True])
def test_cli_scanner_sandbox_is_explicit_opt_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], no_sandbox: bool, explicit_root: bool,
) -> None:
    from modules.operations.scripts import archaeology as cli

    calls = []

    def capture(inventory, output, scanners, *, use_sandbox):
        calls.append((inventory, output, scanners, use_sandbox))
        return {"receipt_sha256": "fixture", "summary": {"observations": 0}}

    monkeypatch.setattr(cli, "write_hypotheses", capture)
    arguments = ["hypotheses", "--inventory", str(tmp_path / "inventory.json"),
                 "--output", str(tmp_path / "output")]
    if explicit_root:
        arguments.extend(["--tools-root", str(tmp_path)])
    if no_sandbox:
        arguments.append("--no-sandbox")
    assert cli.main(arguments) == 0
    assert len(calls) == 1
    inventory, output, scanners, sandbox = calls[0]
    assert inventory == tmp_path / "inventory.json"
    assert output == tmp_path / "output"
    assert sandbox is (not no_sandbox)
    if explicit_root:
        assert scanners == ScannerPaths.from_tools_root(tmp_path)
    else:
        assert scanners is None
    assert json.loads(capsys.readouterr().out)["receipt_sha256"] == "fixture"


def test_scanner_configuration_reads_environment_at_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for tool, key in (
        ("vulture", "GIGA_ARCHAEOLOGIST_VULTURE"),
        ("jscpd", "GIGA_ARCHAEOLOGIST_JSCPD"),
        ("cgc_python", "GIGA_ARCHAEOLOGIST_CGC_PYTHON"),
    ):
        monkeypatch.setenv(key, str(tmp_path / tool))
    first = ScannerPaths()
    assert first.vulture == tmp_path / "vulture"
    assert first.jscpd == tmp_path / "jscpd"
    assert first.cgc_python == tmp_path / "cgc_python"
    monkeypatch.setenv("GIGA_ARCHAEOLOGIST_VULTURE", str(tmp_path / "changed"))
    assert ScannerPaths().vulture == tmp_path / "changed"
    assert first.vulture == tmp_path / "vulture"


def test_scanner_configuration_discovers_path_and_current_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in ("GIGA_ARCHAEOLOGIST_VULTURE", "GIGA_ARCHAEOLOGIST_JSCPD",
                "GIGA_ARCHAEOLOGIST_CGC_PYTHON"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    vulture = _executable(tmp_path / "vulture", "#!/bin/sh\nexit 0\n")
    jscpd = _executable(tmp_path / "jscpd", "#!/bin/sh\nexit 0\n")
    paths = ScannerPaths()
    assert paths.vulture == vulture
    assert paths.jscpd == jscpd
    assert paths.cgc_python == Path(sys.executable)
    monkeypatch.setenv("PATH", "")
    fallback = ScannerPaths()
    legacy = Path("${HOME}/Documents/developer-tools/giga-archaeologist-tools")
    assert fallback.vulture == legacy / ".venv/bin/vulture"
    assert fallback.jscpd == legacy / "node/node_modules/.bin/jscpd"


def test_explicit_tools_root_and_missing_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in ("GIGA_ARCHAEOLOGIST_VULTURE", "GIGA_ARCHAEOLOGIST_JSCPD",
                "GIGA_ARCHAEOLOGIST_CGC_PYTHON"):
        monkeypatch.setenv(key, str(tmp_path / "ignored-environment"))
    paths = ScannerPaths.from_tools_root(tmp_path)
    assert paths.vulture == tmp_path / ".venv/bin/vulture"
    assert paths.jscpd == tmp_path / "node/node_modules/.bin/jscpd"
    assert paths.cgc_python == tmp_path / ".venv/bin/python"
    with pytest.raises(HypothesisError, match="tools root is unavailable"):
        ScannerPaths.from_tools_root(tmp_path / "missing")


def test_cli_uses_explicit_tools_root_before_inventory(tmp_path: Path) -> None:
    cli = Path(__file__).resolve().parents[1] / "modules/operations/scripts/archaeology.py"
    result = subprocess.run(
        [sys.executable, "-B", str(cli), "hypotheses",
         "--tools-root", str(tmp_path), "--inventory", str(tmp_path / "missing.json"),
         "--output", str(tmp_path / "output")],
        cwd=tmp_path, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode != 0
    assert str(tmp_path / ".venv/bin/vulture") in result.stdout + result.stderr
    assert not (tmp_path / "output").exists()


def test_cli_preserves_explicit_scanner_override(tmp_path: Path) -> None:
    cli = Path(__file__).resolve().parents[1] / "modules/operations/scripts/archaeology.py"
    missing_tool = tmp_path / "configured-missing-vulture"
    result = subprocess.run(
        [sys.executable, "-B", str(cli), "hypotheses",
         "--inventory", str(tmp_path / "missing.json"),
         "--output", str(tmp_path / "output")],
        env={**os.environ, "GIGA_ARCHAEOLOGIST_VULTURE": str(missing_tool)},
        cwd=tmp_path, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode != 0
    assert str(missing_tool) in result.stdout + result.stderr
    assert not (tmp_path / "output").exists()


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


@pytest.fixture()
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "src").mkdir()
    (root / "src/app.py").write_text(
        "def unused():\n    return 1\n\ndef used():\n    return 2\n", encoding="utf-8"
    )
    (root / "src/a.js").write_text("function a() { return 1; }\n", encoding="utf-8")
    (root / "src/b.js").write_text("function b() { return 1; }\n", encoding="utf-8")
    (root / "memory").mkdir()
    (root / "memory/private.py").write_text(
        "SECRET = 'never-project'\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o700)
    return path


def _scanners(tmp_path: Path, *, cgc_exit: int = 0) -> ScannerPaths:
    vulture = _executable(
        tmp_path / "vulture",
        "#!/bin/sh\nprintf 'projection/src/app.py:1: unused function '\"'\"'unused'\"'\"' (60%% confidence)\\n'\nexit 3\n",
    )
    jscpd = _executable(
        tmp_path / "jscpd",
        """#!/usr/bin/python3
import json, pathlib, sys
args = sys.argv
out = pathlib.Path(args[args.index('--output') + 1])
out.mkdir(parents=True)
payload = {'duplicates': [{'firstFile': {'name': 'src/a.js:javascript', 'start': 1, 'end': 1},
 'secondFile': {'name': 'src/b.js:javascript', 'start': 1, 'end': 1}, 'format': 'javascript',
 'lines': 1, 'tokens': 8}], 'statistics': {}}
(out / 'jscpd-report.json').write_text(json.dumps(payload))
""",
    )
    cgc = _executable(
        tmp_path / "cgc_bridge.py",
        f"""#!/usr/bin/python3
import json, pathlib, sys
args = sys.argv
out = pathlib.Path(args[args.index('--output') + 1])
projection = pathlib.Path(args[args.index('--projection') + 1])
out.write_text(json.dumps({{'potentially_unused_functions': [{{'path': str(projection / 'src/app.py'),
 'line_number': 1, 'function_name': 'unused', 'confidence': 'high',
 'confidence_reason': 'fixture'}}]}}))
raise SystemExit({cgc_exit})
""",
    )
    return ScannerPaths(
        vulture=vulture,
        jscpd=jscpd,
        cgc_python=Path("/usr/bin/python3"),
        cgc_bridge=cgc,
        vulture_version="fixture-vulture",
        jscpd_version="fixture-jscpd",
        cgc_version="fixture-cgc",
    )


def test_cli_no_sandbox_runs_synthetic_scanners(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from modules.operations.scripts import archaeology as cli

    inventory_dir = tmp_path / "inventory"
    write_inventory(repository, inventory_dir)
    scanners = _scanners(tmp_path)
    monkeypatch.setattr(cli.ScannerPaths, "from_tools_root", lambda root: scanners)
    before = _git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    output = tmp_path / "hypotheses"
    assert cli.main([
        "hypotheses", "--inventory", str(inventory_dir / "inventory.json"),
        "--output", str(output), "--tools-root", str(tmp_path), "--no-sandbox",
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["observations"] == 3
    assert result["status"] == "PASS"
    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == before


def test_scanners_only_mint_observed_hypotheses_and_preserve_source(
    repository: Path, tmp_path: Path
) -> None:
    inventory_dir = tmp_path / "inventory"
    write_inventory(repository, inventory_dir)
    before = _git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    output = tmp_path / "hypotheses"
    payload = write_hypotheses(
        inventory_dir / "inventory.json", output, _scanners(tmp_path), use_sandbox=False
    )
    validate_self_hash(payload)
    assert payload["summary"] == {
        "observations": 3,
        "states": {"OBSERVED": 3},
        "tools_not_passed": 0,
        "tools_passed": 3,
    }
    assert {item["tool"] for item in payload["findings"]} == {
        "vulture",
        "jscpd",
        "codegraphcontext",
    }
    assert all(item["state"] == "OBSERVED" for item in payload["findings"])
    assert all(item["authority_granted"] is False for item in payload["findings"])
    assert all(item["cleanup_permitted"] is False for item in payload["findings"])
    assert {path for item in payload["findings"] for path in item["paths"]} <= {
        "src/app.py",
        "src/a.js",
        "src/b.js",
    }
    assert payload["authority_granted"] is False
    assert payload["cleanup_permitted"] is False
    assert (
        _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == before
    )
    rendered = (output / "hypotheses.json").read_text(encoding="utf-8")
    assert "SECRET" not in rendered
    assert "memory/private.py" not in rendered
    assert (output / "tools/jscpd.report.json").is_file()


def test_failed_tool_is_evidence_and_cannot_improve_state(
    repository: Path, tmp_path: Path
) -> None:
    inventory_dir = tmp_path / "inventory"
    write_inventory(repository, inventory_dir)
    payload = write_hypotheses(
        inventory_dir / "inventory.json",
        tmp_path / "hypotheses",
        _scanners(tmp_path, cgc_exit=7),
        use_sandbox=False,
    )
    cgc = next(item for item in payload["tools"] if item["id"] == "codegraphcontext")
    assert cgc["status"] == "ERROR"
    assert cgc["exit_code"] == 7
    assert payload["summary"]["tools_not_passed"] == 1
    assert "codegraphcontext" not in {item["tool"] for item in payload["findings"]}


def test_tampered_inventory_and_existing_output_refuse(
    repository: Path, tmp_path: Path
) -> None:
    inventory_dir = tmp_path / "inventory"
    write_inventory(repository, inventory_dir)
    path = inventory_dir / "inventory.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cleanup_permitted"] = True
    path.write_bytes(canonical_bytes(payload))
    with pytest.raises(HypothesisError, match="self-hash mismatch"):
        write_hypotheses(
            path, tmp_path / "hypotheses", _scanners(tmp_path), use_sandbox=False
        )

    clean_inventory = tmp_path / "clean-inventory"
    write_inventory(repository, clean_inventory)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(HypothesisError, match="must not already exist"):
        write_hypotheses(
            clean_inventory / "inventory.json",
            existing,
            _scanners(tmp_path),
            use_sandbox=False,
        )


def test_published_files_are_private(repository: Path, tmp_path: Path) -> None:
    inventory_dir = tmp_path / "inventory"
    write_inventory(repository, inventory_dir)
    output = tmp_path / "hypotheses"
    write_hypotheses(
        inventory_dir / "inventory.json", output, _scanners(tmp_path), use_sandbox=False
    )
    for path in output.rglob("*"):
        if path.is_file():
            assert os.stat(path, follow_symlinks=False).st_mode & 0o777 == 0o600
