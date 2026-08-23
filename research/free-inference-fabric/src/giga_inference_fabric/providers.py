from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import Completion, CostTier, ModelSpec


class ProviderError(RuntimeError):
    pass


class ModelAdapter(Protocol):
    name: str

    def complete(
        self, model: ModelSpec, *, system: str, prompt: str,
        max_output_tokens: int = 4096, timeout: int = 180,
    ) -> Completion: ...


def _assistant_text(message: object) -> tuple[str, str]:
    """Extract a candidate from common OpenAI-compatible response variants.

    Final content remains authoritative when present. Some local reasoning models exhaust the
    generation budget before emitting final content and expose only ``reasoning`` or
    ``reasoning_content``. That output is retained as an explicitly labelled fallback candidate;
    the external objective evaluator still decides whether it is useful.
    """
    if not isinstance(message, dict):
        raise ProviderError("provider returned a malformed assistant message")
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content, "content"
    if isinstance(content, list):
        fragments = [
            item.get("text") for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ]
        joined = "".join(fragments)
        if joined.strip():
            return joined, "content_fragments"
    for field in ("reasoning", "reasoning_content"):
        value = message.get(field)
        if isinstance(value, str) and value.strip():
            return value, f"{field}_fallback"
    raise ProviderError("provider returned empty completion and no reasoning fallback")


def _post_json(url: str, payload: dict, headers: dict[str, str], timeout: int) -> tuple[dict, int]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), int((time.monotonic() - started) * 1000)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:1000]
        raise ProviderError(f"HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"provider transport failure: {exc}") from exc


@dataclass
class OpenAICompatibleAdapter:
    name: str
    base_url: str
    api_key_env: str | None = None
    extra_headers: dict[str, str] | None = None

    def complete(
        self, model: ModelSpec, *, system: str, prompt: str,
        max_output_tokens: int = 4096, timeout: int = 180,
    ) -> Completion:
        headers = dict(self.extra_headers or {})
        if self.api_key_env:
            api_key = os.environ.get(self.api_key_env)
            if not api_key:
                raise ProviderError(f"missing credential environment variable: {self.api_key_env}")
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model.model_id,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_output_tokens,
        }
        if model.supports_structured_output:
            payload["response_format"] = {"type": "json_object"}
        raw, latency_ms = _post_json(f"{self.base_url.rstrip('/')}/chat/completions", payload, headers, timeout)
        choices = raw.get("choices") or []
        if not choices:
            raise ProviderError("provider returned no choices")
        text, text_source = _assistant_text(choices[0].get("message"))
        usage = raw.get("usage") or {}
        return Completion(
            text=text,
            model_id=str(raw.get("model") or model.model_id),
            adapter=self.name,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            latency_ms=latency_ms,
            cost_usd=float(raw.get("usage", {}).get("cost") or 0.0),
            raw={
                "id": raw.get("id"), "finish_reason": choices[0].get("finish_reason"),
                "text_source": text_source,
            },
        )


def openrouter_adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        extra_headers={"HTTP-Referer": "https://github.com/ArtiomTr/giga-user", "X-Title": "GIGA Inference Fabric"},
    )


def local_adapter(base_url: str = "http://127.0.0.1:11434/v1") -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(name="local", base_url=base_url)


@dataclass
class OpenCodeOpenRouterAdapter:
    """Use OpenCode's existing OpenRouter login without reading or copying its credential."""

    name: str = "opencode-openrouter"
    binary: str | None = None
    allow_paid: bool = False
    auth_file: Path | None = None

    def complete(
        self, model: ModelSpec, *, system: str, prompt: str,
        max_output_tokens: int = 4096, timeout: int = 180,
    ) -> Completion:
        if model.cost_tier == CostTier.PAID and not self.allow_paid:
            raise ProviderError("OpenCode paid transport requires explicit adapter admission")
        if model.cost_tier not in {CostTier.FREE, CostTier.PAID}:
            raise ProviderError("OpenCode transport accepts only OpenRouter free or paid models")
        binary = self.binary or os.environ.get("OPENCODE_BIN") or shutil.which("opencode")
        if not binary:
            raise ProviderError("OpenCode binary is unavailable")
        model_id = model.model_id if model.model_id.startswith("openrouter/") else f"openrouter/{model.model_id}"
        message = (
            f"{system}\n\nOUTPUT CEILING: do not exceed {max_output_tokens} tokens.\n\n{prompt}"
        )
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="giga-opencode-") as empty_dir:
            # OpenCode canonicalises macOS /var to /private/var. Use that same identity for the
            # project directory, explicit file-plugin URI and receipts or its compatibility
            # loader can treat the local plugin as outside the active project.
            root = Path(empty_dir).resolve()
            home = root / "home"
            home.mkdir()
            auth_source = self.auth_file or (Path.home() / ".local/share/opencode/auth.json")
            if not auth_source.is_file():
                raise ProviderError("OpenCode authentication file is unavailable")
            isolated_data = root / "xdg-data" / "opencode"
            isolated_data.mkdir(parents=True)
            (isolated_data / "auth.json").symlink_to(auth_source.resolve())
            plugin_dir = root / ".opencode" / "plugins"
            plugin_dir.mkdir(parents=True)
            plugin_path = plugin_dir / "giga-output-budget.js"
            init_receipt_path = root / "plugin-init-receipt"
            hook_receipt_path = root / "output-cap-receipt.json"
            (root / "opencode.json").write_text(
                json.dumps({
                    "$schema": "https://opencode.ai/config.json",
                    "plugin": [plugin_path.as_uri()],
                    "permission": "deny",
                    "share": "disabled",
                    "autoupdate": False,
                    "snapshot": False,
                }),
                encoding="utf-8",
            )
            plugin_path.write_text(
                "import { writeFileSync } from 'node:fs';\n"
                "let invocationCount = 0;\n"
                "export const GigaOutputBudget = async () => {\n"
                f"  writeFileSync({json.dumps(str(init_receipt_path))}, 'loaded', {{ mode: 0o600 }});\n"
                "  return ({\n"
                "  'chat.params': async (input, output) => {\n"
                "    invocationCount += 1;\n"
                "    if (invocationCount !== 1) throw new Error('multiple LLM invocations denied');\n"
                f"    if (input.model.providerID !== 'openrouter' || input.model.id !== {json.dumps(model.model_id)}) {{\n"
                "      throw new Error('unadmitted model invocation denied');\n"
                "    }\n"
                f"    output.maxOutputTokens = {int(max_output_tokens)};\n"
                f"    writeFileSync({json.dumps(str(hook_receipt_path))}, JSON.stringify({{\n"
                "      invocationCount, providerID: input.model.providerID, modelID: input.model.id,\n"
                "      maxOutputTokens: output.maxOutputTokens,\n"
                "    }}), { mode: 0o600 });\n"
                "  },\n"
                "  });\n"
                "};\n",
                encoding="utf-8",
            )
            environment = {
                key: value for key, value in os.environ.items()
                if key in {"PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR"}
            }
            environment["HOME"] = str(home)
            environment["XDG_CONFIG_HOME"] = str(root / "xdg-config")
            environment["XDG_DATA_HOME"] = str(root / "xdg-data")
            environment["XDG_STATE_HOME"] = str(root / "xdg-state")
            environment["XDG_CACHE_HOME"] = str(root / "xdg-cache")
            environment["OPENCODE_CONFIG_DIR"] = str(root / ".opencode")
            environment["NO_COLOR"] = "1"
            preflight = subprocess.run(
                [binary, "debug", "config"], cwd=str(root), text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=min(timeout, 60), check=False, env=environment,
            )
            try:
                resolved_config = json.loads(preflight.stdout)
            except json.JSONDecodeError as exc:
                raise ProviderError("OpenCode config preflight returned invalid JSON") from exc
            if (
                preflight.returncode != 0
                or plugin_path.as_uri() not in resolved_config.get("plugin", [])
                or init_receipt_path.read_text(encoding="utf-8") != "loaded"
            ):
                raise ProviderError("OpenCode config/plugin preflight failed closed")
            init_receipt_path.unlink()
            try:
                result = subprocess.run(
                    [
                        binary, "run", "--print-logs", "--log-level", "WARN",
                        "--format", "json", "--dir", str(root),
                        "--title", "giga-inference-fabric", "--model", model_id, message,
                    ],
                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=timeout, check=False, env=environment,
                )
            except subprocess.TimeoutExpired as exc:
                raise ProviderError(f"OpenCode transport timed out after {timeout}s") from exc
            if not init_receipt_path.is_file():
                raise ProviderError(
                    "OpenCode run process did not load the admitted plugin: " + result.stdout[-2000:]
                )
            try:
                hook_receipt = json.loads(hook_receipt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ProviderError(
                    "OpenCode output-cap hook did not produce a valid receipt: " + result.stdout[-2000:]
                ) from exc
            expected_receipt = {
                "invocationCount": 1,
                "providerID": "openrouter",
                "modelID": model.model_id,
                "maxOutputTokens": max_output_tokens,
            }
            if hook_receipt != expected_receipt:
                raise ProviderError("OpenCode output-cap hook receipt failed closed")
        text_parts = []
        prompt_tokens = completion_tokens = 0
        cost_usd = 0.0
        errors = []
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "text":
                value = (event.get("part") or {}).get("text")
                if isinstance(value, str):
                    text_parts.append(value)
            elif event.get("type") == "error":
                errors.append(json.dumps(event.get("error"), ensure_ascii=False, sort_keys=True)[:2000])
            elif event.get("type") == "step_finish":
                part = event.get("part") or {}
                tokens = part.get("tokens") or {}
                prompt_tokens += int(tokens.get("input") or 0)
                completion_tokens += int(tokens.get("output") or 0) + int(tokens.get("reasoning") or 0)
                cost_usd += float(part.get("cost") or 0.0)
        if result.returncode != 0 or errors:
            detail = "; ".join(errors) or result.stdout[-2000:] or f"exit {result.returncode}"
            raise ProviderError(f"OpenCode provider failure: {detail}")
        completion_text = "".join(text_parts).strip()
        if not completion_text:
            raise ProviderError("OpenCode provider returned no text event")
        if model.cost_tier == CostTier.FREE and cost_usd > 0:
            raise ProviderError("free-tier OpenCode call reported non-zero cost")
        return Completion(
            text=completion_text, model_id=model.model_id, adapter=self.name,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            latency_ms=int((time.monotonic() - started) * 1000), cost_usd=cost_usd,
            raw={
                "provider_output_cap": max_output_tokens,
                "permission_profile": "deny",
                "llm_invocations": hook_receipt["invocationCount"],
                "auth_exposure": "isolated-symlink-only",
            },
        )


def discover_local_models(base_url: str = "http://127.0.0.1:11434/v1", timeout: int = 10) -> list[ModelSpec]:
    request = urllib.request.Request(f"{base_url.rstrip('/')}/models", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"local model discovery failed: {exc}") from exc
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ProviderError("local model discovery returned no OpenAI-compatible data array")
    models = []
    for item in rows:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            continue
        models.append(ModelSpec(
            model_id=item["id"], adapter="local", cost_tier=CostTier.LOCAL,
            capabilities=frozenset({"text"}), metadata={"owned_by": item.get("owned_by")},
        ))
    return sorted(models, key=lambda model: model.model_id)


def discover_openrouter_models(timeout: int = 30) -> list[ModelSpec]:
    request = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"OpenRouter discovery failed: {exc}") from exc
    models: list[ModelSpec] = []
    for item in payload.get("data", []):
        pricing = item.get("pricing") or {}
        try:
            free = float(pricing.get("prompt", 1)) == 0.0 and float(pricing.get("completion", 1)) == 0.0
        except (TypeError, ValueError):
            free = False
        model_id = str(item.get("id") or "")
        if not model_id:
            continue
        supported = set(item.get("supported_parameters") or [])
        architecture = item.get("architecture") or {}
        modalities = set(architecture.get("input_modalities") or ["text"])
        models.append(ModelSpec(
            model_id=model_id,
            adapter="openrouter",
            cost_tier=CostTier.FREE if free else CostTier.PAID,
            context_length=int(item.get("context_length") or 0),
            capabilities=frozenset(modalities | {"text"}),
            supports_tools="tools" in supported or "tool_choice" in supported,
            supports_structured_output="response_format" in supported or "structured_outputs" in supported,
            # Endpoint-level ZDR must be checked separately before sensitive use.
            zero_data_retention=False,
            preview=any(word in model_id.lower() for word in ("preview", "alpha", "beta", "experimental")),
            metadata={"name": item.get("name"), "created": item.get("created"), "pricing": pricing},
        ))
    return sorted(models, key=lambda model: model.model_id)
