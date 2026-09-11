# Amendment 2 — EE is the only target; handover becomes a reported outcome; service stays a floor

Date: 2026-09-11. **Pre-result** (CF3PILOT had not launched). Owner: *"我最終其實只看 ee 值，所以是可以犧牲
其他的指標來換 ee 值的提升"*. Amends the constrained-endpoint declaration and the pilot declaration.

## What changes

1. **C-H is removed as a constraint.** Handover may be traded for EE. For A1/A2/A3, **`lambda` is fixed at 0**
   (no dual ascent); the action rule is `argmax_a [Q_B − eta Q_E]`. `H_inter`, `H_intra`, total handovers
   per user-minute are **reported beside every EE figure**, and whether each arm would have met the former
   0.6016 bound is stated — as information, not as a pass/fail.
2. **C-S (service) stays.** Service availability non-inferior to A1 OFF within −0.5 pp. **Reason — pooled EE
   without a service floor is degenerate**: serving fewer users lights fewer beams, cuts interference and
   energy, and raises bits per joule; the limit is one beam serving one user. Measured here: a per-satellite
   cap of 3 raised pooled EE 1.162x by serving 58% of user-steps and delivering 0.48x the bits (CAPPENALTY).
   An EE gain bought by dropping users is not a result any reviewer accepts, and it is not what the owner means
   by higher EE.
3. **`Q_H` stays in the network as a monitored head** (trained on `H`, logged, not used in the argmax), so the
   three-head structure and the three catfish are unchanged in code. C2's contribution is now **as a data
   source** — the conservative hysteresis rule, which already dominates the frozen learner on EE — not as a
   handover guard. The C2 "INACTIVE" classification of Amendment 1 is replaced by: report how many evaluation
   decisions would change if `lambda` were set so that `H_inter` met 0.6016 (diagnostic only).

## What this does and does not buy

- It removes the one mechanism that could have **cost** EE in the pilot (a binding `lambda`). With every
  known policy except `MAX_NOMINAL_GAIN` under 0.6016, the practical effect is small.
- **It does not raise the ceiling much on its own**: on the measured frontier, EE is nearly flat from
  `A m=2dB` (0.586 handovers) to `A m=6dB` (0.364), and the highest-churn rule (`m=0`, 0.712) is *lower*.
  More churn is not where extra EE is. The EE lever this physics exposes is **fewer lit beams at full
  service** (less interference) — which is C3's direction — and the objective change (dropping `r2`), which A1
  already carries.
- **Thesis framing**: the narrative becomes "maximise EE at a service floor; handover reported". Reviewers will
  still ask about churn (DR-2/ASK-2: >1.2/min is above the published envelope), so the handover numbers must be
  in the main table, not an appendix.

## Unchanged

Arms, seeds, 1000 episodes, `gamma = 1`, common vector replay 8/9 + 1/27 x 3, `eta` fixed to episode 500,
learning check, per-episode reseeded evaluation, learning-speed readings, declared reading (with C-H removed
from it; C-S retained).
