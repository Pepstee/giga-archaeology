# Install the portable GIGA control folder

Use Python 3.11 or later. Unpack the source distribution into the folder you want to retain, then run from that folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps --no-build-isolation .
.venv/bin/giga-derived-payloads --root "$PWD" --mode staged-v2 --write
.venv/bin/giga-derived-payloads --root "$PWD" --mode staged-v2
.venv/bin/giga-twin --help
```

The build has no build dependencies and the base package has no runtime dependencies. Generation creates local derived settings from the included templates and binds them to CHARTER.md and CONTEXT.md. These files remain unverified or staged. Installation does not change any account settings or activate providers, daemons or corpus access. Read the canonical governance files before using derived settings.

Linux capability-owner status uses the separately delivered `giga-archaeology` wheel, version `0.1.0+7d652482`, and system bubblewrap. Install that wheel into the same environment before using the optional status capability. Research extras listed in pyproject.toml are optional. Inference Fabric remains its separately migrated project, not a bundled duplicate.

The source distribution uses an explicit allowlist. It excludes the personal corpus, memory contents, live registries, credentials, activation receipts, private runtime state and unrelated projects. Host-bound corpus commands refuse access until an independently authorised activation mechanism exists.

This file owns portable installation instructions. Existing ArtVault bootstrap and project-specific deployment scripts configure different systems and are not a GIGA package installer.
