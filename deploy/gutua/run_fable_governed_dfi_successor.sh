#!/usr/bin/env bash
set -euo pipefail

unit=fable-governed-dfi-20260725.service
run_dir=/home/gutua/software-factory/.control/fable-governed-dfi-20260725

while systemctl --user is-active --quiet "$unit"; do
    sleep 15
done

printf '%s\n' "$(( $(date +%s) + 50400 ))" > "$run_dir/deadline_epoch"
printf '%s\n' "0" > "$run_dir/attempt_count"
date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/successor_started_at"

exec /home/gutua/software-factory/giga-user/deploy/gutua/run_fable_governed_dfi.sh
