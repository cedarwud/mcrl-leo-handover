# FEASFRONT progress

Started 2026-09-11. Read-only + scripted rollouts. **No training, no `update()`, no gradient step.**
Output: `FEASIBLE-FRONTIER-2026-09-11.md` (this directory).

Harness, estimand, `DiagnosticStepEnvironment` factory, placebo discipline and the
`_age_rng` confound all reused from
`.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md` — not reimplemented.

Reference points being tested against (from that report's pooled-EE section):
- `MAX_NOMINAL_GAIN` pooled EE 111,553,182.85 bit/J, ho 0.7117, served 0.9981
- trained `e6b063ef…`  pooled EE  93,137,893.02 bit/J, ho 0.2796, served 0.9988

## Declared grid (fixed before the run; not to be extended or re-centred)

Family A margin `m` ∈ {0, 0.5, 1, 2, 3, 4, 6, 9, 12} dB.
Family B: `B1_NO_NEW_BEAM`, `B2_PREFER_SHARED`.
Family C: `C1_SAT_LOCK`, `C2_SAT_LOCK_3DB`.
Family D: `A m=0` (unrestricted `MAX_NOMINAL_GAIN`, shared with Family A) and `HOLD_WHILE_LEGAL`.
Harness check: `RANDOM_MASKED`. Reference: `TRAINED e6b063ef…` (greedy, ε=0).

16 cells total, 24 episodes each, frozen seeds (42/1337/7), fresh env per cell.

## Arm status

- [ ] Script written: scratchpad `frontier.py`
- [ ] Smoke test (1 episode, 3 arms) passed
- [ ] Full run launched detached (single python process, `nice -n 16`, OMP/BLAS threads 1)
- [ ] All 16 cells complete — raw output in scratchpad `frontier.out`
- [ ] Question 1 answered; table built
- [ ] Report written

## JSRL guide-horizon coverage sweep (coordinator follow-up, after the frontier)

- [ ] `h` ∈ {0..10}, guide = `MAX_NOMINAL_GAIN`, learner = trained `e6b063ef…` greedy
- [ ] Coverage measure declared before the run (1-NN distance in 112-dim observation
      space from each handover state to the pool of `h=0` states at the same step index)
- [ ] Placebo: `h=0` reproduces the trained reference; `h=10` reproduces `MAX_NOMINAL_GAIN`
- [ ] Section appended

## Results (filled in as cells complete)

See `FEASIBLE-FRONTIER-2026-09-11.md`.
