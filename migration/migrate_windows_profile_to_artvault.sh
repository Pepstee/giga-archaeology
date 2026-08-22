#!/usr/bin/env bash

# Run this script as root inside ArtVault. Plan, stage, and verify temporarily
# mount Windows C: read-only. Cutover uses an explicitly gated read-write mount
# to remove only manifest-bound files after complete destination and source
# preflights. Every mode restores the normal no-Windows-mount state on exit.

set -euo pipefail

mode="${1:-}"
manifest_confirmation="${2:-}"
source_mount='/mnt/windows-source'
source_profile="${source_mount}/Users/gutua"
migration_root='/srv/artvault/migrations/windows-gutua-20260821'
destination_profile="${migration_root}/profile"
receipt_root="${migration_root}/receipts"
temporary_changes=''
temporary_file_list=''

usage() {
  printf '%s\n' \
    'Usage: migrate_windows_profile_to_artvault.sh plan|stage|verify' \
    '       migrate_windows_profile_to_artvault.sh cutover-check MANIFEST_SHA256' \
    '       migrate_windows_profile_to_artvault.sh cutover MANIFEST_SHA256' \
    '       migrate_windows_profile_to_artvault.sh resume-cutover RESIDUAL_RECEIPT_SHA256' \
    '       migrate_windows_profile_to_artvault.sh prepare-host-cutover RESIDUAL_RECEIPT_SHA256' \
    '' \
    'plan    Report the included file count and byte total without transfer.' \
    'stage   Transfer/update included files before the removal cutover.' \
    'verify  Byte-compare source and destination without changing either.' \
    'cutover-check  Run every cutover preflight with a read-only source.' \
    'cutover Reverify both sides, then delete only manifest-bound source files.' \
    'resume-cutover Retry only an exact, digest-bound cutover residual receipt.' \
    'prepare-host-cutover Capture changed residuals and emit an exact host deletion plan.'
}

fail() {
  printf 'Windows-to-ArtVault migration: %s\n' "$1" >&2
  exit 1
}

cleanup() {
  local cleanup_status=0

  if findmnt -rn "${source_mount}" >/dev/null 2>&1; then
    umount "${source_mount}" || cleanup_status=1
  fi

  if [[ -d /mnt/c ]] && ! findmnt -rn /mnt/c >/dev/null 2>&1; then
    if [[ -z "$(find /mnt/c -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
      rmdir /mnt/c || cleanup_status=1
    fi
  fi

  if [[ -d "${source_mount}" ]] && \
     [[ -z "$(find "${source_mount}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    rmdir "${source_mount}" || cleanup_status=1
  fi

  if [[ -n "${temporary_changes}" && -f "${temporary_changes}" ]]; then
    rm -f -- "${temporary_changes}" || cleanup_status=1
  fi

  if [[ -n "${temporary_file_list}" && -f "${temporary_file_list}" ]]; then
    rm -f -- "${temporary_file_list}" || cleanup_status=1
  fi

  if (( cleanup_status != 0 )); then
    printf '%s\n' 'WARNING: temporary mount cleanup was incomplete.' >&2
  fi
}

mount_source() {
  local access_mode="$1"
  [[ "${access_mode}" == 'ro' || "${access_mode}" == 'rw' ]] || \
    fail "invalid source-mount access mode: ${access_mode}"
  mkdir -p "${source_mount}"
  mount -t drvfs 'C:' "${source_mount}" \
    -o "${access_mode},metadata,uid=0,gid=0,umask=077"

  local options
  options="$(findmnt -rn -o OPTIONS "${source_mount}")"
  [[ ",${options}," == *,"${access_mode}",* ]] || \
    fail "the Windows source mount is not ${access_mode}."
  [[ -d "${source_profile}" ]] || fail "source profile is missing: ${source_profile}"
}

rsync_common=(
  --recursive
  --links
  --times
  --omit-dir-times
  --hard-links
  --safe-links
  --no-perms
  --no-owner
  --no-group
  --chown=art:art
  --chmod=Du=rwx,Dgo=,Fu=rw,Fgo=
  --exclude='/.cache/***'
  --exclude='/Application Data'
  --exclude='/Cookies'
  --exclude='/Local Settings'
  --exclude='/My Documents'
  --exclude='/NetHood'
  --exclude='/PrintHood'
  --exclude='/Recent'
  --exclude='/SendTo'
  --exclude='/Start Menu'
  --exclude='/Templates'
  --exclude='/NTUSER.DAT*'
  --exclude='/ntuser.dat*'
  --exclude='/AppData/Local/Application Data'
  --exclude='/AppData/Local/History'
  --exclude='/AppData/Local/Temporary Internet Files'
  --exclude='/AppData/Local/D3DSCache/***'
  --exclude='/AppData/Local/NVIDIA/***'
  --exclude='/AppData/Local/Package Cache/***'
  --exclude='/AppData/Local/pip/***'
  --exclude='/AppData/Local/Temp/***'
  --exclude='/AppData/Local/wsl/***'
  --exclude='/AppData/Local/Microsoft/Windows/UsrClass.dat*'
  --exclude='/AppData/Local/Microsoft/Windows/INetCache/***'
  --exclude='/AppData/Local/Microsoft/Windows/Caches/***'
  --exclude='/AppData/Local/Microsoft/Windows/Explorer/iconcache*.db'
  --exclude='/AppData/Local/Microsoft/Windows/PowerShell/StartupProfileData-*'
  --exclude='/AppData/LocalLow/Microsoft/CryptnetUrlCache/***'
  --exclude='/AppData/Local/Microsoft/Windows/Notifications/*.tmp'
  --exclude='/AppData/Local/Microsoft/Windows/WebCache/***'
  --exclude='/AppData/Local/Microsoft/Windows/WebCacheLock.dat'
  --exclude='/AppData/Local/Comms/UnistoreDB/***'
  --exclude='/AppData/Local/Microsoft/OneDrive/logs/***'
  --exclude='/AppData/Local/Microsoft/OneDrive/**/logUploaderSettings*.ini'
  --exclude='/AppData/Local/Microsoft/Windows Terminal/Fragments/Microsoft.WSL/***'
  --exclude='/AppData/Local/Packages/*/Settings/settings.dat*'
  --exclude='/AppData/Local/Packages/*/SystemAppData/Helium/*.dat*'
  --exclude='/**/*.db-shm'
  --exclude='/**/*.db-wal'
  --exclude='/**/*-shm'
  --exclude='/**/*-wal'
  --exclude='/.codex/logs_2.sqlite*'
  --exclude='/.codex/models_cache.json'
  --exclude='/**/BrowserMetrics/***'
  --exclude='/**/Cache/***'
  --exclude='/**/Code Cache/***'
  --exclude='/**/CryptnetUrlCache/***'
  --exclude='/**/Network/Cookies*'
  --exclude='/**/Network/Reporting and NEL*'
  --exclude='/**/Network/Network Persistent State'
  --exclude='/**/Network/TransportSecurity'
  --exclude='/**/Local Storage/leveldb/***'
  --exclude='/**/LOCK'
  --exclude='/**/Safe Browsing Cookies*'
  --exclude='/**/shared_proto_db/***'
  --exclude='/**/Sessions/Session_*'
  --exclude='/**/Sessions/Tabs_*'
  --exclude='/**/DawnWebGPUCache/***'
  --exclude='/**/GPUCache/***'
  --exclude='/**/GrShaderCache/***'
  --exclude='/**/ShaderCache/***'
  --exclude='/**/DawnGraphiteCache/***'
  --exclude='/**/GPUPersistentCache/***'
  --exclude='/**/sentry/***'
  --exclude='/AppData/Local/Packages/OpenAI.Codex_*/LocalCache/Local/Codex/Logs/***'
  --exclude='/AppData/Local/Packages/Claude_*/LocalCache/Roaming/Claude/vm_bundles/***'
  --exclude='/AppData/Local/Packages/Microsoft.Windows.StartMenuExperienceHost_*/LocalState/start2.bin'
  --exclude='/**/Search/AppsIndex.db'
  --exclude='/AppData/LocalLow/9c79e790d27aefb810e91723b102b336d1eaaf385ad31eb49dde213a5ca9e75a'
  --exclude='/AppData/Roaming/Microsoft/Windows/Start Menu/Ubuntu.lnk'
  --exclude='/OneDrive/.849C9593-D756-4E56-8D6E-42412F2A707B'
)

write_scope_receipt() {
  local path="${receipt_root}/SCOPE.txt"
  {
    printf '%s\n' \
      'Windows profile migration scope v1' \
      'Source: C:\Users\gutua' \
      'Destination: /srv/artvault/migrations/windows-gutua-20260821/profile' \
      'Source is mounted read-only during plan, staging, and verification.' \
      'Included: all readable profile files except the exclusions below.' \
      'Excluded as separate WSL storage: AppData\Local\wsl' \
      'Excluded as disposable cache/temp: .cache, D3DSCache, NVIDIA, Package Cache, pip, Temp' \
      'Excluded for purge at cutover: live cookie/session/cache DBs and per-app registry hives' \
      'Excluded as Windows junctions: legacy profile compatibility links' \
      'Excluded as live Windows registry hives: NTUSER.DAT*, UsrClass.dat*' \
      'Plan, stage, and verify never delete source files; cutover is manifest-gated.'
  } > "${path}"
  chown art:art "${path}"
  chmod 0600 "${path}"
}

plan_copy() {
  rsync "${rsync_common[@]}" \
    --dry-run \
    --stats \
    "${source_profile}/" "${destination_profile}/"
}

stage_profile() {
  local timestamp stats_path error_path rsync_status
  timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
  stats_path="${receipt_root}/stage-${timestamp}.stats.txt"
  error_path="${receipt_root}/stage-${timestamp}.errors.txt"

  set +e
  rsync "${rsync_common[@]}" \
    --checksum \
    --delete \
    --delete-excluded \
    --stats \
    "${source_profile}/" "${destination_profile}/" \
    > "${stats_path}" \
    2> "${error_path}"
  rsync_status=$?
  set -e

  chown -R art:art "${destination_profile}"
  chown art:art "${stats_path}" "${error_path}"
  chmod 0600 "${stats_path}" "${error_path}"
  if (( rsync_status != 0 )); then
    fail "staging failed with rsync status ${rsync_status}; see ${error_path}"
  fi
  printf 'Staging completed. Statistics: %s\n' "${stats_path}"
}

verify_profile() {
  local timestamp changes_count manifest_path reconciled_changes unreconciled_changes
  timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
  temporary_changes="$(mktemp)"

  if find "${destination_profile}" \( ! -user art -o ! -group art \) -print -quit | grep -q .; then
    fail 'destination contains an entry not owned by art:art.'
  fi

  rsync "${rsync_common[@]}" \
    --checksum \
    --dry-run \
    --delete \
    --delete-excluded \
    --itemize-changes \
    --out-format='%i|%n%L' \
    "${source_profile}/" "${destination_profile}/" \
    > "${temporary_changes}"

  changes_count="$(wc -l < "${temporary_changes}" | tr -d ' ')"
  if [[ "${changes_count}" != '0' ]]; then
    reconciled_changes="$(mktemp)"
    unreconciled_changes="$(mktemp)"
    while IFS='|' read -r change relative_path; do
      if [[ "${change}" == '>f'* || "${change}" == '.f'* ]] && \
         [[ -f "${source_profile}/${relative_path}" ]] && \
         [[ -f "${destination_profile}/${relative_path}" ]] && \
         cmp -s -- "${source_profile}/${relative_path}" \
           "${destination_profile}/${relative_path}"; then
        printf '%s|%s\n' "${change}" "${relative_path}" >> "${reconciled_changes}"
      else
        printf '%s|%s\n' "${change}" "${relative_path}" >> "${unreconciled_changes}"
      fi
    done < "${temporary_changes}"

    if [[ -s "${reconciled_changes}" ]]; then
      install -o art -g art -m 0600 "${reconciled_changes}" \
        "${receipt_root}/verify-${timestamp}.transient-reconciled.txt"
    fi
    if [[ -s "${unreconciled_changes}" ]]; then
      changes_count="$(wc -l < "${unreconciled_changes}" | tr -d ' ')"
      install -o art -g art -m 0600 "${unreconciled_changes}" \
        "${receipt_root}/verify-${timestamp}.differences.txt"
      rm -f -- "${reconciled_changes}" "${unreconciled_changes}"
      fail "verification found ${changes_count} unreconciled source/destination differences."
    fi
    rm -f -- "${reconciled_changes}" "${unreconciled_changes}"
  fi

  manifest_path="${receipt_root}/sha256-${timestamp}.txt"
  (
    cd "${destination_profile}"
    find . -type f -print0 | sort -z | xargs -0 -r sha256sum
  ) > "${manifest_path}"
  chown art:art "${manifest_path}"
  chmod 0600 "${manifest_path}"

  printf 'Verification passed: source and destination bytes match.\n'
  printf 'Destination manifest: %s\n' "${manifest_path}"
}

cutover_profile() {
  local manifest_path actual_manifest_sha timestamp preflight_failures
  local deleted_count deleted_bytes deletion_failures expected_sha relative_path
  local source_path destination_path current_sha file_bytes receipt_path

  [[ "${manifest_confirmation}" =~ ^[0-9a-f]{64}$ ]] || \
    fail 'cutover requires the lowercase SHA-256 digest of the verified destination manifest.'

  manifest_path="$(find "${receipt_root}" -maxdepth 1 -type f \
    -name 'sha256-*.txt' -printf '%T@ %p\n' | sort -nr | sed -n '1s/^[^ ]* //p')"
  [[ -n "${manifest_path}" && -f "${manifest_path}" ]] || \
    fail 'no verified destination manifest is available for cutover.'
  actual_manifest_sha="$(sha256sum "${manifest_path}" | awk '{print $1}')"
  [[ "${actual_manifest_sha}" == "${manifest_confirmation}" ]] || \
    fail 'the supplied manifest digest does not match the latest verified manifest.'

  temporary_file_list="$(mktemp)"
  awk '
    {
      hash = $1
      sub(/^[^ ]+  /, "")
      sub(/^\.\//, "")
      if (hash !~ /^[0-9a-f]{64}$/ || $0 == "" || $0 ~ /^\// || $0 ~ /(^|\/)\.\.($|\/)/) {
        exit 2
      }
      print hash "|" $0
    }
  ' "${manifest_path}" > "${temporary_file_list}" || \
    fail 'the verified destination manifest contains an unsafe entry.'
  [[ -s "${temporary_file_list}" ]] || fail 'the verified manifest is empty.'

  # Phase 1 is non-destructive. Bind the current ArtVault bytes to the manifest,
  # then bind every current Windows source file to the same expected digest.
  (
    cd "${destination_profile}"
    sha256sum --check --status "${manifest_path}"
  ) || fail 'the ArtVault destination no longer matches its verified manifest.'

  timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
  preflight_failures="${receipt_root}/cutover-${timestamp}.preflight-failures.txt"
  : > "${preflight_failures}"
  while IFS='|' read -r expected_sha relative_path; do
    source_path="${source_profile}/${relative_path}"
    if [[ ! -f "${source_path}" ]]; then
      printf 'missing|%s\n' "${relative_path}" >> "${preflight_failures}"
      continue
    fi
    if ! current_sha="$(sha256sum "${source_path}" 2>/dev/null | awk '{print $1}')"; then
      printf 'read-failed|%s\n' "${relative_path}" >> "${preflight_failures}"
      continue
    fi
    if [[ "${current_sha}" != "${expected_sha}" ]]; then
      printf 'hash-mismatch|%s\n' "${relative_path}" >> "${preflight_failures}"
    fi
  done < "${temporary_file_list}"

  if [[ -s "${preflight_failures}" ]]; then
    chown art:art "${preflight_failures}"
    chmod 0600 "${preflight_failures}"
    fail 'cutover preflight found source files that do not match the verified manifest.'
  fi
  rm -f -- "${preflight_failures}"

  if [[ "${mode}" == 'cutover-check' ]]; then
    printf 'Cutover preflight passed for manifest %s. No source file was deleted.\n' \
      "${actual_manifest_sha}"
    return
  fi

  # Phase 2 deletes only regular files that passed the complete preflight, and
  # rechecks each file immediately before its exact path is removed.
  deleted_count=0
  deleted_bytes=0
  deletion_failures="${receipt_root}/cutover-${timestamp}.deletion-failures.txt"
  : > "${deletion_failures}"
  while IFS='|' read -r expected_sha relative_path; do
    source_path="${source_profile}/${relative_path}"
    destination_path="${destination_profile}/${relative_path}"
    if [[ ! -f "${source_path}" || ! -f "${destination_path}" ]]; then
      printf 'missing-at-delete|%s\n' "${relative_path}" >> "${deletion_failures}"
      continue
    fi
    if ! current_sha="$(sha256sum "${source_path}" 2>/dev/null | awk '{print $1}')"; then
      printf 'read-failed-at-delete|%s\n' "${relative_path}" >> "${deletion_failures}"
      continue
    fi
    if [[ "${current_sha}" != "${expected_sha}" ]]; then
      printf 'changed-at-delete|%s\n' "${relative_path}" >> "${deletion_failures}"
      continue
    fi
    if ! file_bytes="$(stat -c '%s' "${source_path}" 2>/dev/null)"; then
      printf 'stat-failed-at-delete|%s\n' "${relative_path}" >> "${deletion_failures}"
      continue
    fi
    if rm -f -- "${source_path}"; then
      deleted_count=$((deleted_count + 1))
      deleted_bytes=$((deleted_bytes + file_bytes))
    else
      printf 'remove-failed|%s\n' "${relative_path}" >> "${deletion_failures}"
    fi
  done < "${temporary_file_list}"

  receipt_path="${receipt_root}/CUTOVER-${timestamp}.txt"
  {
    printf 'schema=giga.artvault-windows-profile-cutover.v1\n'
    printf 'created_at_utc=%s\n' "${timestamp}"
    printf 'manifest_path=%s\n' "${manifest_path}"
    printf 'manifest_sha256=%s\n' "${actual_manifest_sha}"
    printf 'deleted_regular_files=%s\n' "${deleted_count}"
    printf 'deleted_regular_file_bytes=%s\n' "${deleted_bytes}"
    printf 'source_profile_retained_for_service_account=true\n'
  } > "${receipt_path}"
  chown art:art "${receipt_path}" "${deletion_failures}"
  chmod 0600 "${receipt_path}" "${deletion_failures}"

  if [[ -s "${deletion_failures}" ]]; then
    fail 'cutover was partial; exact undeleted paths are recorded in the deletion-failures receipt.'
  fi
  rm -f -- "${deletion_failures}"

  printf 'Cutover completed: deleted %s verified source files (%s bytes).\n' \
    "${deleted_count}" "${deleted_bytes}"
  printf 'Cutover receipt: %s\n' "${receipt_path}"
}

resume_cutover() {
  local residual_receipt residual_receipt_count actual_residual_sha
  local cutover_timestamp cutover_receipt manifest_path manifest_sha
  local timestamp retry_failures expected_sha relative_path reason
  local source_path destination_path source_sha destination_sha file_bytes
  local removed_count removed_bytes already_absent_count receipt_path

  [[ "${manifest_confirmation}" =~ ^[0-9a-f]{64}$ ]] || \
    fail 'resume-cutover requires the lowercase SHA-256 digest of a residual receipt.'

  residual_receipt=''
  residual_receipt_count=0
  while IFS= read -r candidate; do
    [[ -f "${candidate}" ]] || continue
    actual_residual_sha="$(sha256sum "${candidate}" | awk '{print $1}')"
    if [[ "${actual_residual_sha}" == "${manifest_confirmation}" ]]; then
      residual_receipt="${candidate}"
      residual_receipt_count=$((residual_receipt_count + 1))
    fi
  done < <(find "${receipt_root}" -maxdepth 1 -type f \
    \( -name 'cutover-*.deletion-failures.txt' \
       -o -name 'resume-cutover-*.deletion-failures.txt' \) -print | sort)
  [[ "${residual_receipt_count}" == '1' ]] || \
    fail 'the supplied digest must identify exactly one residual receipt.'

  cutover_timestamp="$(basename "${residual_receipt}")"
  cutover_timestamp="${cutover_timestamp#cutover-}"
  cutover_timestamp="${cutover_timestamp#resume-cutover-}"
  cutover_timestamp="${cutover_timestamp%.deletion-failures.txt}"
  cutover_receipt="${receipt_root}/CUTOVER-${cutover_timestamp}.txt"
  if [[ ! -f "${cutover_receipt}" ]]; then
    cutover_receipt="${receipt_root}/RESUME-CUTOVER-${cutover_timestamp}.txt"
  fi
  [[ -f "${cutover_receipt}" ]] || \
    fail 'the residual receipt has no matching cutover receipt.'

  manifest_path="$(sed -n 's/^manifest_path=//p' "${cutover_receipt}")"
  manifest_sha="$(sed -n 's/^manifest_sha256=//p' "${cutover_receipt}")"
  [[ "${manifest_path}" == "${receipt_root}/sha256-"*.txt ]] || \
    fail 'the cutover receipt references an unexpected manifest path.'
  [[ -f "${manifest_path}" && "${manifest_sha}" =~ ^[0-9a-f]{64}$ ]] || \
    fail 'the cutover receipt does not reference a valid manifest.'
  [[ "$(sha256sum "${manifest_path}" | awk '{print $1}')" == "${manifest_sha}" ]] || \
    fail 'the manifest no longer matches the digest recorded at cutover.'
  (
    cd "${destination_profile}"
    sha256sum --check --status "${manifest_path}"
  ) || fail 'the ArtVault destination no longer matches its verified manifest.'

  temporary_file_list="$(mktemp)"
  awk '
    {
      hash = $1
      sub(/^[^ ]+  /, "")
      sub(/^\.\//, "")
      if (hash !~ /^[0-9a-f]{64}$/ || $0 == "" || $0 ~ /^\// || $0 ~ /(^|\/)\.\.($|\/)/) {
        exit 2
      }
      print hash "|" $0
    }
  ' "${manifest_path}" > "${temporary_file_list}" || \
    fail 'the verified destination manifest contains an unsafe entry.'

  timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
  retry_failures="${receipt_root}/resume-cutover-${timestamp}.deletion-failures.txt"
  : > "${retry_failures}"
  removed_count=0
  removed_bytes=0
  already_absent_count=0

  while IFS='|' read -r reason relative_path; do
    reason="${reason%$'\r'}"
    relative_path="${relative_path%$'\r'}"
    case "${reason}" in
      missing-at-delete|read-failed-at-delete|changed-at-delete|stat-failed-at-delete|remove-failed) ;;
      *) fail "residual receipt contains an unsupported failure reason: ${reason}" ;;
    esac
    [[ -n "${relative_path}" && "${relative_path}" != /* && \
       "${relative_path}" != '..' && "${relative_path}" != ../* && \
       "${relative_path}" != */../* && "${relative_path}" != */.. ]] || \
      fail 'residual receipt contains an unsafe path.'

    expected_sha="$(awk -F'|' -v path="${relative_path}" \
      '$2 == path { print $1; count++ } END { if (count != 1) exit 2 }' \
      "${temporary_file_list}")" || \
      fail "residual path is not uniquely bound to the verified manifest: ${relative_path}"
    source_path="${source_profile}/${relative_path}"
    destination_path="${destination_profile}/${relative_path}"

    if [[ ! -e "${source_path}" ]]; then
      already_absent_count=$((already_absent_count + 1))
      continue
    fi
    if [[ ! -f "${source_path}" || ! -f "${destination_path}" ]]; then
      printf 'not-regular-or-destination-missing|%s\n' "${relative_path}" >> "${retry_failures}"
      continue
    fi
    if ! destination_sha="$(sha256sum "${destination_path}" 2>/dev/null | awk '{print $1}')" || \
       [[ "${destination_sha}" != "${expected_sha}" ]]; then
      printf 'destination-check-failed|%s\n' "${relative_path}" >> "${retry_failures}"
      continue
    fi
    if ! source_sha="$(sha256sum "${source_path}" 2>/dev/null | awk '{print $1}')"; then
      printf 'source-read-failed|%s\n' "${relative_path}" >> "${retry_failures}"
      continue
    fi
    if [[ "${source_sha}" != "${expected_sha}" ]]; then
      printf 'source-changed|%s\n' "${relative_path}" >> "${retry_failures}"
      continue
    fi
    if ! file_bytes="$(stat -c '%s' "${source_path}" 2>/dev/null)"; then
      printf 'source-stat-failed|%s\n' "${relative_path}" >> "${retry_failures}"
      continue
    fi
    if rm -f -- "${source_path}"; then
      removed_count=$((removed_count + 1))
      removed_bytes=$((removed_bytes + file_bytes))
    else
      printf 'remove-failed|%s\n' "${relative_path}" >> "${retry_failures}"
    fi
  done < "${residual_receipt}"

  receipt_path="${receipt_root}/RESUME-CUTOVER-${timestamp}.txt"
  {
    printf 'schema=giga.artvault-windows-profile-resume-cutover.v1\n'
    printf 'created_at_utc=%s\n' "${timestamp}"
    printf 'source_residual_receipt=%s\n' "${residual_receipt}"
    printf 'source_residual_receipt_sha256=%s\n' "${manifest_confirmation}"
    printf 'manifest_path=%s\n' "${manifest_path}"
    printf 'manifest_sha256=%s\n' "${manifest_sha}"
    printf 'deleted_regular_files=%s\n' "${removed_count}"
    printf 'deleted_regular_file_bytes=%s\n' "${removed_bytes}"
    printf 'already_absent_regular_files=%s\n' "${already_absent_count}"
    printf 'source_profile_retained_for_service_account=true\n'
  } > "${receipt_path}"
  chown art:art "${receipt_path}" "${retry_failures}"
  chmod 0600 "${receipt_path}" "${retry_failures}"

  if [[ -s "${retry_failures}" ]]; then
    fail 'residual cutover remains partial; the new exact residual receipt records every undeleted path.'
  fi
  rm -f -- "${retry_failures}"
  printf 'Residual cutover completed: deleted %s files (%s bytes); %s were already absent.\n' \
    "${removed_count}" "${removed_bytes}" "${already_absent_count}"
  printf 'Residual cutover receipt: %s\n' "${receipt_path}"
}

prepare_host_cutover() {
  local residual_receipt residual_count candidate candidate_sha
  local receipt_name receipt_timestamp cutover_receipt
  local manifest_path manifest_sha timestamp delta_root plan_path capture_path
  local reason relative_path expected_sha current_sha destination_sha delta_sha
  local source_path destination_path delta_path planned_count absent_count plan_sha

  [[ "$manifest_confirmation" =~ ^[0-9a-f]{64}$ ]] || \
    fail 'prepare-host-cutover requires a lowercase residual-receipt SHA-256 digest.'

  residual_receipt=''
  residual_count=0
  while IFS= read -r candidate; do
    candidate_sha="$(sha256sum "$candidate" | awk '{print $1}')"
    if [[ "$candidate_sha" == "$manifest_confirmation" ]]; then
      residual_receipt="$candidate"
      residual_count=$((residual_count + 1))
    fi
  done < <(find "$receipt_root" -maxdepth 1 -type f \
    \( -name 'cutover-*.deletion-failures.txt' \
       -o -name 'resume-cutover-*.deletion-failures.txt' \) -print | sort)
  [[ "$residual_count" == '1' ]] || \
    fail 'the supplied digest must identify exactly one residual receipt.'

  receipt_name="$(basename "$residual_receipt")"
  receipt_timestamp="${receipt_name#cutover-}"
  receipt_timestamp="${receipt_timestamp#resume-cutover-}"
  receipt_timestamp="${receipt_timestamp%.deletion-failures.txt}"
  cutover_receipt="$receipt_root/CUTOVER-$receipt_timestamp.txt"
  if [[ ! -f "$cutover_receipt" ]]; then
    cutover_receipt="$receipt_root/RESUME-CUTOVER-$receipt_timestamp.txt"
  fi
  [[ -f "$cutover_receipt" ]] || \
    fail 'the residual receipt has no matching cutover receipt.'

  manifest_path="$(sed -n 's/^manifest_path=//p' "$cutover_receipt")"
  manifest_sha="$(sed -n 's/^manifest_sha256=//p' "$cutover_receipt")"
  [[ "$manifest_path" == "$receipt_root/sha256-"*.txt ]] || \
    fail 'the cutover receipt references an unexpected manifest path.'
  [[ -f "$manifest_path" && "$manifest_sha" =~ ^[0-9a-f]{64}$ ]] || \
    fail 'the cutover receipt does not reference a valid manifest.'
  [[ "$(sha256sum "$manifest_path" | awk '{print $1}')" == "$manifest_sha" ]] || \
    fail 'the cutover manifest digest no longer matches its receipt.'
  (
    cd "$destination_profile"
    sha256sum --check --status "$manifest_path"
  ) || fail 'the canonical ArtVault destination no longer matches its manifest.'

  temporary_file_list="$(mktemp)"
  awk '
    {
      hash = $1
      sub(/^[^ ]+  /, "")
      sub(/^\.\//, "")
      if (hash !~ /^[0-9a-f]{64}$/ || $0 == "" || $0 ~ /^\// || $0 ~ /(^|\/)\.\.($|\/)/) {
        exit 2
      }
      print hash "|" $0
    }
  ' "$manifest_path" > "$temporary_file_list" || \
    fail 'the verified destination manifest contains an unsafe entry.'

  timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
  delta_root="$migration_root/residual-delta/$timestamp"
  plan_path="$receipt_root/host-delete-plan-$timestamp.txt"
  capture_path="$receipt_root/HOST-DELETE-CAPTURE-$timestamp.txt"
  mkdir -p "$delta_root"
  {
    printf 'schema=giga.artvault-windows-host-delete-plan.v1\n'
    printf 'source_root=C:\\Users\\gutua\n'
  } > "$plan_path"
  {
    printf 'schema=giga.artvault-windows-host-delete-capture.v1\n'
    printf 'created_at_utc=%s\n' "$timestamp"
    printf 'source_residual_receipt=%s\n' "$residual_receipt"
    printf 'source_residual_receipt_sha256=%s\n' "$manifest_confirmation"
    printf 'manifest_path=%s\n' "$manifest_path"
    printf 'manifest_sha256=%s\n' "$manifest_sha"
    printf 'delta_root=%s\n' "$delta_root"
  } > "$capture_path"
  planned_count=0
  absent_count=0

  while IFS='|' read -r reason relative_path; do
    reason="${reason%$'\r'}"
    relative_path="${relative_path%$'\r'}"
    [[ -n "$reason" && -n "$relative_path" && "$relative_path" != /* && \
       "$relative_path" != '..' && "$relative_path" != ../* && \
       "$relative_path" != */../* && "$relative_path" != */.. ]] || \
      fail 'the residual receipt contains an unsafe entry.'

    expected_sha="$(awk -F'|' -v path="$relative_path" \
      '$2 == path { print $1; count++ } END { if (count != 1) exit 2 }' \
      "$temporary_file_list")" || \
      fail "a residual path is not uniquely bound to the manifest: $relative_path"
    source_path="$source_profile/$relative_path"
    destination_path="$destination_profile/$relative_path"

    if [[ ! -e "$source_path" ]]; then
      printf 'already-absent||%s\n' "$relative_path" >> "$capture_path"
      absent_count=$((absent_count + 1))
      continue
    fi
    [[ -f "$source_path" && -f "$destination_path" ]] || \
      fail "a residual is not a regular source and destination file: $relative_path"
    current_sha="$(sha256sum "$source_path" | awk '{print $1}')" || \
      fail "a residual cannot be read: $relative_path"

    if [[ "$current_sha" == "$expected_sha" ]]; then
      destination_sha="$(sha256sum "$destination_path" | awk '{print $1}')"
      [[ "$destination_sha" == "$expected_sha" ]] || \
        fail "a canonical destination changed: $relative_path"
      printf 'canonical-manifest|%s|%s\n' "$current_sha" "$relative_path" \
        >> "$capture_path"
    else
      delta_path="$delta_root/$relative_path"
      mkdir -p "$(dirname "$delta_path")"
      cp --reflink=auto -- "$source_path" "$delta_path"
      chown art:art "$delta_path"
      chmod 0600 "$delta_path"
      delta_sha="$(sha256sum "$delta_path" | awk '{print $1}')"
      [[ "$delta_sha" == "$current_sha" ]] || \
        fail "a changing residual could not be captured consistently: $relative_path"
      printf 'current-delta|%s|%s\n' "$current_sha" "$relative_path" \
        >> "$capture_path"
    fi

    printf '%s|%s\n' "$current_sha" "$relative_path" >> "$plan_path"
    planned_count=$((planned_count + 1))
  done < "$residual_receipt"

  [[ "$planned_count" != '0' ]] || fail 'no residual source files remain to plan.'
  {
    printf 'planned_files=%s\n' "$planned_count"
    printf 'already_absent_files=%s\n' "$absent_count"
  } >> "$capture_path"
  chown -R art:art "$delta_root"
  chmod 0700 "$migration_root/residual-delta" "$delta_root"
  chown art:art "$plan_path" "$capture_path"
  chmod 0600 "$plan_path" "$capture_path"
  plan_sha="$(sha256sum "$plan_path" | awk '{print $1}')"

  printf 'Host deletion plan prepared after capturing every current residual byte.\n'
  printf 'Plan: %s\n' "$plan_path"
  printf 'Plan SHA-256: %s\n' "$plan_sha"
  printf 'Capture receipt: %s\n' "$capture_path"
}

main() {
  [[ "$(id -u)" == '0' ]] || fail 'run as root inside ArtVault.'
  command -v findmnt >/dev/null 2>&1 || fail 'findmnt is unavailable.'
  command -v rsync >/dev/null 2>&1 || fail 'rsync is unavailable.'
  command -v cmp >/dev/null 2>&1 || fail 'cmp is unavailable.'
  command -v sha256sum >/dev/null 2>&1 || fail 'sha256sum is unavailable.'

  case "${mode}" in
    plan|stage|verify|cutover-check|cutover|resume-cutover|prepare-host-cutover) ;;
    -h|--help|'') usage; exit 2 ;;
    *) usage >&2; exit 2 ;;
  esac

  trap cleanup EXIT
  if [[ "${mode}" == 'cutover' || "${mode}" == 'resume-cutover' ]]; then
    mount_source rw
  else
    mount_source ro
  fi

  mkdir -p "${destination_profile}" "${receipt_root}"
  chown -R art:art "${migration_root}"
  chmod 0700 "${migration_root}" "${destination_profile}" "${receipt_root}"
  write_scope_receipt

  case "${mode}" in
    plan) plan_copy ;;
    stage) stage_profile ;;
    verify) verify_profile ;;
    cutover-check) cutover_profile ;;
    cutover) cutover_profile ;;
    resume-cutover) resume_cutover ;;
    prepare-host-cutover) prepare_host_cutover ;;
  esac
}

main "$@"
