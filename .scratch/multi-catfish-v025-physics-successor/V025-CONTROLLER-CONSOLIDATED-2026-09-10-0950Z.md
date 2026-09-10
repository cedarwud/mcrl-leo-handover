# Consolidated position — 2026-09-10 09:50 UTC

**Every number below carries four fields: reference / information class / estimand /
numerator. A number that cannot carry all four is not reported.** This rule exists because
all six of today's retractions were numbers reported without them.

---

## 1. What stands

**C1's declared target is weakly learnable for ordering, and not for level or choice; the
ceiling looks informational.** `C1REAL`, exact declared target `c1_difference_surplus` built
on the dormant exact branch (flag set on the imported module object, file unedited).

| statistic | sealed `(8,)` head | flexible nonlinear, same 16 slots | floor |
|---|---:|---:|---:|
| LOAO ordering | `0.5889` `[0.5658, 0.6115]` | `0.6197` | `0.5` |
| LOAO level `R^2` | **`-0.2724`** `[-0.5750, -0.0435]` | `0.0933` | — |
| top-1 accuracy | `0.1711` | `0.1854` | **`0.1716`** |
| LOWO level `R^2` | — | **`-0.0714`** | — |

*ref: held-out anchors and worlds · info: nominal, decision-time only · estimand: declared
`c1_difference_surplus` · numerator: n/a, this is prediction quality not EE.*

A high-capacity model on the same inputs also fails, and widths 32 and 128 do not improve
reliably. **The binding constraint is the information in the 16 slots, not the architecture,
the epoch count or the seed.** Consistent with `PREFLIGHT-DATA-CENSUS`: two slots are exactly
constant, slots 4 and 12 are exact indicators of 3 and 11, the design matrix has rank 14, the
effective input dimension is 12, and **there is no elevation feature at all**.

**The only measured contrast between the learned routes and neutral-source training is
negative.** `FULL - ALL_NEUTRAL_CONTROL = -0.01745324091886997`, identically under both
provisioning rules. *ref: `ALL_NEUTRAL_CONTROL` · info: as-run panel smoke · estimand: relative
pooled-EE marginal · numerator: pooled EE.* Confirmed by digest-checked read of
`.scratch/c3-panel-smoke-r8/smoke.json` by two independent reviewers and one receipt-only check.

**The corrected coordination span.** `+1.29%` (20 anchors) and `+0.899%` (8 anchors).
*ref: correctly-paired unilateral fixed point · info: nominal, strict clearance · estimand:
exact set residual · numerator: pooled EE.* The 30-date interval `[+0.436%, +0.997%]` is
**old-pairing** and must never be cited as this span's interval.

**Clean negatives.** Occupancy floor `-7.66x`; ladder floor `+6.36% -> +0.51%`.

**Structural facts.** All 176,223 shipped source rows carry `kappa*tanh(log ratio)`
surrogates, not the declared targets. The sealed checkpoint format admits five learned arms,
2,000 epochs, cadence 100, round-trip verified, resume bit-exact. `MARGIN_Q` was never
engaged by the panel bridge. Scalar `evaluate` and dense `evaluate_many` disagree; global
authority `UNDETERMINED`.

---

## 2. What is retracted or not established

| | status |
|---|---|
| `FULLSPAN` `+17.03%` / `+10.80%` | **retracted** — reference vacuous, selector clairvoyant |
| `FACTORIAL` "4 of 6 pass" | **retracted** — its C1/C2/C3 are not the contract's routes |
| `RESIDTOGGLE` `+5.62%` vs the 10%/5% screens | **retracted** — same construction |
| `9.8698%` multi-start | **retracted** — order statistic, defective rule |
| `+78.02%` causal mode selection | **retracted** — carrier base `3.89` Mbit/J, does not transfer |
| `+119%` / `+134%` control law | **retracted** — non-causal, best-known, undeflated |
| `22.99x` conditioning, `+480/-440/+40` | **not established** — inside the mixed-path artefact envelope: sampled `abs(99*epsilon)` spans `127.2` to `2107.1` kappa, and `abs(Psi) = 440.079` sits inside it, with step 16 matching both magnitude (`-440.93`) and sign |
| "an exact marginal upper-bounds a learned one" | **false** — my own `PARAMETRISATION` record shows replacing either learned half by its exact counterpart **worsens** selection regret, `3.618 -> 9.043` / `9.647`; contract v1.2 item 3 explicitly permits it |

---

## 3. What this means

The three-route conjunction has **never** been measured against neutral-source training
except once, and that once is `-1.75%`. Everything else measured today used the carrier
incumbent as reference, and `repair_reference` gives every arm the same exact-surplus seed, so
that reference cannot separate arms at all.

Separately, the first route's declared target is not usefully learnable from the declared
features. That is a **feature** finding, not an architecture finding, and no amount of
training changes it.

**Both audits independently ranked the same item first.** They were run in parallel, in
separate workspaces, neither shown the other's output.

---

## 4. Where the work goes

1. **The contrast that has never been run**: routes versus neutral-source training, at a
   reference that can separate arms. Nothing else settles the claim.
2. **The feature schema** is the binding constraint on C1. Two dead slots, rank 14, no
   elevation. This is on the owed-repair register and has been since 07:00.
3. **`D1` cannot be decided on conditioning** now that `22.99x` is not established. The
   bake-off's pre-declared metrics stand, but its premise needs re-deriving on a
   path-consistent basis.
4. **The training gate must be rewritten** without the ceiling premise.

`OBJMISMATCH` is the only job still running, at 5h41m.
