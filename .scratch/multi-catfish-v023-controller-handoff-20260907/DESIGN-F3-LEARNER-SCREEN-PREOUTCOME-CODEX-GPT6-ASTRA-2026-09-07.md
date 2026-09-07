F3 should be a **conditionally admitted, terminal-checkpoint observability screen with a mandatory composition veto**. This memo proposes the missing design choices; it does not freeze files or authorize execution. Inspection was local and read-only; no network, SSH, or F1/F2 outcome artifacts were opened.

1. **Admission and source artifact**

   Admit only `X = D` if D passes F2; otherwise F if F independently passes. Never try F because D subsequently fails F3. This follows the [locked ladder](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md).

   **Gap—F3 panel:** reuse F2 worlds `2026121721–24`, lineages `2026092101–03`, authenticated checkpoints, and BASE trajectories. Freeze this reuse before outcomes: the ladder does not require a fresh F3 panel. Disclose selection-conditioned development evidence, not independent confirmation.

   **Gap—anchors:** use R7’s noninitial steps `1..9`: 108 world/lineage/anchor records; step 0 advances the trajectory only. Each record contains every legal `(focal user, action)`, native masks, references, physical identities, and tape/anchor hashes.

   Let \(c=b[u\leftarrow a]\), \(\Delta s=share_u(c)-share_u(b)\), and \(\Delta E=E(c)-E(b)\):
   \[
   y_F=-\lambda(\Delta s-\Delta E)/\kappa,\qquad
   y_D=[dt\sum_{v\ne u}(R_v(c)-R_v(b))-\lambda(\Delta s-\Delta E)]/\kappa.
   \]
   Import F0 `compute_c3_targets`; retain raw bits and divide exactly once by frozen \(\kappa=10097071012.757404\). Reference targets are zero. No clipping, filtering, or reweighting.

   F2 tapes lack complete C3View features. Replay BASE to reconstruct them; require exact stored state, Q12, mask, reference, and action-identity agreement. Keep the field `MCRL_V023_LCSRS_C3_OBSERVABILITY_V1, world`; do not replace tape labels with R7’s 32-draw LC-SRS targets.

2. **Neutral source and interface**

   **Premise correction:** [C1/C2 neutral materialization](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c1c2-neutral-materialization/README.md:9) randomizes predecision source selection, then computes physical targets. Its rules are `c1-cluster-profile-matched-randomized-predecision-v2` and `c2-equal-budget-uniform-predecision-v1`. Neither declares same-row target replacement or zero labels.

   **Proposed F3-specific neutral:** adapt [R7’s matched placebo](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md:533). Preserve rows/features/masks/reference zeros; cyclically permute nonreference labels within training-only strata:
   `(world,lineage,phase-bin,opening,destination-occupancy,committed-active,base-gap-bin)`.
   Reuse R7 phase/gap bins; explicitly extend opening to `{0,1}` and occupancy to `{0,1,2+}` for general D/F actions. Sort `(world,lineage,step,user,action)`; use R7’s nonzero-shift hash algorithm with key `MCRL_V023_C3_F3_NEUTRAL_V1`. Singletons retain labels and count as ineligible; require R7’s ≥80% permutation coverage per fold. Held-out labels never move.

   Reuse [R7’s encoder](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:2234), C3View, and transforms unchanged. Targets and identifiers remain outside features. **Interface limitation:** the existing view/head rejects empty legal masks; such anchors produce `F3_INTERFACE_UNSUPPORTED`, without deleting users or widening masks.

3. **Learner and checkpoints**

   Reuse the [structured Q3 head](/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/ee_axis_lcsrs_c3_head.py): dimensions `28/29/38`, `67-64-64-1` ReLU scorer, token aggregation and reference gauge unchanged. Adam: `0.001`, betas `(0.9,0.999)`, epsilon `1e-8`, weight decay `0`. Freeze Q1/Q2; update Q3 only.

   **Gap—loss:** D/F targets do not have R7’s sparse S/R/C semantics. Declare mean squared error over legal nonreference cells; batch 256, sampling anchors uniformly then cells uniformly with replacement. Do not assign artificial zero targets to R7 CONTROL cells.

   Derive three learner seeds using first eight SHA-256 bytes, big-endian, sign bit cleared, from:
   `MCRL_V023_C3_F3_LEARNER_SEED_1_V1`,
   `MCRL_V023_C3_F3_LEARNER_SEED_2_V1`,
   `MCRL_V023_C3_F3_LEARNER_SEED_3_V1`.
   Use each seed for initialization and a separate PCG64 sampling stream. Paired arms share initial bytes and row schedules, with independent parameters/optimizers.

   Four LOWO folds hold out **all three lineages** of one world: 24 fits total. Each performs exactly 2,000 updates; checkpoint/evaluate `0,100,…,2000`. Only update 2000 decides; no checkpoint selection.

4. **Observability predicate**

   Copy [R7 §4–§5](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md:73): INFORMED mean Spearman ≥0.20, balanced accuracy ≥0.60, informed-minus-neutral balanced accuracy ≥0.05, and ≥24 positive plus ≥24 negative eligible rows. Sign eligibility remains `|y|≥0.02`; strict-zero predictions are wrong. Report raw accuracy nondecisively.

   Pool each held-out nonreference row once per seed; average seed metrics. Use tie-aware Spearman on all such rows. Missing/nonfinite correlations or class denominators fail.

   **Gap—eight versus four worlds:** preserve R7’s proportions, rounding required counts upward: `ceil(4×6/8)=3` informed-over-neutral world wins; each seed needs nonnegative Spearman in `ceil(4×5/8)=3` worlds. This is an explicit panel-size adaptation, not literal R7 compliance.

   Falsifier: any terminal predicate failure ends this F3 route. Passing establishes observability, not efficacy.

5. **Composition veto before F4**

   Yes: [R7 STOP](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/R7-STOP-PHYSICS-RESULT-2026-09-07.md) demonstrates that fit success alone is insufficient.

   Evaluate terminal held-out models once through native masked `argmax(Q1+Q2+Q3)`, coefficient one, lowest-index exact ties. Measure matched BASE, oracle X, INFORMED, and NEUTRAL full-roster profiles; pool bits/joules before averaging seed results.

   **Gap—D/F are not closure-specific:** prospectively retain R7’s closure panel as a conservative interface stress test, without claiming it defines D/F. Reuse outcome-blind pair enumeration and 32 matched pair-profile draws. Require inherited thresholds: ≥24 pairs, ≥1/world; action change ≥10%; literal-11 ≥25%; harmful partial ≤5%; topology consistency ≥80%; teacher and learned EE above BASE pooled and in ≥half the worlds; literal-11 present in ≥half; service ≥BASE−0.01 per world. Half means two here. Selected-11 denominator zero fails.

   Topology means source empty and destinations still occupied by nonmembers after simultaneous selection. Measure without rescoring or coordination. F2’s separate 0.001 service rule remains unchanged.

6. **Implementation, receipts, cost, freeze**

   Import byte-identical F0 formulas, F1/F2 physical primitives, encoder/head, and applicable metric functions. New code owns dense-target datasets, neutral mapping, LOWO/checkpoint orchestration, composition adapter, and verifier. Reuse C1/C2 authentication/resume patterns; their two-route factory cannot accept C3 unchanged.

   Seal source/mapping/initialization/code/environment hashes, consumed-row schedules, optimizer/RNG/cursor state, all denominators, startup/heartbeat/terminal receipts, and atomic manifests. Verify exact resume; invalid execution permits defect repair only.

   Claim ceiling:
   `TRAIN_DEVELOPMENT_C3_F3_SOURCE_LEARNER_COMPOSITION_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY`.

   Implementation is non-heavy. Execution belongs on Ubuntu: 48,000 updates imply **5.3–12 serial hours** using today’s supplied Q1/Q2 proxy, excluding evaluation. Measure actual Q3 throughput, memory, replay/token cost, and composition cost. F1 r2 must supply tape profile counts, seconds/profile, serialization and replay timings; tape cost remains unknown.

   Before any F1/F2 outcome, freeze every choice above, including failure rules and all checkpoints. After F2, only survivor identity is a scientific fill-in; hashes and receipts are mechanical bindings. F4 remains separately frozen and unauthorized.

ASTRA_F3_DESIGN=DONE