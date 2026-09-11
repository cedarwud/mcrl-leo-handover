#!/bin/bash
# SOLO Level 2: sequential knockout scoring, one python process at a time.
set -u
cd /home/sat/mcrl-v025-solo-ws
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
PF=/home/sat/mcrl-v025-panelfix-ws/artifacts
PV=/home/sat/mcrl-v025-panelv3-ws/artifacts
PZ=/home/sat/mcrl-v025-panelz-ws/artifacts
run() { # tag rundir panel receipt sha epoch
  echo "=== $1 $(date -u +%FT%TZ)"
  /usr/bin/time -v nice -n 15 $PY scripts/solo_level2.py --tag "$1" --run-dir "$2" --panel "$3" --panel-receipt "$4" --panel-sha256 "$5" --epoch "$6" --out ".scratch/level2/$1-epoch-$6.json" 2>&1 | grep -v '^\s*\(Page\|Minor\|Major\|Swaps\|File\|Socket\|Signals\|Voluntary\|Involuntary\|Average\|Exit\|Percent\|System\|User\|Elapsed\)' 
  echo "=== rc=${PIPESTATUS[0]} $(date -u +%FT%TZ)"
}
run exact22 /home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-step-decay-16seed-4000-20260910 $PF/panel-q1v1.json $PF/panel-q1v1.receipt.json dc5df10b17250f298ab7bbaa2a099c895204a83f3b2f8d2c93ef73cc94e50134 4000
run q1v3 /home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-step-decay-16seed-4000-20260910 $PV/panel-q1v3.json $PV/panel-q1v3.receipt.json 90cf0181a997a12202912c59dc294ae14567eed2d7e654e464e1de0eb9319f94 4000
run q1v3_control /home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-control-step-decay-16seed-4000-20260910 $PV/panel-q1v3-control.json $PV/panel-q1v3-control.receipt.json bd5a967b9e013bc74dd52c321ffed06835c2361ad28fd4c370b1bb0d4434e8c8 4000
run exact93 /home/sat/mcrl-v025-exact93-ws/artifacts/exact93-step-decay-16seed-4000-20260911 $PF/panel-q1v1.json $PF/panel-q1v1.receipt.json dc5df10b17250f298ab7bbaa2a099c895204a83f3b2f8d2c93ef73cc94e50134 4000
run zq1v1 /home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z $PF/panel-q1v1.json $PF/panel-q1v1.receipt.json dc5df10b17250f298ab7bbaa2a099c895204a83f3b2f8d2c93ef73cc94e50134 500
run zq1v2 /home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z $PF/panel-q1v2.json $PF/panel-q1v2.receipt.json b5a2c365a1c1936399530dd98e509a464a56d88bb9857f03d611c3fde3643638 500
run zview /home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2z-500ep-20260910T1512Z $PZ/panel-q1v2z.json $PZ/panel-q1v2z.receipt.json 2a905423c8b9b573bef56398ad4b36ce671cc1a41bf232df07d359e81b69e203 500
echo ALL_DONE
