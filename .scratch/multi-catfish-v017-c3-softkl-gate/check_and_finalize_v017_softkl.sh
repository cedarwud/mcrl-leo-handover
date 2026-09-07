#!/usr/bin/env bash
set -euo pipefail

repo_root="/home/u24/papers/mcrl-leo-handover"
server_host="sat"
server_root="/home/sat/mcrl-v017-c3-softkl-gate-20260903-r2"
session_name="mcrl-v017-softkl-r2"
artifact_root="${repo_root}/artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1"
result_path="${artifact_root}/server-run-r1/learner-gate/result.json"
monitor_root="${repo_root}/.scratch/multi-catfish-v017-c3-softkl-gate/monitor"

mkdir -p "${monitor_root}"
exec 9>"${monitor_root}/monitor.lock"
flock -n 9 || exit 0
if [[ -f "${monitor_root}/done" || -f "${monitor_root}/failed" ]]; then
  exit 0
fi

timestamp="$(date --iso-8601=seconds)"
if ssh "${server_host}" "test -f '${server_root}/controller.complete'"; then
  if [[ ! -f "${result_path}" ]]; then
    env V017K_SERVER_HOST="${server_host}" V017K_SERVER_ROOT="${server_root}" \
      "${repo_root}/.scratch/multi-catfish-v017-c3-softkl-gate/finalize_v017_softkl_server.sh"
  fi
  (
    cd "${artifact_root}"
    sha256sum -c MANIFEST-R1.sha256
  ) > "${monitor_root}/manifest-check.log"
  "${repo_root}/.venv/bin/python" \
    "${repo_root}/.scratch/multi-catfish-v017-c3-softkl-gate/verify_v017_softkl_result.py" \
    "${result_path}" > "${monitor_root}/final-verification.json"
  printf '%s complete and independently verified\n' "${timestamp}" \
    >> "${monitor_root}/status.log"
  : > "${monitor_root}/done"
  exit 0
fi

if ssh "${server_host}" "tmux has-session -t '${session_name}' 2>/dev/null"; then
  printf '%s server gate still running\n' "${timestamp}" >> "${monitor_root}/status.log"
  exit 0
fi

printf '%s server gate ended without controller.complete\n' "${timestamp}" \
  >> "${monitor_root}/status.log"
ssh "${server_host}" "tail -80 '${server_root}/controller.log' 2>/dev/null || true" \
  > "${monitor_root}/failure-tail.log"
: > "${monitor_root}/failed"
exit 1
