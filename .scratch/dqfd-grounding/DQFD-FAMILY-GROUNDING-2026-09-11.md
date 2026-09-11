**The published evidence supports exactly ONE demonstration stream in ONE permanently-retained buffer with priority-controlled (not fixed-ratio) sampling — no paper in the DQfD family runs more than one demonstration buffer — and the single biggest risk for a demonstrator that is expert on one objective and unmeasured on the others is that DQfD's large-margin supervised loss `J_E` is an unconditional hard anchor to the demonstrator's action, so the learner is pinned to the specialist's r1-optimal action on every state the specialist visited, including states where r2/r3 make that action wrong.**

---

Author: literature-grounding agent, 2026-09-11.
Scope: read-only literature study. Source-paper texts fetched from arXiv/ar5iv/PMLR; numbers quoted are from the papers themselves.
The project's two source papers (the MODQN handover paper and the RIS "catfish"/CDRL paper) were **not** read for this task, per instruction. Section 6 uses only a numeric/mechanism restatement of the RIS paper supplied by the owner (`07-true-catfish-formulas.md`), used as a *statement of what is to be mapped*, never as scientific authority.

Convention used throughout:
- **[STATED]** = the cited paper says this, with location.
- **[INFERRED]** = my reading, not in any paper.
- **[NOT FOUND]** = searched, no published support located.

---

## 1. DQfD itself — Hester et al., AAAI 2018, arXiv:1704.03732

### 1.1 The four loss terms and their weights

**[STATED]** (Method section, "Deep Q-Learning from Demonstrations"):

```
J(Q) = J_DQ(Q) + λ1·J_n(Q) + λ2·J_E(Q) + λ3·J_L2(Q)
```

| Term | What it is | Weight | Value (Supplementary Material) |
|---|---|---|---|
| `J_DQ` | 1-step double Q-learning loss | implicit 1.0 | — (no λ0; it carries weight 1) |
| `J_n` | n-step double Q-learning loss, n = 10 | λ1 | **1.0** |
| `J_E` | supervised large-margin classification loss | λ2 | **1.0** |
| `J_L2` | L2 regularisation on weights **and biases** | λ3 | **1e-5** |

n-step return, forward view, "similar to A3C":
`r_t + γ r_{t+1} + … + γ^{n-1} r_{t+n-1} + max_a γ^n Q(s_{t+n}, a)`, with **n = 10** [STATED, Method + Supplementary].

**Critical asymmetry [STATED]:** "All the losses are applied to the demonstration data in both phases, while the supervised loss is not applied to self-generated data (λ2 = 0)." So `J_E` is active *only* on demonstration transitions — it never fires on the agent's own data.

**[STATED]** L2 exists specifically "to help prevent it from over-fitting on the relatively small demonstration dataset."

### 1.2 The large-margin loss and its margin function

```
J_E(Q) = max_{a∈A} [ Q(s,a) + l(a_E, a) ] − Q(s, a_E)
```

`l(a_E, a) = 0` when `a = a_E`, and **0.8** otherwise [STATED, Supplementary: "Expert margin l(a_E,a) when a ≠ a_E = 0.8"]. Attributed to Piot, Geist & Pietquin 2014a.

**Why it exists [STATED, verbatim]:** "The supervised loss is critical for the pre-training to have any effect. Since the demonstration data is necessarily covering a narrow part of the state space and not taking all possible actions, many state-actions have never been taken and have no data to ground them to realistic values. If we were to pre-train the network with only Q-learning updates towards the max value of the next state, the network would update towards the highest of these ungrounded variables and the network would propagate these values throughout the Q function."

And its effect [STATED, verbatim]: "This loss forces the values of the other actions to be at least a margin lower than the value of the demonstrator's action. Adding this loss grounds the values of the unseen actions to reasonable values, **and makes the greedy policy induced by the value function imitate the demonstrator**." (emphasis added — this sentence is the crux of §3 below.)

The paper is also explicit that `J_E` alone is not enough [STATED]: "If the algorithm pre-trained with only this supervised loss, there would be nothing constraining the values between consecutive states and the Q-network would not satisfy the Bellman equation."

### 1.3 The pre-training phase

**[STATED]** Length: `k = 750,000` mini-batch updates (Supplementary Material).
**[STATED]** What is sampled: "During this pre-training phase, the agent samples mini-batches **from the demonstration data**" — demonstration data only; there is no environment interaction at all during pre-training.
**[STATED]** All four losses are applied during pre-training.
**[STATED]** Goal: "to learn to imitate the demonstrator with a value function that satisfies the Bellman equation so that it can be updated with TD updates once the agent starts interacting with the environment."

### 1.4 Mixing demonstration and self-generated data afterwards

**[STATED]** There is **one** replay buffer `D_replay`, initialised with the demonstration set. The agent adds its own transitions to the same buffer.

**[STATED, verbatim]** "For proportional prioritized sampling, different small positive constants, ε_a and ε_d, are added to the priorities of the agent and demonstration transitions to control the relative sampling of demonstration versus agent data."

Values [STATED, Supplementary]: **ε_a = 0.001, ε_d = 1.0** — a 1000× priority floor advantage for demonstration transitions. Prioritised replay exponent **α = 0.4**; IS exponent **β0 = 0.6** (as in Schaul et al. 2016).

**Is the demo fraction controlled directly? No — it emerges.** [STATED, Discussion, verbatim]: "The ratio of both types of data in each mini-batch is **automatically controlled by a prioritized-replay mechanism**." And the emergent behaviour is measured [STATED, Figure 1 right subplot]: "For the most difficult games like Pitfall and Montezuma's Revenge, the demonstration data is sampled more frequently over time. For most other games, the ratio converges to a near constant" level.

**[INFERRED]** This is the mechanically important point for the design at hand: DQfD does **not** declare a demo fraction. `ε_d/ε_a` sets a floor; TD error sets the rest; the realised fraction is an *output* that the paper plots, not an input it fixes.

### 1.5 Is demonstration data ever evicted?

**No.** [STATED, verbatim]: "Data is added to the replay buffer until it is full, and then the agent starts over-writing old data in that buffer. **However, the agent never over-writes the demonstration data.**" Restated in the six-differences list: "DQfD is given a set of demonstration data, which it **retains in its replay buffer permanently**." Algorithm 1 line: "Store (s,a,r,s′) into D_replay, overwriting oldest **self-generated** transition if over capacity."

### 1.6 Scale of the demonstration set

**[STATED]** 5,574 to 75,472 transitions per game; 3 to 12 episodes per game (Table 2 / Discussion). "DQN and DQfD receive **three orders of magnitude more interaction data** for RL than demonstration data."

---

## 2. The published ablations — what actually matters

DQfD's own ablations are **Figure 2** (Montezuma's Revenge and Q-Bert, four seeds each).

### 2.1 Loss ablations (Figure 2, left subplots)

Arms [STATED]: full DQfD; DQfD with **λ1 = 0** (no n-step TD loss); DQfD with **λ2 = 0** (no supervised loss).

- **λ2 = 0 (no supervised loss)** [STATED, verbatim]: "pre-training without any supervised loss results in a network trained towards ungrounded Q-learning targets and **the agent starts with much lower performance and is slower to improve**."
- **λ1 = 0 (no n-step loss)** [STATED, verbatim]: "Removing the n-step TD loss has **nearly as large an impact on initial performance**, as the n-step TD loss greatly helps in learning from the limited demonstration dataset."
- Figure 2 caption [STATED]: "Removing either loss degrades the performance of the algorithm."

**No numeric effect sizes are given in the text** — the ablation is reported as curves in Figure 2 only. [NOT FOUND: a table of ablation deltas.]

### 2.2 Pre-training / buffer-only ablations (Figure 2, right subplots)

Three published prior algorithms are run as the "what if you drop pre-training or drop the supervised loss" arms [STATED]:

| Arm | What it is (DQfD's own description) | Result |
|---|---|---|
| **RBS** (Lipton et al. 2016) | "PDD DQN with the replay buffer initially full of demonstration data" — seeding only, **no pre-training**, and demo data is **not** kept permanently | worse than DQfD in both games |
| **HER**, Human Experience Replay (Hosu & Rebedea 2016) | "keeps the demonstration data and **mixes demonstration and agent data in each mini-batch**" — no pre-training, **no supervised loss** | worse than DQfD in both games |
| **ADET** (Lakshminarayanan, Ozair & Bengio 2016) | "essentially DQfD with the large margin supervised loss replaced with a **cross-entropy** loss", and no pre-training | worse than DQfD, but much better than RBS/HER |

[STATED, verbatim]: "all three of these approaches are worse than DQfD in both games. **Having a supervised loss is critical to good performance, as both DQfD and ADET perform much better than the other two algorithms.**" All three were given the *same* demonstration data, plus prioritised replay and n-step returns, "to make them as strong a comparison as possible."

[STATED, Discussion, verbatim]: "naively adding (e.g. only pre-training or filling the replay buffer) this small amount of data to a pure deep RL algorithm does not provide similar benefit **and can sometimes be detrimental**."

### 2.3 Headline comparisons

- DQfD > PDD DQN on the first million steps on **41 of 42** games [STATED, Results].
- DQfD > pure supervised imitation in mean score on **39 of 42** games [STATED, Results].
- DQfD out-performs the **best** demonstration episode it was given on **14 of 42** games [STATED, Abstract/Results].
- DQfD out-performs the **worst** demonstration episode on **29 of 42** games [STATED, Results].
- State-of-the-art on 11 games [STATED, Table 1].

**[INFERRED, and important]** 14/42 = the learner beat its demonstrator in one third of games. The margin loss is not a hard ceiling — but neither is escaping it the common case in the original paper.

### 2.4 Ordering of importance, as the papers give it

1. **Supervised loss present at all** — the largest single lever; the two arms lacking it (RBS, HER) are the two worst [STATED, Fig 2 right].
2. **n-step TD** — "nearly as large an impact" as the supervised loss on initial performance [STATED].
3. **Pre-training** — separable and real: ADET has the classification loss but no pre-training and still trails DQfD [STATED].
4. **Margin form (large-margin vs cross-entropy)** — ADET vs DQfD; DQfD wins but the gap is much smaller than the gap to no-supervised-loss [STATED, Fig 2 right]. [INFERRED] the *existence* of a classification term matters far more than which one.

---

## 3. Demonstrator quality — does the margin loss anchor you to a mediocre expert?

### 3.1 Yes, and it is named as a defect by three independent groups

- **POfD** (Kang, Jie & Feng, ICML 2018, PMLR v80) [STATED, Related Work, verbatim]: methods that "require the value of demonstrated state-action pairs to be larger than the others **with a margin** … **would suffer performance decline when only imperfect demo data are given.**" This is a direct, named criticism of the DQfD/Piot margin family.
- **MCPO** (arXiv:1911.07109, "Reinforcement Learning from Imperfect Demonstrations under Soft Expert Guidance") [STATED]: "continuously enforcing such type of rewards during the whole learning phase is problematic if the provided demonstrations are imperfect."
- **Nair et al.** (arXiv:1709.10089, "Overcoming Exploration in Reinforcement Learning with Demonstrations") [STATED]: applying the behaviour-cloning loss directly "prevents the learned policy from improving significantly beyond the demonstration policy."

DQfD's authors do not claim otherwise; they state the loss "makes the greedy policy induced by the value function **imitate the demonstrator**" [STATED, §1.2 above], and they note human demonstrators "may be using information that is not available in the agent's state representation."

### 3.2 The published fixes, and which of them survive an expert that is better on one objective and worse on another

| Fix | Paper | Mechanism | Tolerates a one-objective expert? |
|---|---|---|---|
| **Q-filter** | Nair et al., arXiv:1709.10089 | BC loss gated by an indicator `1[ Q(s_i,a_i) > Q(s_i, π(s_i)) ]` — the imitation term applies **only where the critic says the demo action is better** | **Yes, conditionally.** [INFERRED] With a scalar critic it filters on the *learner's own* objective, so a demo action that is r1-good but r2/r3-bad is filtered out automatically — provided the critic scores the composite objective the learner is actually optimising. With per-head critics the filter must be defined over the scalarisation, which the paper does not do. |
| **No imitation loss at all** | DDPGfD, Vecerik et al., arXiv:1707.08817 | Demonstrations enter only as off-policy transitions (1-step + n-step + L2 on critic and actor); **no BC and no margin term** | **Yes.** [INFERRED] Nothing anchors the policy to demonstrator actions; the demos only supply reward-labelled transitions, which are objective-agnostic. This is the most conservative published option. |
| **Occupancy-measure matching instead of action matching** | POfD, Kang et al. ICML 2018 | `L(π_θ) = −η(π_θ) + λ1 · D_JS(ρ_θ, ρ_E)`, realised as reward reshaping `r′(s,a) = r(s,a) − λ1 log D_w(s,a)` | **Partially.** [STATED] POfD is designed for imperfect demos and beats them; [INFERRED] but the JS term still pulls the *state-action distribution* toward the specialist, so an r1-specialist still biases occupancy. |
| **Soft/trust-region expert constraint** | MCPO, arXiv:1911.07109 | Expert similarity becomes a **constraint** `D[ρ_{π_k} ‖ ρ_{π_E}] ≤ d_k` that is relaxed once satisfied, rather than a permanent penalty | **Yes in principle** [STATED for imperfect experts]; [NOT FOUND] no multi-objective instance. |
| **Self-imitation instead of external imitation** | SIL, Oh et al., ICML 2018, arXiv:1806.05635 | Imitate only your own past trajectories whose return exceeded your value estimate: `(R − V_θ(s))_+`, with replay prioritised by that clipped advantage | **Yes, trivially** — there is no external demonstrator to be misaligned. [INFERRED] The `(·)_+` clip is the generic "filter by return" primitive: never imitate an action whose realised return was not better than what you already expected. |
| **Very small demo fraction** | R2D3, Paine et al., arXiv:1909.01387 | Fixed demo ratio ρ, swept | see §3.3 — the strongest quantitative result in this whole family |

### 3.3 R2D3 — the demo-ratio result, and it points the opposite way from a 30% mix

**[STATED]** R2D3 = Recurrent Replay Distributed DQN from Demonstrations. It keeps **two separate replay buffers** — a demo buffer and an agent buffer — and the learner samples each batch as a mixture, with the **demo ratio ρ** as an explicit hyperparameter (unlike DQfD, where the ratio emerges).

**[STATED, Abstract]:** "we find that the **optimal demo ratio is very small (but non-zero)** across a wide variety of tasks."

**[STATED, §6.2 / Figure 6]:** four demo ratios × six tasks × five seeds = 120 agents. "lower demo ratios consistently outperform the higher demo ratios across the suite of tasks", and "tuning the demo ratio has a **strong effect on the success rate**."

**[STATED, Appendix D.3]:** for Baseball, Navigate Cubes, Push Blocks and Wall Sensor Stack, a demo ratio of **1/256 ≈ 0.39%** worked best.

**[STATED]** ρ = 0 (pure R2D2, no demos) fails completely on these tasks.

**[STATED]** R2D3 does **not** use a DQfD-style large-margin supervised loss; demonstrations enter through the sampled mixture only.

**[INFERRED, and this is the single most actionable number in the report]** The one paper in this family that *directly controls* the demonstration fraction and sweeps it finds the optimum near **0.4%**, two orders of magnitude below a 30% fixed mix, and reports that higher ratios are consistently worse. Any design that fixes the demo share at 30% is choosing a point the only published sweep says is on the bad side of the curve.

### 3.4 Where the papers disagree

- **DQfD vs POfD on whether the supervised/margin loss is an asset.** DQfD: it "is critical to good performance" and its removal is the worst ablation [STATED, Fig 2]. POfD: margin methods "suffer performance decline when only imperfect demo data are given" [STATED]. These are not reconcilable by picking a winner; they are evaluated on different demonstrator qualities. DQfD's demonstrators are human players whose *objective is the game score* — the same scalar the agent optimises. POfD's demonstrators are deliberately under-trained TRPO agents on the same objective. [INFERRED] Neither regime is the one at issue here (an expert on a *different* objective), and the DQfD result is the one that assumes objective alignment.
- **DQfD vs DDPGfD on whether an imitation loss is needed at all.** DQfD: yes, critical. DDPGfD: no imitation loss; demos enter only as transitions, and it still beats demonstrations by 2–4× in step efficiency [STATED]. [INFERRED] Discrete vs continuous action space is the obvious confound; the disagreement is real and unresolved in the literature.
- **DQfD vs POfD on data efficiency.** POfD [STATED, Results]: "The demonstration data insufficiency severely limits the learning ability of DQfD which usually **requires as many demonstration data as self-generated ones**." This is POfD's characterisation of DQfD and it contradicts DQfD's own Discussion, which says the agent gets "three orders of magnitude more interaction data … than demonstration data." Report the disagreement; do not resolve it.

### 3.5 The POfD numbers on imperfect demonstrators

**[STATED, POfD Table 1 / Results, Walker2d]:** demonstration return **1701.13**; dense-reward TRPO "expert" **6717.08**; POfD **7687.47**. POfD exceeded both the demonstration and the expert. Baselines are explicitly reported as failing the other way [STATED, verbatim]: "DDPGfD and GAIL share some common drawback: **they both converge to the imperfect demonstration data** as training proceeds."

**[STATED]** POfD used "only one single imperfect trajectory as demonstrations", collected by "train[ing] an agent insufficiently by running TRPO".

**[INFERRED]** This is the cleanest published demonstration that (a) demonstration-anchored methods converge to the demonstrator and (b) distribution-matching-with-environment-reward escapes it — with a demonstrator 4× worse than the final policy.

---

## 4. Multiple demonstrators — the core question

### 4.1 Do published methods ever use separate per-demonstrator buffers?

**Almost never. The dominant published pattern is: pool all demonstrators into ONE demonstration buffer, kept separate only from the agent's own data.**

| Paper | Buffer structure | Evidence |
|---|---|---|
| **DQfD**, arXiv:1704.03732 | One buffer, demo transitions permanently retained inside it; a single human player per game | [STATED] |
| **R2D3**, arXiv:1909.01387 | **Two** buffers: one demo, one agent. Demonstrations were collected from **three different human experts** ("100 demonstrations for each task spread across three different experts, each expert contributed roughly one third") — and **pooled into the single demo buffer**. No per-expert buffer, no conflict detection, no per-source weighting | [STATED] |
| **Nair et al.**, arXiv:1709.10089 | Two buffers: demo `R_D` and agent `R`; fixed per-batch draw `N_D = 128` from `R_D`, `N = 1024` from `R` | [STATED] |
| **InfoGAIL**, arXiv:1703.08840 | Pooled; structure recovered by a latent code, not by buffers | [STATED] |
| **Hausman et al.**, arXiv:1705.10479 | Pooled — explicitly a "combined data set of all three behaviors", unstructured and unlabelled | [STATED] |
| **Triple-GAIL**, arXiv:2005.10622 | Pooled ("a mixed set of labeled demonstrations with multiple expert modalities") | [STATED] |
| **T-REX**, arXiv:1904.06387 / **D-REX**, arXiv:1907.03976 | Pooled; distinguished only by a global pairwise ranking | [STATED] |
| **DWBC**, arXiv:2207.10050 | Expert set `D_e` and offline set `D_o` collected separately, then combined into one training batch `D_b = D_e ∪ D_o` | [STATED] |

**The exceptions — and they are thin:**

- **Policy Distillation**, Rusu et al., ICLR 2016, arXiv:1511.06295 [STATED]: "separate replay memory buffers are maintained for each task, and training is evenly interleaved between all tasks". [INFERRED] But the teachers are trained on *different games*, not conflicting policies for the same task — this is multi-task distillation, adjacent rather than on-point.
- **ZPD teaching strategies**, Seita, Chan et al., NeurIPS 2019 Deep RL workshop, arXiv:1910.12154 [STATED]: "we can treat the corresponding dataset `D_T_ZPD` of samples as a distinct 'ZPD teacher' replay buffer", and the method *selects* which teacher-snapshot buffer to draw from rather than pooling.
- **ILEED**, Beliaev, Shih, Ermon, Sadigh & Pedarsani, ICML 2022, arXiv:2202.01288 (verified) [STATED]: "The full dataset `D = {(i, D_i)}_{i=1}^m` is the union of the dataset from each of the m demonstrators, **labeled by the demonstrator index**." Demonstrator *identity* is known and kept; demonstrator *expertise* is learned unsupervised.
- **DMDE**, Dong, Li, Yuan & Gong, *Information Sciences* 648 (2023), "Accelerating Wargaming Reinforcement Learning by Dynamic Multi-Demonstrator Ensemble" — per abstract, places "multi-demonstration into multiple individual datasets" and pre-trains "an individual imitator" per dataset. **Full text paywalled; numbers unverified.** This is the only located DQfD-style pipeline with literally per-demonstrator buffers, and it could not be checked.
- **[NOT FOUND]** Any peer-reviewed DQfD variant with more than one demonstration buffer whose per-buffer design is supported by an ablation.

### 4.2 How are conflicting demonstrators combined?

Four published families, none of which uses a fixed per-source batch quota:

1. **Latent conditioning variable.** InfoGAIL (arXiv:1703.08840) uses a discrete categorical latent `z` with an InfoGAN mutual-information regulariser; the driving experiments use exactly **2** discrete modes [STATED]. Hausman et al. (arXiv:1705.10479) use a joint categorical+continuous intention variable with the category count set equal to the number of known skills (2–4 targets; 3 behaviours) [STATED]. Triple-GAIL (arXiv:2005.10622) adds a third player, a **selector**, that predicts the skill label `c` from `(s,a)`; 3 skills for driving, 2 for RTS [STATED].
2. **Per-demonstrator expertise weighting.** ILEED (arXiv:2202.01288) learns a per-demonstrator embedding `ω_i` and a shared state embedding `φ`, with expertise `ρ(s, ω_i) = φ(s)·ω_i` interpolating the imitation loss between the learned policy and uniform-random — a **state-dependent, per-demonstrator down-weighting** [STATED]. Reported: outperforms competitors in 21 of 23 settings, 7–60 % final-reward improvement, and can exceed the best individual demonstrator [STATED, abstract].
3. **Bayesian posterior over which expert to reuse.** **Bayesian Experience Reuse (BERS)**, Gimelfarb, Sanner & Lee, arXiv:2006.05725 (verified). Abstract, verbatim: "demonstration data can often come from **multiple experts with conflicting goals**, making it difficult to incorporate safely and effectively in online settings." The fix: Bayesian NNs with normal-inverse-gamma priors model per-expert task functions; a quadratic program yields "a probability distribution over the expert models", and demonstrations are sampled in accordance with that distribution. [INFERRED] This is the closest published thing to "per-source priority" — and note the priority is *learned from task-relevance*, not fixed by the designer.
4. **Confidence / discriminator weighting.** 2IWIL and IC-GAIL (Wu et al., ICML 2019, arXiv:1901.09387) keep a confidence-labelled set `D_c` and an unlabelled set `D_u` separate and importance-weight [STATED]. DWBC (Xu, Zhan & Zhu, ICML 2022, arXiv:2207.10050) weights the BC loss per sample by a jointly trained discriminator `d(s,a)` [STATED]. MD2-GAIL (*Neurocomputing* 457, 2021) explicitly targets "imperfect demonstrations by multiple demonstrators" with per-demonstration confidence scores — **full text inaccessible, unverified**.
5. **Explicit failure-mode documentation.** "Eliciting Compatible Demonstrations for Multi-Human Imitation Learning", arXiv:2210.08073 [STATED, abstract]: "sequences of users improve on a policy by iteratively collecting new, **possibly conflicting** demonstrations". [INFERRED] This paper's existence is itself the evidence that conflicting demonstrators are a recognised, unsolved problem.

### 4.3 How many demonstrators help, and where does it stop helping?

**[NOT FOUND] — and this was checked explicitly, paper by paper.**

No paper located reports a controlled ablation that **sweeps the number of demonstrators / experts / modes** and states where the marginal benefit saturates or reverses. Confirmed absent in: InfoGAIL (fixes 2 modes; its Table 2 ablates reward augmentation / replay buffer / WGAN, not mode count), Hausman et al. (fixed skill counts per experiment, no sweep), Triple-GAIL (Table II ablates loss terms `R_E`, `R_G`, not skill count), Policy Distillation (reports 3-game and 10-game configurations separately, with no interpolation or scaling statement), T-REX (fixed 12 trajectories Atari; 9/12/24 MuJoCo, no performance-vs-count curve), D-REX (fixed noise-level counts), 2IWIL/IC-GAIL (fixes 20 % confidence labelling; Fig. 3 sweeps *total unlabelled data*, not demonstrator count), and **ILEED — the paper best positioned to have such an ablation, since it is built around per-demonstrator expertise embeddings — which fixes m = 10 (Table 1), m = 3 (Table 3) and m = 6 (§4.4) in different experiments and never varies m itself.**

The three closest quantitative statements, none of which is a count sweep:

- **ZPD, arXiv:1910.12154, Table 2 (9 Atari games).** The "best ahead" strategy — always imitate the single strongest teacher snapshot — **won 0/9 games on average performance and 1/9 on last-100-episode performance**, against "10 ahead" winning 4/9 and "5 ahead" winning 3/9. [STATED, verbatim] "in almost all cases the best ahead strategy is sub-optimal with respect to both final reward and sample efficiency." [INFERRED] This is published evidence that **the strongest available demonstrator is not automatically the best training signal** — the closest thing in the literature to a warning against simply pointing the learner at the best specialist. It is a teacher-*selection* result, not a count result.
- **DWBC, arXiv:2207.10050, Table 1.** Sweeps the *proportion* of expert trajectories in a two-source mix, X ∈ {30, 60, 90} %, 5 seeds; e.g. hopper at X = 30: DWBC 87.2 ± 12.3 vs BC-exp 74.8 ± 11.6; DWBC beats baselines on 21 of 24 tasks. A **ratio** ablation, not a **headcount** ablation.
- **R2D3, arXiv:1909.01387.** Pools exactly three experts and never varies or reports sensitivity to that count — while sweeping the demo *ratio* over 120 agents (§3.3).

### 4.4 Disagreements in this literature, reported not adjudicated

- **Pool vs separate is an unresolved design split.** InfoGAIL / Hausman / Triple-GAIL / T-REX / DWBC / R2D3 all pool and recover structure via a conditioning variable or a reweighting scheme. ZPD, ILEED and (unverified) DMDE keep explicit per-demonstrator buffers. **No paper argues against the other's choice** — there is no head-to-head experiment. [INFERRED] Which means a design that adopts per-demonstrator buffers cannot cite an experiment for it; it can only cite that some papers do it.
- **Whether the best demonstrator should dominate.** ZPD's Table 2 result is in tension with the monotone-quality assumption implicit in DQfD, R2D3, T-REX and D-REX. None of those four test a case where a lower-ranked source is the better training signal, so this is an unaddressed gap rather than a stated disagreement.

---

## 5. Multi-objective + demonstrations — the intersection is nearly empty

Searched: "multi-objective reinforcement learning from demonstrations", "multi-objective imitation learning", "MORL demonstrations", "preference-conditioned MORL demonstrations", "vector reward DQfD", "MOIRL", "Envelope Q-learning demonstrations", "multi-objective GAIL", "MO-DQfD", "multi-head Q network demonstration", "reward mismatch demonstrations", "misaligned demonstrator", "hidden objective demonstrations" — across arXiv, OpenReview, IEEE Xplore, Springer, PMLR (~20 queries).

### 5.1 Forward MORL seeded with demonstrations — three papers, none a general framework for a one-head expert

| Paper | What it does | Is the demonstrator per-objective? |
|---|---|---|
| **DG-MORL**, arXiv:2404.03997 (2024) | Vectorised `Q(s,a,w)` over preference weights; "corner weights" computed from a convex coverage set of demonstration returns align each demonstration with an inferred preference vector; a self-evolving mechanism replaces suboptimal demos | **No.** Demonstrations are described as "capable of performing reasonably across multiple objectives" — generalists, merely sub-optimal |
| **Demonstration-Enhanced Adaptable Multi-Objective Robot Navigation**, de Heuvel, Sethuraman & Bennewitz, arXiv:2404.04857 (2024, verified) | Reward vector `r = (r_core, r_demo, r_distance, r_efficiency)`; **only `r_demo` is learned from demonstrations** (a D-REX-distilled reward model), the other three are hand-specified. Single preference-conditioned critic `λᵀQ` | **Yes — the closest published match.** The paper states the demonstration pattern is "contradictory to the other two [style] objectives": the demonstrator is good on exactly one reward dimension and explicitly bad on others |
| **Interpretable Multi-Objective RL through Policy Orchestration**, Noothigattu et al., arXiv:1809.08343 (2018; AIES 2019, verified) | Reward vector with ℓ components, one of which is **hidden** and learnable only from demonstrations via IRL; a separate RL policy handles the observed reward; a contextual-bandit **orchestrator** picks between the two policies per state | **Yes on the demonstrator side** — "the demonstrators may be good at demonstrating what not to do in a domain but may not provide examples of how best to maximize reward". **But there is no joint multi-head value function**: it is two single-objective policies plus an arbiter |

**[NOT FOUND]** A peer-reviewed general algorithm combining (a) demonstration-seeded *forward* RL, (b) a shared multi-head / vector-valued Q network, and (c) a demonstrator that is expert on exactly one head and unmeasured or adversarial on the others. The two papers above each satisfy two of the three criteria and split on the third.

**[NOT FOUND]** Any published multi-objective variant of DQfD itself. A GitHub class project (`svikramank/DQfD_for_multi-expertRL`) exists; it is not peer-reviewed and uses a scalar reward. Not usable as grounding.

### 5.2 Multi-objective *inverse* RL — a related but different problem, reported separately

This sub-field infers a vector reward or preference weights *from* demonstrations. It is not the design at hand (which fixes the reward vector and uses demonstrations to seed learning), and it should not be cited as if it were.

- **MOIQ / "Learning From Diverse Experts: Behavior Alignment Through Multi-Objective IRL"**, ICLR 2025 (earlier OpenReview id `pqgDqYinDZ`, "Learning From Multi-Expert Demonstrations: A Multi-Objective IRL Approach"). Assumes all experts share a **common vector reward** and differ only in scalarisation weights; infers per-expert vector rewards and reconciles them with a "reward consensus" penalty.
- **DWPI, "Inferring Preferences from Demonstrations in Multi-Objective RL"**, arXiv:2409.20258 / *Neural Computing & Applications* 2024. Infers unknown scalarisation weights; states it works for sub-optimal demonstrations.
- **Neural scalarisation for multi-objective IRL**, *Journal of Information and Telecommunication* 2023; **MODIRL**, IEEE 2022 — both keep the linear-scalarisation, generalist-demonstrator assumption.
- **MOCI, "Multi-Objective Constraint Inference using IRL"**, arXiv:2605.06951. Notable because it *states the gap*: prior work "assume[s] homogeneous demonstrations … generated by a single expert or multiple experts with identical objectives", and MOCI instead handles "heterogeneous expert trajectories, where multiple experts pursue different objectives." [INFERRED] This is the closest published acknowledgement that per-objective experts are an open setting — but it is inverse RL, and the abstract does not confirm a strict one-expert-per-objective design.

### 5.3 Demonstrator optimising a *different* objective from the learner

- **"RL with Demonstrations from Mismatched Task under Sparse Reward"**, arXiv:2212.01509 — mismatch is across *tasks*, single scalar reward per task; proposes extracting partial guidance rather than imitating.
- **PAGAR**, arXiv:2306.01731 — "reward misalignment" from finite/degenerate demonstrations in single-objective IRL. Not multi-objective.
- **[NOT FOUND]** Any paper whose central research question is "the demonstrator optimises head A while the learner's reward vector also contains heads B and C", outside the two §5.1 papers.

### 5.4 The plain statement, since it is itself the answer

**The literature does not contain a validated recipe for what is being proposed.** The default assumption everywhere in demonstration-guided MORL and multi-objective IRL is that a demonstrator is a *generalist scalariser with unknown weights*, not a *specialist on one head*. The two documented instances of a genuinely one-head demonstrator (arXiv:2404.04857, arXiv:1809.08343) both handle it by **keeping the demonstration signal confined to its own reward component** — de Heuvel by routing it into a dedicated `r_demo` head, Noothigattu by giving it its own policy and an orchestrator — and **neither lets it write a supervised action-matching loss over the joint policy.** [INFERRED] That is a convergent design choice across two unrelated papers, and it is the single most transferable structural fact in this section.

---

## 6. The honest mapping — the five "catfish" mechanisms against the published record

Source of the five mechanism statements: the owner-supplied restatement `07-true-catfish-formulas.md`. Used as a *description of what is to be mapped*, not as evidence for anything.

| # | Catfish mechanism | Nearest published mechanism | Independent evidence for the published mechanism | Verdict |
|---|---|---|---|---|
| **(i)** | External-solver-seeded replay memory (DFT codebook enumeration → WMMSE → argmax EE, seeded into the catfish buffer as initial experience) | **Demonstration-seeded replay.** Exactly **RBS** (Replay Buffer Spiking, Lipton et al. 2016) as characterised by DQfD: "PDD DQN with the replay buffer initially full of demonstration data … they do not pre-train the agent … or keep the demonstration data permanently". Broader class: DQfD (arXiv:1704.03732), DDPGfD (arXiv:1707.08817), R2D3 (arXiv:1909.01387). A *machine/solver* demonstrator rather than a human is also published: ADET used "a trained DQN agent to generate their demonstration data, which on most games is better than human data" | **Class: strong** — four independently reproduced algorithms. **This variant: published NEGATIVE.** DQfD Figure 2 (right subplots) shows RBS among the two worst arms, and the Discussion states verbatim that "naively adding (e.g. only pre-training or filling the replay buffer) this small amount of data to a pure deep RL algorithm does not provide similar benefit **and can sometimes be detrimental**" | **SUPPORTED AS A CLASS, BUT THE CATFISH PARAMETERISATION IS THE PUBLISHED NEGATIVE ARM.** Seeding without pre-training and without a supervised loss is RBS. To inherit the positive evidence the design must add pre-training + a classification loss (DQfD/ADET) or at minimum n-step + prioritisation (DDPGfD) |
| **(ii)** | EE-threshold separation into two buffers (`EE ≥ EE_high` → catfish memory; otherwise main memory) | Two different published things, and the catfish claim maps onto the weaker one. **(a) Split by SOURCE** (demo vs agent): R2D3's two buffers; Nair et al.'s `R_D` / `R` — well supported. **(b) Split by VALUE/return**: the mature published form is **Self-Imitation Learning** (Oh et al., ICML 2018, arXiv:1806.05635), which admits a transition only when `(R − V_θ(s))_+ > 0` and prioritises replay by that clipped advantage. **Prioritized Experience Replay** (Schaul et al. 2016) prioritises by **TD error**, not by value | **(a) strong.** **(b) partial.** SIL is reproduced and its `(·)_+` gate is the standard "filter by return" primitive — but SIL's gate is **relative to the agent's own value estimate**, adaptive and self-normalising, not an absolute externally-set threshold. Searches for an absolute value-threshold two-buffer split returned only scattered, non-canonical work (reward-categorised buffers, dual positive/negative buffers) with no independently reproduced result | **PARTIAL.** Splitting by *source* is supported; splitting by an *absolute EE threshold* is **NOT FOUND** as a mature mechanism. Note also: if the catfish buffer is fed by the catfish agent's own rollouts (as the owner's explainer records), this stops being a demonstration buffer at all and becomes an unnormalised SIL — in which case SIL's relative gate is the published correction |
| **(iii)** | Asymmetric discounts `γ^M ≤ γ^CF` (myopic main agent, farsighted catfish agent) | **Multiple discount factors as a multi-head auxiliary task**: Fedus et al., "Hyperbolic Discounting and Learning over Multiple Horizons", arXiv:1902.06865 — learn many Q-values, each with a different γ, aggregated; the multi-horizon auxiliary task "often improves over strong baselines including C51 and Rainbow in the ALE" | The *ingredient* (several γ in one learner) is published and reproduced. **[NOT FOUND]:** any published result where **two separate agents** are given different discount factors and one seeds the other's replay. Searched multi-horizon RL, hyperbolic discounting, ensemble-γ, and teacher–student RL | **NO PUBLISHED COUNTERPART for the catfish use.** The multi-γ ingredient is real; the two-agent asymmetric-γ teacher/student arrangement is not in the literature. A thesis cannot lean on this one. (Independently, the owner's own explainer records that in a 10-step episode with no cumulative state the `γ·Q(s′)` term is action-independent, i.e. the mechanism is disclosed dead-weight in that environment — an implementation fact, not a literature one) |
| **(iv)** | Periodic 70/30 batch intervention (`S_mix = S^M ∪ S^CF`, 70 % main + 30 % catfish, at randomised intervals) | **Exactly HER** (Human Experience Replay, Hosu & Rebedea 2016) as characterised by DQfD: "keeps the demonstration data and **mixes demonstration and agent data in each mini-batch**". Also **R2D3**'s explicit demo ratio ρ, and **Nair et al.**'s fixed `N_D = 128` of 1152 per batch (**11.1 %**) | **The published evidence on this exact mechanism is negative at the catfish's setting.** (1) DQfD Fig. 2 right: HER is one of the two worst arms, worse than DQfD in both games, on identical demo data with prioritisation and n-step returns included. (2) R2D3 §6.2 / Fig. 6, 120 agents over 4 ratios × 6 tasks × 5 seeds: "the **optimal demo ratio is very small (but non-zero)**"; "lower demo ratios consistently outperform the higher demo ratios across the suite of tasks"; Appendix D.3 reports **1/256 ≈ 0.39 %** as best on four tasks. (3) DQfD deliberately declines to fix the ratio, letting `ε_d`/`ε_a` and prioritised replay produce it, and plots the emergent value | **MECHANISM EXISTS AND THE EVIDENCE POINTS THE OTHER WAY.** 30 % is ≈ 77× the only published swept optimum and ≈ 3× the only other published fixed ratio. Separately, the *randomised period* has **NO published counterpart** — every method located (DQfD, R2D3, Nair, HER) mixes **every batch**; none gates mixing on a stochastic interval |
| **(v)** | Competitive reward `r^C = r + η·(r^CF − r^M)` (ACRM) | **Difference rewards** (Wolpert & Tumer 2001; Tumer & Agogino 2007), `D_i(z) = G(z) − G(z−z_i)`, and **COMA**'s counterfactual baseline (Foerster et al., AAAI 2018). The RIS paper's own cited analogue, "SASR", could not be matched to a "Shen et al." paper; the SASR located is **Ma et al., "Highly Efficient Self-Adaptive Reward Shaping for RL", ICLR 2025, arXiv:2408.03029**, which derives shaped rewards from Beta-distributed **success rates**, not from a competitive differential between two agents — **the claimed resemblance does not hold and the citation is unverified** | **The resemblance is superficial and the difference is the load-bearing part.** COMA's counterfactual term enters the **advantage** in the policy gradient and provably has **zero expected contribution to the gradient** — it is a variance-reduction baseline that leaves the objective unchanged. ACRM **adds** the differential to the **reward**, changing the MDP. And **Ng, Harada & Russell, ICML 1999, "Policy Invariance Under Reward Transformations"** proves that potential-based shaping `F = γΦ(s′) − Φ(s)` is a **necessary** condition for policy invariance: "any other transformation may yield suboptimal policies unless further assumptions are made about the underlying MDP". `η(r^CF − r^M)` depends on another agent's realised reward, not on a state potential, so it lies outside the invariance class | **NO PUBLISHED COUNTERPART, AND A PUBLISHED THEORETICAL WARNING AGAINST IT.** A thesis cannot lean on this one either; if it is run, the shifted optimum must be declared up front, and any reported EE must be scored on the **unshaped** reward |

### 6.1 The three the thesis cannot lean on

- **(iii) asymmetric two-agent discounts** — [NOT FOUND].
- **(v) competitive reward differential added to the environment reward** — [NOT FOUND], plus Ng et al. 1999 says a non-potential shaping term may move the optimum.
- **the randomised-period element of (iv)** — [NOT FOUND]; the 70/30 *ratio* itself has a counterpart, and its published evidence is unfavourable.

### 6.2 The two that do map — with a caveat each

- **(i)** maps onto a strongly supported class, but the catfish's specific parameterisation (seed only; no pre-training; no supervised loss) is precisely the arm DQfD published as one of its worst.
- **(ii)** maps cleanly for the *source* split and only partially, via SIL, for the *value* split — and SIL's threshold is relative to the learner's own value estimate, not absolute.

---

## Table D2 (DQfD) — every hyperparameter needed to run it

All values from Hester et al., AAAI 2018, arXiv:1704.03732. Location column: **Supp.** = the "Supplementary Material" bulleted parameter list; **Method** = the "Deep Q-Learning from Demonstrations" section; **Alg. 1** = the pseudo-code; **Disc.** = Discussion.

| Parameter | Paper value | Location |
|---|---|---|
| Pre-training gradient steps `k` | **750,000** mini-batch updates, on demonstration data only, no environment interaction | Supp.; Method |
| n for the n-step return | **10**, forward view, "similar to A3C" | Supp.; Method |
| Weight on 1-step double-Q loss `J_DQ` | **1.0** (implicit — it carries no λ in `J(Q)`) | Method |
| λ1, n-step loss weight | **1.0** | Supp. |
| λ2, supervised large-margin loss weight | **1.0** on demonstration data; **0** on self-generated data | Supp.; Method |
| λ3, L2 weight (on weights **and** biases) | **1e-5** | Supp. |
| Large-margin value `l(a_E, a)`, `a ≠ a_E` | **0.8** (and 0 when `a = a_E`) | Supp.; Method |
| `ε_d`, demonstration priority bonus | **1.0** | Supp. |
| `ε_a`, agent priority bonus | **0.001** | Supp. |
| Prioritization exponent α | **0.4** | Supp. |
| Importance-sampling exponent β0 | **0.6**, "as in (Schaul et al. 2016)" | Supp. |
| β annealing schedule | **UNSPECIFIED** — DQfD gives only β0 and defers to Schaul et al. (who anneal β → 1); DQfD itself states no schedule | Supp. |
| Discount γ | **0.99** | Supp. |
| Target-network update period τ | **10,000** | Supp. |
| ε-greedy exploration ε | **0.01** | Supp. |
| Are demonstrations ever evicted? | **No.** "the agent never over-writes the demonstration data"; "retains in its replay buffer permanently"; Alg. 1 overwrites "oldest **self-generated** transition if over capacity" | Method; Alg. 1 |
| Demo/agent batch fraction | **Not a hyperparameter.** "The ratio of both types of data in each mini-batch is automatically controlled by a prioritized-replay mechanism" — it is an emergent quantity, measured and plotted (Fig. 1, right) | Disc.; Fig. 1 |
| Demonstration set size | **5,574 – 75,472 transitions per game; 3 – 12 episodes** (game-dependent) | Table 2; Disc. |
| Interaction:demonstration data ratio | ≈ **1000:1** ("three orders of magnitude more interaction data … than demonstration data") | Disc. |
| Learning rate | **UNSPECIFIED** — no learning rate appears anywhere in the paper or supplementary list | — |
| Optimizer | **UNSPECIFIED** | — |
| Mini-batch size | **UNSPECIFIED** — Alg. 1 says "a mini-batch of n transitions" with no value given | Alg. 1 |
| Replay buffer capacity | **UNSPECIFIED** — the paper says only "until it is full" | Method |
| Network architecture | Dueling double DQN over 84×84 grayscale, 4 stacked frames, action repeat 4 (inherited from PDD DQN; not restated as DQfD-specific) | Supp.; Experiments |

**Note on tuning provenance** [STATED]: "We performed informal parameter tuning for all the algorithms on six Atari games and then used the same parameters for the entire set of games. … Our coarse search over prioritization and n-step return parameters led to the same best parameters for DQfD and PDD DQN."

**[INFERRED]** Four UNSPECIFIED entries (learning rate, optimizer, mini-batch size, buffer capacity) are enough to make an exact reproduction impossible from the paper alone. For a declared-before-running arm they must be fixed by the project and recorded as **project choices, not paper values** — otherwise a later reader cannot tell which numbers carry Hester et al.'s authority. Note also that four of the listed values (γ, τ, ε, α, β0) are inherited PDD DQN/PER defaults rather than DQfD contributions.

---

## Table D1 (catfish) — the same treatment for the five RIS mechanisms

Numbers taken from the owner-supplied `07-true-catfish-formulas.md` (numbers only, not authority). Two columns are kept apart deliberately: **what the RIS paper specifies** vs **what the project's code happens to use**. Only the first column can be declared as "the paper's value".

| # | Parameter | RIS paper's value | Project code's value (for contrast; not a paper value) |
|---|---|---|---|
| (i) | Phase-1 seed generator | DFT codebook enumeration over `Φ̃_RIS` and `F̃^RF` → WMMSE digital beamformer → `argmax EE` | **Not implemented** (no Phase-1 anywhere; the catfish buffer is only ever written from the catfish agent's own rollouts) |
| (i) | Number of seeded transitions / solution cases | **UNSPECIFIED** | n/a (zero) |
| (ii) | EE threshold `EE_high` | **UNSPECIFIED** — the paper gives only the rule `if EE ≥ EE_high → catfish memory, else main memory`; no numeric value | rolling quantile, `strat_threshold_quantile = 0.80` (top 20 %); `strat_mid_quantile = 0.50`; `strat_hard_discard = False` (soft). **This is a relative quantile, not the paper's absolute threshold** |
| (ii) | Whether main keeps the full stream | **UNSPECIFIED** (paper says "moderate EE" go to main) | soft mode: main keeps the full stream; `faithful_full` hard mode: top 20 % → catfish, 20–50 % → main, bottom 50 % discarded |
| (iii) | `γ^M` (main discount) | **UNSPECIFIED** — the paper states only the inequality `γ^M ≤ γ^CF` | `GAMMA_MAIN = 0.9` |
| (iii) | `γ^CF` (catfish discount) | **UNSPECIFIED** — inequality only | `GAMMA_CATFISH = 0.99` (with a hard assert `γ_CF > γ_M`) |
| (iv) | Batch mix ratio | **70 % main / 30 % catfish** — the one numeric value the paper does specify | `intervention_ratio_catfish = 0.30` (matches) |
| (iv) | Intervention period | **UNSPECIFIED** — described only as "randomized periodic intervention" / random interval | `period ~ Uniform[4, 16]` steps; `min_catfish_replay_size = 32` |
| (iv) | Which agent the mixed batch updates | main agent, using `γ_main` | matches |
| (v) | ACRM `η` | **UNSPECIFIED** — the paper defines only its role ("the coefficient controlling the weight of this reward; when η → 0 the model degrades to the original reward model") | `acrm_eta_weight` — value not recorded in the explainer; **UNSPECIFIED there too**. `acrm_enabled = False` by default and no config in the repo turns it on |
| (v) | ACRM base term | `r^C = r + η·r^S`, `r^S = r^CF − r^M`, where `r` is "the original EE reward from the environment" | code computes `r^C = r^CF + η(r^CF − r^M)` — i.e. it substitutes `r^CF` for the paper's `r`. **A discrepancy that must be declared**, since it changes the fixed point |
| (v) | `r^M` definition | main agent's EE "on the same task" | counterfactual: main agent's greedy action evaluated at the same catfish pre-state |
| — | Backbone | actor-critic (DDPG-style), continuous action `a_t = [w^BB_k, F^RF, C^RF, (Λ_RIS), φ_RIS, (A/B_RIS)]`, scalar reward `r_t = Σ_k R_k` = EE | project code is a discrete multi-head DQN — a different algorithm class from the paper's |
| — | Learning rates `μ_c`, `μ_a` | **UNSPECIFIED** | — |
| — | Replay capacities (main, catfish) | **UNSPECIFIED** | — |
| — | Batch size | **UNSPECIFIED** | — |
| — | Is catfish data ever evicted? | **UNSPECIFIED** — the paper says nothing about retention | underlying buffer is a `deque(maxlen=capacity)`, so **yes, evicted FIFO** — the opposite of DQfD's guarantee |

**[INFERRED] Count of the declaration:** the RIS paper specifies **one** runnable number (the 70/30 mix). Every other quantity in Table D1 — the EE threshold, both discount factors, the intervention period, and `η` — is **UNSPECIFIED in the source**. Table D2 specifies **fifteen**, with four UNSPECIFIED. That asymmetry is a real finding about the two arms, not a gap to be papered over: the catfish arm cannot be "run as published" because there is almost nothing published to run, whereas the DQfD arm can be run as published up to four engineering constants.

**[INFERRED] Consequence for the head-to-head.** If both tables are declared before the run and not tuned afterwards, five of the catfish arm's six free numbers will be project choices. Any outcome — win or lose — is then an outcome for *the project's instantiation of catfish*, not for the published mechanism. That should be written into the arm's declaration now, not discovered at reporting time.

---

## What this says the design should be

**1. How many demonstration streams the published evidence supports: ONE.**
No paper in the DQfD family runs more than one demonstration buffer with an ablation behind it. R2D3 had three human experts available and **pooled them into one buffer** (arXiv:1909.01387). The three located exceptions (Policy Distillation arXiv:1511.06295, ZPD arXiv:1910.12154, DMDE *Inf. Sci.* 2023) either address a different problem (multi-task), are a workshop paper, or are paywalled and unverified. And **no paper anywhere sweeps the number of demonstrators** (§4.3) — so there is no published answer to "where does adding another demonstrator stop helping", and a thesis claiming one would be claiming something the field has not established.

**2. Do the streams get separate buffers? Separate from the AGENT's data, yes. Separate from EACH OTHER, no published warrant.**
Two buffers split by **source** (demonstration vs self-generated) is the well-supported architecture: R2D3 (two buffers, explicit ratio) and Nair et al. arXiv:1709.10089 (`R_D` / `R`, 128 : 1024 per batch). DQfD achieves the same effect inside one buffer by never evicting demo transitions and giving them `ε_d = 1.0` against `ε_a = 0.001`. Splitting by an **absolute value threshold** — the catfish's mechanism (ii) — has no mature published counterpart; the mature version of "keep only the good experience" is SIL's `(R − V_θ(s))_+` gate (arXiv:1806.05635), which is **relative to the learner's own value estimate**.

**3. What loss terms are needed.**
- **1-step TD** — always.
- **n-step TD, n = 10, λ1 = 1.0** — DQfD's ablation puts its removal at "nearly as large an impact" as removing the supervised loss (Fig. 2). Cheap and uncontested; include it.
- **L2 on weights and biases, λ3 = 1e-5** — DQfD's stated purpose is preventing over-fit to a small demonstration set, which is exactly this situation. Include it.
- **The supervised large-margin loss `J_E`, λ2 = 1.0, margin 0.8 — this is the contested term and it should be an explicitly declared arm, not a default.** DQfD says it "is critical to good performance" (Fig. 2, and RBS/HER — the two arms lacking it — are the two worst). POfD (ICML 2018), MCPO (arXiv:1911.07109) and Nair et al. (arXiv:1709.10089) all name it as the reason a learner cannot exceed an imperfect demonstrator. Both positions are published; the disagreement is real and turns on whether the demonstrator optimises the learner's objective — which here, it does not.
- **If `J_E` is used, gate it.** The published gate is Nair et al.'s **Q-filter**: apply the imitation term only where `Q(s, a_demo) > Q(s, π(s))`. Applied here, that means the filter must be evaluated on the **scalarised multi-head objective the learner actually optimises**, so that an action which is r1-excellent but r2/r3-costly is dropped from the imitation loss automatically. No published paper defines a Q-filter over a multi-head critic (§5) — that step is an extension, and must be labelled as one.
- **The published zero-risk alternative is DDPGfD (arXiv:1707.08817): no imitation loss at all**, demonstrations enter only as reward-labelled off-policy transitions. It still beat its demonstrations by 2–4× in step efficiency. This is the option with the fewest assumptions about demonstrator alignment.

**4. The demo fraction should not be fixed at anything like 30 %.**
DQfD does not fix it at all — `ε_d`/`ε_a` set a floor and prioritised replay determines the realised fraction, which the paper *measures* rather than declares. The one paper that does fix it and sweeps it, R2D3, ran 120 agents and found the optimum near **1/256 (0.39 %)**, with "lower demo ratios consistently outperform the higher". Nair et al.'s fixed value is **11.1 %**. If the design declares a fixed fraction before running, declare it near the bottom of that range and treat 30 % as the adversarial high-ratio point, not the default.

**5. The single largest risk the literature flags for a demonstrator that is expert on one objective and unmeasured on the others.**

**The large-margin loss `J_E` is unconditional.** It gates on nothing. It fires on every demonstration transition and forces `Q(s, a_specialist)` above every alternative by the full 0.8 margin — in the units of whatever head the loss is wired to. The specialist here is measured *only* on r1 (62.50 vs 41.28 Mbit/J pooled EE) and is **unmeasured on r2 handover cost and r3 beam occupancy**. Therefore, on every state where the r1-maximising action is also handover-expensive or occupancy-heavy, `J_E` is actively teaching the wrong action — and DQfD's own design makes that damage permanent and privileged: the transition is **never evicted** ("the agent never over-writes the demonstration data") and carries a **1000× priority floor** (`ε_d = 1.0` vs `ε_a = 0.001`). The learner's own experience can outvote it only by accumulating TD error faster than the floor, which DQfD reports does *not* happen on the hardest tasks — there the demo fraction **grows** over training (Fig. 1, right).

This failure mode is not speculative; it is the named result in three independent papers. POfD, verbatim: margin methods "would suffer performance decline when only imperfect demo data are given." Its Walker2d experiment is the clean demonstration — demonstration return **1701.13**, POfD **7687.47**, and the anchored baselines "both converge to the imperfect demonstration data as training proceeds." And ZPD (arXiv:1910.12154, Table 2) adds the twist that matters most for a specialist-seeded design: the single **best** available demonstrator won only **0/9** Atari games on average performance against moderately-skilled teacher snapshots. Being better on the measured axis is not, by itself, evidence of being the right thing to imitate.

**Corollary from §5, and the one structural precedent that exists.** The only two published papers with a genuinely one-objective demonstrator — de Heuvel et al. arXiv:2404.04857 and Noothigattu et al. arXiv:1809.08343 — both **confine the demonstration signal to its own reward component** (a dedicated `r_demo` head; a dedicated policy plus an orchestrator) and **neither lets it write a supervised action-matching loss over the joint policy.** Two unrelated papers converging on the same containment is the strongest transferable evidence in this report for how an r1-only specialist should be wired in.

---

## Sources

Verified by direct fetch of the paper text (arXiv/ar5iv/PMLR PDF):
- Hester et al., *Deep Q-learning from Demonstrations*, AAAI 2018 — arXiv:1704.03732 (full text + Supplementary Material)
- Paine et al., *Making Efficient Use of Demonstrations to Solve Hard Exploration Problems* (R2D3), 2019 — arXiv:1909.01387 (§6.2, Fig. 6, App. D.3)
- Vecerik et al., *Leveraging Demonstrations for Deep RL on Robotics Problems with Sparse Rewards* (DDPGfD), 2017 — arXiv:1707.08817
- Nair et al., *Overcoming Exploration in RL with Demonstrations*, 2017 — arXiv:1709.10089 (Q-filter, Eq. 8; Fig. 4)
- Kang, Jie & Feng, *Policy Optimization with Demonstrations* (POfD), ICML 2018 — PMLR v80 kang18a (full PDF text extracted; Table 1, Figs. 2–3)
- Oh et al., *Self-Imitation Learning*, ICML 2018 — arXiv:1806.05635
- *RL from Imperfect Demonstrations under Soft Expert Guidance* (MCPO), 2019 — arXiv:1911.07109 (Table 1)
- de Heuvel, Sethuraman & Bennewitz, *Demonstration-Enhanced Adaptable Multi-Objective Robot Navigation*, 2024 — arXiv:2404.04857 (abstract verified)
- Noothigattu et al., *Interpretable Multi-Objective RL through Policy Orchestration*, 2018/AIES 2019 — arXiv:1809.08343 (abstract verified)
- Beliaev et al., *Imitation Learning by Estimating Expertise of Demonstrators* (ILEED), ICML 2022 — arXiv:2202.01288 (abstract verified)
- Gimelfarb, Sanner & Lee, *Bayesian Experience Reuse for Learning from Multiple Demonstrators* (BERS), 2020 — arXiv:2006.05725 (abstract verified verbatim)

Fetched by the delegated searches (paper text via ar5iv/arXiv; quotes as extracted):
- Li, Song & Ermon, *InfoGAIL*, NeurIPS 2017 — arXiv:1703.08840
- Hausman et al., *Multi-Modal Imitation Learning from Unstructured Demonstrations using GANs*, NeurIPS 2017 — arXiv:1705.10479
- Kuefler & Kochenderfer, *Burn-In Demonstrations for Multi-Modal Imitation Learning*, CoRL 2017 — arXiv:1710.05090 (secondary summary only; lower confidence)
- *Triple-GAIL*, IJCAI 2020 — arXiv:2005.10622
- Rusu et al., *Policy Distillation*, ICLR 2016 — arXiv:1511.06295
- Seita, Chan et al., *ZPD Teaching Strategies for Deep RL from Demonstrations*, NeurIPS 2019 Deep RL workshop — arXiv:1910.12154 (Table 2)
- Brown et al., *T-REX*, ICML 2019 — arXiv:1904.06387; *D-REX*, CoRL 2019 — arXiv:1907.03976
- Wu et al., *Imitation Learning from Imperfect Demonstration* (2IWIL / IC-GAIL), ICML 2019 — arXiv:1901.09387
- Xu, Zhan & Zhu, *Discriminator-Weighted Offline Imitation Learning from Suboptimal Demonstrations* (DWBC), ICML 2022 — arXiv:2207.10050 (Table 1)
- *Eliciting Compatible Demonstrations for Multi-Human Imitation Learning*, 2022 — arXiv:2210.08073
- DG-MORL, 2024 — arXiv:2404.03997
- DWPI, *Inferring Preferences from Demonstrations in MORL*, 2024 — arXiv:2409.20258
- MOCI, *Multi-Objective Constraint Inference using IRL*, arXiv:2605.06951
- *Learning From Diverse Experts: Behavior Alignment Through Multi-Objective IRL* (MOIQ), ICLR 2025
- *RL with Demonstrations from Mismatched Task under Sparse Reward*, 2022 — arXiv:2212.01509
- PAGAR, 2023 — arXiv:2306.01731

Cited from search-level evidence only (not fetched in full):
- Lipton et al., *Replay Buffer Spiking* (RBS), 2016 — characterised here via DQfD's own description
- Hosu & Rebedea, *Human Experience Replay* (HER), 2016 — characterised here via DQfD's own description
- Lakshminarayanan, Ozair & Bengio, *ADET*, 2016 workshop — characterised here via DQfD's own description
- Ng, Harada & Russell, *Policy Invariance Under Reward Transformations*, ICML 1999, pp. 278–287
- Wolpert & Tumer, difference rewards, 2001/2002; Tumer & Agogino 2007
- Foerster et al., *Counterfactual Multi-Agent Policy Gradients* (COMA), AAAI 2018
- Fedus et al., *Hyperbolic Discounting and Learning over Multiple Horizons*, 2019 — arXiv:1902.06865
- Ma et al., *Highly Efficient Self-Adaptive Reward Shaping for RL* (SASR), ICLR 2025 — arXiv:2408.03029 (**not** the "SASR / Shen et al." the RIS paper cites; that citation could not be matched)

Paywalled / unverified, flagged as such wherever used:
- Dong, Li, Yuan & Gong, *Accelerating Wargaming RL by Dynamic Multi-Demonstrator Ensemble* (DMDE), *Information Sciences* 648 (2023)
- MD2-GAIL, *Neurocomputing* 457 (2021)
- *From Many Imperfect to One Trusted*, OpenReview ~Oct 2025 (venue/id unconfirmed)

Not literature, explicitly excluded from evidence:
- `svikramank/DQfD_for_multi-expertRL` (GitHub class project, not peer-reviewed)
