The audit is complete. The note is written to `/home/sat/mcrl-v025-selector-ws/audits/PANEL-AUDIT-FABLE-2026-09-10.md` (the retrain workspace is read-only and has no audits directory, so it went under my primary working directory). Full text follows.

---

**DO NOT PROCEED AS CONFIGURED. Blocking defect: the `MARGIN_Q` branch never reaches the variant seam. `scripts/run_c3_rule_evaluator.py:100` scores every selected configuration through the sealed probe's scalar `StepEvaluator.evaluate`, which bypasses `evaluate_ar_tdm_catalogue` (the only place the variant is installed, `:40`), so "both provisioning rules" is `SEALED` run twice under two labels. The r8 receipt proves it: all eight `MARGIN_Q` contrast marginals equal the `SEALED` ones to 16 significant digits.**

# C3 panel harness audit — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`. Audit only. Nothing in `/home/sat/mcrl-v025-retrain-ws` or any sibling workspace was modified. No constant, threshold, seed, horizon, price, guard, acceptance rule, sealed artefact, manifest, contract, acceptance test or harness file was changed. One process was used (the harness contract tests, run with `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1`). Auditor: Claude Fable 5.1.

Scope read in code: `src/mcrl/stagec_v025/c3_panel.py`, `scripts/run_c3_panel_smoke.py`, `scripts/run_c3_rule_evaluator.py`, `tests/stagec_v025/test_c3_panel_harness.py`, the relevant parts of `scripts/run_v025_pilot_c3.py`, `learner.py`, `deployment.py`, `state.py`, the engine `.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py`, the sealed probe and variant seam in `/home/sat/mcrl-v025-harness-ws`, the r8 receipt `.scratch/c3-panel-smoke-r8/smoke.json`, contract v1/v1.1/v1.2, and `MATCHED-ANCHOR-TIER-2026-09-10.md` in `mcrl-v025-c1c2suff-ws`. Line numbers for the engine refer to the retrain-ws copy unless prefixed `sealed`.

## Findings

### BLOCKING

**B1. `MARGIN_Q` is not engaged; the two-rule branch is one rule twice.**
`scripts/run_c3_rule_evaluator.py:40` installs the variant by assigning `reference.probe.evaluate_ar_tdm_catalogue`. In the sealed probe that seam is consulted only inside `StepEvaluator.evaluate_many` (`sealed …/run_v025_matrix_probe.py:1356-1387`). The bridge constructs `probe.StepEvaluator` (`:58-67`) and then calls `evaluator.evaluate(config)` per request (`:100`); the scalar `evaluate` (`sealed …:1481-1495`) goes through `build_shared_tape`/`score_setting` and never touches the seam. `harness/proof.py:13-16` states that `MARGIN_Q` at α=0.10 must change `max_rf_power_w` and mode counts, so identical outputs are not a coincidence. Receipt evidence: `.scratch/c3-panel-smoke-r8/smoke.json` `screen_by_provisioning_rule` gives, for both rules, FULL−BASELINE `4.017143208622553`, FULL−DROP_C1 `0.00884473214140279`, FULL−DROP_C2 `-0.01745324091886997`, and so on for all eight contrasts. The receipt still *looks* like two rules because `evaluator_sha256` hashes the variant name and source (`:68-73`) and the cache key's `physical_setting_sha256` hashes the rule label (`run_c3_panel_smoke.py:645`). Consequence if run as configured: half the realised compute is a duplicate and the report attributes one physics to two rules. The harness's own contract tests cannot catch this (they never call the bridge; 9/9 pass, verified).

**B2. The declared protocol has no implementation to audit.**
The only entry point, `scripts/run_c3_panel_smoke.py`, hard-codes one learner seed and two epochs (`:604-612`), one tier anchor (`:616`), step 0 in every plan-building call (`:345, :354, :405, :416, :651`) and `--steps 5 --step 0` for the child (`:483-487`). `PanelTrainer` (`c3_panel.py:68-151`) has no checkpoint write or load. The sealed checkpoint loader `V1LineageOrchestrator.load_checkpoint` rejects `completed > LEGACY_EPOCH_BUDGET` (2000) at `learner.py:1186` and any arm inventory other than the five production arms at `:1170-1171`, so 9000-epoch, eight-arm checkpoints at 100-epoch cadence cannot use the sealed format. Two seeds, five evaluation points, multiple anchors and both rules therefore require new driver code that does not exist in this or any sibling workspace (searched all `mcrl-v025-*-ws` for `c3_panel`, `PanelTrainer`, `select_then_realise`). The harness document says this itself (H6.10). If the run is launched from the smoke script it is a two-epoch smoke; if launched from new code, that code is unaudited and will inherit D7 and D8 below if copied from the smoke.

### DEGRADES_THE_RESULT

**D1. The degeneracy screen's reference is the carrier, not a head-independent fixed point.**
`degeneracy_report` (`c3_panel.py:395-506`) is correct: it never drops an anchor (`anchors_retained`, `:502`), reports the all-anchor marginal and the restricted marginal for every contrast (`:487-498`), and uses exact cross-multiplication with no tolerance (`:433-436`); the test at `test_c3_panel_harness.py:213-250` confirms both views are returned. But what the smoke feeds it is BASELINE's own realised outcome of `base.assignments` (`run_c3_panel_smoke.py:682, :695-697`) with a self-attested certificate over the BASELINE catalogue whose scores are `-changed_users` (`:448-451, :684-692`), so the "fixed point" is trivially the carrier. In the receipt every learned arm is 100 users away from the carrier and about 5× its EE (`FULL-minus-BASELINE = +401 %`), `below_reference` is false for all nine arms, and the restricted subset equals the full set. The pre-declared reference (matched-anchor tier and reseeded-span: the head-independent unilateral fixed point) would sit far above the carrier. As wired, the screen cannot bite.

**D2. All learned arms start from a C3-blind repair seed that is itself the dominant effect.**
`_arm_owned_plans` (`run_c3_panel_smoke.py:395-400`) calls `ProfileSelector.repair_reference` (`deployment.py:512-547`), which takes the Q1+Q2 argmax over the *legal rows of the carrier catalogue*. That catalogue contains whole-profile `s0-top-two` rows that move every user to its top-margin option (engine `:610-616`). In the receipt every raw proposal failed the served guard (`proposal_repaired: true` for all eight), all eight arms collapsed to the same seed (`arm_owned_plans.*.seed_sha256` identical), and that seed differs from the carrier on all 100 users. The +401 % over BASELINE is therefore a head-independent geometry effect; the learned contrasts are ±1.7 % perturbations on top of it. This is consistent with the matched-anchor tier note ("C3 changes ranking, not the seed"), but the report must say the contrast is conditional on a C3-blind seed chosen by C1+C2.

**D3. The C3 head can only act on the second first-improvement step, through at most ~20 pairwise rows.**
`_select` (`c3_panel.py:318-340`) offers only Hamming-1 neighbours within the static catalogue. `_score` (`run_c3_panel_smoke.py:264-281`) adds `model.interaction` only when the candidate differs from the seed, and `AdamSetInteractionHead.score` returns 0.0 for one changed user (`learner.py:836-838`). So the first move is always C3-blind; C3 matters only if the first accepted unilateral move is one of the top-10-user × top-2-option moves that have a pairwise row (engine `:625-631`); `s0-top-two` and `beam-evacuation` rows are unreachable by Hamming-1 chains. Receipt: the committed configurations form exactly the groups {FULL, DROP_C3}, {DROP_C1, ONLY_C2}, {DROP_C2, ONLY_C1}, {ONLY_C3, ALL_NEUTRAL_CONTROL} plus BASELINE, so all four C3 contrasts were exactly zero at the only tier anchor. Hamming distances between the learned groups (2, 3, 3) show one group reached a pairwise row, so the channel is not closed by construction, but it is narrow, and the harness discards the accepted-move count (`c3_panel.py:339`), so the report cannot show how often C3 was consulted. This is a consequence of the pre-declared first-improvement tier, not a code bug, but it must be reported per anchor or the C3 contrast is uninterpretable.

**D4. The informed C3 source is one row per anchor, the best pair by exact C1+C3.**
`run_v025_pilot_c3.py:776-791` selects a single pairwise coalition per anchor by maximum exact `C1 + C3`. The C3 training set is therefore A rows for A anchors, all top-synergy pairs, and the neutral source is those rows with Ψ = 0. Contract §B5/§C2 asks for the residual over the coalition support of the bounded catalogue. At 9000 full-batch Adam epochs the set head memorises A rows with positive bias; what "informative C3" means in this run is "memorised best pairs".

**D5. Source-side physics is not the sealed realised physics.**
`src/mcrl/physics_v025` in the retrain workspace differs from `mcrl-v025-harness-ws/sealed/src/mcrl/physics_v025` in nine files (acm 40, adapter 24, architectures 149, batch 128, channel 82, provider_legacy 269, resolution 25, tapes 97, targets 86 changed lines). The sealed `acm.py` has `select_transmitted_mode`/`decode_transmitted_mode` with the fading-quantile margin; the source side has neither, and its `StepEvaluator` has no `fading_quantile_alpha`. Features and labels are built on one physics, outcomes realised on another; the receipt records `source_tape_sha256 09129e…` versus `evaluation_tape_sha256 c949f8…`. Same domain and world seed, so geometry should coincide, but equivalence is unproven (harness H6.3). If the owner later requires label/realisation physics equivalence, the training must be redone.

**D6. Selection-time features are carrier-context, applied to seed-context candidates.**
`_score` looks up `rows_by_user_action[(user, identity)]` (`run_c3_panel_smoke.py:265-271`), rows whose occupancy, beam/satellite activity and coupled nominal margin were computed with `base.mapping` = carrier (`run_v025_pilot_c3.py:598-600, :640-690`), while the candidate is a deviation from a seed 100 users away (D2). The guard evaluates the true configuration; the learned scores do not. Inherited from the fixed-reference pilot, but the arm-owned seed makes the mismatch total.

**D7. The only cache-key builder fills context fields with constants.**
`run_c3_panel_smoke.py:639-652`: `decision_time_ns=0`, `prefix_history_sha256` = hash of `{"step": 0, "prefix": []}`, `physical_setting_sha256` = hash of two labels, `transition_sha256` = the source-side incumbent while the child derives its own (`run_c3_rule_evaluator.py:55-57`). Harmless in the smoke because a fresh cache is created per rule per anchor (`:633`); a driver that shares one cache across steps of a world would return step-0 outcomes for step-k queries. The module itself is sound: `PhysicalCacheKey` binds all eleven declared dimensions and each changes the digest (`c3_panel.py:233-283`, test `:189-210`); `realise` raises before `seal_selection` (`:307-308`); `select_then_realise` selects all nine, seals, then realises the union (`:354-363`). I could not construct a leak: `_score` and `guarded` reference only nominal evaluators (`run_c3_panel_smoke.py:343-349, :383-393`), the stage-2 forecast features are nominal (engine `:1615-1623`), and the rule child is never referenced during plan building.

**D8. The plan-builder guard is a 48-boundary nominal evaluation with no rekey ledger.**
`run_c3_panel_smoke.py:343-350` constructs `StepEvaluator(..., field="nominal", run_setting=...)` without `boundary_indices` (default `tuple(range(48))`, engine `:777`) and without `cell_rekeyed_users`; the row builder uses `(0,)` and the rekey ledger (`run_v025_pilot_c3.py:549-556`). `served` is "decoding time > 0 over the evaluated boundaries" (engine `:838`), so the served-count guard is the committed-resolution served set, not the declared selection-time count. It is internally consistent (the carrier reference uses the same validator) but it is a different guard than declared, it is wrong for step > 0 anchors, and it is the cost driver in C1.

**D9. Protocol scale: two seeds, 9000 epochs, no stopping-rule field.**
Contract §C7 declares 12 seeds (v1.1: 16); two seeds give no seed-variance estimate, acceptable for a diagnostic only if labelled. `LEGACY_EPOCH_BUDGET = 2000` is part of `LEGACY_TRAINER_LITERALS` (`learner.py:40, :64`); `PanelTrainer.train_epoch` bypasses the orchestrator's budget guard by calling `head.update` directly (`c3_panel.py:120-123`). Reporting at 9000 with four pre-declared trajectory points avoids checkpoint picking. Note the existing epoch-trend evidence: the FULL−DROP_C3 sign reversed between epochs 600 and 1000 on a defective model, so 9000 full-batch epochs on ~2k pairs and A coalition rows is an overfitting regime by design and should be read as such.

**D10. Both rules share one plan set.**
Plans are built once (`run_c3_panel_smoke.py:619-626`) and the same tuple is passed to both rule branches (`:662`). Even after B1 is fixed, a rule can change realisation only, never selection, catalogue or guard (harness H6.2). Whether that is what "both provisioning rules" means is an owner decision to record before spending.

### COSMETIC

**C1.** The repair catalogue and its 48-boundary validation are rebuilt for every arm from identical inputs (`run_c3_panel_smoke.py:343-361` inside the arm loop, plus `:438-447` for BASELINE): nine identical builds and eight identical 1 005 × 48 validations. This is the "residual plan preparation" of ~936 s per anchor, about two-thirds of the projected 185 worker-hours.

**C2.** Names that do not match contents in both row paths: `off_axis_angle_rad=0.0` (`run_v025_pilot_c3.py:450, :661`; Q1 feature 7, `state.py:37`, is a constant column); `previous_beam_max_rf_over_cap = min(1, required_ratio)` of the *candidate* (`:449, :675-677`); `decoding_availability=1.0, useful_availability=1.0` in the C1 label (`:626-636`); `legal=True` unconditionally (`:697`). Constant columns are harmless to Adam; the labels mislead readers.

**C3.** `_select` discards `_accepted` (`c3_panel.py:339`); the receipt should carry per-arm accepted-move counts so D3 can be quantified.

**C4.** The certificate's `fixed_point` assumes catalogue row 0 is the seed (`run_c3_panel_smoke.py:687-691`); true today (engine `:655-660`) but not asserted.

**C5.** `worker_processes_used_peak: 2` and `process_limit: 4` are literals (`run_c3_panel_smoke.py:716-717`), not measurements.

**C6.** `deployment_receipt` checks update counts and payload presence (`c3_panel.py:136-142`) but not contract §C5's "neutral-trained head differs from initialisation".

## Direct answers to the seven questions

1. **All heads retained, updated, deployed: yes.** `PanelTrainer.train_epoch` loops every route for every arm and picks the informed or neutral batch by `PANEL_SOURCE_MAP` (`c3_panel.py:104-128`); neutral batches keep support and zero the targets (`learner.py:147-166, :635-657`); clones are deep (`learner.py:704-716, :833-834, :938-941`); all arms clone one initialisation (`c3_panel.py:89-92`); proposal uses C1+C2 (`run_c3_panel_smoke.py:330-341`) and catalogue scoring uses q1, q2 and psi (`:264-281`). No arm drops a head or leaves one at initialisation. Caveat D3 on how far psi reaches.
2. **Cache leak: none found.** See D7. The two defects are the constant key fields and, more importantly, B1 (the realised evaluator is not the rule it claims to be).
3. **Degeneracy screen: reporting-only, verified.** Defect is the reference fed to it (D1).
4. **Local search: identical function, genuine first-improvement.** `_select` is the same for all nine arms (`c3_panel.py:355`); `first_improvement` takes the first strict improvement in catalogue order (`:215-230`); order is base then `configuration_id`-sorted (engine `:655-660`); tests `test_c3_panel_harness.py:109-153`. Traversal sequences differ by arm only because catalogues are arm-owned.
5. **Distinguishable: not vacuous by construction, but** all four C3 contrasts were exactly zero in the smoke (D3) and all eight arms shared one seed (D2).
6. **Protocol:** B2 (nothing implements it), B1 (one rule, not two), D9, D10.
7. **Other:** D4, D5, D6, D8, C2.

## What would make this run wasted

In order: B1 (half the compute duplicates the other half under a false label), B2 (nothing runnable matches the declaration), D1 (the pre-declared screen cannot bite), D3 with C3 (the C3 contrast may be zero at most anchors with no record of why), D5 (labels and outcomes from different physics). Nothing else forces a rerun; D2, D4, D6, D8, D9, D10 are interpretability limits that must be stated in the report.

Harness contract tests: 9 passed (`tests/stagec_v025/test_c3_panel_harness.py`). They do not exercise the rule bridge, the plan builder or the row builder.
