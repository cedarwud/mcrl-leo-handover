# Declaration — the MODQN comparator binding, and an amendment to a sealed condition

Date: 2026-09-10 ~17:05Z
Decision by: the owner, on this date, in response to `BASELINE-MODQN-REFERENCE-2026-09-10.md`
Status: **the acceptance gate's definition. Written before any MODQN EE on V0.25 exists.**

## The gap this closes

`BASELINE-MODQN-REFERENCE-2026-09-10.md` (`/home/sat/mcrl-v025-modqn-ws`) established, by
reading the seals and loading the artefacts:

- the V0.25 contract names an **"external BASELINE"** and **binds nothing executable** — no
  policy, checkpoint, training regime, or V0.25-to-legacy interface mapping;
- the V0.23 declaration binds it precisely: *"the unchanged, externally authenticated
  pre-Catfish MODQN policy … and is **never a trained arm**"*, checkpoint SHA-256
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`, **112 states, 28
  actions**, 9,000 episodes;
- the checkpoint and its adapter still load, but **no path submits their decisions to the
  V0.25 `a-r0` evaluator**, so the gate is **unmeasured, not zero**;
- the object the current pilot calls `BASELINE` is `carrier_base`, a **fixed carrier geometry
  control**. **Using its numbers as the MODQN gate would be a category error**, and without
  this determination that is what tonight would have reported.

## The decision

**Primary gate: a MODQN retrained on V0.25 physics.**
**Secondary, reported alongside: the frozen V0.23 checkpoint replayed on V0.25 physics.**

Both are reported, always, in every place the gate is stated. Neither may be omitted because
it is the less favourable of the two.

**Why retrained is primary.** The V0.23 checkpoint learned on a physics engine that V0.25
replaced — angle/rate/TPC/TDM/ACM, corrected v1.9 provisioning, a different energy account.
A policy frozen on the old engine and deployed on the new one is handicapped by distribution
shift. Beating it would partly measure *"we changed the engine"*, not *"the three routes
help"*. The owner's criterion is about the three routes, so the gate must be physics-matched.

**Why frozen is retained as secondary.** It is what the sealed record literally names, and
dropping it would break continuity with the V0.23 declaration.

## This amends a sealed condition, and the amendment is declared as such

The V0.23 declaration says `BASELINE` **"is never a trained arm"**. Retraining it is a change
to that condition, so it is declared, not slipped in:

1. **The prior declaration is acknowledged**, quoted above in full.
2. **The reason is independent of the outcome it would help.** V0.25 replaced the physics
   engine; a comparator frozen on the previous engine is not like-for-like. That reason existed
   before any V0.25 measurement and does not depend on which way the comparison goes.
3. **The outcome is not known at the time of the decision.** `MODQNREF` verified that MODQN's
   V0.25 pooled EE is **unmeasured**. Nobody — owner or controller — knows whether retraining
   makes the gate easier or harder.
4. **The frozen arm is not removed**, only demoted to secondary, so no evidence is lost.

## Fairness bindings — fixed now, before MODQN is trained

Retraining creates a surface on which the comparator could be weakened, deliberately or by
inattention. These close it. **They are fixed before the run and are not to be revised against
an observed MODQN result.**

1. **At least the Catfish budget.** MODQN receives **no less** training budget and **no fewer
   seeds** than the five sealed Catfish arms. If the Catfish arms run 16 seeds, MODQN runs at
   least 16.
2. **At least the Catfish information.** MODQN's observation carries **no less** decision-time
   information than the Catfish system's. If a field is available to Q1/Q2/Q3, it is available
   to MODQN unless the legacy interface structurally cannot carry it — and every such case is
   named in the report.
3. **Its own hyperparameters, honestly chosen.** MODQN is tuned by the **same procedure** used
   for the Catfish heads — a convergence screen against a rule fixed before it runs, computing
   no EE — and the admissible setting is chosen on the same grounds (earliest admissibility,
   then cost). It is not given the Catfish heads' literals if those are wrong for it.
4. **No outcome-selected reruns.** The first completed run under this binding is the reported
   one. A rerun requires a stated defect, declared before its result is seen.
5. **Report the stronger of primary and secondary as the harder gate.** If the frozen replay
   scores **higher** than the retrained MODQN, the frozen number is the one the Catfish must
   clear. **The comparator is never selected downward.**
6. **Configuration frozen before launch**, with digests, in a launch receipt.

## The evaluator rule, binding on every measurement under this declaration

Selection: **one fresh dense `StepEvaluator(boundary_indices=(0,))`** per anchor, with `BASE`
and every candidate in its **first** `evaluate_many` call; **no scalar `evaluate`**, no foreign
cache preceding it. Endpoints: **one separate fresh realised dense full-48** evaluator, `BASE`
and all endpoints in one call. Assert both in code and report the assertion result.

Non-negotiable: `SELECTION-SURFACE-2026-09-10.md` showed a scalar-cached `BASE` moved a
published fixed point from `13.430253` to `31.028111`, retaining **0 of 12** configuration IDs.

## What is measured, and how it is reported

On the development panel, full-buffer numerator, no demand cap: pooled EE, pooled bits, pooled
joules, served PHY, rate-target attainment, `modal_frac`, `active` beams and satellites,
`argmax_distinct` — for **retrained MODQN**, **frozen-replay MODQN**, and the learned arms.

**Disclosure that is not optional.** The non-learned family is **not** a gate — the owner has
fixed that the Catfish need only beat MODQN. But where the Catfish and MODQN sit relative to
`RSS_MAX` (**41.621560**), the clean fixed point (**31.028111**) and `RANDOM` (**11.233999**)
is **reported every time the gate is reported**. A reviewer will ask; the answer is given
before it is asked.

## Open, and not settled here

Whether MODQN retraining on V0.25 is a bounded piece of work at all. `MODQNBRIDGE` (17:03Z) is
building the option-independent half — the 112-field projection, the 28-slot roster with a
physical-identity round trip, the edge rules and known-answer tests — and is instructed to stop
and report if the projection **cannot be completed without invention**. If it cannot, this
declaration's primary gate is not yet constructible and that becomes the next decision.
