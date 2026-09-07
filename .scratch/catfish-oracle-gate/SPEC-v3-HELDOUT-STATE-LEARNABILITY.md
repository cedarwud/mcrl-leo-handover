# Frozen held-out focal-state separability gate for R3 Catfish

Status: frozen before collecting the new held-out seed set or fitting any
classifier. Evaluation only. This does not modify rewards, train an RL policy,
add a deployment-time gate, or authorize multi-Catfish composition claims.

Date: 2026-08-26

## Question

Can the exact 112-dimensional observation already available to an independent
Q3 head distinguish which state/action pairs from the state-only
`r3_prev_inactive_split` proposal have a positive R3 topology/load endpoint,
positive immediate EE, and safe service relative to the full checkpoint's
Q1-only action?

The supervised scorer is a diagnostic for state sufficiency. It is discarded
after this gate and may not become a post-training accept/reject coordinator.

## Frozen evidence and partitions

- Source v2 receipt SHA-256:
  `cd88d8c5b17d163a957d8c2e56c2995080c4bb1636cbcc93fae13b234ba50658`.
- Source v2 spec SHA-256:
  `9a0a70dac4f8f892a29a5162692b0464406899d7deb6b8ea6327a17ac369a760`.
- Same episode-8999 checkpoint SHA-256:
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.
- Development seeds are the already-observed v2 seeds
  `2026082401` through `2026082410`:
  - fit: `2026082401` through `2026082408`;
  - score-threshold calibration: `2026082409`, `2026082410`.
- New one-shot held-out seeds are `2026082501` through `2026082510`.
- Every collection uses 100 users, ten steps, and a data-blind draw of ten
  focal users per step without replacement before eligibility.
- No model, threshold, feature, or pass rule may change after any held-out
  outcome is read.

## Data collection

Re-run the exact v2 Q1-only reference and state-only previous-inactive proposal
with common-random-number counterfactual evaluation. Record only the R3 split
family plus:

- the focal user's exact live encoded state presented to the checkpoint,
  length 112 and ordered as
  `[access(28), log1p(SINR)(28), theta_rad(28), load/100(28)]`;
- its action mask and canonical proposal action;
- the v2 selection receipt, physics outcomes, EE identity, and labels.

The development collection must reproduce v2's 1,000 eligible split rows, 184
joint-positive rows, per-seed counts, and physics values exactly before it may
be used. The held-out collection has no expected scientific count.

## Leakage boundary

Classifier input is only the 112-dimensional encoded focal state. Its selected
logit is indexed by the canonical proposal action, matching the Q-head output
contract. The classifier must not read:

- the Q1 reference action, Q1 values, or any other head output;
- another user's state, action, Q value, or current intent;
- reference or alternative current-slot physics;
- active-set changes, current loads, rate/power/EE deltas, or any label.

The dataset may retain those forbidden values solely for evaluation. The
training loader must construct its tensor from `focal_encoded_state` alone and
assert that its dimension is exactly 112.

## Frozen supervised proxy

- Architecture: the runtime `DQNNetwork(112, 28, (100, 50, 50), "tanh")`.
- For each row, take only output `proposal_action` and fit the binary target
  `jointly_positive` with `BCEWithLogitsLoss`.
- Three-member ensemble, Torch CPU seeds `730001`, `730002`, `730003`.
- Examples sorted by `(evaluation_seed, step_index, focal_user,
  proposal_action)` before deterministic seeded shuffling each epoch.
- Adam, learning rate `1e-3`, weight decay `1e-4`, batch size 128, 300 epochs.
- Positive class weight is `N_negative/N_positive` from fit seeds only.
- No early stopping, hyperparameter sweep, calibration-label fitting, or model
  selection.
- Score is the mean of the three sigmoid outputs.
- Acceptance threshold is NumPy's linear 80th percentile of ensemble scores on
  the two calibration seeds. Calibration labels do not set the threshold.

## Required baselines and metrics

Report on the untouched held-out seeds:

1. Always-propose prevalence, mean Delta EE, service-unsafe rate, and coverage.
2. Proposal-SINR-only ranking as a non-fitted observable baseline.
3. Ensemble AUROC and average precision with tie-aware deterministic formulas.
4. At the frozen threshold: count, coverage, joint precision/recall, precision
   lift over held-out prevalence, mean/median Delta EE, mean Delta throughput
   and power, service-unsafe rate, and per-seed values.
5. Seed-clustered descriptive t95 interval for accepted mean Delta EE using
   seed as the independent unit and `t_0.975,9 = 2.2621571628540993`.
6. Each ensemble member's AUROC and average precision as stability diagnostics.

## Frozen pass rule

The state-sufficiency gate passes only if every condition holds on the single
held-out evaluation:

1. all engineering/parity/replay checks pass;
2. ensemble AUROC is at least `0.65`;
3. ensemble average precision is at least both held-out prevalence plus `0.05`
   and `1.25` times held-out prevalence;
4. accepted coverage is between `0.10` and `0.30`, with at least 100 accepted
   rows;
5. accepted joint precision is at least both `0.30` and `1.5` times held-out
   prevalence;
6. accepted mean Delta EE is positive, its seed-clustered descriptive t95 lower
   endpoint is positive, and accepted mean Delta EE is positive in at least 8
   of 10 held-out seeds;
7. at least 8 of 10 held-out seeds contain an accepted jointly-positive case;
8. accepted service-unsafe rate is no more than the larger of `1%` and the
   always-propose unsafe rate plus `0.5` percentage point.

The proposal-SINR baseline is comparative only and cannot make the ensemble
pass or fail. Failure of any primary condition blocks R3 reward training. No
alternate classifier may be tried on the held-out labels under this spec.

## Decision and claim ceiling

- Passing supports only: the current independent Q3 observation contains
  reproducible held-out information that a Q-head-shaped supervised proxy can
  use to enrich immediate R3-and-EE-positive split opportunities.
- Passing next permits a separately frozen activation-aware R3 reward shadow
  test on development seeds; it does not permit RL training directly.
- Failure means the current state/reward direction is insufficient or the
  opportunity is not predictably selectable; redesign must precede training.
- Neither outcome proves temporal-difference learnability, fixed-weight joint
  composition, long-horizon EE gain, or a completed multi-Catfish mechanism.
