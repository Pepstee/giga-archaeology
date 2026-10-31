from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "modules/platform/packaging/archaeology_build_backend.py"
SPEC = importlib.util.spec_from_file_location("archaeology_build_backend", BACKEND_PATH)
assert SPEC is not None and SPEC.loader is not None
BACKEND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BACKEND)
QUICKSTART_PATH = ROOT / "examples/quickstart.py"
QUICKSTART_SPEC = importlib.util.spec_from_file_location("archaeology_quickstart", QUICKSTART_PATH)
assert QUICKSTART_SPEC is not None and QUICKSTART_SPEC.loader is not None
QUICKSTART = importlib.util.module_from_spec(QUICKSTART_SPEC)
QUICKSTART_SPEC.loader.exec_module(QUICKSTART)


def test_quickstart_is_in_source_archive_but_not_runtime_wheel(tmp_path: Path) -> None:
    wheel_name = BACKEND.build_wheel(str(tmp_path))
    sdist_name = BACKEND.build_sdist(str(tmp_path))

    with zipfile.ZipFile(tmp_path / wheel_name) as wheel:
        assert "examples/quickstart.py" not in wheel.namelist()
    with tarfile.open(tmp_path / sdist_name, "r:gz") as sdist:
        expected = f"{BACKEND.NAME}-{BACKEND.VERSION}/examples/quickstart.py"
        assert expected in sdist.getnames()
        assert sdist.extractfile(expected) is not None


def test_contributing_guide_is_in_both_distributions(tmp_path: Path) -> None:
    wheel_name = BACKEND.build_wheel(str(tmp_path))
    sdist_name = BACKEND.build_sdist(str(tmp_path))
    expected_sdist = f"{BACKEND.NAME}-{BACKEND.VERSION}/CONTRIBUTING.md"
    expected_content = (ROOT / "CONTRIBUTING.md").read_bytes()

    with zipfile.ZipFile(tmp_path / wheel_name) as wheel:
        assert wheel.read("CONTRIBUTING.md") == expected_content
    with tarfile.open(tmp_path / sdist_name, "r:gz") as sdist:
        assert expected_sdist in sdist.getnames()
        member = sdist.extractfile(expected_sdist)
        assert member is not None and member.read() == expected_content


def test_readme_and_validation_record_are_in_both_distributions(tmp_path: Path) -> None:
    wheel_name = BACKEND.build_wheel(str(tmp_path))
    sdist_name = BACKEND.build_sdist(str(tmp_path))
    expected = {
        "README.md": (ROOT / "README.md").read_bytes(),
        "architecture/archaeology/BETA_VALIDATION.md": (
            ROOT / "architecture/archaeology/BETA_VALIDATION.md"
        ).read_bytes(),
    }

    with zipfile.ZipFile(tmp_path / wheel_name) as wheel:
        for name, content in expected.items():
            assert wheel.read(name) == content

    prefix = f"{BACKEND.NAME}-{BACKEND.VERSION}/"
    with tarfile.open(tmp_path / sdist_name, "r:gz") as sdist:
        for name, content in expected.items():
            member = sdist.extractfile(prefix + name)
            assert member is not None and member.read() == content


def test_release_metadata_includes_search_terms_and_project_links(tmp_path: Path) -> None:
    wheel_name = BACKEND.build_wheel(str(tmp_path))
    with zipfile.ZipFile(tmp_path / wheel_name) as wheel:
        metadata_name = next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = wheel.read(metadata_name).decode("utf-8")
    assert "Keywords: repository-analysis, source-mapping, static-analysis, coding-agents\n" in metadata
    assert "Project-URL: Repository, https://github.com/Pepstee/giga-archaeology\n" in metadata
    assert "Project-URL: Issues, https://github.com/Pepstee/giga-archaeology/issues\n" in metadata
    project_version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert BACKEND.VERSION == project_version
    assert f"Version: {project_version}\n" in metadata
    assert wheel_name == f"giga_archaeology-{project_version}-py3-none-any.whl"


def test_quickstart_refuses_store_inside_repository() -> None:
    store = ROOT / "examples" / ".quickstart-test-store"
    assert not store.exists()

    try:
        QUICKSTART.main([str(ROOT), str(store), "Serializer"])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("quickstart accepted an output store inside the source repository")
    assert not store.exists()


def test_quickstart_preserves_nonempty_external_store(tmp_path: Path) -> None:
    store = tmp_path / "existing-store"
    store.mkdir()
    sentinel = store / "keep.txt"
    sentinel.write_text("operator data", encoding="utf-8")

    try:
        QUICKSTART.main([str(ROOT), str(store), "Serializer"])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("quickstart accepted a non-empty output store")
    assert sentinel.read_text(encoding="utf-8") == "operator data"


def test_quickstart_runs_end_to_end_on_committed_repository(
    tmp_path: Path, monkeypatch
) -> None:
    repository = tmp_path / "source"
    repository.mkdir()
    (repository / "totals.py").write_text(
        "def calculate_total(values):\n"
        "    return sum(values)\n\n"
        "class Invoice:\n"
        "    def __init__(self, values):\n"
        "        self.values = values\n\n"
        "    def total(self):\n"
        "        return calculate_total(self.values)\n",
        encoding="utf-8",
    )

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-q")
    git("config", "user.name", "Archaeology Synthetic Test")
    git("config", "user.email", "archaeology-test@example.invalid")
    git("add", "totals.py")
    git("commit", "-q", "-m", "add synthetic invoice source")

    inherited_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = os.pathsep.join(
        item for item in (str(ROOT), inherited_pythonpath) if item
    )
    monkeypatch.setenv("PYTHONPATH", pythonpath)
    store = tmp_path / "output"

    assert QUICKSTART.main(
        [str(repository), str(store), "calculate_total", "Invoice"]
    ) == 0

    navigation = json.loads((store / "navigation.json").read_text(encoding="utf-8"))
    mapper = json.loads((store / "mapper.json").read_text(encoding="utf-8"))
    query = json.loads((store / "query.json").read_text(encoding="utf-8"))
    context = json.loads((store / "context.json").read_text(encoding="utf-8"))
    assert navigation["status"] == "CURRENT"
    assert navigation["files"] == 1
    assert mapper["status"] == "CURRENT"
    assert mapper["entities"] > 0
    assert mapper["relations"] > 0
    assert query["status"] == "PASS"
    assert any(row["name"] == "calculate_total" for row in query["results"])
    assert context["status"] == "PASS"
    assert "calculate_total" in context["context"]
    assert "Invoice" in context["context"]


@pytest.mark.parametrize(
    ("entrypoint", "program"),
    (
        ("archaeology", "giga-archaeology"),
        ("archaeologist", "giga-archaeologist"),
    ),
)
def test_console_entrypoint_help_uses_its_command_name(
    entrypoint: str, program: str, capsys: pytest.CaptureFixture[str]
) -> None:
    if entrypoint == "archaeology":
        from modules.operations.scripts.archaeology import main
    else:
        from modules.operations.scripts.archaeologist import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.startswith(f"usage: {program} ")
