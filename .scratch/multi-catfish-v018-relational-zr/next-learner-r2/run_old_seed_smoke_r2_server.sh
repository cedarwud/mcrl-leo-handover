#!/usr/bin/env bash
set -uo pipefail

checkout=/home/sat/mcrl-v018-learned-q3-smoke-20260904-r1
python_bin=/home/sat/mcrl-leo-handover/.venv/bin/python
worker_dir="$checkout/.scratch/multi-catfish-v018-relational-zr/next-learner-r2"
config="$worker_dir/smoke-old-seed-2026120401-lineage-2026092101.json"
log="$checkout/old-seed-smoke-r2.log"
receipt="$checkout/old-seed-smoke-r2.complete"

cd "$checkout" || exit 70
status=0
PYTHONUNBUFFERED=1 "$python_bin" \
  "$worker_dir/relational_simulator_source_adapter.py" \
  --config "$config" \
  --config-sha256 f1a1953613e86b492107fb6145a740edd8fd6818fe9d099d0f192fc7516645d7 \
  >"$log" 2>&1 || status=$?
printf 'exit_code=%s\n' "$status" >"$receipt"
exit "$status"
