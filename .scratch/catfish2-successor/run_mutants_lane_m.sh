#!/usr/bin/env bash
# LANE-M: run tests/test_cf_multid3.py once per NAMED MUTANT and once clean.
# Every mutant must turn the suite RED on its own; the clean run must be GREEN.
# Usage: bash .scratch/catfish2-successor/run_mutants_lane_m.sh [outfile]
set -u
cd "$(dirname "$0")/../.." || exit 1
OUT="${1:-.scratch/catfish2-successor/mutants-lane-m.log}"
PY=/home/u24/papers/mcrl-leo-handover/.venv/bin/python
export MCRL_TLE_ROOT=/home/u24/mcrl-runtime/tle-pinned-427e6a91
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
: > "$OUT"
MUTANTS="
teacher_weights_reintroduced
acf_summed_over_members
acf_cardinality_counts_duplicates
illegal_teacher_actions_admitted
margin_applied_to_members
loss_admits_illegal_members
order_dependence_introduced
teacher_identity_dropped_from_hash
deployment_path_touched
null_drawn_with_replacement
null_single_proposal
"
for m in "" $MUTANTS; do
  name="${m:-CLEAN}"
  MULTI_MUTANT="$m" nice -n 16 "$PY" -m pytest tests/test_cf_multid3.py -q -p no:randomly \
      > "/tmp/lane-m-$name.txt" 2>&1
  rc=$?
  failed=$(grep -oE '^FAILED [^ ]+' "/tmp/lane-m-$name.txt" | sed 's/FAILED tests.test_cf_multid3.py:://' | tr '\n' ' ')
  tail1=$(grep -E '^[0-9]+ (passed|failed)|passed|failed' "/tmp/lane-m-$name.txt" | tail -1)
  printf '%-40s rc=%d  %s\n    red: %s\n' "$name" "$rc" "$tail1" "${failed:-none}" >> "$OUT"
done
cat "$OUT"
