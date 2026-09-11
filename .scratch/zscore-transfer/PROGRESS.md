# ZWHY progress — z-score transfer audit

Started 2026-09-11. Read-only, two repos.

- [ ] Q1 what is z-score in each project (code)
- [ ] Q2 sibling's recorded evidence z-score helped
- [ ] Q3 was sibling z-score run confounded
- [ ] Q4 this project's evidence z-score harmful/unnecessary
- [ ] Q5 mechanism (batch z-score destroys absolute scale vs pooled-EE ratio-of-sums)
- [ ] Q6 is collapse absent here (measured)
- [ ] Verdict written to ZSCORE-TRANSFER-2026-09-11.md

## Log
- 09:xx set up scratch dir, began repo orientation.
- Q1 (sibling side) DONE: sibling z-score = STATE-FEATURE cross-user per-feature population z, appended raw||z (112->224 in modqn_faithful_ablation/encoding.py:62-107; 140->280 in coordinator_dqfd_zscore/representation.py:132-169). Z0 = width-matched raw-duplicate control. Raw block provably recoverable (representation.py:269-274). NOT reward normalisation, NOT per-batch.
- Q1 (this project) DONE-ish: `grep -c zscore src/` = 0. No z-score in this repo's src. The z view lives in server workspaces (/home/sat/mcrl-v025-design-ws/build_zscore_corpus.py) — same construction: raw || live-user population z appended to C1/C2/C3 member blocks (Q1 15->30, Q2 22->44, C3 296/66).
- Q4 partial: this project DID run a matched z experiment. .scratch/reviews/evidence-bundle-2026-09-11/reports/Z-VIEW-SCORING-2026-09-10.md (16 seeds, ep500, own panel) and RAW-DUP-CONTROL-2026-09-10.md (raw_dup width-matched control, 16 seeds).
  * z view shrinks FULL-DROP_C1 from +12.691 Mbit/J (16/16 pos) to +1.353 (14/16, sign flips) — 16/16 seeds smaller. C2/C3/ALL_NEUTRAL marginals indistinguishable.
  * BUT z IMPROVES representation: row-collinearity 0.360 vs 0.482 non-z (floor 0.2735), C2 srank frac 0.903 vs 0.454; repairs step-3/step-7 C2 rank collapse. raw_dup control moves neither axis => not capacity.
- Two Explore agents dispatched (sibling evidence; this-project records).

## Decisive findings (own verification, not relayed)
- Q2/Q3 DECIDER: sibling's headline "146.6 -> 357.1" is flagged **CROSS-CONDITION** by the sibling's OWN files:
  configs/shared_q_isolation/v3/fulldqfd_OFF_raw.yaml:7 ("must NOT be cited as if it were matched")
  and analysis/family-b-collapse-diagnosis/FULLDQFD-GROUPD-PREREG-2026-07-14.md:10,38,55.
  04-zscore.md:56 cites exactly that pair as "實測支持". => the explainer's headline evidence is unmatched.
- Q3 CONFOUND NAMED: analysis/family-b-collapse-diagnosis/COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md.
  Same frozen scorer, n=3/cell: raw/lr0.01 150.13; concat-z/lr0.01 235.53; concat-z/lr0.001 472.22; raw/lr0.001/9000ep 493.18 & 428.60.
  Doc line ~72: "z-score *helps* but does not prevent the collapse; lr is the controlling variable."
  => the collapse z was credited with fixing is an lr=0.01 artifact. (A)-shaped, and the confound the brief predicted.
- BUT NOT PURE (C): §5 of the same doc reports L2-L1 = +56.54 Mbit/J, 6/6 seeds, at healthy lr=1e-3/9000ep, 6 formal seeds, same scorer.
  Verified L1/L2 configs differ ONLY by the `shared_q_isolation: {form: concat, zscore_eps: 1e-6}` block (diff of abl9k_baseline_raw.yaml vs abl9k_baseline.yaml).
  => a genuine MATCHED z-on/off win exists in the sibling at correct lr.
- Q2 METRIC: argmax_EE is NOT pooled EE. score_argmax_endpoint.py:121 `m["argmax_EE"] = m["r1"]/1e6`, and r1 is
  mean-over-users -> mean-over-steps -> mean-over-episodes (lines 105,118,120) of r1_system_ee_contribution
  (= R_u/P_system, family_b_recalibration.py:120-132). Mean of ratios over time, not ratio of sums.
- Q6 MEASURED here (not assumed): MODQN-COLLAPSE-2026-09-10.md:1 modal_frac 0.04170, 68.70 beams / 7.47 sats (myopic control 0.05010, 63.32/6.47);
  BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md:1 learner a0 modal_frac 0.05236, 49.07 beams (myopic 0.05500, 51.68).

## COMPLETE 2026-09-11
All six questions answered. Report written to ZSCORE-TRANSFER-2026-09-11.md.
Verdict: mostly (C), residual (B) with a measured physics reason; (A) rejected as posed.

Late additions (both surfaced by parallel record searches, each re-verified by me against the primary file):
- Q0 (NEW, biggest): this repo already recorded the whole answer on 2026-07-20.
  .scratch/chinese-word-r1-symbols-20260905-r1/input/thesis-mc/WRITING-RULES.md:270-290 is headed
  "USER OVERRIDE — 解崩敘事還原回去，與同日權威裁決相反且現有數據不支持", quotes the user instruction
  verbatim, and lists L1=428.60 healthy / collapse=145-150 seed-identical / L2-L1=+56.54 "把健康的往上推,
  不是把崩掉的救回來" / 2026-07-17 retraction / "z-score 有幫助但擋不住崩;lr 才是控制變數".
  Also: "z-score = substrate, 不得宣稱為 MCRL 元件, 因為它沒有 leave-one-out 對照臂".
- Q4: out-ZSCORE.md:7-11 — z view 29.9486 vs non-z 29.1769 Mbit/J (+0.7717). The only z-vs-non-z EE
  level written down here has z HIGHER. [R], off-machine report.
- Q4: CROWDING-COST-2026-09-10.md:1,134 — d(EE)/d(active) = -425,009.885 bit/J per added mean-active
  beam, no sign flip 8.00-98.25. Spreading is EE-negative here => measured physical reason for (B).
- Q4: MODQNZ declared "z line closed" (TRAINING-PAUSE:11, AGENT-REGISTRY:55) but its numbers are NOT on
  this filesystem (log stops at ep 800/9000; report at /home/sat/mcrl-v025-mqz-ws/). Named as missing measurement 0.
- Q6 QUALIFIED: src/mcrl/runtime/collapse_metrics.py:1-6,40-45 mandates all four G-3 indicators
  (active_beam_count, argmax_agreement, q_margin, q_entropy; missing any one fails). Verified grep:
  BOTH collapse reports have 0 hits for q_margin/q_entropy. So "collapse absent here" is a two-of-four
  report, not a passed gate — and the missing two are exactly the pair that catches
  "argmax dispersion under near-flat Q".
