#!/usr/bin/env bash
set -euo pipefail

run_root="${1:-/home/sat/mcrl-v014-learnability-20260903-r1}"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
runner=".scratch/multi-catfish-v014-learner/run_v014_q3_support_probe.py"
artifact="artifacts/multi-catfish-v014-q3-support-probe-20260903-r1"
contract="${artifact}/contracts/MULTI-CATFISH-MCRL-V014-Q3-SUPPORT-PROBE-PREREG-2026-09-03.md"
receipt="${artifact}/contracts/prereg.sha256"
output="${artifact}/result.json"

cd "${run_root}"
grep -Fq 'Status: **FROZEN BEFORE PROBE MODEL OUTCOME**' "${contract}"
(
  cd "$(dirname "${contract}")"
  sha256sum -c "$(basename "${receipt}")"
)
if [[ -e "${output}" || -L "${output}" ]]; then
  echo "refusing to overwrite ${output}" >&2
  exit 2
fi

source_args=()
while IFS= read -r -d '' shard; do
  source_args+=(--source "${shard}")
done < <(find source-panel/shards -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
if (( ${#source_args[@]} != 42 )); then
  echo "expected 21 source shards" >&2
  exit 3
fi

checkpoint_args=(
  --checkpoint "2026108101=learner-gate/checkpoints/init-2026108101-rung-003000.pt"
  --checkpoint "2026108102=learner-gate/checkpoints/init-2026108102-rung-003000.pt"
  --checkpoint "2026108103=learner-gate/checkpoints/init-2026108103-rung-003000.pt"
)

env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 PYTHONPATH=src \
  "${python_bin}" "${runner}" "${source_args[@]}" \
  "${checkpoint_args[@]}" --output "${output}"
