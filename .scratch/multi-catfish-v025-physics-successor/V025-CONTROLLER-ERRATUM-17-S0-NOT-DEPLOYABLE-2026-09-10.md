# Erratum 17 — S0's +1.812631% is not a deployable-information result

Date: 2026-09-10 · Controller · Found by REVIVE, not by me
Source: `/home/sat/mcrl-v025-selector-ws/SET-LEVEL-DECODER-REVIVAL-2026-09-10.md`

## What I said

Repeatedly, including in the design-state document given to the owner and in the
memory file `c3-s0-deployable-decoder-2026-09-08.md`:

> "S0 是第一個以**可部署資訊**拿到 headroom 的正結果 (+1.812631%)，達到天花板的 91%。"

## What is true

**The scoring was deployable. The candidate formation was not.**

S0's joint candidates were imported from E1 tapes. E1 formed each origin-beam
evacuation group **after a keyed-fading BASE evaluation**, using that realised
profile's `served`, `serving_satellite`, `serving_cell`. The selector then rescored
those rows with fading disabled — so the *score* is fade-free, but *which rows were
on the menu* was decided with information a deployed system does not have.

**This is not a dormant path.** S0 chose a joint row on **109 of 120 anchors**. The
contaminated construction is where nearly the whole result came from.

Second error, smaller: **"91% of the ceiling" is against U1 only.**
`1.812631 / 1.992311 = 90.981%` (U1); `1.812631 / 2.222094 = 81.573%` (J1).
I quoted the larger fraction without naming which ceiling.

## What survives

**C3-S v1 repaired exactly this boundary.** It rebuilt the evacuation catalogue from
a detached fade-free nominal BASE, rejects live-environment/RNG access, and
fingerprints state before and after selection. REVIVE verifies it as
**deployable at the decision boundary**.

So the deployable set-level result is **C3-S FULL +2.883167% / LITE +2.921776%**
(BASE 117,419,389.19; 35,971/36,000 served in every arm) — not S0. The stronger
number was always the clean one; I had been leaning on the weaker contaminated one.

## Why this matters beyond bookkeeping

The set-level direction was the one place I told the owner "this already works with
deployable information, we just need to port it." The honest statement is narrower:
**one V0.23 screen (C3-S v1) demonstrates a deployable set-level decoder on V0.23
physics.** And REVIVE's transfer table says the physics engine, the catalogues, the
checkpoints, the harness, the panels and even the choice score do **not** transfer —
V0.25's contract score is `F(a)=B−η_ref·E−Φ(a)`, not V0.23's `B−η_ref·E`. What
transfers is the *decision object* and the *information principle*, nothing numeric.

**No V0.23 percentage states a V0.25 expectation.**

## Third finding, unrelated to S0, that blocks measurement

`EVALPATH-2026-09-10.md` leaves evaluator path authority **UNDETERMINED**, and the
cause is a defect: **the evaluator cache key omits field / path / boundary
semantics**, so a scalar-cached BASE can be silently compared against dense
candidates. Existing mixed-path S0 rows are invalid inputs to any revival decision.
Any set-level probe must open **one fresh dense boundary-0 evaluator for selection**
and **one fresh dense full-48 batch for endpoints**, or it measures nothing.

## Standing correction

Every future statement about the set-level route cites **C3-S v1** and says
"V0.23 physics, development screen, does not transfer numerically."
The S0 number is retired from evidential use.
