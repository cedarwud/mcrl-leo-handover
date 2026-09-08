[R2] **F3 pre-outcome design — R2**

F3 is a conditionally admitted, terminal-checkpoint observability screen with a mandatory composition veto. This memo proposes design choices; it neither freezes files nor authorizes execution. Inspection was local, read-only, offline, without SSH; no F1/F2 outcome artifacts were opened. `[R2]` marks replacements or clarifications.

1. **Admission and source artifact**

   Admit `X=D` if D passes F2; otherwise F only if F independently passes. Never try F because D subsequently fails F3. Follow the [locked ladder](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md:58).

   Reuse F2 worlds `2026121721–24`, lineages `2026092101–03`, authenticated checkpoints, and BASE trajectories. Freeze reuse before outcomes; disclose selection-conditioned development evidence, not independent confirmation.

   Use noninitial steps `1..9`: 108 world/lineage/anchor records; step 0 advances trajectories only. Store every legal `(user,action)`, masks, references, physical identities, and tape/anchor hashes.

   Let \(c=b[u\leftarrow a]\), \(\Delta s=share_u(c)-share_u(b)\), and \(\Delta E=E(c)-E(b)\):
   \[
   y_F=-\lambda(\Delta s-\Delta E)/\kappa,\qquad
   y_D=[dt\sum_{v\ne u}(R_v(c)-R_v(b))-\lambda(\Delta s-\Delta E)]/\kappa.
   \]
   Import F0 `compute_c3_targets`; retain raw bits and divide exactly once by frozen \(\kappa=10097071012.757404\). Reference targets are zero. No clipping, filtering, or reweighting.

   Replay BASE to reconstruct missing C3View features; require exact stored state, Q12, mask, reference, and action-identity agreement. Retain field `MCRL_V023_LCSRS_C3_OBSERVABILITY_V1, world`; do not substitute R7’s 32-draw targets.

2. **Neutral source and interface**

   [R2] C1 uses `c1-cluster-profile-matched-randomized-predecision-v2`: uniform anchor selection for homogeneous profiles; seeded feasible one-to-one profile matching otherwise, then uniform users within alternative-count strata. C2 uses `c2-equal-budget-uniform-predecision-v1`: uniform sampling without replacement from the sealed opportunity universe. These select sources before physical targets exist. The [materializer](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c1c2-neutral-materialization/materialize_v023_c1c2.py:1463) calls those selectors; the [adapter](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c1c2-neutral-adapters/README.md:14) authenticates equal budgets. Neither defines C3 label replacement.

   [R2] Because these predecision selectors cannot operate on immutable C3 replay rows, **declare here, pre-outcome**, F3’s equal-budget NEUTRAL as a training-only matched label permutation, key `MCRL_V023_C3_F3_NEUTRAL_V1`. Preserve R1’s strata:
   `(world,lineage,phase-bin,opening,destination-occupancy,committed-active,base-gap-bin)`.

   [R2] Encode phase bins `1–3/4–6/7–9` as `0/1/2`; opening and committed-active as `0/1`; detached destination occupancy as `0/1/2+→0/1/2`; Q12 reference-minus-action gap bins `[0,.01)/[.01,.05)/[.05,.20)/[.20,∞)` as `0/1/2/3`, retaining R7’s tie tolerance.

   [R2] Within each fitting-only stratum, sort nonreference cells by `(world,lineage,step,user,action)`. For size \(n≥2\), follow [R7’s hash algorithm](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_lcsrs_c3_placebo.py:142): compact sorted-key UTF-8 JSON `{"key":key,"stratum":[ordered stratum integers]}`; set \(h=1+\operatorname{uint64be}(SHA256(payload)[:8])\bmod(n-1)\), and `neutral[i]=true[(i-h)%n]`.

   [R2] Singletons retain labels and are permutation-ineligible. Require ≥80% eligible training nonreference cells per fold; otherwise fail. Preserve exact rows, features, masks, reference zeros, label histograms, and budgets. All seeds share the mapping; held-out labels never move. No zero-label substitute.

   Reuse R7 encoder, C3View, and transforms unchanged; targets/identifiers remain outside features. Empty legal masks yield `F3_INTERFACE_UNSUPPORTED`, without deleting users or widening masks.

3. **Learner and checkpoints**

   Reuse the structured Q3 head: dimensions `28/29/38`, `67-64-64-1` ReLU scorer, unchanged token aggregation/reference gauge. Adam: learning rate `.001`, betas `(.9,.999)`, epsilon `1e-8`, weight decay `0`. Freeze Q1/Q2; update Q3 only.

   [R2] **New F3 gap specification, not an R7 copy:** mean squared error over legal nonreference cells; batch 256, sampling anchors uniformly then cells uniformly with replacement. D/F lack sparse S/R/C semantics; do not manufacture CONTROL zeros.

   Derive three seeds from first eight SHA-256 bytes, big-endian, sign bit cleared, of `MCRL_V023_C3_F3_LEARNER_SEED_{i}_V1`, \(i=1,2,3\). Each seeds initialization and a separate PCG64 sampling stream. Paired arms share initial bytes and row schedules, with independent parameters/optimizers.

   Four LOWO folds hold out all three lineages of one world: 24 fits. Each performs exactly 2,000 updates; evaluate/checkpoint `0,100,…,2000`. Only update 2000 decides; no checkpoint selection.

4. **Observability predicate**

   Retain [R7 §§4–5](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md:61) numerical thresholds: INFORMED mean Spearman ≥.20, balanced accuracy ≥.60, informed-minus-neutral balanced accuracy ≥.05, and ≥24 positive plus ≥24 negative eligible rows. Eligibility is `|y|≥.02`; strict-zero predictions are wrong. Raw accuracy is nondecisive.

   Pool held-out nonreference rows once per seed, then average seed metrics. Use tie-aware Spearman; missing/nonfinite correlations or class denominators fail.

   [R2] **Panel adaptations:** apply `ceil(4×required_R7_worlds/8)`: INFORMED-over-NEUTRAL mean-seed Spearman wins ≥3/4 (`6/8`); each seed’s nonnegative Spearman ≥3/4 (`5/8`). These are not literal R7 compliance.

   Any terminal predicate failure ends this route. Passing establishes observability, not efficacy.

5. **Composition veto before F4**

   [R2] Prospectively retain an outcome-blind interface sanity veto, independent of prior gate outcomes. The ladder supplies the shared-tape EE/service scope; this memo specifies its pre-F4 application.

   Evaluate terminal held-out models through native masked `argmax(Q1+Q2+Q3)`, coefficient one, lowest-index exact ties. Measure matched BASE, oracle X, INFORMED, and NEUTRAL full-roster profiles; pool bits/joules before averaging seed results.

   [R2] Carry over teacher and INFORMED EE above BASE pooled and in ≥2/4 worlds: **panel adaptation** `ceil(4×4/8)=2`. Carry over INFORMED service ≥BASE−.01 in every world. Use inherited tolerances and ratio-of-sums direction checks. F2’s .001 service rule remains unchanged.

   [R2] Retain applicable mechanics, masks, matched fields, leakage/provenance checks, deterministic BLAS/OpenMP settings, and replay identity; mismatches mean `INVALID_RUN`. Independently authenticated C1/C2 context remains separately reported; unresolved HOLD blocks later episode authorization.

   [R2] **Not applicable:** ≥24 closure pairs, ≥1/world, ≥90% pair mechanics, 32-draw 11-versus-00 signature, ≥10% pair action exposure, literal-11 ≥25%/world coverage, harmful partial ≤5%, and topology ≥80%/selected-11 denominator. D/F define unilateral continuous corrections, not closure pairs. Retained closure diagnostics are nondecisive; zero selected-11 cannot veto D/F. No additional closure simulation is required.

6. **Implementation, receipts, cost, freeze**

   Reuse byte-identical F0 formulas, F1/F2 primitives, encoder/head, and applicable metrics. New code owns dense datasets, neutral mapping, LOWO/checkpoints, composition adapter, and verifier. Reuse authentication/resume patterns; the C1/C2 two-route factory cannot accept C3 unchanged.

   Seal source/mapping/initialization/code/environment hashes, consumed-row schedules, optimizer/RNG/cursor state, denominators, startup/heartbeat/terminal receipts, and atomic manifests. Verify exact resume; invalid execution permits defect repair only.

   Claim ceiling: `TRAIN_DEVELOPMENT_C3_F3_SOURCE_LEARNER_COMPOSITION_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY`.

   Implementation is non-heavy; execution belongs on Ubuntu. Retain R1’s provisional 5.3–12 serial hours for 48,000 updates, excluding evaluation; measure actual Q3/replay/composition cost. F1 r2 must provide profile counts, seconds/profile, serialization/replay timings; tape cost remains unknown.

   Freeze choices before F1/F2 outcomes. Afterwards, only survivor identity is a scientific fill-in; hashes/receipts are mechanical bindings. F4 remains separately frozen and unauthorized.

[R2] **Deltas R1→R2**

- Remove outcome-based composition motivation.
- Replace closure vetoes with EE/service predicates and explicit applicability.
- Formalize C3 neutral mapping and distinguish C1/C2 selection.
- Label world-count adaptations and newly specified loss; preserve remaining R1 choices.

ASTRA_F3_DESIGN_R2=DONE
