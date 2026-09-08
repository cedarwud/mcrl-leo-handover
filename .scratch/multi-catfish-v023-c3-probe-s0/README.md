# Multi-catfish V0.23 C3 probe S0

TRAIN-only development diagnostic. It has no learner, admission authority,
efficacy claim, or TEST access. The E1 output is authenticated read-only input.

Use the canonical interpreter and runtime pins:

```bash
export PYTHONPATH=/home/sat/mcrl-leo-handover-e1/src
export TMPDIR=/home/sat/mcrl-leo-handover-e1/.tmp
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
$PY run_probe_s0.py --estimate --workers 12
$PY run_probe_s0.py --unit WORLD:LINEAGE
$PY run_probe_s0.py --merge
```

Each unit authenticates its E1 tape before replay and writes one immutable
partial result. Merge authenticates all twelve partials and writes the single
terminal JSON and Markdown table, both write-once.
