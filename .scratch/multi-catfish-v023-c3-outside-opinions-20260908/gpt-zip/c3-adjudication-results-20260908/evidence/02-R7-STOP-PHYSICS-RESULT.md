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


---

# Appendix A — Independent adjudication (codex gpt-6-astra, read-only, 2026-09-07)

Verbatim copy of `ADJUDICATION-R7-STOP-PHYSICS-CODEX-GPT6-ASTRA-2026-09-07.md`.

---

## VERIFIED

References below use filenames within the packages specified in the request; `result.json` means the local sealed receipt.

**Seal evidence.** Local hashes of `result.json`, `domain-repair-r4-receipt.json`, and `LAUNCH-METADATA.json` match `MANIFEST.sha256`; the manifest hash matches `COMPLETE`. The result records `integrity_status=VERIFIED`, `status=PASS_FINAL_INTEGRITY`, `c3_decision=STOP_PHYSICS_R7`, and `no_rescue=true`. These confirm local receipt consistency, not an independently repeated server-wide verification. [Files: named manifest entries; `COMPLETE:1`; `result.json` fields.]

**Token derivation.** `STOP_PHYSICS_R7` is mandatory. After integrity and coverage pass, the adjudicator tests `mechanics ∧ physical_signature ∧ teacher_composition`. Only **`physical_signature=false`** fails this conjunction. I also evaluated the isolated adjudicator with the sealed predicates. If physics alone passed, the observability checks would pass and the output would be **`REDESIGN_INTERFACE_R7`**. `STOP_OBSERVABILITY_R7` has intermediate precedence but requires failure of target support, held-out learner, or world stability; none failed here. [ `r7_balanced_successor_gate.py:359–376`; `result.json:predicates`.]

**Harmful-partial polarity.** The aggregate `harmful_partial` is a **passing guard**: nonempty pair panel and harmful-pair fraction ≤0.05. Therefore `false` means the guard failed; the memo’s **FAIL rendering is correct**. Conversely, each underlying `pair_harmful_partial=true` identifies a harmful selected 10/01 profile. Its denominator in the aggregate is all informed pair records, not only partial selections. [ `verify_v023_lcsrs_final.py:937–958,1644–1668`; `v023_lcsrs_composition_adapter.py:1010–1030`; memo:6.]

**Predicate input trace.**

- `physical_signature`: source NPZ `profile_bits` and `profile_energy_j`, profiles 00 and 11; pooled ratio-of-sums direction must be strictly positive and ≥4 worlds positive. [ `verify_v023_lcsrs_scientific.py:1897–1902,1956–1957,2142–2151`.]
- `mechanics`: source physical keys, reference/designated actions, active-beam sets/counts, service arrays, and ratio-identity checks across all 32 draws; ≥90% of pairs must pass. [Same file:1867–1895,1929–1944,2141.]
- `teacher_composition` / `learned_composition`: composition `physical_total_bits` and `physical_energy_j`, baseline/teacher/learned roles; pool within seed, average across seeds, require positive direction and ≥4 positive worlds. [ `verify_v023_lcsrs_final.py:1600–1607,1672–1687`.]
- `topology_consistency`: validated composition actions/physical keys determine literal 11, emptied source, and destinations retained by nonmembers; agreeing selected-11 fraction must be ≥0.80. [Same file:959–974,1651–1668; composition adapter:1032–1054.]

**Six corrections, individually.** None changes those five predicates’ scientific values or decision comparisons:

| Correction | Actual scope and effect |
|---|---|
| R3 digest domain | Selects source versus composition hash domain; original loader still authenticates unchanged arrays. [R3 `verify_v023_lcsrs_final_domain_repair.py:265–295`.] |
| R3 sibling import | Temporarily exposes frozen verifier siblings; restores `sys.path`. No metric operation. [Same file:125–141.] |
| R3 broadcast | Changes the **integrity comparison’s expected operand**, broadcasting identical four-profile actions across draws; does not alter actual actions, bits, energy, topology calculations, or scientific thresholds. [Same file:188–215; final verifier:896–901.] |
| R4 pair keys | Independently derives source expectations from JSON topology and NPZ physical keys/actions, requires agreement, and injects only two keys into a shallow mapping for the unchanged identity join. Composition topology arrays remain untouched. [R4 `verify_v023_lcsrs_final_domain_repair_r4.py:255–305,389–417`.] |
| R4 C2 list | Preserves diagnostic rows/order/provenance and sums counts for the original accessor. No scientific-array modification. [Same file:480–548.] |
| R4 float32 delta | Changes only `_context_status.expected_q2_delta` to reproduce writer subtraction precision; does not change Q2 predictions, actions, physical arrays, or the five predicates. [Same file:573–625,630–698.] |

Local R3, R4, and final-verifier hashes match receipt fields (`7d242eb2…`, `a471495d…`, `3cc57371…`). The receipt records 8/48 source/composition loads and 688 reconstructed pairs. [ `domain-repair-r4-receipt.json`: corresponding digest, dispatch, reconstruction fields.]

**Training admission.** Current factory V2 calls the GO-only field validator; STOP triggers the stated refusal. Launching this 100E screen with this root requires violating a frozen admission rule. [Factory V2:653–657; factory V1:550–568; `V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md:47–65`.]

**Observations.** Receipt aggregates yield 11-versus-00 **−0.049259%, 2/8 positive worlds**; teacher **+0.335158%**, learned **−0.659687%**; topology **379/707=0.536068**; informed/placebo balanced accuracy **0.705040/0.625735**. [ `result.json:source_panel.world_results`, `positive_world_count`, `composition.pooled`, `composition.pair_denominators`, `fit_panel.aggregate`.]

## INFERRED

**High confidence:** repairs enabled an admissible scientific decision; they did not reverse an earlier valid scientific decision. Earlier verifier failure meant unavailable adjudication.

**High confidence:** these observations document failure of the frozen physical prediction despite learner observability. They neither establish a causal explanation nor identify a successful replacement.

**Unverified runtime:** the audit reports r8 C1/C2 generation continuing independently and the controller mandate ending for R7→100E; no server state was checked. [Audit:517–519.]

## RECOMMENDATION

1. **Close LC-SRS R7.** Preserve all sealed artifacts and frozen manifests. No TEST, rescue rerun, second metric revision, outcome-driven changes to formulas/signs/thresholds/seeds/worlds/horizons/lambda/acceptance, or automatic CSE/EC promotion. [R7 contract §7.]

2. **Retain independent C1/C2 work.** Existing r8 computation may finish under its own authorization and claim ceiling. Any subsequent C1/C2-only training needs a fresh bounded handoff and declared inputs, updates, validation, and claims. Reuse authenticated targets and the 448-D Q2 implementation; do not reuse R7 as C3 admission or call this three-Catfish success.

3. **Consider CSE/EC only conditionally.** Establish its already-declared formula, falsifier, and outcome-independent eligibility before computation; freshly freeze execution panel, seeds, budgets, admission rules, manifests, verifier, and authority. Reuse compatible heads, target-generation infrastructure, and runner/launcher plumbing after authentication. Do not reuse R7 residuals, favorable worlds, fits, or labels to select or validate the candidate. This adjudication has not established candidate eligibility.

4. **Otherwise require a distinct design handoff.** A new C3/composition proposal needs independent justification and prospective formula/interface, falsifier, data exclusions, and evaluation contract. Fresh registration does not erase outcome-based selection. Reusable plumbing is not reusable scientific authorization. Genuine three-route training needs newly qualified sources; later physical evaluation needs authenticated BASELINE and matched ablations. The desired ordering remains a goal; source loss and oracle direction cannot establish efficacy.

5. **Record all observations as falsified-prediction evidence.** Reporting the fixed aggregates is legitimate; using residuals to choose a replacement mechanism, sign, scale, subset, or threshold is outcome-based selection and prohibited here.

**Controller decision line:** “Accept sealed `STOP_PHYSICS_R7`; the LC-SRS successor and its conditional 100E execution mandate end, with immutable evidence preserved.”

**User decision line:** “The user must decide whether to close this research direction or issue a fresh handoff for an independently justified, contract-eligible experiment.”

ASTRA_R7_STOP_ADJUDICATION=DONE