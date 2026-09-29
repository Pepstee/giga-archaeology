from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.dossier import build_context_projection
from modules.operations.archaeology.javascript_map import (
    JavaScriptMapError,
    extract_javascript_file_fragment,
    javascript_backend_identity,
)
from modules.operations.archaeology.mapper import query_mapper, refresh_mapper
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


@pytest.fixture()
def javascript_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "scripts").mkdir()
    (root / "scripts/lib.mjs").write_text(
        "export function helper(value) { return value + 1; }\n",
        encoding="utf-8",
    )
    (root / "scripts/main.mjs").write_text(
        """#!/usr/bin/env node
import { helper } from "./lib.mjs";
import fs from "node:fs";
function run(input) {
  const local = helper(input);
  return local;
}
run(1);
fs.readFileSync("never-read.txt");
const fake = "function invented() { missing(); }";
""",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    (root / "src/model.ts").write_text(
        """export interface Item { value: number }
export type ItemName = string;
export function score(item: Item): number { return item.value + 1; }
export class Counter { next(value: number): number { return value + 1; } }
""",
        encoding="utf-8",
    )
    (root / "staging").mkdir()
    (root / "staging/main-copy.mjs").write_text(
        (root / "scripts/main.mjs").read_text(encoding="utf-8"),
        encoding="utf-8",
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


def test_tree_sitter_javascript_fragment_is_structural_and_non_executing() -> None:
    content = b"""import { helper as mapped } from "./lib.mjs";
export const run = input => mapped(input);
const fake = "function invented() { missing(); }";
"""
    fragment = extract_javascript_file_fragment("scripts/main.mjs", content)
    backend = javascript_backend_identity()

    assert backend["tree_sitter_version"] == "0.26.0"
    assert backend["javascript"]["grammar_version"] == "0.25.0"
    assert backend["typescript"]["grammar_version"] == "0.23.2"
    assert fragment["tree_root_type"] == "program"
    assert {item["name"] for item in fragment["definitions"]} == {"fake", "run"}
    assert fragment["imports"][0]["specifier"] == "./lib.mjs"
    assert fragment["imports"][0]["bindings"] == [
        {"imported_name": "helper", "local_name": "mapped"}
    ]
    assert fragment["imports"][0]["syntax"] == "ESM"
    assert fragment["exports"] == [
        {
            "exported_name": "run",
            "local_name": "run",
            "span": {
                "byte_start": 46,
                "byte_end": 88,
                "line_start": 2,
                "column_start": 0,
                "line_end": 2,
                "column_end": 42,
            },
            "syntax": "ESM",
        }
    ]
    assert [item["expression"] for item in fragment["calls"]] == ["mapped"]
    assert "input" in fragment["scope_bindings"]["run"]
    assert "invented" not in {item["name"] for item in fragment["references"]}
    assert "missing" not in {item["name"] for item in fragment["references"]}


def test_tree_sitter_javascript_refuses_error_tree_and_non_utf8() -> None:
    with pytest.raises(JavaScriptMapError, match="parse failed"):
        extract_javascript_file_fragment("broken.ts", b"export function broken( {")
    with pytest.raises(JavaScriptMapError, match="not UTF-8"):
        extract_javascript_file_fragment("broken.js", b"const value = '\xff';")


def test_m32_commonjs_extraction_refuses_shadowed_conditional_and_mixed_state() -> None:
    shadowed = extract_javascript_file_fragment(
        "shadowed.cjs",
        b'function require(value) { return value; }\nconst lib = require("./lib.cjs");\n',
    )
    assert shadowed["imports"] == []

    conditional = extract_javascript_file_fragment(
        "conditional.cjs",
        b'if (flag) { const lib = require("./lib.cjs"); exports.run = lib; }\n',
    )
    assert conditional["imports"] == []
    assert conditional["exports"] == []

    mixed = extract_javascript_file_fragment(
        "mixed.cjs",
        b"function run() {}\nexports.run = run;\nmodule.exports = run;\n",
    )
    assert mixed["exports"] == []


def test_m30_javascript_symbols_imports_calls_entrypoints_and_typescript(
    javascript_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(javascript_repository, tmp_path)
    counts = run.manifest["counts"]

    assert counts["javascript_files"] == 3
    assert counts["javascript_parse_failures"] == 0
    assert counts["javascript_modules"] == 3
    assert counts["javascript_symbols"] >= 9
    assert counts["javascript_imports"] == 2
    assert counts["javascript_imports_resolved"] == 1
    assert counts["javascript_calls"] == 3
    assert counts["javascript_calls_resolved"] == 2
    assert counts["javascript_cross_file_calls_resolved"] == 1
    assert counts["javascript_cross_file_references_resolved"] == 1
    assert counts["javascript_exports"] == 5
    assert counts["javascript_exports_resolved"] == 5
    assert counts["javascript_import_bindings"] == 2
    assert counts["javascript_import_bindings_resolved"] == 1
    assert counts["javascript_commonjs_imports"] == 0
    assert counts["javascript_entrypoints"] == 1
    assert (
        run.manifest["maps"]["symbols"]
        == "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_PARTIAL"
    )

    run_symbol = _one(
        query_mapper(mapper, "run", maps=("symbols",)),
        "JAVASCRIPT_SYMBOL",
        "scripts/main.mjs::module::function:run",
    )
    definitions = [
        item
        for item in run_symbol["facts"]["observations"]
        if item["predicate"] == "JAVASCRIPT_DEFINITION"
    ]
    assert definitions[0]["source"]["path"] == "scripts/main.mjs"
    assert definitions[0]["source"]["line_start"] == 4
    incoming = [
        item
        for item in run_symbol["facts"]["relations"]
        if item["predicate"] == "CALLS" and item["direction"] == "INCOMING"
    ]
    assert incoming[0]["truth_class"] == "INFERRED"
    assert incoming[0]["confidence"] == 0.75

    internal_import = _one(
        query_mapper(mapper, "./lib.mjs", maps=("dependencies",)),
        "JAVASCRIPT_IMPORT",
        "scripts/main.mjs::import:./lib.mjs",
    )
    assert internal_import["attributes"]["resolution"] == "EXACT_INVENTORY_PATH"
    assert internal_import["attributes"]["resolved_path"] == "scripts/lib.mjs"
    external_import = _one(
        query_mapper(mapper, "node:fs", maps=("dependencies",)),
        "JAVASCRIPT_IMPORT",
        "scripts/main.mjs::import:node:fs",
    )
    assert external_import["attributes"]["resolution"] == "EXTERNAL_PACKAGE"

    helper_call = _one(
        query_mapper(mapper, "helper", maps=("calls",)),
        "JAVASCRIPT_CALL",
        "scripts/main.mjs::call:helper@5:16",
    )
    assert helper_call["attributes"]["resolution"] == "EXACT_CROSS_FILE_IMPORT"
    assert helper_call["attributes"]["target_entity_id"] is not None
    helper_symbol = _one(
        query_mapper(mapper, "helper", maps=("symbols",)),
        "JAVASCRIPT_SYMBOL",
        "scripts/lib.mjs::module::function:helper",
    )
    assert helper_call["attributes"]["target_entity_id"] == helper_symbol["entity_id"]
    cross_file_incoming = [
        item
        for item in helper_symbol["facts"]["relations"]
        if item["predicate"] == "CALLS" and item["direction"] == "INCOMING"
    ]
    assert cross_file_incoming[0]["attributes"]["resolution"] == (
        "EXACT_CROSS_FILE_IMPORT"
    )

    interface = _one(
        query_mapper(mapper, "Item", maps=("symbols",)),
        "JAVASCRIPT_SYMBOL",
        "src/model.ts::module::interface:Item",
    )
    assert interface["attributes"]["language"] == "typescript"
    assert interface["attributes"]["symbol_kind"] == "INTERFACE"

    method = _one(
        query_mapper(mapper, "next", maps=("symbols",)),
        "JAVASCRIPT_SYMBOL",
        "src/model.ts::Counter::method:next",
    )
    owners = [
        item
        for item in method["facts"]["relations"]
        if item["predicate"] == "DEFINES" and item["direction"] == "INCOMING"
    ]
    assert owners[0]["other"]["qualified_name"] == (
        "src/model.ts::module::class:Counter"
    )

    endpoint = _one(
        query_mapper(mapper, "main.mjs", maps=("api_events",)),
        "ENTRYPOINT",
        "JAVASCRIPT_MODULE:scripts/main.mjs",
    )
    assert endpoint["attributes"]["kind"] == "JAVASCRIPT_MODULE"
    assert endpoint["attributes"]["shebang"] == "#!/usr/bin/env node"
    assert not any(
        item["source"]["path"].startswith("staging/")
        for item in query_mapper(mapper, "run", maps=("symbols",))["results"]
        if item["source"] is not None
    )

    context = build_context_projection(
        mapper,
        "implementation",
        ["run"],
        token_budget=220,
        limit_per_term=100,
        candidate_limit=500,
        fact_limit=10,
        include_semantic=False,
    )
    assert context["entries"][0]["kind"] == "JAVASCRIPT_SYMBOL"
    assert context["entries"][0]["qualified_name"] == (
        "scripts/main.mjs::module::function:run"
    )
    assert context["entries"][0]["ranking"]["exact_term_matches"] == 1


def test_m30_parse_failure_is_partial_and_does_not_publish_false_module(
    javascript_repository: Path, tmp_path: Path
) -> None:
    (javascript_repository / "scripts/broken.js").write_text(
        "export function broken( {\n", encoding="utf-8"
    )
    mapper, run = _compile(javascript_repository, tmp_path)

    assert run.manifest["counts"]["javascript_files"] == 3
    assert run.manifest["counts"]["javascript_parse_failures"] == 1
    result = query_mapper(mapper, "broken", maps=("symbols",))
    assert not any(item["kind"] == "JAVASCRIPT_MODULE" for item in result["results"])


def test_m32_resolves_esm_default_namespace_and_commonjs_calls_across_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "cross-file"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "esm").mkdir()
    (root / "esm/lib.ts").write_text(
        """export default function build() { return 1; }
export function named() { return 2; }
""",
        encoding="utf-8",
    )
    (root / "esm/main.ts").write_text(
        """import make, { named as calculate } from "./lib.ts";
import * as library from "./lib.ts";
make();
calculate();
library.named();
""",
        encoding="utf-8",
    )
    (root / "cjs").mkdir()
    (root / "cjs/lib.cjs").write_text(
        """function helper() { return 1; }
function privateHelper() { return 0; }
module.exports = { helper, alias: helper };
""",
        encoding="utf-8",
    )
    (root / "cjs/main.cjs").write_text(
        """const { helper: mapped } = require("./lib.cjs");
const library = require("./lib.cjs");
mapped();
library.alias();
library.privateHelper();
""",
        encoding="utf-8",
    )
    (root / "cjs/default.cjs").write_text(
        "function factory() { return 3; }\nmodule.exports = factory;\n",
        encoding="utf-8",
    )
    (root / "cjs/default-main.cjs").write_text(
        'const factory = require("./default.cjs");\nfactory();\n',
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "cross-file fixture")

    mapper, run = _compile(root, tmp_path)
    counts = run.manifest["counts"]
    assert counts["javascript_files"] == 6
    assert counts["javascript_imports"] == 5
    assert counts["javascript_commonjs_imports"] == 3
    assert counts["javascript_import_bindings"] == 6
    assert counts["javascript_import_bindings_resolved"] == 6
    assert counts["javascript_cross_file_calls_resolved"] == 6

    expected = {
        "esm/main.ts::call:make@3:0": (
            "EXACT_CROSS_FILE_IMPORT",
            "esm/lib.ts::module::function:build",
        ),
        "esm/main.ts::call:calculate@4:0": (
            "EXACT_CROSS_FILE_IMPORT",
            "esm/lib.ts::module::function:named",
        ),
        "esm/main.ts::call:library.named@5:0": (
            "EXACT_CROSS_FILE_NAMESPACE_MEMBER",
            "esm/lib.ts::module::function:named",
        ),
        "cjs/main.cjs::call:mapped@3:0": (
            "EXACT_CROSS_FILE_IMPORT",
            "cjs/lib.cjs::module::function:helper",
        ),
        "cjs/main.cjs::call:library.alias@4:0": (
            "EXACT_CROSS_FILE_NAMESPACE_MEMBER",
            "cjs/lib.cjs::module::function:helper",
        ),
        "cjs/default-main.cjs::call:factory@2:0": (
            "EXACT_CROSS_FILE_IMPORT",
            "cjs/default.cjs::module::function:factory",
        ),
    }
    for qualified_name, (resolution, target_qualified_name) in expected.items():
        call = _one(
            query_mapper(mapper, qualified_name, maps=("calls",)),
            "JAVASCRIPT_CALL",
            qualified_name,
        )
        target = _one(
            query_mapper(mapper, target_qualified_name, maps=("symbols",)),
            "JAVASCRIPT_SYMBOL",
            target_qualified_name,
        )
        assert call["attributes"]["resolution"] == resolution
        assert call["attributes"]["target_entity_id"] == target["entity_id"]

    private_call = _one(
        query_mapper(mapper, "library.privateHelper", maps=("calls",)),
        "JAVASCRIPT_CALL",
        "cjs/main.cjs::call:library.privateHelper@5:0",
    )
    assert private_call["attributes"]["resolution"] == (
        "UNRESOLVED_CROSS_FILE_NAMESPACE_MEMBER"
    )
    assert private_call["attributes"]["target_entity_id"] is None


def test_m32_refuses_ambiguous_paths_and_shadowed_commonjs_require(
    tmp_path: Path,
) -> None:
    root = tmp_path / "negative-cross-file"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "lib.js").write_text("export function work() {}\n", encoding="utf-8")
    (root / "lib.ts").write_text("export function work() {}\n", encoding="utf-8")
    (root / "main.js").write_text(
        'import { work } from "./lib";\nwork();\n', encoding="utf-8"
    )
    (root / "common.cjs").write_text(
        """function require(value) { return value; }
const library = require("./lib.js");
library.work();
""",
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "negative fixture")

    mapper, run = _compile(root, tmp_path)
    assert run.manifest["counts"]["javascript_commonjs_imports"] == 0
    ambiguous = _one(
        query_mapper(mapper, "./lib", maps=("dependencies",)),
        "JAVASCRIPT_IMPORT",
        "main.js::import:./lib",
    )
    assert ambiguous["attributes"]["resolution"] == "AMBIGUOUS_INVENTORY_PATH"
    call = _one(
        query_mapper(mapper, "work", maps=("calls",)),
        "JAVASCRIPT_CALL",
        "main.js::call:work@2:0",
    )
    assert call["attributes"]["target_entity_id"] is None
