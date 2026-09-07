#!/usr/bin/env bash
set -euo pipefail

# Fetch and independently verify the completed V0.20 C3 matched gate.  This
# script is intentionally read-only toward the server and fail-closed locally.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V020_SERVER_HOST:-sat}"
server_root="${V020_SERVER_ROOT:-/home/sat/mcrl-v020-repriced-c3-gate-20260904-r1}"
remote_run="${server_root}/artifacts/multi-catfish-v020-repriced-c3-gate-20260904-r1/server-run"
local_parent="${repo_root}/artifacts/multi-catfish-v020-repriced-c3-gate-20260904-r1"
local_run="${local_parent}/server-run"
staging="${local_parent}/.server-run.staging"
python_bin="${repo_root}/.venv/bin/python"
verifier="${repo_root}/.scratch/multi-catfish-v020-c3-source-audit/verify_v020_repriced_c3_gate.py"

if [[ -e "${local_run}" || -L "${local_run}" || -e "${staging}" || -L "${staging}" ]]; then
  echo "refusing to overwrite local result or staging directory" >&2
  exit 2
fi
if [[ ! -x "${python_bin}" || ! -f "${verifier}" || -L "${verifier}" ]]; then
  echo "missing local verifier or Python environment" >&2
  exit 2
fi

ssh "${server_host}" \
  "set -e; test -f '${remote_run}/COMPLETE'; test ! -L '${remote_run}/COMPLETE'; cd '${remote_run}'; sha256sum -c RESULTS.sha256"

mkdir -p "${local_parent}"
mkdir "${staging}"
rsync -a "${server_host}:${remote_run}/" "${staging}/"

"${python_bin}" "${verifier}" --run-root "${staging}" \
  > "${staging}/independent-verification.json"
(
  cd "${staging}"
  sha256sum \
    result/result.json \
    result/result-seal.json \
    independent-verification.json \
    > FETCHED-SERVER-RESULTS.sha256
)

mv "${staging}" "${local_run}"
echo "V020_REPRICED_C3_GATE_FETCHED ${local_run}"
