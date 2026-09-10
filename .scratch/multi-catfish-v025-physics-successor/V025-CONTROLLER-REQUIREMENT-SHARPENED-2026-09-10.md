# Requirement sharpened — every marginal, alone and conditional, must be strictly positive

**2026-09-10, ~08:55 UTC. Owner decision about what the paper claims. No estimand, formula,
sign, threshold, seed, horizon, price, guard or acceptance rule is changed. Nothing sealed is
modified.**

## The owner's words

> "雖然我說可以比較小，但不代表單獨可以是負的或是零，然後跟其他 catfish 搭配的時候可以稍微
> 變小，但也是一樣不能搭配的時候變成零或是負的"

**Each route must be strictly positive alone, and strictly positive in combination.**
Magnitudes may be unequal and may shrink under combination. Zero and negative are excluded in
both positions.

**This is recorded before `C2WIRING` reports** and while `SWEEPA`/`SWEEPF` are still running.

## The bar is now six inequalities, not one

| | required |
|---|---|
| `C1_ONLY > BASELINE` | strictly |
| `C2_ONLY > BASELINE` | strictly |
| `C3_ONLY > BASELINE` | strictly |
| `FULL > DROP_C1` | strictly |
| `FULL > DROP_C2` | strictly |
| `FULL > DROP_C3` | strictly |

## Where `FACTORIAL` stands against it — exact terms, a ceiling, not achievable values

| route | alone | conditional | verdict |
|---|---:|---:|---|
| C1 | **+10.80%** | **+17.10%** | passes both |
| C2 | **+0.45%** | **+0.00%** | **fails conditional** — `FULL` and `DROP_C2` are identical in EE, bits, energy and selected sizes |
| C3 | **−0.06%** | **+5.62%** | **fails alone** — `-0.004505` Mbit/J |

**Four of six pass.** Both failures are small in magnitude and both are already under
investigation: `C2WIRING` is testing whether C2's exact-zero conditional marginal is a
magnitude fact or a wiring defect of the kind proven for the provisioning-rule variant
earlier today.

## The observation this requirement forces, and it is not a complaint

`C3_ONLY` scores catalogue rows by `Psi = Delta F(A) - sum_i d_i` **alone**. `Psi` is defined
as the part of the joint change that the per-user terms do not account for. Ranking
configurations by that residual **while ignoring the per-user terms it is a residual of** is
not an information source being used on its own; it is a fragment of an identity evaluated
outside the identity.

So `C3_ONLY > BASELINE` is a requirement the present decomposition's third route is
**structurally poorly placed to meet** — not because the coordination information is absent,
but because the object chosen to carry it is defined by subtraction. Its measured `-0.06%` is
consistent with that: near zero, slightly the wrong side.

**This makes the sharpened requirement an argument for the replacement decompositions, not
against the owner's ask.** Both candidates on record define three routes each of which is a
standalone quantity:

- **F** (fable): credited bits under the candidate's occupancy; resource energy under the
  candidate's activation; continuation. Pointwise parts-to-total `1.00x` at small sizes,
  `1.61x` at the grand row, against the incumbent's `1.57x`-`22.99x`.
- **A** (astra): local-link, temporal and relational innovations of `E[Y | I0, X_J]` where
  `Y = B - eta_ref*E`. Orthogonal increments, population RMS amplification bound `sqrt(3)`.

Under either, "each route alone" is a meaningful question with a meaningful answer. Under the
incumbent, for the third route, it is not.

## What does not follow

- **This does not authorise changing the incumbent decomposition** to make a sign come out
  right. The comparison metrics for the two candidates were fixed in
  `V025-CONTROLLER-PREDECLARATION-DECOMPOSITION-BAKEOFF-2026-09-10.md` before any exact row
  existed, and they are unchanged by this record.
- **It does not retract `FACTORIAL`.** Its numbers stand exactly as reported, including
  `+17.03%` for the joint span and both failing marginals.
- **It does not lower the training gate.** `V025-CONTROLLER-PREDECLARATION-TRAINING-GATE-2026-09-10.md`
  still requires the exact marginals to justify training and the target to be learnable.
- Every number above is a **ceiling** — exact terms, not learned predictions. A learned head
  recovers a fraction of it, and the one learned head measured today was one to two orders of
  magnitude mis-scaled.
