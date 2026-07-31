#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "usage: $0 RUN_DIR SNAPSHOT EXPECTED_COMMIT PROMPT_FILE ARM_LABEL" >&2
  exit 64
fi

run_dir=$1
snapshot=$2
expected_commit=$3
prompt_file=$4
arm_label=$5

mkdir -p "$run_dir"
chmod 700 "$run_dir"

exec >"$run_dir/wrapper.stdout.log" 2>"$run_dir/wrapper.stderr.log"

experiment_root=$(dirname "$(dirname "$run_dir")")
auth_lock=/home/gutua/software-factory/.control/claude-global.lock
exec 9>"$auth_lock"
if ! flock -n 9; then
  echo "another blind-review invocation owns the Claude authentication lock" >&2
  exit 68
fi
if pgrep -x claude >/dev/null; then
  echo "another Claude process is active; refusing to contaminate the blind review" >&2
  exit 69
fi

auth_home=$(mktemp -d "$experiment_root/.reviewer-auth.XXXXXX")
chmod 700 "$auth_home"
mkdir -m 700 "$auth_home/.claude"
install -m 600 \
  /home/gutua/.claude/.credentials.json \
  "$auth_home/.claude/.credentials.json"
cleanup_auth_home() {
  rm -rf -- "$auth_home"
}
trap cleanup_auth_home EXIT

date -u +%Y-%m-%dT%H:%M:%SZ >"$run_dir/started_at"
printf '%s\n' "$arm_label" >"$run_dir/arm"
printf '%s\n' "$expected_commit" >"$run_dir/expected_commit"
sha256sum "$prompt_file" >"$run_dir/prompt.sha256"

actual_commit=$(git -C "$snapshot" rev-parse HEAD)
printf '%s\n' "$actual_commit" >"$run_dir/actual_commit"
git -C "$snapshot" status --porcelain=v1 >"$run_dir/source_status.before"

if [[ "$actual_commit" != "$expected_commit" ]]; then
  echo "commit mismatch: expected $expected_commit, got $actual_commit" >&2
  exit 65
fi
if [[ -s "$run_dir/source_status.before" ]]; then
  echo "source snapshot is not clean" >&2
  exit 66
fi

session_id=$(python3 -c 'import uuid; print(uuid.uuid4())')
printf '%s\n' "$session_id" >"$run_dir/session_id"

set +e
timeout --signal=TERM --kill-after=30s 3300s \
  bwrap \
    --die-with-parent \
    --new-session \
    --ro-bind /usr /usr \
    --symlink usr/bin /bin \
    --ro-bind /lib /lib \
    --ro-bind /lib64 /lib64 \
    --ro-bind /etc /etc \
    --dir /mnt \
    --dir /mnt/wsl \
    --ro-bind /mnt/wsl/resolv.conf /mnt/wsl/resolv.conf \
    --proc /proc \
    --dev /dev \
    --tmpfs /tmp \
    --dir /home \
    --bind "$auth_home" /home/reviewer \
    --ro-bind "$snapshot" /workspace \
    --ro-bind "$prompt_file" /review-prompt.md \
    --chdir /workspace \
    --setenv HOME /home/reviewer \
    --setenv USER reviewer \
    --setenv LOGNAME reviewer \
    --setenv PATH /usr/local/bin:/usr/bin:/bin \
    --setenv PYTHONDONTWRITEBYTECODE 1 \
    /usr/bin/bash -lc \
      '/usr/bin/claude --print \
        --model claude-opus-5 \
        --effort max \
        --safe-mode \
        --no-session-persistence \
        --disable-slash-commands \
        --no-chrome \
        --strict-mcp-config \
        --mcp-config "{\"mcpServers\":{}}" \
        --permission-mode bypassPermissions \
        --tools "Read,Grep,Glob,Bash" \
        --output-format json \
        --session-id '"$session_id"' \
        "$(< /review-prompt.md)"' \
    >"$run_dir/result.raw.json" \
    2>"$run_dir/claude.stderr.log"
exit_code=$?
set -e

printf '%s\n' "$exit_code" >"$run_dir/exit_code"
date -u +%Y-%m-%dT%H:%M:%SZ >"$run_dir/finished_at"
git -C "$snapshot" status --porcelain=v1 >"$run_dir/source_status.after"
sha256sum "$run_dir/result.raw.json" >"$run_dir/result.sha256"

if [[ "$exit_code" -eq 0 ]] && python3 - "$auth_home/.claude/.credentials.json" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
if not isinstance(payload, dict) or not payload:
    raise SystemExit(1)
PY
then
  refreshed_credentials="/home/gutua/.claude/.credentials.json.portfolio.$$"
  install -m 600 \
    "$auth_home/.claude/.credentials.json" \
    "$refreshed_credentials"
  mv -f -- "$refreshed_credentials" /home/gutua/.claude/.credentials.json
  printf '%s\n' "synced-after-success" >"$run_dir/auth_refresh_status"
else
  printf '%s\n' "not-synced" >"$run_dir/auth_refresh_status"
fi

python3 - "$run_dir/result.raw.json" "$run_dir/result.md" "$run_dir/result.metadata.json" <<'PY'
import json
import pathlib
import sys

raw_path = pathlib.Path(sys.argv[1])
report_path = pathlib.Path(sys.argv[2])
metadata_path = pathlib.Path(sys.argv[3])

try:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
except Exception as exc:
    metadata_path.write_text(
        json.dumps({"parse_ok": False, "error": str(exc)}, indent=2),
        encoding="utf-8",
    )
    raise SystemExit(0)

result = payload.get("result")
if isinstance(result, str):
    report_path.write_text(result, encoding="utf-8")

metadata = {
    "parse_ok": True,
    "type": payload.get("type"),
    "subtype": payload.get("subtype"),
    "is_error": payload.get("is_error"),
    "duration_ms": payload.get("duration_ms"),
    "duration_api_ms": payload.get("duration_api_ms"),
    "num_turns": payload.get("num_turns"),
    "session_id": payload.get("session_id"),
    "total_cost_usd": payload.get("total_cost_usd"),
    "usage": payload.get("usage"),
    "model_usage": payload.get("modelUsage"),
}
metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
PY

if [[ -s "$run_dir/source_status.after" ]]; then
  echo "source snapshot changed despite read-only mount" >&2
  exit 67
fi

exit "$exit_code"
