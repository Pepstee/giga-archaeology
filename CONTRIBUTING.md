# Contributing to GIGA Archaeology

GIGA Archaeology is in developer beta. Read the [README](README.md) for the supported product scope and [beta validation notes](architecture/archaeology/BETA_VALIDATION.md) for what has and has not been verified.

## Set up the test environment

Use Python 3.11 or newer. Keep the development environment outside the repository.

On macOS or Linux:

```sh
python3 -m venv "$HOME/.venvs/giga-archaeology-dev"
. "$HOME/.venvs/giga-archaeology-dev/bin/activate"
```

In Windows PowerShell:

```powershell
python -m venv "$HOME\.venvs\giga-archaeology-dev"
& "$HOME\.venvs\giga-archaeology-dev\Scripts\Activate.ps1"
```

From the repository root, install the test dependencies and run the suite:

```sh
python -m pip install ".[test]"
python -m pip check
python -m pytest -q
```

The core mapping path does not need a model subscription or API key. Linux quarantine tests may need `bubblewrap` and working user namespaces. If the host denies a sandbox operation, the test should report that limitation explicitly. Do not change a denied operation into a passing security check.

## Keep tests safe and repeatable

Use synthetic repositories and temporary files in tests. Do not add company source, personal repositories, real mapper stores, reports, credentials or other private data to fixtures or commits. Keep generated stores outside the repository being scanned.

Tests should make their limits clear. A passing parser or fixture test does not establish whole-repository accuracy, runtime reachability or that deleting code is safe. Cross-platform claims need a successful run on the named operating system and Python version. Shared primitives or a partial test run are not enough.

## Prepare a change

For a code change, add or update a focused regression test. Update the README when the supported user workflow changes, and add a changelog entry for user-visible behavior. Keep unsupported or partial findings labeled that way. Do not describe a command as release-ready just because it appears in `--help`.

Before opening a pull request, run the full test suite and check the diff for generated files or private data. In the pull request, explain the user problem, the behavior that changed, the exact test command and environment, and any known limits. If a platform could not be tested, say so.

## Open a pull request

Keep each pull request focused. Include a link to the relevant issue when one exists, and call out changes to installation, stored data, CLI behavior or supported platforms. Avoid attaching mapper output because it can contain source code and absolute paths.
