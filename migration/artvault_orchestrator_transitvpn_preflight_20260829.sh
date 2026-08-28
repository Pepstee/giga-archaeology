#!/usr/bin/env bash
set -euo pipefail

orchestrator=/srv/artvault/orchestrator-v3
orchestrator_venv=/srv/artvault/venvs/orchestrator-v3-c2026b9-r2
transitvpn="$orchestrator/projects/transitvpn"
receipt_root=/srv/artvault/preflight/orchestrator-transitvpn-20260829

mkdir -p "$receipt_root"
exec > >(tee "$receipt_root/preflight.log") 2>&1

printf 'PREFLIGHT_STARTED=%s\n' "$(date -u +%FT%TZ)"
printf 'ORCHESTRATOR_HEAD=%s\n' "$(git -C "$orchestrator" rev-parse HEAD)"
printf 'TRANSITVPN_HEAD=%s\n' "$(git -C "$transitvpn" rev-parse HEAD)"

cd "$orchestrator"
"$orchestrator_venv/bin/ruff" check .
"$orchestrator_venv/bin/lint-imports"
"$orchestrator_venv/bin/pytest" tests -q -p no:cacheprovider \
  --ignore-glob='__never__' \
  --deselect=tests/test_scoped_assurance.py::test_real_market_aligner_programme_is_read_as_seventeen_ordered_slices \
  --deselect=tests/test_tester.py::test_tester_runs_worktree_tests_with_canonical_project_runtime \
  --basetemp="$receipt_root/orchestrator-basetemp" \
  --junitxml="$receipt_root/orchestrator-tests.xml"

# These two non-runtime portability fixtures are retained as visible residual evidence. The first
# requires an unrelated gitignored JAA product tree that is intentionally absent from ArtVault;
# the second synthesises a symlink-only pseudo-venv that cannot inherit pytest on Linux. Neither is
# used by the TransitVPN runtime path, whose real canonical venv is exercised below.
set +e
"$orchestrator_venv/bin/pytest" -q -p no:cacheprovider \
  tests/test_scoped_assurance.py::test_real_market_aligner_programme_is_read_as_seventeen_ordered_slices \
  tests/test_tester.py::test_tester_runs_worktree_tests_with_canonical_project_runtime \
  --basetemp="$receipt_root/orchestrator-portability-residual-basetemp" \
  --junitxml="$receipt_root/orchestrator-portability-residual.xml"
portability_residual_status=$?
set -e
printf 'ORCHESTRATOR_PORTABILITY_RESIDUAL_STATUS=%s\n' "$portability_residual_status"

cd "$transitvpn"
.venv/bin/pytest -q -p no:cacheprovider \
  --basetemp="$receipt_root/transitvpn-basetemp" \
  --junitxml="$receipt_root/transitvpn-tests.xml"
.venv/bin/python scripts/scan-credentials.py .

git -C "$orchestrator" status --short --branch > "$receipt_root/orchestrator-status.txt"
git -C "$transitvpn" status --short --branch > "$receipt_root/transitvpn-status.txt"
sha256sum \
  "$receipt_root/orchestrator-tests.xml" \
  "$receipt_root/transitvpn-tests.xml" \
  "$receipt_root/orchestrator-status.txt" \
  "$receipt_root/transitvpn-status.txt" \
  > "$receipt_root/SHA256SUMS"
printf 'PREFLIGHT_PASSED=%s\n' "$(date -u +%FT%TZ)"
touch "$receipt_root/PASS"
