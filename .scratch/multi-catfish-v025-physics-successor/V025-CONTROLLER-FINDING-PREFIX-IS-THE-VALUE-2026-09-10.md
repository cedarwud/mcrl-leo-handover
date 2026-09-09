# Controller finding — the non-learned prefix is not a convenience, it is the value
Recorded 2026-09-10 from the prefix ablation: eight real anchors fixed before results, identical world digests across rules, identical catalogue rules, caps, objective, price, tie-break and served-count guard between arms; only the seed configuration changes. `DIAGNOSTIC_NOT_CLAIM`. No learner, no training run, nothing sealed modified.

## The owner's masking concern, answered
The owner observed that a coordination layer sitting on top of a learned network re-scatters what was learned, so the learning effect cannot be seen. That is true, and this measurement establishes the reason it cannot simply be removed.

Seeding the bounded joint catalogue from the **raw geometric assignment** instead of from the iterated unilateral fixed point recovers only **6.03 %** of the prefix's pooled uplift under the sealed rule and **4.99 %** under the corrected one. Against the geometric baseline the catalogue-only arm gains **+35.78 %** and **+21.63 %**, where the prefix gains **+593.06 %** and **+433.66 %**.

**The raw geometric state does not expose a large one-catalogue learning band. The non-learned prefix creates almost all of it.**

## Why, structurally
The catalogue can move only prescribed groups of at least two users, each member restricted to a single alternate computed at the current seed. The unilateral search instead makes a long sequence of context-dependent **singleton** moves, changing the interference and occupancy context at each step and recomputing against it.

The report's decisive observation: **no accepted unilateral transition is directly expressible as a catalogue row**, and the unilateral endpoint configuration **is absent from all eight initial catalogue-only candidate sets** under both rules.

## Iterating the catalogue does not substitute either
| arm | against the prefix | per-anchor | cost per anchor |
|---|---:|---|---|
| corrected rule, sixteen catalogue rounds | **−20.93 %** | **worse on 8 of 8** | 60,198 evaluations, 904.8 s |
| sealed rule, sixteen catalogue rounds | +9.38 % | **worse on 5 of 8** | 61,372 evaluations, 603.9 s |
| the prefix itself | — | — | ~12,000 evaluations, 30–36 s |

Under the sealed rule iterated set-level moves do eventually exceed the prefix's pooled value, but at roughly twenty times the evaluation cost while still losing on most anchors. The honest reading, which the report states itself, is that the prefix is a **much cheaper route to broadly high quality**, not that the catalogue-only asymptote is necessarily lower.

## What this closes
Together with two other measurements today, every route for making the coordination layer's contribution look larger is now closed:

- **the deadline route** — a competent anytime unilateral already holds 82 % to 88 % of its converged gain at the 30.08-second interval;
- **the prefix-removal route** — this measurement;
- **the reparametrisation route** — direct prediction ranks better but removes the three-route structure the owner's requirement is stated over.

The coordination span itself is currently **unknown**, because every figure recorded today is paired against a local optimum that a different traversal order improves on. That re-measurement is running.

## The consequence for where effort goes
There is no remaining exploratory direction on the coordination side. What has never been measured at scale is the owner's actual requirement — the source-training contrast over the three routes — whose arms are compared with each other and are therefore untouched by all of the above. That is where the remaining effort belongs.
