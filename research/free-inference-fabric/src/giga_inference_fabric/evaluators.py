from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import Candidate, GateResult


class Evaluator(Protocol):
    def evaluate(self, candidate: Candidate) -> GateResult: ...


@dataclass
class JsonEvaluator:
    required_keys: tuple[str, ...]

    def evaluate(self, candidate: Candidate) -> GateResult:
        try:
            payload = json.loads(candidate.completion.text)
        except json.JSONDecodeError as exc:
            return GateResult(False, 0.0, f"invalid JSON: {exc}")
        missing = [key for key in self.required_keys if key not in payload]
        if missing:
            score = (len(self.required_keys) - len(missing)) / max(len(self.required_keys), 1)
            return GateResult(False, score, "missing keys: " + ", ".join(missing))
        return GateResult(True, 1.0, "valid JSON with all required keys")


@dataclass
class TextContractEvaluator:
    required_patterns: tuple[str, ...]
    forbidden_patterns: tuple[str, ...] = ()

    def evaluate(self, candidate: Candidate) -> GateResult:
        text = candidate.completion.text
        required = [pattern for pattern in self.required_patterns if re.search(pattern, text, re.I | re.M)]
        forbidden = [pattern for pattern in self.forbidden_patterns if re.search(pattern, text, re.I | re.M)]
        score = len(required) / max(len(self.required_patterns), 1)
        passed = len(required) == len(self.required_patterns) and not forbidden
        summary = f"required {len(required)}/{len(self.required_patterns)}; forbidden hits {len(forbidden)}"
        return GateResult(passed, score if not forbidden else max(0.0, score - 0.25), summary)


@dataclass
class CommandEvaluator:
    """Run objective checks against a candidate artifact without trusting model prose.

    The candidate text is written to a temporary file and exposed as
    ``GIGA_CANDIDATE_PATH``. A project-specific materializer/evaluator can read that file,
    apply a patch in a disposable checkout, run tests and exit non-zero on failure.
    """

    commands: tuple[tuple[str, ...], ...]
    cwd: Path
    timeout_seconds: int = 300

    def evaluate(self, candidate: Candidate) -> GateResult:
        checks: list[dict] = []
        passed = 0
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".candidate", delete=False) as handle:
            handle.write(candidate.completion.text)
            candidate_path = handle.name
        try:
            # Objective gates receive only the environment needed to execute local tools.
            # Provider credentials and unrelated process state must not leak into project tests.
            environment = {
                key: os.environ[key]
                for key in ("PATH", "LANG", "LC_ALL", "TMPDIR")
                if key in os.environ
            }
            environment["GIGA_CANDIDATE_PATH"] = candidate_path
            for command in self.commands:
                try:
                    result = subprocess.run(
                        list(command), cwd=self.cwd, env=environment, text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        timeout=self.timeout_seconds, check=False,
                    )
                    ok = result.returncode == 0
                    passed += int(ok)
                    checks.append({
                        "command": list(command), "passed": ok, "exit_code": result.returncode,
                        "output": result.stdout[-4000:],
                    })
                except subprocess.TimeoutExpired as exc:
                    checks.append({"command": list(command), "passed": False, "timeout": True, "output": str(exc)})
            total = len(self.commands)
            all_passed = total > 0 and passed == total
            summary = f"objective commands passed {passed}/{total}"
            return GateResult(all_passed, passed / max(total, 1), summary, tuple(checks))
        finally:
            Path(candidate_path).unlink(missing_ok=True)


@dataclass
class CompositeEvaluator:
    evaluators: tuple[Evaluator, ...]

    def evaluate(self, candidate: Candidate) -> GateResult:
        results = [evaluator.evaluate(candidate) for evaluator in self.evaluators]
        passed = bool(results) and all(result.passed for result in results)
        score = sum(result.score for result in results) / max(len(results), 1)
        return GateResult(
            passed, score, "; ".join(result.summary for result in results),
            tuple(check for result in results for check in result.checks),
        )


def evaluator_from_contract(contract: dict) -> Evaluator:
    """Compile a strict, versioned evaluator contract into external gate objects."""
    allowed = {"schema", "required", "forbidden", "commands", "cwd", "timeout_seconds"}
    unknown = sorted(set(contract) - allowed)
    if unknown:
        raise ValueError("unknown evaluator contract fields: " + ", ".join(unknown))
    if contract.get("schema") != "giga.evaluator-contract.v1":
        raise ValueError("unsupported evaluator contract schema")

    evaluators: list[Evaluator] = []
    required = contract.get("required") or []
    forbidden = contract.get("forbidden") or []
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise ValueError("evaluator required patterns must be a list of strings")
    if not isinstance(forbidden, list) or not all(isinstance(item, str) for item in forbidden):
        raise ValueError("evaluator forbidden patterns must be a list of strings")
    if required or forbidden:
        evaluators.append(TextContractEvaluator(tuple(required), tuple(forbidden)))

    commands = contract.get("commands") or []
    if not isinstance(commands, list) or not all(
        isinstance(command, list) and command and all(isinstance(part, str) and part for part in command)
        for command in commands
    ):
        raise ValueError("evaluator commands must be non-empty argument arrays")
    if commands:
        cwd_value = contract.get("cwd")
        if not isinstance(cwd_value, str) or not cwd_value:
            raise ValueError("command evaluator requires cwd")
        cwd = Path(cwd_value).expanduser().resolve(strict=True)
        if not cwd.is_dir():
            raise ValueError("command evaluator cwd must be a directory")
        timeout = contract.get("timeout_seconds", 300)
        if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
            raise ValueError("command evaluator timeout_seconds must be between 1 and 3600")
        evaluators.append(CommandEvaluator(tuple(tuple(command) for command in commands), cwd, timeout))

    if not evaluators:
        raise ValueError("evaluator contract must contain a text or command gate")
    return evaluators[0] if len(evaluators) == 1 else CompositeEvaluator(tuple(evaluators))
