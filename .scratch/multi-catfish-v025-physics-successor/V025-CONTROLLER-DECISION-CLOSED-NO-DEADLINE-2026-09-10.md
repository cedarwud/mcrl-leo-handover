# Controller decision — closed: the deadline framing is not available, and the unilateral baseline is stronger than we recorded
Recorded 2026-09-10 from the anytime-curve measurement, built on the standing harness with a pre-declared timing contract. `DIAGNOSTIC_NOT_CLAIM`. No learner, no training run, no policy run; nothing sealed changed.

**Decision: no.** The operational within-interval comparison cannot carry the project's claim.

## The measurement
At the 30.08-second decision interval, a competently implemented anytime unilateral search has already obtained **81.74 %** of its converged gain under the sealed rule and **87.85 %** under the corrected one. Measured against the archived endpoints those fractions are **89.39 %** and **89.60 %**. By twenty seconds it already holds 69.51 % and 77.03 %.

The argument I had been building — the exact search misses the interval, so a learned method may claim the within-interval win — therefore fails. A learned method must beat the **actual anytime incumbent** at the same wall clock, not the legal base configuration and not a convergence-certificate time.

## Two escape routes closed with it
**Certification is not the bottleneck.** I had hoped most of the sixty-five seconds was proving that no improvement remained. It is not: median finding time is **55.94 s** against a **7.43 s** certificate under the sealed rule, and 44.77 s against 4.11 s under the corrected one. Removing the certification sweep buys almost nothing.

**The baseline is better than the one we have been citing.** Simply accepting the first strict improvement instead of completing a best-improvement sweep changes the search path and the fixed point on **all twenty anchors under both rules**, and converges to a pooled efficiency **8.13 % above** the archived endpoint under the sealed rule and **1.62 % above** it under the corrected one. The "certified unilateral fixed point" the project has been comparing against was not even the best cheap thing available. Every coordination span measured against it is correspondingly overstated.

## Why the measurement is admissible
The stopwatch starts before base construction and legal-option enumeration and includes all candidate construction, physical evaluation and cache misses. A checkpoint receives only a move whose evaluation **completed** by that timestamp, so nothing is credited with hindsight. The forty-eight-boundary committed evaluation runs after timing and cannot influence the search path, and the final no-move sweep is a separate probe excluded from the anytime and joint caches. Scalar evaluation was piloted, found to take 176.84 s on the first anchor, and rejected as an implementation defect in favour of the sealed dense evaluator's native vectorised path — which is precisely the ordinary implementation improvement an external review said must be made before declaring a baseline infeasible.

## What this does and does not affect
It does **not** bear on the owner's requirement directly. That requirement is the §C3 source-training contrast, whose arms are compared with each other, not with this comparator.

It does close the §C4 positioning route, and it makes the coordination span smaller than every figure recorded today, because the comparator it is measured against improves by 8.13 % under the sealed rule once its search order is fixed.

## Standing
No claim priority was changed and no comparator was promoted; the question was whether one could be, and the answer is no. The converged comparison remains the one in the contract.
