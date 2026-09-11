# ZCLOSE progress — BOTH JOBS COMPLETE

Report: `.scratch/zclose/Z-CLOSURE-AND-COLLAPSE-INDICATORS-2026-09-11.md`

## Job 1 — retrieve MODQNZ — DONE

- `/home/sat/mcrl-v025-mqz-ws/MODQN-Z-INTERVENTION-2026-09-10.md` **DOES NOT EXIST**.
  Workspace holds only runner + test + `artifacts/`; git has zero commits. No report was ever
  written and no conclusion was ever recorded anywhere (codex log ends mid-diff at ep 300/9000).
- Retrieved to `.scratch/zclose/modqnz/`: `run_modqn_z_intervention.py`,
  `test_modqn_z_intervention.py`, all `artifacts/**/{progress,result}.json` + timing files.
- Arms: MODQN_RAW 9000/9000 complete, MODQN_Z_INPLACE 9000/9000 complete.
  MODQN_Z_CONCAT 2300/9000 abandoned (no result.json). MODQN_RAW_DUP never started.
  => the local 800/9000 log was stale; conclusion rests on two full 9000-ep runs.
  => the width-controlled pair does not exist.
- **Metric IS pooled EE (ratio of sums)**: `run_modqn_z_intervention.py:379`
  `pooled_bits / pooled_joules`; accumulation at `:324-327,340-341`. No mean anywhere on the
  EE path. Closure DOES rest on EE evidence in this project's estimand.
- RAW 90,866,329.62 vs Z_INPLACE 87,676,034.45 bit/J => **−3,190,295.18 (−3.511%)**.
  Z spread the allocation (+3.38 active physical beams, +0.77 sats, +67 served).
  => **row 4** of MODQNZ's own predeclared reading rule (`MODQNZ.codex.log:95-103`).
- n = 1 training seed per arm. MODQN_RAW is a from-scratch retrain, NOT the frozen checkpoint
  (frozen ckpt is only hashed as a tamper anchor, never loaded).

## Job 2 — G-3 four indicators — DONE

- **No numeric threshold exists for any of the four.** Criterion as written is completeness +
  normalisation + finiteness: `collapse_metrics.py:46` "G-3 fails on a missing one, not on a
  bad value"; `:3-5`, `:40-45`, `:108-130`.
- Computed all four on 4 checkpoints. Script `/home/sat/zclose-g3/score_g3.py`; output
  `.scratch/zclose/g3-indicators.json`. 74.6 s, 0.89 GB RSS, 1 proc, nice 16, threads 1.
  Frozen ckpt sha e6b063ef… unchanged before/after.
  - FROZEN_MODQN: 7.470 / 0.4871 / 0.144691 / 0.996027
  - UNTRAINED_INIT_SEED42: 2.580 / **0.9225** / 0.114468 / **0.999150**
  - MODQNZ_MODQN_RAW: 9.110 / 0.3875 / 0.157988 / 0.996287
  - MODQNZ_MODQN_Z_INPLACE: 6.510 / 0.4435 / 0.167438 / 0.995020
  - Reproduction check: my active_beam_count 7.470 == MODQN-COLLAPSE's argmax_distinct 0.07470.
- **Key finding**: q_margin/q_entropy do not discriminate. Untrained net (0 gradient steps,
  92.25% argmax agreement) scores q_margin at 79.1% of the trained policy's and q_entropy
  HIGHER. q_entropy spans only 6.06e-03 across all 400 profiles and correlates −0.952 with
  q_range — it is unnormalised by Q range and saturates.
- Learner: 2 of 4 only. active_beam_count 7.7344, argmax_agreement 0.4185 (192 profiles,
  q1-v2 non-z selection cache). q_margin/q_entropy NOT computable — per-action score rows were
  never persisted; only selected indices are cached. No proxy substituted.
- **VERDICT: UNDETERMINED.** Not absent (no pass criterion exists, and the two added indicators
  discriminate nothing here); not present (indicators 1-2 nowhere near degenerate).

## Notes

- Session hit a usage limit mid-task. score_g3.py had already completed; nothing was recomputed.
- Server scratch left at `/home/sat/zclose-g3/` (script + json + log). No protected tree touched.
