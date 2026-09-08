#!/usr/bin/env bash
# Launch the sealed 31-cell x 4-world probe with a hard concurrency ceiling.
set -euo pipefail

provider=${1:?usage: launch_v025_units.sh PACKAGE:FACTORY LAUNCH_ROOT [MAX_UNITS]}
launch_root=${2:?usage: launch_v025_units.sh PACKAGE:FACTORY LAUNCH_ROOT [MAX_UNITS]}
max_units=${3:-8}
if (( max_units < 1 || max_units > 8 )); then
  echo "MAX_UNITS must be in 1..8" >&2
  exit 2
fi

repo=/home/sat/mcrl-v025-codex-ws-engine
runner="$repo/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"
output="$launch_root/output"
logs="$launch_root/logs"
mkdir -p "$output" "$logs"

mapfile -t cells < <(
  cd "$repo"
  PYTHONPATH=src python -c \
    'from mcrl.physics_v025.matrix import MATRIX_SETTINGS; print("\n".join(row.label for row in MATRIX_SETTINGS))'
)

index=0
for cell in "${cells[@]}"; do
  for world in 1 2 3 4; do
    index=$((index + 1))
    while (( $(jobs -pr | wc -l) >= max_units )); do
      wait -n
    done
    (
      cd "$repo"
      PYTHONPATH=src python "$runner" \
        --unit "$cell:$world" \
        --provider "$provider" \
        --world-manifest "$output/world-manifest.json" \
        --calibration "$output/calibration-manifest.json" \
        --output "$output"
    ) >"$logs/unit-$(printf '%03d' "$index")-world-$world.log" 2>&1 &
  done
done
wait
