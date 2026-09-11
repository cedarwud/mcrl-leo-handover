**The evidence does not support an empirical claim that Multi-Catfish MCRL or its three routes (C1, C2, C3) improve satellite system energy efficiency over baselines; instead, the evidence establishes an offline counterfactual accounting framework whose learned components fail to demonstrate positive route marginals or out-of-sample gains under the evaluated single-step open-loop benchmark.**

# Independent Scientific Review: Evidence-Based Claim Structure of Multi-Catfish MCRL

- **Evaluator Role**: Independent Reviewer (Zero prior involvement in project development or internal steering).
- **Scope & Protocol**: Grounded strictly in the evidentiary artifacts contained in `./evidence/` (declarations, code implementations, verification receipts, and diagnostic reports). Interpretative controller notes and unverified narratives are excluded from authority.
- **Evaluation Date**: 2026-09-11

---

## 1. The Strongest Defensible Scientific Claim

The strongest defensible scientific claim this project could make about a three-route method, stated as a careful, skeptical peer reviewer would accept, is:

> *"We propose Multi-Catfish MCRL, an offline accounting decomposition that splits single-agent beam assignment counterfactuals into three distinct views: focal immediate surplus ($C_1$), focal next-slot attributable surplus ($C_2$), and non-focal opening externalities ($C_3$). Under high-fidelity LEO satellite radio and power physics (V0.25), this decomposition satisfies an exact accounting identity; however, on single-step open-loop evaluation panels, learned models implementing these routes fail to demonstrate positive additive route marginals, fail to outperform a simple static maximum-gain heuristic, and reveal fundamental misalignments between surrogate linear optimization objectives and pooled system energy efficiency."*

### Rationale for this Ceiling

A reviewer cannot accept any claim of algorithmic superiority or empirical performance gains because:
1. **The Owner's Primary Requirement Fails**: The owner's explicit requirement was that routes $C_1, C_2,$ and $C_3$ must each raise system energy efficiency (EE). In empirical evaluations across all tested architectures and learner seeds, this condition is violated. $C_3$ ablation marginals are consistently negative (dropping $C_3$ improves EE), $C_2$ marginals are either statistically indistinguishable from zero or negative, and $C_1$ is unstable and confounded by input representation defects.
2. **Simple Heuristics Dominate Learned Policies**: The static, non-learning `RSS_MAX` baseline achieves **41.62 Mbit/J** by assigning users to maximum-gain beams and leaving idle beams off. Fully learned models (`FULL`) hover between **32.96 and 42.26 Mbit/J** strictly in-sample.
3. **Absence of Runnable Baselines**: The project has never evaluated a runnable, authenticated multi-objective DQN (MODQN) baseline on V0.25 physics. The published comparisons utilized an un-tuned geometric carrier strawman (`carrier_base`).
4. **Data Leakage**: 100% of reported learned model evaluations were conducted on training anchors; there is zero verified out-of-sample evidence.

Therefore, the project's defensible contribution is entirely representational, diagnostic, and methodological: it formalizes the multi-user satellite beam handover counterfactual decomposition and provides a rigorous autopsy of why standard reinforcement learning abstractions break down under coupled satellite payload power constraints.

---

## 2. The Claim Structure Supported by the Evidence

The evidence supports a **negative result and architectural failure analysis**. The table below summarizes the claim components, the decisive evidence, and the evidential status.

| Claim Dimension | Claim Supported by Evidence | Decisive Evidence Artifacts | Evidence Status |
|---|---|---|---|
| **Target Metric Alignment** | Maximizing linear surrogate $F = B - \eta_{\text{ref}} E$ conflicts with pooled system EE ($\frac{\sum B}{\sum E}$), rejecting large EE improvements. | `ETA-EXCHANGE-RATE-2026-09-10.md`<br>`COORDINATION-VALUE-2026-09-10.md` | **Established** (Learner-free proof and empirical checks) |
| **Route $C_1$ (Focal Immediate)** | Fails to learn focal surplus; omitting nominal gain prevents expressing `RSS_MAX`; adding gain causes complete cross-user rank collinearity. | `APPROACHING-THE-INSTRUMENTS-2026-09-10.md`<br>`EXACT93-TRAINING-2026-09-10.md`<br>`Q1-SCHEMA-V4-2026-09-10.md` | **Established** (Learner-free & trained models; in-sample) |
| **Route $C_2$ (Continuation)** | Provides zero or negative selection value; evaluation harness is single-step open loop and cannot measure multi-step horizon value. | `C2-TARGET-VALUE-2026-09-10.md`<br>`Z-VIEW-SCORING-2026-09-10.md`<br>`V025-AMENDMENT-v1.6/v1.9` | **Established** (Learner-free oracle & trained models; in-sample) |
| **Route $C_3$ (Externality / Coordination)** | Coordination headroom is negligible (+0.84%); candidate catalog has zero improving multi-user moves; learned $C_3$ strictly degrades EE. | `CEILING-CLEAN-AND-LEVERS-2026-09-10.md`<br>`COORDINATION-VALUE-2026-09-10.md`<br>`BASIN-BARRIER-2026-09-10.md`<br>`Z-VIEW-SCORING-2026-09-10.md` | **Established** (Learner-free & trained models; in-sample) |
| **Physical Regime (Crowding vs Load Balancing)** | Beam activation carries heavy DC penalties; crowding users into few beams maximizes EE; load balancing directly degrades EE. | `CROWDING-COST-2026-09-10.md`<br>`BEAM-CAPACITY-REALISM-2026-09-10.md`<br>`BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md` | **Established** (Physics verification) |
| **Baseline Comparison** | No runnable V0.25 MODQN exists; pilot substituted a fixed geometric carrier, invalidating baseline superiority claims. | `BASELINE-MODQN-REFERENCE-2026-09-10.md`<br>`MODQN-COLLAPSE-2026-09-10.md` | **Established** (Codebase audit) |
| **Generalization & Evaluation Integrity** | 100% data leakage across all reported checkpoints (20/20 panel anchors are training anchors); prior F8 gains were evaluator cache artifacts. | `CONVERGED-EXACT-SCORING-2026-09-11.md`<br>`STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md`<br>`Z-VIEW-SCORING-2026-09-10.md` | **Established** (Receipt & code audit) |

---

### Detailed Evidentiary Analysis

#### A. Target Metric vs. Linear Surrogate ($F = B - \eta_{\text{ref}} E$)
- **What Evidence Establishes**:
  - The project's declared optimization metric is system pooled energy efficiency: $\eta^N = \frac{\sum_u B_u}{\sum_s E_s}$ (ratio of sums, in Mbit/J; `code/energy_efficiency.py`, paper Eq. 3.25).
  - To select actions, the candidate selector maximizes a scalar surrogate: $F = B - \eta_{\text{ref}} E$, with a fixed exchange rate $\eta_{\text{ref}} = 10.943$ Mbit/J (`ETA-EXCHANGE-RATE-2026-09-10.md`).
  - Mathematical analysis and empirical measurements in `ETA-EXCHANGE-RATE-2026-09-10.md` establish that no single constant $\eta \ge 0$ can reconcile the linear surrogate with pooled EE across diverse operational states. At operating points with high efficiency (e.g., `RSS_MAX` at 41.62 Mbit/J), the effective marginal exchange rate required to reject wasteful power expenditure is much higher than 10.943 Mbit/J.
  - In `COORDINATION-VALUE-2026-09-10.md`, the linear objective $F$ actively rejected candidate moves that yielded $+7.85$ Mbit/J in pooled EE, because $F$ rewarded marginal bit increases regardless of the disproportionate energy cost.
- **Inference**: The search and selector mechanisms are guided by an objective misaligned with the primary evaluation metric.

#### B. Route $C_1$ (Focal Immediate Surplus)
- **What Evidence Establishes**:
  - In Q1 v1 and Q1 v2, per-option `nominal_gain` was excluded from input features (`APPROACHING-THE-INSTRUMENTS-2026-09-10.md`). Consequently, the learned $Q_1$ network was mathematically incapable of expressing the simplest direct policy (`RSS_MAX`), showing a median user-allocation distance of 92.5/100 users.
  - Furthermore, upstream pipeline errors in v2 caused two critical power coordinates (`nominal_required_power_over_cap` and `previous_beam_max_rf_over_cap`) to be hardcoded constants (1.0) on all 81,638 legal rows (`Q1-SCHEMA-V4-2026-09-10.md`).
  - Training on exact labels (`EXACT93-TRAINING-2026-09-10.md`) produced a negative level $R^2$ (-0.0345) and a top-1 action match of only 6.6% (ordering 0.532).
  - When per-option gain is supplied in Q1 v4 (`Q1-SCHEMA-V4-2026-09-10.md`), candidate generation orders slots by descending gain for every user identically (rank correlation 1.0000 across all users, Pearson $\rho = 0.9958$). This creates extreme cross-user input collinearity, inducing severe policy generalization risks.
  - In `Z-VIEW-SCORING-2026-09-10.md`, while Q1 v2 showed a high in-sample marginal (`FULL - DROP_C1 = +12.69 Mbit/J`), adding live-user population z-features caused this marginal to collapse to `+1.35 Mbit/J` with sign flips across seeds (14/16 positive, failing the project's pre-declared result threshold).
- **Inference**: $C_1$ has not learned an accurate surrogate of focal opening surplus; its apparent performance is driven by representation artifacts rather than genuine functional approximation.

#### C. Route $C_2$ (Focal Continuation / Attributable Surplus)
- **What Evidence Establishes**:
  - **Structural Protocol Mismatch**: $C_2$ is defined as the attributable surplus across future steps $t+1, t+2, t+3$. However, the project's evaluation harness (`StepEvaluator`) executes open-loop single-step evaluations at step $t$ across 48 intra-step boundaries (`C2-TARGET-VALUE-2026-09-10.md`). An open-loop, single-step evaluation cannot reward an agent for actions taken to optimize multi-step horizons.
  - **Oracle Failure**: In `C2-TARGET-VALUE-2026-09-10.md`, when an exact, perfect oracle for $C_2$ was added to exact $C_1$, the resulting pooled EE change was $+0.68\%$ (95% bootstrap CI $[-3.60\%, +5.73\%]$, indistinguishable from zero). On a 22-anchor subset, oracle $C_2$ degraded EE by $-2.10\%$, degrading choices at 20 of 30 changed anchors.
  - **Architectural Nullification**: Under the sealed tie-break reading (Amendments v1.6 and v1.9), $C_2$ enters the selector strictly as a tie-breaker when $C_1 + C_3$ are equal. Because continuous network scores rarely produce exact ties, $C_2$'s theoretical selection marginal is strictly $0.000\%$ by design.
  - **Empirical Degradation**: In trained epoch-500 models (`Z-VIEW-SCORING-2026-09-10.md`), `FULL - DROP_C2` is negative in Q1 v2 ($-1.15$ Mbit/J, 15/16 seeds negative); in the z-view, it flips signs across seeds (13/16 positive, not a certified result).
- **Inference**: Route $C_2$ has no empirical utility in this system, and the evaluation framework is structurally incapable of assessing its intended temporal hypothesis.

#### D. Route $C_3$ (Non-Focal Opening Externality / Coordination)
- **What Evidence Establishes**:
  - **Vanishing Headroom**: `CEILING-CLEAN-AND-LEVERS-2026-09-10.md` demonstrates that at 1.66° beam separation, the clean coordination ceiling above unilateral search is only $+0.844\%$. Expanding coalition sizes from $|A| \le 1$ to $|A| \le 6$ adds exactly $+0.000\%$ headroom.
  - **Empty Improving Neighborhood**: In `COORDINATION-VALUE-2026-09-10.md`, across 5,814 evaluated multi-user configurations, exactly **0** yielded an EE improvement over unilateral search ($k=1$).
  - **No Multi-User Barrier**: Unilateral moves ($k=1$) improve EE from `RSS_MAX` at 12 out of 12 anchors (`BASIN-BARRIER-2026-09-10.md`), refuting the hypothesis of a local coordination barrier that necessitates multi-agent joint learning.
  - **Consistently Harmful in Trained Models**: In `Z-VIEW-SCORING-2026-09-10.md`, across all tested schemas and seeds, dropping $C_3$ improved performance:
    - Q1 v1: `FULL - DROP_C3 = -10.04 Mbit/J` ($-23.35\%$, 16/16 seeds negative).
    - Q1 v2: `FULL - DROP_C3 = -1.20 Mbit/J` ($-2.76\%$, 14/16 seeds negative).
    - z-view: `FULL - DROP_C3 = -2.25 Mbit/J` ($-5.26\%$, 15/16 seeds negative).
- **Inference**: $C_3$ acts as destructive noise during inference, corrupting viable unilateral candidate allocations.

#### E. Physical Realism: Crowding vs. Load Balancing
- **What Evidence Establishes**:
  - Under V0.25 radio and power physics (`CROWDING-COST-2026-09-10.md`), each active satellite incurs 40 W idle and 80 W RF overhead, plus per-beam power. The empirical derivative of pooled EE with respect to active beams is strongly negative: $\frac{d(\text{EE})}{d(\text{active})} = -425,009$ bit/J per beam.
  - Concentrating 100 users into 8 active beams yields **46.11 Mbit/J**; spreading them across 98.25 beams drops EE to **7.75 Mbit/J** (`CROWDING-COST-2026-09-10.md`, `BEAM-CAPACITY-REALISM-2026-09-10.md`).
  - The learned base policy $a_0$ selects 49.07 active beams across 5.79 satellites, nearly indistinguishable from zero-learning myopic control (51.68 beams / 5.18 satellites; `BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md`).
- **Inference & Literature Appeal**: The legacy MODQN reward formulation incorporates $r_3 = -U$ (beam occupancy penalty, intended to balance load). This goal is directly counterproductive in satellite systems where beam activation carries massive fixed energy penalties. Spreading traffic across beams maximizes joules faster than it increases bits.

#### F. The Missing Baseline MODQN Reference
- **What Evidence Establishes**:
  - `BASELINE-MODQN-REFERENCE-2026-09-10.md` establishes that **no runnable, authenticated MODQN baseline exists on V0.25 physics**.
  - The pilot comparisons substituted a static geometric carrier proposal (`carrier_base`), achieving 3.89–11.03 Mbit/J, rather than a trained MODQN agent.
  - On native V0.23 legacy physics (`MODQN-COLLAPSE-2026-09-10.md`), authenticated MODQN maintains a well-distributed, non-collapsed physical profile (68.7 active beams, 7.47 satellites, modal fraction 0.0417). Its true performance on V0.25 physics has never been measured.
- **Inference**: Any claim that Multi-Catfish MCRL outperforms MODQN is an unverified assertion.

#### G. Verification Integrity: 100% In-Sample Evaluation & Cache Contamination
- **What Evidence Establishes**:
  - **Total Data Leakage**: `CONVERGED-EXACT-SCORING-2026-09-11.md` reveals that all 20 panel anchors across all completed runs (`V025_PROBE/world/1`, steps 0–6) are training anchors. All reported performance metrics for trained models are strictly in-sample.
  - **Cache Contamination in Published Baselines**: `STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md` and `Z-VIEW-SCORING-2026-09-10.md` show that earlier evaluations used a corrupted evaluator cache that deflated search baselines (`FIRST_IMPROVEMENT_FP`) from 31.03 Mbit/J to 13.43 Mbit/J. This artifact created illusory $2.5\times$–$3.3\times$ gains for learned models in early F8 reporting tables, all of which collapsed upon clean re-evaluation.
  - The clean static heuristic `RSS_MAX` achieves **41.62 Mbit/J**, outperforming or matching every learned model evaluated.

---

## 3. Missing Evidence and the Decisive Measurement

### Critical Evidence Gaps
1. **Authenticated MODQN Baseline on Target Physics**: A verified implementation of MODQN trained and evaluated on V0.25 physics under identical rate-target and power-control constraints.
2. **True Out-of-Sample Evaluation**: Evaluation of learned models on held-out TLE orbital dates and unobserved satellite constellations.
3. **Closed-Loop Multi-Step Evaluation Harness**: An evaluation framework that executes sequential transitions over extended horizons ($T \ge 10$ steps) to provide an environment where continuation value ($C_2$) can be meaningfully exercised.
4. **Viable Coordination Candidate Generation**: A candidate generator capable of identifying improving joint multi-user moves, overcoming the current catalog's 0/5,814 defect.

### The Single Decisive Measurement

The single measurement that would most decisively resolve whether Multi-Catfish MCRL has scientific validity is:

> **A multi-step, closed-loop rollout evaluation comparing the full learned model (`FULL`), route-ablated models (`DROP_C1`, `DROP_C2`, `DROP_C3`), clean static heuristics (`RSS_MAX`, first-improvement search), and an authenticated MODQN baseline on a strictly held-out panel of unseen TLE dates, measuring pooled system energy efficiency ($\frac{\sum \text{bits}}{\sum \text{joules}}$) across extended trajectories ($T \ge 10$).**

#### Why this Measurement is Decisive
- **Tests the Core Temporal Hypothesis**: It provides the first legitimate test of $C_2$. If $C_2$ does not demonstrate a positive marginal when multi-step handovers and link continuity are evaluated in closed loop, the continuation hypothesis is empirically refuted.
- **Resolves Generalization**: Testing on unseen TLE dates breaks the 100% in-sample data leakage, proving whether learned representations capture genuine orbital geometry.
- **Adjudicates Route Marginality**: It directly verifies whether the owner's requirement (all three routes simultaneously raise EE) can hold under any valid evaluation regime.
- **Grounds Claims Against Real Baselines**: It replaces the geometric strawman with authentic MODQN and static `RSS_MAX`, establishing whether reinforcement learning provides any net benefit over classical rules.

---

## 4. What the Project Must Not Claim

Based strictly on the evidence in `./evidence/`, the project is prohibited from making the following claims:

1. **Must NOT claim that Multi-Catfish MCRL improves system energy efficiency over baselines.**  
   *Reason*: Clean static heuristics (`RSS_MAX` at 41.62 Mbit/J) outperform or match all learned models, and comparisons against MODQN on V0.25 physics were never conducted.

2. **Must NOT claim that routes $C_1, C_2,$ and $C_3$ each raise energy efficiency.**  
   *Reason*: Empirical data directly refutes this. $C_3$ ablation marginals are negative across all seeds and architectures; $C_2$ oracle and empirical marginals are indistinguishable from zero or negative; $C_1$ is unstable and confounded by schema changes.

3. **Must NOT claim that Route $C_2$ captures or delivers continuation/horizon value.**  
   *Reason*: The evaluation harness operates strictly single-step open loop. Furthermore, oracle $C_2$ degrades decisions on 20 of 30 changed anchors, and sealed tie-break semantics nullify its selection impact.

4. **Must NOT claim that Route $C_3$ solves a multi-user coordination problem.**  
   *Reason*: The clean coordination ceiling is negligible (+0.84%), no multi-user basin barrier exists (unilateral moves improve EE at 12/12 anchors), and the candidate catalog contains zero improving multi-user configurations.

5. **Must NOT claim out-of-sample generalization or convergence.**  
   *Reason*: 100% of reported learned model results are derived from training anchors (total data leakage), and pre-declared convergence audits confirm that models at 500 epochs were unconverged.

6. **Must NOT claim superiority over MODQN on V0.25 physics.**  
   *Reason*: No runnable V0.25 MODQN exists in the codebase. All published comparisons against "baseline" used a static geometric carrier proposal (`carrier_base`).

7. **Must NOT claim that load balancing ($r_3 = -U$) or legacy multi-objective rewards promote system energy efficiency.**  
   *Reason*: Physical analysis establishes that beam activation costs dominate power consumption. Spreading load across redundant beams drastically reduces system EE.
