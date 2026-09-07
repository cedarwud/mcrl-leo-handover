#!/usr/bin/env bash
set -euo pipefail

# External preflight is deliberately a separate process from the probe.  It
# authenticates the non-circular manifest before the runner loads inherited
# V0.20/V0.18/V0.15/V0.13 modules or opens the TLE archive.

if [[ "$#" -ne 3 ]]; then
  printf 'usage: %s OUTPUT_DIR TLE_ROOT PREREG_JSON\n' "$0" >&2
  exit 2
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
REPO=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)
PYTHON="$REPO/.venv/bin/python"
OUTPUT=$1
TLE_ROOT=$2
PREREG=$3
MANIFEST="$SCRIPT_DIR/PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST="$SCRIPT_DIR/PREFLIGHT-MANIFEST.sha256"
PREFLIGHT="$SCRIPT_DIR/preflight_v022_coalition_residual.py"
RUNNER="$SCRIPT_DIR/run_v022_coalition_residual_probe.py"

"$PYTHON" "$PREFLIGHT" \
  --manifest "$MANIFEST" \
  --manifest-digest "$MANIFEST_DIGEST" \
  --repo "$REPO" \
  --prereg "$PREREG" >/dev/null

exec "$PYTHON" "$RUNNER" \
  --output "$OUTPUT" \
  --tle-root "$TLE_ROOT" \
  --prereg "$PREREG" \
  --manifest "$MANIFEST" \
  --manifest-digest "$MANIFEST_DIGEST"
