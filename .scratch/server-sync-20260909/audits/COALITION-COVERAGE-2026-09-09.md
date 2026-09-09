# Coalition coverage audit — 2026-09-09

`DIAGNOSTIC_NOT_CLAIM`. This is a read-only audit of the inherited full-scale pilot rows, not an experiment and not claim evidence.

## 1. Coalition-size histogram (deliverable)

**Sizes 2–6 are not adequately represented: size 2 has 180/180 rows, while sizes 3, 4, 5, and 6 have zero; the learner therefore saw the verified two-user case but never the verified three-user case.**

The full histogram over every stored C3 `TRAIN` row is:

| Coalition size | Rows | Share |
|---:|---:|---:|
| 2 | 180 | 100.000% |
| 3 | 0 | 0.000% |
| 4 | 0 | 0.000% |
| 5 | 0 | 0.000% |
| 6 | 0 | 0.000% |

No other coalition sizes occur. Thus the requested absolute counts for sizes 2, 3, 4, 5, and 6 are **180, 0, 0, 0, and 0**, respectively.

| Statistic | Minimum | P05 | P25 | P50 | P75 | P95 | Maximum |
|---|---:|---:|---:|---:|---:|---:|---:|
| Coalition size | 2 | 2 | 2 | 2 | 2 | 2 | 2 |

The corpus has 180 coalition shards and 180 coalition rows: 90 anchors in each of `V025_PROBE/world/1` and `V025_PROBE/world/2`. Each shard has one header and one row, all rows have `split: TRAIN`, and `original_changed_user_count`, the member count, and the recorded changed-user inventory agree on every row. The adjacent 176,223 rows are the Q1/Q2 per-action source corpus, not additional coalition rows. The full training manifest confirms `aggregate_batch_rows.C3 = 180`; its completed learned lineages made one full-batch C3 update per source epoch. The `FULL`, `DROP_C1`, and `DROP_C2` arms use this informed C3 batch; `DROP_C3` and `ALL_NEUTRAL_CONTROL` use the neutral C3 batch.

## 2. Exact interaction target by size

The audited value is `psi_normalized_hex`, the scalar target actually loaded into `CoalitionBatch.target_psi` by [learner.py](/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/learner.py:580). It is the exact interaction objective divided by the row's `kappa_normalization_bits`; it is dimensionless. All 180 rows carry this finite target, are uncapped (`capped_decomposition: false`), and are marked `EXACT_SHAPLEY_SMALL_SET`.

| Size | N | Mean | Population SD | Min | P05 | P25 | P50 | P75 | P95 | Max | Positive |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 180 | 10.835500 | 26.131451 | -46.069323 | -24.371692 | -6.140488 | 5.287294 | 30.619912 | 59.674021 | 84.966530 | 108/180 (60.000%) |
| 3 | 0 | — | — | — | — | — | — | — | — | — | — |
| 4 | 0 | — | — | — | — | — | — | — | — | — | — |
| 5 | 0 | — | — | — | — | — | — | — | — | — | — |
| 6 | 0 | — | — | — | — | — | — | — | — | — | — |

At size 2 there are also 72 negative targets and no exact zeros. Small coalitions are not rare in this corpus—they are the entire corpus—but the corpus provides no cross-size evidence about whether positive interaction concentrates at size 2 versus size 3–6. The actionable coverage hole is specifically **all sizes above 2**, including the verified size-3 mechanism.

## 3. How training coalitions were generated

This was **not uniform mask sampling**. It was a deterministic, fixed-size selection from a score-shortlisted catalogue. The run fixes `PILOT_PRIMITIVE_SOURCE_FALLBACK = True` in [run_v025_pilot_c3.py](/home/sat/mcrl-v025-pilot-ws/scripts/run_v025_pilot_c3.py:89), and `_build_anchor_rows` dispatches to that primitive path at lines 537–543. For each anchor the primitive path builds the bounded catalogue, discards every entry except configurations changing exactly two users, and chooses the lexicographically smallest `configuration_id`—not a random mask and not the highest interaction label:

```python
catalogue, _ = ENGINE._catalogue_with_census(...)
pairwise = [row for row in catalogue if row.changed_users == 2]
selected = min(pairwise, key=lambda row: row.configuration_id)
```

Those are [run_v025_pilot_c3.py lines 501–508](/home/sat/mcrl-v025-pilot-ws/scripts/run_v025_pilot_c3.py:501). The upstream bounded catalogue first ranks users by their best exact nonlinear nominal unilateral surplus and retains ten users, then enumerates pairs over each user's first two legal proposals:

```python
ranked_users = sorted(
    users,
    key=lambda user: (-best_surplus[user], user),
)[:PAIRWISE_TOP_K_USERS]
...
for first, second in itertools.combinations(ranked_users, 2):
    for first_row in unilaterals[first][:TOP_PROPOSALS]:
        for second_row in unilaterals[second][:TOP_PROPOSALS]:
            ...
            rows.append(_configuration(base, mapping, kind="pairwise-top10-top2"))
```

These are [run_v025_matrix_probe.py lines 619–640](/home/sat/mcrl-v025-pilot-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:619); the constants are top 10 users and top 2 options per user. Finally, row generation writes exactly one coalition row per anchor ([run_v025_pilot_c3.py lines 1009–1016](/home/sat/mcrl-v025-pilot-ws/scripts/run_v025_pilot_c3.py:1009)). This rule mechanically explains the degenerate histogram.

## 4. Within-anchor coverage

| Per-anchor quantity | Result over 180 anchors |
|---|---:|
| Coalition rows | 1 at every anchor |
| Distinct coalitions | 1 at every anchor |
| Distinct coalition sizes | 1 at every anchor |

There are 91 distinct changed-user sets globally, but no anchor has two coalitions or two sizes. Consequently the corpus has **zero within-anchor coalition or size variation**. The 180 different anchors cannot identify how interaction changes between candidate coalitions at a fixed anchor; they provide only one supervised interaction point per anchor.

## 5. Can evaluation propose a small coalition?

**Yes. The evaluation candidate generator can propose size 2, and the observed pilot evaluation also contained candidates at sizes 3–6.** The standard bounded catalogue explicitly constructs pairwise candidates among the top-ten ranked users and their top-two options ([run_v025_matrix_probe.py lines 633–640](/home/sat/mcrl-v025-pilot-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:633)). It also constructs a beam-evacuation set by moving every incumbent user on an active beam ([lines 642–653](/home/sat/mcrl-v025-pilot-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:642)), so its resulting size can be 3, 4, 5, 6, or larger depending on beam occupancy. The `P-u` catalogue independently enumerates all pairs among its ten ranked users ([run_v025_pilot_c3.py lines 1428–1441](/home/sat/mcrl-v025-pilot-ws/scripts/run_v025_pilot_c3.py:1428)).

The five-anchor minimal evaluation receipts establish actual availability in the `P-u` catalogue, not only theoretical reachability. FULL's selection counts were identical for the `P-a0` and `P-u` catalogue-anchor variants:

| Candidate size | `P-u` anchors with at least one positive-joint candidate | FULL selections per catalogue-anchor variant (2 seeds × 5 anchors) |
|---:|---:|---:|
| 2 | 3/5 | 0 |
| 3 | 3/5 | 0 |
| 4 | 3/5 | 0 |
| 5 | 3/5 | 0 |
| 6 | 2/5 | 0 |
| 100 | 5/5 | 10 |

Therefore the “selector is never offered size 2” failure does **not** apply, and neither does “the head never saw size 2.” What does apply is: **the informed interaction head never saw sizes 3–6, while evaluation could ask it to score them; and even when small positive-joint candidates were present, FULL chose size 100 every time in this five-anchor diagnostic.** The latter is an observed ranking outcome, not proof that the candidate generator excludes small coalitions.

## Audit basis and method

- Coalition corpus: `/home/sat/mcrl-v025-pilot-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/rows/world-*/*coalition-anchor-*.jsonl`.
- Row manifest: `/home/sat/mcrl-v025-pilot-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-rows-manifest.json` (SHA-256 `490925bc04f1b3d1ea9d69a3f825993d4ed545c6234836f08720e0fd595b98a6`).
- Training manifest: `/home/sat/mcrl-v025-pilot-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-training-manifest.json`.
- Evaluation availability check: inherited five-anchor receipts at `/home/sat/mcrl-v025-pilot-ws/artifacts/v025-pilot-min-20260909-PILOT_NOT_CLAIM/evaluation/PILOT_NOT_CLAIM-raw-receipts.jsonl` and their `u_positive_joint_sizes` field.
- Size percentiles use nearest-rank order statistics; target percentiles use linear interpolation. “Positive” means `psi_normalized > 0`; SD is population SD over the complete 180-row corpus.
- No source workspace was modified. The only written file is this report in the coverage workspace.
