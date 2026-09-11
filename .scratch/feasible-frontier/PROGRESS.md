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

- [x] Script written: scratchpad `frontier.py`
- [x] Smoke test (1 episode, 3 arms) passed
- [x] Full run launched detached (single python process, `nice -n 16`, OMP/BLAS threads 1)
- [x] All 16 cells complete — raw output in scratchpad `frontier.out`
- [x] Question 1 answered; table built
- [x] Report written

## JSRL guide-horizon coverage sweep (coordinator follow-up, after the frontier)

- [x] `h` ∈ {0..10}, guide = `MAX_NOMINAL_GAIN`, learner = trained `e6b063ef…` greedy
- [x] Coverage measure declared before the run (1-NN distance in 112-dim observation
      space from each handover state to the pool of `h=0` states at the same step index)
- [x] Placebo: `h=0` reproduces the trained reference; `h=10` reproduces `MAX_NOMINAL_GAIN`
- [x] Section appended

## Results

**Q1: NO — the trained policy is NOT on the Pareto frontier.** Dominated by `A m=12dB`
(ho 0.2258, EE 101,467,361.95; n=48 re-run ho 0.2257±0.0017 vs trained 0.2802±0.0028 = −16.9 sem,
EE ×1.077 = +6.7 sem) and on point estimates by `A m=9dB` (ho 0.2753, EE 105,701,579.47; at n=48 its
ho edge is −0.0040 = −1.1 sem → a TIE on handover, +12.9 sem on EE).

Placebos: `A m=0dB` = 111,504,571.388934 and TRAINED = 93,110,907.973748 — both bit-identical to the
previous round's fresh-env figures; RANDOM_MASKED = 53,060,175.561473 bit-identical too.

Raw n=24 output: scratchpad `frontier.out`; n=48 confirmation: scratchpad `confirm48.out`.

Secondary: A m=6/9/12 also beat the trained policy on its OWN calibrated scalar
(+0.9538/+1.1309/+1.2232 vs +0.9033; n=48: +1.1271/+1.2101 vs +0.9167). Hysteresis is observation-only
(block 1 incumbent + block 2 gain), so this overturns the catfish-surface report's
"no expressible arm beats the learner on the scalarized objective" — that search covered myopic rules only.

JSRL n=24 done (scratchpad `jsrl.out`): placebos bit-identical (h=0 = TRAINED, h=10 = A m=0).
EE monotone increasing in h (93.11 M -> 111.50 M, no interior max). Coverage NOT flat but NOT rising:
steps up at h=1 (R 1.60, out95 0.66 vs 1.00/0.05) then oscillates R 1.39-2.20, out95 peaks 0.74 at h=2
and falls to 0.28-0.42 for h>=4. Kill condition "flat" not met; "rises" met only as a step.
Audit re-run (deterministic; diff vs first run empty; `jsrl_rerun.out`, `jsrl_states.npz`,
`jsrl_blocks.out`): novelty lives mainly in block 4 `loads` (32-50% of 1-NN sq. distance, block-only
R 3.8-8.8) and block 2 `snr`; survives on same-incumbent rows (R 1.21-1.66). Not measured: whether
novelty persists after the hand-off.

## ALL DONE — nothing to resume. Report: `FEASIBLE-FRONTIER-2026-09-11.md` (frontier + JSRL section).
No detached processes left running.
