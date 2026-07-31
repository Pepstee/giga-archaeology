#!/usr/bin/env bash
set -euo pipefail

factory_root="${1:-/home/gutua/software-factory}"
incoming_root="$factory_root/.verified-incoming-20260722"
agentic_target="$factory_root/agentic-orchestrator"
giga_target="$factory_root/giga-user"
portable_target="$factory_root/portable-user-config"
receipt_root="$incoming_root/giga-user/migration/receipts"

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

[[ -f "$incoming_root/agentic-orchestrator/projects/orchestrator-v3/STOP" ]] || {
  echo "STOP is not armed in incoming orchestrator" >&2
  exit 3
}
if pgrep -af 'control\.factory|run_forever\.sh|factory_launch' >/dev/null; then
  echo "Factory-like process is running; refusing activation" >&2
  pgrep -af 'control\.factory|run_forever\.sh|factory_launch' >&2 || true
  exit 4
fi

for target in "$agentic_target" "$giga_target" "$portable_target"; do
  [[ ! -e "$target" ]] || { echo "Refusing to overwrite existing target: $target" >&2; exit 5; }
done

mv "$incoming_root/agentic-orchestrator" "$agentic_target"
mv "$incoming_root/giga-user" "$giga_target"
mv "$incoming_root/portable-user-config" "$portable_target"

backup="$factory_root/pre-activation-user-config-20260722"
mkdir -p "$backup/.codex" "$backup/.agents" "$backup/.claude"

for relative in .codex/AGENTS.md .codex/config.toml .claude/CLAUDE.md; do
  current="/home/gutua/$relative"
  if [[ -e "$current" ]]; then
    mkdir -p "$backup/$(dirname "$relative")"
    cp -a "$current" "$backup/$relative"
  fi
done
for relative in .codex/skills .codex/rules .agents/skills .claude/skills .graphify; do
  current="/home/gutua/$relative"
  if [[ -e "$current" ]]; then
    mkdir -p "$backup/$(dirname "$relative")"
    cp -a "$current" "$backup/$relative"
  fi
done

bash "$giga_target/migration/resume_gigabyte_control_layer.sh" "$factory_root"

# The Mac config and plugin trees are preserved but intentionally not activated wholesale on Linux.
# They contain useful provenance plus platform-specific paths/binaries. Linux-native configuration
# and provider authentication remain the WSL machine's responsibility.

echo "Gigabyte factory paths activated."
echo "STOP remains armed; no factory process was launched."
echo "Portable skills/rules are active. Original WSL user config backup: $backup"
