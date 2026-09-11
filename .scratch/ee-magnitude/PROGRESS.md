# EE magnitude reconciliation — PROGRESS (COMPLETE 2026-09-11)
Output: EE-MAGNITUDE-RECONCILIATION-2026-09-11.md ; bridge script/output: eegap_bridge.py / eegap_bridge.txt

## Status — all done
- [x] Q-estimand — 1/U claim WRONG for cited July numbers (true only for sibling code after 60807490, 2026-08-05).
  July eta_u = R_u*N_b/P_b (rev 0082683d family_b_recalibration.py:121-167) = (B/3)log2(1+SINR)/P_b_RF.
  Measured estimand factor C/B = 0.980 (TRAINED), 0.927 (RANDOM).
- [x] Q-numerator — identical B/3, U=100, Shannon law, full buffer; SINR differs (G0 40 vs 33 dBi); SE 3.51 here vs ~4.4 sib [I].
- [x] Q-denominator — sib RF-only 0.25+0.35sqrt(N); this PA supply+0.338/beam+0.2/sat. Measured consumed/RF = 7.60. PA 94.2%.
- [x] Q-environment — sib <=12 beams (healthy 9-12, collapsed 3), ~8.5 users/beam; this 67.9 beams, 1.48 users/beam.
  Beam count ~cancels at first order; -425,009.885 is V0.25 a-r0, not MODQN harness.
- [x] Q-collapsed baseline — lr 1e-3 baseline 428.60 (L1) / 493.18 (waveE); best methods 609-620 (+42-45%); collapse = served-fraction penalty.
- [x] Bridge — TRAINED on sibling July formula = 693.87; RANDOM = 373.61. Harness reproduced 53,060,175.56 / 93,110,907.97 exactly.
- [x] Report written
