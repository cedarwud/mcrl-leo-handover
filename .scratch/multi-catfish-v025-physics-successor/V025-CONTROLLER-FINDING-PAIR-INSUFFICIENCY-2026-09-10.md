# Controller finding — pairwise truncation changes the decision, not just the value
Recorded 2026-09-10 from the exact-pair selection replay. `DIAGNOSTIC_NOT_CLAIM`. No model was run: the replay did arithmetic on existing exact receipts, and every one of the 11,924 family-index records joined one-to-one to a labelled row by authenticated SHA-256.

## The number that matters
On the labelled candidate pools, the pair-calibrated winner differs from the exact winner at **50 of 180 anchors (27.8 %)**, and **46 of those 50 reversals (92 %) exceed the project's +0.5 % relative margin** — so **25.6 % of all anchors** are decided wrongly by a pairwise score at a magnitude the project treats as material.

This is the first evidence that omitting third-and-higher-order interaction is a **decision-level** problem. Every earlier measurement of it was value-fitting error, which a ranker can absorb; a reversal it cannot.

## Why shortlisting does not rescue it
The obvious cheap architecture — score with pairs, re-rank the top K exactly — was measured on the 50 reversing anchors:

| K | exact optimum recovered | still above +0.5 % |
|---:|---:|---:|
| 3 | 8/50 (16 %) | 38/50 (76 %) |
| 5 | 12/50 (24 %) | 34/50 (68 %) |
| 10 | 18/50 (36 %) | 29/50 (58 %) |

Monotone but far from lossless. A pairwise score is a usable **proposal** score; its top ten is not a near-lossless exact shortlist on these pools. The pairwise winner does sit in the exact top three at 90.6 % of all anchors, but only 66 % of the reversing ones.

No result here depends on tie-breaking: there are no ties at the top under either score, none at the top-three cutoff, and none at the K = 3, 5 or 10 shortlist cutoffs.

## The bound
Writing `F = Q2 + R≥3`, and since the pair winner maximises `Q2`, the realised regret is at most the within-anchor range of `R≥3`. That was checked on all 50 reversing anchors with no violation and a smallest slack of 1.134 normalised units. The largest range is 31.017 units at world 1 anchor 80, whose pair winner ranks **ninth** under exact `F`.

## What it does not say
The pools are the labelled candidate pools, not the whole action space. This is an oracle for **exact pair calibration** specifically: a scorer that deliberately sacrifices pair-value accuracy could rank better, so this is not an upper bound on every refitted pairwise ranker. And `R≥3` on a coalition larger than three carries every order from three upward; the six size-six observations do not on their own demonstrate a sixth-order effect.

## Standing
Together with the architecture comparison — where a resource-aware and a ranker variant both beat pairwise on mean regret, 5.25 and 5.68 against 7.00 — this converts the third-order head from "a quantity we can measure" into "a quantity the decision needs". It is the strongest support the C3 route has had. It remains development evidence.
