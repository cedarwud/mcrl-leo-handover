Workspace: /home/sat/mcrl-v025-ladder-ws is BUSY; use /home/sat/mcrl-v025-arch-ws instead (its job finished). Interpreter: /home/sat/mcrl-leo-handover/.venv/bin/python with PYTHONPATH=src and `nice -n 15`. Never modify /home/sat/mcrl-leo-handover or its venv.

# Task: map the energy-efficiency-optimal beam occupancy, analytically, under the declared physics

`DIAGNOSTIC_NOT_CLAIM`. No training, no learner, no policy run. This is a closed-form/numeric map over the project's own sealed constants, using the production physics functions where they exist.

## Background you must verify from code, not assume
The successor physics is `V025-ANGLE-RATE-TPC-TDM-ACM`. Read the actual implementations under `src/mcrl/physics_v025/` before computing anything, and cite file:line for every constant and formula you use. The pieces that matter:
- per-user rate target r* and the equal-airtime TDM sharing rule, giving the required spectral efficiency as a function of beam occupancy n;
- the mode table (EN 302 307-1 based) and its selection rule, including its maximum spectral efficiency and its minimum threshold;
- the power-amplifier supply model (a square-root supply law with a saturation power and an efficiency divisor), the per-chain circuit power, and the per-satellite baseband power;
- the off-axis antenna gain law and its 3 dB beamwidth parameter;
- the per-beam power cap.
If any of these differs from that description, follow the code and say so.

## The question
Under the sealed law, transmit power is provisioned so the nominal signal-to-noise ratio lands on the required mode's threshold. Consider instead an occupancy n served by one beam versus the same n users split across two or more beams. Consolidating raises the required spectral efficiency per user linearly in n, so the required threshold — and therefore the radiated power — grows much faster than linearly. Spreading instead pays an additional always-on chain cost and, if it opens a beam on another satellite, an additional baseband cost.

That is a convex trade-off with a possible interior optimum. **Find it, or show it does not exist**, for our constants.

## Deliverables

### D1 — the power-versus-occupancy curve
For a single beam at a fixed link geometry, tabulate for n = 1..12: required spectral efficiency, the selected mode and its threshold, the required radiated power, the amplifier supply power, and the total power including chain and baseband. Report the growth factor from n to n+1. Do this for BOTH provisioning rules and label them clearly:
- `SEALED`: provision to the nominal threshold exactly (the current law);
- `MARGIN`: provision to threshold divided by the fading quantile, i.e. enough that the faded signal still clears the threshold.
State explicitly at which n each rule first hits the per-beam power cap, and at which n the required spectral efficiency first exceeds the table maximum.

### D2 — the efficiency-optimal occupancy
Define pooled efficiency as total delivered bits over total joules for a fixed user population, and compute, for each provisioning rule, the occupancy that maximises it when N users must be partitioned across beams. Sweep N over 1..24. Report the optimal number of active beams and the optimal occupancy per beam. If the optimum is always "one beam" or always "one user per beam", say so plainly — a corner solution is a legitimate answer and is more informative than a manufactured interior one.

### D3 — geometry dependence (this is the owner's first hard requirement)
Repeat D2 across a grid of off-axis angles from boresight out to the beam edge, and across a representative range of slant ranges. Report whether the optimal occupancy **changes** with off-axis angle and with slant range, and by how much. Produce a small table of optimal occupancy against (off-axis angle, slant range). If the optimum is invariant to geometry, say so plainly — that would mean the geometry cannot drive a coordination decision, which is a finding the project needs.

### D4 — the discriminator
Recompute D2's optimum with the always-on per-chain and baseband costs set to zero. If the interior optimum survives at zero fixed cost, the trade-off is driven by the mode/power physics; if it collapses to a corner, it was driven by the fixed costs. Report both and state which.

## Rules
- Use exact or high-precision arithmetic where the production code does; do not silently substitute a continuous Shannon rate for the discrete mode table — if you also want a continuous-rate comparison, report it as a clearly separated reference row.
- Do not change any constant, threshold, sign, seed, or acceptance rule. Do not modify sealed artefacts.
- Every number must be reproducible from a script you leave in the workspace, with the exact command line in the report.
- If a deliverable is infeasible in your time, complete the earlier ones fully and say which you did not reach.
- Write `OCCUPANCY-CONVEXITY-2026-09-10.md` in the workspace root and print it as your final message. Lead with one line: whether an interior efficiency-optimal occupancy exists under each provisioning rule, and whether it depends on off-axis angle.
