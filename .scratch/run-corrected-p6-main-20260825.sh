#!/usr/bin/env bash
set -uo pipefail

repo=/home/sat/mcrl-leo-handover-20260825-corrected
python=/home/sat/mcrl-leo-handover/.venv/bin/python
log="$repo/artifacts/training-2026-08-25-rerun01.log"
exit_receipt="$repo/artifacts/training-2026-08-25-rerun01.exit"

cd "$repo" || exit 97
export PYTHONUNBUFFERED=1

set +e
/usr/bin/time -v "$python" scripts/run_server_training.py pipeline 2>&1 \
  | tee "$log"
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > "$exit_receipt"
exit "$status"
