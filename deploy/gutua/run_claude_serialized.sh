#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "usage: $0 CLAUDE_ARGUMENT..." >&2
  exit 64
fi

control_root=/home/gutua/software-factory/.control
lock_file="$control_root/claude-global.lock"
wait_seconds=${CLAUDE_LOCK_TIMEOUT_SECONDS:-7200}

mkdir -p "$control_root"
exec 9>"$lock_file"
if ! flock -w "$wait_seconds" 9; then
  echo "timed out waiting for the host-wide Claude execution lock" >&2
  exit 75
fi

exec /usr/bin/claude "$@"
