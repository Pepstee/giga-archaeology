#!/usr/bin/env bash
set -euo pipefail

root=/home/gutua/software-factory
run_dir="$root/.control/gigabyte-dfi06-dfi07-20260724"
prompt="$root/giga-user/reports/GIGABYTE_UNSUPERVISED_DFI06_DFI07_PROMPT_2026-07-24.md"
predecessor=dfi06-expanded-polish-20260724.service

mkdir -p "$run_dir"

if [[ -f "$run_dir/attempt_count" ]]; then
    attempt_count=$(<"$run_dir/attempt_count")
else
    attempt_count=0
fi
attempt_count=$((attempt_count + 1))
printf '%s\n' "$attempt_count" > "$run_dir/attempt_count"
if (( attempt_count > 3 )); then
    date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/restart_ceiling_reached"
    exit 0
fi

if [[ -f "$run_dir/absolute_deadline_epoch" ]]; then
    absolute_deadline_epoch=$(<"$run_dir/absolute_deadline_epoch")
else
    absolute_deadline_epoch=$(( $(date +%s) + 50400 ))
    printf '%s\n' "$absolute_deadline_epoch" > "$run_dir/absolute_deadline_epoch"
fi

printf '%s\n' "$$" > "$run_dir/wrapper.pid"
date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/wrapper_started_at"

while systemctl --user is-active --quiet "$predecessor"; do
    if (( $(date +%s) >= absolute_deadline_epoch )); then
        date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/absolute_deadline_reached"
        exit 0
    fi
    date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/waiting_for_predecessor"
    sleep 15
done

systemctl --user show "$predecessor" \
    -p ActiveState -p Result -p ExecMainStatus \
    > "$run_dir/predecessor_result.txt" 2>&1 || true

cd "$root/giga-user"
date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/coordinator_started_at"

if (( $(date +%s) >= absolute_deadline_epoch )); then
    date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/absolute_deadline_reached"
    exit 0
fi

set +e
/usr/bin/codex exec \
    --dangerously-bypass-approvals-and-sandbox \
    --model gpt-5.6-sol \
    --cd "$root/giga-user" \
    --add-dir "$root/agentic-orchestrator" \
    --add-dir "$root/.worktrees" \
    --add-dir "$root/.control" \
    --color never \
    --json \
    --output-last-message "$run_dir/final.txt" \
    - < "$prompt" >> "$run_dir/activity.jsonl" 2>&1
status=$?
set -e

printf '%s\n' "$status" > "$run_dir/exit_code"
date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/coordinator_finished_at"
exit "$status"
