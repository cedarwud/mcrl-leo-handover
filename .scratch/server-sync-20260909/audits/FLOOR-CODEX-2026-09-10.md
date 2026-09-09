# Captured fraction: **−765.853965%** (`−7.658540×`)

Status: **`DIAGNOSTIC_NOT_CLAIM`**

The occupancy-three floor captures none of the oracle's gain over unilateral.
Its pooled EE is **48.700653% below UNILATERAL**, while ORACLE_SET is
**6.359000% above UNILATERAL**. Therefore

\[
\frac{EE_{FLOOR}-EE_{UNILATERAL}}
     {EE_{ORACLE\_SET}-EE_{UNILATERAL}}
=\frac{14{,}605{,}387.891-28{,}470{,}904.273}
       {30{,}281{,}369.063-28{,}470{,}904.273}
=\mathbf{-7.6585396485}.
\]

This is a clear negative result. The invariant removes the targeted
occupancy-1/2 regime and greatly improves the incumbent, but it does not
recover post-unilateral coordination headroom. It also serves fewer users
than UNILATERAL at every anchor, so no apparent gain could be credited on the
requested service criterion.

## Pooled endpoint

Pooled EE is the ratio of summed decoded bits to summed corrected-engine
joules, not the mean of per-anchor ratios.

| Arm | Decoded bits | Joules | Pooled EE (bit/J) | Served count |
|---|---:|---:|---:|---:|
| BASELINE | 545,927,267,996.825 | 146,564.590466 | **3,724,823.753560** | 826 |
| UNILATERAL | 1,660,779,577,104.985 | 58,332.519445 | **28,470,904.272641** | 1,939 |
| FLOOR | 1,061,661,613,093.402 | 72,689.723889 | **14,605,387.891091** | 1,453 |
| ORACLE_SET | 1,694,404,970,756.872 | 55,955.362098 | **30,281,369.063314** | 1,957 |

FLOOR versus BASELINE is **+292.109503% EE**: decoded bits rise 94.4694%,
energy falls 50.4043%, and served count rises from 826 to 1,453. FLOOR beats
BASELINE in EE and serves at least as many users on all 20 anchors.

FLOOR versus UNILATERAL is **−48.700653% EE**: decoded bits fall 36.0745%,
energy rises 24.6127%, and served count falls by 486 (25.0645%). It serves at
least as many users as UNILATERAL on **0/20 anchors**. ORACLE_SET's reference
gain over UNILATERAL is **+6.359000%**.

## Fixed policy actually run

FLOOR starts directly from **BASELINE**, the incumbent `nearest-eligible`
assignment. It does not start from UNILATERAL.

1. Record the initially active beams with occupancy one or two and visit that
   fixed list once in ascending `(satellite, beam)` identity order.
2. At each still-underfull beam, prescribe at most two complete repairs:
   consolidation imports the nearest-slant legal occupants of other currently
   underfull beams until occupancy three; evacuation moves every occupant to
   its nearest-slant legal beam already at occupancy at least three. A user is
   assigned `NULL` only when no such evacuation destination is legal.
3. Score those prescribed branches at realised boundary 0 with the unchanged
   exact binary64 objective
   `F = bits − 19,720,681.00172232 × joules`. A branch remains eligible only
   when its served count is at least BASELINE's unchanged boundary-0 service
   guard. Choose greater exact F; ties prefer greater service, consolidation,
   then lexicographically smaller configuration identity.
4. Commit immediately and continue the one pass. There is no no-op branch:
   the invariant is mandatory. The committed assignment is then evaluated on
   the same complete 48-boundary realised endpoint as the other arms.

This is a whole-assignment policy, not the prior three-family per-anchor rule
coordinator. Only threshold **3** was tried. No threshold, sign, seed, horizon,
price, service guard, or acceptance rule was varied after outcomes were seen.

## Occupancy result

Across the 20 anchors, 503 of 835 initially active beam incidences were below
the floor: **60.2395%**. The one pass left no active beam below occupancy three.

| Occupancy | Active beams before | Active beams after |
|---:|---:|---:|
| 1 | 262 | 0 |
| 2 | 241 | 0 |
| 3 | 151 | 66 |
| 4 | 127 | 84 |
| 5 | 39 | 88 |
| 6 | 5 | 42 |
| 7 | 10 | 50 |
| 8 | 0 | 23 |
| 9 | 0 | 2 |
| 10 | 0 | 2 |
| 11 | 0 | 2 |
| **Total active** | **835** | **359** |

Of the 503 initially underfull beams, **27 were consolidated** to occupancy at
least three and **476 were emptied**. There were 473 explicit repair decisions
(27 consolidate, 446 empty); another 30 beams emptied indirectly when their
occupants were used as consolidation donors. The policy changed 706 user
assignments in total. Across committed FLOOR assignments, 180 user-anchor
incidences ended at `NULL` because no already-stable legal evacuation beam was
available.

## Every anchor, including service and failure mechanism

EE columns are million bit/J. `Served B/U/F/O` gives BASELINE, UNILATERAL,
FLOOR, and ORACLE_SET. `Δbits` and `ΔJ` are FLOOR relative to UNILATERAL;
`C/E` counts initially underfull beams consolidated/emptied. These deltas state
why FLOOR is worse at each anchor.

| Anchor | B EE | U EE | F EE | O EE | Served B/U/F/O | F vs U EE | Δbits | ΔJ | C/E | Users moved | Decision s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| W1/A0 | 4.081 | 31.359 | 15.977 | 32.863 | 43/98/72/99 | −49.05% | −37.0% | +23.7% | 3/25 | 36 | 0.619 |
| W1/A1 | 3.760 | 35.290 | 17.338 | 37.286 | 37/99/75/99 | −50.87% | −35.0% | +32.4% | 1/26 | 40 | 0.361 |
| W1/A2 | 4.785 | 24.594 | 16.558 | 28.025 | 40/97/72/98 | −32.68% | −32.5% | +0.3% | 2/22 | 33 | 0.281 |
| W1/A3 | 3.128 | 19.727 | 14.383 | 23.168 | 35/90/68/99 | −27.09% | −28.7% | −2.2% | 2/24 | 33 | 0.400 |
| W1/A4 | 4.149 | 36.183 | 11.456 | 36.490 | 43/99/65/99 | −68.34% | −44.9% | +74.0% | 2/19 | 26 | 0.240 |
| W2/A0 | 3.075 | 31.565 | 14.485 | 32.275 | 33/99/68/99 | −54.11% | −41.1% | +28.4% | 0/23 | 35 | 0.388 |
| W2/A1 | 4.914 | 39.257 | 15.134 | 40.548 | 44/98/69/98 | −61.45% | −38.0% | +60.9% | 0/23 | 35 | 0.261 |
| W2/A2 | 5.187 | 30.489 | 18.326 | 31.183 | 45/100/76/100 | −39.89% | −31.6% | +13.7% | 0/23 | 35 | 0.274 |
| W2/A3 | 2.662 | 16.474 | 14.538 | 17.002 | 36/98/71/98 | −11.75% | −29.9% | −20.6% | 0/23 | 35 | 0.495 |
| W2/A4 | 6.229 | 26.729 | 16.440 | 30.811 | 58/97/72/98 | −38.49% | −32.7% | +9.4% | 0/25 | 34 | 0.311 |
| W3/A0 | 3.455 | 28.234 | 13.544 | 29.611 | 43/96/74/96 | −52.03% | −36.4% | +32.5% | 2/25 | 40 | 0.282 |
| W3/A1 | 4.075 | 33.196 | 15.865 | 35.549 | 43/98/77/99 | −52.21% | −35.4% | +35.2% | 1/25 | 36 | 0.272 |
| W3/A2 | 5.708 | 25.950 | 18.596 | 26.602 | 50/96/86/97 | −28.34% | −23.3% | +7.1% | 1/25 | 36 | 0.315 |
| W3/A3 | 3.128 | 22.713 | 14.124 | 25.213 | 42/93/78/95 | −37.81% | −33.8% | +6.4% | 1/25 | 36 | 0.475 |
| W3/A4 | 1.948 | 34.659 | 8.444 | 37.127 | 28/91/55/93 | −75.64% | −59.2% | +67.4% | 0/25 | 40 | 0.273 |
| W4/A0 | 2.748 | 35.208 | 11.525 | 35.852 | 33/97/71/97 | −67.27% | −42.7% | +75.1% | 2/25 | 37 | 0.451 |
| W4/A1 | 3.867 | 32.704 | 17.472 | 34.377 | 47/97/80/97 | −46.58% | −29.7% | +31.5% | 1/25 | 37 | 0.327 |
| W4/A2 | 4.762 | 32.020 | 16.942 | 34.013 | 53/99/82/99 | −47.09% | −27.4% | +37.3% | 3/23 | 34 | 0.334 |
| W4/A3 | 2.259 | 24.747 | 13.057 | 27.023 | 39/100/76/100 | −47.24% | −35.5% | +22.2% | 3/23 | 34 | 0.638 |
| W4/A4 | 2.619 | 33.251 | 10.416 | 34.010 | 34/97/66/97 | −68.68% | −50.1% | +59.3% | 3/22 | 34 | 0.280 |

FLOOR is worse than UNILATERAL on **all 20 anchors** and worse than BASELINE
on **none**. All 20 lose decoded bits relative to UNILATERAL. Eighteen also use
more energy; W1/A3 and W2/A3 use less energy, but their 28.7% and 29.9% bit
losses dominate. All 20 serve fewer users than UNILATERAL.

The causal explanation visible in the measurements is that occupancy three is
necessary for the first credited mode in the stated regime, but it is not
sufficient for an efficient complete assignment. The floor collapses active
beams from 835 to 359 and eliminates the zero-mode occupancy class, yet its
nearest-slant evacuations strand 180 user-anchor incidences and do not perform
UNILATERAL's user-specific power/interference reassignment. The mandatory
one-pass commits can also accept the less damaging of two repairs even when
both are worse than the current partial assignment. The result is much better
than the sparse incumbent, but simultaneously fewer bits and usually more
energy than the coordinate-wise optimum.

## Decision time

The measured FLOOR decision includes construction and exact boundary-0
scoring of both prescribed branches at each visited beam:

- mean **0.363842 s**; p50 **0.320753 s**; p95 **0.620094 s**; maximum
  **0.638450 s**; total **7.276843 s** over 20 anchors;
- 0/20 decisions exceed the engine's 30.08-s snapshot interval;
- the non-simulator rule bookkeeping alone averaged **12.906 ms** (p95
  14.366 ms, max 14.972 ms), but that is not the decision time because the
  branch rule was explicitly defined by exact F;
- 529 exact physical boundary-0 configurations were evaluated during FLOOR
  branch scoring.

The complete diagnostic took 197.333 s (3 min 17.333 s) in one
`nice -n 12` process with one thread per numeric library, within the requested
maximum of three processes.

## Panel, evaluator, and integrity

- Same real ceiling panel: four `V025_PROBE_R2` TRAIN worlds × first five
  decision anchors = 20 anchors. The world digests and seeds match the ceiling
  receipt. No TEST or claim-panel world was opened.
- BASELINE, the certified no-deadline UNILATERAL local optimum, and ORACLE_SET
  were reconstructed from the authenticated ceiling receipt and re-evaluated
  alongside FLOOR with the current exact 48-boundary evaluator. Their
  configuration identities and served counts matched exactly; bits and joules
  reproduced with a maximum absolute replay difference of
  `1.52587890625e-05` (binary64 accumulation order).
- Corrected physics source: requested engine commit `75c5c78c`; source tree
  `1728f6b0462f86d85618a4c73f4d1dd2d2c07376`; local starting commit
  `06f4b1cd0df3593e07c46146adedc4c3921e345c`; probe SHA-256
  `f4122d6784cb56de7743c55d51dc80a6c968ccea601d637cd1b41a8b5604c76c`.
- Oracle input file SHA-256:
  `af5a0ae34fd511b1598ab79d004be311fb1f1ea2478ca276ecbe3e8c96c79a83`;
  corrected result file SHA-256:
  `b7c235141b5e624f7d54d5c9a79b69b489b2fd90cfeba6da725282a13ea89956`;
  embedded result receipt:
  `33c2f24f9b6085d3ecf22b031378d120a734541fe22f7e3db96dc4e5acfba1a0`.
- Independent receipt and aggregate verifier: **VERIFIED**. Three focused
  occupancy-floor policy tests: **3 passed**. `git diff --check`: clean.

## Conclusion

The one-line invariant is useful as a repair of the sparse incumbent, not as a
substitute for coordinated optimization after unilateral convergence. Its
negative captured fraction, lower service on every anchor, and 36.1% pooled
bit loss reject the hypothesis that occupancy floor alone captures the oracle
headroom. The residual structure is genuinely non-trivial: it includes which
users move where, service retention, and joint power/interference effects.
