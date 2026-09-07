#!/usr/bin/env bash
set -uo pipefail

repo_root=/home/sat/mcrl-c3-shadow-20260827-v1
python_bin=/home/sat/mcrl-leo-handover/.venv/bin/python
tle_root=/home/sat/mcrl-runtime/tle-frozen-20260820
log_path="$repo_root/.scratch/catfish-design-data/c3-paired-path-development-smoke-2026082701-v6.log"
exit_path="$repo_root/.scratch/catfish-design-data/c3-paired-path-development-smoke-2026082701-v6.exit"

cd "$repo_root" || exit 98
/usr/bin/time -v "$python_bin" \
  .scratch/catfish-design-data/run_c3_paired_path_development_smoke.py \
  --tle-root "$tle_root" >"$log_path" 2>&1
run_status=$?
printf '%s\n' "$run_status" >"$exit_path"
exit "$run_status"
