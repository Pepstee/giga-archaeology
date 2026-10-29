# GIGA Archaeology

Developer beta.

GIGA Archaeology maps a local Python Git repository into source-linked symbols and relationships, then builds bounded context for developers and coding agents.

The supported path makes no model/API calls and does not execute scanned code. Queries use structural and lexical matching. They do not certify feature completeness, capture every runtime call or show that code is safe to delete.

## Install

Python 3.11+ and Git are required. The latest full-suite run against the current canonical source
passed on ArtVault Linux with Python 3.12.3: 422 passed, 1 skipped, and 2 subtests passed. Earlier
Python 3.11–3.14 results cover a source revision before the location inventory was added. The earlier
macOS arm64 Python 3.14 canary covers 0.1.3b1/b2, not this candidate. Windows has not been verified.
Recent GitHub Actions jobs could not start; the last recorded GitHub annotation cited an account
[provider-specific account diagnostic removed]
[the validation record](architecture/archaeology/BETA_VALIDATION.md) for exact scope and history.

Obtain the wheel from the operator-provided beta bundle. This version is not claimed to be on PyPI.
Create an environment outside the repository you intend to scan, then install the wheel:

```sh
python3 -m venv "$HOME/.venvs/giga-archaeology"
. "$HOME/.venvs/giga-archaeology/bin/activate"
python -m pip install ./giga_archaeology-0.1.3b3-py3-none-any.whl
python -m pip check
giga-archaeology --help
```

On Windows, use PowerShell and the venv's executable paths directly:

```powershell
py -3.12 -m venv "$env:USERPROFILE/.venvs/giga-archaeology"
$python = "$env:USERPROFILE/.venvs/giga-archaeology/Scripts/python.exe"
& $python -m pip install "$PWD/giga_archaeology-0.1.3b3-py3-none-any.whl"
& $python -m pip check
& "$env:USERPROFILE/.venvs/giga-archaeology/Scripts/giga-archaeology.exe" --help
```

Pip installs the four pinned public Tree-sitter parser packages automatically. The core installation
does not require the Giga control plane, a model subscription, an API key or your own project checkout.
Parser packages are required by the current shared mapper even for Python-only repositories.

For offline installation, download the wheel and all its dependencies on a connected machine with the
same Python/platform, then install with `--no-index --find-links ./wheelhouse`. A wheelhouse is
platform-specific. Do not assume one downloaded on macOS will install on Linux or Windows.

## First scan and query

For a runnable Python walkthrough, see [`examples/quickstart.py`](examples/quickstart.py).
After installing Archaeology, run the script from a GIGA Archaeology source checkout or source
archive and pass a separate committed Git repository to scan:

```sh
python examples/quickstart.py /absolute/path/to/repository /absolute/path/to/new-output Serializer dumps
```

The first term drives the symbol query; every term is used for bounded context. The script refuses
output directories inside the repository or non-empty stores, then runs the inventory,
map, symbol-query, and bounded-context steps below. The resulting maps and context may contain source
code and absolute paths. Keep the output private. The script is included in the source archive, not
the runtime wheel.

Use a local Git repository with a commit. An extracted source archive alone is not a Git repository.
Keep all output stores outside the repository. Use an absolute path for both variables:

```sh
repo_path="/absolute/path/to/repository"
store_root="/absolute/path/to/archaeology-output"

giga-archaeology navigation-refresh --root "$repo_path" --store "$store_root/inventory"
giga-archaeology mapper-refresh --inventory-store "$store_root/inventory" --mapper-store "$store_root/maps"
giga-archaeology mapper-query --mapper-store "$store_root/maps" --view symbols --limit 10 --without-facts Serializer

giga-archaeology mapper-context --mapper-store "$store_root/maps" --token-budget 1200 --without-semantic implementation Serializer dumps loads > context.json
python -c 'import json; print(json.load(open("context.json"))["context"])'
```

Replace the query terms with actual class/function names from your repository. Queries use structural
and lexical matching; they are not a natural-language semantic search service. `navigation-refresh`
returns the admitted file count; `mapper-refresh` returns entity/relation counts and a receipt identity.
Inspect coverage and failure fields before treating output as complete. Refresh inventory and maps
after source changes; previously generated maps are tied to an exact source snapshot.

Example compact context from the ItsDangerous 2.2.0 canary:

```text
src/itsdangerous/serializer.py:L311-L322 | PYTHON_SYMBOL | itsdangerous.serializer.Serializer.dumps(...)
src/itsdangerous/serializer.py:L330-L345 | PYTHON_SYMBOL | itsdangerous.serializer.Serializer.loads(...)
```

The abbreviated signatures above are illustrative; actual output includes full signatures.

## The context budget is not the JSON response size

`--token-budget` bounds only the `context` field using the documented `giga.lexical-token.v1` counter.
It is not a provider tokenizer guarantee. The JSON envelope also contains coverage, provenance and
other evidence and can be much larger. Feed only `context` to a model when a compact source index is
wanted; retain the full JSON separately for audit. Do not advertise model-token savings from byte counts.

## Supported release scope

- Local Python Git repositories: inventory, syntax-level symbols/imports/static calls and source locations.
- `navigation-refresh`, `navigation-status`, `mapper-refresh`, `mapper-status`, `mapper-query`,
  `mapper-context`, and inspection of the resulting evidence.
- Static results distinguish covered, partial, unsupported and failed evidence. Source locations can be
  checked against the exact source revision.

The CLI exposes more commands than this release certifies. JavaScript/TypeScript/Bash parsing, SCIP,
semantic/Graphify extraction, external scanners, governance feeds, retention, quarantine and automated
cleanup are not part of the supported beta promise. Their presence in `--help` is not readiness evidence.
Dynamic Python dispatch, monkey patching, generated code and namespace-package resolution can remain
partial or unresolved. Static non-reachability is never proof that deletion is safe.

## Project location inventory (Issue #2)

The source checkout also provides `locations-inspect`, `locations-refresh`, and
`locations-query` for explicit registered project roots. They record declared
ownership/canon levels separately from local Git metadata, preserve unknowns and
conflicts, and report the exact inspected scope. See the
[location inventory contract](architecture/archaeology/LOCATION_INVENTORY.md) for
inputs, examples, privacy boundaries and the metadata-only dirty-state limitation.

## Optional Giga integration

Repositories with JSON capability manifests under `capabilities/manifests/` need the existing Giga
validator. The core mapper refuses those manifests explicitly when the integration is absent rather
than silently claiming validation. Existing Giga operators can install `giga-archaeology[giga]` with an
approved local `giga-user-control-plane==0.1.0` wheel available through `--find-links`. That integration
is not included or publicly distributed in the standalone beta bundle.

## Evidence and limitations

The real-repository canary used Pallets' ItsDangerous 2.2.0, upstream commit
`096c8d42545d3b68ea21a4f890fb2b2d8979c0bd`: https://github.com/pallets/itsdangerous/tree/2.2.0.
The 60-file scan produced 1,457 entities and 2,649 relations in the initial 0.1.2 run. Five class/method
locations and one static call were independently checked against the source. Those checks are useful
anchors, not a measurement of whole-repository precision/recall. The source stayed unchanged.

The earlier seven-file synthetic canary independently checked five functions, their source spans and
three static call relationships. Version 0.1.2 repaired the undeclared parser dependencies it exposed.
See `architecture/archaeology/BETA_VALIDATION.md` for this release's verification and exact limitations.

Mapping results and full evidence can contain source code and absolute paths. Treat output as private
unless you have reviewed it for sharing. The deterministic supported path stays local; do not interpret
this as certification of every optional external tool or a complete secret-detection guarantee.

## Run the test suite

The `test` extra installs pytest and Graphify for the optional Graphify-adapter tests; neither is a
runtime dependency of the standalone core package.

```sh
python -m pip install ".[test]"
python -m pytest -q
```

Linux runs that exercise the quarantine sandbox also require `bubblewrap` and working unprivileged
user namespaces. Install `bubblewrap` with the operating system package manager before running the full
suite. Tests for optional commands do not expand the supported release scope listed above.

## Distribution status

This is a release candidate prepared for operator review, not a published public release.
Archaeology is licensed under the MIT License. See LICENSE for the full terms.
Third-party dependencies retain their own licences. This package is not affiliated with Pallets.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup, test expectations and pull request guidance.
