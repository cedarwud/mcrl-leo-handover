# Controller finding — the corrected span is more than double what I reported, and the third route is not a size penalty
Recorded 2026-09-10 from two pre-declared measurements that landed within a minute of each other. Both reuse frozen splits, seeds, estimator families and tie-breaks from earlier work; neither tuned any scorer. `DIAGNOSTIC_NOT_CLAIM`. No learner deployed, no training run, no policy run, nothing sealed modified.

## The coordination span, correctly paired
Every span recorded today compared a joint selector seeded from one local optimum against that same optimum, when a different traversal order of the same neighbourhood reaches a better one. Re-measured with **both arms on the better search**:

| rule | mispaired | **correctly paired** | negative anchors |
|---|---:|---:|---:|
| sealed | +6.3590 % | **+4.6046 %** | 1 of 20 |
| **corrected** | **+0.5448 %** | **+1.2913 %** | 6 of 20 |

**Under the corrected physics the span is more than double what I have been reporting all day.** The mispairing overstated the sealed figure by 1.75 points and **understated** the corrected one by 0.75 points — opposite directions, which is why no ratio may be used to extrapolate the other figures.

My inference that the better unilateral endpoint would overtake the archived joint selector was correct — 30.7869 against 30.2814 under the sealed rule. But the joint selector re-seeded from that better endpoint overtakes it again, at **32.2045**. **Coordination is real, not an artefact of traversal order.**

The two sign counts answer different questions and must not be merged: on the selection-time objective the joint selector strictly improves on its seed at **20 of 20** anchors under both rules; on the forty-eight-boundary committed efficiency it is positive at 19 of 20 under the sealed rule and 14 of 20 under the corrected one.

One detail worth keeping: under the corrected rule the better unilateral endpoint delivers **fewer** bits than the archived one, 3.169 against 3.202 Tbit, while spending far less energy, 72,516 against 74,453 J. First-improvement trades bits for energy there.

## The third route is not a size penalty
A design reviewer's specific objection was that the interaction route's correction is a large, nearly size-proportional term, and that until the system beats a fixed per-size prior the honest description is that the sum needs a size penalty and this route supplies one. Tested:

| scorer | held-out mean selection regret |
|---|---:|
| **learned interaction head** | **3.618** |
| size-only prior | 13.114 |
| zero interaction | 13.683 |

The learned head's advantage over the size prior is **9.496**; the size prior's advantage over zero is **0.569**. **Knowing the coalition size is worth almost nothing; nearly all of the learned head's value is set-specific.**

The fitted prior is instructive rather than weak: it does capture the large negative at size one hundred, at −12.402 against small positives at sizes two to four, and it still lands at 13.114. Reproducing the size effect is not the same as ranking.

## What this changes and what it does not
It raises my estimate for the third route materially — its one named threat is now tested and failed — and it more than doubles the budget the three routes have to share under corrected physics.

It does **not** measure the owner's requirement. Both results are offline measurements on labelled candidate pools with exact labels, not closed-loop policy runs, and the source-training contrast over the three routes has still never been run at scale.

## An immediate consequence for a result I reported tonight
The five-point beam-width curve was computed with the same mispairing. I told the owner that coordination is **negative** at the width we currently model, at −0.303 %. On the twenty-anchor panel that same mispairing understated the corrected span by a factor of 2.4. That curve must be recomputed with correct pairing before the "this design point is dead" conclusion stands. I am not extrapolating the factor; it must be measured.
