#!/usr/bin/env bash
set -euo pipefail

root=/home/gutua/software-factory
run_dir="$root/.control/fable-governed-dfi-20260725"
prompt="$root/giga-user/deploy/gutua/FABLE_GOVERNED_DFI_CONTINUATION.md"
deadline_file="$run_dir/deadline_epoch"
attempt_file="$run_dir/attempt_count"
complete_file="$run_dir/DFI_PROGRAMME_COMPLETE"

mkdir -p "$run_dir"
if [[ ! -f "$deadline_file" ]]; then
    printf '%s\n' "$(( $(date +%s) + 50400 ))" > "$deadline_file"
fi
deadline=$(<"$deadline_file")
attempt=0
[[ -f "$attempt_file" ]] && attempt=$(<"$attempt_file")

while (( $(date +%s) < deadline )) && [[ ! -f "$complete_file" ]]; do
    attempt=$((attempt + 1))
    printf '%s\n' "$attempt" > "$attempt_file"
    if (( attempt > 6 )); then
        date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/restart_ceiling_reached"
        exit 1
    fi

    attempt_dir="$run_dir/attempt-$attempt"
    mkdir -p "$attempt_dir"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$attempt_dir/started_at"

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
        --output-last-message "$attempt_dir/final.txt" \
        - < "$prompt" >> "$attempt_dir/activity.jsonl" 2>&1
    status=$?
    set -e

    printf '%s\n' "$status" > "$attempt_dir/exit_code"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$attempt_dir/finished_at"
    [[ -f "$complete_file" ]] && exit 0
    sleep $(( attempt * 30 ))
done

date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/window_finished"
