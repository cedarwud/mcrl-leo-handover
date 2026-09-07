#!/usr/bin/env bash
set -euo pipefail

# Template only.  It is intentionally unusable until a separately authored
# learner contract is frozen before outcomes.  In particular, this script has
# no world, lineage, seed, threshold, simulator, or TEST default.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
server_host="${V018R_SERVER_HOST:-sat}"
server_root="${V018R_SERVER_ROOT:-}"
python_bin="${V018R_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
contract_rel="${V018R_LEARNER_CONTRACT:-}"
contract_expected="${V018R_LEARNER_CONTRACT_SHA256:-}"
code_manifest_rel="${V018R_CODE_MANIFEST:-}"
code_manifest_expected="${V018R_CODE_MANIFEST_SHA256:-}"
runner_rel="${V018R_LEARNER_RUNNER:-}"
preflight_tests="${V018R_PREFLIGHT_TESTS:-.scratch/multi-catfish-v018-relational-zr/next-learner-draft/tests/test_next_learner_draft.py}"

fail_closed() {
  echo "V018 relational learner sync is fail-closed: $*" >&2
  exit 2
}

[[ -n "${contract_rel}" ]] || fail_closed "V018R_LEARNER_CONTRACT is not set"
[[ -n "${server_root}" ]] || fail_closed "V018R_SERVER_ROOT is not set"
[[ "${server_root}" = /* && "${server_root}" != "/" ]] || fail_closed "V018R_SERVER_ROOT must be a non-root absolute path"
[[ -n "${contract_expected}" ]] || fail_closed "V018R_LEARNER_CONTRACT_SHA256 is not set"
[[ -n "${code_manifest_rel}" ]] || fail_closed "V018R_CODE_MANIFEST is not set"
[[ -n "${code_manifest_expected}" ]] || fail_closed "V018R_CODE_MANIFEST_SHA256 is not set"
[[ -n "${runner_rel}" ]] || fail_closed "V018R_LEARNER_RUNNER is not set"
[[ "${contract_expected}" =~ ^[0-9a-f]{64}$ ]] || fail_closed "learner contract digest is not lowercase SHA-256"
[[ "${code_manifest_expected}" =~ ^[0-9a-f]{64}$ ]] || fail_closed "code manifest digest is not lowercase SHA-256"

resolve_repo_file() {
  local relative="$1"
  [[ "${relative}" != /* ]] || fail_closed "paths must be repository-relative: ${relative}"
  local resolved="${repo_root}/${relative}"
  [[ -f "${resolved}" && ! -L "${resolved}" ]] || fail_closed "missing or symlinked file: ${relative}"
  printf '%s\n' "${resolved}"
}

contract_file="$(resolve_repo_file "${contract_rel}")"
code_manifest_file="$(resolve_repo_file "${code_manifest_rel}")"
runner_file="$(resolve_repo_file "${runner_rel}")"
grep -Eq '^Status:[[:space:]]*`FROZEN_BEFORE_OUTCOME`[[:space:]]*\.?[[:space:]]*$' "${contract_file}" \
  || fail_closed "learner contract is not marked FROZEN_BEFORE_OUTCOME"
actual_contract="$(sha256sum "${contract_file}" | awk '{print $1}')"
[[ "${actual_contract}" == "${contract_expected}" ]] || fail_closed "learner contract digest mismatch"
actual_manifest="$(sha256sum "${code_manifest_file}" | awk '{print $1}')"
[[ "${actual_manifest}" == "${code_manifest_expected}" ]] || fail_closed "code manifest digest mismatch"

# Baseline is deliberately limited to pure code, the draft seam, and tests.
# A future runner can add old helper roots through V018R_EXTRA_PATHS after the
# frozen contract explicitly names them; no production data is implicit here.
sync_paths=(
  pyproject.toml
  src
  .scratch/multi-catfish-v018-relational-zr/next-learner-draft
  "${contract_rel}"
  "${code_manifest_rel}"
  "${runner_rel}"
)
if [[ -n "${V018R_EXTRA_PATHS:-}" ]]; then
  read -r -a extra_paths <<< "${V018R_EXTRA_PATHS}"
  sync_paths+=("${extra_paths[@]}")
fi
for path in "${sync_paths[@]}"; do
  [[ "${path}" != /* ]] || fail_closed "sync path must be repository-relative: ${path}"
  [[ -e "${repo_root}/${path}" && ! -L "${repo_root}/${path}" ]] \
    || fail_closed "sync path is missing or symlinked: ${path}"
done

if ssh "${server_host}" "test -e '${server_root}'"; then
  fail_closed "refusing to overwrite existing ${server_host}:${server_root}"
fi
ssh "${server_host}" "mkdir -p '${server_root}'"
rsync -aR --exclude='__pycache__/' --exclude='*.pyc' \
  "${sync_paths[@]}" "${server_host}:${server_root}/"

ssh "${server_host}" "
  set -euo pipefail
  cd '${server_root}'
  test -f '${contract_rel}' && test ! -L '${contract_rel}'
  grep -Fq FROZEN_BEFORE_OUTCOME '${contract_rel}'
  test \"\$(sha256sum '${contract_rel}' | awk '{print \$1}')\" = '${contract_expected}'
  cd \"\$(dirname '${code_manifest_rel}')\"
  sha256sum -c \"\$(basename '${code_manifest_rel}')\"
  cd '${server_root}'
  env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    PYTHONPATH=src '${python_bin}' -m pytest -q ${preflight_tests}
"

echo "V018 relational learner code synced and pure preflight passed: ${server_host}:${server_root}"
