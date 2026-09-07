#!/usr/bin/env bash
set -euo pipefail

# Fresh-server wrapper for the bounded V0.23 DROP_C3-only development
# evaluation.  This file is launch glue, not a launch receipt.  It never
# changes a prior server root and never includes a BASELINE or C3 stage.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V023_DROPC3_SERVER_HOST:-sat}"
server_root="${V023_DROPC3_SERVER_ROOT:-/home/sat/mcrl-v023-dropc3-evaluation-20260906-r1}"
session="${V023_DROPC3_TMUX_SESSION:-mcrl-v023-dropc3-evaluation-20260906-r1}"
python_bin="${V023_DROPC3_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
tle_root="${V023_DROPC3_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
run_root="${V023_DROPC3_RUN_ROOT:-${server_root}/run}"
output_dir="${run_root}/drop-c3-100ep"
resume_checkpoint="${V023_DROPC3_RESUME_CHECKPOINT:-}"

if [[ ! "${server_root}" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]]; then
  echo "unsafe V023_DROPC3_SERVER_ROOT: ${server_root}" >&2
  exit 2
fi
if [[ ! "${run_root}" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]]; then
  echo "unsafe V023_DROPC3_RUN_ROOT: ${run_root}" >&2
  exit 2
fi
if [[ ! "${tle_root}" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]]; then
  echo "unsafe V023_DROPC3_TLE_ROOT: ${tle_root}" >&2
  exit 2
fi
if [[ ! "${session}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  echo "unsafe V023_DROPC3_TMUX_SESSION: ${session}" >&2
  exit 2
fi
if [[ -n "${resume_checkpoint}" && ! "${resume_checkpoint}" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]]; then
  echo "unsafe V023_DROPC3_RESUME_CHECKPOINT: ${resume_checkpoint}" >&2
  exit 2
fi

cd "${repo_root}"
contract=".scratch/multi-catfish-v023-physical/V023-DROPC3-DEVELOPMENT-EVALUATION-CONTRACT-2026-09-06.md"
runner=".scratch/multi-catfish-v023-physical/v023_physical_episode_runner.py"
server_entry=".scratch/multi-catfish-v023-physical/run_v023_dropc3_evaluation_server.py"
prereg="artifacts/PREREG-FROZEN-2026-08-25-R2.json"
checkpoint=".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt"

test -f "${contract}" && test ! -L "${contract}"
test "$(sha256sum "${contract}" | awk '{print $1}')" = \
  "7ff5d639cef0310bdbf66a54b6a8513aff0ff9460554543cf33e8c39e5673885"
test -f "${runner}" && test ! -L "${runner}"
test -f "${server_entry}" && test ! -L "${server_entry}"
test -f "${prereg}" && test ! -L "${prereg}"
test "$(sha256sum "${prereg}" | awk '{print $1}')" = \
  "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
test -f "${checkpoint}" && test ! -L "${checkpoint}"
test "$(sha256sum "${checkpoint}" | awk '{print $1}')" = \
  "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"

if ssh "${server_host}" "test -e '${server_root}' || test -L '${server_root}'"; then
  echo "refusing to overwrite ${server_host}:${server_root}" >&2
  exit 3
fi
ssh "${server_host}" "mkdir '${server_root}'"

rsync -aR \
  pyproject.toml \
  src \
  "${runner}" \
  "${server_entry}" \
  "${contract}" \
  "${prereg}" \
  .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/authority.json \
  .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt \
  .scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md \
  .scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md \
  "${server_host}:${server_root}/"

ssh "${server_host}" \
  "test -x '${python_bin}'; test -d '${tle_root}'; cd '${server_root}'; '${python_bin}' --version; sha256sum '${contract}' '${prereg}' '${checkpoint}'"
ssh "${server_host}" "mkdir -p '${run_root}'"

if [[ -n "${resume_checkpoint}" ]]; then
  launch_args="--tle-root '${tle_root}' --output '${output_dir}' --resume-checkpoint '${resume_checkpoint}'"
else
  launch_args="--tle-root '${tle_root}' --output '${output_dir}'"
fi
ssh "${server_host}" \
  "cd '${server_root}' && tmux new-session -d -s '${session}' \"cd '${server_root}' && exec '${python_bin}' '${server_entry}' ${launch_args} > '${run_root}/server-controller.log' 2>&1\""

echo "launched ${server_host}:${output_dir} in tmux ${session}"
