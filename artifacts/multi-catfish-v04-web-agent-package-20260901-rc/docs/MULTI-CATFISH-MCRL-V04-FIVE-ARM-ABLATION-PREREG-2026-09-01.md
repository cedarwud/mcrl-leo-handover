# Multi-Catfish MCRL V0.4 five-arm frozen-policy ablation preregistration

Date: 2026-09-01  
Status: frozen pre-outcome work order; authentication hashes completed before
prepare; no five-arm episode opened

## Question and promotion authority

This evaluation asks whether each frozen Catfish route makes a positive
marginal contribution to the same final ratio-of-sums EE, and whether the
three-route policy improves upon the frozen Main MODQN baseline.

Execution is authorized only by the sealed C3 decision `CONFIRM_C3` at
`artifacts/multi-catfish-v04-c3-confirmatory-20260901-r1`, result SHA-256
`bb1a46a8a782a5fb6d3c37391c17866ac0dbbb9bcc7c42bd2c9d8a9f0dd396dd`,
and result-seal SHA-256
`d569049cf648d5d261306ad27d850755070b851a8aecf723f0ebd60d085ee54b`.

The candidate is fixed before any new episode:

- C1/Q1 and C2/Q2: the authenticated V0.3 rung-10 heads embedded in the
  three selected V0.4 hybrids;
- C3/Q3: the authenticated V0.4 selected rung-100 head;
- selected hybrid SHA-256 values, in initialization order
  `2026092101`, `2026092102`, `2026092103`:
  `efc460a785194d189d085df794dc47292798b606871587beb36f073f91ea2171`,
  `019e2160ed7c3802c142a92d4b391d63a0d2e3c0b7cfc0478ab6dbfd0b1178fc`,
  and `c0da537690a1ce1be1992ed62ea1972cf34cd6f86553bbe4e0065fd40d3fe377`;
- Main baseline: the verified completed 9000-episode checkpoint at
  `artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`, SHA-256
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`;
- Main status receipt SHA-256:
  `3e980bc8c47087ff313c5f5589dab053e0f52440fff692d0c88153af4cce7fa1`;
- Main episode-log receipt SHA-256:
  `635e375fe04e890d22aed41eebd40c808b41635a2f15bdadfc4e85b5580769f0`.

No source update, gradient, checkpoint selection, learned route weight,
post-action coordinator, auction, or replay write is allowed.

## Frozen arms and deployment

The five arms are:

| Arm | Deployment score |
|---|---|
| `FULL` | `Q1 + Q2 + Q3` |
| `DROP_C1` | `Q2 + Q3` |
| `DROP_C2` | `Q1 + Q3` |
| `DROP_C3` | `Q1 + Q2` |
| `MAIN` | the frozen legacy MODQN scalarized Main policy |

For each route arm, the evaluator calls `q_values_by_route` exactly once,
sums only the declared route surfaces, applies the one common Boolean legal-
action mask, and performs one masked argmax.  `MAIN` is an independent frozen
baseline, not an empty route set, coordinator, or fourth Catfish.

## Frozen physical-world block

- evaluation seeds: exactly `2026092601`--`2026092630`;
- ephemeris split: TRAIN only; no source validation row and no TEST split;
- three frozen Multi-Catfish initializations;
- 100 users and 10 decision steps per episode;
- identical environment RNG, mobility RNG, episode start, and keyed-fading
  field for every arm and initialization at one evaluation seed;
- keyed-field root components:
  `V04_FIVE_ARM_ABLATION_V1`, the sealed C3 confirmatory result SHA-256, and
  the evaluation seed; arm and initialization are excluded;
- no gradient, optimizer step, source training, replay write, or checkpoint
  write.

The four route arms require `30 x 3 x 4 = 360` episodes.  The initialization-
independent Main checkpoint is evaluated once in each physical world, adding
30 episodes, for exactly 390 simulator episodes.  For pooled FULL-versus-Main
estimators, each sampled Main world total is weighted by three so it matches
the three frozen FULL initializations; this weighting does not change Main's
ratio-of-sums EE.

## Endpoints and estimators

For route `Cj`, the primary marginal endpoint is

\[
\Delta_j = \eta_{\mathrm{FULL}}-\eta_{\mathrm{DROP\text{-}Cj}},
\qquad j\in\{1,2,3\},
\]

where every \(\eta\) is the canonical pooled ratio of total delivered bits to
total energy.  Report absolute and percentage contrasts, delivered bits,
energy, served fraction, outage, action-trace digests, and exact common-world
digests.  Report each contrast pooled, by initialization, and by physical
world, including median and positive-world count.

Also report `FULL` versus `MAIN` pooled, by initialization, and by world.  Use
deterministic paired-world bootstrap with 10,000 replicates, resampling the 30
physical-world seeds while retaining all three Multi-Catfish initializations.
Bootstrap seeds are `2026092691`, `2026092692`, `2026092693`, and `2026092694`
for C1, C2, C3, and Main respectively.

## Predeclared route decision rule

`CONFIRM_Cj` requires all of the following for `FULL` versus `DROP_Cj`:

1. pooled FULL EE is strictly greater;
2. at least two of three initialization-specific EE contrasts are positive;
3. median per-world EE contrast is positive;
4. paired-world bootstrap 95% lower bound is positive;
5. pooled FULL served fraction is non-inferior and at least two of three
   initialization-specific served-fraction contrasts are nonnegative.

Per-world service losses are mandatory nonfatal diagnostics.  `FULL_BEATS_MAIN`
requires positive pooled and median per-world EE contrasts, a positive
bootstrap lower bound, and pooled served-fraction non-inferiority.  The overall
status is `CONFIRM_MULTI_CATFISH` only if `CONFIRM_C1`, `CONFIRM_C2`,
`CONFIRM_C3`, and `FULL_BEATS_MAIN` all pass.  Otherwise the result must name
every failed comparison and use `MULTI_CATFISH_NOT_ALL_CONFIRMED`; no seed,
checkpoint, or threshold may be changed using these outcomes.

Authentication failure, non-finiteness, broken common-world matching, changed
model state, replay mutation, unexpected episode count, or TEST opening makes
the run invalid rather than a scientific result.

## Promotion boundary

`CONFIRM_MULTI_CATFISH` authorizes a separately preregistered parameter sweep
and later held-out evaluation.  It does not authorize additional route
training or a 1500/3000/9000 run.  A failed C1 or C2 gate identifies the exact
route requiring redesign; a passed route is not retrained merely to increase
its observed effect.
