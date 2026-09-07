#!/usr/bin/env bash
set -euo pipefail

run_root="${1:-/home/sat/mcrl-zero-energy-c3-v012-20260903-r1}"
run_dir="${run_root}/run-v012"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
runner=".scratch/zero-energy-c3-v012/run_v012_zero_energy_c3_oracle.py"

if [[ ! -d "${run_dir}/shards" || ! -d "${run_dir}/logs" ]]; then
  echo "missing V0.12 run directories under ${run_dir}" >&2
  exit 2
fi

active="$(tmux list-sessions 2>/dev/null | grep -c '^v012-' || true)"
if [[ "${active}" != "0" ]]; then
  echo "V0.12 still has ${active} active shard sessions" >&2
  exit 3
fi

mapfile -t shards < <(find "${run_dir}/shards" -mindepth 2 -maxdepth 2 -type f -name shard.json | sort)
if [[ "${#shards[@]}" != "18" ]]; then
  echo "expected 18 shard receipts, found ${#shards[@]}" >&2
  exit 4
fi

failed_logs=0
for log in "${run_dir}"/logs/*.log; do
  if grep -Eq 'Traceback|Error|FAILED|Killed' "${log}"; then
    echo "error marker in ${log}" >&2
    failed_logs=$((failed_logs + 1))
  fi
done
if [[ "${failed_logs}" != "0" ]]; then
  echo "refusing merge because ${failed_logs} logs contain error markers" >&2
  exit 5
fi

if [[ -e "${run_dir}/merged" || -L "${run_dir}/merged" ]]; then
  echo "refusing to overwrite ${run_dir}/merged" >&2
  exit 6
fi

cd "${run_root}"
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 PYTHONPATH=src \
  "${python_bin}" "${runner}" merge \
    --shards "${shards[@]}" \
    --output run-v012/merged \
    --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
    --prereg artifacts/PREREG-FROZEN-2026-08-25-R2.json \
    --v03-root artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1

sha256sum run-v012/merged/result.json
