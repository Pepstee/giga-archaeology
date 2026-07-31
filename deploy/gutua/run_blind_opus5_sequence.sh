#!/usr/bin/env bash
set -euo pipefail

root=/home/gutua/software-factory/.control/blind-opus-portfolio-20260725
runner="$root/run_review.sh"
prompt="$root/prompt.md"
v2_snapshot="$root/v2-snapshot"
v3_snapshot="$root/v3-snapshot"
v2_commit=32efb0797905078a6917d748ce93efd46f7527be
v3_commit=35efb19b07867bb58e1288479513078cf9ab65e4
v2_run="$root/runs/v2-opus5-r3"
v3_run="$root/runs/v3-opus5-r3"
sequence_log="$root/opus5-sequence.status"

if [[ -e "$v2_run" || -e "$v3_run" ]]; then
  echo "refusing to overwrite an existing Opus 5 run directory" >&2
  exit 70
fi

validate_arm() {
  local run_dir=$1
  local expected_arm=$2

  python3 - "$run_dir" "$expected_arm" <<'PY'
import json
import pathlib
import sys

run_dir = pathlib.Path(sys.argv[1])
expected_arm = sys.argv[2]
metadata = json.loads((run_dir / "result.metadata.json").read_text(encoding="utf-8"))
arm = (run_dir / "arm").read_text(encoding="utf-8").strip()
exit_code = (run_dir / "exit_code").read_text(encoding="utf-8").strip()
report = run_dir / "result.md"
before = run_dir / "source_status.before"
after = run_dir / "source_status.after"

errors = []
if arm != expected_arm:
    errors.append(f"arm mismatch: {arm!r}")
if exit_code != "0":
    errors.append(f"non-zero wrapper exit: {exit_code!r}")
if metadata.get("parse_ok") is not True:
    errors.append("result JSON did not parse")
if metadata.get("type") != "result" or metadata.get("subtype") != "success":
    errors.append("Claude result was not successful")
if metadata.get("is_error") is not False:
    errors.append("Claude marked the result as an error")
if "claude-opus-5" not in (metadata.get("model_usage") or {}):
    errors.append("exact claude-opus-5 model evidence is absent")
if not report.is_file() or report.stat().st_size < 1000:
    errors.append("portfolio report is absent or implausibly short")
if before.read_bytes() or after.read_bytes():
    errors.append("read-only repository snapshot cleanliness failed")

if errors:
    raise SystemExit("; ".join(errors))
PY
}

printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "V2_STARTED" >"$sequence_log"
"$runner" "$v2_run" "$v2_snapshot" "$v2_commit" "$prompt" V2
validate_arm "$v2_run" V2
printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "V2_VALIDATED" >>"$sequence_log"

printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "V3_STARTED" >>"$sequence_log"
"$runner" "$v3_run" "$v3_snapshot" "$v3_commit" "$prompt" V3
validate_arm "$v3_run" V3
printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "V3_VALIDATED" >>"$sequence_log"

sha256sum \
  "$v2_run/result.md" \
  "$v2_run/result.metadata.json" \
  "$v3_run/result.md" \
  "$v3_run/result.metadata.json" \
  >"$root/opus5-sequence.sha256"
printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "COMPLETE" >>"$sequence_log"
