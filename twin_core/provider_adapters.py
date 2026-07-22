"""No-tool structured-output provider adapters for memory proposals."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .memory_proposals import proposal_output_schema


def extract_json(raw: str) -> Mapping[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("provider returned no JSON object")
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("provider proposal must be a JSON object")
    return value


def _run(cmd: list[str], *, cwd: Path, timeout: int) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    out = (proc.stdout or "").strip()
    return out if proc.returncode == 0 and out else None


def claude_proposal(
    instructions: str, *, cwd: Path, timeout: int = 180, model: str = "sonnet"
) -> Mapping[str, Any] | None:
    raw = _run(
        ["claude", "-p", "--model", model, "--permission-mode", "plan", "--tools=",
         "--safe-mode", "--disable-slash-commands", "--no-session-persistence",
         "--json-schema", json.dumps(proposal_output_schema(), separators=(",", ":")),
         "--", instructions],
        cwd=cwd,
        timeout=timeout,
    )
    return extract_json(raw) if raw is not None else None


def codex_proposal(instructions: str, *, timeout: int = 180) -> Mapping[str, Any] | None:
    # The bounded context is in the prompt. Run in an empty disposable workspace so project
    # instructions and data are neither discovered nor addressable through relative paths.
    with tempfile.TemporaryDirectory(prefix="giga-provider-") as folder:
        provider_root = Path(folder)
        output_path = provider_root / "proposal.json"
        schema_path = provider_root / "schema.json"
        schema_path.write_text(json.dumps(proposal_output_schema()), encoding="utf-8")
        try:
            proc = subprocess.run(
                ["codex", "exec", "--ephemeral", "--sandbox", "read-only",
                 "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
                 "--output-schema", str(schema_path), "-C", str(provider_root),
                 "-o", str(output_path), "-"],
                cwd=provider_root,
                input=instructions,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        raw = output_path.read_text(encoding="utf-8", errors="replace").strip() if output_path.exists() else ""
        return extract_json(raw) if proc.returncode == 0 and raw else None


def run_proposal(
    instructions: str, *, cwd: Path, timeout: int = 180, model: str = "sonnet"
) -> tuple[str, Mapping[str, Any]] | None:
    proposal = claude_proposal(instructions, cwd=cwd, timeout=timeout, model=model)
    if proposal is not None:
        return "Claude", proposal
    proposal = codex_proposal(instructions, timeout=timeout)
    return ("GPT", proposal) if proposal is not None else None
