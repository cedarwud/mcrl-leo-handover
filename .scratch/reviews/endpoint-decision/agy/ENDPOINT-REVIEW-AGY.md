**PROCEED WITH CHANGES** (Mandatory changes: (1) Pre-register 3GPP-derived constraint bounds and report unconstrained pooled EE as a mandatory negative baseline; (2) Rebuild CF-GUARD around an explicit physical hysteresis/signaling penalty, not the inert 142 ms interruption; (3) Replace scalar Bellman DQfD with a decoupled two-critic (Q_B, Q_E) ratio architecture to resolve mathematical incompatibility with fractional objectives).

# Cross-Model Independent Review: Endpoint Respecification and Demonstration-Guided Architecture

**Reviewer:** Independent Cross-Model Reviewer (AGY / Antigravity)  
**Date:** 2026-09-11  
**Scope:** Evaluation of primary endpoint modification, DQfD backbone, specialist complementarity, ratio-objective reinforcement learning, and scientific defensibility in `mcrl-leo-handover`.  
**Target File:** `/home/u24/papers/mcrl-leo-handover/.scratch/reviews/endpoint-decision/agy/ENDPOINT-REVIEW-AGY.md`

---

## Executive Summary & Core Diagnostic

The project stands at a critical juncture. The unconstrained pooled Energy Efficiency (EE) metric has completely inverted the scientific claim: a trivial one-line physical rule (`MAX_NOMINAL_GAIN`) outperforms the trained MODQN policy by **+19.8%** (111.55 vs 93.14 Mbit/J, 13.2 sem), expanding to **+22.2%** under segment re-anchoring ablation. The trained policy is beaten on *both* bits (1.146×) and joules (0.957×). Meanwhile, the predecessor C1/C2/C3 decomposition has collapsed under mathematical identity ($C_1 + C_3 = \Delta F$ identically), non-discrimination against random baselines, and negative oracle marginals.

The controller now proposes two major shifts:
1. **Respecifying the endpoint** from unconstrained pooled EE to a Constrained Multi-Objective RL (CMORL) formulation (pooled EE subject to handover-rate and QoS/service constraints).
2. **Replacing the Catfish heuristics with a DQfD backbone** utilizing a Q-filtered margin loss and two specialists (`CF-EE` and `CF-GUARD`).

**Verdict: PROCEED WITH CHANGES.**  
The endpoint change is scientifically necessary because unconstrained EE in this simulator induces a pathological, non-deployable operating regime (71.2% handover rate per 30 s step). However, **without three mandatory structural changes**, the proposed DQfD redesign will simply reproduce the failures of the previous ten iterations.

---

## 1. Ruling on the Endpoint Change: Legitimate or Outcome-Selected?

### 1.1 The Plain Ruling: Post-Hoc Recovery vs Physical Misspecification
In formal clinical and empirical methodology, altering a declared primary endpoint after observing that the primary hypothesis failed is **outcome selection by definition** (HARKing / p-hacking). If this paper attempts to claim that the *original* research question was answered affirmatively by switching to a constrained metric, peer review will reject it immediately.

However, continuing to optimize **unconstrained pooled EE** in this specific environment is scientifically bankrupt for a different reason: **the metric is physically misspecified**.
- In the simulator, handovers incur **zero energy cost** (`grep -ci handover` is 0 across `link_budget.py`, `energy_efficiency.py`, `interference.py`, and `service.py`).
- Worse, handovers actively **save energy** due to the segment entry power anchor (`step.py:786-808`), where switching associations resets link power to $p_0 = 0.825\text{ W}$, whereas continuing links age up to $1.65\text{ W}$.
- Consequently, an unconstrained maximizer achieves +22.2% EE by inducing an absurd **71.17% handover rate** every 30.08 s (`dt`). No telecommunications operator would ever deploy a policy that forces 70% of user terminals to execute inter-beam or inter-satellite handovers every 30 seconds, flooding the random access channel (RACH), congesting core network signaling, and causing control-plane collapse.

**Conclusion:** The endpoint change is **legitimate ONLY as a formal problem reformulation (successor specification)**, NOT as a retroactive patch to validate the original run.

### 1.2 What Must Be Fixed in Advance (Pre-Registration Requirements)
To prevent the CMORL formulation from degenerating into circular outcome-fitting:
1. **The Unconstrained Metric Must Be Published as a Negative Result:** The paper must transparently report the unconstrained failure: that greedy `MAX_NOMINAL_GAIN` beats the trained policy by +22.2% at a 71.2% handover churn, proving that unconstrained EE in LEO satellite handover is degenerate without operational constraints.
2. **The Handover Constraint Must Be Exogenous (External Provenance):**
   - The handover constraint threshold $H_{\max}$ **must not be fitted to the trained policy’s performance (0.2796)**. Setting $H_{\max} = 0.30$ simply because the trained checkpoint achieves 0.28 while the greedy baseline achieves 0.71 is blatant outcome-fitting.
   - **External Source for Handover Constraint:** Derive $H_{\max}$ strictly from **3GPP NTN orbital geometry standards (3GPP TR 38.821 §6.1 / TS 38.300)**. In a typical 600 km LEO constellation (e.g. Walker Star / Starlink-like shells), satellite overhead pass duration is approximately $300\text{ s}$ to $600\text{ s}$ (10 to 20 steps of $dt = 30.08\text{ s}$). An acceptable operational handover frequency permits at most **one inter-satellite handover per satellite pass** plus a bounded intra-satellite beam switch budget.
   - For an average visibility window of $T_{\text{pass}} \approx 450\text{ s}$ (15 steps), the baseline inter-satellite handover rate is bounded by $1/15 \approx 0.067$ per step. Allowing an intra-satellite beam-switch budget of at most 1 switch per 3 steps yields a principled ceiling:
     $$H_{\max} \le 0.067 + 0.333 = 0.40\text{ handovers/user-step}$$
   - Any threshold chosen in the range $[0.25, 0.40]$ must be justified **exclusively by satellite dwell-time constraints and core-network signaling limits**, completely independent of the checkpoint's logged numbers.
3. **The Service Constraint Must Be Separated from Synthetic Rate Attainment:**
   - As established in earlier audits (`ADVERSARY-NARRATIVE-2026-09-11.md`), the 50 Mbit/s target was declared a "synthetic power-control setpoint, not a demand model".
   - The service constraint $S_{\min}$ must be pegged strictly to **PHY decodability and outage** (SINR $\ge -1.44\text{ dB}$, BLER $\le 10\%$, service availability $\ge 99.0\%$ or $99.5\%$, matching 3GPP TS 38.133 Annex A.14.2). Retroactively turning a 50 Mbit/s rate attainment target into a disqualifying service constraint after observing that concentrated configurations only reach 2.5% attainment is illegitimate.

### 1.3 What Makes a Choice of Threshold Illegitimate?
A choice of threshold is illegitimate if:
- It is set to the post-hoc operating point of any evaluated policy (e.g., $H_{\max} = 0.28$).
- It is swept or tuned on evaluation claim dates to find a boundary where the proposed learner wins.
- It changes definition between ablation arms (e.g. evaluating one arm on PHY service and another on rate attainment).

---

## 2. Attack on the Proposed Design

### 2.1 The Weakest Component: The Ratio-Objective Bellman Failure
The weakest component of the proposed design is **the fundamental mathematical mismatch between standard Bellman Q-learning in DQfD and the fractional pooled EE endpoint**.

DQfD trains a neural network via Temporal Difference (TD) learning on scalar transitions:
$$Q(s, a) \leftarrow Q(s, a) + \alpha \left[ r_t + \gamma \max_{a'} Q(s', a') - Q(s, a) \right]$$
The Bellman optimality equation is linear in expectations: it optimizes $\mathbb{E} \left[ \sum_{t=0}^\infty \gamma^t r_t \right]$.

However, the declared primary endpoint is:
$$\text{Pooled EE} = \frac{\sum_{t=1}^T \sum_{u=1}^U \text{Bits}_{u,t}}{\sum_{t=1}^T \sum_{u=1}^U \text{Joules}_{u,t}}$$
This is a **ratio of sums**, not a sum of ratios.
Even if $r_1$ is defined locally as bits/joules per user-step, $\mathbb{E}[\text{Bits}/\text{Joules}] \neq \frac{\mathbb{E}[\text{Bits}]}{\mathbb{E}[\text{Joules}]}$.

Worse, the current reward vector combines three heads:
$$r_t = 0.5 r_1 + 0.3 r_2 + 0.2 r_3$$
As established in Findings 7, 9, and 11:
1. $r_2$ (handover penalty) penalizes an action that **costs zero joules** and actually saves energy in the simulator.
2. $r_3$ ($-\text{occupancy}$ or throughput spread) **rewards spreading users across beams**. In physical reality, spreading users powers up additional RF chains (338 mW each) and increases unweighted multi-beam interference (`interference.py:10-14`), directly degrading pooled EE!
3. Power-infeasible/outage steps receive $r_2 = 0, r_3 = 0$, which is higher than served steps ($r_3 \le -1$), providing an artificial incentive for outages.

**The Failure Mode:**  
When the proposed DQfD backbone runs, it updates the Q-network using Bellman targets derived from $r_t$. Even if pre-training on `CF-EE` demonstrations initializes the network near high-EE actions, **the Bellman operator will relentlessly drag the policy toward the fixed point of $r_t$**. The moment the policy explores or updates on self-generated transitions, the Q-filter will detect that the demonstrator's action $a_D$ has lower $Q(s, a)$ under the misaligned reward than the spread-out, low-churn policy, and will **permanently disable the supervised loss**. The agent will unlearn the demonstration and collapse back to the suboptimal MODQN plateau.

### 2.2 The Single Decisive Measurement That Proves It Solves Nothing
**Measurement:** **Demonstration Retention and Regret Trajectory Across Training.**  
Track two metrics across the 3,000 training episodes:
1. **Q-Filter Acceptance Rate:** $\Phi_{\text{gate}}(e) = \frac{1}{|B_{\text{demo}}|} \sum_{(s, a_D) \in B_{\text{demo}}} \mathbf{1}\left( Q(s, a_D) > \max_{a \neq a_D} Q(s, a) \right)$.
2. **Policy-Demonstrator Action Overlap on OOS Anchors:** $J(e) = \frac{1}{|\mathcal{U}|} \sum_{u} \mathbf{1}\left( \pi_{\theta_e}(s_u) = a_u^{\text{CF-EE}} \right)$.

**Falsification Rule:**  
If $\Phi_{\text{gate}}(e)$ collapses toward zero and $J(e)$ drops back to baseline random/myopic levels ($\le 0.20$) as TD steps progress, while the converged policy fails to beat `MAX_NOMINAL_GAIN` on pooled EE or fails the handover constraint, **the architecture has solved nothing**. It will confirm that DQfD cannot retain demonstrations that are anti-aligned with its underlying Bellman reward.

---

## 3. Analysis of the Two-Specialist Structure: Real or Pseudonymous?

### 3.1 Arithmetic of the Interruption Channel (Finding 8)
Finding 8 demonstrates that moving handover cost into the numerator via a 142 ms physical interruption (3GPP TS 38.133 Annex A.14.2) across a 30.08 s step destroys:
$$\frac{0.142\text{ s}}{30.08\text{ s}} \approx 0.472\% \text{ of a step's bits}$$
Applied at its most favorable edge, it moves the pooled EE ratio from $1.19771 \to 1.19526$, closing only **1.2% of the gap** between `MAX_NOMINAL_GAIN` and the baseline.
To close the gap through transmission interruption alone would require **10.38 seconds of interruption per handover (68× to 167× the 3GPP specification)**, which violates all physical provenance.

### 3.2 The Verdict on CF-GUARD vs CF-EE
If `CF-GUARD` is parameterized merely by evaluating Dinkelbach EE with this 142 ms bit interruption, the utility difference between staying and handing over is $< 0.5\%$.
In contrast, the link gain difference between satellite beams typically spans **3 to 10 dB (a factor of 2× to 10× in received power or spectral efficiency)**.

Because link-margin differences dwarf the 0.47% interruption cost by an order of magnitude, the argmax of `CF-GUARD` and `CF-EE` will be **identical on >98% of decisions**.
Therefore, as currently conceived, **CF-GUARD is a pseudonymous relabelling of CF-EE**. Feeding both into separate logical buffers or sampling them conditionally is cosmetic complexity that accomplishes nothing.

### 3.3 What CF-GUARD Must Be Built on Instead
To make `CF-GUARD` genuinely complementary to `CF-EE`, it cannot rely on the inert physical bit-interruption. It must be built on one of two **binding operational trade-offs**:

1. **Option A: Explicit 3GPP Measurement-Report Hysteresis (A3/A4 Handover Margin):**  
   In cellular/NTN standards, a handover is never triggered merely because an alternative beam has an infinitesimally higher instantaneous SINR. It requires:
   $$\text{SINR}_{\text{target}} > \text{SINR}_{\text{serving}} + \text{Hysteresis Margin } (\text{e.g. } 3.0\text{ dB})$$
   and must persist over a Time-To-Trigger (TTT).  
   `CF-GUARD` should be constructed as a **Hysteresis-Filtered Dinkelbach Rule**: it chooses the target beam only if the projected net EE gain over the horizon exceeds a significant threshold $\Delta_{\text{margin}}$ (e.g. 15–25%), otherwise forcing association continuity.

2. **Option B: Beam Consolidation & RF Chain Extinction Guard:**  
   `CF-EE` selects beams based purely on per-user SNR, indifferent to whether its choice lights up an empty beam.  
   `CF-GUARD` should be an **Occupancy-Aware Consolidation Rule** that evaluates the marginal cost of lighting an idle RF chain ($338\text{ mW}$) or activating a satellite ($200\text{ mW}$). It penalizes beam dispersion and only allows handovers that join existing high-occupancy beams or allow an under-occupied beam to be completely extinguished.

### 3.4 Decisive Test of Complementarity
Before any neural network training begins, evaluate the two rule-based specialists across all development anchors:
1. **Action Disagreement Rate:** Compute $D(\text{CF-EE}, \text{CF-GUARD}) = 1 - \frac{1}{N} \sum_{i=1}^N \mathbf{1}(a_i^{\text{EE}} = a_i^{\text{GUARD}})$.  
   - If $D < 0.10$, **reject the two-specialist structure as redundant**.  
   - If $D \ge 0.25$, they represent genuinely distinct policies.
2. **Orthogonal Pareto Placement:** On the 2D plane of $(\text{Pooled EE}, \text{Handover Rate})$:
   - `CF-EE` must achieve high EE ($\ge 110\text{ Mbit/J}$) but violate the handover constraint ($H > 0.60$).
   - `CF-GUARD` must achieve compliant handover rate ($H \le 0.35$) with lower EE ($\sim 95\text{ Mbit/J}$).  
   Only if this contrast holds do the two specialists span the constrained decision boundary.

---

## 4. Theoretical Analysis: Ratio-Objective Reinforcement Learning

The objective is to find a policy $\pi$ maximizing the ratio of two expected cumulative quantities over a horizon $T$:
$$\max_\pi \rho(\pi) = \frac{\mathbb{E}_\pi \left[ \sum_{t=0}^T B(s_t, a_t) \right]}{\mathbb{E}_\pi \left[ \sum_{t=0}^T E(s_t, a_t) \right]} = \frac{\bar{B}(\pi)}{\bar{E}(\pi)}$$
where $B(s_t, a_t) \ge 0$ is successfully decoded bits and $E(s_t, a_t) > 0$ is total energy consumed.

### 4.1 Comparison of Formulations

| Formulation | Mathematical Principle | Compatibility with Off-Policy DQN | Convergence & Stability |
|---|---|---|---|
| **Dinkelbach Policy Iteration** (Dinkelbach 1967; Zappone & Jorswieck 2015) | Solves sequence of linear subproblems: $\max_\pi (\bar{B}(\pi) - \eta_k \bar{E}(\pi))$ with $\eta_{k+1} = \bar{B}(\pi_k)/\bar{E}(\pi_k)$. | **Poor if inner loop is DQN.** Shifting $\eta_k$ continuously changes the scalar reward $r_t(\eta) = B_t - \eta E_t$, invalidating replay buffer targets and destabilizing TD learning. | Superlinear convergence for exact inner optimization; unstable with function approximation. |
| **Semi-Markov / Reward-per-Cost** (Howard 1960; Puterman 1994) | Treats $E_t$ as transition duration $\tau_t$. Bellman equation: $h(s) = \max_a [B(s,a) - \rho^* E(s,a) + \sum P h(s')]$. | **Moderate.** Requires tracking differential values and global gain $\rho^*$. Difficult to stabilize in deep off-policy Q-learning. | Guaranteed for tabular discrete MDPs; non-trivial under deep neural networks. |
| **Average-Reward RL** (Mahadevan 1996; Wan, Naik & Sutton 2021) | Optimizes $\lim \frac{1}{T}\sum r_t$ via differential value functions $Q(s, a) - \bar{r}$. | **Incompatible directly.** Optimizes an expectation of ratios or simple average, not a ratio of two distinct expectations. | Well-studied for linear/tabular; sensitive to function approximation. |
| **Direct Ratio Policy Gradient** (Chen et al. 2022; Shen et al. 2023) | $\nabla_\theta \rho(\pi_\theta) = \frac{1}{\bar{E}(\theta)} \left[ \nabla \bar{B}(\theta) - \rho(\theta) \nabla \bar{E}(\theta) \right]$. | **Completely incompatible.** Requires on-policy trajectories (actor-critic / PPO); cannot run off-policy discrete DQN. | Stable with policy gradient / natural actor-critic, but high sample complexity. |
| **Constrained MDP (CMDP)** (Altman 1999; Achiam et al. 2017) | $\max_\pi \bar{B}(\pi)$ s.t. $\bar{E}(\pi) \le E_{\text{budget}}, H(\pi) \le H_{\max}$. Dual Lagrangian: $\min_\lambda \max_\pi \mathcal{L}(\pi, \lambda)$. | **Compatible for constraints**, but does not inherently solve the ratio form unless converted to an energy constraint. | Oscillations in primal-dual updates; requires careful learning rate tuning. |
| **Two-Critic Ratio Optimization ($Q_B, Q_E$)** (Geibel 2001; Calvo-Fullana et al. 2023) | Learns two independent, physically grounded critics $Q_B(s, a)$ and $Q_E(s, a)$ off-policy. Policy evaluates $Q_B(s, a) - \eta Q_E(s, a)$. | **Fully compatible with off-policy, discrete, action-masked DQN.** Replay buffer stores fixed physical primitives $(s, a, B, E, s')$. | High stability; critics have stationary targets independent of $\eta$. |

### 4.2 The Winning Architecture: Decoupled Two-Critic DQN with Outer-Loop Dinkelbach
The only mathematically rigorous way to combine off-policy discrete action-masked DQN with a ratio-of-sums endpoint is the **Decoupled Two-Critic ($Q_B, Q_E$) Architecture**.

#### 1. Replay Buffer Storage:
Every transition stores the raw physical primitives:
$$(s_t, a_t, B_t, E_t, s_{t+1}, \mathcal{M}_{t+1})$$
where $\mathcal{M}_{t+1}$ is the Boolean legal-action mask. **No synthetic scalarized reward is stored.**

#### 2. Critic Bellman Updates:
Two separate neural networks (or a shared torso with two independent output heads) are trained using standard Double-DQN:
$$\mathcal{L}(Q_B) = \mathbb{E} \left[ \left( B_t + \gamma Q_B^{\text{target}}\left(s_{t+1}, a^*_{t+1}\right) - Q_B(s_t, a_t) \right)^2 \right]$$
$$\mathcal{L}(Q_E) = \mathbb{E} \left[ \left( E_t + \gamma Q_E^{\text{target}}\left(s_{t+1}, a^*_{t+1}\right) - Q_E(s_t, a_t) \right)^2 \right]$$
where the greedy target action $a^*_{t+1}$ is selected via the current operational ratio exchange rate $\eta_k$:
$$a^*_{t+1} = \arg\max_{a' \in \mathcal{M}_{t+1}} \left[ Q_B(s_{t+1}, a') - \eta_k Q_E(s_{t+1}, a') \right]$$
Here, $\eta_k$ is updated periodically in the outer loop:
$$\eta_{k+1} = \frac{\sum_{i \in \mathcal{B}_{\text{eval}}} B_i}{\sum_{i \in \mathcal{B}_{\text{eval}}} E_i}$$

#### 3. Demonstrator Advantage and Q-Filtering:
Under this formulation, the demonstrator advantage for action $a_D$ is **linear in the critics and mathematically well-posed**:
$$A_{\text{demo}}(s, a_D; \eta_k) = \left[ Q_B(s, a_D) - \eta_k Q_E(s, a_D) \right] - \max_{a \in \mathcal{M}(s), a \neq a_D} \left[ Q_B(s, a) - \eta_k Q_E(s, a) \right]$$

The DQfD supervised margin loss is applied only when the Q-filter test passes:
$$J_E(Q) = \mathbf{1}\left( A_{\text{demo}}(s, a_D; \eta_k) \ge -\epsilon \right) \cdot \left[ \max_{a \in \mathcal{M}(s)} \left( Q_{\eta_k}(s, a) + l(a_D, a) \right) - Q_{\eta_k}(s, a_D) \right]$$
This guarantees that demonstrations are evaluated against the true energy efficiency ratio rather than a distorted scalar proxy.

#### Literature Citations:
- **Dinkelbach, W.** (1967). "On nonlinear fractional programming." *Management Science*, 13(7), 492–498.
- **Zappone, A., & Jorswieck, E.** (2015). "Energy efficiency in wireless networks via fractional programming theory." *Foundations and Trends in Communications and Information Theory*, 11(3–4), 185–396.
- **Geibel, P.** (2001). "Reinforcement learning with bounded risk and ratio objectives." *International Conference on Machine Learning (ICML)*.
- **Calvo-Fullana, M., Ribeiro, A., et al.** (2023). "State-augmented reinforcement learning for constrained and multi-objective problems." *IEEE Transactions on Signal Processing*, 71, 2011–2026.
- **Hester, T., et al.** (2018). "Deep Q-learning from Demonstrations (DQfD)." *AAAI Conference on Human Computation and Crowdsourcing / AAAI*.
- **Nair, A., et al.** (2018). "Overcoming exploration in reinforcement learning with demonstrations." *IEEE International Conference on Robotics and Automation (ICRA)*.

---

## 5. Novelty Assessment

The prompt correctly observes:
- Multiple heterogeneous demonstrators (R2D3, Gulcehre et al. 2020) are published.
- Q-filtering (Nair et al. 2018) is published.
- Imperfect-demonstration filtering (Wu et al. 2019; Wang et al. 2021) is published.
- Multi-objective RL with demonstrations is published.
- Dinkelbach fractional programming in wireless communications (Zappone & Jorswieck 2015) is published.

Is there a defensible algorithmic novelty here? **No.** Anyone claiming a novel RL algorithm will be shredded by reviewers.

The defensible contribution is entirely **empirical, diagnostic, and systems-architectural**.

### One-Sentence Contribution Statement:
> **"The defensible contribution of this work is not a new reinforcement learning algorithm, but an empirical and architectural finding in satellite communications: demonstrating that conventional multi-objective handover rewards actively degrade energy efficiency by penalizing handovers and rewarding beam spreading, and showing that only a decoupled, ratio-consistent demonstration architecture can prevent reinforcement learning from collapsing below simple physical heuristics under operational constraints."**

---

## 6. The Three Strongest Objections Ranked

### Objection 1 (Rank 1): The Endpoint Shift is Circular Outcome-Selection Unless Externally Bound to 3GPP Standards and Accompanied by Full Disclosure of the Unconstrained Result.
- **The Risk:** Changing from unconstrained EE to constrained EE after finding that `MAX_NOMINAL_GAIN` wins by +22.2% will be seen as moving the goalposts to salvage a failed hypothesis.
- **Evidence That Settles It:**
  1. Formally seal and pre-register the constraint bounds **before running any training**:
     - Service availability: $S_{\min} = 99.0\%$ decodable PHY steps (derived from 3GPP TS 38.133).
     - Handover frequency: $H_{\max} \le 0.40$ handovers/step (derived from 450 s LEO pass duration / 30 s time-step, completely independent of the checkpoint's 0.2796 figure).
  2. Include a primary diagnostic table displaying the **unconstrained endpoint**, showing that `MAX_NOMINAL_GAIN` achieves 111.55 Mbit/J but suffers a 71.17% handover churn, proving that unconstrained optimization produces an operationally infeasible control policy.

### Objection 2 (Rank 2): The Two Specialists (`CF-EE` and `CF-GUARD`) are Computationally Redundant Under the Sourced 142 ms Interruption Cost.
- **The Risk:** Finding 8 proves that the 142 ms interruption accounts for only 0.47% bits loss and 0 J cost. Under Dinkelbach selection, this negligible penalty will not overcome multi-dB link margin differences, causing `CF-GUARD` to emit action profiles $>98\%$ identical to `CF-EE`. The two-specialist architecture becomes theater.
- **Evidence That Settles It:**
  1. Build `CF-GUARD` on a true operational constraint: either an explicit 3GPP hysteresis margin ($\Delta_{\text{margin}} \ge 3\text{ dB}$) or an explicit beam-activation penalty ($338\text{ mW}$ RF chain extinction).
  2. Measure the pairwise action divergence $D(\text{CF-EE}, \text{CF-GUARD})$ across the 12 development anchors. If the action divergence is $< 10\%$, **halt immediately** and merge them into a single demonstrator.

### Objection 3 (Rank 3): Scalar DQfD Cannot Optimize a Fractional Pooled Ratio via Standard Bellman Updates.
- **The Risk:** In standard DQfD, the scalar reward $r_t = 0.5 r_1 + 0.3 r_2 + 0.2 r_3$ contains $r_3$ (spreading users, which increases RF chain power and interference) and $r_2$ (which prices a zero-joule event). During training, TD updates will pull the policy toward the misaligned reward's fixed point, causing the Q-filter to reject demonstrator actions and unlearning the demonstration.
- **Evidence That Settles It:**
  1. Replace the scalar Q-network with the decoupled **Two-Critic ($Q_B, Q_E$) Architecture**, storing raw $(B_t, E_t)$ in the replay buffer.
  2. Measure the **Demonstrator Advantage Gate Fraction** $\Phi_{\text{gate}}$ across 3,000 training episodes. A stable, non-zero gate fraction ($0.15 \le \Phi_{\text{gate}} \le 0.60$) through convergence confirms that the Q-filter maintains demonstrator alignment without collapsing.

---

## 7. Audit Ledger: Verified Facts vs Inferences

| Dimension | Item / Measurement | Verified Fact (Code/Data) | Reviewer Inference / Assertion |
|---|---|---|---|
| **Physics** | Handover energy cost | Verified: `grep -ci handover` is 0 in energy routines; segment change resets power to $p_0 = 0.825\text{ W}$. | Handovers save energy in the simulator; $r_2$ is economically inverted. |
| **Physics** | Interruption impact | Verified: 142 ms out of 30.08 s is $0.472\%$ bits; closes only $1.2\%$ of the gap. | `CF-GUARD` cannot produce distinct actions based on interruption alone. |
| **Physics** | Load balancing ($r_3$) | Verified: Beam rate is $B \cdot \text{mean}(SE)$; interference is z-gated and unweighted; RF chain costs 338 mW. | Spreading users degrades EE; $r_3$ is actively anti-aligned with pooled EE. |
| **Performance** | Unconstrained EE gap | Verified: `MAX_NOMINAL_GAIN` reaches 111.55 Mbit/J vs trained 93.14 Mbit/J (+19.8% / +22.2% ablated). | Unconstrained EE is dominated by a greedy heuristic; learner is unnecessary on that metric. |
| **Performance** | Handover rates | Verified: `MAX_NOMINAL_GAIN` has 0.7117 handover rate; trained has 0.2796. | Handover constraint separates the heuristic from the learner; creates the only valid job for RL. |
| **Theory** | Ratio optimization | Verified: $\mathbb{E}[B]/\mathbb{E}[E] \neq \mathbb{E}[B/E]$; Bellman expectation equations are linear. | Standard scalar DQfD has a mathematical mismatch with pooled EE; requires $(Q_B, Q_E)$ two-critic decoupling. |
| **Prior Work** | C1/C2/C3 Status | Verified: $C_1 + C_3 = \Delta F$ identically; C1 loses to `RSS_MAX` by $-6.45\%$; C3 oracle marginal is $-1.78\%$. | The three-route decomposition is dead and must not be resurrected. |

---

## 8. Summary of Mandatory Changes for the Project Execution

1. **Adopt CMORL Formulation with Pre-Registered 3GPP Constraints:**  
   - Declare primary endpoint as: **Pooled EE subject to Handover Rate $H \le 0.40$ and Service Availability $S \ge 99.0\%$.**  
   - Report unconstrained Pooled EE as an unconstrained negative control.
2. **Re-architect CF-GUARD Around 3GPP Hysteresis or Beam Evacuation:**  
   - Discard the 142 ms interruption as CF-GUARD's mechanism.  
   - Define CF-GUARD using a declared $\Delta_{\text{SINR}} \ge 3\text{ dB}$ hysteresis rule and assert $D(\text{CF-EE}, \text{CF-GUARD}) \ge 0.20$ before training.
3. **Implement Decoupled Two-Critic ($Q_B, Q_E$) Architecture:**  
   - Store raw $(B, E)$ in replay partitions.  
   - Remove $r_2$ and $r_3$ from the Bellman target.  
   - Use Dinkelbach parameter $\eta_k$ only in the outer policy evaluation loop.
4. **Enforce Supervised Representability Gate Before Training:**  
   - Ensure the per-user observation space can fit the demonstration actions (BC Top-1 accuracy $\ge 85\%$) before launching the 3,000-episode training run.
