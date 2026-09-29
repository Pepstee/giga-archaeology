from __future__ import annotations

import importlib.util
import tarfile
import zipfile
from pathlib import Path


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


def test_release_metadata_includes_search_terms_and_project_links(tmp_path: Path) -> None:
    wheel_name = BACKEND.build_wheel(str(tmp_path))
    with zipfile.ZipFile(tmp_path / wheel_name) as wheel:
        metadata_name = next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = wheel.read(metadata_name).decode("utf-8")
    assert "Keywords: repository-analysis, source-mapping, static-analysis, coding-agents\n" in metadata
    assert "Project-URL: Repository, https://github.com/Pepstee/giga-archaeology\n" in metadata
    assert "Project-URL: Issues, https://github.com/Pepstee/giga-archaeology/issues\n" in metadata


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
