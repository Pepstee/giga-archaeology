from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.mapper import query_mapper, refresh_mapper
from modules.operations.archaeology.dossier import build_context_projection
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)
from modules.operations.archaeology.shell_map import (
    ShellMapError,
    extract_shell_file_fragment,
    shell_backend_identity,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


@pytest.fixture()
def shell_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "scripts").mkdir()
    (root / "scripts/task.py").write_text("print('task')\n", encoding="utf-8")
    (root / "scripts/lib.sh").write_text(
        "#!/usr/bin/env bash\nLIB_MODE=ready\n", encoding="utf-8"
    )
    (root / "scripts/run.sh").write_text(
        """#!/usr/bin/env bash
set -u
MODE=ready
helper() {
  printf '%s\\n' "$MODE"
}
helper
python3 scripts/task.py
source scripts/lib.sh
VALUE=$(python3 - <<'PY'
from pathlib import Path
print(Path.cwd())
PY
)
printf '%s\\n' "$VALUE" "$HOME"
""",
        encoding="utf-8",
    )
    (root / "staging").mkdir()
    (root / "staging/run-copy.sh").write_text(
        (root / "scripts/run.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _compile(root: Path, tmp_path: Path):
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    return mapper, refresh_mapper(inventory, mapper)


def _one(result: dict, kind: str, qualified_name: str) -> dict:
    matches = [
        item
        for item in result["results"]
        if item["kind"] == kind and item["qualified_name"] == qualified_name
    ]
    assert len(matches) == 1, result["results"]
    return matches[0]


def test_tree_sitter_bash_fragment_is_structural_and_non_executing() -> None:
    content = b"""#!/usr/bin/env bash
MODE=ready
run() { printf '%s\\n' "$MODE"; }
run
python3 scripts/task.py
VALUE=$(python3 - <<'PY'
import definitely_not_a_shell_command
PY
)
"""
    fragment = extract_shell_file_fragment("scripts/run.sh", content)

    assert shell_backend_identity()["grammar_version"] == "0.25.1"
    assert fragment["tree_root_type"] == "program"
    assert [item["name"] for item in fragment["functions"]] == ["run"]
    assert {item["name"] for item in fragment["assignments"]} == {"MODE", "VALUE"}
    command_names = {item["name"] for item in fragment["commands"]}
    assert {"printf", "run", "python3"} <= command_names
    assert "import" not in command_names
    assert "definitely_not_a_shell_command" not in command_names
    dependencies = {
        dependency
        for command in fragment["commands"]
        for dependency in command["script_dependencies"]
    }
    assert dependencies == {"scripts/task.py"}


def test_tree_sitter_bash_refuses_error_tree() -> None:
    with pytest.raises(ShellMapError, match="parse failed"):
        extract_shell_file_fragment("broken.sh", b"if true; then\n")


def test_m25_shell_symbols_references_commands_dependencies_and_entrypoints(
    shell_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(shell_repository, tmp_path)
    counts = run.manifest["counts"]
    assert counts["shell_files"] == 2
    assert counts["shell_parse_failures"] == 0
    assert counts["shell_functions"] == 1
    assert counts["shell_variables"] >= 3
    assert counts["shell_references"] >= 3
    assert counts["shell_references_resolved"] >= 2
    assert counts["shell_commands"] >= 5
    assert counts["shell_function_calls"] == 1
    assert counts["shell_dependencies"] == 2
    assert counts["shell_dependencies_resolved"] == 2
    assert counts["shell_entrypoints"] == 2
    assert (
        run.manifest["maps"]["symbols"]
        == "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_PARTIAL"
    )

    helper = _one(
        query_mapper(mapper, "helper", maps=("symbols",)),
        "SHELL_SYMBOL",
        "scripts/run.sh::function:helper",
    )
    assert helper["attributes"]["symbol_kind"] == "FUNCTION"
    definitions = [
        item
        for item in helper["facts"]["observations"]
        if item["predicate"] == "SHELL_DEFINITION"
    ]
    assert definitions[0]["source"]["path"] == "scripts/run.sh"
    assert definitions[0]["source"]["line_start"] == 4
    calls = [
        item
        for item in helper["facts"]["relations"]
        if item["predicate"] == "CALLS" and item["direction"] == "INCOMING"
    ]
    assert calls[0]["truth_class"] == "INFERRED"
    assert calls[0]["confidence"] == 0.75

    mode = _one(
        query_mapper(mapper, "MODE", maps=("symbols",)),
        "SHELL_SYMBOL",
        "scripts/run.sh::script::variable:MODE",
    )
    references = [
        item
        for item in mode["facts"]["observations"]
        if item["predicate"] == "SHELL_REFERENCE"
    ]
    assert references[0]["value"]["resolution"] == "SAME_SCRIPT_DECLARATION"
    assert references[0]["source"]["line_start"] == 5

    dependency_result = query_mapper(mapper, "scripts/task.py", maps=("dependencies",))
    dependency = _one(
        dependency_result,
        "SHELL_DEPENDENCY",
        "scripts/run.sh::dependency:scripts/task.py",
    )
    assert dependency["attributes"]["resolution"] == "EXACT_INVENTORY_PATH"
    assert dependency["attributes"]["resolved_path"] == "scripts/task.py"

    endpoint = _one(
        query_mapper(mapper, "run.sh", maps=("api_events",)),
        "ENTRYPOINT",
        "SHELL_SCRIPT:scripts/run.sh",
    )
    assert endpoint["attributes"]["kind"] == "SHELL_SCRIPT"
    assert endpoint["attributes"]["executable"] is False
    assert not any(
        item["source"]["path"].startswith("staging/")
        for item in query_mapper(mapper, "run", maps=("symbols",))["results"]
        if item["source"] is not None
    )

    context = build_context_projection(
        mapper,
        "implementation",
        ["helper"],
        token_budget=200,
        limit_per_term=100,
        candidate_limit=500,
        fact_limit=10,
        include_semantic=False,
    )
    assert context["entries"][0]["kind"] == "SHELL_SYMBOL"
    assert context["entries"][0]["qualified_name"] == "scripts/run.sh::function:helper"
    assert context["entries"][0]["ranking"]["exact_term_matches"] == 1
