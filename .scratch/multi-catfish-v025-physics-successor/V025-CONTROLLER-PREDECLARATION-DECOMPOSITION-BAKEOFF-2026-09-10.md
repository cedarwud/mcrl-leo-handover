# Pre-declaration — head-to-head screen of the two candidate decompositions

**2026-09-10, written BEFORE any exact-path row exists.** `EXACTGEN` is generating the
corpus and has produced nothing yet. No sealed artefact, constant, threshold, sign, seed,
horizon, price, guard or acceptance rule is changed. This fixes the comparison metrics while
no data exists to tune them against.

## The two candidates

| | Partitions | Three routes | Cost to the claim |
|---|---|---|---|
| **F** (fable) | the **physical quantity** | credited bits under the candidate's occupancy; resource energy under the candidate's activation; continuation | **forfeits coordination as a named ablatable route** |
| **A** (astra) | the **information** | local-link innovation; temporal innovation; relational innovation — successive increments of `E[Y \| I0, X_J]` where `Y = B - eta_ref*E` | keeps three named routes; **ablation must propagate through the whole computation**, not zero an output |

They partition different axes, so they are not variants of one another and **neither is a
special case of the other**.

## What can and cannot run in parallel

**Can, and should:**
- Both derive every target from the same coupled-physics quantities — whole-network bits and
  joules, per-user attribution, the three sealed offsets. `EXACTGEN` produces those once and
  both consume them. **The expensive part is shared.**
- Both can be screened **offline, with no training and no policy run**, by computing their
  targets on the same rows and measuring the quantities below.
- The mode-selection change (`R2`/`R3` stale-CQI) sits in the control law, not the route
  layer, and is orthogonal to both.

**Cannot:**
- A contract v2 declaration names **one** set of three route identities. The choice is
  exclusive **at declaration time**, not at measurement time.
- Full training of both to endpoint would double the panel cost. This screen deliberately
  stops before that.

## Metrics, fixed now

Computed for **F**, for **A**, and for the **incumbent** `Psi = Delta F(A) - sum d_i`, on the
same rows, same anchors, same catalogue:

1. **Pointwise conditioning.** Parts-to-total ratio `(sum |parts|) / |total|` at each
   coalition size, and its growth in size. The incumbent's measured values are 1.57x at pairs
   and 22.99x at the grand row; report every candidate on that same scale. Report the
   **pointwise** figure for all three. A population RMS bound may be reported **alongside**
   but never in place of it, and never compared directly against a pointwise number.
2. **Reachability.** Fraction of anchors at which the third route's term changes the catalogue
   argmax, computed **exactly** (with the exact term, not a learned head), plus the share of
   catalogue rows the term can never reorder.
3. **Learnability of each route, separately.** Held-out `R^2`, within-group pairwise ordering,
   and top-1 argmax agreement, under leave-one-anchor-out and leave-one-world-out, against a
   linear model, a constant predictor, and a high-capacity model on the same inputs. A
   high-capacity failure means the ceiling is **informational**, not architectural.
4. **Distinctness.** Pairwise correlation between the three routes' targets, and the `R^2` of
   each route regressed on the other two. A route that is a function of the others is not a
   separate source, whatever it is named.
5. **Cost.** Wall time to produce each route's target per anchor, so the panel can be costed
   before it is funded.

## Reading rule, fixed now

- **No winner is declared on conditioning alone.** Conditioning is necessary, not sufficient:
  a perfectly conditioned decomposition whose routes are not separately learnable, or not
  distinct, fails.
- **A candidate that fails (2) — its third route cannot change the argmax — is rejected for
  the three-route claim**, regardless of how well it scores elsewhere. It may still be
  reported as a better total-score predictor.
- **If both pass every metric**, the choice is **the owner's**, because the deciding question
  is what the paper claims — whether "coordination" survives as a named ablatable route — and
  that is not a measurement.
- **If both fail**, that is reported plainly, with the incumbent's numbers beside them, and
  no third candidate is invented to rescue the outcome in the same breath.
- Nothing here is an EE claim. None of these metrics is pooled EE, and none may be reported
  as one. Committed pooled EE is measured only on a declared panel, later, if one is funded.

## What this pre-declaration is not

It does not authorise contract v2, a corpus substitution, a panel, or any training. It fixes
how two proposals will be compared, before either has a number attached.
