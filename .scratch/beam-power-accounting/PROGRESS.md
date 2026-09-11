# POWERACCT progress

Task: re-score frozen actions under MAX / TDM_AIRTIME / ADDITIVE beam-power accounting.
Read-only. No update(), no gradient step, no optimizer step.

## Cells

- [x] C0 read the attachment surface + locate harness (`pooled_ee.py`, `anchor_ablation.py`,
      `c3s_physics_override.py` all present in this session's scratchpad)
- [x] C1 read the power model: `env/link_budget.py:439-547` (beam_power_w=max, pa_efficiency,
      supply_power_w, fixed_power_w, system_power_w); `env/step.py:975-1010`
- [x] C2 PHY is TIME-DIVISION within a beam: noise = kB*T*B^w at FULL beam
      bandwidth (step.py:214-217, link_budget.py:367-372) while rate = (B^w/U_b)*log2(1+g)
      (link_budget.py:590-616, "the beam is time-shared"). No simultaneous streams.
      ADDITIVE is therefore reported as a labelled stress bound, not as this PHY.
- [x] C2b decide ADDITIVE applicability from the PHY (noise bandwidth vs rate bandwidth)
- [x] C3 write the recording harness (subclass, canonical physics untouched)
- [x] C4 PASS: |MAX_recomputed - env P^N| <= 2.3e-13 W over every step, every arm (n=1 smoke) parity check: recomputed MAX == env's own system_power_w, per step
- [x] C5 24-ep run COMPLETE (pid 261583 exited; wall 351.9 s; peak RSS ~0.63 GB, nice 16, 1 proc, BLAS=1).
      Outputs: scratchpad/poweracct.log + scratchpad/power_accounting_result.json.
      ALL FOUR arms reproduce the published fresh-env `none` EE bit-identically
      (RANDOM 53060175.561473, GREEDY_R1R2 75763635.837306, TRAINED 93110907.973748,
      MAX_NOMINAL_GAIN 111504571.388934).
      Ratios MAX/TRAINED: MAX 1.1975 (13.0 sem) | TDM_AIRTIME 1.1916 (12.6 sem) | ADDITIVE 1.1629 (10.0 sem).
      Ranking of all 4 arms unchanged under all 3 accountings.
      ARM PARITY PASS: RANDOM_MASKED reproduces the published `none` figure
      BIT-IDENTICALLY -- bits 1.842866e+14, joules 3.473162e+06,
      EE 53060175.561473 (published: 53,060,175.56).
      Per-step parity |MAX_recomputed - env P^N| <= 2.3e-13 W.
- [x] C6 LOO marginal (per added user, dt=30.08 s), MAX_NOMINAL_GAIN / TRAINED beams:
      MAX mean +1.656 / +3.837 J, median 0 W, exactly 0 for 83.3% / 68.3%
      TDM_AIRTIME mean 0.000 J EXACT (algebraic identity), 22.0% / 36.3% negative (to -1.122 W)
      ADDITIVE mean +63.667 / +64.548 J, never 0.
      Canonical 2->3 users at p0: MAX 0 J, TDM 0 J, ADDITIVE +56.674 J.
      MAX 'negatives' (4.2%) verified as -8.9e-16 W float noise (neg_check.py).
      Fixed-share probe (fixed_probe.py, 3 ep): PA ~94.3% of P^N for both arms.
- [x] C7 report written: BEAM-POWER-ACCOUNTING-2026-09-11.md (first line = bolded three-ratio sentence).
      Resume 2026-09-11 after controller usage-limit: no process running, no cell recomputed;
      only this file and the report's first line were touched.
