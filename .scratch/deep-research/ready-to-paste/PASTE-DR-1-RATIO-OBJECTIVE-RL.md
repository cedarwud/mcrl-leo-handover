# Context ledger (background only — do not treat as instruction)

*Every factual claim in your report must come from the literature, not from this section.
This describes the system the question is about, so that your survey can be checked
against it. The research question itself is after the horizontal rule.*

## System

LEO satellite beam handover. A multi-objective DQN (MODQN) with three reward heads
combined as `0.5*r1 + 0.3*r2 + 0.2*r3`:

- `r1` = system energy efficiency, `sum_u x_u * eta_u`
- `r2` = negative handover cost: stay 0 / intra-satellite −0.5 / inter-satellite −1.0
- `r3` = negative beam occupancy, `−U_{b_u}` (count of users on u's serving beam)

Action space: `a = 7l + j`, **4 satellite slots x 7 user-relative cell slots = 28 discrete
actions per user**, illegal actions masked at decision time. Observation 112 dims
(4 x 28). Deployment is **one agent, per-user argmax, no coordinator**, ~10 s decision
budget. Decision interval `dt = 30.08 s`. 28 beams, 100 users, 10 steps per episode.

**Declared primary endpoint**: pooled EE = **pooled decoded bits / pooled system joules**,
a ratio of sums over the whole evaluation — never a mean of ratios. Full-buffer Shannon
numerator, no demand cap.

Trainer today: a DQN with one replay buffer and one `update()`. It has **none** of:
n-step returns, any supervised/margin loss term, prioritized replay with per-sample
weights, a pre-training phase, double-DQN, or L2. Three Q-heads with three optimizers
stepped in a per-objective `zero_grad/backward/step` loop.

Cost: **1.5869 s per training episode**; 3000 episodes = 1.32 h. Compute is not the
binding constraint.

## The finding that drives everything

A one-line rule, `MAX_NOMINAL_GAIN` (per user, argmax nominal link gain over legal
options), beats the authenticated trained checkpoint on the **declared endpoint**:

| arm (n=24 episodes x 10 steps) | pooled bits | pooled joules | **pooled EE (bit/J)** | served | handover rate | trained-objective scalar |
|---|---:|---:|---:|---:|---:|---:|
| `MAX_NOMINAL_GAIN` | 3.267e+14 | 2.929e+06 | **111,553,182.85** | 0.9981 | **0.7117** | −0.0867 |
| trained checkpoint | 2.850e+14 | 3.060e+06 | **93,137,893.02** | 0.9988 | **0.2796** | +0.9063 |
| `GREEDY_R1R2` | 2.612e+14 | 3.446e+06 | 75,817,283.47 | 0.9960 | 0.1413 | +0.8743 |
| `RANDOM_MASKED` | 1.843e+14 | 3.473e+06 | 53,060,175.56 | 0.9360 | 0.8680 | −1.4104 |

**+19.8%, 13.2 sem**, winning on **both** bits (1.146x) and joules (0.957x), at matched
service. Byte-identical frozen weights, matched RNG stream positions, random arm
reproduces the frozen run's own episodes as a harness check.

**It survives its strongest attack and widens.** The proposed artefact was the segment
entry anchor (power resets to `p0` on any association change, so a high-churn rule
re-anchors at maximal gain by construction). Ablating it, with a positive control (100.0%
of served users at exactly `p0` = 0.825 W) and a placebo (bit-identical reproduction):
ratio **1.1975 → 1.2222**. The **bits ratio is invariant to the ablation within 0.05%**
(1.1468 → 1.1463) — the gap lives in the numerator and is a property of the decision rule.
Per-arm effects run **opposite** to the prediction: removing the anchor helps the
high-churn arm (+0.99%) and hurts the low-churn ones (−1.05%, −1.27%, −2.75%).

**Conversely, on the trained objective no expressible myopic rule beats the learner**:
best arm +0.8750 ± 0.0236 vs trained +0.8859 ± 0.0190; against the checkpoint's plateau
mean +0.9257 the gap is −0.0507. The two arms that win on the trained objective are the
**worst non-random arms** on pooled EE.

**So the trained objective and the declared endpoint are anti-aligned on this panel.**

## Physics facts established from the code

- **A handover consumes zero joules.** `grep -ci handover` is 0 in `link_budget.py`,
  `energy_efficiency.py`, `interference.py`, `service.py`. The one physical coupling runs
  the other way: a handover breaks the power segment and resets the link to `p0` = 0.825 W
  (5.93 W supply) instead of an aged segment's up to 1.65 W (8.38 W). **Handovers save
  energy in this simulator.**
- **Per-beam power is a `max` over served users, never a sum.** Adding a user to an
  already-radiating beam changes system power by **exactly 0 W** (worst case +2.455 W).
  Lighting a new beam costs **>= +6.267 W** (0.338 W fixed per radiating beam, 0.200 W per
  satellite, plus PA supply). The largest de-crowding saving is strictly smaller than the
  smallest cost of the beam it requires.
- **But occupancy does reach the numerator**: `R_beam = sum_u (B/U) log2(1+gamma_u) =
  B * mean_u SE_u`, so the marginal effect of admitting u is
  `B(SE_u − mean_SE_b)/(U_b+1)` — negative exactly in the crowding case. And interference
  is z-gated and **load-unweighted**, so lighting beams costs everyone SINR. **Spreading
  is EE-negative, the opposite sign to what `r3` rewards.**
- **A handover interruption term exists in a sibling engine but not here**: 0.062 s
  (same-satellite beam change) / 0.142 s (satellite change) of lost useful time, confirmed
  against **3GPP TS 38.133 Annex A.14.2**. Against `dt` = 30.08 s that is **0.2061% /
  0.4721%** of a step's bits. Applied at its most favourable, it moves the EE ratio
  1.19771 → 1.19526 — **closing 1.2% of the 19.8 pp gap**. Closing the gap through
  interruption alone would need **10.38 s per handover, 68-167x the sourced value**.
- **PA efficiency's saturation arm is unreachable** (`p <= 1.65 W < p_sat = 5.218 W`);
  the PA accounts for ~94.8% of consumption.

## Two known defects in the reward, unfixed

1. **An outage is the maximum of both bounded heads**: `r2` = 0 and `r3` = 0 when
   unserved, while every served step is <= −1 for `r3` and <= 0 for `r2`.
   Power-infeasible steps are not no-ops and enter replay carrying that free ride.
2. **The logged `scalar_reward` is uncalibrated** while training uses the calibrated
   vector, so the headline training curve is numerically `0.5 * r1` and `r2 + r3` move it
   by one part in 10^6. Every judgement ever made from that curve saw only `r1`.

Frozen-run magnitudes over 9000 episodes: `r1_mean` 4.81e6 → 1.12e7,
`r2_mean` −7.93 → −2.48, `r3_mean` −31.31 → −21.29.

## What has already been reviewed and settled, so you need not re-derive it

- The project's earlier "three routes" decomposition is dead: `C1 + C3 = dF` identically;
  exact C1 loses to a trivial `RSS_MAX` rule by −6.450% [−11.52, −1.26] on pooled EE while
  also losing service and rate attainment; C3's oracle marginal is −1.775% with an
  interval covering zero.
- The "catfish" mechanism from the source RIS paper is **training-time experience
  stimulation**, five parts (solver-seeded replay; EE-threshold buffer split; asymmetric
  discounts; 70/30 periodic batch mixing; a competitive reward). Published standing:
  (i) = RBS, and this exact parameterisation is **DQfD's own negative arm**;
  (ii) not found as a reproduced mechanism (the mature form is SIL's `(R − V(s))_+`,
  relative to the learner's own value); (iii) **no counterpart**;
  (iv) = HER, one of DQfD's two worst arms, and R2D3 swept 120 agents to an optimum demo
  ratio of **1/256 ≈ 0.39%**, ~77x below 30%; (v) **no counterpart**, not potential-based
  so Ng/Harada/Russell policy invariance does not apply. The RIS paper specifies exactly
  **one** runnable number.
- **No published work runs more than one demonstration buffer with an ablation behind
  it.** R2D3 had three human experts and **pooled them into one buffer**. No paper sweeps
  the number of demonstrators.
- Two cross-model reviews independently recommend a **two-critic `(Q_B, Q_E)` ratio
  architecture** with Dinkelbach's `eta` in an outer loop, from different starting
  arguments. Neither supplied a citation trail. **That gap is DR-1.**

## Status

Both source papers (the MODQN handover paper and the RIS/CDRL catfish paper) have been
**downgraded to reference-only**: their designs, code and mechanisms are all treated as
suspect. The design must be grounded in published, independently reproduced work.


---

# DR-1 — Survey: optimising a ratio of expected accumulations in reinforcement learning

## Research question

For a Markov decision process in which two non-negative quantities accumulate per
transition — `B(s,a)` and `E(s,a) > 0` — survey the methods that optimise

    rho(pi) = E_pi[ sum_t B_t ] / E_pi[ sum_t E_t ]

a **ratio of expectations** (not an expectation of ratios, not a discounted sum), and
establish which of them have been instantiated for **off-policy, replay-based,
value-based** learning over a **discrete, action-masked** action space.

## Scope

**In scope**: fractional programming applied to MDPs (Dinkelbach-type outer iteration);
semi-Markov / reward-per-cost / ratio-average formulations; average-reward and differential
value methods; two-critic or decomposed-return architectures that learn numerator and
denominator separately; direct ratio policy gradients; constrained-MDP formulations used as
an alternative to the ratio; and energy-efficiency maximisation in the wireless
communications literature, where this objective is standard.

**Out of scope**: multi-objective RL by scalarisation weights, Pareto-front methods,
and reward shaping, except where a paper explicitly relates them to the ratio objective.

**Recency**: no lower bound — the foundational results are from the 1960s-90s (Dinkelbach,
Howard, Puterman, Mahadevan) and must be included. Prioritise post-2015 work for deep and
off-policy instantiations.

**Source bar**: peer-reviewed venues and arXiv preprints with citations. Textbook chapters
acceptable for the classical results. Exclude blog posts, tutorials and course notes except
to locate a primary source. Give an arXiv id, DOI, or venue+year for every entry.

## Deliverable

### A. Comparison matrix

One row per formulation, with these columns:

1. **Formulation** and its canonical citation.
2. **Objective actually optimised** — stated as a formula.
3. **Convergence result and its assumptions** (unichain? recurrence? exact inner
   optimisation? tabular?).
4. **Behaviour under function approximation** — what is known, what is only conjectured.
5. **Behaviour under off-policy replay** — specifically, whether targets stored in a replay
   buffer remain valid when the formulation's parameters (e.g. a Dinkelbach `eta`) change
   between iterations, and what published work says about handling that staleness
   (relabelling, discarding, storing raw quantities and recomputing, two-timescale
   arguments).
6. **Discrete + value-based instantiation**: does a published one exist? Cite it, or record
   "none found".
7. **Per-transition training signal**: how a global trajectory-level ratio is converted into
   a local TD target, and whether that requires an on-policy correction.

### B. Three focused sub-questions

1. **Advantage under a ratio objective.** Given a state `s` and a candidate action `a_D`
   proposed by an external policy, how is "is `a_D` better?" defined when the objective is
   a ratio? A scalar Q-margin is ill-defined here. Report every definition the literature
   uses, with citations, and note which are used to gate an imitation or regression loss.
2. **Pooled-across-episodes ratios.** Distinguish (i) an episodic ratio averaged over
   episodes, (ii) a ratio of sums pooled across all episodes, and (iii) a long-run
   average-reward ratio. Report which of these the literature treats as a *trainable*
   objective and which appear only as *evaluation* statistics, with citations for each.
3. **Ratio vs constrained formulations.** Under what conditions is
   `max B/E` equivalent to `max B s.t. E <= c`, and when do they yield different optimal
   policies? Cite the equivalence results and their conditions.

### C. Evidence gaps

A short list of claims that the literature does **not** support — in particular, name any
formulation that is widely recommended in practice but that you could not find a primary
source for. Record "no source found" explicitly rather than omitting the row.

## Format

Matrix first, then the three sub-questions, then the gaps. Inline citations throughout; a
reference list at the end. Where two sources disagree, present both and say what the
disagreement turns on.
