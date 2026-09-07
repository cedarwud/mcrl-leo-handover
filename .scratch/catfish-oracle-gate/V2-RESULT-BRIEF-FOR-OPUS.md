# V2 state-only Catfish result brief for independent review

Date: 2026-08-26

This is an evaluation-only result. No reward has been changed and no new model
has been trained.

## Frozen and verified evidence

- Spec: `SPEC-v2-STATE-ONLY.md`, SHA-256
  `9a0a70dac4f8f892a29a5162692b0464406899d7deb6b8ea6327a17ac369a760`.
- Runner: `run_state_observable_gate.py`, SHA-256
  `7f26af5e56460ff297f16cd2de4bf208cbe0a51e7b94091529bd547e623b7b63`.
- Confirmation receipt: `state-only-confirmation-seeds-10-k10-v2.json`,
  SHA-256
  `cd88d8c5b17d163a957d8c2e56c2995080c4bb1636cbcc93fae13b234ba50658`.
- Ten frozen evaluation seeds, 100 users, 10 focal users per step, ten steps;
  3,000 sampled family rows and 1,822 evaluated rows.
- The fail-closed replay reconstructed all focal-state canonical proposals,
  EE identities, role/joint labels, sampling rows, and summaries.
- The proposal function receives only the focal user's current access vector,
  valid candidate physical keys, previous beam loads, candidate SINR, and the
  focal Q1 reference action. It does not receive other users' simultaneous Q1
  actions, current intent sets, or current-slot outcomes.
- Outcomes are used only for discarded evaluation labels.

## Frozen gate results

### R2 access-visible exact stay

- Eligible: 758/1,000.
- Joint handover-role-positive and immediate-physics-EE-positive: 393/758 =
  51.84697%, present in 10/10 seeds.
- Descriptive seed-clustered t95 interval: 48.33% to 55.20%.
- All eligible one-step proposals mean Delta EE: +0.03668 Mbit/J.
- Joint cases mean Delta EE: +0.7450 Mbit/J.
- This remains unidentified for full handover-aware EE because the simulator
  has no physical handover interruption `T_HO` or access energy `E_HO`.
- Required avoided equivalent burden over all eligible rows: median 0,
  mean 130.15 Mbit/s, p95 511.89 Mbit/s; equivalent avoided power median 0,
  mean 1.538 W, p95 7.030 W.
- Frozen decision: advance only to physical handover parameterisation.

### R3 previous-inactive split/open

- Eligible: 1,000/1,000.
- True role-positive opening plus positive load relief: 424/1,000.
- Joint role-positive, service-safe, immediate-EE-positive: 184/1,000 = 18.4%,
  present in 10/10 seeds.
- Per-seed joint rates: 13%, 13%, 19%, 18%, 23%, 13%, 26%, 21%, 20%, 18%.
- Descriptive seed-clustered t95 interval: 15.23% to 21.57%.
- Blindly applying all 1,000 canonical proposals has mean Delta EE
  -0.05377 Mbit/J.
- Applying the role endpoint alone to all 424 true openings has mean Delta EE
  -0.23709 Mbit/J.
- The 184 joint cases have mean Delta EE +0.61591 Mbit/J, mean throughput
  gain +0.86576 Gbit/s, and mean power increase +6.3033 W.
- Joint cases are distinguishable only imperfectly in simple descriptive focal
  features: proposal SINR median 47.72 versus 31.01 for non-joint rows; valid
  candidate count median is 28 in both groups; previous reference load median
  is zero in both groups.
- Frozen decision: advance only to a held-out focal-state learnability screen.

### R3 previous-active lower-load alternative

- Eligible: 64/1,000.
- Joint: 3/64 = 4.6875%, present in 3/10 seeds.
- Frozen decision: drop or redesign before training.

## Current runtime reward that is now suspect

`src/mcrl/env/service.py::r3_counting` returns `-U_b` for every served user.
It is decomposable and its population sum is `-sum_b U_b^2`, but it has no
activation-power price. The v2 result shows that load relief/opening alone is
not an EE certificate.

## Constraints for the next decision

1. Keep three distinct roles: R1 direct system EE, R2 continuity/handover, R3
   congestion/topology shaping.
2. No post-training auction, coordinator, or access to other users'
   simultaneous decisions.
3. The final action may use the existing fixed MODQN multi-objective
   scalarisation, but R2/R3 rewards must each have a defensible causal path to
   EE and must not merely clone R1.
4. Do not authorize RL training yet. The next allowed step is a held-out
   state-feature separability/learnability screen and R2 physical
   parameterisation.
5. Separate opportunity, learnability, joint composability, long-horizon gain,
   and trained-policy claims.

## Review questions

1. Is the evidence sufficient to retain R2 exact-stay and R3 selective split as
   the two indirect-EE roles, while dropping the lower-load alternative?
2. Specify a minimal leakage-resistant held-out learnability gate for R3:
   allowed focal-state features, seed split or cross-validation unit, model
   class, baselines, primary metrics, minimum coverage, and pass/fail rule.
3. Compare these R3 reward directions and recommend one falsifiable next
   candidate:
   - keep `-U_b` unchanged;
   - activation-regularised local congestion reward, such as
     `-(U_b + lambda_on I[newly activated])` or its action advantage;
   - a marginal activation-economics term using throughput benefit minus an
     EE-priced beam activation cost, while avoiding duplication of R1.
4. State what parameters must be frozen independently rather than tuned on the
   ten confirmation seeds.
5. Give the maximum defensible claim now, and the exact next experiment before
   any RL training.

