#!/usr/bin/env bash
set -euo pipefail

FAST500_REPO="/home/sat/mcrl-leo-handover-v03a-20260830"
FAST500_PY="${FAST500_REPO}/.venv/bin/python"
FAST500_RUNNER="${FAST500_REPO}/.scratch/c2-v03a-fast500/fast500_prefix_arm.py"
FAST500_RUNNER_SHA="11a46453a76ed582b1e17bfcdee4048aeb03ca777404dc4a64d475cba3c4ef01"
FAST500_TLE="/home/sat/mcrl-runtime/tle-frozen-20260820"
FAST500_ROOT="${FAST500_REPO}/artifacts/multi-catfish-v03a-fast500-prefix-training-20260831-r1"

case "${1:-}" in
    lr0p001)
        FAST500_LR="lr0p001"
        FAST500_AUTHORITY="${FAST500_REPO}/artifacts/multi-catfish-v03a-intermediate-authority-20260830-r2/1500-lr0p001.json"
        FAST500_AUTHORITY_SHA="d95469b98b2335f32ba7b309bb0a415083d6439f5b68f51989129245fb0fbbc7"
        ;;
    lr0p01)
        FAST500_LR="lr0p01"
        FAST500_AUTHORITY="${FAST500_REPO}/artifacts/multi-catfish-v03a-intermediate-authority-20260830-r2/1500-lr0p01.json"
        FAST500_AUTHORITY_SHA="ce6f8c49127ba29b4b0af27f123b499c641ae83b97f1c3b53e8c72c4eaa6c265"
        ;;
    *)
        echo "usage: $0 lr0p001|lr0p01" >&2
        exit 2
        ;;
esac

mkdir -p "${FAST500_ROOT}/logs"
exec >>"${FAST500_ROOT}/logs/${FAST500_LR}-chain.log" 2>&1

date -Iseconds
echo "Starting clean EP500 prefix chain for ${FAST500_LR}."
for FAST500_ARM in A011 A101 A110; do
    FAST500_OUTPUT="${FAST500_ROOT}/${FAST500_LR}/${FAST500_ARM}"
    echo "$(date -Iseconds) ${FAST500_LR} ${FAST500_ARM} start"
    "${FAST500_PY}" "${FAST500_RUNNER}" \
        --authority "${FAST500_AUTHORITY}" \
        --expected-authority-sha256 "${FAST500_AUTHORITY_SHA}" \
        --expected-runner-sha256 "${FAST500_RUNNER_SHA}" \
        --arm "${FAST500_ARM}" \
        --output-dir "${FAST500_OUTPUT}" \
        --tle-root "${FAST500_TLE}"
    echo "$(date -Iseconds) ${FAST500_LR} ${FAST500_ARM} complete"
done
echo "$(date -Iseconds) ${FAST500_LR} chain complete"
