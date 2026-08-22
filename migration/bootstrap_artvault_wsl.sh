#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "bootstrap_artvault_wsl.sh must run as root" >&2
  exit 1
fi

entity_user="art"
entity_home="/home/${entity_user}"
marker="/var/lib/artvault/bootstrap-v1.complete"
node_release="v22.23.2"
claude_code_version="2.1.237"
codex_cli_version="0.148.0"
operator_public_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMp0m0M3CMVGujPXp3L9eIKQV2h2Zv7qSIF3gygWr8Dm artvault-gigabyte-20260820"

install -d -m 0755 /var/lib/artvault

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  git \
  gnupg \
  jq \
  openssh-server \
  sudo \
  unzip \
  xz-utils

node_arch="$(dpkg --print-architecture)"
case "${node_arch}" in
  amd64) node_arch="x64" ;;
  arm64) node_arch="arm64" ;;
  *)
    echo "Unsupported Node.js architecture: ${node_arch}" >&2
    exit 1
    ;;
esac

node_tmp="$(mktemp -d)"
trap 'rm -rf "${node_tmp}"' EXIT
curl --fail --silent --show-error --location \
  --output "${node_tmp}/SHASUMS256.txt" \
  "https://nodejs.org/dist/${node_release}/SHASUMS256.txt"
curl --fail --silent --show-error --location \
  --output "${node_tmp}/node.tar.xz" \
  "https://nodejs.org/dist/${node_release}/node-${node_release}-linux-${node_arch}.tar.xz"
(
  cd "${node_tmp}"
  grep "  node-${node_release}-linux-${node_arch}\\.tar\\.xz$" SHASUMS256.txt \
    | sed 's#  .*#  node.tar.xz#' \
    | sha256sum --check --status
)
tar --extract --file="${node_tmp}/node.tar.xz" --directory=/usr/local \
  --strip-components=1
rm -rf "${node_tmp}"
trap - EXIT

if ! id "${entity_user}" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "${entity_user}"
fi

usermod --append --groups sudo "${entity_user}"
passwd --lock "${entity_user}" >/dev/null

install -d -o "${entity_user}" -g "${entity_user}" -m 0700 "${entity_home}/.ssh"
install -d -o "${entity_user}" -g "${entity_user}" -m 0700 "${entity_home}/.config"
install -d -o "${entity_user}" -g "${entity_user}" -m 0700 "${entity_home}/.local"
install -d -o "${entity_user}" -g "${entity_user}" -m 0700 "${entity_home}/.claude"
install -d -o "${entity_user}" -g "${entity_user}" -m 0700 "${entity_home}/.codex"
install -d -o "${entity_user}" -g "${entity_user}" -m 0750 /srv/artvault
printf '%s\n' "${operator_public_key}" > "${entity_home}/.ssh/authorized_keys"
chown "${entity_user}:${entity_user}" "${entity_home}/.ssh/authorized_keys"
chmod 0600 "${entity_home}/.ssh/authorized_keys"

cat > /etc/wsl.conf <<'EOF'
[boot]
systemd=true

[automount]
enabled=false
mountFsTab=false

[interop]
enabled=false
appendWindowsPath=false

[network]
hostname=artvault
generateHosts=true

[user]
default=art
EOF

install -d -m 0755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/50-artvault.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
AllowUsers art
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
AllowStreamLocalForwarding no
PermitTunnel no
DisableForwarding yes
MaxAuthTries 3
EOF

ssh-keygen -A
systemctl enable ssh.service
systemctl restart ssh.service

install -d -m 0755 /usr/share/keyrings
curl --fail --silent --show-error --location \
  --output /usr/share/keyrings/tailscale-archive-keyring.gpg \
  https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg
curl --fail --silent --show-error --location \
  --output /etc/apt/sources.list.d/tailscale.list \
  https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list
chmod 0644 \
  /usr/share/keyrings/tailscale-archive-keyring.gpg \
  /etc/apt/sources.list.d/tailscale.list
apt-get update
apt-get install -y --no-install-recommends tailscale
systemctl enable tailscaled.service
systemctl start tailscaled.service

runuser --user "${entity_user}" -- env \
  HOME="${entity_home}" \
  CLAUDE_CODE_VERSION="${claude_code_version}" \
  CODEX_CLI_VERSION="${codex_cli_version}" \
  bash -lc '
  set -euo pipefail
  cd "$HOME"
  npm config set prefix "$HOME/.local"
  npm install --global "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"

  installer="$(mktemp)"
  trap '\''rm -f "$installer"'\'' EXIT
  curl --fail --silent --show-error --location \
    --output "$installer" \
    https://chatgpt.com/codex/install.sh
  CODEX_NON_INTERACTIVE=1 CODEX_RELEASE="${CODEX_CLI_VERSION}" \
    bash "$installer" </dev/null
'

cat > /etc/sudoers.d/90-artvault-operator <<'EOF'
art ALL=(ALL:ALL) NOPASSWD: ALL
EOF
chmod 0440 /etc/sudoers.d/90-artvault-operator
visudo --check --file=/etc/sudoers.d/90-artvault-operator

sshd -t
sshd_effective="$(sshd -T)"
for required_ssh_setting in \
  'permitrootlogin no' \
  'pubkeyauthentication yes' \
  'passwordauthentication no' \
  'kbdinteractiveauthentication no' \
  'x11forwarding no' \
  'allowagentforwarding no' \
  'allowtcpforwarding no' \
  'allowstreamlocalforwarding no' \
  'permittunnel no' \
  'disableforwarding yes' \
  'maxauthtries 3' \
  'allowusers art'; do
  if ! grep --fixed-strings --line-regexp --quiet \
    "${required_ssh_setting}" <<< "${sshd_effective}"; then
    echo "Missing effective SSH setting: ${required_ssh_setting}" >&2
    exit 1
  fi
done

if findmnt --noheadings --raw /mnt/c >/dev/null 2>&1; then
  echo 'Windows C: is mounted despite the ArtVault isolation policy' >&2
  exit 1
fi
if command -v cmd.exe >/dev/null 2>&1; then
  echo 'Windows interoperability is active despite the ArtVault isolation policy' >&2
  exit 1
fi
if printenv WSL_INTEROP >/dev/null 2>&1; then
  echo 'WSL_INTEROP is present in the ArtVault environment despite the isolation policy' >&2
  exit 1
fi
if [[ "$(stat --format='%a:%U:%G' "${entity_home}/.ssh")" != '700:art:art' ]] ||
   [[ "$(stat --format='%a:%U:%G' "${entity_home}/.ssh/authorized_keys")" != '600:art:art' ]] ||
   [[ "$(stat --format='%a:%U:%G' "${entity_home}/.claude")" != '700:art:art' ]] ||
   [[ "$(stat --format='%a:%U:%G' "${entity_home}/.codex")" != '700:art:art' ]]; then
  echo 'ArtVault credential directory ownership or mode assertion failed' >&2
  exit 1
fi
systemctl is-enabled --quiet ssh.service
systemctl is-active --quiet ssh.service
systemctl is-enabled --quiet tailscaled.service
systemctl is-active --quiet tailscaled.service

operator_key_fingerprint="$(ssh-keygen -lf "${entity_home}/.ssh/authorized_keys" \
  | awk '{print $2}')"

{
  printf 'schema=artvault.bootstrap.v1\n'
  printf 'completed_at=%s\n' "$(date --utc +%Y-%m-%dT%H:%M:%SZ)"
  printf 'os=%s\n' "$(. /etc/os-release && printf '%s' "${PRETTY_NAME}")"
  printf 'user=%s\n' "${entity_user}"
  printf 'windows_automount=disabled\n'
  printf 'windows_interop=disabled\n'
  printf 'ssh_password_auth=disabled\n'
  printf 'ssh_forwarding=disabled\n'
  printf 'operator_key_fingerprint=%s\n' "${operator_key_fingerprint}"
  printf 'tailscale_version=%s\n' "$(tailscale version | head -n 1)"
  printf 'node_version=%s\n' "$(node --version)"
  printf 'claude_version=%s\n' "$(runuser --user "${entity_user}" -- env HOME="${entity_home}" "${entity_home}/.local/bin/claude" --version)"
  printf 'codex_version=%s\n' "$(runuser --user "${entity_user}" -- env HOME="${entity_home}" "${entity_home}/.local/bin/codex" --version)"
} > "${marker}"
chmod 0644 "${marker}"

echo "ArtVault bootstrap complete"
