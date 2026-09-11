**The `CAP_050` search winner (62.502712 Mbit/J, 1200/1200 served, 354/1200 attaining) performs 0.975000 handovers and 0.839167 κ of Φ-priced handover cost per user-step; it PASSES the complete-service guard against both references (+50.75 pp [+36.42, +63.67] against the geometric base, +50.42 pp [+36.17, +63.50] against the declared incumbent) and FAILS both handover guards against both references (against the base: handover rate +200.77 % [+69.08, undefined], Φ cost +180.50 % [+57.05, undefined], threshold +5 %; against the incumbent: `FAIL_UNDEFINED_DENOMINATOR` by the sealed zero-baseline rule, the incumbent having zero handovers by construction) — and the constrained version that passes all three guards against the base reaches only 17.257910 Mbit/J, 1001/1200 served, 192/1200 attaining, giving up 45.244802 Mbit/J, 72.389 % of the specialist's EE.**

# SPECPROFILE — the non-EE behaviour of the strongest non-learned configuration on the V0.25 development panel

`DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM.` **Learner-free: no checkpoint, learner output, or loss
value was read.** Only the 12 frozen development anchors were read; **no evaluation-only claim
date was read.** No sealed artefact and no physics was changed. All work is under
`/home/sat/mcrl-v025-specprofile-ws`.

## Naming and reference class (erratum 23)

The label `GAIN_IN_SET` was applied to this configuration **after the fact** by the task brief; it
does not appear anywhere in `/home/sat/mcrl-v025-beamcount-ws`. Throughout this report the
configuration is called **the `CAP_050` search winner**. It is *not* a declared rule:
BEAMCOUNT selected it on **boundary-0 EE** from nine declared rules plus a bounded
first-improvement local search plus the inherited winners of every smaller cap. Its per-anchor
`winner_start` is `RSS_MAX_within_cap` (polished) at step 0 and `INHERITED_CAP_030_WINNER` at
steps 1–3, identically for all three carriers (**verified by reading the frozen shard receipts**).

The **strongest declared rule** at C = 50 is a different object and is profiled separately below:
`S2_descending_coverage | A2_max_nominal_gain` — descending-coverage beam set, max-nominal-gain
assignment within it — at **52.042303 Mbit/J, 1200/1200 served, 303/1200 attaining**.

**This is a statement about the V0.25 decision problem only.** V0.25 options are global
`(norad_id, cell_id)` pairs over 9 satellites and 370 distinct legal beams (**verified by running
code**, and matching BEAMCOUNT's per-step census), with the active beam set an explicit capped
decision variable. That the MODQN sibling's activation is derived rather than chosen and carries
no cap is **transcribed from the companion audit via the controller and not re-verified here**;
on that basis the two do not share an action space, and none of the handover or Φ figures here
transfer to that setting.

## Reporting conventions — the four fields on every number

- **Reference**: the 12 frozen V0.25 development anchors, `V025_PROBE/world/1`, steps 0–3 ×
  {`nearest-eligible`, `stay-if-possible`, `random-masked`}; current V0.25 `a-r0` physics;
  realised field; **all 48 within-step boundaries**.
- **Information class**: development-anchor, non-evaluation, learner-free. Where a constrained
  arm was constructed by search, selection used boundary 0 only; **every EE, service, attainment,
  complete-service and Φ figure reported below is the full-48 endpoint.**
- **Estimand**: pooled EE = `sum(bits) / sum(joules)` over the anchors in scope, never a mean of
  per-anchor EEs. Handover rate and Φ cost are `sum(events) / sum(user-steps)` and
  `sum(Φ) / sum(user-steps)`, 100 user-steps per anchor, full roster in every denominator.
- **Numerator**: saturated full-buffer successfully decoded forward-downlink information bits,
  **no demand cap**.
- **Served and attainment appear beside every EE figure.** Attainment is against the nominal
  50 Mbit/s power-control setpoint, which declaration v1.1 permits partial delivery against, so a
  low attainment is not a contract violation but must be read beside the EE.

Evidence is marked **verified by running code**, **verified by reading primary source**,
**transcribed**, **derived**, or **inferred**.

## Declared definitions used (verified by reading primary source)

- **Event classification** — `targets.classify_physical_transition`, classified on the physical
  NORAD/beam chain, never the action slot: `satellite_change` when the NORAD id differs,
  `beam_change` when only the beam differs, `cell_rekey` when neither differs but the cell was
  re-keyed, `initial_entry` / `reentry` when there was no prior assignment, `exit` when there is
  no new one, else `unchanged`.
- **Φ pricing** — `constants_v025.PHI_SAME_SATELLITE = 0.5`, `PHI_SATELLITE_CHANGE = 1.0`
  (dimensionless multiples of κ, explicitly "not joules or seconds"), applied by `targets.phi_qos`.
  A `cell_rekey` and an `initial_entry` / `exit` are priced 0 and are not handovers.
- **Complete-service availability** — the producer is
  `run_v025_matrix_probe._arm_row`: the count of roster users whose `decoding_time_s` equals the
  full decision interval `DECISION_INTERVAL_S = 30.08 s` exactly (`abs_tol = 1e-9`), over the full
  roster of 100.
- **The guard** (`V025-CONTROLLER-DECISIONS-STAGE2-2026-09-08` item 6) — non-inferior when the
  95 % cluster-bootstrap interval of (arm − reference) lies **above −0.5 pp** for complete-service
  availability, and the interval of the **relative** change lies **below +5 %** for both the
  handover rate and the Φ-priced handover cost per user-step.
- **Zero baseline** (`V025-CONTROLLER-DECISIONS-STAGEC-SPEC-2026-09-08` item 11,
  `ZERO-QOS-BASELINE`) — reference event count zero and arm positive ⇒
  `FAIL_UNDEFINED_DENOMINATOR`; both zero ⇒ non-inferior by rule.
- **Incumbent** — `runner._base_configuration(tape, max(0, step − 1), carrier)`, the carrier's
  committed assignment at t−1, which is exactly the `transition_from` of every evaluator here.

### Three structural facts about this panel that shape every event count

**Verified by reading primary source and confirmed by running code.**

1. **There are no cell re-keys.** `_rekeyed_users` returns `()` whenever the step exposes
   primitive arrays, which the frozen exact panel always does. The re-key column is 0 at all 12
   anchors for every arm, so the "priced 0, counted separately" branch of EVENT-QOS is exercised
   with a count of zero and never affects a verdict.
2. **There are no re-entries, initial entries or exits.** `_physical_events` passes
   `was_previously_served = (before is not None)`, so the `reentry` branch of
   `classify_physical_transition` is unreachable from this call path; and on this panel the
   carrier base has **0 null users at every anchor**, and every incumbent identity remains legal
   at t, so `initial_entry` and `exit` are both 0 everywhere. Every event on this panel is a
   `beam_change`, a `satellite_change`, or `unchanged`. The re-entry pricing clause of EVENT-QOS
   is therefore **untested here**, not confirmed.
3. **At step 0 the declared incumbent is the same-step base.** `max(0, step − 1)` makes the
   incumbent at step 0 the step-0 carrier base, so at 3 of the 12 anchors the base reference has
   **zero handovers by construction**. Combined with the `stay-if-possible` carrier (which by
   definition holds its assignment) this leaves **7 of 12 anchors with a zero-handover base
   reference**: steps 0 (all three carriers), 1 `stay-if-possible`, 2 `stay-if-possible`,
   3 `nearest-eligible`, 3 `stay-if-possible`. This is why the bootstrap intervals below carry
   undefined upper endpoints, and why a steps-1–3-only sensitivity is reported.

## Mandatory gates

### Parity — passed at the full-48 endpoint, reported before anything else

**Verified by running code.** Every arm was rebuilt from the exact user→beam mapping recovered
from the frozen BEAMCOUNT shard receipts' `configuration_id` strings and **rescored from scratch**
on a fresh full-48 realised dense evaluator. Pooled over the same 12 anchors:

| Required value | Target | Measured (full 48) | Served | Attaining |
|---|---:|---:|---:|---:|
| `CAP_050` search winner pooled EE | 62.502712 Mbit/J | **62.502712 Mbit/J** | 1200/1200 | 354/1200 (29.500 %) |
| `RSS_MAX` pooled EE | 41.621560 Mbit/J | **41.621560 Mbit/J** | 1200/1200 | 297/1200 (24.750 %) |
| geometric base (`BASE`) pooled EE | 11.027760 Mbit/J | **11.027760 Mbit/J** | 960/1200 | 127/1200 (10.583 %) |
| strongest declared rule at C = 50 | 52.042303 Mbit/J | **52.042303 Mbit/J** | 1200/1200 | 303/1200 (25.250 %) |

To the six decimals of the published values, all four reproduce. **62.502712 is a full-48
endpoint figure, not a boundary-0 figure**; what was done at boundary 0 was the *selection* among
candidates, not the scoring. Every guard verdict in this report is computed on full-48 endpoint
profiles.

The boundary-0 selection warning is nonetheless real and is quantified here rather than assumed:
a **matched-budget unconstrained polish** of the search winner (the same first-improvement
boundary-0 search, 4 passes, full legal option set) **raises boundary-0 EE and lowers the full-48
endpoint**, from 62.502712 to **59.516177 Mbit/J** (1200/1200 served, 432/1200 attaining). More
boundary-0 search buys less full-48 EE.

### Evaluator rule — passed

**Verified by running code.** `StepEvaluator.evaluate` was replaced class-wide by a counting,
raising stub before any measured work, in all three processes. Construction of every constrained
arm ran inside **one fresh dense `StepEvaluator(field="realised", boundary_indices=(0,))` per
anchor**, with the carrier `BASE` **and** the held incumbent submitted in the first
`evaluate_many` batch alongside the candidates; profiles were read only from
`StepEvaluator._evaluated`. Endpoints used **one separate fresh realised dense full-48
`StepEvaluator(boundary_indices=range(48))` per anchor**, populated by exactly one
`evaluate_many` call. **All three processes ended with `scalar_evaluate_calls = 0` and printed
`PASS: zero scalar StepEvaluator.evaluate calls`.** No foreign cache was used: the BEAMCOUNT
receipts supplied only mappings (as text), never profiles.

## The profile — pooled over the 12 anchors, full-48 endpoints

**Verified by running code.** `ho/us` is handover events per user-step; `Φ/us` is Φ-priced
handover cost per user-step in multiples of κ. Events are against the declared incumbent at t−1.
There were zero `cell_rekey`, `initial_entry`, `reentry` and `exit` events in every row.

| Arm | pooled EE (Mbit/J) | served PHY | complete service | attaining | beam changes | satellite changes | ho/us | Φ/us (κ) | active beams |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| declared incumbent, held | 10.325892 | 929/1200 | 232/1200 | 115/1200 | 0 | 0 | 0.000000 | 0.000000 | 57.50 |
| geometric base (`BASE`) | 11.027760 | 960/1200 | 228/1200 | 127/1200 | 60 | 329 | 0.324167 | 0.299167 | 57.33 |
| `RSS_MAX` | 41.621560 | 1200/1200 | 333/1200 | 297/1200 | 475 | 714 | 0.990833 | 0.792917 | 47.75 |
| **strongest declared rule** (S2\|A2) | 52.042303 | 1200/1200 | 708/1200 | 303/1200 | — | — | 0.979167 | 0.848750 | 32.75 |
| **`CAP_050` search winner** | **62.502712** | **1200/1200** | **837/1200** | **354/1200** | **326** | **844** | **0.975000** | **0.839167** | 23.25 |
| search winner, matched free polish | 59.516177 | 1200/1200 | 540/1200 | 432/1200 | 346 | 818 | 0.970000 | 0.825833 | 40.50 |
| search winner, satellite lock | 43.818876 | 1197/1200 | 505/1200 | 357/1200 | 1109 | 0 | 0.924167 | 0.462083 | 38.58 |
| search winner, handover budget vs base | 17.257910 | 1001/1200 | 520/1200 | 192/1200 | 65 | 321 | 0.321667 | 0.294583 | 38.83 |
| search winner, zero handover | 10.325892 | 929/1200 | 232/1200 | 115/1200 | 0 | 0 | 0.000000 | 0.000000 | 57.50 |

**The headline non-EE facts.** The search winner moves **1170 of 1200 users** at the decision
instant — 0.975 handovers per user-step — and **72 % of those moves change satellite**
(844 satellite changes against 326 beam changes), which is why the Φ price per user-step,
0.839167 κ, is close to the raw rate. It is not merely "more handovers than the base": it is
**three times** the base's rate (0.324167) and nearly **as many handovers as there are users**.

**The one place it is better than every reference is complete service.** 837/1200 complete-service
user-steps against 228 for the base and 232 for the held incumbent, and 1200/1200 PHY-served
against 960 and 929. The availability guard is not what it fails.

### Per anchor — the `CAP_050` search winner

**Verified by running code.** Carrier invariance holds for a fixed mapping: the full-48 endpoint
is identical across the three carriers at each step, so the EE column repeats in blocks of three;
the *event* columns differ by carrier because the incumbent differs.

| Anchor | EE (Mbit/J) | served | complete | attaining | beam ch. | sat ch. | ho/us | Φ/us (κ) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 nearest-eligible | 76.593772 | 100 | 28 | 40 | 77 | 21 | 0.98 | 0.595 |
| 0 stay-if-possible | 76.593772 | 100 | 28 | 40 | 77 | 21 | 0.98 | 0.595 |
| 0 random-masked | 76.593772 | 100 | 28 | 40 | 18 | 81 | 0.99 | 0.900 |
| 1 nearest-eligible | 64.901158 | 100 | 84 | 31 | 5 | 94 | 0.99 | 0.965 |
| 1 stay-if-possible | 64.901158 | 100 | 84 | 31 | 5 | 94 | 0.99 | 0.965 |
| 1 random-masked | 64.901158 | 100 | 84 | 31 | 19 | 75 | 0.94 | 0.845 |
| 2 nearest-eligible | 61.165544 | 100 | 77 | 32 | 29 | 70 | 0.99 | 0.845 |
| 2 stay-if-possible | 61.165544 | 100 | 77 | 32 | 14 | 85 | 0.99 | 0.920 |
| 2 random-masked | 61.165544 | 100 | 77 | 32 | 19 | 78 | 0.97 | 0.875 |
| 3 nearest-eligible | 50.120026 | 100 | 90 | 15 | 39 | 54 | 0.93 | 0.735 |
| 3 stay-if-possible | 50.120026 | 100 | 90 | 15 | 3 | 97 | 1.00 | 0.985 |
| 3 random-masked | 50.120026 | 100 | 90 | 15 | 21 | 74 | 0.95 | 0.845 |

The handover rate never drops below 0.93 at any anchor for any carrier. There is no anchor at
which this configuration is quiet.

## The guard verdicts

**Verified by running code.** 10,000-resample cluster bootstrap, seed 20260911, percentile
interval [2.5 %, 97.5 %], clusters = the 12 anchors. Intervals are of (arm − reference) in
percentage points for complete-service availability and of the **relative** change in per cent
for the two handover quantities. `undef` marks an upper endpoint that is undefined because some
resamples draw only anchors whose reference event count is zero — for the base-referenced rows
that is **20 of 10,000 draws**, and the *lower* endpoint already lies far above +5 %, so the
verdict is unambiguous.

### Arm = `CAP_050` search winner

| Guard | Reference = declared incumbent | Reference = geometric base |
|---|---|---|
| complete-service availability (> −0.5 pp) | **+50.4167 pp** [+36.1667, +63.5000] → **PASS** | **+50.7500 pp** [+36.4167, +63.6667] → **PASS** |
| handover rate, relative (< +5 %) | reference is 0 by construction → **FAIL_UNDEFINED_DENOMINATOR** | **+200.77 %** [+69.08, undef] → **FAIL** |
| Φ-priced cost per user-step, relative (< +5 %) | reference is 0 by construction → **FAIL_UNDEFINED_DENOMINATOR** | **+180.50 %** [+57.05, undef] → **FAIL** |

### Arm = strongest declared rule (S2 | A2)

| Guard | Reference = declared incumbent | Reference = geometric base |
|---|---|---|
| complete-service availability | **+39.6667 pp** [+29.2500, +50.4167] → **PASS** | **+40.0000 pp** [+30.0833, +50.0833] → **PASS** |
| handover rate, relative | **FAIL_UNDEFINED_DENOMINATOR** | **+202.06 %** [+70.95, undef] → **FAIL** |
| Φ-priced cost, relative | **FAIL_UNDEFINED_DENOMINATOR** | **+183.70 %** [+61.01, undef] → **FAIL** |

### Stated plainly

**No, the specialist does not satisfy every declared co-primary outcome.** Against the declared
incumbent it fails both handover guards by the sealed zero-baseline rule; against the geometric
base it fails both by roughly a factor of three on rate and a factor of 2.8 on Φ price. It passes
the complete-service guard comfortably against both. **The gap the design proposal points at is
real, and it is entirely a handover-cost gap, not an availability gap.**

The verdict does not depend on the reference-class correction: **all nine declared C = 50 rules
fail both handover guards as well**, and two of them also fail the availability guard.

| Declared rule at C = 50 | pooled EE | served | complete | attaining | ho/us | Φ/us (κ) | complete-service | handover | Φ |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| S2 desc. coverage \| A2 max gain | 52.042303 | 1200 | 708 | 303 | 0.979167 | 0.848750 | PASS +40.00 pp | FAIL +202.06 % | FAIL +183.70 % |
| S3 desc. gain \| A2 max gain | 52.024243 | 1200 | 792 | 411 | 0.987500 | 0.844167 | PASS +47.00 pp | FAIL +204.63 % | FAIL +182.17 % |
| S1 asc. coverage \| A2 max gain | 40.595657 | 1200 | 1005 | 33 | 0.976667 | 0.922083 | PASS +64.75 pp | FAIL +201.29 % | FAIL +208.22 % |
| S3 desc. gain \| A1 coverage first | 26.821230 | 1197 | 546 | 216 | 0.970833 | 0.876667 | PASS +26.50 pp | FAIL +199.49 % | FAIL +193.04 % |
| S3 desc. gain \| A3 least loaded | 25.550758 | 1185 | 219 | 207 | 0.961667 | 0.838333 | FAIL −0.75 pp | FAIL +196.66 % | FAIL +180.22 % |
| S2 desc. coverage \| A3 least loaded | 20.344485 | 1134 | 180 | 102 | 0.928333 | 0.822500 | FAIL −4.00 pp | FAIL +186.38 % | FAIL +174.93 % |
| S2 desc. coverage \| A1 coverage first | 19.205699 | 1161 | 519 | 183 | 0.970000 | 0.889167 | PASS +24.25 pp | FAIL +199.23 % | FAIL +197.21 % |
| S1 asc. coverage \| A1 coverage first | 17.478088 | 1170 | 606 | 162 | 0.972500 | 0.917083 | PASS +31.50 pp | FAIL +200.00 % | FAIL +206.55 % |
| S1 asc. coverage \| A3 least loaded | 16.674991 | 1137 | 543 | 180 | 0.965833 | 0.912083 | PASS +26.25 pp | FAIL +197.94 % | FAIL +204.87 % |

All contrasts in that table are against the geometric base. `RSS_MAX` fails the same way:
+205.66 % [+72.01, undef] handover, +165.04 % [+49.91, undef] Φ, and it also **fails** the
availability guard, +8.7500 pp [−0.5854, +19.0000] — its lower endpoint sits just below −0.5 pp.

### Sensitivity — clustering by physical step

**Verified by running code.** Because a fixed mapping scores identically across carriers at a
step, the 12 anchors carry only 4 independent physical steps for the arm side (the reference side
does differ by carrier). Re-clustering the bootstrap on the 4 physical steps changes no verdict:
search winner versus base becomes complete-service +50.7500 pp [+27.5833, +67.8333] PASS,
handover +200.77 % [+74.25, undef] FAIL, Φ +180.50 % [+72.45, undef] FAIL. Treat the panel's
effective sample size as 4, not 12.

### Sensitivity — steps 1–3 only

**Verified by running code.** Dropping the three step-0 anchors, where the incumbent is the
same-step base by construction, leaves 9 anchors. Pooled: the search winner is 58.423324 Mbit/J
(900/900 served, 234/900 attaining), 0.972222 ho/us, 0.886667 κ Φ/us; the base is 10.967040
(732/900 served, 85/900 attaining), 0.432222 ho/us, 0.398889 κ. The relative handover excess is
+124.9 % and the Φ excess +122.3 % — smaller than on the full panel, because the surviving
reference is noisier rather than quieter, but still an order of magnitude past the +5 % threshold.

## What EE has to be given up to pass

Two constraints were run, both re-scoring the same configuration family under a stated
restriction that enforces the failed guard.

### Constraint A — satellite lock (the brief's worked example)

Each user is restricted to legal options **on its incumbent's satellite**; the same
max-nominal-gain assignment is applied inside that set and then polished by the same bounded
boundary-0 first-improvement search. **Every user had exactly 7 legal options on its incumbent's
satellite at all 12 anchors** (against 28 legal options unrestricted), so **no user was exempted**
in either pass.

**This removes every satellite change but does not pass.** The search winner under satellite lock
reaches **43.818876 Mbit/J (1197/1200 served, 357/1200 attaining, 505/1200 complete service)**,
with 1109 beam changes and **0 satellite changes**. Φ per user-step falls from 0.839167 κ to
0.462083 κ — a 44.9 % reduction, close to the 50 % that the Φ₁/Φ₂ ratio implies — but the
**handover rate barely moves** (0.975000 → 0.924167), because a satellite lock changes the
*price* of a move, not whether one happens. Verdict against the base: complete-service
+23.0833 pp [+15.5833, +30.8333] PASS, handover **+185.09 % [+56.30, undef] FAIL**, Φ
**+54.46 % [−14.27, undef] FAIL**. Cost: −29.9 % of EE for a guard it still fails. The declared
rule behaves the same way (52.042303 → 29.016715 Mbit/J, −44.2 %, still FAIL on both).

### Constraint B — a per-anchor handover and Φ budget (the constraint that passes)

Starting from the held incumbent (zero handovers), users are admitted to their target assignment
in descending order of boundary-0 marginal EE, subject at **every anchor** to
`handovers ≤ floor(1.05 × reference handovers)` and `Φ ≤ 1.05 × reference Φ`. Because the
constraint binds anchor-by-anchor, the pooled relative excess is ≤ +5 % in **every** bootstrap
resample, so the guard is satisfied by construction and then verified empirically.

| Arm | pooled EE (Mbit/J) | served PHY | complete service | attaining | ho/us | Φ/us (κ) | complete-service guard | handover guard | Φ guard |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| search winner, budget vs base | **17.257910** | **1001/1200** | 520/1200 | **192/1200** | 0.321667 | 0.294583 | **PASS** +24.3333 pp [+5.9167, +44.2500] | **PASS** −0.77 % [−4.29, +3.85] | **PASS** −1.53 % [−6.63, +1.14] |
| declared rule, budget vs base | **17.200058** | **999/1200** | 445/1200 | **180/1200** | 0.328333 | 0.295000 | **PASS** +18.0833 pp [+4.3333, +33.9167] | **PASS** +1.29 % [−2.27, +4.26] | **PASS** −1.39 % [−5.52, +1.66] |
| either, zero handover (= hold the incumbent) | **10.325892** | **929/1200** | 232/1200 | **115/1200** | 0.000000 | 0.000000 | vs incumbent **PASS** +0.0000 pp; vs base **FAIL** +0.3333 pp [−0.8333, +2.0000] | **PASS** | **PASS** |

**Derived from those verified aggregates.**

- Against the **geometric base** as reference, the price of passing is
  **62.502712 → 17.257910 Mbit/J, a loss of 45.244802 Mbit/J = 72.389 %** of the specialist's EE
  (declared rule: 52.042303 → 17.200058, −34.842245 = −66.950 %).
- Against the **declared incumbent** as reference, the zero-baseline rule means the only arm that
  can pass is one with **zero** handovers, which on this panel is exactly holding the incumbent:
  **10.325892 Mbit/J, 929/1200 served, 115/1200 attaining** — a loss of **83.48 %**. There is no
  interior option: the reference has no handovers to be non-inferior to.
- The constrained arm is nonetheless **well above the base at equal handover cost**:
  17.257910 against 11.027760 Mbit/J, **+56.50 %**, at 0.321667 ho/us versus the base's 0.324167
  and 0.294583 κ versus 0.299167 κ, with more users served (1001 versus 960) and more attaining
  (192 versus 127).

### The size of the room a learner would have to work in

**Derived.** Under the sealed guard with the geometric base as reference, the EE that is actually
admissible on this panel runs from **11.027760 Mbit/J** (the base itself) to at least
**17.257910 Mbit/J** (this constrained construction), while the unconstrained specialist sits at
**62.502712 Mbit/J** and is inadmissible. The room is therefore bounded above by
**45.244802 Mbit/J** and below by the **6.230150 Mbit/J** already taken by a non-learned greedy
admission rule.

**This is an upper bound on the room, not a measurement of it.** The constrained arm is a
first-improvement greedy admission from a stated rule, not a constrained optimum; a better
assignment inside the same handover budget would raise 17.257910 and shrink the room by exactly
that much. Nothing here establishes that a learner can reach any particular point in it.

## Answering the question the job exists for

1. **Does the strongest non-learned configuration already satisfy every declared co-primary
   outcome?** **No.** It passes complete-service availability by a wide margin against both
   declared references and fails the handover-rate and Φ-priced-cost guards against both, by
   roughly 200 % and 180 % relative against the base and by the zero-baseline rule against the
   incumbent. The same is true of the strongest declared rule and of all nine declared rules.
2. **Is the contribution therefore the rule rather than the method?** On the EE axis alone the
   rule is very strong (5.67× the base). But **it is not deployable under the declared guard**,
   and the guard-satisfying version of it retains only 27.6 % of its EE. The gap between
   17.257910 and 62.502712 Mbit/J at a fixed handover budget is a well-posed, unclaimed job.
3. **Is that job a learning job?** **This measurement does not say so**, and must not be read as
   saying so. It establishes that a gap exists and bounds it. Whether a learned policy, a better
   non-learned admission rule, or a hysteresis-tuned variant closes it is unmeasured — and the
   cheapest next test is the non-learned one, since a better greedy admission inside the same
   budget would shrink the room before any learner is trained.

## What this does not establish

- **No optimum is reported anywhere.** Every arm is a stated construction plus, where noted, a
  bounded first-improvement boundary-0 search. A better assignment at any constraint level raises
  that row.
- **Boundary-0 is a weak proxy and was used only for selection.** The matched-budget free polish
  shows it actively misleads at the endpoint (62.502712 → 59.516177). The greedy admission order
  inside Constraint B was also ranked on boundary-0 marginal EE, so the constrained EE of
  17.257910 is a floor for that rule family for the same reason.
- **The re-entry and cell-re-key branches of EVENT-QOS were exercised with zero events** and are
  therefore untested on this panel, not validated.
- **The effective sample size is 4 physical steps**, not 12 anchors, for the arm side; and 7 of
  12 anchors have a zero-handover base reference, which is why the handover and Φ intervals carry
  undefined upper endpoints. The verdicts hold in both clusterings and in the steps-1–3-only
  sensitivity.
- **No transfer to the MODQN sibling.** Different action space, no cap on the derived active set;
  none of these event counts or Φ prices are defined there.
- **No claim about the 48 evaluation-only dates**, which were not read, and no learner arm is
  ranked or referred to.

## Execution receipt

**Verified by running code.** Three Python processes in total, never more than two concurrently,
the mandated interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, niceness 16, all six
BLAS/OMP thread controls pinned to 1.

| Process | anchors | wall (s) | peak RSS | scalar `evaluate` calls |
|---|---:|---:|---:|---:|
| shard A (steps 0–1 × 3 carriers) | 6 | 317.4 | 1.883 GiB | 0 |
| shard B (steps 2–3 × 3 carriers) | 6 | 714.3 | 1.894 GiB | 0 |
| declared-rule pass (all 12) | 12 | 426.6 | 1.655 GiB | 0 |

Peak RSS is below the 5 GB limit for every process.

Artefacts, all under `/home/sat/mcrl-v025-specprofile-ws/`:

- Runners `.scratch/specprofile/run_specprofile.py`, `.scratch/specprofile/run_specprofile2.py`;
  mergers `.scratch/specprofile/merge_specprofile.py`, `.scratch/specprofile/merge_declared.py`;
  launcher `.scratch/specprofile/launch.sh`.
- Receipts `.scratch/specprofile/specprofile-shard-A.json`,
  `.scratch/specprofile/specprofile-shard-B.json`,
  `.scratch/specprofile/specprofile-declared-rules.json` (all `status = COMPLETE`,
  `scalar_evaluate_calls = 0`).
- Merged `.scratch/specprofile/specprofile-merged.json`,
  `.scratch/specprofile/specprofile-declared-rules-merged.json`.
- Rehearsal `.scratch/specprofile/rehearsal-specprofile-shard-A.json` and `rehearsal2.log`.
- Resume state `PROGRESS.md`.

Read-only inputs, unchanged: BEAMCOUNT shard receipts
`/home/sat/mcrl-v025-beamcount-ws/.scratch/beamcount/beamcount-shard-{nearest-eligible,
stay-if-possible,random-masked}.json` (SHA-256 recorded in every receipt), pilot
`run_v025_pilot_c3.py`, engine `run_v025_matrix_probe.py`, `batch.py`, `energy.py`, `targets.py`
(SHA-256 recorded in every receipt). World tape: domain `V025_PROBE/world/1`, digest recorded in
every receipt.

This is a design-phase measurement, not a claim.
