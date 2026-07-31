#!/usr/bin/env python3
"""Run Codex review with a schema-bound verdict; exit zero only for PASS."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "CHANGES_REQUIRED"]},
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                    },
                    "location": {"type": "string"},
                    "mechanism": {"type": "string"},
                    "regression": {"type": "string"},
                    "repair": {"type": "string"},
                },
                "required": ["severity", "location", "mechanism", "regression", "repair"],
            },
        },
    },
    "required": ["verdict", "summary", "findings"],
}


def _emit_error(message: str, kind: str) -> None:
    print(
        json.dumps(
            {"error": message, "type": kind},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ),
        file=sys.stderr,
    )


def main() -> int:
    if len(sys.argv) != 5:
        _emit_error(
            "usage: codex_review_gate.py WORKTREE PROMPT RESULT MODEL",
            "UsageError",
        )
        return 2
    worktree, prompt_path, result_path, model = sys.argv[1:]
    prompt = Path(prompt_path)
    result = Path(result_path)
    result.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=result.parent,
        prefix="codex-review-schema-",
        suffix=".json",
        delete=False,
    ) as schema_file:
        json.dump(SCHEMA, schema_file, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        schema_path = Path(schema_file.name)

    try:
        with prompt.open("r", encoding="utf-8") as prompt_stream:
            completed = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--sandbox",
                    "workspace-write",
                    "--ephemeral",
                    "--model",
                    model,
                    "--output-schema",
                    str(schema_path),
                    "--output-last-message",
                    str(result),
                    "--cd",
                    worktree,
                    "-",
                ],
                stdin=prompt_stream,
                check=False,
            )
        if completed.returncode != 0:
            _emit_error(f"codex exited {completed.returncode}", "CodexProcessError")
            return completed.returncode
        try:
            verdict = json.loads(result.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _emit_error(str(exc), type(exc).__name__)
            return 4
        print(json.dumps(verdict, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
        return 0 if verdict.get("verdict") == "PASS" else 3
    finally:
        schema_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
