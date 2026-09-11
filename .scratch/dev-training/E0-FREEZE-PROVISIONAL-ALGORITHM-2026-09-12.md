# Provisional algorithm frozen at the end of E0 — 2026-09-11 22:44 UTC

**Development lane.** This is a DEVELOPMENT freeze under Amendment 6 (§1 level E0/E1, §7): it fixes what goes into E1. It is
not an Amendment 4 screening result, it is not formal evidence, and nothing here is a paper claim. Every number behind it is a
DEVVAL reading on development seeds; the formal evaluation, calibration and CONFIRM episodes were never touched.

The freeze rule was fixed by the controller **before** the k = 2 numbers existed: "if k = 2 preserves the direction and QoS,
freeze the provisional algorithm at once". It did, so it is frozen.

## The frozen provisional algorithm
1. **Execution contract**: the B1 engineering core (`cf_credit.py` + the `credit_mode` wiring, commit `63b02dc0`), with
   `credit_mode = equal_share` as the development credit. The credit interface stays pluggable; the final credit is an
   instantiation branch, not a blocker, and no exact-DR learner is trained.
2. **Learner**: the current ratio learner unchanged -- three heads `(Q_B, Q_E, Q_H)`, `DQNNetwork (100, 50, 50)` tanh, 113-dim
   observation (112 MODQN + normalised remaining steps), 28-action contract, deployed score `S = Q~_B - eta~ Q~_E` with
   `lambda = 0`, `eta` fixed at `eta_0 = 110,507,234.83444457` bit/J, units `s_B = 13,329,082,278.45065`,
   `s_E = 120.61728174105066`, gamma 1 with a true terminal at step 10, Adam 1e-3, batch 128, replay 50,000, hard target sync
   every 50 episodes, one update per decision step, P-03 filtering, epsilon 1.0 -> 0.01 over round(2000 N / 9000) episodes.
3. **Teacher**: **T0 = LP-prev(c = 1, m = 0)** computed from the RAW user state at collection time and stored with each
   transition (action + 28-score vector). `R_repr` 0.93-0.98 (T0REPR); the privileged sequential teacher is not the direction
   (`R_repr(T_SEQ)` ~ 0.13-0.15, B2 closed).
4. **Injection mechanism (PROVISIONAL PRIMARY)**: **D3 unconditional large margin** on the deployed score over the legal
   actions, `lambda_E * (max_a [S(s,a) + m 1(a != a_T)] - S(s, a_T))`, `m = 0.15`, `lambda_E = 1.0`, `a_T` = T0's action.
5. **Strongest soft comparator**: **D2-T0 with tau = 0.3** (`alpha = 1`, `tau_s = 1`), by the outcome-independent rule
   "strongest observed DEVVAL comparator not worse on the listed QoS quantities". No claim that tau = 0.3 beats tau = 1
   (they are tied at +0.007 %); tau = 3 is excluded as D2's representative configuration.
6. **Matched null**: **D3-null** -- the same loss, margin, weight, schedule, masks and gradient path with the target replaced
   by a seeded uniform legal action from `(9_241_000, k)`; no T0 quantity in any loss input.
7. **Code**: worktree branch `dev/e0-harness-20260912`, commit `05aadf1bb24a9e3a730975227fbf27ab7760deb9` (aggregator
   `27f69edf`), base = B1 engineering core `63b02dc0`. `cf_ratio.py`, `cf_credit.py` and `modqn.py` are unedited.

## The development evidence behind it (DEVVAL, 24 episodes, greedy, paired per-episode, direction only)

| seed | depth | D0 | D3-T0 | D3-T0 vs paired D0 | D3-null | D3-T0 vs D3-null | D3-T0 served / p10 / min rate |
|---|---|---:|---:|---|---:|---|---|
| k = 0 | 100 | 103,059,357 | 112,444,230 | +9.11 %, 24/24 | 57,469,863 | x1.96, 24/24 | 0.99862 / 1.189e8 / 6.62e6 |
| k = 0 | 300 | 105,491,679 | 113,130,902 | +7.24 %, 24/24 | -- | -- | 0.99829 / 1.174e8 / 8.26e6 |
| k = 1 | 100 | 99,301,084 | 112,551,340 | +13.34 %, 24/24 | 60,547,627 | x1.86, 24/24 | 0.99850 / 1.145e8 / 4.80e6 |
| k = 2 | 100 | 103,531,085 | 113,082,503 | +9.23 %, 24/24 | 46,917,434 | x2.41, 24/24 | 0.99813 / 1.246e8 / 6.79e6 |

Three paired development seeds, same direction on all three, no QoS collapse (served >= 0.998 everywhere, p10 always above
the paired D0's, minimum served-user rate always above the paired D0's). Against the DEVVAL references: D3-T0 reaches
0.96 of T0 = LP-prev(1,0), 1.03 of MAX_NOMINAL_GAIN, 1.01 of `A m=2dB`, and **+19.8 % / +19.2 % / +19.8 % over the frozen
baseline MODQN eq-(16) checkpoint** at k = 0/300, k = 1/100 and k = 2/100 -- a **development reference**, never formal evidence.
The matched null is the load-bearing control: the same margin loss aimed at a random legal action is worse than no teacher at
all (-39 % to -55 % against the paired D0) and collapses service to ~0.93, so D3-T0's gain is T0's action information and not
the shape or the weight of the extra loss.

## What is NOT frozen (open for E1)
The episode budget (E0 ceiling was 300; no arm needs to reach it), the number and identity of the E1 seeds, the credit branch
(`equal_share` is the development credit, not an endorsement), the observation-contract branch, the eta schedule beyond
`eta = eta_0`, the catfish count and multi-teacher composition, and every S1 element (frozen configuration, all declared arms,
matched nulls, the `rho / R_repr` gate, service and rate floors, confidence statements). E1's purpose remains what Amendment 6
§8 says: a modest multi-seed run that fixes the shared kernel and its development hyperparameters before any formal screen.
