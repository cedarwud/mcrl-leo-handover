# Record — CFSCREEN: all three sources representable; C1/C2 are two thresholds of one rule; C3 independent

Date: 2026-09-11. Source: `.scratch/catfish-screens/CATFISH-SCREENS-2026-09-11.md`. Diagnostics, not
gates. Harness: FEASFRONT's `frontier.py` exec'd verbatim; **unpinned** local TLE archive (`e07f3e1e…`) —
EE figures here are not comparable to pinned-archive results; within-harness comparisons stand.

## Representability — yes for all three

Information ceiling 100%: every rule is exactly recoverable from the learner's own encoded observation
plus mask (24,000/24,000 each). Behaviour-cloning probe (same architecture as the Q-network, masked
softmax, episode-split 3-fold): held-out top-1 `MAX_NOMINAL_GAIN` 0.812, `A m=2dB` 0.838, `A m=9dB`
0.920, `A m=12dB` 0.935, `B1` 0.714, `B2` 0.683 (positive control learner-own-policy 0.877; random
labels 0.038). Plateau, not under-training. Closed-loop: A-family probes hold the rule's operating
point (EE within 1.4 sem, errors are near-ties ~0.24 dB); **C3 probes reproduce ~70% of the
consolidation** (47.3/45.5 active beams vs rule 37.9, learner 67.9).

## C1 vs C2 — distinct by role, not by coverage

- Actions: 35-55% disagreement on the same states — but that equals the probability mass in the
  gain-gap band between the two thresholds (e.g. 0.3633 = 0.3633): **one hysteresis rule at two
  thresholds.**
- States: C2's visited states lie inside C1's distribution (R 1.16-1.17, out95 0.05); C1 has 20-31%
  outside C2's. **As coverage sources, one.**
- `A m=2dB` also reads the incumbent; only `MAX_NOMINAL_GAIN` is memoryless (HARVEST's "gain-only"
  label is inaccurate for `A m=2dB`).

**Consequence for the frozen pilot — none; for the narrative — yes.** In the pilot C1 feeds `Q_B` and
C2 feeds `Q_H`: they are justified as two catfish **by the objective each head serves** (the EE-max
end vs the handover-cap end — they teach opposite actions on the same states), not by distinct
coverage or information. The thesis must say so. If a coverage-distinct second source is wanted
later, `MAX_NOMINAL_GAIN` (memoryless) is the candidate for C1.

## C3 — the most independent source

Action disagreement with C1/C2 0.44-0.72; states independent in both directions (R 1.31-1.64 vs the
A-family, 2.19-2.25 vs the learner), carried by the loads block (R 10-12 on that block alone).
B1 and B2 are one source (disagreement 0.05). **The trained old Q3 (load-balance head) agrees with C3
on only 2.0-2.7% of states — below chance (~3.8%)**: the old r3 head points against consolidation,
confirming that C3 must attach to the redefined energy head, as the pilot does.

## Margin scale (next version, not this pilot)

Per-state std of scalarised Q across legal actions ~0.14-0.16 (p10-p90 0.11-0.21). Learner already
picks the source's action on C1 0.25/0.36, C2 0.64/0.66, C3 0.22/0.16 of source-visited states — none
near 1, so a margin loss would fire for every source.

## Harness fact — cross-cell comparisons are unpaired

Only episode 0 is paired across cells; for episodes ≥1 the start epoch is drawn from `env_rng` and
fading draws depend on actions, so t=0 SNR/theta differ in 100% of rows (divergence verified;
mechanism inferred). **"Same 24 episodes" in FEASFRONT and earlier reports means same seeds.** Their
between-arm EE differences are unpaired comparisons; any paired statistic across cells is invalid.
Sent to CF3PILOT (per-episode reseed in evaluation if it is a pure harness change, else report
unpaired) and to CURATE (registry column).
