# Cross-model review — should a declared endpoint be changed, and is the proposed design sound?

You are a fresh-context independent reviewer. Answer from the evidence below and from the
literature. Do not assume the controller who assembled this is right; it has issued
**nine errata** in two days withdrawing its own claims, including comparing a beam count
against an energy efficiency, declaring a research line closed on the existence of
receipts when no conclusion had ever been written, and an algebra error in its own physics
argument. Its previous framing was rejected 6/6 by independent reviewers, and a tenth
review rejected its last proposal outright.

## The system

LEO satellite beam handover. A multi-objective DQN (MODQN), three reward heads combined as
`0.5*r1 + 0.3*r2 + 0.2*r3`: `r1` = system energy efficiency (eq. 3.25, `sum x*eta`),
`r2` = negative handover cost (stay 0 / intra-satellite −0.5 / inter-satellite −1.0),
`r3` = negative beam occupancy `−U_{b_u}`.

**Declared primary endpoint**: pooled EE = pooled decoded bits / pooled system joules, a
ratio of sums, never a mean of ratios.

**The owner's requirement, verbatim**: a RIS-style catfish (or DQfD-family) algorithm plus
one or more additional catfish, that **raises EE**.

## Established measurements (each by a separate agent; verify what carries weight)

1. **Catfish is a training-time experience-stimulation mechanism**, five parts: external
   solver seeds a catfish replay memory; EE-threshold buffer separation; asymmetric
   discounts; 70/30 periodic batch intervention; competitive reward
   `r^C = r + eta(r^CF − r^M)`. Only the main agent is deployed. **The project's C1/C2/C3
   are not this** — they are a decomposition of one scalar objective (`C1 + C3 = dF`
   identically). The stage-C learner is not an RL learner at all (`learner.py:279-280`:
   "No reward, next state, target network, discount, or bootstrap exists").
2. **Published standing of the five catfish mechanisms**: (i) solver-seeded replay = RBS,
   and this exact parameterisation is **DQfD's own negative arm** ("naively adding … can
   sometimes be detrimental"); (ii) absolute-EE-threshold buffer split — **not found** as
   a reproduced mechanism, the mature form is SIL's `(R − V(s))_+`, relative to the
   learner's own value; (iii) asymmetric discounts, two agents — **no counterpart**;
   (iv) 70/30 = HER, one of DQfD Fig. 2's **two worst arms**, and R2D3 swept 120 agents to
   an optimum ratio of **1/256 ≈ 0.39%**, ~77x below 30%; (v) ACRM — **no counterpart**,
   not potential-based so Ng/Harada/Russell policy invariance does not apply. The RIS
   paper specifies **exactly one runnable number** (the 70/30 mix); the other five are
   unspecified.
3. **No published work runs more than one demonstration buffer with an ablation behind
   it.** R2D3 had three human experts and **pooled them into one buffer**. No paper sweeps
   the *number* of demonstrators.
4. **On the trained objective, no expressible myopic rule beats the learner.** Best arm
   `GREEDY_R1R2` +0.8750 ± 0.0236 vs trained `e6b063ef…` +0.8859 ± 0.0190; against the
   checkpoint's plateau mean +0.9257 the gap is −0.0507. So on that objective **there is
   no demonstrator**, and demonstration-seeded RL has nothing to seed.
5. **On the declared endpoint, the ordering reverses.** Pooled EE (ratio of sums, 24
   episodes x 10 steps, byte-identical frozen weights, matched RNG stream positions):
   `MAX_NOMINAL_GAIN` **111,553,182.85** bit/J vs trained **93,137,893.02** — **+19.8%,
   13.2 sem**, winning on **both** bits (1.146x) and joules (0.957x), service 0.9981 vs
   0.9988, handover rate 0.7117 vs 0.2796. The two arms that won on the trained objective
   are the **worst non-random arms** on pooled EE.
6. **That gap survives its strongest attack and widens.** A reviewer argued it was the
   segment entry anchor (`step.py:786-808` resets power on any association change, so a
   high-churn rule re-anchors at maximal gain by construction — the "renewal premium").
   Ablating the anchor, with a positive control (100.0% of served users at exactly
   `p0` = 0.825 W) and a placebo (bit-identical reproduction): ratio **1.1975 → 1.2222**.
   The **bits ratio is invariant to the ablation within 0.05%** (1.1468 → 1.1463) — the
   gap lives in the numerator and is a property of the decision rule. Per-arm effects run
   opposite to the prediction: removing the anchor **helps** the high-churn arm (+0.99%)
   and hurts the low-churn ones (−1.05%, −1.27%, −2.75%).
7. **`r2` prices something that costs zero joules.** `grep -ci handover` is 0 in
   `link_budget.py`, `energy_efficiency.py`, `interference.py`, `service.py`. The one
   physical coupling runs the other way: a handover breaks the power segment and resets
   the link to `p0` = 0.825 W instead of an aged segment's up to 1.65 W. **Handovers save
   energy in this simulator.**
8. **The proposal to move the handover cost into the numerator was rejected, with
   arithmetic.** `dt` = 30.08 s, so a sourced 142 ms interruption destroys 0.472% of a
   user-step's bits; applied at its most favourable it moves the ratio 1.19771 → 1.19526,
   **closing 1.2% of the gap**. Closing it would need **10.38 s per handover, 68-167x the
   sourced value**, which the project's provenance matrix explicitly forbids. In calibrated
   units one handover currently costs +13.71% of episode `r1` to break even; under the
   proposal it would cost +0.047% of bits — **a ~290x cut, i.e. a near-deletion of `r2`.**
   (The 62/142 ms constants were independently confirmed against **3GPP TS 38.133
   Annex A.14.2**.)
9. **`r3 = −U` is the wrong instrument, but the controller's reason was wrong.** It argued
   `R = (B/U)log2(1+gamma)` makes a beam's rate U-invariant. False when SINRs differ:
   `R_beam = B * mean_u SE_u`, and the marginal effect of admitting u is
   `B(SE_u − mean_SE_b)/(U_b+1)`, negative exactly in the crowding case. Also
   `interference.py:10-14`: interference is z-gated and load-unweighted, so lighting beams
   costs everyone SINR — spreading is EE-negative, the opposite sign to what `r3` rewards.
   Separately, the **sealed V0.25 successor already adds occupancy → required-power and
   removes the entry anchor**, which would make `r3`'s premise true.
10. **The V0.25 stage-C route is closed** by a pre-declared kill rule: exact C1 loses to
    `RSS_MAX` by −6.450% [−11.52, −1.26] and to `S0_TOP1` by −6.105% [−11.24, −0.86],
    losing on EE, service and attainment simultaneously; C3's oracle marginal is −1.775%
    with an interval covering zero; 83 of 93 C1 choices are simply one of two `s0`
    proposals.
11. **Two reward defects, independent of everything above**: an outage is the **maximum**
    of both bounded heads (r2 = 0, r3 = 0 when unserved, while every served step is <= −1
    for r3), and power-infeasible steps enter replay carrying that free ride; and the
    logged `scalar_reward` is **uncalibrated** while training uses the calibrated vector,
    so the headline curve is numerically `0.5*r1` and r2+r3 move it by one part in 10^6.
12. **Cost**: 1.5869 s per training episode, so 3000 episodes = 1.32 h. Cost is not a
    constraint. The trainer is DQfD-shaped (one agent, one buffer, one `update()`), and
    the delta for a DQfD is bounded at ~470-640 lines across six named files — but it has
    **none** of n-step returns, a supervised/margin loss term, prioritized replay with
    per-sample weights, a pre-training phase, double-DQN, or L2.

## The decision

**Should the declared endpoint be changed** from unconstrained pooled EE to **pooled EE
subject to handover-rate and service constraints** (a CMORL formulation, which this
project's earlier outside review also recommended)?

The argument for: on the current endpoint a one-line rule beats the trained policy by
22.2%, so the endpoint and the trained objective are anti-aligned, and no amount of
demonstration-seeded RL fixes a policy trained on the wrong scalar. Under a constrained
endpoint, `MAX_NOMINAL_GAIN` becomes a demonstrator that is **optimal on the objective but
infeasible on the constraint**, and a budgeted rule becomes one that is **feasible but far
worse on the objective** — so neither can do what the learner is asked to do, which is the
definition of a job for a learner, and it gives each catfish a measured reason to exist.

The argument against: changing a declared endpoint after seeing a result that went the
wrong way is exactly how endpoints get selected by outcome. **Say plainly whether this
crosses that line.**

## The proposed design, to review on its merits

Backbone **DQfD, not the RIS catfish** (RIS catfish retained as a faithful comparator
arm). One **physical** replay store with `source_id` logical partitions and source-aware
sampling — not one buffer per catfish. Losses 1-step TD + n-step + L2, with the
**supervised margin loss gated by a Q-filter / positive-advantage test** (Nair) rather
than fired unconditionally; the Q-filter is also offered as the published, state-relative
form of the RIS catfish's absolute EE-threshold split. Demo ratio swept from a low
starting value, not fixed at 30%. One deployed main agent.

Two specialists:
- **CF-EE** — full-horizon ratio-consistent EE specialist. `MAX_NOMINAL_GAIN` as the cheap
  expressible floor; the formal version a **Dinkelbach local search with an adaptive
  per-anchor `eta_0 = B_H(a0)/E_H(a0)`**, not a fixed global `eta_ref` (a fixed one is
  already known not to preserve EE ordering).
- **CF-GUARD** — pooled-EE specialist under a **declared hysteresis margin** and the QoS
  guards, i.e. switch only if the predicted horizon gain exceeds a margin from a
  pre-declared grid.

A third, `CF-PAYLOAD` (incremental payload power: active beams, active satellites, per-beam
max required RF power, interference, mean spectral efficiency), is held back because the
active-beam set and other users' current choices are **not in the per-user observation**,
so a set-level specialist may be unimitable by a per-user argmax policy.

Arm ladder, two rounds rather than a factorial. Round 1 fixes CF-EE and compares
demonstration *utilisation*: `D0` none / `D1` replay-buffer spike only / `D2` faithful RIS
catfish / `D3` full DQfD / `D4` Q-filtered DQfD. Round 2 fixes the winner and compares
*sources*: `S0` none / `S1` CF-EE / `S2` CF-EE + CF-GUARD / `S2-unlabelled`. A supervised
representability gate (behaviour-cloning / ranker on the same observation, OOS top-1 and
action regret) runs **before** any trainer modification. All arms share a **corrected
no-demonstration baseline**; the original frozen checkpoint is an external historical
reference only, never the causal control.

## What I need from you

1. **Rule on the endpoint change**: legitimate, or outcome-selected? If legitimate, what
   must be fixed in advance so it cannot become outcome-selected — specifically, **how
   should the constraint thresholds be set, from what external source, and what would make
   a choice of threshold illegitimate?**
2. **Attack the design.** Its weakest component, and the single measurement that would
   show it solves nothing.
3. **Is the two-specialist structure real or is CF-GUARD a relabelling of CF-EE?** Note
   finding 8: if CF-GUARD's cost channel is the interruption, it is a ~1% effect and the
   two specialists may produce near-identical action distributions. Say what CF-GUARD must
   be built on instead for the pair to be genuinely complementary, and what test decides it.
4. **Ratio-objective RL.** For a finite-horizon or average-reward MDP, what is the correct
   way to maximise pooled bits / pooled joules? Compare Dinkelbach policy iteration,
   reward-per-cost / semi-Markov formulations, average-reward RL, two-critic ratio
   optimisation (`Q_B`, `Q_E` with `eta_{k+1} = sum B(pi_k)/sum E(pi_k)`), direct ratio
   policy gradient, and constrained MDPs. Which is compatible with an **off-policy,
   discrete, action-masked DQN**, and how is a per-transition training signal and a
   demonstrator advantage computed under it? **Cite papers.**
5. **Novelty.** Given that multiple heterogeneous demonstrators, Q-filtering, imperfect-
   demonstration filtering and demonstration-guided MORL are all published, **is there a
   defensible contribution here at all**, and if so state it in one sentence. If the honest
   answer is that the contribution is the integration and the measurement rather than the
   mechanism, say so.

Give a verdict — **PROCEED**, **PROCEED WITH CHANGES** (name them), or **REJECT** (say what
to do instead) — with your three strongest objections ranked, each with the evidence that
would settle it. Separate what you verified from what you assert. Be concrete about
numbers; do not restate the brief back.
