#!/usr/bin/env bash
set -euo pipefail

factory_root="${1:-/home/gutua/software-factory}"
agentic_target="$factory_root/agentic-orchestrator"
giga_target="$factory_root/giga-user"
portable_target="$factory_root/portable-user-config"
snapshot="$portable_target/home-snapshot"
backup="$factory_root/pre-activation-user-config-20260722"
partial="$factory_root/partial-activation-user-config-20260722"
receipt_root="$giga_target/migration/receipts"

for receipt in comparison-agentic-orchestrator.json comparison-giga-user.json; do
  path="$receipt_root/$receipt"
  [[ -f "$path" ]] || { echo "Missing comparison receipt: $path" >&2; exit 2; }
  python3 - "$path" <<'PY'
import json
import sys
receipt = json.load(open(sys.argv[1], encoding="utf-8"))
if receipt.get("schema") != "giga.factory-tree-comparison.v1" or receipt.get("passed") is not True:
    raise SystemExit(f"Comparison receipt is not a pass: {sys.argv[1]}")
PY
done

[[ -f "$agentic_target/projects/orchestrator-v3/STOP" ]] || {
  echo "STOP is not armed in canonical orchestrator" >&2
  exit 3
}
if pgrep -af 'control\.factory|run_forever\.sh|factory_launch' >/dev/null; then
  echo "Factory-like process is running; refusing control-layer activation" >&2
  exit 4
fi
[[ -d "$snapshot" && -d "$backup" ]] || {
  echo "Portable snapshot or pre-activation backup is missing" >&2
  exit 5
}
[[ ! -e "$partial" ]] || {
  echo "Partial-activation preservation path already exists: $partial" >&2
  exit 6
}

mkdir -p "$partial/.codex" "$partial/.agents" "$partial/.claude"

activate_tree() {
  local relative="$1"
  local source="$snapshot/$relative"
  local active="/home/gutua/$relative"
  local preserved="$partial/$relative"
  [[ -d "$source" ]] || { echo "Snapshot tree missing: $source" >&2; exit 7; }
  mkdir -p "$(dirname "$preserved")"
  if [[ -e "$active" || -L "$active" ]]; then
    mv "$active" "$preserved"
  fi
  mkdir -p "$active"
  rsync -a --delete "$source/" "$active/"
}

activate_tree .codex/skills
activate_tree .codex/rules
activate_tree .agents/skills
activate_tree .claude/skills
activate_tree .graphify

# Preserve the one WSL-only skill discovered during the pre-activation comparison.
if [[ ! -e /home/gutua/.codex/skills/librarian \
      && -d "$backup/.codex/skills/librarian" ]]; then
  cp -a "$backup/.codex/skills/librarian" /home/gutua/.codex/skills/librarian
fi

for relative in .codex/AGENTS.md .claude/CLAUDE.md; do
  source="$snapshot/$relative"
  active="/home/gutua/$relative"
  preserved="$partial/$relative"
  [[ -f "$source" ]] || { echo "Snapshot file missing: $source" >&2; exit 8; }
  mkdir -p "$(dirname "$preserved")" "$(dirname "$active")"
  if [[ -e "$active" || -L "$active" ]]; then
    mv "$active" "$preserved"
  fi
  cp -a "$source" "$active"
done

echo "Portable control layer activated after recoverable collision handling."
echo "Pre-existing WSL config: $backup"
echo "Partially activated intermediate state: $partial"
echo "STOP remains armed; no factory process was launched."
