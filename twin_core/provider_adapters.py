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
    return codex_structured(
        instructions,
        schema=proposal_output_schema(),
        timeout=timeout,
    )


def codex_structured(
    instructions: str,
    *,
    schema: Mapping[str, Any],
    timeout: int = 180,
    model: str | None = None,
    reasoning_effort: str = "low",
) -> Mapping[str, Any] | None:
    """Run an authenticated, ephemeral Codex worker with closed JSON output.

    The complete bounded input is embedded in ``instructions``. The worker runs from an empty
    read-only directory, loads neither repository rules nor user config, and can publish only the
    final response validated by ``schema``. This is the canonical local subscription-backed
    structured-output seam for provider-free automation such as Graphify semantic extraction.
    """
    result = _codex_structured_result(
        instructions,
        schema=schema,
        timeout=timeout,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    return result[0] if result is not None else None


def codex_structured_with_usage(
    instructions: str,
    *,
    schema: Mapping[str, Any],
    timeout: int = 180,
    model: str | None = None,
    reasoning_effort: str = "low",
) -> tuple[Mapping[str, Any], Mapping[str, int]] | None:
    """Return closed structured output together with measured Codex token usage."""
    result = _codex_structured_result(
        instructions,
        schema=schema,
        timeout=timeout,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    if result is None or result[1] is None:
        return None
    return result[0], result[1]


def _codex_structured_result(
    instructions: str,
    *,
    schema: Mapping[str, Any],
    timeout: int,
    model: str | None,
    reasoning_effort: str,
) -> tuple[Mapping[str, Any], Mapping[str, int] | None] | None:
    if not isinstance(instructions, str) or not instructions:
        raise ValueError("Codex structured instructions must be a non-empty string")
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        raise ValueError("Codex structured output schema must describe an object")
    if reasoning_effort not in {"low", "medium", "high"}:
        raise ValueError("unsupported Codex reasoning effort")
    # The bounded context is in the prompt. Run in an empty disposable workspace so project
    # instructions and data are neither discovered nor addressable through relative paths.
    with tempfile.TemporaryDirectory(prefix="giga-provider-") as folder:
        provider_root = Path(folder)
        output_path = provider_root / "proposal.json"
        schema_path = provider_root / "schema.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        command = [
            "codex", "exec", "--ephemeral", "--sandbox", "read-only",
            "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
            "--json", "--output-schema", str(schema_path), "-C", str(provider_root),
            "-c", f'model_reasoning_effort="{reasoning_effort}"',
        ]
        if model is not None:
            command.extend(["--model", model])
        command.extend(["-o", str(output_path), "-"])
        try:
            proc = subprocess.run(
                command,
                cwd=provider_root,
                input=instructions,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        raw = output_path.read_text(encoding="utf-8", errors="replace").strip() if output_path.exists() else ""
        if proc.returncode != 0 or not raw:
            return None
        usage = None
        for line in (proc.stdout or "").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "turn.completed" or not isinstance(event.get("usage"), dict):
                continue
            candidate = event["usage"]
            required = {"input_tokens", "cached_input_tokens", "output_tokens"}
            if required.issubset(candidate) and all(
                isinstance(candidate[key], int) and not isinstance(candidate[key], bool)
                and candidate[key] >= 0
                for key in required
            ):
                usage = {key: candidate[key] for key in sorted(required)}
        return extract_json(raw), usage


def run_proposal(
    instructions: str, *, cwd: Path, timeout: int = 180, model: str = "sonnet"
) -> tuple[str, Mapping[str, Any]] | None:
    proposal = claude_proposal(instructions, cwd=cwd, timeout=timeout, model=model)
    if proposal is not None:
        return "Claude", proposal
    proposal = codex_proposal(instructions, timeout=timeout)
    return ("GPT", proposal) if proposal is not None else None
