# The coordination headroom ceiling: how much of the corrected physics' infeasibility is interference-driven?

`DIAGNOSTIC_NOT_CLAIM`. This bounds the maximum value any coordination layer could have, before we spend more compute searching for one. It is cheap: no search, only re-evaluation.

## Why this is the right measurement now
Under the corrected causal ACM the system is deeply power-limited. Verified from `/home/sat/mcrl-v025-codex-ws-engine/.tmp/stage4h-formal/smoke/a-r0-world-1.json`:
* `rate_target_feasible` is **false for 11,428 of 28,000 user-steps, 40.8 %**, meaning those users cannot reach `r* = 50 Mbit/s` even at the 1.65 W RF cap;
* `m_tx` is `NO_MODE` for about **62 %** of transmissions;
* beam occupancy never exceeds **6** users against a 12-user feasibility ceiling, mean 2.44 per user-weighted count, so the occupancy edge is not binding.

A user that fails because of path loss and thermal noise cannot be rescued by any reassignment, and every such user is dead weight for C3. A user that fails because of interference from other beams **can** be rescued. The ratio between those two populations is the ceiling on coordination value in this physics.

## Workspace and constraints
`/home/sat/mcrl-v025-probe-ws-acm2` is a clean checkout of engine commit `75c5c78c` with the corrected physics. **Another agent is running the interaction-existence probe in that same workspace right now.** So make your own copy: `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C /home/sat/mcrl-v025-headroom-ws` after creating that directory. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, `/home/sat/mcrl-v025-probe-ws-acm2`, or `src/mcrl/env/`. Use at most 3 concurrent processes and `nice -n 10`; other jobs own this machine.

## Measure these, on `a-r0` and on at least one other regime
For every user-step in a real evaluation, decompose the link budget and report:

1. **Interference-free counterfactual.** Recompute the wanted-link SINR with the interference term set to zero, changing nothing else. Report the share of user-steps that move from `rate_target_feasible = false` to `true`, and the share whose `m_tx` moves off `NO_MODE`. **This is the headline number: it is the absolute ceiling on what perfect interference coordination could deliver.**
2. **Interference-to-noise ratio.** The distribution of `I / (N0·W)` per user-step, in dB, split by whether the user is feasible. If interference sits far below thermal noise for most users, the ceiling in item 1 will be near zero and no coordination design can change that.
3. **Why each infeasible user fails.** Classify every infeasible user-step into: noise-limited (interference-free still infeasible), interference-limited (interference-free becomes feasible), or cap-limited (feasible in SINR terms but the 1.65 W cap binds first). Report the three shares.
4. **Where the interference comes from**, for the interference-limited population only: same-satellite adjacent beam, other satellite, or the aggregate of many weak contributors. If it is dominated by a single strong interferer, a coordination layer has a concrete lever; if it is the sum of many weak ones, it does not.
5. **Energy sensitivity.** For the interference-limited population, the joules that would be saved if those users reached their target mode rather than transmitting at the cap for nothing. Under the corrected ACM a `NO_MODE` user still burns full power and still sits in the availability denominator, so this is real recoverable energy.

## Reporting rules
Report shares and distributions, not a verdict. Do not conclude that C3 will or will not work. Do not compare arms, do not run a learner, do not touch any acceptance rule, threshold, seed or price. If a number cannot be computed from the receipts, say so rather than estimating it.

Write `/home/sat/mcrl-v023-codex-audits/parallel-20260909/HEADROOM-CEILING-2026-09-09.md` and print it as your final message. Lead with item 1. Mark each number VERIFIED, meaning you computed it, or UNKNOWN. End with an HONEST LIMITS paragraph naming the worlds, anchors and user-steps the numbers cover. Budget 2 wall hours.
