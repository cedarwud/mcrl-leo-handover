#!/usr/bin/env bash
set -euo pipefail

audit_dir="$(cd "$(dirname "$0")" && pwd)"
repo_dir="$(cd "$audit_dir/../.." && pwd)"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$repo_dir/src:/home/sat/mcrl-leo-handover/.venv/lib/python3.13/site-packages:$audit_dir"
cd "$repo_dir"

python "$audit_dir/reference_physics.py"
python -m pytest -q \
  "$audit_dir/test_audit_regressions.py" \
  "$audit_dir/target_parity_suite/tests/test_target_parity.py"
python "$audit_dir/target_replay.py" >/dev/null
python "$audit_dir/c3_oracle_comparison.py" >/dev/null
python "$audit_dir/build_lambda_provenance.py" >/dev/null
python "$audit_dir/oracle_marginal_rerun.py" >/dev/null

set +e
python "$audit_dir/differential_audit.py" --output "$audit_dir/part2-results-run1.json" >/dev/null
first_status=$?
python "$audit_dir/differential_audit.py" --output "$audit_dir/part2-results-run2.json" >/dev/null
second_status=$?
set -e
if [[ $first_status -ne 1 || $second_status -ne 1 ]]; then
  echo "expected the differential runner to return 1 for threshold findings" >&2
  exit 2
fi
first_hash="$(sha256sum "$audit_dir/part2-results-run1.json" | cut -d' ' -f1)"
second_hash="$(sha256sum "$audit_dir/part2-results-run2.json" | cut -d' ' -f1)"
if [[ "$first_hash" != "$second_hash" ]]; then
  echo "nondeterministic differential evidence" >&2
  exit 3
fi
echo "audit evidence: PASS ($first_hash)"
