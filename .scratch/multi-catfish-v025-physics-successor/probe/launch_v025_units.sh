#!/usr/bin/env bash
# Launch a-r0 first, then the sealed contingency ladder and sensitivities.
set -euo pipefail

provider=${1:?usage: launch_v025_units.sh PACKAGE:FACTORY LAUNCH_ROOT [MAX_UNITS]}
launch_root=${2:?usage: launch_v025_units.sh PACKAGE:FACTORY LAUNCH_ROOT [MAX_UNITS]}
max_units=${3:-20}
anchor_stride=${4:-1}
if (( max_units < 1 || max_units > 20 )); then
  echo "MAX_UNITS must be in 1..20" >&2
  exit 2
fi
if (( anchor_stride < 1 )); then
  echo "ANCHOR_STRIDE must be positive" >&2
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
    'from mcrl.physics_v025.matrix import LAUNCH_RUN_ORDER; print("\n".join(row.run_id for row in LAUNCH_RUN_ORDER))'
)

index=0
launch_pids=()
launch_cell() {
  local cell=$1
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
        --anchor-stride "$anchor_stride" \
        --output "$output"
    ) >"$logs/unit-$(printf '%03d' "$index")-$cell-world-$world.log" 2>&1 &
    launch_pids+=("$!")
  done
}

wait_for_launches() {
  local failed=0
  local pid
  for pid in "${launch_pids[@]}"; do
    wait "$pid" || failed=1
  done
  launch_pids=()
  (( failed == 0 ))
}

# PHYSICS-GO owns a-r0 alone.  No sensitivity is opened before all four
# primary units finish successfully.
launch_cell "${cells[0]}"
wait_for_launches
touch "$output/AR0-DONE"

# LAUNCH_RUN_ORDER is R1,R2,R3,R4,R5=a′-r0,R6=a-γ0,C2-H1,C2-H2,
# then every remaining treatment.  Background jobs preserve queue order.
for cell in "${cells[@]}"; do
  [[ "$cell" == "a-r0" ]] && continue
  [[ -f "$output/AR0-DONE" ]] || { echo "AR0-DONE missing" >&2; exit 3; }
  launch_cell "$cell"
done
wait_for_launches
