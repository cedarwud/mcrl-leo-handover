# Controller finding — the deadline argument has a hole I did not see, and my conditioning number was wrong
Recorded 2026-09-10 from two external deep-research rounds. `DIAGNOSTIC_NOT_CLAIM`. No code, no run.

## The load-bearing correction: the seed cannot be free
The learned joint search is **seeded from the converged unilateral fixed point**. Replacing only the scoring of joint candidates therefore does not remove the upstream cost. The learned system pays the same 65 seconds the exact method does.

I had been arguing that the exact search is too slow for the 30.08-second interval and that learning is what makes coordination affordable. That argument does not stand as stated. Three options remain and one of them must be established: accelerate the seeding stage, replace it, or establish a legitimate advance-computation protocol.

The review adds a second thing I had never measured: **time to convergence is not time to a useful decision.** A search that takes 65 seconds to *certify* convergence may have obtained almost all of its improvement far earlier. Our own profiling already hints at it from the other side — for the joint search, the median time to find the eventual winner is about one second while certifying it adds a median of nine and a p95 of forty-one.

A measurement was dispatched in response: the anytime quality curve of the unilateral search on the standing harness, reporting the true objective of the action it would actually commit if interrupted at each of eight wall-clock points, the fraction of the converged prize available at the deadline, the certification cost separated from the improvement cost, and what the joint search achieves when seeded from the incumbent available at ten, twenty and thirty seconds with its own time counted inside the same budget.

Two further conditions the review sets on any deadline comparison, which I accept as constraints:
- **Symmetric certification.** If the learned method need not certify local optimality, the classical comparator must not be required to finish a complete-neighbourhood certificate before its incumbent counts. Both must satisfy the same output contract: a valid action committed by the deadline.
- **Advance scheduling does not create capacity.** If each epoch creates 65 seconds of serial work and epochs arrive every 30.08 seconds, starting earlier does not let one worker keep up. "Takes longer than one period" is a much weaker statement than "no causally valid implementation can decide within the schedule", and our timings establish neither.

## Corrections to what I told the owner about the conditioning
- The condition number of the split is **(|S| + |Ψ|) / |f| = (480.113 + 440.079) / 40.034 ≈ 23**, not 12. My figure was the sensitivity to a relative perturbation in the additive component **alone**. With adversarial relative errors in both components, one per cent in each produces about twenty-three per cent in the total.
- **Absolute errors add**; they are not multiplied. The amplification is of *relative* error measured against the much smaller answer.
- A factor of twenty-three does not explain an observed error near fifty from arithmetic. That error is the learned heads' approximation error **exposed** by cancellation, not a precision problem, and higher precision would not touch it.
- **There is no general theorem that an additive-plus-interaction representation is statistically inferior to direct prediction.** I stated the reformulation as the fix; it is a well-motivated experiment. The established names are cancellation, loss of significance and ill-conditioned summation; the nearest decomposition-specific theory is the equivalence of anchored and ANOVA decompositions and whether its constants deteriorate with dimension.

## A comparator our running experiment does not have
The stronger comparison is **not** "decomposition versus no structure" but "mandatory anchored output decomposition versus direct output with the structure retained in the inputs". Concretely: predict the joint change from a set representation, the context, the size, **and the additive estimate as an input feature**, so the model may rescale or ignore it rather than being forced to add it with coefficient exactly one. The methodological relatives are stacking and multi-fidelity modelling, both of which learn the relationship rather than assuming a unit coefficient.

The comparison now running declared two arms in advance. I am not adding a third mid-run; it will be a separate pre-declared follow-up.

## What neither reformulation fixes
Both rounds independently say the same thing: **neither change resolves the extrapolation** from a corpus concentrated at sizes two and three to a selector that routinely chooses size one hundred. Representation results for permutation-invariant set models are not extrapolation guarantees, and recovery guarantees for structured set functions require chosen queries, not a passive corpus concentrated on small sets.

That is the blocker, and it is not a conditioning problem.

## A receipt discrepancy, resolved
My directly computed pooled figures came from an intermediate result file written at 17:29; the adjudication's table comes from a stricter audit written at 17:55. Where they differ, **the audited report is authoritative**. The conclusion is unchanged either way: the coordination gap falls from about six per cent to about half a per cent under corrected provisioning.
