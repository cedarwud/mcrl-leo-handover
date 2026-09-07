#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V014_SERVER_HOST:-sat}"
server_root="${V014_SERVER_ROOT:-/home/sat/mcrl-v014-learnability-20260903-r1}"
contract="artifacts/multi-catfish-v014-learnability-20260903-r1/contracts/MULTI-CATFISH-MCRL-V014-LEARNABILITY-PREREG-2026-09-03.md"
contract_receipt="artifacts/multi-catfish-v014-learnability-20260903-r1/contracts/prereg.sha256"

cd "${repo_root}"
grep -Fq 'Status: **FROZEN BEFORE FRESH SOURCE ACCESS**' "${contract}" || {
  echo "refusing sync because the V0.14 contract is not frozen" >&2
  exit 1
}
(
  cd "$(dirname "${contract}")"
  sha256sum -c "$(basename "${contract_receipt}")"
)

if ssh "${server_host}" "test -e '${server_root}'"; then
  echo "refusing to overwrite existing ${server_host}:${server_root}" >&2
  exit 2
fi

ssh "${server_host}" "mkdir -p '${server_root}'"
rsync -aR \
  pyproject.toml \
  src \
  scripts \
  tests \
  .scratch/c3-v04 \
  .scratch/zero-energy-c3-v013 \
  .scratch/multi-catfish-v014-learner \
  "${contract}" \
  "${contract_receipt}" \
  artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1 \
  "${server_host}:${server_root}/"

ssh "${server_host}" "cd '${server_root}' && (cd \"\$(dirname '${contract}')\" && sha256sum -c \"\$(basename '${contract_receipt}')\") && env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/test_w146_ee_axis_v014_q3_state.py tests/test_w147_ee_axis_v014_head.py tests/test_w148_ee_axis_v014_q2_state.py tests/test_w149_ee_axis_v014_q2_pairs.py tests/test_w150_ee_axis_v014_q3_pairs.py tests/test_w151_v014_source_shard.py tests/test_w152_ee_axis_v014_learnability.py tests/test_w153_ee_axis_v014_gate.py tests/test_w154_v014_learnability_gate_runner.py tests/test_w155_v014_five_arm_evaluation.py tests/test_w156_v014_learner_gate_verifier.py"
