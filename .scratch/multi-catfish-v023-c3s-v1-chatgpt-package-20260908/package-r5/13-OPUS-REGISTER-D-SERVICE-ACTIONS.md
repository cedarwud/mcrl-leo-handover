# Assumptions register — slice D (service, QoS, action contract, masks, candidates, handover classes)

Auditor: Claude Opus 5, fresh context, 2026-09-08. Read-only; no git state changed.
Live measurements below were taken with `.venv/bin/python` against the real TLE archive,
`START = 2026-08-20 06:00 UTC`, `PhysicsConfig()` (warm start on) unless stated.
Scripts under the session scratchpad only; nothing written into the repo except this file.

## 0. Measurements this audit produced (they settle most of the questions)

| Measurement | Config | Result |
|---|---|---|
| served / outage / no-op | 100 users × 30 steps, `stay-if-possible` | **3000 / 3000 served, 0 outage, 0 no-op** |
| mask attrition per user-step | same | `slot_occupied` kills **3.54 / 28**; `cell_exists` **0.00**; `cell_reachable` **0.00**; min ⎮A_u⎮ = **21**, never 0 |
| handover classes | same | NONE 2387, **φ1 = 0**, φ2 = 613 |
| link power p over the episode | same | max 1.559 W at t=0 → ≤ 0.826 W from t=6; median **0.825 → 0.647** by t=29 (i.e. below p⁰) |
| realised SINR of *served* links | same | p5 −6.0 dB, **p50 +1.3 dB**, p95 16.2 dB; **29.5 % below −2.35 dB**, 43.5 % below 0 dB, 53.4 % below +2 dB |
| beam occupancy | same | load p50 3 / p95 5 / max 6; **44.2 radiating beams**; under `random-masked`: load p50 1, **80.2 beams** |
| 20 users × 10 steps, four policies × warm on/off | — | served 200/200 everywhere except `random-masked` + warm start (**182/200, 18 outages, all at t = 0**) |
| "renew the beam-max user each step" vs `stay` | 100 × 30 | EE −1.45 %, **39/3000 service lost**, φ1 0 → 111 |

## 1. Summary table (ranked by impact)

| # | Assumption | Implemented | Docs | Standard practice | Distorts | Magnitude | Verdict |
|---|---|---|---|---|---|---|---|
| D1 | "Served" = a boolean per user-step = *selected a masked action* ∧ *recurrence power ≤ p_max*. **No rate, SINR, latency or QoS requirement of any kind.** | `service.py:185-261` (`served[uid]=True` at :248); `step.py:812-822`; `link_budget.py:411-436` | `service.py:40-50` (ruling C-11); `required_sinr()` deleted `service.py:289-301`; "明文排除最低速率反推" | NTN admission is SINR/MODCOD-threshold based (DVB-S2X, 3GPP 38.821); a power-only admission test is non-standard | Service constraint in every kill rule; pooled EE numerator | 100 % served vs ≈70 % under γ_min = −2.35 dB | **FIX** |
| D2 | Service saturates at 100/100 *by construction*, not by luck: **any association change sets `start_gain = current gain`, so p = p⁰ = p_max/2 exactly — feasible always** | `step.py:784-806` (`continuing` false ⇒ `start_gain = transmit_gain[uid]`); pinned by `tests/test_w17_step_environment.py:483-517` ("a handover must restart the segment at p0") | Undocumented as an *invariant of the action space*; docs frame it as a physics property | No standard model makes feasibility a function of association age | Makes "move" strictly safer than "stay"; makes the service margin unreachable | outage 0/3000 for stay & nearest; only holders or t=0 movers can fail | **FIX** |
| D3 | Service margin `δ_S = 0.001` (absolute served fraction vs BASELINE) is a live guard | `…successor-physical-evaluation/v023_c1c2_successor_physical_runner.py:88, 946`; same constant in F1/F2/C3-S/E1 | LC-SRS gate contract §10 uses `0.01`; everywhere else `0.001` — **the two disagree** | Non-inferiority margins are normally set against observed dispersion | Every HELD/FALSIFIED disposition | At N=3000 it licenses **9,000 lost user-steps** against observed dispersion ≈ 0 | **FIX** |
| D4 | The decision mask is **three** terms, not the four SDD §4A.5 declares | `action_contract.py:313-369`; `candidates.py:15-24` states the omission | SDD §4A.5 `mask[a]=1 ⟺ occupied ∧ cell exists ∧ **link feasible**`; `docs/CONTROLLER-BRIEF-W18-2026-08-22.md:114-119` already asks whether the mask is identically true | Feasibility normally gates candidate selection, not post-hoc | Agent may select a guaranteed-infeasible action and be paid a *neutral* reward for it | `cell_exists`/`reachable` attrition exactly 0.00/28 | **DECLARE now, FIX under ACM** |
| D5 | Handover classes: φ1 = intra-satellite (0.5), φ2 = inter-satellite (1.0), re-entry after outage = φ2 | `action_contract.py:398-456`, `HANDOVER_COST` :414 | `docs/G9-TEST-MAP.md` T1–T7; `docs/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md`: "dimensionless project choices, **not physical time or energy**" | 38.133 A.14.2: 72 ms intra-sat, 142–152 ms inter-sat ⇒ 0.24 %/0.5 % of a 30.08 s step | r2 only; the EE endpoint has **no** handover term at all | φ1 measured **0** in 3000 user-steps under `stay`; the class is priced but unused | **DECLARE** |
| D6 | A "renewal to the same beam" is not an action — "stay" is whichever index maps to the incumbent `(norad, cell)`; same beam ⇒ `NONE`, cost 0, and the **only** case where the power segment continues | `action_contract.py:452-456`; `step.py:784-790`; `Segment.continues` `step.py:240-246` | `service.py`/`step.py` docstrings | Standard (association-based, not index-based) — this part is right | The segment key `(norad, cell)` makes *every* non-stay a free power reset | see D2 | **KEEP (identity) / FIX (its power consequence)** |
| D7 | An unserved step reads neutral on 2 of 3 objectives, and the gate that exists to catch this measures the wrong numerator | rewards `step.py:1075-1104` (`realised = UNSERVED` ⇒ r2 = 0, r3 = 0, r1 = 0); `outage_gate.py` numerator = `no_op_dropped + all_invalid_next_dropped` | `outage_gate.py:11-27` and `docs/PREREG-DRAFT.md:298-308` state the hazard verbatim | — | Training signal: outage is *rewarded* on r2 and r3 | Gate reads **0.0000** identically; P7 measured `outage_infeasible` = **6.3 %** (main warm arm) | **FIX** |
| D8 | Dwell `N = 4` freezes `j → cell_id` **and** the 4-satellite window for the segment | `dwell.py:92-104`, `scenario.py:352-388`, `candidates.py:271-338` | `dwell.py:41-57`, `docs/LINK-BUDGET-NOTES.md:186-198` | Earth-fixed dwell is standard; freezing the *candidate window* with it is not | Forces φ1 handovers the policy never chose; delays entry of a better satellite by ≤ 3 steps | re-key 3.25 % (P2 frozen) / 3.182 % (P2 rerun) | **DECLARE** |
| D9 | Feasibility is judged on the **deterministic** transmit gain; fading and interference never enter it | `step.py:751-822`; pinned by `tests/test_w17_step_environment.py:755` | `step.py:22-33` ("no fixed point in that chain") | ACM admission is by *realised* Es/N0 | "Served" is a nominal, interference-blind quantity while the rate that scores it is realised | — | **DECLARE / FIX under ACM** |
| D10 | Training-time masks == deployment masks | `runtime/trainer_env.py:253-260` → `observation.masks`; `…physical_runner.py:993, 1041, 1065-1072` | — | Correct | — | identical objects; Q2 mask equality is asserted at :1041 | **KEEP** |
| D11 | Deployment **refuses** an empty mask; training emits `NO_OP` and drops the transition | `…physical_runner.py:1031`; vs `modqn.py:324-348`, `action_contract.py:71-89` | SDD §4A.5a(1) | — | Latent only — masks are never empty | never fires | **DECLARE** |
| D12 | `ALL_NEUTRAL_CONTROL` ≠ `BASELINE` | `…five-arm-source-training-runner:62-70` (`{C1,C2,C3} = neutral`); `BASELINE` = frozen authenticated MODQN checkpoint with `routes = []`, `…physical_runner.py:534-560` | `SUCCESSOR-BRIEF-COMMON-2026-09-07.md:13`; declaration §: "no arm named `ALL_NEUTRAL_CONTROL`, `FULL`, `DROP_C3` or `BASELINE` in stage A" | — | Naming discipline only | — | **KEEP** |
| D13 | The action space cannot name another user, a beam, or a set | `action_contract.py:7-24` (`a = 7l + j`, 28 flat outputs) | SDD §4A.1 | Multi-agent handover papers typically keep per-user actions | Any *additive per-user* coordination head is expressing a set-level quantity through a per-user index | explains the eighteen C3 failures better than any target formula | **DECLARE** |
| D14 | Beam activation is derived, `z = 1{U > 0}`; there is no "switch a beam off" action and no per-satellite beam-count ceiling | `service.py:132-162`; `link_budget.py:180-200` | ruling 2026-08-22 §7.4 | Standard for load-derived activation | Consolidation is the only EE lever, and it is only reachable collectively | 44.2 vs 80.2 beams (stay vs random) | **KEEP** |

## 2. Per-item detail and known-answer tests

**D1/D2 — what "served" is, and why it is 100 %.** `resolve_service` (`service.py:185-261`) takes
three inputs: the action, the decision-time slot table, and a boolean `link_infeasible`. It sets
`served = True` iff the action is not `NO_OP` and `link_infeasible` is false. `link_infeasible` is
built at `step.py:812-822` from exactly two conditions: a pattern null (`G^T ≤ 0`), and
`p > p_max` where `p = p⁰·G^T(θ(τ))/G^T(θ(t))`. Because a **new** segment sets `τ = t`
(`step.py:801-803`), `p = p⁰ = p_max/2` identically, so *every* association change is feasible
by construction from step 1 onward — a fact the test suite states as a requirement
(`tests/test_w17_step_environment.py:483-517`). Only two populations can fail: (i) a user
**holding** a segment through more than `SEGMENT_GAIN_BUDGET_DB = 3.010 dB` of transmit-gain
loss (largest measured in-segment loss: 0.718 dB), and (ii) a user at **step 0**, whose segment is
warm-started from a historical satellite position. My 20-user sweep isolates (ii): `random-masked`
loses 18/200 user-steps and all of them at t = 0, while `stay`/`nearest` lose none. So the
observed "outage" is an episode-boundary artefact, not a physical outage.
*Known-answer test:* with `PhysicsConfig(segment_warm_start="none", fading_enabled=False)`, drive
any policy that changes `(norad, cell)` every step; assert `link_power_w[served] == p⁰` exactly and
`served.all()` for all steps — hand-computable, no ephemeris needed beyond the fixture.

**D3 — the margin.** `service = Σ served / (USERS·STEPS)`; the rule is
`service[arm] ≥ service["BASELINE"] − 0.001` (`…physical_runner.py:946`). Observed dispersion is
zero to three decimals for every reference policy. Astra's own seal note computes the allowance as
9,000,000 opportunities × 0.001 = **9,000 user-steps**. A guard four orders of magnitude looser
than the noise is not a guard. Worse, it points the wrong way: dropping a user removes its bits
*and* can remove a whole beam's 0.338 W circuit charge plus its PA supply, so **losing service can
raise pooled EE**. The only arm I could construct that lost service (renew-the-beam-max) lost 39
user-steps — and it lost them at t = 0 through the warm start, not through any coordination effect.
Separately, `docs/MULTI-CATFISH-…-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md:697-701`
freezes the margin at **0.01**, ten times the value every runner implements. That is a live
code-vs-docs contradiction inside the frozen contract family.
*Known-answer test:* construct a two-user, two-beam fixture where dropping the sole user of one
beam removes `fixed + supply` and raises Σbits/Σjoules; verify the disposition still returns HELD.

**D4 — the mask.** `candidates.py:15-24` says so in plain text: the fourth §4A.5 term is "**not**
applied yet". Measured attrition per user-step: `cell_exists` 0.00/28 and `cell_reachable` 0.00/28
— both structurally dead here (the lattice carries a guard ring; `CELL_VISIBILITY_MIN_ELEVATION_DEG
= 0.0` at `candidates.py:51-57` makes the horizon test almost vacuous). Only `slot_occupied`
binds, at 3.54/28 ≈ half a satellite row, and never all four. `A_u(t)` was never once a strict
subset small enough to matter and was never empty, so C-15's no-op branch, `modqn.py`'s
`no_op_transitions_skipped`, `all_invalid_next_transitions_skipped`, the semi-MDP clause and the
outage gate are all **unreachable code**. The 2026-08-22 controller brief anticipated exactly this
and asked for a measurement; the measurement is above and the answer is (ii) — redundant by
construction, not merely a loose scenario.

**D5/D6 — handover classes.** `classify_handover` is association-based and correct (T1/T2 false
positives/negatives are pinned). But: (a) `φ1 = 0` in 3000 user-steps under `stay-if-possible`, and
the project's own R2 record gives 0 φ1 / 1741 φ2 in 10,000 for the same policy — so the intra/inter
distinction carries no weight for any stay-ish policy and the whole φ1 branch is a modelling
statement the experiment never exercises; (b) an **outage step is charged NONE (cost 0) and the
*return* is charged φ2** (`action_contract.py:446-451`), so the ledger prices re-entry rather than
departure; (c) φ1/φ2 are dimensionless (the provenance matrix is explicit), and the EE endpoint
contains **no handover energy or interruption at all**, so at the endpoint a handover is exactly
free while at training time it costs 0.5 or 1.0 in an arbitrary unit. That asymmetry is a target/
estimand mismatch, not a tuning question.
*Known-answer test:* an unserved user at t, served at t+1 on the *identical* `(norad, cell)`;
assert `r2 = −φ2` and `link_power_w = p⁰`, i.e. the model charges the maximum handover cost for a
step in which nothing physically moved, and simultaneously grants the cheapest power.

**D7 — the outage gate measures the wrong thing.** `outage_gate.py`'s docstring names the exact
hazard ("r1 ≈ 0, r2 = 0, r3 = 0 … truncating the future makes outage **free**"), but its numerator
is `no_op_dropped + all_invalid_next_dropped`, both driven by an empty mask, which never occurs.
The population that actually reads neutral is `resolution.outage_infeasible`, which is **not
dropped** — it is stored in replay with `(0, 0, 0)`, i.e. the *worst possible* r1 alongside the
*best possible* r2 and r3. P7 measured that population at 6.31 % (main warm arm) / 5.21 %
(sensitivity arm) — both far above the 1e-3 ceiling the gate was written to enforce.
*Known-answer test:* run the gate on a trajectory with a forced infeasible link and assert the
verdict is `drop-admissible` while `outage_infeasible` is 100 % — the gate cannot see it.

**D8 — dwell.** `is_boundary(t) ⇔ t mod 4 == 0`. Between boundaries the anchor is frozen even if
the user teleports; the satellite window is frozen too (`scenario.py:360-388`), with live D2 fields
refreshed but no new identity admitted (`candidates.py:271-338`). Two consequences: a re-key
(3.25 %) moves the physical cell under a constant index and is charged φ1 *and* resets the power
segment, and a satellite that becomes best mid-dwell cannot be chosen for up to 3 steps. The dwell
rule therefore **causes** handovers rather than forbidding them, and it never forces one directly.

**D13/D14 — can the candidate set make coordination trivial or impossible?** Neither. Each user
sees 4 satellites × their *own* 7 cells; two users share a candidate beam only when the cell is in
both neighbourhoods *and* the satellite in both windows, so beams are shareable but not universally
so (`tests/test_candidate_assembly.py:192-198` pins that windows differ). Activation is derived, so
consolidation is a purely collective act — no single user's action darkens a beam. Measured, the
lever is real and large: `stay` runs 44.2 radiating beams at load p50 = 3; `random` runs 80.2 at
load p50 = 1. What is impossible is *expressing* it: the 28 actions name only `(satellite slot,
cell slot)` for the acting user, so a per-user additive head can only ever approximate a set-level
quantity. This is a structural explanation for the C3 failure series that does not depend on any
target formula.

## 3. Code-vs-docs disagreements found

1. **Service margin 0.001 vs 0.01.** Every runner implements `0.001`
   (`…physical_runner.py:88`, F1/F2, C3-S, E1); the frozen LC-SRS observability gate contract
   §10 (`docs/MULTI-CATFISH-…-2026-09-05.md:697-701`) says `delta_S = 0.01`. Ten-fold.
2. **SDD §4A.5's four-term mask vs the three-term implementation.** `candidates.py:15-24` and
   `action_contract.py:331-334` document the divergence but the SDD text is not corrected;
   the paper §4.1 and slide part1 p25 still describe a binding `m_{u,c}(t)`.
3. **`outage_gate` is named for `outage_infeasible` and measures `no_op`.** The docstring and
   `docs/PREREG-DRAFT.md:298-308` describe the infeasibility population; the code counts the
   empty-mask population.
4. **`ServiceResolution.served` docstring** says "chose an action AND it survived the **execution
   mask**" (`service.py:101`) — `m^e` was deleted by ruling C-11; the surviving gate is power
   feasibility. The module header corrects this at :26-31 but the field docstring was not updated.
5. **`docs/LINK-BUDGET-NOTES.md:251` and `PREREG-SIGNOFF:81`** still quote "28/28 valid" as the
   attrition figure. Measured at the stage-C scale it is 24.46/28 (mean), min 21 — the number
   moved when the population went to 100 users, though the conclusion (never empty) holds.
6. **`SEGMENT_START_POWER_W`'s own ⚠** already records that ch5's sentence ("3 dB = you left your
   cell") does not match the code ("3 dB worse than when you connected"), with 11.2 % of segments
   starting outside the 3 dB contour. Still uncorrected in ch5.

## 4. What the service rule should become under fixed-EIRP + ACM, and what changes

**Rule.** `served_u ⇔ γ_u ≥ γ_min`, with `γ_u` the *realised* (3.13) SINR and `γ_min` the lowest
admitted MODCOD threshold (DVB-S2X QPSK 1/4 ≈ −2.35 dB Es/N0); rate becomes
`R_u = (B^w/U)·η(γ_u)` from a MODCOD staircase, zero below `γ_min`, instead of unbounded Shannon.

**Why it changes the experiment rather than decorating it.** 29.5 % of currently-"served" links sit
below −2.35 dB and 43.5 % below 0 dB; median is +1.3 dB. Served would fall from 100 % to ≈70 %
(γ_min = −2.35 dB) or ≈57 % (γ_min = +2 dB), and Σbits loses the long low-SINR tail that Shannon
currently credits. The service margin would start binding on its first evaluation, and the
service-vs-EE trade the kill rules pretend to police would become a real trade.

**Code paths that change.**
- `step.py::_resolve_physics:769-822` — the whole segment/recurrence block and the `p > p_max`
  test disappear; `link_power` becomes a constant per beam. `Segment`, `PhysicsConfig.segment_*`,
  `_draw_segment_ages`, `_warm_start_gain`, `training_state_dict`'s age stream, and
  `link_budget.recurrence_power_w / SEGMENT_START_POWER_W / SEGMENT_GAIN_BUDGET_DB /
  SEGMENT_START_EXCEEDS_BEAM_CEILING / classify_link_power_feasibility` all become dead.
- `service.py::resolve_service:185-261` — its `link_infeasible` argument becomes a *post-SINR*
  predicate, which **introduces the fixed point the current chain is proud of not having**
  (`step.py:22-27`): who is served sets which beams radiate, which sets interference, which sets
  who is served. It needs a declared admission iteration (drop the lowest-γ user, recompute,
  repeat to a fixed point) with a frozen tie-break and a bounded iteration count — this is the
  single largest piece of new design, and it must be pre-registered before any run.
- `action_contract.py::build_slot_table:313-369` and `candidates.py` — the §4A.5 fourth term can
  finally be implemented, using the *nominal* (interference-free, or previous-step-interference)
  candidate SINR that `_candidate_sinr` already computes: `mask[a] &= γ_nominal(a) ≥ γ_min`. This
  makes the mask bind, makes empty masks reachable, and revives the no-op / semi-MDP / outage-gate
  machinery that is currently unreachable — so `outage_gate`'s numerator must be repaired first
  (item D7) or the gate will still read 0.
- `link_budget.py::shannon_rate_bps:~660` → MODCOD staircase; `test_w06_link_budget_g2` and
  `test_w17::test_the_sinr_lands_in_a_physically_sensible_band` need new anchors.
- `…physical_runner.py:946` and every F1/F2/C3-S/E1 kill rule — the margin must be re-derived
  against the *new* dispersion, and re-frozen before it is used.
- Handover pricing: with the power reset gone, `r2` is the only handover cost left and the endpoint
  still has none. A 38.133-sourced interruption (72 ms intra / 142–152 ms inter of a 30.08 s step)
  would put φ1/φ2 on a physical footing and make the endpoint able to see churn at all.

**What does *not* change:** the association-based handover classification, the per-user candidate
windows, the derived activation `z = 1{U>0}`, the `(norad, cell)` beam key, and the fact that
training and deployment masks are the same object.

## 5. Rules that silently make "stay" or "move" free

- **"Move" is free and safer.** Any association change resets `p` to `p⁰` at zero endpoint cost and
  is feasible by construction (D2). The training reward charges φ1/φ2; the EE endpoint charges
  nothing.
- **"Stay" is the only thing that can lose service**, and it accrues the only power the recurrence
  can raise. It is also the only thing that keeps `p` *below* `p⁰` late in a segment (measured
  median 0.647 W at t = 29), so the two effects fight and the sign depends on the geometry — which
  is itself the argument that the recurrence is not modelling anything physical.
- **"Go dark" is free on two of three objectives** (r2 = 0, r3 = 0) and its cost is charged to the
  *next* step as φ2 (D5/D7).
- **Step 0 is the one place where the action choice changes feasibility**, through the warm start;
  every measured "outage" in this audit occurred there.

---

### The three assumptions I would overturn first

1. **"Served" = power feasibility with no QoS floor** (`service.py:185-261`, `step.py:812-822`) — **FIX**: 29.5 % of served links are below the lowest DVB-S2X threshold and are still credited Shannon bits; adopt `served ⇔ γ ≥ γ_min` with a MODCOD rate, accepting the admission fixed point it creates.
2. **Any association change resets the segment to `p⁰` and is therefore always feasible** (`step.py:784-806`, asserted by `tests/test_w17_step_environment.py:483-517`) — **FIX**: this single line makes "move" free and strictly safer than "stay", saturates service at 100/100, and is the action-side half of the renewal premium; it must go with the recurrence.
3. **The `0.001` service margin is a live guard** (`…physical_runner.py:88, 946`; contradicted at `0.01` by the frozen LC-SRS gate contract) — **FIX**: it licenses 9,000 lost user-steps against an observed dispersion of zero, protects nothing, and points the wrong way because losing a user can *raise* pooled EE; re-derive and re-freeze it only after the service rule changes.
