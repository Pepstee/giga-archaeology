#!/usr/bin/env bash
# Persistent daily supervisor. Launched from an already-authorised user app so macOS TCC
# permits access to ~/Documents; provider scheduling is deliberately not involved.
set -u
cd "$(dirname "$0")/.." || exit 1
mkdir -p "$HOME/.jarvis"
LOCK="$HOME/.jarvis/daily_personal_knowledge.lock"
STOP="$HOME/.jarvis/DAILY_STOP"
LOG="$HOME/.jarvis/daily_personal_knowledge.supervisor.log"

if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "[daily-supervisor] already running (pid $(cat "$LOCK"))"
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

while [ ! -f "$STOP" ]; do
  WAIT_SECONDS=$(python3 - <<'PY'
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
tz = ZoneInfo("Asia/Ho_Chi_Minh")
now = datetime.now(tz)
target = now.replace(hour=6, minute=6, second=0, microsecond=0)
if target <= now:
    target += timedelta(days=1)
print(max(1, int((target - now).total_seconds())))
PY
  )
  echo "[daily-supervisor] $(TZ=Asia/Ho_Chi_Minh date '+%F %T ICT') next run in ${WAIT_SECONDS}s" >> "$LOG"
  # Chunked sleep notices STOP within a minute and survives ordinary long waits cleanly.
  while [ "$WAIT_SECONDS" -gt 0 ] && [ ! -f "$STOP" ]; do
    CHUNK=60
    [ "$WAIT_SECONDS" -lt 60 ] && CHUNK="$WAIT_SECONDS"
    sleep "$CHUNK"
    WAIT_SECONDS=$((WAIT_SECONDS - CHUNK))
  done
  [ -f "$STOP" ] && break
  python3 scripts/daily_personal_knowledge.py --force >> "$LOG" 2>&1
done

echo "[daily-supervisor] STOP present — staying down" >> "$LOG"
