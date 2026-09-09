# Controller finding — the reformulation wins, and four of the reasons I gave for it are wrong
Recorded 2026-09-10 from the parametrisation comparison, whose arms, metrics, estimator family, grid, split and seed were all declared before any fitting. `DIAGNOSTIC_NOT_CLAIM`. No production training run, no policy run; no sealed contract, target, scorer, schema digest, manifest, acceptance test or price was modified.

## The measured result
Predicting the joint objective change **directly** beats the sealed additive-plus-interaction parametrisation on held-out mean selection regret: **2.4269 against 3.6180, a 32.92 % reduction**, with p95 falling from 19.825 to 10.477.

But it makes **more** mistakes, not fewer: its choice differs from the exact winner at **30.00 %** of held-out anchors against the additive form's **23.33 %**. **The win is in the severity of errors, not their frequency.**

## Four things I told the owner that this refutes
**The conditioning objection is far weaker in practice than in theory.** Measured on held-out rows, the additive-part and interaction-part errors have Pearson correlation **−0.788**, with opposite signs on 68 % of rows. Their combined error RMSE is **0.491 times** the root-sum-square of the parts, and the realised relative error of the sum is **0.887 times** that of the additive part alone. The realised amplification is therefore **below one**, not the twelvefold I first claimed nor the twenty-threefold the external round corrected me to. Both figures were worst-case bounds under an independence assumption the fits do not satisfy.

**"Which half is to blame" is not a well-formed question.** Supplying exact per-user terms and learning only the interaction gives mean regret **9.043**; supplying the exact interaction and learning only the per-user terms gives **9.647**. Both are far **worse** than learning both, at 3.618, because making either half exact destroys the cancellation the other was fitted alongside.

**Selecting the all-user coalition is not a bias.** The exact winner is the size-100 coalition at **26 of 30** held-out anchors. The oracle picks it too. Earlier I read the selector's preference for large coalitions as a scale artefact of the growing additive term; on these pools the large coalition is simply usually best.

**The extrapolation problem was solved by data, not by reformulation.** Exact labels at size 100 were generated and included — 180 training, 60 validation, 60 test rows — and out-of-support selections then fall to **0.00 % for both arms**. That is precisely the third of the three routes the external round identified, and neither parametrisation deserves credit for it. Sizes 7 to 99 remain absent, so the size curve is observed at 2–6 and 100, not continuously.

## What remains as the case for opening the contract
One measured advantage: a third off the mean regret and nearly half off the p95, on a pre-declared decision metric with matched features, estimator, grid, split and seed, against exact labels verified to zero residual against their fraction receipts.

The report's own wording is the right standing: this supports **keeping the reformulation open for a sealed-contract decision; it does not authorise that change.**

## A methodological note worth keeping
The initially assigned test anchors had been opened by a loader smoke test before fitting. Rather than assert they were untouched, the run **quarantined them and drew a fresh test set from previously unopened blocks**, loading it only after hyperparameters were selected and recorded. That is the behaviour the project should expect by default.

## One incidental finding
The 163 resource-context coordinates that the interaction head sees and the per-user head does not make interaction RMSE slightly **worse** — by 0.177 — while improving the additive arm's mean selection regret by **1.067**. Decision-relevant ranking information need not improve pointwise calibration, which is a caution against judging any head by its explained variance.
