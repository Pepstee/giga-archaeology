#!/usr/bin/env bash
set -euo pipefail

source_root=/home/gutua/software-factory/.control/transitvpn-v3-full-codex-20260820
target_root=/home/gutua/software-factory/.control/transitvpn-v3-full-codex-r2-20260820
source_project="$source_root/projects/transitvpn"
target_project="$target_root/projects/transitvpn"
seed=/mnt/c/Users/gutua/transitvpn_v3_seed_20260820.json
expected_source=c714d01
expected_project=5a9839c17ad417305838733cb824816881e0a3d5

if [[ -e "$target_root" ]]; then
  printf 'REFUSED: fresh target already exists: %s\n' "$target_root" >&2
  exit 20
fi
if [[ ! -f "$seed" ]]; then
  printf 'REFUSED: task seed missing: %s\n' "$seed" >&2
  exit 21
fi
if [[ -n "$(git -C "$source_root" status --porcelain)" ]]; then
  printf 'REFUSED: source candidate is dirty\n' >&2
  exit 22
fi
if [[ "$(git -C "$source_root" rev-parse --short HEAD)" != "$expected_source" ]]; then
  printf 'REFUSED: source candidate HEAD is not %s\n' "$expected_source" >&2
  exit 23
fi
if [[ -n "$(git -C "$source_project" status --porcelain)" ]]; then
  printf 'REFUSED: TransitVPN source project is dirty\n' >&2
  exit 24
fi
if [[ "$(git -C "$source_project" rev-parse HEAD)" != "$expected_project" ]]; then
  printf 'REFUSED: TransitVPN project HEAD mismatch\n' >&2
  exit 25
fi

git clone --quiet --no-hardlinks "$source_root" "$target_root"
git clone --quiet --no-hardlinks "$source_project" "$target_project"
mkdir -p "$target_root/state/inbox"
install -m 600 "$seed" "$target_root/state/inbox/transitvpn-beijing-readiness-20260820-r2.json"

cd "$target_root"
python3 -m dispatch.isolation certify --root "$target_root"
python3 -c \
  'from pathlib import Path; from control.self_test import run_boot_self_test; ok, detail = run_boot_self_test(Path.cwd()); print(detail); raise SystemExit(0 if ok else 1)'

printf 'PREPARED root=%s source_head=%s project_head=%s\n' \
  "$target_root" \
  "$(git rev-parse HEAD)" \
  "$(git -C "$target_project" rev-parse HEAD)"
