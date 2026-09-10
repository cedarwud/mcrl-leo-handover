**Do not proceed as configured: MARGIN_Q is applied only to realised scoring; its training and selection inputs are constructed under the inherited rule.**

`DIAGNOSTIC_NOT_CLAIM` — Codex — 2026-09-10. Read-only audit of `/home/sat/mcrl-v025-retrain-ws` and relevant sibling code. No files, constants, sealed artefacts or acceptance rules were changed.

1. **BLOCKING — The two provisioning-rule branches do not implement two complete experiments.**

   The runner builds all arm plans **before** entering the provisioning-rule loop. Proposal repair, catalogue construction, learned scores and eligibility guards therefore remain identical between SEALED and MARGIN_Q. The selected variant is installed in the child that measures realised outcomes.

   This measures the same inherited-rule decisions under two outcome evaluators. It does not evaluate decisions constructed under each provisioning rule. Evidence: [run_c3_panel_smoke.py:619](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:619), [run_c3_panel_smoke.py:631](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:631), [run_c3_rule_evaluator.py:38](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_rule_evaluator.py:38).

2. **BLOCKING — Source/planning physics and realised evaluation are not authenticated as the same physical context.**

   The parent builds its tape with the local provider. The child loads the sibling’s sealed source tree and constructs another tape. Only the selected assignment crosses the bridge; no comparison establishes equivalence of the features, labels, guards and physical context. Both tape digests are recorded without an equality or equivalence check.

   The existing successful smoke records source digest `09129e…d32e` and evaluator digest `c949f8…64a6`. Different digests alone do not prove different numerical outcomes, but matching world names do not establish equivalence either. The run presently cannot authenticate which physical problem its learned decisions were trained and selected against.

   Evidence: [run_c3_panel_smoke.py:531](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:531), [harness/sealed.py:89](/home/sat/mcrl-v025-harness-ws/harness/sealed.py:89), [run_c3_panel_smoke.py:507](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:507), [run_c3_panel_smoke.py:679](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:679).

3. **BLOCKING — The selector has a structural blind spot for C3’s joint improvements.**

   A jointly legal independent Q1+Q2 argmax becomes the search seed. C3 is exactly zero for singleton coalitions. The panel then permits only one-user moves and requires a strict score improvement.

   Consequently, when that seed is already an additive optimum, C3 cannot cause the first move—even if its prediction makes a two-user configuration decisively better. C3 counterparts share Q1/Q2, so they can commit identical configurations at **every anchor satisfying this condition**, despite different trained C3 heads.

   I reproduced this in memory: seed score `0`, singleton scores `−1, −1`, joint score `+2` for FULL and `−2` for DROP_C3. Both arms selected the seed. These are diagnostic inputs, not changes to project constants.

   The existing smoke also commits identical configurations for all four C3 counterpart pairs under both rules: FULL/DROP_C3, DROP_C1/ONLY_C2, DROP_C2/ONLY_C1, and ONLY_C3/ALL_NEUTRAL_CONTROL. That one-anchor, two-epoch observation does **not** prove equality at epoch 9000. Repaired seeds can sometimes escape through additive improvements outside their repair support.

   Evidence: [deployment.py:521](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/deployment.py:521), [learner.py:836](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/learner.py:836), [run_c3_panel_smoke.py:416](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:416), [c3_panel.py:325](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:325), [smoke.json:475](/home/sat/mcrl-v025-retrain-ws/.scratch/c3-panel-smoke-r8/smoke.json:475).

4. **BLOCKING — The “exact” source path still inherits the pilot’s one-boundary forecast substitution.**

   Importing the pilot sets `ENGINE.SELECTION_BOUNDARY_INDICES` to `(0,)`. The smoke’s private exact builder disables the primitive-source dispatcher, but retains that engine. Its C2 forecasts therefore use one boundary per offset rather than the engine’s declared `(0, 12, 24, 36, 47)`.

   Calling the production target function does not restore the omitted physical evaluations. Training longer on these labels would not become training on the declared forecast source.

   Evidence: [run_v025_pilot_c3.py:92](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:92), [run_v025_pilot_c3.py:113](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:113), [run_c3_panel_smoke.py:98](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:98), [run_v025_matrix_probe.py:156](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:156), [run_v025_matrix_probe.py:1623](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1623).

5. **BLOCKING — The supplied degeneracy reference is not the certified physical fixed point.**

   BASELINE receives the artificial score `−changed_users`, which makes staying at BASELINE optimal by construction. The runner hashes those scores, names BASELINE the fixed point, and sets `head_independent=True` and `fixed_point_certified=True`. It never demonstrates exhaustion of improving physical neighbours.

   The report consequently measures shortfall against the carrier baseline, not the required certified reference. This invalidates the specified restricted marginal, although the all-anchor pooled marginal remains separately computable.

   Evidence: [run_c3_panel_smoke.py:448](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:448), [run_c3_panel_smoke.py:684](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:684), [run_c3_panel_smoke.py:698](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:698).

6. **BLOCKING — No executable integration of the declared training/checkpoint/evaluation schedule exists in the audited panel path.**

   The sole panel caller uses one learner seed, trains two epochs, evaluates the first source anchor, and accepts only an output-directory argument. `PanelTrainer.train()` has no checkpoint writing or scheduled evaluation. The older orchestrator has checkpoint machinery but implements five learned arms and rejects exceeding its 2000-epoch budget.

   Thus there is no audited driver implementing two seeds, 9000 epochs, checkpoints every 100, evaluation **only** at 500/1000/2000/4000/9000, and the final contrast at 9000. The smoke is also evaluated on an anchor used to construct its training rows.

   The requested schedule itself is coherent for a diagnostic. Two seeds limit conclusions about seed variability; that alone is not a reason to reject the run or substitute the older twelve-seed design.

   Evidence: [run_c3_panel_smoke.py:604](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:604), [run_c3_panel_smoke.py:616](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:616), [run_c3_panel_smoke.py:752](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:752), [c3_panel.py:130](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:130), [learner.py:1043](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/learner.py:1043).

7. **DEGRADES_THE_RESULT — Several model inputs still contain constants or different quantities from their names.**

   Both source paths write off-axis angle as zero. The exact path writes `previous_beam_max_rf_over_cap` using the **current candidate configuration’s maximum required power**, clipped at one—not the previous beam’s RF value. Its candidate decoding margin and ACM features likewise come from whole-profile summaries.

   C3’s `missing_incumbent` is populated from the selected action row’s `outage`; these are different events. Its `shared_capacity` is always `1.0`, while `capacity_margin` is `10 − occupancy`, without reading physical capacity or residual capacity.

   These inputs are consumed by the networks, so their semantic limitations survive the exact-target refactor.

   Evidence: [run_v025_pilot_c3.py:450](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:450), [run_v025_pilot_c3.py:652](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:652), [run_v025_pilot_c3.py:675](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:675), [run_v025_pilot_c3.py:877](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:877), [run_v025_pilot_c3.py:905](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:905), [coalitions.py:255](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/coalitions.py:255).

8. **DEGRADES_THE_RESULT — Reseeding does not rebuild the action features against the new background.**

   Source action rows are constructed against the carrier configuration. After obtaining each learned seed, scoring still retrieves those original rows; C3 contexts also embed them. Subtracting the stored row for the seed action does not recompute occupancy, interference, power or forecasts under the seed’s other-user assignments.

   The catalogue is arm-owned, but these physical feature contexts remain carrier-based. This limits interpretation of scores around substantially different learned seeds.

   Evidence: [run_v025_pilot_c3.py:549](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:549), [run_c3_panel_smoke.py:265](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:265), [run_c3_panel_smoke.py:401](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:401), [run_v025_pilot_c3.py:875](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:875).

9. **DEGRADES_THE_RESULT — Duplicate anchor IDs corrupt the degeneracy restriction.**

   Status is stored by `anchor_id`, overwriting earlier rows with the same ID. All rows remain in the sums, but the last status is then applied to every duplicate. The runner’s ID omits learner seed and checkpoint.

   I reproduced two rows with the same physical-anchor ID: DROP_C3 was below reference in the first and above in the second. The report returned zero below-reference rows and included both in the restricted marginal. This becomes relevant when combining the planned seeds using the current ID format.

   Evidence: [c3_panel.py:427](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:427), [c3_panel.py:474](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:474), [run_c3_panel_smoke.py:694](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:694).

10. **DEGRADES_THE_RESULT — First-improvement is consistent within the panel, but differs from the established reference traversal.**

    All panel arms use the same implementation: strict first improvement, restarting the scan after an accepted move, over a static catalogue ordered by configuration-ID strings. There is no arm-specific best-improvement branch.

    The sibling reference instead traverses numerically ordered users and their ordered actions, constructs neighbours from the current configuration, and continues to the next user after accepting a move. These procedures can reach different optima. Their results and certificates are not interchangeable merely because both say “first-improvement.”

    Evidence: [c3_panel.py:223](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:223), [run_v025_matrix_probe.py:657](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:657), [harness/anytime.py:192](/home/sat/mcrl-v025-harness-ws/harness/anytime.py:192), [harness/anytime.py:223](/home/sat/mcrl-v025-harness-ws/harness/anytime.py:223).

11. **DEGRADES_THE_RESULT — The deployment receipt can certify an untrained model.**

    It checks update counters against `completed_source_epochs`, allowing `0 == 0`, then returns `all_learned_arms_retain_update_deploy_all_heads=True`. I reproduced that result before training. The actual smoke trains first, so this is not an observed head-initialisation defect in that execution; it is an ineffective integration guard.

    Evidence: [c3_panel.py:136](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:136).

12. **DEGRADES_THE_RESULT — The supplied report does not expose the full factorial’s source contrasts.**

    The runner requests only FULL-minus-each-other-arm. It omits, for example, ONLY_C1 versus ALL_NEUTRAL_CONTROL and the other backgrounds needed to inspect each route across the factorial. The generic report accepts those pairwise contrasts, and retained outcomes permit later calculation, so this is a reporting omission rather than a reason to repeat physical evaluation.

    Evidence: [run_c3_panel_smoke.py:705](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:705).

13. **COSMETIC — The C3 encoder’s “IDs … are not features” description is inaccurate.**

    Member features explicitly contain hashed satellite and beam identities. This is an existing architectural input, not an audit recommendation to change the architecture.

    Evidence: [coalitions.py:63](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/coalitions.py:63), [coalitions.py:240](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/coalitions.py:240).

**All-head retention passed.** The eight source combinations are explicit; every arm clones all three heads and updates every route. Neutral substitution preserves inputs/support and replaces targets with zero. Deployment uses Q1 and Q2 scores and the C3 interaction head. BASELINE has no learner. Using the existing smoke source files and seed, I ran two epochs entirely in memory: **all 24 heads changed parameters and all 24 Adam step counters reached two**. No missing, frozen or initialisation-only head was found. Evidence: [c3_panel.py:45](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:45), [c3_panel.py:92](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:92), [c3_panel.py:104](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:104), [learner.py:147](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/learner.py:147), [learner.py:635](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/learner.py:635), [run_c3_panel_smoke.py:270](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:270).

**No realised-cache leak into selection was found.** The digest includes tape, world, time, complete assignment, physical/run settings, evaluator identity, field, boundaries, transition and prefix history. Selection finishes before keys and realised outcomes are requested; pre-barrier cache access raises. Oppositely ranked realised values did not change selections in the poisoning check. The caller hashes physical-setting labels rather than the complete object, but the fixed configuration is additionally covered by the run-setting and sealed-evaluator identities; I did not establish a current collision. Evidence: [c3_panel.py:268](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:268), [c3_panel.py:307](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:307), [c3_panel.py:354](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:354), [run_c3_panel_smoke.py:645](/home/sat/mcrl-v025-retrain-ws/scripts/run_c3_panel_smoke.py:645).

**The degeneracy function is reporting-only for uniquely identified anchors.** It computes exact-sign comparisons, retains every anchor in the primary pooled marginal, and separately reports the subset where both contrast arms meet the reference. An empty subset returns no marginal. Its defects are the supplied reference and duplicate-ID handling, not silent removal from the primary population. Evidence: [c3_panel.py:433](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:433), [c3_panel.py:487](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/c3_panel.py:487).

The primitive path still duplicates geometric legality into validity and survival; the smoke bypasses that path for its training rows. Its exact path forwards the engine’s distinct fields correctly. The exact C1 builder’s availability values of `1.0` are unused by the C1 target calculation, so those particular constants do not alter its label. Evidence: [run_v025_pilot_c3.py:427](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:427), [run_v025_pilot_c3.py:689](/home/sat/mcrl-v025-retrain-ws/scripts/run_v025_pilot_c3.py:689), [targets.py:169](/home/sat/mcrl-v025-retrain-ws/src/mcrl/physics_v025/targets.py:169).

Verification comprised eight existing pure harness tests called directly without pytest filesystem output, the in-memory head-update check, and the two counterexamples above. No production run, smoke rerun or acceptance run was launched. Execution stayed within two concurrent audit processes. The named supporting decision documents were not present in the permitted sibling scratch directories; the matched-anchor verification was available at the `c1c2suff` sibling root. Findings above rest on code and inspected receipts.

The note is printed in full here. `PANEL-AUDIT-Codex-2026-09-10.md` was not created: the exception to “never modify anything” remains unanswered, and the retrain workspace is outside the permitted writable roots.
