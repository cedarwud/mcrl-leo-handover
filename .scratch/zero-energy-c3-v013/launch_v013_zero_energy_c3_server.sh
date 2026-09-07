#!/usr/bin/env bash
set -euo pipefail

run_root="${1:-/home/sat/mcrl-zero-energy-c3-v013-20260903-r1}"
run_dir="${run_root}/run-v013"
python_bin="/home/sat/mcrl-leo-handover/.venv/bin/python"
panel_runner=".scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_panel_server.sh"
runner=".scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py"
contract_path="${V013_CONTRACT_PATH:-docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md}"
tle_root="${V013_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
prereg_path="${V013_PREREG_PATH:-artifacts/PREREG-FROZEN-2026-08-25-R2.json}"
v03_root="${V013_V03_ROOT:-artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1}"
authority_path="${V013_AUTHORITY_PATH:-artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/FROZEN-AUTHORITY.json}"
max_parallel="${V013_MAX_PARALLEL:-18}"

if [[ ! "${max_parallel}" =~ ^[0-9]+$ ]] || (( max_parallel < 1 || max_parallel > 20 )); then
  echo "V013_MAX_PARALLEL must be an integer from 1 through 20" >&2
  exit 1
fi

if [[ ! -d "${run_root}" || -L "${run_root}" ]]; then
  echo "missing isolated V0.13 run root ${run_root}" >&2
  exit 2
fi

if [[ ! -x "${python_bin}" ]]; then
  echo "missing server Python ${python_bin}" >&2
  exit 3
fi

(
  cd "${run_root}"
  [[ -f "${panel_runner}" && -f "${runner}" && -f "${contract_path}" ]]
  [[ -f "${prereg_path}" && -d "${v03_root}" && -d "${tle_root}" ]]
  [[ -f "${authority_path}" && ! -L "${authority_path}" ]]
  grep -Fq 'Status: **FROZEN BEFORE OUTCOME ACCESS**' "${contract_path}"
  env PYTHONPATH=src "${python_bin}" "${runner}" verify-authority \
    --authority "${authority_path}" --prereg "${prereg_path}" \
    --v03-root "${v03_root}" --contract "${contract_path}" >/dev/null
) || {
  echo "V0.13 launch authority preflight failed" >&2
  exit 4
}

if [[ -e "${run_dir}" || -L "${run_dir}" ]]; then
  echo "refusing to overwrite ${run_dir}" >&2
  exit 5
fi

if [[ -e "${run_dir}/controller.complete" || -L "${run_dir}/controller.complete" ]]; then
  echo "refusing to overwrite controller completion marker" >&2
  exit 5
fi

if tmux has-session -t v013-controller 2>/dev/null; then
  echo "refusing to reuse active tmux session v013-controller" >&2
  exit 6
fi

tmux new-session -d -s v013-controller \
  "cd '${run_root}' && env V013_MAX_PARALLEL='${max_parallel}' V013_CONTRACT_PATH='${contract_path}' V013_AUTHORITY_PATH='${authority_path}' V013_TLE_ROOT='${tle_root}' V013_PREREG_PATH='${prereg_path}' V013_V03_ROOT='${v03_root}' bash '${panel_runner}' '${run_root}'"

echo "launched v013-controller with max parallelism ${max_parallel}"
