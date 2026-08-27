"""Read-only GIGA Archaeologist evidence pipeline.

Scanner observations are hypotheses.  Nothing in this package grants cleanup,
quarantine, deletion, or migration authority.
"""

from .inventory import InventoryError, InventoryPolicy, build_inventory, write_inventory
from .hypotheses import HypothesisError, ScannerPaths, build_hypotheses, write_hypotheses
from .counterevidence import (
    CounterevidenceError,
    build_counterevidence,
    write_counterevidence,
)

__all__ = [
    "HypothesisError",
    "CounterevidenceError",
    "InventoryError",
    "InventoryPolicy",
    "ScannerPaths",
    "build_hypotheses",
    "build_counterevidence",
    "build_inventory",
    "write_hypotheses",
    "write_counterevidence",
    "write_inventory",
]
