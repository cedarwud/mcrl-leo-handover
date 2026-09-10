**Median gap: 3.0 rungs and 3.921 dB among slots with a declared transmitted mode; mode selection alone offers 9,858,751 extra delivered bit/J (9,685,923 bit/J demand-capped), at identical transmit power.**

# Mode-selection gap diagnostic — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM` · `FAST_DIAGNOSIS` · pure evaluation of the existing law.

**When the law selected a transmitted mode, it was usually below the highest mode supported by realised SINR; the unharvested-headroom explanation is supported on this slice.**

## Slot-level result

The law selected `NO_MODE` in **78.49%** of powered transmission records. Those records have no transmitted threshold, so their requested rung and dB gaps are undefined. The main distribution below uses records with an actual transmitted mode; every `NO_MODE` row remains in the raw ledger and supplemental census.

Rung gaps are signed: `highest realised-supported rung - transmitted rung`. Rungs are the sealed modes ordered by increasing spectral efficiency, matching the law's greatest-efficiency selector.

| occupancy | slots with transmitted mode | mean rung gap | median rung gap | zero rungs | >=3 rungs | mean dB gap | median dB gap |
|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 27262 | 3.786 | 3.000 | 4.21% | 65.94% | 3.928 | 3.921 |
| 1 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| 2 | 80 | 1.212 | 1.000 | 20.00% | 0.00% | 1.699 | 1.991 |
| 3 | 9759 | 3.047 | 3.000 | 4.53% | 54.85% | 3.687 | 3.590 |
| 4 | 12995 | 3.741 | 3.000 | 4.49% | 69.60% | 4.038 | 4.066 |
| 5 | 3768 | 5.372 | 5.000 | 1.80% | 81.10% | 4.124 | 4.006 |
| 7 | 660 | 6.850 | 6.000 | 5.61% | 79.09% | 4.491 | 4.375 |

All powered transmission records use `NO_MODE=-1` only for this supplemental rung census:

| occupancy | powered records | virtual median rung gap | virtual zero rungs | virtual >=3 rungs | no transmitted mode | decode failure |
|---:|---:|---:|---:|---:|---:|---:|
| all | 126720 | 1.000 | 41.64% | 30.19% | 78.49% | 79.32% |
| 1 | 43008 | 0.000 | 63.42% | 9.20% | 100.00% | 100.00% |
| 2 | 37632 | 2.000 | 34.45% | 33.81% | 99.79% | 99.79% |
| 3 | 10752 | 3.000 | 7.92% | 53.62% | 9.24% | 13.07% |
| 4 | 26112 | 2.000 | 30.81% | 44.45% | 50.23% | 52.21% |
| 5 | 6144 | 3.000 | 26.27% | 56.12% | 38.67% | 40.15% |
| 7 | 3072 | 0.000 | 65.69% | 24.77% | 78.52% | 79.88% |

Each raw row records anchor/boundary/slot/user/beam, occupancy, exact RF power, transmitted mode and threshold, realised SINR, highest supported sealed mode, signed rung gap, and dB gap.

## Same-power mode-only counterfactual

| credit view | declared bits (Gbit) | highest-supported bits (Gbit) | same joules | declared Mbit/J | highest-supported Mbit/J | extra bit/J | relative gain |
|---|---:|---:|---:|---:|---:|---:|---:|
| Delivered capacity | 107.263070 | 378.963278 | 27559.293301 | 3.892083 | 13.750834 | 9,858,750.926 | 253.30% |
| Demand-capped | 107.263070 | 374.200269 | 27559.293301 | 3.892083 | 13.578007 | 9,685,923.241 | 248.86% |

**Mode selection alone makes 9,858,750.926 extra delivered bit/J available, or 9,685,923.241 extra bit/J after capping each user's per-anchor credit at 50 Mbit/s, with every RF power held fixed.**

The delivered view credits the full capacity of the highest mode cleared by realised SINR. The demand-capped view applies `min(user integrated bits, 50 Mbit/s × 30.08 s)` separately for each user and anchor. Both reuse the declared radiation objects and their energy; the counterfactual changes only the credited mode.

## Coverage and committed configuration

- real world: `V025_PROBE_R2/world/1` (seed `3525272352645343090`, tape digest `a7d222eab02789c26de423f7cd87d7e2f677c574f64fb181bd98ec799fdec704`)
- anchors: `[0, 1, 2, 3]`; 48 realised boundaries per anchor; 126720 active transmission-slot observations
- configuration: corrected causal `a-r0`, `realised` keyed fading, `MARGIN_Q` alpha=0.10, carrier `nearest-eligible`
- committed assignment: `BASE:nearest-eligible`; the authoritative ten-anchor stage-4h smoke records every FULL decision missing the sealed deadline and atomically committing BASE, so anchors 0–3 are direct committed-pipeline configurations, not searched replacements
- sealed constants retained: RF cap 1.65 W, target 50 Mbit/s, bandwidth 166.666667 MHz, active-chain circuit 0.338 W
- power isolation: the script runs one declared evaluation per anchor, then re-credits its immutable `Transmission` records; it performs no second power solve and asserts exact equality of the common energy denominator

Per-anchor power-vector SHA-256 values:

- anchor 0: `daf04c86f3c907994173c1dbcc1747f7a7b52a1abb49dd76cfb19462a7c28a7b`; 32256 observations; 6930.395666 J
- anchor 1: `65a8166daf1ced75e81708b0f346e7836940b378a1849f04fc5403eef6c758f2`; 31488 observations; 6346.435418 J
- anchor 2: `0dd207b5c91c23906ed6679c353677b5d853251ac5b631ac91a437a629482f1b`; 30720 observations; 6303.423332 J
- anchor 3: `c50532b210139adad8412f5f19254c04ade796264570e63370586c0ae60066df`; 32256 observations; 7979.038885 J

## Reproduction

From the workspace root:

```bash
PYTHONPATH=src nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python diagnose_mode_selection_gap.py --world 1 --anchors 0 1 2 3
sha256sum diagnose_mode_selection_gap.py MODE-SELECTION-GAP-2026-09-10.md .scratch/mode-selection-gap/mode-selection-gap.json
```

- source commit: `4508f5ba085f1d8a4ce9e1a32e52088bfb5e018a`; tracked tree: `1728f6b0462f86d85618a4c73f4d1dd2d2c07376`
- evaluator script SHA-256 before report rendering: `c6afbde924141260ec4de2a086389691330c84bbfc0160c1bd8dbcefdeefc0c7`
- imported matrix runner SHA-256: `f4122d6784cb56de7743c55d51dc80a6c968ccea601d637cd1b41a8b5604c76c`
- sealed ACM table SHA-256: `4463331e621d778f4aa97d60ed5726c1e02bcf791e2be7b134ec29eace631627`
- raw ledger: `.scratch/mode-selection-gap/mode-selection-gap.json`

The JSON contains all slot observations plus the exact aggregates used above. Validation fails closed if there are fewer than four anchors or 48 boundaries per anchor, if baseline bit reconstruction differs from the ordinary evaluator, if energy changes, or if any highest-supported mode fails its own realised threshold.

## Interpretation

The literal mechanism needs one correction: `m_target` provisions power, but corrected `MARGIN_Q` does not simply transmit `m_target`; it selects `m_tx` from the alpha=.10 margin-adjusted nominal SINR. Even so, realised SINR commonly clears substantially higher modes, and the same-power upper bound is more than large enough to contain the fast look's reported gain. It does not prove how much of that separate result actually came from modes.

The predicted low-occupancy ordering is **not observed**. Among records with an actual mode, the median gap is 1 rung at occupancy 2, 3 at occupancies 3–4, 5 at occupancy 5, and 6 at occupancy 7; occupancy 1 selected no mode at all. This is diagnostic evidence on one real world and four committed anchors, not an efficacy claim or a proposal to alter the sealed law.
