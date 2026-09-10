# Pre-declaration — how the residual-ceiling result will be read

**2026-09-10, written BEFORE either measurement has reported.** No sealed artefact,
constant, threshold, sign, seed, horizon, price, guard or acceptance rule is changed by this
record. Its only purpose is to fix the reading rule while the outcome is still unknown.

## What is being measured

- **RESIDTOGGLE** — over one fixed catalogue at 8 anchors under corrected physics,
  `ADDITIVE_ONLY` versus `WITH_RESIDUAL` in the **deployed selector**, scored on the
  **reported** objective: pooled committed EE over 48 boundaries, demand-capped. This is the
  ceiling on what **any** C3 head can be worth inside the deployed selector, because it gives
  the residual exactly rather than predicting it.
- **OBJMISMATCH** — whether the certified endpoints are locally optimal under the **reported**
  objective, as opposed to the boundary-0 selection objective `F = B - eta_ref E` they were
  certified against.

## The screens, as the two strategic reviews stated them

| Reviewer | Screen |
|---|---|
| astra | **10%** |
| fable | **5%**, and required on **both** halves |

Both were stated before either measurement ran. **They are not adjusted here and will not be
adjusted after the fact.**

## The reading rule

Let `R` be the residual ceiling RESIDTOGGLE reports on the reported numerator.

- **`R` at or above 10%** — both screens pass. The current decomposition can in principle
  support a substantial C3 contribution, and repairing the panel harness is justified. The
  repair order is the owed-repair register in
  `V025-CONTROLLER-FINDING-CORPUS-IS-SURROGATE-2026-09-10.md` section 5, not a new plan.
- **`R` between 5% and 10%** — the reviewers' screens disagree on this interval. **This is
  not mine to resolve by preference.** It goes to the owner with both screens stated, both
  numbers stated, and no unilateral call.
- **`R` below 5%** — both screens fail. The current decomposition cannot support the stated
  requirement for C3, and the panel as designed should not be built. That is reported plainly,
  against fable's stated conclusion and astra's, without softening.

OBJMISMATCH is read the same way on its own half and does not substitute for `R`.

## What does not count as evidence here

- Any gain measured under the **capacity** numerator. One such headline moved from `+113.412%`
  to `+0.273%` today when the demand cap was applied.
- Any **oracle-only** gain, including a mode-selection counterfactual that uses the realised
  fading draw.
- Any loss value, from any route, in any direction.
- Anything measured on the shipped surrogate corpus, whose C1/C2 labels are not the declared
  targets.

## Validity condition, declared in advance

`EVALPATH` is currently determining whether `StepEvaluator.evaluate` and `evaluate_many`
disagree on the same `Configuration`, and if so which is authoritative. **If it finds that
RESIDTOGGLE was scored through the non-authoritative path, or through a mixture of the two,
that measurement must be repeated on the authoritative path.**

This repetition is declared **now, before either result is known**, precisely so that it
cannot later be an outcome-selected rerun. It is conditioned on a validity finding about the
instrument, not on the value of `R`. If EVALPATH finds the paths agree, or finds RESIDTOGGLE
used the authoritative path, the first result stands as reported — **including if it fails
the screens**.

## What I will not do

- I will not re-run either measurement because of what it reported.
- I will not move a screen, in either direction, after seeing a number.
- I will not report a pass by quoting the more favourable of the two numerators.
- I will not describe a result between the two screens as a pass.
