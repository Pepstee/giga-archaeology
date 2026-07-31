from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .goal_parser import parse_goal_text, parse_goal_with_openai
from .pipeline import load_goal, make_digest, run_pipeline, save_goal


def _telegram_call(method: str, payload: dict) -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def send_digest(report: dict, chat_id: str | None = None) -> None:
    target = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not target:
        raise RuntimeError("TELEGRAM_CHAT_ID is not set.")
    _telegram_call(
        "sendMessage",
        {
            "chat_id": target,
            "text": make_digest(report),
            "disable_web_page_preview": "true",
        },
    )


def run_control_loop(
    *,
    input_path: str | Path,
    goal_path: str | Path,
    output_path: str | Path,
    feature_points_path: str | Path | None = None,
    cadastral_values_path: str | Path | None = None,
) -> None:
    """Long-polling bot: every authorized text message is a goal correction and rerun."""
    allowed_chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not allowed_chat:
        raise RuntimeError("TELEGRAM_CHAT_ID must whitelist the single controlling chat.")
    offset = 0
    while True:
        try:
            response = _telegram_call(
                "getUpdates",
                {"offset": offset, "timeout": 30, "allowed_updates": json.dumps(["message"])},
            )
            for update in response.get("result", []):
                offset = max(offset, int(update["update_id"]) + 1)
                message = update.get("message", {})
                chat_id = str(message.get("chat", {}).get("id", ""))
                text = str(message.get("text") or "").strip()
                if chat_id != str(allowed_chat) or not text:
                    continue
                base = load_goal(goal_path)
                if os.environ.get("OPENAI_API_KEY"):
                    goal = parse_goal_with_openai(text, base)
                else:
                    goal = parse_goal_text(text, base)
                save_goal(goal, goal_path)
                report = run_pipeline(
                    input_path,
                    goal_path,
                    output_path,
                    feature_points_path=feature_points_path,
                    cadastral_values_path=cadastral_values_path,
                    use_openai=bool(os.environ.get("OPENAI_API_KEY")),
                )
                send_digest(report, chat_id)
        except KeyboardInterrupt:
            return
        except Exception as exc:
            _telegram_call(
                "sendMessage",
                {"chat_id": allowed_chat, "text": f"Монитор завершил цикл с ошибкой: {exc}"},
            )
            time.sleep(5)

