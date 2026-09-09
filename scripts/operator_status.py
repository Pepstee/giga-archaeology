#!/usr/bin/env python3
"""Compile the read-only GIGA operator-status snapshot."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from twin_core.operator_status import (  # noqa: E402
    AdapterAdmissionError,
    admit_no_write_adapter,
    OperatorStatusError,
    canonical_json,
    compile_status,
    render_summary,
)


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _admission_for_run(root: Path, no_write: bool) -> dict | None:
    """Admit the official read-only adapter for the no-write onramp only."""
    if not no_write:
        return None
    return admit_no_write_adapter(root)


def _reject_mutation_with_admission(admission: dict | None, no_write: bool) -> None:
    if admission is not None and not no_write:
        raise AdapterAdmissionError(
            "adapter-admission-write-conflict",
            "the admitted no-write authority cannot justify a mutating output path",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--observed-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument(
        "--runtime-evidence", help="repository-relative runtime evidence packet"
    )
    parser.add_argument("--stale-after-seconds", type=int, default=86_400)
    parser.add_argument("--output", default="outputs/operator-status/latest.json")
    parser.add_argument(
        "--json",
        action="store_true",
        help="print canonical JSON instead of the human summary",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="validate and print without writing the snapshot",
    )
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        admission = _admission_for_run(root, args.no_write)
        payload = compile_status(
            root,
            args.observed_at,
            runtime_evidence=args.runtime_evidence,
            stale_after_seconds=args.stale_after_seconds,
            admission=admission,
        )
        serialized = canonical_json(payload)
        if not args.no_write:
            _reject_mutation_with_admission(admission, args.no_write)
            output = Path(args.output)
            if output.is_absolute():
                raise OperatorStatusError("absolute output paths are forbidden")
            destination = (root / output).resolve()
            try:
                destination.relative_to(root)
            except ValueError as exc:
                raise OperatorStatusError(
                    "output path escapes repository root"
                ) from exc
            _write_atomic(destination, serialized)
        sys.stdout.write(serialized if args.json else render_summary(payload))
        return 0
    except (OperatorStatusError, OSError) as exc:
        print(f"operator-status: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
