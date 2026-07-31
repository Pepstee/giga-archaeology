#!/usr/bin/env python3
"""Calculate and persist the GIGA Sovereignty Index."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from twin_core.sovereignty import (  # noqa: E402
    MODEL_VERSION,
    RESULT_SCHEMA,
    SovereigntyError,
    calculate,
    canonical_json,
    render_markdown,
)


DEFAULT_STATE = Path.home() / ".giga" / "sovereignty"


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _load(path: Path) -> dict:
    import json

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SovereigntyError(f"cannot read valid JSON from {path}") from exc
    if not isinstance(value, dict):
        raise SovereigntyError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assessment", type=Path, help="assessment JSON using the v1 contract")
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=DEFAULT_STATE,
        help="private result directory (default: ~/.giga/sovereignty)",
    )
    parser.add_argument("--previous", type=Path, help="explicit previous result for trend comparison")
    parser.add_argument("--no-write", action="store_true", help="validate and print without persistence")
    parser.add_argument("--json", action="store_true", help="print canonical JSON instead of Markdown")
    args = parser.parse_args()

    try:
        assessment = _load(args.assessment.expanduser())
        state_dir = args.state_dir.expanduser().resolve()
        latest = state_dir / "latest.json"
        previous = None
        if args.previous:
            previous = _load(args.previous.expanduser())
        elif latest.exists():
            candidate = _load(latest)
            compatible = (
                candidate.get("schema_version") == RESULT_SCHEMA
                and candidate.get("model_version") == MODEL_VERSION
            )
            if (
                compatible
                and candidate.get("assessment_id") != assessment.get("assessment_id")
            ):
                previous = candidate
        result = calculate(assessment, previous=previous)
        serialized = canonical_json(result)
        markdown = render_markdown(result)
        if not args.no_write:
            history = state_dir / "history" / result["model_version"] / (
                f"{result['period_end']}_{result['assessment_id']}.json"
            )
            history_exists = history.exists()
            if history_exists:
                if history.read_text(encoding="utf-8") != serialized:
                    raise SovereigntyError(
                        f"history snapshot already exists with different content: {history}"
                    )
            else:
                _write_atomic(history, serialized)
            _write_atomic(latest, serialized)
            _write_atomic(state_dir / "latest.md", markdown)
        sys.stdout.write(serialized if args.json else markdown)
        return 0
    except (OSError, SovereigntyError) as exc:
        print(f"sovereignty-index: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
