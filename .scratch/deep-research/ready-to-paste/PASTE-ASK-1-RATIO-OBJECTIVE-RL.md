(Same conversation as DR-1. You already have the context ledger and your own research report above.)

## Decision — architecture decision (consumes DR-1)

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
