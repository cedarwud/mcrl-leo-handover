#!/usr/bin/env bash
set -euo pipefail

exec env \
  -C /home/sat/mcrl-leo-handover-v04-c3-20260901 \
  PYTHONPATH=src \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/c3-v04/run_v04_c3_500_update_screen.py \
  --gate-dir artifacts/multi-catfish-v04-c3-learnability-20260901-r2 \
  --source-dir artifacts/multi-catfish-v04-c3-source-20260901-r2 \
  --v03-root artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1 \
  --prereg artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
  --output-dir artifacts/multi-catfish-v04-c3-500-update-screen-20260901-r1
