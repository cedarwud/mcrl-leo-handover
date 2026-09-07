#!/usr/bin/env bash
set -euo pipefail

run_root="${1:-/home/sat/mcrl-joint-c3-v011-20260903-r1}"
run_dir="${run_root}/run-v011"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
runner=".scratch/joint-c3-v011/run_v011_joint_c3_ordered_oracle.py"

if [[ -e "${run_dir}" || -L "${run_dir}" ]]; then
  echo "refusing to overwrite ${run_dir}" >&2
  exit 1
fi

mkdir -p "${run_dir}/logs" "${run_dir}/shards"

arms=(DROP_C3 FULL_M1D FULL_AP DIAG_O_DROP DIAG_O_FULL)
lineages=(2026092101 2026092102 2026092103)

for arm in "${arms[@]}"; do
  for lineage in "${lineages[@]}"; do
    arm_lower="${arm,,}"
    session="v011-${arm_lower}-${lineage}"
    output="run-v011/shards/${arm}-${lineage}"
    log="run-v011/logs/${arm}-${lineage}.log"
    tmux new-session -d -s "${session}" \
      "cd '${run_root}' && env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src '${python_bin}' '${runner}' shard --arm '${arm}' --lineage '${lineage}' --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 --prereg artifacts/PREREG-FROZEN-2026-08-25-R2.json --v03-root artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1 --output '${output}' > '${log}' 2>&1"
    echo "launched ${session}"
  done
done
