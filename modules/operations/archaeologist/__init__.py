"""Compatibility import surface for the renamed GIGA Archaeology package.

``modules.operations.archaeology`` is the canonical owner.  This package exists
only so already-installed launchers and third-party imports do not fail during
the identity migration.  Every legacy submodule name resolves to the exact
canonical module object; no implementation is duplicated here.
"""

from __future__ import annotations

import importlib
import sys


_CANONICAL_PACKAGE = "modules.operations.archaeology"
_SUBMODULES = (
    "benchmark",
    "capability_feed",
    "cgc_bridge",
    "cleanup_map",
    "consultation",
    "counterevidence",
    "dossier",
    "evidence",
    "flow_policy",
    "governance_map",
    "history",
    "hypotheses",
    "inventory",
    "javascript_map",
    "judge",
    "map_catalog",
    "mapper",
    "navigation_inventory",
    "navigation_maintenance",
    "operational_map",
    "python_map",
    "quality_map",
    "quarantine",
    "retention",
    "runtime_map",
    "scip_map",
    "semantic_graph",
    "shell_map",
)

_canonical = importlib.import_module(_CANONICAL_PACKAGE)
for _name in _SUBMODULES:
    _module = importlib.import_module(f"{_CANONICAL_PACKAGE}.{_name}")
    globals()[_name] = _module
    sys.modules[f"{__name__}.{_name}"] = _module

for _name in _canonical.__all__:
    globals()[_name] = getattr(_canonical, _name)

__all__ = tuple(_canonical.__all__)
