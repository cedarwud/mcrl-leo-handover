**The strongest candidate is JSRL (Jump-Start RL, Uchendu et al., arXiv:2204.02372, ICML 2023), and constraint 5 decides it: JSRL is the only screened method that never puts the demonstrator's action into any loss term, so it needs no assumption whatsoever about whether the demonstrator's actions are good under the learner's reward — it needs only that the demonstrator's state visitation covers the optimum's (Assumption 4.2), and the paper states in terms that a policy satisfying it "may be far from optimal due to the wrong choice of actions in each step."**

---

Author: literature-screening agent, 2026-09-11. Read-only; no training, no server jobs.
Scope: the **wider** learn-from-suboptimal-data family. The demonstration-seeding subfamily (DQfD, R2D3, DDPGfD, POfD, SIL, ZPD, BERS, Nair's Q-filter, InfoGAIL/Triple-GAIL) was screened in `.scratch/dqfd-grounding/DQFD-FAMILY-GROUNDING-2026-09-11.md` and its findings are **taken as given, not re-derived**.

Convention: **[STATED]** = the cited paper says this. **[INFERRED]** = my reading, not in any paper. **[NOT FOUND]** = searched, no published support located.

Codebase facts used for delta costing were read directly from this repo and are marked **[CODE]**:
`src/mcrl/algorithms/modqn.py` — `update()` at L511 (one buffer, `for obj_idx in range(3)`, 1-step target `r + γ·max_a' Q_target(s',a')` with `q_next_all[~nm] = -1e9`, three separate optimizers); `_scalarize_q_values()` at L261 (fixed linear `w0·Q0+w1·Q1+w2·Q2`); `_select_masked_greedy_action()` at L291; the rollout loop at L1143–1168 with a **single** `select_actions(...)` call at L1162. `src/mcrl/runtime/replay_buffer.py` — 156 lines, plain uniform deque buffer.

---

## 0. A factual correction that changes the question

The predicted failure mode was stated as a property of "the DQfD route". Two independent screening passes converged on the same correction, and the prior audit's own §1.2/§5 text agrees with it:

- **DQfD has no Q-filter.** Its supervised term `J_E(Q) = max_a[Q(s,a) + l(a_E,a)] − Q(s,a_E)` is applied with a **fixed** `λ₂ = 1.0` to every demonstration transition and is gated on nothing [STATED, arXiv:1704.03732, Supplementary; confirmed verbatim in the prior audit §1.1 and §5]. It cannot "permanently disable" itself. When the Bellman operator pushes another action above `a_E`, `J_E` becomes **more** positive and pushes back harder. DQfD's real failure under a misaligned demonstrator is a **persistent bias term fighting the TD term at a fixed weight**, not unlearning.
- **The Q-filter is Nair et al., arXiv:1709.10089, Eq. 8**: `L_BC = Σ‖π(sᵢ)−aᵢ‖²·1[Q(sᵢ,aᵢ) > Q(sᵢ,π(sᵢ))]`, and it is a **DDPG / continuous-action** method. The authors present the self-disabling as a *feature*: [STATED] "Filtering by Q-value gives a natural way to anneal the effect of the demonstrations as it **automatically disables the BC loss** when a better action is found."

So the reviewer's mechanism describes a **DQfD + Q-filter hybrid**, which is what §"What this says the design should be" item 3 of the prior audit proposed, not published DQfD. This matters for the screen because it separates two different things a candidate can be judged on:

- **Failure mode A (persistent misaligned anchor):** an ungated imitation term keeps pulling toward a wrong-objective action forever. DQfD, TD3+BC.
- **Failure mode B (silent no-op):** a value-gated imitation term switches itself off because the learner's own reward says the demonstrator is worse — so the method degenerates to plain DQN and the demonstrations bought nothing. Q-filter, CRR-binary, MARWIL/AWR/AWAC/IQL-AWR (softened), QDagger, Cal-QL.

**[INFERRED] For this problem, B is the near-certain outcome of every value-gated method, and it is not really a "failure" — it is the correct answer to a badly posed question.** If the demonstrator is worse on the deployed scalar, then any gate scored on the deployed scalar *should* turn it off. The published evidence that this is the shape is direct: Grigsby & Qi (arXiv:2110.04698) name it for binary advantage filters — [STATED] "we may be entirely disregarding a large portion of each minibatch" when advantage estimates cluster near zero. The consequence for the thesis is that **a value-gated method cannot produce a positive result here, only a null one**, and a null there is uninformative.

A useful piece of counter-evidence to file alongside the prior audit's ordering: **Ape-X DQfD (Pohlen et al., arXiv:1805.11593)** applies the imitation loss only to the *best* expert episode and its ablation says [STATED] "just removing the imitation loss does not have a significant effect on the algorithm's performance." That **disagrees with DQfD's own Figure 2**, which calls the supervised loss the single largest lever. Both are Atari, both discrete. Report the disagreement; do not resolve it.

---

## 1. Screening table

Verdicts are against the eight constraints as given. "VIABLE WITH PORT" = the mechanism survives but no published instance matches our setting, so we would be the first instance and would carry the risk.

### 1a. Offline / conservative RL

| Paper | Verdict | Deciding constraint |
|---|---|---|
| **CQL**, Kumar et al., arXiv:2006.04779 (discrete variant §6 + App. F, QR-DQN base, Atari) | **DISQUALIFIED** | **5**. The conservative penalty has no gate and enters the *fixed point* directly (Thm 3.1: `Q̂^π = Q^π − α[(I−γP^π)^{-1} μ/π̂_β]`), and Thm 3.4 is explicitly **gap-expanding**: it widens the Q-gap between in-distribution and OOD actions. Under a wrong-objective demonstrator the actions that are good on the deployed scalar *are* the OOD actions, so CQL actively suppresses exactly what we want to learn. Transformed failure: not unlearning — **forbidden to exceed the demonstrator**. |
| **discrete BCQ**, Fujimoto et al., arXiv:1910.01708 §4 | **DISQUALIFIED** | **5**. `π(s)=argmax_{a | G_ω(a|s)/max_{a'}G_ω(a'|s) > τ} Q(s,a)`, with the **same mask on the target argmax**. `G_ω` is trained by cross-entropy on data actions and never sees the reward, so failure mode B is structurally impossible — but the mask is then a **permanent hard lock onto the wrong objective's support**, unaffected by any amount of new environment data. [STATED] "setting τ=0 returns Q-learning and τ=1 returns an imitator of the actions contained in the batch" — there is no usable middle setting, and the threshold is *relative* (`τ·max G`), so a near-deterministic demonstrator collapses any τ>0 to near-imitation. |
| **IQL**, Kostrikov et al., arXiv:2110.06169 (discrete D-IQL only in arXiv:2303.15810 App. D, via d3rlpy) | **DISQUALIFIED** | **5** (and **2**). Value side (Eq. 5/6 expectile) has no disableable term — the constraint lives inside the backup. Policy side (Eq. 7 AWR, `exp(β(Q−V))`) **is** the softened Q-filter using the learner's own Q → failure mode B, graded rather than binary. Harder ceiling: `V` is an expectile over **data actions**, so offline IQL cannot exceed the best action present in the demonstration set. Also needs a policy head in discrete (d3rlpy uses a stochastic head). |
| **TD3+BC**, arXiv:2106.06860 | **DISQUALIFIED** | **1**. Continuous only; `−(π(s)−a)²` needs a metric on actions, undefined for 28 unordered masked actions. Also failure mode A: the BC term is unconditional and λ only normalises Q scale. |
| **BRAC** arXiv:1911.11361; **ReBRAC** arXiv:2305.09836; **AWAC** arXiv:2006.09359; **Cal-QL** arXiv:2303.05479 | **DISQUALIFIED** | **1** (no discrete variant) and **2** (all actor-critic). Cal-QL additionally: its `V^μ` floor is measured on the **learner's** reward, so a wrong-objective demonstrator gives a low floor, the `max()` never binds, and it degenerates to CQL [INFERRED from Eq. 5.1]. Cal-QL's own diagnosis is worth quoting anyway — [STATED] conservative methods "tend to **unlearn the policy initialization** learned from offline data." |
| **Decision Transformer** arXiv:2106.01345 (discrete Atari §4.1); **Trajectory Transformer** arXiv:2106.02039 | **DISQUALIFIED** | **2** and **5**. Not value-based at all; conditioning is on return-to-go computed with the **learner's** scalar, so a demonstrator good on another objective has low RTG and conditioning on a high target return is pure extrapolation. TT states it outright: [STATED] RTGs "are functions of the *behavior* policy that collected the training data." Neither has an online loop (ODT arXiv:2202.05607 is continuous). |
| **Hy-Q (Hybrid RL)**, Song, Zhou, Sekhari, Bagnell, Krishnamurthy & Sun, ICLR 2023, arXiv:2210.06718 | **VIABLE** | Survives 1, 2, 5, 7, 8. Value-based Q-learning/iteration, **no actor**, offline dataset **and** online interaction in the same fitted-Q regression, discrete (Montezuma's Revenge), **no conservatism term at all**. [STATED] efficient "whenever the offline dataset supports a high-quality policy" and "we require **no** assumptions on the coverage provided by the initial distribution." The assumption is the thing to test, not a blocker on its face. |
| **Scaled QL** arXiv:2211.15144; **REM** arXiv:1907.04543 | noted, not shortlisted | Discrete Atari, online fine-tunable, but Scaled QL is a CQL variant and inherits CQL's constraint-5 problem. |
| **PrefID / Policy-regularized Offline MORL**, Lin, Yu, Liu & Wu, arXiv:2401.02244 | **DISQUALIFIED as a method; essential as a citation** | **2** (needs an actor) and it is **offline-only**. But it is the published **name** for our situation. Abstract, verbatim (verified by fetch): "such methods face a new challenge in offline MORL settings, namely the **preference-inconsistent demonstration problem**. We propose two solutions to this problem: 1) filtering out preference-inconsistent demonstrations via approximating behavior preferences, and 2) adopting regularization techniques with high policy expressiveness." Its diagnosis locates the damage in the **behaviour-cloning term** — which is the prior audit's conclusion arrived at independently. |

**[NOT FOUND] across all twelve offline methods: any multi-head / vector-Q variant.** Twin critics and ensembles are multiple estimates of one scalar, not multiple objectives. The vector-valued offline work is a separate line (arXiv:2401.02244; MO-DT arXiv:2308.16379; arXiv:2512.08012), all continuous and all offline.

### 1b. Advantage-weighted / filtered BC

| Paper | Verdict | Deciding constraint |
|---|---|---|
| **CRR**, Wang et al., NeurIPS 2020, arXiv:2006.15134 | **DISQUALIFIED** | **1** and **2**. Objective `argmax_π E_{(s,a)~B}[f(Q_θ,π,s,a)·log π(a|s)]`, `f = 1[Â>0]` (binary) or `exp(Â/β)` (exp), `Â_mean` over `m=4` sampled actions. **All experiments are continuous control; no discrete action space is tested** [STATED]. Requires a **separate actor network** (Fig. 3), and the CWP inference variant needs multiple action samples at test time — a further constraint-8 problem. |
| — *and on the reason CRR was flagged* | | **It does not avoid the predicted failure mode.** CRR-binary's `1[Â>0]` is the Q-filter with the learner's own critic; CRR-exp only replaces the hard indicator with a smooth exponential decay that is never exactly zero. Same direction, softer slope — **failure mode B, graded**. This is the single cleanest negative result of the screen, and the published confirmation is Grigsby & Qi, arXiv:2110.04698: binary advantage filters hit an **effective-batch-size** collapse when advantages cluster near zero, [STATED] "we may be entirely disregarding a large portion of each minibatch." |
| **AWR**, Peng et al., arXiv:1910.00177 | **DISQUALIFIED** | **2**. Discrete **is** supported (LunarLander-v2) [STATED], but it needs actor + critic; and `exp((1/β)(R−V(s)))` is again the learner's own advantage → failure mode B. |
| **MARWIL**, Wang et al., NeurIPS 2018 | **DISQUALIFIED** | **2**, **5**. Discrete supported (RLlib `Discrete`); `β=0` reduces to plain BC. Uses the **behaviour-policy** advantage `A^{π_β}=Q^{π_β}−V^{π_β}` — but still under the learner's reward, so the ranking is the same. Its guarantee is monotone improvement **over the behaviour policy**, which here is a guarantee to beat something already worse than the learner. |
| **ABM**, Siegel et al., arXiv:2002.08396 | **DISQUALIFIED**; strongest citation in this family | **1**, **2**. Continuous only, needs actor + MPO. But it is the one paper here that names the problem: [STATED] the dataset may contain "behavioral trajectories from different policies ... which solve different tasks, or the same task in different ways ... **that are not necessarily aligned with the target task**." Filter `f = 1₊`, i.e. the same step function → same mode-B behaviour. |

### 1c. Guide-policy / curriculum bootstrapping

| Paper | Verdict | Deciding constraint |
|---|---|---|
| **JSRL**, Uchendu et al., arXiv:2204.02372, ICML 2023 (PMLR v202:34556) | **VIABLE WITH PORT** | Passes 2, 3, 5, 6, 7, 8 cleanly. Port is on **1**: [NOT FOUND] any published discrete-action JSRL instance — all experiments are continuous (IQL on D4RL AntMaze/Adroit; QT-Opt vision grasping). See §2. |
| **RAJS (Random Annealing Jump Start)**, arXiv:2407.15083 | supporting evidence for JSRL | Guide horizon upper bound annealed to zero on a performance metric; guide is a prior feedback controller with **8%** success, final agent **97%** [STATED]. Evidence that a weak and differently-designed guide still pays. |
| **SPIBB / SPIBB-DQN**, Laroche, Trichelair & Tachet des Combes, arXiv:1712.06924, ICML 2019 | **DISQUALIFIED** | **8**. Discrete, value-based, no imitation loss — the closest near-miss. But `π_b` appears inside the Bellman target (Eq. 9) and `π_spibb` reproduces `π_b` pointwise on bootstrapped `(x,a)`, so the baseline policy **and a pseudo-count model must ship to inference**. Also its safety guarantee is "no worse than `π_b`", which points the wrong way when `π_b` is worse on the deployed scalar; and it is batch-only. |
| **Kickstarting**, arXiv:1803.03835 | **DISQUALIFIED** | **2**. `H(π_T‖π_S)` cross-entropy needs an explicit policy distribution; learner is IMPALA. `λ_k` is tuned online by PBT, not hand-set [STATED]. |
| **THOR**, arXiv:1805.11240 | **DISQUALIFIED** | **2**, **5**. The second method here with no action-matching loss (it uses potential-based shaping `c' = c + γΦ(s')−Φ(s)`, `Φ = V̂^e`), but `Φ` must be the expert's value function **for the same cost**. Ours is not. Learner is policy-gradient. |
| **Distral** arXiv:1707.04175; **Policy Distillation** arXiv:1511.06295; **Actor-Mimic** arXiv:1511.06342 | **DISQUALIFIED** | **5**. All write action-matching losses; Policy Distillation and Actor-Mimic have **no reward term at all** — they copy the guide. Actor-Mimic reaches only 27.5% of its expert on Seaquest [STATED]. |
| **DAgger** arXiv:1011.0686; **AggreVaTe(D)** arXiv:1406.5979 / arXiv:1703.01030 | **DISQUALIFIED** | **5**. DAgger has no reward signal and a bound `J(π̂) ≤ J(π*) + uTε_N` tied to the expert — structurally cannot exceed it. AggreVaTe needs the expert's **cost-to-go `Q*`** under our reward, which we do not have. |
| **LOKI** arXiv:1805.10413 | **DISQUALIFIED** | **1**. Continuous only (TRPO). |

### 1d. Constrained RL

This family is **orthogonal** to learn-from-suboptimal-data — with two exceptions it assumes no demonstrations at all. It is screened here because constraint 6 needs an answer and constraint 5 has a constraint-shaped component (the demonstrator violates the handover cap).

| Paper | Verdict | Deciding constraint |
|---|---|---|
| **Deep Constrained Q-learning ("Constrained DQN")**, Kalweit, Huegle, Werling & Boedecker, arXiv:2003.09398 | **VIABLE** | Passes 1, 2, 3, 7, 8. Discrete, value-based, off-policy; constraints enforced by restricting the action set **inside the Q-update**, both at behaviour selection and at the **target argmax** — no Lagrange multiplier, therefore no on-policy estimate, therefore no conflict with replay. The paper is itself the published argument that masking beats reward shaping and Lagrangian methods, because the latter give [STATED] "no guarantees that the agent satisfies the constraints at all points in time." **[CODE]** the repo already masks at both points (`q_next_all[~nm] = -1e9` at L548; `_select_masked_greedy_action` at L291), so this is a change of *what goes in the mask*, not of machinery. |
| **BFTQ / Budgeted MDP**, Carrara et al., NeurIPS 2019, arXiv:1903.01004 | **VIABLE WITH PORT** | Discrete, fitted-Q, off-policy, **`Q=(Q_r,Q_c)` as two heads in one network** — the only published precedent for a multi-head *constrained* Q. But the budget enters the state and the greedy step is a convex-hull/LP over the frontier that **mixes two actions**, which is a deviation from per-user argmax (constraint 8) and ~200–400 lines. |
| **Sauté RL**, Sootla et al., arXiv:2202.06558, ICML 2022; and arXiv:2301.11592 (AAAI 2024) | **VIABLE**, as a component | [STATED] the Saute MDP "satisfies the Bellman equation" — the principled answer to "a reward penalty is not Markov w.r.t. the original state". arXiv:2301.11592 gives [STATED] "an **equivalent** unconstrained formulation ... with an **augmented state space** and reward penalties". ~30–60 lines (one extra state dimension for remaining handover budget). |
| **RCPO**, Tessler et al., arXiv:1805.11074 | **DISQUALIFIED** | **2**, **3**. Scalarises to `r̂ = r − λc` with a **single** critic (destroys the three-head structure), and [STATED] "λ is still optimized using **Monte-Carlo sampling on the original constraint**" — on-policy, which breaks replay-based training. |
| **CPO** arXiv:1705.10528; **PPO-Lag / TRPO-Lag** arXiv:1910.01708 | **DISQUALIFIED** | **2**. On-policy actor-critic policy search; [NOT FOUND] any value-based variant. |
| **Safety layer** arXiv:1801.08757 | **DISQUALIFIED** | **1**. Title is *Continuous* Action Spaces; the closed-form correction linearises in the action, which 28 unordered actions do not admit. |
| **Shielding**, Alshiekh et al., AAAI 2018, arXiv:1708.08611; **invalid action masking**, arXiv:2006.14171 | supporting citations | The published warrant for treating masking as the constraint mechanism in discrete RL. The shield [STATED] "provides a **list of safe actions**". |
| **Suttle et al., ICML 2021, PMLR 139:9989–9999, "RL for Cost-Aware MDPs"** | noted | Value-based two-timescale RVI Q-learning whose objective is the **ratio of long-run average reward to long-run average cost**, with tabular a.s. convergence. Ratio **without** additional CMDP constraints. |
| **Off-policy Primal-Dual Safe RL**, arXiv:2401.14758, ICLR 2024 | warning | [STATED] off-policy cost values are **systematically underestimated**, causing constraint violation. The known pathology of buffer-based λ. |
| **Deep Inverse Q-learning with Constraints**, Kalweit et al., NeurIPS 2020, arXiv:2008.01712 | **DISQUALIFIED as a method; important as a precedent** | It is an *inverse* method (it infers the reward), and ours is known. But it is the closest published statement of our constraint-5/6 shape: [STATED] "including constraints directly in IQL leads to **optimal constrained imitation from unconstrained demonstrations**" — the demonstrator is not bound by the learner's constraint set, and the constraint is imposed by restricting the max in the Bellman update. Discrete, value-based, SUMO. |
| **Accelerating Safe RL with Constraint-mismatched Policies**, Yang, Rosca, Narasimhan & Ramadge, ICML 2021, arXiv:2006.11645 | **DISQUALIFIED as a method; important as a precedent** | **2** (trust-region policy search, continuous). But the problem statement is ours verbatim: [STATED] the baseline policy "may be sub-optimal for the task at hand, and is **not guaranteed to satisfy the specified constraints**." |
| ICL / constraint inference: Scobee & Sastry arXiv:1909.05477; Malik et al. arXiv:2011.09999; CoCoRL arXiv:2305.16147 | **DISQUALIFIED** | Direction reversed. These **infer** constraints from demonstrations that are assumed **feasible**; CoCoRL [STATED] tolerates sub-optimal but not unsafe demonstrations. We know the constraint and know the demonstrator violates it. |
| **Altman, *Constrained Markov Decision Processes*, 1999** | structural caveat | CMDP optima are in general **stochastic**, randomising in at most L states for L constraints. A DQN greedy argmax is deterministic, so the exact CMDP optimum may lie outside our policy class [STATED for CMDP theory; [INFERRED] for the DQN implication]. BFTQ's two-action hull mixture is the engineering response to exactly this. |

### 1e. Multi-objective RL

| Paper | Verdict | Deciding constraint |
|---|---|---|
| **SF & GPI**, Barreto et al., NeurIPS 2017 arXiv:1606.05312; ICML 2018 arXiv:1901.10964; PNAS 2020 doi:10.1073/pnas.1907370117; **SF-DQN** arXiv:2405.15920 | **VIABLE WITH PORT** | Passes 1, 2, 3, 5, 8. Fails **4** on its face and is repaired only via §3d. See §2. |
| **Envelope Q-learning**, Yang, Sun & Narasimhan, NeurIPS 2019, arXiv:1908.08342 | **DISQUALIFIED** | **3**, **4**. Discrete and DQN-based, but a **single** network outputs `|A|×m`, the preference ω is a network **input**, and the homotopy schedule `∇L = (1−λ)∇L_A + λ∇L_B` is a single loss — incompatible with three heads and three optimizers. Title is "with **linear** preferences"; ratio utility [NOT FOUND]. |
| **PD-MORL**, Basaklar, Gumussoy & Ogras, ICLR 2023, arXiv:2208.07914 | **DISQUALIFIED** | **3**, **4**. A discrete variant does exist (MO-DDQN-HER on Deep Sea Treasure / Fruit Tree) [STATED], but it is again one preference-conditioned universal network with linear scalarisation plus a cosine/angle alignment term. |
| **CAPQL**, Lu, Herman & Yu, **ICLR 2023, OpenReview `TjEzIsyEsQ6`** | **DISQUALIFIED** | **1**, **2**. SAC-based, continuous only. **Correction: [NOT FOUND] any arXiv id for this paper** — arXiv full-text search for "concave-augmented Pareto Q-learning" returns zero, and an author search for Haoye Lu does not list it. Cite the OpenReview id, not an arXiv id. Its theory is still worth citing: the value range of stationary policies in a discounted MDP is **convex**, so linear scalarisation suffices to reach the whole Pareto front — *when the objective is itself linear*. |
| **Pareto Q-learning**, Van Moffaert & Nowé, JMLR 15:3483–3512 (2014) | **DISQUALIFIED** | **7**. The only family that never scalarises during learning, so a ratio utility can legitimately be applied at selection time — but it is **tabular**, maintaining a non-dominated vector set per `(s,a)`. [NOT FOUND] an authoritative deep variant from the original authors. Infeasible at our state-space size [INFERRED]. |
| **GPI-LS / GPI-PD**, Alegre et al., AAMAS 2023, arXiv:2301.07784 | **DISQUALIFIED** | **3**, **4**. Preference-conditioned `Q_θ(s,a,w)`, linear utility `u(v^π,w)=v^π·w`. |
| **Multi-objective DQN (DOL)**, Mossalam et al., arXiv:1610.02707 | **DISQUALIFIED** | **4**. Vector output, single optimizer, linear only, outer loop retrains per w. |
| Demonstration-guided MORL 2024–2026: arXiv:2409.09958, arXiv:2408.15501, arXiv:2401.02244, arXiv:2305.00567 (PEDA/D4MORL), arXiv:2512.08012 | **DISQUALIFIED** | **2** and offline-only, uniformly. |

### 1f. Replay mechanics

| Paper | Verdict | Deciding constraint |
|---|---|---|
| **QDagger / Reincarnating RL**, Agarwal et al., NeurIPS 2022, arXiv:2206.01626 | **DISQUALIFIED — predictable no-op** | **5**. Structurally the best fit in the whole screen (discrete, DQN/QR-DQN/Rainbow, Atari, single buffer, no PER, no IS weights) and its `L_QDagger = L_TD + λ_t·E_{s~D}[Σ_a π_T(a|s) log π(a|s)]` costs perhaps 40–80 lines. But `λ_t = 1_{t<t₀}·max(1 − G^π/G^{π_T}, 0)` is measured on the **deployed scalar** for both student and teacher. Our teacher is **worse on the deployed scalar**, so `1 − G^π/G^{π_T} ≤ 0` from essentially the first evaluation, `λ_t` clamps to zero, and QDagger degenerates to plain DQN. Failure mode B in its purest form, and here it is **predictable in advance without running anything**. [STATED] `t₀` = 6M of a 10M-frame budget; the original `L_TD` is n-step, though CleanRL's `qdagger_dqn_atari_*` is 1-step. |
| **ZPD teaching**, Seita et al., arXiv:1910.12154 | noted | The **only** published demonstration-ratio anneal: fixed 50% blend until the student beats all teacher snapshots, then [STATED] "anneal `f_blend`, in a linear decay towards no teacher samples". Same deployed-return criterion as QDagger's `λ_t`, so the same objection applies. |
| **PER**, Schaul et al., arXiv:1511.05952 | **DISQUALIFIED** | **5**. Needs a sum-tree and per-sample IS weights (~50 lines by LAP's own count). **[INFERRED] It systematically over-samples reward-misaligned demonstration transitions**, because their Bellman residual does not converge — it spends learning capacity on exactly the data the learner most disagrees with, which is a feature when objectives align and a bug when they do not. Nearest published warnings: PER itself ("sensitive to noise spikes ... exacerbated by bootstrapping"); LAP's corollary that MSE+PER "will be minimized by some expression which **may favor outliers**" (arXiv:2007.06049); DisCor's argument for **down**-weighting high-target-error transitions (arXiv:2003.07305). **[NOT FOUND] no paper names this pathology.** Note it compounds with DQfD's structural over-sampling (`ε_d=1.0` vs `ε_a=0.001`). |
| **LAP / PAL**, Fujimoto, Meger & Precup, arXiv:2007.06049 | **VIABLE**, as a cheap component | PAL keeps uniform sampling and changes only the loss shape — no sum-tree, no IS weights, [STATED] "can be added to any deep RL algorithm in only a few lines of code". If any non-uniformity is wanted, this is the one to use. |
| **DisCor**, arXiv:2003.07305 | **DISQUALIFIED** | **7**. Right direction, but it costs an extra network `Δ_φ(s,a)` and its own optimizer. |
| **ERE** arXiv:1906.04009; **CER** arXiv:1712.01275; **Attentive ER** AAAI 2020; **Selective ER** AAAI 2018 | not shortlisted | ERE has no discrete/DQN instance; CER is near-neutral; Attentive ER is *designed* to filter out off-distribution states, i.e. it would actively remove the demonstrations. |
| — demonstration retention generally | — | **[NOT FOUND]** any paper on **evicting** demonstrations, and **[NOT FOUND]** any formal curriculum over the demonstration ratio beyond ZPD's linear anneal. R2D3's ratio is a fixed hyperparameter and [STATED] "must be carefully tuned"; no follow-up anneals it. |

### 1g. Ratio objective (added — nothing in the brief's list addresses constraint 4)

| Paper | Verdict | Deciding constraint |
|---|---|---|
| **Fractional Deep RL for Age-Minimal MEC**, Jin, Tang, Zhang & Wang, arXiv:2312.10418v2 | **VIABLE** | Directly on constraint 4. Objective is a **ratio of expected sums**; Dinkelbach outer loop makes the inner MDP reward `c = c_N − γ·c_D`; the parameter updates as `γ_{i+1} = N_i(s₀,a_i)/D_i(s₀,a_i)`; **Theorem 1** gives **linear convergence** of `γ_i → γ*`. **The inner solver is a discrete, value-based D3QN** (a DDPG is used only for a separate continuous sub-action). [STATED] minimising an instantaneous ratio "is [not] equivalent to minimizing [the] time-average ratio". |
| **Sharpe Ratio Optimization in MDPs**, arXiv:2509.00793 | supporting | [STATED] "**dynamic programming does not work for fractional objectives**." Dinkelbach's transform converts it; the fixed-point property is that at `λ = λ*` the transformed problem and the ratio problem share an optimal policy. |
| **Asynchronous Fractional Multi-Agent DRL**, arXiv:2409.16832 | supporting | Extends Dinkelbach, shows equivalence to inexact Newton, linear convergence rate. |
| **Non-Cumulative Objectives**, Nägele et al., arXiv:2405.13609 | alternative | A general **NCMDP → standard MDP** mapping for objectives `f(r₁,…,r_T)`, explicitly including ratio forms ("their mean divided by their standard deviation"); costs state augmentation rather than an outer loop. |
| **Vamplew, Watkins, Foale & Dazeley, arXiv:2402.06266** | **read before anything else** | [STATED, verbatim] "This paper investigates two previously unreported issues which can hinder the performance of value-based MORL algorithms **when applied in conjunction with a non-linear utility function** — value function interference, and sensitivity to overestimation." Value-based + vector Q + non-linear utility is exactly our configuration. **[INFERRED] The failure modes it describes do not show on a training curve.** |

---

## 2. Ranked shortlist (four)

### #1 — JSRL / JSRL-Random (arXiv:2204.02372, ICML 2023; RAJS arXiv:2407.15083)

**Mechanism.** Roll the guide policy `π^g` for the first `h` steps of each episode, hand over to the learner `π^e` for the remaining `H−h`, put the whole trajectory in the buffer, train `π^e` normally, then decrease `h`. JSRL-Curriculum gates the decrease on an evaluation; JSRL-Random samples `h` uniformly each episode with no gate.

**What it would require here.** **[CODE]** the rollout loop is `for ep ... for _step_idx in range(steps_per_episode): actions = self.select_actions(...)` at modqn.py L1160–1167 — a single call site. The delta is: a guide-policy wrapper exposing `(states, masks) → actions`; an `h` schedule; a branch at L1162; and plumbing `guide_policy` / `h_schedule` through `train()` and `training_pipeline.py`. **`update()` is not touched at all. The three heads, three optimizers, the buffer, the masking and the deployed argmax are all unchanged.**
**~60–110 lines** across `modqn.py`, `training_pipeline.py`, a new `guide_policy.py`, plus tests.

**Multi-head structure:** preserved exactly. JSRL is agnostic to what the learner's update is.

**Ratio objective:** **neutral.** JSRL changes the state distribution the learner trains on and nothing else; it neither helps nor hurts the SER/ratio mismatch, which remains whatever it was. Compose with #4 if you want that fixed.

**Does the predicted failure mode apply? No — structurally.** JSRL's loss is *only* the learner's TD loss. The guide never appears in any objective. Q-learning's target is `max_{a'} Q(s',a')`, not `Q(s', π^g(s'))`, so guide transitions are ordinary off-policy samples and the fixed point on the covered support remains the learner's own `Q*`. There is no term to disable and no anchor to unlearn. **[INFERRED] This is the discriminator: compare JSRL's objective with DQfD's `J(Q)=J_DQ+λ₁J_n+λ₂J_E+λ₃J_L2` — JSRL has no `J_E`-shaped term at all.**

**Its own failure modes, which are different and must be pre-declared:**
1. **Coverage failure (`C → ∞` in Assumption 4.2).** [STATED] the theorem needs `sup_{s,h} d_h^{π*}(φ(s))/d_h^{π^g}(φ(s)) ≤ C`, where `π*` is optimal for **our composite reward**. If the EE-optimal guide systematically never enters states the composite optimum occupies, `C` diverges and Theorem 4.3 is vacuous — and in practice `π^e` is simply never trained there. The symptom is a flat curve, not a decaying one.
2. **Curriculum gate stall.** Algorithm 1's gate evaluates the **combined** policy, whose first `h` steps are the guide. If the guide is bad on the deployed scalar, the combined return never reaches `β`, `h` never decreases, and the whole budget burns on a degenerate curriculum. **Mitigation: use JSRL-Random**, which has no gate — [STATED] "we sample each `h` uniformly and independently".
3. **Handover-budget contamination (our problem specifically, [INFERRED]).** The guide runs at 0.7117 handovers/user-step. If the composite reward or the handover cap depends on an episode-accumulated handover count, that count must be in the state (or the MDP is not Markov), and once it is, `π^e` trains from start states whose budget was spent in a way that never occurs at deployment. Train/test mismatch in the wrong direction.
4. **Exploration blind spot at the head of the episode.** ε-greedy only fires after step `h`. If the EE-optimal and composite-optimal actions diverge mainly at the *start* of the episode — which is plausible when the first serving-satellite choice determines the whole handover chain — JSRL learns that part last, only once `h→0`, i.e. once the guide has stopped helping.
5. [STATED, Limitations] "The presence of adversarial guide-policies might result in learning that is even slower than random exploration."

**Precondition:** JSRL needs a **queryable** guide policy, not a logged dataset. If the EE demonstrator exists only as frozen transitions, JSRL is not applicable and #3 is the fallback.

### #2 — Successor Features + GPI (arXiv:1606.05312; arXiv:1901.10964; PNAS 2020; SF-DQN arXiv:2405.15920)

**Why it is here.** It is the only published framework in the entire screen that treats "a policy optimal for exactly one reward component" as a **first-class object**. PNAS 2020 instantiates base policies as [STATED] "π₁ and π₂ as solutions to the tasks w₁=[1,0]ᵀ and w₂=[0,1]ᵀ" — one-hot per component, which is our demonstrator. And it reuses the demonstrator's **value function**, never its actions:

- GPI (Thm 1, arXiv:1606.05312): with `|Q^{π_i} − Q̃^{π_i}| ≤ ε`, `π(s) ∈ argmax_a max_i Q̃^{π_i}(s,a)` gives `Q^π(s,a) ≥ max_i Q^{π_i}(s,a) − 2ε/(1−γ)`.
- Transfer bound (Thm 2): `Q*_i(s,a) − Q^π_i(s,a) ≤ (2/(1−γ))[φ_max·min_j‖w_i−w_j‖ + ε]`.

**What it would require here.** **[CODE]** the three heads are *almost* successor features already — `φ = (r1_system_ee_contribution, r2_handover, r3_load_balance)` and `w = config.objective_weights` give `r = φᵀw` exactly for the *current* linear scalarisation. But **[INFERRED, from modqn.py L546–549] the three heads are NOT `ψ^π`**: each bootstraps with its **own** argmax (`q_next_all.max(dim=1)` per objective), so head *i* approximates `Q*_i`, the optimum of objective *i* alone, and `Σ_i w_i Q*_i` is **not** `Q*` of the scalarised reward. Making them successor features means bootstrapping **every** head at the argmax of the **scalarised** next-state Q — a change of two lines in `update()` that would make `Σ_i w_i ψ_i = Q^π` of the scalarised reward exactly. **This is a finding about the existing code independent of any candidate, and it is worth acting on either way.**
Then: a second `ψ^{π_demo}` network (3 outputs per action), trained by **policy evaluation** on demonstrator rollouts (no max), and a GPI selection rule `argmax_{a valid} max(wᵀψ^{learner}(s,a), wᵀψ^{demo}(s,a))`.
**~220–320 lines** across `modqn.py`, a new `successor_features.py`, the evaluation path and tests.

**Multi-head structure:** best fit of anything screened — it is the only framework whose native object *is* a vector of per-objective values.

**Ratio objective:** **this is where it fails on its face.** SF requires `r = φ(s,a,s')ᵀw` with a fixed `w`. `Σbits/Σjoules` is not `Σγᵗφᵀw` for any fixed `w`. [STATED, arXiv:2608.25723] "the SFs framework is equivalent to MORL under linear utility functions", and that paper's own fix is MONES — a **policy-search** method, not value-based GPI. **The bridge is #4: at a fixed Dinkelbach `λ`, `E[bits] − λ·E[joules]` IS a linear scalarisation with `w(λ) = (1, −λ)`,** so SF&GPI is legal at every fixed λ and `w` simply tracks λ.

**Does the predicted failure mode apply? No — and the transformed one is benign.** There is no loss term referencing the demonstrator's actions, so nothing can be disabled. What happens instead: when `wᵀψ^{demo}(s,a) < wᵀψ^{learner}(s,a)` everywhere, GPI just never selects the demonstrator's branch. That is **failure mode B again — a no-op** — but with a property none of the gated methods have: **Theorem 1 guarantees the GPI policy is no worse than the best library member**, so the no-op is provably harmless rather than merely probably harmless. With one library member, Theorem 2's bound is vacuous unless `w ≈ w_demo` [INFERRED, direct consequence of `min_j‖w−w_j‖`].

**Constraint-8 cost:** GPI keeps per-user argmax and needs no coordinator, but it does keep `ψ^{demo}` resident at inference — one extra forward pass. That is a deviation from "one agent", not from "no coordinator".

### #3 — Hy-Q, Hybrid RL (Song, Zhou, Sekhari, Bagnell, Krishnamurthy & Sun, ICLR 2023, arXiv:2210.06718)

**Why it is here.** It is the closest published thing to "value-based, discrete, online learning seeded by a fixed dataset, with **no conservatism term and no imitation term**". Abstract, verbatim (verified by fetch): value-based Q-learning/iteration adapted to the hybrid setting; efficient "whenever the offline dataset supports a high-quality policy and the environment has bounded bilinear rank"; "we require **no** assumptions on the coverage provided by the initial distribution"; outperforms online, offline and hybrid baselines "including Montezuma's Revenge". It is the discrete value-based analogue of the prior audit's "zero-risk option", DDPGfD.

**What it would require here.** A second buffer holding the demonstration transitions, and sampling both in the same update. **[CODE]** `ReplayBuffer` is 156 lines and `update()` calls `self.replay.sample(...)` once — the delta is a `DualReplayBuffer` with a fixed offline/online split and a single changed line in `update()`. **~90–150 lines.** Note this is architecturally what the prior audit's §"2" already endorses (split by *source*: R2D3's two buffers, Nair's `R_D`/`R`) and what the catfish mechanism (i) does badly; Hy-Q is the version with a theorem attached.

**Multi-head structure:** unchanged. **Ratio objective:** neutral, same as #1.

**Failure mode:** none of the gated kind — there is no gate. The risk is entirely in the assumption: **"the offline dataset supports a high-quality policy"** is precisely what a wrong-objective demonstrator may not satisfy. If it does not, Hy-Q's transitions are just extra off-policy data of the wrong distribution — harmless but useless, at a cost in effective batch size. This is a **no-op** too, but a cheap and diagnosable one.

**Named alternative in this slot:** **NAC — Gao, Xu, Lin, Yu, Levine & Darrell, "Reinforcement Learning from Imperfect Demonstrations", ICML 2018, arXiv:1802.05313.** Single Q network, no actor; `V_Q(s)=α log Σ_a exp(Q/α)`, `π_Q(a|s)=exp((Q−V_Q)/α)`; **discrete only in its experiments** (Toy Minecraft 4 actions, TORCS 9, GTA V 7); a pre-training phase on demonstrations then environment interaction with [STATED] "the same objective" in both phases and **no imitation loss**. Its robustness mechanism is the extra `−∇_θ V_Q(s)` term, which [STATED] "reduces the Q-values of actions that were not observed along the demonstrations" — note this is the *opposite* direction from what we want when the demonstrations are off-objective, so it is a worse fit than Hy-Q despite being older and better-matched on action space. [STATED] the paper does **not** discuss demonstrations collected under a different reward.

### #4 — Dinkelbach / fractional outer loop (arXiv:2312.10418v2; arXiv:2509.00793)

**Not a learn-from-suboptimal-data method.** It is on the shortlist because constraint 4 has no other answer and because it composes with all three above.

**Mechanism.** Replace the per-step reward used for training with `c = c_N − λ·c_D` — for us, `bits − λ·joules` — hold λ fixed for an inner training round, then set `λ ← N/D` measured on that round's rollouts. [STATED] Theorem 1 gives linear convergence `λ_i → λ*`; at `λ*` the transformed problem and the ratio problem share an optimal policy (arXiv:2509.00793).

**What it would require here.** **[CODE]** `reward_vector_from_step_result()` at modqn.py L590 already returns the three components separately, and `_scalarize_q_values()` at L261 already takes a weight row. The delta is: (a) expose the bits and joules accumulators per episode, (b) a λ state variable and its update between rounds, (c) recombine the EE reward column as `bits − λ·joules` instead of the pre-formed `r1_system_ee_contribution`, (d) the outer loop in `training_pipeline.py`. **~120–200 lines.**

**Multi-head structure:** preserved — λ changes the *weights*, not the architecture. This is the cheapest of the four in architectural terms.

**Caveat to declare before running:** three rounds of Dinkelbach means three training runs, so the 1.32 h budget becomes ~4 h. Still not binding.

**Read first:** arXiv:2402.06266. Value-based + vector Q + non-linear utility is the exact configuration it reports silent failures for.

---

## 3. The single strongest candidate, and the one experiment that settles it

**JSRL-Random**, for the reason in the opening sentence: among everything screened it is the only method that makes **no claim of any kind** about whether the demonstrator's actions are good under our reward. Every other survivor either uses the demonstrator's value function under our reward (SF&GPI — safe, but then it needs `r=φᵀw`, which our ratio endpoint breaks), or uses its transitions under our reward (Hy-Q — safe, but then it needs the dataset to "support a high-quality policy", which is the thing in doubt). JSRL asks for one thing only, and it is a thing an EE expert in the *same environment* plausibly has: **state coverage**.

Use **JSRL-Random, not JSRL-Curriculum**: the curriculum gate evaluates the *combined* policy on the deployed scalar, and a guide that is worse on the deployed scalar can stall the gate permanently at `h = H`. JSRL-Random has no gate.

### The cheap kill screen — **no training required**

Run the **guide-horizon sweep on the already-trained learner**. For `h ∈ {0,1,2,…,10}`, roll the EE demonstrator for the first `h` steps of each episode and the current trained learner for the remaining `10−h`, over the standard evaluation seed set, and record three things per `h`:

1. **Pooled EE** (bits/joules, the deployed endpoint) of the combined policy.
2. **Handover rate** of the combined policy — this quantifies failure mode 3 directly: if the budget is spent by step `h`, `π^e` is being trained from start states that never occur at deployment.
3. **New-state coverage**: the fraction of the states visited after step `h` that the learner alone (`h=0`) never visits. This is the only empirical proxy for Assumption 4.2's `C`.

**Decision rule, declared before running:**
- **Kill JSRL** if (3) is flat in `h` — the guide adds no states the learner does not already reach, so `d^{π^g}` contributes nothing and JSRL's entire mechanism is inert. This is the expected outcome if the EE expert and the learner occupy the same region of state space.
- **Kill JSRL** if (2) shows the handover budget is exhausted by small `h`, unless the budget is reset at the handover point — in which case that reset must be pre-declared as a reward/state change and version-stamped as a successor.
- **Proceed** only if (3) is increasing in `h` **and** (1) at some `h>0` is not catastrophically below `h=0`.

**Cost:** 11 evaluation sweeps with no gradient steps. At the measured evaluation cost this is minutes, not hours. **[INFERRED] It is strictly cheaper than any training-based screen and it tests the one assumption JSRL actually makes** — which is the property the prior audit says is missing from every demonstration method it examined: an assumption that can be checked before committing.

A second, even cheaper probe worth running alongside: **the divergence-time distribution** — over the evaluation set, at each step index `t ∈ {0..9}`, the fraction of users where the demonstrator's action differs from the learner's greedy action. If divergence concentrates at small `t`, JSRL's blind spot (failure mode 4) lands exactly where the decisions matter, and the expected speed-up goes to zero. The existing oracle/marginals probes can produce this without new machinery.

---

## 4. What the published evidence does NOT cover

Stated plainly, because the gap is itself the answer.

**4.1 The exact configuration has no published method.** **[NOT FOUND]** any peer-reviewed method that combines all of: (a) a demonstrator optimal for a *different* objective than the learner's, (b) a **ratio-of-pooled-sums** endpoint, (c) a **discrete, action-masked** action space, (d) a **multi-head** value-based learner with per-objective optimizers, (e) **online** interaction rather than a fixed dataset. Every located paper satisfies at most three of the five. This was checked family by family across ~six independent search programmes and is consistent with the prior audit's §5.4 finding for the narrower demonstration-seeding family.

**4.2 The problem does have a published name, but only in the offline actor-critic setting.** `arXiv:2401.02244` calls it the **preference-inconsistent demonstration (PrefID) problem** and locates the damage in the behaviour-cloning term. That is the citation to use when stating the problem. It is **not** a citation for any method we can run: it is offline-only, policy-regularized (needs an actor), and continuous.

**4.3 No published method for a one-component demonstrator in value-based MORL.** The nearest structural precedent is SF&GPI, whose PNAS 2020 exposition uses one-hot component tasks `w₁=[1,0]`, `w₂=[0,1]` — but SF&GPI **predates the demonstration-guided MORL literature entirely and does not present itself as one**, and its linearity requirement is violated by our endpoint. Everything published *as* demonstration-guided MORL (DG-MORL arXiv:2404.03997, de Heuvel arXiv:2404.04857, MODULI arXiv:2408.15501, PEDA arXiv:2305.00567, arXiv:2409.09958, arXiv:2512.08012) is either offline, or actor-based, or assumes a generalist demonstrator.

**4.4 Ratio objectives are solved, but not jointly with anything else we need.** Dinkelbach + value-based RL for a ratio of expected sums is published and has a convergence theorem (arXiv:2312.10418). Ratio of long-run averages with a value-based method is published (Suttle et al., ICML 2021). **[NOT FOUND]** any work combining a ratio objective **with** CMDP constraints **and** a discrete value-based learner, and **[NOT FOUND]** any discussion of ratio/fractional utilities in the MORL utility literature at all — Hayes et al. (arXiv:2103.09568) treat only linear and monotonically-increasing utilities.

**4.5 Nobody has studied what a misaligned subset does to prioritised replay.** [INFERRED] TD-error prioritisation should over-sample exactly the transitions the learner's reward disagrees with. The nearest published statements are about *noise*, *outliers*, *sparse rewards* and *stale priorities* (PER arXiv:1511.05952; LAP arXiv:2007.06049; DisCor arXiv:2003.07305; arXiv:2007.09569). **[NOT FOUND]** the misaligned-demonstration case by name. If this is claimed in the thesis it has to be demonstrated, not cited.

**4.6 Nobody publishes demonstration eviction, and only one paper anneals the ratio.** [NOT FOUND] for eviction; ZPD (arXiv:1910.12154) is the sole ratio anneal, and its criterion is the deployed return — the same criterion that makes QDagger a no-op here.

**4.7 No published MORL architecture uses three independent optimizers, one per objective.** Every method examined uses a single optimizer over a vector output or a preference-conditioned single network. **[NOT FOUND]** — so the existing architecture itself has no published counterpart, which bears on what can be claimed about it. Related and more urgent: **[INFERRED, from modqn.py L546–549] the three heads bootstrap with per-head argmaxes, so `Σ_i w_i Q_i` is not the Q-function of the scalarised reward.** Under SF theory the correct object is `ψ^π` — all heads evaluated under one common policy. This is independent of which candidate is chosen.

**4.8 The warning that applies regardless of choice.** Vamplew et al., arXiv:2402.06266, report **value function interference** and **overestimation sensitivity** as problems that arise specifically [STATED] "when applied in conjunction with a non-linear utility function" in value-based MORL. That is our configuration exactly, and the paper's premise is that these were **previously unreported** — i.e. the field has been running this configuration without knowing. Read it before committing to any of the four.

**4.9 What this means for the thesis claim.** The honest framing is not "we applied method X from the literature". It is: *the published learn-from-suboptimal-data literature assumes the demonstrator is a noisy or under-trained version of a policy optimising the learner's own objective; where it relaxes that, it does so offline, or in continuous control, or with an actor. For a demonstrator that is optimal for a different objective, under a ratio endpoint, in a masked discrete multi-head DQN, there is no method to apply and no result to inherit.* That is a defensible contribution statement and a much stronger one than a borrowed method with a null result.

---

## 5. Where papers disagree (reported, not adjudicated)

1. **Is a supervised imitation term an asset?** DQfD (arXiv:1704.03732, Fig. 2): "critical to good performance", its removal is the worst ablation. **Ape-X DQfD** (arXiv:1805.11593), same family, same domain: [STATED] "just removing the imitation loss does not have a significant effect on the algorithm's performance." Both Atari, both discrete. Unresolved.
2. **Should offline value pre-training precede online RL?** Cal-QL (arXiv:2303.05479) and Scaled QL (arXiv:2211.15144) say yes, with a calibration fix. **Rainbow-DemoRL** (arXiv:2603.27400, ManiSkill, continuous): [STATED] "complex offline RL value pretraining often **slows down** online adaptation due to the sample overhead required for critic recalibration", recommending simple BC initialisation plus replay prefilling. Different domains; unresolved.
3. **Does linear scalarisation suffice?** CAPQL (ICLR 2023, OpenReview `TjEzIsyEsQ6`) proves the stationary-policy value range is convex in discounted MDPs, so linear scalarisation reaches the whole Pareto front. Shah & Jeewa (arXiv:2511.16476) report empirically that scalarisation's success depends heavily on Pareto-front shape and often fails to retain discovered solutions, preferring inner-loop multi-policy algorithms. The reconciliation is that CAPQL's theorem is about a *linear* objective; ours is not.
4. **Does prioritisation help or hurt?** PER prioritises **up** by TD error; DisCor prioritises **down** by estimated target error. Both published, opposite directions, no head-to-head on a misaligned-data regime.

---

## 6. Corrections to carry forward

- **CAPQL has no arXiv id.** Cite Lu, Herman & Yu, *Multi-Objective Reinforcement Learning: Convexity, Stationarity and Pareto Optimality*, **ICLR 2023, OpenReview `TjEzIsyEsQ6`**. An arXiv full-text search for the algorithm name returns zero results.
- **The predicted failure mode is not DQfD's.** See §0. It is Nair et al.'s Q-filter (arXiv:1709.10089, DDPG, continuous) attached to DQfD's `J_E`.
- **`arXiv:2412.07322` is not an offline-to-online survey** (it is a program-search paper unrelated to RL); the intended reference may be arXiv:2412.07762.
- **D-IQL's discrete action selection is unconfirmed** — arXiv:2303.15810 App. D says only "based on d3rlpy", and d3rlpy PR #404 discusses a stochastic policy head. Verify against code before citing.
- Full-text access failed for: Roijers et al. JAIR 2013 (arXiv:1402.0590) SER/ESR definitions — use Hayes et al. arXiv:2103.09568 and Roijers, Steckelmacher & Nowé, ALA@AAMAS 2018 instead; the offline-RL surveys arXiv:2203.01387 and arXiv:2005.01643; Trajectory Transformer Appendix F (secondary only).

---

## Sources

Verified by direct fetch during this screen:
arXiv:2006.15134 (CRR) · arXiv:1910.00177 (AWR) · arXiv:2002.08396 (ABM) · arXiv:2110.04698 (AFBC) · arXiv:1802.05313 (NAC) · arXiv:2204.02372 (JSRL, quotes taken verbatim from ar5iv) · arXiv:2407.15083 (RAJS) · arXiv:2312.10418v2 (Fractional Deep RL) · arXiv:2509.00793 (Sharpe-ratio MDP) · arXiv:2409.16832 · arXiv:1606.05312 (Successor Features) · arXiv:2210.06718 (Hy-Q) · arXiv:2401.02244 (PrefID)

Verified by the delegated screening passes (arXiv/ar5iv/PMLR/OpenReview text, quotes as extracted):
arXiv:2006.04779 (CQL) · arXiv:1910.01708 (discrete BCQ) · arXiv:1812.02900 (BCQ) · arXiv:2110.06169 (IQL) · arXiv:2303.15810 (D-IQL) · arXiv:2106.06860 (TD3+BC) · arXiv:1911.11361 (BRAC) · arXiv:2305.09836 (ReBRAC) · arXiv:2106.01345 (DT) · arXiv:2106.02039 (TT) · arXiv:2006.09359 (AWAC) · arXiv:2303.05479 (Cal-QL) · arXiv:2211.15144 (Scaled QL) · arXiv:1907.04543 (REM) · arXiv:2206.01626 (QDagger) · arXiv:1805.11593 (Ape-X DQfD) · arXiv:1803.03835 (Kickstarting) · arXiv:1707.04175 (Distral) · arXiv:1511.06295 (Policy Distillation) · arXiv:1511.06342 (Actor-Mimic) · arXiv:1805.10413 (LOKI) · arXiv:1805.11240 (THOR) · arXiv:1011.0686 (DAgger) · arXiv:1406.5979 / arXiv:1703.01030 (AggreVaTe) · arXiv:1712.06924 (SPIBB) · arXiv:1705.10528 (CPO) · arXiv:1805.11074 (RCPO) · arXiv:1910.01708 (Safety Gym) · arXiv:1903.01004 (BFTQ) · arXiv:2003.09398 (Constrained DQN) · arXiv:2008.01712 (Deep Inverse Q-learning with Constraints) · arXiv:1805.07708 / arXiv:1901.10031 (Lyapunov) · arXiv:1801.08757 (safety layer) · arXiv:1708.08611 (shielding) · arXiv:2006.14171 (action masking) · arXiv:2202.06558 (Sauté) · arXiv:2301.11592 · arXiv:2006.11645 · arXiv:2312.10385 · arXiv:1909.05477 · arXiv:2305.16147 · arXiv:2401.14758 · arXiv:2002.03016 · arXiv:1706.04208 (HRA) · Suttle et al. PMLR 139:9989–9999 · arXiv:1908.08342 (Envelope) · JMLR 15:3483–3512 (Pareto Q) · arXiv:2208.07914 (PD-MORL) · OpenReview `TjEzIsyEsQ6` (CAPQL) · arXiv:1901.10964 · PNAS 2020 doi:10.1073/pnas.1907370117 · arXiv:2405.15920 (SF-DQN) · arXiv:2301.07784 (GPI-LS/PD) · arXiv:1610.02707 (DOL) · arXiv:2103.09568 (Hayes et al.) · arXiv:2402.06266 (value-based MORL issues) · arXiv:2511.16476 · arXiv:2608.25723 · arXiv:2105.14127 · arXiv:2405.13609 (NCMDP) · arXiv:2405.11331 · arXiv:1511.05952 (PER) · arXiv:2007.06049 (LAP/PAL) · arXiv:2003.07305 (DisCor) · arXiv:1906.04009 (ERE) · arXiv:1712.01275 (CER) · AAAI 2020 Attentive ER · AAAI 2018 Selective ER · arXiv:1910.12154 (ZPD) · arXiv:2007.09569 · arXiv:2510.01460 · arXiv:2605.12379 (DRIFT) · arXiv:2603.27400 (Rainbow-DemoRL) · arXiv:2409.09958 · arXiv:2408.15501 · arXiv:2305.00567 · arXiv:2512.08012

Taken as given, not re-derived:
`.scratch/dqfd-grounding/DQFD-FAMILY-GROUNDING-2026-09-11.md` and every source in it.
