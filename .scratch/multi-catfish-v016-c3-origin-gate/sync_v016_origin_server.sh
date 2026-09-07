#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V016O_SERVER_HOST:-sat}"
server_root="${V016O_SERVER_ROOT:-/home/sat/mcrl-v016-c3-origin-gate-20260903-r1}"
contract="artifacts/multi-catfish-v016-c3-origin-gate-20260903-r1/contracts/MULTI-CATFISH-MCRL-V016-C3-ORIGIN-GATE-PREREG-2026-09-03.md"
contract_receipt="artifacts/multi-catfish-v016-c3-origin-gate-20260903-r1/contracts/prereg.sha256"

cd "${repo_root}"
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
  scripts/run_head_pivotality_probe.py \
  tests/test_w140_ee_axis_zero_marginal_c3.py \
  tests/test_w141_ee_axis_zero_marginal_c3_live.py \
  tests/test_w146_ee_axis_v014_q3_state.py \
  tests/test_w148_ee_axis_v014_q2_state.py \
  tests/test_w159_ee_axis_v015_c3_csr.py \
  tests/test_w160_ee_axis_v015_c3_state.py \
  tests/test_w161_ee_axis_v015_c3_selector.py \
  tests/test_w162_ee_axis_v015_c3_pivotal.py \
  tests/test_w163_ee_axis_v015_c3_reference_state.py \
  tests/test_w166_ee_axis_v016_c3_origin_state.py \
  tests/test_w167_ee_axis_v016_c3_origin_source_shard.py \
  tests/test_w168_ee_axis_v016_c3_origin_gate.py \
  .scratch/c3-v04 \
  .scratch/zero-energy-c3-v013 \
  .scratch/multi-catfish-v015-c3-learned-context \
  .scratch/multi-catfish-v016-c3-origin-gate \
  artifacts/multi-catfish-v016-c3-origin-gate-20260903-r1/contracts \
  artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1 \
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate \
  "${server_host}:${server_root}/"

ssh "${server_host}" "cd '${server_root}' && (cd \"\$(dirname '${contract}')\" && sha256sum -c \"\$(basename '${contract_receipt}')\") && env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/test_w140_ee_axis_zero_marginal_c3.py tests/test_w141_ee_axis_zero_marginal_c3_live.py tests/test_w146_ee_axis_v014_q3_state.py tests/test_w148_ee_axis_v014_q2_state.py tests/test_w159_ee_axis_v015_c3_csr.py tests/test_w160_ee_axis_v015_c3_state.py tests/test_w161_ee_axis_v015_c3_selector.py tests/test_w162_ee_axis_v015_c3_pivotal.py tests/test_w163_ee_axis_v015_c3_reference_state.py tests/test_w166_ee_axis_v016_c3_origin_state.py tests/test_w167_ee_axis_v016_c3_origin_source_shard.py tests/test_w168_ee_axis_v016_c3_origin_gate.py"
