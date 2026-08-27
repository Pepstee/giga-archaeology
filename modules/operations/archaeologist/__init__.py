"""Read-only GIGA Archaeologist evidence pipeline.

Scanner observations are hypotheses.  Nothing in this package grants cleanup,
quarantine, deletion, or migration authority.
"""

from .inventory import InventoryError, InventoryPolicy, build_inventory, write_inventory

__all__ = ["InventoryError", "InventoryPolicy", "build_inventory", "write_inventory"]
