#!/usr/bin/env bash
set -euo pipefail
echo 1000 > /proc/self/oom_score_adj

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${V023_STAGEC_PYTHON:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=2
export PYTHONPATH="${repo_root}/src"
export TMPDIR="${repo_root}/.tmp"
mkdir -p "${TMPDIR}"
exec "${python_bin}" "${repo_root}/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch/run_v023_c1c2_successor_stage_b.py" "$@"
