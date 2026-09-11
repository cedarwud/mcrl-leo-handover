# Erratum 25 — the objective re-specification proposal is rejected; my r3 argument contains an algebra error

> **PROVENANCE WARNING (added 2026-09-11 by the controller after CURATE):** this document contains at least one comparison between numbers produced under different conditions (physics/harness, estimand, host + TLE archive, or paired vs unpaired). Before citing any number from it, look it up in `.scratch/RESULTS-REGISTRY.md` (conditions per row, §2 lists the cross-condition comparisons) and check this document's status in `.scratch/DOCUMENT-STATUS.md`. Text below is unchanged.

Date: 2026-09-11. Adversarial review: `.scratch/reviews/objrespec/ADVERSARY-OBJECTIVE-RESPEC-2026-09-11.md`.
**Verdict: REJECT.** I accept it in full.

## Objection 1 — the replacement term is ~100x too weak, so the proposal deletes r2

`dt = 30.08 s`, so a sourced 142 ms interruption destroys **0.472%** of one user-step's
bits. Applied to the panel at its most favourable: `MAX_NOMINAL_GAIN` x 0.99664,
`TRAINED` x 0.99868, ratio 1.19771 → **1.19526**. **It closes 0.24 pp of a 19.77 pp gap —
1.2% of it.**

To close the gap you would need `f = 0.34516`, i.e. **10.38 s of interruption per
handover, 68-167x the sourced value** — which `docs/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md:206`
**explicitly forbids**.

In the run's own calibrated units, one handover currently costs a **+13.71%** rise in
episode `r1` to break even; under my proposal it would cost **+0.047%** of bits.

**My proposal cuts the handover price by ~290x. That is a near-total deletion of `r2`
wearing a physics costume**, not the "move the cost to where it physically lands" I
described it as. I did not do this arithmetic before proposing it. **The 0.2506 pp
cross-arm figure SPECPROFILE gave me was exactly this number, and I reported it without
drawing the conclusion it forces.**

## Objection 2 — my r3 argument contains an algebra error

I wrote, and told the owner:

> `R = (B/U)*log2(1+gamma)` makes a beam's total rate independent of `U`.

**That is false when the served users' SINRs differ.**

`R_beam = sum_u (B/U) log2(1+gamma_u) = B * mean_u SE_u`

The beam's total rate is `B` times the **mean spectral efficiency**, not a `U`-invariant.
The marginal effect of admitting user u is `B(SE_u − mean_SE_b)/(U_b+1)`, **negative
exactly in the crowding case** — a large numerator derivative standing against the zero
power derivative I had correctly established.

The repo's own proof that the old r3 was load-blind (`service.py:334-351`,
`old_r3_is_load_blind`) takes `spectral_efficiency` as a **scalar** — it assumes
homogeneous SINR. **I inherited that assumption without noticing it was an assumption.**

**Second channel I missed**: `interference.py:10-14` — interference is z-gated and
load-unweighted, so lighting beams costs everyone SINR. **That makes spreading
EE-negative, which is the opposite sign to what `r3` rewards.**

So `r3 = −U` is still the wrong instrument — the review concedes this, and the panel's own
paired `GREEDY_R1R2 − GREEDY_SCALARIZED = +0.0091` at ~2.7 sem agrees — **but my
diagnosis of why was wrong, and therefore so was my treatment.**

## Objection 3 — I overturned a sealed decision, uncited, for the third time

The review could not break the 19.8% statistically and concedes all four fronts I claimed:
epochs independently drawn (`ephemeris.py:421`), fading RNG consumption action-independent
(`step.py:1375-1388`), estimand defect <= 0.06%, and the frozen run has a real 10-seed
eval loop.

**But `step.py:786-808` resets the power segment on any association change**, pinning
received power at `p0*G(tau)`. `MAX_NOMINAL_GAIN` re-anchors at maximal gain **every
step**, so it gets more bits *and* fewer joules **by construction**. That is the renewal
premium this project recorded on 2026-09-08
([[segment-anchored-power-finding-2026-09-08]]).

**And the sealed V0.25 successor already fixes both**: it adds occupancy → required-power
and **removes the entry anchor**. It removes the mechanism producing finding 3, and it
makes `r3`'s premise **true** (required SINR ∝ `2^(r*n_b/B)`, exponential in occupancy).

**I proposed overturning a sealed decision, without citing it, in the direction it
rejects.** [[adversarial-review-before-overturning]] records this error as having been
made twice. **This is the third.** The memory says to read the full revision history and
search whether I have previously attacked the thing myself. I did neither.

## The moot test — dispatched

Re-run `MAX_NOMINAL_GAIN` and the trained checkpoint on pooled EE with the **segment entry
anchor ablated**. The harness exists: diag2 already established the premium was "purely
the `p0` reset". **If the +19.8% collapses, the objective never disagreed and the whole
proposal was treating an artefact.**

## What survives

- **The C1VSGAIN closure** — untouched. It concerns the V0.25 stage-C route design.
- **The demonstration-line closure** — untouched. No expressible arm beats the learner on
  the trained objective.
- **`r3 = −U` is the wrong instrument** — conceded by the review, on two independent
  grounds neither of which is mine.
- **The two reward defects** (outage as the maximum of both bounded heads; the logged
  `scalar_reward` being uncalibrated so the headline curve is `0.5*r1`) — independent of
  all of this and still to be fixed.
- **Verified by the reviewer against repo constants**: 6.26606 W new-beam cost and
  2.45536 W max in-segment bump reproduce exactly; zero-joule handover and the `p0` reset
  confirmed at file:line; 62/142 ms confirmed against **TS 38.133 Annex A.14.2** — which
  also resolves the `VERIFY_SOURCE` flag on those two constants.

## The review's own recommendation, recorded not adopted

Run the anchor ablation; **touch nothing until the successor lands**; and if the gap
survives, fix the **endpoint declaration** — pooled EE subject to handover and service
constraints, the CMORL formulation this project's own outside review already recommended —
**not the reward**.

That is a change to a declared endpoint and is the owner's decision, not mine. It is
recorded here so it is not lost, and it is **not** being acted on.
