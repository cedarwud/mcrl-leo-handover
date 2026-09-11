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
- [~] C5 24-ep run in flight (pid 261583, RSS ~0.6 GB, nice 16, 1 proc, BLAS=1).
      ARM PARITY PASS: RANDOM_MASKED reproduces the published `none` figure
      BIT-IDENTICALLY -- bits 1.842866e+14, joules 3.473162e+06,
      EE 53060175.561473 (published: 53,060,175.56).
      Per-step parity |MAX_recomputed - env P^N| <= 2.3e-13 W.
- [ ] C6 marginal-joule figures
- [ ] C7 write report
