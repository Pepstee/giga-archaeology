#!/bin/bash

set -euo pipefail

readonly ARTVAULT_HOST='100.101.96.58'
readonly ARTVAULT_USER='art'
readonly ARTVAULT_IDENTITY="${HOME}/.ssh/artvault_ed25519"
readonly ARTVAULT_KNOWN_HOSTS="${HOME}/.ssh/artvault_known_hosts"
readonly ARTVAULT_REMOTE_DIR='/srv/artvault'
readonly ARTVAULT_CODEX='/home/art/.local/bin/codex'
readonly ARTVAULT_EXPECTED_KEY_FINGERPRINT='SHA256:tXXvFap3rm4Vzz4FoWL7Xvi/1rfjtTmUhjCUOPLfKhw'
readonly ARTVAULT_EXPECTED_HOST_FINGERPRINT='SHA256:XklGmndKV8Jb43zx3P96XZEvkuvlDAvBSTFdsfipUfA'

usage() {
  printf '%s\n' \
    'Usage: ArtVault Codex.command [--check]' \
    '' \
    'Without arguments, opens the interactive Codex terminal inside ArtVault.' \
    '--check verifies the secure connection and Codex login without opening the UI.'
}

fail() {
  printf 'ArtVault Codex: %s\n' "$1" >&2
  exit 1
}

preflight() {
  command -v ssh >/dev/null 2>&1 || fail 'the Mac SSH client is unavailable.'
  command -v ssh-keygen >/dev/null 2>&1 || fail 'ssh-keygen is unavailable.'
  [[ -r "${ARTVAULT_IDENTITY}" ]] || fail "missing private key: ${ARTVAULT_IDENTITY}"
  [[ -r "${ARTVAULT_IDENTITY}.pub" ]] || fail "missing public key: ${ARTVAULT_IDENTITY}.pub"
  [[ -r "${ARTVAULT_KNOWN_HOSTS}" ]] || fail "missing pinned host key: ${ARTVAULT_KNOWN_HOSTS}"
  [[ "$(stat -f '%Lp' "${ARTVAULT_IDENTITY}")" == '600' ]] || \
    fail 'the ArtVault private key must have mode 0600.'
  [[ "$(stat -f '%Lp' "${ARTVAULT_KNOWN_HOSTS}")" == '600' ]] || \
    fail 'the ArtVault host-key file must have mode 0600.'

  local actual_fingerprint host_key_line actual_host_fingerprint
  actual_fingerprint="$(ssh-keygen -lf "${ARTVAULT_IDENTITY}.pub" | awk '{print $2}')"
  [[ "${actual_fingerprint}" == "${ARTVAULT_EXPECTED_KEY_FINGERPRINT}" ]] || \
    fail 'the ArtVault identity fingerprint does not match the installed launcher.'

  ssh-keygen -F "${ARTVAULT_HOST}" -f "${ARTVAULT_KNOWN_HOSTS}" >/dev/null 2>&1 || \
    fail 'the pinned ArtVault host key is missing.'
  host_key_line="$(awk -v host="${ARTVAULT_HOST}" \
    '$1 == host && $2 == "ssh-ed25519" { print $2 " " $3; exit }' \
    "${ARTVAULT_KNOWN_HOSTS}")"
  [[ -n "${host_key_line}" ]] || fail 'the pinned ArtVault Ed25519 host key is missing.'
  actual_host_fingerprint="$(printf '%s\n' "${host_key_line}" | ssh-keygen -lf - | awk '{print $2}')"
  [[ "${actual_host_fingerprint}" == "${ARTVAULT_EXPECTED_HOST_FINGERPRINT}" ]] || \
    fail 'the ArtVault server fingerprint does not match the installed launcher.'
}

ssh_artvault() {
  local tty_mode="$1"
  shift
  ssh \
    "${tty_mode}" \
    -i "${ARTVAULT_IDENTITY}" \
    -o BatchMode=yes \
    -o IdentitiesOnly=yes \
    -o PreferredAuthentications=publickey \
    -o PasswordAuthentication=no \
    -o KbdInteractiveAuthentication=no \
    -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile="${ARTVAULT_KNOWN_HOSTS}" \
    -o GlobalKnownHostsFile=/dev/null \
    -o HostKeyAlgorithms=ssh-ed25519 \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -o ForwardAgent=no \
    -o ClearAllForwardings=yes \
    -o ControlMaster=no \
    -o ControlPath=none \
    "${ARTVAULT_USER}@${ARTVAULT_HOST}" \
    "$@"
}

check_connection() {
  local result
  result="$(ssh_artvault -T \
    "test \"\$(id -u)\" = 1000 && test \"\$(hostname)\" = artvault && test -x '${ARTVAULT_CODEX}' && cd '${ARTVAULT_REMOTE_DIR}' && '${ARTVAULT_CODEX}' login status && printf '\\nARTVAULT_CODEX_READY\\n'" \
    2>&1)"

  [[ "${result}" == *'Logged in using ChatGPT'* ]] || fail 'Codex is not logged in inside ArtVault.'
  [[ "${result}" == *'ARTVAULT_CODEX_READY'* ]] || fail 'the ArtVault readiness check failed.'
  printf '%s\n' 'ArtVault Codex is ready.'
}

main() {
  case "${1:-}" in
    '') ;;
    --check)
      [[ "$#" -eq 1 ]] || { usage >&2; exit 2; }
      preflight
      check_connection
      return
      ;;
    -h|--help)
      usage
      return
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac

  preflight
  [[ -t 0 && -t 1 ]] || fail 'open this launcher in Terminal, or double-click it in Finder.'

  printf '\033]0;ArtVault Codex\007'
  printf '%s\n' \
    'ArtVault Codex' \
    'Connected directly over Tailscale. Files and credentials stay inside ArtVault.' \
    'Press Ctrl+C twice to leave.' \
    ''

  ssh_artvault -tt \
    "cd '${ARTVAULT_REMOTE_DIR}' && exec '${ARTVAULT_CODEX}'"
}

main "$@"
