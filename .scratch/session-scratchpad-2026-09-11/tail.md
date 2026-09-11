
## 7. F8 reference axes are CONTAMINATED — do not read them as sound

The scorer emits F8 (arm / certified fixed point, arm − 10 s anytime incumbent) for every checkpoint. In each of the three runs, the pooled fixed-point EE is 12.947467 Mbit/J and the pooled anytime-incumbent EE is 12.867610 Mbit/J. Every learned arm comes out at 1.57–3.36× the "fixed point" (table above). **These axes are not sound**, and I do not report any F8 fraction as a result.

### Verified by reading source artefacts

- All three panel receipts bind the same `panelceil_receipt`: `anchor_count = 12`, file SHA-256 `52400cf180cd55f4b004be785ba4ff8021e09e38eba20cec7321fbad9999cf7d`. PANELFIX states that the certified fixed point and the anytime incumbent for global anchors **000–011** came from PANELCEIL, and that 012–019 were recomputed by the producer. PANELZ reads "12 PANELCEIL plus 8 complete producer certificates". So **12 of the 20 panel anchors** carry PANELCEIL reference endpoints.
- `/home/sat/mcrl-v025-rank2-ws/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md` (table at lines 24–30) shows the published PANELCEIL `FIRST_IMPROVEMENT_FP` moving from **13.430252782 to 31.028111071 Mbit/J** on the clean evaluator path, with **0/12 configuration IDs retained**. `/home/sat/mcrl-v025-probe-ws/EVALPATH-2026-09-10.md` documents the mechanism: a scalar-cached `BASE` survives the later dense batch calls, because the evaluator cache is keyed only by `configuration_id`.
- The anytime incumbent comes from the same PANELCEIL traversal on the same evaluator, so it falls in the same contaminated class for those 12 anchors.

Consequence: `certified_fixed_point` and `anytime_incumbent` are contaminated for the 12 PANELCEIL-reused anchors in **all three** panels. So the pooled 12.947467 and 12.867610 Mbit/J figures, and every "arm / fixed point" and "arm − anytime" value above, are unsound. The published clean value (31.028111 Mbit/J) is on a 12-anchor set, not these 20, so it cannot stand in for the pooled fixed point here. Axis A (F6/F7, the arm levels and marginals in §3–§5) does not use these reference objects.

## 8. What must not be concluded

- **No route is dead.** These are **500 constant-rate updates**. A predeclared convergence rule found that horizon inadmissible for all three architectures: `/home/sat/mcrl-v025-c1c2-ws/LR-CONVERGENCE-SWEEP-2026-09-10.md`, line 1, "no grid learning rate is admissible by epoch 500" for C1, C2 and C3. The heads were trained on **surrogate labels**. Their argmax disagrees with the exact labels on **C1 1,137/2,200 (51.6818%), C2 1,216/2,200 (55.2727%) and C3 18/22 (81.8182%)** of anchors (`/home/sat/mcrl-v025-exacttrain-ws/EXACT-CORPUS-TRAINING-2026-09-10.md`, line 1; verified by reading). The sign-consistent negative FULL − DROP_C3 in Q1 v1 (16/16) says only this: at this budget, on these labels, the informed C3 head selects profiles with lower pooled EE than the neutral-target C3 head. It says nothing about C3 as a route.
- **No cross-panel comparison.** Each EE level belongs to its own panel. §5 pairs within-panel marginals; it does not compare levels.
- **No converged-behaviour statement.** None of the runs is converged, so no marginal here predicts converged behaviour.
- **No F8 claim.** See §7.
- **Not claim-grade.** These are development anchors, and evaluator-path authority is UNDETERMINED.

## 9. Evidence classification

- **Verified by running code:** the 48 scorer runs (exit 0, unmodified scorer, digests above). This covers every per-seed arm pooled EE, bits, joules, served / rate-target / handover counts, the knockout comparison (20/20 differing anchors at every checkpoint) and every F6/F7/F8 row. It also covers the 48 checkpoint sidecar verifications, the three panel SHA-256s, the resource receipts and the per-seed sign counts.
- **Verified by reading artefacts:** the panel-to-run schema-digest match (§2); identical seed lists, runner and `epochs = 500` across the launch receipts; PANELCEIL binding and the 13.430253 → 31.028111, 0/12 contamination (§7); the surrogate-label disagreement rates and the convergence-rule verdict (§8).
- **Derived:** pooled-across-seeds EE (Σ bits / Σ joules over the scorer's per-seed sums), marginals, relative marginals (÷ comparator arm), per-seed means and ranges, and the paired z − base differences.
- **Inferred:** the §5 reading of where the C1 change comes from, and the carry-over of contamination to the anytime incumbent.
- **Relayed, not re-verified here:** that catalogue and outcomes are identical field for field across the three panels (PANELFIX/PANELZ verifiers).

## 10. What this closes and what it leaves open

- Closes cheaply: at equal, unconverged budget, the z view's **C2 and C3 marginals are indistinguishable** from Q1 v2's (paired sign flips), and so is FULL − ALL_NEUTRAL.
- Leaves open: the z view's **C1 marginal is smaller than Q1 v2's at 16/16 seeds**. That is a real paired difference at this budget. Whether it survives convergence or exact labels is untested.
- Not done: a deliberate cross-panel mismatch run to exercise the scorer's width guard. The schema-digest match in §2 made it unnecessary for identification. Nothing was committed to the workspace git.
