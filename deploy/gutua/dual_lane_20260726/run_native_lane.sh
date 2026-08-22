#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 LANE WORKTREE PROMPT_FILE CONTROL_DIR" >&2
  exit 64
fi

lane=$1
worktree=$2
prompt_file=$3
control_dir=$4
factory_root=/home/gutua/software-factory
run_seconds=50400
max_rounds=12
gate="$factory_root/giga-user/deploy/gutua/gate_admission.py"
constitution="$factory_root/giga-user/CHARTER.md"
turnstile="$factory_root/giga-user/scripts/factory_turnstile.py"

[[ "$lane" == "jaa" || "$lane" == "dfi" ]] || {
  echo "invalid lane: $lane" >&2
  exit 64
}
[[ -d "$worktree" && -f "$prompt_file" ]] || {
  echo "worktree or prompt is missing" >&2
  exit 66
}

mkdir -p "$control_dir"
chmod 700 "$control_dir"
work_order="$control_dir/work-order.json"
preflight_receipt="$control_dir/preflight-receipt.json"
completion_receipt="$control_dir/completion-receipt.json"
completion_verification="$control_dir/completion-verification.json"
confinement_plan="$control_dir/write-confinement-plan.json"
confinement_execution="$control_dir/write-confinement-execution.json"
override_ledger="$factory_root/.control/constitution-overrides.jsonl"
semantic_review="$control_dir/semantic-review.json"
operator_override="$control_dir/operator-override.json"

[[ -f "$work_order" ]] || {
  echo "constitutional work order is required: $work_order" >&2
  exit 42
}
[[ -f "$gate" && -f "$constitution" && -f "$turnstile" ]] || {
  echo "constitutional gate, Constitution, or Factory Turnstile is missing" >&2
  exit 42
}
worker_executable=$(command -v codex || true)
[[ -n "$worker_executable" && -x "$worker_executable" ]] || {
  echo "Codex worker executable is unavailable" >&2
  exit 42
}

exec 8>"$control_dir/supervisor.lock"
flock -n 8 || {
  echo "another $lane supervisor already owns this control directory" >&2
  exit 75
}

preflight_args=(
  constitution preflight
  --work-order "$work_order"
  --constitution "$constitution"
  --worktree "$worktree"
  --override-ledger "$override_ledger"
  --receipt-out "$preflight_receipt"
)
[[ -f "$semantic_review" ]] && preflight_args+=(--semantic-review "$semantic_review")
[[ -f "$operator_override" ]] && preflight_args+=(--override "$operator_override")
python3 "$gate" "${preflight_args[@]}" >"$control_dir/preflight-result.json" || {
  printf 'PREFLIGHT_REJECTED\n' >"$control_dir/status"
  exit 42
}

plan_confinement() {
  if ! python3 "$gate" constitution plan-confinement \
      --work-order "$work_order" \
      --constitution "$constitution" \
      --worktree "$worktree" \
      --preflight-receipt "$preflight_receipt" \
      --worker-executable "$worker_executable" \
      --receipt-out "$confinement_plan" \
      >"$control_dir/write-confinement-plan-result.json"; then
    printf 'CONFINEMENT_REJECTED\n' >"$control_dir/status"
    return 42
  fi
}
plan_confinement

work_order_hash=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["work_order_sha256"])' "$preflight_receipt")
claim_marker=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["completion"]["claim_marker"])' "$work_order")
turnstile_control="$control_dir/turnstile-$work_order_hash"
if [[ ! -f "$turnstile_control/state.json" ]]; then
  python3 "$turnstile" \
    --control-dir "$turnstile_control" \
    --worktree "$worktree" \
    init --stage "$lane:$work_order_hash" \
    >"$control_dir/turnstile-init.json"
fi

verify_completion_claim() {
  [[ -f "$worktree/$claim_marker" ]] || return 1
  if ! python3 "$gate" constitution prove \
      --work-order "$work_order" \
      --constitution "$constitution" \
      --worktree "$worktree" \
      --preflight-receipt "$preflight_receipt" \
      --confinement-plan "$confinement_plan" \
      --confinement-execution "$confinement_execution" \
      --evidence-dir "$control_dir/completion-evidence" \
      --receipt-out "$completion_receipt" \
      >"$control_dir/completion-result.json"; then
    printf 'COMPLETION_REJECTED\n' >"$control_dir/status"
    return 42
  fi
  if ! python3 "$gate" constitution verify-completion \
      --work-order "$work_order" \
      --constitution "$constitution" \
      --worktree "$worktree" \
      --preflight-receipt "$preflight_receipt" \
      --completion-receipt "$completion_receipt" \
      --confinement-plan "$confinement_plan" \
      --confinement-execution "$confinement_execution" \
      --receipt-out "$completion_verification" \
      >"$control_dir/completion-verification-result.json"; then
    printf 'COMPLETION_REJECTED\n' >"$control_dir/status"
    return 42
  fi
  printf 'OBJECTIVE_COMPLETE_VERIFIED\n' >"$control_dir/status"
  return 0
}

if [[ ! -f "$control_dir/deadline.epoch" ]]; then
  printf '%s\n' "$(( $(date +%s) + run_seconds ))" >"$control_dir/deadline.epoch"
fi
deadline="$(<"$control_dir/deadline.epoch")"
printf '%s\n' "$(date --iso-8601=seconds)" >"$control_dir/started_at"
printf 'RUNNING\n' >"$control_dir/status"

round=0
while (( round < max_rounds )); do
  now="$(date +%s)"
  remaining=$(( deadline - now ))
  if (( remaining < 300 )); then
    printf 'TIMEBOX_COMPLETE\n' >"$control_dir/status"
    exit 0
  fi
  if [[ -f "$worktree/$claim_marker" ]]; then
    verify_completion_claim
    exit $?
  fi

  round=$(( round + 1 ))
  round_dir="$control_dir/round-$(printf '%02d' "$round")"
  mkdir -p "$round_dir"
  printf '%s\n' "$(date --iso-8601=seconds)" >"$round_dir/started_at"
  printf '%s\n' "$round" >"$control_dir/current_round"
  plan_confinement || exit $?

  set +e
  timeout --signal=TERM --kill-after=90s "${remaining}s" \
    python3 "$turnstile" \
      --control-dir "$turnstile_control" \
      --worktree "$worktree" \
      worker --actor codex -- \
    python3 "$gate" constitution run-confined \
      --work-order "$work_order" \
      --worktree "$worktree" \
      --preflight-receipt "$preflight_receipt" \
      --confinement-plan "$confinement_plan" \
      --execution-receipt-out "$confinement_execution" \
      -- \
    "$worker_executable" exec \
      --model gpt-5.6-sol \
      --config 'model_reasoning_effort="high"' \
      --sandbox workspace-write \
      --ask-for-approval never \
      --ephemeral \
      --ignore-user-config \
      --ignore-rules \
      --cd "$worktree" \
      --json \
      --color never \
      - <"$prompt_file" \
      >"$round_dir/events.jsonl" \
      2>"$round_dir/stderr.log"
  result=$?
  set -e

  printf '%s\n' "$result" >"$round_dir/exit_code"
  printf '%s\n' "$(date --iso-8601=seconds)" >"$round_dir/finished_at"
  git -C "$worktree" status --short --branch >"$round_dir/git-status.txt" || true
  git -C "$worktree" rev-parse HEAD >"$round_dir/head.txt" || true

  if [[ -f "$worktree/$claim_marker" ]]; then
    verify_completion_claim
    exit $?
  fi

  now="$(date +%s)"
  if (( now >= deadline )); then
    printf 'TIMEBOX_COMPLETE\n' >"$control_dir/status"
    exit 0
  fi

  if (( result == 124 || result == 137 )); then
    printf 'TIMEBOX_COMPLETE\n' >"$control_dir/status"
    exit 0
  fi

  printf 'ROUND_%02d_SETTLED_%d\n' "$round" "$result" >"$control_dir/status"
  sleep 20
  printf 'RUNNING\n' >"$control_dir/status"
done

printf 'ROUND_LIMIT_REACHED\n' >"$control_dir/status"
exit 0
