#!/bin/bash
# train_casual_v0.sh — arm now, train at 04:00 local (Vietnam time on this Mac).
# Arm with:  cd ~/Documents/giga-user && nohup bash scripts/train_casual_v0.sh > /dev/null 2>&1 & disown
# Everything logs to ~/.jarvis/train_casual_v0.log ; Telegram ping on finish or failure.
set -u
export HF_HUB_DISABLE_XET=1     # classic HTTP downloads — the xet backend dies on flaky networks
GIGA="$HOME/Documents/giga-user"
LOG="$HOME/.jarvis/train_casual_v0.log"
CONF="$HOME/.jarvis/config.json"
TRAIN_DIR="$GIGA/corpus/training"
MODEL="mlx-community/Qwen2.5-3B-Instruct-4bit"
mkdir -p "$HOME/.jarvis" "$TRAIN_DIR/adapters"
exec >> "$LOG" 2>&1

tg() {  # tg "message" — best-effort Telegram ping
  python3 - "$1" <<'PY' || true
import json, sys, urllib.request, urllib.parse, pathlib
conf = json.loads((pathlib.Path.home()/".jarvis/config.json").read_text())
data = urllib.parse.urlencode({"chat_id": conf["chat_id"], "text": sys.argv[1][:3900]}).encode()
urllib.request.urlopen(f"https://api.telegram.org/bot{conf['token']}/sendMessage", data=data, timeout=30)
PY
}

echo "=== $(date) armed ==="
# 1) Do the fragile parts NOW, while the operator is awake and online.
python3 -m pip show mlx-lm >/dev/null 2>&1 || python3 -m pip install mlx-lm --break-system-packages
echo "$(date) prefetching model weights (~2GB, one-time)"
python3 - <<PY
from mlx_lm import load
load("$MODEL")
print("prefetch ok")
PY
if [ $? -ne 0 ]; then tg "Training armed FAILED at prefetch stage - check ~/.jarvis/train_casual_v0.log before 4am."; exit 1; fi
tg "Casual-v0 training armed: model prefetched, will start at 04:00. Keep the Mac plugged in."

# 2) Sleep until next 04:00 local, holding the Mac awake.
WAIT=$(python3 -c "
import datetime as d, zoneinfo
tz = zoneinfo.ZoneInfo('Asia/Ho_Chi_Minh')   # 04:00 VIETNAM time, whatever the Mac's clock says
now = d.datetime.now(tz)
t = now.replace(hour=4, minute=0, second=0, microsecond=0)
if t <= now: t += d.timedelta(days=1)
print(int((t-now).total_seconds()))")
echo "$(date) sleeping ${WAIT}s until 04:00 Asia/Ho_Chi_Minh (caffeinate holds wake)"
caffeinate -is -t "$WAIT"

# 3) Train.
echo "=== $(date) training starts ==="
cd "$TRAIN_DIR"
caffeinate -is python3 -m mlx_lm.lora \
  --model "$MODEL" \
  --train --data mlx --iters 800 --batch-size 4 --num-layers 16 \
  --adapter-path adapters/casual-v0
RC=$?
if [ $RC -ne 0 ]; then
  tg "Casual-v0 training FAILED (exit $RC) - tail of log: $(tail -c 500 "$LOG")"
  exit $RC
fi
echo "=== $(date) training done, sampling ==="

# 4) Three blind samples for the morning verdict.
SAMPLES=""
for P in "Wassup, how was the gym?" "Ты где сейчас? Когда созвон?" "What are we doing tomorrow?"; do
  OUT=$(caffeinate -is python3 -m mlx_lm.generate --model "$MODEL" \
        --adapter-path adapters/casual-v0 --max-tokens 60 --prompt "$P" 2>/dev/null | tail -5)
  SAMPLES="$SAMPLES>> $P
$OUT

"
done
echo "$SAMPLES"
tg "Casual-v0 TRAINED. Morning eval samples:

$SAMPLES
Full log: ~/.jarvis/train_casual_v0.log — reply-test protocol in corpus/training/TRAINING.md"
echo "=== $(date) all done ==="
