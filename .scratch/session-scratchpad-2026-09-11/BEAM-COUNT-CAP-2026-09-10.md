**The feasibility floor is exactly 8 active beams at every one of the 12 development anchors, so the sibling project's literal 3-beam cap is infeasible here; pooled EE rises monotonically as the cap is loosened and peaks at the loosest level measured, C = 50, at 62.502712 Mbit/J with 1200/1200 PHY-served and 354/1200 (29.500%) attaining the nominal rate target — and the cap is slack there (23.25 realised active beams), so the peak is not a cap effect and no measured cap raises EE.**

# BEAMCOUNT — what a cap on the NUMBER OF ACTIVE BEAMS does in this physics

`DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM.` Learner checkpoints were read only as inputs to a
selection rule; no loss value is used as evidence. Only the 12 frozen development anchors were
read. **No evaluation-only claim date was read.** No sealed artefact and no physics was changed.

## Decision in plain language

A cap on the number of active beams is **not** a live design candidate on this panel, and the
sibling constraint does not transfer in its literal form.

1. **The floor is 8.** The exact minimum legal-beam set cover is 8 at all four physical steps.
   A 3-beam cap cannot serve the roster at all, so it is infeasible here; caps 4, 5 and 6 are
   likewise below the floor and were not run.
2. **Tightening the cap costs EE and costs service quality.** Over the evaluated grid
   {8, 9, 10, 15, 20, 30, 50} pooled EE is monotonically increasing in the cap: 46.876067 Mbit/J
   at C = 8 (1194/1200 served, 3/1200 attaining) up to 62.502712 Mbit/J at C = 50 (1200/1200
   served, 354/1200 attaining). There is no interior peak. The question "at what cap does EE
   peak" therefore has the answer "at the loosest cap measured", which is the same as "a cap
   does not help".
3. **The peak is not a cap effect.** At C = 50 the realised mean active-beam count is 23.25
   (range 16–36), so the constraint is slack at the point that attains the best EE. The measured
   EE-good operating region is roughly 16–36 active beams, well above the 8-beam floor and below
   the 47.75 beams of `RSS_MAX`.
4. **The premise that this physics rewards concentration is rule-specific, not general.** The
   CROWDCOST coverage-first assignment rule is reproduced exactly and does fall monotonically
   with beam count (46.110374 → 17.478088 Mbit/J from C = 8 to C = 50). Holding the same beam
   sets and changing only the within-set assignment to max-nominal-gain reverses the direction.
   The earlier "opening beams lowers EE" slope is a property of that assignment rule, not of the
   beam count.
5. **The sibling's constraint is per satellite, and its translated form does not bind at the
   floor but does bind every EE-good point.** A per-satellite cap of 3 still admits an 8-beam
   cover (2 + 3 + 3 across three satellites); a per-satellite cap of 1 is infeasible. But the
   EE-good assignments stack many beams on one satellite (`RSS_MAX` mean 23, max 33), so a
   per-satellite 3 cap would bind them.

## Reporting conventions

Every EE figure below carries its service and attainment beside it, as required.

- **Reference**: the 12 frozen development anchors, `V025_PROBE/world/1`, steps 0–3 ×
  `nearest-eligible`, `stay-if-possible`, `random-masked`; current V0.25 `a-r0` physics; realised
  field; all 48 within-step boundaries.
- **Information class**: development-anchor, non-evaluation. Selection used boundary 0 only;
  endpoints used all 48 boundaries.
- **Estimand**: pooled EE = `sum(bits) / sum(joules)` over the 12 anchors, never a mean of
  per-anchor EEs.
- **Numerator**: saturated full-buffer successfully decoded information bits, no demand cap.
- **Attainment**: users meeting the nominal 50 Mbit/s setpoint, which declaration v1.1 makes a
  nominal power-control setpoint permitting partial delivery, so a low attainment is not a
  contract violation but must be read beside every EE number.

Evidence classes are marked throughout as **verified by running code**, **verified by reading
primary source**, **transcribed**, **derived**, or **inferred**.

## Mandatory gates

### Parity — passed, reported before anything else

**Verified by running code.** Both required values reproduce to the sixth decimal in the same run
that produced everything else, from full-48 endpoints read out of the dense cache:

| Required value | Target | Measured | Delta |
|---|---:|---:|---:|
| `RSS_MAX` pooled EE | 41.621560 Mbit/J | 41.621560 Mbit/J | −1.8285e-07 Mbit/J |
| Crowded endpoint pooled EE | 46,110,374.337747 bit/J | 46,110,374.33774687 bit/J | −1.2666e-07 bit/J |

The crowded endpoint reproduces at 1200/1200 PHY-served with exactly 8.000 active beams per
anchor, and `RSS_MAX` at 1200/1200 served, 297/1200 (24.750%) attaining, 47.750 mean active
beams. These independently match [`STATIC-BASELINE-FAMILY-CLEANPATH`](/home/sat/mcrl-v025-rank2-ws/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md:42),
the parity gate in [`CEILING2`](/home/sat/mcrl-v025-ceiling2-ws/CEILING-CLEAN-AND-LEVERS-2026-09-10.md:19),
and the parity table in [`COORDVALUE`](/home/sat/mcrl-v025-coord-ws/COORDINATION-VALUE-2026-09-10.md:15).

### Evaluator rule — passed

**Verified by running code.** `StepEvaluator.evaluate` was replaced class-wide by a counting,
raising stub before any measured work. Every selection comparison ran inside one fresh dense
`StepEvaluator(field="realised", boundary_indices=(0,))` per (anchor, cap), with the carrier
`BASE` submitted through `evaluate_many` in the same batch as that cap's candidates; profiles
were read only from `StepEvaluator._evaluated`. Endpoints used one separate fresh realised dense
full-48 `StepEvaluator(boundary_indices=range(48))` per anchor, populated by exactly one
`evaluate_many` call. **All three sweep shards ended with `scalar_evaluate_calls = 0` and the
assertion `PASS: zero scalar StepEvaluator.evaluate calls`.** The dense path cannot silently fall
back: `evaluate_many` delegates to scalar `evaluate` only when the batch is empty or the setting
is not `a-r0` ([run_v025_matrix_probe.py:793](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:793)).

An internal check that batch composition does not leak: `configuration_id` is a pure function of
the mapping ([run_v025_matrix_probe.py:527](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:527)),
and the same `RSS_MAX` configuration scored in batches of different composition in different
processes returned bit-identical pooled EE.

## Part 1 — feasibility floor

**Verified by running code.** Per physical step, on the exact legal-option graph
(`runner._legal_options`), with an exact minimum set cover using dominated-mask pruning and a
branch-and-bound identical in procedure to the one CROWDCOST used:

| Step | Exact minimum legal-beam set cover | Greedy upper bound | Max distinct-beam matching rank | Distinct legal beams | Legal options per user | Users with no legal option | Satellites |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | **8** | 10 | 100 | 370 | 28 | 0 | 9 |
| 1 | **8** | 10 | 100 | 370 | 28 | 0 | 9 |
| 2 | **8** | 10 | 100 | 370 | 28 | 0 | 9 |
| 3 | **8** | 10 | 100 | 370 | 28 | 0 | 9 |

The cover is the same beam set at all four steps: `(57502,25) (57502,48) (60104,20) (60104,29)
(60104,53) (60104,55) (62045,27) (62045,62)`. Exact-cover solve time was under 0.01 s per step.
This confirms the 8 reported by CROWDCOST and confirms it is a legality floor, not a chosen value.

**Therefore a 3-beam cap is infeasible on this panel**: three beams cannot cover 100 users whose
minimum legal cover is eight. Caps 4, 5 and 6 are below the floor and were skipped as infeasible,
as pre-declared. The sibling's moving-footprint scenario is a different geometry and its literal
3 does not transfer.

### The sibling constraint is per satellite, not system-wide

**Verified by reading primary source on this server.** The brief's `k_cap = 3` is a *per
satellite* limit, not a system-wide active-beam budget:

- `k_cap: int = 3` with the comment that it is "the current explicit scenario-capacity
  assumption" ([family_b_step.py:58,86](/home/sat/mcrl-figures-deps/papers/modqn-paper-reproduction/src/modqn_paper_reproduction/env/family_b_step.py:86));
- it is applied inside a per-satellite loop, `active[l, order[: self.config.k_cap]] = True`
  where `l` indexes satellites ([family_b_step.py:725](/home/sat/mcrl-figures-deps/papers/modqn-paper-reproduction/src/modqn_paper_reproduction/env/family_b_step.py:725));
- the code states the mapping explicitly: "V (beams per satellite) <-> k_cap (simultaneously
  radiating beams per satellite), giving K = L * k_cap", implemented as
  `k_universe = int(self.config.l_w) * int(self.config.k_cap)`
  ([family_b_step.py:1165-1173](/home/sat/mcrl-figures-deps/papers/modqn-paper-reproduction/src/modqn_paper_reproduction/env/family_b_step.py:1173)).

Also **verified by reading primary source**: `target_active_beam_count: int = 3` exists at
[angle_aware_ee_phase02a_contracts.py:151](/home/sat/modqn-paper-exploration/src/modqn_paper_reproduction/analysis/angle_aware_ee_phase02a_contracts.py:151)
— line 151 in the tree reachable here, not the 160 given in the brief, so it is a different
revision. **Transcribed, and not verifiable on this server**: the `moving_footprint_geometry.py`
and `moving_footprint_contract.py` files named in the brief are not present anywhere under
`/home/sat`, so their `max_active_beams: int = 3` and the validator string
`"served_coverage target_active_beam_count must be 3"` remain transcribed only. I did not verify
them and do not rely on them.

**Verified by running code** — the translated per-satellite constraint on this panel, by exact
minimum cover subject to at most `k` beams per NORAD id (dominance pruning restricted to within a
satellite, which is the only form that stays sound under a per-satellite cardinality constraint):

| Per-satellite cap | System-wide beam universe (9 satellites) | Status | Exact minimum cover | Distribution |
|---:|---:|---|---:|---|
| 1 | 9 | **INFEASIBLE** (exact, searched to 9) | — | — |
| 2 | 18 | EXACT | **8** | 2+2+2+1+1 over five satellites |
| 3 | 27 | EXACT | **8** | 2+3+3 over three satellites |

So the sibling's actual constraint, translated, **costs nothing at the floor**: the 8-beam cover
can be arranged within 3 beams per satellite. Its EE at that floor is 47.183353 Mbit/J
(1200/1200 served, 30/1200 attaining) under coverage-first assignment — essentially the crowded
endpoint. **But it would bind every EE-good point**: see Part 2's per-satellite census.

## Part 2 — the cap sweep

### Construction rule (stated)

For each cap `C`, candidate assignments were built from three beam-set rules × three
within-set assignment rules, all of which cover every user legally:

- **Beam sets** (all start from the exact minimum cover and extend through the beam/user
  transversal matroid so every selected beam keeps a private witness user): **S1** adds beams in
  ascending panel-anchor coverage (the CROWDCOST canonical order), **S2** descending coverage,
  **S3** descending total boundary-0 nominal gain.
- **Assignments**: **A1** gives each selected beam a distinct witness then crowds the rest onto
  the in-set legal beam of greatest coverage (the CROWDCOST canonical rule); **A2** gives each
  user its in-set legal beam of greatest boundary-0 nominal gain; **A3** least-loaded in-set
  legal beam.
- **Local search**: the two best starts by boundary-0 EE were polished by first-improvement
  single-user reassignment restricted to the selected beam set, accepting a move only if
  boundary-0 EE strictly improves and boundary-0 PHY-served does not decrease, up to 3 passes.
- **Nesting**: the winner of every smaller cap, and `RSS_MAX` when its active count is within
  `C`, were added to cap `C`'s candidate pool, because a smaller-cap point is feasible at every
  larger cap. This makes the boundary-0 selection monotone in `C` by construction.
- **Winner**: greatest boundary-0 EE among all starts and polished points in that cap's
  evaluator that meet the carrier-`BASE` boundary-0 served guard.

Every declared rule was also carried to the full-48 endpoint batch, so the cap curve can be read
without boundary-0 acting as the selector.

### Result — boundary-0-selected winner at each cap

**Verified by running code.** Pooled over 12 anchors, full-48 realised endpoints.

| Cap C | pooled EE (Mbit/J) | pooled bits | pooled joules | served PHY | rate-target attained | modal_frac | realised active beams, mean [range] |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 (floor) | 46.876067 | 1.072015e+12 | 22,869.134 | 1194/1200 | 3/1200 (0.250%) | 0.180000 | 8.00 [8, 8] |
| 9 | 52.210340 | 1.276079e+12 | 24,441.116 | 1200/1200 | 21/1200 (1.750%) | 0.162500 | 9.00 [9, 9] |
| 10 | 53.844237 | 1.335964e+12 | 24,811.647 | 1200/1200 | 27/1200 (2.250%) | 0.157500 | 10.00 [10, 10] |
| 15 | 56.063266 | 1.451682e+12 | 25,893.645 | 1200/1200 | 147/1200 (12.250%) | 0.140000 | 13.50 [10, 15] |
| 20 | 59.711267 | 1.574048e+12 | 26,360.992 | 1200/1200 | 285/1200 (23.750%) | 0.142500 | 17.25 [16, 18] |
| 30 | 60.006133 | 1.594761e+12 | 26,576.633 | 1200/1200 | 330/1200 (27.500%) | 0.145000 | 18.50 [16, 23] |
| **50** | **62.502712** | 1.635706e+12 | 26,170.158 | **1200/1200** | **354/1200 (29.500%)** | 0.125000 | **23.25 [16, 36]** |

**The number this job exists for:** pooled EE peaks at **C = 50**, the loosest cap measured, at
**62.502712 Mbit/J**, with **1200/1200 served** and **354/1200 = 29.500% attaining** the nominal
rate target. EE increases at every step of the grid, so there is no interior optimum. Service is
full from C = 9 upward; the only service loss is at the floor itself, where the C = 8 winner
serves 1194/1200. Attainment moves the same way as EE, so the failure mode the brief warned about
— "a cap that maximises EE while collapsing service" — does **not** arise; instead the tight caps
are worse on both axes at once.

Because a cap is a constraint, the constrained optimum is non-decreasing in `C` by construction,
and no cap can exceed the unconstrained optimum. The measurement adds the empirical part: the
constrained optimum is still climbing at C = 50 while the realised count sits at 23.25, i.e. the
binding region has been left behind.

### Reference points, same panel and estimand

| Arm | pooled EE (Mbit/J) | served PHY | rate-target attained | modal_frac | active beams, mean [range] |
|---|---:|---:|---:|---:|---:|
| carrier `BASE` (`NEAREST_ELIGIBLE`) | 11.027760 | 960/1200 | 127/1200 (10.583%) | 0.042500 | 57.33 [41, 90] |
| `RSS_MAX` | 41.621560 | 1200/1200 | 297/1200 (24.750%) | 0.050000 | 47.75 [46, 50] |
| crowded min-cover (CROWDCOST rule) | 46.110374 | 1200/1200 | 30/1200 (2.500%) | 0.190000 | 8.00 [8, 8] |
| uncapped boundary-0 search, seeds `BASE`/`RSS_MAX` | 54.596129 | 1200/1200 | 366/1200 (30.500%) | 0.047500 | 47.00 [41, 50] |
| uncapped boundary-0 search, best known | 58.624918 | 1200/1200 | 426/1200 (35.500%) | 0.060000 | 42.75 [29, 50] |

The uncapped rows are **search results, not optima**. That the C = 50 winner (62.502712) exceeds
them is a property of the searches, not evidence that a cap helps; any capped point is by
definition also available uncapped.

### The direction reversal is an assignment-rule effect

**Verified by running code.** Holding the beam sets fixed and varying only the within-set
assignment rule:

| Cap C | S1 ascending coverage + A1 coverage-first (CROWDCOST canonical) | best of the nine declared rules | best rule at that cap |
|---:|---:|---:|---|
| 8 | 46.110374 (1200 served, 30 attained) | 46.110374 | S1/S2/S3 + A1 (identical at the floor) |
| 9 | 39.847179 (1197, 0) | 51.106945 (1200, 18) | S3 + A2 max nominal gain |
| 10 | 38.562079 (1197, 3) | 52.925000 (1200, 30) | S3 + A2 |
| 15 | 29.935513 (1170, 24) | 53.304280 (1200, 111) | S3 + A2 |
| 20 | 26.867606 (1170, 51) | 58.541926 (1200, 252) | S3 + A2 |
| 30 | 19.225860 (1146, 45) | 55.283649 (1200, 324) | S3 + A2 |
| 50 | 17.478088 (1170, 162) | 52.042303 (1200, 303) | S2 + A2 |

The left column reproduces CROWDCOST's monotone decline (46.110374 → 17.478088 Mbit/J, a 62.1%
loss) and also loses service as the cap loosens. The right column rises over the same beam
counts. **Same beam sets, opposite sign.** This localises the earlier finding: on this panel
`d(EE)/d(active) < 0` is a statement about coverage-first crowding, not about the number of
active beams. It does not overturn CROWDCOST's arithmetic, which reproduces exactly; it bounds
what that arithmetic is about.

### Per physical step

**Verified by running code.** Pooled EE / served / attained / mean active beams, three carrier
anchors pooled per step:

| Arm | step 0 | step 1 | step 2 | step 3 |
|---|---|---|---|---|
| `RSS_MAX` | 71.839 / 300 / 102 / 46 | 65.792 / 300 / 120 / 50 | 49.718 / 300 / 66 / 47 | **19.837** / 300 / 9 / 48 |
| crowded min cover | 52.690 / 300 / 6 / 8 | 51.907 / 300 / 9 / 8 | 44.454 / 300 / 9 / 8 | 36.435 / 300 / 6 / 8 |
| C = 8 winner | 53.743 / 300 / 0 / 8 | 52.987 / 300 / 3 / 8 | 45.653 / 300 / 0 / 8 | 36.736 / 294 / 0 / 8 |
| C = 20 winner | 64.863 / 300 / 90 / 17 | 64.640 / 300 / 87 / 18 | 60.292 / 300 / 69 / 18 | 50.310 / 300 / 39 / 16 |
| C = 50 winner | 76.594 / 300 / 120 / 36 | 64.901 / 300 / 93 / 18 | 61.166 / 300 / 96 / 23 | 50.120 / 300 / 45 / 16 |

The pooled ranking of `RSS_MAX` below the crowded endpoint comes entirely from step 3, where
`RSS_MAX` collapses to 19.837 Mbit/J with 9/300 attaining. This is consistent with the per-step
starts recorded independently by [`COORDVALUE`](/home/sat/mcrl-v025-coord-ws/COORDINATION-VALUE-2026-09-10.md:35).
At every step the C = 20 winner beats both the 8-beam point and `RSS_MAX`.

### Per-satellite census of the measured points

**Verified by running code**, parsed from the endpoint `configuration_id`s: mean over the 12
anchors of the largest number of beams used on any single satellite.

| Arm | mean max beams on one satellite [range] | anchors exceeding 3 | mean active satellites |
|---|---:|---:|---:|
| crowded min cover / C = 8 winner | 4.00 [4, 4] | 12/12 | 3.00 |
| C = 20 winner | 4.50 [4, 6] | 12/12 | 5.25 |
| C = 50 winner | 10.25 [4, 28] | 12/12 | 5.00 |
| `RSS_MAX` | 23.00 [19, 33] | 12/12 | 5.00 |
| per-satellite-3 cover (A1/A2) | 3.00 [3, 3] | 0/12 | 3.00 |

This is why the per-satellite reading matters: a per-satellite cap of 3 is feasible at the floor,
but every EE-good point measured here violates it, including the unconstrained-cover 8-beam point
that puts 4 beams on satellite 60104.

## Part 3 — where the current policies land: NOT COMPLETED

**Not run.** The projection pass — `RSS_MAX` and the learned `a0` (all 16 epoch-500 FULL-arm
checkpoints from the completed 16/16-seed run at
`/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z`, read-only) projected
onto each cap's winning beam set and onto each policy's own top-`C` footprint — was launched and
then **stopped by the controller's cost-control instruction before its first anchor completed**.
No projected number is reported and none should be inferred.

What *is* established for this part, verified by running code in the sweep itself:

- `RSS_MAX` sits at **47.75 mean active beams** [46, 50], 41.621560 Mbit/J, 1200/1200 served,
  297/1200 (24.750%) attaining — far above the 16–36 beam region where the measured EE-good
  points sit, and above the 23.25 realised at the best cap level.
- The learned `a0` arm was fully prepared and validated but not scored: 16 epoch-500 FULL
  checkpoints were loaded and digest-checked, the 12 development corpus shards were digest-checked
  against the launch receipt (`11920d3ae7d8…`), and the corpus action shortlist was audited
  against the tape's legal options (9–10 shortlisted actions per user versus 28 legal options;
  zero corpus actions illegal in the tape). The `a0` rule is the raw independent masked
  `argmax(Q1 + Q2)` per user, **before** joint-conflict repair.
- Prior measurement, **transcribed** from [`BASE-COLLAPSE-DIAGNOSIS`](/home/sat/mcrl-v025-probe-ws/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md:27):
  learned `a0` averages 49.07 active beams for the q1-v2 design run and 41.28 for the q1-v1
  sensitivity — note the brief's 49.07 is the q1-v2 number from `/home/sat/mcrl-v025-design-ws`,
  whereas the run the brief names for this job is q1-v1 in `/home/sat/mcrl-v025-retrain-ws`.
  Those counts are on the 22 TRAIN anchors, not this 12-anchor panel, and carry no EE.

To resume exactly: `cd /home/sat/mcrl-v025-beamcount-ws/.scratch/beamcount && BEAMCOUNT_SCRIPT=run_beamcount_project.py ./launch.sh project - project.log`.
The three sweep shards are final inputs and do not need to be rerun; expected cost is one process
for roughly 25–35 minutes at current machine load.

## Part 4 — differentiable beam-count penalty: OMITTED

Omitted on the controller's instruction, because six independent reviews have since rejected
treating beam concentration as a relabelled route. No pricing, recommendation, or route
classification is offered here.

## Cap levels run and not run

| Requested | Status |
|---|---|
| 4, 5, 6 | **Not run — infeasible**, below the floor of 8 (pre-declared skip) |
| floor = 8, floor+1 = 9, floor+2 = 10 | Run |
| 8, 10, 15, 20, 30, 50 | Run |
| uncapped | Run as two boundary-0 searches (natural seeds; best known); not an optimum |
| per-satellite 1, 2, 3 (added) | Feasibility run for all three; EE run at the per-satellite floor only |

Every requested cap level that is feasible was completed. The sweep was not truncated.

## What this does not establish

- **Boundary-0 is a weak proxy for the 48-boundary endpoint.** The mandated selection field is
  boundary 0, and it systematically overstates: the C = 20 winner at step 0 scores 70.5 Mbit/J at
  boundary 0 but 64.9 at full 48, and the uncapped search raised boundary-0 EE from `RSS_MAX`
  71.84 to 114.06 while full-48 EE *fell* to 65.38. Every reported EE is the full-48 endpoint;
  the selection that produced it was made on a single boundary.
- **None of these points is an optimum.** They are the best of a stated, finite rule family plus
  a bounded first-improvement search. A better assignment at any cap would raise that cap's row.
- **The per-satellite cap was priced only at its own floor.** Its constrained optimum — the best
  assignment using up to 27 beams with at most 3 per satellite — was not searched, so how much EE
  a per-satellite-3 cap would actually cost at a good operating point is **unmeasured**. That is
  the one cheap follow-up I would flag as genuinely open.
- **Carrier invariance.** For a fixed mapping the full-48 endpoint is identical across the three
  carriers at a step (0 differing label-steps out of all checked), matching
  [`COORDVALUE`](/home/sat/mcrl-v025-coord-ws/COORDINATION-VALUE-2026-09-10.md:41). The 12 anchors
  therefore carry 4 independent physical steps for every non-`BASE` arm; treat the panel's
  effective sample size accordingly.
- **The C = 8 service loss** (1194/1200) reflects a weak guard: the served floor used in selection
  is the carrier-`BASE` boundary-0 served count, which is low. The declared-rule C = 8 rows serve
  1200/1200 at 46.110374 Mbit/J.
- No claim about the 48 evaluation-only dates, which were not read.

## Execution receipt

**Verified by running code.** Three sweep shards, one per carrier, each one Python process, the
mandated interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, niceness 15, and all six
BLAS/OMP thread controls equal to 1. At most three Python processes ran at any time. Each shard
printed `anchor k/N` at every anchor.

| Shard | anchors | wall (s) | tape (s) | peak RSS | scalar evaluate calls |
|---|---:|---:|---:|---:|---:|
| `nearest-eligible` | 4 | 1,650.345 | 337.5 | 1,873,010,688 B = 1.744 GiB | 0 |
| `stay-if-possible` | 4 | 1,617.771 | 283.5 | 1,871,839,232 B = 1.743 GiB | 0 |
| `random-masked` | 4 | 2,179.359 | 254.2 | 1,881,538,560 B = 1.752 GiB | 0 |
| per-satellite feasibility | 4 steps | 3.454 | — | 40,640,512 B = 0.038 GiB | n/a (no physics) |

Peak RSS is well below the 5 GB limit for every process.

Artefacts, all under `/home/sat/mcrl-v025-beamcount-ws/`:

- Sweep runner `.scratch/beamcount/run_beamcount.py`, SHA-256
  `0b9818f31a58a0b34acca50bc98379f9143af0867d04cbeae911ef1bb427fd58`, frozen copy at
  `.scratch/beamcount/run_beamcount_sweep_frozen.py` (identical hash); each shard receipt records
  this hash.
- Shard receipts `.scratch/beamcount/beamcount-shard-{carrier}.json`, SHA-256
  `7ddb0f3e…` (nearest-eligible), `e16cc5ec…` (stay-if-possible), `eaca616a…` (random-masked).
- Per-cap-level files `.scratch/beamcount/caps/cap-{008,009,010,015,020,030,050}.json`.
- Merged partial receipt (parity, pooled sweep, cap frontier, per-satellite frontier)
  `.scratch/beamcount/beamcount-partial.json`, status `PARTIAL` because the stopped Part 3 pass
  writes the final receipt only on completion.
- Per-satellite feasibility `.scratch/beamcount/persat-feasibility.json`.
- Resume state `PROGRESS.md`.

Source under measurement, unchanged and read-only: pilot `95103bb96caa…`, engine `d430baf38eee…`,
`batch.py` `1b0064399d55…`, `energy.py` `c33dd94892ce…`, `targets.py` `e951aa2a73dc…`.

This is a design-phase measurement, not a claim.
