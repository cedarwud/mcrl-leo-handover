**On the 24 evaluation episodes, parity max |Δ| = 0.0 exactly in every cell: the rate-floored sequential oracle B-real-floor(R1) reaches 134,129,417.19 bit/J = +25.353 % vs `A m=2dB` (paired +25.71 ± 0.95 %, 24/24), served 0.99887, p10 165.46 Mbit/s = 1.63 × the rule's, with 0 of 23,973 served user-steps under the per-user rate floor, while the rate-floored simultaneous oracle A-real-floor(R1) reaches only 113,531,833.46 bit/J = +6.104 % (paired +5.72 ± 0.95 %, 23/24), served 0.99925, p10 28.60 Mbit/s = 0.28 × — throughput-degenerate, 32.2 % of its served user-steps under the floor, because 72–96 of its 100 users move simultaneously each step; unfloored the same two cells give +29.523 % (p10 1.14 ×) and +5.927 % (p10 0.27 ×); so of Amendment 1 §3 only **rule 3 holds, by +19.25 percentage points** (rules 1, 2 and 4 do not), and of Amendment 4 §2 condition 1 is met (+19.25 pp ≥ +3.3 pp) while condition 2 holds for B-real-floor alone and condition 3 is not yet measured — the B-real-floor calibration teacher set it needs is complete here (+22.551 % on the 24 calibration episodes, 24/24, 0 floor violations); the two R2 cells are HELD unrun, the R2 rule itself scoring −3.983 % vs `A m=2dB` on this set.**

# Realised-information oracle cells — A-real and B-real, rate-floored and unfloored, reference `A m=2dB`

Date 2026-09-11 (cells run 16:31–18:41 UTC on `sat`). Measurement only: no training, no weight changed, no new arm.
Companion to `LP-PROBE-2026-09-11.md` (the nominal-information cells of the same table). Supersedes the controller's
provisional `BRANCH-NUMBERS-FLOOR-R1-EVAL.md` (whose every printed field this report reproduces — see "Cross-check").
Written as the **minimal branch-adjudication artefact** the owner asked for at 20:10 UTC: the completed cells, their
conditions and the declared rules. Unpolished by intent; the held cells are listed with what each would have answered.

```
PROVENANCE [A] (this report's own measurements)
- physics / harness (C):   MODQN-harness ; MDP modifiers: cap UNKNOWN (not stated for this pilot), segment anchor
                           UNKNOWN (not stated), interruption UNKNOWN (not stated), users 100
- estimand (C):            pooled ratio-of-sums (Σbits/ΣJ, divided once), full-buffer
                           + numerator: full-buffer Shannon, no demand cap
                           + scoring horizon: n.a. (not a V0.25 a-r0 panel quantity)
                           "% vs A m=2dB" = pooled relative difference against the rule ON THE SAME SET; the paired
                           statistic beside it is mean ± sem of the 24 per-episode relative differences (sem =
                           sd(ddof=1)/√24); percentage POINTS ("pp") are differences of two such percentages
- power accounting (C):    consumed, per-beam max over served users (MODQN default)
- host + TLE archive (C):  sat ; archive = pinned 427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9,
                           asserted in every process and recorded in every item JSON ; reference rolls re-derived here
                           and checked bit-for-bit against `calibration.json` (sha256 59952214…562d) and against the
                           LP probe's own rolls — see "Validity machinery"
- evaluation construction (C): fresh env per episode ; EVALUATION (primary) env 9,111,000+i / mobility 9,112,000+i,
                           i = 0..23 ; CALIBRATION (tie-in) env 9,121,000+i / mobility 9,122,000+i, i = 0..23 ;
                           never compared with each other ; the oracles consume no RNG (the evaluator deep-copies it)
- evaluator path:          `StepEnvironment.evaluate_actions` (common random numbers, no state committed), with an
                           exact memo of the step-0 warm-start gain (PROGRESS T2-5), verified bitwise 5,760 times
- tree / commit / flags:   mcrl-leo-handover-cf3, branch cf3/pilot-20260911, commit 102b2d4d (staged src/scripts/tests
                           + artifacts/PREREG-FROZEN-2026-08-25-R2.json) ; `scripts/oracle_cells.py` v1 850f0e77…
                           (unfloored cells), v4 7c12ae9a… (floored evaluation cells), v6 40307da6… (floored
                           calibration cell); decision logic identical across versions (v4 vs v5 checked on 1,600
                           mock cases; v4 vs v2 smoke bit-identical on all 15 per-step fields)
- policy / checkpoint:     no trained network is touched. The A1-OFF-s0 final checkpoint (sha256 d7048d59…15cb) is
                           read ONLY for its `TrainerConfig`, to encode the saved 113-dim learner observations
                           (snr_encoding log1p, theta_encoding raw_radians, offset_scale_km 100.0,
                           load_normalization divide_by_num_users)
- n:                       5 cells × 24 episodes × 10 steps × 100 users ; ≈ 2,500 counterfactual evaluations per step
                           (≈ 600,000 per cell) ; sem type: paired per-episode (n = 24) ; served non-inferiority by
                           paired cluster bootstrap over episodes (10,000 draws, seed 20260911)
- in-sample?:              no — no fitting of any kind; both sets disjoint from the training-seed family
- status of this report:   DIAGNOSTIC (Amendment 1 oracle-first screen) ; it decides no gate by itself ;
                           supersedes: `BRANCH-NUMBERS-FLOOR-R1-EVAL.md` (provisional, controller-computed)
```

## Scope

Amendment 1 to Ruling 2 §2 asks, before any training, what a mechanism's **ideal version** achieves: the decisions a learner
would make if it had perfectly learned what the mechanism asks. This report measures the two realised-information cells of
that table — **A-real** (simultaneous best response, the difference-reward credit at the deployed per-user contract) and
**B-real** (one sequential sweep, current-step visibility of earlier users' choices) — plus the **rate-floored** variants the
controller ordered on 2026-09-11 (Amendment 4 §2). No training, no weight change, no new arm: every number comes from rolling
out hand-specified decision rules with the environment's own counterfactual evaluator.

## Definitions (declared in PROGRESS.md T2-3 / T2-13 before any counted run)

At every step t of every episode, with `StepEnvironment.evaluate_actions(actions, rng)` (common random numbers: it deep-copies
the generator and snapshot/restores the one field it writes, so nothing is committed and the rng does not advance):

- **Reference joint action** R_t — R1 = `A m=2dB` (`cf_sources.C1_A_m2dB`), R2 = `B1_NO_NEW_BEAM` (`cf_sources.C3_B1_NO_NEW_BEAM`) —
  computed by the rule's own code on the current observation.
- **Price** η_t = bits(R_t)/joules(R_t) from one evaluation of R_t (the Dinkelbach price at the reference, per the amendment).
  **Objective** F(x) = bits(x) − η_t·joules(x). By construction **F(R_t) = 0 exactly**, so the difference reward of a unilateral
  deviation is D_u(a) = F(R_{−u}, a) − F(R_t) = F(R_{−u}, a), and D_u(a) > 0 is exactly "this deviation raises the step's EE
  above the reference action's EE at this state".
- **Candidates**: every legal slot (`flatnonzero(mask_u)`). `NO_OP` is never a candidate — the action contract
  (`assert_selected_actions_valid`, SDD §3.7 P-4) accepts a no-op only when the mask is empty — so no oracle can switch a user
  off to save energy.
- **Service floor (all cells)**: a candidate is rejected if it leaves ANY user unserved that R_t served, judged against R_t's
  served set. **Rate floor (the `-floor` cells only, R1)**: additionally rejected if any user R_t served falls below 50 % of its
  rate under R_t — the per-user floor of Ruling 2 §2, applied per candidate move. **Ties keep the reference action** (strict
  improvement only, candidates scanned in ascending index).
- **A-real(R)**: every user evaluates all its candidates with the others held at R_t; every user whose best allowed candidate
  has D_u > 0 moves; all moves are committed together. **B-real(R)**: users in order 0..99 (or 99..0), user k best-responding to
  R_t updated by the choices of the users before it; commit after the sweep. F of the running vector never decreases during a
  sweep, so **B-real's committed step EE is ≥ the reference action's step EE at the same state by construction**; A-real has no
  such guarantee.
- Both are **one-step myopic**, hence (amendment §2) **lower bounds** of each mechanism's ceiling — the conservative direction
  for a screen, but see "What the herding means" below for how loose the A-real bound is.

## Validity machinery (every check passed; any failure stops the process by design)

| check | how | result |
|---|---|---|
| **Parity** (the task's "stop and report this first" check) | at every committed step the chosen joint action is evaluated once more immediately BEFORE `env.step` (which advances the rng), and compared with the committed step's energy ledger | **max \|Δbits\| = max \|Δjoules\| = 0.0 exactly**, over all 1,200 committed steps of the 5 cells |
| Step-0 warm-start memo | the memo cuts step-0 cost ~6 × (`_warm_start_gain` → Bessel series, pure in (uid, norad, cell) within a step); the committed `env.step` always runs the pristine path; at every step 0 the reference evaluation, the first 20 and every 100th candidate evaluation are recomputed with the memo OFF and compared bitwise (bits, joules, served vector, and from v4 the per-user rate vector) | **5,760 verifications, max \|Δ\| = 0.0** |
| Memo vs no memo, end to end | 2-step smoke of A-real(R1) and B-real(R1) run once without and once with the memo | identical on all 15 per-step fields and on the full rate lists |
| Replay from the saved joint actions | 122 items replayed on a fresh env from their own seeds: reference reproduced at every step; committed bits/joules equal the saved values bitwise; re-encoded observation and action equal the saved `.npz` rows bitwise; evaluator per-user rates equal committed per-user rates bitwise | **all 122 exact** |
| Advantage vectors reproduce the decisions | `adv_check.py` over the three cells that carry them: for every decision, the chosen action is the arg-max of the stored 28-action advantage vector over allowed legal actions when that max is positive, and the reference action otherwise; NaN exactly on illegal actions | **0 inconsistent decisions in 72,000** |
| Reference rolls | `A m=2dB` re-rolled through the instrumented loop = LP-prev(0, 2) bit-for-bit on both sets and = `calibration.json` on calibration (20 fields); `B1_NO_NEW_BEAM` = `calibration.json` on calibration (7 fields) and = LP-prev(12, 0) bit-for-bit on **both** sets (12 fields) | all identical |
| Pinned archive | `assert_tle_archive_pinned()` = `427e6a91…8fe9` asserted in every process and stored in every item JSON | one value throughout |

## Cross-check against the controller's provisional file

The controller aggregated the two floored evaluation cells independently while this agent was down
(`BRANCH-NUMBERS-FLOOR-R1-EVAL.md`, 18:22 UTC). Re-derived here with this agent's own aggregator: **every field it
prints matches at its printed precision — 11 of 11 for each cell, and B − A = +19.2499 pp against its +19.25.** One
clarification, not a discrepancy: its 316,073 / 415,758 are the **total** disallowed-candidate counts (as its own text
says); the **rate-floor-only** counts are 277,407 (A-floor) and 377,093 (B-floor), and the field
`n_disallowed_floor_only` is present in every v4 item inside `steps_detail[*]`.


### EVALUATION set

| cell | pooled EE (bit/J) | % vs A m=2dB (pooled) | paired per-ep mean ± sem (wins) | served (Δ vs rule; cluster-bootstrap lo95) | lit beams/step | bits / rule bits | rate mean / p10 / min (Mbit/s) | p10 / rule p10 | per-user floor violations (served user-steps < 50 % of own rate under A m=2dB, same step) | ho /user-min | evaluations /step | wall |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| rule `A m=2dB` (R1 rule, own trajectory) | 107,000,983.53 | — | — | 0.99862 | 63.29 | 1.000 | 431.12 / 101.40 / 4.763 | 1.000 | 0 (by definition) | 1.2184 | — | 40.7 s (rollout) |
| rule `B1_NO_NEW_BEAM` (R2 rule, own trajectory) | 102,738,840.61 | -3.983 % | -3.65 ± 0.98 % (7/24) | 0.99825 | 38.33 | 0.586 | 252.68 / 38.39 / 0.006 | 0.379 | — | 0.8733 | — | 35.5 s (rollout) |
| **A-real-floor(R1)** | 113,531,833.46 | +6.104 % | +5.72 ± 0.95 % (23/24) | 0.99925 (+0.06 pp; lo95 +0.02) | 59.13 | 0.992 | 427.21 / 28.60 / 3.960 | 0.282 **degenerate** | 32.18 % (7,717/23,982) | 1.4638 | 2,500 | 226 s/ep |
| **B-real-floor(R1)** | 134,129,417.19 | +25.353 % | +25.71 ± 0.95 % (24/24) | 0.99887 (+0.02 pp; lo95 -0.01) | 66.93 | 1.321 | 569.27 / 165.46 / 16.048 | 1.632 | 0.00 % (0/23,973) | 1.3688 | 2,514 | 233 s/ep |
| **A-real(R1)** | 113,342,542.25 | +5.927 % | +5.67 ± 0.88 % (23/24) | 0.99925 (+0.06 pp; lo95 +0.02) | 58.05 | 0.972 | 418.76 / 27.47 / 2.864 | 0.271 **degenerate** | 33.20 % (7,963/23,982) | 1.5043 | 2,494 | 224 s/ep |
| **B-real(R1)** | 138,591,214.31 | +29.523 % | +29.95 ± 1.03 % (24/24) | 0.99913 (+0.05 pp; lo95 +0.00) | 64.91 | 1.323 | 570.15 / 115.65 / 0.000 | 1.141 | 13.32 % (3,193/23,979) | 1.4468 | 2,511 | 226 s/ep |

### CALIBRATION set

| cell | pooled EE (bit/J) | % vs A m=2dB (pooled) | paired per-ep mean ± sem (wins) | served (Δ vs rule; cluster-bootstrap lo95) | lit beams/step | bits / rule bits | rate mean / p10 / min (Mbit/s) | p10 / rule p10 | per-user floor violations (served user-steps < 50 % of own rate under A m=2dB, same step) | ho /user-min | evaluations /step | wall |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| rule `A m=2dB` (R1 rule, own trajectory) | 112,195,917.54 | — | — | 0.99775 | 62.98 | 1.000 | 450.57 / 111.39 / 2.168 | 1.000 | 0 (by definition) | 1.1704 | — | 42.4 s (rollout) |
| rule `B1_NO_NEW_BEAM` (R2 rule, own trajectory) | 104,190,378.68 | -7.135 % | -6.97 ± 0.71 % (0/24) | 0.99808 | 38.57 | 0.574 | 258.35 / 36.99 / 0.001 | 0.332 | — | 0.8561 | — | 35.3 s (rollout) |
| **B-real-floor(R1)** | 137,497,201.09 | +22.551 % | +22.64 ± 0.59 % (24/24) | 0.99871 (+0.10 pp; lo95 +0.02) | 67.95 | 1.317 | 592.91 / 177.07 / 22.151 | 1.590 | 0.00 % (0/23,969) | 1.3695 | 2,523 | 234 s/ep |

### Per-step-index profile (mean over episodes; EVALUATION set unless named)


**A-real-floor-R1-evaluation-fwd** — committed step EE below the reference action's step EE at the same state on 36.2 % of steps

| t | users moved | candidates disallowed | lit beams | served | per-step p10 (Mbit/s) | step EE / reference step EE (same state) | evaluations |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 75.2 | 2056.6 | 71.6 | 99.33 | 246.9 | 1.0973 | 2,702 |
| 1 | 79.3 | 1499.6 | 64.9 | 99.92 | 133.8 | 1.0579 | 2,702 |
| 2 | 88.5 | 1259.0 | 51.9 | 100.00 | 37.7 | 0.8813 | 2,683 |
| 3 | 95.6 | 977.8 | 44.9 | 100.00 | 15.3 | 0.7229 | 2,654 |
| 4 | 72.1 | 1431.8 | 69.5 | 100.00 | 206.5 | 1.1035 | 2,702 |
| 5 | 72.7 | 1273.0 | 63.5 | 100.00 | 141.3 | 1.0895 | 2,289 |
| 6 | 77.7 | 1101.6 | 54.1 | 100.00 | 56.7 | 0.9795 | 2,141 |
| 7 | 92.5 | 926.8 | 41.8 | 100.00 | 15.6 | 0.7830 | 2,129 |
| 8 | 71.9 | 1391.8 | 68.1 | 100.00 | 212.2 | 1.1044 | 2,702 |
| 9 | 73.1 | 1251.7 | 61.0 | 100.00 | 128.7 | 1.0791 | 2,295 |

**B-real-floor-R1-evaluation-fwd** — committed step EE below the reference action's step EE at the same state on 0.0 % of steps

| t | users moved | candidates disallowed | lit beams | served | per-step p10 (Mbit/s) | step EE / reference step EE (same state) | evaluations |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 58.6 | 2188.9 | 80.9 | 99.17 | 377.6 | 1.1941 | 2,702 |
| 1 | 58.0 | 1849.6 | 75.1 | 99.83 | 291.6 | 1.2052 | 2,702 |
| 2 | 55.3 | 1852.0 | 63.2 | 100.00 | 180.3 | 1.2221 | 2,683 |
| 3 | 55.8 | 1811.0 | 51.1 | 99.96 | 110.9 | 1.2783 | 2,654 |
| 4 | 55.7 | 1740.5 | 75.5 | 100.00 | 316.1 | 1.1806 | 2,702 |
| 5 | 54.1 | 1562.8 | 69.8 | 99.92 | 242.4 | 1.1777 | 2,388 |
| 6 | 49.0 | 1531.6 | 59.6 | 100.00 | 165.1 | 1.2178 | 2,133 |
| 7 | 51.3 | 1438.7 | 49.1 | 100.00 | 93.6 | 1.2627 | 2,085 |
| 8 | 55.3 | 1734.2 | 76.3 | 100.00 | 315.9 | 1.1729 | 2,702 |
| 9 | 52.9 | 1614.0 | 68.6 | 100.00 | 228.4 | 1.1884 | 2,392 |

**B-real-floor-R1-calibration-fwd** — committed step EE below the reference action's step EE at the same state on 0.0 % of steps

| t | users moved | candidates disallowed | lit beams | served | per-step p10 (Mbit/s) | step EE / reference step EE (same state) | evaluations |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 58.7 | 2230.8 | 82.7 | 99.21 | 408.0 | 1.1762 | 2,702 |
| 1 | 61.3 | 1850.7 | 78.2 | 99.62 | 333.0 | 1.2066 | 2,702 |
| 2 | 58.4 | 1769.8 | 66.6 | 100.00 | 205.8 | 1.2413 | 2,702 |
| 3 | 57.0 | 1834.1 | 53.6 | 100.00 | 116.7 | 1.2800 | 2,702 |
| 4 | 55.8 | 1736.9 | 76.3 | 100.00 | 336.4 | 1.1548 | 2,702 |
| 5 | 51.0 | 1598.8 | 70.2 | 99.96 | 266.4 | 1.1633 | 2,436 |
| 6 | 53.3 | 1482.2 | 60.8 | 100.00 | 167.8 | 1.2406 | 2,136 |
| 7 | 49.2 | 1442.1 | 47.9 | 100.00 | 90.7 | 1.2618 | 2,058 |
| 8 | 53.2 | 1763.1 | 74.0 | 100.00 | 310.0 | 1.1523 | 2,702 |
| 9 | 50.9 | 1573.2 | 69.2 | 99.92 | 255.6 | 1.1578 | 2,390 |

**A-real-R1-evaluation-fwd** — committed step EE below the reference action's step EE at the same state on 37.5 % of steps

| t | users moved | candidates disallowed | lit beams | served | per-step p10 (Mbit/s) | step EE / reference step EE (same state) | evaluations |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 77.2 | 1608.7 | 71.2 | 99.33 | 244.7 | 1.1027 | 2,702 |
| 1 | 82.3 | 0.8 | 63.2 | 99.96 | 118.0 | 1.0624 | 2,702 |
| 2 | 89.3 | 0.0 | 52.6 | 100.00 | 38.2 | 0.9076 | 2,683 |
| 3 | 95.6 | 0.0 | 44.7 | 100.00 | 14.9 | 0.6694 | 2,654 |
| 4 | 76.2 | 0.1 | 65.8 | 100.00 | 183.6 | 1.1131 | 2,702 |
| 5 | 77.0 | 1.2 | 61.5 | 100.00 | 144.1 | 1.1026 | 2,265 |
| 6 | 81.5 | 0.1 | 52.7 | 100.00 | 58.2 | 0.9849 | 2,129 |
| 7 | 93.4 | 0.0 | 41.9 | 100.00 | 14.2 | 0.7536 | 2,118 |
| 8 | 76.4 | 0.0 | 67.0 | 100.00 | 201.1 | 1.1157 | 2,702 |
| 9 | 76.6 | 0.7 | 59.8 | 99.96 | 113.4 | 1.0835 | 2,279 |

**B-real-R1-evaluation-fwd** — committed step EE below the reference action's step EE at the same state on 0.0 % of steps

| t | users moved | candidates disallowed | lit beams | served | per-step p10 (Mbit/s) | step EE / reference step EE (same state) | evaluations |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 65.5 | 1608.7 | 80.5 | 99.25 | 328.6 | 1.2160 | 2,702 |
| 1 | 68.8 | 0.6 | 73.8 | 99.88 | 225.4 | 1.2365 | 2,702 |
| 2 | 68.9 | 0.2 | 61.5 | 100.00 | 135.5 | 1.2733 | 2,683 |
| 3 | 67.3 | 0.0 | 49.7 | 100.00 | 76.1 | 1.3048 | 2,654 |
| 4 | 65.5 | 0.0 | 73.2 | 100.00 | 223.7 | 1.2093 | 2,702 |
| 5 | 64.8 | 1.2 | 67.0 | 100.00 | 165.0 | 1.2094 | 2,382 |
| 6 | 63.4 | 0.0 | 56.8 | 100.00 | 105.0 | 1.2902 | 2,128 |
| 7 | 65.0 | 0.0 | 45.8 | 100.00 | 64.3 | 1.3310 | 2,083 |
| 8 | 65.5 | 0.0 | 74.0 | 100.00 | 241.0 | 1.2035 | 2,702 |
| 9 | 62.5 | 0.8 | 66.7 | 100.00 | 165.9 | 1.2281 | 2,375 |

## Adjudication — Amendment 1 §3 rules 1–4 on the **rate-floored** cells (evaluation set, primary)

Reference `A m=2dB` on the same set; the declared +3.3 % / +3.3 pp thresholds are reused, not redefined.
A-real-floor = **+6.104 %**, B-real-floor = **+25.353 %**, **B − A = +19.25 percentage points**
(relative B/A − 1 = +18.14 %; paired per-episode +19.26 ± 1.96 %, 24/24 episodes).

| rule | condition | status |
|---|---|---|
| **1** | A-real ≤ rule + 3.3 % → the difference-reward credit has no room even with perfect information; B1 dropped untrained | **not met arithmetically** (+6.104 % > +3.3 %) — **but the gain does not count**: A-real-floor is throughput-degenerate (p10 0.282 × the rule, Amendment 4 §1.3 floor fails; 32.2 % of its served user-steps below the per-user floor), and Ruling 2 §2 says a gain the rate floor does not protect does not count toward A/B/C. Read together, A-real has **no counted gain**. The two readings point opposite ways on the arithmetic alone; that tension is flagged, not resolved here |
| **2** | A-real wins and B-real ≤ A-real + 3.3 → the credit change alone is the fix; B1 proceeds, sequential decoding not pursued | **not met** (B exceeds A by +19.25 pp; relative +18.14 %) |
| **3** | B-real ≥ A-real + 3.3 → the learner must see the current-step lighting pattern; B2 is the path | **MET, by +19.25 pp** (both the points and the relative reading), and B-real-floor is **not** degenerate: served 0.99887, bits 1.321 ×, p10 1.632 ×, **0** per-user floor violations |
| **4** | both A-real and B-real ≤ rule + 3.3 → only the corner is high; coordination required | **not met** (B-real-floor is high). The corner itself (the centralised search) is outside this report and was not read |

**Rule 5 (deployability, on top of 2–3)** — the nominal-information cells come from the LP probe on the same sets and
harness (`LP-PROBE-2026-09-11.md`, block [A-LP]): the simultaneous side has a deployable cell — LP-prev(1, 0) **+6.66 %**,
served 0.99854, p10 1.016 ×, bits 0.954 — clearing +4.5 % with every side condition; the sequential side has **none**:
LP-seq(1, 0) +6.65 % but bits 0.712 and p10 0.575 ×, LP-seq(2, 0) +8.92 % but served 0.98796 and p10 0.409 ×, and no
LP-seq cell above the rule reaches bits ratio ≥ 0.95. So for the B2 path rule 5 currently **fails**: the realised cell wins
and the nominal cell does not, whose declared next step is an **observation-redesign screen**, still before any training.

## Amendment 4 §2 — the three B2 entry conditions

| # | condition | status |
|---|---|---|
| 1 | B-real − A-real ≥ +3.3 pp of pooled EE over `A m=2dB`, **after** the rate-floor replay of both cells | **MET** — +19.25 pp (floored cells; unfloored the gap is +23.60 pp) |
| 2 | service and the rate floor preserved in **both** cells | **PARTLY** — B-real-floor: served 0.99887 (Δ +0.02 pp, cluster-bootstrap lo95 −0.01 pp), p10 1.632 ×, bits 1.321 ×, 0/23,973 per-user floor violations → preserved. A-real-floor: served fine (0.99925, lo95 +0.02 pp) but p10 0.282 × and 7,717/23,982 (32.2 %) violations → **not** preserved. The failure is in the comparator cell, not in B-real-floor |
| 3 | the extra value representable from the B2 student's observation (T_SEQ `R_repr` ≥ 0.5 for at least one clone on the augmented observation) | **not measured here** — it is the next screen. Its teacher data is complete and shipped: B-real-floor R1 **evaluation** and **calibration**, both with 28-action advantage vectors |

**Therefore: B2 is indicated but not entered** — entering it is an execution-contract change and the owner's decision, and
condition 3 is outstanding. B1 keeps priority (Amendment 4 §2). Nothing here authorises training, and no threshold moved.

## Why the simultaneous cell fails even with a per-move rate floor (measured, not inferred)

A-real's moves are each individually legal — every candidate is evaluated against the reference with all other users held
at R — but **72–96 of the 100 users move in the same step**, so the committed joint action is far from any deviation that
was tested. Consequences measured on the evaluation set: the committed step EE is **below** the reference action's step EE
at the same state on **36.2 %** of steps; lit beams and per-step p10 collapse on a ~4-step cycle (t = 2, 3 and 6, 7:
42–52 beams, p10 15–57 Mbit/s); and adding the per-move floor changes almost nothing — pooled EE +0.18 pp
(paired +0.05 ± 0.37 %, 10/24) and floor violations 33.2 % → 32.2 %. The sequential cell has the opposite structure: each
user best-responds to the vector its predecessors already fixed, F never decreases within a sweep, so **0.0 %** of its
steps fall below the reference step EE, and the floor is satisfied exactly (0 violations, worst ratio exactly 0.5000) at a
cost of 4.17 pp of EE (+29.52 % → +25.35 %).

## The B2 teacher dataset (confirmed independently)

`B-real-floor-R1-calibration-fwd-ep00-obs-actions.npz` carries, as the controller verified: `obs` (1000, 113) float32,
`mask` (1000, 28) bool, `action`, `ref_action` (1000,) int16, `adv` (1000, 28) float32, `adv_disallowed`,
`adv_disallowed_floor` (1000, 28) bool, `episode`, `step`, `user` (1000,) int16. Checked here: `adv` is NaN **exactly** on
illegal actions, `adv[u, ref_action[u]] = 0` on every row with a non-empty mask, and `adv_disallowed_floor ⊆
adv_disallowed` (15,221 of 17,073 flags in this episode are rate-floor-only). Across the whole cell (24,000 decisions)
`adv_check.py` reproduces **every** committed action from the stored vector under the declared rule (0 inconsistent).
In the Af/Bf kinds `adv_disallowed` is the **union** of service-floor and rate-floor rejections; `adv_disallowed_floor` is
the rate-floor-only subset. The floored **evaluation** cells (v4) carry `adv` and the union mask but **not** the
floor-only mask; the calibration cell (v6) carries all three.

**B2 student context rule.** In one sweep each user decides exactly once, in the item's `order` ("fwd" = 0,1,…,99;
"rev" = 99,…,0). At step t, when user u decides, the joint action in force is
`context_t(u)[v] = joint_chosen[t][v]` for every v **before** u in the order, and `joint_ref[t][v]` for v = u and every v
**after** u. That is exactly the vector the oracle evaluated for u, so its base action is `joint_ref[t][u]` and
`adv[u, joint_ref[t][u]] = 0`. Users that never moved have `joint_chosen == joint_ref`, so the rule is well defined
everywhere. All 72 B-type items store `order`, `joint_ref` and `joint_chosen` as 10 × 100 lists.

## HELD — not run, and what each would have answered

| cell | items | what it would answer |
|---|---|---|
| A-real-floor R1 **calibration** | 0/24 | whether A-real's degeneracy is set-specific or structural (the floored simultaneous tie-in) |
| A-real R2 evaluation | 2/24 (v1, no vectors) | whether the credit gain depends on which rule's joint action is the reference; context: the R2 rule itself is −3.983 % vs `A m=2dB` on this set |
| B-real R2 evaluation | 0/24 | same question for the sequential cell |
| **B-real R1 reverse order (evaluation ep 0–5)** | 0/6 | the brief's **order-sensitivity** check — how much of B-real's +25.35 % depends on the fixed 0..99 sweep order. **Open**: this report does not bound it |
| A-real R1 / B-real R1 calibration (unfloored) | 0/24 each | calibration tie-ins for the unfloored cells |
| A-real R2 / B-real R2 calibration | 0/24 each | tie-ins for the second reference |

Queue entries are kept in `scripts/oracle_cells.py` (v6) in `HELD`; removing a tuple and relaunching the four shard
commands resumes it (idempotent, ~23 min per 24-episode cell on 4 processes).

## Files

- Cells (sat `/home/sat/mcrl-v025-h4-probe-ws/results-oracle/`, mirrored to `.scratch/h4-probe/results-oracle/`):
  120 per-episode JSONs for the five complete cells (+2 held R2 items), 122 replay JSONs under `replay/`, and per-cell
  `<cell>-obs-actions.npz`: A-real-floor-R1-evaluation `4961b6d0…53b0`, B-real-floor-R1-evaluation `1cd4ec79…9dd7`,
  **B-real-floor-R1-calibration `a8ee80fc59034d6c608a73966b4e059d2e6fed53ff85e3980ac6935d99d20daa`**,
  A-real-R1-evaluation `84823f5b…f6d2` (no vectors), B-real-R1-evaluation `44add380…c153` (no vectors); all
  sha256-verified identical on both ends. Aggregate: `results-oracle/AGGREGATE-oracle.json`; tables:
  `results-oracle/TABLES-final.md`.
- References: `results-lp/REF-C1_A_m2dB-{evaluation,calibration}.json`,
  `results-lp/REF-EPISODES-{C1_A_m2dB,C3_B1_NO_NEW_BEAM}-{evaluation,calibration}.json`.
- Code: `scripts/oracle_cells.py` (v6; v1–v5 kept beside it), `oracle_replay.py`, `oracle_aggregate.py`,
  `oracle_tables.py`, `adv_check.py`, `ref_rules.py`, `switch_shard.sh`.
- Logs on sat: `logs/oracle-shard*.log`, `logs/oracle-v4-shard*.log`, `logs/oracle-v5-shard*.log`,
  `logs/oracle-smoke*.log`, `logs/ref-rules.log`, `logs/oracle-replay-1.log`.

## Status and scope limits

DIAGNOSTIC. These cells decide no gate by themselves. They are **one-step myopic lower bounds**, and the A-real bound is
demonstrably loose (its own herding costs it more than the credit gains it). The order-sensitivity check and every R2 cell
are HELD, so nothing here separates "sequential information" from "this particular sweep order", and nothing here speaks
to the second reference. Rules are diagnostics, never a success gate: the owner's success gate remains beating baseline
MODQN.
