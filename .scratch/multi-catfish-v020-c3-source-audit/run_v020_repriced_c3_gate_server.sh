#!/usr/bin/env bash
set -euo pipefail

# Execute the frozen 4-world x 3-arm x 3-lineage V0.20 C3 gate inside an
# isolated Ubuntu-server checkout.  Scheduling order starts every expensive
# BASE shard first; it does not alter any scientific input or outcome.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${V020_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
tle_root="${V020_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
run_dir="${V020_RUN_DIR:-${repo_root}/artifacts/multi-catfish-v020-repriced-c3-gate-20260904-r1/server-run}"
runner="${repo_root}/.scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py"
max_parallel="${V020_MAX_PARALLEL:-18}"

worlds=(2026121501 2026121502 2026121503 2026121504)
arms=(BASE EXACT_ZR NOMINAL_ZR)
lineages=(2026092101 2026092102 2026092103)

if [[ ! -x "${python_bin}" ]]; then
  echo "missing Python environment: ${python_bin}" >&2
  exit 2
fi
if [[ ! -d "${tle_root}" || -L "${tle_root}" ]]; then
  echo "missing or symlinked TLE root: ${tle_root}" >&2
  exit 2
fi
if [[ ! "${max_parallel}" =~ ^[0-9]+$ ]] || (( max_parallel < 1 || max_parallel > 20 )); then
  echo "V020_MAX_PARALLEL must be an integer from 1 through 20" >&2
  exit 2
fi
if [[ -e "${run_dir}" || -L "${run_dir}" ]]; then
  echo "refusing to overwrite existing run directory: ${run_dir}" >&2
  exit 3
fi

cd "${repo_root}"

# Cheap server-side authentication and focused mechanics tests precede every
# physical shard.  These do not open a world or perform learner updates.
env PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 "${python_bin}" -m py_compile "${runner}"
env PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 "${python_bin}" -m pytest -q \
  .scratch/multi-catfish-v020-c3-source-audit/test_v020_canonical_serializer.py \
  tests/test_w140_ee_axis_zero_marginal_c3.py \
  tests/test_w141_ee_axis_zero_marginal_c3_live.py \
  tests/test_w148_ee_axis_v014_q2_state.py \
  tests/test_w173_ee_axis_relational_zr_c3.py \
  tests/test_w174_ee_axis_v018_gate.py
env PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 "${python_bin}" -c \
  "import importlib.util,pathlib,sys; p=pathlib.Path('${runner}'); s=importlib.util.spec_from_file_location('v020_preflight',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); assert m._validate_global_inputs()['status']=='GO_MATCHED_C3_GATE'; [m.load_repriced_heads(i) for i in m.LINEAGES]; m._load_module('v020_preflight_v018', m.V018_PATH); print('V020_SERVER_PREFLIGHT_OK')"

mkdir -p "$(dirname "${run_dir}")"
mkdir "${run_dir}"
mkdir "${run_dir}/logs" "${run_dir}/shards"

run_one() {
  local world="${1:?world required}"
  local arm="${2:?arm required}"
  local lineage="${3:?lineage required}"
  local output="${run_dir}/shards/${world}-${arm}-${lineage}"
  local log="${run_dir}/logs/${world}-${arm}-${lineage}.log"
  if [[ -e "${output}" || -L "${output}" || -e "${log}" || -L "${log}" ]]; then
    echo "duplicate shard target: ${world}/${arm}/${lineage}" >&2
    return 4
  fi
  set -C
  env PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 "${python_bin}" "${runner}" shard \
      --world "${world}" \
      --arm "${arm}" \
      --lineage "${lineage}" \
      --tle-root "${tle_root}" \
      --prereg artifacts/PREREG-FROZEN-2026-08-25-R2.json \
      --output "${output}" > "${log}" 2>&1
}

export -f run_one
export repo_root python_bin tle_root run_dir runner

task_count=$(( ${#worlds[@]} * ${#arms[@]} * ${#lineages[@]} ))
if (( task_count != 36 )); then
  echo "frozen panel must contain exactly 36 shards" >&2
  exit 5
fi

# BASE is the slow diagnostic arm.  Launch all BASE shards first so the
# server's remaining cores can drain the shorter exact/nominal arms in
# parallel without extending the critical path.
for arm in "${arms[@]}"; do
  for world in "${worlds[@]}"; do
    for lineage in "${lineages[@]}"; do
      printf '%s\0%s\0%s\0' "${world}" "${arm}" "${lineage}"
    done
  done
done | xargs -0 -n 3 -P "${max_parallel}" bash -c 'run_one "$1" "$2" "$3"' _

merge_args=()
for arm in "${arms[@]}"; do
  for world in "${worlds[@]}"; do
    for lineage in "${lineages[@]}"; do
      shard="${run_dir}/shards/${world}-${arm}-${lineage}/shard.json"
      log="${run_dir}/logs/${world}-${arm}-${lineage}.log"
      if [[ ! -s "${shard}" || -L "${shard}" || ! -s "${log}" || -L "${log}" ]]; then
        echo "missing canonical shard or log: ${world}/${arm}/${lineage}" >&2
        exit 6
      fi
      merge_args+=(--shard "${shard}")
    done
  done
done

env PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 "${python_bin}" "${runner}" merge \
  "${merge_args[@]}" --output "${run_dir}/result" \
  > "${run_dir}/merge.log" 2>&1

sha256sum "${run_dir}/result/result.json" "${run_dir}/result/result-seal.json" \
  > "${run_dir}/RESULTS.sha256"
touch "${run_dir}/COMPLETE"
echo "V020_REPRICED_C3_GATE_COMPLETE ${run_dir}"
