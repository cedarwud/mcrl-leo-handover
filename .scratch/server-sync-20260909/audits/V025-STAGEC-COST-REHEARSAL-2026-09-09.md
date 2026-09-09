Report written to `V025-STAGEC-COST-REHEARSAL-2026-09-09.md`. Final report follows.

---

# V025 Stage-C cost rehearsal — 2026-09-09

**These are engineering measurements on synthetic fixtures, not scientific results.** No real world was opened, no TEST data touched, no sealed artifact edited. All work was done in the snapshot copy; the live workspace was not touched. Nothing here is evidence about EE, power, or any C1/C2/C3 claim.

## Method

Python 3.13.3 / numpy 2.5.2 (scipy-openblas) from `/home/sat/mcrl-leo-handover/.venv`, `PYTHONPATH=src`. Host: 20 logical cores, 91 GiB RAM. **The box was busy throughout** (load 8.3–9.5 from the live workspace); every benchmark was pinned to one BLAS thread and run ≤1 at a time, and a fixed matmul probe confirmed single-core throughput was not degraded (48 GFLOP/s). Timings are medians of 2–5 repeats after warm-up, through the production entry points — the evaluation benchmark imports the contract-v1 acceptance fixtures, so the measured path is the one T1–T3 exercise. ≈11 core-minutes of the ≤45 budget spent, ≤1 concurrent.

## Two structural findings that change the arithmetic

**(i) There are 16 training lineages, not 96.** `V1LineageOrchestrator` is constructed per *learner seed* and `train_epoch()` updates **all five learned arms across all three routes in one epoch** (15 head updates) from one shared initialisation (`learner.py:1021–1042`); `BASELINE` is never trained. Total FLOPs are similar, but the **parallelism ceiling is 16, not 96** — which is what sets wall time.

**(ii) Evaluation emits 8 arm rows per step, not 6.** Measured receipts carry `ARM_ORDER`'s 6 plus the §C4 comparators `S0` and `S_UNI`. Arms live *inside* an allocation unit, so the panel is 160 × 16 × 2 = **5,120 units** — units are **not** multiplied by 6.

## Measured unit costs

| Phase | Unit | Measured |
|---|---|---:|
| Source build | s / 1 000 rows | **0.0451** (0.0374 at 1 k) |
| Shard write | s / 1 000 rows | **0.1374** at 16 k; 0.0960 at 1 k — **superlinear** |
| Shard bytes | bytes / 1 000 rows | **3.13 MB** (flat 1 k–16 k) |
| Learner | s / source epoch | **5.195 × 10⁻⁵ per Q1 pair** (marginal slope) |
| Learner | measured points | 0.0030 s @ 8 pairs; 0.0302 @ 320; 0.0985 @ 1 280; 0.2980 @ 5 120 |
| Checkpoint | s / 7.28 MB file | **0.131**, constant (depends only on fixed head dims) |
| Evaluation | s / world-arm-seed @ 30 steps | **1.449** (240 step rows) |
| Evaluation | s / bare fork+pipe | **0.00199** (one per unit×arm×step) |
| Evaluation | bytes / 30-step receipt | **757 KB** |
| Merge | s / step row | **5.14 × 10⁻⁵** (linear; streams) |

**Peak RSS:** source 264 MiB · learner 270 MiB · evaluation 84 MiB parent + 51 MiB forked child · merge 85 MiB, **flat from 32 to 384 receipts** (merge streams). Memory is a non-issue: 16 concurrent lineages ≈ 4.3 GB against 91 GiB.

## Projections

Panel: 5,120 units × 240 step rows = **1,228,800 step rows**, 5,120 receipts, 1,075,200 coordinator calls.

| Phase | core-h | Wall @ 20 cores | Bytes |
|---|---:|---:|---:|
| **(a) source generation** | 0.10 | minutes | 6.00 GB |
| **(b) training** | **591** | **36.9 h** (16-way) / 147.8 h (4-way) | 2.33 GB ckpt |
| **(c) evaluation** — fixture floor | 2.1 | 0.10 h | 3.87 GB |
| (c) @ 1.0 s/coordinator call | 298.7 | 14.9 h | |
| (c) @ 10 s/call (§F2 ceiling) | 2 986.7 | 149.3 h = 6.2 d | |
| **(d) merge** | 0.018 | 63 s (single process) | |
| **Total, floor eval** | **593** | **29.7 h = 1.24 d** | |
| Total, eval @10 s/call | 3 578 | 178.9 h = 7.45 d | |

**The total exceeds one day of wall time in every scenario, including the most optimistic.** At the ≤4-concurrent posture actually in force, the floor is ≈6.4 days.

**The single most decision-relevant number:** if the real coordinator's mean solve time exceeds **≈1.6 s**, evaluation *alone* breaks one day at 20 cores. §F2's 10 s is a cancellation deadline, not a target — the mean matters far more than the bound, and nothing currently seals it.

## Three cheapest levers

1. **Hoist the constant neutral batches out of `train_epoch` — measured 1.91×, ~282 core-h, contract-neutral.** `informed.neutral(definition)` is called every epoch (`learner.py:1027`, `:1034`), rebuilding a deterministic zeroed-target batch and re-hashing it (`learner.py:652`). Measured: **44.8 % of every source epoch re-derives a constant.** No weight, digest or checkpoint field changes. Training 591 → **309 core-h**, wall @16 → **19.3 h**.
2. **Cap the sealed aggregate batch.** Training is exactly linear in batch rows (slope 5.195 × 10⁻⁵ s/pair/epoch across 320→5 120). A 4× stratified reduction → **148 core-h / 9.2 h**, with lever 1 → **77 core-h / 4.8 h**. Must be decided before the §C7 seal, and justified on estimator grounds — not a free win.
3. **Raise training concurrency 4 → 16.** Lineages are independent, numpy is single-threaded, RSS is 270 MiB each. **4× wall reduction** at zero compute cost. The ceiling is 16, not 96 — committing more buys nothing.

The runner's fork-per-step costs 0.68 core-h (33 % of the evaluation *floor*, negligible against any realistic budget). Don't optimise it; it buys the §F2 cancellation guarantee.

## Key assumptions

Source scale is **assumed, not sealed** (20 users/step × 10 actions/user → 1.92 M rows); both (a) and (b) scale linearly in this product — the largest uncertainty in (b). Batch composition follows the fixture. The evaluation fixture is small (3 users, 4 profiles, 1 ms synthetic latency), so per-unit evaluation is a **floor, not a forecast**. 2 000 epochs are exhausted with no early stopping. 20 cores assumes a quiet box. **(a) excludes the upstream tape/physics forward model** that computes margins, powers and forecasts — almost certainly larger than the 0.10 core-h measured for the row/shard layer.

## Bottom line

The timeline is **dominated by training, not evaluation or merge** — unless the coordinator's mean solve time lands above ~1.6 s, at which point evaluation overtakes it. Lever 1 (contract-neutral code fix) plus lever 3 (16-way training) takes the floor scenario from 6.4 days to **≈20 hours**, the cheapest route to a one-day timeline with no seal-time decision required.

Two items should be resolved before the launch package rather than discovered mid-run: the **16-vs-96 lineage count**, which caps useful training parallelism at 16, and the **coordinator mean solve time**, currently the difference between a 1.5-hour and a 6-day evaluation phase.
