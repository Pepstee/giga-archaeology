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

Linux capability-owner status uses the separately delivered `giga-archaeology` wheel, version `0.1.1`, and system bubblewrap. Install that wheel into the same environment before using the optional status capability. Research extras listed in pyproject.toml are optional. Inference Fabric remains its separately migrated project, not a bundled duplicate.

The source distribution uses an explicit allowlist. It excludes the personal corpus, memory contents, live registries, credentials, activation receipts, private runtime state and unrelated projects. Host-bound corpus commands refuse access until an independently authorised activation mechanism exists.

This file owns portable installation instructions. Existing ArtVault bootstrap and project-specific deployment scripts configure different systems and are not a GIGA package installer.

AGENTS.md ships with the folder and resolves CHARTER.md and CONTEXT.md locally. Host-specific external workspace authority remains limited to the named host path. Programme status, numbered workstream briefs and personal project state are not installation assets; provide the exact authorised workstream separately when needed. Host-installed skills are dependencies of the agent environment, not silently bundled or activated by this package.

## Deterministic ECC and SkillTree tools

The source distribution also retains `ecc-integration/scripts/` and the SkillTree audit
at `deploy/skills/skilltree-operator/scripts/audit_tree.py`, with their pinned public
inventory, findings, contracts and taxonomy inputs. These files are tools, not automatically
activated agent skills. Run their `--help` commands with the installation's Python.

Generate a new SkillTree registry for this installation using the audit tool's explicit
`--root`, `--export`, `--evidence-map`, `--output` and `--report` arguments. Generated
registries and private evidence are not packaged. Missing evidence must remain missing.
The retained evidence map describes the original source installation and contains host-specific
references. It does not establish that those capabilities are installed on another host.

The extraction validator accepts `--upstream` pointing to the separately preserved ECC pin.
Its complete check also requires a freshly generated SkillTree registry and matching status
report under `skilltree/`, with `IMPLEMENTATION_REPORT.md` symlinked to
`IMPLEMENTATION_STATUS.md`. It refuses missing inputs or stale reports. The upstream drift and
inventory tools additionally require an ECC Git checkout; a source-only seal supplies file
validation but does not supply Git history. Nothing here fetches or deploys automatically.
