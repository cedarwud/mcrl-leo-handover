# Slice A assumptions audit — geometry, ephemeris, mobility, and time base

Read-only audit of `/home/sat/mcrl-leo-handover-e1`. No files or Git state were modified.  
Impact abbreviations: **L** = absolute EE level; **P** = policy-vs-policy comparison; **M** = C1/C2/C3 marginal; **T** = training signal.

## Ranked summary

| Rank | Assumption | Implementation | Documentation | Standard/literature status | Distorts | Magnitude | Verdict |
|---:|---|---|---|---|---|---|---|
| 1 | One geometry snapshot represents an entire 30.08 s slot | `constants.py:59-92`; `scenario.py:300-351`; physical runner `:954-978` | Integration rule undocumented | A zero-order hold is defensible only when within-slot variation is negligible; it is not here | L, P, M, T | Fixed audit fixture: elevation \|Δ\| p50/p95/max = 3.95°/14.66°/23.89°; slant change = 131/197/201 km; candidate transmit-gain \|Δ\| p50/p95 = 1.47/7.62 dB | **FIX** |
| 2 | Dwell feasibility was evaluated on the live clock | `dwell.py:206-220`; test `test_w05_dwell.py:203-226` | `dwell.py:25-29`; `EPHEMERIS-NOTES.md:158-175` | Dwell must be compared in seconds, not merely decision counts | L, P, M, T | Helper/test use the obsolete 1 s default: 378/(4×1)=94.5 segments; live value is 378/(4×30.08)=3.141 | **FIX** |
| 3 | “10° minimum elevation” is the live visibility rule | `ephemeris.py:659-680`; `scenario.py:61-76,162-168`; `candidates.py:51-57,341-367` | `EPHEMERIS-NOTES.md:174-175` uses a ≥10° service window | A minimum service elevation should be a single explicit eligibility contract | L, P, M, T | `EphemerisConfig.min_elevation_deg=10` is manifest-only; tracked-universe and cell floors are 0°. User eligibility instead comes from D2, roughly 17°–24° on release across measured shells | **FIX** |
| 4 | N=4 is an outcome-independent geometry choice | `dwell.py:41-85`; `scenario.py:352-388`; `step.py:783-862` | `prereg_draft.py:523-580` calls it independent of outcomes but records EE/power movement | With the anchored recurrence, any boundary-induced physical reassociation resets power; N therefore changes the renewal process | L, P, M, T | N=4 means 120.32 s identity/cell caching and ≈1.003 km user travel; recorded EE dynamic range changes 0.3%, power swing 5.4% | **SENSITIVITY** |
| 5 | D2 is fully initialized by a TTT-length warm-up | `d2.py:127-142,299-330`; `scenario.py:184-206,300-350` | `D2-NOTES.md:78-94` says warm-up settles the latches | A Schmitt latch requires enough history to determine which threshold was crossed last; TTT history alone is insufficient | P, T; possibly M | Ten-minute causal-history check found one false-negative eligible satellite among 327 eligible across four one-user fixtures | **FIX** |
| 6 | The baseline implements 3GPP Event D2 | `d2.py:1-38,200-211,255-261` | `D2-NOTES.md:11-31` admits candidate-side-only use | Candidate-only proximity gating is a project-specific selector, not the complete two-condition Event D2 | P, T | Can admit a candidate even when the serving-side D2 condition is false; dozens of eligible satellites make the gate mainly a ranking/filter mechanism | **DECLARE** |
| 7 | Users are effectively static | `mobility.py:37-68,96-135`; `scenario.py:217-219` | `mobility.py:1-24`; stale distance statement in `dwell.py:19-23` | Random wandering is under-specified by the source paper; the turn and reflection rules are project choices | P, M, T | 250.667 m per decision, 1.003 km per dwell, 2.256 km across the nine movements between ten observations | **DECLARE** |
| 8 | “Fresh worlds” are independent draws keyed by their world seed | world builder `:87-118`; physical runner `:1090-1092,1217-1268,1330-1346`; `step.py:414-452,526-536` | Builder does not disclose cross-world age state | Independent worlds should not contain state inherited from the preceding world; arms may intentionally use CRN | P, M, statistics | Epoch/mobility/fading are newly seeded, but segment-age RNG state is carried serially. Among 9,000 planned seeds, 75 start epochs repeat; repetitions themselves are valid sampling-with-replacement | **FIX** |
| 9 | Nearest TLE means the most recent available TLE | `ephemeris.py:97-159`; `tle.py:89-91` | `EPHEMERIS-NOTES.md:34-45` | Retrospective geometry may use nearest elements; an operational/backtest interpretation normally forbids future information | L, P | Up to 24 h of future-element look-ahead; reduces element age relative to past-only selection | **SENSITIVITY** |
| 10 | Mixed Earth/frame approximations are negligible at decision boundaries | `constants.py:20-38`; `geometry.py:9-14,68-138,159-217` | Mostly declared in code; absent from the two requested notes | WGS-72 SGP4 is correct for TLEs; high-fidelity ground geometry normally uses ITRF/EOP and an ellipsoid | L, P | Declared bounds: ≈1.7 km spherical-radius mismatch plus ≤0.45 km UTC-as-UT1 rotation, corresponding to an order-0.1° angular bound at 1,000 km slant | **SENSITIVITY** |
| 11 | The 30 s coarse shortlist has a proven 5° safety margin | `ephemeris.py:621-650`; `scenario.py:161-168` | `EPHEMERIS-NOTES.md:158-168` reports elevation rates up to ≈0.82°/s | Coarse screening needs a dense-scan equivalence test or a defensible kinematic bound | P, T | Code rationale says ≈0.06°/s, while measured 30.08 s changes reach 23.89°, far exceeding 5°. Long LEO passes make an actual miss unlikely but unproven | **SENSITIVITY** |
| 12 | Doppler can be ignored without stating a receiver model | No Doppler implementation found; range rate only at `geometry.py:141-156` | Undocumented | Link simulators may assume ideal frequency tracking, but must state it | L; feasibility | At 20 GHz and 7 km/s, \|f_d\|≈467 kHz, about 0.28% of the 166.7 MHz reuse bandwidth | **DECLARE** |

## Decisive evidence and known-answer tests

### 1. Within-slot geometry is not quasi-static

The clocks are arithmetically consistent: 47×0.640 s = 30.08 s, enforced at `scenario.py:84-98`. D2 receives all 47 propagations, but candidate geometry, gain, rate, and power use only the final decision snapshot (`scenario.py:318-351`). Evaluation then multiplies that instantaneous rate and power by 30.08 s (`v023_c1c2_successor_physical_runner.py:954-978`).

The fixed measurement used 2026-08-20 06:00 UTC. For 171 satellites above 10° at both ends, elevation and range moved materially. A 100-user, seed-2026090601 scenario had 2,800 candidates common to adjacent snapshots; off-axis \|Δ\| was 0.252° median and 0.844° p95, producing 1.47 dB median and 7.62 dB p95 transmit-gain movement. This is large enough to interact directly with the gain-inversion recurrence.

**Known-answer test:** let an endpoint field vary as `x(t)=t` over 30.08 s. Exact integral = 30.08²/2 = 452.4032; holding the ending snapshot gives 30.08² = 904.8064. Require substep integration or demonstrate an error bound on physical rates and power.

### 2. Dwell feasibility still uses the obsolete 1 s clock

`segments_per_service_window()` defaults to `time_step_s=1.0` (`dwell.py:206-220`). Its tests omit the argument and assert more than 90 segments per pass (`test_w05_dwell.py:203-226`). That tests the old clock while the frozen decision is 30.08 s.

The ≥10° window is itself optimistic for D2 eligibility: the documented release threshold corresponds to ≈17.0° at 426 km, 20.34° at 485 km, and 24.12° at 550 km (`D2-NOTES.md:33-44`).

**Known-answer test:** for `service_window=378 s`, `N=4`, and `dt=30.08 s`, require exactly `378/(4×30.08)=3.1410`, not 94.5. The test must pass the live clock explicitly.

### 3. Elevation has three conflicting meanings

The frozen manifest advertises 10° (`ephemeris.py:667-680`), but `ScenarioDriver` supplies its separate 0° default to the shortlist (`scenario.py:61-76,162-168`). Candidate-cell visibility also defaults to 0° (`candidates.py:51-57`). The 10° field has no live consumer.

Actual user eligibility is the D2 latch: enter below 1,050 km, remain latched until above 1,150 km. Consequently the service window is altitude-dependent and substantially narrower than the ≥10° window used to justify dwell.

**Known-answer test:** construct a cell/satellite pair with exactly 5° elevation. With a declared 10° service mask it must be false; `_cell_visibility()` currently returns true under its default. Separately assert that changing `EphemerisConfig.min_elevation_deg` changes the live mask, not only the manifest.

### 4. Dwell boundaries and the renewal premium are coupled

N=4 freezes both cell neighborhoods and four NORAD identities between boundaries (`scenario.py:360-388`). At a boundary, the same action index can name a new cell or satellite. Handover classification correctly uses physical `(norad_id, cell_id)` (`action_contract.py:398-455`), and the power segment continues only when both identities match (`step.py:224-244,783-862`).

Thus N is not isolated from the known non-standard recurrence: more or fewer boundary remappings change when power returns to `p0`. The recorded equality of handover rate across N does not establish absence of renewal bias.

**Known-answer test:** hold action index 0 constant. At step 3 map it to `(sat=1,cell=10)` and at step 4 re-key it to `(1,11)`. Require `INTRA_SATELLITE`, termination of the old segment, and—under current recurrence—power reset to `p0`. Repeat with N=2 and compare reset counts.

### 5. D2 warm-up does not reconstruct Schmitt-latch history

Priming covers only two 640 ms samples (`d2.py:127-142,299-330`). Step 0 then replays the preceding 29.44 s after that priming (`scenario.py:300-350`), so physical time is processed non-monotonically. More fundamentally, a receding satellite can remain between 1,050 and 1,150 km for longer than this reconstruction window after entering on approach.

A long-history versus normal-reset comparison found a receding-band satellite that should remain latched but was absent after normal reset. It did not enter the top-four window in that fixture, but the initialization contract is still false.

**Known-answer test:** feed a tracker three samples at 1,000 km to latch it, followed by 100 samples at 1,100 km. The causal tracker remains eligible. A new tracker warmed only on the final two or 47 band samples remains ineligible. Episode reset must reproduce the causal result.

### 6. “D2” is a custom half-event

The baseline deliberately omits serving-side D2-1/D2-3 (`d2.py:10-15,200-211`). Its `Ml2` is satellite slant range, a disclosed interpretation of “moving reference location” (`d2.py:17-29`). TTT semantics are otherwise internally coherent: close samples at 0, 0.64, and 1.28 s yield elapsed counters 0, 1, and 2, becoming eligible on the third sample (`d2.py:322-329,384-400`).

**Known-answer test:** use serving slant 1,000 km, candidate slant 1,000 km, and three satisfying candidate samples. Candidate-only code admits it; complete D2 must reject it because `Ml1−Hys > Thresh1` is false. Label the former “D2-derived candidate gate,” not full Event D2.

### 7. Mobility is dynamic but slow relative to satellite geometry

Users are uniformly scattered, turn independently by up to ±45° once per decision, move 30 km/h, and reflect at boundaries (`mobility.py:88-173`). They are held fixed throughout the 47 D2 substeps. The resulting omitted within-slot user motion is only 0.2507 km versus roughly 200 km satellite motion, but mobility can still cross a cell boundary and create an intra-satellite handover.

**Known-answer test:** with speed 30 km/h, heading zero, and no boundary encounter, require displacement `30×30.08/3600=0.2506667 km`; after four moves require 1.002667 km. A same-satellite cell re-key must classify as φ1, not “no handover.”

### 8. Worlds are fresh objects, not fully independent state draws

The plan assigns unique consecutive seeds and keyed-fading roots (`build_v023_c1c2_successor_world_plan.py:87-118`). The runner constructs a new environment and new epoch/mobility RNGs for each arm/world (`physical_runner.py:1217-1268`). However, it restores the preceding episode’s `age_rng_state` and saves it again (`physical_runner.py:1253-1266,1330-1346`). `StepEnvironment` explicitly defines this as cross-episode state (`step.py:414-452`).

Different arms within one world are intentionally paired CRN, which is correct. Different worlds are not fully world-keyed because world k’s warm-start ages depend on all earlier age draws and ordering.

**Known-answer test:** evaluate world B alone and after world A, keeping B’s world seed fixed. B’s epoch, mobility, and fading should match; its segment-age vector currently need not. Require every world-owned random field to be a pure function of `(world_seed, field_name)`.

### 9. TLE selection is acausal under an operational interpretation

Element age is absolute (`tle.py:89-91`), and the closest record may be after the simulated time (`ephemeris.py:104-114`). This is explicit, but the claim that past-only selection would double mean age is not a substitute for a sensitivity result.

**Known-answer test:** for one NORAD provide records at `t−20 h` and `t+1 h`. Current selection must choose `t+1 h`; a past-only arm must choose `t−20 h`. Report geometry and candidate churn differences without touching TEST.

### 10. Frame conversions are mostly declared, not silent

SGP4 correctly uses WGS-72 and emits TEME (`ephemeris.py:467-543`). TEME is rotated using GMST; UTC substitutes for UT1 and polar motion is omitted (`geometry.py:9-14,68-138`). Users and cells instead use a 6,371 km spherical Earth and a flat local-to-lat/lon conversion (`constants.py:20-29`; `geometry.py:182-217`).

**Known-answer test:** at GMST=90°, TEME `[1,0,0]` must become ECEF `[0,−1,0]`. A satellite directly above spherical ground must give elevation 90° and off-nadir 0°. Independently compare one full pass to an ITRF/WGS-84 reference and enforce the declared ≤1 km satellite-position budget.

### 11. Coarse shortlist safety is asserted, not demonstrated

The shortlist samples every 30 s and subtracts a 5° margin (`ephemeris.py:621-650`). Its comment estimates ≈0.06°/s, inconsistent with the project’s measured p95 rates of 0.70–0.82°/s (`EPHEMERIS-NOTES.md:158-168`) and the 23.89° maximum 30.08 s change in the audit fixture.

The long duration of a horizon pass probably prevents missed eligible satellites, but that is a different argument and lacks a dense-scan equivalence test.

**Known-answer test:** compare shortlist identities from 30 s sampling against 0.640 s sampling for complete episodes and all four documented epochs. Require the coarse set to be a superset of every satellite that becomes D2-eligible for any service-area corner.

### 12. Doppler is absent

Only geometric range rate is computed; no carrier-frequency shift or tracking residual reaches the link budget. Ideal frequency tracking is plausible, but presently implicit.

**Known-answer test:** at 20 GHz and radial speed 7 km/s, require raw Doppler magnitude `20e9×7000/299792458 ≈ 466,990 Hz`. If ideal compensation is assumed, the post-compensation residual fixture must be exactly zero and the assumption declared.

## Code-versus-documentation disagreements

- `EPHEMERIS-NOTES.md:65-66` calls an episode 10 s; code runs ten 30.08 s charged slots, totaling 300.8 s.
- `dwell.py:19-23` says “10 s of travel is 83 m”; live movement is 250.7 m per decision and 1.003 km per four-step dwell.
- `test_w05_dwell.py:203-226` validates 1 s dwell arithmetic and `>90` segments per pass; the live result for N=4 is 3.141.
- The same test’s prose says old rates select N=3 (`test_w05_dwell.py:233-246`), while its assertion and frozen mapping select N=4 (`:254-261`).
- `EphemerisConfig.min_elevation_deg=10°` is documented and serialized but does not control `ScenarioDriver` or candidate visibility.
- Dwell is justified using a ≥10° service window, while D2 supplies a materially higher, altitude-dependent effective user threshold.
- `D2-NOTES.md:84-91` says a TTT-length prime settles the latches; it cannot reconstruct a receding Schmitt latch whose entry predates the warm-up.
- “Fresh real environment” (`physical_runner.py:1090-1092`) describes object construction, not statistical state: the segment-age generator is inherited across worlds.
- `tests/test_w02_tle.py:33-210` thoroughly tests parsing, checksums, quarantine, and archive membership, but provides no propagation-cadence, frame, visibility, or dense-shortlist known-answer test.

## The three assumptions I would overturn first

1. **A single instantaneous rate/gain/power value can represent 30.08 s.** Measured geometry and gain movement are too large; this directly biases the EE endpoint and the anchored recurrence.
2. **N=4 was physically validated on the live time base and is independent of the energy mechanism.** Its feasibility test still uses 1 s, while boundary remapping changes recurrence resets and the renewal premium.
3. **The simulator has one coherent 10° visibility contract.** The advertised 10° setting is dead; the live system mixes a 0° shortlist, 0° cell visibility, and an altitude-dependent D2 service window.