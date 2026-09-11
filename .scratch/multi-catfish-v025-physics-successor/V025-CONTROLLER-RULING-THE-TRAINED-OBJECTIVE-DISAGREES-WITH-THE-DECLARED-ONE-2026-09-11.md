# Ruling — the trained objective and the declared primary objective disagree by 19.8% of pooled EE

Date: 2026-09-11. Branch 2 of a reading declared **before** the measurement ran.

## The pre-declaration being executed

From `V025-CONTROLLER-RULING-NO-DEMONSTRATOR-ON-THE-TRAINED-OBJECTIVE-2026-09-11.md`,
written before the pooled-EE numbers existed:

> **`MAX_NOMINAL_GAIN`'s pooled EE > the learner's** — then the trained objective and the
> declared primary objective disagree, and *that* is the paper's finding: a scalarisation
> whose handover term, which has no energy cost, drives the policy away from the declared
> objective. **It still does not reopen the demonstration line by itself.**

**Branch 2 occurred.**

## The measurement

Pooled EE = two running totals over 24 episodes x 10 steps, divided once. Bits and joules
are the environment's own per-step `system_throughput_bps` / `system_consumed_power_w`
(`trainer_env.py:239-248`, `energy_efficiency.py:37-49`), `dt = 30.08 s`
(`constants.py:76`). Numerator convention: **full-buffer Shannon, no demand cap**
(`link_budget.py:590-615` eq. 3.14, applied at `step.py:964-970`).

The trained arm ran at the **same** RNG stream positions 0-23 as every scripted arm; the
local `final-checkpoint.pt` is byte-identical to the frozen artefact
(`e6b063ef...1b09c28b`). **The stream-position caveat from the previous round is gone.**

| arm (n=24) | pooled bits | pooled joules | **pooled EE (bit/J)** | served | ho rate | scalar |
|---|---:|---:|---:|---:|---:|---:|
| `MAX_NOMINAL_GAIN` | 3.267020e+14 | 2.928666e+06 | **111,553,182.85** | 0.9981 | 0.7117 | −0.0867 |
| **trained `e6b063ef...`** | 2.850357e+14 | 3.060363e+06 | **93,137,893.02** | 0.9988 | 0.2796 | +0.9063 |
| `GREEDY_R1R2` | 2.612398e+14 | 3.445650e+06 | 75,817,283.47 | 0.9960 | 0.1413 | +0.8743 |
| `GREEDY_SCALARIZED` | 2.614246e+14 | 3.473047e+06 | 75,272,421.21 | 0.9961 | 0.1502 | +0.8649 |
| `RANDOM_MASKED` | 1.842866e+14 | 3.473162e+06 | 53,060,175.56 | 0.9360 | 0.8680 | −1.4104 |

Ratio **1.1977**, delta **+1.8415e+07 bit/J**, **13.2 sem**. Resolvable by a wide margin,
so the "not resolvable" branch does not apply.

## Why this is not an artefact

- **Not the estimand defect.** Episode-level mean-of-ratios and ratio-of-sums agree to
  **<= 0.06%** on every arm and no ordering depends on the choice. Three orders of
  magnitude too small to produce a 19.8% flip. (Not instrumented at the
  per-user-per-step level; not inferred across windows.)
- **Not a denominator effect.** `MAX_NOMINAL_GAIN` wins **both halves at once**: 1.146x
  the learner's bits *and* 0.957x its joules.
- **Not bought by dropping service.** Served 0.9981 vs 0.9988; every arm sits in
  0.936-0.9988.
- **It is a weighting disagreement.** Pooled EE prices `r1` and nothing else; the trained
  objective prices `0.5*r1 + 0.3*r2 + 0.2*r3`. `MAX_NOMINAL_GAIN` is **last** on the
  scalar and **first** on pooled EE; its handover rate is 0.7117 against the learner's
  0.2796. `r2` carries weight 0.3 in one and **zero** in the other.
- **The two arms that won on the trained objective are the worst non-random arms on
  pooled EE** (0.808x and 0.814x the learner). The scalarisation is not merely
  imperfectly aligned with EE; on this panel it is **anti-aligned**.

## Incidental finding, recorded

**Rate attainment has no referent in this environment.** A grep for
`demand_cap|rate_target|nominal_rate|setpoint|target_rate|min_rate|qos_rate` over
`src/mcrl/env/` returns **zero hits**. The V0.25 panel's 50 Mbit/s setpoint belongs to
different physics and was correctly not imported. Served rate is reported instead.

## What this does and does not license

**Does:** the project can state, on its own declared estimand, with a matched harness and
byte-identical frozen weights, that **a one-line rule beats the authenticated checkpoint
by 19.8% on pooled EE**, and that the gap is created by the `r2` term.

**Does not:** reopen the demonstration line. On the objective the learner is trained on,
no expressible arm reaches it — that closure stands and is unaffected.

## The danger, stated plainly

Three findings now point the same way — r2's premise is false in the power model, r3's
premise is false in the power model, and the scalarisation costs 19.8% of pooled EE. It
is very tempting to re-specify the objective, watch the demonstrator become admissible,
and call the demonstration line reopened.

**That is legitimate only under conditions that must be fixed now, before the decision:**

1. The r2/r3 re-specification is justified **from the power model alone**. R23HISTORY
   established both premises as false **before** this measurement existed and cited no
   training outcome; that is the record, and it is the only admissible basis.
2. **All current evidence resets.** A changed objective invalidates the frozen checkpoint
   as comparator, `code_sha256 = 544fcf07...`, `trainer_config_sha256 = b69f6f46...`,
   `prereg_digest = 3a920671...`, the frozen calibration scales, and every gate that
   reads the reward. Every arm is re-measured. This is a cost, not an obstacle — 3000
   episodes is 1.32 h.
3. The re-specification is **declared in full before any run**, including what each
   outcome will mean, and is not adjusted afterwards.
4. It goes to the **fresh-context cross-model reviewers** first. My previous framing was
   rejected six times out of six; I do not adjudicate my own proposal.

**The decision is the owner's, and it is a modelling decision about whether a handover
costs anything in this physics — not a decision about whether the demonstrator wins.**

## Addendum — the churn cost cannot be charged in either physics as they stand

SPECPROFILE was sent to re-score under the declared handover interruption, to test whether
the 62.502712 → 17.257910 trade-off was an artefact of not charging churn. **It stopped as
instructed, because the measurement does not exist.**

- The interruption is a **matrix treatment code**, `PhysicsSetting.interruption in
  {"off","on"}` (`matrix.py:24,34-35`), set by treatment letter (`matrix.py:79-90`). Ten
  of 31 declared settings are `"on"`. **The entire V0.25 development panel record is
  interruption-off**: all 12 anchors sit in cell `a-r0`, and so do BEAMCOUNT, CLEANPATH,
  CEILING2 and COORDVALUE.
- **The mandated dense path structurally cannot express it.**
  `batch.evaluate_ar_tdm_catalogue` has **no interruption parameter** at all (verified by
  `inspect.signature`) and never receives the event ledger; `evaluate_many` goes dense
  **only when the label is exactly `a-r0`** (`probe:798`) and otherwise falls back to
  scalar. Every interruption-on label is a different label. **In this engine, "dense
  batch" and "interruption on" are mutually exclusive — no code path has both.**
- Which constant applies: `same_satellite_beam_change` → 0.062 s, otherwise → 0.142 s
  (`integration.py:78-89`); initial entry and re-entry are skipped. Incidental defect
  found: `cell_rekey` maps to `same_satellite_beam_change` (`probe:743-758`), so a re-key
  is priced 0 in `Phi` yet opens a 0.062 s blackout. Not triggered on this panel. Both
  constants remain `VERIFY_SOURCE` / UNVERIFIABLE_HERE.

**None of the three pre-declared readings was reached.** No constant substituted, no
treatment approximated, no re-scoring, no winner re-selected. Every previously reported
figure stands unchanged, all `a-r0`, interruption off.

**Two things the declared code does lock:**

1. **Interruption moves the numerator only.** Joules accumulate outside the per-user loop
   (`integration.py:129`) and the blackout term is never deducted from them; only `bits`
   and `useful` carry `- removed_*` (`:151-152`). **Consistent with R23HISTORY's
   zero-joule finding, and it means churn can only ever cost bits, never energy.**
2. **Scale of the declared window** — derived arithmetic on frozen receipts, **not a
   measurement, not an upper bound, and explicitly not sufficient to claim the ranking is
   unchanged**: 0.062 s / 0.142 s are **0.2061% / 0.4721%** of the 30.08 s interval.
   Over 36,096 user-seconds: incumbent 0%, budgeted arms ~0.1374%, base 0.1397%,
   `RSS_MAX` 0.3625%, search winner 0.3880%, declared rule 0.3929%. **Largest cross-arm
   difference 0.2506 pp.** Unverified premise: this equates a bit fraction to a time
   fraction, which holds only if a user's rate over the first 0.142 s equals their 30.08 s
   average; a front-loaded profile makes the loss larger and is not bounded here.

**Two ways to make it measurable, both owner decisions, neither costed:**
**(a)** add a per-user blackout parameter to `evaluate_ar_tdm_catalogue`, separate dense
`useful_time_s` from `decoding_time_s`, and widen the label gate — preserves the evaluator
rule and every parity target, but touches the engine, so it needs a versioned successor.
**(b)** run scalar `a-r0` and scalar `a-rH` over the same 12 anchors and 7 configurations
and report the **scalar-to-scalar difference**, differencing out the discontinuity
mechanism — no engine change, exact, but needs an explicit exemption from the mandatory
evaluator rule and the non-batch path is far more expensive. **SPECPROFILE recommends (b).**

### What this does to the MODQN finding above

In the MODQN physics there is **no interruption term at all**, and handover consumes zero
joules. **So churn there is genuinely free**, and the 19.8% pooled-EE gap cannot be
explained by an unaccounted cost of `MAX_NOMINAL_GAIN`'s 0.7117 handover rate — within
that physics, there is nothing for it to cost.

That is what makes this a **physics-completeness** question rather than a reward-tuning
one: the V0.25 successor engine models a handover cost as **lost bits in the numerator**;
the MODQN engine models it as **a preference term in the reward**. Only the first is
physically grounded, and it is the one MODQN does not have.

## Two defects that must be fixed regardless of which way that decision goes

Both from R23HISTORY, both independent of the objective question:

1. **An outage is the maximum of both bounded heads** — r2 = 0 and r3 = 0 when unserved,
   while every served step is <= −1 for r3 and <= 0 for r2. Power-infeasible steps are not
   no-ops; they enter replay carrying that free ride.
2. **The logged `scalar_reward` is uncalibrated** (`modqn.py:1302`) while training uses
   the calibrated vector (`:1269`). The headline curve is numerically `0.5 * r1`; r2 and
   r3 move it by one part in 10^6. **Every judgement ever made from that curve saw only
   r1.**
