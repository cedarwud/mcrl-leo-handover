# Ruling — the 19.8% gap survives the segment-anchor ablation and widens to 22.2%

Date: 2026-09-11. Branch 2 of a reading declared **before** the measurement, in
erratum 25's moot test.

## Result

**Anchored ratio 1.1975 → ablated ratio 1.2222.** The renewal premium is not the
explanation. The disagreement is real, restated at **+22.2%**.

| physics | arm | pooled bits | pooled joules | **pooled EE** | served | ho |
|---|---|---:|---:|---:|---:|---:|
| `none` | `MAX_NOMINAL_GAIN` | 3.266731e+14 | 2.929683e+06 | 111,504,571.39 | 0.9981 | 0.7120 |
| `none` | trained `e6b063ef...` | 2.848622e+14 | 3.059385e+06 | 93,110,907.97 | 0.9988 | 0.2799 |
| **`ablate_anchor`** | `MAX_NOMINAL_GAIN` | 3.262056e+14 | 2.896868e+06 | **112,606,306.11** | 1.0000 | 0.7105 |
| **`ablate_anchor`** | trained `e6b063ef...` | 2.845606e+14 | 3.088655e+06 | **92,130,894.38** | 1.0000 | 0.2825 |

Gap +1.839e+07 (13.0 sem) → +2.048e+07 (14.3 sem), **11.3% larger**.

## Why the review's mechanism is real but is not the cause

The asymmetry the reviewer named is **confirmed and live**: under anchored physics
`MAX_NOMINAL_GAIN` sits at `p0` for **70-76%** of served users while the trained policy
sits at `p0` for only **4-5%** and pays up to 1.63 W.

But removing it entirely moves nothing, because **the gap is carried by the numerator**:

| | bits ratio MAX/TRAINED | joules ratio | EE ratio |
|---|---:|---:|---:|
| anchored | 1.1468 | 0.9576 | 1.1975 |
| ablated | **1.1463** | 0.9379 | 1.2222 |

**The bits ratio is invariant to the ablation to within 0.05%.** `MAX_NOMINAL_GAIN`
delivers ~14.6% more bits by pointing at the highest-gain legal beam — **a property of
the decision rule, not of the power recurrence.** The anchor lives wholly in the
denominator, and equalising transmit power at `p0` **widens** the joules ratio.

Per-arm effects run **opposite** to the prediction: MAX **+0.99%**, TRAINED −1.05%,
`GREEDY_R1R2` −1.27%, RANDOM −2.75%. Removing the anchor **helps** the high-churn arm and
**hurts** the three lower-churn ones.

diag2's cited result remains correct on its own terms: forced renewal **at fixed
association** gains +0.49% anchored and exactly zero ablated. `MAX_NOMINAL_GAIN` is not
that arm — **it changes *which* beam, not merely *when* the anchor resets.** That is the
step the extrapolation skipped, mine included.

## Method quality, recorded because it is what makes the result usable

- **The ablation is diag2's, reused not invented** — declared verbatim at
  `codex-sol-c3s-churn-null.md:16`, implementation fetched read-only
  (`c3s_physics_override.py`, sha256 `a5342447...78f03a`, 137 lines), applied through its
  own subclass factory. It ports unchanged because it is written against this repo's own
  `mcrl.env.step.StepEnvironment`. Only one ablation is specified, so there was no choice
  to make.
- **Positive control**: under `ablate_anchor`, **100.0% of served users transmit at
  exactly `p0` = 0.825 W**, every step, both arms.
- **Placebo**: `none` through the wrapper reproduces `RANDOM_MASKED` bit-identically
  (MAX −0.044%, TRAINED −0.029%).
- **A confound in its own prior section was found and fixed**: `_age_rng` spawns once and
  carries across arms (`step.py:534-536`), so the earlier shared-env run gave later arms
  different segment-age draws. Every cell here builds a fresh env. Effect <= 0.044%,
  disclosed rather than buried.
- **Limit flagged, not buried**: the ablation raises served to 1.0000 for every arm
  (pinning `p` at `p0` removes power infeasibility), so the two columns are **two
  operating points, not a decomposition**. It does not threaten the reading — the ablated
  comparison is between two arms at **identical full service and identical uniform
  transmit power**, and the gap is larger there.

## Standing of the three objections in erratum 25

- **Objection 1 stands.** My replacement term closes 1.2% of the gap; the proposal cut the
  handover price ~290x. The re-specification remains **rejected**.
- **Objection 2 stands.** My r3 algebra was wrong: `R_beam = B * mean SE`, not
  U-invariant; and interference is z-gated and load-unweighted. `r3 = −U` is still the
  wrong instrument, on grounds that are not mine.
- **Objection 3 is refuted empirically.** The segment anchor is real, is live, and is
  **not** what produces the gap.

## What is now established

On the project's own declared estimand, with a matched harness, byte-identical frozen
weights, a positive control, a placebo, and after ablating the strongest proposed
artefact: **a one-line rule beats the authenticated trained checkpoint by 22.2% on pooled
EE, at identical service, by delivering 14.6% more bits.** The learner does not do this
because `r2` penalises the handovers it requires, and `r2` prices something that costs
zero joules in this physics.

**The trained objective and the declared primary endpoint disagree, and the disagreement
is a property of the objective, not of the simulator's power recurrence.**

## The decision this forces, which is the owner's

The reviewer's own recommendation, conditional on exactly this outcome: **if the gap
survives, fix the endpoint declaration — pooled EE subject to handover and service
constraints (the CMORL formulation this project's outside review already recommended) —
not the reward.** The gap survived.

That is a change to a **declared endpoint**. It is not mine to make, it resets evidence,
and it must be declared in full before anything runs. Put to the owner; nothing acted on.
