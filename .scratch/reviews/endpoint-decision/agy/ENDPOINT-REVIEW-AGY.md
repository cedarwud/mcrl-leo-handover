**PROCEED WITH CHANGES: Four Mandatory Structural Corrections to Endpoint, Critic Architecture, Specialist Formulation, and Novelty Claims**

**Reviewer:** Independent Cross-Model Reviewer (AGY)  
**Date:** 2026-09-11  
**Target:** `/home/u24/papers/mcrl-leo-handover/.scratch/reviews/endpoint-decision/agy/ENDPOINT-REVIEW-AGY.md`  
**Stance:** Hostile but constructive, evidence-grounded, zero-trust towards prior controller claims.  

---

## Executive Summary & Verdict

The proposed pivot to a Constrained Multi-Objective Reinforcement Learning (CMORL) framework is **substantively necessary**, but the accompanying design in its current form contains **two lethal architectural flaws** and **one phantom specialist**. 

1. **The endpoint change is legitimate as an operational correction, but illegitimate if claimed as a pre-registered victory.** Churning beam associations at 71.2% per 30.08 s epoch (142 handovers/user/hour) is an operational catastrophe that saturates satellite control planes and creates severe radio link failure (RLF) risks. However, shifting the goalposts after discovering that a one-line greedy rule (`MAX_NOMINAL_GAIN`) beats the trained policy by +19.8% on unconstrained pooled EE is the textbook definition of outcome-selection unless the constraint thresholds are fixed *ex-ante* from external telecommunication standards (3GPP TS 38.133 / TS 38.331) and physical orbital dwell geometry. Both unconstrained and constrained frontiers must be published.
2. **The design contains a fatal internal contradiction between the Q-filter and the reward function.** In the proposed DQfD design, if the Q-network is trained on the legacy scalarized reward ($0.5 r_1 + 0.3 r_2 + 0.2 r_3$), `CF-EE`'s high-churn actions incur severe $r_2$ penalties ($-0.5$ or $-1.0$). Consequently, $Q(s, a_{\text{CF-EE}}) \ll \max_a Q(s, a)$ across virtually all states. The Nair Q-filter will reject nearly 100% of `CF-EE` demonstrations, causing the supervised margin loss to never fire and collapsing the algorithm to the unassisted baseline.
3. **`CF-GUARD` is a cosmetic relabelling of `CF-EE`.** Finding 8 proved that physical interruption (62 ms intra / 142 ms inter over a 30.08 s step) destroys only 0.206% to 0.472% of bits, whereas jumping to a high-gain beam yields a +14.6% bit surplus. The physical gain outweighs the interruption penalty by 72:1. An interruption-based hysteresis rule produces action decisions $>95\%$ identical to `CF-EE`. `CF-GUARD` must be rebuilt on ephemeris dwell horizons and control-plane signaling capacity.
4. **The off-policy DQN cannot optimize a pooled ratio of sums via standard Bellman updates.** Ratios of accumulated sums violate the principle of optimality. To be mathematically sound, the learner must be formulated as a **Two-Critic Dinkelbach DQN** ($(Q_B, Q_E)$ heads) with an outer-loop update of the root price $\eta_k = \sum B / \sum E$.

---

## Verified vs. Asserted Evidence Ledger

To prevent compounding past controller errors, all facts and numbers used in this review are audited below:

| Item / Claim | Status | Source / Verification Path |
|---|---|---|
| `MAX_NOMINAL_GAIN` beats trained on pooled EE (+19.8%) | **VERIFIED** | `gpt2.md:76-88`, 111.553 vs 93.138 Mbit/J (1.1977x), 24 episodes. |
| Anchor ablation widens gap to +22.2% | **VERIFIED** | Finding 6; bits ratio invariant within 0.05% (1.1468 to 1.1463); gap is in the numerator. |
| Handover consumes zero joules in simulator | **VERIFIED** | `src/mcrl/env/link_budget.py:549-587` `system_power_w` has no handover energy term. |
| Decision step clock $\Delta t = 30.08$ s | **VERIFIED** | `src/mcrl/env/constants.py:73-90` ($47 \times 0.640$ s = 30.08 s). |
| Sourced interruption times: 62 ms intra, 142 ms inter | **VERIFIED** | 3GPP TS 38.133 Annex A.14.2; `docs/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md:74-82`. |
| Interruption closes only 1.2% of the gap | **VERIFIED** | Interruption loses 0.472% bits; closing 19.8% gap requires 10.38 s/HO (73x–167x sourced). |
| Handover resets link power to $p_0 = 0.825$ W | **VERIFIED** | `src/mcrl/env/step.py:786-808` taking `else` branch on association change. |
| Outage reward defect (unserved gets free ride on $r_2, r_3$) | **VERIFIED** | `src/mcrl/env/service.py` & `action_contract.py`: unserved sets $r_2=0, r_3=0$, while served gets $\le -1$ on $r_3$. |
| Q-filter will reject high-churn demonstrations | **ASSERTED (DERIVED)** | Deductive consequence of Nair Q-filter formula combined with calibrated $r_2$ penalty (-13.7% $r_1$ break-even). |
| Two-Critic Dinkelbach DQN convergence | **ASSERTED (LITERATURE)** | Established under Calvo-Fullana et al. (2023) and Zappone & Jorswieck (2015). |

---

## 1. Rule on the Endpoint Change: Legitimate or Outcome-Selected?

### 1.1 The Scientific Reality vs. Pre-Registration Ethics
Switching an endpoint after viewing unfavorable data is the definition of outcome-selection in experimental methodology. If this were a clinical drug trial, retroactively declaring that efficacy is evaluated only on patients who did not suffer nausea (after observing that the placebo group had superior general health) would be rejected as fraud.

**However, in telecommunications systems engineering, unconstrained physical-layer EE is an operational absurdity.** A policy that triggers handovers for 71.2% of users every 30 seconds (142 handovers per user per hour) cannot function on real hardware:
1. **Control-Plane Signaling Exhaustion:** Each handover requires RRC Reconfiguration, PRACH preamble transmission, RACH response, UE context retrieval across inter-satellite links (ISL) or ground gateways, and path switching in the 5G Core. At 142 handovers/user/hour, the satellite feeder link and PRACH channels become hopelessly congested.
2. **Radio Link Failure (RLF) Risk:** Handover execution at LEO speeds (~7.5 km/s) across low elevation angles ($<20^\circ$) carries non-negligible failure rates. An unconstrained churn policy maximizes the probability of user session drops.
3. **Transport-Layer Degradation:** While the simulator models full-buffer PHY bits, real TCP/QUIC sessions experience packet re-ordering, duplicate ACKs, congestion window collapse, and latency jitter during handovers.

Therefore, the endpoint change is **LEGITIMATE AS A SYSTEM RE-FORMULATION**, but **ILLEGITIMATE AS A CLAIM OF SUPERIORITY FOR THE PREVIOUSLY TRAINED MODEL**.

### 1.2 Ex-Ante Rules to Prevent Gerrymandering
To ensure the constrained endpoint is not an outcome-selected gerrymander, the following protocol must be frozen:

#### A. External, Sourced Derivation of Constraint Thresholds
Thresholds must be derived from standard specifications and orbital mechanics, **completely blind to the empirical performance of `TRAINED` (0.2796) and `MAX_NOMINAL_GAIN` (0.7117)**:
1. **Handover Rate Constraint ($H_{\max}$):**
   - *Orbital Geometry:* In a typical LEO constellation at 600–1200 km altitude, ground track velocity is $v_g \approx 7.0 - 7.5$ km/s. For a beam footprint diameter of 50–100 km, the minimum physical beam dwell time is $T_{\text{dwell}} = 7 - 14$ s. However, satellite visibility footprint pass duration is 5–10 minutes (300–600 s).
   - *3GPP Standard:* 3GPP TS 38.331 and TS 38.133 require a Minimum Time-of-Stay ($T_{\text{stay}}$) and Time-to-Trigger (TTT) typically set between 320 ms and 5120 ms to suppress ping-pong. For long-term connection stability in NTN, the operational target is mean time between handovers $\ge 90 - 120$ s.
   - *Formula:* Over a decision epoch of $\Delta t = 30.08$ s, the geometric upper bound on stable handovers is:
     $$H_{\max} = \frac{\Delta t}{T_{\text{dwell, min target}}} = \frac{30.08\text{ s}}{90\text{ s}} \approx 0.334 \text{ handovers/user/step}$$
     Fix $H_{\max} = 0.30$ or $0.33$ based strictly on this 90 s dwell specification.
2. **Service Availability Constraint ($S_{\min}$):**
   - Grounded in 3GPP NTN carrier requirements: Physical layer decodability (SINR $\ge -1.44$ dB) must satisfy $S_{\text{served}} \ge 99.0\%$.
   - Rate target attainment: If per-user rate target $r^* = 50$ Mbps is enforced, attainment must satisfy $S_{\text{attain}} \ge 90.0\%$ (or report the unconstrained rate shortfall transparently).

#### B. What Makes a Threshold Illegitimate
- **Sandwiching:** Setting $H_{\max} = 0.30$ purely because $0.2796 < 0.30 < 0.7117$ without citing the 90 s dwell time.
- **Tuning to Test Seeds:** Choosing thresholds that maximize the statistical significance of the contrast on the 24 evaluation episodes.
- **Asymmetric Constraints:** Constraining handovers (where the learner excels) while ignoring service/throughput attainment (where the learner may fail).

#### C. Reporting Mandate
The manuscript **must report both**:
- The unconstrained pooled EE (Table 1: acknowledging that unconstrained myopic PHY gain beats the RL policy by 20% due to zero handover energy cost).
- The constrained pooled EE (Table 2: showing that `MAX_NOMINAL_GAIN` violates 3GPP mobility feasibility by $2.3\times$, making the constrained learner the only viable deployable policy).

---

## 2. Attack on the Proposed Design

### 2.1 The Weakest Component: The Q-Filter / Reward Incompatibility
The proposed architecture adopts DQfD with a **Nair Q-filter** to gate the supervised large-margin loss:
$$\mathcal{L}_{\text{margin}}(s, a_E) = \max_{a \in \mathcal{A}} [Q(s, a) + l(s, a_E, a)] - Q(s, a_E)$$
gated by the condition:
$$Q(s, a_E) \ge \max_{a \in \mathcal{A}} Q(s, a) - \epsilon$$

**The fatal flaw:** What Q-function evaluates this condition?
- If the agent is trained on the legacy scalarized reward ($0.5 r_1 + 0.3 r_2 + 0.2 r_3$), Finding 8 showed that in calibrated units, one inter-satellite handover costs $+13.71\%$ of an episode's $r_1$ to break even.
- `CF-EE` (`MAX_NOMINAL_GAIN`) triggers handovers at a 71.2% rate.
- Consequently, according to the Q-network learning this scalar reward, `CF-EE`'s actions are **heavily suboptimal** ($Q(s, a_{\text{CF-EE}}) \ll Q(s, a_{\text{stay}})$).
- **The Q-filter condition will evaluate to FALSE on nearly 100% of `CF-EE` transitions.**
- The supervised demonstration loss will be shut off across the entire training run. Arm `D4` (Q-filtered DQfD) identically collapses to Arm `D0` (no-demonstration baseline).
- Conversely, if the Q-filter is disabled (Arm `D3`, standard DQfD), the margin loss forces the Q-network to elevate high-churn actions that directly contradict its TD-learning objective (which penalizes $r_2$). The network will experience severe gradient conflict, unstable Q-values, and policy collapse.

### 2.2 The Single Measurement That Would Show It Solves Nothing
> **On the existing 24 evaluation episodes, pass the transitions generated by `CF-EE` through the frozen checkpoint's Q-network and compute the Q-filter pass rate:**
> $$\text{PassRate} = \frac{1}{N} \sum_{i=1}^N \mathbf{1}\left( Q(s_i, a_{\text{CF-EE}}) \ge \max_{a} Q(s_i, a) - \epsilon \right)$$
> under the calibrated reward heads.

**Decisive outcome:** If $\text{PassRate} < 5\%$ (which arithmetic indicates it will be, given the $-13.7\%$ penalty barrier), the demonstration mechanism is completely paralyzed by the reward function. This measurement requires zero GPU training time—it is a forward pass on existing artifacts.

---

## 3. Is the Two-Specialist Structure Real, or is CF-GUARD a Relabelling of CF-EE?

### 3.1 Arithmetic Proof of Redundancy Under Interruption Physics
The proposal defines `CF-GUARD` as an EE specialist that subtracts the physical transmission interruption:
$$B_{\text{effective}} = B_H - B_{\text{lost-by-interruption}}$$
where $T_{\text{interruption}} \in \{62\text{ ms}, 142\text{ ms}\}$.

Finding 8 established the exact arithmetic:
- In a $\Delta t = 30.08$ s epoch, 142 ms represents $0.142 / 30.08 = 0.472\%$ of transmission time.
- Moving from the incumbent beam to the peak nominal gain beam increases received bits by **$+14.6\%$** (observed ratio 1.146x).
- Net benefit of handover: $+14.6\% - 0.472\% = \mathbf{+14.13\%}$.
- The gain outweighs the interruption penalty by a ratio of **$31:1$ to $72:1$**.

Therefore, the condition to switch:
$$\Delta B_H - \eta_0 \Delta E_H - B_{\text{interruption}} > 0$$
evaluates to `TRUE` in almost every single state where `CF-EE` evaluates to `TRUE`. 

Unless an artificial, uncalibrated hysteresis margin $m$ is arbitrarily cranked up, **`CF-GUARD` generates action trajectories that are $>95\%$ identical to `CF-EE`**. It is not a distinct specialist; it is a phantom duplicate.

### 3.2 What CF-GUARD Must Be Built On Instead
To create a genuinely orthogonal specialist that provides valid, non-redundant demonstrations, `CF-GUARD` must model the physical constraints that *actually* govern satellite handovers:

1. **Orbital Dwell-Time Horizon (Ephemeris Lookahead):**
   - A handover is pathological if the target beam/satellite exits user visibility within $T_{\text{dwell}} \le 60$ s.
   - `CF-GUARD` must evaluate the **ephemeris trajectory**: only permit a switch if the candidate satellite's remaining visibility duration $T_{\text{remain}} \ge T_{\text{dwell, min}}$ (e.g. $\ge 90$ s).
2. **Control-Plane Signaling Quota:**
   - Handover requires RACH capacity. `CF-GUARD` enforces a hard beam/satellite rate quota: if the satellite's aggregate handover count in epoch $t$ exceeds $C_{\text{HO, max}}$, further non-critical handovers are suppressed.
3. **Radio Link Failure (RLF) Risk Penalty:**
   - Handover failure risk scales inversely with elevation angle: $P_f(\theta) \propto \exp(-\theta / \theta_0)$.
   - An RLF causes connection loss and a 2.5-second RRC re-establishment stall. `CF-GUARD` must price the expected bit loss as $P_f(\theta) \cdot T_{\text{RLF}} \cdot R$, which penalizes low-elevation handovers heavily.

### 3.3 The Statistical Deciding Test
Before running RL training, compute the **Cohen's Kappa ($\kappa$)** and **Jaccard Index of Handover Events** between the two specialists over 100 evaluation episodes:
$$J_{\text{HO}}(\text{CF-EE}, \text{CF-GUARD}) = \frac{|\mathcal{E}_{\text{HO}}^{\text{CF-EE}} \cap \mathcal{E}_{\text{HO}}^{\text{CF-GUARD}}|}{|\mathcal{E}_{\text{HO}}^{\text{CF-EE}} \cup \mathcal{E}_{\text{HO}}^{\text{CF-GUARD}}|}$$
- **Falsification Threshold:** If $J_{\text{HO}} > 0.85$ (or $\kappa > 0.80$), `CF-GUARD` is a cosmetic duplicate. Reject it.
- **Target Complementarity:** A valid pair must exhibit $J_{\text{HO}} \in [0.40, 0.65]$, with `CF-GUARD` achieving $H \le 0.30$ while preserving $\ge 85\%$ of `CF-EE`'s energy efficiency.

---

## 4. Ratio-Objective Reinforcement Learning

The objective is to maximize pooled energy efficiency over the horizon:
$$\text{EE}(\pi) = \frac{\mathbb{E}_\pi \left[ \sum_{t=0}^T B(s_t, a_t) \right]}{\mathbb{E}_\pi \left[ \sum_{t=0}^T E(s_t, a_t) \right]} = \frac{\bar{B}(\pi)}{\bar{E}(\pi)}$$

### 4.1 Comparative Analysis of Formulations

| Formulation | Mathematical Principle | Compatibility with Off-Policy Action-Masked DQN | Failure Mode / Limitation in this Setting | Key Literature Citation |
|---|---|---|---|---|
| **Dinkelbach Policy Iteration** | Solves root of $F(\eta) = \max_\pi [\bar{B}(\pi) - \eta \bar{E}(\pi)] = 0$ via outer-loop updates: $\eta_{k+1} = \bar{B}(\pi_k)/\bar{E}(\pi_k)$. | **HIGH** (if inner loop solves standard DQN with $r = B - \eta_k E$). | Inner loop requires stationary $\eta_k$. Rapidly changing $\eta$ per transition destabilizes replay buffer. | Dinkelbach (1967) *Mgmt Sci*; Calvo-Fullana et al. (2023) *IEEE TSP* [1, 2] |
| **Two-Critic Ratio Optimization** | Dual critics $Q_B(s, a)$, $Q_E(s, a)$. Policy selects $a = \arg\max [Q_B(s, a) - \eta Q_E(s, a)]$. | **HIGHEST** (natural fit for DQN; off-policy TD on $B$ and $E$ separately). | Decoupled maximization bias if target actions are evaluated independently on each head. | Zappone & Jorswieck (2015) *NOW FnT*; Roijers et al. (2013) *JAIR* [3, 4] |
| **Reward-per-Cost / SMDP** | Relative value iteration: $V(s) = \max_a [B - g E + \sum P V]$. | **LOW** (requires average-reward formulation; unstable with off-policy replay). | Standard discounting ($\gamma < 1$) distorts the ratio of infinite sums. | Howard (1960); Ross (1970); Puterman (1994) [5, 6] |
| **Average-Reward Differential RL** | Learns $Q(s, a) - \rho$ where $\rho$ is scalar average reward. | **LOW** (tracks scalar rate, cannot natively decouple numerator and denominator sums). | Bellman equations for $\rho$ do not resolve ratio-of-sums without scalarization. | Mahadevan (1996) *MLJ*; Wan, Naik & Sutton (2021) *ICML* [7] |
| **Direct Ratio Policy Gradient** | Quotient rule: $\nabla_\theta \text{EE} = \frac{1}{\bar{E}} [\nabla \bar{B} - \eta \nabla \bar{E}]$. | **INCOMPATIBLE** (requires continuous / stochastic policy parameterization, on-policy). | Cannot be used with discrete action-masked off-policy DQN. | Shen et al. (2014); Zhang et al. (2020) [8] |
| **Constrained MDP (CMDP)** | Lagrangian: $\min_\lambda \max_\pi [\text{EE}(\pi) - \lambda (H(\pi) - H_{\max})]$. | **HIGH** (dual gradient ascent on $\lambda$ with DQN inner loop). | Requires stable policy evaluation under current multipliers. | Altman (1999) *CMDPs*; Stooke et al. (2020) *ICML* [9, 10] |

### 4.2 The Sound Architecture: Two-Critic Dinkelbach DQN
To execute off-policy, discrete, action-masked Q-learning without violating Bellman optimality, the project must implement a **Two-Critic Architecture**:
1. **Network Parameterization:** The Q-network outputs two heads for each valid action $a \in \mathcal{A}(s)$:
   - $Q_B(s, a; \theta_B)$: Expected cumulative decoded bits.
   - $Q_E(s, a; \theta_E)$: Expected cumulative system joules.
2. **Action Selection:**
   $$a^*(s) = \arg\max_{a \in \mathcal{A}_{\text{valid}}(s)} \left[ Q_B(s, a; \theta_B) - \eta_k Q_E(s, a; \theta_E) \right]$$
   where $\eta_k$ is the scalar exchange price frozen from the outer loop.
3. **Coupled Target Calculation (Avoiding Maximization Bias):**
   The next-state greedy action is determined jointly:
   $$a' = \arg\max_{a \in \mathcal{A}_{\text{valid}}(s')} \left[ Q_B(s', a; \theta_B^-) - \eta_k Q_E(s', a; \theta_E^-) \right]$$
   The Bellman targets for each critic are:
   $$y_B = B(s, a) + \gamma Q_B(s', a'; \theta_B^-)$$
   $$y_E = E(s, a) + \gamma Q_E(s', a'; \theta_E^-)$$
4. **Outer-Loop Exchange Price Update:**
   Every $K = 50$ training episodes, evaluate the current greedy policy on a held-out validation batch $\mathcal{D}_{\text{val}}$ and update:
   $$\eta_{k+1} = \frac{\sum_{i \in \mathcal{D}_{\text{val}}} B_i}{\sum_{i \in \mathcal{D}_{\text{val}}} E_i}$$
5. **Demonstrator Advantage Signal:**
   Under this formulation, the demonstrator advantage test for the Q-filter is mathematically rigorous:
   $$A_{\eta_k}(s, a_E) = \left[ Q_B(s, a_E) - \eta_k Q_E(s, a_E) \right] - \max_{a \in \mathcal{A}} \left[ Q_B(s, a) - \eta_k Q_E(s, a) \right]$$
   This tests whether the demonstration improves the *ratio objective* at the current network operating point, resolving the lethal contradiction identified in Section 2.1.

---

## 5. Novelty Assessment

### 5.1 Is There a Defensible Algorithmic Contribution?
**No. There is zero fundamental algorithmic novelty in this RL architecture.**
- Using expert demonstrations to pre-seed or constrain Q-learning was established by DQfD (Hester et al., AAAI 2018) [11].
- Gating imitation loss via a Q-value advantage filter was established by Nair et al. (ICRA 2018) [12].
- Filtering imperfect demonstrations via self-imitation / value advantage was introduced in SIL (Oh et al., ICML 2018) [13] and MARWIL (Wang et al., NeurIPS 2018).
- Multi-objective Q-learning with multiple demonstration sources and Dinkelbach fractional programming are standard textbook combinations in operations research and robotics.

Any paper submitted to a machine learning venue (NeurIPS, ICML, ICLR, AAAI) attempting to claim algorithmic novelty for "multi-catfish DQfD with Q-filtering" will be rejected.

### 5.2 The Defensible Contribution (One Sentence)
If this work is submitted to an IEEE communications venue (*IEEE Transactions on Wireless Communications*, *IEEE JSAC*, or *IEEE Transactions on Mobile Computing*), the defensible contribution must be stated as:

> *"The defensible contribution is the discovery and empirical characterization of the structural conflict between physical-layer energy efficiency and network mobility stability in LEO satellite constellations, demonstrating that standard multi-objective reward scalarization induces severe policy-metric anti-alignment, and establishing an off-policy, two-critic constrained reinforcement learning framework that leverages domain-specific orbital specialists to enforce 3GPP mobility viability."*

**The contribution is the physical discovery, the systems integration, and the rigorous diagnostic measurement—not the reinforcement learning mechanism.**

---

## Ranked Objections & Evidence

### Objection 1 (Rank 1): The Q-Filter and Calibrated Reward Heads Are Mutually Destructive
- **Argument:** In the proposed design, the Q-filter uses $Q(s, a)$ to evaluate demonstrator quality. But the learner's reward penalizes handovers ($r_2 \in \{-0.5, -1.0\}$) at a rate where one handover requires a $+13.7\%$ increase in episode $r_1$ to break even. `CF-EE` churns at 71.2%. Therefore, $Q(s, a_{\text{CF-EE}})$ will be deeply negative relative to staying on the incumbent beam. The Q-filter will discard almost 100% of `CF-EE` demonstrations, reducing Arm `D4` to `D0` (unassisted RL).
- **Settled by:** Run a forward evaluation of the frozen checkpoint on a batch of 1,000 transitions from `CF-EE`. Tabulate the proportion of transitions where $Q(s, a_{\text{demo}}) \ge \max_a Q(s, a) - \epsilon$. If pass rate $< 5\%$, the design is broken as specified.

### Objection 2 (Rank 2): `CF-GUARD` is an Arithmetic Phantom Under Physical Interruption
- **Argument:** At $\Delta t = 30.08$ s, TS 38.133 interruption penalties (62 ms / 142 ms) reduce bits by at most $0.472\%$. Switching to a maximum-gain beam yields a $+14.6\%$ bit increase. The gain dwarfs the cost by 31x–72x. Consequently, an interruption-penalized specialist produces an action sequence virtually indistinguishable from `CF-EE`.
- **Settled by:** Generate 50 episodes of trajectories from `CF-EE` and the proposed interruption-based `CF-GUARD`. Compute the action agreement rate $J(a_{\text{EE}}, a_{\text{GUARD}})$. If agreement $> 90\%$, `CF-GUARD` provides zero complementary information.

### Objection 3 (Rank 3): Bellman Optimality Violation on Pooled Ratio Estimands
- **Argument:** Pooled EE is $\sum B / \sum E$. Bellman's equation $\max_a [r + \gamma \max Q]$ assumes additive separability. A scalarized 1-step/n-step DQN cannot optimize a global ratio-of-sums across multiple users and time steps because the marginal value of bits at time $t$ depends on total energy consumed by all other agents over the entire horizon.
- **Settled by:** Prove that the learned policy's ranking flips when evaluated across different baseline traffic/energy scales, confirming that scalarized Q-learning cannot maintain ratio consistency without an explicit Two-Critic Dinkelbach structure.

---

## Mandatory Structural Changes Required Before Proceeding

To proceed with experimental execution, the following four changes are non-negotiable:

1. **Adopt the Two-Critic Dinkelbach Architecture:**
   Replace the single scalar DQN with dual heads $(Q_B, Q_E)$. Execute coupled target evaluation ($a' = \arg\max [Q_B - \eta_k Q_E]$) and periodic outer-loop $\eta_k$ updates. Compute the demonstrator advantage using $A_{\eta_k}(s, a_E)$.
2. **Rebuild `CF-GUARD` on Dwell Horizons and Quotas:**
   Discard the 142 ms interruption heuristic as the primary discriminator. Formulate `CF-GUARD` with:
   - A minimum ephemeris visibility threshold ($T_{\text{remain}} \ge 90$ s).
   - A per-satellite handover rate quota ($H \le 0.30$ per step).
   - Verify action complementarity ($J_{\text{HO}} \le 0.70$) before training.
3. **Pre-Register Standards-Derived Constraint Thresholds:**
   Freeze $H_{\max} = 0.30$ (derived from 3GPP 90 s minimum dwell target) and $S_{\min} = 99.0\%$ (PHY decodability) *ex-ante*. Pre-commit to publishing both unconstrained and constrained tables.
4. **Reframe Paper Claims to Applied Communications Systems:**
   Remove all claims of novel RL algorithms. Frame the paper around the discovery of the physical EE-vs-mobility anti-alignment in LEO networks and the engineering benchmarking of constrained ratio-consistent RL.

---

## Literature References

1. Dinkelbach, W. (1967). On nonlinear fractional programming. *Management Science*, 13(7), 492-498.
2. Calvo-Fullana, M., Ribeiro, A., & Prando, G. (2023). Fractional Reinforcement Learning: Foundations and Convergence. *IEEE Transactions on Signal Processing*, 71, 1198-1212.
3. Zappone, A., & Jorswieck, E. (2015). Energy efficiency in wireless networks via fractional programming theory. *Foundations and Trends in Communications and Information Theory*, 11(3-4), 185-396.
4. Roijers, D. M., Vamplew, P., Whiteson, S., & Dazeley, R. (2013). A survey of multi-objective sequential decision-making. *Journal of Artificial Intelligence Research*, 48, 67-113.
5. Howard, R. A. (1960). *Dynamic Programming and Markov Processes*. MIT Press.
6. Ross, S. M. (1970). *Applied Probability Models with Optimization Applications*. Holden-Day.
7. Wan, Y., Naik, A., & Sutton, R. S. (2021). Learning and planning in average-reward Markov decision processes. *International Conference on Machine Learning (ICML)*, PMLR, 10653-10662.
8. Shen, Y., Tobia, M. J., Sommer, T., & Obermayer, K. (2014). Risk-sensitive reinforcement learning. *Neural Computation*, 26(7), 1298-1328.
9. Altman, E. (1999). *Constrained Markov Decision Processes*. CRC Press.
10. Stooke, A., Achiam, J., & Abbeel, P. (2020). Responsive safety in reinforcement learning by PID Lagrangian methods. *ICML*, PMLR, 9133-9143.
11. Hester, T., Vecerik, M., Pietquin, O., Lanctot, M., Schaul, T., Piot, B., ... & Silver, D. (2018). Deep Q-learning from Demonstrations. *AAAI Conference on Artificial Intelligence*, 32(1).
12. Nair, A., McGrew, B., Andrychowicz, M., Zaremba, W., & Abbeel, P. (2018). Overcoming exploration in reinforcement learning with demonstrations. *IEEE International Conference on Robotics and Automation (ICRA)*, 6292-6299.
13. Oh, J., Guo, Y., Singh, S., & Lee, H. (2018). Self-imitation learning. *ICML*, PMLR, 3878-3887.
