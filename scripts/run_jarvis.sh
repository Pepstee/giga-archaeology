#!/usr/bin/env bash
# run_jarvis.sh — keep the Telegram librarian alive (the run_forever pattern, personal size).
#   start:  nohup bash scripts/run_jarvis.sh > ~/.jarvis/jarvis.log 2>&1 &
#   stop:   touch ~/.jarvis/STOP
#   resume: rm ~/.jarvis/STOP && start again
cd "$(dirname "$0")/.." || exit 1
mkdir -p ~/.jarvis
# Own stable descriptors. Re-running an outer `nohup ... > jarvis.log` must not truncate or
# invalidate the live supervisor's output; append internally and never inherit Terminal stdin.
exec </dev/null >> ~/.jarvis/jarvis.log 2>&1
LOCK=~/.jarvis/run.lock
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "[jarvis-supervisor] already running (pid $(cat "$LOCK")) — exiting."
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT
while [ ! -f ~/.jarvis/STOP ]; do
  echo "[jarvis-supervisor] $(date '+%F %T') launching librarian"
  python3 scripts/jarvis_telegram.py
  [ -f ~/.jarvis/STOP ] && break
  echo "[jarvis-supervisor] $(date '+%F %T') exited — relaunch in 10s (touch ~/.jarvis/STOP to stop)"
  sleep 10
done
echo "[jarvis-supervisor] STOP present — staying down."
