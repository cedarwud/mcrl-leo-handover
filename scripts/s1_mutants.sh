#!/usr/bin/env bash
# Run tests/test_s1_harness.py once per NAMED MUTANT and record red/green.
# Every mutant must FAIL the suite; the unmutated tree must PASS it.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${S1_PYTEST_PYTHON:-/home/u24/papers/mcrl-leo-handover/.venv/bin/python}"
export MCRL_TLE_ROOT="${MCRL_TLE_ROOT:-/home/u24/mcrl-runtime/tle-pinned-427e6a91}"
export PYTHONPATH="$REPO/src:$REPO/scripts"

MUTANTS=(
  xep_reference_state_not_substituted
  xep_current_mask_not_applied
  xep_reference_regenerated_per_episode
  xep_agreement_against_itself
  xep_reference_missing_from_config_hash
  s1_null_uses_dev_stream
  s1_reuses_dev_training_triple
  s1_evaluates_on_calibration
  s1_modqn_uses_shared_bootstrap
  s1_manifest_drops_arm_configs
  s1_partial_matrix_allowed
)

cd "$REPO" || exit 1
echo "=== clean ==="
S1_MUTANT="" "$PY" -m pytest tests/test_s1_harness.py -q >/tmp/s1-clean.log 2>&1
echo "clean: $([ $? -eq 0 ] && echo GREEN || echo RED) -- $(tail -1 /tmp/s1-clean.log)"

for m in "${MUTANTS[@]}"; do
  log="/tmp/s1-mutant-$m.log"
  S1_MUTANT="$m" "$PY" -m pytest tests/test_s1_harness.py -q >"$log" 2>&1
  rc=$?
  failed=$(grep -c "^FAILED\|^ERROR" "$log")
  if [ $rc -ne 0 ]; then
    echo "RED   $m  ($failed failing test(s))"
    grep "^FAILED\|^ERROR" "$log" | sed 's/^/        /' | head -6
  else
    echo "GREEN $m  <-- MUTANT SURVIVED, the suite does not catch it"
  fi
done
