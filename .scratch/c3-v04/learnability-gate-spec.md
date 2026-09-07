# V0.4 C3 fresh learnability gate

Date: 2026-09-01  
Status: sealed `GO_500EP_SCREEN_ONLY`; no TEST or EE endpoint opened

## Fixed evidence boundary

The sealed V0.3 result remains authoritative for the unchanged routes:

- C1 mean skill `+0.1493016867`, positive in 3/3 initializations;
- C2 mean skill `+0.0198744979`, positive in 3/3 initializations;
- C2 anchor-balanced and leave-one-anchor-out gates passed.

Those numbers belong to the sealed masked-mean/max architecture at common
rung 10.  V0.4 carries forward only the independent Q1 and Q2 heads; it does
not carry forward the failed V0.3 Q3 head and does not reopen Q1/Q2 selection.

V0.4 opens only the fresh C3 TRAIN/validation datasets generated from source
seeds `2026092301`--`2026092307`.  It opens no prior C3 validation rows, no
TEST source, no EE endpoint, and no 500EP trajectory.

## Learner and views

- fresh Q3 action-shared local scorer `12 -> 100 -> 50 -> 50 -> 1`;
- learning rate `0.001`, beta `0.1`, shared kappa
  `0x1.2cea89d260f2ap+33`;
- exactly three initialization seeds: `2026092101`, `2026092102`,
  `2026092103`;
- update rungs: `3`, `10`, `30`, `100`, `300`;
- only Q3 receives gradient in this gate;
- Q1/Q2 later consume the V0.3 state view through their frozen masked-mean/max
  heads; Q3 consumes the V0.4 victim-burden view through its local head;
- the gate output names the selected fresh rung `selected_q3_rung`; it never
  changes the sealed Q1/Q2 rung, which remains 10.

For the later deployment screen, each initialization seed uses exactly one
hybrid container.  It loads Q1 head index 0 and Q2 head index 1 from the same
seed's authenticated rung-10 checkpoint and pairs them with the fresh Q3 head
from that same initialization seed.  The required V0.3 checkpoint SHA-256
digests are below; every checkpoint must also carry authority SHA-256
`71f339d840bf999642f9392baa0e0325459672419d5e5e21e2de0731ad2b1755`.

| Initialization | Rung-10 checkpoint SHA-256 |
|---:|---|
| `2026092101` | `f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0` |
| `2026092102` | `6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba` |
| `2026092103` | `507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2` |

## Metric and promotion

For every initialization/rung, compare held-out Q3 pair-difference MAE with
the strongest state-independent TRAIN-only null from action-only, zero, and
TRAIN-median predictions.  To prevent anchor pseudoreplication, compute each
candidate's absolute errors in this fixed order:

1. mean across comparisons belonging to one physical anchor;
2. mean across physical anchors within one validation source seed;
3. mean across the three validation source seeds.

Apply the same anchor-then-seed weighting to every null.  Null parameters are
fit on TRAIN only.  Neither a prolific anchor nor a seed with more retained
rows receives extra weight.

Select one `selected_q3_rung` by minimizing the frozen mean model-to-strongest-
null ratio over the three initializations, using the anchor-then-seed metric
above.  At that rung:

- mean Q3 skill must be strictly positive;
- at least 2/3 initialization skills must be strictly positive;
- collision/duplicate-input census must have zero deterministic conflicting
  target floor;
- dataset, schedule, physical-anchor and physical-action keys, Q3 checkpoint,
  source manifest, sealed real-TLE smoke, frozen PREREG/ephemeris, exact Main
  status/log/checkpoint files, and sealed Q1/Q2 checkpoint lineage must
  authenticate.

Success status: `GO_500EP_SCREEN_ONLY`.  Failure status: `STOP_V04_C3`.
There is no second V0.4 architecture/source/seed/rung fallback under this
authority.

Passing proves fresh C3 learnability only.  C3 becomes independently
EE-positive only if the subsequent matched 500EP comparison
`Q1+Q2+Q3 > Q1+Q2` on canonical ratio-of-sums EE also passes its service
guard.  The full and drop-C3 arms must reuse bit-identical Q1/Q2 tensors and
surfaces; the only score removed in the ablation is Q3.  This protects the
marginal C3 estimand but does not assume unilateral externalities will add
linearly under simultaneous multi-user action selection.

## Post-GO screen contract

The sealed gate selected Q3 rung 100 with mean stronger-null skill
`0.12362866324697346`, positive in all three initializations.  The sealed
result is
`artifacts/multi-catfish-v04-c3-learnability-20260901-r2/result.json` with
status `GO_500EP_SCREEN_ONLY`.  This is learnability-screen evidence only;
it is not an EE result.

The matched screen must first evaluate the sealed selected-rung hybrid before
any further Q3 update.  This is `screen_updates_completed = 0` and is the
primary marginal-C3 comparison.  It then runs exactly 500 additional complete
Q3 TRAIN-batch `update_c3` calls and saves exploratory trend checkpoints at
`screen_updates_completed` 100, 200, 300, 400, and 500.  These are source-
training epochs, not simulator episodes.  Later trend checkpoints must be
reported separately and cannot erase or relabel the selected-rung primary
result.

At every reported checkpoint:

- compare only `FULL = Q1 + Q2 + Q3` with `DROP_C3 = Q1 + Q2`;
- keep Q1/Q2 tensors and surfaces bit-identical and use one common safe mask
  and one argmax;
- use fresh TRAIN evaluation seeds `2026092401`--`2026092410`, 100 users and
  10 decision steps per matched episode, with identical environment,
  mobility, and keyed-fading randomness in the two arms;
- report canonical pooled ratio-of-sums EE, per-seed paired contrasts, served
  fraction, outage, bits, and energy;
- require zero-loss service guard: FULL served-user-steps must not be below
  DROP-C3 per matched pair or in the pooled aggregate;
- open no TEST split and authorize no 1500/3000/9000 promotion.

For V0.4 C3, route survival is the marginal `FULL` versus `DROP_C3` EE and
service comparison above.  This route-specific rule supersedes the older
generic informed-versus-neutral-source survival clause.  The informed C3
source-curation effect remains untested and must not be claimed.
