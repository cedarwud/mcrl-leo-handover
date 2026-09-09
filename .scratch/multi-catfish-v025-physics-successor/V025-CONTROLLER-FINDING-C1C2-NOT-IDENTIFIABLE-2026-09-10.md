# Controller finding — the C1 and C2 heads cannot see what their own targets are made of
Recorded 2026-09-10 from the C1/C2 feature-sufficiency diagnostic. `DIAGNOSTIC_NOT_CLAIM`. No production learner was trained; the only fitted estimator was a diagnostic nearest-neighbour regressor.

The owner asked directly whether all this work on the third head means the first two are fine. They are not. This is the answer to that question.

## Both heads admit collisions
Each head is a scalar readout over one numeric sequence — 16 values for the first, 22 for the second — and nothing else: no action identity, no association map, no geometry, no cross-gain matrix, no coupled-power result, no network outcome.

**First head.** Two admissible network states encode **byte-identically** while their exact targets are `11/10` and `−33/10`. The gap is `22/5`, so any deterministic predictor on that row takes squared loss at least `4.84` on one of the pair. The two states differ only in background association topology, focal cross gains, background coupled powers, and the resulting whole-network outcome — all of it discarded by the encoder. This is a contract-level witness. A separate exhaustive scan of all 176,223 existing corpus rows found **no** naturally occurring collision for this head: all 5,230 duplicate groups were other carrier views of the same physical step. So for this head the impossibility is proved, but its empirical frequency is unmeasured.

**Second head.** The witness is **real**, not constructed: production tape world 1, step 0, user 6, action (65028, 44), two anchors differing only in carrier rule. Byte-identical inputs, exact targets `5.4095` and `19.3467`, gap `13.937`, squared-loss floor `48.56`. Among just those two anchors there are **62** exact collision groups.

And the reason is worse than a missing feature. The exact projection has the offset-1 forecast **not surviving** in one state and surviving in the other, but the stored 22-scalar row reports valid and surviving at all three offsets in **both**. The encoded row misreports a quantity the pipeline already computed. A follow-up is running to classify this as an encoder bug rather than a sufficiency gap; if it is a bug it is cheap to fix and the second head's identifiability may largely return.

## Held-out predictability
Thirty anchors, 26,345 valid rows, split by whole physical step so byte-identical carrier views cannot leak across partitions — train on steps 1, 2, 4, 6, 7, 8, 9, validate on 5, test on 0 and 3 (5,280 held-out rows).

| Head | held-out explained variance | RMSE |
|---|---:|---:|
| First | **−0.336** | 3.468 |
| Second | **0.211** | 3.386 |

A negative explained variance means the predictor does **worse than predicting the mean**. On these anchors the first head has no demonstrated predictive value at all.

## The trap in the comparator
The same diagnostic reports explained variance of exactly `1.0` given the "discarded structure", with fitted coefficients `[+1,−1,+1,−1,+1,−1]` and `[+1,+1,+1,−1]`. That is **tautological and must not be read as a repair target**: those regressors are the whole-network candidate and default bits, energy and potential, which are literally the terms the target is defined from — and they are the *output* of the expensive coupled evaluation the head exists to avoid. Feeding them to the encoder would be leakage and would leave nothing to learn.

The admissible question, now dispatched, is whether features computable from the **pre-decision** state alone — background topology, cross-gain magnitudes, background coupled powers — separate the colliding states, and how much of that ceiling they actually recover.

## A second, independent defect confirmed
The diagnostic also closed the missing acceptance test. With the pilot's primitive-source fallback on, production labels disagree with the exact evaluator (`0.16304` against `0.12757` for the first head; `0.15939` against `−3` for the second). Turning only that flag off makes all four checks pass; turning it back on makes them fail again. The test is left red on the defective path by design.

## Standing
No sealed value changed. No threshold, sign, seed, horizon, price, service guard or acceptance rule was touched. The consequence for planning is that a three-head training run on the current encoders would not be a fair test of the first two heads, and a null result from it would be uninterpretable.
