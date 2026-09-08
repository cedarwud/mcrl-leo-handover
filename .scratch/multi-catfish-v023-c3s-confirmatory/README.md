# V0.23 FULL2+C3-S confirmatory ladder v2

Engineering machinery only; nothing here grants launch authority or starts compute.
The fixed comparison is `FULL2` versus `FULL2+C3-S(c)` on distinct fresh TRAIN
worlds, 100 users, 30 committed decisions, 3,000 opportunities per episode.
Rungs are 100/500/1,500/3,000 with 100-episode chunks. Failed EE or service at
independently verified N=100 or N=500 emits FALSIFIED/`EARLY_FUTILITY`;
otherwise `RUNG_HELD` releases one interval. Contribution HELD requires N=3,000.

Runtime setup:

```bash
export PYTHONPATH="$PWD/src:$PWD/.scratch/multi-catfish-v023-c3s-confirmatory"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MCRL_C3S_WORKER_CONCURRENCY=0
export MCRL_C3S_CACHE_CONDITIONS=prospectively-fixed-cold-or-warm-scope
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
```

Safe, non-executing checks:

```bash
$PY run_v023_c3s_confirmatory.py --estimate --configuration LITE --episodes 3000
$PY run_v023_c3s_confirmatory.py --estimate --configuration V-C --matrix-timing MATRIX-TERMINAL.json
$PY run_v023_c3s_confirmatory.py --dry-run --configuration V-H
$PY build_c3s_confirm_world_plan.py --check C3S-CONFIRM-WORLD-PLAN-9000.json
$PY -m pytest -q test_c3s_confirmatory.py
```

Preflight refuses until the separately sealed plan v2, screen and matrix
contracts, complete matrix and v1 receipts, attempt-3 stage-A PASS plus its
epoch-100/200-update export manifest and FULL2 hashes, stage-B PASS, physical
inputs, world plan, and absent output root all authenticate. Matrix
INVALID_RUN/INCOMPLETE, a missing LITE-equivalence audit, or unexplained
same-panel disagreement leaves `ARM_UNRESOLVED`.

The runner also provides:

```bash
$PY run_v023_c3s_confirmatory.py --verify-equivalence OLD NEW \
  --decision-record ARCHIVE.json --equivalence-reviewer NAME --output RECEIPT.json
$PY run_v023_c3s_confirmatory.py --benchmark-uncontended --code-path CODE.py \
  --decision-record D01.json ... --decision-record D30.json --output BENCHMARK.json
$PY run_v023_c3s_confirmatory.py --decompose --result FALSIFIED.json --code-path REPLAY.py \
  --decision-record PAIRED-ARCHIVE.json --output DECOMPOSITION.json
```

Formal order: scientific seal; preflight; both arm acceptance authorities and
acceptance receipts; then a separate rung/chunk authority for each permitted
100-episode chunk. Only a preceding `RUNG_HELD` receipt releases a later interval.
