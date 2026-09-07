#!/usr/bin/env bash
set -euo pipefail

# Build a fresh isolated server checkout, authenticate it, and launch the
# frozen V0.20 matched C3 gate in tmux.  This wrapper never overwrites a prior
# server root or local result directory.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V020_SERVER_HOST:-sat}"
server_root="${V020_SERVER_ROOT:-/home/sat/mcrl-v020-repriced-c3-gate-20260904-r1}"
session="${V020_TMUX_SESSION:-mcrl-v020-repriced-c3-gate-20260904-r1}"
python_bin="${V020_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"

if [[ ! "${server_root}" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]]; then
  echo "unsafe V020_SERVER_ROOT: ${server_root}" >&2
  exit 2
fi
if [[ ! "${session}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  echo "unsafe V020_TMUX_SESSION: ${session}" >&2
  exit 2
fi

cd "${repo_root}"

# Authenticate the frozen contract and learned inputs before copying bytes.
test "$(sha256sum .scratch/multi-catfish-v020-c3-source-audit/REPRICED-C3-LAMBDA-CONFOUND-GATE-CONTRACT-2026-09-04.md | awk '{print $1}')" = \
  "8587537e0c4790b383b62680748b21ecffb89550849814e50043d035cd918759"
test "$(sha256sum .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json | awk '{print $1}')" = \
  "4657a1f758fa83c92deb631231431abf6bae586c050abfffc9f7e06963d9029a"
for checkpoint in \
  .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt \
  .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092102/checkpoints/lineage-2026092102-q2init-2026108102-rung-003000.pt \
  .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092103/checkpoints/lineage-2026092103-q2init-2026108103-rung-003000.pt; do
  test -f "${checkpoint}" && test ! -L "${checkpoint}"
done

if ssh "${server_host}" "test -e '${server_root}' || test -L '${server_root}'"; then
  echo "refusing to overwrite ${server_host}:${server_root}" >&2
  exit 3
fi
ssh "${server_host}" "mkdir '${server_root}'"

rsync -aR \
  pyproject.toml \
  src \
  scripts/run_head_pivotality_probe.py \
  tests/test_w140_ee_axis_zero_marginal_c3.py \
  tests/test_w141_ee_axis_zero_marginal_c3_live.py \
  tests/test_w148_ee_axis_v014_q2_state.py \
  tests/test_w173_ee_axis_relational_zr_c3.py \
  tests/test_w174_ee_axis_v018_gate.py \
  .scratch/c3-v04 \
  .scratch/zero-energy-c3-v013 \
  .scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py \
  .scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py \
  .scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py \
  .scratch/multi-catfish-v020-c3-source-audit/test_v020_canonical_serializer.py \
  .scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate_server.sh \
  .scratch/multi-catfish-v020-c3-source-audit/REPRICED-C3-LAMBDA-CONFOUND-GATE-CONTRACT-2026-09-04.md \
  .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit \
  artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  "${server_host}:${server_root}/"

ssh "${server_host}" \
  "test -x '${python_bin}'; test \"\$(readlink -f /home/sat/demo/tle_data/starlink/tle)\" = /home/sat/mcrl-runtime/tle-frozen-20260820; test -d /home/sat/mcrl-runtime/tle-frozen-20260820; cd '${server_root}'; bash -n .scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate_server.sh; '${python_bin}' --version; tmux new-session -d -s '${session}' \"cd '${server_root}' && exec bash .scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate_server.sh > server-controller.log 2>&1\""

echo "launched ${server_host}:${server_root} in tmux ${session}"
