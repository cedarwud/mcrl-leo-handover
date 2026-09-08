# Adversarial Red-Team Review: C3-S Closed-Loop Kill Screen v1

## 1. Artifact Hypotheses (Ranked by Threat to Findings)

### Rank 1: Learner Defect Correction Masquerading as "Coordination" (Strawman Baseline)
- **Mechanism:** BASE is the argmax of frozen, under-trained Q-heads. Oracle marginal diagnostics prove Q1 alone leaves +8.5% to +23.2% EE on the table. The coordinator intervened at all 360/360 decisions. If most chosen actions are unilateral edits rather than joint beam evacuations, C3-S is not performing multi-agent coordination; it is acting as a 1-step nominal greedy gradient step that cleans up obvious blunder moves from defective Q-heads.
- **Confirmation/Refutation:** Inspect action census in receipt logs (`runs/c3s-20260908-r1/`): count fraction of selected actions with candidate ID `(1, user, action)` (unilateral) vs `(2, ...)` (evacuation). If unilateral edits dominate choices and EE delta, "coordination" is refuted.
- **Cheap Test (≤ 2h):** Script an ablation run of S0-U vs S0-J on closed-loop trajectories using existing receipts.
- **Probability of Overturning "Coordination" Claim:** **75%** (overturning raw +2.9% number: 15%).

### Rank 2: Unrealistic PA Energy Accounting (Zero Idle / Activation Penalty)
- **Mechanism:** RF power is modeled as the maximum over served users ($P_{\text{RF}} = \max_u P_u \le 1.65\text{ W} \ll P_{\text{sat}} = 5.218\text{ W}$), and PA constitutes 94.8% of energy. If turning off a beam completely zeroes PA power without modeling PA standby bias, baseband overhead, or switching transients, the simulator creates an artificial mathematical cliff. Herding users into fewer beams yields enormous synthetic Joule savings that vanish on actual hardware where idling PAs consume quiescent power.
- **Confirmation/Refutation:** Check `src/mcrl/env/step.py` and energy accounting: verify whether PA power drops to true zero when unserved and whether beam reactivation incurs penalty Joules.
- **Cheap Test (≤ 2h):** Re-compute episode energy under a conservative 10% PA quiescent idle power baseline using recorded active beam counts per step.
- **Probability of Overturning Real-World Gain:** **60%**.

### Rank 3: Proxy Exploitation & Optimizer's Curse (The LITE > FULL Paradox)
- **Mechanism:** LITE (+2.922%) strictly outperforms FULL (+2.883%) despite searching a strict subset of FULL's unilateral actions. Step logs show LITE and FULL are byte-identical for steps 0–25 and diverge only in steps 26–29. Because nominal physics has proxy noise (unit Rician, 0 dB shadowing vs realized fading), searching a larger catalog (FULL) suffers from optimizer’s curse: selecting extreme positive proxy noise outliers that underperform in realized physics.
- **Confirmation/Refutation:** Compare steps 26–29 in unit receipts: identify decisions where FULL selected a candidate outside LITE's catalog, verify that FULL's nominal margin exceeded LITE's but realized EE was worse.
- **Cheap Test (≤ 2h):** Tally realized vs nominal prediction errors for all instances where FULL and LITE diverged in the 12 unit receipts.
- **Probability of Overturning Mechanism Soundness:** **50%**.

### Rank 4: Nominal Model Privilege (Simulator Incest)
- **Mechanism:** The coordinator shares the exact functional equations and deterministic parameters of the simulator (OPS-3 median: unit Rician, 0 dB shadowing). In real deployments, channel state information (CSI) is noisy and delayed. The S0 diagnostic showed choice agreement with Oracle U1 was only **1.67%** (2/120 matches). A controller that achieves +2.9% by exploiting exact simulator formulas without real fading uncertainty will degrade rapidly under real-world mismatch.
- **Confirmation/Refutation:** Check whether candidate selection switches drastically when small noise is introduced to nominal path-loss/channel equations.
- **Cheap Test (≤ 2h):** Perturb nominal channel gains by $\pm 1.5\text{ dB}$ log-normal noise in a one-step re-evaluation of step-0 snapshots; measure candidate choice stability.
- **Probability of Overturning Claim in Deployed Reality:** **45%**.

### Rank 5: $\eta_{\text{ref}}$ Price Distortion Across Operational Regimes
- **Mechanism:** Coordinator objective is $\arg\max [\hat{B} - \eta_{\text{ref}} \hat{E}]$. The frozen price $\eta_{\text{ref}} = 124.08\text{ Mbit/J}$ was inherited from historical E1, whereas realized BASE in this screen was only $117.42\text{ Mbit/J}$ (~5.6% lower). Over-pricing energy forces the coordinator to hyper-prioritize Joule reduction over throughput. In finite demand regimes (G1–G3), true system EE drops by up to 35× (to ~3.5 Mbit/J); a static $\eta_{\text{ref}} \approx 124\text{ Mbit/J}$ will lead to severe policy breakdown by aggressively shedding energy for bits that have zero marginal value.
- **Confirmation/Refutation:** Inspect oracle marginal results for G1–G3: observe how C3 marginal delta collapses to negative or zero as demand becomes finite.
- **Cheap Test (≤ 2h):** Sweep $\eta_{\text{ref}} \in [100, 130]\text{ Mbit/J}$ across the 120 S0 probe anchors; test whether EE gain flips negative when priced at true operating points.
- **Probability of Overturning Metric Generalizability:** **40%**.

### Rank 6: Short-Horizon Boundary Debt (Handover Suppression)
- **Mechanism:** Episodes are only $T=30$ steps (902.4 s, ~15 min), matching a single LEO satellite pass. If C3-S achieves EE gains by delaying handovers to avoid beam activation penalties, it may be accumulating "handover debt"—trapping users on setting satellites at steep elevation angles. At step 29, the terminal state is truncated before the deferred handovers or forced packet drops must be paid for.
- **Confirmation/Refutation:** Check handover frequencies and terminal user-satellite elevation angles in BASE vs C3-S.
- **Cheap Test (≤ 2h):** Plot cumulative $\Delta\text{EE}_t$ and handover rate over $t=0\dots 29$. Verify if gains concentrate in the final 5 steps.
- **Probability of Overturning Long-Horizon Efficacy:** **35%**.

### Rank 7: Severe Pseudoreplication (4 World Clusters)
- **Mechanism:** 36 episodes are constructed from only 4 physical world seeds crossed with 3 lineages. Lineages share identical satellite trajectories and user mobility tracks. In Oracle marginals, world variance was enormous (C3 delta varied 7-fold across worlds in G0). Testing only 4 physical realizations provides insufficient degrees of freedom to rule out seed selection bias.
- **Confirmation/Refutation:** Calculate intra-cluster correlation (ICC) of EE deltas across lineages within the same world seed.
- **Cheap Test (≤ 2h):** Run a cluster-robust permutation test on the 4 world clusters to compute exact non-parametric p-values for the +2.9% gain.
- **Probability of Overturning Statistical Significance:** **30%**.

### Rank 8: Toothless Service Guard by Topological Construction
- **Mechanism:** Served counts are identical down to the single user across all three arms (35,971 / 36,000 pooled; exactly 8982, 8998, 8991, 9000 per world). This is not an empirical achievement; it is a mathematical artifact of the hard constraint $\hat{C}_t(x) \ge \hat{C}_t(b_t)$ coupled with a service metric that is purely geometric/topological (pre-fading line-of-sight admission) rather than packet-delay or SINR-outage based.
- **Confirmation/Refutation:** Check `service.py` to confirm whether service status depends on small-scale fading or purely on geometric coverage.
- **Cheap Test (≤ 2h):** Verify in code whether `served` can ever differ between nominal and realized states for identical association vectors.
- **Probability of Overturning Claim that Service was "Defended":** **80%** (overturning EE gain: 5%).

---

## 2. Estimand Critique

The declared contrast `FULL2 + C3-S vs FULL2, pooled EE, service ≥ BASE - 0.001` is structurally flawed for claiming a "third Catfish":

1. **Category Error (RL Head vs Heuristic Search):** C3-S contains no learned parameters, no neural network, and no value function. Labeling an online 1-step model-predictive local search layer as a "third Catfish" alongside learned Q-heads (Q1, Q2) is scientifically misleading.
2. **Asymmetric Compute & Information Baseline:** BASE runs reactive forward inference in 1.9 s. C3-S spends 49–67 s per decision evaluating ~2,700 complete states against simulator physics equations. The contrast credits C3-S for "coordination" when the advantage could stem entirely from giving one arm 35× more compute and direct access to an analytical physics engine.
3. **Missing Hostile Baselines:** A hostile reviewer will demand:
   - `Heuristic (e.g. Max-RSRP) + C3-S vs FULL2 + C3-S`: Does learned BASE provide any value over an unlearned initialization, or does C3-S fix heuristics just as easily?
   - `BASE + 1-step Random Search (equal compute)`: Does C3-S beat simple compute-matched baselines?
   - `Pure Nominal MPC (no Q-heads)`: What is the marginal contribution of Q1/Q2 if nominal physics does the selection?
4. **Service Metric Insensitivity:** Pooled served count masks user fairness, tail latency, packet queuing, and inter-beam interference degradation.

---

## 3. Upstream Framing Check

The two-week failure of additive C3 heads (oracle marginals $\le 0$ everywhere) and the sudden success of set-level C3-S point to a fundamental conceptual error in the team's initial formulation:

1. **The Additive Decomposition Fallacy:**
   The team attempted to represent coordination as an additive per-user scalar Q-head: $\arg\max_a (Q_1 + Q_2 + Q_3)$. But multi-beam satellite physics is governed by non-linear step functions:
   - RF power is an extreme-value metric ($P_{\text{RF}} = \max_u P_u$).
   - PA power (94.8% of total) is all-or-nothing: turning off a beam requires an evacuation where *every* user vacates simultaneously.
   - Bandwidth is shared ($W / N$).
   An individual user leaving a beam provides zero energy savings unless *all other users* also leave. In game-theoretic terms, beam evacuation is a strict coordination game (stag hunt). Independent scalar addition cannot solve step-level collective action; credit assignment fails completely. Additive C3 was mathematically doomed.
2. **"Load Balancing" vs "Load Consolidation":**
   Terrestrial load balancing spreads users across cells to reduce congestion. In satellite EE where PA fixed power dominates, spreading users increases power by activating more beams. Maximum EE requires *load consolidation* (packing users into minimal beams and evacuating the rest). Framing C3 as "load balancing" pointed the architecture in the wrong direction.
3. **Paper Framing Correction:**
   Abandon the claim of a "three-Catfish RL model." Frame the architecture honestly as a **hybrid two-tier controller**: a fast, decentralized learned actor (C1/C2) generating candidate proposals, filtered by a centralized model-based topology coordinator (C3-S).

---

## 4. Top 3 Priority Actions

| Priority | Action | Cost | Decision Informed |
| :--- | :--- | :--- | :--- |
| **1** | **Action Census & Decomposition**<br>Parse receipt logs to quantify the proportion of chosen actions that are Unilateral Edits vs Beam Evacuations, and compute their isolated EE contributions. | **0.5 worker-hours** | **Mechanism Validation:** Determines if C3-S is actually coordinating (evacuations) or merely patching Q1 single-agent suboptimality (unilateral). |
| **2** | **Zero-Learner Baseline Test (`Heuristic + C3-S`)**<br>Run C3-S on top of a standard unlearned heuristic (e.g., Max-RSRP / nearest beam) across the same 4 worlds. | **1.5 worker-hours** | **Architectural Necessity:** Tests whether learned Q-heads are necessary, or if the entire +2.9% gain is an artifact of 1-step nominal search. |
| **3** | **PA Idle Power Sensitivity Audit**<br>Re-evaluate pooled EE from step records assuming 5%, 10%, and 20% PA standby quiescent power when beams are inactive. | **1.0 worker-hours** | **Physical Viability:** Establishes whether the EE gain survives realistic satellite hardware RF constraints before drafting confirmatory protocols. |
