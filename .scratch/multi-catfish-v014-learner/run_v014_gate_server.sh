#!/usr/bin/env bash
set -euo pipefail

run_root="${1:?isolated V0.14 server root is required}"
source_dir="${run_root}/source-panel"
output_dir="${run_root}/learner-gate"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
runner=".scratch/multi-catfish-v014-learner/run_v014_learner_gate.py"

if [[ ! -f "${source_dir}/controller.complete" || -L "${source_dir}/controller.complete" ]]; then
  echo "source panel is not complete" >&2
  exit 2
fi
if [[ -e "${output_dir}" || -L "${output_dir}" ]]; then
  echo "refusing to overwrite ${output_dir}" >&2
  exit 3
fi

cd "${run_root}"
source_args=()
while IFS= read -r -d '' shard; do
  source_args+=(--source "${shard}")
done < <(find source-panel/shards -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
if (( ${#source_args[@]} != 42 )); then
  echo "expected 21 source shards" >&2
  exit 4
fi

env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 PYTHONPATH=src \
  "${python_bin}" "${runner}" "${source_args[@]}" --output "${output_dir}"

