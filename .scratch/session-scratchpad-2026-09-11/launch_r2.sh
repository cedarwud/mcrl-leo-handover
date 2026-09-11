#!/usr/bin/env bash
# Round-2 pilots (ruling 2026-09-11 item 6).  Idempotent: skips an arm whose
# status is complete or whose PID is alive.  2 arms = 2 python processes.
set -u
WS=/home/sat/mcrl-v025-b0-ws
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MCRL_TLE_ROOT=$WS/tle-pinned-427e6a91
for spec in BASELINE_EQ16:eq16-per-head-max SHARED_BOOTSTRAP:shared-continuation-argmax; do
  ARM=${spec%%:*}; MODE=${spec#*:}
  OUT=$WS/r2-pilot-$ARM-500; LOG=$OUT.log; PIDF=$OUT.pid
  if [ -f "$OUT/status.json" ] && grep -q '"status": "complete"' "$OUT/status.json"; then echo "$ARM complete, skip"; continue; fi
  if [ -f "$PIDF" ] && kill -0 "$(cat $PIDF)" 2>/dev/null; then echo "$ARM running as $(cat $PIDF), skip"; continue; fi
  cd $WS/r2
  setsid nohup systemd-run --user --scope -p MemoryMax=5G --quiet \
    nice -n 16 $PY scripts/run_b0_pilot.py --out-dir $OUT --episodes 500 --label $ARM --td-bootstrap-mode $MODE \
    >> $LOG 2>&1 < /dev/null &
  echo $! > $PIDF
  echo "$ARM launched pid $(cat $PIDF) mode $MODE out $OUT"
done
