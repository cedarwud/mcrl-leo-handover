# V0.18 relational-Q3 production source harvester work order

Status: `IMPLEMENTATION_WORK_ORDER_NO_RUN_AUTHORITY`.

## Owned output

Implement one configurable source-only shard runner under
`next-learner-r2/`. It must consume a frozen contract and strict external run
config; no world, lineage, threshold, or checkpoint digest may be silently
selected in code.

## Reuse boundary

Reuse the already authenticated V0.18/V0.15 paths for:

- frozen Q1 rung-10 and learned Q2 rung-3000 loading;
- TLE archive and canonical environment construction;
- `Q1 + learned-Q2` background and native masked argmax;
- current required-power/opening surfaces;
- keyed common-random field;
- exact `measure_zero_marginal_c3` and unchanged ZR formula;
- `encode_relational_zr_c3_state` through `relational_source_bridge`.

Do not copy or alter the EE, OPS-3, ZR, fading, action-mask, or environment
formula.

## Per-anchor order

For each of ten physical steps and 100 focal users:

1. compute/detach Q1, learned Q2, common mask, and background action;
2. capture and authenticate the relational observation;
3. persist the detached `Q1+Q2` surface only in a separate
   evaluation-sidecar buffer, never among learner feature fields;
4. invoke the exact target provider after the capture;
5. build native-bit centred ZR labels (`z3_bits`, not normalized Q values);
6. require bit-exact compatibility equality and unchanged live/RNG digest;
7. execute only the background action and advance once.

There is no target/sign/support filtering. A complete shard has exactly 1000
rows.

## Write-once closure

Aggregate the ten ordered in-memory anchor captures into one authenticated
source closure per `(split, world, lineage)`. Persist an ordered capture
sequence receipt containing each step's predecision digest, exact-target
digest, live-state/RNG before/after digest, anchor digest, row interval, and
compatibility identity. The aggregate arrays must reproduce every child
digest.

Persist a separate authenticated decision-context NPZ/metadata/receipt with
only:

- detached `background_q12` surface;
- matching native mask/reference actions or their exact source-array digests;
- step/user indices and anchor identities;
- Q1/Q2 checkpoint and parameter digests;
- contract, config, source-array, and field-root bindings.

The learner runner must not load the decision-context sidecar. The validation
reporter may load it only after training to compute decision metrics.

## Fail-closed checks

- contract/config/status/hash mismatch;
- undeclared split/world/lineage;
- anything other than TRAIN or VALIDATION;
- reused V0.18 analytic worlds;
- source rows other than exactly 1000;
- nonfinite, mask/reference, kappa, schema, or feature-list drift;
- Q1/Q2 checkpoint or parameter digest drift;
- exact target nonzero at reference/outside mask;
- any positive target outside compatibility;
- environment/RNG mutation during exact measurement;
- overwrite or symlink output;
- TEST or episode-training flag;
- missing/inconsistent sequence or decision-context receipt.

## Tests

Add pure/synthetic tests for ordering, 10×100 aggregation, native-bit target
scale, sidecar isolation, source/sidecar row identity, tampering, duplicate or
missing step, wrong world/split/lineage/kappa/checkpoint, nonfinite arrays,
compatibility mismatch, live-state mutation, and write-once behavior. A real
one-step old-seed smoke may be run only after pure tests pass and cannot count
as efficacy.

Do not start fresh source harvesting from this work order. That requires the
final frozen contract, config, code manifest, server preflight, and explicit
launch record.
