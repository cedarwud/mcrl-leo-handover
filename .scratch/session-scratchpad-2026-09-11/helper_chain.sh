#!/bin/bash
# SEEDPAR helper (the job's single helper process).
#   1. When the seed-1 equivalence process exits, launch seed 16 (keeps <= 8 concurrent training processes).
#   2. When every training process has exited: bit-for-bit comparisons, per-seed stopping analysis,
#      scored-checkpoint summary, and fill the completion section of the report.
# Reads the EXACT93 workspace; writes only under /home/sat/mcrl-v025-seedpar-ws.
# Usage: helper_chain.sh   (reads .scratch/seed-map.tsv and .scratch/training-pids.tsv)
set -uo pipefail
WS=/home/sat/mcrl-v025-seedpar-ws
SEQ=/home/sat/mcrl-v025-exact93-ws/artifacts/exact93-step-decay-16seed-4000-20260911
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
cd "$WS"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
       VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 \
       PYTHONPATH=/home/sat/mcrl-v025-retrain-ws/src PYTHONDONTWRITEBYTECODE=1
log() { echo "$(date -u +%FT%TZ) $*"; }

# alive <pid> <output-dir-name>: true only if the pid is a runner-v3 process writing that directory.
alive() {
  [ -r "/proc/$1/cmdline" ] || return 1
  tr '\0' ' ' < "/proc/$1/cmdline" | grep -q -- "scripts/run_stagec_training_v3.py .*artifacts/$2 "
}

wait_for() {  # wait_for <pid> <dir>
  while alive "$1" "$2"; do sleep 60; done
  if [ -f "artifacts/$2/training-result.json" ]; then log "EXITED OK $2 (pid $1)"; else log "EXITED WITHOUT training-result.json $2 (pid $1)"; fi
}

log "helper start pid $$"
PILOT_PID=$(awk -F'\t' '$2=="seedpar-s01-equiv-20260911"{print $1}' .scratch/training-pids.tsv)
wait_for "$PILOT_PID" seedpar-s01-equiv-20260911

S16_DIR=seedpar-s16-20260911
if [ ! -e "artifacts/$S16_DIR" ]; then
  S16_PID=$(./scripts/launch_one.sh "$S16_DIR" 16)
  printf '%s\t%s\t%s\n' "$S16_PID" "$S16_DIR" "16" >> .scratch/training-pids.tsv
  log "launched seed 16 pid $S16_PID"
fi

while IFS=$'\t' read -r pid dir indices; do
  wait_for "$pid" "$dir"
done < .scratch/training-pids.tsv
log "all training processes have exited"

mkdir -p .scratch/equivalence .scratch/stopping
nice -n 15 "$PY" scripts/compare_checkpoints.py --reference "$SEQ" --candidate artifacts/seedpar-s01-equiv-20260911 \
  --seed 6407676579069309528 --epochs common --output .scratch/equivalence/seed01-full-sequential-vs-v3.json \
  > .scratch/equivalence/seed01-full.log 2>&1; log "seed-1 full comparison exit $?"
P23=$(awk -F'\t' '$1==2{print $2}' .scratch/seed-map.tsv)
nice -n 15 "$PY" scripts/compare_checkpoints.py --reference "$SEQ" --candidate "artifacts/$P23" \
  --seed 925030429265975792 --epochs common --output .scratch/equivalence/seed02-overlap-sequential-vs-v3.json \
  > .scratch/equivalence/seed02-overlap.log 2>&1; log "seed-2 overlap comparison exit $?"

ARGS=()
while IFS=$'\t' read -r index dir; do
  if [ "$index" = "1" ]; then RUN="$SEQ"; else RUN="$WS/artifacts/$dir"; fi
  OUT=.scratch/stopping/stopping-analysis-seed$(printf '%02d' "$index").json
  if [ ! -e "$OUT" ]; then
    nice -n 15 "$PY" scripts/stopping_analysis.py --run "$RUN" --output "$OUT" --seed-index "$index" \
      > ".scratch/stopping/seed$(printf '%02d' "$index").log" 2>&1
    log "stopping analysis seed $index exit $?"
  fi
  [ -f "$OUT" ] && ARGS+=(--analysis "$index=$OUT")
done < .scratch/seed-map.tsv

nice -n 15 "$PY" scripts/scored_checkpoints.py "${ARGS[@]}" --output .scratch/stopping/scored-checkpoints.json \
  --markdown .scratch/stopping/scored-checkpoints.md > .scratch/stopping/scored.log 2>&1
log "scored checkpoints exit $?"
nice -n 15 "$PY" scripts/finalize_report.py > .scratch/finalize.log 2>&1
log "finalize exit $?"
log "helper done"
