# Coalition coverage audit — 2026-09-09

`DIAGNOSTIC_NOT_CLAIM`. This is a read-only audit of the inherited full-scale pilot rows, not an experiment and not claim evidence.

## 1. Coalition-size histogram

**Sizes 2–6 are not adequately represented: size 2 has 180/180 rows, while sizes 3, 4, 5, and 6 have zero; the learner therefore saw the verified two-user case but never the verified three-user case.**

| Coalition size | Rows | Share |
|---:|---:|---:|
| 2 | 180 | 100.000% |
| 3 | 0 | 0.000% |
| 4 | 0 | 0.000% |
| 5 | 0 | 0.000% |
| 6 | 0 | 0.000% |

No other coalition sizes occur. The requested absolute counts for sizes 2–6 are **180, 0, 0, 0, and 0**, respectively.

| Statistic | Minimum | P05 | P25 | P50 | P75 | P95 | Maximum |
|---|---:|---:|---:|---:|---:|---:|---:|
| Coalition size | 2 | 2 | 2 | 2 | 2 | 2 | 2 |

The corpus has 180 coalition shards and 180 coalition rows: 90 anchors in each of `V025_PROBE/world/1` and `V025_PROBE/world/2`. Each shard has one header and one row, all rows have `split: TRAIN`, and the recorded size, member count, and changed-user inventory agree on every row.

The adjacent 176,223 rows are the Q1/Q2 per-action source corpus, not additional coalition rows. The full training manifest confirms `aggregate_batch_rows.C3 = 180`. `FULL`, `DROP_C1`, and `DROP_C2` use this informed C3 batch; `DROP_C3` and `ALL_NEUTRAL_CONTROL` use a neutral C3 batch.

## 2. Exact interaction target by size

The audited value is `psi_normalized_hex`, the target actually loaded into `CoalitionBatch.target_psi` by [learner.py](/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/learner.py:580). It is the exact interaction objective divided by `kappa_normalization_bits`. All 180 rows carry this finite target, are uncapped, and are marked `EXACT_SHAPLEY_SMALL_SET`.

| Size | N | Mean | Population SD | Min | P05 | P25 | P50 | P75 | P95 | Max | Positive |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 180 | 10.835500 | 26.131451 | -46.069323 | -24.371692 | -6.140488 | 5.287294 | 30.619912 | 59.674021 | 84.966530 | 108/180 (60.000%) |
| 3 | 0 | — | — | — | — | — | — | — | — | — | — |
| 4 | 0 | — | — | — | — | — | — | — | — | — | — |
| 5 | 0 | — | — | — | — | — | — | — | — | — | — |
| 6 | 0 | — | — | — | — | — | — | — | — | — | — |

At size 2 there are 72 negative targets and no exact zeros. Small coalitions are not rare—they are the entire corpus—but no cross-size comparison is possible. The coverage hole is specifically **every size above 2**, including the verified size-3 mechanism.

## 3. How training coalitions were generated

This was **not uniform mask sampling**. It was deterministic, fixed-size selection from a score-shortlisted catalogue.

The run fixes `PILOT_PRIMITIVE_SOURCE_FALLBACK = True` in [run_v025_pilot_c3.py](/home/sat/mcrl-v025-pilot-ws/scripts/run_v025_pilot_c3.py:89). For every anchor, that path builds the bounded catalogue, discards everything except configurations changing exactly two users, and takes the lexicographically smallest configuration ID:

```python
catalogue, _ = ENGINE._catalogue_with_census(...)
pairwise = [row for row in catalogue if row.changed_users == 2]
selected = min(pairwise, key=lambda row: row.configuration_id)
```

These are [run_v025_pilot_c3.py lines 501–508](/home/sat/mcrl-v025-pilot-ws/scripts/run_v025_pilot_c3.py:501).

The upstream catalogue ranks users by their best exact nonlinear nominal unilateral surplus, retains ten users, and enumerates pairs using each user’s first two legal proposals:

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

These are [run_v025_matrix_probe.py lines 619–640](/home/sat/mcrl-v025-pilot-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:619). Row generation then writes exactly one coalition row per anchor ([run_v025_pilot_c3.py lines 1009–1016](/home/sat/mcrl-v025-pilot-ws/scripts/run_v025_pilot_c3.py:1009)).

This rule mechanically explains the histogram.

## 4. Within-anchor coverage

| Per-anchor quantity | Result over 180 anchors |
|---|---:|
| Coalition rows | 1 at every anchor |
| Distinct coalitions | 1 at every anchor |
| Distinct coalition sizes | 1 at every anchor |

There are 91 distinct changed-user sets globally, but no anchor has two coalitions or two sizes. The corpus therefore has **zero within-anchor coalition or size variation**. Its 180 anchors provide only one supervised interaction point apiece and cannot identify how interaction changes between candidate coalitions at a fixed anchor.

## 5. Can evaluation propose a small coalition?

**Yes. Evaluation can propose size 2, and the observed evaluation contained candidates at sizes 3–6.**

The standard catalogue explicitly constructs pairwise candidates among the top-ten users and their top-two options ([run_v025_matrix_probe.py lines 633–640](/home/sat/mcrl-v025-pilot-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:633)). It also constructs beam-evacuation sets by moving every incumbent user on an active beam ([lines 642–653](/home/sat/mcrl-v025-pilot-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:642)), allowing sizes 3–6 or larger depending on occupancy. The `P-u` catalogue independently enumerates pairs among its ten ranked users ([run_v025_pilot_c3.py lines 1428–1441](/home/sat/mcrl-v025-pilot-ws/scripts/run_v025_pilot_c3.py:1428)).

The five-anchor minimal evaluation receipts show actual `P-u` availability:

| Candidate size | Anchors with a positive-joint candidate | FULL selections per catalogue-anchor variant |
|---:|---:|---:|
| 2 | 3/5 | 0 |
| 3 | 3/5 | 0 |
| 4 | 3/5 | 0 |
| 5 | 3/5 | 0 |
| 6 | 2/5 | 0 |
| 100 | 5/5 | 10 |

Thus neither “the head never saw size 2” nor “the selector is never offered size 2” applies.

What does apply is: **the informed interaction head never saw sizes 3–6, although evaluation can ask it to score them; and even when small positive-joint candidates were present, FULL chose size 100 every time in this five-anchor diagnostic.**

## Audit basis

- Coalition corpus: `/home/sat/mcrl-v025-pilot-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/rows/world-*/*coalition-anchor-*.jsonl`
- Row manifest SHA-256: `490925bc04f1b3d1ea9d69a3f825993d4ed545c6234836f08720e0fd595b98a6`
- Size percentiles use nearest-rank statistics; target percentiles use linear interpolation.
- “Positive” means `psi_normalized > 0`; SD is population SD.
- Validation passed: 180 TRAIN rows, histogram `{2: 180}`, 108 positive targets, and exactly one coalition and one size at every anchor.
- No source workspace was modified.

Saved as [COALITION-COVERAGE-2026-09-09.md](/home/sat/mcrl-v025-coverage-ws/COALITION-COVERAGE-2026-09-09.md).
