#!/usr/bin/env bash
# B1-CREDIT LP-credit oracle-first screen, one lane (<= 2 lanes total). Idempotent: finished episodes are skipped.
#   lane A: nominal eta0 (eval, cal), nominal 1e8 (eval, cal), evaluator 1e8 (eval 0-5)
#   lane B: evaluator eta0 (eval 0-5)
set -u
cd /home/u24/papers/mcrl-leo-handover-b1
export MCRL_TLE_ROOT=/home/u24/mcrl-runtime/tle-pinned-427e6a91 OMP_NUM_THREADS=1
PY=/home/u24/papers/mcrl-leo-handover/.venv/bin/python
L=/home/u24/papers/mcrl-leo-handover/.scratch/b1-credit/lp-credit
lane=$1
wait_for() {  # anchored pattern: the interpreter path, never this shell
  while pgrep -f "^$PY $1" >/dev/null; do sleep 10; done
}
if [ "$lane" = A ]; then
  wait_for "scripts/b1_lp_credit_rule.py --kind rule"
  for eta in eta0 1e8; do
    for set in evaluation calibration; do
      nice -n 16 $PY scripts/b1_lp_credit_rule.py --kind nominal --eta $eta --set $set --episodes 0-23 --out $L || exit 1
    done
  done
  nice -n 16 $PY scripts/b1_lp_credit_rule.py --kind evaluator --eta 1e8 --set evaluation --episodes 0-5 --out $L || exit 1
elif [ "$lane" = B ]; then
  while pgrep -f "run_mutants.sh" >/dev/null; do sleep 10; done
  nice -n 16 $PY scripts/b1_lp_credit_rule.py --kind evaluator --eta eta0 --set evaluation --episodes 0-5 --out $L || exit 1
fi
echo "lane $lane done $(date -Is)"
