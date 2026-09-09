# Round 13B (Q&A): choosing a coalition under a hard real-time deadline

## The problem
A coordinator must choose, within a **10 second** wall-clock budget, a subset of about 100 agents to move and where to move them. The value function is neither submodular nor supermodular, which I have verified with an explicit counterexample, so greedy carries no approximation guarantee. Exact evaluation of one candidate assignment costs a physics solve of a coupled fixed point.

Measured today: decisions take 5.7 to 9.9 seconds against the 10 second budget, so the margin at the worst anchor is under 0.1 seconds. If the budget is missed the system falls back to a default, which makes every experimental arm identical and the experiment worthless.

## Questions

1. **Anytime selection.** What are the practical patterns for a selection procedure that must return a usable answer at a hard deadline, and improves monotonically until then? I am interested in the engineering shape, not only the theory: how the incumbent is maintained, how partial evaluation is scheduled, how the deadline is enforced without corrupting the committed answer.

2. **Where the budget usually goes.** In systems like this, is the time normally spent in candidate generation, in evaluation, or in search? Are there standard profiling patterns and standard wins, for example caching invariants across candidates, or a cheap surrogate used to shortlist before exact evaluation?

3. **Lossless pruning.** I am only permitted speedups that provably cannot change the selected candidate. What are the standard techniques for that in combinatorial selection with an expensive oracle, and what evidence is normally required to call one lossless?

4. **The margin problem.** A 0.1 second margin at the worst case is clearly too thin. Is there a principled way to decide how much headroom a real-time decision loop needs, given a measured latency distribution with a heavy tail?

5. **What real systems do.** For a coordination decision in a wireless or satellite network on a tens-of-seconds cadence, what latency budgets do deployed systems actually work with, and how do they handle the case where the optimiser does not finish?

## Context you may need
The decision is recomputed every 30 seconds. A missed deadline is not a crash; it falls back to keeping the previous assignment. The concern is not safety but that a high fallback rate destroys the measurement.
