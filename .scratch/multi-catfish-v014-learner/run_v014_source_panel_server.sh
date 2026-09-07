#!/usr/bin/env bash
set -euo pipefail

run_root="${1:?isolated V0.14 server root is required}"
run_dir="${run_root}/source-panel"
max_parallel="${V014_MAX_PARALLEL:-18}"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
runner=".scratch/multi-catfish-v014-learner/run_v014_source_shard.py"
contract="artifacts/multi-catfish-v014-learnability-20260903-r1/contracts/MULTI-CATFISH-MCRL-V014-LEARNABILITY-PREREG-2026-09-03.md"
contract_receipt="artifacts/multi-catfish-v014-learnability-20260903-r1/contracts/prereg.sha256"
tle_root="${V014_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
prereg="artifacts/PREREG-FROZEN-2026-08-25-R2.json"
v03_root="artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"

if [[ ! "${max_parallel}" =~ ^[0-9]+$ ]] || (( max_parallel < 1 || max_parallel > 18 )); then
  echo "V014_MAX_PARALLEL must be an integer from 1 through 18" >&2
  exit 2
fi
if [[ ! -d "${run_root}" || -L "${run_root}" ]]; then
  echo "missing isolated V0.14 root ${run_root}" >&2
  exit 3
fi
if [[ -e "${run_dir}" || -L "${run_dir}" ]]; then
  echo "refusing to overwrite ${run_dir}" >&2
  exit 4
fi

cd "${run_root}"
(
  cd "$(dirname "${contract}")"
  sha256sum -c "$(basename "${contract_receipt}")"
)
mkdir "${run_dir}"
mkdir "${run_dir}/logs" "${run_dir}/shards"

run_one() {
  local world="${1:?world is required}"
  local lineage="${2:?lineage is required}"
  local output="source-panel/shards/${world}-${lineage}"
  local log="source-panel/logs/${world}-${lineage}.log"
  env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 PYTHONPATH=src \
    "${python_bin}" "${runner}" harvest \
      --world-seed "${world}" \
      --lineage "${lineage}" \
      --steps 10 \
      --tle-root "${tle_root}" \
      --prereg "${prereg}" \
      --v03-root "${v03_root}" \
      --output "${output}" > "${log}" 2>&1
}

export -f run_one
export python_bin runner tle_root prereg v03_root
worlds=(2026108001 2026108002 2026108003 2026108004 2026108005 2026108006 2026108007)
lineages=(2026092101 2026092102 2026092103)
task_count=$(( ${#worlds[@]} * ${#lineages[@]} ))

for world in "${worlds[@]}"; do
  for lineage in "${lineages[@]}"; do
    printf '%s\0%s\0' "${world}" "${lineage}"
  done
done | xargs -0 -n 2 -P "${max_parallel}" bash -c 'run_one "$1" "$2"' _

(
  set -C
  printf 'schema=multi-catfish-mcrl-v014-source-panel-complete-v1\ntask_count=%s\nmax_parallel=%s\n' \
    "${task_count}" "${max_parallel}" > "${run_dir}/controller.complete"
)

