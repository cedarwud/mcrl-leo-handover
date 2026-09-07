# Multi-Catfish MCRL V0.14 Q3 support-detectability probe

Status: **FROZEN BEFORE PROBE MODEL OUTCOME**

Frozen on 2026-09-03 (Asia/Taipei), after the failed V0.14 uniform-MSE
learner gate and its descriptive source census. This is deliberately a
post-gate, source-only diagnostic on the same already-opened TRAIN and
VALIDATION panel. It cannot provide fresh-world confirmation, deployed EE
evidence, or permission for episode training by itself.

## 1. Fixed question and unchanged components

The only question is whether the existing target-free 287-dimensional Q3
state contains enough information to identify the rare C3 actions that have
positive compatible ZR surplus when the uniform surface-MSE objective is
replaced by a support-aware objective.

The following remain unchanged:

- C1/Q1;
- C2/OPS-3 teacher and the learned rung-3000 Q2 checkpoints;
- C3/ZR teacher, compatibility label, kappa, safe mask, and 287-dimensional
  deployable state;
- hidden widths `(100, 50, 50)`, tanh activation, Adam learning rate `0.001`;
- deterministic cyclic 512-anchor batches and 3,000 updates;
- TRAIN worlds `2026108001`--`2026108004`, VALIDATION worlds
  `2026108005`--`2026108007`, three frozen lineages, and three learner seeds;
- one masked argmax and literal unweighted Q-head addition.

No simulator step, new source harvest, TEST world, episode-policy update,
threshold sweep, seed search, formula change, or C2 redesign is authorized.

## 2. Frozen support-aware objective

For every legal non-reference action, let

`y = compatibility AND ((z3(a) - z3(reference)) / kappa > 0)`.

Two action-set scorers with the existing masked mean/max architecture are
trained jointly:

1. a class-balanced BCE support classifier; and
2. a positive-amplitude regressor, optimized only where `y=true`, with a
   softplus output.

The positive BCE weight is the TRAIN-only ratio `N_negative/N_positive`.
Because this estimates an equal-class posterior, inference restores the
natural TRAIN prior `pi` by

`p = sigmoid(logit_balanced + log(pi / (1 - pi)))`.

The unsupported amplitude is fixed before learning to the TRAIN-only
conditional mean of normalized unsupported target deltas, `mu_negative`.
The Q3 diagnostic score is

`Q3_hat = p * positive_amplitude_hat + (1 - p) * mu_negative`,

with the route reference gauged to exactly zero. BCE and positive-amplitude
MSE have unit coefficients; neither coefficient is tuned.

Arm A uses only the unchanged 287-dimensional deployable state. Arm B adds
the ten local features at the route reference action as extra global
features. Arm B is diagnostic and cannot be deployed or promoted to the
method from this run.

## 3. Fixed diagnostics

For each lineage and pooled where applicable, report:

- support-label ROC AUC and the TRAIN action-prior null AUC;
- positive-amplitude MAE and RMSE in kappa units;
- student action-change exposure, positive supported-change fraction, and
  teacher-change recovery;
- the joint diagnostics under both exact OPS-3 and the corresponding frozen
  rung-3000 learned Q2 checkpoint.

Arm B is explanatory only. The binding decision uses Arm A only.

## 4. Binding stop/go rule

`GO_REBALANCED_Q3_GATE` requires Arm A to satisfy all of:

1. pooled supported-change fraction is at least `0.50` with exact OPS-3;
2. pooled supported-change fraction is at least `0.50` with learned Q2; and
3. at least two of three lineages have nonzero action-change exposure under
   each Q2 context.

Otherwise the decision is `STOP_THREE_HEAD` for the current fixed ZR-C3
state/teacher family. AUC, amplitude error, Arm B, and teacher recovery are
diagnostic and cannot override the rule after outcome access.

A GO authorizes only implementation and a separately frozen rebalanced-Q3
learnability gate. It does not itself authorize the five-arm 100-episode run.
That run remains conditional on a learned, deployable Q3 checkpoint passing
the next gate. No new intermediate diagnostic may be inserted.

## 5. Frozen evidence and code closure

- prior gate result SHA-256:
  `289949275e9241cc5b885b1fc588a69e97446f755d9cf4f3ccfe9542f03f6c7c`
- source panel SHA-256:
  `d6ce30bb5859be9d48f6f5739dc4ea03245f24feb9dff3e9f429e5ec1d2a81b4`
- Q2 checkpoint, initialization `2026108101`:
  `d981232a9e56e6ce71c8e8b1fda789efc69852d4a6a22e918a2992ddc58a533d`
- Q2 checkpoint, initialization `2026108102`:
  `9a45f5bc125d6ba453d7d74dbc640ec3d2e927fffb161518e383e6b3aabbe8ef`
- Q2 checkpoint, initialization `2026108103`:
  `8f9d2e5d1749515a0896137082b1430419ae1b8a794d28ea772a23c86648be81`
- probe runner:
  `51cd29c445c87de59dedf89c3bc08009850711a965fac9ff96e80ac68c0baac2`
- W157 probe tests:
  `c911e7b4f7dd5a7bd3a150bc632d0fe3bbf380774d3fd10ee76edf2fd4306780`
- unchanged V0.14 action-set head:
  `b1ac88edd16cbe19a0b9ffc8371c1bf15f161ebdb656802d80126d3fe402481`
- unchanged V0.14 Q3 state:
  `f6fa25893446a814b9a55cf32b058b4c25cf8537008f687f85a67e09cf742027`

Immediately before freeze, W157 passed `5 passed`; the combined W155--W157
selection/physical/probe tests passed `13 passed`. These are implementation
facts only.

## 6. Evidence discipline

This probe was designed after observing the original V0.14 gate and source
census, so its result is mechanistic development evidence. It cannot be
called fresh confirmation or algorithm efficacy. Fable 5.1 Max session
`b41383f4-f20f-4be2-aa65-a57071672356` independently selected
`Q3_OBJECTIVE_REBALANCE` and this single support-detectability probe; that
review is advisory, not experimental evidence.
