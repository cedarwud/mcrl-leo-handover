# Controller finding — the confirmatory design rests on one ephemeris date, and that is the real bottleneck
Recorded 2026-09-09. Verified by reading the acceptance and merge code and the evaluation artefacts. `DIAGNOSTIC_NOT_CLAIM`.

## The three answers that matter
**Coverage is marginal, not simultaneous.** The calibration counts each of the three contrast intervals separately with denominator `3 * repetitions`. So `0.95^3 = 0.857` is **not** the benchmark and the measured **0.863 to 0.920 is genuine average marginal undercoverage** against 0.95. I doubted this at midday after an outside review raised the simultaneous-coverage possibility; the code settles it against me. My original reading was right.

A second, sharper point: the "95 % lower bound" is implemented as the **lower endpoint of an equal-tailed two-sided 95 % interval**, a 2.5 % lower-tail allowance, not a one-sided 95 % bound with a 5 % tail. The sealed wording does not distinguish these and they differ in both calibration and power.

**The 5 % date standard deviation is on the paired log contrast**, not on raw efficiency. The simulation adds the date effect directly to `log(1 + true gain)`, so it cannot cancel through pairing. That is the unfavourable of the two readings.

**We have one independent date.** `2025-11-16`, one world, `V025_PROBE/world/3`. The production cluster identity is `(world start date, training seed)`. Anchors, learner seeds, catalogue anchors and repeated checkpoint evaluations create **no** additional date blocks.

## Why this outranks the power question
Date is the dominant variance term and `D = 1`. At fixed `D`, adding seeds drives the contrast variance to `Sigma_date / D` and no further, so **more seeds cannot help**. I spent part of today weighing 16 against 24 seeds; on this evidence that choice is close to irrelevant.

Worse, a two-way bootstrap over dates crossed with seeds has **nothing to resample on the date axis** when there is one date. Whatever interval width it reports on that axis is not estimated from data.

And the assumed 0.05 has never been measured: with one date the sample standard deviation of the paired contrast across dates is undefined. The only two-point comparison available is the same date at different checkpoints, `+0.376` at epoch 200 against `-0.291` at epoch 2000, which measures checkpoint sensitivity and says nothing about date variance.

Round 14's illustrative arithmetic, under its stated assumptions, put a true 2 % contribution at roughly **137 independent dates** and a 3 % contribution at roughly **50**. Against `D = 1` the gap is not a tuning problem.

## What this does and does not threaten
It does **not** touch today's mechanism results. The interaction witness, the prevalence census at 30 of 30 anchors, and the perfect-knowledge ceiling of **+6.36 % over the certified unilateral optimum with the served count increased** are exact evaluations of a deterministic objective. They carry no bootstrap and no date clustering.

It threatens the **confirmatory claim**: the sealed intersection of three contrasts each clearing +0.5 % relative with a lower bound above it, plus three quality-of-service conditions. On one date that claim cannot be established at any seed count.

## The work this implies, and its character
Generating more independent ephemeris dates is **world generation**, not training. It is independent of every learner defect found today and can proceed in parallel with all of them. It is also the item with the longest lead time, which is an argument for starting it early rather than after the learner is repaired.

I am not proposing a date count here. Round 14 was explicit that a count needs the effect sizes, the quality-of-service margins, the joint covariance and a calibrated interval, and this audit shows the variance input itself has never been measured. The honest first step is to generate enough dates to **measure** the paired-contrast standard deviation, then size the design from a measured value rather than an assumed one.

## Standing
No threshold, sign, seed, horizon, price, service guard, acceptance rule or claim condition changes. No run is authorised. The date count is a design parameter of a confirmatory experiment that has not started, and any change to it is the owner's decision.
