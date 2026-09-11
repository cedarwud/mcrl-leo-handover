(Same conversation as DR-2. You already have the context ledger and your own research report above.)

## Decision — physics defensibility (consumes DR-2)

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
