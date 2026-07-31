#!/usr/bin/env bash
set -euo pipefail

factory_root=/home/gutua/software-factory
source_root="$factory_root/giga-user/deploy/gutua/dual_lane_20260726"
control_root="$factory_root/.control/native-dual-lane-20260726"
unit_root="$HOME/.config/systemd/user"

mkdir -p "$control_root"/{bin,jaa,dfi} "$unit_root"
chmod 700 "$control_root" "$control_root"/{bin,jaa,dfi}
chmod 755 \
  "$source_root/preflight_dual_lane.sh" \
  "$source_root/run_native_lane.sh"

install -m 755 \
  "$factory_root/giga-user/deploy/gutua/run_claude_serialized.sh" \
  "$control_root/bin/claude"
install -m 644 \
  "$source_root/systemd/giga-jaa-native.service" \
  "$unit_root/giga-jaa-native.service"
install -m 644 \
  "$source_root/systemd/giga-dfi-native.service" \
  "$unit_root/giga-dfi-native.service"

systemctl --user daemon-reload
systemctl --user enable giga-jaa-native.service giga-dfi-native.service
echo "INSTALL_OK"

