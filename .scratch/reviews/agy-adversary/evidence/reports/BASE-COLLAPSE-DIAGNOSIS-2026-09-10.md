**Across 11 epoch-500 v2 seeds × 22 TRAIN anchors, learned `a0` has mean `modal_frac=0.05236`, `active=49.07 beams / 5.79 satellites`, and `argmax_distinct=0.49070`; the zero-learning myopic control has `0.05500`, `51.68 / 5.18`, and `0.51682`, respectively.**

# BASE concentration diagnosis — 2026-09-10

This is a design-phase diagnostic, not a performance or EE claim. The measured learned proposals are numerically far from the supplied sibling one-beam regime, while their mean active-satellite count overlaps the sibling's supplied 5–7-satellite spread proxy. I do not turn that comparison into a binary “collapsed/not collapsed” label. One requested comparator remains unavailable: the exact S_UNI implementation could not certify even the first anchor within a 600-second diagnostic allowance under the resource limits, so its BASE fallback is not reported as a fixed point.

## What was actually measured

The primary learned result is the newer q1-v2 design run. For every available exact epoch-500 checkpoint, I replayed the FULL-arm heads on every action row in the 22 launch-receipt anchors and selected each user's stable masked `argmax(Q1 + Q2)`. This is the raw independent `a0`, before joint-conflict repair: the implementation loops over users and sums the two head scores independently ([deployment.py:101](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/deployment.py:101), [deployment.py:112](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/deployment.py:112)); repair is a later operation ([deployment.py:125](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/deployment.py:125)). Physical beam identity means `(NORAD ID, beam-chain ID)`, not an action-table slot.

Scope was exactly `V025_PROBE/world/1`, split `TRAIN`, steps 0–7, 100 users, and the 22 anchors listed by both live launch receipts. No evaluation-only date or evaluation shard was opened by either probe. External live-run and source directories were read only.

Definitions:

- `modal_frac = max non-null beam occupancy / 100`. Null choices are excluded from the numerator but remain in the denominator and are reported separately.
- `active beams` is the number of distinct selected non-null physical beam identities; `active satellites` is the number of distinct selected NORAD IDs.
- `argmax_distinct = active beams / 100`.
- Geometric control: the nearest-eligible carrier profile for the matching step, reused across the three carrier-context anchors at that step.
- Myopic control: for each user, stable masked argmax of `q1_state[0]`, the current nominal SINR/decoding margin at the rate target. It has no fitted parameters, forecast, or cross-user coordination.

## Verified by running code

All values below are arithmetic means over the indicated physical profiles. Ranges are profile-level minima and maxima.

| Profile | Profiles | `modal_frac` mean [range] | Active beams mean [range] | Active satellites mean [range] | `argmax_distinct` mean [range] | Null users mean [range] |
|---|---:|---:|---:|---:|---:|---:|
| Learned `a0`, q1-v2 (primary) | 242 | 0.05236 [0.02, 0.13] | 49.07 [24, 66] | 5.79 [2, 9] | 0.49070 [0.24, 0.66] | 1.68 [0, 74] |
| Zero-learning myopic | 22 | 0.05500 [0.03, 0.08] | 51.68 [38, 73] | 5.18 [2, 9] | 0.51682 [0.38, 0.73] | 0 [0, 0] |
| Geometric nearest-eligible | 22 | 0.05000 [0.05, 0.05] | 43.77 [41, 47] | 3.36 [2, 5] | 0.43773 [0.41, 0.47] | 0 [0, 0] |
| Learned `a0`, q1-v1 sensitivity | 286 | 0.06864 [0.01, 0.13] | 41.28 [1, 60] | 5.57 [1, 9] | 0.41283 [0.01, 0.60] | 4.51 [0, 98] |
| Certified S_UNI | 0 | unavailable | unavailable | unavailable | unavailable | unavailable |

The auxiliary carrier-BASE profiles embedded in the 22 source anchors—not the requested geometric control—had `modal_frac=0.04318`, `active=55.82 beams / 4.50 satellites`, and `argmax_distinct=0.55818`. This distinction matters because stay-if-possible and random-masked source anchors are not geometric nearest-eligible profiles.

### Full occupancy histograms

Notation is `users on a selected beam → number of beam/profile instances`. It includes every occupied-beam tail value. The audit JSON also contains every profile's full descending occupancy vector, not only this aggregation.

| Profile | Complete histogram |
|---|---|
| Learned `a0`, q1-v2 | `1→5320, 2→3057, 3→2158, 4→924, 5→354, 6→37, 7→15, 8→4, 9→3, 10→2, 13→1` |
| Zero-learning myopic | `1→589, 2→251, 3→155, 4→84, 5→44, 6→11, 7→2, 8→1` |
| Geometric nearest-eligible | `1→290, 2→310, 3→209, 4→107, 5→47` |
| Learned `a0`, q1-v1 sensitivity | `1→4808, 2→2758, 3→2033, 4→1111, 5→586, 6→269, 7→141, 8→53, 9→20, 10→12, 11→9, 12→2, 13→5` |
| Certified S_UNI | unavailable; no uncertified fallback histogram substituted |

Null selection is a separate concentration symptom worth exposing. In q1-v2, the worst case is seed `925030429265975792`, anchor `V025_PROBE/world/1|3|random-masked`: 74 null choices, with the remaining 26 users spread over 24 beams (`[2,2,1×22]`). Thus its low `modal_frac=0.02` is not evidence that all users received diverse service. All 11 q1-v2 seeds selected null for 11–74 users at that particular anchor; most other profiles had none. The q1-v1 sensitivity is more severe: one profile has 98 nulls, and its minimum one active beam occurs with 96 nulls and four users on that beam. Neither is the sibling's “all users on one beam” pattern.

### Checkpoints, seeds, and epochs

The primary result used these 11 q1-v2 FULL checkpoints, all at epoch 500:

`389903013832883586`, `925030429265975792`, `1437152739566466432`, `2306713132836500212`, `2539879246662512149`, `3155344545377116990`, `5166716249291843642`, `6114226365011333154`, `6407676579069309528`, `7234013715671416945`, `7291913070596938501`.

They were read from `/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z/checkpoints/learner-<seed>-epoch-000500.json`. The launch receipt SHA-256 is `19ac748748942b3cf81aa7f3a2375447295d7c228e4e9c9084a5e1f84da4d893`; corpus digest is `ab81d942993d005e6eab964e4e1011a8b85cfed49d47fac7448a39e729514016`.

The q1-v1 sensitivity used these 13 FULL checkpoints, all at epoch 500:

`389903013832883586`, `925030429265975792`, `1437152739566466432`, `2306713132836500212`, `2539879246662512149`, `3155344545377116990`, `5166716249291843642`, `5683607794651051129`, `6114226365011333154`, `6407676579069309528`, `7234013715671416945`, `7291913070596938501`, `9087876568043732533`.

They were read from `/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z/checkpoints/learner-<seed>-epoch-000500.json`. The launch receipt SHA-256 is `11920d3ae7d827438c31752daf43ac1004d65421b7f7534fc39ad86e55d9aff7`; corpus digest is `23814e63d9300fe049bd730897b7e07ef880e5fe21f7a5624c1fee4a9d5eb20c`. Seed `2914121027624601215` was only at epoch 100 at inventory time and was excluded. Exact checkpoint-file SHA-256 values are recorded in the audit JSON.

The newer schema removes two duplicate activation bits but retains background occupancy and previous served load and adds focal elevation ([q1_schema_v2.py:73](/home/sat/mcrl-v025-design-ws/q1_schema_v2.py:73)). This makes the v1/v2 comparison a schema sensitivity, not additional replicates of one identical learner.

## Load, occupancy, reward, and selection objective: code facts

There is no reinforcement-learning reward in this learner. It performs fixed-target pairwise regression; the code explicitly states that no reward, next state, target network, discount, or bootstrap exists ([learner.py:278](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/learner.py:278)). The nonlinear heads fit candidate-minus-reference targets ([learner.py:779](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/learner.py:779)). Loss values therefore provide no evidence here about concentration or EE.

There is **no explicit occupancy/load penalty or bonus in the physical selection objective**. The whole-network objective is exactly `F = B - eta_ref E` ([targets.py:130](/home/sat/mcrl-v025-probe-ws/src/mcrl/physics_v025/targets.py:130)); the separate `Phi` term penalizes satellite and beam handovers only ([targets.py:72](/home/sat/mcrl-v025-probe-ws/src/mcrl/physics_v025/targets.py:72)). Source C1 targets implement the corresponding difference `(ΔB - eta_ref ΔE)/kappa + ΔPhi` ([run_v025_pilot_c3.py:608](/home/sat/mcrl-v025-coalgen-ws/scripts/run_v025_pilot_c3.py:608)). Raw learned `a0` then selects only by the learned `Q1+Q2` sum.

Occupancy nevertheless enters in two indirect ways:

1. It is observable to the shared heads. q1-v1 includes `background_occupancy_excluding_focal` and `previous_served_load_for_action`; q2 includes background occupancy as well ([state.py:30](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/state.py:30), [state.py:49](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/state.py:49)). The source generator computes those values from the carrier BASE and incumbent profile ([run_v025_pilot_c3.py:624](/home/sat/mcrl-v025-coalgen-ws/scripts/run_v025_pilot_c3.py:624)). Thus “shared head” does not mean identical input for every user/action.
2. It changes physical `B` and `E`. TDM effective airtime bandwidth is divided by occupancy and required spectral efficiency is `rate × occupancy / bandwidth` ([acm.py:77](/home/sat/mcrl-v025-probe-ws/src/mcrl/physics_v025/acm.py:77)); the batch physics constructs an occupancy-refined slot grid and the occupancy-indexed required-SINR table ([batch.py:65](/home/sat/mcrl-v025-probe-ws/src/mcrl/physics_v025/batch.py:65), [batch.py:106](/home/sat/mcrl-v025-probe-ws/src/mcrl/physics_v025/batch.py:106)).

So the precise answer is: no explicit load term in a reward or selection objective, but load is present as model input and implicitly through the physical bits/energy targets and required-SINR/TDM calculation. There is also no cross-user coupling in the raw `a0` argmax itself.

## Fixed `eta_ref` and its realised-panel context

Every inspected source row in both corpora and every anchor carries the same exact float encoding, `0x1.4df5240780e6fp+23 = 10,943,122.01465532 bits/J`. The live corpus calibration file identifies this as a `one-development-anchor-proxy`; SHA-256 `7a4cec5937d64d9c38727b856e40f213cd2525896741718e2e43283ad3fa98ca`. It is passed unchanged to the target construction, so it is fixed across anchors and learned arms. The general calibration contract defines `eta_ref = B_ref/E_ref` ([calibration.py:108](/home/sat/mcrl-v025-probe-ws/src/mcrl/physics_v025/calibration.py:108), [calibration.py:138](/home/sat/mcrl-v025-probe-ws/src/mcrl/physics_v025/calibration.py:138)).

For scale only—not as an EE claim—I replayed the saved physical profiles through all 48 realised boundaries on the same 22 TRAIN anchors. Pooling bits and joules across all 11 q1-v2 seeds gives `34,129,440.64 bits/J`, so fixed `eta_ref` is `0.32064×` that pooled value. Per-seed pooled values span `31,387,708.07–36,251,705.17 bits/J`, making `eta_ref` `0.30187–0.34864×` the per-seed values. The corresponding context controls are geometric `13,347,867.24` (`eta/EE=0.81984`), myopic `16,159,013.89` (`0.67721`), and carrier BASE `11,633,155.61` (`0.94068`). These numbers answer only how the frozen scalarisation price sits relative to realised pooled ratios; they are not comparisons, claims, or evidence from loss.

An older prepared local tape was deliberately rejected because its calibration encoded `eta_ref≈27.06M`, not the `10.943M` bound into these live source rows. The realised context above was regenerated in memory with the source-generation physics and matching calibration.

## S_UNI: verified blocker, not a substituted result

The code's S_UNI is an exact full-legal single-user best response to convergence under the exact nominal joint physics ([run_v025_matrix_probe.py:1831](/home/sat/mcrl-v025-coalgen-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1831)). Only `NO_IMPROVING_LEGAL_UNILATERAL` at the no-change pass is a certificate ([run_v025_matrix_probe.py:1921](/home/sat/mcrl-v025-coalgen-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1921)); the production budget is 10 seconds, after which the engine returns BASE as `DEADLINE_FALLBACK_BASE` ([run_v025_matrix_probe.py:162](/home/sat/mcrl-v025-coalgen-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:162), [run_v025_matrix_probe.py:1873](/home/sat/mcrl-v025-coalgen-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1873)).

I allowed 600 seconds for a diagnostic certificate on anchor 0, versus 10 seconds in production, and tried exact batch widths 256, 128, 64, 16, and 8 while enforcing the RSS watchdog. Wider paths either reached the 3,900,000-KiB watchdog or timed out. The final fresh-process width-8 run stayed at 2,320,240 KiB observed peak RSS but returned `DEADLINE_FALLBACK_BASE` after 605.85 CPU seconds. Because even anchor 0 did not reach the certificate, running the other 21 cannot produce a valid panel under the current constraints. Reporting the returned BASE would falsely label a timeout fallback as a certified fixed point; therefore S_UNI has no concentration statistics in this diagnosis.

## Derived on paper

- With 100 users, the reported `argmax_distinct` values are exactly active physical beams divided by 100; no estimate or threshold is involved.
- The aggregate histograms are sums of each profile's complete occupied-beam counts. For q1-v2, for example, `5320 + … + 1 = 11,874` occupied beam/profile cells, matching `49.0702479 × 242` up to representation.
- The `eta_ref` ratios are computed from pooled totals as `eta_ref / (ΣB/ΣE)`, not as a mean of per-anchor EE ratios.

## Inference and positioning against the supplied sibling regimes

The sibling collapsed regime supplied in the brief has `argmax_distinct=1/100=0.01`, one active action, and effectively all users on it (`modal_frac≈1`). The primary q1-v2 learned profiles here average `0.49070`, 49.07 beams, and `modal_frac=0.05236`; their worst beam concentration is 13 users, and no q1-v2 profile has only one active beam. On those observables, these measurements sit far from the supplied one-beam regime.

The sibling spread proxy is described only as 5–7 active satellites. This panel's learned mean is 5.79 satellites with a 2–9 profile range, so its mean overlaps that supplied spread description, while some profiles lie below or above it. The environments and available satellite counts differ, and the sibling brief supplies no proxy `modal_frac` or beam-level distinctness, so a stronger equivalence would be unsupported.

The myopic control is slightly more diverse by active beams and `argmax_distinct` (`+2.61` beams and `+0.02612`) but slightly more concentrated by modal fraction (`+0.00264`) than learned q1-v2. It therefore does not dominate every concentration statistic. The learned v1 and v2 null-action excursions also show that a low modal beam fraction can coexist with mass null selection. Those facts argue for keeping beam concentration, null rate, and service outcomes separate in any later claim-stage analysis.

## Reproducibility artifacts

- [Concentration audit JSON](/home/sat/mcrl-v025-probe-ws/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.json), SHA-256 `275cf828ca54bdfee43c9d60dd54e37bd7a19a09a5fc3448ff2b56f9babf87e9`. It contains every physical profile, per-profile occupancy vector, checkpoint path/hash, and aggregate histogram.
- [Realised context JSON](/home/sat/mcrl-v025-probe-ws/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.physics.json), SHA-256 `99ee389d97a35f9f17f1835a143f19ea47a22dad21759ca0d740c9d32c6fa2a9`.
- [Concentration probe](/home/sat/mcrl-v025-probe-ws/scripts/probe_base_collapse.py) and [fresh-process physics companion](/home/sat/mcrl-v025-probe-ws/scripts/probe_base_collapse_physics.py).

Both successful runs used `/home/sat/mcrl-leo-handover/.venv/bin/python`, `nice -n 15`, one Python process at a time, and all listed BLAS thread controls set to 1. Peak RSS was 1,486,060 KiB for concentration and 1,220,120 KiB for realised pooling. Failed exact-S_UNI attempts were watchdog-terminated before crossing 3,900,000 KiB; the final low-memory timeout peaked at 2,320,624 KiB by `/usr/bin/time -v`.
