# Draft brief — T_SEQ representability screen (Amendment 4 §2 condition 3 for B2). NOT DISPATCHED YET

Written 2026-09-11 ~18:55 UTC by the controller while the oracle lane finishes, so it can be dispatched the moment its
preconditions are confirmed. **Preconditions (check before dispatching):** (1) the oracle agent has confirmed the floored
B-real R1 **calibration** cells (24/24) and that they carry the per-decision 28-action advantage vectors, the observation, the
legal mask, the reference and chosen joint actions and the user order; (2) the oracle agent's own aggregation of the floored
**evaluation** cells matches `.scratch/h4-probe/BRANCH-NUMBERS-FLOOR-R1-EVAL.md`; (3) the owner has not ruled otherwise on B2.

## What this screen decides

Amendment 4 §2 condition 3: B2 may be entered only if the extra value of the sequential oracle over the simultaneous one is
**representable from the B2 student's observation**. The measured gap to explain is **B-real-floor − A-real-floor = +19.25
percentage points** of `A m=2dB`'s EE on the 24 evaluation episodes (B-floor +25.35 %, served 0.99887, bits ratio 1.321, p10
1.632 × the rule; A-floor +6.10 % but p10 0.282 ×, throughput-degenerate).

## The B2 observation (declare exactly, then never change it)

The current 113-dim student input plus **only** what a sequential protocol can deliver at execution time: for each candidate
beam, whether it is already lit **this step** by an earlier-deciding user, and how many earlier users have chosen it. Nothing
else: no realised rates, no other user's SINR, no future information. The exact encoding (one extra block of 28 counts,
normalised like the previous-step loads) is declared in the screen's own progress file before any fit.

## Method (mirrors the T0 screen, `.scratch/t0-repr/`)

1. **Placebo first**: re-roll the floored B-real teacher on two calibration episodes from the saved joint actions and
   reproduce the stored per-episode EE exactly; and reproduce `A m=2dB` on both sets bit-for-bit.
2. **Data**: the floored B-real R1 **calibration** cells (24 episodes, 24,000 decisions) as training data — out of the
   evaluation set by construction. Reconstruct each decision's B2 observation from the saved order, `joint_ref` and
   `joint_chosen` (context for user u = chosen actions of the users before u in the order, reference actions after).
   Held out by episode, as CFSCREEN did.
3. **Two clones**, the learner's own architecture on the B2 observation: one-hot behaviour cloning of the teacher's action,
   and soft distillation toward `softmax(advantage vector / τ)` with τ chosen on a validation split and written down before any
   closed-loop run.
4. **Closed loop**: roll each clone on the 24 evaluation episodes **sequentially** (fixed order 0..99, the clone seeing earlier
   users' choices this step), greedy, per-episode reseeded, pinned archive. Report pooled EE with bits and joules, served,
   per-served-user rate mean / p10 / min, lit beams, H_inter / H_intra.
5. **Metric**: `R_repr(T_SEQ) = (EE(clone) − EE(A m=2dB)) / (EE(B-real-floor) − EE(A m=2dB))` on the evaluation set, and the same
   on the calibration set; plus held-out top-1 / top-3 and the teacher's conditional action entropy given the B2 observation
   (the T0 screen found the closed-loop metric, not accuracy, is the one that decides — a longer-trained clone scored better
   on accuracy and worse in closed loop).
6. **Reading, declared here**: condition 3 is met iff at least one clone reaches `R_repr ≥ 0.5` on both episode sets **and** is
   not throughput-degenerate (served ≥ 0.995, bits ratio ≥ 0.95, p10 ≥ 0.5 × the rule's on the same set). A clone that recovers
   the headroom by collapsing the rate tail does not count, exactly as for the oracle cells.
7. Compare against the T0 baseline clone on the same evaluation episodes, so the **marginal** value of the sequential
   information is visible, not just its absolute level.

## Constraints

Measurement only, no learner training. Own workspace on `sat`, ≤ 3 processes, `nice -n 16`, 1 BLAS thread, < 5 GB, detached for
anything long, pinned archive asserted, exact-PID kills, sha256-verified copies, PROGRESS.md updated after every step, the
formal evaluation / calibration episodes never used for any tuning choice (τ is selected on a validation split of the
calibration data). Report `.scratch/b2-representability/T-SEQ-REPRESENTABILITY-2026-09-12.md`, first line = `R_repr` for both
clones on both sets, the degeneracy check, and whether Amendment 4 §2 condition 3 is met.
