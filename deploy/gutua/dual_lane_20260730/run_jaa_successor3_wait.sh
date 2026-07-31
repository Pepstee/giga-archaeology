#!/usr/bin/env bash
set -euo pipefail

predecessor_unit=giga-jaa-single-codex-successor2.service
predecessor_control=/home/gutua/software-factory/.control/jaa-single-codex-successor2-20260730
poll_seconds=30

while systemctl --user is-active --quiet "$predecessor_unit"; do
  sleep "$poll_seconds"
done

if [[ -e "$predecessor_control/OBJECTIVE_COMPLETE" ]]; then
  exit 0
fi

exec /home/gutua/software-factory/giga-user/deploy/gutua/dual_lane_20260729/run_jaa_single_codex_supervisor.sh
