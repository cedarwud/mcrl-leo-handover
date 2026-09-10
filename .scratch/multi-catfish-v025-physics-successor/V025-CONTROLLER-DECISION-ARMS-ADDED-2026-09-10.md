# Controller decision — add the three single-informative arms, and how to measure them cheaply
Recorded 2026-09-10. Decided under the owner's criterion that every ruling be judged by whether it serves the goal of all three routes individually raising pooled efficiency. Evidence: an ultra-effort verification that read the deployed code **and executed a real-anchor probe** rather than arguing. `DIAGNOSTIC_NOT_CLAIM`; nothing sealed modified, no learner fitted, existing checkpoints rehydrated without perturbation.

**Decision: add them.** The leave-one-in contrast is half of the owner's stated requirement, and without those arms that half cannot be evaluated at all. The cost objection is now resolved with measurements rather than assertions.

## The reviewers' disagreement, resolved
One reviewer said the singles are necessary; the other said not to add them and cited a matched-anchor tier that would make nine arms cost about one. **They were describing two different settings, and both were partly right.**

The dependence is real: the proposal is a per-user argmax over the first two routes' outputs, the infeasibility repair uses their summed scores, and the bounded catalogue builder generates candidates **around whatever seed it is given** — copying that base's mapping, computing surplus relative to it, and constructing evacuations from the beams it occupies.

But **no production caller connects those two functions.** The existing pilot supplies a common carrier reference rather than the learned proposal. So the shared-catalogue lookup is sound *for the pipeline as implemented*, and unsound the moment arms carry their own learned seeds.

## The measurement that settles it
On three real anchors, comparing the full arm's catalogue with the first-route drop arm's:

| step | full | drop | **intersection** | union | Jaccard |
|---|---:|---:|---:|---:|---:|
| 0 | 908 | 910 | **0** | 1,818 | **0** |
| 1 | 911 | 912 | **0** | 1,823 | **0** |
| 2 | 910 | 909 | **0** | 1,819 | **0** |

**Zero cross-arm reuse.** Reseeding does not produce even approximately shared coverage, so "nine arms for the price of one" is false whenever arms reseed.

## A structural asymmetry that must be stated in any §C3 result
Proposed assignments changed, against the full arm:

| arm | assignments changed |
|---|---:|
| first-route drop | 12 to 26 |
| second-route drop | 29 to 69 |
| **third-route drop** | **0 at every anchor** |
| all-neutral | 64 to 92 |

**The third route's ablation acts through ranking alone; the first two act through both the proposal and the ranking.** The three routes are not mechanistically symmetric, and a §C3 table that does not say so invites a reviewer to assume they are.

## The construction adopted
Each arm keeps **its own seed and catalogue**, preserving its proposal, repair, candidate restrictions, reference contexts and score. A **shared physical cache** evaluates a configuration once per identical physical context, and each arm looks up its own candidates. For the one-step pooled comparison, only the **union of chosen configurations** is realised — at most nine outcomes per anchor. Realising every catalogue row is needed only for candidate-level regret questions.

Two rules carried verbatim into the design: **cached realised outcomes must never leak into selection**, and cache keys must bind tape, world, time, physical and run settings, evaluator identity, the nominal-versus-realised field, the boundary set and the prefix history — raw configuration identifiers are not sufficient because base identifiers embed carrier names.

Measured cost: a catalogue build takes 3.17 to 10.41 seconds at 701 nominal boundary evaluations; forty-eight profiles over forty-eight boundaries take 5.41 seconds; repeated lookups take microseconds. So the dominant per-anchor cost is **one catalogue build per arm**, not realisation.

## Standing
This decides how to measure the contrast, not what the contrast is. No arm definition, source, catalogue rule or acceptance criterion changes. The captured probe is a component measurement on pilot heads, not deployment conformance and not source-benefit evidence.
