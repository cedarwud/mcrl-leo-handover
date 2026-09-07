#!/usr/bin/env bash
set -euo pipefail

# Template only.  This launcher has no production world, lineage, seed,
# threshold, episode, or TEST default.  A separately frozen learner contract
# and an explicit pre-outcome config are required before it can launch.

server_host="${V018R_SERVER_HOST:-sat}"
server_root="${V018R_SERVER_ROOT:-}"
python_bin="${V018R_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
contract_rel="${V018R_LEARNER_CONTRACT:-}"
contract_expected="${V018R_LEARNER_CONTRACT_SHA256:-}"
code_manifest_rel="${V018R_CODE_MANIFEST:-}"
code_manifest_expected="${V018R_CODE_MANIFEST_SHA256:-}"
runner_rel="${V018R_LEARNER_RUNNER:-}"
config_rel="${V018R_LEARNER_RUN_CONFIG:-}"
output_rel="${V018R_LEARNER_RUN_OUTPUT:-}"
log_rel="${V018R_LEARNER_RUN_LOG:-}"
tmux_session="${V018R_LEARNER_TMUX_SESSION:-}"

fail_closed() {
  echo "V018 relational learner launch is fail-closed: $*" >&2
  exit 2
}

[[ -n "${contract_rel}" ]] || fail_closed "V018R_LEARNER_CONTRACT is not set"
[[ -n "${server_root}" ]] || fail_closed "V018R_SERVER_ROOT is not set"
[[ "${server_root}" = /* && "${server_root}" != "/" ]] || fail_closed "V018R_SERVER_ROOT must be a non-root absolute path"
[[ -n "${contract_expected}" ]] || fail_closed "V018R_LEARNER_CONTRACT_SHA256 is not set"
[[ -n "${code_manifest_rel}" ]] || fail_closed "V018R_CODE_MANIFEST is not set"
[[ -n "${code_manifest_expected}" ]] || fail_closed "V018R_CODE_MANIFEST_SHA256 is not set"
[[ -n "${runner_rel}" ]] || fail_closed "V018R_LEARNER_RUNNER is not set"
[[ -n "${config_rel}" ]] || fail_closed "V018R_LEARNER_RUN_CONFIG is not set"
[[ -n "${output_rel}" ]] || fail_closed "V018R_LEARNER_RUN_OUTPUT is not set"
[[ -n "${log_rel}" ]] || fail_closed "V018R_LEARNER_RUN_LOG is not set"
[[ -n "${tmux_session}" ]] || fail_closed "V018R_LEARNER_TMUX_SESSION is not set"
[[ "${contract_expected}" =~ ^[0-9a-f]{64}$ ]] || fail_closed "learner contract digest is not lowercase SHA-256"
[[ "${code_manifest_expected}" =~ ^[0-9a-f]{64}$ ]] || fail_closed "code manifest digest is not lowercase SHA-256"
[[ "${tmux_session}" =~ ^[A-Za-z0-9_.-]+$ ]] || fail_closed "tmux session contains unsafe characters"

validate_relative() {
  local field="$1"
  local value="$2"
  case "${value}" in
    /*|..|../*|*/../*|*/..)
      fail_closed "${field} must stay below the isolated server root: ${value}"
      ;;
  esac
}
for pair in \
  "contract:${contract_rel}" \
  "code-manifest:${code_manifest_rel}" \
  "runner:${runner_rel}" \
  "config:${config_rel}" \
  "output:${output_rel}" \
  "log:${log_rel}"; do
  field="${pair%%:*}"
  value="${pair#*:}"
  validate_relative "${field}" "${value}"
done

ssh "${server_host}" "
  set -euo pipefail
  cd '${server_root}'
  test -f '${contract_rel}' && test ! -L '${contract_rel}'
  grep -Fq FROZEN_BEFORE_OUTCOME '${contract_rel}'
  test \"\$(sha256sum '${contract_rel}' | awk '{print \$1}')\" = '${contract_expected}'
  cd \"\$(dirname '${code_manifest_rel}')\"
  sha256sum -c \"\$(basename '${code_manifest_rel}')\"
  cd '${server_root}'
  test -f '${runner_rel}' && test ! -L '${runner_rel}'
  test -f '${config_rel}' && test ! -L '${config_rel}'
  test ! -e '${output_rel}' && test ! -L '${output_rel}'
  test ! -e '${log_rel}' && test ! -L '${log_rel}'
  mkdir -p \"\$(dirname '${output_rel}')\" \"\$(dirname '${log_rel}')\"
  if tmux has-session -t '${tmux_session}' 2>/dev/null; then
    echo 'refusing to overwrite an existing learner tmux session' >&2
    exit 3
  fi
  tmux new-session -d -s '${tmux_session}' -c '${server_root}' \
    \"env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=src '${python_bin}' '${runner_rel}' --contract '${contract_rel}' --config '${config_rel}' --output '${output_rel}' > '${log_rel}' 2>&1\"
"

echo "V018 relational learner template launched in ${server_host}:${server_root} (tmux ${tmux_session})"
