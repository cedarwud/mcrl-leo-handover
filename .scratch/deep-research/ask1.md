# Architecture decision

**Build a single transformed-return masked DQN, \(Q_\eta\), with \(\eta\) frozen during each inner training phase. Do not make independent \(Q_B\) and \(Q_E\) heads the primary architecture. Do not use \(Q_B/Q_E\) for action selection. Do not add an advantage-filtered imitation or margin loss in the first implementation.**

For each fixed \(\eta_k\), the DQN should solve

$$
\max_\pi\;
J_B(\pi)-\eta_kJ_E(\pi),
$$

using the per-transition signal

$$
g_{\eta_k,t}=B_t-\eta_k E_t.
$$

After that inner policy has been trained, estimate its numerator and denominator from **fresh greedy-policy rollouts** and update

$$
\eta_{k+1}
=
\frac{\sum_{\text{evaluation}} B_t}
     {\sum_{\text{evaluation}} E_t}.
$$

This applies the published Dinkelbach transformation. The nonlinear masked-DQN implementation, replay treatment, and approximate inner solves are adaptations; they do not inherit a deep-RL convergence theorem from Dinkelbach. Dinkelbach establishes the parametric root condition \(F(\eta)=\max_\pi[J_B-\eta J_E]=0\), while CARVI and FQL provide the nearest RL precedents for transformed reward-per-cost control. ([pubsonline.informs.org][1])

## 1. Status of the two-critic recommendation

The recommendation contains two separable claims.

| Claim                                                                                                                      | Decision                                                                             |
| -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Use Dinkelbach and compare actions through \(B-\eta E\)                                                                    | **Supported**                                                                        |
| Implement this as two independent optimal critics \(Q_B,Q_E\)                                                              | **Unsupported**                                                                      |
| Select by \(\arg\max Q_B/Q_E\)                                                                                             | **Unsupported and not implied by Dinkelbach**                                        |
| Maintain two component critics under one shared \(\eta\)-greedy continuation policy, then combine them as \(Q_B-\eta Q_E\) | **Algebraically coherent, but no complete published replay-DQN precedent was found** |
| Full package: two critics, replay, changing \(\eta\), discrete masked argmax                                               | **No primary source found**                                                          |

The critical semantic distinction is between

$$
Q_B^{\pi_\eta}(s,a)-\eta Q_E^{\pi_\eta}(s,a),
$$

where **both components use the same continuation policy** \(\pi_\eta\), and

$$
Q_B^\star(s,a)-\eta Q_E^\star(s,a)
\quad\text{or}\quad
\frac{Q_B^\star(s,a)}{Q_E^\star(s,a)},
$$

where each head has independently applied its own Bellman optimum. In the second construction, the numerator and denominator can correspond to different future policies. They therefore do not describe the ratio or transformed return of any single implementable policy.

The closest fractional-Q derivation decomposes the transformed value as

$$
Q_\eta=N_\eta-\eta D_\eta,
$$

but \(N_\eta\) and \(D_\eta\) are evaluated under the same \(\eta\)-dependent policy. Suttle et al. use separate reward and cost critics in an actor–critic algorithm, not in a two-Q-head discrete DQN. The DR-1 search found no primary source for the full proposed combination.  

Therefore:

* Calling a two-independent-critic architecture an application of an established ratio-DQN method would be inaccurate.
* A shared-policy two-head implementation would be a **new architectural adaptation**.
* The single \(Q_\eta\) implementation is the smaller and more directly literature-grounded design.

The thesis can accurately say that it **applies Dinkelbach’s fractional transformation to a masked discrete DQN**. It must separately identify replay relabelling, approximate outer iteration, and any two-head decomposition as engineering or methodological adaptations.

## 2. Replay when \(\eta\) changes

First, a correction to the replay abstraction: **TD targets should not be stored in the replay buffer at all.** They must be recomputed when a minibatch is sampled. Likewise, the buffer must not store only the already transformed reward \(B-\eta_{\text{old}}E\).

The published FQL/D3QN example closest to this setting computes the transformed scalar under the current fractional parameter and stores that scalar in replay, while subsequently changing the parameter. Its paper gives no relabelling, buffer clearing, or convergence treatment for those old transformed rewards. Thus it demonstrates that replay has been combined with fractional deep RL, but not that this particular staleness is sound. ([arXiv][2])

The surveyed possibilities are:

### A. Keep old transformed scalar rewards

$$
r^{\rm buffer}_t=B_t-\eta_{\rm old}E_t.
$$

**Reject this.** Once \(\eta\) changes, these samples belong to a different Bellman problem.

### B. Invoke CARVI’s two-timescale theorem to excuse stale replay

**Reject this justification.** CARVI’s theorem is for online stochastic approximation with a fast value update and a slow ratio update. It is not a theorem for nonlinear target-network DQN repeatedly sampling a finite buffer containing old transformed rewards. 

### C. Store raw \(B_t,E_t\) and re-form \(B_t-\eta E_t\) when sampled

This removes transformed-reward staleness exactly:

$$
g_t^{(k)}
=
B_t-\eta_kE_t.
$$

The physical transition

$$
(s_t,a_t,B_t,E_t,s_{t+1})
$$

remains valid when \(\eta\) changes because \(\eta\) changes the optimisation criterion, not the environment transition. However, DR-1 found no primary paper presenting this as a validated fractional-DQN replay protocol. It is a sound algebraic adaptation, not a reproduced method. 

### D. Clear and regenerate replay after every accepted \(\eta\) update

This also eliminates mixed-\(\eta\) labels and additionally removes the old policy’s replay distribution. DR-1 found no published comparison establishing this as the canonical treatment, but it is the most conservative choice here because your transitions are inexpensive to regenerate. 

### Recommended protocol

Use **both raw storage and a fresh buffer at each outer iteration**:

1. Freeze \(\eta=\eta_k\).
2. Clear replay.
3. Synchronise the target network from the online network.
4. Reset optimiser moments.
5. Generate fresh transitions.
6. Train only against \(B-\eta_kE\).
7. Freeze the greedy policy.
8. Run a separate evaluation batch.
9. Update \(\eta\) from the pooled evaluation totals.
10. Begin a new phase.

Warm-starting the network weights from the preceding \(\eta\) phase is acceptable as an initialisation choice. It does not create a stale reward label, but it does mean the initial function represents the previous Bellman fixed point. For the thesis, include at least one cold-start-per-\(\eta\) ablation or a comparison against full reinitialisation. Resetting the optimiser and target network is the minimum protection against carrying the preceding loss geometry into the new phase.

Raw-\(B,E\) replay without clearing should be a secondary efficiency ablation, not the sole confirmatory protocol. It is algebraically defensible but lacks a published deep fractional-replay validation.

The estimate used to update \(\eta\) must come from **fresh on-policy greedy evaluation**, not the replay buffer. Off-policy replay frequencies generally do not estimate \(J_B(\pi_k)\) and \(J_E(\pi_k)\) for the deployed policy without an off-policy evaluation procedure. The appropriate sample estimator for the declared endpoint is

$$
\widehat{\rho}(\pi_k)
=
\frac{\sum_i B_i}{\sum_i E_i},
$$

not

$$
\frac1N\sum_i\frac{B_i}{E_i}.
$$

The pooled quotient is the natural estimator of the ratio of expectations; the literature does not treat the finite-batch quotient itself as a per-transition TD loss. 

## 3. How to score a demonstrator action

A sound ratio-consistent local comparison exists. What does **not** exist in the surveyed literature is a validated use of that comparison as a DQfD-style imitation gate.

Let \(a_L\) be the learner’s proposed action and \(a_D\) the demonstrator’s action. At a fixed \(\eta\), define

$$
\Delta_\eta(s;a_D,a_L)
=
Q_\eta(s,a_D)-Q_\eta(s,a_L).
$$

If component values are available under one common continuation policy,

$$
\begin{aligned}
\Delta_\eta
={}&
\left[
Q_B^{\pi_\eta}(s,a_D)
-
Q_B^{\pi_\eta}(s,a_L)
\right]\\
&-
\eta
\left[
Q_E^{\pi_\eta}(s,a_D)
-
Q_E^{\pi_\eta}(s,a_L)
\right].
\end{aligned}
$$

Then the demonstrator action is locally preferred for the current Dinkelbach subproblem when

$$
\Delta_\eta>0.
$$

At \(\eta=\rho(\pi)\), the corresponding policy-gradient quantity is the ratio advantage

$$
A_\rho^\pi(s,a)
=
A_B^\pi(s,a)-\rho(\pi)A_E^\pi(s,a),
$$

up to the common positive factor \(1/J_E(\pi)\). Suttle et al. derive this structure for ratio actor–critic updates. It is a local policy-improvement direction under the current-policy semantics, not a guarantee that replacing the complete policy by a demonstrator will improve its global ratio. ([Proceedings of Machine Learning Research][3]) 

A stronger policy-level statement is available. For two complete policies \(\pi_D\) and \(\pi\), with \(J_E(\pi_D)>0\),

$$
\rho(\pi_D)>\rho(\pi)
$$

is equivalent to

$$
J_B(\pi_D)-\rho(\pi)J_E(\pi_D)>0.
$$

For a one-state intervention, this can be applied to “take \(a_D\) now and then follow a specified common continuation policy.” The common continuation condition matters. A comparison using independently optimal \(Q_B^\star\) and \(Q_E^\star\) does not meet it.

### Does this justify an imitation gate?

No published ratio-aware demonstration gate was found. In particular, DR-1 found no fractional-RL paper using

$$
A_B-\rho A_E
\quad\text{or}\quad
Q_B-\eta Q_E
$$

to gate a supervised regression loss, behavioural-cloning loss, or DQfD large-margin term. 

Therefore the smallest defensible architecture should contain **no supervised demonstrator loss**. A demonstrator can still be used in three non-claim-bearing ways:

* as an evaluation baseline;
* as a behaviour policy for collecting ordinary raw-\(B,E\) transitions;
* as initial replay data trained with exactly the same TD loss as every other transition.

That is experience provision, not a claim that the demonstrator action has been certified superior.

If a ratio-aware Q-filter is later introduced, it must be presented as a new component. Its evaluation would need direct rollout-based labels or audits, gate-open rates over training, calibration of \(\Delta_\eta\), and ablations against no imitation, unconditional imitation, and replay seeding alone.

## 4. Does two-critic learning avoid the predicted Q-filter failure?

**It avoids the original reward mismatch only if the critics and \(\eta\) correctly represent the declared ratio objective. It does not avoid the self-disabling Q-filter mechanism. It relocates it.**

Under the old scalar reward, the filter asks whether the demonstrator is superior according to the wrong objective. Replacing that critic with \(Q_\eta\) changes the criterion to the correct Dinkelbach subproblem:

$$
Q_B-\eta Q_E.
$$

That is a genuine correction to objective alignment.

But the control loop remains:

1. Bellman learning moves the critic toward the current transformed-reward fixed point.
2. The gate consults that same critic.
3. If the critic places \(a_D\) below the learner action, the supervised term turns off.
4. Once off, nothing in the imitation term can repair a mistaken ranking.
5. Subsequent Bellman updates reinforce the policy selected by the critic.

With two component critics, the relevant gate is

$$
\widehat{\Delta}_\eta
=
\widehat{\Delta Q_B}
-
\eta\widehat{\Delta Q_E}.
$$

Its failure sources become:

* error in \(Q_B\);
* error in \(Q_E\);
* cancellation error when two large terms are subtracted;
* an inaccurate or changing \(\eta\);
* different continuation-policy semantics across the heads;
* out-of-distribution error on demonstrator actions;
* premature gate closure before either critic is calibrated.

Changing \(\eta\) can also legitimately reverse a demonstrator ranking. An action that is favoured when bits are weighted heavily can be rejected after the fractional parameter rises. Consequently, “the demonstrator was once accepted” supplies no persistence guarantee.

If each head uses its own optimal Bellman action, the situation is worse: the combined gate may not represent any coherent policy. If both heads use the same combined action, the gate is coherent, but it is still critic-dependent and can disable itself because of estimation error.

Thus the two-critic formulation:

* **does correct the old objective’s semantics**, provided it is implemented with shared continuation actions;
* **does not guarantee retention of demonstrations**;
* **does not solve premature Q-filter shutdown**;
* introduces an additional two-estimator subtraction problem.

For that reason, a Q-filter should not be bundled into the first ratio-correct architecture. First establish that the ratio Bellman target itself beats `MAX_NOMINAL_GAIN` on untouched pooled-EE evaluation.

## 5. Smallest defensible implementation

### 5.1 Replay record

Store one record as

```text
(
    state,
    action,
    bits_increment,
    joules_increment,
    next_state,
    terminal,
    next_legal_action_mask,
    remaining_horizon
)
```

`eta_version` may be stored for audit purposes, but it must not determine the reward label.

Do not store:

```text
bits / joules
B - eta_old * E
precomputed TD target
old scalar_reward
r1/r2/r3 weighted sum
```

`bits_increment` and `joules_increment` must be exactly the additive quantities whose sums reproduce the evaluator’s numerator and denominator. The accounting unit must be consistent. In particular, a system-level joule term must not be accidentally duplicated a different number of times from system-level bits when per-user samples are constructed.

### 5.2 Network

Replace the three objective heads with **one Q head of 28 outputs**:

$$
Q_{\eta_k}(s,a)
=
\mathbb E\!\left[
\sum_{\tau=t}^{T-1}
\left(
\widetilde B_\tau
-
\widetilde\eta_k\widetilde E_\tau
\right)
\,\middle|\,
s_t=s,a_t=a
\right].
$$

Use one optimiser and one `zero_grad/backward/step` sequence.

Because bits and joules have very different numerical scales, use fixed positive normalisers \(B_0,E_0\):

$$
\widetilde B_t=\frac{B_t}{B_0},
\qquad
\widetilde E_t=\frac{E_t}{E_0},
\qquad
\widetilde\eta_k=\eta_k\frac{E_0}{B_0}.
$$

Then

$$
\widetilde B_t-\widetilde\eta_k\widetilde E_t
=
\frac{B_t-\eta_k E_t}{B_0},
$$

so normalisation changes only the positive overall scale, not the optimal policy. Keep \(B_0,E_0\) fixed from a calibration set; do not adapt them separately for each experimental arm.

### 5.3 TD target

For the actual 10-step finite-horizon ratio objective, use an undiscounted proper episodic target:

$$
g_t
=
\widetilde B_t-\widetilde\eta_k\widetilde E_t,
$$

$$
y_t
=
g_t
+
(1-d_t)
\max_{a'\in\mathcal A(s_{t+1})}
Q^-_{\eta_k}(s_{t+1},a').
$$

Here \(d_t\) is the terminal indicator and \(\mathcal A(s')\) is the legal action set.

A discount below one changes the criterion to a discounted ratio surrogate. It should not be introduced merely because ordinary DQN uses \(\gamma<1\). The FQL deep experiment found in DR-1 uses a discounted approximation, while its exact average-objective relation is asymptotic rather than an exact finite-\(\gamma\) identity. 

Because finite-horizon optimal values generally depend on time remaining, include the decision index or remaining horizon in the state unless episode termination is purely an artificial data cut and the intended process is continuing. If the 10-step boundary is artificial rather than a real reset, the correct architecture changes toward continuing reward-per-cost/differential learning; terminalising every tenth step would optimise another objective.

Do not bundle Double DQN, n-step returns, prioritisation, or imitation into this first repair. They can be tested later. The causal question in the first experiment should be whether replacing the misaligned scalarisation by the ratio-consistent Bellman signal fixes the endpoint.

### 5.4 Action selection

During collection:

$$
a_t=
\begin{cases}
\text{random legal action}, & \epsilon\text{-exploration},\\[3pt]
\displaystyle
\arg\max_{a\in\mathcal A(s_t)}
Q_{\eta_k}(s_t,a), & \text{otherwise}.
\end{cases}
$$

At deployment:

$$
a_t^\star
=
\arg\max_{a\in\mathcal A(s_t)}
Q_{\eta_{\rm final}}(s_t,a).
$$

Apply the mask before every online-network and target-network maximisation. The final \(\eta\) is frozen at deployment.

Do **not** use

$$
\arg\max_a\frac{Q_B(s,a)}{Q_E(s,a)}.
$$

### 5.5 Outer update

For iteration \(k\):

1. Hold \(\eta_k\) fixed for the entire inner DQN phase.
2. Train to a predeclared plateau or fixed update budget.
3. Freeze exploration and network weights.
4. Evaluate the greedy masked policy on fresh episodes.
5. Accumulate global totals:

$$
\widehat J_B^{(k)}
=
\sum_{\rm eval} B_t,
\qquad
\widehat J_E^{(k)}
=
\sum_{\rm eval} E_t.
$$

6. Set

$$
\eta_{k+1}
=
\frac{\widehat J_B^{(k)}}{\widehat J_E^{(k)}}.
$$

7. Also report the Dinkelbach residual under the old parameter:

$$
\widehat F_k
=
\widehat J_B^{(k)}
-
\eta_k\widehat J_E^{(k)}.
$$

8. Stop only after both the quotient and residual stabilise under a prespecified statistical tolerance.

Use a calibration or validation seed panel for outer updates. Keep the final test panel untouched. Initialising \(\eta_0\) with the pooled EE of `MAX_NOMINAL_GAIN` on a separate calibration panel is reasonable and gives the parameter an appropriate scale; it must not be estimated on the final test panel.

### 5.6 Optional two-head research arm

A two-head version can later be tested as a **novel ablation**, provided both heads share the same continuation action:

$$
a^\star(s')
=
\arg\max_{a'\in\mathcal A(s')}
\left[
Q_B(s',a')-\eta Q_E(s',a')
\right],
$$

$$
y_B
=
B_t+(1-d_t)Q_B^-(s',a^\star),
$$

$$
y_E
=
E_t+(1-d_t)Q_E^-(s',a^\star).
$$

The deployment score remains

$$
Q_B(s,a)-\eta Q_E(s,a).
$$

This preserves common-policy semantics. It may provide diagnostics about whether an action wins through bits or energy, but it does not remove the need to retrain when \(\eta\) changes because the shared continuation policy changes. It also adds approximation and conditioning risks. It should not precede the one-head benchmark.

## What should be removed from the present trainer

For the primary ratio experiment:

* remove the \(0.5r_1+0.3r_2+0.2r_3\) training target;
* remove the three independently stepped Q-head optimisers;
* remove the uncalibrated `scalar_reward` from model selection;
* do not make handover count or occupancy an auxiliary reward;
* retain those quantities only as evaluation diagnostics unless they become explicit physical contributions to \(B\) or \(E\).

If service, outage, or handover limits are genuine requirements, encode them as:

1. feasibility/action masks;
2. explicit service constraints;
3. separately declared non-inferiority endpoints.

Adding them back as arbitrary reward weights would recreate the same objective mismatch. A constrained fractional objective is possible, but it is a different algorithmic problem from unconstrained \(\max J_B/J_E\).

## Confidence and unresolved points

### High confidence

* The established core is \(B-\eta E\), not independently optimal \(Q_B/Q_E\).
* The full two-critic masked replay-DQN recommendation is unsupported as a published standard method. 
* Pretransformed rewards or TD targets must not survive an \(\eta\) change.
* Raw \(B,E\) must be retained so the current transformed signal can be reconstructed.
* The outer quotient must use pooled numerator and denominator totals.
* A ratio-consistent local action comparison exists at fixed \(\eta\).
* No published ratio-aware imitation or margin gate was found.
* Two critics relocate rather than eliminate Q-filter self-disabling.
* The smallest defensible primary learner is one masked \(Q_\eta\) head.

### Unresolved by the literature

* There is no general convergence theorem for nonlinear target-network DQN with replay, changing \(\eta\), and dynamic action masks.
* No primary study was found comparing raw replay reuse, replay relabelling, and fresh-buffer regeneration for fractional DQN.
* Dinkelbach’s classical guarantee assumes exact inner optimisation; a trained neural DQN supplies only an approximate, stochastic inner solution.
* Warm-start versus cold-start behaviour across \(\eta\) phases is an empirical question.
* The existing per-user independent argmax factorisation may itself prevent optimisation of a coupled system-level objective. Dinkelbach corrects the scalar objective but does not create coordination among users.
* Whether the ten-step boundary is a true finite horizon or merely a training truncation must be fixed explicitly.
* A service/QoS requirement, if mandatory, must be specified as a constraint rather than inferred from the EE ratio.
* Any two-head decomposition or ratio-aware demonstration filter would be a new contribution requiring its own evidence.

The resulting thesis claim should therefore be narrow:

> **The project applies a Dinkelbach-transformed reward-per-energy objective to a discrete masked DQN. It introduces a conservative raw-component replay and outer-evaluation protocol to prevent quotient-parameter staleness.**

It should not claim to be applying an established two-critic ratio-DQN architecture.

[1]: https://pubsonline.informs.org/toc/mnsc/13/7?utm_source=chatgpt.com "Management Science: Vol 13, No 7"
[2]: https://arxiv.org/html/2312.10418v2 "Fractional Deep Reinforcement Learning for Age-Minimal Mobile Edge Computing"
[3]: https://proceedings.mlr.press/v139/suttle21a/suttle21a.pdf "Reinforcement Learning for Cost-Aware Markov Decision Processes"
