#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V013_SERVER_HOST:-sat}"
server_root="${V013_SERVER_ROOT:-/home/sat/mcrl-zero-energy-c3-v013-20260903-r1}"
contract="docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md"
authority="artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/FROZEN-AUTHORITY.json"

cd "${repo_root}"
grep -Fq 'Status: **FROZEN BEFORE OUTCOME ACCESS**' "${contract}" || {
  echo "refusing sync because V0.13 is not frozen" >&2
  exit 1
}
[[ -f "${authority}" && ! -L "${authority}" ]] || {
  echo "refusing sync because V0.13 frozen authority is missing" >&2
  exit 1
}

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
  "${contract}" \
  "${authority}" \
  artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1 \
  "${server_host}:${server_root}/"

ssh "${server_host}" \
  "cd '${server_root}' && sha256sum '${contract}' '${authority}' .scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py && env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py verify-authority --authority '${authority}' --contract '${contract}'"
