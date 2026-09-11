#!/bin/bash
# usage: run.sh <script.py> args...   (cwd = ws; pinned TLE; 1 thread; nice 16; MemoryMax 5G)
WS=/home/sat/mcrl-v025-t0-repr-ws
cd "$WS" || exit 9
export MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
exec nice -n 16 systemd-run --user --scope -q -p MemoryMax=5G /home/sat/mcrl-leo-handover/.venv/bin/python "$WS/scripts/$1" "${@:2}"
