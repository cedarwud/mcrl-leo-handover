# Multi-Catfish MCRL V0.8 C2 clean-room design decision (Fable 5.1 challenger lane)

Date: 2026-09-02  
Status: `V07_RETIRED__H_A_SELECTED__STAGE1_CENSUS_PASS__STAGE1B_C2_DIRECTION_PASS__METHOD_GATE_C3_CONTEXT_FAIL__NO_LEARNER__NO_EPISODE_TRAINING`  
Claim ceiling: **formula-first design decision and fail-fast development evidence only; no C2 efficacy claim, no whole-method claim, no Chapter 5 result**

Supersedes as the C2 design direction: V0.7 focal-next `motion-one` (retired by R14).  
Does not change: the canonical ratio-of-sums EE, the fixed TRAIN-only lambda0, the
shared kappa, exactly three Q surfaces, their direct unweighted sum, one common safe
mask, one argmax, one executed Main action, or the frozen C1/C3 bytes.

## 1. Takeover verdict (one page)

1. **V0.7 C2 is retired.** R13 pooled `+0.0465%` with lineage pooled signs `1/3` and
   a six-world bootstrap crossing zero is a null development result; R14 leave-one-anchor-out
   `0/3` lineages beat the strongest state-independent null. Both are authenticated below.
   The motion-one selector reduced exposure; it did not create learned positive efficacy.
2. **Every prior C2 (V0.3 fork, V0.4 support-complete, V0.5 controlled tape, V0.6 network-total
   k1, V0.7 focal-next) trained Q2 on a realized successor residual under a frozen
   continuation policy.** V0.6 D1 and V0.7 R14 show that this class of target is not
   predictable from the causal state. The hypothesis space is therefore narrowed: the new
   C2 must target a quantity that is deterministic or expected at decision time.
3. **The simulator contains exactly one action-controlled physical carrier of history:
   the link power segment** `(norad, cell, G^T(theta(tau)))`, whose trajectory
   `p(t+k) = p0 G^T(theta(tau)) / G^T(theta(t+k))` is a closed-form function of SGP4 geometry
   and one persisted scalar, and which terminates in a hard infeasibility cliff at 3.010 dB.
   Interference, load, bandwidth share and activation carry no physical lag; the handover
   class enters only the legacy `r2` reward field and never delivered bits or network power.
   A second, weaker deterministic channel exists: the realised incumbent is seated in slot 0
   at the next dwell boundary even when outside the top-four D2 margin.
4. **C1 and C3 have no arithmetic, matching, pairing, leakage or sign-filter defect**, but
   both sealed confirmations are `LIMITED_TO_OLD_Q2_CONTEXT`. In the same sealed 30-world
   block, `Q1` alone reaches 117.05 M bit/J, above `Q1+Q3` (105.01 M), `Main` (93.21 M) and
   `FULL` (73.09 M); `(Q1+Q3)` versus `Q1` is `-10.286%` pooled with all three lineages
   negative. C3's positive marginal was measured only against the toxic old Q2.
5. **Top C2 candidate (H-A): deterministic hold-horizon segment-timing surplus.** It is
   physically represented, action-caused, decision-time computable, and non-overlapping with
   C1 (offset 0) and C3 (offset-0 non-focal rate). Its efficacy direction can be tested
   with an exact oracle score before any learner exists (Stage 1b).
6. **Decision for H-A: `REVISE` at the method level.** Stage 1 census PASS; Stage 1b C2 direction
   PASS (+11.70% pooled, 3/3 lineages, 6/6 worlds) in both the H-A and the OPS-3 formulation;
   the three-direction method gate returns `C3_CONTEXT_FAIL` for both because C3's marginal is
   negative in 0/3 lineages once the toxic old Q2 is replaced. The C2 formula is not revised;
   the blocker is C3's role and is escalated to the user (section 7).
7. **No 500/1500/3000/9000-episode run is authorized by this document.**

## 2. EE-formula causal map for C1/C2/C3

Endpoint as computed: `eta = sum_t sum_u R_u(t) dt / sum_t P^N(t) dt`, dt = 30.08 s,
`R_u = x_u (B^w/U_{b_u}) log2(1+gamma_u)`, `P^N = sum_beams p_beam/xi(p_beam) +
0.338 N_beams + 0.200 N_sats`, `p_beam = max_{served u} p_u`, `xi = 0.35 sqrt(p/5.218)`
so `P^p = 6.5264 sqrt(p)` on the live path (concave in beam power).

| Channel | Path from action to B or E | Offset | Predictability | Covered by |
|---|---|---|---|---|
| I1-I3 | own theta, slant, elevation, segment continuation -> own p, own SINR, own R | 0 | deterministic / state | C1 |
| I5-I8 | joint occupancy, activation, beam max, interference -> others' R and total E | 0 | joint action at t | C3 (rates), C1 (energy) |
| I9 | own `p > p_max` -> outage, zero bits | 0 | deterministic given segment | C1 |
| **T1** | segment recurrence: hold -> `p(t+k)` trajectory; switch -> reset to p0 | 1..3 | **deterministic** (SGP4 + persisted start gain) | none |
| **T2** | segment-age cliff: `p(t+k) > p_max` -> zero bits at t+k | 1..3 | **deterministic** | none |
| T3 | realised incumbent -> slot 0 at next dwell boundary -> future action set | boundary | deterministic | none |
| T4 | focal aged segment sets beam max -> `sqrt` energy and linear interference for others | 1..3 | state-predictable (focal half deterministic) | V0.7 at k=1 only |
| T5 | observation-mediated policy cascades | 1..3 | stochastic (policy-mediated) | V0.3/V0.6 targets; not predictable |
| T6 | handover class -> `r2` | - | - | **not a B/E channel** |

Evidence: `src/mcrl/env/step.py:777-855` (segments), `src/mcrl/env/link_budget.py:379-436`
(recurrence and gate), `:439-587` (energy terms), `src/mcrl/env/scenario.py:270-293`
(`satellite_ecef_at`), `src/mcrl/env/action_contract.py:213-224` (incumbent seating),
`src/mcrl/env/step.py:1094` (the only consumer of `HANDOVER_COST`).

## 3. C1/C3 early health audit (summary)

| Item | Finding | Class |
|---|---|---|
| Paper vs code formula, units, ratio-of-sums | identical; native bits; accounting identity enforced | CONFIRMED |
| lambda0 provenance | frozen value is B/E of an r1-greedy Main rollout, not of the (0.5,0.3,0.2) Main policy; C3 unaffected (lambda-invariant), C1 uniformly shifted; amend text, do not recompute | IMPLEMENTATION_DEFECT (low) + DOCUMENTATION_DRIFT |
| lambda0/kappa window | one 10-step 100-user TRAIN episode; within contract, undisclosed | DOCUMENTATION_DRIFT |
| State causality, action alignment, deployment availability | committed-previous-slot only; same live anchor; masks cross-checked | CONFIRMED |
| Source selection outcome-blind; all signs retained | yes | CONFIRMED |
| Gauge: one shared kappa, raw linear heads, literal head omission | yes; Q1/Q2 are mask-conditioned mean/max scorers, Q3 is not | CONFIRMED |
| Five-arm / confirmatory pairing | common keyed field excludes init seed and policy label; identity asserted per world | CONFIRMED |
| Leakage of r1/r2/r3, six-Q, coordinator, selector-only deployment | none on the endpoint path | CONFIRMED |
| Route-interaction diagnostic reports only C1's conditional margins | C3's `(Q1+Q3)-Q1 = -10.286%` derivable but unsurfaced | DOCUMENTATION_DRIFT |
| `CONFIRM_C1` `+254.596%` | equals `FULL/(Q2+Q3)-1`, the weakest arm; same head gives `+169.7%`, `+49.2%` in other contexts | LIMITED_TO_OLD_Q2_CONTEXT |
| `CONFIRM_C3` `+21.970%` / `+21.216%` | both with old Q2 present in both arms; Q2-free evidence points negative | LIMITED_TO_OLD_Q2_CONTEXT / NEEDS_NEW_C2_INTEGRATION |
| Public docs still describe motion-one as provisional | presentation layer, figure handoff | DOCUMENTATION_DRIFT |
| Retired estimand modules importable (`ee_axis_targets.py`, V0.2 function) | not on any active path | DOCUMENTATION_DRIFT |

Full table with file:line evidence: `artifacts/fable-51-c2-cleanroom-20260902-r1/audit/c1c3-health-audit.md`.


### 3.1 Authentication of every cited number (independent recomputation from raw JSON)

| Claim | Claimed | Recomputed | Match |
|---|---|---|---|
| Five-arm FULL vs DROP-C1 / C2 / C3 / Main | +254.596% / -30.397% / +21.970% / -21.582% | identical; per-init and per-world counts identical; 10,000-replicate paired-world bootstrap intervals reproduced to 9-10 significant figures with the stored seeds | yes |
| Route interaction (Q1+Q3) vs Q3, (Q1+Q3) vs Q1 | +49.247%, -10.286% (3/3 lineages negative) | identical | yes |
| C3 confirmatory | +21.216%, [+18.619%, +23.996%], 30/30, 2/3 | identical (bootstrap seed 2026092599) | yes |
| V0.7 R13 pooled and per-lineage | +0.0465%; -0.0109% / -0.1544% / +0.3064%; 11/7 cells | identical from raw per-cell totals | yes |
| V0.7 R14 LOAO | 0/3 lineages beat the strongest null | identical from per-fold MSE | yes |

Seal files match `sha256sum` for the five-arm, route-interaction and confirmatory
artifacts. Two process gaps: the R13/R14 JSON files carry no seal file, and the
single-route arms `Q1` and `Q3` of the route-interaction diagnostic persisted only
pooled summaries (no per-episode rows), although `action_trace_diversity` records
90 episodes each. Pooled ranking, identical in every initialization for rank 1:
`Q1 > Q1+Q3 > Main > FULL > Q3 > Q1+Q2 > Q2 > Q2+Q3` (`Main` and `Q1+Q3` swap ranks
2-3 by initialization). Full table: `artifacts/fable-51-c2-cleanroom-20260902-r1/audit/number-authentication.md`.

## 4. Ranked C2 hypotheses (at most three)

### H-A (selected) — deterministic hold-horizon segment-timing surplus

- Causal path: action fixes the segment reference `G^T(theta(tau))`; under hold the
  recurrence power follows SGP4 geometry (T1), may cross `p_max` (T2), and, as the beam
  max, sets `sqrt`-shaped supply power and activation (focal half of T4).
- Target (native bits, fixed lambda0), offsets k = 1..3, hold censored at the cliff,
  non-focal context frozen at the committed previous slot:
  `zeta_2,u(a) = sum_{k=1}^{3} dt [ R_u^a(k) - lambda0 P_{u,a}(k) ]`
  with `R_u^a(k) = (B^w/(n_a+1)) log2(1 + p0 G_a(tau) path_a(t+k)/(I_a+N))` and
  `P_{u,a}(k) = Psup(max(m_a, p_a(k))) - Psup(m_a) + [n_a=0](0.338 + [sat idle] 0.200)`.
  Pairwise label: `zeta_2,u(a) - zeta_2,u(a^M)`.
- Non-overlap: offsets 1..3 only (C1 is offset 0); focal-own rate and focal-marginal
  power only (C3 is non-focal rate at offset 0). Identity with the old full-window
  decomposition is deliberately not claimed; the realized cascade residual T5 is excluded
  because it is not decision-time predictable (V0.6 D1, V0.7 R14).
- Minimal decision-time state for Q2 (route view `s_{2,u}`): per legal action slot the
  three log gain ratios `log G_a(k)/G_a(0)`, the segment-start ratio for the continue slot
  (already present), the frozen-context `n_a`, `m_a`, satellite-active bit (already present
  as lagged blocks), and the three feasibility bits. All computable from SGP4 and the
  committed previous slot; no outcome is read.
- Outcome-blind source: every non-empty predecision anchor, every legal action, exact
  formula label; no rollout, so support is complete by construction and no selection by
  target sign is possible.
- Why predictable across anchors: the target is a deterministic function of the proposed
  state features; held-out failure can only come from function approximation, not from
  unobserved successor randomness.
- Fastest falsification: (i) prediction check — realised `p(t+1)` for users who hold must
  equal `p0 G(tau)/G(theta(t+1))` up to mobility drift; (ii) Stage 1b oracle screen with
  `Q2* = zeta_2/kappa` plugged directly into the deployed sum (contract sha256
  `2ac39ce557ed23596728d9a83619ce585c9c30e308559bd20f48d08c0e6d1545`).
- Main failure mode and hard stop: the deployed Q1+Q3 policy may already switch before the
  cliff so that the within-anchor spread of `zeta_2` is negligible relative to `Q1+Q3`
  (near-zero flip rate) or the frozen-context rate term may be dominated by unmodelled
  interference. Stop rule: `C2_DIRECTION_FAIL` in the Stage 1b contract; no rescaling.
- Cost: formula target and encoder ~1 day; census and oracle screen are non-heavy
  (minutes); a learner gate is hours on the server.


### 4.1 Convergence with the parallel routes produced today

Three independent design routes were written on 2026-09-02:

| Route | Top target | Relation to H-A |
|---|---|---|
| This controller (H-A) | deterministic hold-horizon segment-timing surplus, sum over k = 1..3, cliff censored to zero | - |
| Codex/Sol OPS-3 (`docs/MULTI-CATFISH-C2-OPS3-FRESH-REVIEW-2026-09-02.md`) | same physics; 1/H_t average, explicit -kappa per projected-outage offset, episode-end truncation, above-horizon indicator | same family; four declared differences, pre-registered as variant arms (Addendum A) |
| Other Fable clean-room review (`docs/MULTI-CATFISH-C2-FABLE-51-CLEANROOM-REVIEW-2026-09-02.md`) | offset-1 option value `V_C - V_M` with a declared common background; its own second-ranked idea is the deterministic hold-life surplus | different family; requires committing opening branches and a background/no-op semantics that its own review flags as unresolved (issues 1-3); not evaluated in this screen |

Two of three routes converge on the deterministic projected-persistence target.
Under deterministic geometry and a never-binding mask, the option-value target
reduces largely to the k = 1 slice of H-A with a max operator over fresh
alternatives, so it is not independent evidence for a distinct mechanism.

Design fork worth recording: OPS-3's `-kappa` outage term is a service-shaped
component inside the C2 target. The V0.3 contract places service protection in
the mask or in a separate acceptance guard, not in an optimized target, and at
the fixed lambda0 an unserved offset with `R - lambda0 P < 0` is genuinely
EE-preferable, so H-A keeps the pure fixed-multiplier surplus and relies on the
service guard. The matched screen adjudicates the two readings without post hoc
choice (Addendum A sha256 recorded in section 6).

### H-C (fallback subset) — energy-and-cliff-only hold-horizon surplus

Same mechanics as H-A with the rate term removed except for the cliff loss
(`- dt R_u(0)` proxy at censored offsets). Avoids the frozen-interference assumption;
rate-blind. Use only if H-A's census shows the rate term dominates the within-anchor
variance while the prediction check for the rate part fails.

### H-B (distinct mechanism) — dwell-boundary window control

Value of keeping the realised incumbent seated in slot 0 at the next boundary versus the
displaced fourth-best D2 satellite. Deterministic, but its magnitude is unmeasured, it
fires only every fourth step, and with `H^c = N = 4` no existing horizon observes it.
Requires its own census (window-quality gap at boundaries) before it can be ranked above
H-C.

Rejected classes: any realized successor residual (T5), any handover-count or `phi1/phi2`
proxy (no B/E path), any coordinator, veto, route weight, second argmax, or post-training
mechanism.

## 5. Stage 1 mechanism census (results)

Bounded non-heavy development census, run locally (173.6 s rollout + 8.6 s analysis).
Design: six fresh TRAIN worlds (seeds 2026090211-2026090216, verified unused) x three
frozen Q1/Q3 lineages (2026092101-03, Q3 rung 100), behaviour policy = the frozen
`Q1+Q3` argmax (byte-identical to the five-arm `DROP_C2` arm on 2000/2000 decisions),
18,000 predecision anchors, 468,391 legal (anchor, action) pairs, lambda0 and kappa reused
from the sealed constants, no TEST, no gradient, nothing written into the repository.
Outputs: `artifacts/fable-51-c2-cleanroom-20260902-r1/census/`.

| Census item | Result | Reading |
|---|---|---|
| Coverage | 0 empty masks; 28 legal actions at 71.7% of anchors, 21 at 28.3% (one unoccupied satellite slot) | complete native support by construction |
| Geometry headroom | `G_a(k)/G_a(0)` median 1.354 / 1.734 / 2.009 at k = 1/2/3; p5 0.93-1.04, p95 6.6-43 | strongly action-specific; holding usually gets cheaper |
| Cliff incidence | 1.96% of legal actions infeasible by k = 1, 1.98% by k <= 3; incumbent infeasible at k = 1 in 0.038% of anchors | the cliff is real but rare under the trained policy; the operative channel is the power slope, not the cliff |
| Within-anchor spread | std(zeta_2/kappa) median 1.72 vs std(Q1+Q3) 0.245, ratio **6.92**; nonzero range at **100%** of anchors; corr with Q1+Q3 median 0.545 | decision-time discriminability that every realized-residual C2 lacked; scale is ~7x Q1+Q3 |
| Positive alternatives | a legal action beats the Q1+Q3 argmax on zeta_2 at **62.4%** of anchors; median best gain **0.52 kappa** (mean 1.12, p95 3.9) | material projected headroom |
| Oracle flip rate | argmax(Q1+Q3+Q2*) differs from argmax(Q1+Q3) at **57.0%** pooled (0.608 / 0.532 / 0.571 per lineage); 51.6% at x0.5, 59.6% at x2.0, 33.2% at a spread-matched x0.145 | high exposure, insensitive to the multiplier: the ordering, not the weight, drives the flips |
| Components | rate/energy variance shares 49% / 51% (median); ranking equals the energy-only ranking at 0% of anchors | not a disguised energy or rate term |
| Hold realism | Q1+Q3 keeps the incumbent at 40.1% of decisions with an incumbent (~0.5 away from dwell boundaries, 0.08 at steps 4 and 8) | the hold premise holds for about half of non-boundary decisions |
| **Prediction check** | realised `p(t+1)` vs forecast for continuing links (t >= 1, n = 5,485): median rel. error **0.335%**, p95 1.45%, max 3.54%; switchers exact to 1e-16 | the deterministic channel is real and observable; residual = frozen-user-position drift |
| Step-0 exception | continuing links at t = 0 show 12% median error because the simulator warm-starts segment ages that decision-time state cannot see | episode-boundary artifact, 10% of anchors, not an H-A defect |

**Stage 1 verdict for H-A: PASS.** Real EE causal channel (T1, T4 focal half), action-specific
headroom at every anchor, decision-time observability confirmed by an out-of-sample physical
prediction, and a learnable deterministic ranking. Two risks are carried forward explicitly:
(i) the natural scale is ~7x the trained Q1+Q3 spread, so the unit-weight sum is Q2-dominated
(the OPS-3 variant's 1/H_t averaging is the pre-declared lower-exposure comparison; no other
scale may be introduced after outcomes); (ii) the hold premise is realised for roughly half of
non-boundary decisions under Q1+Q3, so the projected surplus overstates the realised temporal
effect unless the FULL policy itself holds more often (reported as a per-arm diagnostic in
Stage 1b).


## 6. Stage 1b oracle interaction screen (results, if run)

### 6.0 Runner validation (engineering smoke, seed 2026090299, one lineage; not a preregistered outcome)

The independent second implementation of the H-A oracle (`artifacts/fable-51-c2-cleanroom-20260902-r1/oracle/run_v08_c2_oracle_screen.py`)
reproduced the census physics: recomputed opening gains match the observation to 2.6e-11;
realised `p(t+1)` on continued segments (t >= 1, n = 138) matches the forecast with median
relative error 0.42% and p95 1.35%; the P13 arm's action selection is identical to the sealed
five-arm `DROP_C2` path. Per-episode cost 7-12 s including the oracle (+0.6-0.9 s).

The smoke's own EE numbers are mechanics evidence only and carry no decision weight. They are
recorded because the contract requires every run to be reported: on that one world, `Q2*`
alone reached 1.114e8 bit/J with served fraction 1.000 (Q1 alone 1.113e8, Main 0.904e8), and
the three directions read +12.9% (C2), -0.11% (C3), +1.16% (C1). Hold fractions were 0.15
for P123 versus 0.20 for P13 and 0.64 for Main: the oracle switches more often, not less,
because handover carries no physical cost in this simulator and a fresh segment on a
better-placed beam usually projects a higher rate than an aged low-received-power segment.
This is a legitimate consequence of the frozen physics but must be disclosed in any paper.

Source-closure note: the working tree has 23 modules added since the sealed V0.4 manifest and
`step.py`/`trainer_env.py` changed (additive counterfactual seams; the mirrored physics is
untouched), so strict cross-artifact source authentication cannot pass in this tree for the
five-arm runner or for this screen. Development runs record the failure verbatim and verify
gate seals, checkpoint hashes and the PREREG-TLE binding only. Any confirmatory run needs a
newly sealed source manifest.

### 6.1 Preregistered block (contract sha256 `2ac39ce557ed23596728d9a83619ce585c9c30e308559bd20f48d08c0e6d1545`; Addendum A sha256 `b538932006f7e597ee199fb0701a4473587afa81b4580ca76e1dff13f9ea7046`)

Six fresh TRAIN worlds 2026090221-2026090226, three frozen lineages, keyed field component
`V08_C2_ORACLE_SCREEN_V1` rooted on (component, evaluation seed) only. H-A block: 132
episodes, 1149 s. OPS-3 block: 72 episodes, 969 s. World identity across
the two blocks (start epoch, initial world/state/mask, fading-field digests): identical for
all six seeds. Old learned Q2 loaded: False. Runner sha256 `3cc504fd80047607e34cfd2a9c9c81a5167f4c3cff8f5ccc9b08688e66d91c92`.
Source closure: receipt-only (gate seals, checkpoint hashes and PREREG-TLE binding verified;
the strict cross-artifact source manifest cannot pass in this tree, note recorded verbatim in
both results). OPS-3 self-check `Q2*_OPS3 = Q2*_HA/3` where H_t = 3 and all chi = 1:
max relative error 2.61e-16 over 1318972 legal actions.

### 6.2 Arm table (pooled ratio of sums over 18 rows per route arm, 6 for MAIN)

| Arm | pooled EE (M bit/J) | served | hold | infeasible holds |
|---|---:|---:|---:|---:|
| P1 = Q1 | 117.82 | 0.99733 | 0.429 | 48 |
| P2 = Q2*(H-A) | 118.67 | 0.99783 | 0.147 | 39 |
| P3 = Q3 | 71.09 | 0.96633 | 0.065 | 606 |
| P12 = Q1+Q2* | 119.40 | 0.99783 | 0.175 | 39 |
| P13 = Q1+Q3 | 106.37 | 0.99772 | 0.361 | 41 |
| P23 = Q2*+Q3 | 118.06 | 0.99767 | 0.149 | 42 |
| P123 = Q1+Q2*+Q3 | 118.82 | 0.99767 | 0.182 | 42 |
| MAIN | 93.27 | 0.99833 | 0.625 | 10 |
| O2 = Q2*(OPS-3) | 113.36 | 0.99783 | 0.140 | 39 |
| O12 = Q1+Q2*(OPS-3) | 119.67 | 0.99789 | 0.252 | 38 |
| O23 = Q2*(OPS-3)+Q3 | 109.98 | 0.99800 | 0.123 | 36 |
| O123 = Q1+Q2*(OPS-3)+Q3 | 116.46 | 0.99778 | 0.252 | 40 |

### 6.3 Predeclared primary directions

| Direction | pooled | per lineage (%) | positive lineages | positive worlds |
|---|---:|---|---:|---:|
| H-A D-C2: P123 vs P13 | **+11.700%** | +12.492 / +10.670 / +12.001 | 3/3 | 6/6 |
| H-A D-C3: P123 vs P12 | **-0.485%** | -0.710 / -0.255 / -0.489 | 0/3 | 2/6 |
| H-A D-C1: P123 vs P23 | **+0.644%** | +0.322 / +0.947 / +0.666 | 3/3 | 4/6 |
| OPS-3 D-C2: O123 vs P13 | **+9.480%** | +9.823 / +8.478 / +10.195 | 3/3 | 6/6 |
| OPS-3 D-C3: O123 vs O12 | **-2.687%** | -3.356 / -2.073 / -2.638 | 0/3 | 0/6 |
| OPS-3 D-C1: O123 vs O23 | **+5.892%** | +5.181 / +6.284 / +6.208 | 3/3 | 6/6 |

### 6.4 Service guard S (pooled served fraction of the top arm not below each comparator, and >= 2/3 lineage contrasts nonnegative)

| Route | vs DROP-C2 arm | vs DROP-C3 arm | vs DROP-C1 arm | S overall |
|---|---|---|---|---|
| H-A (P123) | pooled -0.000056 (one user-step of 18,000), 2/3 lineages: **FAIL** | pooled -0.000167, 0/3: **FAIL** | +0.000000, 3/3: PASS | **FAIL** |
| OPS-3 (O123) | pooled +0.000056, 3/3: PASS | pooled -0.000111, 1/3: **FAIL** | pooled -0.000222, 1/3: **FAIL** | **FAIL** |

### 6.5 Mechanical decision strings (contract section 4, applied literally by the runner's report)

- H-A: **`C3_CONTEXT_FAIL`** (D-C2 passes pooled and 3/3; D-C3 fails pooled and 0/3; D-C1 passes).
- OPS-3: **`C3_CONTEXT_FAIL`** (same pattern; D-C3 fails by a larger margin).
- Addendum A: neither route reaches `PASS_STAGE1B`; no route is selected, no hybrid is formed, and no
  rescaling, horizon, outage-term or threshold change may be introduced against these outcomes.

### 6.6 Diagnostics (never decisional)

| Diagnostic contrast | pooled |
|---|---:|
| P123 vs MAIN | +27.396% |
| O123 vs MAIN | +24.864% |
| P1 vs MAIN | +26.325% |
| P2 vs P1 | +0.723% |
| P12 vs P1 | +1.339% |
| O12 vs P1 | +1.573% |
| P13 vs P1 | -9.716% |
| O2 vs P2 | -4.480% |

Paired-world bootstrap (2000 replicates, seed 2026090299, report only): H-A: D-C2 fraction positive 1.000, D-C3 fraction positive 0.080, D-C1 fraction positive 0.991; OPS-3: O123_vs_O12 fraction positive 0.000, O123_vs_O23 fraction positive 1.000.

Per-arm hold fraction fell from 0.62 (Main) and 0.43 (Q1) to 0.15-0.25 for every arm containing an
oracle Q2*: the oracle switches more, not less, because a handover has no physical cost in this
simulator and a fresh segment on a better-placed beam usually projects a higher rate than an aged
low-received-power segment. This must be disclosed in any paper that uses this mechanism.

Reading of the diagnostics (inference, labelled as such): Q1 and Q2* are largely redundant
(Q2* alone +0.72% versus Q1 alone; together +1.34%), so C1's marginal shrinks to
+0.64% beside the full-strength oracle and grows to +5.89% beside the one-third-strength
OPS-3 surface. Q3 is anti-complementary in every strong context on these worlds: -9.72% on top of Q1
(independent replication of the sealed -10.286%), -0.48% on top of Q1+Q2*, -2.69% on top of
Q1+Q2*(OPS-3). The weaker the Q2, the more Q3 hurts. O2 alone is -4.48% relative to P2 alone;
because O2 differs from P2 in the -kappa outage term, the episode-end truncation and the
horizon indicator together, this is consistent with but does not isolate the contract-based
argument that a service-shaped term inside a fixed-multiplier EE target moves the argmax away
from the EE optimum.


## 7. Decision

**Top C2 candidate (H-A): `REVISE` at the method level; the C2 formula itself is not revised.**

- Stage 1 (mechanism census): PASS. Stage 1b, C2 direction: PASS (+11.70% pooled, 3/3
  lineages, 6/6 worlds). Stage 1b, method gate: `C3_CONTEXT_FAIL`; service guard fails
  literally against the DROP-C2 arm by one user-step in 18,000 (2/3 lineages nonnegative) and
  against the DROP-C3 arm (0/3).
- Because the preregistered `PASS_STAGE1B` was deliberately conditioned on all three
  directions, this document authorizes **no Q2 learner, no source generation for training, and
  no episode run**. The C2 mechanism has passed every C2-local test that was pre-declared; what
  failed is a property of the frozen C3 in the new context. By contract the controller does not
  alter C1 or C3; the finding is escalated.
- `STOP` is not the correct label: no pre-declared C2 stop rule fired, and both independent
  formulations of the same physics passed their C2 direction in every lineage.
- `GO` is not the correct label: the binding goal is three positive marginals, and one is
  negative in 0/3 lineages in both formulations.

Statements the takeover prompt requires separately:

1. **Is V0.7 C2 retired?** Yes. So is the whole realized-successor-residual class (V0.3-V0.7).
2. **Is a new positive C2 physically plausible, merely unproven, or structurally impossible?**
   Physically plausible and now direction-validated at development level: the deterministic
   segment-timing channel exists, its forecast matches realised physics to 0.3% median error,
   it has action-specific headroom at every anchor, and the exact oracle adds +11.7% (H-A) /
   +9.5% (OPS-3) pooled EE on top of frozen Q1+Q3 in 3/3 lineages and 6/6 fresh worlds. It is
   not efficacy evidence: six development worlds, an oracle rather than a learned Q2, and no
   held-out confirmatory block.
3. **Do C1 and C3 remain trustworthy under their old frozen context?** Yes, as executed: no
   arithmetic, pairing, leakage or sign defect; every cited number recomputes. Both are
   `LIMITED_TO_OLD_Q2_CONTEXT`. In the new-Q2 context C1 stays positive (3/3 lineages, small
   beside H-A, +5.9% beside OPS-3) and C3 turns negative (0/3 lineages in both formulations;
   -9.7% on top of Q1 alone on fresh worlds, replicating the sealed -10.3%).
4. **What exact evidence is still required to trust all three together?** (a) A user decision on
   C3: accept a two-head result with C3 recorded as context-dependent, or open a new C3 design
   cycle whose target is complementary to what Q1+Q2* already capture; (b) then the Q2 learner
   gate (world/anchor-disjoint skill over zero and action-only nulls, calibration slope in
   [0.5, 1.5]); (c) a fresh matched 2^3 route-mask factorial integration screen with the three
   `FULL versus DROP-Cj` directions, the service guard and a sign-stability check across
   partner contexts (heavy, Ubuntu server, ~30 fresh worlds); (d) a preregistered confirmatory
   block with paired-world bootstrap and service non-inferiority.
5. **Is any 500/1500/3000/9000-episode run authorized now?** No.

Next executable step (non-heavy, read-only): none that this lane may take alone. The
decision that unblocks the ladder is the C3 decision above and belongs to the user. If the
user elects to continue the C2 lane independently of C3, the next step is the small Q2 learner
gate on formula labels (heavy: hours on the Ubuntu server), which would need its own frozen
contract; this document does not authorize it.

### 7.1 Patch plan for shared authority (proposed, not applied; this lane edits no shared file)

1. `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`: add a post-Stage-1b notice: C2 status
   `H_A_DIRECTION_VALIDATED__METHOD_GATE_C3_CONTEXT_FAIL__NO_LEARNER`; C3 status
   `C3_CONTEXT_DEPENDENT` with the fresh-world numbers above; V0.7 retirement unchanged.
2. `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md`: amend the lambda0
   sentence to state the actual calibration policy (r1-greedy Main rollout, objective weights
   (1, 0, 0), one 10-step TRAIN episode); do not recompute the constant.
3. `docs/MULTI-CATFISH-MCRL-V04-ROUTE-INTERACTION-DIAGNOSTIC-2026-09-01.md`: add the C3
   conditional margin `(Q1+Q3) - Q1 = -10.286%` that the artifact already implies.
4. `src/mcrl/env/link_budget.py:748-751`: the docstring claiming the feasibility gate is
   non-binding ("outage 0 of 12,000") is contradicted by `artifacts/probe-p7-main-arm-2026-08-23.json`
   (outage 0.076 under warm start); mark it stale.
5. `docs/MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md` lines 114-148 and the figure
   handoff: motion-one must not be drawn as the current C2 (already flagged by the authority).


## 8. Retained, retired, provisional, blocked

- Retained: C1/C3 bytes and their sealed blocks as old-Q2-context evidence; canonical EE;
  freeze/seal infrastructure; five-arm evaluator pattern.
- Retired: V0.7 motion-one learner and its three lineages; all realized-successor C2
  targets (V0.3-V0.7) as learner candidates; the old Q2 checkpoints.
- Provisional: H-A formula, its route view, and the Stage 1b contract.
- Blocked: any new learner until Stage 1 and Stage 1b pass; any FULL-versus-DROP claim
  until a fresh matched 2^3 integration screen; any 500+ episode run.

## 9. Files changed / deliberately untouched

Created by this lane (all new, isolated, Fable-prefixed):

- `docs/FABLE-51-C2-CLEANROOM-V08-DESIGN-DECISION-2026-09-02.md` (this file).
- `artifacts/fable-51-c2-cleanroom-20260902-r1/` with `MANIFEST.sha256` and `receipt.json`:
  `audit/` (C1/C3 health audit, EE causal map, number authentication), `census/` (script, result,
  report, raw arrays), `oracle/` (runner, report generator, smoke log, `stage1b-HA-20260902/`,
  `stage1b-OPS3-20260902/`, `stage1b-report.md`, README), `contracts/` (Stage 1b contract and
  Addendum A with their sha256 files).

Deliberately untouched: `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` and every other existing
document; every V0.3-V0.7 artifact (retained as negative evidence); the C1/C3 checkpoints and
the five-arm, confirmatory and route-interaction evaluators; the OPS-3 lane's files
(`docs/MULTI-CATFISH-C2-OPS3-*`, `src/mcrl/runtime/ee_axis_ops3.py`, `tests/test_w129_ee_axis_ops3.py`);
the ChatGPT review package; `src/**` and `tests/**`; `~/demo/tle_data`. No file was reset,
stashed, staged, committed, deleted or rewritten. The pre-existing dirty worktree state is
preserved.

Concurrency note: another Fable clean-room review (`docs/MULTI-CATFISH-C2-FABLE-51-CLEANROOM-REVIEW-2026-09-02.md`)
and the OPS-3 lane ran in parallel with this session; their outputs were read after they
appeared and are compared in section 4.1. The OPS-3 arms evaluated here implement this
controller's reading of the OPS-3 formula (Addendum A) and are not that lane's own result.

