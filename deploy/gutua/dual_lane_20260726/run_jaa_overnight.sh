#!/usr/bin/env bash
set -euo pipefail

factory_root=/home/gutua/software-factory
worktree="$factory_root/.worktrees/jaa-native-completion"
prompt="$factory_root/giga-user/deploy/gutua/dual_lane_20260726/jaa_overnight_prompt.md"
control_dir="$factory_root/.control/jaa-overnight-20260726"

if systemctl --user is-active --quiet giga-jaa-native.service; then
  echo "original JAA service is still active; refusing a second writer" >&2
  exit 75
fi

mkdir -p "$control_dir"
chmod 700 "$control_dir"
exec 8>"$control_dir/supervisor.lock"
flock -n 8 || {
  echo "overnight JAA coordinator is already active" >&2
  exit 75
}

if [[ -e "$control_dir/events.jsonl" || -e "$control_dir/OBJECTIVE_COMPLETE" ]]; then
  echo "overnight control directory already contains a run; refusing overwrite" >&2
  exit 73
fi

printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/started_at"
printf 'RUNNING\n' >"$control_dir/status"

set +e
timeout --signal=TERM --kill-after=90s 36000s \
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
git -C "$worktree" rev-parse HEAD >"$control_dir/head.txt" || true

if [[ -f "$control_dir/OBJECTIVE_COMPLETE" ]]; then
  printf 'OBJECTIVE_COMPLETE\n' >"$control_dir/status"
elif [[ -f "$control_dir/BLOCKED" ]]; then
  printf 'BLOCKED\n' >"$control_dir/status"
elif [[ -f "$control_dir/TIMEBOX_SETTLED" ]]; then
  printf 'TIMEBOX_SETTLED\n' >"$control_dir/status"
elif (( result == 0 )); then
  printf 'SETTLED_WITHOUT_TERMINAL_MARKER\n' >"$control_dir/status"
elif (( result == 124 || result == 137 )); then
  printf 'TIMEBOX_EXPIRED\n' >"$control_dir/status"
else
  printf 'FAILED_%d\n' "$result" >"$control_dir/status"
fi

exit "$result"

