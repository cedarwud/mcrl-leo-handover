# Multi-Catfish MCRL V0.14 Q2/Q3 learnability preregistration

Status: **FROZEN BEFORE FRESH SOURCE ACCESS**

Frozen on 2026-09-03 (Asia/Taipei). This contract authorizes only a
TRAIN-only counterfactual source harvest and a supervised Q2/Q3 learnability
gate. It does not authorize TEST access, episode-policy training, a deployed
EE claim, or the 9000-episode run.

## 1. Scientific question and fixed method

The final objective remains the canonical Main-only ratio-of-sums energy
efficiency. V0.14 retains three independent action-value heads and one common
safe-action argmax:

`argmax_a [Q1(s,a) + Q2(s,a) + Q3(s,a)]`.

- C1/Q1 is the frozen V0.3 rung-10 EE head.
- C2/Q2 distils the unchanged OPS-3 projected-persistence teacher `z2` from
  the 448-dimensional, target-free OPS-3 feature state.
- C3/Q3 distils the unchanged V0.13 zero-marginal-energy-supported spatial
  teacher `z3` from the 287-dimensional, target-free ZR state.
- Source behaviour is frozen `Q1 + OPS3`; source collection never updates a
  learner.
- Q2 is gauged against the Q1-only reference action. Q3 is gauged against the
  Q1+OPS3 background reference action. The two reference actions are allowed
  to differ; their Boolean safe-action masks must be identical.
- Q1, Q2, and Q3 never share parameters or optimizers. No target, target
  sign, counterfactual outcome, Q-value, reference action, or selected action
  is a deployable Q2/Q3 state input.

State schema digests:

- Q2: `440f98a87b8a91be647e28a15a2509853f8566864a2be560b8602421185efc50`
- Q3: `04b46fa95db7c20c41e5ac379be7580d649e8b9a746ce5a01d2623c8d72facb6`

## 2. Fresh source panel

- TRAIN worlds: `2026108001`, `2026108002`, `2026108003`, `2026108004`
- VALIDATION worlds: `2026108005`, `2026108006`, `2026108007`
- frozen Q1 lineages: `2026092101`, `2026092102`, `2026092103`
- one shard for every world-lineage pair: 21 shards
- 100 users and 10 physical steps per shard
- keyed fading component inherited unchanged from the V0.13 source authority
- execution location: isolated Ubuntu-server root
  `/home/sat/mcrl-v014-learnability-20260903-r1`
- no TEST world is opened

The declared fresh world and learner seeds had no occurrence in `docs/`,
`src/`, `tests/`, or non-V0.14 `.scratch/` sources before this freeze.

## 3. Learner panel

Initialization-to-lineage mapping is positional:

- `2026108101` -> `2026092101`
- `2026108102` -> `2026092102`
- `2026108103` -> `2026092103`

For both heads:

- action dimension: 28
- independent shared-action scorer: legal-set local features plus masked
  legal-set mean/max context
- hidden layers: `(100, 50, 50)`
- activation: `tanh`
- optimizer: Adam
- learning rate: `0.001`
- pairwise gauge coefficient: `0.1`
- common normalization: OPS-3 `kappa`, hexadecimal
  `0x1.2cea89d260f2ap+33`
- deterministic cyclic batch size: 512
- update rungs: `3, 10, 30, 100, 300, 1000, 3000`
- CPU execution; complete worlds, not rows, define TRAIN/VALIDATION separation

One common deployment rung is selected by the minimum mean strongest-null MAE
ratio pooled over both heads and all three initializations, ties to the lower
rung. Route-local best rungs remain diagnostic only. All binding head and
joint decisions use the common deployment rung.

## 4. Frozen gate

Q2 and Q3 each pass their head gate only if mean validation skill versus the
strongest frozen null is strictly positive and at least two of three
initializations have strictly positive skill.

The joint diagnostic forms:

- background teacher: `Q1 + z2/kappa`
- full teacher: `Q1 + z2/kappa + z3/kappa`
- learned student: `Q1 + Q2_hat + Q3_hat`

The binding joint support gate passes only if:

1. the learned student changes at least one background action in the pooled
   panel and in at least two of three initializations; and
2. strictly more than half of pooled changed student actions, and strictly
   more than half in at least two of three initializations, have the frozen
   positive ZR support label (`compatibility=true` and `z3>0`).

Teacher-action imitation, agreement improvement over the background, and
teacher-change recovery are recorded as diagnostics but are not binding.
They cannot be promoted to binding gates after outcomes are opened.

`PASS_LEARNABILITY_GATE` requires Q2 head pass, Q3 head pass, and joint
support pass. A pass authorizes only a separately sealed TRAIN-development
100-episode five-arm physical evaluation. A failure is reported without
tuning formula, state, thresholds, seeds, scale, or horizon against these
worlds. More oracle confirmation is prohibited.

## 5. Pre-outcome five-arm endpoint commitment

If the learner gate passes, the next bounded block uses exactly:

- `FULL = Q1 + Q2 + Q3`
- `DROP_C1 = Q2 + Q3`
- `DROP_C2 = Q1 + Q3`
- `DROP_C3 = Q1 + Q2`
- `MAIN`, the independent frozen legacy baseline

Every route uses the same Boolean safe mask, an unweighted literal head sum,
and one masked argmax; a dropped head is omitted without renormalization.
The endpoint is pooled total bits divided by pooled total energy, with service
reported separately. It is a 100-episode TRAIN-development screen and writes
a checkpoint receipt at episode 100. Its physical adapter, fresh evaluation
seed block, and artifact hashes must be sealed before that block opens any
episode. It is not 9000-episode training and cannot support a final efficacy
claim.

The desired directional screen is `FULL` above each three drop arm and above
`MAIN` in pooled ratio-of-sums EE, with service noninferiority and at least two
of three initializations showing the same sign for each Catfish contrast.
Every world need not be positive, and pairwise synergy is not required at
this stage.

## 6. Frozen code closure

- `afda043ac7a9da749d22101a0e0a22d15ef68c23a030d3371ae7c5f92c9b58c2`
  `.scratch/multi-catfish-v014-learner/run_v014_source_shard.py`
- `c38f3cc662333465b4c1da01f2774a4904340466a5366bda5635ef9fcd64c750`
  `.scratch/multi-catfish-v014-learner/run_v014_learner_gate.py`
- `c0a56b005aa209f16072e8fbee16424062be653f8cb416acabbd5668749f1a82`
  `.scratch/multi-catfish-v014-learner/run_v014_five_arm_evaluation.py`
- `b1ac88edd16cbe19a0b9ffc8371c1bf15f161ebdb656802d801db21c15183fa8`
  `src/mcrl/algorithms/ee_axis_v014_head.py`
- `6d65a8993dcf9fdb3492b28a2f606a0d73d41bc80126da42237e91a15019094a`
  `src/mcrl/runtime/ee_axis_v014_gate.py`
- `48f3af59317a34fff18698976fa11118e60f6c45cf457448153b2b5b8f51c362`
  `src/mcrl/runtime/ee_axis_v014_learnability.py`
- `412ce464975e369e44cbb1825e02f1ce36b2ce84882bf110a63b351d63de07f7`
  `src/mcrl/runtime/ee_axis_v014_q2_state.py`
- `f6fa25893446a814b9a55cf32b058b4c25cf8537008f687f85a67e09cf742027`
  `src/mcrl/runtime/ee_axis_v014_q3_state.py`
- `68251ff750410ff74abfb412df83bafef459831874abfcfbee6e1e04d1adea02`
  `src/mcrl/runtime/ee_axis_ops3.py`
- `6847069235ce3789c9f2f76bfd1de9f7a4e02402788eed0fabcc0ab57faed35a`
  `src/mcrl/runtime/ee_axis_ops3_live.py`
- `36084d422651abd7168c0113c3a0e7f19d706ae21c86c0895b0b32f229a3691c`
  `src/mcrl/runtime/ee_axis_zero_marginal_c3.py`
- `f52753fd8e6a374ae6e03fde64cc749ce39fb9c21aa482adef7f12323a6192b3`
  `src/mcrl/runtime/ee_axis_zero_marginal_c3_live.py`
- `c97ed8f92e8123ca6bf861d327bb653e623f91cd1ad219890f1ac63b00a82217`
  `.scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py`

Immediately before freeze, W146-W155 passed: `39 passed`. A two-step real old-
seed source smoke produced 200 authenticated rows, and the real merger loaded
200 TRAIN plus 100 VALIDATION rows while preserving 124 and 61 differing
Q2/Q3 route-local references respectively. These are plumbing facts, not
efficacy evidence.

## 7. Evidence discipline

Source labels, oracle signs, validation skill, or a TRAIN-development
five-arm sign are not final algorithm efficacy. No result from this contract
may be described as held-out TEST evidence. The 9000-episode run requires a
separate notice to the user and a later frozen authority.

