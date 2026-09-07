#!/usr/bin/env bash
set -euo pipefail

e1_repo_root="${1:?repository root is required}"
e1_generation_pid="${2:?generation PID is required}"
e1_python="${3:?Python executable is required}"
e1_source_root="${4:?source authority root is required}"
e1_tle_root="${5:?TLE root is required}"

e1_log_root="${e1_repo_root}/logs"
e1_runner="${e1_repo_root}/.scratch/ee-axis-redesign/run_v03_e1_fresh_sources.py"
e1_ladder="${e1_repo_root}/.scratch/ee-axis-redesign/run_v03_e1_validation_ladder.py"

mkdir -p "${e1_log_root}"

while kill -0 "${e1_generation_pid}" 2>/dev/null; do
  sleep 60
done

cd "${e1_repo_root}"

env PYTHONPATH=src "${e1_python}" "${e1_runner}" verify \
  --output-dir "${e1_source_root}" \
  --tle-root "${e1_tle_root}" \
  >"${e1_log_root}/e1-source-verify.log" 2>&1

e1_receipt_path="${e1_source_root}/source-data/receipt.json"
test -f "${e1_receipt_path}"
e1_receipt_sha256="$(sha256sum "${e1_receipt_path}" | cut -d ' ' -f 1)"
test "${#e1_receipt_sha256}" -eq 64
printf '%s\n' "${e1_receipt_sha256}" >"${e1_log_root}/e1-source-receipt.sha256"

env PYTHONPATH=src "${e1_python}" "${e1_ladder}" \
  --source-root "${e1_source_root}" \
  --output-dir "${e1_source_root}/ladder-authority" \
  --expected-source-receipt-sha256 "${e1_receipt_sha256}" \
  --device cpu \
  >"${e1_log_root}/e1-validation-ladder.log" 2>&1

printf '%s\n' "PIPELINE_COMPLETED" >"${e1_log_root}/e1-pipeline.status"
