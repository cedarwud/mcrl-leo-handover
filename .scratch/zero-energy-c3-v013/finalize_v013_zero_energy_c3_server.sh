#!/usr/bin/env bash
set -euo pipefail

run_root="${1:-/home/sat/mcrl-zero-energy-c3-v013-20260903-r1}"
run_dir="${run_root}/run-v013"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
runner=".scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py"
contract_path="${V013_CONTRACT_PATH:-docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md}"
tle_root="${V013_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
prereg_path="${V013_PREREG_PATH:-artifacts/PREREG-FROZEN-2026-08-25-R2.json}"
v03_root="${V013_V03_ROOT:-artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1}"
authority_path="${V013_AUTHORITY_PATH:-artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/FROZEN-AUTHORITY.json}"

if [[ ! -d "${run_dir}/shards" || ! -d "${run_dir}/logs" ]]; then
  echo "missing V0.13 run directories under ${run_dir}" >&2
  exit 2
fi

marker="${run_dir}/controller.complete"
if [[ ! -f "${marker}" || -L "${marker}" ]]; then
  echo "V0.13 controller did not record a regular completion marker" >&2
  exit 3
fi

mapfile -t marker_lines < "${marker}"
if [[ "${#marker_lines[@]}" != "3" \
  || "${marker_lines[0]}" != "schema=multi-catfish-mcrl-v013-panel-complete-v1" \
  || "${marker_lines[1]}" != "task_count=24" \
  || "${marker_lines[2]}" != max_parallel=* ]]; then
  echo "V0.13 controller completion marker is malformed" >&2
  exit 4
fi
marker_max_parallel="${marker_lines[2]#max_parallel=}"
if [[ ! "${marker_max_parallel}" =~ ^[0-9]+$ ]] \
  || (( marker_max_parallel < 1 || marker_max_parallel > 20 )); then
  echo "V0.13 controller completion marker has invalid max_parallel" >&2
  exit 5
fi
if [[ -n "${V013_MAX_PARALLEL:-}" && "${marker_max_parallel}" != "${V013_MAX_PARALLEL}" ]]; then
  echo "V0.13 completion marker max_parallel disagrees with requested setting" >&2
  exit 6
fi

active="$(tmux list-sessions 2>/dev/null | grep -c '^v013-' || true)"
if [[ "${active}" != "0" ]]; then
  echo "V0.13 still has ${active} active shard sessions" >&2
  exit 7
fi

worlds=(2026104901 2026104902 2026104903 2026104904)
arms=(DROP_C3 FULL_ZR)
lineages=(2026092101 2026092102 2026092103)
shards=()
logs=()
for world in "${worlds[@]}"; do
  for arm in "${arms[@]}"; do
    for lineage in "${lineages[@]}"; do
      shard_dir="${run_dir}/shards/${world}-${arm}-${lineage}"
      shard_file="${shard_dir}/shard.json"
      log_file="${run_dir}/logs/${world}-${arm}-${lineage}.log"
      if [[ ! -d "${shard_dir}" || -L "${shard_dir}" \
        || ! -f "${shard_file}" || -L "${shard_file}" ]]; then
        echo "missing or non-regular shard receipt ${shard_file}" >&2
        exit 8
      fi
      mapfile -t shard_entries < <(find "${shard_dir}" -mindepth 1 -maxdepth 1 -print)
      if [[ "${#shard_entries[@]}" != "1" || "${shard_entries[0]}" != "${shard_file}" ]]; then
        echo "shard directory is not canonical ${shard_dir}" >&2
        exit 9
      fi
      if [[ ! -f "${log_file}" || -L "${log_file}" || ! -s "${log_file}" ]]; then
        echo "missing, symlinked, or empty shard log ${log_file}" >&2
        exit 10
      fi
      shards+=("${shard_file}")
      logs+=("${log_file}")
    done
  done
done

mapfile -t shard_dirs < <(find "${run_dir}/shards" -mindepth 1 -maxdepth 1 -print | sort)
if [[ "${#shard_dirs[@]}" != "24" ]]; then
  echo "expected exactly 24 canonical shard directories, found ${#shard_dirs[@]}" >&2
  exit 11
fi

mapfile -t log_entries < <(find "${run_dir}/logs" -mindepth 1 -maxdepth 1 -print | sort)
if [[ "${#log_entries[@]}" != "24" ]]; then
  echo "expected exactly 24 canonical shard logs, found ${#log_entries[@]}" >&2
  exit 12
fi

failed_logs=0
for log in "${logs[@]}"; do
  if grep -Eq 'Traceback|Error|FAILED|Killed' "${log}"; then
    echo "error marker in ${log}" >&2
    failed_logs=$((failed_logs + 1))
  fi
done
if [[ "${failed_logs}" != "0" ]]; then
  echo "refusing merge because ${failed_logs} logs contain error markers" >&2
  exit 13
fi

if [[ -e "${run_dir}/merged" || -L "${run_dir}/merged" ]]; then
  echo "refusing to overwrite ${run_dir}/merged" >&2
  exit 14
fi

cd "${run_root}"
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 PYTHONPATH=src \
  "${python_bin}" "${runner}" merge \
    --shards "${shards[@]}" \
    --output run-v013/merged \
    --tle-root "${tle_root}" \
    --prereg "${prereg_path}" \
    --v03-root "${v03_root}" \
    --contract "${contract_path}" \
    --authority "${authority_path}"

sha256sum run-v013/merged/result.json
