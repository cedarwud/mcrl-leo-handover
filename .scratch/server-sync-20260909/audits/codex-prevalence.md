# Prevalence census: how often does a profitable coalition actually exist in the real worlds?

`DIAGNOSTIC_NOT_CLAIM`. Budget 90 minutes. This is a counting exercise, not a search for the best coalition.

## Why this is the decisive remaining measurement
Existence is settled. A witness run on the corrected engine produced positive interaction on four mechanisms, with the strongest showing energy efficiency of 29.496 Mbit/J at the anchor, 28.240 and 23.283 for the two single moves, and **36.794 for the joint move**, a gain of 24.74 %, with the served count unchanged at 4 so the service guard held.

What is unknown is **prevalence**. That witness is a hand-built five-user geometry. If coalitions of that shape are vanishingly rare in the real hundred-user worlds, there is nothing for a learner to learn and the coordination component cannot be worth its cost. If they are common, it can.

## What to measure
Workspace: create `/home/sat/mcrl-v025-prevalence-ws` and populate it with `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C /home/sat/mcrl-v025-prevalence-ws`. That is the corrected causal ACM. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or `src/mcrl/env/`. At most 4 concurrent processes, `nice -n 10`. Build any tape fresh in this workspace; never link one from another workspace.

Use the real evaluation worlds and real anchors, the same ones the matrix would use. Prefer breadth over depth: **more anchors with a cheap test beats a few anchors with an exhaustive one.** At least 20 anchors if you can, and say how many you managed.

At each anchor, count how many anchors admit **at least one** coalition that satisfies all three of:
1. every member's individual move is non-improving, `d_i <= 0`;
2. the joint move strictly improves the objective;
3. the served count does not fall below the anchor's.

## Where to look, since the mechanism is known
Do **not** enumerate blindly and do **not** rank candidate users by the size of `|d_i|`; that ranking argument has been withdrawn. Build candidates from physical events:

* **Occupancy activation.** At 10 degrees elevation the engine's own quantile is `q10 = 0.42923539` and the lowest mode threshold is `0.7174947935`. A beam at occupancy 1 or 2 has `q*Gamma(n)` below that threshold and selects no mode, while occupancy 3 clears it. So for each beam at occupancy 1 or 2, try moving in the two nearest legal users. Report how many beams sit at occupancy 1 or 2 in the first place.
* **Multi-aggressor relief.** A separate diagnostic found that 91.1 % of infeasible user-steps are interference-limited, that a single aggressor carries 74.3 % of a victim's interference, and that removing the top-1 aggressor alone rescues 76.4 % of them. **The remaining 23.6 % need two or more aggressors relieved, and that is the population that belongs to the interaction term rather than to the individual marginals.** For victims in that tail, move their top-2 and top-3 aggressors to their own best legal alternatives.
* **Complete beam evacuation.** A beam's per-chain circuit power is saved only when every occupant leaves, so a beam with 2 or 3 occupants gives a coalition whose value appears only when all of them move. Include these; they need no decode threshold at all.

## Report
`PREVALENCE-CENSUS-2026-09-09.md` in the workspace root, printed as your final message. Lead with a single number: **the fraction of anchors at which at least one qualifying coalition exists.** Then:
* that fraction broken down by the three mechanisms above, so it is clear which one carries the prevalence;
* the distribution of the energy-efficiency gain of the best qualifying coalition per anchor, as `EE(joint)/EE(anchor) - 1`, reported as min, median and max. **Energy efficiency is the outcome the owner cares about, so report it as EE and not only as the score;**
* coalition sizes found;
* how many anchors and worlds you covered, and the search budget, so a low number reads as "rare within this budget" rather than "absent".

If the answer is that qualifying coalitions are rare or absent, say so plainly and early. A low prevalence is a real and useful finding, and reporting it clearly is worth more than finding a way to make the number look good. Do not tune anything to raise it. Do not change any threshold, sign, seed, horizon, price, service guard or acceptance rule.
