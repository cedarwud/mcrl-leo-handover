#!/usr/bin/env bash
set -euo pipefail

# Safe entry point for the V0.23 staged gate.  The default action only emits a
# schedule plan and authenticates no outcome.  Physical/source and learner
# stages are intentionally not reachable until a future server adapter is
# added to run_v023_lcsrs_observability_gate.py.

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
REPO=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)
PYTHON=${PYTHON:-"$REPO/.venv/bin/python"}
PREFLIGHT="$SCRIPT_DIR/preflight_v023_lcsrs_observability.py"
MANIFEST="$SCRIPT_DIR/PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST="$SCRIPT_DIR/PREFLIGHT-MANIFEST.sha256"
PREREG="$REPO/artifacts/PREREG-FROZEN-2026-08-25-R2.json"
RUNNER="$SCRIPT_DIR/run_v023_lcsrs_observability_gate.py"

if [[ "$#" -eq 0 || "$1" == "plan" ]]; then
  OUTPUT=${2:-"$SCRIPT_DIR/plan.json"}
  "$PYTHON" "$PREFLIGHT" \
    --manifest "$MANIFEST" \
    --manifest-digest "$MANIFEST_DIGEST" \
    --repo "$REPO" \
    --prereg "$PREREG" >/dev/null
  exec "$PYTHON" "$RUNNER" plan --output "$OUTPUT"
fi

printf '%s\n' \
  'V0.23 launch is scaffold-only: source/fit/merge stages require the future' \
  'server adapter and an explicit parent-authorized launch contract.' >&2
exit 2

