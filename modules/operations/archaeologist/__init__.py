"""Read-only GIGA Archaeologist evidence pipeline.

Scanner observations are hypotheses.  Nothing in this package grants cleanup,
quarantine, deletion, or migration authority.
"""

from .inventory import InventoryError, InventoryPolicy, build_inventory, write_inventory
from .history import HistoryError, build_history, write_history
from .hypotheses import HypothesisError, ScannerPaths, build_hypotheses, write_hypotheses
from .counterevidence import (
    CounterevidenceError,
    build_counterevidence,
    write_counterevidence,
)

__all__ = [
    "HypothesisError",
    "HistoryError",
    "CounterevidenceError",
    "InventoryError",
    "InventoryPolicy",
    "ScannerPaths",
    "build_hypotheses",
    "build_history",
    "build_counterevidence",
    "build_inventory",
    "write_hypotheses",
    "write_history",
    "write_counterevidence",
    "write_inventory",
]
