# Round 14: is my experiment able to detect the effect at all, even if everything works?

## The worry
I have spent weeks debugging why a three-component system shows no effect. Today I found several real implementation defects. But it has occurred to me that I may also have an experiment that cannot detect the effect even when the effect is real, and no amount of debugging fixes that.

I would like this checked before I spend days of compute on the repaired system.

## The design
Three components, C1, C2 and C3, are evaluated by ablation. Four arms: FULL with all three enabled, and DROP_C1, DROP_C2, DROP_C3 each with one disabled. There is also an all-neutral control.

The primary outcome is **pooled energy efficiency**, computed as the ratio of summed bits to summed joules over the whole evaluation, not as a mean of per-episode ratios.

**The success claim is an intersection**: each of the three contrasts, FULL minus DROP_Cx, must exceed a prespecified margin of **+0.5 % relative** with its 95 % lower confidence bound above that margin, and FULL must additionally be quality-of-service non-inferior to each DROP arm.

Uncertainty is a two-way pigeonhole bootstrap with clusters formed by satellite-ephemeris date crossed with training seed, recomputing the pooled ratio on each resample.

Sixteen training seeds. A handful of evaluation worlds. Roughly ninety decision anchors per world.

## What I measured about the design itself
* Bootstrap coverage measured at **0.86 to 0.92** against a nominal 0.95.
* Conjunction power, meaning the probability that all three contrasts clear their margin simultaneously when all three effects are real, estimated at **0.38 at 5 seeds, 0.50 at 12, 0.68 at 16, and 0.68 at 24**, assuming a 5 % standard deviation across dates.

So at my planned sixteen seeds I appear to have roughly a **one in three chance of missing a real effect**, and my intervals are narrower than they claim to be.

## The questions

1. **Is the conjunction structure the main problem?** Requiring three separate contrasts to clear simultaneously multiplies the failure probability. Is there a standard alternative that preserves the scientific meaning of "each component contributes" without paying this cost? I am aware of intersection-union testing and that it is conservative by construction; what do people actually do when a claim genuinely is a conjunction?

2. **Why does power plateau at 0.68 from sixteen to twenty-four seeds?** Adding seeds stops helping. That suggests the variance is dominated by something other than seeds, presumably the dates. If so, what does the design need instead of more seeds, and how would I confirm that diagnosis from the data I already have?

3. **The undercoverage.** Measured coverage of 0.86 to 0.92 against nominal 0.95 means my confidence intervals are too narrow, so a lower bound clearing the margin means less than it appears to. What causes this in a two-way clustered bootstrap on a **ratio of sums**, and what is the standard remedy? Is a ratio estimator the culprit, or the clustering, or the number of clusters?

4. **Is pooled ratio the right estimand?** A ratio of sums weights heavily toward the largest denominators. If a few dates or anchors dominate the joules, the pooled ratio may be an average over almost nothing. What diagnostics distinguish this, and when is a pooled ratio preferable to a paired per-block log contrast?

5. **A bias I recently identified.** When the decision-making component fails to finish inside its real-time budget, the system falls back to a default and that arm's decision is not exercised. The realised gain is `G = (1 - M) * Delta` where `M` indicates fallback. Since difficult decisions are plausibly also the high-gain ones, fallbacks may remove exactly the cases where the effect lives, biasing the comparison toward the null. How should an experiment be designed or analysed so that this does not silently destroy it? Is there an established treatment of this, for example as non-compliance or as a censoring problem?

6. **The question I most need answered.** Given all of the above, what is the smallest change to my design that would give adequate power, and what would "adequate" be for a claim of this shape? If the honest answer is that the design needs more evaluation worlds or dates rather than more seeds, or a different claim structure entirely, please say so directly. I would rather redesign now than run for days and get an uninterpretable null.

## What I will do with the answer
Decide whether to run the confirmatory experiment as designed, or to change the design first. Please distinguish established statistical results from your judgement, and say clearly where my numbers are too sparse to support a recommendation.
