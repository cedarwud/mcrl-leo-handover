# V0.25 closed-loop quantile sweep — 2026-09-09

Status: `SMOKE_NOT_MATRIX`, TRAIN-only. Primary alpha remains 0.10 regardless of this diagnostic.

The sweep uses the common exogenous tape `V025_SMOKE/world/1`, two carried decision anchors, all 14 arms, four declared evaluation workers, the sealed one-boundary/M=48 selection fallback, and the ordinary realised 48-boundary committed endpoint. Each arm carries its own configuration and served-user state; calls are deduplicated only while both states are identical. Deadline misses and BASE fallbacks remain in the outcomes.

Immutable receipt: `.tmp/stage4h/quantile-sweep-corrected.json` (file SHA-256 `288f87a42df57e111d4f6bee7a94c04e6b9292a123e95106c72e9ab2d9cf2565`, embedded receipt `4b8bb4ce3f106127ad2f03cf610047685a408aa845f9124086a0f747a4f898a6`). Provider construction took 22.082 s and the sweep 412.088 s on this one-CPU host.

## Trajectory result

| selection view | arm trajectories equal to alpha=.10 | differing arm | pooled-EE delta for differing arm (bit/J) |
|---|---:|---|---:|
| alpha=.05 | 13/14 | E1_U1 | +38,019.128 |
| alpha=.10 primary | 14/14 | none | 0 |
| alpha=.25 | 14/14 | none | 0 |
| unchanged nominal | 13/14 | NOMINAL_GREEDY | -10,027,588.356 |

The nominal comparator is genuinely unchanged: it passes no fading quantile into the mode selector. Its NOMINAL_GREEDY trajectory delivered 44.754389 Gbit for 5,568.429 J (8.037166 Mbit/J, availability 0.294734), versus 81.916796 Gbit for 4,534.620 J (18.064755 Mbit/J, availability 0.511011) under primary alpha=.10.

For the set-level FULL arm, every variant reached the same two-step BASE-fallback trajectory: 71.728549 Gbit, 12,675.247 J, 5.658947 Mbit/J and availability 0.453138. FULL recorded two deadline fallbacks; certified S_UNI reached the same endpoint totals with no deadline miss. This equality is reported as observed, not promoted into a robustness claim beyond this quarantined two-anchor smoke.

E1_U1 was the only alpha sensitivity: alpha=.05 produced 73.353542 Gbit, 11,991.996 J, 6.116875 Mbit/J and availability 0.472926, while alpha=.10/.25 produced 72.907238 Gbit, 11,993.579 J, 6.078856 Mbit/J and availability 0.474043.
