# Open contradiction — the residual's sign flips between two measurements

**2026-09-10. `DIAGNOSTIC_NOT_CLAIM`. Recorded while unresolved, deliberately. No sealed
artefact, constant, threshold, sign, seed, horizon, price, guard or acceptance rule is
changed. This record exists so the contradiction cannot later be quietly resolved in whichever
direction turns out to be convenient.**

**Two receipts, both complete, disagree on the sign of the exact set residual's effect on
pooled reported EE. `RESIDTOGGLE` reports `+5.62%`. `C3REACH` reports `-60%`. Neither is
being preferred here.**

## The two receipts

| | `RESIDTOGGLE` | `C3REACH` |
|---|---|---|
| report | `ORACLE-RESIDUAL-TOGGLE-2026-09-10.md` | `C3-ARGMAX-REACHABILITY-2026-09-10.md` |
| worlds | `V025_PROBE_R2/world/1`, `/2` | `V025_PROBE/world/3` |
| anchors | 8 | 20 (x 4 lineages = 80 decisions) |
| catalogue | purpose-built, 8,192 cap, singletons + bundles + evacuations + rung controls | pilot's deployed `_build_anchor_rows(full_legal_actions=True)` + `_catalogue_with_census`, 948-1000 rows |
| **price / objective** | **exact-Fraction Dinkelbach, one common price across all eight anchors, per numerator** | **the pilot's own score: additive + interaction, boundary-0 `F = B - eta_ref*E` in kappa units** |
| exact residual effect, demand-capped | **+5.62%** (`8.548697 -> 9.029226` Mbit/J) | **30.82 -> 12.30 Mbit/J** over the 48 changed decisions |
| mechanism visible in the receipt | served `486 -> 503`, target attained `181 -> 192` | capped bits `6.219e12 -> 4.825e12`, **energy `201,800 -> 392,255 J`** |

## What both agree on

- **The residual is reachable.** `RESIDTOGGLE`: the two selectors differ at **8/8** anchors.
  `C3REACH`: exact `Psi` changes the argmax at **14/20** anchors, learned `Psi` at **20/20**.
  The earlier "C3 is structurally inert" reading is dead by two independent routes, and
  erratum 15 and erratum 16 are confirmed rather than merely argued.
- **Tie-breaks are not doing the work.** `C3REACH`: 0/80 final-ranking tie-break flips, and
  the top two rows were within 1 ULP in 0/80 rankings under every scoring variant.
- **The learned head is badly scaled.** Learned `Psi` spans 2,518-11,205 against an additive
  score spread of 107-264 at the same anchor - one to two orders of magnitude. It dominates
  the ranking rather than adjusting it. This independently confirms a worker's report that
  the learned head is "off by two orders of magnitude at the grand row" and reaches the
  decision "destructively".
- **`contexts.get(...)` is `None` on 79.164%** of pooled legal rows, so the residual can only
  reorder about a fifth of any catalogue. It still flips 70% of anchors within that fifth.

## Candidate explanations, none established

1. **Objective mismatch.** `RESIDTOGGLE` selects under a price solved to target pooled EE;
   `C3REACH` selects under the pilot's boundary-0 `F`. If the pilot's selection objective is
   misaligned with the reported numerator, a large-magnitude term would **amplify** that
   misalignment - which is consistent with energy nearly doubling in `C3REACH`. **`OBJMISMATCH`
   is measuring exactly this and has not reported.**
2. **Different worlds.** `world/3` versus `world/1` and `/2`.
3. **Different catalogues.** A purpose-built catalogue with evacuations and bundles versus the
   pilot's deployed catalogue.
4. **Different residual object.** `RESIDTOGGLE` adds `joint - sum(singletons)` reconstructing
   the candidate surplus exactly; `C3REACH` adds `_exact_interactions` under the production
   `contexts` gate, which is absent on 79% of rows. **These may not be the same quantity.**

Explanation 1 would mean the fault is in the **scoring objective**, not in the route - and
would be repairable without touching any of the three routes. Explanation 4 would mean the two
jobs measured **different things** and neither is wrong. I have evidence for neither.

## The rule I am binding myself to

- **Neither receipt is preferred, cited alone, or quietly dropped.** Any later statement about
  the residual's value must carry both numbers until the contradiction is resolved by
  measurement.
- The resolution must come from a measurement that **discriminates** between the candidates
  above - at minimum, running both scoring treatments on the **same** world, anchors and
  catalogue. That measurement is to be declared before it runs.
- **`RESIDTOGGLE`'s `+5.62%` remains reported against the pre-declared 10% and 5% screens**
  exactly as it was, and the pre-declared reading rule for it is unchanged. This record does
  not retract it; it records that a second measurement disagrees.
- If the contradiction resolves in the direction that makes the work harder, it is reported
  the same way and in the same detail as if it had gone the other way.
