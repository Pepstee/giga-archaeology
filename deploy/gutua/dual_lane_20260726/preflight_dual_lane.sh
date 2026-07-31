#!/usr/bin/env bash
set -euo pipefail

factory_root=/home/gutua/software-factory
control_root="$factory_root/.control/native-dual-lane-20260726"
jaa_worktree="$factory_root/.worktrees/jaa-native-completion"
dfi_worktree="$factory_root/.worktrees/orchestrator-v3-dfi-08"
production_root="$factory_root/agentic-orchestrator/projects/orchestrator-v3"

expected_jaa_branch=codex/jaa-native-completion-20260725
expected_jaa_head=3679d98b1402b434e1e55c79b8b7d8a4f0a3c14a
expected_dfi_branch=di/dfi-08-shadow-ledger
expected_dfi_head=d1d0ba75fb7d1cfab0d8fcfa207c4895746176a0

fail() {
  echo "PREFLIGHT_FAIL: $*" >&2
  exit 1
}

command -v codex >/dev/null || fail "codex is unavailable"
command -v claude >/dev/null || fail "claude is unavailable"
command -v flock >/dev/null || fail "flock is unavailable"
command -v systemctl >/dev/null || fail "systemctl is unavailable"

codex login status 2>&1 | grep -q "Logged in" ||
  fail "Codex is not authenticated"
claude auth status 2>&1 | grep -q '"loggedIn": true' ||
  fail "Claude is not authenticated"
systemctl --user is-system-running | grep -Eq 'running|degraded' ||
  fail "the user systemd manager is unavailable"

[[ -d "$jaa_worktree/.git" || -f "$jaa_worktree/.git" ]] ||
  fail "JAA worktree is missing"
[[ -d "$dfi_worktree/.git" || -f "$dfi_worktree/.git" ]] ||
  fail "DFI worktree is missing"

[[ "$(git -C "$jaa_worktree" branch --show-current)" == "$expected_jaa_branch" ]] ||
  fail "unexpected JAA branch"
[[ "$(git -C "$jaa_worktree" rev-parse HEAD)" == "$expected_jaa_head" ]] ||
  fail "unexpected JAA HEAD"
[[ -z "$(git -C "$jaa_worktree" status --short)" ]] ||
  fail "JAA worktree is not clean"

[[ "$(git -C "$dfi_worktree" branch --show-current)" == "$expected_dfi_branch" ]] ||
  fail "unexpected DFI branch"
[[ "$(git -C "$dfi_worktree" rev-parse HEAD)" == "$expected_dfi_head" ]] ||
  fail "unexpected DFI HEAD"

actual_dfi_status="$(git -C "$dfi_worktree" status --short)"
expected_dfi_status=$' M pyproject.toml\n?? infra/execution_ledger.py\n?? tests/architecture/test_execution_ledger_architecture.py\n?? tests/test_execution_ledger.py'
[[ "$actual_dfi_status" == "$expected_dfi_status" ]] ||
  fail "DFI dirty-path set differs from the frozen candidate"

check_sha256() {
  local relative_path=$1
  local expected=$2
  local actual
  actual="$(sha256sum "$dfi_worktree/$relative_path" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] ||
    fail "DFI candidate hash mismatch: $relative_path"
}

check_sha256 pyproject.toml \
  41a69b029afcebf887134b0d15670f846d2fc5ddf2d106d3c33efcc5a00585d1
check_sha256 infra/execution_ledger.py \
  e4baa389e4e0d2e69eb90c16a93616f757408196ad0b44c59f00ed6a8bf9a37e
check_sha256 tests/test_execution_ledger.py \
  567af5589f996477520d24c74dc97d219b9bd09163729aeb37ca3f55805552fa
check_sha256 tests/architecture/test_execution_ledger_architecture.py \
  a54e2be02d6f53290a7dbedb76507450a108913974ec9473aab64b584b0bf571

[[ -f "$production_root/STOP" ]] || fail "production STOP is not armed"
if systemctl --user is-active --quiet orchestrator-v3.service; then
  fail "production orchestrator-v3.service is active"
fi

if systemctl --user is-active --quiet giga-jaa-native.service; then
  fail "JAA native supervisor is already active"
fi
if systemctl --user is-active --quiet giga-dfi-native.service; then
  fail "DFI native supervisor is already active"
fi

if pgrep -af 'codex exec' | grep -v 'preflight_dual_lane' >/dev/null; then
  fail "another codex exec process is already active"
fi
if pgrep -af '/usr/bin/claude|claude -p' >/dev/null; then
  fail "another Claude process is already active"
fi

mkdir -p "$control_root"/{bin,jaa,dfi}
chmod 700 "$control_root" "$control_root"/{bin,jaa,dfi}

exec 9>"$factory_root/.control/claude-global.lock"
flock -n 9 || fail "the global Claude lock is currently held"
flock -u 9

loginctl show-user "$(id -un)" -p Linger
echo "PREFLIGHT_OK"
