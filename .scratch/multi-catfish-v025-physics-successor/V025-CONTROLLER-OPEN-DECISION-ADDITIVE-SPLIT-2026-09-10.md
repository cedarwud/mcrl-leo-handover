# Open owner decision — the additive split is ill-conditioned, and replacing it means opening contract v1
Recorded 2026-09-10 from the target-design review. `DIAGNOSTIC_NOT_CLAIM`. No training run, no policy run; nothing sealed was modified and the review stopped at the sealed boundary by instruction. Related: [pair insufficiency], [C1/C2 estimator artefact], [novelty closed].

## First, a fact that invalidates a body of earlier evidence
**The 176,223 checked-in pilot source rows do not carry the production targets.** The pilot's fallback substitutes a per-user-local monotone squash of a gain ratio, which by construction contains **no coupled-fixed-point content at all**. The numeric signature confirms it: the first label saturates at exactly −1.0 on 1,000 of 9,805 sampled rows, the second at exactly −3.0 on 1,865.

The consequence is quantitative. A plain linear model on the sealed 16 features reaches **R² 0.598 and 0.801 pairwise ordering on the surrogate**, against **R² 0.151 and 0.650 ordering on the production target**. Every earlier read of "the first head is learnable" was measuring an easier problem. No conclusion about learnability may be drawn from those rows. The 180 coalition rows in that run are genuine; the source rows are not the production estimand.

## Second head: well-posed
The object is bounded, gauge-consistent under the differences the pipeline actually takes, and its discrete component is a closed-form function of features the head already receives. There is no discontinuity a smooth regressor cannot represent on the observed support. **If it underperforms, the cause is features or estimation, not what it is asked to predict.** The review explicitly declined to manufacture a redesign for it.

This resolves an apparent disagreement with the earlier admissibility diagnostic, which found no admissible feature separating one colliding pair. Both hold: specific pairs are indistinguishable, while the target as a whole is well-posed — and the independent estimator audit measured the collision ceiling at 0.9446, so collisions bind about 5.5 % of the variance, not the bulk.

## First head: reformulate, on three measured facts
1. **79.3 %** of the target's variance sits in whole-network coupled terms that require exactly the solve the head exists to avoid — and **98.9 %** of the externality's variance is *within* an anchor, so none of it cancels in the ranking.
2. With the production head shape and the sealed vector, held-out **R² 0.151**, pairwise ordering **0.650**. A ranking objective reaches only 0.693. An oracle that removes just the cross-user externality reaches **0.902**.
3. **Even an exact head does not produce the intended selector behaviour.** The additive term grows about linearly in coalition size — median **200.4** at the additive optimum against **8.02** for the best single move — so the entire correction sits in an interaction term of opposite sign and comparable magnitude: **+480.113 and −440.079 to produce a +40.034 result** at size 100.

That third fact is the one that matters. Two large opposing quantities cancel by roughly ten to one to produce the answer, so any error in either is amplified tenfold at the decision. **This is an ill-conditioned split, not a learning failure.** No amount of data or capacity repairs a conditioning problem.

## Why this is the same finding four other measurements reached
The architecture comparison found a set-level ranker and a resource-aware variant both beating the pairwise decomposition on mean regret, 5.25 and 5.68 against 7.00. The exact-pair replay found pairwise truncation reversing the winner at 27.8 % of anchors, 92 % of those beyond the project's margin. The retraining pilot found six of ten selections landing outside the training support with interaction error of 50.077 and 60 % sign agreement. All four are the same defect seen from different sides: **the per-user additive decomposition is the wrong object to rank on.**

It is also the mechanism behind the owner's own observation that a coordination layer makes the learned network's effect invisible. The learner is asked to estimate two large quantities whose difference is small, downstream of a non-learned optimiser that already found the bulk of the value.

## The proposed alternative
Rank on a single set-conditioned prediction of the joint objective change rather than on a sum of per-user deviations plus an interaction correction. The sealed identity already reconstructs exactly this quantity, and the permutation-invariant set head and coalition context that would carry it **already exist in the codebase**. Predicting the sum directly removes the tenfold cancellation. The per-user heads would be retained for what they are demonstrably adequate at and what the contract already uses them for: generating the reference proposal and repairing joint conflicts, where only within-user ordering matters.

## What it costs — this is the decision
The reformulation **touches sealed artefacts and frozen manifests**:
- contract v1, sealed 2026-09-08, whose §B4 fixes the decomposition and its identity as a known-answer test, §C1 fixes the head form and per-user deployment, and §C2 fixes the deployed score;
- the target module's decomposition and identity assertion;
- the deployment scorer's additive-plus-interaction form;
- the row label fields and both feature-schema digests, which are carried in every shard header and re-checked on read;
- the two acceptance tests written against exactly this identity.

Contract §C6 states that a negative or inconclusive result does not permit changing features, catalogues, sources or regimes. **So opening it is the owner's decision, and the review correctly refused to prepare the change.**

The honest framing for that decision: the evidence that the split is ill-conditioned is arithmetic, not outcome-dependent — the ten-to-one cancellation is a property of the decomposition at coalition size, visible with an exact head and no learner involved. It is not a result that came out unfavourably.

## One repair owed regardless
The pilot's training rows carry surrogate labels. Whatever is decided about the target object, that path must stop being used to generate anything that informs a learnability judgement.
