#!/usr/bin/env bash
set -euo pipefail

run_root="${1:?run root is required}"
run_dir="${run_root}/run-v013"
max_parallel="${V013_MAX_PARALLEL:-18}"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
runner=".scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py"
contract_path="${V013_CONTRACT_PATH:-docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md}"
tle_root="${V013_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
prereg_path="${V013_PREREG_PATH:-artifacts/PREREG-FROZEN-2026-08-25-R2.json}"
v03_root="${V013_V03_ROOT:-artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1}"
authority_path="${V013_AUTHORITY_PATH:-artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/FROZEN-AUTHORITY.json}"

if [[ ! "${max_parallel}" =~ ^[0-9]+$ ]] || (( max_parallel < 1 || max_parallel > 20 )); then
  echo "V013_MAX_PARALLEL must be an integer from 1 through 20" >&2
  exit 2
fi

if [[ ! -d "${run_root}" || -L "${run_root}" ]]; then
  echo "missing isolated V0.13 run root ${run_root}" >&2
  exit 3
fi

if [[ -e "${run_dir}" || -L "${run_dir}" ]]; then
  echo "refusing to overwrite existing V0.13 run directory ${run_dir}" >&2
  exit 4
fi

mkdir "${run_dir}"
mkdir "${run_dir}/logs" "${run_dir}/shards"

run_one() {
  local world="${1:?world is required}"
  local arm="${2:?arm is required}"
  local lineage="${3:?lineage is required}"
  local output="run-v013/shards/${world}-${arm}-${lineage}"
  local log="run-v013/logs/${world}-${arm}-${lineage}.log"

  if [[ -e "${output}" || -L "${output}" || -e "${log}" || -L "${log}" ]]; then
    echo "refusing to overwrite shard output or log for ${world}/${arm}/${lineage}" >&2
    return 5
  fi

  env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 PYTHONPATH=src \
    "${python_bin}" "${runner}" shard \
      --world "${world}" \
      --arm "${arm}" \
      --lineage "${lineage}" \
      --tle-root "${tle_root}" \
      --prereg "${prereg_path}" \
      --v03-root "${v03_root}" \
      --contract "${contract_path}" \
      --authority "${authority_path}" \
      --output "${output}" > "${log}" 2>&1
}

export -f run_one
export python_bin runner contract_path authority_path tle_root prereg_path v03_root

worlds=(2026104901 2026104902 2026104903 2026104904)
arms=(DROP_C3 FULL_ZR)
lineages=(2026092101 2026092102 2026092103)
task_count=$(( ${#worlds[@]} * ${#arms[@]} * ${#lineages[@]} ))

if [[ -e "${run_dir}/controller.complete" || -L "${run_dir}/controller.complete" ]]; then
  echo "refusing to overwrite controller completion marker" >&2
  exit 6
fi

cd "${run_root}"
for world in "${worlds[@]}"; do
  for arm in "${arms[@]}"; do
    for lineage in "${lineages[@]}"; do
      printf '%s\0%s\0%s\0' "${world}" "${arm}" "${lineage}"
    done
  done
done | xargs -0 -n 3 -P "${max_parallel}" bash -c 'run_one "$1" "$2" "$3"' _

if [[ -e "${run_dir}/controller.complete" || -L "${run_dir}/controller.complete" ]]; then
  echo "refusing to overwrite controller completion marker" >&2
  exit 7
fi

(
  set -C
  printf 'schema=multi-catfish-mcrl-v013-panel-complete-v1\ntask_count=%s\nmax_parallel=%s\n' \
    "${task_count}" "${max_parallel}" > "${run_dir}/controller.complete"
)
