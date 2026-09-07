#!/usr/bin/env bash
set -Eeuo pipefail

# R4 isolated reproduction of the only R3 source-world failure.  This script
# runs one frozen TRAIN world and no learner, composition, TEST, or episode
# evaluation.  Its output path is write-once through the source-server guard.

root="/home/sat/mcrl-v023-lcsrs-debug-20260906-r4-1706"
python="/home/sat/mcrl-leo-handover/.venv/bin/python"
output="${root}/replay/world-2026121706.json"
exec >"${root}/replay-world-2026121706.log" 2>&1

cd "${root}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

exec "${python}" \
  .scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_source_server.py \
  --world 2026121706 \
  --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
  --prereg artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  --manifest .scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.json \
  --manifest-digest .scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.sha256 \
  --execution-addendum docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md \
  --placebo-key MCRL_V023_LCSRS_MATCHED_PLACEBO_V1 \
  --placebo-key-sha256 7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825 \
  --lineage 2026092101 \
  --source-family MCRL_V023_LCSRS_C3_OBSERVABILITY_V1 \
  --preflight-sha256 8ce6c78ebfa0ef75192e139c0163064ccfb4ca796a76495df80daf17a377b4e6 \
  --output "${output}"
