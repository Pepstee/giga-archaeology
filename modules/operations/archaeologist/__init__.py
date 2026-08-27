"""Read-only GIGA Archaeologist evidence pipeline.

Scanner observations are hypotheses.  Nothing in this package grants cleanup,
quarantine, deletion, or migration authority.
"""

from .inventory import InventoryError, InventoryPolicy, build_inventory, write_inventory
from .hypotheses import HypothesisError, ScannerPaths, build_hypotheses, write_hypotheses

__all__ = [
    "HypothesisError",
    "InventoryError",
    "InventoryPolicy",
    "ScannerPaths",
    "build_hypotheses",
    "build_inventory",
    "write_hypotheses",
    "write_inventory",
]
