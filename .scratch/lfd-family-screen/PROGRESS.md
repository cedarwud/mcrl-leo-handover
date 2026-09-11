# LFDSCREEN progress

Task: screen the wider "learn from suboptimal data" family against the 8 hard constraints.
Output file: `.scratch/lfd-family-screen/LFD-FAMILY-SCREEN-2026-09-11.md`
Prior audit (given, not redone): `.scratch/dqfd-grounding/DQFD-FAMILY-GROUNDING-2026-09-11.md`

## Families

| # | Family | Status |
|---|---|---|
| 0 | Read prior DQfD audit | DONE |
| 1 | Offline / conservative RL (CQL, IQL, TD3+BC, AWAC, BCQ, discrete BCQ, BRAC, ReBRAC, DT) | DONE |
| 2 | Advantage-weighted / filtered BC (CRR, AWR, MARWIL, ABM) | DONE (self) |
| 3 | Guide-policy / curriculum (JSRL, Kickstarting, Distral, distillation, LOKI/THOR, DAgger) | DONE (delegated, returned) |
| 4 | Constrained RL (CPO, RCPO, Lagrangian value-based, safety layer, discrete constrained) | DONE |
| 5 | Multi-objective RL (envelope Q, Pareto Q, PD-MORL, CAPQL, GPI, demo-guided MORL) | DONE |
| 6 | Replay mechanics (PER, LAP, DisCor, demonstration retention, QDagger) | DONE |
| 7 | Ratio objective / fractional programming RL (Dinkelbach, average-reward, CMDP-ratio) | DONE (self) |
| 8 | Write report | DONE |

## Notes from family 2 (self, verified by fetch)
- CRR (Wang et al., NeurIPS 2020, arXiv:2006.15134): objective `argmax_pi E_{(s,a)~B}[ f(Q_theta,pi,s,a) log pi(a|s) ]`;
  f = 1[Â>0] (binary) or exp(Â/beta) (exp); Â_mean uses m=4 sampled actions. **All experiments continuous control;
  no discrete action space tested.** Requires a SEPARATE actor network (Fig 3). CWP inference variant needs
  multiple action samples at test time.
- AWR (Peng et al., arXiv:1910.00177): `argmax_pi E[log pi(a|s) exp((1/beta)(R - V(s)))]`. **Discrete supported**
  (LunarLander-v2). Needs actor + critic.
- MARWIL (Wang et al., NeurIPS 2018): exp(beta*A) weighted imitation; advantage is A^{pi_beta} = Q^{pi_beta} - V^{pi_beta}
  (BEHAVIOUR-policy advantage, not learner's). Discrete supported (RLlib Discrete(2)); beta=0 reduces to plain BC.
- ABM (Siegel et al., arXiv:2002.08396): filter f = 1_+ step function; continuous only; needs actor + MPO.
  **Explicitly addresses data from "policies which solve different tasks ... not necessarily aligned with the target task"** — closest
  stated match to constraint 5 in this family.
- AFBC closer-look (Grigsby & Qi, arXiv:2110.04698): binary advantage filters have an **effective-batch-size**
  failure — "we may be entirely disregarding a large portion of each minibatch" when advantages cluster near zero.
  This is the transformed form of the reviewer's predicted failure mode: not unlearning, but NO SIGNAL.

## Notes from family 7 (self, verified by fetch)
- Sharpe Ratio Optimization in MDPs (arXiv:2509.00793): [STATED] "dynamic programming does not work for
  fractional objectives". Dinkelbach transform -> parametric linear subproblem.
- **Fractional Deep RL for Age-Minimal MEC (Jin, Tang, Zhang, Wang, arXiv:2312.10418v2)** — DIRECT HIT.
  Objective is a ratio of expected sums. Dinkelbach outer loop: inner MDP reward `c = c_N - gamma * c_D`;
  gamma update `gamma_{i+1} = N_i(s0,a_i)/D_i(s0,a_i)`. Theorem 1: linear convergence of gamma_i -> gamma*.
  **Inner solver is a DISCRETE, VALUE-BASED D3QN** (plus DDPG for a continuous sub-action).
  Quote: minimising instant ratio "is [not] equivalent to minimizing [the] time-average ratio".
- Extension: arXiv:2409.16832 (asynchronous fractional multi-agent DRL), Dinkelbach == inexact Newton, linear rate.

## Extra find (self) — NAC, the discrete value-based "no imitation loss" option
- Gao, Xu, Lin, Yu, Levine, Darrell, *RL from Imperfect Demonstrations* (NAC), ICML 2018, arXiv:1802.05313.
  Single Q-network, no separate actor. V_Q(s)=alpha*log sum_a exp(Q/alpha); pi_Q(a|s)=exp((Q-V_Q)/alpha).
  **Discrete action spaces only in experiments**: Toy Minecraft (4 actions), TORCS (9), GTA V (7).
  Pre-training on demos for k steps, then environment interaction, **same objective in both phases, no imitation loss**.
  Mechanism for imperfect demos: the extra -grad V_Q(s) term "reduces the Q-values of actions that were not
  observed along the demonstrations"; "does not force [the agent] to mimic all of the examples in the dataset".
  [STATED] Paper does NOT discuss demonstrations collected under a different reward.
- SQIL (arXiv:1905.11108) — replaces the reward with r=1 on demo transitions; pure imitation -> disqualified on constraint 5.

## Notes from family 3 (delegated, returned)
- **JSRL** (Uchendu et al., arXiv:2204.02372, ICML 2023 / PMLR v202:34556) is the ONLY method in this family with
  NO imitation/action-matching loss. Guide policy rolls the first h steps; learner takes over; h decreases on a
  curriculum gate. TrainPolicy is explicitly instantiable as "a Deep Q-Network ... with epsilon-greedy" [STATED].
  Assumption 4.2 is a state-COVERAGE condition sup d^{pi*}/d^{pi^g} <= C, and the paper states verbatim
  "A policy that satisfies Assumption 4.2 may be far from optimal due to the wrong choice of actions in each step."
  Theorem 4.3: suboptimality O(C H^{5/2} S^{1/2} A / T^{1/2}) for tabular (finite S,A). Guide is TRAINING-ONLY.
  [NOT FOUND] no published DISCRETE-action JSRL instance — all experiments are continuous (IQL AntMaze/Adroit, QT-Opt).
  Cross-objective guide WAS tested: indiscriminate-grasping guide used for instance grasping, "slightly worse than
  using the instance guide ... both JSRL versions are much better than vanilla QT-Opt".
  JSRL-Random (h sampled uniformly, no gate) is the gate-free variant.
- **SPIBB / SPIBB-DQN** (Laroche et al., arXiv:1712.06924, ICML 2019): discrete, value-based, no imitation loss —
  but pi_b appears in the Bellman target (Eq. 9) and pi_spibb copies pi_b pointwise on bootstrapped (x,a),
  so the baseline policy is needed AT INFERENCE -> fails constraint 8. Its safety guarantee is "no worse than pi_b",
  which is the wrong direction when pi_b is worse on the deployed scalar.
- Kickstarting (1803.03835) needs a policy head (IMPALA); Distral, Policy Distillation, Actor-Mimic, DAgger,
  AggreVaTe all write action-matching losses or have bounds tied to the expert. LOKI continuous-only.
  THOR (1805.11240) is the second no-action-matching method but uses Phi = V^e of the SAME cost, and is policy-gradient.
- **FACTUAL CORRECTION the agent raised**: DQfD has NO Q-filter. Its J_E is unconditional with fixed lambda2=1.0.
  The Q-filter is Nair et al. arXiv:1709.10089 (DDPG, continuous). So the reviewer's "the Q-filter permanently
  disables the supervised loss" mechanism applies to a DQfD+Q-filter HYBRID, not to published DQfD.

## Notes from family 4 (delegated, returned)
- **Deep Constrained Q-learning** (Kalweit, Huegle, Werling, Boedecker, arXiv:2003.09398): "Constrained DQN",
  DISCRETE + VALUE-BASED + OFF-POLICY. Constraints enforced by restricting the action set inside the Q-update
  (both behaviour selection and the target argmax) — NO Lagrange multiplier. Paper explicitly argues masking beats
  reward shaping and Lagrangian because the latter give "no guarantees that the agent satisfies the constraints at
  all points in time". Delta ~20-40 lines for single-step constraints; +1 truncated value head per multi-step constraint.
- **Deep Inverse Q-learning with Constraints** (Kalweit et al., NeurIPS 2020, arXiv:2008.01712): [STATED]
  "including constraints directly in IQL leads to **optimal constrained imitation from unconstrained demonstrations**".
  Discrete, value-based, SUMO lane-change. Structurally isomorphic to our demonstrator-violates-the-cap case —
  BUT it is an INVERSE method (infers the reward), and our reward is known.
- **BFTQ / Budgeted MDP** (Carrara et al., NeurIPS 2019, arXiv:1903.01004): discrete, fitted-Q, off-policy;
  Q=(Q_r,Q_c) two heads in ONE network — a published precedent for a multi-head constrained Q. No lambda;
  budget goes into the state; greedy step is a convex-hull/LP over the frontier (mixes TWO actions) -> ~200-400 lines.
- **RCPO** (arXiv:1805.11074): scalarises to r - lambda*c with a SINGLE critic (incompatible with the 3-head structure),
  and [STATED] "lambda is still optimized using Monte-Carlo sampling on the original constraint" — on-policy,
  which breaks replay-based training. CPO/PPO-Lag/TRPO-Lag are on-policy actor-critic -> disqualified on constraint 2.
- **Sauté RL** (arXiv:2202.06558, ICML 2022): budget into state; [STATED] the Saute MDP "satisfies the Bellman equation" —
  the principled answer to "a reward penalty is non-Markov w.r.t. the original state". ~30-60 lines.
  Same idea in arXiv:2301.11592 (AAAI 2024), "an equivalent unconstrained formulation ... with an augmented state space".
- **Suttle et al., ICML 2021, PMLR 139:9989-9999, "RL for Cost-Aware MDPs"**: objective is the RATIO of long-run
  average reward to long-run average cost; two-timescale RVI Q-learning, tabular a.s. convergence. Value-based.
  Ratio + CMDP constraints + discrete value-based together = [NOT FOUND].
- **Altman (1999) CMDP theory**: optimal CMDP policies are in general STOCHASTIC (randomise in at most L states for
  L constraints). A DQN greedy argmax is deterministic -> the exact CMDP optimum may lie outside our policy class.
- Lagrangian penalty and the Bellman fixed point: no paper found that refutes Lagrangian penalties via
  Ng/Harada/Russell 1999 directly [NOT FOUND], but RCPO itself calls -lambda*c a "guiding penalty" and needs an
  extra assumption; the state-augmentation papers exist precisely because a reward penalty alone is not equivalent.
- Constraint-mismatched baseline policy: **Yang, Rosca, Narasimhan, Ramadge, ICML 2021, arXiv:2006.11645** —
  baseline "may be sub-optimal for the task at hand, and is not guaranteed to satisfy the specified constraints".
  Policy-gradient / trust-region, continuous; no value-based variant [NOT FOUND].

## Notes from family 6 (delegated, returned)
- **QDagger / Reincarnating RL** (Agarwal et al., NeurIPS 2022, arXiv:2206.01626) — best structural fit in this family:
  DISCRETE, VALUE-BASED (DQN / QR-DQN / Impala-CNN Rainbow), Atari 10 games, single buffer, NO PER, NO IS weights.
  Loss: `L_QDagger = L_TD + lambda_t * E_{s~D}[ sum_a pi_T(a|s) log pi(a|s) ]`,
  `lambda_t = 1_{t<t0} * max(1 - G^pi / G^{pi_T}, 0)`; t0 = 6M of a 10M-frame budget ("we wean off the teacher at
  6 million frames"). [STATED] student "outperforms the teacher in 75% of runs"; design intent is to let the student
  "deviate from the suboptimal teacher policy". Original L_TD is n-step; CleanRL's `qdagger_dqn_atari_*` is 1-step.
  **DECISIVE MECHANICAL FINDING**: G^pi and G^{pi_T} are both measured on the DEPLOYED scalar. Our teacher is WORSE
  on the deployed scalar, so 1 - G^pi/G^{pi_T} <= 0 essentially from the first evaluation -> lambda_t clamps to 0 ->
  QDagger degenerates to plain DQN. Predictable NO-OP, not unlearning.
- **ZPD Teaching** (arXiv:1910.12154, DDQN + 9 Atari): the ONLY published demo-ratio anneal — fixed 50% blend until the
  student beats all teacher snapshots, then "anneal f_blend, in a linear decay towards no teacher samples".
  Same deployed-return criterion as QDagger's lambda_t.
- **PER** (arXiv:1511.05952): needs sum-tree + per-sample IS weights; ~50 lines per LAP's own statement.
  [INFERRED] It systematically OVER-samples reward-misaligned demo transitions, because their Bellman residual never
  converges. Nearest published warnings: PER itself ("sensitive to noise spikes ... exacerbated by bootstrapping");
  LAP's corollary that MSE+PER "will be minimized by some expression which may favor outliers"; DisCor argues for
  DOWN-weighting high-target-error transitions. **[NOT FOUND] no paper names the misaligned-demo over-sampling pathology.**
- **PAL** (arXiv:2007.06049): uniform sampling, loss-shape change only, "a few lines of code" — the cheap alternative to PER.
- **DisCor** (arXiv:2003.07305): right direction (down-weight high target error) but costs an extra network + optimizer.
- **[NOT FOUND]** any paper on EVICTING demonstrations, or a formal curriculum over the demonstration ratio.

## Codebase grounding for delta costing (read-only, verified)
- `src/mcrl/algorithms/modqn.py` (1380 lines). `MODQNTrainer`:
  - `update()` at line 511: samples ONE buffer, loops `for obj_idx in range(3)`, per-objective reward column
    `rewards[:, obj_idx]`, 1-step target `r + gamma * max_a' Q_target(s',a')` with `q_next_all[~nm] = -1e9` masking,
    three separate `self.optimizers[obj_idx]`. No n-step, no double-DQN, no PER, no IS weights, no L2, no margin loss.
  - `_scalarize_q_values()` at line 261: fixed linear weights `w0*Q0 + w1*Q1 + w2*Q2`.
  - `_select_masked_greedy_action()` at line 291: masked argmax over the scalarised row.
  - `reward_vector_from_step_result()` at line 590: `[r1_system_ee_contribution, r2_handover, r3_load_balance]`.
  - **Rollout loop at line 1143-1168**: `for ep in ...: for _step_idx in range(steps_per_episode): actions = self.select_actions(...)`.
    A JSRL roll-in is a single branch at line 1162 -> the smallest possible insertion point in this codebase.
- `src/mcrl/runtime/replay_buffer.py` (156 lines): plain deque-style uniform buffer, `push`/`sample`.
- `src/mcrl/runtime/training_pipeline.py` (1524 lines) calls `trainer.train(...)`.

## Self-verified extras (fetched directly)
- JSRL quotes verified first-hand from ar5iv 2204.02372: TrainPolicy example "updating the exploration-policy via a
  Deep Q-Network with epsilon-greedy"; Assumption 4.2 full text; "may be far from optimal"; Theorem 4.3;
  JSRL-Random ("we sample each h uniformly and independently"); "The presence of adversarial guide-policies might
  result in learning that is even slower than random exploration."
  [INFERRED, not stated] the paper does not explicitly say the guide is training-only — but h -> 0 and the deployed
  object is pi^e, so it follows from Algorithm 1.
- RAJS (Rocket Landing Control with Random Annealing Jump Start, arXiv:2407.15083): JSRL follow-up; guide horizon
  upper bound annealed to zero on a performance metric; guide is a prior feedback controller with 8% success,
  final agent 97%. Evidence that a weak / differently-designed guide still works.
- Successor Features (Barreto et al., NeurIPS 2017, arXiv:1606.05312): r = phi(s,a,s')^T w; psi^pi(s,a)=E^pi[sum gamma^i phi];
  Q^pi_w = psi^pi(s,a)^T w. Discrete actions, value-based. SF-DQN convergence/generalisation: arXiv:2405.15920.
- **[INFERRED, from reading modqn.py:546-549] The existing three heads are NOT successor features.** Each head
  bootstraps with its OWN argmax (`q_next_all.max(dim=1)` per objective), so head i approximates Q*_i (optimal for
  objective i alone), and `sum_i w_i Q*_i` is NOT Q* of the scalarised reward. SF theory says the correct object is
  psi^pi — all three heads evaluated under ONE common policy. One-line change (bootstrap every head at the argmax of
  the SCALARISED next-state Q) would make `sum_i w_i psi_i = Q^pi` of the scalarised reward exactly.

## Notes from family 1 (delegated, returned; key items re-verified by me)
Discrete variants published: discrete BCQ (arXiv:1910.01708 §4, Atari); CQL discrete (arXiv:2006.04779 §6 + App. F,
QR-DQN base, Atari); Decision Transformer (arXiv:2106.01345 §4.1, Atari); D-IQL (not the original paper —
arXiv:2303.15810 App. D Table 10, via d3rlpy); Scaled QL (arXiv:2211.15144).
NO discrete variant: TD3+BC, BRAC, ReBRAC, AWAC, Cal-QL, Trajectory Transformer.
**All twelve: [NOT FOUND] any multi-head / vector-Q variant.**

- **discrete BCQ**: `pi(s)=argmax_{a | G_w(a|s)/max_a' G_w(a'|s) > tau} Q(s,a)`, and the SAME mask is applied to the
  target argmax. G_w is trained by cross-entropy on data actions only, never sees the reward -> the reviewer's
  failure mode is structurally impossible. But the mask is then a PERMANENT hard lock on the wrong objective's
  support, unaffected by any amount of new environment data. Paper [STATED]: "setting tau=0 returns Q-learning and
  tau=1 returns an imitator of the actions contained in the batch" — no usable middle ground.
- **CQL**: the penalty has no gate and enters the FIXED POINT (Thm 3.1: Q_hat^pi = Q^pi - alpha[(I-gamma P^pi)^-1 mu/pi_beta]);
  Thm 3.4 gap-expanding actively suppresses OOD actions — which are exactly the actions that are good on the deployed
  scalar. Transformed failure: not unlearning, but being FORBIDDEN to exceed the demonstrator. Also offline-first.
- **IQL**: value side (Eq.5/6 expectile) has no term to disable — the constraint is inside the backup. Policy side
  (Eq.7 AWR, `exp(beta(Q-V))`) IS the softened Q-filter, using the learner's own Q -> graded decay, never exactly zero.
  Ceiling: V is an expectile over DATA actions, so offline IQL cannot exceed the best action present in the data.
- **Cal-QL**: its V^mu floor is measured on the LEARNER's reward, so a wrong-objective demonstrator gives a low floor
  -> the max() is not binding -> degenerates to CQL. Also continuous/actor-critic only.
- **Decision Transformer / Trajectory Transformer**: return-to-go conditioning on the learner's scalar; TT [STATED]
  RTGs "are functions of the *behavior* policy that collected the training data". Offline, no online loop.
- **Ape-X DQfD (arXiv:1805.11593)**: imitation loss applied only to the BEST expert episode, and the ablation says
  [STATED] "just removing the imitation loss does not have a significant effect on the algorithm's performance".
  **This DISAGREES with DQfD's own Fig. 2 ablation** (which calls the supervised loss critical). Report both.
- **Rainbow-DemoRL (arXiv:2603.27400, ManiSkill, continuous)**: [STATED] "complex offline RL value pretraining often
  slows down online adaptation due to the sample overhead required for critic recalibration"; recommends simple BC
  init + replay prefilling.

### Two out-of-list finds that matter most (both re-verified by me)
- **PrefID — "Policy-regularized Offline Multi-Objective RL"** (Lin, Yu, Liu, Wu, arXiv:2401.02244).
  Abstract verbatim (verified): "such methods face a new challenge in offline MORL settings, namely the
  **preference-inconsistent demonstration problem**. We propose two solutions ...: 1) filtering out
  preference-inconsistent demonstrations via approximating behavior preferences, and 2) adopting regularization
  techniques with high policy expressiveness."
  **This is the published NAME for our constraint-5 situation.** But: OFFLINE-only (no online interaction),
  policy-regularized (needs an actor), continuous D4MORL benchmarks. Cite as problem-statement precedent, not as method.
- **Hy-Q — "Hybrid RL: Using Both Offline and Online Data Can Make RL Efficient"** (Song, Zhou, Sekhari, Bagnell,
  Krishnamurthy, Sun; ICLR 2023, arXiv:2210.06718). Abstract verbatim (verified): value-based Q-learning/iteration,
  NO actor; efficient "whenever the offline dataset supports a high-quality policy and the environment has bounded
  bilinear rank"; "we require no assumptions on the coverage provided by the initial distribution"; beats online,
  offline and hybrid baselines "including Montezuma's Revenge" (discrete).
  **Closest published thing to "value-based + discrete + online seeded by a fixed dataset, with NO conservatism term".**
  Its assumption "the offline dataset supports a high-quality policy" is exactly what a wrong-objective demonstrator
  may not satisfy — that is the thing to test.

## Notes from family 5 (delegated, returned; GPI re-verified by me)
- **SF & GPI** (Barreto et al., NeurIPS 2017 arXiv:1606.05312; ICML 2018 arXiv:1901.10964; PNAS 2020
  doi:10.1073/pnas.1907370117; SF-DQN arXiv:2405.15920). Discrete, value-based, epsilon-greedy Q-learning, no actor.
  GPI Thm 1: `pi(s) in argmax_a max_i Qtilde^{pi_i}(s,a)` gives `Q^pi(s,a) >= max_i Q^{pi_i}(s,a) - 2eps/(1-gamma)`.
  Thm 2 transfer bound: `Q*_i - Q^pi_i <= (2/(1-gamma))[phi_max * min_j ||w_i - w_j|| + eps]`.
  **PNAS 2020 explicitly instantiates base policies as solutions to one-hot tasks w1=[1,0], w2=[0,1]** — i.e. a policy
  optimal for exactly ONE reward component. That is the published precedent for our demonstrator.
  Requires `r = phi(s,a,s')^T w` with known task-independent phi, and successor features psi^pi with Q^pi = psi^pi^T w.
  With a single library member the Thm-2 bound is vacuous unless w is close to w_demo [INFERRED].
  [STATED, arXiv:2608.25723] "the SFs framework is equivalent to MORL under linear utility functions" — a ratio
  utility breaks the psi^T w decomposition; that paper's fix is MONES (policy search), NOT value-based GPI.
- **Envelope Q** (arXiv:1908.08342): discrete, DQN-based, but a SINGLE network outputting |A| x m, preference omega as
  a network INPUT, homotopy single-loss — incompatible with three heads + three optimizers. Linear preferences only.
- **PD-MORL** (arXiv:2208.07914): discrete MO-DDQN-HER exists; still preference-conditioned single network, linear.
- **CAPQL**: **[NOT FOUND] no arXiv id** — correct cite is Lu, Herman & Yu, ICLR 2023, OpenReview TjEzIsyEsQ6.
  SAC-based, continuous only. Its theory: stationary-policy value range is convex in discounted MDPs, so linear
  scalarisation suffices to reach the whole Pareto front — when the objective is itself linear.
- **Pareto Q-learning** (JMLR 15:3483-3512, 2014): tabular; the ONLY family that never scalarises during learning,
  so a ratio utility can be applied at selection time. No authoritative deep variant [NOT FOUND].
- **SER vs ESR** (Hayes et al., arXiv:2103.09568, JAAMAS 2022) verbatim: SER `V^pi_u = u(E[sum gamma^t r_t])`,
  ESR `V^pi_u = E[u(sum gamma^t r_t)]`; "For a linear utility function there is no difference ... However, for a
  non-linear utility function the policies learned under SER and ESR are significantly different."
  **[INFERRED] pooled bits / pooled joules = SER with a NON-LINEAR u(x)=x1/x2** (pool first, divide last).
  Good: SER is the field default, no accrued-reward state augmentation needed. Bad: every linear-preference method's
  guarantee (Envelope, PD-MORL, GPI-LS, CAPQL) does not directly apply. Hayes et al. never discuss ratio utilities [NOT FOUND].
- **WARNING to read first**: Vamplew, Watkins, Foale & Dazeley, arXiv:2402.06266, "Issues with Value-Based MORL:
  Value Function Interference and Overestimation Sensitivity" — [STATED] these arise "when applied in conjunction
  with a non-linear utility function". Value-based + vector Q + non-linear utility is exactly our configuration.
- Demonstration-guided MORL 2024-2026: all located work is OFFLINE MORL (arXiv:2409.09958, 2408.15501, 2401.02244,
  2305.00567 PEDA/D4MORL, 2512.08012). **[NOT FOUND]** any method for a demonstrator optimal on one component only,
  reused in a discrete action-masked value-based online MORL learner.
- Ratio-objective cross-check: arXiv:2405.13609 (NCMDP -> standard MDP mapping for non-cumulative objectives such as
  "their mean divided by their standard deviation", via state augmentation) is the alternative to Dinkelbach.

## COMPLETE 2026-09-11
Report written to `.scratch/lfd-family-screen/LFD-FAMILY-SCREEN-2026-09-11.md`.
Verdict: strongest candidate = **JSRL-Random** (arXiv:2204.02372), decided by constraint 5.
Shortlist: 1) JSRL-Random  2) SF&GPI  3) Hy-Q (alt: NAC)  4) Dinkelbach fractional outer loop (orthogonal, for constraint 4).
Kill screen: guide-horizon sweep h in 0..10 on the already-trained learner, no gradient steps — measure pooled EE,
handover rate, and new-state coverage; kill if coverage is flat in h.
