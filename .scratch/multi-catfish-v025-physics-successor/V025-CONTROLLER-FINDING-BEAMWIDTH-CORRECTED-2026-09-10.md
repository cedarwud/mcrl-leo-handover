# Controller finding — under corrected physics the beam-width story inverts at the point we actually model
Recorded 2026-09-10 from the beam-width sweep re-run under the corrected provisioning rule, on the same eight anchors, worlds, seeds, baseline, unilateral procedure, catalogue rules and commit separation as the original. `DIAGNOSTIC_NOT_CLAIM`. No sealed constant changed; every point is a diagnostic evaluation on a copy.

## The curve does not survive
| one-sided | full span | defective rule | **corrected rule** | corrected anchors negative |
|---:|---:|---:|---:|---:|
| **1.66°** (what we model) | 3.32° | +6.502 % | **−0.303 %** | **5 of 8** |
| 2.40° | 4.80° | +10.397 % | +1.209 % | 0 of 8 |
| **3.32°** (the source's own value) | 6.64° | +11.563 % | **+0.985 %** | 2 of 8 |
| 4.50° | 9.00° | +14.639 % | +3.205 % | 2 of 8 |
| 6.65° | 13.30° | +41.949 % | +7.315 % | 3 of 8 |

Three things follow.

**At the width we currently model, coordination is negative.** Not merely small — the bounded joint selector is *worse* than the certified unilateral fixed point on five of eight anchors. There is nothing at this design point for three components to divide.

**The monotone rise does not survive.** The corrected curve dips at the source's own value relative to 2.40°, so the clean "wider beam, more coordination value" statement is gone. What survives is that the two widest points remain materially positive.

**The gap does not vanish.** At 4.50° it is +3.205 % and at 6.65° it is +7.315 %.

## The one defensible move, and its price
Correcting the beam-width convention from the 1.66° one-sided edge we model to the 3.32° the cited source's own equation and table specify moves the corrected gap from **−0.303 % to +0.985 %** — from negative to positive. That is a **provenance correction, not a design choice made to flatter the result**, which is the strongest position available on this axis.

But +0.985 % is only twice the project's materiality threshold, with two of eight anchors negative. And it is paid for in service: users attaining the per-user rate target fall from **550 to 443** for the unilateral arm across that change, and from 541 to 434 for the joint arm. By 4.50° attainment has almost halved, to 338 and 337.

Reaching the comfortable +3.205 % requires 4.50°, which is 1.35 times the source's value and 2.7 times ours, and **no provenance supports it**. A reviewer will ask whether the antenna was chosen to suit the method.

## Two things worth registering separately
The joint selector attains **fewer** rate targets than the unilateral arm at the two narrowest widths — 541 against 550, and 434 against 443. It buys energy efficiency while leaving more users below target. Under a pooled metric that is invisible.

And for the third time, at panel scale: under the defective rule **none of 12,000 selector-by-user-step results attains the rate target**, at any width, for any arm. Under the corrected rule attainment is non-zero at every width for every arm.

## Standing
This closes the current design point and leaves one defensible but narrow move. It does not close the project, because a second and independent axis — offered load per beam and the per-user rate target — is still being measured, and a result there would not carry the "you chose a favourable antenna" objection.
