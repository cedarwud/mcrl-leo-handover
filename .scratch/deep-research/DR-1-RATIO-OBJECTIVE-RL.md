# DR-1 — How do you actually maximise a ratio of sums with an off-policy discrete RL agent?

*Paste `00-EVIDENCE-LEDGER.md` above this.*

This is the architecture decision for the project and it is currently unsupported by any
citation trail. Two independent reviewers both recommended a two-critic formulation; both
asserted it rather than sourced it. **Settle it from the literature.**

## The question

A policy `pi` acts for a finite horizon `T` in a discrete, action-masked MDP. Two
non-negative quantities accrue per transition: `B(s,a)` (decoded bits) and `E(s,a) > 0`
(joules). The objective is

    rho(pi) = ( E_pi[ sum_t B_t ] ) / ( E_pi[ sum_t E_t ] )

a **ratio of expectations**, not an expectation of ratios, and not a discounted sum.
`E[B/E] != E[B]/E[E]`, and the Bellman optimality equation is linear in expectation, so
standard TD learning on any fixed scalar reward optimises the wrong functional.

**What is the correct formulation, and which one survives contact with an off-policy,
replay-based, action-masked, discrete-action deep Q-learner?**

## Formulations to compare — and I want the failure modes, not the sales pitch

For each: the objective it actually optimises, the convergence result and its assumptions,
what breaks under function approximation, what breaks under **off-policy replay**, and
whether a published **discrete, value-based** instantiation exists.

1. **Dinkelbach / fractional programming** (Dinkelbach 1967; Zappone & Jorswieck's
   energy-efficiency line). Solves `max_pi [ B(pi) − eta_k E(pi) ]` with
   `eta_{k+1} = B(pi_k)/E(pi_k)`. **The specific concern**: `eta_k` moving between outer
   iterations changes the scalar reward `r_t = B_t − eta_k E_t`, which **invalidates every
   target already in the replay buffer**. Is there published work on Dinkelbach with a
   *replay-based* inner solver? How is buffer staleness handled — relabelling, discarding,
   storing raw `(B, E)` and recomputing, a two-timescale argument?
2. **Semi-Markov / reward-per-cost / ratio-average MDPs** (Howard 1960; Puterman ch. 11;
   the SMDP literature). Treating `E_t` as a transition "duration" gives
   `h(s) = max_a [ B(s,a) − rho* E(s,a) + sum P h(s') ]`. What are the conditions
   (unichain? recurrence?) and do they plausibly hold for a 10-step episodic task? Is
   there a deep off-policy instantiation?
3. **Average-reward / differential RL** (Mahadevan 1996; Wan, Naik & Sutton 2021 and
   successors; differential Q-learning). Does the differential-value machinery extend to a
   *ratio* of two accumulations rather than a single average?
4. **Two-critic ratio optimisation**: learn `Q_B` and `Q_E` separately on raw `(B, E)`,
   select `argmax_a [ Q_B(s,a) − eta_k Q_E(s,a) ]`, update `eta` from realised sums.
   **Is this published?** Under what name, with what guarantee, and what is the bias when
   both critics carry function-approximation error — does the error in the ratio compound?
   If it is folklore rather than published, say so plainly.
5. **Direct ratio policy gradient / fractional policy optimisation** — anything that
   differentiates the ratio directly. Variance? On-policy only?
6. **Constrained MDPs** (Altman; Lagrangian methods; CPO/RCPO and value-based variants) as
   an *alternative* framing: maximise bits subject to an energy budget, rather than
   maximise the ratio. **When is the constrained problem equivalent to the ratio problem,
   and when does it give a different optimal policy?** This matters because the project is
   separately considering a constrained endpoint.
7. Anything in the **wireless / energy-efficiency RL** literature specifically: EE
   maximisation is a standard objective there, so what do those papers actually do? Do
   they optimise the ratio properly, or do they scalarise with a fixed multiplier and not
   say so?

## Three things I specifically need decided

- **A. Per-transition credit.** Under the winning formulation, what is the training signal
  for a single transition? A ratio is a global property of a trajectory; TD needs a local
  target. How does each formulation bridge that, and does any of them do it without an
  on-policy correction?
- **B. Demonstrator advantage.** If a demonstration `(s, a_D)` comes from an external
  specialist, how is "is this action better?" computed **under a ratio objective**? A
  scalar Q-margin `Q(s,a_D) > max_a Q(s,a)` is ill-defined when the objective is a ratio.
  Give the correct advantage definition. This gates whether an advantage-filtered
  imitation loss (Q-filter, CRR-style weighting) can be used at all.
- **C. Horizon and pooling.** The endpoint pools over the **whole evaluation**, not per
  episode. Does that change the formulation (an episodic ratio vs a pooled-across-episodes
  ratio)? Is the pooled-across-episodes ratio even a well-posed RL objective, or does it
  only make sense as an *evaluation* statistic while training optimises something else
  that is consistent with it? **If the honest answer is that no RL formulation directly
  optimises the pooled-across-episodes ratio, say so** — the project needs to know whether
  its endpoint is trainable or only measurable.

## Output

A recommendation with a citation for every load-bearing claim, an explicit statement of
what is **not** covered by published work, and — if the answer is "the correct thing is
known but has no published deep off-policy discrete instantiation" — say that, because it
changes what the thesis can claim to have contributed.

Do not restate the ledger. Do not recommend on elegance; recommend on what survives
off-policy replay with function approximation in a masked discrete action space.
