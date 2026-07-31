#!/usr/bin/env python3
"""Repository-local entry point for provider-neutral scientific evidence."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from twin_core.scientific_evidence_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
