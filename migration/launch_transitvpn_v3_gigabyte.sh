#!/usr/bin/env bash
set -euo pipefail

run_root=/home/gutua/software-factory/.control/transitvpn-v3-overseer-candidate-20260821
log_path="$run_root/state/transitvpn-v3-overseer.log"
lock_path="$run_root/state/transitvpn-v3-overseer.launch.lock"

mkdir -p "$run_root/state"
exec 9>"$lock_path"
if ! flock -n 9; then
  printf '%s launcher refused duplicate instance\n' "$(date -u +%FT%TZ)" >>"$log_path"
  exit 0
fi

exec >>"$log_path" 2>&1
printf '%s Windows-owned full TransitVPN orchestrator launch started\n' "$(date -u +%FT%TZ)"
cd "$run_root"

# Preserve the complete planner/replan loop. The operator has selected a Codex-only factory;
# every role remains explicit rather than silently falling back to a fixed task DAG.
export AGENTIC_TASK_MANAGER=codex:gpt-5.6-terra
export AGENTIC_BUILDER=codex:gpt-5.6-sol
export AGENTIC_TESTER=codex:gpt-5.6-sol
export AGENTIC_JUDGE=codex:gpt-5.6-terra
export AGENTIC_OVERSEER=codex:gpt-5.6-terra
export AGENTIC_TASK_MANAGER_EFFORT=medium
export AGENTIC_BUILDER_EFFORT=medium
export AGENTIC_TESTER_EFFORT=medium
export AGENTIC_JUDGE_EFFORT=high
export AGENTIC_OVERSEER_EFFORT=high
# The current Codex transport reports its mandatory stdin read as one tool call.  One permits
# transport only; the planner still receives no budget for exploratory host inspection.
export AGENTIC_TASK_MANAGER_MAX_TOOL_CALLS=1
export AGENTIC_BUILDER_MAX_TOOL_CALLS=16
export AGENTIC_TESTER_MAX_TOOL_CALLS=12
export AGENTIC_JUDGE_MAX_TOOL_CALLS=18
export AGENTIC_OVERSEER_MAX_TOOL_CALLS=1
export AGENTIC_FACTORY_CONTEXT_MODE=contained
export AGENTIC_DETERMINISTIC_CACHE_MODE=active
export AGENTIC_HOST_ASSURANCE_MODE=active
export AGENTIC_EXTERNAL_EVIDENCE_MODE=active
export AGENTIC_RUNNER_TIMEOUT_SECONDS=1200

set +e
timeout --signal=TERM --kill-after=120s 18h \
  python3 -c \
    'from control.daemon import run_daemon; run_daemon("/home/gutua/software-factory/.control/transitvpn-v3-overseer-candidate-20260821", max_cycles=None, poll_interval=2, per_project_cap=1, max_workers=4)'
result=$?
set -e

printf '%s Windows-owned full TransitVPN orchestrator launch exited status=%s\n' \
  "$(date -u +%FT%TZ)" "$result"
exit "$result"
