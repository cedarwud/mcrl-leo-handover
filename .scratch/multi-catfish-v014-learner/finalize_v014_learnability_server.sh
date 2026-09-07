#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V014_SERVER_HOST:-sat}"
server_root="${V014_SERVER_ROOT:-/home/sat/mcrl-v014-learnability-20260903-r1}"
artifact_root="${repo_root}/artifacts/multi-catfish-v014-learnability-20260903-r1"
destination="${artifact_root}/server-run"
verifier=".scratch/multi-catfish-v014-learner/verify_v014_learner_gate.py"

if [[ -e "${destination}" || -L "${destination}" ]]; then
  echo "refusing to overwrite ${destination}" >&2
  exit 2
fi

ssh "${server_host}" "cd '${server_root}' && test -f source-panel/controller.complete && test -f learner-gate/result.json && test -f learner-gate/result-seal.json && test ! -e learner-gate/independent-verification-server.json && set -C && env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python '${verifier}' learner-gate > learner-gate/independent-verification-server.json"

mkdir "${destination}"
rsync -a "${server_host}:${server_root}/source-panel" "${destination}/"
rsync -a "${server_host}:${server_root}/learner-gate" "${destination}/"

cd "${repo_root}"
env PYTHONPATH=src .venv/bin/python "${verifier}" \
  "${destination}/learner-gate" > "${destination}/learner-gate/independent-verification-local.json"
(
  cd "${artifact_root}"
  find contracts server-run -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum > MANIFEST.sha256
)
