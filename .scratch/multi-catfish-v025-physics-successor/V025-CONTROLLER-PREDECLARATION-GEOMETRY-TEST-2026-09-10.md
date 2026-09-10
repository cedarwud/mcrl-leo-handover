# Pre-declaration — the geometry-feature test for the first route, with my expectation stated before it runs
Recorded 2026-09-10, **before dispatching** and before any result exists. `DIAGNOSTIC_NOT_CLAIM`. Nothing here authorises a change to the sealed feature schema; it declares a diagnostic and the prediction it will be judged against.

## What will be tested
Two candidate features for the per-user route, both **action-local** and both computable from the decision-time tape without any coupled solve:

- the **off-axis angle** of the focal user under the candidate beam, replacing the hard-coded zero that both row-building paths currently write;
- the **elevation angle** of the candidate beam's satellite at the focal user, for which no feature slot exists at all.

The arms, metrics, split, seed, estimator family and grid will be those of the two comparisons already run today, so the result is directly comparable to the resource-context test that failed. The primary metric is **held-out pairwise ordering within each anchor's candidate pool**, the same quantity measured at 0.650 for this route and 0.902 for an oracle that removes only the cross-user externality. The materiality rule already frozen for that test applies unchanged.

## My expectation, stated now
**I expect the gain to be small, and I would not be surprised by zero.**

The reason against: if the nominal margin at the rate target is exact, it already contains the antenna gain and the path — for the **focal link** the angle is a sufficient statistic and adds nothing beyond it.

The reason for: the target is a whole-network difference, and 79.3 % of its variance is externality — how *other* users' links change. That depends on angular geometry between beams, which the focal link's margin does not express. The raw angle at least locates the focal user in the pattern, and so hints how much of the focal beam's power spills into neighbours.

The hole in that reason: what actually determines the spill is the **neighbours'** geometry, not the focal angle alone. That is precisely what the 163 resource-context coordinates encode, and they failed today — rebuilt per focal action, only 28 of them varied at all.

So the mechanism that would make this work is the same one that has already been measured not to work, approached from a thinner direction.

## Why it is still worth one measurement
It is cheap, the harness exists, and the candidate is **not** in the class that failed for a structural reason: the resource-context coordinates failed because their useful variation is coalition-level while this route's interface is action-local. An angle is action-local. So this test distinguishes "the interface cannot carry the information" from "this particular information does not help", which are different diagnoses with different consequences.

And the hard-coded zero is a defect regardless of what the test shows: a slot the designers provided, filled with a constant, at both row-building sites.

## The standard this is held to
If the gain is immaterial, the record will show I predicted it, and the first route will have had three repairs measured and rejected — at which point the honest next step is to stop proposing repairs and run the contrast, letting the route answer for itself.

If the gain is material, the surprise is itself information: it would mean the externality is partly predictable from focal geometry, which nothing measured so far suggests.

Either way the prediction is on the record before the measurement, which is the point.
