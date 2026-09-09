# Deadline fallback, measured directly on 20 anchors

Controller-run, no agent. Corrected engine working tree with the deadline fix.
Receipts carry both the new measured `deadline_missed` and the superseded
predicate recomputed on the same anchor, so before and after are paired.

## Invocation
```
PYTHONPATH=src nice -n 5 /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --unit a-r0:1 --smoke-not-matrix --calibration .tmp/stage4h-formal/calibration-manifest.json --world-manifest .tmp/stage4h-formal/world-manifest.json --anchors 20 --anchor-stride 3 --provider mcrl.physics_v025.provider_legacy:factory --output .tmp/deadline-check
```

exit code: 137

## Run did not complete; last 25 lines
```
/tmp/deadline_measure.sh: line 26: 1827987 Killed                  timeout 5400 env PYTHONPATH=src nice -n 5 /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py --unit a-r0:1 --smoke-not-matrix --calibration .tmp/stage4h-formal/calibration-manifest.json --world-manifest .tmp/stage4h-formal/world-manifest.json --anchors 20 --anchor-stride 3 --provider mcrl.physics_v025.provider_legacy:factory --output .tmp/deadline-check
```
