# Controller finding — the sealed model credits nothing on three quarters of its transmissions, and the cause is one line
Recorded 2026-09-10. Two independent adjudications, one by `gpt-6-astra` at ultra effort and one by `claude-opus-5`, reached the same verdict from different starting points. The second was given a neutral prompt that did not disclose the first's interim conclusion or my own position. `DIAGNOSTIC_NOT_CLAIM`. Nothing under the sealed physics was written to; both counterfactual rules were evaluated on generated copies, and the copy was asserted bit-identical to the sealed path on bits, transmissions, mode counts and maximum radiated power before any counterfactual ran.

## The verdict
**"A lightly loaded beam cannot be served" is an artefact, not physics.**

It is a reference-frame mismatch between two lines. Power is provisioned so that the **nominal** signal-to-noise ratio equals the rate-target threshold exactly. The transmission mode is then selected from that same ratio **after** multiplying it by a sub-unity fade quantile. The de-rating is applied at selection and never compensated at provisioning, so every link is demoted down the ladder by the full fade depth — roughly 1.1 to 4.8 dB at the tenth percentile.

At occupancy one the rate target *is* the bottom rung, so the demotion falls off the bottom of the table and no mode exists at all. The measured margin the provisioning rule leaves at occupancy one is **9.1621 × 10⁻⁹ dB**.

## The panel
Eight real ephemeris steps, 48 boundaries, 100 users: **275,616 transmission instances**.

**207,607 of them — 75.32 % — produce no transmitted mode.**

| occupancy | instances | no mode | % | served |
|---:|---:|---:|---:|---:|
| **1** | 91,584 | **91,584** | **100.00** | **0** |
| 2 | 70,848 | 70,763 | 99.88 | 85 |
| 3 | 31,968 | 6,662 | 20.84 | 24,351 |
| 4 | 57,888 | 26,131 | 45.14 | 30,800 |
| 5 | 16,416 | 7,090 | 43.19 | 9,029 |
| 7 | 6,912 | 5,377 | 77.79 | 1,472 |

Every single-user beam in the panel delivers nothing. Not 99.9 % of them — all 91,584.

## Attribution
| cause | how removed | restored | % |
|---|---|---:|---:|
| per-beam power cap binding | cap raised | 25,253 | 12.16 |
| required efficiency above table maximum | — | 0 | 0.00 |
| **the de-rating applied only at selection** | remove it | **137,810** | **66.38** |
| provisioning leaving no margin | provision to threshold ÷ quantile | 80,201 | 38.63 |
| cap **and** de-rating together | both | 171,969 | 82.83 |

**The cap is not the cause at low occupancy: raising it restores 0 of 91,584 occupancy-one failures.** The maximum occupancy realised is seven, so the table-maximum cause contributes exactly zero here.

## The argument that closes it
Both halves are declared, so the honest counterargument is that their combination is the declared physics. Three things defeat that reading. The rate target is derived purely from a rate requirement with no margin term, and no sealed constant allocates a fade margin to provisioning — the 1.7 dB already folded into every threshold is a receiver implementation loss. The code's own comment calls the only headroom above the threshold "one negligible solver-scale step", explicitly a numerical device rather than a design margin. And the resulting service curve is non-monotone in a physically impossible direction: a beam with thirteen users, which the model declares infeasible, is forced to cap power, selects a high mode and **is credited**, while a beam with one user is credited nothing.

A model in which over-subscribing a beam thirteen-fold is the way to get it served is not describing radio propagation.

## What this costs
Every energy-efficiency figure, served count, prevalence census and coordination headroom the project holds was computed on a model that credits nothing on three quarters of its transmissions. They do not transfer. The consolidation mechanism that two strategic reviews recommended making the contribution is this artefact.

What survives is better than what it replaces: under corrected provisioning an interior efficiency-optimal occupancy still exists, survives removing the fixed per-chain and per-satellite costs, and moves with off-axis angle and slant range — so the geometry dependence the owner requires does not depend on the defect. That analysis is itself under adversarial review.

## Standing
This is a physics defect, so its correction is a versioned successor and an owner decision, not mine. No constant has been changed and no run is authorised. The obligation this creates is to recompute, not to re-argue.
