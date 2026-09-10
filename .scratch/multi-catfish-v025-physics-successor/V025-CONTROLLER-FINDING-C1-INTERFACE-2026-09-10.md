# Controller finding — the first route's problem is its interface, not its features
Recorded 2026-09-10 from the resource-context diagnostic, whose arms, metrics, estimator family, grid, split and seed were declared before any fitting. `DIAGNOSTIC_NOT_CLAIM`. Offline fit on copies; nothing sealed modified.

## The hypothesis, and its result
I assembled it from three of today's reports: the design review measured the first route's pairwise ordering at 0.650 against 0.902 for an oracle that removes only the cross-user externality; the sufficiency diagnostic found the interaction head already receives 163 resource-context coordinates the per-user head does not; and the parametrisation comparison measured those coordinates as worth 1.067 in mean selection regret. So: perhaps the missing information already exists, is already consumed at decision time, and the per-user head simply does not receive it.

**Result: held-out pairwise ordering 0.619236 with the admissible context against 0.620817 without it. A gain of −0.001581**, closing −0.63 % of the gap, with leave-one-step-out gains ranging −0.006425 to +0.004496. Against the frozen materiality rule — at least 0.0252 and positive on every omission — this is **not material**, and its sign is negative.

## Why, and this is the part that matters
The coordinate formulas are admissible: they are built from the reference assignment and the decision-time tape, read static cross-gain arrays, and accept no evaluator or outcome. But **a coalition-wide vector depends on the other proposed members' actions, while the first route's interface is action-local.** The stored values could therefore not be handed over; the same 163 formulas had to be rebuilt from the reference profile and the focal user-action alone.

Rebuilt that way, **only 28 of the 163 slots vary across held-out singleton actions.** The coalition-induced variation in the remaining 135 is unavailable under an action-local rule.

**The useful variation in those coordinates is coalition-level, and the first route is per-user by interface. It cannot receive it.** This is not a feature-plumbing problem.

## The same lesson as this morning, from the other side
| arm | validation RMSE |
|---|---:|
| sealed vector only | 11.418 |
| plus admissible context | **8.123** |
| plus context, externality removed from the target | **5.356** |
| leaky oracle, not deployable | 0.000036 |

The context improves **value** prediction substantially and makes **ordering** slightly worse. The parametrisation comparison found the mirror image — those same coordinates worsened pointwise interaction calibration while improving selection regret by 1.067. **Value error and ranking are different quantities, and the one we need is ranking.**

## What this closes and what it does not
It closes the cheapest remaining repair for the identified bottleneck, and it is the **second** first-route repair today to buy exactly nothing — the first being an admissible feature that turned out constant at all thirty anchors. The difference is that this time the reason is structural: any real fix would have to change what that route sees at the interface, which is fixed by contract §C1 — the same class of change I declined earlier today for the third route on the grounds that it removes the structure the owner's requirement is stated over.

**It does not establish that the first route's ablation marginal is zero.** These diagnostics measure how well its target can be predicted from pre-decision information. The owner's contrast measures whether informative source training changes the committed outcome relative to neutral training — a different question. The tier probe measured that dropping this route changes **12 to 26 proposed assignments** at every anchor tested, so it demonstrably moves the decision. Whether it moves it for the better is exactly what has never been run.

## Standing
I am proposing no third repair. Two of my own have now bought nothing. The next step is to run the contrast and let the route answer for itself.
