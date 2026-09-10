# Pre-declaration — how the exact-corpus C3 result will be read, given that the surrogate run says −23%

Date: 2026-09-10 ~17:28Z · Controller
**Written after the surrogate-corpus number exists and BEFORE the exact-corpus run produces
one.** `EXACTTRAIN2` launched 17:22Z and has produced no result.

## The number this document exists to constrain

First five-arm scoring, `panel-q1v1`, 20 development anchors.
*Reference: each `DROP_X` arm, and `ALL_NEUTRAL_CONTROL`. Information class: development —
**one seed** (`6407676579069309528`), **500 unconverged updates**, **surrogate labels**, and
**12 of 20 anchors' reference objects reused from the contaminated `PANELCEIL` path**.
Estimand: relative pooled-EE marginal. Numerator: full-buffer pooled EE, no demand cap.*

| arm | pooled EE (Mbit/J) |
|---|---:|
| `DROP_C3` | **43.211826** |
| `FULL` | 33.255431 |
| `DROP_C1` | 32.476038 |
| `DROP_C2` | 25.991598 |
| `ALL_NEUTRAL_CONTROL` | 23.469363 |

| route | `FULL − DROP_X` | relative to `DROP_X` |
|---|---:|---:|
| C1 | +0.779393 | **+2.400%** |
| C2 | +7.263833 | **+27.947%** |
| **C3** | **−9.956395** | **−23.041%** |
| `FULL − ALL_NEUTRAL_CONTROL` | +9.786068 | +41.696% |

**Two routes positive; C3 strongly negative. Removing C3 improves pooled EE by 23%.**

## The confound that must not be used as an excuse afterwards

`EXACT-CORPUS-TRAINING-2026-09-10.md` measured, before this scoring was read:
**C3's surrogate labels disagree with the exact labels on 18 of 22 anchors — 81.8182%.**
C1 is 51.68%, C2 55.27%.

**A head trained on 82%-wrong labels actively degrading the decision is the expected outcome,
not a surprise.** But "the labels were wrong" is exactly the kind of explanation I could reach
for after seeing any unfavourable number, so the reading is fixed here instead.

## The reading rule, fixed now

`EXACTTRAIN2` trains the same five arms on the **exact** corpus with the declared step-decay
schedule and the offline stopping rule. When its scoring lands:

| exact-corpus C3 marginal | reading, fixed in advance |
|---|---|
| **positive** | the surrogate result was a label artefact. C3's earlier negatives — including the F1 kill screen and the oracle-marginals probe — were measured on the same defective labels and their scope is narrower than recorded. **This does not make C3 "alive"; it makes the earlier negatives uninformative.** |
| **near zero** | C3 contributes nothing at this operating point. The owner's three-route requirement is not met by this design, and the honest options are a different C3 target, a wider catalogue (`\|A\|<=2` is 98.13% today), or dropping to two routes. |
| **still strongly negative** | **C3 is harmful, on exact labels, at convergence.** That is a real finding and it stands. It is then reported as a negative result, and no further label, schedule or corpus explanation is offered for it. |
| positive but service falls | **not admissible** under the service guard, whatever the EE. |

## What this scoring may and may not be used for

**May:** confirm the arms produce distinct, nonzero contrasts — they do, and `SCALE` predicted
it from decision counts (`DROP_C3` differs from `FULL` on 39/480 decisions, 11/20 anchors).

**May not:** state that any route is dead, or that C3 is harmful. **One seed, unconverged, wrong
labels, partly contaminated reference.** Fifteen further seeds exist and were not scored; this
was an interface-acceptance run.

## Two things to fix regardless of the outcome

1. **Score all 16 seeds**, not one. A single seed is not a result and I will not report the
   ranking above as one.
2. **The 12 contaminated reference anchors** in `panel-q1v1` still need correcting, and the
   `certified_fixed_point` / `anytime_incumbent` axes remain unusable until then.

## Note on what is *not* claimed

`DROP_C3` at 43.211826 sits above `RSS_MAX`'s 41.621560 — **on a different panel** (20 anchors
versus 12) and therefore **not comparable**. I am recording that explicitly so the coincidence
is not repeated later as a comparison.
