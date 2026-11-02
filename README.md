# GIGA Archaeology

Map a committed Python repository before debugging, reviewing, or handing code to an AI coding agent. GIGA Archaeology inventories admitted files, Python symbols, imports, and statically visible calls, then returns bounded, source-linked context for the exact repository revision.

Its core path is deterministic: it reads source without executing repository code and does not call a model API.

Queries combine structural and lexical matching. Coverage may be partial, and dynamic behavior can be missed. Treat findings as navigation evidence, never as proof that code is safe to remove.

## What you get

- File inventory and source-linked symbol, import, and call maps.
- Queries that return source locations and bounded context with explicit coverage and omissions.
- Local evidence tied to the inspected repository revision; output stays local until you choose to share it.

## Beta status

Version 0.1.3b4 is an unpublished developer beta. The latest full source suite passed on Linux
x86_64 with CPython 3.12.3: 444 passed, 1 skipped, and 2 subtests passed. That run covers Linux
only. Full macOS and Windows source suites for this release remain unverified.

The latest GitHub Actions run stopped before any job step, so it produced no hosted test result.
The current wheel and source archive passed static inspection. Their exact-hash install checks are
still pending. See [beta validation](architecture/archaeology/BETA_VALIDATION.md) for scope and
limits, and the [release evidence ledger](evidence/release-artifacts/0.1.3b4.json) for build
records.

## Install from a source checkout

Python 3.11+ and Git are required. No package has been published to PyPI. Once the GitHub
repository is public, clone the source and create an environment:

```sh
git clone https://github.com/Pepstee/giga-archaeology.git
cd giga-archaeology
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python -m pip check
giga-archaeology --help
```

On Windows, use PowerShell:

```powershell
git clone https://github.com/Pepstee/giga-archaeology.git
Set-Location .\giga-archaeology
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install .
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\giga-archaeology.exe --help
```

Pip installs the four pinned Tree-sitter parser packages. The core does not clone the target
repository or require remote credentials; provide a local Git checkout with at least one commit.
Parser packages are required by the shared mapper, including for Python-only repositories.

For offline installation, download the wheel and its dependencies on a connected machine with the
same Python version and platform, then install with `--no-index --find-links ./wheelhouse`. A
wheelhouse is platform-specific.

## First scan and query

The quickstart script is included in the source archive, not the runtime wheel. After installing
Archaeology, clone the tested ItsDangerous 2.2.0 tag and pass that committed Git repository to the
script. Keep the output store outside both checkouts.

macOS and Linux:

```sh
git clone --depth 1 --branch 2.2.0 https://github.com/pallets/itsdangerous.git ../itsdangerous-2.2.0
store_root="$(mktemp -d ../archaeology-output.XXXXXX)"
python examples/quickstart.py "$(cd ../itsdangerous-2.2.0 && pwd)" "$store_root" Serializer dumps
```

Windows PowerShell:

```powershell
git clone --depth 1 --branch 2.2.0 https://github.com/pallets/itsdangerous.git ..\itsdangerous-2.2.0
$targetRepo = (Resolve-Path ..\itsdangerous-2.2.0).Path
$storeRoot = Join-Path $env:TEMP ("giga-archaeology-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $storeRoot | Out-Null
& .\.venv\Scripts\python.exe .\examples\quickstart.py $targetRepo $storeRoot Serializer dumps
```

The run writes `navigation.json`, `mapper.json`, `query.json`, and `context.json` to the output
store. Expect `CURRENT` inventory and map statuses and a `PASS` symbol query. The script prints a
bounded source-linked context; its evidence can include source code and absolute paths, so keep the
store private. Replace `Serializer` and `dumps` with names from your repository when scanning your
own code.

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
