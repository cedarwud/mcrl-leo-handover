#!/usr/bin/env bash
set -euo pipefail

run_root="${1:-/home/sat/mcrl-zero-energy-c3-v012-20260903-r1}"
run_dir="${run_root}/run-v012"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
runner=".scratch/zero-energy-c3-v012/run_v012_zero_energy_c3_oracle.py"

if [[ -e "${run_dir}" || -L "${run_dir}" ]]; then
  echo "refusing to overwrite ${run_dir}" >&2
  exit 1
fi

mkdir -p "${run_dir}/logs" "${run_dir}/shards"

worlds=(2026104801 2026104802)
arms=(DROP_C3 FULL_ZR FULL_HR)
lineages=(2026092101 2026092102 2026092103)

for world in "${worlds[@]}"; do
  for arm in "${arms[@]}"; do
    for lineage in "${lineages[@]}"; do
      arm_lower="${arm,,}"
      session="v012-${world}-${arm_lower}-${lineage}"
      output="run-v012/shards/${world}-${arm}-${lineage}"
      log="run-v012/logs/${world}-${arm}-${lineage}.log"
      tmux new-session -d -s "${session}" \
        "cd '${run_root}' && env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src '${python_bin}' '${runner}' shard --world '${world}' --arm '${arm}' --lineage '${lineage}' --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 --prereg artifacts/PREREG-FROZEN-2026-08-25-R2.json --v03-root artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1 --output '${output}' > '${log}' 2>&1"
      echo "launched ${session}"
    done
  done
done
