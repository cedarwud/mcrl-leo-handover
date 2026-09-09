**No—`ORACLE_FROM_BASE` is far worse than `UNILATERAL`: it recovers only 6.03% of A1's pooled uplift under the sealed rule and 4.99% under the margin rule.**

# Prefix ablation — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`

## Direct answers

1. **A3 does not reach anywhere near A1.** On pooled committed energy efficiency, A3 is -80.41% below A1 under sealed provisioning and -77.21% below under margin provisioning. Relative to A0, A3 gains only +35.78% and +21.63%, versus A1's +593.06% and +433.66%. The raw geometric state therefore does not expose a large one-catalogue learning band; the non-learned prefix creates almost all of it.

2. **What is missing is a long sequence of context-dependent singleton moves.** The catalogue can move only prescribed groups of at least two users, and every member is restricted to one alternate computed at the current seed. A1 repeatedly changes the interference/occupancy context and then recomputes unilateral choices. Counts are given below; no accepted A1 transition is directly expressible as a catalogue row, and the final A1 configuration is absent from all eight initial A3 catalogues under both rules.

3. **The unilateral prefix buys both quality and practical speed under the margin rule; under sealed provisioning it buys speed and anchor-level consistency, though not the largest pooled value observed by round 16.** Margin A4 is -20.93% below A1, worse on 8/8 anchors, and costs 60,198 evaluations / 904.8 s per anchor versus A1's 12,917 / 35.9 s. Sealed A4 reaches a pooled value +9.38% above A1 by the cap, but remains worse on 5/8 anchors and costs 61,372 / 603.9 s versus A1's 11,300 / 29.4 s. Thus the prefix is a much cheaper route to broadly high quality; it is not proof that the catalogue-only asymptote is lower under sealed provisioning.

## Panel and invariant method

I used **eight real anchors**, fixed before results: `V025_PROBE_R2` worlds 1–2, steps 0–3. Anchor IDs and world-tape SHA-256 values are identical between rules. Selection uses realised boundary 0 held for 30.08 s and the exact binary64-derived Fraction objective `F = bits − 19720681.00172232 × joules`; committed reporting reevaluates the chosen configurations over all 48 realised boundaries. Pooled EE is `sum(bits)/sum(joules)`, never a mean of anchor ratios.

The unchanged catalogue uses same-beam occupant subsets of sizes 2–4 with the 1,024 generation-attempt cap, victim plus top-2/top-3 physical contributors, and complete-beam evacuations. It deduplicates full assignments, rejects <2-user changes, asserts rather than truncates at 4,096 unique candidates, and uses the original objective and tie-break. The incumbent fallback wins exact ties; among strict improvements the lowest configuration ID wins.

A3 derives the catalogue's required per-user alternates by evaluating every legal singleton deviation once around A0, but adopts none of them. A4 repeats that fixed-seed alternate scan plus the unchanged catalogue around each current selection. Those prerequisite evaluations are included in cost. The declared A4 cap was **16 catalogue rounds**. A round counts one complete alternate scan, catalogue generation, exact ranking, and reselection.

### Served-count guard

For **A1, A2, A3, and every A4 round**, the guard reference is the same rule-specific A0 boundary-0 selection-time served count; it is never reset to the current arm or to target attainment. A0 is the reference/fallback. Counts by W1S0…W2S3 are:

- sealed: `[38, 26, 36, 35, 28, 37, 42, 35]`

- margin: `[54, 54, 56, 47, 46, 55, 60, 45]`

`served_count` means any physical decode. `rate_target_attained_count` means integrated per-user bits reached the declared target. They are never merged below.

## Pooled results

EE is in Mbit/J. Served and target-attained values are sums over 8×100 user-anchor observations. “Worse” is strict per-anchor committed EE below A1; the selection-time fallback does not guarantee committed-horizon ordering. Costs are mean unique boundary-0 configuration evaluations and mean selector wall seconds per anchor; committed reevaluation is excluded.

### Sealed provisioning

| arm | EE | gap to A1 | gap to A0 | served | target | worse | evals | seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 `BASELINE` | 3.861 | -85.57% | +0.00% | 313 | 0 | 8/8 | 1.0 | 0.18 |
| A1 `UNILATERAL` | 26.762 | +0.00% | +593.06% | 779 | 0 | 0/8 | 11,300.5 | 29.39 |
| A2 `ORACLE_FROM_UNI` | 28.502 | +6.50% | +638.12% | 790 | 0 | 0/8 | 12,316.6 | 42.98 |
| A3 `ORACLE_FROM_BASE` | 5.243 | -80.41% | +35.78% | 393 | 0 | 8/8 | 3,834.2 | 26.83 |
| A4 `ORACLE_FROM_BASE_ITERATED` | 29.273 | +9.38% | +658.09% | 762 | 0 | 5/8 | 61,372.5 | 603.92 |

### Margin provisioning

| arm | EE | gap to A1 | gap to A0 | served | target | worse | evals | seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 `BASELINE` | 8.125 | -81.26% | +0.00% | 452 | 174 | 8/8 | 1.0 | 0.20 |
| A1 `UNILATERAL` | 43.359 | +0.00% | +433.66% | 800 | 540 | 0/8 | 12,917.1 | 35.94 |
| A2 `ORACLE_FROM_UNI` | 43.283 | -0.18% | +432.72% | 800 | 539 | 3/8 | 13,631.4 | 41.56 |
| A3 `ORACLE_FROM_BASE` | 9.883 | -77.21% | +21.63% | 495 | 191 | 8/8 | 3,837.2 | 28.44 |
| A4 `ORACLE_FROM_BASE_ITERATED` | 34.284 | -20.93% | +321.96% | 792 | 381 | 8/8 | 60,198.0 | 904.78 |

The eight-anchor margin A2 result is -0.18%, not the approximately `+0.51%` reported for the full twenty-anchor panel. This is not a changed rule: on this fixed subset A2 is lower on 3/8 committed anchor EEs, and ratio-of-sums weighting makes the pooled subset contrast slightly negative. I did not run the other twelve anchors.

## Per-anchor selector cost and A4 status

Each arm cell is `unique configuration evaluations / wall seconds`. A0/A1/A2 are cumulative stage prefixes of one isolated evaluator, matching their actual pipeline costs. A3 is A4's first-round snapshot; A4 caches only within its own iterative arm. World construction and 48-boundary committed reporting are excluded. Execution used one coordinator plus two fork workers, with OMP/OpenBLAS/MKL/NumExpr threads fixed to one and `nice -n 15`.

### Sealed provisioning

| anchor | A0 | A1 | A2 | A3 | A4 | A4 stop |
| --- | --- | --- | --- | --- | --- | --- |
| W1S0 | 1 / 0.42 | 9,235 / 22.95 | 10,324 / 30.61 | 3,843 / 22.27 | 60,336 / 436.45 | cap@16 |
| W1S1 | 1 / 0.33 | 14,500 / 30.91 | 15,461 / 37.86 | 3,905 / 20.81 | 62,889 / 404.31 | cap@16 |
| W1S2 | 1 / 0.20 | 13,339 / 35.84 | 14,245 / 42.35 | 3,862 / 31.51 | 62,340 / 641.70 | cap@16 |
| W1S3 | 1 / 0.16 | 8,857 / 35.83 | 10,324 / 74.22 | 3,827 / 45.25 | 66,430 / 1417.97 | cap@16 |
| W2S0 | 1 / 0.02 | 10,747 / 23.67 | 11,651 / 37.15 | 3,808 / 21.78 | 59,684 / 503.69 | cap@16 |
| W2S1 | 1 / 0.10 | 13,798 / 28.86 | 14,699 / 36.82 | 3,812 / 21.82 | 58,571 / 334.71 | cap@16 |
| W2S2 | 1 / 0.03 | 11,395 / 25.89 | 12,286 / 38.26 | 3,812 / 25.94 | 59,488 / 385.09 | cap@16 |
| W2S3 | 1 / 0.20 | 8,533 / 31.14 | 9,543 / 46.55 | 3,805 / 25.28 | 61,242 / 707.47 | cap@16 |

### Margin provisioning

| anchor | A0 | A1 | A2 | A3 | A4 | A4 stop |
| --- | --- | --- | --- | --- | --- | --- |
| W1S0 | 1 / 0.43 | 10,747 / 18.06 | 11,400 / 20.17 | 3,848 / 26.25 | 59,755 / 721.28 | cap@16 |
| W1S1 | 1 / 0.47 | 13,366 / 22.79 | 14,076 / 25.43 | 3,908 / 24.72 | 60,124 / 476.38 | cap@16 |
| W1S2 | 1 / 0.22 | 11,098 / 25.84 | 11,855 / 30.47 | 3,868 / 25.93 | 60,183 / 956.24 | cap@16 |
| W1S3 | 1 / 0.32 | 12,043 / 56.03 | 12,912 / 67.75 | 3,834 / 73.48 | 61,187 / 2160.14 | cap@16 |
| W2S0 | 1 / 0.03 | 13,420 / 39.60 | 14,114 / 44.55 | 3,809 / 15.50 | 61,682 / 557.62 | cap@16 |
| W2S1 | 1 / 0.01 | 15,418 / 36.77 | 16,055 / 39.17 | 3,812 / 17.72 | 59,077 / 688.15 | cap@16 |
| W2S2 | 1 / 0.04 | 11,179 / 31.90 | 11,853 / 36.63 | 3,814 / 22.25 | 59,511 / 501.63 | cap@16 |
| W2S3 | 1 / 0.11 | 16,066 / 56.57 | 16,786 / 68.28 | 3,805 / 21.62 | 60,065 / 1176.84 | cap@16 |

**A4 iterations to termination:** none terminated. All 8/8 sealed and 8/8 margin anchors made a strict improvement in every one of 16 rounds and then stopped only at the declared cap. Therefore `16` is an iteration count to the cap, not to a no-improvement fixed point.

## Missing move types

- **sealed:** A1 accepted **760** singleton moves: 607 same-satellite beam changes and 153 satellite changes. Origins had occupancy 1/2/3/4+ in 163/96/97/404 moves; 23 moved to an empty beam and 737 to an occupied beam. Exactly **0/760** are catalogue rows because the shared generator rejects every <2-user change. Only **351/760 (46.2%)** chosen destinations equal that user's one-shot BASELINE alternate. Across the net A0→A1 delta, only **284/578 (49.1%)** destinations match the baseline scan, and the complete A1 endpoint appears in the initial A3 catalogue on **0/8** anchors.

- **margin:** A1 accepted **1,106** singleton moves: 451 same-satellite beam changes and 655 satellite changes. Origins had occupancy 1/2/3/4+ in 297/274/272/263 moves; 337 moved to an empty beam and 769 to an occupied beam. Exactly **0/1,106** are catalogue rows because the shared generator rejects every <2-user change. Only **385/1,106 (34.8%)** chosen destinations equal that user's one-shot BASELINE alternate. Across the net A0→A1 delta, only **265/764 (34.7%)** destinations match the baseline scan, and the complete A1 endpoint appears in the initial A3 catalogue on **0/8** anchors.

This exposes two distinct missing capabilities. First, the catalogue cannot take a singleton step at all, even when that is the locally best strict improvement. Second, A3 freezes one alternate per user in the raw A0 context. After other users move, many A1 destinations change. A4 partially repairs the second limitation by regenerating, but it still has to bundle changes into the three hand-written group families and pay a fresh 2,700-row singleton alternate scan on every round and anchor.

## Quality versus speed at matched quality

A3 is not a matched-quality competitor: it is cheaper in unique rows than A1 but remains 77–80% below A1 in pooled EE. Under margin, no A4 round through 16 reaches A1's committed EE on any anchor, so there is **no matched-quality timing comparison** to report there.

| sealed anchor | first A4 round ≥ A1 EE | A4 evals / s | A1 evals / s |
| --- | --- | --- | --- |
| W1S2 | 12 | 46,669 / 478.66 | 13,339 / 35.84 |
| W1S3 | 12 | 49,585 / 888.87 | 8,857 / 35.83 |
| W2S3 | 12 | 45,784 / 526.47 | 8,533 / 31.14 |

Only 3/8 sealed anchors reach A1's committed EE by round 16; all first do so at round 12. On those matched anchors A4 averages 47,346 evaluations / 631.3 s versus A1's 10,243 / 34.3 s—4.62× the evaluations and 18.42× the wall time. Thus at observed matched anchor quality, the prefix is decisively a speed device. On the other five sealed anchors and all eight margin anchors, A4 never supplies a matched-quality point within the declared budget.

A2 adds relatively little cost after A1: sealed means rise from 11,300 to 12,317 evaluations and 29.4 to 43.0 s, for +6.50% pooled EE. Margin means rise from 12,917 to 13,631 and 35.9 to 41.6 s; the committed subset contrast is slightly negative as noted above.

## What was not reached

- A4 did **not** reach a no-improvement termination on any of the 16 arm/rule anchor evaluations. Its round-16 values are capped trajectory points, not certified catalogue-only optima.

- Margin A4 did **not** reach A1 quality on any anchor or in pooled EE. Sealed A4 reached A1 committed EE on only 3/8 anchors, despite exceeding A1 in pooled ratio-of-sums at round 16.

- I ran eight anchors, not the complete twenty-anchor panel. Consequently the full-panel `+6.36%`/`+0.51%` A2 figures were not targets for exact reproduction; sealed is close on this subset, while margin is negative.

- No claim is made about A4 beyond round 16 or about a learned selector operating on the larger catalogue-only trajectory. No learner, training run, policy run, tuning, or acceptance decision was performed.

## Reproduction and custody

From `/home/sat/mcrl-v025-arch-ws`:

```bash
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 PYTHONPATH=src nice -n 15 \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/run_prefix_ablation.py --provisioning-rule sealed \
  --worlds 2 --anchors-per-world 4 \
  --output .scratch/prefix-ablation-20260910/sealed.json

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 PYTHONPATH=src nice -n 15 \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/run_prefix_ablation.py --provisioning-rule margin \
  --worlds 2 --anchors-per-world 4 \
  --output .scratch/prefix-ablation-20260910/margin.json

/home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/render_prefix_ablation_report.py \
  --sealed .scratch/prefix-ablation-20260910/sealed.json \
  --margin .scratch/prefix-ablation-20260910/margin.json \
  --output PREFIX-ABLATION-2026-09-10.md
```

The runner intentionally loads the exact stage-4h reference probe and physics source read-only from `/home/sat/mcrl-v025-ladder-ws` because the current workspace copy predates the strict margin implementation. The cleared margin evaluator itself was copied into this workspace at `.scratch/prefix-ablation-20260910/cleared_margin_batch.py`; no reference workspace or virtual environment was modified.

- current workspace commit/tree: `7eb8ad3e4c8f6fe0756c7c30f4c1b35ab6a8a4f1` / `0e6481adefa86e3d32e5f152fbbdb67a02249dff`

- read-only reference commit/tree: `9c73dcd90a2a1fbefab787208ea77c9e72863551` / `1728f6b0462f86d85618a4c73f4d1dd2d2c07376`

- runner SHA-256: `a2784173ea18f1fcbfe4b2cbfe1c055537041245c608ab5a6ebb41806a4ecc41`

- reference probe SHA-256: `f4122d6784cb56de7743c55d51dc80a6c968ccea601d637cd1b41a8b5604c76c`

- copied cleared-margin SHA-256: `bf9f3cfecba54125c6a7736f550032e6bd7292f03f8fc6281f1d02979c14a85f`

- sealed receipt SHA-256: `055c6a487964853e7cc10747f33ac7beb28b1f44536ac6e0888e080bf05fe50a`

- margin receipt SHA-256: `3266e69b79d6ab8164708a0c73baa91d67f28f71bfc7aa936b0eef8aee145954`

- sealed total run wall time: `5292.162 s`; margin: `7684.668 s`

The machine-readable receipts are `.scratch/prefix-ablation-20260910/sealed.json` and `.scratch/prefix-ablation-20260910/margin.json`. They include every assignment, unilateral move, A4 round, catalogue size, guard count, committed metric, and per-arm cost used here.
