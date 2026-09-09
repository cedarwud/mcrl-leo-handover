End-to-end pass finished. Report written to `/home/sat/mcrl-v025-pilot-ws/V025-PILOT-MIN-REPORT-2026-09-09.md` (sha256 `37a83abe…`).

---

# V0.25 minimal pilot — end-to-end pass report (`PILOT_NOT_CLAIM`)

**Every number below is `PILOT_NOT_CLAIM`.** Per the track declaration, none of it may enter the paper, select any configuration/regime/margin/seed count, or be cited for or against C1/C2/C3.

## What actually ran

The previous agent had already completed **rows** and **training** at full scale (2 worlds × 90 anchors, 176 223 source rows, 4 seeds × 5 learned arms × 2000 epochs, 400 checkpoints). Only **evaluation** had failed — four times. I reused rows and training verbatim and drove the evaluation phase to completion at minimal scale.

Scope of this pass: rows from **world 1 only, anchor shards 000–004**; eval on **world 3, 5 anchors, nearest-eligible carrier only**; **2 learner seeds**; arms **FULL, DROP_C3, BASELINE** (+ S0, S_UNI); **epoch-200 checkpoint — not the sealed 2000**.

## Realised pooled EE per arm (world 3, 5 anchors, 2 seeds)

| Arm | Pooled EE (bits/J), P-a0 | Availability |
|---|---:|---:|
| FULL | 34 250 712 | 0.7438 |
| DROP_C3 | 23 517 487 | 0.7925 |
| S0 (exact) | 17 589 688 | 0.7707 |
| BASELINE | 16 987 632 | 0.7632 |
| S_UNI (iterated) | 16 987 632 | 0.7632 |

**Contrasts (relative pooled-EE difference):** FULL vs DROP_C3 **+0.4564** (P-u: +0.4596) · FULL vs S0 **+0.9472** · FULL vs S_UNI **+1.0162**.

## Matched-anchor g_A/g_I decomposition (FULL, 10 points)

| | min | p50 | max |
|---|---:|---:|---:|
| g_A (additive) | −0.6045 | 1.1249 | 1.7730 |
| g_I (interaction) | 0.4645 | 0.6481 | 1.1640 |

g_I is strictly positive at every anchor; g_A goes negative at one. Identical on both catalogue anchors.

## C2 tie frequency

**0.0** (`c2_tie_frequency` 0.0, `c2_tie_pair_fraction_mean` 0.0). Build 3 had no C2 tie-break and hard-coded this field to `False`; I implemented the smallest schema-satisfying measurement — exact equality of the FULL-arm C2 head score against the incumbent over non-incumbent (user, action) candidates. The zero is now measured rather than by construction, but it proxies head indiscriminability, not a build-3 code path.

## Wall time per phase

| Phase | Wall | Core | Provenance |
|---|---:|---:|---|
| rows | 1533.9 s | 1527.6 s | **inherited full-scale**, not re-run |
| training | 248.0 s | 2840.7 s | **inherited full-scale**, not re-run |
| evaluation | 600.8 s | 420.1 s | **this minimal run** |

Of which: eval tape build 60.1 s (8 of 33 steps); per-decision total wall p50 42.2 s, p95 248.9 s; physics calls per anchor p50 6917.

## DEFECTS (9 new, full text in the report)

- **D-MIN-1 (root cause of the 4 prior failures).** `build_world_tape(steps=33)` on world 3 did not finish in 19 wall minutes; SIGINT put the stack in `provider_legacy.step_arrays → channel.transmit_gain_linear → runtime/bessel._series_array`. Worked around by truncating the eval tape to a `EVAL_ANCHOR_STEPS + 3 = 8`-step prefix (60.1 s). **The Bessel series path is the highest-value engineering target before any full-scale evaluation.**
- **D-MIN-2.** `S_UNI` pooled EE equals `BASELINE` to the last digit — under the 5 s budget it accepted no unilateral improvement at any anchor. The FULL-vs-S_UNI contrast above is an *empty* comparator; do not read it as evidence.
- **D-MIN-3.** FULL selects the all-users (size-100) coalition at all 10 anchor-seeds, never sizes 2–6, despite positive-joint escape opportunities there. Likely an epoch-200 head-scale artefact. 2 of 10 were harmful by exact joint delta.
- **D-MIN-4.** `V_CA` net is −1.365e11 bit-equivalents while FULL has the *highest* pooled EE. Either the V_CA reference or the pooled-EE aggregation is not measuring what the schema intends — must be resolved before V_CA is reported at scale.
- **D-MIN-5.** C2 tie statistic newly implemented (above).
- **D-MIN-6.** DROP_C1, DROP_C2, ALL_NEUTRAL_CONTROL skipped for time; their epoch-200 checkpoints are present and only `PILOT_ARMS` needs widening.
- **D-MIN-7.** Statistical power is nil — 10 FULL decisions; p05/p95 coincide with min/max.
- **D-MIN-8.** Rows and training were inherited; a defect confined to `generate_rows`/`train` would not be caught by this pass.
- **D-MIN-9.** `top_choice_agreement` is 0.5 on P-a0 but 0.0 on P-u with no mechanism identified at this sample size.

Code changes are engineering-only scale knobs (`--min-pilot`, tape-prefix truncation, progress prints) plus the C2 tie measurement; defaults still reproduce the full-scale pilot exactly. Artefacts in `artifacts/v025-pilot-min-20260909-PILOT_NOT_CLAIM/`; the original full-scale directory was left untouched.
