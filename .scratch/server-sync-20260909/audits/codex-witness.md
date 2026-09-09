# Verify ONE predicted configuration. This is not a search.

`DIAGNOSTIC_NOT_CLAIM`. Budget 45 minutes. Completion beats completeness.

An outside structural review produced a counterexample showing positive interaction is possible under our scoring equations, and a separate check confirmed our own fading quantile sits inside the window the counterexample needs. **So we already know what configuration to build.** Build it, score it with the real engine, and report the number. Do not search a neighbourhood. Do not enumerate candidates.

## The prediction, from the engine's own constants
At 10 degrees elevation the engine's `channel.fading_product_quantile` gives `q10 = 0.42923539`. The lowest mode threshold is `gamma_min = 0.7174947935` linear, `-1.441812` dB. The rate-target mode thresholds by beam occupancy are:

| occupancy | target mode | Gamma(n), dB | q*Gamma(n) | vs gamma_min | predicted |
|---:|---|---:|---:|---|---|
| 1 | QPSK 1/4 | -1.441812 | 0.30797 | below | **NO_MODE** |
| 2 | QPSK 2/5 | +0.608188 | 0.49382 | below | **NO_MODE** |
| 3 | QPSK 3/5 | +3.138188 | 0.88407 | above | **mode selected** |

So a beam needs **two arrivals** to become usable and one arrival achieves nothing. That is the super-additive structure.

## What to build
Workspace `/home/sat/mcrl-v025-witness-ws`, already a clean checkout of engine commit `75c5c78c` with the corrected causal ACM. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, `/home/sat/mcrl-v025-probe-ws-acm2`, or `src/mcrl/env/`. Two processes maximum.

Three users, three beams on one satellite, homogeneous channels at 10 degrees elevation, no interference between the three beams if the geometry permits it, otherwise state what interference exists.

* **Anchor**: one user on each of beams X, Y, Z. Occupancy (1,1,1). All three should be `NO_MODE`, delivering zero bits while consuming power.
* **Single move A**: the Y user moves to X. Occupancy (2,1,0).
* **Single move B**: the Z user moves to X. Occupancy (2,0,1).
* **Joint move**: both move to X. Occupancy (3,0,0). Beam X should activate.

## What to report
1. **First, confirm the prediction.** For each of the four states, the per-beam occupancy, the target mode, the transmitted mode, whether it is `NO_MODE`, and the credited bits. If the engine does **not** reproduce the NO_MODE-at-1-and-2, mode-at-3 pattern, stop and report that. A prediction that fails is the most valuable outcome available, so report it clearly rather than adjusting the scenario until it works.
2. **The four score evaluations** `F(anchor)`, `F(A)`, `F(B)`, `F(joint)`, using the engine's own `_objective` and the sealed calibration values from `/home/sat/mcrl-v025-codex-ws-engine/.tmp/stage4h-formal/calibration-manifest.json`. State which calibration you used.
3. **`d_A`, `d_B`, and `Psi = F(joint) - F(anchor) - d_A - d_B`.** This is the headline number.
4. **Run it twice**: once with the engine's real signalling penalty, and once with that penalty set to zero, so the physics is separated from the handover price. Report both `Psi` values. Do not change any other quantity.
5. **The decomposition** `Psi_B - eta*Psi_E - Psi_Phi`, so it is clear whether a positive result comes from credited bits, from energy, or from the penalty.
6. **Energy detail**: the power-amplifier, per-chain circuit and per-satellite baseband energy in each of the four states. Beams Y and Z close in the joint move, so their circuit power should disappear; say whether it does.
7. Whether the service guard, served count not below the anchor's, holds in each state.

## Rules
Do not tune `eta_ref`, `lambda`, `kappa`, any threshold, sign, seed, horizon or the service guard. Do not modify `src/mcrl/physics_v025/`. You may write new scenario-construction scripts freely. If the engine's API makes the minimal scenario hard to express, say so and build the smallest thing that goes through the real evaluator rather than reimplementing the physics.

Write `PSI-WITNESS-REPORT-2026-09-09.md` in the workspace root and print it as your final message. Lead with one line: `PSI POSITIVE`, `PSI NON-POSITIVE`, or `PREDICTION NOT REPRODUCED`. Then the numbers. Then an HONEST LIMITS paragraph saying what a three-user synthetic scenario does and does not establish about the hundred-user system.
