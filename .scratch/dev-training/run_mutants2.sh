#!/bin/bash
# DEVHARNESS preflight: every named mutant must turn ITS test red (exit-code detection).
cd /home/u24/papers/mcrl-leo-handover-dev || exit 1
export MCRL_TLE_ROOT=/home/u24/mcrl-runtime/tle-pinned-427e6a91
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/home/u24/papers/mcrl-leo-handover-dev/src
PY=/home/u24/papers/mcrl-leo-handover/.venv/bin/python
source /home/u24/papers/mcrl-leo-handover/.scratch/dev-training/mutant_pairs.sh
red=0; bad=0
for pair in "${PAIRS[@]}"; do
  m="${pair%%|*}"; t="${pair##*|}"
  if DEV_MUTANT="$m" $PY -m pytest tests/test_cf_dev.py -q -x -p no:warnings -k "$t" >/dev/null 2>&1; then
    echo "GREEN-BAD $m -> $t"; bad=$((bad+1))
  else
    echo "RED       $m -> $t"; red=$((red+1))
  fi
done
echo "MUTANTS: $red red / $((red+bad)) total; $bad did NOT turn their test red"
