# Ruling — no expressible demonstrator beats the learner on the trained objective; the line closes as declared

Date: 2026-09-11. Executes the pre-declaration in erratum 23.

## The pre-declaration being executed

From `V025-CONTROLLER-ERRATUM-23-...-2026-09-11.md`, written **before** the measurement:

> **If no expressible rule beats the learner on the scalarized objective, there is no
> demonstrator here and the whole demonstration-RL line closes** — that outcome is
> declared now and will be reported if it occurs.

**It occurred. The line closes on the objective as currently defined.**

## The measurement

Scripted arms on the MODQN harness, frozen seeds, no `update()` call. Harness validity:
`RANDOM_MASKED` reproduces the frozen run's own episodes 0-7 (r1 5.554e+06 vs 5.416e+06;
scalar −1.4037 vs −1.4498).

| arm | r1_mean | r2_mean | r3_mean | calibrated scalar | handover rate |
|---|---:|---:|---:|---:|---:|
| `GREEDY_R1R2` (best), n=24 | 7.518e+06 | −1.366 | −16.587 | **+0.8750** ± 0.0236 | 0.1412 |
| `GREEDY_SCALARIZED`, n=24 | 7.462e+06 | −1.426 | −15.936 | +0.8659 ± 0.0232 | 0.1501 |
| `MAX_NOMINAL_GAIN`, n=24 | **1.107e+07** | −6.757 | −20.964 | −0.0866 ± 0.0425 | 0.7115 |
| `GREEDY_R1R3`, n=8 | 9.321e+06 | −8.364 | −25.389 | −1.0587 | 0.9000 |
| `RANDOM_MASKED`, n=8 | 5.554e+06 | −7.756 | −13.361 | −1.4037 | 0.8664 |
| **trained `e6b063ef...` last-100** | 8.939e+06 | −2.322 | −18.598 | **+0.8859** ± 0.0190 | 0.2490 |

Best arm delta **−0.0109** against combined sem ~0.0303 — point estimate below target,
difference not resolvable. Against the checkpoint's five-window plateau mean **+0.9257**
the gap widens to **−0.0507**. `kappa` swept over eight values across five decades; single
peak, so the free constant does not explain it.

**Discipline note worth recording**: an 8-episode pass had the best arm at +0.8897, above
target. The agent reran at n=24, it reversed, and the reversal was reported rather than
the favourable pass.

## What the terms do

- **`r2` carries the whole thing.** Dropping it collapses the rule to −1.0587 with a
  handover rate of 0.9000, worse than random. The scalarized rule's entire edge over
  `MAX_NOMINAL_GAIN` is handover suppression.
- **`r3` does not carry it and mildly hurts.** Paired over the same 24 episodes,
  `GREEDY_R1R2 − GREEDY_SCALARIZED = +0.0091`, sem 0.0034 (~2.7 sem). Block 4 is
  `N_u(t−1)`; steering on a one-step-stale load count costs more than it buys.
- **`MAX_NOMINAL_GAIN`'s r1 win is real and survives**: 1.993x random against the
  learner's 1.650x. It is bought at handover rate 0.7115 = 2.9x the learner's 0.2490.

## The convergence, and why it is not a rescue

Two **independent** lines now say r3 does not earn its place:

1. **The power model** (R23HISTORY, from the code, no training outcome cited): adding a
   user to an active beam changes system power by **exactly 0 W**; lighting a new beam
   costs **>= +6.267 W**; the largest de-crowding saving is strictly smaller than the
   smallest cost of the beam it requires; `R = (B/U)*log2(1+gamma)` makes a beam's total
   rate independent of `U`.
2. **This measurement**: the r3 term costs +0.0091 at ~2.7 sem.

These were established separately and neither cites the other. That convergence is the
legitimate basis for reopening r3 — **not** the fact that the demonstrator lost.

## The tension that must be stated and must not be used to overturn this ruling

The separating term is **`r2`**, and R23HISTORY established — independently, from the
energy accounting, before this measurement ran — that **a handover consumes zero joules
in this simulator**, and that the one physical coupling has the **opposite** sign: a
handover breaks the power segment, resetting the link to `p0 = 0.825 W` (5.93 W supply)
instead of an aged segment's up to 1.65 W (8.38 W). **Handovers save energy here.**

So the learner's entire measured advantage lies in respecting a penalty with no
corresponding energy cost.

**This does not overturn the ruling, and it must not be used to.** The objective as
declared and as trained includes r2; against that objective there is no demonstrator, and
that is the reported result. Whether r2 should price handovers at all is a **modelling
decision for the owner**, to be made on the physics, and if it is changed then **all of
this evidence resets and every arm is re-measured**. Deciding it now, in the light of a
result that went the wrong way, would be selecting the objective by outcome.

## The estimand defect that makes all of the above provisional

**None of these numbers is pooled EE.** `r1_mean` is a mean over steps of a per-step
system EE — **a mean of ratios**. The project's declaration (v1.8 item 5) defines EE as
**pooled decoded bits over pooled system joules, a ratio of sums, never a mean of
ratios**. ZWHY found the same defect in the sibling's `argmax_EE`.

**The declared primary endpoint has never been measured for any of these arms, including
the trained checkpoint.** That measurement is dispatched, with its reading declared in
advance below.

## Declared reading of the pooled-EE measurement, written before it runs

- **The learner's pooled EE >= `MAX_NOMINAL_GAIN`'s** — the ruling above stands
  unqualified, on the declared objective as well as the trained one. The line stays
  closed.
- **`MAX_NOMINAL_GAIN`'s pooled EE > the learner's** — then the trained objective and the
  declared primary objective disagree, and *that* is the paper's finding: a scalarisation
  whose handover term, which has no energy cost, drives the policy away from the declared
  objective. **It still does not reopen the demonstration line by itself**; it makes the
  r2 modelling decision urgent and puts it to the owner.
- **Not resolvable at the seed count run** — reported as not resolvable; no widening of
  the search, no additional arms.

No threshold, weight or arm is added or changed after seeing this measurement.
