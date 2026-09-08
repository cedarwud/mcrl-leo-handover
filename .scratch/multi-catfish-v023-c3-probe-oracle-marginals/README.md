# Oracle marginal probe

TRAIN-only, oracle-level development diagnostic over the authenticated E1
four-world × three-lineage × ten-anchor panel. It has no learner, admission,
efficacy, or TEST authority.

Run with the canonical interpreter and runtime bindings:

```bash
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  PYTHONPATH=/home/sat/mcrl-leo-handover-e1/src \
  TMPDIR=/home/sat/mcrl-leo-handover-e1/.tmp \
  /home/sat/mcrl-leo-handover/.venv/bin/python oracle_marginals.py --estimate
```

The full run permits `--workers 1..8` and writes `oracle-marginals.json` plus
`oracle-marginals.md` once under
`/home/sat/mcrl-v023-c3-probe-marginals-20260908-r1`.
