# Multi-Catfish MCRL: Science Claim Map (V0.23)

- **Authority Baseline:** `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`, `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md`, `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md`.
- **Purpose:** Provide an unambiguous, audit-ready taxonomy distinguishing **Active Verified Method Facts**, **Historical Development Evidence**, **Scientific Inferences**, **Active Method Proposals & Gate Protocol**, and **Prohibited Claims**.
- **Core Principle:** **Never claim efficacy.** Development gates, mathematical identities, and offline losses do not constitute proof of episode-level reinforcement learning performance. The method name is strictly *Multi-Catfish MCRL*; MCRL must never be expanded as arbitrary phrases.

---

## 1. Active Verified Method Facts (Mathematical & Architectural Truths)

These items are mathematically proven identities, code-audited specifications, or architectural invariants guaranteed by construction and verified by unit tests:

1. **Canonical Evaluation Metric ($\eta^N$):**
   The sole scientific endpoint is the network ratio-of-sums energy efficiency:
   $$
   \eta^N = \frac{\mathcal{B}}{\mathcal{E}} = \frac{\sum_t \sum_{u\in\mathcal{U}} R_u(t) \Delta t}{\sum_t P^N(t) \Delta t} \quad [\text{bit/J}]
   $$
   This is a global ratio of episode totals, not an average of per-step or per-link ratios.

2. **Surplus Equivalence ($G(x)$):**
   Using the frozen baseline multiplier $\lambda = \mathcal{B}_0^M / \mathcal{E}_0^M$, the linear network surplus:
   $$
   G(x) = \sum_{u\in\mathcal{U}} B_u(x) - \lambda E(x) \quad [\text{bit}]
   $$
   satisfies $\Delta G > 0 \iff \Delta B - \lambda \Delta E > 0$, preserving the exact first-order gradient direction of the true ratio-of-sums $\eta^N$ at operating point $\lambda$.

3. **Active Exact Conservation Identity (Two-Player Current-Slot LC-SRS):**
   The **only active exact conservation identity** in V0.23 is the named two-user current-slot LC-SRS identity over profiles $00, 10, 01, 11$, with local terms $\ell_i$, unilateral rate externalities $e_i$, and joint interaction surplus $\Psi = \Psi_B - \lambda \Psi_E$:
   $$
   z_{3,i} = e_i + \frac{\Psi}{2} \implies \sum_{i=1}^2 (\ell_i + z_{3,i}) = G(11) - G(00) = G(x^c) - G(x^0)
   $$
   - **Status:** Construction-level exact by mathematical definition, bounded strictly to the named two-user current-slot game.
   - **Verification:** Unit test `test_w181` tests this identity on a synthetic fixture (residual $< 10^{-6}$ bit), not on raw simulator traces. Cited authority is contract §5 and `test_w181`.
   - **Historical Note:** The V0.3 three-route bookkeeping decomposition ($\zeta_{1,u} + \zeta_{3,u} + \zeta_{2,u} = g_0 + g_1$ and $D^o/D^t/D^a$ pipeline) is **retired and strictly historical**. It is NOT a current V0.23 method.

4. **Active Route C3 Coalition Structure:**
   Active Route C3 is strictly a **two-user coalition game** evaluated over 4 matched physical profiles ($00, 10, 01, 11$). It is NOT a general unilateral candidate/reference branch. Unilateral candidate/reference branches are strictly restricted to Route C1.

5. **Structural Zero Invariant via Reference-Centering:**
   In the neural network student, applying reference-centering:
   $$
   Q_{3,i}(a) = F_i(a) - F_i(a_i^0)
   $$
   guarantees that $Q_{3,i}(a_i^0) \equiv 0$ identically for all neural network parameters $\theta$, eliminating baseline drift.

6. **Three-Q Independent Architecture Invariant:**
   Exactly three online Q surfaces exist ($Q_1, Q_2, Q_3$). They share no neural parameters, no common backbone, and no gradient pathways.
   - $Q_1$: Active, confirmed marginal contribution in V0.4.
   - $Q_2$: Present in the 3-Q sum as the current **OPS-3 diagnostic/checkpoint**, but **unqualified**. The old V0.7 learner candidate is retired; C2 has zero confirmed efficacy.
   - $Q_3$: Method core frozen under V0.23; offline gate pending; zero episode efficacy claimed.

7. **One-Pass Native Masked Argmax Deployment:**
   At runtime, execution selects:
   $$
   a_u^\star(t) = \arg\max_{a\in\mathcal{A}_u^+(t)} \left[ Q_1(s_u(t), a) + Q_2(s_u(t), a) + Q_3(s_u(t), a) \right]
   $$
   There is no coordinator, auction, voting, joint action decoder, fallback, or post-selection repair.

8. **Software Preflight Binding:**
   The V0.23 implementation is frozen under SHA-256 preflight manifests (`PASS_V023_IMPLEMENTATION_BOUND`), with unit tests passing.

---

## 2. Historical Development Evidence (Strictly Bounded Context)

These findings represent observed empirical data from past development runs, screens, and diagnostic audits. Each is strictly bounded to its cited test conditions:

1. **Route C1 Marginal Indispensability in V0.4 (Five-Arm Ablation):**
   - Result: `FULL` vs. `DROP-C1` = **+254.596%** pooled ratio-of-sums EE.
   - Context: Evaluated in a V0.4 frozen-policy, old-Q2 context as a marginal contribution only.
   - Robustness: Positive in 3/3 initialization lineages and 30/30 physical evaluation worlds.
   - Status: Sealed as `CONFIRM_C1` in `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md`.
   - Strict Boundary: Establishes that $C_1$ is indispensable within the multi-route ensemble. Does not prove the whole policy beats baseline Main. Words like "massive gains" or "confirmed efficacy" are forbidden.

2. **Route C3 in Historical V0.4 Context (Old-Q2, Victim-Burden Formulation):**
   - Confirmatory block: `FULL` vs. `DROP-C3` = **+21.216%** pooled EE (30/30 worlds positive, 2/3 lineages positive), sealed as `CONFIRM_C3`.
   - Five-arm ablation: `FULL` vs. `DROP-C3` = **+21.970%** pooled EE (30/30 worlds positive, 2/3 lineages positive).
   - Context: V0.4 frozen-policy, old-Q2 context, marginal contribution only.
   - Strict Boundary: These results used the retired V0.4 victim-burden formulation and were evaluated in the presence of the old Q2 head. They are distinct preregistered blocks and must NOT be merged or averaged into a single number.

3. **C3 Route-Interaction Vulnerability (V0.4 Diagnostic):**
   - Result: In the absence of Q2, evaluating $Q_1 + Q_3$ vs. $Q_1$ yielded **-10.286%** pooled EE, with all 3 initialization lineages negative.
   - Significance: Demonstrated that C3's positive marginal contribution in V0.4 was fragile and dependent on Q2 context, motivating the V0.23 LC-SRS cooperative redesign.

4. **Route C2 Diagnostic Status & Historical Failures:**
   - V0.6 C2-k1 learner screen: `FULL` vs. `DROP-C2` = **-28.575%** pooled EE (0/3 lineages positive; 0/10 worlds positive; action-flip rate of 76.07%). Sealed as `C2_K1_LEARNER_NOT_CONFIRMED`.
   - V0.7 R14 LOAO audit: In a 12-anchor leave-one-anchor-out test, all 3 Q2 lineages exhibited higher held-out MSE than the state-independent null predictor (0/3 passed). The old V0.7 learner candidate was retired.
   - Current V0.23 Status: C2 contains the current **OPS-3 diagnostic/checkpoint**, present in the 3-Q architecture but **unqualified**. It is neither redesigned nor retired from the software architecture, but has zero empirical efficacy.

5. **Whole-Policy Trailing in V0.4 Five-Arm Ablation:**
   - Result: `FULL` vs. `M0` (frozen Main baseline) = **-21.582%** pooled EE.
   - Cause: The unconfirmed C2 head degraded overall policy actions. Whole-policy superiority is completely unproven.

6. **Retired V0.3 Three-Route Bookkeeping:**
   - The V0.3 additive target $\zeta_{1,u} + \zeta_{3,u} + \zeta_{2,u} = g_0 + g_1$ and $D^o/D^t/D^a$ data pipeline are historical milestones only. They are superseded and NOT part of the active V0.23 method.

---

## 3. Active V0.23 Development Gate Protocol & Arms

The active V0.23 development gate is strictly an offline learnability/observability verification on 8 fresh TRAIN worlds (`2026121705`–`2026121712`). It is separate from the historical/future multi-arm evaluation matrix ($M0, N000, A011, A101, A110, F111$).

### Active Gate Arms (Contract §§11–14)
1. `INFORMED`: The complete C3View student neural network with true relational tokens ($M_i(a)$) and reference-centering.
2. `MATCHED_PLACEBO`: Control arm evaluating whether the student learns genuine spatial-relational structure versus spurious correlations.
3. `ZERO_SURFACE`: Verifies reference-centering ($Q_3(a^0) \equiv 0$) and baseline zero attribution.
4. `TEACHER_ORACLE`: Evaluates the raw two-user Shapley targets $z_{3,i}$ to establish theoretical teacher bounds.

### Gate Passing Criteria (Frozen Contract §§11–14)
- **Closure Pair Quota:** Total closure-eligible pairs across 8 fresh TRAIN worlds must satisfy $N_{\mathrm{p}} \ge 24$.
- **Structural Zero Invariant:** MSE on reference actions ($a^0$) must be identically zero.
- **Statistical Skill:** `INFORMED` must achieve positive skill over `MATCHED_PLACEBO` across unseen worlds.
- **Permutation / Shuffle Degradation:** Token shuffle must degrade MSE, confirming relational reliance.

---

## 4. Scientific Inferences and Hypotheses (Mechanistic Deductions)

These are causal explanations and mechanistic models deduced from domain physics and observed failures:

1. **Beam Thrashing & Power Contention Hypothesis:**
   In dense LEO networks, independent greedy handover choices optimize link SINR at the expense of waking up new satellite beams, each consuming ~15 W base power. Global EE requires penalizing dormant beam ignition ($C_1$) and rewarding joint beam extinction ($C_3$).

2. **Unilateral Exploration Blindspot:**
   When two users share a source beam, neither user exploring a move alone can observe beam shut-off because the beam must remain active for the other user. A unilateral credit assignment mechanism (like standard Q-learning) is fundamentally blind to beam de-allocation savings. Cooperative coalition modeling (LC-SRS) resolves this blindspot.

3. **Sparse Within-State Action Support Mechanism for C2 Failure:**
   In C2 datasets, supervised candidate/reference pairs cover only 1–2 actions per state. At deployment, unconstrained Q2 networks predicted high positive values for unseen actions, causing 76% action-flip rates and corrupting valid C1/C3 decisions.

4. **Detached Reference Context as a Spatial Anchor:**
   Conditioning C3View on the detached profile $a^0 = \arg\max(Q_1 + Q_2)$ provides a stable combinatorial baseline, allowing the relational token model to infer coalition opportunities without executing multi-agent negotiation.

---

## 5. Claims Prohibited Until Closed-Loop Episode Evaluation

The following statements are **strictly forbidden** in all papers, presentations, and reports until a formal multi-episode training run is authorized, executed, and sealed:

| # | Prohibited Claim | Why It Is Forbidden |
|:---|:---|:---|
| 1 | *"Multi-Catfish MCRL improves LEO network energy efficiency over baseline MODQN."* | `FULL` trailed Main by -21.58% in V0.4 due to C2 failure. Full policy superiority is unproven. |
| 2 | *"Route C2 is confirmed, solved, or ready for deployment."* | C2 failed in V0.6 (-28.58%) and V0.7 (0/3 LOAO MSE). C2 contains the current OPS-3 diagnostic/checkpoint, which is present but unqualified. |
| 3 | *"Route C3 / LC-SRS improves episode energy efficiency."* | V0.23 is an offline observability gate on 8 TRAIN worlds; it has NOT run episode rollouts. |
| 4 | *"Passing the V0.23 gate proves that LC-SRS or Multi-Catfish is effective."* | A gate pass proves offline learnability and observability only, NOT closed-loop policy efficacy. |
| 5 | *"Multi-Catfish operates as a multi-agent team or coordinator at runtime."* | Runtime deployment is strictly one decentralized agent taking one masked argmax. |
| 6 | *"Merging C3 confirmatory (+21.2%) and five-arm (+22.0%) into an average result."* | These are distinct frozen-policy blocks evaluated under different preregistrations. |
| 7 | *"Evaluation results on the TEST split."* | TEST split is strictly closed. All V0.23 work is TRAIN-development only. |
| 8 | *"100, 1500, 3000, or 9000 episode training runs have been completed."* | Episode training is halted under launch authority restrictions until C2 is resolved. |
| 9 | *"Sub-millisecond runtime performance achieved."* | Unsupported empirical latency claim; execution timing benchmarks have not been officially sealed. |
| 10 | *"Operating under less-than-10-degree elevation angles."* | The simulation environment enforces minimum operational elevation thresholds ($\ge 10^\circ$). |
| 11 | *"Proving causal learning in reinforcement learning."* | The architecture provides credit decomposition, not a mathematical proof of causal induction. |
| 12 | *"Expanding MCRL as arbitrary expansions."* | The official authorized method name is strictly *Multi-Catfish MCRL*. |

---

## 6. Summary Boundary Verdict

- **Route C1:** `CONFIRMED_MARGINAL` (+254.6% marginal EE in frozen-policy, old-Q2 five-arm ablation).
- **Route C2:** `PRESENT_BUT_UNQUALIFIED_OPS3_DIAGNOSTIC` (mandatory in 3-Q architecture sum, but empirical efficacy is unconfirmed).
- **Route C3:** `METHOD_CORE_FROZEN__GATE_PENDING` (V0.23 LC-SRS mathematically frozen; offline gate authorized on server; zero episode efficacy claimed).
- **Overall System:** `DEVELOPMENT_GATE_PHASE` (Authorized strictly for V0.23 development gate; no episode training or full-method efficacy claimed).
