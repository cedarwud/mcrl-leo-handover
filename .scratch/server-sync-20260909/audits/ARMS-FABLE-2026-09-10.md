# Design note: is "each component individually improves over a control" testable with the sealed panel?

`DIAGNOSTIC_NOT_CLAIM`. Nothing was run and nothing sealed was touched. Sources read: the stage 6–8 contract v0, the pre-outcome contingency ladder, the engine-audit decisions, the stage-4h report with its 14-arm smoke table, and the Psi witness report.

**Answer to question 1.** The requirement is not well-posed as stated, for three separate reasons. First, "individually improve over a control" names at least three different experiments, and the sealed panel runs only one of them. Second, "control" is undefined among three candidates that differ by two orders of magnitude, and one of them makes the requirement trivially true. Third, the materiality rule attached to it cannot be met by a component adding value, because the entire span a ranker can add above the certified fixed point is about the same size as the margin demanded per contrast. Any leave-one-out gap that clears the margin is therefore evidence that the leave-one-out arm fell below the fixed point, not that the missing component was worth that much. The scientifically meaningful reading is the leave-one-out marginal on realised pooled efficiency, with every arm referenced to the certified unilateral fixed point and screened for degeneracy. That reading is measurable with the six sealed arms plus deterministic reference arms that need no learner seeds. The "singles" reading is not measurable without three added arms, and I would not add them.

## Readings, controls and the headroom problem

The phrase admits these readings. The owner's own sentence mixes the first and third.

- **Leave-one-out marginal.** FULL minus DROP_Cx for each x. The reference is the arm with the other two components present. This is what the six sealed arms measure, and it is the "full-minus-one" style of the source paper.
- **Single-component-only.** ONLY_Cx minus control. The reference is the all-neutral control. This is the paper's second style. No sealed arm provides it.
- **Full factorial ordering.** FULL above every pair, every pair above control, every single above control. Eight cells. The pairs are exactly the DROP arms, so the sealed panel covers five of the eight cells. The three singles are missing.

The leave-one-out reading is the meaningful one because it answers the question the deployed system poses: given the architecture as built, does removing this head cost realised efficiency. The single-only reading answers whether a head is deployable alone, which the paper does not claim. The ordering FULL above pairs above control does not imply singles above control, since interactions can be negative, so the owner's "every subset positive" is a stronger claim than the ordering actually written down.

"Control" has three candidates in the workspace: the external geometry-only baseline, ALL_NEUTRAL_CONTROL, and the deterministic fixed-point fallback, which the engine calls NULL and whose iterated form is S_UNI. The shared unilateral prefix is worth roughly +442 % over geometry-only. Every arm has it. Against geometry-only, "beats control" is true for every arm by construction and says nothing about learning. Against ALL_NEUTRAL, the comparison is real but has its own problem, described below. The fixed point is the only zero that is deterministic, cheap, and cannot be degraded by a bad ranker.

The headroom arithmetic is the decisive point. The stage-4h evidence and your own figures give:

| Quantity | Value |
|---|---|
| Span from certified fixed point to exhaustive bounded joint search | about +0.51 % |
| Declared lower-bound margin per FULL minus DROP contrast | +0.5 % |
| Pilot leave-one-out gap | +15.6 % |

A learned ranker chooses among catalogue entries around the fixed point, with the fixed point as fallback. Its realised gain above the fixed point is therefore bounded by the joint-search span. If FULL sits at most about half a percent above the fixed point, and a DROP arm sits at or above the fixed point, their contrast cannot exceed about half a percent. For three contrasts to each clear the margin, each DROP arm would have to sit within a few hundredths of a percent of the fixed point. That is the claim that removing any one head erases essentially all joint value, three times over. It is not impossible, but it is indistinguishable from the DROP arm simply misranking, and the pilot gap is roughly thirty times the ceiling. The pilot arm was below the fixed point by at least fifteen percent. That is a broken ranker, not a valuable component.

One caveat on the bound. The span was measured as a matched-anchor quantity. Over a closed-loop trajectory, states bifurcate and the ceiling is not formally bounded by the one-step span. The closed-loop ceiling arm in the 14-arm inventory measures it directly and should be reported beside the learned arms.

The score decomposition explains the mechanism of degeneracy. At coalition size 100 the per-user sum and the interaction correction are of opposite sign and nearly equal magnitude, netting to a small positive. Remove the correction and the ranker sees the uncorrected sum, which grows with coalition size. DROP_C3 will therefore prefer the largest coalitions the guard allows, whose predicted value is inflated by roughly the size of the correction. The measured "C3 marginal" is then the cost of a size-biased ranker, not the value of a learned interaction term. The same fragility affects FULL: a small relative error in either term flips the ranking at that size, so FULL's ordering of large coalitions is close to noise.

Finally, a neutral-source head is not a null. The contract's stated estimand is "informative versus neutral source training for that route", and that is honest. But a head trained on a neutral source outputs whatever function it converged to, which varies by seed and is not the constant that would make the selector equivalent to a missing term. The engine-audit decision B2 defines DROP arms by term removal in the same selector and catalogue. The contract v0 defines them by neutral-source substitution. These are two different experiments. Term removal tests the architecture. Neutral substitution tests the training signal. Only the first supports "the component adds value". The two documents should agree before training starts.

## Arms that would test it, and what would make the result uninterpretable

What should be run, with each arm's reference:

- **FULL, DROP_C1, DROP_C2, DROP_C3** at the sealed seed count. Each DROP arm is the reference for its own component. Use term removal, or, if neutral substitution is kept, add the term-removal variants because the two answer different questions.
- **NULL, the certified fixed point.** Deterministic, no learner, one evaluation per world. It is the zero for every arm. Report every arm as its realised efficiency relative to NULL.
- **S_UNI.** Deterministic. Required anyway by the separate contract clause, and it is the reference for the coordination claim.
- **The bounded-search ceiling arm.** Deterministic. Its gap above NULL is the headroom the learned layer is competing for.
- **ALL_NEUTRAL_CONTROL.** Keep it only for the training-source estimand. Interpret it against NULL. If it falls below NULL it is a degenerate ranker and "pair beats control" becomes trivially true for the mirror-image reason that "beats geometry-only" is.
- **Geometry-only baseline.** One deterministic run. Redundant for the component question. It reports the prefix, nothing else.
- **Singles ONLY_Cx.** Not needed unless the paper claims a single head is deployable. If the owner insists on the literal "every subset", run them at the matched-anchor tier described below, not as full closed-loop arms.

The six sealed arms already answer the ordering FULL above pairs above control. They do not answer "singles above control", and they cannot distinguish value from degeneracy without the deterministic references. Adding those references costs no learner seeds.

Things that would make the result uninterpretable, including ones you did not list:

- **Degeneracy of the reference arm.** Handled by the screen: a DROP arm below NULL is flagged and its contrast reported as unidentified. Also report the selected-coalition size distribution and the fallback rate per arm. A C3 marginal that arrives with DROP_C3 choosing systematically larger coalitions is the bias artefact above.
- **The shared prefix.** Handled by referencing to NULL and by refusing to count the geometry-only gap as evidence about learning.
- **Deadline fallback asymmetry.** In the stage-4h smoke every coordinator arm missed the deadline and fell back to BASE, so all learned arms were identical, while S_UNI fell back on fewer anchors and the control on none. Three heads cost more compute than two. If FULL falls back more often than a DROP arm, the contrast measures the compute budget, not the component. Fallback rate must be reported per arm and either matched or declared part of the deployment claim.
- **Multiplicity.** The contract treats the claim as a conjunction, which is a valid intersection-union test with no per-contrast inflation. That is correct for the claim "all three hold". It has very low power when each effect is small, and it does not license reporting any single sub-claim on its own if the others fail. Which contrasts carry the margin rule and which need only sign must be declared now. The S3-or-S0 choice for the C3 layer is a forking path and must be fixed before outcomes are seen.
- **Physics artefact.** The ladder note argues that "a lightly loaded beam cannot be served" is a reference-frame mismatch between provisioning and mode selection, not declared physics. Two of the four Psi witnesses depend on exactly that behaviour. If the artefact is later corrected, the joint headroom and the sign of each marginal can change. The contingency ladder already records that C2's sign was regime-dependent under the old physics. Any ordering established now is an ordering under the artefact.
- **Numerator shedding.** Corrected causal ACM roughly halved availability. Pooled efficiency can rise by delivering fewer bits. The service guard is a count, not a rate. Report bits and joules separately for every contrast.
- **Seed count discrepancy.** The consultation says twelve learner seeds. The contract v0 I read says five. Whichever is sealed governs, but the note should not be read as endorsing either.

## Cheaper design and what I would refuse to conclude

The deterministic references cost nothing in seeds and remove the largest confound, so they are the first thing to add, not the last. Beyond that:

- **Matched-anchor tier.** On a common set of anchors, the prefix and the catalogue are identical across arms. Evaluate each catalogue row's realised one-step outcome once, then every arm's choice is a lookup. Nine arms cost about one. This tier has paired variance far below the closed-loop panel and answers C1 and C3 cleanly. It cannot answer C2, whose value is multi-step by construction, so C2 needs the closed-loop panel.
- **Seeds.** For a paired ordering test the seed is a nuisance replicate, and the cluster is date by seed. With hundreds of dates, most of the variance is across worlds, not seeds. Three to five seeds per learned arm lose little for the ordering. Twelve buys a seed-robustness statement, not power. Reserve the full seed count for FULL and the three DROP arms. Run any singles at the matched-anchor tier only.
- **Redundancy.** Geometry-only adds nothing to the component question. ALL_NEUTRAL is redundant with NULL if the neutral ranker is a faithful null and misleading if it is not. Keep it at reduced seeds for the training-source estimand.

Even with every ordering holding at a comfortable margin, I would refuse to conclude:

- **That any head coordinates users.** That is the S_UNI contrast with decision-relevant nonadditivity, the ladder's Level A. Orderings among learned arms say nothing about it.
- **That a gap larger than the headroom is value.** It is degeneracy of the reference arm, full stop.
- **That C3 has learned an interaction.** Its correction is a large, nearly size-proportional term. Until FULL beats a variant where C3 is replaced by a fixed per-size prior, the honest description is that the sum needs a size penalty and C3 supplies one.
- **That the learned layer is the contribution.** The prefix is worth hundreds of percent and the learned layer at most a fraction of one. The paper cannot present the heads as the source of the system's efficiency.
- **That effects transfer.** The marginals are conditional on this hand-written catalogue, this regime, and the current physics, artefact included.
- **That neutral-source contrasts are present-versus-absent contrasts.**
- **That a result with unmatched fallback rates is a component result.** It is a compute-budget result.

Where I stand on changing the requirement. Not measurable as stated: "individually" without single arms, "control" without naming which, neutral substitution presented as absence, and a per-contrast margin equal to the whole headroom. Would have designed differently: referencing to the fixed point, the matched-anchor tier, a size-prior comparator for C3, and dropping the singles. My recommendation to the owner is to restate the requirement as: each leave-one-out marginal on realised pooled efficiency has a positive paired lower bound, every learned arm sits at or above the fixed point, FULL beats S_UNI, and the materiality margin applies to FULL over the fixed point rather than to each contrast. That is a recommendation only. No constant, threshold, seed, or acceptance rule was changed.
