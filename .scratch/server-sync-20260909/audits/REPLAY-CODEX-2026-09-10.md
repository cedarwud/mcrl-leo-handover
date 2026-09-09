# Exact-pair selection replay — 2026-09-10

**25.6% (46/180) of anchors have pair-truncation selection regret above the project's +0.5% relative margin.** This is `DIAGNOSTIC_NOT_CLAIM`. On these labelled pools, omitted `R>=3` is a decision-level problem, not only a value-fitting problem.

The pair-calibrated winner differs from the exact winner at 50/180 anchors (27.8%); 46 of those 50 reversals (92.0%) exceed the margin. The pair values were retained, so this replay performed arithmetic on existing exact receipts and did not run a model or physics evaluation.

## 1. Per-anchor selection regret

For every anchor I added the legal no-move baseline to its labelled feasible coalition pool, then selected

\[
A^*=\arg\max_A F(A),\qquad
A_2=\arg\max_A Q_2(A),
\]

with the production rule of descending score followed by lowest stable configuration ID. The reported raw regret is \(F(A^*)-F(A_2)\), in the corpus's normalized objective units.

| Population | n | mean | p50 | p75 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| All anchors | 180 | 0.632375 | 0 | 0.210129 | 3.859773 | 7.246490 | 7.310753 |
| Changed-selection anchors only | 50 | 2.276548 | 1.802406 | 3.255896 | 7.219980 | 7.279264 | 7.310753 |

For comparison with +0.5%, relative regret is defined here as

\[
\rho(A_2)=\frac{F(A^*)-F(A_2)}{|F(A^*)|}.
\]

This explicit absolute-value denominator is necessary because the sealed objective \(F=B-\eta E+\kappa\Phi\) is signed: 41/180 exact winners and 42/180 pair winners have non-positive objective values. The project's +0.5% claim margin is originally a positive pooled-EE ratio, so this is a diagnostic translation of that scale, not a claim-estimator substitution. The headline count is insensitive to using \(|F(A_2)|\) instead: it remains 46/180.

| Population | n | mean | min | p05 | p25 | p50 | p75 | p95 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All anchors | 180 | 4.298% | 0% | 0% | 0% | 0% | 0.588% | 13.605% | 147.885% |
| Changed-selection anchors only | 50 | 15.473% | 0.0037% | 0.340% | 2.208% | 5.174% | 12.485% | 89.758% | 147.885% |

The large upper-tail percentages occur where the signed exact optimum is near zero; the normalized-unit table supplies the denominator-free magnitude.

## 2. Winner and exact-top-three agreement

- \(A_2=A^*\) at **130/180 anchors (72.2%)**.
- \(A_2\) is in the production-ordered exact top three at **163/180 anchors (90.6%)**.
- Conditional on the 50 changed selections, \(A_2\) is in the exact top three at **33/50 (66.0%)**; it is outside the top three at 17/50.

### Consequential ties

There are no top-score ties under exact \(F\), no top-score ties under \(Q_2\), and no exact-top-three cutoff ties. There are also no \(Q_2\) cutoff ties at K = 3, 5, or 10. Thus no reported winner, top-three membership, or shortlist result depends on tie-breaking in this replay.

## 3. Exact re-ranking of the top K under Q2

The table below is deliberately restricted to the 50 anchors where \(A_2\ne A^*\). “Recovered” means that exact re-ranking of the \(Q_2\) shortlist attains the exact best value; the gap is the remaining \(F(A^*)-F(A_{2,K})\).

| K | exact optimum recovered | gap > 0.5% | normalized gap mean | p50 | p95 | max | relative gap p50 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 8/50 (16%) | 38/50 (76%) | 1.531829 | 0.862529 | 5.077456 | 6.268515 | 4.033% | 35.017% |
| 5 | 12/50 (24%) | 34/50 (68%) | 1.264468 | 0.750445 | 4.684784 | 5.378469 | 2.381% | 26.197% |
| 10 | 18/50 (36%) | 29/50 (58%) | 1.098047 | 0.300969 | 4.684784 | 5.378469 | 1.300% | 25.330% |

Exact shortlisting helps monotonically, but a small shortlist does **not** recover nearly everything on the decisions that actually reverse. Even K = 10 exactly recovers only 36% of reversals and leaves 58% above the relative margin. A pairwise score remains useful as a proposal score, but these pools do not support relying on its top ten as a near-lossless exact shortlist.

## 4. Rigorous truncation-regret bound

Write \(F(A)=Q_2(A)+R_{\ge3}(A)\). Since \(A_2\) maximizes \(Q_2\),

\[
\begin{aligned}
F(A^*)-F(A_2)
&=Q_2(A^*)-Q_2(A_2)+R_{\ge3}(A^*)-R_{\ge3}(A_2)\\
&\le R_{\ge3}(A^*)-R_{\ge3}(A_2)\\
&\le \max_A R_{\ge3}(A)-\min_A R_{\ge3}(A).
\end{aligned}
\]

For each of the 50 changed-selection anchors, the extrema in the last line are over that anchor's full labelled pool, including the baseline and size-two coalitions with \(R_{\ge3}=0\). This full-pool range is mathematically required for the bound; the distribution below is restricted to anchors whose selection changed.

| n | mean | min | p05 | p25 | p50 | p75 | p95 | max |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 9.100798 | 3.223373 | 4.993282 | 6.761666 | 8.639069 | 10.992184 | 13.453309 | 31.017343 |

The largest within-anchor range is **31.017343 normalized units**, carried by **`V025_PROBE/world/1`, anchor 80**: minimum \(R_{\ge3}=-30.715730\), maximum \(R_{\ge3}=0.301612\), pool size 124 including baseline. Its realized selection regret is 4.731339 normalized units (4.514% relative), and \(A_2\) ranks ninth under exact \(F\).

The bound was checked on every changed-selection anchor. The smallest numerical slack, range minus realized regret, is 1.133569 normalized units; no violation occurred. This uses within-anchor ranges, not the irrelevant pooled magnitude of residuals.

## Scope, naming, and integrity

- These results concern the **labelled candidate pools**, not the best coalition in the whole action space.
- This is an oracle for **exact pair calibration**. It is not an upper bound on every possible refitted pairwise ranker: a scorer that deliberately sacrifices pair-value accuracy could rank better.
- The omitted quantity is called **`R>=3`**. For a coalition larger than three it contains every order from three through the coalition size. The six size-six observations do not, by themselves, demonstrate a sixth-order effect.
- Loss, shortlist-gap, and bound distributions are restricted to the 50 anchors whose selected configuration changed. The all-anchor denominator is retained only where required for the headline margin fraction and the winner/top-three agreement rates.
- All 11,924 family-index records joined one-to-one to all 11,924 labelled coalition rows by authenticated row SHA-256. Direct singleton-plus-retained-pair \(Q_2\) satisfied \(Q_2+R_{\ge3}=F\) to maximum absolute floating representation error \(4.36\times10^{-15}\).
- The no-move baseline was legal at every anchor because it is the corpus's realized anchor configuration. Pair terms were present for every size-three-or-larger labelled coalition. Nothing was recomputed.

## Reproduction and repository note

Run:

```bash
nice -n 15 env PYTHONPATH=src \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/replay_pair_selection.py --compact
```

The report is saved at [PAIR-REPLAY-2026-09-10.md](/home/sat/mcrl-v025-replay-ws/PAIR-REPLAY-2026-09-10.md), with the replay implementation at [replay_pair_selection.py](/home/sat/mcrl-v025-replay-ws/scripts/replay_pair_selection.py). Fresh-repository commit: `436e99a`.

The workspace's inherited `.git` is mounted read-only by the execution environment. Both the requested `rm -rf .git` and a move were therefore blocked. A fresh writable repository is maintained in `.git-replay` with `--work-tree=.`; this changes no other workspace. The failed safe move left a recoverable copy of the inherited Git data at `/tmp/mcrl-v025-replay-ws-source-git-20260909`.
