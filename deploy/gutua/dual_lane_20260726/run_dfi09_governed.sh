#!/usr/bin/env bash
set -euo pipefail

factory_root=/home/gutua/software-factory
worktree="$factory_root/.worktrees/orchestrator-v3-dfi-09"
prompt="$factory_root/giga-user/deploy/gutua/dual_lane_20260726/dfi09_prompt.md"
control_dir="$factory_root/.control/dfi09-governed-20260726"

mkdir -p "$control_dir"
chmod 700 "$control_dir"
exec 8>"$control_dir/supervisor.lock"
flock -n 8 || {
  echo "DFI-09 coordinator is already active" >&2
  exit 75
}

if [[ -e "$control_dir/events.jsonl" || -e "$control_dir/CERTIFIED" ]]; then
  echo "DFI-09 control directory already contains a run; refusing overwrite" >&2
  exit 73
fi

printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/started_at"
printf 'RUNNING\n' >"$control_dir/status"

set +e
timeout --signal=TERM --kill-after=90s 43200s \
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

if [[ -f "$control_dir/CERTIFIED" ]]; then
  printf 'CERTIFIED\n' >"$control_dir/status"
elif [[ -f "$control_dir/NOT_CERTIFIED" ]]; then
  printf 'NOT_CERTIFIED\n' >"$control_dir/status"
elif (( result == 0 )); then
  printf 'SETTLED_WITHOUT_TERMINAL_MARKER\n' >"$control_dir/status"
else
  printf 'FAILED_%d\n' "$result" >"$control_dir/status"
fi

exit "$result"

