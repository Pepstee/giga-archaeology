#!/usr/bin/env bash
set -euo pipefail

lane=${1:?lane required}
worktree=${2:?worktree required}
prompt=${3:?prompt required}
control_dir=${4:?control directory required}
expected_head=${5:?expected head required}
time_limit=${6:-10800}

mkdir -p "$control_dir"
chmod 700 "$control_dir"
exec 8>"$control_dir/supervisor.lock"
flock -n 8 || {
  echo "auxiliary lane already active: $lane" >&2
  exit 75
}

actual_head=$(git -C "$worktree" rev-parse HEAD)
if [[ "$actual_head" != "$expected_head" ]]; then
  echo "entry HEAD mismatch: expected $expected_head, got $actual_head" >&2
  exit 73
fi
if [[ -n "$(git -C "$worktree" status --porcelain)" ]]; then
  echo "entry worktree is dirty" >&2
  exit 73
fi

printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/started_at"
printf 'RUNNING\n' >"$control_dir/status"
printf '%s\n' "$actual_head" >"$control_dir/entry_head"

set +e
timeout --signal=TERM --kill-after=90s "${time_limit}s" \
  codex exec \
    --model gpt-5.6-sol \
    --config 'model_reasoning_effort="high"' \
    --dangerously-bypass-approvals-and-sandbox \
    --dangerously-bypass-hook-trust \
    --cd "$worktree" \
    --json \
    --color never \
    --output-last-message "$control_dir/final.md" \
    - <"$prompt" \
    >"$control_dir/events.jsonl" \
    2>"$control_dir/stderr.log"
result=$?
set -e

printf '%s\n' "$result" >"$control_dir/exit_code"
printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/finished_at"
git -C "$worktree" status --short --branch >"$control_dir/git-status.txt" || true
git -C "$worktree" rev-parse HEAD >"$control_dir/final_head" || true

if (( result == 0 )); then
  printf 'COMPLETE\n' >"$control_dir/status"
elif (( result == 124 || result == 137 )); then
  printf 'TIMEBOX_EXPIRED\n' >"$control_dir/status"
else
  printf 'FAILED_%d\n' "$result" >"$control_dir/status"
fi
exit "$result"
