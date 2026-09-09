Workspace: the current directory, `/home/sat/mcrl-v025-ladder-ws`. It already contains a working twenty-anchor panel runner and a margin-provisioning variant from a previous task — read `.scratch/ladder-floor-20260910/` first and reuse it rather than rebuilding. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. No training run, no policy run, no learner. **No sealed constant is being changed**: every sweep point is a separate diagnostic evaluation on a copy, exactly as the margin variant was. Adopting any point would be a separate owner decision made on design grounds, and this task does not recommend one. Do not change any sign, seed, horizon, price, service guard or acceptance rule, and do not modify sealed artefacts or frozen manifests.

# The hypothesis under test

On this project's current operating point, a bounded joint (multi-user) association search beats an iterated unilateral search run to a certified fixed point by only **+0.51 %** in pooled energy efficiency, while the unilateral fixed point beats a geometry-only baseline by **+442 %**.

That small joint-over-unilateral gap is what theory predicts for an association game whose best-response dynamics have converged: the price of anarchy for load-balancing-style association is usually a few per cent. Where the gap is known to be large is in **constrained** regimes — when moves are interdependent, when hard capacity limits cause blocking, and when coupling between players is strong.

The current operating point is lightly loaded in exactly the relevant sense. With a 50 Mbit/s per-user target, 166.67 MHz per beam under reuse 3, and equal-airtime sharing, the required spectral efficiency is `0.3n`, so the mode table's maximum of about 3.71 caps a beam at roughly twelve users, and the efficiency-optimal single-beam occupancy is about seven. Interference barely binds.

**The question: does the joint-over-unilateral gap grow as the system becomes constrained, and if so how fast?**

This is falsifiable. If the gap stays near half a per cent across the whole sweep, that is a clean negative result and the most valuable thing you can report.

# The sweep

Two axes, swept independently and then jointly at a few points:

**Axis L — offered load per beam.** Vary the user population over the same worlds and geometry. Include the current population and at least three larger points, chosen so that mean occupancy spans roughly the current value up to the point where the cap and the table maximum bind frequently. State the realised occupancy distribution at each point.

**Axis R — per-user rate target.** Vary the per-user rate target across at least five points spanning well below and above the sealed 50 Mbit/s, chosen so that the implied required spectral efficiency at typical occupancy spans from comfortably inside the mode table to close to its maximum. **State at every point that the sealed value is 50 Mbit/s and that no sealed constant was changed.**

Run every point under **both** provisioning formulations already implemented here — the sealed one and the margin one — because a conclusion that only holds under a defective formulation is worthless.

# At each sweep point, report

- pooled energy efficiency for the neutral baseline, the iterated unilateral fixed point, and the bounded joint selector;
- **the joint-over-unilateral relative gap**, which is the quantity the hypothesis is about, with the count of anchors where it is negative;
- the unilateral-over-baseline gap, for scale;
- served counts **and, separately, the count attaining the per-user rate target** — these are different quantities and must not be merged;
- the share of boundaries where the per-beam power cap binds, and the share where no eligible mode exists;
- the interference-limited share of infeasible user-steps, and the top-one aggressor share;
- the realised mean and maximum beam occupancy.

Use at least eight anchors per point; say how many. If the budget forces a cut, reduce anchors rather than dropping sweep points — the shape of the curve is the deliverable.

# Rules

- **The curve is the deliverable, not a winner.** Do not rank points, do not recommend a value, and do not describe any point as better. The scientific question is *in what regime does set-level coordination have value*.
- If the gap does not grow, say so in the first line. A clean negative here saves the project weeks.
- If the gap grows, report where it crosses one per cent and two per cent, and what is binding at that point — cap, table maximum, or interference.
- Every number must be reproducible from a script left in the workspace, with exact command lines.
- Say plainly which points you did not reach.

Write `LOAD-REGIME-SWEEP-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether the joint-over-unilateral gap grows with load or rate target, and where.
