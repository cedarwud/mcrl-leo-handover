# Follow-up reasoning prompts — normal chat, run AFTER the matching DR returns

These are the **judgement** halves that were wrongly folded into the DR prompts. Deep
Research searches; it does not adjudicate, and asking it to attack a design or forecast a
referee just gets the judgement语气 handed back without the judgement.

**How to run each**: paste `00-EVIDENCE-LEDGER.md`, then the DR report it consumes, then
the prompt below. Use a strong reasoning model in normal chat, not Deep Research.

---

## ASK-1 — architecture decision (consumes DR-1)

Above is a survey of methods for optimising a ratio of expected accumulations, and a ledger
describing a specific system: a discrete, action-masked, off-policy DQN with three Q-heads,
`dt` = 30.08 s, 10-step episodes, whose declared endpoint is pooled bits over pooled joules
across the entire evaluation.

Two independent reviewers have separately recommended a two-critic `(Q_B, Q_E)`
architecture with a Dinkelbach `eta` updated in an outer loop. Neither supplied a citation.

**Decide what this project should build**, and in doing so answer:

1. Does the survey support the two-critic recommendation, contradict it, or leave it
   unsupported? If it is unsupported folklore, say so — that changes whether the thesis is
   *applying* a method or *inventing* one, and the latter requires a different burden of
   evidence.
2. The specific replay problem: if `eta` changes between outer iterations, every target in
   the buffer was computed under a stale `eta`. Which of the surveyed treatments actually
   works here, given that transitions are cheap to regenerate (1.59 s per episode) but the
   buffer holds 50,000?
3. **How is a demonstrator's action scored as better or worse under this objective?** An
   external rule proposes `a_D`; a scalar Q-margin is ill-defined under a ratio. If no
   sound definition exists, then advantage-filtered imitation cannot be used and the design
   must change — say so.
4. A reviewer predicted this failure mode for a margin-loss design: the Bellman operator
   drags the policy to the fixed point of the deployed scalar; a Q-filter then finds the
   demonstrator's action has lower Q under that misaligned reward and permanently disables
   the supervised loss; the agent unlearns the demonstrations. **Does the two-critic
   formulation avoid this, or relocate it?**
5. Give the smallest implementation that is defensible, in the existing trainer's terms:
   what is stored in the buffer, what each head predicts, what the TD target is, where
   `eta` enters, and what the action-selection rule becomes.

State plainly what you are confident in and what remains unresolved.

---

## ASK-2 — physics defensibility (consumes DR-2)

Above is a provenance survey of LEO/NTN handover cost, operating points and payload power
models, and a ledger describing one simulator.

**Assess whether this simulator's physics would survive review**, and answer:

1. For each place the simulator differs from standard practice — zero-joule handovers, no
   interruption term, `max`-over-users beam power, occupancy-independent power, a 30.08 s
   decision interval, load-unweighted interference — say whether the difference changes the
   **sign** or only the **magnitude** of any conclusion drawn from it. Rank them by how
   damaging they are.
2. The learner operates at 0.2796 handovers per user-step and a greedy energy-efficiency
   rule at 0.7117, at `dt` = 30.08 s. **Are either of these inside the realistic envelope?**
   One reviewer called 0.71 operationally absurd; check that against the surveyed figures,
   and say whether 0.28 is also outside.
3. A handover-rate constraint is being considered. From the surveyed exogenous bases,
   **what ceiling is actually derivable, and which part of any proposed ceiling is a
   stipulation rather than a derivation?** A prior proposal was `H_max <= 0.40` as
   `1/15` (one inter-satellite handover per pass) plus `1/3` (a stipulated beam-switch
   budget) — assess both terms separately.
4. Two of the three reward heads have premises that fail inside the model: `r2` prices a
   handover that costs zero joules, and `r3` rewards spreading users, which the model shows
   is energy-neutral and interference-negative. **Given the survey, where do those costs
   actually belong** — in the numerator, in a constraint, in a separate reported outcome,
   or nowhere?
5. Name the single physics change that would most improve defensibility per unit of work.

---

## ASK-3 — contribution and positioning (consumes DR-3)

Above is a survey of reported results, baselines and demonstration-guided RL in satellite
resource allocation, and a ledger describing one project's findings.

**Assess what this project can honestly claim**, and answer:

1. Where do this project's numbers sit in the field's distribution — magnitudes, baseline
   practice, statistical treatment? Is its own standard higher or lower than the field's?
2. Given that multiple heterogeneous demonstrators, advantage-filtered imitation,
   imperfect-demonstration filtering and constrained multi-objective RL are all published:
   **is there a defensible contribution left?** State it in one sentence if there is. If the
   honest answer is that the contribution is the integration and the measurement rather
   than any new mechanism, say so, and say what a paper of that shape must carry —
   baselines, ablations, statistical treatment, venue.
3. A second candidate contribution is the **negative result**: a trivial rule beats a
   trained multi-objective policy by 19.8-22.2% on the declared energy-efficiency endpoint
   because the training scalarisation prices a handover that costs zero joules in the
   model. **Is a result of that shape publishable in this field, and where?**
4. Rank the objections a referee at a good venue would raise, and for each say whether it
   is fatal, fixable, or answerable in text.
5. If the honest conclusion is that the intended contribution is already published and the
   remaining one is diagnostic, say that directly.

---

## Note on running these

Do **not** use these to adjudicate the endpoint decision — that is already with two
cross-model reviewers holding the full evidence bundle (agy and codex `gpt-6-astra`, both
returned PROCEED WITH CHANGES). A third opinion formed from a summary is worth less than
either, and three opinions invite picking the congenial one.

Every load-bearing claim that comes back must be checked against the primary source before
it enters a declaration or the thesis. This project has already been bitten by a citation
that does not resolve to any paper.
