#!/usr/bin/env python3
"""jarvis_telegram.py — the librarian on Telegram (design cribbed from the orchestrator's
battle-tested operator_chat: long-poll, sender-lock, durable offset, at-least-once).

Each authorised message is persisted before provider invocation. Claude or Codex then reads the
memory and returns a bounded JSON proposal; deterministic code projects, validates and commits
the proposal before Telegram acknowledges completion. Providers never receive write authority.
Anyone else's messages are dropped unread (sender lock).

Config (secrets stay OUT of this folder, per the no-secrets law):
    ~/.jarvis/config.json    {"token": "<bot token from @BotFather>", "chat_id": <your id>}
    ~/.jarvis/offset.json    (managed automatically; durable across restarts)

Run:   python3 scripts/jarvis_telegram.py          (foreground)
       nohup bash scripts/run_jarvis.sh > ~/.jarvis/jarvis.log 2>&1 &   (kept alive)
Stop:  touch ~/.jarvis/STOP  (honoured within one poll cycle)

Honest notes: replies take 15–180 s because this is a real model call. The message and processing
receipt remain local and retryable if providers fail. Treat the bot token like a key to your notes.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

HOME = Path.home()
CONF = HOME / ".jarvis" / "config.json"
OFFSET = HOME / ".jarvis" / "offset.json"
STOP = HOME / ".jarvis" / "STOP"
GIGA = Path(__file__).resolve().parent.parent      # the giga-user folder
if str(GIGA) not in sys.path:
    sys.path.insert(0, str(GIGA))

from twin_core.execution_policy import REQUEST_SCHEMA, decide_route  # noqa: E402
from twin_core.provider_adapters import run_proposal  # noqa: E402
from twin_core.store import TwinStore  # noqa: E402
from twin_core.telegram_pipeline import ProcessingOutcome, process_event  # noqa: E402

LONG_POLL_S = 50
CLAUDE_TIMEOUT_S = 180
RETRY_S = 15 * 60
MODEL = "sonnet"                                    # filing doesn't need a frontier model
ROUTE_CALLER = "scripts.jarvis_telegram:_process_update"
DAILY = GIGA / "scripts" / "daily_personal_knowledge.py"
DAILY_STATE = HOME / ".jarvis" / "daily_knowledge_state.json"
DAILY_LOG = HOME / ".jarvis" / "daily_personal_knowledge.bot-launch.log"
VIETNAM = ZoneInfo("Asia/Ho_Chi_Minh")
_daily_process: subprocess.Popen | None = None
_daily_attempt_date: str | None = None

def _api(token: str, method: str, **params):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(url, data=data, timeout=LONG_POLL_S + 15) as r:
        return json.loads(r.read())


def _worker(instructions: str) -> tuple[str, Mapping[str, Any]] | None:
    return run_proposal(instructions, cwd=GIGA, timeout=CLAUDE_TIMEOUT_S, model=MODEL)


def _shadow_route(event_id: str, instructions: str) -> Mapping[str, Any]:
    """Observe the deterministic route without granting authority or changing execution."""
    request = {
        "schema_version": REQUEST_SCHEMA,
        "registry_version": 1,
        "capability_id": "telegram-memory-proposal",
        "operation_id": "telegram.memory.proposal",
        "caller_id": ROUTE_CALLER,
        "idempotency_key": event_id,
        "input_sha256": hashlib.sha256(instructions.encode("utf-8")).hexdigest(),
        "requested_authority": "A0",
        "target": "memory-proposal",
        "max_cost_usd": 1.0,
        "max_tokens": 4096,
        "timeout_seconds": CLAUDE_TIMEOUT_S,
        "reversibility": "not-applicable-proposal-only",
        "expected_receipt_type": "telegram.memory.commit",
    }
    return decide_route(GIGA, request)


def _save_offset(path: Path, offset: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".offset.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"offset": offset}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _capture_update(store: TwinStore, update: Mapping[str, Any]) -> tuple[str, bool, str]:
    message = update.get("message") or {}
    text = str(message.get("text") or "").strip()
    update_id = int(update["update_id"])
    message_id = message.get("message_id")
    observed = datetime.fromtimestamp(
        int(message.get("date") or datetime.now(timezone.utc).timestamp()), timezone.utc
    ).isoformat()
    event_id, created = store.record_event(
        idempotency_key=f"telegram:update:{update_id}",
        kind="telegram.message.received",
        observed_at=observed,
        source=f"telegram:message:{message_id}",
        actor="operator",
        trust_class="operator_confirmed",
        sensitivity="sensitive",
        payload={"update_id": update_id, "message_id": message_id, "text": text},
    )
    if created:
        store.record_receipt(
            event_id=event_id,
            operation="telegram.capture",
            status="committed",
            details={"update_id": update_id, "message_id": message_id},
        )
    return event_id, created, text


def _process_update(store: TwinStore, update: Mapping[str, Any]) -> ProcessingOutcome:
    event_id, _, text = _capture_update(store, update)
    return process_event(
        store=store,
        memory_root=GIGA / "memory",
        event_id=event_id,
        text=text,
        worker=_worker,
        route_observer=lambda instructions: _shadow_route(event_id, instructions),
    )


def _maybe_start_daily() -> None:
    """Use the already-authorised Telegram daemon as the provider-independent clock.

    This avoids Claude's quota-bound scheduler and macOS launchd's TCC denial for
    ~/Documents. The daily worker itself still uses Claude -> GPT fallback.
    """
    global _daily_process, _daily_attempt_date
    now = datetime.now(VIETNAM)
    today = str(now.date())
    if now.hour < 6 or _daily_attempt_date == today:
        return
    if _daily_process is not None and _daily_process.poll() is None:
        return
    try:
        state = json.loads(DAILY_STATE.read_text()) if DAILY_STATE.exists() else {}
    except (OSError, json.JSONDecodeError):
        state = {}
    if state.get("last_success_vietnam") == today:
        _daily_attempt_date = today
        return
    DAILY_LOG.parent.mkdir(exist_ok=True)
    with DAILY_LOG.open("a") as output:
        _daily_process = subprocess.Popen(
            ["python3", str(DAILY)], cwd=str(GIGA), stdout=output, stderr=output,
            start_new_session=True,
        )
    _daily_attempt_date = today
    print(f"[jarvis] launched daily personal-knowledge run pid={_daily_process.pid}")


def main() -> int:
    conf = json.loads(CONF.read_text())
    token, chat_id = conf["token"], int(conf["chat_id"])
    OFFSET.parent.mkdir(exist_ok=True, mode=0o700)
    os.chmod(OFFSET.parent, 0o700)
    store = TwinStore()
    offset = json.loads(OFFSET.read_text()).get("offset", 0) if OFFSET.exists() else 0
    if offset == 0:
        # first contact: drain history WITHOUT processing (no replay flood — the
        # orchestrator's operator_chat lesson, inherited verbatim)
        upd = _api(token, "getUpdates", timeout=0)
        if upd.get("result"):
            offset = upd["result"][-1]["update_id"] + 1
            _save_offset(OFFSET, offset)
        print(f"[jarvis] first contact — drained backlog, offset={offset}")
    print("[jarvis] listening")
    while not STOP.exists():
        _maybe_start_daily()
        try:
            upd = _api(token, "getUpdates", timeout=LONG_POLL_S, offset=offset)
        except Exception as exc:
            print(f"[jarvis] poll error ({type(exc).__name__}) — retrying in 30s")
            time.sleep(30)
            continue
        for u in upd.get("result", []):
            next_offset = u["update_id"] + 1
            msg = u.get("message") or {}
            if (msg.get("chat") or {}).get("id") != chat_id:
                offset = next_offset
                _save_offset(OFFSET, offset)
                continue                            # sender lock: everyone else unread
            text = (msg.get("text") or "").strip()
            if not text:
                offset = next_offset
                _save_offset(OFFSET, offset)
                continue
            print(f"[jarvis] message: {text[:60]!r}")
            try:
                outcome = _process_update(store, u)
            except Exception as exc:
                print(f"[jarvis] capture/process crash: {type(exc).__name__}: {exc}")
                offset = int(u["update_id"])
                time.sleep(RETRY_S)
                break
            reply = outcome.reply
            sent = False
            try:
                _api(token, "sendMessage", chat_id=chat_id, text=reply,
                     reply_to_message_id=msg.get("message_id", ""))
                sent = True
            except Exception as exc:
                print(f"[jarvis] send failed: {exc}")
            if outcome.success and sent:
                offset = next_offset
                _save_offset(OFFSET, offset)
            else:
                # Keep this update addressable. A committed receipt prevents repeat model work;
                # a failed attempt remains retryable after a bounded backoff.
                offset = int(u["update_id"])
                print(f"[jarvis] event retained for retry: {outcome.error or 'reply not sent'}")
                time.sleep(RETRY_S)
                break
    print("[jarvis] STOP present — going quiet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
