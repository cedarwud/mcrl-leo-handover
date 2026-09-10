**The pooled gain from enabling the exact set residual is +2.88% for delivered capacity and +5.62% demand-capped; below the predeclared ten per cent screen.**

# Oracle residual toggle — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`

## Decisive result

### Delivered capacity

| selector | pooled EE (Mbit/J) | numerator (Gbit) | energy (J) | served | rate-target attained | selected-size counts |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ADDITIVE_ONLY` | 9.204712 | 610.442970 | 66318.526800 | 488 | 180 | `{'4': 4, '7': 4}` |
| `WITH_RESIDUAL` | 9.469707 | 630.897774 | 66622.734941 | 503 | 196 | `{'1': 2, '3': 1, '5': 3, '6': 2}` |

Residual gain: **+2.88%**; selectors differ on **8/8** anchors; 10% screen: **BELOW**.

| anchor | additive EE | residual EE | gain | different | sizes A/R | served A/R | target A/R |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: |
| V025_PROBE_R2/world/1:step/0 | 9.229053 | 9.953318 | +7.85% | yes | 7/1 | 61/67 | 22/26 |
| V025_PROBE_R2/world/1:step/1 | 11.367263 | 11.954153 | +5.16% | yes | 7/5 | 67/72 | 28/31 |
| V025_PROBE_R2/world/1:step/2 | 10.871514 | 11.113590 | +2.23% | yes | 7/5 | 67/71 | 22/26 |
| V025_PROBE_R2/world/1:step/3 | 6.886948 | 6.933930 | +0.68% | yes | 7/3 | 54/53 | 20/22 |
| V025_PROBE_R2/world/2:step/0 | 8.433042 | 8.474465 | +0.49% | yes | 4/6 | 58/58 | 20/20 |
| V025_PROBE_R2/world/2:step/1 | 12.062040 | 12.173839 | +0.93% | yes | 4/6 | 65/66 | 30/30 |
| V025_PROBE_R2/world/2:step/2 | 11.090171 | 11.338885 | +2.24% | yes | 4/1 | 67/68 | 27/26 |
| V025_PROBE_R2/world/2:step/3 | 5.190929 | 5.257463 | +1.28% | yes | 4/5 | 49/48 | 11/15 |

### Demand-capped

| selector | pooled EE (Mbit/J) | numerator (Gbit) | energy (J) | served | rate-target attained | selected-size counts |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ADDITIVE_ONLY` | 8.548697 | 563.369024 | 65901.159454 | 486 | 181 | `{'1': 2, '4': 3, '7': 3}` |
| `WITH_RESIDUAL` | 9.029226 | 601.150664 | 66578.317281 | 503 | 192 | `{'1': 1, '3': 1, '4': 1, '5': 3, '6': 2}` |

Residual gain: **+5.62%**; selectors differ on **8/8** anchors; 10% screen: **BELOW**.

| anchor | additive EE | residual EE | gain | different | sizes A/R | served A/R | target A/R |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: |
| V025_PROBE_R2/world/1:step/0 | 8.751549 | 9.397722 | +7.38% | yes | 7/1 | 61/67 | 22/26 |
| V025_PROBE_R2/world/1:step/1 | 10.784458 | 11.375875 | +5.48% | yes | 7/5 | 67/72 | 28/31 |
| V025_PROBE_R2/world/1:step/2 | 9.571960 | 10.605119 | +10.79% | yes | 7/5 | 67/71 | 22/24 |
| V025_PROBE_R2/world/1:step/3 | 6.132764 | 6.526545 | +6.42% | yes | 1/3 | 51/53 | 20/22 |
| V025_PROBE_R2/world/2:step/0 | 8.125603 | 8.176333 | +0.62% | yes | 4/6 | 58/58 | 20/20 |
| V025_PROBE_R2/world/2:step/1 | 11.423559 | 11.642121 | +1.91% | yes | 4/6 | 65/66 | 30/30 |
| V025_PROBE_R2/world/2:step/2 | 10.515941 | 10.806532 | +2.76% | yes | 4/4 | 67/68 | 27/24 |
| V025_PROBE_R2/world/2:step/3 | 4.547709 | 5.086537 | +11.85% | yes | 1/5 | 50/48 | 12/15 |

Across the 32 selector/numerator/anchor choices, **0 selected a nonzero adjacent-mode offset**. The coarse joint power/mode alternatives were present in every catalogue, but every winner retained the corrected contracted-rate target control; the realised per-user RF powers and target/transmitted modes are still preserved for all 22 distinct selected profiles.

## Fixed catalogue and selector rules

The rules were fixed before evaluating outcomes. Each anchor catalogue is built directly around the nearest-eligible incumbent; no exact-search, local-search, or learned prefix is run.

- incumbent;
- all 2,700 legal association singletons (27 alternatives for each of 100 users), without shortlisting;
- both adjacent-mode control singletons for every user;
- same-origin-beam, common-destination occupant bundles of sizes 2–4, enumerated canonically and capped at 1,024 generation attempts;
- complete-beam evacuations to every common legal destination in canonical order, capped at 1,024 attempts;
- beam-wide adjacent-mode controls; and
- ±1 ACM-rung controls for every changed member of the first 512 joint assignment candidates in canonical configuration order.

The hard post-deduplication cap is **8,192** and is asserted, never silently truncated. A mode offset chooses an adjacent existing ACM target rung. The corrected `Gamma/q_0.10(elevation)` provisioning and exact coupled-power solve are then applied. Thus these are joint power-and-mode controls, not changed thresholds. The contracted target remains 50 Mbit/s and is also the separate attainment criterion.

For a candidate changed-user set A, each per-user term is the exact 48-boundary surplus change of that user's atomic association/control change from the incumbent. `ADDITIVE_ONLY` sums those terms. `WITH_RESIDUAL` adds the exact residual `joint − sum(singletons)`, reconstructing the complete candidate surplus exactly. Both use the same eligibility guard (valid corrected solve and committed served count no lower than the incumbent), incumbent-first/lexicographic tie-break, observable catalogue, and candidate profiles.

A separate exact-Fraction Dinkelbach solve uses one common price across all eight anchors for each selector and numerator. Capacity uses all delivered bits. Demand-capped uses `min(per-user delivered bits, 50 Mbit/s × 30.08 s)`. Reported EE is always the realised 48-boundary ratio of pooled selected totals, never a fixed-price boundary-0 snapshot or a mean of anchor ratios.

## Interpretation

The bounded direct catalogue does not clear the planning screen under either numerator. Under the declared rule, this stops this candidate design. It does **not** establish universal impossibility for every conceivable catalogue, factorization, or control arrangement.

Served means at least one realised physical decode over the committed horizon. Rate-target attainment means integrated per-user delivery reached 50 Mbit/s × 30.08 s. They are reported separately and never substituted for one another.

## Custody and reproduction

The machine receipt is `.scratch/oracle-residual-toggle-20260910/result.json` (SHA-256 `4292fe01f183707be60d1bdfefb3ce19727b97ba9e02268f0c659b197ba844ce`). It contains all candidate definitions and exact rational score components. The selected-record file is `.scratch/oracle-residual-toggle-20260910/selected-records.json` (SHA-256 `bd66a625c4108f7829b883b2174e807b7cf14a0bbc7090955d7f27eb20350cd6`); it contains all chosen assignments, 48-boundary per-user RF powers, target/transmitted modes, per-user delivery, service flags, and per-record digests. Selected-record canonical payload digest: `b4edc8f94a5339964602a3fd7e32ef653d9bc8b4eb83d41f007d3a026fc61733`.

From `/home/sat/mcrl-v025-arch-ws`:

```bash
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 PYTHONPATH=src nice -n 15 \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/run_oracle_residual_toggle.py --workers 1 \
  --output .scratch/oracle-residual-toggle-20260910/result.json \
  --selected-records .scratch/oracle-residual-toggle-20260910/selected-records.json \
  --report ORACLE-RESIDUAL-TOGGLE-2026-09-10.md
```

Exactly 1 worker process was used. No test split, learner, training job, or policy run was opened. Runner SHA-256: `e204ddf332ffdbc98679a2b9b4cb63261f137a9fb42b08edfad58506587a10a3`; corrected margin source SHA-256: `bf9f3cfecba54125c6a7736f550032e6bd7292f03f8fc6281f1d02979c14a85f`; probe SHA-256: `f4122d6784cb56de7743c55d51dc80a6c968ccea601d637cd1b41a8b5604c76c`. Reference source was read-only at commit `9c73dcd90a2a1fbefab787208ea77c9e72863551`; the virtual environment was not modified.

## Scope

This is an exact-arithmetic selector toggle over a bounded, predeclared catalogue and a fixed physical evaluator. It changes no sealed constant, threshold, sign, seed, horizon, price, service guard, acceptance rule, or declared physics. Binary64 simulator outputs are lifted exactly to `Fraction` before decomposition, residual construction, tie comparison, and common-price optimization. The result is diagnostic opportunity evidence only.
