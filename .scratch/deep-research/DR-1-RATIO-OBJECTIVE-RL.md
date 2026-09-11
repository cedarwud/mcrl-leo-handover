# DR-1 — Survey: optimising a ratio of expected accumulations in reinforcement learning

*Optional context: `00-EVIDENCE-LEDGER.md` describes the application. It is background only
— every factual claim in your report must come from the literature, not from it.*

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
