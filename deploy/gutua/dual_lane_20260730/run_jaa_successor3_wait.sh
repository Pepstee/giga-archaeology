#!/usr/bin/env bash
set -euo pipefail
umask 077

factory_root=/home/gutua/software-factory
predecessor_unit=${JAA_PREDECESSOR_UNIT:-giga-jaa-single-codex-successor2.service}
predecessor_control=${JAA_PREDECESSOR_CONTROL:-"$factory_root/.control/jaa-single-codex-successor2-20260730"}
poll_seconds=${JAA_WAIT_POLL_SECONDS:-30}
worktree=${JAA_WORKTREE:-"$factory_root/.worktrees/jaa-native-completion"}
prompt=${JAA_PROMPT_FILE:-"$factory_root/giga-user/deploy/gutua/dual_lane_20260729/jaa_single_codex_continuation_prompt.md"}
control_dir=${JAA_CONTROL_DIR:-"$factory_root/.control/jaa-single-codex-successor3-20260730"}
work_order=${GIGA_WORK_ORDER_PATH:-"$control_dir/work-order.json"}
worker_unit=${GIGA_WORKER_UNIT:-giga-jaa-single-codex-successor3.service}
worker_unit_file=${GIGA_WORKER_UNIT_FILE:-/home/gutua/.config/systemd/user/giga-jaa-single-codex-successor3.service}
downstream_launcher=${GIGA_DOWNSTREAM_LAUNCHER:-"$factory_root/.control/majaa-24h-20260810/bin/run_agent_loop.sh"}
lane=${GIGA_CHAIN_LANE:-jaa-single-codex-successor3}
total_seconds=${JAA_TOTAL_SECONDS:-172800}
wrapper_self=$(readlink -f -- "$0")

while systemctl --user is-active --quiet "$predecessor_unit"; do
  sleep "$poll_seconds"
done

if [[ -e "$predecessor_control/OBJECTIVE_COMPLETE" ]]; then
  exit 0
fi

# Keep this shell as the launcher's parent: the constitutional gate verifies
# both scripts in the live process ancestry and the enclosing user-unit cgroup.
GIGA_REQUIRED_WAIT_WRAPPER="$wrapper_self" \
GIGA_REQUIRED_WORKER_UNIT="$worker_unit" \
GIGA_REQUIRED_WORKER_UNIT_FILE="$worker_unit_file" \
MAJAA_WORK_ORDER_PATH="$work_order" \
"$downstream_launcher" "$lane" "$worktree" "$prompt" "$total_seconds"
