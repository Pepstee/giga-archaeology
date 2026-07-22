#!/usr/bin/env bash
set -euo pipefail

destination=${1:-"$PWD/gutua-market-aligner-backup"}
host=${GUTUA_SSH_HOST:-gutua@100.80.113.74}
key=${GUTUA_SSH_KEY:-$HOME/.ssh/giga_uk_transfer_ed25519}
remote_base=/home/gutua/giga

snapshot=$(ssh -i "$key" -o IdentitiesOnly=yes -o BatchMode=yes "$host" \
  "wsl -d Ubuntu -- $remote_base/bin/backup_databases.py --source $remote_base/shared/market-aligner --destination $remote_base/backups/manual --keep 30")
mkdir -p "$destination"
rsync -az --rsync-path='wsl -d Ubuntu -- rsync' \
  -e "ssh -i $key -o IdentitiesOnly=yes -o BatchMode=yes" \
  "$host:$snapshot/" "$destination/$(basename "$snapshot")/"
printf '%s\n' "$destination/$(basename "$snapshot")"
