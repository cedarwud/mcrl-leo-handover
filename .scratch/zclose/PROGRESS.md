# ZCLOSE progress

## Job 1 — retrieve MODQNZ — DATA RETRIEVED, ANALYSIS IN PROGRESS

- `/home/sat/mcrl-v025-mqz-ws/MODQN-Z-INTERVENTION-2026-09-10.md` **DOES NOT EXIST**.
  The workspace holds only the runner, one test, and `artifacts/`. No report was ever written.
- Retrieved to `.scratch/zclose/modqnz/`: `run_modqn_z_intervention.py`,
  `test_modqn_z_intervention.py`, and all `artifacts/**/{progress,result}.json` + timing files
  (`.pt` excluded).
- Arms completed: MODQN_RAW 9000/9000, MODQN_Z_INPLACE 9000/9000.
  MODQN_Z_CONCAT 2300/9000, no result.json. MODQN_RAW_DUP never started.
- Metric IS pooled EE (ratio of sums): `run_modqn_z_intervention.py:379`
  `pooled_bits / pooled_joules`.
- Headline: RAW 90,866,329.62 bit/J vs Z_INPLACE 87,676,034.45 bit/J (z lower, −3.511%).
- n = 1 training seed per arm (TRAIN_SEED 42).

## Job 2 — G-3 four indicators — NOT STARTED
