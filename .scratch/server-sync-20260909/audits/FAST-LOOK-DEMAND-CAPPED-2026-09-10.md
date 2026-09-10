**Demand-capped gain: NOT COMPUTABLE from the written receipts; the only recoverable headline remains +113.412% under delivered CAPACITY.**

`DIAGNOSTIC_NOT_CLAIM` · `FAST_LOOK_TWO_ANCHORS` · receipt-only audit

## Stop result

The requested `DEMAND_CAPPED` and `ATTAINMENT_ONLY` rescorings cannot be computed from the receipts that were written. I stopped rather than approximating them, and did not rerun or refine the search.

The fast-look optimizer kept the best-found power and ACM-mode vectors only in in-memory `slots` objects. Its JSON writer serialized each setting as only:

`bits`, `ee_bit_per_j`, `joules`, `mode_counts`, `rate_target_attained_count`, and `served_count`.

The corrected oracle receipt is coarser still: its committed `ORACLE_SET` has only `bits`, `configuration_id`, `ee_bit_per_j`, `joules`, `relative_ee_gain_over_UNILATERAL`, and `served_count`. The `configuration_id` preserves the association, not the best-found power or mode controls.

Consequently, the written artifacts lack:

- for `DEMAND_CAPPED`, each setting's per-user delivered rate at every boundary after exact rational-subslot weighting, or equivalent per-boundary/subslot user delivery records;
- for `ATTAINMENT_ONLY`, each setting's integrated delivered bits keyed by user;
- for the requested split, declared and best-found per-user integrated/capped bits keyed to user, so the 142 declared attainers and 58 declared non-attainers can be followed; and
- as an alternative replay representation, the best-found power and ACM-mode choices for every boundary and rational subslot.

Aggregate bits, attainment counts, mode histograms, and joules do not identify any of those quantities. Many different per-user delivery distributions have the same stored aggregates but different capped totals, strict totals, and cohort splits.

## What remains reproducible: CAPACITY only

The following is arithmetic over the stored fast-look aggregates. It reproduces the published capacity headline exactly at stored precision, but it is not an independent physical rescore because the chosen controls were not serialized.

| Anchor | Numerator | Declared EE (Mbit/J) | Best-known EE (Mbit/J) | Relative gain | Integrated bits, declared → best-known (Gbit) | Joules, declared → best-known | Served, declared → best-known | Rate target attained, declared → best-known |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2025-11-04, step 0 | `CAPACITY` | 46.715 | 100.727 | +115.620% | 164.371 → 359.764 | 3518.587 → 3571.681 | 100 → 100 | 72 → 100 |
| 2025-11-04, step 0 | `DEMAND_CAPPED` | N/A | N/A | N/A | N/A | 3518.587 → 3571.681 | 100 → 100 | 72 → 100 |
| 2025-11-04, step 0 | `ATTAINMENT_ONLY` | N/A | N/A | N/A | N/A | 3518.587 → 3571.681 | 100 → 100 | 72 → 100 |
| 2025-11-04, step 1 | `CAPACITY` | 44.100 | 93.086 | +111.081% | 163.005 → 344.961 | 3696.280 → 3705.830 | 100 → 100 | 70 → 100 |
| 2025-11-04, step 1 | `DEMAND_CAPPED` | N/A | N/A | N/A | N/A | 3696.280 → 3705.830 | 100 → 100 | 70 → 100 |
| 2025-11-04, step 1 | `ATTAINMENT_ONLY` | N/A | N/A | N/A | N/A | 3696.280 → 3705.830 | 100 → 100 | 70 → 100 |
| Two-anchor pool | `CAPACITY` | 45.375 | 96.836 | +113.412% | 327.376 → 704.725 | 7214.867 → 7277.511 | 200 → 200 | 142 → 200 |
| Two-anchor pool | `DEMAND_CAPPED` | N/A | N/A | N/A | N/A | 7214.867 → 7277.511 | 200 → 200 | 142 → 200 |
| Two-anchor pool | `ATTAINMENT_ONLY` | N/A | N/A | N/A | N/A | 7214.867 → 7277.511 | 200 → 200 | 142 → 200 |

Under `CAPACITY`, pooled integrated bits rose by **377.349 Gbit**, or **+115.265%**, while pooled energy rose by **62.643 J**, or **+0.868%**. These are recoverable aggregate facts; their distribution across users is not.

## Faithful cap placement

If the missing records existed, the faithful `DEMAND_CAPPED` calculation would apply the cap **per user per boundary, after exact rational-subslot weighting and before trapezoidal endpoint integration**:

`rate[u,b] = Σ_s fraction[b,s] × delivered_capacity[u,b,s]`

`capped_rate[u,b] = min(rate[u,b], contracted_rate[u])`

The capped boundary rates would then be integrated across the unchanged intervals using the same trapezoidal rule. This placement treats the contracted rate as each user's wall-clock demand at each boundary. Capping raw subslot spectral capacity before applying its TDM fraction would cap the wrong quantity; capping only the endpoint total would let excess at one boundary erase unmet demand at another.

## Direct answers

- **How much of +113.4% survives demand capping?** Not determinable from the written receipts.
- **How much of the bit increase went to users already at target versus bringing users up to target?** The total capacity increase is 377.349 Gbit, but its requested split is not determinable without per-user results and declared-attainer membership.
- **Does the improvement still exist under `ATTAINMENT_ONLY`, and at what size?** Not determinable from the written receipts. The attainment counts alone do not determine the credited bits under the requested numerator.

No sealed objective, constant, threshold, sign, seed, horizon, price, service guard, or acceptance rule was changed. The sealed objective was not replaced. This audit reports that the proposed additional numerators cannot be recovered from the artifacts as written.

## Exact reproduction command

From `/home/sat/mcrl-v025-ceiling30-ws`:

```bash
nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/control_law_demand_capped_receipt_audit.py
```

The script performs existing-JSON arithmetic and receipt-schema checks only. It does not load the simulator, rebuild the world, search, learn, or train. Its terminal status is `BLOCKED_MISSING_RECEIPT_FIELDS`.
