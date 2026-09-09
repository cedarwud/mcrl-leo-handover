The claimed occupancy-activation consolidation mechanism does not survive; oracle-over-unilateral gain falls from +6.359% to +0.513%.

`DIAGNOSTIC_NOT_CLAIM`. This is a diagnostic variant evaluated on a copy. No sealed source, constant, calibration price, cap, mode-table entry or declared physics was amended.

The proposed explanation that low occupancy is physically unservable is a **table-floor artefact of the power/mode control law**. A smaller positive joint-search benefit remains. That residual does not validate the rejected occupancy-activation explanation.

The same 20 real TRAIN anchors were evaluated: `V025_PROBE_R2/world/1–4`, decision steps `0–4`, with 100 users each. Both formulations use the same exogenous tapes, nearest-eligible BASELINE, exhaustive cyclic unilateral search to a terminal no-improvement pass, and bounded oracle catalogue rules. Those rules include occupant subsets of size 2–4 (cap 1,024), complete-beam evacuations, and a victim plus its top two or three interference contributors (overall catalogue cap 4,096). The catalogue is regenerated from each formulation's unilateral optimum. The RF cap remains 1.65 W, target remains 50 Mbit/s, bandwidth remains 500/3 MHz, and the selection price remains exactly 19,720,681.00172232 bit/J. Neither search has a deadline fallback.

| Formulation | Selector | Decoded bits (Gbit) | Energy (kJ) | Pooled EE (Mbit/J) | Served / 2,000 | Rate target attained / 2,000 |
|---|---|---:|---:|---:|---:|---:|
| Original | BASELINE | 545.927268 | 146.564590 | 3.724824 | 826 | 0 |
| Original | UNILATERAL | 1,660.779577 | 58.332519 | 28.470904 | 1,939 | 0 |
| Original | ORACLE_SET | 1,694.404971 | 55.955362 | 30.281369 | 1,957 | 0 |
| Margin provisioned | BASELINE | 1,390.914269 | 175.288781 | 7.934987 | 1,165 | 426 |
| Margin provisioned | UNILATERAL | 3,194.986296 | 73.067001 | 43.726802 | 2,000 | 1,364 |
| Margin provisioned | ORACLE_SET | 3,198.919032 | 72.783895 | 43.950919 | 2,000 | 1,366 |

**The decisive comparison is +6.359000% versus +0.512537%.** EE is the ratio of summed bits to summed joules. The percentage gain is 91.94% smaller. In the variant, ORACLE_SET changes energy by -0.3875% and decoded bits by +0.1231% relative to UNILATERAL. Its realised EE improves on 16 anchors and declines on 4; the original improves on all 20. Positive joint selection-objective improvements still exist on 20/20 variant anchors. This smaller residual coordination gain does not validate the rejected occupancy-activation mechanism.

The selectors maximize `F = B − eta_ref E` at realised decision boundary zero; committed outcomes use all 48 realised boundaries over 30.08 s. “Certified” means a coordinate-wise optimum for that fixed objective and the original BASELINE-relative served-count guard, not a global EE optimum. The same guard rule is recomputed under each formulation. Reported served counts retain the original dense evaluator's definition: a user has some successful decoding during the endpoint. They do not mean continuous service or attainment of 50 Mbit/s.

The code establishes the cause directly. Required SE is `r* n/W = 0.3n`. Target selection in [acm.py](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/acm.py:132) is:

```python
required_se = rate_target_bps * occupancy / full_bandwidth_hz
eligible = [
    mode
    for mode in ACM_MODES
    if mode.spectral_efficiency_bit_per_s_hz >= required_se
]
return min(eligible, key=lambda mode: mode.threshold_linear) if eligible else None
```

[architectures.py:727](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/architectures.py:727) passes that threshold into the nominal coupled power solve. Its update at [line 392](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/architectures.py:392) is:

```python
updated = np.minimum(caps, targets * (noise + coupling @ power) / direct)
```

At an uncapped fixed point, nominal SINR therefore equals `Gamma(n)`. The same nominal channel is used to recompute SINR, followed by quantile-adjusted selection at [line 462](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/architectures.py:462). [acm.py:83](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/acm.py:83) then executes:

```python
return select_mode(nominal_sinr_linear * fading_product_quantile)
```

`select_mode` explicitly returns `None` when no threshold qualifies ([acm.py:69](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/acm.py:69)):

```python
eligible = [mode for mode in ACM_MODES if sinr_linear >= mode.threshold_linear]
return max(eligible, key=lambda mode: mode.efficiency_bit_per_symbol) if eligible else None
```

The dense path used by the oracle repeats these equations at [batch.py:301](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/batch.py:301).

| Occupancy | Required SE | Target mode | Target threshold (dB) | Distance above table floor |
|---:|---:|---|---:|---:|
| 1 | 0.3 | QPSK 1/4 | −1.44181246 | 0 dB |
| 2 | 0.6 | QPSK 2/5 | 0.60818754 | 2.05 dB |
| 3 | 0.9 | QPSK 3/5 | 3.13818754 | 4.58 dB |

Thus `q*Gamma(1)` falls below the first threshold whenever `q<1` by a meaningful amount. **The structural occupancy-one `NO_MODE` is the table floor; the cap is not necessary to produce it.** Occupancy two similarly loses every mode when its quantile deficit exceeds 2.05 dB. It is not universally unservable: sufficiently high quantiles leave QPSK 1/4 available. An isolated uncapped replay reproduces these outcomes without interference.

The deeper zero-margin reading is correct: **every feasible uncapped occupancy receives essentially zero nominal fade margin above its target mode. Only higher occupancies have lower modes to fall back to.** Capped, target-infeasible links can have negative target margin. The existing `1+2e−9` power-clearance nudge and rounded service floor add only numerical clearance, approximately 10⁻⁸ dB, not an engineering margin. The common 1.7 dB implementation allowance is already inside each mode threshold.

At fixed transmit power and otherwise fixed link conditions, the lower required SE is easier to support. The original controller first reduces power to the lower target, then asks the mode selector for a fade allowance without provisioning that allowance.

The alternative provisions `margin_dB(e) = −10 log10(q_0.10(e))`, so its power-solve target is `Gamma_margin(e,n) = Gamma(n)/q_0.10(e)`. This adds the margin in dB and multiplies the linear target by `1/q`. The existing quantile remains in transmitted-mode selection, and coupled powers are re-solved with the original caps. At an uncapped fixed point, `q*SINR_nominal = Gamma(n)`, making the rate-target mode available even at occupancy one. Cap-limited links retain the existing demotion/failure behavior.

The quantile is the existing deterministic 200,000-draw Rician × shadowing × scintillation product quantile, cached at the nearest 0.5° elevation bin; alpha stays 0.10. Illustrative mappings are 3.6730 dB at 10°, 2.9064 dB at 30°, 4.2224 dB at 60°, and 1.1073 dB at 90°. These are the model's elevation-specific margins, not an assumed Ka-band rain requirement.

A numerical trap had to be resolved before this comparison was valid. Simply dividing the target by q while retaining the finite solver unchanged produced **+0.544766%**, but left **1,179 uncapped occupancy-one NO_MODE attempts**. Their deficits below the first threshold were only 5.76e−12 to 2.616e−9 dB, with at least 0.04317 W of cap headroom. The final private variant retains the original solve, then verifies both `SINR_nominal >= Gamma/q` and `q*SINR_nominal >= threshold_target`. It raises only deficient uncapped powers with the existing capped interference update and existing numerical nudge, within the original iteration budget. All selectors were reoptimized after this correction. The uncorrected control is retained separately; it is not the decisive result.

The census covers all 48 boundaries of all 60 committed profiles per formulation. An attempt is one transmission in a native TDM slot at one boundary. Raw counts can repeat a user's transmission when another beam changes the slot partition; airtime shares weight by the slot fraction and trapezoid boundary duration, making them the more comparable exposure measure.

| Formulation | Selector | NO_MODE / attempts | Attempt share | Airtime share | Uncapped NO_MODE |
|---|---|---:|---:|---:|---:|
| Original | BASELINE | 396,440 / 507,744 | 78.079% | 78.195% | 212,910 |
| Original | UNILATERAL | 48,249 / 431,424 | 11.184% | 10.545% | 29,984 |
| Original | ORACLE_SET | 41,682 / 436,320 | 9.553% | 8.948% | 29,312 |
| Margin provisioned | BASELINE | 246,525 / 507,744 | 48.553% | 48.448% | 0 |
| Margin provisioned | UNILATERAL | 58 / 316,652 | 0.018% | 0.016% | 0 |
| Margin provisioned | ORACLE_SET | 0 / 342,380 | 0.000% | 0.000% | 0 |

Pooling the three selectors, the occupancy breakdown is:

| Occupancy | Original NO_MODE / attempts (share) | Margin NO_MODE / attempts (share) | Original airtime share | Margin airtime share |
|---:|---:|---:|---:|---:|
| 1 | 208,608 / 208,608 (100.000%) | 73,227 / 491,138 (14.910%) | 100.000% | 9.022% |
| 2 | 154,634 / 154,944 (99.800%) | 64,621 / 170,160 (37.977%) | 99.771% | 35.088% |
| 3 | 59,348 / 344,448 (17.230%) | 49,502 / 337,392 (14.672%) | 21.602% | 9.947% |
| 4 | 41,078 / 174,720 (23.511%) | 45,211 / 80,544 (56.132%) | 27.313% | 56.566% |
| 5 | 11,580 / 270,912 (4.274%) | 9,663 / 75,062 (12.873%) | 5.211% | 9.412% |
| 6 | 3,742 / 125,664 (2.978%) | 1,595 / 2,880 (55.382%) | 3.817% | 61.631% |
| 7 | 4,873 / 45,888 (10.619%) | 2,764 / 9,600 (28.792%) | 12.157% | 25.087% |
| 8 | 2,124 / 29,760 (7.137%) | No observations | 5.183% | — |
| 9 | 384 / 6,528 (5.882%) | No observations | 7.407% | — |
| 10 | 0 / 5,088 (0.000%) | No observations | 0.000% | — |
| 11 | 0 / 8,928 (0.000%) | No observations | 0.000% | — |

These pooled rows mix different link geometries and selected assignments, so their relative outage rates also reflect those differences.

**Occupancies one and two are servable under the alternative.** They produce 383,324 and 99,282 decoded attempts respectively. Across the complete variant census there are **zero uncapped NO_MODE attempts and zero uncapped demoted-rate misses**. Remaining NO_MODE attempts occur at the RF cap. Realised fading can still prevent decoding after a mode is selected. In the original, occupancy one has no decoded attempts; occupancy two has 310, confirming that its prohibition was almost universal on these anchors, rather than absolute.

At decision boundary zero, the observed activation signature also disappears: an existing occupancy-one/two beam with no eligible mode becomes decoded after ORACLE_SET increases its occupancy on **3 original transitions versus 0 variant transitions**. The original transitions are W1/step2, occupancy 1→5, and W3/steps1 and2, occupancy 1→3. This narrowly defined count excludes newly populated beams and is not a decomposition of the EE gain. At that same boundary in the variant, ORACLE_SET still reduces the number of occupied beams on 5 anchors, leaves it unchanged on 10, and increases it on 5. Generic consolidation and set interactions therefore remain; the structural floor-activation explanation does not.

The review's adjacent-step margin explanation is not correct. On an original uncapped link, nominal headroom above the transmitted mode is `threshold_target − threshold_tx`; demotion can skip several modes. Actual decoding margin is `10 log10(SINR_realised) − threshold_tx_dB`, which also includes realised desired-link and interference fading. The measured distributions are:

| Formulation | Margin distribution (dB) | Minimum | P05 | Median | P95 | Maximum |
|---|---|---:|---:|---:|---:|---:|
| Original | Nominal headroom above transmitted mode | 1.120 | 3.230 | 4.330 | 4.810 | 6.049 |
| Original | Realised margin, all selected modes | -9.765 | 0.090 | 3.740 | 7.900 | 17.791 |
| Original | Realised margin, decoded only | 0.000 | 1.020 | 3.830 | 7.980 | 17.791 |
| Margin provisioned | Nominal headroom above transmitted mode | 1.107 | 2.870 | 3.790 | 4.540 | 5.963 |
| Margin provisioned | Realised margin, all selected modes | -9.832 | -0.670 | 3.410 | 7.930 | 16.812 |
| Margin provisioned | Realised margin, decoded only | 0.000 | 0.680 | 3.630 | 8.070 | 16.812 |

These pool all three selectors. Percentiles are airtime-weighted, using 0.01 dB bins with at most 0.005 dB rounding; extrema retain full precision in the evidence. NO_MODE has no finite transmitted-mode margin and is counted separately. Negative realised margins are decode failures, so the decoded-only distribution is conditional on success.

The margins actually applied span 1.107–4.830 dB. The model contains Rician fading, shadowing and scintillation, with no separate rain attenuation term. These results therefore cannot establish Ka-band rain availability. A rain margin depends on location-specific rainfall and the required exceedance probability, among other link parameters ([ITU-R P.618-14, §2.2.1.1](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.618-14-202308-I!!PDF-E.pdf)).

The rate accounting is explicit. [acm.py:93](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/acm.py:93) credits the transmitted mode's SE only when that mode decodes:

```python
decoded = mode is not None and realised_sinr_linear >= mode.threshold_linear
return ACMRealisedOutcome(
    decoded,
    realised_sinr_linear,
    0.0 if not decoded else mode.spectral_efficiency_bit_per_s_hz,
)
```

The scalar endpoint multiplies by bandwidth and TDM fraction; the dense endpoint does the same and integrates the resulting rate into bits ([adapter.py:185](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/adapter.py:185), [batch.py:417](/home/sat/mcrl-v025-ladder-ws/src/mcrl/physics_v025/batch.py:417)). **The code credits the demoted rate, not `r*`.** Because the target is the lowest-threshold mode satisfying the required SE, a mode with a strictly lower threshold cannot satisfy that requirement. Positive decoded service in the original formulation must not be described as meeting its rate target.

The census confirms that all **846,846 original decoded attempts (100%)** use insufficient SE for `r*n/W`. No original user-anchor endpoint attains the 50 Mbit/s average target. In the margin variant, 53,615 of 850,345 decoded attempts (6.305%) miss that SE target, all at the cap. Whole-endpoint rate attainment is reported separately in the first table.

Verification: all 20 original anchors reproduce the archived committed assignments, bits, joules and served counts exactly; internal F/Psi reductions differ by at most 1.91e−5 bit under serial batching, without changing any selection. All 120 original/variant committed scalar replays match batch bits and joules to relative errors at most 8.88e-16 and 8.88e-16, with identical served counts when using the preserved dense definition. The scalar adapter's stricter within-boundary AND service flag differs from the dense OR flag; neither implementation was amended, and the published dense definition is used consistently here. Seven focused fixtures independently verify uncapped target clearance, capped failures, scalar/batch agreement and unchanged uncoupled outputs.

All changes stayed in this workspace. The sealed source tree remains `1728f6b0462f86d85618a4c73f4d1dd2d2c07376`; only diagnostic copies and outputs were added. Runs used the requested Python, `PYTHONPATH=src`, `nice -n 10`, one numerical thread per process and no more than three concurrent worker processes. No TEST split was opened.

Reproducible evidence:

- [Original results](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/original-result.json), [strict margin results](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/margin-cleared-result.json), and [uncorrected numerical control](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/margin-result.json).
- [Complete census and parity receipt](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/scalar-census-summary-cleared.json), [compact report data](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/report-data-cleared.json), and [activation transitions](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/activation-signatures-cleared.json).
- [Copied batch formulation](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/cleared_margin_batch.py), [independent scalar formulation](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/scalar_diagnostics.py), and [selector runner](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/oracle_runner.py).
- [Original reproduction audit](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/original-reproduction-audit.json), [selector/result audit](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/strict-result-audit.json), [clearance fixture audit](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/strict-variant-audit.json), and [numerical failure trace](/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/uncapped-margin-failure-trace.json).
