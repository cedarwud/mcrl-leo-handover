# Slice B — channel, antenna, interference, bandwidth, bits (independent second opinion)

Auditor: Claude Opus 5, fresh context, 2026-09-08. Checkout `/home/u24/papers/mcrl-leo-handover` @ `31b214b`
(read-only; no git state changes; `git show` only). All numbers below were recomputed in this session with
`.venv/bin/python` against `src/mcrl/env/*`, not copied from the codex slice-B report. PA / system power is out
of scope except where beam power sets received signal.

Independent of the codex audit I confirm items 1, 2, 3, 4, 5, 6, 7 and 9 of its ranked table, **downgrade its
item 2**, **substantially raise its item 4**, and add two findings it did not carry (B-13 physics-side 10°
shadow fallback; B-14 the ceiling falsification of the documented 16.4 dB).

---

## 1. Summary table (ranked by impact on EE / policy comparison)

| # | Assumption | Implemented | Docs | Standard status / what it distorts | Magnitude (measured here) | Verdict |
|---:|---|---|---|---|---|---|
| B-1 | Segment-anchored gain inversion `p(t)=p⁰·G^T(θ(τ))/G^T(θ(t))`, reset to `p⁰` at every renewal | `link_budget.py:379-408`; `step.py:770-810`, `943-958` | defended `link_budget.py:213-252`; caveat `LINK-BUDGET-NOTES.md:240-250` | Non-standard forward-link normalisation. Wanted EIRP is frozen at `p⁰·G^T(θ(τ))` for the whole segment; a handover *discontinuously* rewrites it. Distorts EE, C1/C2/C3 marginals, every policy-vs-policy comparison. | KAT: `G_τ=2000, G_t=1000` → continue `p=1.650 W`, EIRP 1650; reset `p=0.825 W`, EIRP 825 → **exactly 3.010 dB step from bookkeeping alone**. Measured in-segment drop p50/p95/max = 0.026/0.277/0.718 dB (`LINK-BUDGET-NOTES.md:244-247`) | **FIX** |
| B-2 | `receive_gain_dbi` never consumes `RX_ENVELOPE_MIN_DEG = 2.498°`; the S.465-6 envelope is extrapolated below its own validity floor | `antenna.py:197-217` (no use of `:172-192`) | `antenna.py:176-180` says held at `G_R,max`; `LINK-BUDGET-NOTES.md:74-80` blesses 32 dBi at 1° | Direct code/docs/ITU-domain conflict, **non-conservative on interference**. P5 measures **71.6 %** of cross-satellite co-colour interference *power* below this angle (`artifacts/probe-p5-2026-08-23.json`). | Measured `G_R`: 0°→35.000, 0.759°→34.994, 1°→32.000, **2.498°→22.060** (−12.94 dB vs the documented hold), 5°→14.526. Bounding the correction with P4's intra-fraction: mean link −2.4 dB SINR, p05-intra link **−9.5 dB** | **FIX** |
| B-3 | Candidate `γ` is mixed-time: current θ(t), **previous-step** radiating set/powers/satellite positions, `p⁰` for every candidate incl. the incumbent | `step.py:1200-1314`; `interference.py:445-450`, `454-550` | provenance string declared `interference.py:445-452`, carried to PREREG | A declared causal feature, not physical SINR. It is also the block a learner ranks actions on. Distorts training signal and action ranking. | 1 decision = 30.08 s of lag; `two_satellites_one_cell_step_fraction = 0.8` (P4) so the previous set is usually *not* the current one | **FIX** (relabel + fix B-13) |
| B-4 | Observation fading and physics fading are **independent keyed draws** for the same slot | `step.py:903` (`event="physics"`) vs `1230,1278` (`event="observation"`); `keyed_fading.py:137-150` | `prereg.py` records the observation grain only | Policy can select on a draw that is independent of what executes: winner's-curse noise, not channel-aware control. | K = 20 dB → Rician spread ≈ ±1 dB, so the selectable noise is small; shadow σ 1.6–3.6 dB is the larger part | **FIX** (or declare as a deliberate no-CSI design) |
| B-5 | Physics-side shadow σ falls back to the **10° row** for every (user, satellite) pair not in that user's own 4-slot window | `step.py:1548-1558` (`np.full(users, 10.0)`), consumed at `903` → `keyed_fading.py:127` | `step.py:1349-1351` calls 10° "its most pessimistic" | **Wrong, and broader than the candidate-side case.** σ(10°) = 1.9 dB is the second-*lowest* entry; max is 3.6 dB at 80°. Applies to the realised interference sum, not only the candidate proxy. | Lognormal linear-mean uplift: σ=1.9 → +0.416 dB, σ=3.6 → +1.492 dB → interference mean understated by up to **1.08 dB** on affected paths | **FIX** |
| B-6 | Beam radiates `max_u p_{u,s,v}` while each user's wanted term keeps its own `p_{u,s,v}` | `link_budget.py:439-465`; `interference.py:402-425` | disclosed and defended `interference.py:410-417` | Not one coherent transmitter model — but see the magnitude column: it is a tail, not a regime. | KAT: link powers `[0.825, 1.65]` → beam radiates 1.65 W, wanted keeps `[0.825, 1.65]`: 3.010 dB under-credit **for user 0 only**. P7 measures feasible link power p05 = p50 = p95 = **0.825 W** (mean 0.8238, max 1.643) and `link_over_beam_power_ratio = 1.000000000000` → the split is inert for >90 % of links | **DECLARE** (codex says FIX; see §5) |
| B-7 | Full-buffer, uncapped Shannon bits; no MCS / coding-gap / overhead ceiling | `link_budget.py:590-616`; `step.py:964-971` | undocumented | Shannon is an upper bound, not a realisable rate. Inflates the EE tail; the *median* is barely affected. | At P4's realised p50 SINR 6.604 dB → SE 2.478; p95 19.61 dB → **SE 6.53**, i.e. a 256QAM-r5/6 ceiling (~6.6) binds only the top ~5 % | **SENSITIVITY** |
| B-8 | "Equal bandwidth split" is arithmetically full-band TDMA: full-beam noise, rate divided by load afterwards | `link_budget.py:590-616` + `step.py:214-217` | called "time-shared" `link_budget.py:596-598` | Legitimate as a declared TDMA baseline; it is *not* an FDMA split (noise and PSD would change). Creates a consolidation / weak-user-exclusion incentive that `r3` then has to fight. | KAT at SE=5: U=1/2/3 → 833.3/416.7/277.8 Mb/s per user, beam aggregate constant 833.3 Mb/s. Adding an SE=2 user to an SE=6 beam drops system throughput 6B → 4B (−33 %) | **SENSITIVITY** |
| B-9 | Shadow drawn per **(user, NORAD)**, so wanted and intra-satellite interference share one draw | `interference.py:183-247`, `_per_beam_column`; `keyed_fading.py:118-134` | rationale `interference.py:196-205` | Physically right (one path, one shadow) — but it means the model's only large-scale randomness **cancels out of the SIR** that dominates. | P4 mean intra fraction = **0.946**, p50 = 0.99999 ⇒ shadow moves only the ~5 % inter term and the noise term. Effective shadow influence on SINR ≪ σ | **DECLARE** |
| B-10 | Fading is i.i.d. per step; no temporal correlation | `keyed_fading.py:137-150` (key = event, step, NORAD) | grain described, correlation not | Branch-independent CRN is good practice; memoryless shadowing over 30.08 s is not a credible shadow process. Removes any predictive value from channel state. | A stationary user gets a fresh σ=1.9–3.6 dB draw every 30.08 s | **SENSITIVITY** |
| B-11 | Static earth-fixed 3-colour reuse, perfect orthogonality across all satellites | `link_budget.py:21-29`; `cells.py`; `interference.py:349-399` | reuse disclosed as not paper-backed `link_budget.py:24-26` | Colouring is algebraically correct; *global* colour alignment across independent Starlink satellites and zero adjacent-channel leakage are scenario assumptions. | Simultaneously divides B and N by 3 **and** deletes 2/3 of active beams from I. Consistent internally (rate uses B/3, noise uses kT·B/3) | **SENSITIVITY** |
| B-12 | Clear-sky only: gas + tropospheric scintillation; no rain, cloud, depolarisation | `link_budget.py:48-118, 329-359` | substitution disclosed `LINK-BUDGET-NOTES.md:257-303`; rain not mentioned | At 20 GHz this is not an availability model. Mainly moves absolute EE. | Deterministic non-FS loss is only 0.50 dB at 30° elevation (0.250 gas + 0.300 scint), 0.37 dB at zenith | **DECLARE** |
| B-13 | `T_sys = 242.294 K`, `σ² = kT·B/3` over 166.667 MHz | `link_budget.py:35-46, 367-372` | `LINK-BUDGET-NOTES.md:138-158` | Conventional and dimensionally correct; no elevation dependence, which is secondary. | Recomputed: N = **5.57539e-13 W = −92.5372 dBm**; G/T(35 dBi) = **11.1566 dB/K** | **KEEP** |
| B-14 | The documented SINR triple 11.7 / **16.4** / 19.0 dB | quoted `LINK-BUDGET-NOTES.md:235`, `README.md:33`, `CONTROLLER-FINDINGS-W17-2026-08-22.md:26` | — | **Not reproducible and not attainable.** See §3. | Noise-limited zenith-boresight ceiling is 17.16 dB at the corpus median altitude 485 km; a with-interference median of 16.4 dB would need a 23.7 dB CNR median | **FIX (retract)** |

---

## 2. Decisive evidence and known-answer tests

**B-1 (anchor).** `step.py:951-956` multiplies `link_power[uid]` by the *current* `field_now.transmit_gain`, which
cancels the recurrence denominator exactly: realised wanted EIRP = `p⁰·G^T(θ(τ))`, constant across a segment.
Interference uses `radiating.power_w = max_u p_u`, i.e. current geometry × segment-contaminated power
(`step.py:886-898` → `interference.py:277-323`). So a handover changes the wanted term *and* the beam's emitted
power in the same instant, for bookkeeping reasons. **KAT (ran):** `recurrence_power_w([2000],[1000]) = 1.650 W`,
EIRP 1650 W; restarting the identical physical link gives 0.825 W, EIRP 825 W — a 3.010 dB step with no physics
behind it.

**B-2 (receive envelope).** `RX_ENVELOPE_MIN_DEG` appears only in `prereg.py:428`, `probe_p5.py`, and tests — never
in `receive_gain_dbi`. The only clip is `[RX_GAIN_FLOOR_DBI, RX_GAIN_MAX_DBI]`, which holds 35 dBi below
`RX_ENVELOPE_SATURATION_DEG = 0.759°`, not below 2.498°. **KAT (ran):** `[0, 0.759, 1, 2.498, 5, 10, 48]°` →
`[35.000, 34.994, 32.000, 22.060, 14.526, 7.000, −10.000]` dBi. The documented behaviour requires the first four to
be 35.000. Magnitude: P5 says 71.6 % of cross-satellite co-colour interference power sits below 2.498°; P4 says
inter is 5.4 % of I at the mean and 57.6 % at the p05 intra-fraction link. Holding at 35 dBi (uplift ≤ 12.94 dB,
factor ≤ 19.7) gives I × 1.75 (−2.4 dB SINR) at the mean and I × 8.9 (**−9.5 dB SINR**) at the p05 link. This is
the largest *unbooked* interference error in the slice.

**B-3 / B-5 (mixed time, 10° fallback).** `_candidate_sinr` uses `self._previous_radiating` (`step.py:1222`) — its
stored powers *and* satellite ECEF — against current user positions, then draws `event="observation"` fading for
previous-only satellites with **no elevation map** (`step.py:1383-1388`), which lands on `keyed_fading.py:127`'s
`np.full(num_users, 10.0)`. Separately and more seriously, `_elevation_by_norad` (`step.py:1548-1558`) *initialises*
every satellite's whole `(U,)` column at 10.0° and only overwrites the users who carry that satellite in their own
window — and this object feeds the **realised** `event="physics"` draw at `step.py:900-905`. So most (user,
interferer) pairs in the physics interference sum are shadowed at σ = 1.9 dB regardless of true elevation.
**KAT (ran):** σ by elevation = 1.9 / 1.6 / 1.9 / 2.7 / 3.6 / 0.4 dB at 10/20/30/50/80/90°, with linear-mean uplift
+0.416 / +0.295 / +0.416 / +0.839 / **+1.492** / +0.018 dB. `step.py:1351`'s "most pessimistic" is false in both
directions. Fix: give a previous-only satellite its true elevation and assert 3.6 dB at 80°.

**B-4 (two draws).** `step.py:903` vs `1230/1278` differ only in `event`, and `keyed_fading._generator` hashes
`[version, root, event, step, norad]` — so the two are independent substreams by construction. **KAT:** identical
`(root, event, step, NORAD)` must reproduce bit-for-bit; changing only `event` must change the vector.

**B-6 (power split).** **KAT (ran):** `beam_power_w([0.825, 1.65], served, beam 0, 1) = [1.65] W` while
`wanted_power_w` keeps `[0.825, 1.65]` → 3.010 dB under-credit for the first user, every victim interfered at
1.65 W. But P7's realised distribution is p05 = p50 = p95 = 0.825 W: the max and the own-power coincide except in
a thin tail. The asymmetry is real and should be declared; it is not a several-dB regime.

**B-7 / B-8 (bits).** **KAT (ran):** `shannon_rate_bps` at SE 5 gives 833.3 / 416.7 / 277.8 Mb/s for U = 1/2/3 and a
constant 833.3 Mb/s beam aggregate — the arithmetic of TDMA, not of a bandwidth split. Assert `R(2^k − 1) = k·B/U`
for k = 10 and 20 to show there is no rate ceiling anywhere in the stack.

---

## 3. Tracing 16.4 dB → 6.6 dB

Receipts. The 6.6 dB side has one: `artifacts/probe-p4-2026-08-23.json` (prereg digest `0dd7f133…`, 8 epochs,
7894 served links, policy `stay-if-possible` seed 7) — SINR p05/p50/p95 = **−5.795 / 6.604 / 19.614 dB**,
`sinr_db_without_co_colour_sum` p50 = **13.841 dB**, `sinr_cost_of_interference_db` p50 = **7.345 dB**,
I/N p50 = 6.460 dB, mean intra fraction 0.946, 41.75 radiating beams/step. The 16.4 dB side has **no artifact at
all** — it exists only as prose in `docs/CONTROLLER-FINDINGS-W17-2026-08-22.md:26`, copied into
`docs/LINK-BUDGET-NOTES.md:235` and `README.md:33`.

Which term. Using `git show` on the commit that produced it (`a2687b5`, "Apply rulings F-1 and F-2", 2026-08-22)
against the probe commit (`8ba9ac1`, 2026-08-23):

1. **The wanted-signal chain is unchanged.** `p⁰·G^T(θ(τ))` anchor, boresight `_RX_GAIN_MAX_LINEAR`, FSPL,
   `A_zen/sin α`, Rician K = 20 dB, the P-10 same-satellite override and the `wanted/(I+σ²)` line are all present
   at `a2687b5` in the same form. **So the gap is not a channel-formula change.**
2. **The only channel-model delta is C-8.** At `a2687b5`, `SCINTILLATION_LOSS_DB = 0.0` and `SHADOWING_LOSS_DB = 0.0`
   were declared zeros summed into `total_path_loss_db`. Adding them costs a deterministic **0.12–1.08 dB** (L_c)
   plus a zero-median L_s. **≤ ~0.5 dB of 9.8 dB.**
3. **Interference is the dominant term in the P4 number and cannot have been in the 16.4 number.**
   13.841 − 7.345 = 6.50 ≈ 6.604: P4 is internally consistent, interference-limited. For 16.4 dB to be a
   *with-interference* median at the same 41-beam load, its zero-interference median would have to be ≈ 23.7 dB.
4. **That is above the model's own ceiling.** Recomputed here: `p⁰·G₀·G_R/σ² = 189.712 dB`, so the noise-limited,
   zenith, boresight, fading-free CNR ceiling is **19.58 dB at 367 km** (corpus p05 altitude), **17.16 dB at 485 km**
   (`EPHEMERIS-NOTES.md` measured median), **16.23 dB at 540 km** (early corpus), **13.03 dB at the superseded
   780 km**. 23.7 dB is unreachable at every altitude in the corpus. A *median* of 16.4 dB with interference present
   is therefore arithmetically impossible under the frozen constants.
5. **The residual ~2.6 dB (16.4 vs P4's interference-free 13.84) is an operating point, not physics.** Between the
   two measurements, `eddaf2b` / `357f580` (W-19, 2026-08-23) introduced the two-timescale D2 clock and
   warm-started segments. Warm start replaces the step-0 anchor `G^T(θ(t))` with a historical `G^T(θ(τ))`, and P7
   shows its cost directly: outage 0.001625 with `segment_warm_start="none"` vs **0.076** on the main arm — a 47×
   change from that switch alone. The epoch sets also differ (12 vs 8).

**Attribution.** ~0.3–0.5 dB C-8 losses; ~2–2.6 dB from the W-19 clock + warm start moving served geometry and the
segment anchor; the remaining **~7.3 dB is the co-channel interference cost that the 2026-08-22 number does not
carry**. The 16.4 dB figure is a stale, un-receipted, pre-W-19 quantity that the current code cannot reproduce and
that fails its own noise-limited ceiling. It should be retracted from `LINK-BUDGET-NOTES.md:235`, `README.md:33`
and the W-17 findings, and replaced by the P4 receipt. The "~700 Mb/s per user" in `LINK-BUDGET-NOTES.md:216-220`
is tied to the same stale SINR: at the realised p50 of 6.604 dB the per-user rate at U = 1 is 413 Mb/s, not 700.

What is still missing to settle it completely: no JSON receipt, seed, epoch list or policy name was ever written
for the 2026-08-22 run, so the exact 12-epoch geometry cannot be replayed. Re-running P4's harness at `a2687b5`
with the W-17 configuration would close the last ~2.6 dB; everything above it is already settled.

---

## 4. Code-versus-docs disagreements

1. `antenna.py:176-180` claims (3.10c) is "held at `G_R,max` by the clip" below 2.498°; `receive_gain_dbi` holds it
   only below 0.759°, and `LINK-BUDGET-NOTES.md:74-80` blesses the conflicting 32 dBi at 1°. Three sources, three
   behaviours.
2. `step.py:1349-1351` says the 10° shadow row "is its most pessimistic". `link_budget.py:101-106` gives 1.9 dB at
   10° and 3.6 dB at 80°.
3. `step.py:1553-1555` applies that same 10° fallback to the **realised physics** draw, not only to the candidate
   proxy; no document mentions it.
4. `prereg.py` records fading identity at observation grain and omits that execution is a separate `event="physics"`
   substream (`step.py:903`).
5. `LINK-BUDGET-NOTES.md:293-295` describes one sequential sorted-NORAD generator; `KeyedFadingField` uses a
   per-`(event, step, NORAD)` substream (`keyed_fading.py:137-150`).
6. `LINK-BUDGET-NOTES.md:235` / `README.md:33` publish SINR 11.7/16.4/19.0 dB; the only receipted measurement is
   −5.8/6.6/19.6 dB (§3). Same for the "~700 Mb/s" rate and for "outage 0.0000" (P7 measures 0.076 on the main arm).
7. "Equal bandwidth split" (`LINK-BUDGET-NOTES.md`) versus full-band noise + post-hoc `R/U` (TDMA) in code.
8. Full-buffer traffic, coding gap, link adaptation, pilot/control overhead and an SE ceiling are declared nowhere.

---

## 5. Where I differ from the codex slice-B audit

- **Its rank 2 (beam-power / wanted-power split) is over-rated.** The 3.01 dB fixture is correct but P7's realised
  link powers are p05 = p50 = p95 = 0.825 W and `link_over_beam_power_ratio` is exactly 1.0, so the asymmetry is a
  thin tail, not "several dB according to co-users' segment histories". I move it FIX → **DECLARE**.
- **Its rank 4 (S.465-6 floor) is badly under-rated.** Joined to P5's 71.6 % and P4's intra-fraction spread it is
  worth −2.4 dB of SINR at the mean link and −9.5 dB at the p05 link. I move it to **#2 overall**.
- **Its rank 3 misses half the defect**: the 10° fallback also contaminates the realised physics interference sum
  via `_elevation_by_norad`, not only the previous-only candidate path.
- **It does not test the documented 16.4 dB against the model's own ceiling**, which is what actually settles §3.

---

## 6. The three assumptions I would overturn first

1. **B-1 — the segment-anchored gain inversion and its renewal reset.** It is the only mechanism in the slice that
   changes wanted signal *and* radiated interference discontinuously for bookkeeping reasons, it manufactures a
   3.010 dB renewal step in a hand-computable fixture, and it sits directly under every handover-conditioned claim
   (C1/C2/C3 marginals, the C3-S +2.9 %). Nothing else in slice B can be trusted while it stands.
2. **B-2 — the unenforced `RX_ENVELOPE_MIN_DEG` floor.** The code, its own docstring, the notes and the tests
   disagree, the code's choice is the non-conservative one, and it governs 71.6 % of cross-satellite interference
   power — up to −9.5 dB of SINR on exactly the cell-edge / two-satellite users the coordination story is about.
   It is also the cheapest to fix and to pin with a four-point KAT.
3. **B-14 — the published SINR/rate figures.** 16.4 dB is un-receipted, unreproducible, and above the model's own
   noise-limited ceiling once interference is present. Any chapter, calibration or sanity check anchored on it is
   anchored on nothing; the receipted 6.604 dB (interference-limited, 7.345 dB of co-channel cost) is a different
   physical regime and changes what the paper is about.

Runner-up, if a fourth were allowed: **B-4 + B-5 together** — the policy ranks actions on an observation draw that
is independent of what executes, over an interference field that is one 30.08 s decision stale and shadowed at a
mislabelled 10° σ. That is the state the learner has been asked to learn from for two weeks.
