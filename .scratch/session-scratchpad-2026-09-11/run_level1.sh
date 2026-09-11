#!/bin/bash
# SOLO Level 1 launcher: chunks A,B now; chunk C after Level 2 frees its process slot (cap 3 python processes).
set -u
cd /home/sat/mcrl-v025-solo-ws
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
nice -n 15 $PY scripts/solo_level1.py --anchors 0-35 --out .scratch/level1/part-A.jsonl > logs/level1-A.log 2>&1 &
nice -n 15 $PY scripts/solo_level1.py --anchors 36-71 --out .scratch/level1/part-B.jsonl > logs/level1-B.log 2>&1 &
until grep -q ALL_DONE logs/level2.log; do sleep 30; done
nice -n 15 $PY scripts/solo_level1.py --anchors 72-92 --out .scratch/level1/part-C.jsonl > logs/level1-C.log 2>&1 &
wait
echo LEVEL1_ALL_DONE > logs/level1-done.flag
