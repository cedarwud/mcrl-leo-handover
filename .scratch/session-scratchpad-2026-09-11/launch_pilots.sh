#!/usr/bin/env bash
# B0 pilot launcher.  Idempotent: skips an arm whose status is complete or
# whose recorded PID is still alive.  Each arm: 1 python process, nice 16,
# BLAS/OMP threads 1, systemd scope MemoryMax=5G, plus the driver's own RSS
# guard.  Two arms => two python processes (the cap).
set -u
WS=/home/sat/mcrl-v025-b0-ws
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
for ARM in b0 unfixed; do
  OUT=$WS/pilot-$ARM-500
  LOG=$WS/pilot-$ARM-500.log
  PIDF=$WS/pilot-$ARM-500.pid
  if [ -f "$OUT/status.json" ] && grep -q '"status": "complete"' "$OUT/status.json"; then
    echo "$ARM: complete, skip"; continue
  fi
  if [ -f "$PIDF" ] && kill -0 "$(cat $PIDF)" 2>/dev/null; then
    echo "$ARM: running as $(cat $PIDF), skip"; continue
  fi
  cd $WS/$ARM
  setsid nohup systemd-run --user --scope -p MemoryMax=5G --quiet \
      nice -n 16 $PY scripts/run_b0_pilot.py --out-dir $OUT --episodes 500 --label ${ARM^^} \
      >> $LOG 2>&1 < /dev/null &
  echo $! > $PIDF
  echo "$ARM: launched wrapper pid $(cat $PIDF) cwd $WS/$ARM out $OUT log $LOG"
done
