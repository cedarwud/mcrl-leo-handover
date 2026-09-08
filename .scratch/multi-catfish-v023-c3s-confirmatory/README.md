# V0.23 FULL2+C3-S confirmatory ladder

This directory contains engineering machinery only. It does not authorize or
start acceptance or physical evaluation.

The frozen design is two matched TRAIN arms (`FULL2`, `FULL2+C3-S`), 100 users,
10 committed decisions, 100-episode chunks/checkpoints, and descriptive rungs
at 100, 500, 1500, and 3000 episodes per arm. Only a complete independently
verified 3000 boundary can emit `C3S_CONTRIBUTION_HELD` or
`C3S_CONTRIBUTION_FALSIFIED`.

Runtime environment:

```bash
export PYTHONPATH=/home/sat/mcrl-v023-codex-ws-c3s-ladder/src:/home/sat/mcrl-v023-codex-ws-c3s-ladder/.scratch/multi-catfish-v023-c3s-confirmatory
export TMPDIR=/home/sat/mcrl-v023-codex-ws-c3s-ladder/.tmp
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
```

Safe, non-executing checks:

```bash
$PY run_v023_c3s_confirmatory.py --estimate --catalog lite --episodes 3000
$PY run_v023_c3s_confirmatory.py --estimate --catalog full --episodes 3000
$PY run_v023_c3s_confirmatory.py --dry-run --catalog lite
$PY build_c3s_confirm_world_plan.py --check C3S-CONFIRM-WORLD-PLAN-9000.json
```

Freeze order is: controller publishes the sealed plan placeholder target;
build the preflight; build two acceptance authorities; execute and seal each
arm's 200-vs-2x100 acceptance; build all formal per-invocation authorities
while the formal output root is absent; then run only the currently released
100-episode interval. The formal authority builder refuses to proceed without
both ordered acceptance receipts.

