#!/usr/bin/env bash
set -euo pipefail

factory_root=/home/gutua/software-factory
worktree="$factory_root/.worktrees/jaa-native-completion"
prompt="$factory_root/giga-user/deploy/gutua/dual_lane_20260728/jaa_current_supervisor_prompt.md"
control_dir="$factory_root/.control/jaa-current-supervisor-20260728"
total_seconds=43200
round_seconds=7200

for unit in \
  giga-jaa-native.service \
  giga-jaa-overnight.service \
  giga-jaa-authorized-overnight.service \
  giga-jaa-12h-supervisor.service; do
  if systemctl --user is-active --quiet "$unit"; then
    echo "another JAA coordinator is active: $unit" >&2
    exit 75
  fi
done

mkdir -p "$control_dir"
chmod 700 "$control_dir"
exec 8>"$control_dir/supervisor.lock"
flock -n 8 || {
  echo "JAA current supervisor is already active" >&2
  exit 75
}

if [[ -e "$control_dir/started_at" || -e "$control_dir/OBJECTIVE_COMPLETE" ]]; then
  echo "JAA current control directory already contains a run" >&2
  exit 73
fi

started_epoch=$(date +%s)
deadline_epoch=$((started_epoch + total_seconds))
printf '%s\n' "$started_epoch" >"$control_dir/started.epoch"
printf '%s\n' "$deadline_epoch" >"$control_dir/deadline.epoch"
printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/started_at"
printf 'RUNNING\n' >"$control_dir/status"

round=0
terminal_result=0
while (( $(date +%s) < deadline_epoch )); do
  if [[ -e "$control_dir/OBJECTIVE_COMPLETE" || -e "$control_dir/BLOCKED" ]]; then
    break
  fi

  round=$((round + 1))
  round_dir=$(printf '%s/round-%02d' "$control_dir" "$round")
  mkdir -p "$round_dir"
  chmod 700 "$round_dir"

  remaining=$((deadline_epoch - $(date +%s)))
  limit=$round_seconds
  if (( remaining < limit )); then
    limit=$remaining
  fi
  printf '%s\n' "$(date --iso-8601=seconds)" >"$round_dir/started_at"
  printf '%s\n' "$limit" >"$round_dir/time_limit_seconds"

  set +e
  timeout --signal=TERM --kill-after=90s "${limit}s" \
    codex exec \
      --model gpt-5.6-sol \
      --config 'model_reasoning_effort="high"' \
      --dangerously-bypass-approvals-and-sandbox \
      --dangerously-bypass-hook-trust \
      --cd "$worktree" \
      --json \
      --color never \
      --output-last-message "$round_dir/final.md" \
      - <"$prompt" \
      >"$round_dir/events.jsonl" \
      2>"$round_dir/stderr.log"
  result=$?
  set -e

  terminal_result=$result
  printf '%s\n' "$result" >"$round_dir/exit_code"
  printf '%s\n' "$(date --iso-8601=seconds)" >"$round_dir/finished_at"
  git -C "$worktree" status --short --branch >"$round_dir/git-status.txt" || true
  git -C "$worktree" rev-parse HEAD >"$round_dir/head.txt" || true

  if [[ -e "$control_dir/OBJECTIVE_COMPLETE" || -e "$control_dir/BLOCKED" ]]; then
    break
  fi
  if (( result != 0 && result != 124 && result != 137 )); then
    printf 'FAILED_%d\n' "$result" >"$control_dir/status"
    break
  fi
done

printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/finished_at"
git -C "$worktree" status --short --branch >"$control_dir/git-status.txt" || true
git -C "$worktree" rev-parse HEAD >"$control_dir/head.txt" || true

if [[ -e "$control_dir/OBJECTIVE_COMPLETE" ]]; then
  printf 'OBJECTIVE_COMPLETE\n' >"$control_dir/status"
elif [[ -e "$control_dir/BLOCKED" ]]; then
  printf 'BLOCKED\n' >"$control_dir/status"
elif (( $(date +%s) >= deadline_epoch )); then
  printf 'TIMEBOX_EXPIRED\n' >"$control_dir/status"
elif (( terminal_result == 0 )); then
  printf 'SETTLED_WITHOUT_TERMINAL_MARKER\n' >"$control_dir/status"
fi

exit "$terminal_result"
