The independent blind review of **Multi-Catfish MCRL** has been completed and written to both [`/home/u24/BLIND-REVIEW.md`](file:///home/u24/BLIND-REVIEW.md) and [`/home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-blind/BLIND-REVIEW.md`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-blind/BLIND-REVIEW.md).

***

### Summary of Independent Review Findings

1. **The First-Line Verdict**:
   > **The evidence does not support an empirical claim that Multi-Catfish MCRL or its three routes (C1, C2, C3) improve satellite system energy efficiency over baselines; instead, the evidence establishes an offline counterfactual accounting framework whose learned components fail to demonstrate positive route marginals or out-of-sample gains under the evaluated single-step open-loop benchmark.**

2. **The Strongest Defensible Scientific Claim**:
   A skeptical peer reviewer could only accept an **architectural decomposition and diagnostic contribution**:
   * Multi-Catfish MCRL formalizes a mathematically exact offline counterfactual decomposition of satellite beam allocation into three distinct perspectives: focal immediate surplus ($C_1$), focal continuation surplus ($C_2$), and non-focal opening externalities ($C_3$).
   * However, empirical validation under V0.25 radio and power physics demonstrates that these learned routes fail to exhibit positive additive route marginals, fail to outperform simple static heuristics (`RSS_MAX` achieves 41.62 Mbit/J vs. learned models hovering at 32.96–42.26 Mbit/J in-sample), and uncover structural misalignments between linear surrogate optimization objectives ($F = B - \eta_{\text{ref}} E$) and pooled system energy efficiency ($\frac{\sum B}{\sum E}$).

3. **Supported Claim Structure & Evidence Deciding It**:
   * **Target Metric Misalignment**: The surrogate selector objective $F = B - \eta_{\text{ref}} E$ ($\eta_{\text{ref}} = 10.943$ Mbit/J) cannot track the pooled ratio of sums, actively rejecting candidate allocations that improve pooled EE by $+7.85$ Mbit/J (`ETA-EXCHANGE-RATE-2026-09-10.md`, `COORDINATION-VALUE-2026-09-10.md`).
   * **Route $C_1$ (Focal Immediate)**: Omitting nominal gain in Q1 v1/v2 prevented expressing `RSS_MAX` (92.5/100 users distance; `APPROACHING-THE-INSTRUMENTS-2026-09-10.md`). Exact label training yields negative level $R^2$ (-0.0345; `EXACT93-TRAINING-2026-09-10.md`). Supplying gain in Q1 v4 causes rank agreement 1.0000 across all users, inducing extreme cross-user collinearity (`Q1-SCHEMA-V4-2026-09-10.md`).
   * **Route $C_2$ (Continuation)**: Open-loop single-step evaluation (`StepEvaluator`) cannot observe or evaluate multi-step continuation ($t+1 \dots t+3$). Perfect oracle $C_2$ added to exact $C_1$ yields $+0.68\%$ (indistinguishable from zero) and degrades decisions on 20 of 30 changed anchors (`C2-TARGET-VALUE-2026-09-10.md`). Under sealed tie-break semantics, its selection marginal is strictly $0.000\%$.
   * **Route $C_3$ (Externality/Coordination)**: Clean coordination headroom is tiny ($+0.844\%$) and saturated at singleton moves; expanding coalition support adds $+0.000\%$ (`CEILING-CLEAN-AND-LEVERS-2026-09-10.md`). The candidate catalog contains 0 improving multi-user configurations across 5,814 candidates (`COORDINATION-VALUE-2026-09-10.md`). In trained models across all seeds, dropping $C_3$ strictly improves system EE (`Z-VIEW-SCORING-2026-09-10.md`).
   * **Missing Baseline MODQN**: No runnable, authenticated MODQN exists on V0.25 physics (`BASELINE-MODQN-REFERENCE-2026-09-10.md`). Prior comparisons used a fixed geometric carrier proposal (`carrier_base`), invalidating baseline superiority claims.
   * **Total Data Leakage**: All 20 panel anchors across completed runs are training anchors (`CONVERGED-EXACT-SCORING-2026-09-11.md`). Zero out-of-sample evidence exists.

4. **Missing Evidence & The Decisive Measurement**:
   * **Single Most Decisive Measurement**: A multi-step closed-loop rollout evaluation comparing the full learned model (`FULL`), route ablations (`DROP_C1`, `DROP_C2`, `DROP_C3`), clean non-learning heuristics (`RSS_MAX`, local search), and an authentic MODQN baseline on a strictly held-out panel of unseen TLE orbital dates, measuring pooled system EE ($\frac{\sum \text{bits}}{\sum \text{joules}}$) across extended sequential horizons ($T \ge 10$).

5. **Prohibited Claims**:
   The project must not claim: (1) improvement in system EE over baselines, (2) that routes $C_1, C_2, C_3$ each raise EE, (3) that $C_2$ captures continuation value, (4) that $C_3$ solves multi-user coordination barriers, (5) out-of-sample generalization or convergence, (6) superiority over MODQN on V0.25 physics, or (7) that load balancing ($r_3 = -U$) promotes system EE.
