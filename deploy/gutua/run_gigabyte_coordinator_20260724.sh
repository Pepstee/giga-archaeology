#!/usr/bin/env bash
set -u

run_dir=/home/gutua/software-factory/.control/gigabyte-coordinator-20260724
prompt=/home/gutua/software-factory/giga-user/reports/GIGABYTE_COORDINATOR_PROMPT_2026-07-24.md

mkdir -p "$run_dir"
cd /home/gutua/software-factory/giga-user || exit 111

/usr/bin/codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --model gpt-5.6-sol \
  --cd /home/gutua/software-factory/giga-user \
  --add-dir /home/gutua/software-factory/agentic-orchestrator \
  --add-dir /home/gutua/software-factory/.worktrees \
  --add-dir /home/gutua/software-factory/.control \
  --color never \
  --json \
  --output-last-message "$run_dir/final.txt" \
  - < "$prompt" >> "$run_dir/activity.jsonl" 2>&1
status=$?
printf '%s\n' "$status" > "$run_dir/exit_code"
exit "$status"
