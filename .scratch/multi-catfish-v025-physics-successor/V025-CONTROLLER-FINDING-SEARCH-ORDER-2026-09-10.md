# Controller finding — every coordination number today is paired against the wrong baseline
Recorded 2026-09-10, derived by placing two of today's reports side by side rather than by any new run. `DIAGNOSTIC_NOT_CLAIM`. Nothing sealed changed; a corrected measurement is running.

## What the arithmetic says
The anytime measurement reports that accepting the **first** strict improvement, rather than completing a best-improvement sweep, changes the search path and the fixed point on **all twenty anchors under both provisioning rules**, and converges **8.13 % above** the archived endpoint under the sealed rule and **1.62 % above** it under the corrected one.

Applying those to the archived pooled figures:

| sealed rule | pooled efficiency, Mbit/J |
|---|---:|
| archived unilateral, best-improvement | 28.4709 |
| **archived bounded joint selector** | **30.2814** |
| **first-improvement unilateral** | **≈ 30.79** |

The sixty-second row of the anytime curve gives the same answer independently: 29.5396 is 95.39 % of the first-improvement prize, which puts convergence at about 30.787.

Under the corrected rule the first-improvement endpoint lands near 43.71 against the archived joint selector's 43.24.

**Under both rules, changing nothing but the order in which the local search accepts improvements produces a unilateral endpoint that exceeds the bounded joint selector it was supposed to be beaten by.**

## What this does and does not license
It does **not** license "coordination is worthless". The joint selector was **seeded from the best-improvement fixed point**. Re-seeding it from the better endpoint should improve it too, and it may still win.

What it licenses is narrower and worse: **the comparison as run is mispaired.** Every coordination figure the project holds — the archived +6.359 %, the corrected +0.51 %, the five-point beam-width curve, the thirty-date interval and its confidence bounds — measures a joint selector seeded from one local optimum against that same local optimum, when a different traversal order of the same neighbourhood reaches a better one. **The real span is unknown.**

This is also the concrete form of a caution the provisioning adjudication gave and I did not fully absorb: the unilateral certificate establishes local optimality **in the specified neighbourhood**, and the joint result establishes a maximum **over its bounded candidate family**. Neither is a global optimum, and neither is invariant to the traversal order. We have been treating one particular local optimum as though the word "certified" made it canonical.

## What is running
A four-arm re-measurement on the same twenty anchors under both rules: the two unilateral endpoints, the joint selector seeded from each, and both cross pairings so that the seed effect and the search-order effect can be separated. Its first line must state the correctly paired span, and it is instructed to lead with the fact if that span is near zero or negative.

## Standing
No result is withdrawn yet, because the corrected pairing has not been measured. But no coordination figure recorded today should be carried forward until it has been.
