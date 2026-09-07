# R7 balanced successor gate — sealed result and STOP_PHYSICS_R7 (2026-09-07 12:54 UTC)

Root `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1`, sealed by the R4 domain-repair controller at 12:54:16 UTC (log `V023_R7_DOMAIN_REPAIR_R4_PASS source_loads=8 composition_loads=48 pairs=688 c2_rows=688`). Local copies of `result.json`, `domain-repair-r4-receipt.json`, `COMPLETE`, `MANIFEST.sha256`, `LAUNCH-METADATA.json` are in `r7-sealed-receipts/` next to this memo. Receipt status `PASS_R7_FINAL_VERIFIER_DOMAIN_REPAIR_R4`; corrected verification sha `9491562316d3faeb8888e107d79b99bb583bc2b2f6c43e99219b70bb6b2a5329`.

- integrity_status = `VERIFIED`, status = `PASS_FINAL_INTEGRITY`, **c3_decision = `STOP_PHYSICS_R7`**, no_rescue = True, claim_ceiling = `TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY`
- predicates: `action_exposure`=PASS, `finite_nonzero_class_denominators`=PASS, `harmful_partial`=FAIL, `held_out_learner`=PASS, `learned_composition`=FAIL, `literal_11`=PASS, `mechanics`=PASS, `pair_coverage`=PASS, `physical_signature`=FAIL, `pooled_class_support`=PASS, `raw_sign_accuracy_reported_nondecisive`=PASS, `service`=PASS, `target_support`=PASS, `teacher_composition`=PASS, `topology_consistency`=FAIL, `world_stability`=PASS

## Source panel — physical signature (pre-registered: pooled ratio-of-sums EE direction STRICTLY_POSITIVE and ≥4 of 8 worlds positive)

pooled_joint_direction = -1, positive_world_count = 2 of 8, pair_count = 688, mechanics_pass_count = 688, target_support_count = 1339

| world | joint_00 EE (bits/J) | joint_11 EE (bits/J) | 11 vs 00 | pairs |
|---|---:|---:|---:|---:|
| 2026121801 | 122,327,340 | 122,290,220 | -0.0303% | 96 |
| 2026121802 | 129,475,270 | 129,325,888 | -0.1154% | 83 |
| 2026121803 | 122,594,530 | 122,530,281 | -0.0524% | 85 |
| 2026121804 | 127,100,733 | 127,006,717 | -0.0740% | 86 |
| 2026121805 | 129,768,030 | 129,619,236 | -0.1147% | 82 |
| 2026121806 | 125,164,573 | 125,173,818 | +0.0074% | 102 |
| 2026121807 | 125,322,619 | 125,434,619 | +0.0894% | 72 |
| 2026121808 | 123,959,666 | 123,860,797 | -0.0798% | 82 |
| pooled (ratio of sums) | 125,534,182 | 125,472,345 | -0.0493% | 688 |

## Composition panel

- teacher_composition = True (teacher_ee 120,020,084 vs baseline_ee 119,619,170 = +0.335%, teacher_world_positive 5)
- learned_composition = False (learned_ee 118,830,058 vs baseline_ee 119,619,170 = -0.660%, learned_world_positive 2; threshold STRICTLY_POSITIVE and ≥4 worlds)
- topology_consistency = False (selected_11 agreeing 379/707 = 0.536; threshold ≥ 0.8)
- action_exposure = True, literal_11 = True, harmful_partial = False, service = True

| world | INFORMED mean EE | MATCHED_PLACEBO mean EE | baseline mean EE | informed vs placebo | informed vs baseline |
|---|---:|---:|---:|---:|---:|
| 2026121801 | 118,405,003 | 117,653,690 | 118,129,204 | +0.639% | +0.233% |
| 2026121802 | 122,009,305 | 120,907,184 | 123,527,469 | +0.912% | -1.229% |
| 2026121803 | 118,147,578 | 117,266,363 | 119,082,431 | +0.751% | -0.785% |
| 2026121804 | 118,591,921 | 118,498,924 | 118,830,495 | +0.078% | -0.201% |
| 2026121805 | 118,294,991 | 117,885,728 | 120,633,946 | +0.347% | -1.939% |
| 2026121806 | 119,383,909 | 118,416,889 | 118,851,039 | +0.817% | +0.448% |
| 2026121807 | 118,666,261 | 118,114,330 | 119,871,457 | +0.467% | -1.005% |
| 2026121808 | 117,441,833 | 116,872,400 | 118,647,785 | +0.487% | -1.016% |

## Fit panel (held-out learner) — PASSED

- mean informed balanced accuracy 0.705 vs placebo 0.626 (diff +0.079, threshold ≥ 0.05 and informed ≥ 0.6); mean informed spearman 0.839; informed_world_wins 8/8; per-seed nonnegative worlds {'2026135201': 8, '2026135202': 8, '2026135203': 8}
- class denominators positive 1069 / negative 270; raw sign accuracy reported nondecisive by contract

## Context diagnostics — PASSED: C1 sign accuracy 0.806, spearman 0.414 (1343 rows); C2 exposure 0.764, target sign accuracy 0.931, target rank spearman 0.921

## What this is and is not

- VERIFIED: the frozen final verifier (sha 3cc57371…, with the six scoped verifier-side corrections R3+R4 whose receipts are in the root) reports integrity VERIFIED and the pre-registered decision STOP_PHYSICS_R7. The physical-signature numbers are recomputed from the raw source arrays (`recomputed_from_raw_arrays: true`); the source stage of 2026-09-06 15:10 wrote the same arrays, so the decision was determinable since then and was hidden only by the verifier crash chain.
- VERIFIED: the post-R7 provider factory (v1 and v2) refuses this root with `R7 final result c3_decision is not the frozen GO value` (read-only rehearsal on the server, 12:58 UTC). The 100E five-arm source-training launcher therefore cannot start under the frozen contract; this is by design, not a defect.
- NOT a claim about EE efficacy of any learner; NOT a TEST-split result; the STOP is about the pre-registered physical signature of the two-informed-Catfish (11) profile versus 00 under the V022 exact two-player coalition residual on the eight R7 TRAIN_DEVELOPMENT worlds.
