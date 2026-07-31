#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 LANE WORKTREE PROMPT_FILE CONTROL_DIR" >&2
  exit 64
fi

lane=$1
worktree=$2
prompt_file=$3
control_dir=$4
factory_root=/home/gutua/software-factory
run_seconds=50400
max_rounds=12

[[ "$lane" == "jaa" || "$lane" == "dfi" ]] || {
  echo "invalid lane: $lane" >&2
  exit 64
}
[[ -d "$worktree" && -f "$prompt_file" ]] || {
  echo "worktree or prompt is missing" >&2
  exit 66
}

mkdir -p "$control_dir"
chmod 700 "$control_dir"
exec 8>"$control_dir/supervisor.lock"
flock -n 8 || {
  echo "another $lane supervisor already owns this control directory" >&2
  exit 75
}

if [[ ! -f "$control_dir/deadline.epoch" ]]; then
  printf '%s\n' "$(( $(date +%s) + run_seconds ))" >"$control_dir/deadline.epoch"
fi
deadline="$(<"$control_dir/deadline.epoch")"
printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/started_at"
printf 'RUNNING\n' >"$control_dir/status"

round=0
while (( round < max_rounds )); do
  now="$(date +%s)"
  remaining=$(( deadline - now ))
  if (( remaining < 300 )); then
    printf 'TIMEBOX_COMPLETE\n' >"$control_dir/status"
    exit 0
  fi
  if [[ -f "$control_dir/OBJECTIVE_COMPLETE" ]]; then
    printf 'OBJECTIVE_COMPLETE\n' >"$control_dir/status"
    exit 0
  fi

  round=$(( round + 1 ))
  round_dir="$control_dir/round-$(printf '%02d' "$round")"
  mkdir -p "$round_dir"
  printf '%s\n' "$(date --iso-8601=seconds)" >"$round_dir/started_at"
  printf '%s\n' "$round" >"$control_dir/current_round"

  set +e
  timeout --signal=TERM --kill-after=90s "${remaining}s" \
    codex exec \
      --model gpt-5.6-sol \
      --config 'model_reasoning_effort="high"' \
      --dangerously-bypass-approvals-and-sandbox \
      --dangerously-bypass-hook-trust \
      --cd "$worktree" \
      --json \
      --color never \
      --output-last-message "$round_dir/final.md" \
      - <"$prompt_file" \
      >"$round_dir/events.jsonl" \
      2>"$round_dir/stderr.log"
  result=$?
  set -e

  printf '%s\n' "$result" >"$round_dir/exit_code"
  printf '%s\n' "$(date --iso-8601=seconds)" >"$round_dir/finished_at"
  git -C "$worktree" status --short --branch >"$round_dir/git-status.txt" || true
  git -C "$worktree" rev-parse HEAD >"$round_dir/head.txt" || true

  if [[ -f "$control_dir/OBJECTIVE_COMPLETE" ]]; then
    printf 'OBJECTIVE_COMPLETE\n' >"$control_dir/status"
    exit 0
  fi

  now="$(date +%s)"
  if (( now >= deadline )); then
    printf 'TIMEBOX_COMPLETE\n' >"$control_dir/status"
    exit 0
  fi

  if (( result == 124 || result == 137 )); then
    printf 'TIMEBOX_COMPLETE\n' >"$control_dir/status"
    exit 0
  fi

  printf 'ROUND_%02d_SETTLED_%d\n' "$round" "$result" >"$control_dir/status"
  sleep 20
  printf 'RUNNING\n' >"$control_dir/status"
done

printf 'ROUND_LIMIT_REACHED\n' >"$control_dir/status"
exit 0

