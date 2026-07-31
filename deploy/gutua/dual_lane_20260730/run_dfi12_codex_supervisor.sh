#!/usr/bin/env bash
set -euo pipefail

factory_root=/home/gutua/software-factory
worktree="$factory_root/.worktrees/orchestrator-v3-dfi-12"
prompt="$factory_root/giga-user/deploy/gutua/dual_lane_20260730/dfi12_codex_continuation_prompt.md"
control_dir=${DFI12_CONTROL_DIR:-"$factory_root/.control/dfi12-codex-20260730"}
total_seconds=${DFI12_TOTAL_SECONDS:-86400}
round_seconds=7200
auth_retries=3

mkdir -p "$control_dir"
chmod 700 "$control_dir"
exec 8>"$control_dir/supervisor.lock"
flock -n 8 || {
  echo "DFI-12 Codex supervisor already active" >&2
  exit 75
}

if [[ ! -d "$worktree/.git" && ! -f "$worktree/.git" ]]; then
  printf 'WORKTREE_MISSING\n' >"$control_dir/status"
  exit 78
fi
if pgrep -af 'codex exec' | grep -F -- "--cd $worktree" \
  >"$control_dir/unexpected-dfi12-codex-processes.txt"; then
  printf 'DUPLICATE_DFI12_CODEX_REFUSED\n' >"$control_dir/status"
  exit 75
fi
rm -f "$control_dir/unexpected-dfi12-codex-processes.txt"

if [[ ! -e "$control_dir/started.epoch" ]]; then
  started_epoch=$(date +%s)
  deadline_epoch=$((started_epoch + total_seconds))
  printf '%s\n' "$started_epoch" >"$control_dir/started.epoch"
  printf '%s\n' "$deadline_epoch" >"$control_dir/deadline.epoch"
  printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/started_at"
else
  deadline_epoch=$(<"$control_dir/deadline.epoch")
fi
printf 'RUNNING\n' >"$control_dir/status"

round=0
if [[ -s "$control_dir/current_round" ]]; then
  round=$(<"$control_dir/current_round")
fi
terminal_result=0

while (( $(date +%s) < deadline_epoch )); do
  if [[ -e "$control_dir/OBJECTIVE_COMPLETE" || -e "$control_dir/BLOCKED" ]]; then
    break
  fi

  round=$((round + 1))
  printf '%s\n' "$round" >"$control_dir/current_round"
  round_dir=$(printf '%s/round-%02d' "$control_dir" "$round")
  mkdir -p "$round_dir"
  chmod 700 "$round_dir"

  remaining=$((deadline_epoch - $(date +%s)))
  limit=$round_seconds
  if (( remaining < limit )); then
    limit=$remaining
  fi
  if (( limit < 1 )); then
    limit=1
  fi
  printf '%s\n' "$(date --iso-8601=seconds)" >"$round_dir/started_at"
  printf '%s\n' "$limit" >"$round_dir/time_limit_seconds"

  attempt=0
  result=1
  while (( attempt < auth_retries )); do
    attempt=$((attempt + 1))
    attempt_dir=$(printf '%s/attempt-%02d' "$round_dir" "$attempt")
    mkdir -p "$attempt_dir"
    printf '%s\n' "$(date --iso-8601=seconds)" >"$attempt_dir/started_at"

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
        --output-last-message "$attempt_dir/final.md" \
        - <"$prompt" \
        >"$attempt_dir/events.jsonl" \
        2>"$attempt_dir/stderr.log"
    result=$?
    set -e

    printf '%s\n' "$result" >"$attempt_dir/exit_code"
    printf '%s\n' "$(date --iso-8601=seconds)" >"$attempt_dir/finished_at"
    if (( result == 0 || result == 124 || result == 137 )); then
      break
    fi
    if grep -Eqi 'refresh token|token_expired|401 Unauthorized|sign in again' \
      "$attempt_dir/stderr.log" "$attempt_dir/events.jsonl"; then
      printf 'AUTH_RETRY_%d\n' "$attempt" >"$control_dir/status"
      sleep $((attempt * 30))
      continue
    fi
    break
  done

  terminal_result=$result
  printf '%s\n' "$result" >"$round_dir/exit_code"
  printf '%s\n' "$(date --iso-8601=seconds)" >"$round_dir/finished_at"
  git -C "$worktree" status --short --branch >"$round_dir/git-status.txt" || true
  git -C "$worktree" rev-parse HEAD >"$round_dir/head.txt" || true

  if [[ -e "$control_dir/OBJECTIVE_COMPLETE" || -e "$control_dir/BLOCKED" ]]; then
    break
  fi
  if (( result != 0 && result != 124 && result != 137 )); then
    latest_stderr=$(find "$round_dir" -name stderr.log | sort | tail -1)
    if [[ -n "$latest_stderr" ]] && grep -Eqi \
      'refresh token|token_expired|401 Unauthorized|sign in again' "$latest_stderr"; then
      printf 'AUTH_REQUIRED\n' >"$control_dir/status"
      touch "$control_dir/AUTH_REQUIRED"
    else
      printf 'FAILED_%d\n' "$result" >"$control_dir/status"
    fi
    break
  fi
  printf 'RUNNING\n' >"$control_dir/status"
done

printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/finished_at"
git -C "$worktree" status --short --branch >"$control_dir/git-status.txt" || true
git -C "$worktree" rev-parse HEAD >"$control_dir/head.txt" || true

if [[ -e "$control_dir/OBJECTIVE_COMPLETE" ]]; then
  printf 'OBJECTIVE_COMPLETE\n' >"$control_dir/status"
elif [[ -e "$control_dir/BLOCKED" ]]; then
  printf 'BLOCKED\n' >"$control_dir/status"
elif [[ -e "$control_dir/AUTH_REQUIRED" ]]; then
  printf 'AUTH_REQUIRED\n' >"$control_dir/status"
elif (( $(date +%s) >= deadline_epoch )); then
  printf 'TIMEBOX_EXPIRED\n' >"$control_dir/status"
elif (( terminal_result == 0 )); then
  printf 'SETTLED_WITHOUT_TERMINAL_MARKER\n' >"$control_dir/status"
fi

exit "$terminal_result"
