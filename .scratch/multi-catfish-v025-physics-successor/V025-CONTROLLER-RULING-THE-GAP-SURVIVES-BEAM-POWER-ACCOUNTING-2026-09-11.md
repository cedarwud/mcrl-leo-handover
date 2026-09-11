# Ruling — the gap survives every applicable beam-power accounting; the `max` operator was not carrying it

Date: 2026-09-11. Branch 1 of a reading declared **before** the measurement ran.
Source: `.scratch/beam-power-accounting/BEAM-POWER-ACCOUNTING-2026-09-11.md`; scripts and raw
output copied into `.scratch/beam-power-accounting/scripts/` (result JSON sha256 `47b2a9a0…`).

## Why this was run

ASK-2 ranked the simulator's `max`-over-users beam power as **the single highest
defensibility risk, and sign-changing**, on the grounds that the multiuser payload
literature sums user powers (Ha et al., GLOBECOM 2022). If the 19.8% result depended on
that operator, it would be a simulator counterexample, not a physics finding. Same frozen
actions, re-scored; no retraining.

## Result

| accounting | `MAX_NOMINAL_GAIN` EE | trained EE | ratio | separation | share of gap the operator explains |
|---|---:|---:|---:|---:|---:|
| `MAX` (current) | 111,504,571.39 | 93,110,907.97 | **1.1975** | 13.0 sem | — |
| `TDM_AIRTIME` | 112,139,763.26 | 94,111,458.32 | **1.1916** | 12.6 sem | 3.0% |
| `ADDITIVE` (stress bound, **not applicable to this PHY**) | 93,572,620.07 | 80,465,428.82 | **1.1629** | 10.0 sem | 17.5% |

Parity: the `MAX` column reproduces all four published figures bit-for-bit; recomputed
per-step power matches the environment's own to within 2.3e-13 W. Ordering of all four arms
is identical in every column.

## Why no accounting can flip it

**Only joules change between accountings; bits are identical by construction.**
`MAX_NOMINAL_GAIN` delivers **1.1468x** the trained checkpoint's bits in every column. An
accounting that made both arms' joules exactly equal would still leave it **14.7% ahead**.
The joule side can account for at most 5.1 of the 19.8 percentage points.

## ASK-2's recommended fix has the property ASK-2 criticised

Under `TDM_AIRTIME` — the accounting ASK-2 recommended — each beam's airtime sums to exactly
1, so the beam's draw is the **mean** of its users' draws, and an added user costs
`(P_DC(p_new) − mean) / (U_b + 1)`: **zero at the mean and negative below it.** Measured:
mean exactly 0 J, with 22.0% (rule) and 36.3% (trained) of users **negative**. Only
`ADDITIVE` charges every added user (+63.67 J / +64.55 J), and it is the one accounting this
PHY does not support.

**`ADDITIVE` does not apply here**, because the PHY is time-division within a beam: noise is
taken over the whole beam bandwidth while each user's rate gets `B/U_b`
(`step.py:214-217`, `link_budget.py:367-372, 590-616`); the code states the beam is
time-shared; and each beam has one power and one boresight with no per-user precoder
(`interference.py:119-152`). A genuinely additive PHY would also change interference and
therefore bits; that was not measured and its direction is unknown.

**So for this PHY the defensible accounting is `TDM_AIRTIME`, under which `max` overcharges
by ~0.6-1.1% of joules and moves the ratio by 3% of the gap.** ASK-2's "sign-changing"
ranking assumed a simultaneous-stream PHY; for a TDM beam it is **magnitude-only**. The
review's broader point — that `max` is not the standard multiuser model — stands and must
be stated in the thesis, with `TDM_AIRTIME` as the corrected accounting.

`TDM_AIRTIME` also slightly **favours the trained policy**, not the rule (joules −1.06% vs
−0.57%), because averaging cuts more where within-beam link powers vary more.

## What this settles and what it does not

**Settles:** the 19.8% result is not an artefact of the `max` operator. It is carried by the
numerator — 14.7% more bits from pointing at the highest-gain legal beam — and it survives
the applicable standard accounting at 12.6 sem.

**Revises:** the r3-premise argument. Under the corrected TDM accounting, adding a user to a
radiating beam still costs **zero joules on average** — so "occupancy has no power
derivative" holds under the standard-aligned accounting for this PHY too, not only under
`max`. The occupancy channel that does exist is the numerator (`R_beam = B · mean SE`), as
erratum 25 established.

**Does not settle:** that `r2` is the cause (ASK-3: not yet identified — needs the
factorial reward knockout); that the rule is the better policy overall (it does not
Pareto-dominate on handover rate); or external validity beyond this PHY.

## Standing of the headline, after two attacks

| attack | result |
|---|---|
| segment entry anchor (renewal premium) | ratio **1.1975 → 1.2222**, widened |
| standard beam-power accounting (`TDM_AIRTIME`) | ratio **1.1975 → 1.1916**, 3.0% of gap |
| stress bound (`ADDITIVE`, inapplicable) | ratio 1.1629, still 10.0 sem |
