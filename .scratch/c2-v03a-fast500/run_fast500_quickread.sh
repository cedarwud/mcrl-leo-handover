#!/usr/bin/env bash
set -euo pipefail

QUICK_REPO="/home/sat/mcrl-leo-handover-v03a-20260830"
QUICK_PY="${QUICK_REPO}/.venv/bin/python"
QUICK_EVAL="${QUICK_REPO}/.scratch/smc-er-short-ep/sweep_evaluation.py"
QUICK_TLE="/home/sat/mcrl-runtime/tle-frozen-20260820"
QUICK_PREREG="${QUICK_REPO}/artifacts/PREREG-FROZEN-2026-08-25-R2.json"
QUICK_OUT="${QUICK_REPO}/artifacts/multi-catfish-v03a-fast500-quickread-u100-seed2026082904-20260831-r1"

mkdir -p "${QUICK_OUT}"
for QUICK_LR in lr0p001 lr0p01; do
    if [[ "${QUICK_LR}" == "lr0p001" ]]; then
        QUICK_SOURCE="${QUICK_REPO}/artifacts/multi-catfish-v03a-1500-lr0p001-20260830-r2"
    else
        QUICK_SOURCE="${QUICK_REPO}/artifacts/multi-catfish-v03a-1500-lr0p01-20260830-r2"
    fi
    taskset -c 16-19 nice -n 10 "${QUICK_PY}" "${QUICK_EVAL}" \
        --arm "Baseline MODQN=${QUICK_SOURCE}/arms/B000/checkpoints/ep-000500-main.pt" \
        --arm "Full Multi-Catfish MCRL=${QUICK_SOURCE}/arms/F111/checkpoints/ep-000500-main.pt" \
        --users 100 \
        --seeds 2026082904 \
        --tle-root "${QUICK_TLE}" \
        --prereg "${QUICK_PREREG}" \
        --output-dir "${QUICK_OUT}/${QUICK_LR}"
done
