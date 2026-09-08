# Slice A assumptions register — geometry, ephemeris, mobility, time base

Independent second opinion (Claude Opus 5, fresh context, 2026-09-08). Read-only; no git state changed.
Fixture: local repo `/home/u24/papers/mcrl-leo-handover`, `.venv`, TLE archive `~/demo/tle_data/starlink/tle`
(377 files, 2025-07-27…2026-08-24; TRAIN = 167 dates). Episode starts drawn from the **frozen TRAIN
`EpisodeStartSampler`** at world seeds 2026090601…08, i.e. the same distribution the V0.23 plan uses.
Scripts under the session scratchpad; every number below is reproducible from them.

Impact codes: **L** absolute EE level · **P** policy-vs-policy · **M** C1/C2/C3 marginal · **T** training signal.
Codex verdicts I disagree with are marked **[Δcodex]**.

## Ranked summary

| # | Assumption | Implemented | Documented | Standard practice | Distorts | Magnitude (measured) | Verdict |
|--:|---|---|---|---|---|---|---|
| 1 | Probe P2's re-key rate is the rate at which a dwell boundary re-keys `j→cell`, so "largest N with re-key ≤ 5%" selects N=4 | `runtime/probe_p2.py:61-63`, `dwell.py:184-193`, `dwell.py:44-57` | `dwell.py:44-86` records **3.250 %** at N=4 | A selection statistic must not include events that cannot occur | L,P,M,T | The estimator counts the step-0 boundary, where `rekeyed` is all-False *by construction* (`dwell.py:186-190`). Undiluted rate at N=4 on the live clock = **4.942 %** (40 000 boundary-user events, σ=0.11 pp) vs 3.295 % with step-0 included — reproducing 3.250 % to MC error. N=4 clears its own 5 % ceiling by **0.058 pp**; at the corpus-p05 grid altitude 426 km it is **5.580 % → FAIL** | **FIX** |
| 2 | The dwell segment is short against the usable service window | `dwell.py:25-29,206-220`; `scenario.py:75-76` | `EPHEMERIS-NOTES.md:158-174` mandates the ≥10° 6.3 min window | Dwell must be short against the window in which the link is *admissible*, not merely visible | L,P,M,T | ≥10° window p50 measured **390 s** (doc 380 s ✓) → 3.24 segments. But live admission is D2 `slant<1050 km`, p50 **240 s** → **1.995 segments**: an N=4 earth-fixed anchor spans **half** a D2 admission window | **FIX** |
| 3 | One instantaneous snapshot represents 30.08 s | `scenario.py:313-351`; runner `:962-968` | integration rule undocumented | Zero-order hold needs a bounded within-slot variation | L, weakly P | Geometry moves a lot (see #4), **but Δt cancels in the estimand**: EE = Σ Δt·R / Σ Δt·P with one constant Δt. Residual ZOH bias in the transmit-power denominator = mean\_substep(p)/p(t\_end) = **1.0227** (p5/p95 0.932/1.114), i.e. the endpoint *under-charges* energy by ≈2.3 %, and it is **age-dependent**: 1.0227 at segment age 0 vs 1.0280 at age 1 → a **≈0.5 pp arm-dependent** component | **SENSITIVITY** **[Δcodex: FIX→SENSITIVITY; the ×2 integral test is wrong for this estimand]** |
| 4 | Within-slot geometry motion is negligible | as #3 | undocumented | — | L,P | Per 30.08 s step, sats ≥10° at both ends (n=1401): \|Δel\| p50/p95/max **3.53/12.56/22.94°**; \|Δslant\| **119/188/201 km**. All 28 candidate rows (n=56 000): \|Δθ\| p50/p95 **0.362/0.936°**, \|ΔG^T\| **1.65/8.17 dB**. Served row (slot 0 × anchor cell): \|Δθ\| **0.150/0.383°**, \|ΔG^T\| **0.256/1.03 dB** | **DECLARE** (confirms codex's numbers; the *served* row is 6× milder) |
| 5 | The size of the gain-inversion recurrence is a property of the physics | `step.py:783-822,1250-1265` | `step.py:36-37` | — | L,P,M,T | The recurrence's excursion is a pure function of how far θ moves in Δt: mean \|10log₁₀ G(τ)/G(t)\| = **0.482 dB after 1 step, 0.692 dB after 2, 0.578 after 3**. On the pre-2026-08-23 1 s clock it would be ≈1/30 of that. The "renewal premium" the whole audit was triggered by is **manufactured by the time base**, which was chosen for objective non-degeneracy (`constants.py:77-92`), never re-validated for the energy model | **FIX / cross-ref EE audit** |
| 6 | The simulator has one coherent visibility contract at 10° | `ephemeris.py:665-667`; `scenario.py:61-62,167`; `candidates.py:51-57` | `EPHEMERIS-NOTES.md:158-174`; `D2-NOTES.md:33-44` | One explicit eligibility contract | L,P,M,T | `EphemerisConfig.min_elevation_deg=10.0` has **no live consumer** (grep: only `as_dict`/manifest). Live shortlist floor 0° minus a 5° margin (**−5°**, ~815 sats/world); cell visibility floor **0°**; actual eligibility is D2 entry `slant<1050 km` = **19.69°/23.40°/27.65°** at 426/485/550 km | **FIX** |
| 7 | A dwell re-key is a bookkeeping event, not a physical one | `step.py:240-244,783-822`; `dwell.py:1-23` | `dwell.py:5-13` says only that the ledger must see the cell | — | L,P,M | `Segment.continues` keys on `(norad_id, cell_id)`. A boundary re-key moves the physical cell under a fixed action index → segment terminates → **p resets to p⁰ = 0.825 W with no handover decision and no handover energy**. Rate: 4.942 % per boundary × 2 re-keyable boundaries per episode ⇒ ≈**9.6 % of user-episodes** get a free renewal | **FIX** |
| 8 | D2 latches are fully initialised by a TTT-length prime | `d2.py:127-142,299-330`; `scenario.py:184-206,300-350` | `D2-NOTES.md:84-91` | A Schmitt latch needs history back to the last crossing | P,T | Confirmed and **quantified**: vs a 15-min causal tracker at the area centre over 4 worlds — causal 271 eligible, shipped prime 267, **4 false negatives (1.48 %)**. All 4 sit in the 1050–1150 km hold band (11 sats/world), whose margin is −50…+50 km, so §4A.3 margin ordering (`action_contract.py:213-224`) makes them **provably unable to reach the 4-slot window** | **DECLARE** **[Δcodex: FIX→DECLARE, unreachable]** |
| 9 | Prime and the step-0 sub-step loop share one continuous clock | `d2.py:322-329`; `scenario.py:189-194,313-324,343-350` | undocumented | — | P,T | Prime is stamped at tracker indices −2,−1 but at physical times start−1.28/−0.64 s; the linear index↔time map the live loop uses (`base = k·47`, window ends at the decision instant) puts those times at indices **+44,+45**. Physical time therefore runs **backwards by 28.16 s** at the seam and TTT is credited 46 steps early there. Steps k≥0 are self-consistent | **FIX** (new; codex saw the non-monotonicity, not the 46-step index error) |
| 10 | Users may be held fixed across the 47 sub-steps | `scenario.py:198,328` | `step.py:1414-1422` claims the omitted user motion is **2.5 %** of \|Δθ\| | — | L,P | User motion per step = 30 km/h × 30.08 s = **250.67 m**, subtending **0.0297°** at 483 km. Measured \|Δθ\| p50 is **0.362°** (all rows) / **0.150°** (served row) ⇒ the true ratio is **8.2 % / 19.8 %**, not 2.5 %. Also the users are pinned at the **end-of-interval** position while the satellites sweep the whole interval (`scenario.py:218` steps mobility *before* `_resolve`) — a systematic ~125 m lead | **DECLARE** |
| 11 | The 30 s coarse shortlist has a proven 5° margin | `ephemeris.py:621-650` | `EPHEMERIS-NOTES.md:158-168` gives per-pass max rates 0.70–0.82 °/s | Coarse screening needs a dense-scan equivalence test | P,T | Rationale text ("≈0.06 °/s") is **wrong by ~7×**: measured per-decision-step rate p50/p95/max = **0.117/0.418/0.763 °/s**. But a dense 0.640 s scan (≥0°) over the episode window found **0 satellites the coarse shortlist missed** across 4 worlds — long passes save it | **DECLARE** (fix the comment) **[Δcodex: SENSITIVITY→DECLARE]** |
| 12 | "Fresh worlds" are independent draws keyed by `world_seed` | `step.py:414-452,534-536`; runner `:1253-1266,1330-1346` | runner `:1090-1092` says "fresh real environment" | Worlds should be pure functions of their key | statistics, reproducibility | Confirmed: the segment-age stream is restored across worlds, so world *k*'s ages depend on all earlier worlds. **But the draw is `rng.integers(0,10,size=100)` exactly once per episode (`step.py:1391-1406`), policy-independent, and all four arms consume the same stream in the same world order ⇒ CRN across arms is intact.** The 75/9000 repeated start epochs are ordinary birthday collisions (167 dates × 2873 slots ⇒ E[collisions]≈74) and are correct sampling-with-replacement | **DECLARE** **[Δcodex: FIX→DECLARE; not an arm-comparison bias]** |
| 13 | Nearest TLE = most recent TLE | `ephemeris.py:97-159`; `tle.py:89-91` | `EPHEMERIS-NOTES.md:34-45`; `ephemeris.py:107-114` | Backtests normally forbid future elements | L,P | Absolute \|epoch−t\|, so up to 24 h of look-ahead. Declared, retrospective-geometry reading is defensible | **SENSITIVITY** |
| 14 | Mixed Earth/frame approximations are negligible | `constants.py:20-38`; `geometry.py:9-14,68-138,182-217` | declared in code, absent from both notes | WGS-72 SGP4 is right for TLEs; ITRF/EOP for high-fidelity ground | L | Reviewed `teme_to_ecef`, `teme_velocity_to_ecef` (ω×r present), `look_angles`, `local_km_to_ecef`, `julian_date`, `step_times` (fixed JD + advancing fraction). **No silent error found.** Declared bounds: ≈1.7 km ground-radius, ≤0.45 km UTC-as-UT1 | **KEEP** |
| 15 | Doppler can be ignored | no implementation; range rate only `geometry.py:141-156` | undocumented | Must be stated | L, feasibility | 20 GHz × 7 km/s ⇒ 467 kHz, 0.28 % of the 166.7 MHz reuse band | **DECLARE** |

## Per-item detail and known-answer tests

### 1. The N=4 selection rests on a diluted estimator (new — codex missed this)

`ProbeP2Accumulator` (`runtime/probe_p2.py:61-63`) does `if dwell.is_boundary: self.boundaries += users;
self.rekeys += dwell.rekey_count`. `DwellController.step` sets `rekeyed = zeros(...)` whenever
`previous is None` (`dwell.py:186-190`), which is exactly the step-0 boundary. With H=10 and N=4 the
boundaries are {0,4,8}; one third of the denominator can never contribute to the numerator.

Direct measurement (200 seeds × 100 users, frozen `MobilityConfig`, `build_cell_grid(483 km)`, r_cell = 13.998 km):

| N | re-key excluding step-0 | including step-0 (P2's estimator) | rule "≤5 %" |
|--:|---|---|---|
| 2 | 2.558 % | 2.046 % | pass / pass |
| 3 | 3.773 % | 2.830 % | pass / pass |
| 4 | **4.942 %** | **3.295 %** | **pass by 0.058 pp** / pass |

3.295 % reproduces the frozen 3.250 % to Monte-Carlo error, which identifies the estimator. The frozen
rule still selects N=4 at 483 km, but the grid altitude is itself **PROVISIONAL** and is open decision C-2
(`scenario.py:53-59`); at the corpus p05 altitude 426 km the honest rate is **5.580 %** and the rule selects
N=3. The selection is therefore knife-edge and depends on an undecided parameter.

**Known-answer test.** Ten steps, N=4, one user placed 1 m inside a Voronoi boundary and walking across it.
Boundaries {0,4,8}; require `rekeys/boundaries` computed over **{4,8}** only. Assert P2 reports 50 %, not
33.3 %. Separately assert `segments_per_service_window` is called with the live clock.

### 2. Dwell versus the window that actually admits the link

Longest-run measurement over a 3 h horizon at 10 s sampling, 2 worlds, complete passes only
(11 319 passes ≥10°, 6 767 passes with `slant<1050 km`): ≥10° window p50 **390 s**; D2-entry window p50
**240 s**, p90 260 s. `segments_per_service_window(N=4)` with the **live** 30.08 s clock:

* 378 s (the frozen justification) → **3.141**
* measured ≥10° p50 390 s → 3.241
* measured D2 admission p50 240 s → **1.995**
* shipped default `time_step_s=1.0` (`dwell.py:210`) → **94.5**

So the feasibility argument that "a dwell segment must be short against the window" holds only under the
window D2 does not use. Under the live admission rule the earth-fixed anchor is held for **half** the time
the satellite is admissible — 120.32 s of a 240 s window.

**Known-answer test.** `segments_per_service_window(DwellConfig(4), service_window_s=240.0,
time_step_s=DECISION_STEP_S) == 1.9946…`; make `time_step_s` a required keyword so no caller can inherit 1.0.

### 3–5. What the 30.08 s zero-order hold really costs

`aggregate_last_outcomes` (runner `:962-968`) accumulates `total_bits += Δt·Σrates` and
`total_energy += Δt·power` with one constant `Δt = driver.config.ephemeris.time_step_s`. Because the
endpoint is a **ratio of sums over the same Δt**, Δt cancels exactly. Codex's known-answer test
(452.4032 vs 904.8064, a factor of 2) measures an absolute integral this project never reports; it does not
bound the estimand. The bias that survives is the difference between `mean over 47 sub-steps` and `value at
the final sub-step` of the *nonlinear* rate and power functions.

Measured on the served row (slot 0 × anchor cell, 4 worlds × 10 steps × 100 users, n = 4000), with
p(t) = p⁰·G^T(θ(τ))/G^T(θ(t)) evaluated at all 47 sub-steps:

* `mean_substep(p) / p(t_end)` = **1.0227** (p5 0.932, p50 1.018, p95 1.114) — the endpoint under-charges
  transmit energy by ≈2.3 %. With the PA at ≈94.8 % of system power this is ≈2.2 % of the denominator.
* By segment age: **1.0227 (age 0) / 1.0280 (1) / 1.0253 (2) / 1.0217 (3)**. The age-0 case is the
  just-handed-over link, where p ≡ p⁰ exactly at the sampled instant. The ≈0.5 pp gap between age 0 and
  age 1 is an **arm-dependent** artefact at the same order as the +1.81 %/+2.9 % effects being chased.
* The recurrence excursion itself scales with Δt: mean \|10log₁₀ G(τ)/G(t)\| = 0.482 / 0.692 / 0.578 dB at
  ages 1/2/3. The mechanism is a creature of the 30.08 s clock.

**Known-answer test.** Freeze one (sat, cell, user) triple and one segment anchor. Assert
`Σ_{i=0}^{46} p(t_i)/47` and `p(t_46)` differ by the tabulated ratio, and that the reported EE is invariant
to Δt when rate and power are held constant (proving the cancellation) but *not* invariant when they are
recomputed per sub-step (isolating the real bias).

### 6. Three different elevation floors, none of them 10°

`ScenarioDriver.reset` passes `config.screen_min_elevation_deg` — the driver's own 0.0 default
(`scenario.py:61-62,167`) — to `shortlist_visible`, which then subtracts a 5° margin, so the tracked
universe is "ever above −5°" (measured **814.8 satellites/world**, of which 388 are above 0° and 187 above
10° at the decision instant). `_cell_visibility` defaults to `CELL_VISIBILITY_MIN_ELEVATION_DEG = 0.0`
(`candidates.py:51-57`). `EphemerisConfig.min_elevation_deg = 10.0` appears only in `as_dict()`.

Real eligibility is `D2Config`: entry `slant + 50 < 1100` ⇒ **<1050 km**, release **>1150 km**. Entry
elevation by altitude — **19.69° (426 km), 23.40° (485 km), 27.65° (550 km)** — matches `D2-NOTES.md:38-40`'s
own table. (Codex quoted the *release* column, 17.01/20.34/24.12°; the gate that admits is the entry column,
so the effective floor is 2.7–3.5° *higher* than codex reported.)

**Known-answer test.** Build a cell/satellite pair at exactly 5° elevation. Assert `_cell_visibility` is
False under a declared 10° service mask. Assert that changing `EphemerisConfig.min_elevation_deg` changes
the live shortlist, not only the manifest hash.

### 7. A dwell re-key is a physical event for the energy model

`Segment.continues` (`step.py:240-244`) requires both `norad_id` and `cell_id` to match; `_resolve_physics`
(`step.py:783-822`) and the commit loop (`:824-862`) drop the segment otherwise and restart the recurrence
at p⁰. `DwellController.step` rebuilds `anchor_cell_ids` from `CellGrid.anchor_cell_ids` at every boundary
(`dwell.py:184-190`), and `neighborhood_cell_ids` is a pure function of the anchor — so an index-stable
policy silently changes physical cell on 4.942 % of re-keyable boundaries. Over an episode that is
2 × 4.942 % ≈ **9.6 % of user-episodes receiving an uncommanded p⁰ renewal**, with the endpoint charging
zero handover energy. This is *not* independent of N: it is the term that makes the frozen "N ignores EE"
claim (`dwell.py:52-57`) false.

**Known-answer test.** Pin action index 0. At step 3 map it to (sat 1, cell 10), at step 4 to (sat 1, cell 11).
Require `INTRA_SATELLITE`, segment termination, and p = p⁰ exactly. Repeat at N=2 and compare reset counts.

### 8–9. D2 warm-up: two separate defects, one small, one exact

*Coverage.* `warmup_steps = max(ttt_steps,1) = 2`, so the prime sees 1.28 s of history. A causal 15-min
tracker vs the shipped path at the area centre, 4 worlds: **271 vs 267 eligible, 4 causal-only**. All four
are in the 1050–1150 km hold band (11 per world at t₀), whose `margin_km = 1100 − slant` lies in [−50,+50]
while the four slots fill by *descending* margin (`action_contract.py:213-224`) from ~267 candidates with
margins up to ≈+600 km. The false negatives cannot enter the action set: contract false, consequence nil.

*Index/time seam.* `prime()` calls `update(−2)` and `update(−1)` for samples at start−1.28 s and −0.64 s.
`_resolve` then runs indices 0…46 for samples at start−29.44 s…start. The live map is
`t = start + (index − 46)·0.64 s`, under which the two prime samples belong at indices +44 and +45. TTT is
computed as `step_index − started`, so at the seam a satellite entering during the prime carries
`started = −2` into the step-0 loop and latches at index 0 with `elapsed = 2 ≥ ttt_steps` — 46 sub-steps
(29.4 s) of credit it did not earn. Steps k ≥ 0 are internally monotonic and correct.

**Known-answer test.** Three samples at 1000 km then 100 at 1100 km: the causal tracker stays eligible; a
tracker primed only on the last two stays ineligible; require `reset()` to reproduce the causal result.
Separately assert that the tracker index of every prime sample equals `round((t − start)/0.64) + 46`.

### 10. Mobility is dynamic, slow, and mis-described

`RandomWanderingUsers` (`mobility.py:88-135`) = uniform scatter over 200 × 90 km, heading uniform on
[0,2π), per-step turn Uniform(−45°,+45°), speed 30 km/h, specular reflection at the rectangle edge with a
heading flip (`_reflect`, `mobility.py:138-173`). All **S**-level and disclosed; the reflection choice is
argued rather than silent. Live displacement: **250.67 m/step, 1002.7 m/dwell, 2256 m over an episode's nine
moves** — versus ~2000 km of satellite motion. The model itself is sound; its *documentation* is not (see
below), and the omitted within-slot user motion is 8.2 % of the candidate-row \|Δθ\| rather than the 2.5 %
the code claims.

### 11–15. The rest

Coarse shortlist: rationale wrong, conclusion verified (0 misses vs a 0.640 s dense scan, 4 worlds). World
independence: age stream carried, CRN preserved, epoch repeats legitimate. TLE acausality, Earth/frame
mixing, absent Doppler: as codex described; frames reviewed line by line with no undeclared error.

## Code-versus-documentation disagreements

1. `dwell.py:44-57` — "**3.250 %** re-key rate at N=4" is the step-0-diluted statistic; the boundary-conditional
   rate is **4.942 %**.
2. `dwell.py:52-57` — "the mapping deliberately ignores EE" is false while `Segment.continues` keys on
   `cell_id`: N sets how often the power segment is force-renewed.
3. `dwell.py:19-23` — "10 s of travel is 83 m against a cell radius of ~14 km"; live travel is **250.7 m per
   decision, 1003 m per dwell** (radius 13.998 km at 483 km is correct).
4. `mobility.py:66-68` — `step_km` docstring "30 km/h for 1 s is 8.33 m"; the property returns **250.67 m**.
5. `dwell.py:206-220` — `segments_per_service_window(time_step_s=1.0)` default; `tests/test_w05_dwell.py`
   exercises it without the argument (94.5 segments) while the live answer is 3.141.
6. `EPHEMERIS-NOTES.md:66` — "回合長度(10 s)"; an episode is **10 × 30.08 = 300.8 s**.
7. `ephemeris.py:625-627` — "≈0.06 °/s of elevation"; measured per-decision-step rate p95 **0.418 °/s**,
   max **0.763 °/s**, and `EPHEMERIS-NOTES.md:164-168` already records 0.70–0.82 °/s.
8. `ephemeris.py:665-667` — `min_elevation_deg = 10.0` documented as the screening floor; the live screening
   floor is `ScenarioConfig.screen_min_elevation_deg = 0.0` less a 5° margin.
9. `step.py:1414-1422` — "median per-step \|Δθ\| of 1.194° … a 2.5 % contribution"; measured medians are
   **0.362°** (all candidate rows) and **0.150°** (served row), so the contribution is **8.2 %–19.8 %**.
10. `D2-NOTES.md:84-91` — a TTT-length prime "settles the latches"; it covers 1.28 s and cannot reconstruct a
    receding Schmitt latch (1.48 % false negatives measured, all unreachable).
11. Runner `:1090-1092` "fresh real environment" describes object construction; the segment-age generator is
    inherited across worlds (`step.py:414-452`).
12. `tests/test_w02_tle.py:33-210` covers parsing, checksums, quarantine and archive membership only — no
    propagation-cadence, frame, visibility or dense-shortlist known-answer test exists anywhere in slice A.

## Verdict against the codex slice-A audit

| Codex claim | My verdict |
|---|---|
| "A single instantaneous value cannot represent 30.08 s" | **Confirmed in geometry, refuted in magnitude.** Δel p50 3.53°/step and ΔG^T p50 1.65 dB over all candidate rows reproduce codex. But Δt cancels in Σbits/Σjoules, so the ×2 integral test does not apply; the surviving bias is **+2.27 % common-mode** with a **≈0.5 pp arm-dependent** part. SENSITIVITY, not FIX. |
| "Dwell N=4 validated on a 1 s time base while the live base is 30.08 s" | **Confirmed and strengthened.** The helper default is 1.0 s and its test asserts 94.5 segments; the live figure is 3.141 against the ≥10° window and **1.995** against the D2 admission window. And the *selection statistic itself* is diluted — the honest N=4 rate is 4.942 %, clearing 5 % by 0.058 pp and failing at 426 km. |
| "Incoherent visibility contract (10° advertised, 0° shortlist, 0° cell, altitude-dependent D2)" | **Confirmed**, with one correction: the admitting gate is the D2 **entry** elevation (19.69/23.40/27.65° at 426/485/550 km), not the release elevation codex quoted. |

Two further codex verdicts I would downgrade: the D2 warm-up defect is real but **provably unreachable**
through §4A.3 margin ordering (DECLARE, not FIX), and the cross-world age stream **preserves CRN across
arms** so it is a reproducibility defect, not a comparison bias (DECLARE, not FIX). One codex item I would
upgrade: the coarse shortlist passed a dense-scan equivalence check here (0 misses), so only its comment is
wrong.

## The three assumptions I would overturn first

1. **"Probe P2 measured a 3.250 % re-key rate, so the frozen rule selects N = 4."** The estimator counts the
   step-0 boundary, which cannot re-key by construction. The boundary-conditional rate is 4.942 % — inside
   the 5 % ceiling by 0.058 pp at the *provisional* 483 km grid altitude, and 5.580 % (rule ⇒ N = 3) at the
   corpus p05 altitude. N was frozen on a statistic that does not measure what the rule names.
2. **"N is independent of the energy mechanism, and dwell is short against the service window."** `Segment.continues`
   keys on `cell_id`, so every re-key restarts the gain-inversion recurrence at p⁰ with no handover decision
   and no handover energy — ≈9.6 % of user-episodes. And a 120.32 s segment is **1.995** D2 admission
   windows (240 s p50), not the 3.14 the ≥10° justification claims.
3. **"A single instantaneous value biases the EE endpoint."** Overturn the *framing*, not the concern: Δt
   cancels in Σbits/Σjoules, so the exposure is a **+2.27 % under-charge of transmit energy** that varies by
   **≈0.5 pp with segment age** — i.e. an arm-dependent bias of the same order as the +1.81 %/+2.9 % results.
   And the recurrence excursion it interacts with (0.48 dB after one step) is itself ≈30× larger than it was
   on the 1 s clock: the "renewal premium" is a product of the 30.08 s time base, which was never
   re-validated against the energy model when it replaced 1 s.
