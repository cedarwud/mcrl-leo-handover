# Multi-Catfish MCRL V0.4 C2 DESIGN-EVAL amendment

Date: 2026-09-01 18:30 CST (UTC+8)  
Status: `PREOUTCOME_FROZEN_AMENDMENT`  
Claim ceiling: `BOUNDED_DESIGN_SCREEN_ONLY_NO_C2_EFFICACY_CLAIM`

This amendment closes the missing DESIGN-EVAL split in
`MULTI-CATFISH-MCRL-V04-C2-PARALLEL-CANDIDATE-PREREG-2026-09-01.md`.
It was fixed while the three Phase-B shards were still running, before their
merge and before any P0/P1/P2 Q2 update. It does not modify the sealed Phase-A
schedule or its outcomes.

## 1. Bound upstream authority

- parallel-candidate preregistration SHA-256:
  `da3b5c40d528fab85dc32aed6a13de8c465be3c5f26638d0cc4997dd30c6eeab`
- support-complete census preregistration SHA-256:
  `3e5910b9b1d609d429e9f54f53cbdc3d4b3c7828d15c93bd40e048db42714c86`
- Phase-A result file SHA-256:
  `c07e6f12d87ff2cc2cca5fbb5550264424e2c443979ad8c77f940b75782ed4da`
- Phase-A seal file SHA-256:
  `779531ffc72fa5d63e4b0ecc1a4972fecbaceb2d5f04a495a2b850edb63821b3`

## 2. Frozen DESIGN-EVAL block

The DESIGN-EVAL seeds are exactly the ordered closed block
`2026092901`--`2026092910`: ten worlds, without replacement, extension, or
substitution. Each episode has exactly 100 users and ten decision steps.

These seeds are DESIGN-EVAL-only. They may never enter a later TRAIN,
validation, TEST, or confirmatory block, regardless of the result. The
synthetic unit-test literal `2026092901` in
`tests/test_w91_ee_axis_v04_c2_sibling_schedule.py` has fabricated digests and
opened no physical outcome; it is a recorded namespace collision, not data
reuse.

Before the first DESIGN-EVAL episode, a write-once prepare receipt must bind:

- this seed list and order;
- 100 users, ten steps, and the exact eligible-arm set from sealed Phase B;
- rungs `100`, `500`, and `1500` offline Q2 updates;
- initialization seeds `2026092101`, `2026092102`, and `2026092103`;
- the simulator/source manifest, frozen checkpoints, and Phase-B digest;
- the common-random-field rule below;
- `counterfactual_outcomes_evaluated=false`, `test_split_opened=false`, and
  `held_out_ee_evaluated=false`.

No topology, seed, or policy may be replaced after that receipt. Any invalid
or incomplete world makes the applicable screen invalid; it is not permission
to draw a replacement.

## 3. Paired physics and exact budget

For evaluation seed (e), the keyed-field root components are exactly

```text
("V04_C2_PARALLEL_SCREEN_V1", phase_b_sha256, e)
```

Candidate ID, rung, initialization seed, and policy label are excluded. The
environment RNG, mobility RNG, episode start, and fading field must therefore
be byte-identical across all eligible arms, rungs, and initializations for the
same world.

Let \(\mathcal E\) be the Phase-B `eligible_arms` set. The exact episode count
is

```text
90 * |eligible_arms| + 30 DROP-C2 + 10 Main.
```

Thus the maximum is 310 episodes when P0, P1, and P2 are all eligible. A
different count from the formula is `INVALID`, not a result. The update ladder
counts offline replay updates, not simulator episodes, and does not authorize
any 1500/3000/9000-episode MODQN run.

## 4. Arm-specific Phase-B authorization

Phase B must publish a machine-readable `eligible_arms` set:

- P0 is eligible iff G-C passes;
- P1 and P2 are eligible iff the Q13 physical gate passes in at least two of
  three initialization lineages;
- the screen is authorized iff at least one arm is eligible;
- no eligible arm yields `NEXT_C2_FORMULA_PHYSICS_BATCH_REQUIRED`.

There is no method-level `DROP_C2`, `RETIRE_C2`, or two-Catfish disposition.

## 5. Metric partition and selection

Training-side metrics are reported but cannot select an arm or rung: loss,
pair objective, pair-MSE diagnostic, gauge-MSE, full-action target regret,
target Spearman correlation, Q2-to-Q1+Q3 magnitude, update count, minibatch
order, checkpoint digest, and finiteness receipts.

Only DESIGN-EVAL rollout evidence selects the arm and rung:

- total delivered bits and total energy;
- canonical pooled ratio-of-sums EE;
- paired `FULL - DROP-C2` EE, pooled and by initialization;
- downstream delivered-bit change by initialization.

`FULL - Main`, action-flip rate, served fraction, and outage are reported as
non-gating diagnostics. Non-finite values, invalid actions, incomplete traces,
or broken lineage make a cell invalid rather than negative.

The four design-positive gates and tie rule remain exactly those in the
parallel-candidate preregistration. Because the selected cell is the maximum
over up to nine arm/rung cells on one ten-world block, its EE is a biased
ranking statistic. It may not be quoted as an effect size, marginal C2
contribution, or paper-level efficacy evidence.

## 6. Preserved formula and final boundary

This amendment does not change the canonical final ratio-of-sums EE, direct
unweighted `Q1 + Q2 + Q3`, one shared mask and one argmax, or the fixed C2
physics:

- \(\lambda_0=84,994,621.12635651\) bit/J;
- \(\kappa=10,097,071,012.757404\) bit;
- \(H^c=4\), downstream offsets \(k=1,2,3\);
- hold-while-legal with one monotone release;
- no sign filtering, positive-only admission, or target clipping.

Final acceptance still requires fresh frozen evidence that `FULL > DROP-C1`,
`FULL > DROP-C2`, `FULL > DROP-C3`, and `FULL > Main`. The ten DESIGN-EVAL
worlds cannot be used for that confirmation.

