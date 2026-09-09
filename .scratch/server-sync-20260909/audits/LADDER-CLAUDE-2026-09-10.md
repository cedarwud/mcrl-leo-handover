Sealed tree confirmed untouched (`git diff -- src/` is empty). Here is the report in full.

---

# LADDER-INDEPENDENT — V025-ANGLE-RATE-TPC-TDM-ACM

`DIAGNOSTIC_NOT_CLAIM.` No training run and no policy run was performed. No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule was changed. Two counterfactual rules were evaluated on clearly separated, generated copies (`ladder/variant_ar.py`, `ladder/variant_batch.py`); nothing under `src/mcrl/physics_v025/` was written to.

---

## D3 — Verdict

**It is an artefact.** "A lightly loaded beam cannot be served" is not a consequence of the declared radio physics; it is created by a reference-frame mismatch between two lines — power is provisioned so that the *nominal* SINR equals the rate target exactly (`src/mcrl/physics_v025/architectures.py:392` and `:430`, batch twin `src/mcrl/physics_v025/batch.py:311-314` and `:366-374`), while the transmission mode is then selected from that same SINR *after* multiplying it by a sub-unity fade quantile, at

> **`src/mcrl/physics_v025/architectures.py:480`** — `m_tx = select_transmitted_mode(nominal_sinr, quantile)`
> → **`src/mcrl/physics_v025/acm.py:83`** — `return select_mode(nominal_sinr_linear * fading_product_quantile)`
> (dense twin: **`src/mcrl/physics_v025/batch.py:403`** — `predicted_sinr = nominal_sinr * quantile`)

The de-rating is applied at selection and never compensated at provisioning, so every link is demoted down the ACM ladder by the full fade depth (≈ 1.1–4.8 dB at α = 0.10). At occupancy 1 the rate target `Γ_r(1)` *is* the bottom rung of the ladder, so the demotion falls off the bottom and no mode exists at all. The total margin the provisioning rule leaves at occupancy 1 is **9.1621 × 10⁻⁹ dB** (measured, `ladder/margin_line.py`).

The per-beam power cap is **not** the cause at low occupancy: on the real panel below, removing the 1.65 W cap entirely restores **0 of 91,584** occupancy-1 no-mode instances.

### Why this is not simply "the declared design"

The honest counterargument is that both halves are declared — `Γ_r(n)` is the declared target and the α-quantile de-rating is the declared "causal margin-adjusted nominal view" (`acm.py:76`) — so their combination is the declared physics and the result follows necessarily. Three things defeat that reading:

1. `Γ_r(n)` is derived **purely from a rate requirement** (`acm.py:132-138`) with no margin term anywhere in it. No sealed constant allocates a fade margin to provisioning. `IMPLEMENTATION_MARGIN_DB = 1.7 dB` is already folded into every threshold (`acm.py:42`) and is a receiver implementation loss, not a fade margin.
2. The code itself states that it leaves no margin. The only headroom above the threshold is the `2×10⁻⁹` relative nudge, whose own comment (`architectures.py:425-429`) calls it "one negligible solver-scale step into the certified feasible half-space" — a numerical device, explicitly not a design margin.
3. The resulting service curve is **non-monotone in a physically impossible direction**. Verified on the sealed `AngleRateTPC_TDM` path (D1 §6): a beam with 13 users — which the model declares *infeasible*, `Γ_r(13) = None` — is forced to full cap power, selects 32APSK 4/5 and is **credited**, while a beam with 1 user is credited nothing. A model in which over-subscribing a beam thirteen-fold is the way to get it served is not describing radio propagation; it is describing a reference-frame slip.

---

## D1 — The causal chain, with citations and arithmetic

### 1. Per-user rate target and the multiplexing rule → required spectral efficiency

Equal-airtime TDM: a beam's decision interval is partitioned so each of its `n_b` members transmits alone over `1/n_b` of the airtime (`architectures.py:320-336` `_tdm_slots`; dense twin `batch.py:69-74` `_slot_grid`, applied at `batch.py:297-298`). Each member therefore radiates over the full beam bandwidth but only `1/n_b` of the time, so to deliver `r*` bit/s on average it must run at `n_b · r*` while it is on air:

`src/mcrl/physics_v025/acm.py:132`
```python
required_se = rate_target_bps * occupancy / full_bandwidth_hz
```
(docstring `acm.py:119-124` states TDM and FDM share this one expression: `full_bandwidth_hz / occupancy` is the effective airtime bandwidth.)

Occupancy is the count of live users on the beam (`architectures.py:728`; dense twin `batch.py:252`).

Sealed constants: `r*` = 50,000,000 bit/s (`constants_v025.py:47`), `B_beam` = 500 MHz / 3 = 166.666667 MHz (`constants_v025.py:23-25`).

| `n_b` | required SE (bit/s/Hz) |
|---|---|
| 1 | 0.3000 |
| 2 | 0.6000 |
| 3 | 0.9000 |
| 4 | 1.2000 |
| 12 | 3.6000 |
| 13 | 3.9000 |

### 2. Required SE → mode from the table; and what happens when none exists

Each MODCOD row `(name, η bit/symbol, ideal Es/N0 dB)` (`constants_v025.py:94-123`, ETSI EN 302 307-1 Table 13, SHA-256-pinned at `:130-132`) is converted at `acm.py:39-50`:

- `acm.py:41` `SE = η / (1 + ROLL_OFF)` with `ROLL_OFF = 0.20` (`constants_v025.py:43`)
- `acm.py:42` `τ_dB = ideal + IMPLEMENTATION_MARGIN_DB − 10·log10(1 + ROLL_OFF)` with the margin = 1.7 dB (`constants_v025.py:44`)

Verified over the sealed table (`ladder/arith.py`): **SE ∈ [0.408536, 3.710856]**, **τ ∈ [−1.441812460, +16.958187540] dB**. The lowest-threshold and lowest-SE row is the same row, QPSK 1/4.

Selection of the target mode — *lowest threshold* among rows that meet the requirement:

`acm.py:133-138`
```python
eligible = [m for m in ACM_MODES if m.spectral_efficiency_bit_per_s_hz >= required_se]
return min(eligible, key=lambda mode: mode.threshold_linear) if eligible else None
```

When no row meets the requirement (`required_se > 3.710856`, i.e. `n_b ≥ 13`): `rate_target_mode` returns `None` (`acm.py:138`) → `rate_target_sinr` returns `None` (`acm.py:149-150`) → the beam is flagged **forced** and its power is **pinned to the full per-beam cap**, not zeroed: `architectures.py:741` `forced.append(gamma is None)` → `_solve_power` `architectures.py:393, 431, 433` `updated[forced] = caps[forced]` / `power[forced] = caps[forced]`; dense twin `batch.py:121, 302, 316, 376, 382`. It is excluded from the feasibility flag only (`batch.py:446`, `architectures.py:751-763`) — **it still transmits and can still be credited**.

The target SINR is the selected mode's threshold, floored by the separately frozen PHY service boundary:

`acm.py:155`
```python
return max(mode.threshold_linear, SINR_MIN)
```
with `SINR_MIN_DB = −1.441812460` (`constants_v025.py:48-49`). Measured: `SINR_MIN / τ_min − 1 = 1.0966 × 10⁻¹⁰` — i.e. `Γ_r(1)` and the bottom rung are the same number to within one part in 10¹⁰.

**Γ_r(n) over the sealed constants** (measured, `ladder/arith.py`), with "headroom" = decibels of ladder that exist *below* the operating point:

| `n_b` | required SE | `m_target` | `Γ_r(n)` dB | headroom below (dB) |
|---|---|---|---|---|
| **1** | 0.3000 | **QPSK 1/4** | **−1.4418** | **0.0000** |
| 2 | 0.6000 | QPSK 2/5 | 0.6082 | 2.0500 |
| 3 | 0.9000 | QPSK 3/5 | 3.1382 | 4.5800 |
| 4 | 1.2000 | QPSK 3/4 | 4.9382 | 6.3800 |
| 5 | 1.5000 | 8PSK 2/3 | 7.5282 | 8.9700 |
| 6 | 1.8000 | 8PSK 3/4 | 8.8182 | 10.2600 |
| 8 | 2.4000 | 16APSK 3/4 | 11.1182 | 12.5600 |
| 10 | 3.0000 | 32APSK 3/4 | 13.6382 | 15.0800 |
| 12 | 3.6000 | 32APSK 8/9 | 16.5982 | 18.0400 |
| ≥13 | ≥3.9000 | **none** | — | (forced to full cap) |

This is the whole story in one column. **Occupancy 1 has exactly zero decibels of ladder beneath it.**

### 3. Power provisioning relative to the selected mode's threshold

Capped standard-interference fixed point, initialised at zero, targeting the threshold **exactly**:

`architectures.py:392`
```python
updated = np.minimum(caps, targets * (noise + coupling @ power) / direct)
```
then one final update and a single relative nudge into the feasible half-space:

`architectures.py:430-433`
```python
power = np.minimum(caps, targets * (noise + coupling @ power) / direct)
power[forced] = caps[forced]
power = np.minimum(caps, np.nextafter(power * (1.0 + 2.0e-9), np.inf))
power[forced] = caps[forced]
```
Dense twin: `batch.py:311-314` (loop), `batch.py:366-380` (final + nudge).

`direct` here is the **nominal** gain (`architectures.py:783`, `batch.py:260` `direct_nominal = arrays.nominal_gain[...]`) — i.e. the no-fade channel. So, when the cap does not bind,

> **nominal SINR = Γ_r(n) × (1 + 2×10⁻⁹) exactly.**

Measured total margin over the bottom rung at occupancy 1 (`ladder/margin_line.py`): `10·log10(Γ_r(1)·(1+2e-9)/τ_min)` = **9.1621 × 10⁻⁹ dB** (8.6859 × 10⁻⁹ dB from the nudge, 4.76 × 10⁻¹⁰ dB from the `SINR_MIN` rounding). There is no design margin. The provisioning rule is "hit the threshold, to nine significant figures."

### 4. The fading / quantile factor between provisioning and decoding

There are **three** distinct SINRs, and the quantile sits between the first two:

| | expression | citation |
|---|---|---|
| **nominal** (provisioning target) | `power · g_nominal / (N + I_nominal)` | `architectures.py:462-463`; `batch.py:398-402` |
| **predicted** (mode **selection**) | `nominal × q` | `architectures.py:475-480` → `acm.py:83`; `batch.py:403` |
| **realised** (mode **decoding**) | `power · g_realised / (N + I_realised)` | `architectures.py:481-483`; `batch.py:386-390` |

`q = fading_product_quantile(elevation_deg, α)` (`channel.py:303-307`) is the α-quantile of a 200,000-draw Rician × log-normal-shadow × scintillation product (`channel.py:279-300`, `FADING_QUANTILE_DRAWS = 200_000` at `channel.py:41`), cached on 0.5° elevation bins (`channel.py:259-265`). The operating α is 0.10 everywhere in this workspace (`witness/engine_harness.py:70`, `analysis/psi_witness.py:123`, `tests/physics_v025/test_stage4h_amendments.py:104`, `matrix.py` run settings).

Measured over all 161 sealed 0.5° bins in [10°, 90°] (`ladder/universality.py`):

- max `q` = **0.774949** (−1.1073 dB) at 90.0°
- min `q` = **0.328885** (−4.8296 dB) at 80.0°
- bins with `q ≥ 1`: **0 of 161**

The quantile is applied **only** to the selection SINR. It is never fed back into the provisioning target, and it is not what the decoder sees (the decoder sees the actual keyed fading). So the net effect of `q` is a pure, uncompensated demotion down the ladder.

Decoding then credits the *transmitted* mode's SE only if the realised SINR clears that mode's threshold (`acm.py:93-98`; `batch.py:417-419`), and credits 0 otherwise (`acm.py:97`).

### 5. What the per-beam power cap does when the required power exceeds it

`BEAM_RF_CAP_W = 1.65` (`constants_v025.py:34`). The cap is a `np.minimum` on the fixed-point iterate (`architectures.py:392, 430, 432`; `batch.py:311-314, 366-380`). When it binds, the power is clamped, the nominal SINR falls **below** `Γ_r(n)`, and the configuration is marked rate-target-infeasible (`architectures.py:751-763` `_target_feasibility`; `batch.py:446`, `cap_hits` at `batch.py:480-482`). **It does not zero the transmission** — a lower mode may still be selected and decoded.

Critically, the cap can only *reduce* the nominal SINR below `Γ_r(n)`. At occupancy 1 the selection already fails when the nominal SINR equals `Γ_r(1)` exactly, so cap-binding at occupancy 1 is strictly redundant.

### 6. The arithmetic at occupancies 1, 2, 3 and beyond

Selection at occupancy `n` yields a mode iff

```
Γ_r(n) · (1 + 2e-9) · q  ≥  τ_min = 10^(−0.1441812460)
⇔  −10·log10(q)  ≤  headroom(n) + 9.1621e-9 dB
```

i.e. **the fade depth in dB must not exceed the headroom column of the Γ_r table.** With the α = 0.10 fade depth spanning 1.1073–4.8296 dB:

| `n_b` | headroom (dB) | fade depth needed to survive | elevation bins (of 161) with a transmitted mode |
|---|---|---|---|
| **1** | 0.0000 | ≤ 9.2e-9 dB | **0 / 161** |
| 2 | 2.0500 | ≤ 2.05 dB | 6 / 161 |
| 3 | 4.5800 | ≤ 4.58 dB | 153 / 161 |
| 4 | 6.3800 | ≤ 6.38 dB | 161 / 161 |
| 5–12 | 8.97 … 18.04 | — | 161 / 161 each |

*(measured, `ladder/universality.py`)*

Verified end-to-end on the **sealed** `AngleRateTPC_TDM.radiate` path, single beam, no cross-beam interference, elevation 45° (q = 0.442076, −3.5450 dB), direct gain chosen so the occupancy-1 power is 1 % of the cap (`ladder/occupancy_sweep.py`):

```
  n        P_w  cap?   Gam_dB     m_target   nom_dB  pred_dB         m_tx  dec      SE
  1    0.01650 False   -1.442     QPSK 1/4   -1.442   -4.987         None False  0.0000
  2    0.02645 False    0.608     QPSK 2/5    0.608   -2.937         None False  0.0000
  3    0.04737 False    3.138     QPSK 3/5    3.138   -0.407     QPSK 1/4  True  0.4085
  4    0.07169 False    4.938     QPSK 3/4    4.938    1.393     QPSK 2/5  True  0.6578
  5    0.13016 False    7.528     8PSK 2/3    7.528    3.983     QPSK 3/5  True  0.9903
  6    0.17518 False    8.818     8PSK 3/4    8.818    5.273     QPSK 3/4  True  1.2396
  8    0.29750 False   11.118   16APSK 3/4   11.118    7.573     8PSK 2/3  True  1.6505
 10    0.53148 False   13.638   32APSK 3/4   13.638   10.093   16APSK 2/3  True  2.1977
 12    1.05071 False   16.598   32APSK 8/9   16.598   13.053   16APSK 5/6  True  2.7502
 13    1.65000  True      nan         None   18.558   15.013   32APSK 4/5  True  3.2930
 14    1.65000  True      nan         None   18.558   15.013   32APSK 4/5  True  3.2930
```

Four things to read off this table:

1. `nom_dB == Gam_dB` in every row: the provisioning rule leaves no margin.
2. The cap is at **1 % of its value** at occupancy 1 and does not bind anywhere below `n = 13`. The failure at `n = 1, 2` is not a power failure.
3. **`m_tx` is below `m_target` at every occupancy** — the demotion is systematic, not a corner case. At `n = 3` the beam "delivers bits", but it delivers the *bottom* mode QPSK 1/4 (SE 0.4085 against a target SE of 0.9000): each user receives 45.4 % of `r*`. The occupancy-1 case is simply where this same uniform ≈3.5 dB demotion runs out of ladder.
4. At `n ≥ 13` the required SE exceeds the table maximum, `Γ_r` is `None`, the beam is **forced to the full 1.65 W cap** — and consequently selects 32APSK 4/5 and **decodes**. Under the sealed rule an *overloaded* beam is served while a *single-user* beam is not.

---

## D2 — Quantified attribution on a real evaluated panel

### Panel

`ladder/real_panel.py` loads the immutable stage-4h prepared world tape `/home/sat/mcrl-v025-codex-ws-engine/.tmp/stage4h-formal/world-tapes/default-world-1.pickle` (domain `V025_PROBE_R2/world/1`, seed 3525272352645343090, 33 real steps, real Starlink TLE ephemeris via SGP4, 100 users) — the same world family the sealed calibration manifest used by `witness/engine_harness.py:21` is bound to. Every user is assigned to its nearest legal candidate beam (`tapes.py:892-904` `_legal_arrays_by_user`), and all 48 D2 boundaries are evaluated with `field="realised"`, `fading_quantile_alpha=0.10`.

Counterfactuals run on `ladder/variant_batch.py`, generated from the sealed `batch.py` by `ladder/make_variant_batch.py` with 17 named textual patches (run `diff -u src/mcrl/physics_v025/batch.py ladder/variant_batch.py` to audit). The variant at default settings was asserted **bit-identical** to the sealed `evaluate_ar_tdm_catalogue` on bits, transmissions, mode counts and max RF power before any counterfactual was run (`PARITY OK` in the run log).

**Panel size: 8 real steps × 48 D2 boundaries × TDM slots × 100 users = 275,616 transmission instances.** Occupancies realised by the nearest-beam assignment: {1, 2, 3, 4, 5, 7}.

### Baseline (sealed physics)

**207,607 of 275,616 transmission instances (75.32 %) produce no transmitted mode** (`m_tx is None`, i.e. `has_tx_mode` false at `batch.py:415`).

| occupancy | instances | no mode | % | served | cap-bound | forced (Γ = None) |
|---|---|---|---|---|---|---|
| **1** | 91,584 | **91,584** | **100.00** | **0** | 22,721 | 0 |
| 2 | 70,848 | 70,763 | 99.88 | 85 | 21,590 | 0 |
| 3 | 31,968 | 6,662 | 20.84 | 24,351 | 7,685 | 0 |
| 4 | 57,888 | 26,131 | 45.14 | 30,800 | 31,651 | 0 |
| 5 | 16,416 | 7,090 | 43.19 | 9,029 | 10,604 | 0 |
| 7 | 6,912 | 5,377 | 77.79 | 1,472 | 6,279 | 0 |

Every single-user beam in the panel — all 91,584 of them, across 8 real ephemeris steps and 48 boundaries — delivers nothing. Not 99.9 %. All of them. The three-user beams are credited in 76.2 % of instances (24,351 / 31,968).

### Attribution: no-mode instances remaining when each candidate cause is removed

The cap counterfactual is reported at `HOBS_REFERENCE_MAX_RF_W = 100.0 W` (`constants_v025.py:90`) rather than at an unphysical infinity, because at 100 W all 8 of 8 evaluated configurations return a valid solver certificate, whereas at 10⁹ W one of the eight diverges (`ladder/cap_sensitivity.py`). The two settings agree to within 3 % on every count that matters, and agree **exactly** on the one the verdict rests on.

| candidate cause | how removed | still no mode | restored | % |
|---|---|---|---|---|
| **1.** per-beam power cap binding | `beam_cap_w` 1.65 W → 100 W | 182,354 | 25,253 | 12.16 % |
| **2.** required SE > table maximum | — | **not present on this panel** | 0 | 0.00 % |
| **3.** selection running off the bottom of the ladder | remove the `× q` de-rating at `acm.py:83` / `batch.py:403` | 69,797 | **137,810** | **66.38 %** |
| **4.** provisioning leaving no margin | provision to `Γ_r(n)/q` instead of `Γ_r(n)` | 127,406 | 80,201 | 38.63 % |
| 1 + 4 jointly | cap 10⁹ W **and** `Γ_r(n)/q` | 75,440 | 132,167 | 63.66 % |
| **1 + 3 jointly** | cap 100 W **and** no de-rating | **35,638** | **171,969** | **82.83 %** |

Candidate 2 contributes exactly zero here: the maximum occupancy realised is 7, so `Γ_r(n)` is never `None` and `forced` is 0 in every row of the table above. (And on the synthetic sweep in D1 §6, candidate 2 *helps* — it forces full cap power and the beam decodes.)

### The same table, per occupancy — this is where the apportionment lives

| occupancy | base | cap → 10⁹ W | de-rating removed | `Γ/q` provisioning | cap + `Γ/q` | cap + no de-rating |
|---|---|---|---|---|---|---|
| **1** | **91,584** | **91,584** | 23,780 | 43,543 | 31,191 | 13,206 |
| 2 | 70,763 | 70,659 | 17,788 | 28,650 | 15,681 | 5,755 |
| 3 | 6,662 | 3,619 | 4,790 | 8,821 | 5,277 | 2,422 |
| 4 | 26,131 | 7,383 | 14,112 | 32,446 | 14,659 | 4,398 |
| 5 | 7,090 | 3,217 | 4,845 | 8,524 | 4,241 | 2,355 |
| 7 | 5,377 | 3,023 | 4,482 | 5,422 | 4,391 | 2,585 |

### The occupancy-1 answer, as a 2 × 2

All 91,584 occupancy-1 instances fail in the baseline. Removing each cause:

| per-beam cap | fade de-rating at selection | still no mode | restored |
|---|---|---|---|
| 1.65 W | on *(sealed)* | 91,584 | — |
| **100 W** | on | **91,584** | **0 (0.00 %)** |
| **10⁹ W** | on | **91,584** | **0 (0.00 %)** |
| 1.65 W | **off** | 23,780 | 67,804 (74.02 %) |
| 100 W | off | 14,256 | 77,328 (84.43 %) |
| 10⁹ W | off | 13,206 | 78,378 (85.58 %) |

**Raising the per-beam power cap by a factor of 61, or by a factor of 6×10⁸, restores exactly zero of the 91,584 occupancy-1 failures.** This is not a statistical near-miss; it is structural, and no solver pathology can be hiding a restoration behind it, since more power could only ever help. The cap can only pull the nominal SINR *below* `Γ_r(1)`, and the selection at `acm.py:83` already fails when the nominal SINR *equals* `Γ_r(1)`. Candidate 1 is not a sufficient cause at occupancy 1 and never can be.

The de-rating is a **necessary** cause: it is present in every failing instance, and removing it alone restores 74.0 % of them. The cap is a **contributing** cause only in combination — it restores 0 on its own but a further 9,524 instances (10.4 %) once the de-rating is gone, i.e. those are links genuinely too weak to reach the bottom rung at 1.65 W. That residual is real physics: a power-starved link at long slant range and low elevation. It accounts for at most 26 % of the occupancy-1 failures, and none of them would be reported as failures if the de-rating were provisioned for.

At occupancy 3 and above the ordering flips: the cap becomes the dominant cause (at occupancy 4, removing the cap restores 18,748 of 26,131 = 71.7 % at 10⁹ W, while removing the de-rating restores only 12,019 = 46.0 %). That is expected — occupancy 4 has 6.38 dB of headroom, comfortably more than the ≤ 4.83 dB fade depth, so a fully provisioned link there always has a mode and only power shortage can defeat it.

**Apportionment, stated plainly.** Of the 207,607 panel-wide no-mode instances (cap counterfactual at 100 W, all certificates valid):

| attributed to | instances | share |
|---|---|---|
| the uncompensated fade de-rating alone — **artefact** | 137,810 | 66.4 % |
| the per-beam power cap alone — **genuine power limitation** | 25,253 | 12.2 % |
| interaction, needs both removed | 8,906 | 4.3 % |
| survives both removals — genuinely infeasible link | 35,638 | 17.2 % |
| required SE above the table maximum | 0 | 0.0 % |

**All 91,584 occupancy-1 instances fall in the first row or its interaction with the second. None fall in the cap-only row.**

### Credited bits over the panel

| rule | credited bits | ratio to sealed |
|---|---|---|
| sealed | 2.346636 × 10¹¹ | ×1.000 |
| cap removed | 3.645223 × 10¹¹ | ×1.553 |
| `Γ_r(n)/q` provisioning | 5.724546 × 10¹¹ | ×2.439 |
| de-rating removed | 4.564817 × 10¹¹ | ×1.945 |
| cap + `Γ_r(n)/q` | 8.737548 × 10¹¹ | ×3.723 |
| cap + no de-rating | 6.492383 × 10¹¹ | ×2.767 |

The single uncompensated multiplication at `acm.py:83` is worth a factor of **2.44** in credited throughput on this panel once it is properly provisioned for — and the model's own energy accounting would charge the extra power for it.

### Sensitivity of the cap counterfactual (`ladder/cap_sensitivity.py`)

Raising a cap in a coupled standard-interference fixed point can make the iteration diverge, at which point the sealed solver marks the configuration invalid and freezes its iterate (`batch.py:317-320, 351`). This run checks whether the cap counterfactual is contaminated by that:

```
                    rule  valid_cfg  no_mode_tot  occ1_inst  occ1_no_mode
 base       (cap 1.65 W)    8/8            207607      91584         91584
 cf_a  100W (HOBS ref)      8/8            182354      91584         91584
 cf_a  1e9W                 7/8            179485      91584         91584
 cf_ac 100W (no derate)     8/8             35638      91584         14256
 cf_ac 1e9W (no derate)     7/8             30721      91584         13206
 cf_c       (cap 1.65 W)    8/8             69797      91584         23780
```

At 100 W every configuration converges (8/8 valid); at 10⁹ W one of eight diverges. The two settings differ by 1.6 % on the panel total and 7.4 % on the occupancy-1 both-removed residual, and are **identical** on the decisive cell: occupancy-1 no-mode under cap removal alone is 91,584 at 1.65 W, at 100 W and at 10⁹ W. The 100 W column is used for the apportionment above.

---

## D4 — The minimal physically defensible alternative provisioning rule

### The rule

One expression. Provision against the **same design quantile the mode selection is later judged at**:

```
target used by the power solver:   Γ_r(n)  →  Γ_r(n) / q
```
i.e. at `architectures.py:392` and `:430` (dense twin `batch.py:311-314` and `:366-374`), replace `targets` with `targets / quantile`, where `quantile` is the same `fading_product_quantile(elevation, α)` already computed at `architectures.py:475-478` / `batch.py:261-265`.

### Why it is the defensible one

Under the sealed rule the α = 0.10 quantile is a pure penalty: it lowers the selected mode without buying anything, because the *decoder* sees the actual fade, not `q`. Under `Γ_r(n)/q` the quantile recovers its stated meaning as a link-budget fade margin:

- selection SINR becomes `(Γ_r(n)/q) · q = Γ_r(n)` exactly, so **`m_tx = m_target`** and the beam is provisioned to actually deliver `r*`;
- decoding succeeds iff the realised fade `f ≥ q`, which by construction of `q` as the α-quantile is a **90 % link availability** — the design intent.

The alternative of simply deleting the de-rating at `acm.py:83` (measured in D2 as CF-C) is cheaper in power but is *not* defensible: it declares a mode the link cannot hold, and its decode failures are then real.

### Effect on the per-beam power cap

The provisioned power scales by exactly `1/q` at every occupancy — a uniform **+1.107 dB (best bin) to +4.830 dB (worst bin)** in RF power, ×2.26 at 45°.

Measured on a clearly separated copy (`ladder/cfd_sweep.py`; single beam, 45°, direct gain fixed so the occupancy-1 base power is 1 % of the cap; `r/r*` is the per-user delivered fraction of the rate target):

```
  n |     m_target  SE_tgt |   P_base         m_tx      SE   r/r* |    P_cfd     x  cap?         m_tx      SE   r/r*
  1 |     QPSK 1/4  0.3000 |  0.01650         None  0.0000  0.000 |  0.03732  2.26 False     QPSK 1/4  0.4085  1.362
  2 |     QPSK 2/5  0.6000 |  0.02645         None  0.0000  0.000 |  0.05984  2.26 False     QPSK 2/5  0.6578  1.096
  3 |     QPSK 3/5  0.9000 |  0.04737     QPSK 1/4  0.4085  0.454 |  0.10715  2.26 False     QPSK 3/5  0.9903  1.100
  4 |     QPSK 3/4  1.2000 |  0.07169     QPSK 2/5  0.6578  0.548 |  0.16218  2.26 False     QPSK 3/4  1.2396  1.033
  5 |     8PSK 2/3  1.5000 |  0.13016     QPSK 3/5  0.9903  0.660 |  0.29443  2.26 False     8PSK 2/3  1.6505  1.100
  6 |     8PSK 3/4  1.8000 |  0.17518     QPSK 3/4  1.2396  0.689 |  0.39627  2.26 False     8PSK 3/4  1.8568  1.032
  7 |   16APSK 2/3  2.1000 |  0.22361     QPSK 5/6  1.3789  0.657 |  0.50581  2.26 False   16APSK 2/3  2.1977  1.047
  8 |   16APSK 3/4  2.4000 |  0.29750     8PSK 2/3  1.6505  0.688 |  0.67296  2.26 False   16APSK 3/4  2.4723  1.030
  9 |   16APSK 5/6  2.7000 |  0.41066     8PSK 3/4  1.8568  0.688 |  0.92894  2.26 False   16APSK 5/6  2.7502  1.019
 10 |   32APSK 3/4  3.0000 |  0.53148   16APSK 2/3  2.1977  0.733 |  1.20223  2.26 False   32APSK 3/4  3.0861  1.029
 11 |   32APSK 5/6  3.3000 |  0.75942   16APSK 3/4  2.4723  0.749 |  1.65000  2.17  True   32APSK 4/5  3.2930  0.998
 12 |   32APSK 8/9  3.6000 |  1.05071   16APSK 5/6  2.7502  0.764 |  1.65000  1.57  True   32APSK 4/5  3.2930  0.915
 13 |         None  3.9000 |  1.65000   32APSK 4/5  3.2930  0.844 |  1.65000  1.00  True   32APSK 4/5  3.2930  0.844
 14 |         None  4.2000 |  1.65000   32APSK 4/5  3.2930  0.784 |  1.65000  1.00  True   32APSK 4/5  3.2930  0.784
```

Per occupancy, under `Γ_r(n)/q`:

- **n = 1**: power 0.0165 → 0.0373 W (×2.26). Cap **not** bound. `m_tx` becomes QPSK 1/4 — service is restored at the bottom rung, exactly as the target mode intends.
- **n = 2, 3**: ×2.26, cap not bound, `m_tx = m_target`, `r/r*` ≥ 1.
- **n = 4 … 10**: ×2.26, cap still not bound at this link strength; `m_tx = m_target` throughout.
- **n = 11, 12**: the cap **starts to bind** (multiplier compresses to ×2.17 and ×1.57), and the delivered fraction falls back to 0.998 and 0.915.
- **n ≥ 13**: no target mode exists at all, the beam is already forced to the cap, and the rule changes nothing.

The cap-binding occupancy is a function of link strength, not of the rule: the rule shifts the whole demand curve up by exactly `−10·log10 q` dB, so the set of geometries served without cap-binding shrinks by 1.1–4.8 dB of link margin.

**On the real panel this is not free, and I will not pretend otherwise.** With the 1.65 W cap left in place, `Γ_r(n)/q` provisioning is a large gain at low occupancy and a genuine loss at middling occupancy, because every user asking for 3.5 dB more power also *emits* 3.5 dB more interference into the coupled fixed point:

| occupancy | cap-bound instances base → `Γ/q` | credited base → `Γ/q` |
|---|---|---|
| 1 | 22,721 → 43,517 | **0 → 45,215** |
| 2 | 21,590 → 31,774 | **85 → 40,273** |
| 3 | 7,685 → 13,859 | 24,351 → 22,046 |
| 4 | 31,651 → 45,928 | 30,800 → 24,561 |
| 5 | 10,604 → 13,401 | 9,029 → 7,619 |
| 7 | 6,279 → 6,729 | 1,472 → 1,430 |

Net over the panel the rule still wins by a wide margin (credited bits ×2.439, D2 table), because occupancies 1 and 2 are 59 % of all instances. But the honest summary is: **the rule is an unambiguous repair at occupancies 1 and 2, and a power/interference trade at occupancy ≥ 3 that the 1.65 W cap makes adverse.** If the cap is also lifted to the HOBS reference the trade turns positive at every occupancy (`cf_ad` column in D2: occupancy 4 goes 26,131 → 14,659 no-mode).

That trade is a design decision for the model's owner, not something an audit should settle. What the audit does settle is that the *current* rule prices a single-user beam at exactly zero for reasons that have nothing to do with power.

No policy change was implemented in the sealed model.

---

## Reproduction

```
cd /home/sat/mcrl-v025-witness-ws
export PYTHONPATH=src
P=/home/sat/mcrl-leo-handover/.venv/bin/python

nice -n 15 $P ladder/arith.py            # D1 tables 2 and 6 (Gamma_r, ladder extents)
nice -n 15 $P ladder/universality.py     # 161 elevation bins, occupancy survival
nice -n 15 $P ladder/margin_line.py      # the 9.1621e-9 dB margin
nice -n 15 $P ladder/occupancy_sweep.py 45   # sealed AngleRateTPC_TDM occupancy sweep
nice -n 15 $P ladder/make_variant_batch.py   # regenerate the variant from sealed batch.py
diff -u src/mcrl/physics_v025/batch.py ladder/variant_batch.py   # audit the 17 patches
nice -n 15 $P ladder/cfd_sweep.py        # D4 sealed-vs-Gamma/q sweep
nice -n 15 $P ladder/real_panel.py 8     # D2 real panel (~5 min)
nice -n 15 $P ladder/cap_sensitivity.py  # uncapped-counterfactual sensitivity
```

`ladder/variant_ar.py` and `ladder/variant_batch.py` are the only files containing altered physics; both carry a `LADDER VARIANT — NOT THE SEALED MODEL` banner. `ladder/real_panel.py` asserts variant/sealed parity before running any counterfactual and aborts if it fails.

---

## Provenance of each statement

**Verified by running code** — every numeric table in D1 §2, §4, §6, all of D2, and the D4 sweep. Scripts: `ladder/arith.py`, `ladder/universality.py`, `ladder/margin_line.py`, `ladder/occupancy_sweep.py` (sealed path), `ladder/cfd_sweep.py`, `ladder/real_panel.py` (+ `ladder/variant_ar.py`, `ladder/variant_batch.py`, `ladder/make_variant_batch.py`).

**Derived on paper and then confirmed numerically** — the survival condition `−10·log10(q) ≤ headroom(n)`, and the claim that cap-binding at occupancy 1 is strictly redundant (the cap can only lower the nominal SINR below `Γ_r(1)`, and selection already fails at `Γ_r(1)`).

**Started and abandoned** — a second, synthetic multi-world panel (`ladder/panel.py`: five satellite elevations × beams of occupancy 1…14 × 48 boundaries, driven through the sealed scalar `AngleRateTPC_TDM` path) was launched and terminated after ~12 CPU-minutes without completing. It was superseded by `ladder/real_panel.py`, which uses real SGP4/TLE ephemeris and is strictly better evidence. **No result from it is reported here.** The file is left in place; its `parity_check()` against the sealed path does pass.

**Not attempted** — I did not measure what the `Γ_r(n)/q` rule would do to the model's energy accounting, objective `F`, or the coalition/`Ψ` decomposition. The RF power rises by a known factor (`1/q`), but the PA model (`batch.py:483-490`, `√(P·P_sat)/η`) is concave in `P`, so the joule cost does **not** scale by `1/q` and I have not computed it. Any claim about energy-efficiency consequences would be a guess.

**Inferred, not proven** — the *intent* behind `acm.py:83`. The code contains no comment explaining why the quantile is applied at selection but not at provisioning. I read it as a link-budget conservatism that was wired into one stage and not the other; it is possible it was intended as a deliberate pessimistic-selection rule. That reading does not change the measurements, but it changes whether one calls the result a bug or a design choice. What is not a matter of reading: under it, occupancy 1 is unserveable at every elevation and every geometry, and occupancy ≥13 is served.
