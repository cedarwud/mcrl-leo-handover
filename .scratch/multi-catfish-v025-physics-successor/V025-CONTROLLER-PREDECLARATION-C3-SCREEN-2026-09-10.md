# Pre-declaration — the §C3 screening run, fixed before the harness finished and before any contrast existed
Recorded 2026-09-10. The protocol below was written into the dispatch prompt before the run and is recorded here so it survives independently of the server. `DIAGNOSTIC_NOT_CLAIM`, and additionally **`SCREEN_NOT_CONFIRMATORY`**: no result from this run may be reported as the answer to the owner's requirement.

## What is being run, and why it matters
Contract §C3 — the source-training contrast — **for the first time**. For each of three learned routes, that route's training source is replaced by a neutral one while **all heads are retained, updated and deployed**. Neutral never means removing a head.

## The arms: the complete factorial, plus one external reference
Eight learned arms, being all eight cells of {informative, neutral} over three routes:

| arm | first | second | third |
|---|:-:|:-:|:-:|
| full | I | I | I |
| leave-one-out ×3 | N/I/I | I/N/I | I/I/N |
| single-informative ×3 | I/N/N | N/I/N | N/N/I |
| all-neutral control | N | N | N |

Plus the external geometry-only baseline, which has no learner at all. The sealed panel contains five of these eight cells; the three single-informative arms are the addition the owner's requirement needs, and without them the leave-one-in half of that requirement cannot be evaluated at all.

## Fixed before the run
- **Both provisioning rules.** A result under the sealed rule alone would be measured on a model crediting nothing on three quarters of its transmissions; under the corrected rule alone it would prejudge a decision the owner has not taken.
- **Sealed learning rates and architectures, untouched**: first route 1.0e-2 with one hidden layer of eight and ReLU; second 1.0e-3 with 100-50-50 and tanh; third 1.0e-3 with 64-64 and ReLU; Adam at the sealed betas and epsilon; one deterministic full-batch update per route per source epoch. **If a route fails to train, that is the finding.**
- **Two learner seeds**, reported seedwise, supporting no distributional claim.
- **Nine thousand source epochs. Checkpoints every 100. Full panel evaluation at exactly 500, 1000, 2000, 4000 and 9000. The contrast is reported at 9000**; the four earlier evaluations are trajectory and none may be reported as the outcome.

The separation matters: training an epoch and saving a checkpoint are nearly free, while evaluating the panel across arms, anchors and forty-eight boundaries is the expensive operation. **The budget therefore controls evaluation count, not epoch count** — which is why the horizon is nine thousand rather than the two thousand I first proposed. The owner made that point and it was correct.

- **A cost-driven early stop is legitimate** at whichever declared evaluation point was reached, with the measured figures that forced it. A stop chosen because a point looked favourable is not, and the distinction must be visible.

## Convergence rule, declared now
- validation objective still falling at the end → **under-trained**; the remedy is more epochs, **not** a different learning rate;
- oscillating without settling → **that route's rate is too high**;
- flat early and high → rate too low, or capacity or features are the limit, needing diagnosis rather than a rate change.

This exists so that the learning rates are not adjusted on the basis of the contrast they produce.

## Why a declared reporting point at all
A previous pilot moved from −2.4 % at 200 epochs, through −1.6 % at 1000, to +15.6 % at 2000. Choosing among those after the fact would bias everything downstream. Looking early is fine and is the point of the trajectory; **choosing afterwards is not**.

## The primary deliverable is not the contrast
It is the **training curves per route per arm**. Whether the routes converge, oscillate or are still climbing determines whether anything about the budget or the rates needs attention before a confirmatory run. A contrast from a route that never converged is not informative about that route.

## Reading rule
The degeneracy screen pre-declared earlier applies unchanged: below-reference by exact sign against the head-independent certified fixed point, with every contrast reported both over all anchors and over the subset where every arm in that contrast is at or above reference.

## Audit
Two independent pre-run audits of the harness were dispatched in parallel with the screen rather than before it, so that the audits read the code while the screen exercises it. If either reports a blocking defect the screen is stopped and re-run. The machine was idle, so the expected cost of parallelism is lower than the cost of serialising a thirty-minute audit in front of a multi-hour run.
