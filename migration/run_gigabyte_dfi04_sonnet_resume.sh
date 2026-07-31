#!/usr/bin/env bash
set -euo pipefail

factory_root="/home/gutua/software-factory"
worktree="$factory_root/.worktrees/orchestrator-v3-dfi-04"
production="$factory_root/agentic-orchestrator/projects/orchestrator-v3"
prompt_path="$factory_root/giga-user/migration/GIGABYTE_DFI04_SONNET_RESUME_ORDER_2026-07-23.md"

[[ -f "$production/STOP" ]] || {
  echo "Refusing DFI-04 resume: production STOP is not armed." >&2
  exit 2
}
[[ "$(git -C "$production" rev-parse HEAD)" == \
   "35efb19b07867bb58e1288479513078cf9ab65e4" ]] || {
  echo "Refusing DFI-04 resume: production identity drifted." >&2
  exit 3
}
[[ "$(git -C "$worktree" rev-parse HEAD^{tree})" == \
   "3ce0646f0254b45726860345e470c037a0e869fa" ]] || {
  echo "Refusing DFI-04 resume: isolated worktree baseline drifted." >&2
  exit 4
}
[[ -f "$prompt_path" ]] || {
  echo "Refusing DFI-04 resume: work order is missing." >&2
  exit 5
}

cd "$worktree"
exec claude -p \
  --model sonnet \
  --effort medium \
  --permission-mode auto \
  --name dfi04-gigabyte-resume \
  "$(cat "$prompt_path")"
