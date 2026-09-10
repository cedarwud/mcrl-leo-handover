**FAST_LOOK_TWO_ANCHORS — best-known coarse-search gap: +113.4% pooled efficiency over the declared law on two anchors; the gain looks mostly reachable by a per-beam local rule, with cross-beam search adding only about 2.1% over the local probe.**

`DIAGNOSTIC_NOT_CLAIM` · `FAST_LOOK_TWO_ANCHORS`

This is a two-anchor shape check, not an answer to the control-law question. It reports the best-known values found by one coarse search. It must not be promoted beyond this diagnostic; the companion eight-anchor evaluation under both provisioning rules is the relevant larger run.

## Result

The declared law was not close to the settings found in this fast look. With the committed association held exactly fixed, pooled efficiency rose from **45.375 to 96.836 Mbit/J**, or **+113.412% relative to the declared law**. Equivalently, the declared value is **53.142% below** the best-known coarse-search value.

Every accepted searched setting preserved at least the declared credited spectral efficiency for every active transmission slot. This is stronger than the unchanged service guard: served count therefore stayed at 100/100 on each anchor, and rate-target attainment increased from 72 to 100 users on anchor 0 and from 70 to 100 on anchor 1.

| FAST_LOOK_TWO_ANCHORS | Declared EE (Mbit/J) | Best found (Mbit/J) | Best found over declared | Declared below best found | Served, declared → found | 50 Mbit/s target attained, declared → found |
|---|---:|---:|---:|---:|---:|---:|
| 2025-11-04, step 0 | 46.715 | 100.727 | +115.620% | 53.622% | 100 → 100 | 72 → 100 |
| 2025-11-04, step 1 | 44.100 | 93.086 | +111.081% | 52.625% | 100 → 100 | 70 → 100 |
| Two-anchor pool | 45.375 | 96.836 | +113.412% | 53.142% | 200 → 200 | 142 → 200 |

The improvement came primarily from more productive mode choices rather than energy reduction. Pooled integrated bits increased **115.265%**, while joules increased **0.868%**. Per anchor, the changes were +118.873% bits / +1.509% joules at step 0 and +111.626% bits / +0.258% joules at step 1.

## What was searched

The fixed assignment was the corrected pipeline's final committed `ORACLE_SET` configuration at each anchor. No user was moved, dropped, or reattached. The declared comparison was reconstructed with corrected `MARGIN_Q` provisioning, `Gamma_r(n_b) / q_0.10`, and matched the existing corrected receipt to binary64 tolerance for both bits and joules.

For every one of the 48 realised boundaries and every exact rational TDM subslot, the search varied each simultaneously active beam's radiated power on this grid relative to that beam's declared power:

`0, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0, 1.125, 1.25, 1.5, 2.0 × declared power`, with every value clipped to the unchanged **1.65 W** per-beam cap and **1.65 W** also included explicitly.

At every power candidate, all **28 unchanged ACM table modes**, plus no transmission, were evaluated; the highest-throughput mode that decoded under the realised SINR was used. This is an offline best-known diagnostic and has realised-boundary information that a deployable causal rule would not automatically possess.

The optimizer used up to four deterministic coordinate sweeps per subslot and three efficiency-ratio updates per anchor. Each coordinate trial recomputed the complete coupled interference matrix, realised SINR for every active beam, the nonlinear PA draw, per-chain circuit draw, and per-satellite baseband draw. It made 3,593,726 power/mode comparisons at step 0 and 1,333,070 at step 1.

| FAST_LOOK_TWO_ANCHORS search constraint | Unchanged value or treatment |
|---|---|
| Assignment | Exact committed `ORACLE_SET` mapping, held fixed |
| Provisioning baseline | Corrected `MARGIN_Q`: `Gamma_r(n_b) / q_0.10` |
| Power cap | 1.65 W per beam |
| Service guard | Selection-time served count ≥ 60 at step 0 and ≥ 47 at step 1; searched results served 100 at both |
| Rate target | Unchanged 50 Mbit/s; attainment reported separately |
| Extra conservative acceptance condition | No active transmission slot may receive less credited spectral efficiency than under the declared law |
| Interference | Full simultaneous cross-beam coupling recomputed exactly at every candidate |
| Integration | Unchanged 48-boundary trapezoidal integration over 47 × 0.640 s |

## Does it need cross-beam information?

**Mostly no, on these two anchors.** An independent local probe—each beam choosing from the same grid using its own decoded rate and PA/chain cost while holding other beams at their declared powers—reached **94.796 Mbit/J** pooled, +108.915% over the declared law and only **2.107% below** the coupled search's 96.836 Mbit/J. The large gain therefore looks predominantly per-beam-local; exact cross-beam information appears useful for the last roughly two per cent, not for the main effect. This is a rough two-anchor judgement, not a proof.

## Provenance and timing

| FAST_LOOK_TWO_ANCHORS provenance | Value |
|---|---|
| Real anchor IDs | `V025_CEILING30/date/2025-11-04:step/0`; `V025_CEILING30/date/2025-11-04:step/1` |
| World SHA-256 | `cb1c594d852a5aba1bda7ce26b2b1604c97d77ae5a6908048cd3ea5c7dda8e1b` |
| Training seed | `1914058825465947281` |
| Step-0 fixed-assignment SHA-256 | `b23418c436871d9cc193e15d052079fd9d77902a9947461207d193e267ce735a` |
| Step-1 fixed-assignment SHA-256 | `fbbb05709a5018b3111b8555bef9e73f05a62c81e88ef302821b53fd27db70cc` |
| Measured run wall time | 131.859 s (2 min 11.859 s) |
| Concurrency | One process; numerical-library threads pinned to one |

No sealed constant, threshold, sign, seed, horizon, price, guard, acceptance rule, or declared control law was changed. The diagnostic only rebuilt the matching world, replayed the declared corrected law, and evaluated alternative power/mode controls outside the pipeline.

With more time, I would use a denser absolute-plus-relative power grid, multiple coupled-search starting points, and separate causal-mode and realised-information searches across the larger anchor panel. That would test grid sensitivity and distinguish deployable local headroom from offline mode-selection headroom.
