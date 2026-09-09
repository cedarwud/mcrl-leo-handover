# Controller adjudication — the interior optimum exists; almost everything I said about it does not
Recorded 2026-09-10 from an adversarial review at ultra effort, commissioned specifically to break a result I had already described to the owner as the day's best news. It did. `DIAGNOSTIC_NOT_CLAIM`. No production constant, threshold, sign, seed, horizon, price, guard or acceptance rule was changed; all counterfactuals are separate diagnostic calculations. The original generator reproduces its report byte for byte, and the independently recomputed gain, noise and quantile all match.

**Two things I told the owner need correcting.**

## Correction 1 — geometry is a feasibility signal, not an efficiency signal
I reported that the efficiency-optimal partition moves with off-axis angle, and offered that as satisfying the owner's requirement that angle genuinely influence power and efficiency.

With the fixed per-chain and per-satellite costs removed, there are **zero** angle switches and **zero** range switches out of 144 each. The reason is algebraic: at fixed elevation, geometry multiplies every amplifier cost by one common positive scalar, which preserves every feasible partition's ranking exactly.

Of the eight switches that do occur under the sealed rule, seven are cases where the previous winner became **infeasible** — an eight-user beam demanding 1.7986 W against a 1.65 W cap, 9.0 % over — not cases where a different partition became more efficient. Removing the cap eliminates five of them. Exactly **one** switch compares two feasible alternatives, worth 0.831 %. Under the contracted-rate numerator only one feasible-to-feasible angle switch survives per rule, worth about 0.075 %.

The single-beam optimum is occupancy seven at **all nine** geometry cells.

So angle and range do matter, but as a **cap-feasibility warning**, not as an occupancy-control signal. Freezing the reference partition across the whole grid costs at most 0.94 % under the sealed rule. That is the honest version, and it is much weaker than what I said.

## Correction 2 — the mechanism is not identified
I reported that removing the fixed costs and still finding an interior optimum shows the discrete mode ladder and amplifier law are what create it.

A smooth diagnostic model with **no mode table at all** — required ratio `max(floor, margin × (2^{0.3n} − 1))`, sealed rate, bandwidth, margin, noise, gain, cap and square-root amplifier retained — produces an interior optimum at continuous occupancy **7.6637**, from `n / sqrt(2^{0.3n} − 1)` whose stationary condition is `x = 2(1 − e^{−x})`. So the interior optimum does not require the ladder. The zero-fixed-cost test shows only that fixed costs are unnecessary; it does not identify discrete modes as the cause.

Worse, the agreement between the two provisioning rules under that test is **algebraically forced**, not independent corroboration: the margin rule multiplies every demand by one over the quantile and therefore every amplifier cost by one over its square root, so identical rankings on the common feasible set are guaranteed.

And "convexity" is the wrong word: the production occupancy-cost second differences are +0.1770, −0.0415 and −0.3000 W. The sequence is not discretely convex.

## What did survive
The **existence** of an interior occupancy optimum survived every attack, under every formulation tested. That is the weaker statement and it is the one we may make.

## What else the attacks turned up
**Interference favours fewer beams, not more.** This is the opposite of what the literature's spreading argument predicts, and the review failed to produce the reversal toward singleton spreading it was asked to look for — because equal-airtime multiplexing already removes simultaneous within-beam interference, so extra co-channel beams only add interference. But the specific four-beam partition is extremely fragile: the production antenna's coupling at 5.75° separation, −35.50 dB, is **already** enough to defeat it, and its advantage over the three-beam alternative was only 0.0139 %. With real hexagonal cell centres and a repeated-colour pair at 2.666° separation, efficiency falls **21.56 %**.

**The numerator credits capacity nobody asked for.** Crediting the contracted rate instead of delivered capacity moves the optimum, because the surplus is rung-dependent — occupancy three receives 10.03 % more than its contract, occupancy seven 4.65 %, occupancy eight 3.01 %.

**The feasibility filter's stated reason is wrong.** "Excluded because all users must be served" silently substituted contract attainment for production service. Capped-but-degraded beams are valid production outcomes: at occupancy twelve every user is service-complete while **none** attains the rate target. The optimum survives restoring them.

**Under a common fading distribution the two rules are not comparable as published.** Integrating both provisioners' unchanged powers over the production fading distribution, per-user target attainment is **43.2 % under the sealed rule against 89.9 % under the margin rule**. That is a service-reliability argument for the correction that is independent of any efficiency figure — and it is the strongest argument for it I have seen.

**A caution about the corrected rule.** With real cell geometry and interference, every margin-rule assignment failed all-user target attainment; its best attained 17 of 24.

## Standing
The claim we may carry forward is: an interior efficiency-optimal beam occupancy exists in this model, its cause is not identified as the mode ladder, its specific value is fragile to interference and to the choice of numerator, and geometry acts on it through feasibility rather than through efficiency.
