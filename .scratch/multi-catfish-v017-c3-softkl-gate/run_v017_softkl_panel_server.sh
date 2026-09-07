#!/usr/bin/env bash
set -euo pipefail

run_root="${1:?isolated V0.17 server root is required}"
run_dir="${run_root}/source-panel"
max_parallel="${V017K_MAX_PARALLEL:-18}"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
source_runner=".scratch/multi-catfish-v017-c3-softkl-gate/run_v017_softkl_source_shard.py"
gate_runner=".scratch/multi-catfish-v017-c3-softkl-gate/run_v017_softkl_gate.py"
contract="artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1/contracts/MULTI-CATFISH-MCRL-V017-C3-SOFTKL-GATE-PREREG-2026-09-03.md"
contract_receipt="artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1/contracts/prereg.sha256"
tle_root="${V017K_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
prereg="artifacts/PREREG-FROZEN-2026-08-25-R2.json"
v03_root="artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
q2_root="artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate"

if [[ ! "${max_parallel}" =~ ^[0-9]+$ ]] || (( max_parallel < 1 || max_parallel > 18 )); then
  echo "V017K_MAX_PARALLEL must be an integer from 1 through 18" >&2
  exit 2
fi
if [[ ! -d "${run_root}" || -L "${run_root}" ]]; then
  echo "missing isolated V0.17 root ${run_root}" >&2
  exit 3
fi
if [[ -e "${run_dir}" || -L "${run_dir}" || -e "${run_root}/learner-gate" ]]; then
  echo "refusing to overwrite an existing V0.17 run" >&2
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
    "${python_bin}" "${source_runner}" harvest \
      --world-seed "${world}" \
      --lineage "${lineage}" \
      --steps 10 \
      --tle-root "${tle_root}" \
      --prereg "${prereg}" \
      --v03-root "${v03_root}" \
      --q2-root "${q2_root}" \
      --contract "${contract}" \
      --output "${output}" > "${log}" 2>&1
}

export -f run_one
export python_bin source_runner tle_root prereg v03_root q2_root contract
worlds=(2026112001 2026112002 2026112003 2026112004 2026112005 2026112006)
lineages=(2026092101 2026092102 2026092103)
task_count=$(( ${#worlds[@]} * ${#lineages[@]} ))

for world in "${worlds[@]}"; do
  for lineage in "${lineages[@]}"; do
    printf '%s\0%s\0' "${world}" "${lineage}"
  done
done | xargs -0 -n 2 -P "${max_parallel}" bash -c 'run_one "$1" "$2"' _

(
  set -C
  printf 'schema=multi-catfish-mcrl-v017-c3-softkl-source-panel-complete-v1\ntask_count=%s\nmax_parallel=%s\n' \
    "${task_count}" "${max_parallel}" > "${run_dir}/controller.complete"
)

sources=()
for world in "${worlds[@]}"; do
  for lineage in "${lineages[@]}"; do
    sources+=(--source "source-panel/shards/${world}-${lineage}")
  done
done
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 PYTHONPATH=src \
  "${python_bin}" "${gate_runner}" \
    "${sources[@]}" --output learner-gate > learner-gate.log 2>&1
(
  set -C
  printf 'schema=multi-catfish-mcrl-v017-c3-softkl-panel-complete-v1\n' \
    > controller.complete
)
