#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${LAND_MONITOR_PYTHON:-python3}"
node_bin="${LAND_MONITOR_NODE:-node}"
input_path="${LAND_MONITOR_INPUT:-state/listings.json}"
goal_path="${LAND_MONITOR_GOAL:-config/goal.json}"
features_path="${LAND_MONITOR_FEATURES:-state/feature_points.json}"
cadastre_path="${LAND_MONITOR_CADASTRE:-state/cadastral_values.csv}"
report_path="${LAND_MONITOR_REPORT:-outputs/report-data.json}"
workbook_path="${LAND_MONITOR_WORKBOOK:-outputs/latest/land-investment-report.xlsx}"
preview_dir="${LAND_MONITOR_QA_DIR:-outputs/latest/qa}"
lock_dir="state/run.lock"

mkdir -p state "$(dirname "$report_path")" "$(dirname "$workbook_path")"
if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "Another monitor run is already active: $lock_dir" >&2
  exit 75
fi
trap 'rmdir "$lock_dir"' EXIT

if [[ ! -f "$input_path" ]]; then
  echo "Input file not found: $input_path" >&2
  echo "Refresh it from an authorized/licensed source before running the monitor." >&2
  exit 66
fi

run_args=(
  -m land_monitor.cli run
  --input "$input_path"
  --goal "$goal_path"
  --out "$report_path"
)
if [[ -f "$features_path" ]]; then
  run_args+=(--features "$features_path")
fi
if [[ -f "$cadastre_path" ]]; then
  run_args+=(--cadastre "$cadastre_path")
fi
if [[ "${LAND_MONITOR_USE_OPENAI:-false}" == "true" ]]; then
  run_args+=(--use-openai)
fi
if [[ "${LAND_MONITOR_LIVE_ROUTING:-false}" == "true" ]]; then
  run_args+=(--live-routing)
fi

"$python_bin" "${run_args[@]}"
"$node_bin" scripts/build_workbook.mjs "$report_path" "$workbook_path" "$preview_dir"

if [[ "${LAND_MONITOR_SEND_TELEGRAM:-false}" == "true" ]]; then
  "$python_bin" -m land_monitor.cli digest --report "$report_path" --send
fi

echo "Report ready: $workbook_path"
