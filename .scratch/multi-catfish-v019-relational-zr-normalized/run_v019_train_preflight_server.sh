#!/usr/bin/env bash
set -uo pipefail

v019_checkout=/home/sat/mcrl-v019-relational-q3-normalized-20260904-r1
v019_python=/home/sat/mcrl-leo-handover/.venv/bin/python
v019_lane=.scratch/multi-catfish-v019-relational-zr-normalized
v019_preflight="$v019_lane/preflight"
v019_manifest="$v019_preflight/PREFLIGHT-CLOSURE-FROZEN-2026-09-04.sha256"
v019_manifest_sha=c3d7e8616ddec28b3d916a899a753eba9d70eb4dae2197c148cd5e88eea418f4
v019_source=/home/sat/mcrl-v018-relational-learner-20260904-r1/learned-q3-panel-r1/sources/TRAIN
v019_output="$v019_checkout/preflight-run-r1"
v019_log="$v019_checkout/preflight-run-r1.log"
v019_complete="$v019_checkout/preflight-run-r1.complete"

cd "$v019_checkout" || exit 70
test ! -e "$v019_output" || exit 71
test ! -e "$v019_complete" || exit 72
test "$(sha256sum "$v019_manifest" | awk '{print $1}')" = "$v019_manifest_sha" || exit 73
sha256sum -c "$v019_manifest" > "$v019_checkout/preflight-closure-check.log" 2>&1 || exit 74

v019_status=0
PYTHONUNBUFFERED=1 \
OMP_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
PYTHONPATH=src \
"$v019_python" "$v019_preflight/train_only_preflight_v019.py" \
  --source-root "$v019_source" \
  --output "$v019_output" \
  > "$v019_log" 2>&1 || v019_status=$?

printf 'exit_code=%s\n' "$v019_status" > "$v019_complete"
exit "$v019_status"
