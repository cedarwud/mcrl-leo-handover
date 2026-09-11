#!/bin/bash
# OOSPANEL acceptance: one real checkpoint per OOS panel, unmodified scorer, one process at a time.
set -u
WS=/home/sat/mcrl-v025-oospanel-ws
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
SEED=6407676579069309528
declare -A CK=(
  [q1v1]=/home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-step-decay-16seed-4000-20260910/checkpoints/learner-$SEED-epoch-004000.json
  [q1v1-exact93]=/home/sat/mcrl-v025-exact93-ws/artifacts/exact93-step-decay-16seed-4000-20260911/checkpoints/learner-$SEED-epoch-004000.json
  [q1v2]=/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-$SEED-epoch-000500.json
  [q1v2z]=/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2z-500ep-20260910T1512Z/checkpoints/learner-$SEED-epoch-000500.json
  [q1v3]=/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-step-decay-16seed-4000-20260910/checkpoints/learner-$SEED-epoch-004000.json
  [q1v3-control]=/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-control-step-decay-16seed-4000-20260910/checkpoints/learner-$SEED-epoch-004000.json
)
declare -A PANEL=(
  [q1v1]=q1v1 [q1v1-exact93]=q1v1 [q1v2]=q1v2 [q1v2z]=q1v2z [q1v3]=q1v3 [q1v3-control]=q1v3-control
)
for tag in q1v1 q1v1-exact93 q1v2 q1v2z q1v3 q1v3-control; do
  schema=${PANEL[$tag]}
  panel=$WS/artifacts/panel-oos-$schema.json
  receipt=$WS/artifacts/panel-oos-$schema.receipt.json
  want=$(cut -d" " -f1 < "$panel.sha256")
  echo "=== acceptance $tag panel=$schema want=$want"
  bash $WS/scripts/score_one.sh "$tag" "${CK[$tag]}" "$panel" "$receipt" "$want" \
    > "$WS/logs/acceptance-$tag.log" 2>&1
  echo "tag=$tag exit=$? $(grep -E 'dual-axis-scoring-complete|PEAK_RSS_BYTES|SCORER_EXIT|GATE_FAIL' "$WS/logs/acceptance-$tag.log" | tail -3)"
done
echo ACCEPTANCE_ALL_DONE
