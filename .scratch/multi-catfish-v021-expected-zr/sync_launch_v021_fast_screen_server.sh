#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V021_SERVER_HOST:-sat}"
server_root="${V021_SERVER_ROOT:-/home/sat/mcrl-v021-expected-zr-fast-20260905-r1}"
session="${V021_TMUX_SESSION:-mcrl-v021-expected-zr-fast-20260905-r1}"
python_bin="${V021_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
contract_sha="9630e6c51784a8d8f36a7eeea34a2c3b611d9ee4b87f95be157a6adbc75e3c66"

if [[ ! "${server_root}" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]]; then
  echo "unsafe V021_SERVER_ROOT: ${server_root}" >&2
  exit 2
fi
if [[ ! "${session}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  echo "unsafe V021_TMUX_SESSION: ${session}" >&2
  exit 2
fi

cd "${repo_root}"
test "$(sha256sum .scratch/multi-catfish-v021-expected-zr/EXPECTED-ZR-FAST-SCREEN-CONTRACT-2026-09-05.md | awk '{print $1}')" = "${contract_sha}"
test "$(sha256sum .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json | awk '{print $1}')" = "4657a1f758fa83c92deb631231431abf6bae586c050abfffc9f7e06963d9029a"

if ssh "${server_host}" "test -e '${server_root}' || test -L '${server_root}'"; then
  echo "refusing to overwrite ${server_host}:${server_root}" >&2
  exit 3
fi
ssh "${server_host}" "mkdir '${server_root}'"

rsync -aR \
  pyproject.toml \
  src \
  scripts/run_head_pivotality_probe.py \
  tests/test_w180_ee_axis_expected_zr_c3.py \
  .scratch/c3-v04 \
  .scratch/zero-energy-c3-v013 \
  .scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py \
  .scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py \
  .scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py \
  .scratch/multi-catfish-v020-c3-source-audit/REPRICED-C3-LAMBDA-CONFOUND-GATE-CONTRACT-2026-09-04.md \
  .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit \
  .scratch/multi-catfish-v021-expected-zr/EXPECTED-ZR-FAST-SCREEN-CONTRACT-2026-09-05.md \
  .scratch/multi-catfish-v021-expected-zr/run_v021_expected_zr_fast_screen.py \
  artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  "${server_host}:${server_root}/"

ssh "${server_host}" \
  "test -x '${python_bin}'; test \"\$(readlink -f /home/sat/demo/tle_data/starlink/tle)\" = /home/sat/mcrl-runtime/tle-frozen-20260820; cd '${server_root}'; '${python_bin}' -m pytest -q tests/test_w180_ee_axis_expected_zr_c3.py; tmux new-session -d -s '${session}' \"cd '${server_root}' && exec '${python_bin}' .scratch/multi-catfish-v021-expected-zr/run_v021_expected_zr_fast_screen.py --output artifacts/v021-fast-screen-result --tle-root /home/sat/demo/tle_data/starlink/tle --prereg artifacts/PREREG-FROZEN-2026-08-25-R2.json > server-fast-screen.log 2>&1\""

echo "launched ${server_host}:${server_root} in tmux ${session}"
