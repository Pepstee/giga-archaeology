#!/usr/bin/env bash
set -euo pipefail

factory_root="${1:-/home/gutua/software-factory}"
archive_root="$factory_root/.archives-20260722"
incoming_root="$factory_root/.verified-incoming-20260722"

if [[ -e "$incoming_root" ]]; then
  echo "Refusing to overwrite existing verified incoming path: $incoming_root" >&2
  exit 2
fi

declare -A expected=(
  [agentic-orchestrator-20260722.tar.zst]=a69336ada7915d68d6aff3f3dd9f47b8399fcd36a8aed8851f5d1e72661ae3a9
  [giga-user-no-exports-20260722.tar.zst]=3e08f0f70783123eac8a513e45d00fee2ccca8b92a7cfdc59387b54154aeb893
  [factory-user-control-layer-20260722.tar.zst]=122bb1697d4057666f5e81627e937507434c75273990dd3c97cb59a88e84153a
  [factory-graphify-repos-20260722.tar.zst]=f7ed88d3cc83294d85e1ced8da481140d24677b695bdaa8d5adce999989dcc61
)

for name in "${!expected[@]}"; do
  path="$archive_root/$name"
  [[ -f "$path" ]] || { echo "Missing archive: $path" >&2; exit 3; }
  actual="$(sha256sum "$path" | awk '{print $1}')"
  [[ "$actual" == "${expected[$name]}" ]] || {
    echo "Archive hash mismatch: $name" >&2
    exit 4
  }
done

mkdir -p "$incoming_root" "$incoming_root/portable-user-config/home-snapshot"
zstd --long=30 -q -dc "$archive_root/agentic-orchestrator-20260722.tar.zst" \
  | tar -xf - -C "$incoming_root"
zstd --long=29 -q -dc "$archive_root/giga-user-no-exports-20260722.tar.zst" \
  | tar -xf - -C "$incoming_root"
zstd -q -dc "$archive_root/factory-user-control-layer-20260722.tar.zst" \
  | tar -xf - -C "$incoming_root/portable-user-config/home-snapshot"
zstd --long=28 -q -dc "$archive_root/factory-graphify-repos-20260722.tar.zst" \
  | tar -xf - -C "$incoming_root/portable-user-config/home-snapshot"

required=(
  "$incoming_root/agentic-orchestrator/projects/orchestrator-v3/STOP"
  "$incoming_root/agentic-orchestrator/projects/orchestrator-v3/dispatch/isolation.py"
  "$incoming_root/agentic-orchestrator/projects/orchestrator-v3/dispatch/runner.py"
  "$incoming_root/agentic-orchestrator/projects/orchestrator-v3/tests/test_container_runner_integration.py"
  "$incoming_root/agentic-orchestrator/projects/orchestrator-v3/tests/test_linux_isolation_certification.py"
  "$incoming_root/agentic-orchestrator/projects/orchestrator-v3/projects/job-application-automation/.git/HEAD"
  "$incoming_root/giga-user/00_MASTER.md"
  "$incoming_root/giga-user/CHARTER.md"
  "$incoming_root/giga-user/graphify-out/graph.json"
  "$incoming_root/giga-user/migration/GIGABYTE_FACTORY_HANDOFF_2026-07-22.md"
  "$incoming_root/portable-user-config/home-snapshot/.codex/skills/skill-router/SKILL.md"
  "$incoming_root/portable-user-config/home-snapshot/.agents/skills/graphify/SKILL.md"
  "$incoming_root/portable-user-config/home-snapshot/.graphify/repos"
)
for path in "${required[@]}"; do
  [[ -e "$path" ]] || { echo "Required extracted path missing: $path" >&2; exit 5; }
done

banned=(
  "$incoming_root/giga-user/corpus"
  "$incoming_root/giga-user/package.zip"
  "$incoming_root/giga-user/instagram-artiom.png-2026-07-16-58GCGdnZ.zip"
  "$incoming_root/giga-user/1916b63abd801fbb5abf9b44f98d87a68ccd5db992b2a4d30567dd8a4ed29a85-2026-07-19-08-37-41-df72519dd898472489071b0441745ac3.zip"
)
for path in "${banned[@]}"; do
  [[ ! -e "$path" ]] || { echo "Excluded export unexpectedly present: $path" >&2; exit 6; }
done

expected_stop='JAA-01 controlled certification window; factory must remain stopped.'
actual_stop="$(cat "$incoming_root/agentic-orchestrator/projects/orchestrator-v3/STOP")"
[[ "$actual_stop" == "$expected_stop" ]] || {
  echo "STOP content mismatch" >&2
  exit 7
}

echo "Archives verified and extracted to $incoming_root"
echo "STOP remains armed. Canonical factory paths have not been activated."
