#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V017K_SERVER_HOST:-sat}"
server_root="${V017K_SERVER_ROOT:-/home/sat/mcrl-v017-c3-softkl-gate-20260903-r1}"
artifact_root="${repo_root}/artifacts/multi-catfish-v017-c3-softkl-gate-20260903-r1"
destination="${artifact_root}/server-run-r1"

if [[ -e "${destination}" || -L "${destination}" ]]; then
  echo "refusing to overwrite ${destination}" >&2
  exit 2
fi
ssh "${server_host}" "test -f '${server_root}/controller.complete' && test -f '${server_root}/learner-gate/result.json' && test -f '${server_root}/learner-gate/receipt.json'"
mkdir "${destination}"
rsync -a "${server_host}:${server_root}/source-panel" "${destination}/"
rsync -a "${server_host}:${server_root}/learner-gate" "${destination}/"
rsync -a "${server_host}:${server_root}/learner-gate.log" "${destination}/"
rsync -a "${server_host}:${server_root}/controller.complete" "${destination}/"
(
  cd "${artifact_root}"
  find contracts server-run-r1 -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum > MANIFEST-R1.sha256
)
