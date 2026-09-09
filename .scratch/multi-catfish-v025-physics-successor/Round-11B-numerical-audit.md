# Round 11B — independent numerical and package-evidence audit

Date: 2026-09-09. Scope: read-only inspection of the supplied Round 11 package and deterministic scalar calculations. No simulator, learner, TRAIN/TEST panel, or quantile Monte Carlo was executed. No source-package code or sealed declaration was amended.

## Reproduction

Run `python r11b_scalar_check.py > r11b_scalar_check.json` with Python 3.10 or newer. The script uses only the standard library. It independently reconstructs the antenna pattern, noise, path budget, thresholds and mode decisions from declared constants; it does not import or execute the supplied figure generator. The accompanying JSON records all outputs.

The 28-mode threshold and efficiency data are from ETSI EN 302 307-1 V1.4.1, Table 13, printed page 36: normal FECFRAME, no pilots, ideal AWGN thresholds. The script applies the supplied project's 1.7 dB implementation allowance and 0.20 roll-off convention. The 28 entries are the DVB-S2 table, not the whole DVB-S2X catalogue.

## 1. Power reserve identity

Let the non-faded gain be h, fixed interference-plus-noise be D, the transmitted mode's decoding threshold be Gamma, and p0 = Gamma D/h. For a relative **power-gain** random variable G with continuous distribution, q = F_G^(-1)(0.1), and no binding power cap:

- Nominal SINR with p = p0/q is Gamma/q.
- Realized SINR is Gamma G/q.
- Decoding occurs exactly when G >= q: probability 0.9 under the assumed distribution.
- The fade reserve is -10 log10(q) dB.

Equality at the faded design boundary does not cancel that reserve. The threshold includes implementation loss; the additional fade reserve must not also be inserted into the physical decoder threshold. For changed cochannel powers, the interference denominator must be recomputed. A numerator-only quantile with nominal stochastic interference is not automatically a calibrated 90% guarantee.

Primary engineering reference: M. Stojanovic, “Adaptive power and rate control for satellite communications in Ka band,” IEEE ICC 2002, printed page 2968, discussion following Eq. (7) and preceding Eq. (8), explicitly identifies P_T0/G_out as the fixed-fade-margin power.

## 2. Correct closure for the figure's geometry

All rows use 20 GHz, 2,000 km slant range, 10 degrees elevation, 166.6667 MHz bandwidth, 35 dBi receive gain and 1.65 W RF output. The antenna boresight gain is 2,000 linear. Atmospheric loss is the figure's 0.25/sin(10 degrees) + 1.08 dB, not a newly calibrated propagation model.

| Quantity | Boresight | Half-power edge |
|---|---:|---:|
| Transmit gain, dBi | 33.010300 | 30.000004 |
| EIRP, dBW | 35.185139 | 32.174843 |
| Free-space path loss, dB | 184.488983 | 184.488983 |
| Nominal atmospheric loss, dB | 2.519693 | 2.519693 |
| Received carrier, dBW | -116.823536 | -119.833833 |
| System noise temperature, K | 242.294454 | 242.294454 |
| Noise over beam bandwidth, dBW | -122.537245 | -122.537245 |
| C/N at RF cap, dB | **5.713709** | **2.703412** |
| Headroom above lowest-mode threshold, dB | 7.155521 | 4.145225 |

The RF cap already denotes output power. The figure's 5 dB amplifier back-off is used to derive saturation power for its DC-consumption model; it is not a second 5 dB deduction from the 1.65 W RF output.

The supplied engine report's **19.196747/9.851770 dB** values are attached to **550-km boresight / 1,100-km edge cases**, not this 2,000-km figure. The underlying independent link-ledger program and ledger are not included, so their full inputs cannot be independently reconciled here. Changing only beam angle at fixed distance and other losses produces approximately 3.0103 dB, not 9.345 dB, of C/N difference.

## 3. Feasible lone-user counterexample

Lowest mode: QPSK 1/4, threshold -1.4418124605 dB in the project's bandwidth convention, useful beam rate 68.089306 Mbit/s. For an **illustrative** extra 3 dB fade reserve (q = 0.5011872336):

| Quantity | Boresight | Half-power edge |
|---|---:|---:|
| Nominal exact-threshold power, W | 0.317638 | 0.635275 |
| Power including 3 dB reserve, W | 0.633770 | 1.267539 |
| Within 1.65 W cap? | Yes | Yes |

Thus lowest-mode starvation is not inevitable from the figure's physical cap. This is a counterexample using an explicit hypothetical q, **not** a claim that the absent engine q10 equals this value. The approximately 1.1e-10 relative PHY-floor rounding guard in the source has no material impact on these values.

## 4. Occupancy-induced service inversion

With a separate illustrative 1.7 dB *fade* back-off, additional to the 1.7 dB implementation allowance:

| Occupancy | Target mode | Transmitted mode after rate-only back-off | Per-user Mbit/s when decoded |
|---:|---|---|---:|
| 1 | QPSK 1/4 | NO_MODE | 0 |
| 2 | QPSK 2/5 | QPSK 1/4 | 34.044653 |
| 3 | QPSK 3/5 | QPSK 2/5 | 36.546852 |
| 4 | QPSK 3/4 | QPSK 3/5 | 41.260556 |

These assume uncapped exact-target nominal powers. Becoming decodable is not the same as achieving 50 Mbit/s. If the target mode is the least-threshold mode meeting the equal-airtime rate, a back-off to a strictly lower threshold cannot still meet that target under the same airtime.

## 5. Table completeness versus physical reachability

For the project's 0.20 roll-off and 1.7 dB implementation allowance:

`required C/N_dB = ideal Es/N0_dB + 1.7 - 10 log10(1.20)`.

Selected thresholds are -1.441812 dB for QPSK 1/4; 6.408188 dB for 8PSK 3/5; 8.818188 dB for 8PSK 3/4; 9.878188 dB for 16APSK 2/3; and 16.958188 dB for 32APSK 9/10.

At hypothetical C/N = 19.2 dB, the highest-throughput feasible mode without additional fade reserve/interference is 32APSK 9/10. At exactly 9.9 dB it is 16APSK 2/3; at the report's unrounded 9.851770 dB it is instead 8PSK 3/4. The latter rounding difference is consequential.

At the actual figure's 5.713709/2.703412 dB cap values, no 8PSK/16APSK/32APSK mode is nominally feasible with these threshold conventions. The highest-throughput choices are QPSK 4/5 and QPSK 1/2 respectively. Applying any additional positive fade reserve cannot make a higher-order mode feasible. The 11-entry table is therefore a specification mismatch, but it does not establish a higher-order-rate truncation at the fixed 2,000-km geometry.

Table-only maximum capacities are 248.418333 Mbit/s (11 QPSK modes) and 618.475972 Mbit/s (28 modes), corresponding to at most 4 versus 12 equal-airtime 50-Mbit/s users at arbitrarily adequate SINR. Those are not cap-feasible capacities at every geometry.

When extending to 28 modes, choose the greatest useful efficiency among feasible modes, not the last threshold-sorted entry. For example, 16APSK 2/3 has both lower required ideal Es/N0 (8.97 dB) and higher efficiency (2.637201 bit/symbol) than 8PSK 5/6 (9.35 dB, 2.478562 bit/symbol). The source figure's last-feasible-threshold algorithm no longer guarantees maximum throughput after extension.

## 6. Exact package evidence locations and limitations

Paths below are relative to the uploaded ZIP's `r11pkg/` directory.

- `sealed/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.9-AMENDMENT-2026-09-09.md`, line 5: explicit prohibition and incorrect no-reserve rationale. Lines 6–7: nominal interference and complete-product quantile definition.
- `sealed/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.8-AMENDMENT-2026-09-09.md`, line 9: 50 Mbit/s is explicitly a full-buffer power-control setpoint, not a finite-demand traffic model. Line 12: causal transmitted-mode/realized-decode distinction must remain.
- `evidence/figure1_compute.py`, lines 42–68: constants; lines 79–92: QPSK-only table; lines 116–158: antenna, atmospheric, and noise equations; lines 177–207: threshold conversions and selection algorithms.
- `evidence/V025-ENGINE-STAGE4H-REPORT-2026-09-09.md`, lines 25–30: reported 0.453138 availability is a paired two-anchor SMOKE aggregate, with unchanged powers and energy across old/new semantics. Line 36: the different 550-/1,100-km closure cases. Underlying ledgers are referenced but absent.
- `evidence/V025-CONTROLLER-FINDING-FIGURE1-AND-BACKOFF-2026-09-09.md`, lines 31 and 40–42: actual quantile unavailable locally; 62% NO_MODE and 40.8% rate infeasibility are reported census claims, with NO_MODE stated to use “computed power.” They are not independently reproduced in this audit.

The user prompt says all NO_MODE users transmit at full cap, while the finding says computed power; the engine implementation is absent. Distinguish target-mode infeasibility (which may trigger cap power) from a margin-selected NO_MODE at a lower already-computed nominal power.

If 62% NO_MODE and availability 0.453 were computed over the same population, weights and time units, zero useful service for NO_MODE implies availability <= 0.38. Different denominators or samples can resolve this; they must be documented rather than assuming a numerical contradiction is proven.

A further normalization check is needed: the figure already includes deterministic 1.08 dB scintillation in nominal gain, while the v1.9 complete-product quantile includes scintillation. Check that the engine defines its fading multiplier relative to the nominal gain without counting the same factor twice. The supplied files do not prove that the engine double-counts it.

## 7. Design disposition

Remove the prohibition on including fade reserve in power; preserve causal mode selection and actual decoding. Either use fixed-power margin-aware ACM as a reference, or jointly choose power and rate with an explicit outage constraint, cap/interference feasibility, and a defined rate-degradation or data-outage fallback. Do not present low-load starvation as inevitable Ka-band physics or a standard minimum-rate ACM consequence. A rule that retains it must instead be named as an artificial constrained policy whose association incentives include controller-induced outages.
